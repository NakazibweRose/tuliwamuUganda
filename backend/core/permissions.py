from rest_framework.permissions import BasePermission

from accounts.roles import BENEFICIARY_ROLES, INSTITUTIONAL_ROLES, Role


class IsInstitutionalUser(BasePermission):
    """Staff of an active institution. Administrators are NOT institutional users for case content."""

    message = "This action is only available to authorised institutional staff."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role in INSTITUTIONAL_ROLES and u.institution is not None)


class IsBeneficiaryUser(BasePermission):
    message = "This area is only available to beneficiary and caregiver accounts."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role in BENEFICIARY_ROLES)


class IsPlatformAdmin(BasePermission):
    message = "Administrator access required."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role == Role.ADMIN)


class CanViewAnalytics(BasePermission):
    message = "Analytics are available to administrators and institutional supervisors."

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        return u.role == Role.ADMIN or (u.role in INSTITUTIONAL_ROLES and u.is_supervisor)


class HasRole(BasePermission):
    """Use as HasRole.of({Role.POLICE, ...})."""

    roles = set()

    @classmethod
    def of(cls, roles):
        return type("HasRoleOf", (cls,), {"roles": set(roles)})

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role in self.roles)
