"""Replaceable SMS providers. React never talks to a provider; only Django does."""
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger("tuliwamu.sms")


@dataclass
class ProviderResult:
    accepted: bool
    status: str  # one of SmsStatus values
    message_id: str = ""
    error: str = ""


class SmsProvider:
    name = "base"

    def send(self, phone, message):  # pragma: no cover - interface
        raise NotImplementedError


class MockSmsProvider(SmsProvider):
    """Demo provider. Records the message as SIMULATED; it is never sent to a phone."""

    name = "mock"

    def send(self, phone, message):
        return ProviderResult(accepted=True, status="SIMULATED", message_id=f"mock-{uuid.uuid4().hex[:16]}")


class AfricasTalkingSmsProvider(SmsProvider):
    """Africa's Talking SMS via the official SDK.

    An accepted request is recorded as SUBMITTED. Only the delivery-report callback can mark a
    message DELIVERED (see communications.sms.callbacks)."""

    name = "africastalking"
    _initialised = False

    def _client(self):
        import africastalking

        if not AfricasTalkingSmsProvider._initialised:
            africastalking.initialize(settings.AFRICASTALKING_USERNAME, settings.AFRICASTALKING_API_KEY)
            AfricasTalkingSmsProvider._initialised = True
        return africastalking.SMS

    def send(self, phone, message):
        def _call():
            kwargs = {}
            if settings.AFRICASTALKING_SMS_SENDER_ID:
                kwargs["sender_id"] = settings.AFRICASTALKING_SMS_SENDER_ID
            return self._client().send(message, [phone], **kwargs)

        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                response = pool.submit(_call).result(timeout=settings.SMS_TIMEOUT_SECONDS)
        except FutureTimeout:
            return ProviderResult(False, "FAILED", error="timeout")
        except Exception as exc:  # network/auth errors; never log the phone or body
            logger.warning("sms_provider_error type=%s", exc.__class__.__name__)
            return ProviderResult(False, "FAILED", error=exc.__class__.__name__)

        recipients = (response or {}).get("SMSMessageData", {}).get("Recipients", [])
        if not recipients:
            return ProviderResult(False, "FAILED", error="no_recipient_in_response")
        r = recipients[0]
        if r.get("status") == "Success":
            return ProviderResult(True, "SUBMITTED", message_id=r.get("messageId", ""))
        return ProviderResult(False, "FAILED", message_id=r.get("messageId", ""), error=str(r.get("status", "rejected"))[:200])


def get_provider():
    if settings.SMS_PROVIDER == "africastalking" and settings.AFRICASTALKING_API_KEY:
        return AfricasTalkingSmsProvider()
    return MockSmsProvider()
