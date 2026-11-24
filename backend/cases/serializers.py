from rest_framework import serializers

from accounts.models import User
from accounts.roles import Language
from accounts.serializers import UserSummarySerializer
from institutions.models import Region

from . import access
from .models import (
    AgeRange,
    BeneficiaryAccessGrant,
    CaseStage,
    CaseStatusHistory,
    CaseUpdate,
    Child,
    ChildCase,
    FollowUp,
    IncidentCategory,
    JourneyStep,
    Relationship,
    UpdateCategory,
    Visibility,
)

REFERRAL_NEED_CHOICES = ["MEDICAL", "FORENSIC", "PROSECUTION", "PROBATION", "LEGAL_AID", "PSYCHOSOCIAL", "SHELTER"]


class InstitutionRefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    type = serializers.CharField()


class CaseStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseStage
        fields = ["code", "label", "beneficiary_label", "journey_step", "order", "allowed_roles", "is_terminal"]


class CaseListSerializer(serializers.ModelSerializer):
    stage = CaseStageSerializer(read_only=True)
    lead_institution = InstitutionRefSerializer(read_only=True)
    assigned_officer = UserSummarySerializer(read_only=True)
    child_pseudonym = serializers.CharField(source="child.pseudonym", read_only=True)
    age_range = serializers.CharField(source="child.age_range", read_only=True)
    is_lead = serializers.SerializerMethodField()

    class Meta:
        model = ChildCase
        fields = ["id", "reference", "child_pseudonym", "age_range", "incident_category", "district", "stage",
                  "lead_institution", "assigned_officer", "immediate_risk", "date_reported", "created_at", "updated_at", "is_lead"]

    def get_is_lead(self, obj):
        return obj.lead_institution_id == getattr(self.context["request"].user.institution, "id", None)


class CaseDetailSerializer(CaseListSerializer):
    team = serializers.SerializerMethodField()
    child_id = serializers.UUIDField(source="child.id", read_only=True)
    preferred_language = serializers.CharField(source="child.preferred_language", read_only=True)
    sensitive = serializers.SerializerMethodField()
    can = serializers.SerializerMethodField()

    class Meta(CaseListSerializer.Meta):
        fields = CaseListSerializer.Meta.fields + [
            "child_id", "preferred_language", "external_reference", "region", "referral_needs", "closed_at",
            "team", "sensitive", "can",
        ]

    def get_team(self, obj):
        return [
            {"institution": {"id": str(a.institution.id), "name": a.institution.name, "type": a.institution.type},
             "role_in_case": a.role_in_case, "is_lead": a.is_lead,
             "officer": a.officer.display_name() if a.officer else None}
            for a in obj.assignments.filter(is_active=True).select_related("institution", "officer")
        ]

    def get_sensitive(self, obj):
        user = self.context["request"].user
        if not access.can_view_sensitive(user, obj):
            return None  # restricted fields are omitted entirely, not blanked
        return {"protection_concerns": obj.protection_concerns, "location_detail": obj.location_detail}

    def get_can(self, obj):
        user = self.context["request"].user
        stages = [s.code for s in CaseStage.objects.filter(is_active=True) if access.can_set_stage(user, obj, s)]
        return {
            "edit": access.is_lead(user, obj),
            "set_stages": stages,
            "review_beneficiary_updates": access.can_review_beneficiary_content(user, obj),
            "manage_access": access.can_manage_grants(user, obj),
            "create_referral": user.role in {"POLICE", "MEDICAL", "PROSECUTOR", "PROBATION", "LEGAL_AID"},
            "schedule_hearing": user.role == "COURT",
        }


class CaseCreateSerializer(serializers.Serializer):
    child_id = serializers.PrimaryKeyRelatedField(queryset=Child.objects.all(), source="child", required=False, allow_null=True)
    child_pseudonym = serializers.CharField(max_length=60, required=False)
    age_range = serializers.ChoiceField(choices=AgeRange.choices, required=False)
    preferred_language = serializers.ChoiceField(choices=Language.choices, default="en")
    date_reported = serializers.DateField()
    incident_category = serializers.ChoiceField(choices=IncidentCategory.choices)
    district = serializers.CharField(max_length=80)
    region = serializers.ChoiceField(choices=Region.choices)
    location_detail = serializers.CharField(max_length=300, required=False, allow_blank=True)
    protection_concerns = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    immediate_risk = serializers.BooleanField(default=False)
    referral_needs = serializers.ListField(child=serializers.ChoiceField(choices=REFERRAL_NEED_CHOICES), required=False)
    external_reference = serializers.CharField(max_length=60, required=False, allow_blank=True)
    assigned_officer_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), source="assigned_officer", required=False)
    confirm_not_duplicate = serializers.BooleanField(default=False)

    def validate_date_reported(self, value):
        from django.utils import timezone

        if value > timezone.localdate():
            raise serializers.ValidationError("The report date cannot be in the future.")
        return value

    def validate(self, attrs):
        if attrs.get("child") is None:
            if not attrs.get("child_pseudonym"):
                raise serializers.ValidationError({"child_pseudonym": ["Enter a pseudonym (never the child's real name in demos)."]})
            if not attrs.get("age_range"):
                raise serializers.ValidationError({"age_range": ["Select an age range."]})
        return attrs


