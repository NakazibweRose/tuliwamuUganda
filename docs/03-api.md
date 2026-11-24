# API reference

Base path: `/api/`. JSON throughout, except the Africa's Talking callbacks, which use form-encoded
requests and `text/plain` responses.

**Authentication.** Send `Authorization: Bearer <access>`. The refresh token is the httpOnly cookie
`tlw_refresh` (path `/api/auth/`).

**Errors** always use this shape:

```json
{ "error": { "code": "validation_error", "message": "Please check the highlighted fields.", "details": { "field": ["…"] } } }
```

**Lists** are paginated: `?page=`, `?page_size=` (max 100) → `{count, next, previous, results}`. Most lists
support `?search=` and `?ordering=`, plus the filters noted below.

A case or object outside your scope returns **404**. A role that may never perform an action returns **403**.

## Auth

| Method & path | Body | Notes |
|---|---|---|
| `POST auth/login/` | `{username, password}` | → `{access, user}` and sets the refresh cookie. 401 on bad credentials; 403 `locked` after 5 failures |
| `POST auth/refresh/` | — (cookie) | Rotates the cookie → `{access, user}` |
| `POST auth/logout/` | — | Blacklists the refresh token and clears the cookie |
| `GET/PATCH auth/me/` | `{preferred_language, full_name}` | `user.permissions` tells the UI which features to show |
| `POST auth/change-password/` | `{current_password, new_password}` | |
| `POST auth/password-reset/` | `{email}` | Always returns the same message |
| `POST auth/password-reset/confirm/` | `{uid, token, new_password}` | |

## Cases (institutional roles)

| Method & path | Notes |
|---|---|
| `GET cases/` | Filters: `stage`, `incident_category`, `immediate_risk`, `region`. Search: reference, pseudonym, district |
| `POST cases/` | Police / probation only. `{child_pseudonym, age_range, preferred_language, date_reported, incident_category, district, region, location_detail?, protection_concerns?, immediate_risk?, referral_needs?, external_reference?, assigned_officer_id?, child_id?, confirm_not_duplicate?}`. A possible duplicate returns 400 with `details.duplicate_warning` |
| `GET cases/{id}/` | Includes `team`, `sensitive` (lead only, otherwise `null`) and `can` (allowed actions) |
| `PATCH cases/{id}/` | Lead institution only |
| `POST cases/{id}/change-stage/` | `{stage, note?}`. Role must be in `stage.allowed_roles` |
| `GET cases/{id}/timeline/` | Case-team entries plus your institution's internal entries |
| `GET cases/{id}/history/` | Stage history |
| `POST cases/{id}/updates/` | `{category, note, visibility: CASE_TEAM\|INTERNAL, beneficiary_message?, beneficiary_journey_step?}` |
| `GET cases/{id}/referrals/` · `appointments/` · `grants/` · `assistance-requests/` | Scoped sub-lists |
| `GET cases/stages/` · `GET cases/officers/` | Reference data |
| `GET case-updates/pending-review/` | Family messages you may approve (excludes your own) |
| `POST case-updates/{id}/review/` | `{approve, beneficiary_message?}`. The reviewer must be a different officer from the author |

## Referrals

| Method & path | Notes |
|---|---|
| `GET referrals/?direction=incoming\|outgoing` | Filters: `status`, `category`, `priority` |
| `POST referrals/` | `{case_id, receiving_institution_id, category, priority, purpose, shared_fields[], visible_to_beneficiary, send_now=true}` |
| `GET referrals/{id}/` | `shared_data` snapshot, `history`, `actions` you may take, and `restricted_notes` (receiver only) |
| `POST referrals/{id}/send\|resend\|cancel/` | Sender. `note` required for resend/cancel |
| `POST referrals/{id}/acknowledge\|start\|complete\|return\|decline/` | Receiver. `complete` needs `outcome_summary`; `restricted_notes` is optional. `return`/`decline` need `note` |
| `GET referrals/options/` | Eligible receivers per category and the shareable fields |

## Appointments, follow-ups, family access, assistance

| Method & path | Notes |
|---|---|
| `GET/POST appointments/`, `PATCH appointments/{id}/` | `COURT_HEARING` is court role only. Changing `scheduled_for` sets the status to RESCHEDULED and notifies the family |
| `POST appointments/send-reminders/` | Supervisors (demo trigger). Production: `manage.py send_reminders` hourly |
| `GET/POST follow-ups/`, `PATCH follow-ups/{id}/` | `?mine=1`, `status`, `case` |
| `GET/POST access-grants/` | `{case_id, username, relationship, basis, conflict_check_confirmed, valid_until?}` |
| `POST access-grants/{id}/approve/` · `revoke/` | Approval by a different officer; `revoke` needs `{reason}` |
| `GET assistance-requests/`, `POST assistance-requests/{id}/respond/` | `{status: IN_PROGRESS\|RESOLVED\|CLOSED, response_message}` |

## Beneficiary portal (caregiver / child roles)

| Method & path | Returns |
|---|---|
| `GET beneficiary/cases/` | Cases with an active grant: `journey_step`, latest approved message, next appointment, support officer |
| `GET beneficiary/cases/{id}/` · `updates/` · `appointments/` · `services/` | Approved content only |
| `GET/POST beneficiary/assistance-requests/` | `{case_id, request_type, message?, preferred_contact_time?}` (10 per hour) |

## Notifications

`GET notifications/`, `GET notifications/unread-count/`, `POST notifications/{id}/read/` (PATCH also
accepted), `POST notifications/read-all/`, `GET/PATCH notifications/preferences/` (`preferred_channel`,
`sms_consent`, `safe_phone` write-only, quiet hours).

## Analytics (admin or institutional supervisors)

`GET analytics/overview/`, `analytics/referrals/`, `analytics/case-progress/`. Every count is
`{value, suppressed}`. Values from 1 to k−1 come back as `{value: null, suppressed: true}`.

## Communications

| Method & path | Notes |
|---|---|
| `POST communications/ussd/callback/[?token=]` | Africa's Talking form fields `sessionId, serviceCode, phoneNumber, text` → `text/plain` starting with `CON ` or `END ` |
| `POST communications/ussd/events/` | Session-end notification; deletes the session state |
| `POST communications/ussd/simulator/` | Authenticated. `{sessionId: uuid, text}` → `{response, end, text}` — same engine |
| `POST communications/sms/delivery-callback/[?token=]` | Africa's Talking delivery report (`id, status, failureReason`) |
| `GET communications/sms/dashboard/` | Totals by status/type plus recent messages with masked numbers |
| `GET anonymous-reports/` · `GET anonymous-reports/{id}/` | Police / probation roles |
| `POST anonymous-reports/{id}/review/` | `{review_status?, verification_status?, assigned_institution_id?, note}` |
| `POST anonymous-reports/{id}/safe-contact/` | Reveals the optional contact (security-audited) |
| `POST anonymous-reports/{id}/convert-to-case/` | Requires `verification_status=CREDIBLE`. Takes case-creation fields (district and region at minimum) |

## Administration (admin role)

`/admin/users/` (create/edit users, role, institution, supervisor flag), `/institutions/` (write),
`/support-services/` (write), `/audit-logs/` (filters: `action`, `success`, `is_security_event`, `object_type`).
`GET translations/status/` (public) reports how complete and how reviewed each backend catalogue is.
