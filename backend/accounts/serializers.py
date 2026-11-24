from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from institutions.models import Institution, InstitutionMembership

from .models import User
from .roles import INSTITUTIONAL_ROLES, Role


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "full_name", "role"]


class MeSerializer(serializers.ModelSerializer):
    institution = serializers.SerializerMethodField()
    is_supervisor = serializers.BooleanField(read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "full_name", "email", "role", "preferred_language", "institution", "is_supervisor", "permissions"]
        read_only_fields = ["id", "username", "role", "institution", "is_supervisor", "permissions"]

    def get_institution(self, obj):
        inst = obj.institution
        return {"id": str(inst.id), "name": inst.name, "type": inst.type, "district": inst.district} if inst else None

    def get_permissions(self, obj):
        from .roles import ANONYMOUS_REPORT_TRIAGE_ROLES, CASE_REGISTRATION_ROLES, REFERRAL_CREATOR_ROLES

        institutional = obj.role in INSTITUTIONAL_ROLES and obj.institution is not None
        return {
            "register_case": institutional and obj.role in CASE_REGISTRATION_ROLES,
            "create_referral": institutional and obj.role in REFERRAL_CREATOR_ROLES,
            "schedule_hearing": institutional and obj.role == Role.COURT,
            "triage_anonymous_reports": institutional and obj.role in ANONYMOUS_REPORT_TRIAGE_ROLES,
            "view_analytics": obj.role == Role.ADMIN or (institutional and obj.is_supervisor),
            "manage_users": obj.role == Role.ADMIN,
            "view_audit": obj.role == Role.ADMIN,
            "beneficiary_portal": obj.is_beneficiary_user,
        }


class AdminUserSerializer(serializers.ModelSerializer):
    institution_id = serializers.PrimaryKeyRelatedField(
        queryset=Institution.objects.all(), source="institution_ref", required=False, allow_null=True, write_only=True
    )
    institution = serializers.SerializerMethodField()
    title = serializers.CharField(required=False, allow_blank=True, write_only=True)
    is_supervisor = serializers.BooleanField(required=False)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["id", "username", "full_name", "email", "phone", "role", "preferred_language", "is_active",
                  "institution_id", "institution", "title", "is_supervisor", "password", "last_login", "date_joined"]
        read_only_fields = ["id", "last_login", "date_joined"]

    def get_institution(self, obj):
        inst = obj.institution
        return {"id": str(inst.id), "name": inst.name} if inst else None

    def validate(self, attrs):
        role = attrs.get("role", getattr(self.instance, "role", None))
        inst = attrs.get("institution_ref", None)
        if self.instance is None:
            if role in INSTITUTIONAL_ROLES and inst is None:
                raise serializers.ValidationError({"institution_id": ["Institutional roles need an institution."]})
            if not attrs.get("password"):
                raise serializers.ValidationError({"password": ["Set an initial password."]})
        if attrs.get("password"):
            validate_password(attrs["password"])
        return attrs

    def _save_membership(self, user, inst, title, is_supervisor):
        if inst is None:
            return
        user.memberships.exclude(institution=inst).update(is_active=False)
        InstitutionMembership.objects.update_or_create(
            user=user, institution=inst,
            defaults={"is_active": True, "title": title or "", "is_supervisor": bool(is_supervisor)},
        )

    def create(self, validated):
        inst = validated.pop("institution_ref", None)
        title = validated.pop("title", "")
        sup = validated.pop("is_supervisor", False)
        password = validated.pop("password")
        user = User(**validated)
        user.set_password(password)
        user.save()
        self._save_membership(user, inst, title, sup)
        return user

    def update(self, instance, validated):
        inst = validated.pop("institution_ref", None)
        title = validated.pop("title", None)
        sup = validated.pop("is_supervisor", None)
        password = validated.pop("password", None)
        for k, v in validated.items():
            setattr(instance, k, v)
        if password:
            instance.set_password(password)
        instance.save()
        if inst is not None:
            self._save_membership(instance, inst, title, sup)
        elif sup is not None and instance.active_membership:
            m = instance.active_membership
            m.is_supervisor = sup
            m.save(update_fields=["is_supervisor"])
        return instance
