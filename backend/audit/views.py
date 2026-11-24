from rest_framework import mixins, serializers, viewsets

from core.permissions import IsPlatformAdmin

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()
    institution = serializers.CharField(source="institution.name", default=None)

    class Meta:
        model = AuditLog
        fields = ["id", "created_at", "actor", "actor_role", "institution", "action", "object_type", "object_id",
                  "success", "is_security_event", "metadata"]

    def get_actor(self, obj):
        return obj.actor.username if obj.actor else None


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsPlatformAdmin]
    serializer_class = AuditLogSerializer
    filterset_fields = ["action", "success", "is_security_event", "object_type", "actor_role"]
    search_fields = ["action", "object_id", "actor__username"]

    def get_queryset(self):
        return AuditLog.objects.select_related("actor", "institution")
