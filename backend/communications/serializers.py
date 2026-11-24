from rest_framework import serializers

from .models import AnonymousReport, AnonymousReportEvent, SmsMessage


class AnonymousReportListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnonymousReport
        fields = ["id", "reference_code", "channel", "category", "immediate_danger", "general_location", "preferred_language",
                  "verification_status", "review_status", "created_at", "reviewed_at"]


class EventSerializer(serializers.ModelSerializer):
    actor = serializers.CharField(source="actor.display_name", read_only=True)

    class Meta:
        model = AnonymousReportEvent
        fields = ["id", "created_at", "actor", "action", "note"]


class AnonymousReportDetailSerializer(AnonymousReportListSerializer):
    events = EventSerializer(many=True, read_only=True)
    has_safe_contact = serializers.SerializerMethodField()
    assigned_institution = serializers.SerializerMethodField()
    converted_case_id = serializers.UUIDField(source="converted_case.id", default=None, read_only=True)
    converted_case_reference = serializers.CharField(source="converted_case.reference", default=None, read_only=True)

    class Meta(AnonymousReportListSerializer.Meta):
        fields = AnonymousReportListSerializer.Meta.fields + [
            "description", "has_safe_contact", "assigned_institution", "converted_case_id", "converted_case_reference", "events"
        ]

    def get_has_safe_contact(self, obj):
        return bool(obj.optional_safe_contact)

    def get_assigned_institution(self, obj):
        return {"id": str(obj.assigned_institution.id), "name": obj.assigned_institution.name} if obj.assigned_institution else None


class SmsMessageSerializer(serializers.ModelSerializer):
    recipient_role = serializers.CharField(source="recipient.role", default=None)

    class Meta:
        model = SmsMessage
        fields = ["id", "recipient_role", "phone_masked", "message_template", "language", "notification_type", "provider",
                  "delivery_status", "failure_reason", "attempts", "created_at", "submitted_at", "delivered_at", "send_after"]
