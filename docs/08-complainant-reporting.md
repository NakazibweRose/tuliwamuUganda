# Complainant reporting (voice + Sunbird AI) — complainant ↔ police

## Flow

```mermaid
sequenceDiagram
  autonumber
  actor C as Complainant
  participant T as Tuliwamu
  participant S as Sunbird AI
  actor P as Police (assigned station)
  C->>T: Get help — who it is about, age, district, voice note and/or text, reply language
  T-->>C: "Thank you — the police will answer within 24 hours in <language>" (+ report number CR-…)
  T->>S: Speech-to-text (lug / ach / eng …) → translate to English → Sunflower triage (only with consent)
  S-->>T: Transcript, English text, category, urgency, summary, key facts
  T->>P: New report to verify (routed by district; 24-hour clock)
  P->>C: Optional question (auto-translated into the complainant's language)
  C->>P: Reply (auto-translated into English)
  P->>T: Verify → register official case (case ID TLW-…) or close with an explanation
  T-->>C: "Your report has been verified" → dashboard shows the case journey, dates to attend, support
```

* **Home page.** A complainant with no reports sees a welcome page with no case details: what the service is, how it works in three steps, language choice, privacy promises and emergency numbers. After reporting, the page becomes a live tracker that refreshes itself. It shows reports being checked (with the 24-hour countdown), questions from police, and the cases they may follow (journey, next date, who needs to attend, latest approved update).
* **Get help** is a three-step wizard: about the child → tell the story (record up to 3 minutes and/or write) → reply language and AI consent. It works on phones. Without in-browser recording, the complainant can pick a recording from the phone's voice recorder.
* **Case ID.** The complainant gets a *report* number (`CR-…`) straight away. An official *case* number (`TLW-…`) exists only after a police officer verifies the report and registers it.

## Sunbird AI (verified against the live API)

| Step | Endpoint | Notes |
|---|---|---|
| Speech-to-text | `POST /tasks/audio/transcriptions` (multipart `audio`, `language`) | The language is required (`lug`, `ach`, `eng`, `nyn`, `teo`, `swa`). Browser WebM/Opus works |
| Translation | `POST /tasks/translate` | Report → English for police; police messages → the complainant's language; complainant replies → English |
| Triage summary | `POST /tasks/chat/completions` (model `sunflower-9b`) | Returns JSON: category, urgency, summary, key facts. If the model is unavailable, a clearly labelled keyword guess is used |

* **Rate limit:** 50 requests per minute per key. The client backs off and retries. One report uses about 3 calls.
* **Timing:** a voice report took about 80 seconds end to end in testing. Processing runs in the background, so the complainant gets the confirmation immediately.
* **Failures are safe:** if Sunbird is unavailable, times out, or the complainant did not consent, the report still goes to police (the AI status says why). Officers can listen to or read it directly, and can press **Run AI analysis** later.
* **Configuration:** set `SUNBIRD_API_KEY` on the server (Render → `tuliwamu` → Environment). Without it, the platform runs with AI switched off.

## Data protection

| Rule | Where enforced |
|---|---|
| The complainant never sees the AI summary, transcript, translation, category, internal police notes or case documents | `complaints/views.py::complainant_view` (test `test_complainant_never_sees_ai_output_or_transcript`) |
| Statement, transcript, translation, summary and messages are encrypted at rest. Audio is stored encrypted in the database, never on disk | `complaints/models.py`, `services.submit_complaint` (test `test_audio_is_encrypted_and_police_only`) |
| Only police officers of the station the report was routed to can open it or play the audio. Every playback is audited as a security event | `ComplaintViewSet.get_queryset`, `audio` action |
| AI processing needs explicit consent; without it nothing is sent to Sunbird | `process_complaint` (test `test_no_consent_means_no_ai`) |
| Someone who reports **another family's child** is told the outcome but can never follow that child's case | `FOLLOW_RELATIONSHIP` (test `test_reporter_of_another_child_cannot_follow_that_case`) |
| A parent or carer can follow the case only if the registering officer confirms they are not implicated and it is in the child's best interests | Register form checkbox → `BeneficiaryAccessGrant` |
| SMS about reports is generic ("You have an update on Tuliwamu") and never mentions a report or the police | `translations/catalog.py` `sms.*` (test `test_sms_for_complaints_is_generic`) |
| The AI never decides: registration, questions and closure are human actions, attributed and audited | `complaints/services.py` |

**Design choice to review with safeguarding advisers:** for the complainant's own grant, the registering
officer's confirmation replaces the usual second-officer approval, so the complainant is not left waiting
after verification. Grants for anyone else still need two officers.

## Translations

Complainant-facing screens and notifications in Luganda and Acholi were machine-translated with Sunbird's
translator. Any string whose placeholders did not survive translation falls back to English. All of these
are marked "needs review by qualified speakers".

## Tests

* `backend/complaints/tests.py` — 16 tests (routing, AI pipeline with a mocked Sunbird client, consent, encryption, isolation, follow rules, race condition, generic SMS).
* `e2e/complainant-flow.mjs` — a real browser with a fake microphone playing a Luganda clip; uses the real Sunbird API when the server has a key.
