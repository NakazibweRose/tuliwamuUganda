from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.services import record
from cases import access
from cases.models import FollowUp, FollowUpStatus
from core.permissions import IsInstitutionalUser, IsPlatformAdmin
from notifications.services import notify

from .models import AssistanceRequest, AssistanceStatus, AssistanceType, SupportService
from .serializers import AssistanceRequestStaffSerializer, SupportServiceSerializer


class SupportServiceViewSet(viewsets.ModelViewSet):
    serializer_class = SupportServiceSerializer
    filterset_fields = ["category", "is_active"]
    search_fields = ["name", "description", "institution__name"]
    http_method_names = ["get", "post", "patch"]

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated()]
        return [IsPlatformAdmin()]

    def get_queryset(self):
        qs = SupportService.objects.select_related("institution")
        if self.request.user.role != "ADMIN":
            qs = qs.filter(is_active=True)
        return qs


@transaction.atomic
def create_assistance_request(user, case, data, request=None):
    req = AssistanceRequest.objects.create(
        case=case, requested_by=user, request_type=data["request_type"], message=data.get("message", ""),
        preferred_contact_time=data.get("preferred_contact_time", ""), assigned_to=case.assigned_officer,
    )
    urgent = req.request_type == AssistanceType.SAFETY_CONCERN
    FollowUp.objects.create(
        case=case, assistance_request=req, institution=case.lead_institution, assigned_to=case.assigned_officer,
        created_by=user, description=f"Respond to assistance request: {req.get_request_type_display()}",
        due_date=timezone.localdate() + timedelta(days=0 if urgent else 2),
    )
    notify(case.assigned_officer, "ASSISTANCE_REQUEST", link=f"/app/assistance", dedup_key=f"assist:{req.id}")
    record(user, "assistance.create", req, request=request, case_id=str(case.id), type=req.request_type)
    return req


class AssistanceRequestStaffViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Assistance requests for officers responsible for the case (lead institution or probation on the team)."""

    permission_classes = [IsInstitutionalUser]
    serializer_class = AssistanceRequestStaffSerializer
    filterset_fields = ["status", "request_type"]

    def get_queryset(self):
        u = self.request.user
        cases = [c.id for c in access.team_cases(u) if access.can_review_beneficiary_content(u, c)]
        return AssistanceRequest.objects.filter(Q(case_id__in=cases) | Q(assigned_to=u)).select_related(
            "case", "requested_by", "assigned_to"
        ).distinct()

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        req = self.get_object()
        new_status = request.data.get("status")
        message = (request.data.get("response_message") or "").strip()
        if new_status not in {AssistanceStatus.IN_PROGRESS, AssistanceStatus.RESOLVED, AssistanceStatus.CLOSED}:
            raise ValidationError({"status": ["Choose In progress, Responded or Closed."]})
        if new_status == AssistanceStatus.RESOLVED and not message:
            raise ValidationError({"response_message": ["Write a short response the family can read."]})
        if not access.is_on_team(request.user, req.case):
            raise PermissionDenied()
        with transaction.atomic():
            req.status = new_status
            if message:
                req.response_message = message[:500]
                req.responded_at = timezone.now()
            req.save()
            if new_status in {AssistanceStatus.RESOLVED, AssistanceStatus.CLOSED}:
                req.follow_ups.filter(status=FollowUpStatus.PENDING).update(
                    status=FollowUpStatus.DONE, completed_at=timezone.now(), outcome_note=f"Request {new_status.lower()}"
                )
            if message:
                notify(req.requested_by, "ASSISTANCE_RESPONSE", link=f"/me/requests", dedup_key=f"assist-resp:{req.id}:{req.responded_at.timestamp()}")
        record(request.user, "assistance.respond", req, request=request, status=new_status)
        return Response(AssistanceRequestStaffSerializer(req).data)
