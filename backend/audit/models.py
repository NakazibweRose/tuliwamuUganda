from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class AuditLog(TimeStampedModel):
    """Who did what to which object. Never stores sensitive field values."""

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    actor_role = models.CharField(max_length=20, blank=True)
    institution = models.ForeignKey("institutions.Institution", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    action = models.CharField(max_length=60, db_index=True)
    object_type = models.CharField(max_length=40, blank=True)
    object_id = models.CharField(max_length=64, blank=True, db_index=True)
    success = models.BooleanField(default=True)
    is_security_event = models.BooleanField(default=False, db_index=True)
    ip_hash = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