class CaseEditSerializer(serializers.ModelSerializer):
    assigned_officer_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), source="assigned_officer", required=False)

    class Meta:
        model = ChildCase
        fields = ["district", "region", "location_detail", "protection_concerns", "immediate_risk", "referral_needs",
                  "external_reference", "assigned_officer_id"]

    def validate_assigned_officer_id(self, officer):
        if officer.institution != self.context["request"].user.institution:
            raise serializers.ValidationError("The assigned officer must belong to your institution.")
        return officer


class StageChangeSerializer(serializers.Serializer):
    stage = serializers.CharField()
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class CaseUpdateSerializer(serializers.ModelSerializer):
    institution = InstitutionRefSerializer(read_only=True)
    author = UserSummarySerializer(read_only=True)
    reviewed_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = CaseUpdate
        fields = ["id", "created_at", "institution", "author", "category", "note", "visibility", "beneficiary_message",
                  "beneficiary_journey_step", "beneficiary_status", "reviewed_by", "reviewed_at", "system_generated"]


class CaseUpdateCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=UpdateCategory.choices, default=UpdateCategory.GENERAL)
    note = serializers.CharField(max_length=2000)
    visibility = serializers.ChoiceField(choices=Visibility.choices, default=Visibility.CASE_TEAM)
    beneficiary_message = serializers.CharField(max_length=400, required=False, allow_blank=True)
    beneficiary_journey_step = serializers.ChoiceField(choices=JourneyStep.choices, required=False, allow_blank=True)


class ReviewSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    beneficiary_message = serializers.CharField(max_length=400, required=False, allow_blank=True)


class StatusHistorySerializer(serializers.ModelSerializer):
    from_stage = serializers.CharField(source="from_stage.label", default=None)
    to_stage = serializers.CharField(source="to_stage.label")
    changed_by = UserSummarySerializer(read_only=True)
    institution = InstitutionRefSerializer(read_only=True)

    class Meta:
        model = CaseStatusHistory
        fields = ["id", "created_at", "from_stage", "to_stage", "changed_by", "institution", "note"]


class FollowUpSerializer(serializers.ModelSerializer):
    case_id = serializers.PrimaryKeyRelatedField(queryset=ChildCase.objects.all(), source="case")
    case_reference = serializers.CharField(source="case.reference", read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True), source="assigned_to", required=False)
    assigned_to = UserSummarySerializer(read_only=True)
    created_by = UserSummarySerializer(read_only=True)
    referral_id = serializers.UUIDField(required=False, allow_null=True)
    assistance_request_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = FollowUp
        fields = ["id", "case_id", "case_reference", "referral_id", "assistance_request_id", "assigned_to_id", "assigned_to",
                  "created_by", "description", "due_date", "status", "outcome_note", "completed_at", "created_at"]
        read_only_fields = ["id", "completed_at", "created_at", "created_by"]


class GrantSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    created_by = UserSummarySerializer(read_only=True)
    approved_by = UserSummarySerializer(read_only=True)
    case_reference = serializers.CharField(source="case.reference", read_only=True)

    class Meta:
        model = BeneficiaryAccessGrant
        fields = ["id", "case", "case_reference", "user", "relationship", "basis", "conflict_check_confirmed", "status",
                  "created_by", "approved_by", "approved_at", "valid_until", "revoked_at", "revoke_reason", "created_at"]

    def get_user(self, obj):
        return {"id": str(obj.user.id), "username": obj.user.username, "full_name": obj.user.full_name, "role": obj.user.role}


class GrantCreateSerializer(serializers.Serializer):
    case_id = serializers.UUIDField()
    username = serializers.CharField(max_length=150)
    relationship = serializers.ChoiceField(choices=Relationship.choices)
    basis = serializers.CharField(max_length=500)
    conflict_check_confirmed = serializers.BooleanField(default=False)
    valid_until = serializers.DateField(required=False, allow_null=True)
