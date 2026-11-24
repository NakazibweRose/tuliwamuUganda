from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import User
from accounts.roles import CASE_REGISTRATION_ROLES
from audit.services import record
from core.permissions import IsInstitutionalUser
from notifications.services import notify

from . import access, services
from .models import BeneficiaryAccessGrant, CaseStage, CaseUpdate, FollowUp, FollowUpStatus, Visibility
from .serializers import (
    CaseCreateSerializer,
    CaseDetailSerializer,
    CaseEditSerializer,
    CaseListSerializer,
    CaseStageSerializer,
    CaseUpdateCreateSerializer,
    CaseUpdateSerializer,
    FollowUpSerializer,
    GrantCreateSerializer,
    GrantSerializer,
    ReviewSerializer,
    StageChangeSerializer,
    StatusHistorySerializer,
)


def visible_updates(user, case):
    """Timeline entries the caller may see: case-team entries plus their own institution's internal notes."""
    return CaseUpdate.objects.filter(case=case).filter(
        Q(visibility=Visibility.CASE_TEAM) | Q(institution=user.institution)
    ).select_related("institution", "author", "reviewed_by")


class CaseViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                  mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsInstitutionalUser]
    filterset_fields = ["stage", "incident_category", "immediate_risk", "region"]
    search_fields = ["reference", "child__pseudonym", "district", "external_reference"]
    ordering_fields = ["created_at", "updated_at", "date_reported"]
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        # Object-level isolation: anything outside the caller's case team simply does not exist (404).
        return access.team_cases(self.request.user).select_related(
            "stage", "lead_institution", "assigned_officer", "child"
        )

    def get_serializer_class(self):
        if self.action == "list":
            return CaseListSerializer
        if self.action == "create":
            return CaseCreateSerializer
        if self.action == "partial_update":
            return CaseEditSerializer
        return CaseDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        case = self.get_object()
        record(request.user, "case.view", case, request=request, sensitive=access.can_view_sensitive(request.user, case))
        return Response(CaseDetailSerializer(case, context={"request": request}).data)

    def create(self, request, *args, **kwargs):
        if request.user.role not in CASE_REGISTRATION_ROLES:
            raise PermissionDenied("Your role cannot register cases.")
        ser = CaseCreateSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        case = services.register_case(request.user, ser.validated_data, request=request)
        return Response(CaseDetailSerializer(case, context={"request": request}).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        case = self.get_object()
        if not access.is_lead(request.user, case):
            raise PermissionDenied("Only the lead institution can edit core case details.")
        ser = CaseEditSerializer(case, data=request.data, partial=True, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        record(request.user, "case.edit", case, request=request, fields=sorted(ser.validated_data.keys()))
        return Response(CaseDetailSerializer(case, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="change-stage")
    def change_stage(self, request, pk=None):
        case = self.get_object()
        ser = StageChangeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.change_stage(request.user, case, ser.validated_data["stage"], ser.validated_data["note"], request=request)
        case.refresh_from_db()
        return Response(CaseDetailSerializer(case, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        case = self.get_object()
        return Response(CaseUpdateSerializer(visible_updates(request.user, case), many=True).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        case = self.get_object()
        qs = case.status_history.select_related("from_stage", "to_stage", "changed_by", "institution")
        return Response(StatusHistorySerializer(qs, many=True).data)

    @action(detail=True, methods=["post"])
    def updates(self, request, pk=None):
        case = self.get_object()
        ser = CaseUpdateCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        update = services.add_update(request.user, case, ser.validated_data, request=request)
        return Response(CaseUpdateSerializer(update).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def referrals(self, request, pk=None):
        from referrals.serializers import ReferralListSerializer
        from referrals.services import visible_referrals

        case = self.get_object()
        qs = visible_referrals(request.user).filter(case=case)
        return Response(ReferralListSerializer(qs, many=True, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def appointments(self, request, pk=None):
        from appointments.serializers import AppointmentSerializer

        case = self.get_object()
        return Response(AppointmentSerializer(case.appointments.select_related("institution"), many=True, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def grants(self, request, pk=None):
        case = self.get_object()
        if not access.can_manage_grants(request.user, case):
            raise PermissionDenied("You cannot view portal access for this case.")
        return Response(GrantSerializer(case.access_grants.select_related("user", "created_by", "approved_by"), many=True).data)

    @action(detail=True, methods=["get"], url_path="assistance-requests")
    def assistance_requests(self, request, pk=None):
        from support_services.serializers import AssistanceRequestStaffSerializer

        case = self.get_object()
        if not access.can_review_beneficiary_content(request.user, case):
            raise PermissionDenied("Only the responsible officers can see assistance requests.")
        return Response(AssistanceRequestStaffSerializer(case.assistance_requests.all(), many=True).data)

    @action(detail=False, methods=["get"])
    def stages(self, request):
        return Response(CaseStageSerializer(CaseStage.objects.filter(is_active=True), many=True).data)

    @action(detail=False, methods=["get"], url_path="officers")
    def officers(self, request):
        """Officers in the caller's own institution (for assignment pickers)."""
        users = User.objects.filter(memberships__institution=request.user.institution, memberships__is_active=True, is_active=True)
        return Response([{"id": str(u.id), "full_name": u.display_name(), "role": u.role} for u in users])


class CaseUpdateViewSet(viewsets.GenericViewSet):
    permission_classes = [IsInstitutionalUser]

    def get_queryset(self):
        return CaseUpdate.objects.filter(case__in=access.team_cases(self.request.user))

    @action(detail=False, methods=["get"], url_path="pending-review")
    def pending_review(self, request):
        cases = [c for c in access.team_cases(request.user) if access.can_review_beneficiary_content(request.user, c)]
        qs = (CaseUpdate.objects.filter(case__in=cases, beneficiary_status="PENDING")
              .exclude(author=request.user).select_related("case", "institution", "author"))
        data = CaseUpdateSerializer(qs, many=True).data
        for row, obj in zip(data, qs):
            row["case_id"] = str(obj.case_id)
            row["case_reference"] = obj.case.reference
        return Response(data)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        update = self.get_object()
        ser = ReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        update = services.review_update(
            request.user, update, ser.validated_data["approve"], ser.validated_data.get("beneficiary_message"), request=request
        )
        return Response(CaseUpdateSerializer(update).data)


class FollowUpViewSet(viewsets.ModelViewSet):
    permission_classes = [IsInstitutionalUser]
    serializer_class = FollowUpSerializer
    filterset_fields = ["status", "case"]
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        u = self.request.user
        qs = FollowUp.objects.filter(institution=u.institution).select_related("case", "assigned_to", "created_by")
        if self.request.query_params.get("mine") == "1":
            qs = qs.filter(assigned_to=u)
        return qs

    def perform_create(self, serializer):
        u = self.request.user
        case = serializer.validated_data["case"]
        if not access.is_on_team(u, case):
            raise ValidationError({"case_id": ["Unknown case."]})
        assignee = serializer.validated_data.get("assigned_to") or u
        if assignee.institution != u.institution:
            raise ValidationError({"assigned_to_id": ["Assign follow-ups to officers in your institution."]})
        fu = serializer.save(institution=u.institution, created_by=u, assigned_to=assignee)
        if assignee != u:
            notify(assignee, "FOLLOW_UP_DUE", link="/app/follow-ups", dedup_key=f"fu:{fu.id}")
        record(u, "followup.create", fu, request=self.request, case_id=str(case.id))

    def perform_update(self, serializer):
        allowed = {"status", "outcome_note", "due_date", "description"}
        extra = set(serializer.validated_data) - allowed
        if extra:
            raise ValidationError({"detail": [f"Cannot change: {', '.join(sorted(extra))}"]})
        status_value = serializer.validated_data.get("status")
        kwargs = {}
        if status_value == FollowUpStatus.DONE:
            kwargs["completed_at"] = timezone.now()
        fu = serializer.save(**kwargs)
        record(self.request.user, "followup.update", fu, request=self.request, status=fu.status)


class GrantViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsInstitutionalUser]
    serializer_class = GrantSerializer

    def get_queryset(self):
        cases = access.team_cases(self.request.user)
        return BeneficiaryAccessGrant.objects.filter(case__in=cases).select_related("user", "case", "created_by", "approved_by")

    def create(self, request, *args, **kwargs):
        ser = GrantCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        case = get_object_or_404(access.team_cases(request.user), pk=ser.validated_data["case_id"])
        grant_user = User.objects.filter(username=ser.validated_data["username"], is_active=True).first()
        if grant_user is None:
            raise ValidationError({"username": ["No eligible account with this username."]})
        grant = services.create_grant(request.user, case, grant_user, ser.validated_data, request=request)
        return Response(GrantSerializer(grant).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        grant = services.approve_grant(request.user, self.get_object(), request=request)
        return Response(GrantSerializer(grant).data)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        reason = (request.data.get("reason") or "").strip()
        if not reason:
            raise ValidationError({"reason": ["Give a reason for revoking access."]})
        grant = services.revoke_grant(request.user, self.get_object(), reason, request=request)
        return Response(GrantSerializer(grant).data)
