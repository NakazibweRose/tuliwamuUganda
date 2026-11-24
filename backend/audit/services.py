import hashlib
import logging

from django.conf import settings

from .models import AuditLog

logger = logging.getLogger("tuliwamu.audit")


def _client_ip(request):
    if request is None:
        return ""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "")


def hash_ip(ip):
    if not ip:
        return ""
    return hashlib.sha256((settings.SECRET_KEY + ":ip:" + ip).encode()).hexdigest()[:32]


def record(actor, action, obj=None, *, request=None, success=True, security=False, object_type=None, object_id=None, **metadata):
    """Write an audit entry. `metadata` must contain identifiers/codes only — never sensitive values."""
    user = actor if getattr(actor, "is_authenticated", False) else None
    entry = AuditLog.objects.create(
        actor=user,
        actor_role=getattr(user, "role", "") if user else "",
        institution=getattr(user, "institution", None) if user else None,
        action=action,
        object_type=object_type or (obj.__class__.__name__ if obj is not None else ""),
        object_id=str(object_id or getattr(obj, "pk", "") or ""),
        success=success,
        is_security_event=security,
        ip_hash=hash_ip(_client_ip(request)),
        metadata=metadata,
    )
    if security:
        logger.warning("security_event action=%s object_type=%s success=%s", action, entry.object_type, success)
    return entry
