import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from .roles import BENEFICIARY_ROLES, INSTITUTIONAL_ROLES, Language, Role


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True, help_text="Work phone for staff accounts.")
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    preferred_language = models.CharField(max_length=5, choices=Language.choices, default=Language.EN)
    failed_login_count = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    REQUIRED_FIELDS = ["email", "role"]

    @property
    def is_institutional(self):
        return self.role in INSTITUTIONAL_ROLES

    @property
    def is_beneficiary_user(self):
        return self.role in BENEFICIARY_ROLES

    @property
    def is_platform_admin(self):
        return self.role == Role.ADMIN

    @property
    def active_membership(self):
        cached = getattr(self, "_active_membership", "unset")
        if cached == "unset":
            cached = (
                self.memberships.select_related("institution")
                .filter(is_active=True, institution__is_active=True)
                .first()
            )
            self._active_membership = cached
        return cached

    @property
    def institution(self):
        m = self.active_membership
        return m.institution if m else None

    @property
    def is_supervisor(self):
        m = self.active_membership
        return bool(m and m.is_supervisor)

    def display_name(self):
        return self.full_name or self.username

    def __str__(self):
        return f"{self.username} ({self.role})"
