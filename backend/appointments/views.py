from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from cases import access
from core.permissions import IsInstitutionalUser

from . import services
from .models import Appointment
from .serializers import AppointmentSerializer, AppointmentWriteSerializer


class AppointmentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsInstitutionalUser]
    serializer_class = AppointmentSerializer
    filterset_fields = ["status", "type", "case"]
    ordering_fields = ["scheduled_for"]

    def get_queryset(self):
        qs = Appointment.objects.filter(case__in=access.team_cases(self.request.user)).select_related("case", "institution")
        if self.request.query_params.get("upcoming") == "1":
            qs = qs.filter(scheduled_for__gte=timezone.now()).filter(~Q(status__in=["CANCELLED", "COMPLETED"]))
        return qs

    def create(self, request):
        ser = AppointmentWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        # Validate the case against the caller's team (404 instead of revealing it exists).
        case = ser.validated_data["case"]
        if not access.team_cases(request.user).filter(pk=case.pk).exists():
            return Response({"error": {"code": "not_found", "message": "Not found.", "details": None}}, status=404)
        appt = services.create_appointment(request.user, ser.validated_data, request=request)
        return Response(AppointmentSerializer(appt, context={"request": request}).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        appt = self.get_object()
        ser = AppointmentWriteSerializer(appt, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        appt = services.update_appointment(request.user, appt, dict(ser.validated_data), request=request)
        return Response(AppointmentSerializer(appt, context={"request": request}).data)

    @action(detail=False, methods=["post"], url_path="send-reminders")
    def send_reminders(self, request):
        """Manual trigger for the demo; in production run `manage.py send_reminders` on a schedule."""
        if not request.user.is_supervisor:
            return Response({"error": {"code": "forbidden", "message": "Supervisors only.", "details": None}}, status=403)
        return Response({"reminders_sent": services.send_due_reminders()})
