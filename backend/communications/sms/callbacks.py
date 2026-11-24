"""Africa's Talking delivery reports: POST id, status, phoneNumber, networkCode, failureReason, retryCount."""
from django.utils import timezone

from ..models import SmsMessage, SmsStatus

AT_STATUS_MAP = {
    "Success": SmsStatus.DELIVERED,
    "Sent": SmsStatus.SUBMITTED,
    "Buffered": SmsStatus.SUBMITTED,
    "Submitted": SmsStatus.SUBMITTED,
    "Failed": SmsStatus.FAILED,
    "Rejected": SmsStatus.FAILED,
}


def apply_delivery_report(data):
    message_id = (data.get("id") or "").strip()
    status = AT_STATUS_MAP.get((data.get("status") or "").strip())
    if not message_id or status is None:
        return None
    sms = SmsMessage.objects.filter(provider_message_id=message_id).first()
    if sms is None:
        return None
    if sms.delivery_status == SmsStatus.DELIVERED:  # repeated callback: idempotent
        return sms
    sms.delivery_status = status
    if status == SmsStatus.DELIVERED:
        sms.delivered_at = timezone.now()
    if status == SmsStatus.FAILED:
        sms.failure_reason = (data.get("failureReason") or "failed")[:200]
    sms.save(update_fields=["delivery_status", "delivered_at", "failure_reason", "updated_at"])
    return sms
