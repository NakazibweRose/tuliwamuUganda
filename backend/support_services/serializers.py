from rest_framework import serializers

from accounts.serializers import UserSummarySerializer

from .models import AssistanceRequest, AssistanceType, SupportService


class SupportServiceSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source="institution.name", read_only=True)

    class Meta:
        model = SupportService
        fields = ["id", "institution", "institution_name", "category", "name", "description", "public_contact", "hours",
                  "districts", "languages", "is_free", "is_active"]


class AssistanceRequestBeneficiarySerializer(serializers.ModelSerializer):
    case_id = serializers.UUIDField(source="case.id", read_only=True)
    case_reference = serializers.CharField(source="case.reference", read_only=True)

    class Meta:
        model = AssistanceRequest
        fields = ["id", "case_id", "case_reference", "request_type", "message", "preferred_contact_time", "status",
                  "response_message", "responded_at", "created_at"]


class AssistanceRequestCreateSerializer(serializers.Serializer):
    case_id = serializers.UUIDField()
    request_type = serializers.ChoiceField(choices=AssistanceType.choices)
    message = serializers.CharField(max_length=500, required=False, allow_blank=True)
    preferred_contact_time = serializers.CharField(max_length=100, required=False, allow_blank=True)


class AssistanceRequestStaffSerializer(serializers.ModelSerializer):
    case_id = serializers.UUIDField(source="case.id", read_only=True)
    case_reference = serializers.CharField(source="case.reference", read_only=True)
    requested_by = serializers.SerializerMethodField()
    assigned_to = UserSummarySerializer(read_only=True)

    class Meta:
        model = AssistanceRequest
        fields = ["id", "case_id", "case_reference", "requested_by", "request_type", "message", "preferred_contact_time",
                  "status", "assigned_to", "response_message", "responded_at", "created_at"]

    def get_requested_by(self, obj):
        grant = obj.case.access_grants.filter(user=obj.requested_by).first()
        return {"full_name": obj.requested_by.display_name(), "relationship": grant.relationship if grant else None}
