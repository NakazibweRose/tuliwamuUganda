import re
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from translations.catalog import t

from ..models import SmsMessage, SmsStatus
from .providers import get_provider

UG_PHONE_RE = re.compile(r"^(?:\+256|256|0)(7\d{8})$")


def normalise_ug_phone(raw):
    digits = re.sub(r"[\s-]", "", raw or "")
    m = UG_PHONE_RE.match(digits)
    return f"+256{m.group(1)}" if m else None


def mask_phone(phone):
    if not phone:
        return ""
    return phone[:5] + "•" * max(0, len(phone) - 7) + phone[-2:]


def _in_quiet_hours(pref, now):
    start, end, hour = pref.quiet_hours_start, pref.quiet_hours_end, now.hour
    if start == end:
        return False
    return (hour >= start or hour < end) if start > end else (start <= hour < end)


def _next_allowed_time(pref, now):
    candidate = now.replace(hour=pref.quiet_hours_end, minute=0, second=0, microsecond=0)
    return candidate if candidate > now else candidate + timedelta(days=1)


def send_discreet_sms(user, notification_type, dedup_key, *, now=None):
    """Queue and send a discreet, template-based SMS to a user who has consented.

    Returns the SmsMessage (existing one if this dedup_key was already used), or None if the
    user has not opted into SMS."""
    pref = getattr(user, "notification_preference", None)
    if pref is None or pref.preferred_channel != "SMS":
        return None

    existing = SmsMessage.objects.filter(dedup_key=dedup_key).first()
    if existing:
        return existing

    language = pref.preferred_language or user.preferred_language
    phone = normalise_ug_phone(pref.safe_phone)
    body = t(f"notif.{notification_type}.body", language)
    sms = SmsMessage(
        recipient=user,
        phone_encrypted=phone or "",
        phone_masked=mask_phone(phone),
        message_template=f"notif.{notification_type}.body",
        language=language,
        notification_type=notification_type,
        body=body[:320],
        provider=get_provider().name,
        dedup_key=dedup_key,
    )
    if not (pref.sms_consent and pref.consent_reference and phone):
        sms.delivery_status = SmsStatus.BLOCKED
        sms.failure_reason = "no_consent_or_safe_number"
    now = timezone.localtime(now or timezone.now())
    if sms.delivery_status != SmsStatus.BLOCKED and _in_quiet_hours(pref, now):
        sms.delivery_status = SmsStatus.DEFERRED
        sms.send_after = _next_allowed_time(pref, now)
    try:
        with transaction.atomic():
            sms.save()
    except IntegrityError:  # concurrent duplicate
        return SmsMessage.objects.get(dedup_key=dedup_key)
    if sms.delivery_status == SmsStatus.QUEUED:
        dispatch(sms)
    return sms


def dispatch(sms):
    provider = get_provider()
    sms.attempts += 1
    sms.provider = provider.name
    result = provider.send(sms.phone_encrypted, sms.body)
    sms.delivery_status = result.status
    sms.provider_message_id = result.message_id or sms.provider_message_id
    sms.failure_reason = result.error
    if result.accepted:
        sms.submitted_at = timezone.now()
    sms.save(update_fields=["attempts", "provider", "delivery_status", "provider_message_id", "failure_reason", "submitted_at", "updated_at"])
    return sms


def process_queue(now=None):
    """Send deferred messages whose quiet hours have ended and retry failures (bounded)."""
    now = now or timezone.now()
    sent = 0
    for sms in SmsMessage.objects.filter(delivery_status=SmsStatus.DEFERRED, send_after__lte=now):
        dispatch(sms)
        sent += 1
    for sms in SmsMessage.objects.filter(delivery_status=SmsStatus.FAILED, attempts__lt=settings.SMS_MAX_ATTEMPTS):
        dispatch(sms)
        sent += 1
    return sent
