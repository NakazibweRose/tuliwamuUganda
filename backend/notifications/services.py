import logging

from django.core.mail import send_mail
from django.db import IntegrityError, transaction

from translations.catalog import t

from .models import Notification, NotificationPreference

logger = logging.getLogger("tuliwamu.notifications")


def get_preference(user):
    pref, _ = NotificationPreference.objects.get_or_create(
        user=user, defaults={"preferred_language": user.preferred_language}
    )
    return pref


def notify(user, notification_type, *, link="", dedup_key=""):
    """Create a discreet in-app notification and, if the user opted in, an SMS or email.

    The message text comes only from fixed templates — callers cannot inject case details."""
    if not user or not user.is_active:
        return None
    pref = get_preference(user)
    lang = pref.preferred_language or user.preferred_language
    try:
        with transaction.atomic():
            notification = Notification.objects.create(
                recipient=user,
                type=notification_type,
                title=t(f"notif.{notification_type}.title", lang),
                body=t(f"notif.{notification_type}.body", lang),
                link=link,
                dedup_key=dedup_key,
            )
    except IntegrityError:
        return Notification.objects.filter(recipient=user, dedup_key=dedup_key).first()

    if pref.preferred_channel == "SMS":
        from communications.sms.services import send_discreet_sms

        send_discreet_sms(user, notification_type, dedup_key=f"{notification_type}:{user.pk}:{dedup_key or notification.pk}")
    elif pref.preferred_channel == "EMAIL" and user.email:
        try:
            send_mail(notification.title, notification.body, None, [user.email], fail_silently=False)
        except Exception as exc:
            logger.warning("email_failed type=%s", exc.__class__.__name__)
    return notification


def notify_institution(institution, notification_type, *, link="", dedup_key="", exclude=None, roles=None):
    from accounts.models import User

    users = User.objects.filter(memberships__institution=institution, memberships__is_active=True, is_active=True)
    if roles:
        users = users.filter(role__in=roles)
    if exclude is not None:
        users = users.exclude(pk=exclude.pk)
    return [notify(u, notification_type, link=link, dedup_key=f"{dedup_key}:{u.pk}" if dedup_key else "") for u in users.distinct()]
