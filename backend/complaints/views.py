import json

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from accounts.roles import Language
from audit.services import record
from cases.models import AgeRange, IncidentCategory
from cases.serializers import CaseCreateSerializer
from core.permissions import HasRole, IsBeneficiaryUser
from institutions.models import Region

from . import services
from .models import Complaint, ComplaintMessage, ComplaintStatus, Concerning


# ---------------- Serializers ----------------

class SubmitSerializer(serializers.Serializer):
    concerning = serializers.ChoiceField(choices=Concerning.choices)
    child_age_range = serializers.ChoiceField(choices=AgeRange.choices, default="UNKNOWN")
    district = serializers.CharField(max_length=80)
    region = serializers.ChoiceField(choices=Region.choices, required=False, allow_blank=True)
    immediate_danger = serializers.BooleanField(default=False)
    language = serializers.ChoiceField(choices=Language.choices)
    reply_language = serializers.ChoiceField(choices=Language.choices, required=False)
    written_statement = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    ai_consent = serializers.BooleanField(default=False)
    audio_seconds = serializers.IntegerField(required=False, min_value=0, max_value=600)


def message_for_complainant(m):
    """Show police messages in the complainant's language when a translation exists."""
    if m.from_police and m.translated_text:
        return {"text": m.translated_text, "original": m.text, "machine_translated": m.machine_translated}
    return {"text": m.text, "original": None, "machine_translated": False}


def complainant_view(c, detail=False):
    data = {
        "id": str(c.id), "reference": c.reference, "status": c.status, "concerning": c.concerning,
        "created_at": c.created_at, "respond_by": c.respond_by, "reply_language": c.reply_language,
        "first_response_at": c.first_response_at, "reviewed_at": c.reviewed_at,
        # The case itself is only linked when the officer allowed this complainant to follow it.
        "case": {"id": str(c.case_id), "reference": c.case.reference} if c.case_id and c.complainant_can_follow_case else None,
        "unread_messages": sum(1 for m in c.messages.all() if m.from_police and m.read_at is None),
    }
    if detail:
        data["messages"] = [
            {"id": str(m.id), "from_police": m.from_police, "created_at": m.created_at, **message_for_complainant(m)}
            for m in c.messages.all()
        ]
    return data


def police_view(c, detail=False, request=None):
    data = {
        "id": str(c.id), "reference": c.reference, "status": c.status, "concerning": c.concerning,
        "child_age_range": c.child_age_range, "district": c.district, "region": c.region,
        "immediate_danger": c.immediate_danger, "language": c.language, "reply_language": c.reply_language,
        "created_at": c.created_at, "respond_by": c.respond_by, "is_overdue": c.is_overdue,
        "ai_status": c.ai_status, "ai_category": c.ai_category, "ai_urgency": c.ai_urgency,
        "has_audio": hasattr(c, "audio"), "case": {"id": str(c.case_id), "reference": c.case.reference} if c.case_id else None,
        "complainant": {"name": c.complainant.display_name()},
    }
    if detail:
        audio = getattr(c, "audio", None)
        data.update({
            "written_statement": c.written_statement, "ai_consent": c.ai_consent, "transcript": c.transcript,
            "english_text": c.english_text, "ai_summary": c.ai_summary,
            "ai_key_facts": json.loads(c.ai_key_facts) if c.ai_key_facts else [], "ai_model": c.ai_model,
            "ai_error": c.ai_error, "ai_processed_at": c.ai_processed_at, "internal_note": c.internal_note,
            "audio": {"mime_type": audio.mime_type, "size_bytes": audio.size_bytes, "duration_seconds": audio.duration_seconds} if audio else None,
            "complainant_can_follow_case": c.complainant_can_follow_case,
            "can_follow_possible": c.concerning in services.FOLLOW_RELATIONSHIP,
            "messages": [
                {"id": str(m.id), "from_police": m.from_police, "author": m.author.display_name(), "created_at": m.created_at,
                 "text": m.text, "text_language": m.text_language, "translated_text": m.translated_text,
                 "translated_language": m.translated_language, "machine_translated": m.machine_translated}
                for m in c.messages.select_related("author")
            ],
            "events": [{"action": e.action, "note": e.note, "created_at": e.created_at,
                        "actor": e.actor.display_name() if e.actor else "System"} for e in c.events.select_related("actor")],
        })
    return data


class ComplaintThrottle(UserRateThrottle):
    scope = "complaint"

    def allow_request(self, request, view):
        return True if request.method == "GET" else super().allow_request(request, view)


# ---------------- Complainant API ----------------

