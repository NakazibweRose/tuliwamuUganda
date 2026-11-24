"""Sunbird AI integration: speech-to-text, translation and Sunflower-based triage summary.

The AI only *prepares* a report for a human. It never decides whether an allegation is true, never
registers a case and never contacts anyone. Police verify everything (see services.register_case).
"""
import json
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger("tuliwamu.ai")

CATEGORIES = ["SEXUAL_ABUSE", "PHYSICAL_VIOLENCE", "NEGLECT", "EXPLOITATION", "TRAFFICKING", "EMOTIONAL_ABUSE", "OTHER"]
URGENCIES = ["HIGH", "MEDIUM", "LOW"]

TRIAGE_PROMPT = (
    "You help Ugandan police triage child-protection reports. Read the report and reply with ONLY a JSON object "
    "with keys: category (one of " + ", ".join(CATEGORIES) + "), urgency (HIGH, MEDIUM or LOW; HIGH if a child "
    "may be in danger now or was recently hurt), summary (3-5 neutral sentences in English, no personal names), "
    "key_facts (list of short strings: what happened, where, when, who is at risk, what help is needed). "
    "Do not judge whether the report is true and do not add facts that are not in the report."
)


class AiUnavailable(Exception):
    pass


class SunbirdClient:
    def __init__(self, timeout=None, retries=3):
        if not settings.SUNBIRD_API_KEY:
            raise AiUnavailable("not_configured")
        self.base = settings.SUNBIRD_API_URL.rstrip("/")
        self.headers = {"Authorization": f"Bearer {settings.SUNBIRD_API_KEY}"}
        self.timeout = timeout or settings.SUNBIRD_TIMEOUT_SECONDS
        self.retries = retries

    def _post(self, path, **kwargs):
        import time

        for attempt in range(self.retries):
            try:
                r = requests.post(self.base + path, headers=self.headers, timeout=self.timeout, **kwargs)
            except requests.RequestException as exc:
                raise AiUnavailable(f"network:{exc.__class__.__name__}")
            if r.status_code != 429 or attempt == self.retries - 1:  # Sunbird rate limit: back off and retry
                break
            time.sleep(15 * (attempt + 1))
        if r.status_code >= 400:
            raise AiUnavailable(f"http_{r.status_code}")
        return r.json()

    def transcribe(self, audio_bytes, mime_type, language3):
        ext = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "m4a", "audio/mpeg": "mp3",
               "audio/wav": "wav", "audio/x-wav": "wav", "audio/aac": "aac"}.get(mime_type.split(";")[0], "webm")
        data = self._post("/tasks/audio/transcriptions",
                          files={"audio": (f"statement.{ext}", audio_bytes, mime_type.split(";")[0])},
                          data={"language": language3})
        return (data.get("audio_transcription") or "").strip()

    def translate(self, text, source3, target3):
        if not text or source3 == target3:
            return text
        data = self._post("/tasks/translate", json={"source_language": source3, "target_language": target3, "text": text})
        out = (data.get("output") or {})
        translated = out.get("translated_text")
        if not translated:
            raise AiUnavailable("translation_empty")
        return translated.strip()

    def triage(self, english_text):
        data = self._post("/tasks/chat/completions", json={
            "model": "sunflower-9b", "temperature": 0.1, "max_tokens": 600,
            "messages": [{"role": "system", "content": TRIAGE_PROMPT}, {"role": "user", "content": english_text[:6000]}],
        })
        content = data["choices"][0]["message"]["content"]
        return parse_triage(content)


def parse_triage(content):
    match = re.search(r"\{.*\}", content or "", re.S)
    if not match:
        raise AiUnavailable("triage_unparseable")
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        raise AiUnavailable("triage_unparseable")
    category = str(obj.get("category", "OTHER")).upper().strip()
    urgency = str(obj.get("urgency", "MEDIUM")).upper().strip()
    facts = obj.get("key_facts") or []
    if not isinstance(facts, list):
        facts = [str(facts)]
    return {
        "category": category if category in CATEGORIES else "OTHER",
        "urgency": urgency if urgency in URGENCIES else "MEDIUM",
        "summary": str(obj.get("summary", "")).strip()[:2000],
        "key_facts": [str(f).strip()[:200] for f in facts][:10],
    }


# Very small keyword fallback, used only when the language model is unavailable. Clearly labelled.
KEYWORDS = {
    "SEXUAL_ABUSE": ["defile", "rape", "sexual", "touched", "sex", "undress"],
    "PHYSICAL_VIOLENCE": ["beat", "hit", "slap", "burn", "injur", "wound", "swollen", "kick", "cane"],
    "NEGLECT": ["neglect", "abandon", "no food", "left alone", "starv", "not taken to school"],
    "EXPLOITATION": ["work", "labour", "labor", "quarry", "paid", "sell"],
    "TRAFFICKING": ["traffick", "taken away", "smuggl", "sold"],
    "EMOTIONAL_ABUSE": ["insult", "threat", "shout", "humiliat"],
}


def keyword_category(english_text):
    text = (english_text or "").lower()
    scores = {cat: sum(text.count(w) for w in words) for cat, words in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "OTHER"


def translate_for_reader(text, source_ui, target_ui):
    """Best-effort translation of a short message between UI languages. Returns (text, machine_translated)."""
    from .models import SUNBIRD_LANG

    if not text or source_ui == target_ui:
        return text, False
    try:
        # Short timeout: a chat message must not hang if the translator is slow; the original is always kept.
        out = SunbirdClient(timeout=25, retries=1).translate(text, SUNBIRD_LANG.get(source_ui, "eng"), SUNBIRD_LANG.get(target_ui, "eng"))
        return out, True
    except AiUnavailable as exc:
        logger.info("translation_unavailable reason=%s", exc)
        return "", False
