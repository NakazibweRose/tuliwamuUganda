import json
import logging
import threading

from cryptography.fernet import InvalidToken
from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from audit.services import record
from cases.models import BeneficiaryAccessGrant, GrantStatus, Relationship
from cases.services import register_case as create_official_case
from core.fields import _fernet
from core.references import unique_reference
from institutions.models import Institution
from notifications.services import notify, notify_institution

from . import ai
from .models import (
    SUNBIRD_LANG,
    AiStatus,
    Complaint,
    ComplaintAudio,
    ComplaintEvent,
    ComplaintMessage,
    ComplaintStatus,
    Concerning,
)

logger = logging.getLogger("tuliwamu.complaints")

ALLOWED_AUDIO = {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "audio/x-wav", "audio/aac", "audio/x-m4a"}
FOLLOW_RELATIONSHIP = {
    Concerning.SELF: Relationship.SELF,
    Concerning.MY_CHILD: Relationship.PARENT,
    Concerning.CHILD_IN_CARE: Relationship.CAREGIVER,
}
OPEN_STATUSES = {ComplaintStatus.PROCESSING, ComplaintStatus.AWAITING_VERIFICATION, ComplaintStatus.NEEDS_INFO}


def route_to_station(district):
    """The police station in the reported district, else the configured default, else any station."""
    police = Institution.objects.filter(type="POLICE", is_active=True)
    station = police.filter(district__iexact=(district or "").strip()).first()
    if station is None and settings.COMPLAINT_DEFAULT_POLICE_STATION:
        station = police.filter(name=settings.COMPLAINT_DEFAULT_POLICE_STATION).first()
    return station or police.order_by("created_at").first()


def event(complaint, action, actor=None, note=""):
    ComplaintEvent.objects.create(complaint=complaint, actor=actor, action=action, note=note[:300])


@transaction.atomic
def submit_complaint(user, data, audio_file=None, request=None):
    statement = (data.get("written_statement") or "").strip()
    if not statement and audio_file is None:
        raise ValidationError({"written_statement": ["Write what happened or record a voice note."]})
    audio_bytes = None
    if audio_file is not None:
        mime = (audio_file.content_type or "").split(";")[0].lower()
        if mime not in ALLOWED_AUDIO:
            raise ValidationError({"audio": ["Unsupported audio format."]})
        if audio_file.size > settings.COMPLAINT_MAX_AUDIO_BYTES:
            raise ValidationError({"audio": ["The voice note is too long. Please keep it under 3 minutes."]})
        audio_bytes = audio_file.read()
    station = route_to_station(data["district"])
    if station is None:
        raise ValidationError({"district": ["No police station is available to receive reports."]})
    complaint = Complaint.objects.create(
        reference=unique_reference(Complaint, "reference", "CR", length=6),
        complainant=user,
        concerning=data["concerning"],
        child_age_range=data.get("child_age_range") or "UNKNOWN",
        district=data["district"].strip(),
        region=data.get("region", ""),
        immediate_danger=data.get("immediate_danger", False),
        language=data["language"],
        reply_language=data.get("reply_language") or data["language"],
        written_statement=statement,
        ai_consent=data.get("ai_consent", False),
        assigned_institution=station,
    )
    if audio_bytes is not None:
        ComplaintAudio.objects.create(
            complaint=complaint, data=_fernet().encrypt(audio_bytes), mime_type=audio_file.content_type[:60],
            size_bytes=len(audio_bytes), duration_seconds=data.get("audio_seconds"),
        )
    event(complaint, "SUBMITTED", user, "Voice note and/or written statement received")
    record(user, "complaint.submit", complaint, request=request, has_audio=audio_bytes is not None, ai_consent=complaint.ai_consent)
    notify(user, "COMPLAINT_RECEIVED", link=f"/me/reports/{complaint.id}", dedup_key=f"complaint-received:{complaint.id}", lang=complaint.reply_language)
    if settings.COMPLAINT_AI_ASYNC:
        transaction.on_commit(lambda: start_processing(complaint.id))
    else:
        process_complaint(complaint.id)
    return complaint


def start_processing(complaint_id):
    if settings.COMPLAINT_AI_ASYNC:
        threading.Thread(target=_process_in_thread, args=(complaint_id,), daemon=True).start()
    else:
        process_complaint(complaint_id)


def _process_in_thread(complaint_id):
    try:
        process_complaint(complaint_id)
    finally:
        close_old_connections()


def decrypt_audio(audio):
    try:
        return _fernet().decrypt(bytes(audio.data))
    except InvalidToken:
        return None


