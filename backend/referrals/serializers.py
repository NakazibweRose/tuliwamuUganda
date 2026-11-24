from rest_framework import serializers

from accounts.serializers import UserSummarySerializer
from cases import access
from cases.models import ChildCase
from cases.serializers import InstitutionRefSerializer
from institutions.models import Institution

from .models import SHAREABLE_FIELDS, Priority, Referral, ReferralCategory, ReferralStatusHistory


class ReferralListSerializer(serializers.ModelSerializer):
    sending_institution = InstitutionRefSerializer(read_only=True)
    receiving_institution = InstitutionRefSerializer(read_only=True)
    case_reference = serializers.CharField(source="case.reference", read_only=True)
    case_id = serializers.UUIDField(source="case.id", read_only=True)
    direction = serializers.SerializerMethodField()

    class Meta:
        model = Referral
        fields = ["id", "reference", "case_id", "case_reference", "category", "priority", "status", "direction",
                  "sending_institution", "receiving_institution", "sent_at", "acknowledged_at", "completed_at", "created_at"]

    def get_direction(self, obj):
        inst = self.context["request"].user.institution
        return "outgoing" if inst and obj.sending_institution_id == inst.id else "incoming"


class HistorySerializer(serializers.ModelSerializer):
    actor = UserSummarySerializer(read_only=True)
    institution = InstitutionRefSerializer(read_only=True)

    class Meta:
        model = ReferralStatusHistory
        fields = ["id", "created_at", "from_status", "to_status", "actor", "institution", "note"]


class ReferralDetailSerializer(ReferralListSerializer):
    sent_by = UserSummarySerializer(read_only=True)
    assigned_officer = UserSummarySerializer(read_only=True)
    history = HistorySerializer(many=True, read_only=True)
    restricted_notes = serializers.SerializerMethodField()
    case_on_team = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()

    class Meta(ReferralListSerializer.Meta):
        fields = ReferralListSerializer.Meta.fields + [
            "purpose", "shared_fields", "shared_data", "outcome_summary", "restricted_notes", "visible_to_beneficiary",
            "sent_by", "assigned_officer", "history", "case_on_team", "actions",
        ]

    def get_restricted_notes(self, obj):
        inst = self.context["request"].user.institution
        return obj.restricted_notes if inst and obj.receiving_institution_id == inst.id else None

    def get_case_on_team(self, obj):
        return access.is_on_team(self.context["request"].user, obj.case)

    def get_actions(self, obj):
        from .services import TRANSITIONS

        inst = self.context["request"].user.institution
        side = "sender" if inst and obj.sending_institution_id == inst.id else (
            "receiver" if inst and obj.receiving_institution_id == inst.id else None)
        return [a for a, (frm, _to, s) in TRANSITIONS.items() if s == side and obj.status in frm]


class ReferralCreateSerializer(serializers.Serializer):
    case_id = serializers.UUIDField()
    receiving_institution_id = serializers.PrimaryKeyRelatedField(queryset=Institution.objects.filter(is_active=True), source="receiving_institution")
    category = serializers.ChoiceField(choices=ReferralCategory.choices)
    priority = serializers.ChoiceField(choices=Priority.choices, default=Priority.ROUTINE)
    purpose = serializers.CharField(max_length=500)
    shared_fields = serializers.ListField(child=serializers.ChoiceField(choices=list(SHAREABLE_FIELDS.keys())), required=False, default=list)
    visible_to_beneficiary = serializers.BooleanField(default=False)
    send_now = serializers.BooleanField(default=True)


class TransitionSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    outcome_summary = serializers.CharField(max_length=500, required=False, allow_blank=True)
    restricted_notes = serializers.CharField(max_length=4000, required=False, allow_blank=True)
