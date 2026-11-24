from rest_framework import serializers

from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "type", "title", "body", "link", "is_read", "read_at", "created_at"]


class PreferenceSerializer(serializers.ModelSerializer):
    safe_phone_set = serializers.SerializerMethodField()
    safe_phone = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = NotificationPreference
        fields = ["preferred_channel", "preferred_language", "sms_consent", "safe_phone", "safe_phone_set",
                  "quiet_hours_start", "quiet_hours_end", "consent_reference", "consent_recorded_at"]
        read_only_fields = ["consent_reference", "consent_recorded_at"]

    def get_safe_phone_set(self, obj):
        return bool(obj.safe_phone)

    def validate_safe_phone(self, value):
        from communications.sms.services import normalise_ug_phone

        if value and not normalise_ug_phone(value):
            raise serializers.ValidationError("Enter a Ugandan mobile number such as 0772123456.")
        return value

    def validate(self, attrs):
        for f in ("quiet_hours_start", "quiet_hours_end"):
            if f in attrs and not 0 <= attrs[f] <= 23:
                raise serializers.ValidationError({f: ["Use an hour between 0 and 23."]})
        return attrs