def process_complaint(complaint_id):
    """Transcribe → translate → triage. Any failure still hands the report to police (never silently lost)."""
    complaint = Complaint.objects.select_related("assigned_institution").get(pk=complaint_id)
    if complaint.ai_status in {AiStatus.DONE, AiStatus.SKIPPED} and complaint.status != ComplaintStatus.PROCESSING:
        return complaint
    Complaint.objects.filter(pk=complaint.pk).update(ai_status=AiStatus.PROCESSING)
    lang3 = SUNBIRD_LANG.get(complaint.language, "eng")
    fields = {}
    try:
        if not complaint.ai_consent:
            raise ai.AiUnavailable("no_consent")
        client = ai.SunbirdClient()
        transcript = ""
        audio = getattr(complaint, "audio", None)
        if audio is not None:
            raw = decrypt_audio(audio)
            if raw:
                transcript = client.transcribe(raw, audio.mime_type, lang3)
        original = "\n\n".join(p for p in [complaint.written_statement, transcript] if p)
        english = client.translate(original, lang3, "eng") if lang3 != "eng" else original
        fields.update(transcript=transcript, english_text=english)
        try:
            triage = client.triage(english)
            model = "sunbird/sunflower-9b"
        except ai.AiUnavailable:
            triage = {"category": ai.keyword_category(english), "urgency": "HIGH" if complaint.immediate_danger else "MEDIUM",
                      "summary": "", "key_facts": []}
            model = "keyword-fallback (language model unavailable)"
        if complaint.immediate_danger:
            triage["urgency"] = "HIGH"
        fields.update(ai_category=triage["category"], ai_urgency=triage["urgency"], ai_summary=triage["summary"],
                      ai_key_facts=json.dumps(triage["key_facts"]), ai_model=model, ai_status=AiStatus.DONE, ai_error="")
    except ai.AiUnavailable as exc:
        reason = str(exc)
        fields.update(ai_status=AiStatus.SKIPPED if reason in {"no_consent", "not_configured"} else AiStatus.FAILED, ai_error=reason[:120])
        if complaint.language == "en" and complaint.written_statement:
            fields.update(english_text=complaint.written_statement, ai_category=ai.keyword_category(complaint.written_statement),
                          ai_model="keyword-fallback (no AI)")
        if complaint.immediate_danger:
            fields["ai_urgency"] = "HIGH"
    fields["ai_processed_at"] = timezone.now()
    with transaction.atomic():
        c = Complaint.objects.select_for_update().get(pk=complaint.pk)
        for k, v in fields.items():
            setattr(c, k, v)
        if c.status == ComplaintStatus.PROCESSING:
            c.status = ComplaintStatus.AWAITING_VERIFICATION
        c.save()
        event(c, "AI_" + c.ai_status, None, c.ai_error)
    if complaint.status == ComplaintStatus.PROCESSING:
        notify_institution(c.assigned_institution, "NEW_COMPLAINT", link=f"/app/complaints/{c.id}",
                           dedup_key=f"new-complaint:{c.id}", roles=["POLICE"])
    return c


def retry_stuck(minutes=10):
    cutoff = timezone.now() - timezone.timedelta(minutes=minutes)
    stuck = Complaint.objects.filter(status=ComplaintStatus.PROCESSING, updated_at__lt=cutoff).values_list("id", flat=True)
    for cid in list(stuck):
        start_processing(cid)


# ---------------- Police actions ----------------

def _check_officer(user, complaint):
    if user.role != "POLICE" or user.institution is None or complaint.assigned_institution_id != user.institution.id:
        raise PermissionDenied("Only officers of the assigned police station can act on this report.")


def _first_response(complaint):
    if complaint.first_response_at is None:
        complaint.first_response_at = timezone.now()


def police_message(user, complaint, text, needs_info=False, request=None):
    _check_officer(user, complaint)
    text = (text or "").strip()
    if not text:
        raise ValidationError({"text": ["Write a message."]})
    # Translate before opening a transaction (network call), then write atomically.
    translated, machine = ai.translate_for_reader(text, "en", complaint.reply_language)
    with transaction.atomic():
        return _save_police_message(user, complaint, text, translated, machine, needs_info, request)


