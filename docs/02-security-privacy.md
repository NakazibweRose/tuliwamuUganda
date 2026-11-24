# Security, privacy & safeguarding

This is a child-protection application, so these controls are core requirements. Each control below
points to where it is enforced in code and which test checks it.

> The design takes into account Uganda's **Children Act** (as amended, including the Children (Amendment)
> Act, 2016) and the **Data Protection and Privacy Act, 2019**, including section 8 on personal data
> relating to children, and the Data Protection and Privacy Regulations, 2021. **No legal review has been
> done.** Before any real deployment, obtain advice from a qualified Ugandan lawyer, register with the
> Personal Data Protection Office, and complete a data protection impact assessment.

## 1. Access control

| Control | Implementation | Tests |
|---|---|---|
| Least privilege by role | `accounts/roles.py`, `core/permissions.py` | `accounts/tests.py::AdminBoundaryTests` |
| Institution isolation | `cases/access.py::team_cases` filters every case queryset by active `CaseAssignment` for the caller's institution | `cases/tests.py::IsolationTests` |
| Object-level checks / ID tampering | Out-of-scope objects are not in the queryset, so a changed UUID returns **404** (existence is not revealed) | `test_other_institution_cannot_access_case_by_changing_id` |
| Sensitive case fields | `protection_concerns` and `location_detail` are returned only to the lead institution (`sensitive: null` for everyone else) | `test_referral_recipient_sees_only_snapshot_until_acknowledged` |
| Purpose-specific sharing | Referral stores a snapshot of only the selected fields. Only the lead institution can share sensitive fields | `test_non_lead_cannot_share_sensitive_fields` |
| Clinical / forensic confidentiality | `Referral.restricted_notes` is visible to the receiving institution only | `test_restricted_notes_only_visible_to_receiving_institution` |
| Administrators ≠ case readers | Admin role has no institution membership and is refused by `IsInstitutionalUser` | `test_admin_cannot_read_case_content` |
| Stage authority | `CaseStage.allowed_roles`; e.g. only prosecutors record a prosecution decision, only court staff schedule hearings | `ProsecutionAndForensicTests`, `test_only_court_schedules_hearings` |
| No automated decisions | No scoring, prediction, guilt or prosecution logic exists. Every status change is a human action, attributed and audited | — |

## 2. Beneficiary & caregiver safeguards

* **No automatic family access.** A `BeneficiaryAccessGrant` is per case and per person. It needs a written best-interests basis, explicit confirmation that the person is not implicated, and **approval by a second officer**. It can expire and be revoked. Access to one case never extends to another case of the same child.
* **Direct access for a child** is only allowed for age bands 12–14 and 15–17. For younger children, access goes through a caregiver or a social-worker proxy.
* **Four-eyes review** of every family-facing message. Institutional notes and stage changes are never shown automatically. Even system-generated messages (e.g. "medical appointment completed") wait for approval.
* The portal API (`cases/beneficiary_views.py`) returns only approved messages, appointments flagged as visible, service *types*, and the support officer's institutional contact. Tests check that protection concerns, location, clinical notes, outcome summaries, the incident category and the pseudonym never appear.
* **Shared-device protections:** Quick exit (replaces the page in history and drops the session), automatic sign-out after 10 minutes of inactivity (20 for staff), 2-hour maximum session for beneficiaries, no case data in browser storage, and `Cache-Control: no-store` on all API responses.

## 3. Authentication & sessions

* PBKDF2 password hashing (Django default), validators require at least 10 characters.
* Short-lived access JWT (10 minutes) held **in memory only**. The refresh token sits in an **httpOnly** cookie scoped to `/api/auth/`, is rotated on every use and blacklisted on logout.
* Generic login error messages. Account lockout after 5 failures (15 minutes). Login rate limit of 30 per minute per IP. Password-reset responses do not reveal whether an account exists. Children and caregivers recover their accounts in person through their officer.

## 4. Data protection

* **Minimisation:** pseudonyms instead of names, age bands instead of dates of birth, districts instead of addresses. Anonymous reports never require identity.
* **Encryption at rest** (Fernet) for protection concerns, location detail, referral restricted notes, anonymous report descriptions and safe contacts, and safe phone numbers (`core/fields.py`). Set `FIELD_ENCRYPTION_KEY` in production and store it apart from database backups. Use managed PostgreSQL with disk encryption as well.
* **Encryption in transit:** HTTPS is enforced in production (HSTS, secure cookies, SSL redirect).
* **Logs:** request bodies are never logged. Audit metadata contains identifiers and codes only. IP addresses are stored as salted hashes. SMS provider errors are logged by exception type only.
* **USSD:** the phone number is never written to the database. It is used only as a salted, day-scoped hash in the cache for rate limiting. Session answers are wiped when the session ends and purged after expiry (`purge_ussd_sessions`). The privacy limitation is explained to the reporter before submission.
* **Analytics:** region and month granularity, k=5 suppression of small cells and of rates with small denominators, and no cross-tabulation of age × location × category.

## 5. Notifications

* Message text comes only from fixed templates (`translations/catalog.py`). Callers cannot inject content. Tests check that bodies contain no reference, category or name.
* SMS is sent only with recorded consent (`consent_reference`) and a confirmed safe number. Quiet hours defer messages. A deduplication key prevents repeats.
* Delivery is never claimed early: `SIMULATED` (mock) → `SUBMITTED` (API accepted) → `DELIVERED` only when Africa's Talking sends a delivery report.

## 6. Abuse resistance

* Anonymous reports are marked **unverified**, are triaged by humans, and become official cases only after an officer records the outcome "needs action".
* Per-line daily report limit, a lockout on the PIN for status checks (per report and per line), throttling on USSD and login, and an optional shared callback token for Africa's Talking webhooks.

## 7. Correction, retention & backups (to be completed before go-live)

| Topic | Prototype | Needed for production |
|---|---|---|
| Correction | Lead officers can edit core details; every edit is audited | A formal correction-request procedure with a response deadline |
| Retention | USSD sessions purged; nothing else is deleted automatically | A retention schedule agreed with institutions (e.g. archive after case closure + N years) and an automated purge job |
| Backups | Rely on the managed database | Encrypted, access-controlled backups with tested restores |
| Breach response | Security events are visible in the audit log | A breach notification procedure that meets the Act and its regulations |
