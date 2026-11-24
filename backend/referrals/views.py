from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.roles import REFERRAL_CREATOR_ROLES
from audit.services import record
from cases import access
from core.permissions import IsInstitutionalUser
from institutions.models import Institution

from . import services
from .models import CATEGORY_RECEIVER_TYPES, SHAREABLE_FIELDS
from .serializers import ReferralCreateSerializer, ReferralDetailSerializer, ReferralListSerializer, TransitionSerializer


class ReferralViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsInstitutionalUser]
    filterset_fields = ["status", "category", "priority"]
    search_fields = ["reference", "case__reference"]
    ordering_fields = ["created_at", "sent_at", "priority"]

    def get_queryset(self):
        qs = services.visible_referrals(self.request.user).prefetch_related("history__actor", "history__institution")
        direction = self.request.query_params.get("direction")
        inst = self.request.user.institution
        if direction == "incoming":
            qs = qs.filter(receiving_institution=inst)
        elif direction == "outgoing":
            qs = qs.filter(sending_institution=inst)
        return qs

    def get_serializer_class(self):
        return ReferralListSerializer if self.action == "list" else ReferralDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        referral = self.get_object()
        record(request.user, "referral.view", referral, request=request)
        return Response(ReferralDetailSerializer(referral, context={"request": request}).data)

    def create(self, request, *args, **kwargs):
        if request.user.role not in REFERRAL_CREATOR_ROLES:
            raise PermissionDenied("Your role cannot initiate referrals.")
        ser = ReferralCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        case = get_object_or_404(access.team_cases(request.user), pk=ser.validated_data["case_id"])
        referral = services.create_referral(request.user, case, ser.validated_data, request=request)
        return Response(ReferralDetailSerializer(referral, context={"request": request}).data, status=status.HTTP_201_CREATED)

    def _transition(self, request, action_name):
        referral = self.get_object()
        ser = TransitionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        referral = services.transition(
            request.user, referral, action_name,
            note=ser.validated_data.get("note", ""),
            outcome_summary=ser.validated_data.get("outcome_summary"),
            restricted_notes=ser.validated_data.get("restricted_notes"),
            request=request,
        )
        return Response(ReferralDetailSerializer(referral, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        return self._transition(request, "send")

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        return self._transition(request, "acknowledge")

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        return self._transition(request, "start")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._transition(request, "complete")

    @action(detail=True, methods=["post"], url_path="return")
    def return_(self, request, pk=None):
        return self._transition(request, "return")

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        return self._transition(request, "decline")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._transition(request, "cancel")

    @action(detail=True, methods=["post"])
    def resend(self, request, pk=None):
        return self._transition(request, "resend")

    @action(detail=False, methods=["get"], url_path="options")
    def form_options(self, request):
        """Receiving institutions per category and the shareable fields, for the referral form."""
        receivers = {}
        for cat, types in CATEGORY_RECEIVER_TYPES.items():
            receivers[cat] = [
                {"id": str(i.id), "name": i.name, "district": i.district}
                for i in Institution.objects.filter(type__in=types, is_active=True).exclude(pk=request.user.institution.pk)
            ]
        return Response({"receivers": receivers, "shareable_fields": SHAREABLE_FIELDS})