def _save_police_message(user, complaint, text, translated, machine, needs_info, request):
    complaint = Complaint.objects.select_for_update().get(pk=complaint.pk)
    msg = ComplaintMessage.objects.create(
        complaint=complaint, author=user, from_police=True, text=text, text_language="en",
        translated_text=translated, translated_language=complaint.reply_language if translated else "", machine_translated=machine,
    )
    _first_response(complaint)
    if needs_info and complaint.status in OPEN_STATUSES:
        complaint.status = ComplaintStatus.NEEDS_INFO
    complaint.save()
    event(complaint, "POLICE_MESSAGE" + (" (needs info)" if needs_info else ""), user)
    notify(complaint.complainant, "COMPLAINT_NEEDS_INFO" if needs_info else "COMPLAINT_MESSAGE",
           link=f"/me/reports/{complaint.id}", dedup_key=f"cmsg:{msg.id}", lang=complaint.reply_language)
    record(user, "complaint.message", complaint, request=request, needs_info=needs_info)
    return msg


def complainant_reply(user, complaint, text, request=None):
    if complaint.complainant_id != user.id:
        raise PermissionDenied()
    text = (text or "").strip()
    if not text:
        raise ValidationError({"text": ["Write a message."]})
    lang = complaint.reply_language
    translated, machine = ai.translate_for_reader(text, lang, "en")
    with transaction.atomic():
        msg = ComplaintMessage.objects.create(
            complaint=complaint, author=user, from_police=False, text=text, text_language=lang,
            translated_text=translated, translated_language="en" if translated else "", machine_translated=machine,
        )
        # Conditional update: never overwrite a decision the police made meanwhile.
        Complaint.objects.filter(pk=complaint.pk, status=ComplaintStatus.NEEDS_INFO).update(
            status=ComplaintStatus.AWAITING_VERIFICATION, updated_at=timezone.now())
    event(complaint, "COMPLAINANT_REPLY", user)
    notify_institution(complaint.assigned_institution, "COMPLAINT_REPLY", link=f"/app/complaints/{complaint.id}",
                       dedup_key=f"creply:{msg.id}", roles=["POLICE"])
    record(user, "complaint.reply", complaint, request=request)
    return msg


@transaction.atomic
def register_case(user, complaint, case_data, allow_follow, note="", request=None):
    """The officer verifies the report and opens an official case. Only a human can do this."""
    _check_officer(user, complaint)
    complaint = Complaint.objects.select_for_update().get(pk=complaint.pk)
    if complaint.status not in OPEN_STATUSES:
        raise ValidationError({"detail": ["This report has already been decided."]})
    case_data = dict(case_data)
    case_data["confirm_not_duplicate"] = True
    case = create_official_case(user, case_data, request=request)
    complaint.case = case
    complaint.status = ComplaintStatus.REGISTERED
    complaint.reviewed_by = user
    complaint.reviewed_at = timezone.now()
    complaint.internal_note = note
    _first_response(complaint)
    can_follow = bool(allow_follow) and complaint.concerning in FOLLOW_RELATIONSHIP
    complaint.complainant_can_follow_case = can_follow
    complaint.save()
    if can_follow:
        BeneficiaryAccessGrant.objects.create(
            case=case, user=complaint.complainant, relationship=FOLLOW_RELATIONSHIP[complaint.concerning],
            basis=f"Complainant who reported this case ({complaint.reference}); verified by the registering officer.",
            conflict_check_confirmed=True, status=GrantStatus.ACTIVE, created_by=user, approved_by=user,
            approved_at=timezone.now(),
        )
    event(complaint, "REGISTERED", user, f"Case {case.reference} opened" + ("; complainant can follow" if can_follow else ""))
    notify(complaint.complainant, "COMPLAINT_REGISTERED", link=f"/me/reports/{complaint.id}",
           dedup_key=f"cregistered:{complaint.id}", lang=complaint.reply_language)
    record(user, "complaint.register_case", complaint, request=request, case_id=str(case.id), complainant_follows=can_follow)
    return complaint


@transaction.atomic
def decline(user, complaint, message, note="", request=None):
    _check_officer(user, complaint)
    complaint = Complaint.objects.select_for_update().get(pk=complaint.pk)
    if complaint.status not in OPEN_STATUSES:
        raise ValidationError({"detail": ["This report has already been decided."]})
    if not (message or "").strip():
        raise ValidationError({"message": ["Explain to the complainant what happens next (e.g. where to get help)."]})
    complaint.status = ComplaintStatus.NOT_REGISTERED
    complaint.reviewed_by = user
    complaint.reviewed_at = timezone.now()
    complaint.internal_note = note
    complaint.save()
    police_message(user, complaint, message, request=request)
    event(complaint, "NOT_REGISTERED", user)
    record(user, "complaint.decline", complaint, request=request)
    return complaint
