import uuid

from django.db import models


class DemoState(models.Model):
    """Tiny key/value store for one-off operational markers (e.g. which demo reset was applied)."""

    key = models.CharField(max_length=60, primary_key=True)
    value = models.CharField(max_length=200)
    updated_at = models.DateTimeField(auto_now=True)


class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
