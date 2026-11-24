from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from audit.services import record
from core.permissions import IsPlatformAdmin

from .models import Institution
from .serializers import InstitutionSerializer


class InstitutionViewSet(viewsets.ModelViewSet):
    serializer_class = InstitutionSerializer
    filterset_fields = ["type", "region", "is_active"]
    search_fields = ["name", "district"]
    http_method_names = ["get", "post", "patch"]

    def get_permissions(self):
        return [IsAuthenticated()] if self.action in {"list", "retrieve"} and self.request.user.role != "BENEFICIARY" else [IsPlatformAdmin()]

    def get_queryset(self):
        return Institution.objects.annotate(member_count=Count("memberships", filter=Q(memberships__is_active=True)))

    def perform_create(self, serializer):
        inst = serializer.save()
        record(self.request.user, "admin.institution_create", inst, request=self.request)

    def perform_update(self, serializer):
        inst = serializer.save()
        record(self.request.user, "admin.institution_update", inst, request=self.request)
