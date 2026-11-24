import secrets
import uuid

from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import mixins, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from accounts.roles import ANONYMOUS_REPORT_TRIAGE_ROLES, Role
from audit.services import record
from cases.serializers import CaseCreateSerializer
from cases.services import register_case
from core.permissions import CanViewAnalytics, HasRole
from institutions.models import Institution

from .models import AnonymousReport, AnonymousReportEvent, ReviewStatus, SmsMessage, SmsStatus, VerificationStatus
from .serializers import AnonymousReportDetailSerializer, AnonymousReportListSerializer, SmsMessageSerializer
from .sms.callbacks import apply_delivery_report
from .ussd.engine import UssdEngine


class UssdThrottle(AnonRateThrottle):
    scope = "ussd"


def _token_ok(request):
    expected = settings.AFRICASTALKING_CALLBACK_TOKEN
    return not expected or secrets.compare_digest(request.GET.get("token", ""), expected)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([UssdThrottle])
def ussd_callback(request):
    """Africa's Talking USSD callback. Responds with text/plain 'CON …' or 'END …'."""
    if not _token_ok(request):
        return HttpResponse("END Service unavailable.", content_type="text/plain", status=403)
    session_id = (request.data.get("sessionId") or "").strip()
    if not session_id:
        return HttpResponse("END Invalid request.", content_type="text/plain", status=400)
    result = UssdEngine(channel="USSD").handle(
        session_id[:100], request.data.get("phoneNumber", ""), request.data.get("serviceCode", ""), request.data.get("text", "")
    )
    return HttpResponse(result.render(), content_type="text/plain")


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([UssdThrottle])
def ussd_events(request):
    """Session end notifications: delete the session's temporary state immediately."""
    if not _token_ok(request):
        return HttpResponse(status=403)
    from .models import UssdSession

    session_id = (request.data.get("sessionId") or "").strip()
    if session_id:
        UssdSession.objects.filter(session_id=session_id).delete()
    return HttpResponse("OK", content_type="text/plain")


@api_view(["POST"])
@permission_classes([HasRole.of({"COMPLAINANT"})])
def ussd_simulator(request):
    """Web simulator for demonstrations. Uses the SAME UssdEngine as the real gateway callback.
    The client keeps the AT-style cumulative `text` and a random session id."""
    session_id = str(request.data.get("sessionId") or "")
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise ValidationError({"sessionId": ["Use a random UUID per simulated session."]})
    phone = f"sim-{request.user.pk}"  # used only as a rate-limit key, never stored
    result = UssdEngine(channel="SIMULATOR").handle(f"sim-{session_id}", phone, settings.AFRICASTALKING_USSD_SERVICE_CODE, request.data.get("text", ""))
    return Response({"response": result.render(), "end": result.end, "text": result.text,
                     "service_code": settings.AFRICASTALKING_USSD_SERVICE_CODE})


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def sms_delivery_callback(request):
    if not _token_ok(request):
        return HttpResponse(status=403)
    apply_delivery_report(request.data)
    return HttpResponse("OK", content_type="text/plain")


@api_view(["GET"])
@permission_classes([CanViewAnalytics])
def sms_dashboard(request):
    qs = SmsMessage.objects.all()
    by_status = dict(qs.values_list("delivery_status").annotate(n=Count("id")).values_list("delivery_status", "n"))
    by_type = list(qs.values("notification_type").annotate(n=Count("id")).order_by("-n"))
    recent = SmsMessageSerializer(qs.select_related("recipient")[:50], many=True).data
    return Response({
        "provider": "africastalking" if settings.SMS_PROVIDER == "africastalking" and settings.AFRICASTALKING_API_KEY else "mock",
        "totals": {
            "submitted": qs.exclude(delivery_status__in=[SmsStatus.BLOCKED]).count(),
            "delivered": by_status.get(SmsStatus.DELIVERED, 0),
            "failed": by_status.get(SmsStatus.FAILED, 0),
            "pending": by_status.get(SmsStatus.SUBMITTED, 0) + by_status.get(SmsStatus.QUEUED, 0) + by_status.get(SmsStatus.DEFERRED, 0),
            "simulated": by_status.get(SmsStatus.SIMULATED, 0),
            "blocked_no_consent": by_status.get(SmsStatus.BLOCKED, 0),
        },
        "by_status": by_status,
        "by_type": by_type,
        "recent": recent,
    })


TRIAGE = HasRole.of(ANONYMOUS_REPORT_TRIAGE_ROLES)


class AnonymousReportViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Triage of unverified anonymous reports by police / probation officers."""

    permission_classes = [TRIAGE]
    filterset_fields = ["review_status", "verification_status", "category", "immediate_danger", "channel"]
    search_fields = ["reference_code", "general_location"]

    def get_queryset(self):
        if self.request.user.institution is None:
            return AnonymousReport.objects.none()
        return AnonymousReport.objects.select_related("assigned_institution", "converted_case").prefetch_related("events__actor")

    def get_serializer_class(self):
        return AnonymousReportListSerializer if self.action == "list" else AnonymousReportDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        report = self.get_object()
        record(request.user, "anonymous_report.view", report, request=request)
        if report.review_status == ReviewStatus.NEW:
            self._event(report, "OPENED", "")
        return Response(AnonymousReportDetailSerializer(report).data)

    def _event(self, report, action_name, note):
        AnonymousReportEvent.objects.create(report=report, actor=self.request.user, action=action_name, note=note[:500])

    def _respond(self, report):
        report.refresh_from_db()
        return Response(AnonymousReportDetailSerializer(report).data)

    @action(detail=True, methods=["post"], url_path="safe-contact")
    def safe_contact(self, request, pk=None):
        """Reveal the optional safe contact. Audited as a security-relevant access."""
        report = self.get_object()
        record(request.user, "anonymous_report.reveal_contact", report, request=request, security=True)
        self._event(report, "CONTACT_VIEWED", "")
        return Response({"safe_contact": report.optional_safe_contact or None})

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        report = self.get_object()
        if report.review_status == ReviewStatus.CONVERTED:
            raise ValidationError({"detail": ["This report has already been converted to a case."]})
        new_review = request.data.get("review_status")
        verification = request.data.get("verification_status")
        note = (request.data.get("note") or "").strip()
        allowed_review = {ReviewStatus.URGENT, ReviewStatus.UNDER_REVIEW, ReviewStatus.REFERRED, ReviewStatus.CLOSED}
        if new_review and new_review not in allowed_review:
            raise ValidationError({"review_status": ["Not an allowed review status."]})
        if verification and verification not in VerificationStatus.values:
            raise ValidationError({"verification_status": ["Unknown assessment outcome."]})
        if new_review in {ReviewStatus.REFERRED, ReviewStatus.CLOSED} and not note:
            raise ValidationError({"note": ["Record the reason / outcome."]})
        inst_id = request.data.get("assigned_institution_id")
        with transaction.atomic():
            if new_review:
                report.review_status = new_review
            if verification:
                report.verification_status = verification
            if inst_id:
                report.assigned_institution = Institution.objects.filter(pk=inst_id, is_active=True).first()
                if report.assigned_institution is None:
                    raise ValidationError({"assigned_institution_id": ["Unknown institution."]})
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.save()
            self._event(report, f"REVIEW:{new_review or '-'}:{verification or '-'}", note)
        record(request.user, "anonymous_report.review", report, request=request, review_status=report.review_status,
               verification_status=report.verification_status)
        return self._respond(report)

    @action(detail=True, methods=["post"], url_path="convert-to-case")
    def convert_to_case(self, request, pk=None):
        """An officer decides, after assessment, that an official case is justified. Never automatic."""
        report = self.get_object()
        if report.converted_case_id:
            raise ValidationError({"detail": ["Already converted."]})
        if request.user.role != Role.POLICE:
            raise PermissionDenied()
        if report.verification_status != VerificationStatus.CREDIBLE:
            raise ValidationError({"detail": ["Record the assessment outcome 'needs action' before creating a case."]})
        payload = dict(request.data)
        payload.setdefault("incident_category", report.category if report.category != "OTHER" else "OTHER")
        payload.setdefault("child_pseudonym", f"Child from report {report.reference_code}")
        payload.setdefault("age_range", "UNKNOWN")
        payload.setdefault("date_reported", timezone.localdate().isoformat())
        payload.setdefault("preferred_language", report.preferred_language)
        payload.setdefault("immediate_risk", report.immediate_danger == "YES")
        ser = CaseCreateSerializer(data=payload, context={"request": request})
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            case = register_case(request.user, ser.validated_data, request=request)
            report.converted_case = case
            report.review_status = ReviewStatus.CONVERTED
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.save()
            self._event(report, "CONVERTED_TO_CASE", f"Case {case.reference} opened")
        record(request.user, "anonymous_report.convert", report, request=request, case_id=str(case.id))
        return self._respond(report)
