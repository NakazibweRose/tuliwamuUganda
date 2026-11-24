from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from audit.services import record

from .models import Notification
from .serializers import NotificationSerializer, PreferenceSerializer
from .services import get_preference


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    filterset_fields = ["is_read", "type"]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=["patch", "post"])
    def read(self, request, pk=None):
        n = self.get_object()
        if not n.is_read:
            n.is_read, n.read_at = True, timezone.now()
            n.save(update_fields=["is_read", "read_at", "updated_at"])
        return Response(NotificationSerializer(n).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        count = self.get_queryset().filter(is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({"updated": count})

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return Response({"unread": self.get_queryset().filter(is_read=False).count()})

    @action(detail=False, methods=["get", "patch"])
    def preferences(self, request):
        pref = get_preference(request.user)
        if request.method == "PATCH":
            ser = PreferenceSerializer(pref, data=request.data, partial=True)
            ser.is_valid(raise_exception=True)
            consent_given = ser.validated_data.get("sms_consent") and not pref.sms_consent
            pref = ser.save()
            if consent_given:
                pref.consent_reference = f"self-service:{timezone.now():%Y%m%d%H%M}"
                pref.consent_recorded_by = request.user
                pref.consent_recorded_at = timezone.now()
                pref.save()
            if ser.validated_data.get("sms_consent") is False:
                pref.consent_reference = ""
                pref.save(update_fields=["consent_reference"])
            record(request.user, "notifications.preferences", pref, request=request, channel=pref.preferred_channel, sms_consent=pref.sms_consent)
        return Response(PreferenceSerializer(pref).data)