class MyReportsViewSet(viewsets.ViewSet):
    permission_classes = [IsBeneficiaryUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    throttle_classes = [ComplaintThrottle]

    def _qs(self, request):
        return Complaint.objects.filter(complainant=request.user).select_related("case").prefetch_related("messages")

    def list(self, request):
        return Response([complainant_view(c) for c in self._qs(request)])

    def retrieve(self, request, pk=None):
        c = self._qs(request).filter(pk=pk).first()
        if c is None:
            return Response({"error": {"code": "not_found", "message": "Not found.", "details": None}}, status=404)
        c.messages.filter(from_police=True, read_at__isnull=True).update(read_at=timezone.now())
        return Response(complainant_view(c, detail=True))

    def create(self, request):
        ser = SubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        c = services.submit_complaint(request.user, ser.validated_data, request.FILES.get("audio"), request=request)
        c.refresh_from_db()
        return Response(complainant_view(c, detail=True), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def reply(self, request, pk=None):
        c = self._qs(request).filter(pk=pk).first()
        if c is None:
            return Response({"error": {"code": "not_found", "message": "Not found.", "details": None}}, status=404)
        services.complainant_reply(request.user, c, request.data.get("text"), request=request)
        return Response(complainant_view(self._qs(request).get(pk=pk), detail=True))


# ---------------- Police API ----------------

class RegisterSerializer(serializers.Serializer):
    child_pseudonym = serializers.CharField(max_length=60)
    age_range = serializers.ChoiceField(choices=AgeRange.choices)
    incident_category = serializers.ChoiceField(choices=IncidentCategory.choices)
    district = serializers.CharField(max_length=80)
    region = serializers.ChoiceField(choices=Region.choices)
    protection_concerns = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    immediate_risk = serializers.BooleanField(default=False)
    allow_complainant_to_follow = serializers.BooleanField(default=True)
    internal_note = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class ComplaintViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [HasRole.of({"POLICE"})]

    def get_queryset(self):
        inst = self.request.user.institution
        if inst is None:
            return Complaint.objects.none()
        qs = Complaint.objects.filter(assigned_institution=inst).select_related("case", "complainant", "audio")
        status_filter = self.request.query_params.get("status")
        if status_filter == "OPEN":
            qs = qs.filter(status__in=services.OPEN_STATUSES)
        elif status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def list(self, request):
        services.retry_stuck()
        qs = self.get_queryset()
        return Response({"count": qs.count(), "results": [police_view(c) for c in qs[:200]]})

    def retrieve(self, request, pk=None):
        c = self.get_object()
        record(request.user, "complaint.view", c, request=request)
        return Response(police_view(c, detail=True))

    @action(detail=True, methods=["get"])
    def audio(self, request, pk=None):
        c = self.get_object()
        audio = getattr(c, "audio", None)
        raw = services.decrypt_audio(audio) if audio else None
        if raw is None:
            return Response({"error": {"code": "not_found", "message": "No audio.", "details": None}}, status=404)
        record(request.user, "complaint.play_audio", c, request=request, security=True)
        resp = HttpResponse(raw, content_type=audio.mime_type.split(";")[0])
        resp["Cache-Control"] = "no-store, private"
        resp["Content-Disposition"] = "inline"
        return resp

    @action(detail=True, methods=["post"])
    def message(self, request, pk=None):
        c = self.get_object()
        services.police_message(request.user, c, request.data.get("text"), bool(request.data.get("needs_info")), request=request)
        return Response(police_view(self.get_queryset().get(pk=c.pk), detail=True))

    @action(detail=True, methods=["post"])
    def register(self, request, pk=None):
        c = self.get_object()
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = dict(ser.validated_data)
        allow = v.pop("allow_complainant_to_follow")
        note = v.pop("internal_note", "")
        case_ser = CaseCreateSerializer(data={**v, "date_reported": timezone.localdate().isoformat(),
                                              "preferred_language": c.reply_language}, context={"request": request})
        case_ser.is_valid(raise_exception=True)
        services.register_case(request.user, c, case_ser.validated_data, allow, note, request=request)
        return Response(police_view(self.get_queryset().get(pk=c.pk), detail=True))

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        c = self.get_object()
        services.decline(request.user, c, request.data.get("message", ""), request.data.get("internal_note", ""), request=request)
        return Response(police_view(self.get_queryset().get(pk=c.pk), detail=True))

    @action(detail=True, methods=["post"], url_path="rerun-ai")
    def rerun_ai(self, request, pk=None):
        c = self.get_object()
        if not c.ai_consent:
            raise ValidationError({"detail": ["The complainant did not agree to AI processing."]})
        Complaint.objects.filter(pk=c.pk).update(ai_status="PENDING")
        services.process_complaint(c.pk)
        record(request.user, "complaint.rerun_ai", c, request=request)
        return Response(police_view(self.get_queryset().get(pk=c.pk), detail=True))
