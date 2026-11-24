from rest_framework import serializers

from cases.models import ChildCase
from cases.serializers import InstitutionRefSerializer

from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    case_id = serializers.PrimaryKeyRelatedField(queryset=ChildCase.objects.all(), source="case")
    case_reference = serializers.CharField(source="case.reference", read_only=True)
    institution = InstitutionRefSerializer(read_only=True)
    internal_note = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = ["id", "case_id", "case_reference", "institution", "type", "scheduled_for", "previous_scheduled_for",
                  "public_location", "internal_note", "beneficiary_note", "visible_to_beneficiary", "attendees", "status",
                  "reminder_sent_at", "created_at"]
        read_only_fields = ["id", "previous_scheduled_for", "reminder_sent_at", "created_at"]

    def get_internal_note(self, obj):
        inst = self.context["request"].user.institution
        return obj.internal_note if inst and obj.institution_id == inst.id else None


class AppointmentWriteSerializer(serializers.ModelSerializer):
    case_id = serializers.PrimaryKeyRelatedField(queryset=ChildCase.objects.all(), source="case")

    class Meta:
        model = Appointment
        fields = ["case_id", "type", "scheduled_for", "public_location", "internal_note", "beneficiary_note",
                  "visible_to_beneficiary", "attendees", "status"]

    def validate_scheduled_for(self, value):
        from django.utils import timezone

        if self.instance is None and value < timezone.now():
            raise serializers.ValidationError("New appointments must be in the future.")
        return value
