# Demo script (≈8 minutes) and pitch

Before the demo, reset the data: `python manage.py seed_demo --reset` (clean start: accounts only, no cases). On the live site, change `DEMO_RESET_ID` on Render. All accounts use `Tuliwamu#Demo2026`
and can be picked from the **Demonstration accounts** panel on the login page. Use two browser windows
(or one normal and one private window) so you can stay signed in as two people at once.

## User workflow

```mermaid
sequenceDiagram
  autonumber
  actor P as Police (CFPU)
  actor S as Police supervisor
  actor M as Hospital
  actor O as ODPP
  actor C as Court registry
  actor G as Caregiver / child
  P->>P: Register case (pseudonym, age band, category)
  P->>M: Medical referral (only selected fields shared)
  M-->>P: Acknowledge (joins case team, limited view)
  M-->>P: Complete (summary shared; clinical notes stay at hospital)
  Note over S: Family message proposed automatically
  S->>G: Approves plain-language message (four-eyes)
  P->>O: File submitted for prosecution review
  O-->>O: Records review milestones / requests information
  O->>C: Court handoff
  C-->>G: Hearing scheduled → discreet reminder
  G->>P: "Please call me back" → tracked follow-up
```

## Script

| # | Account | Do | Say |
|---|---|---|---|
| 1 | `police.officer` | Overview → **Register case**: “Demo Child C”, 12–14, category, Kampala, tick *immediate protection*, add a protection concern, tick *Medical* | “Only what is needed: a pseudonym and an age band. The protection concern is encrypted and only our station can see it.” |
| 2 | ″ | On the case page: **Make referral** → Medical → Nakawa Demo Referral Hospital; leave the sensitive fields unticked | “Purpose-specific sharing. The hospital gets age range, language and category, nothing else.” |
| 3 | `medical.officer` | Referrals → Incoming → open it. Show that only the snapshot is visible → **Acknowledge** → **Record completion** with a summary plus restricted notes | “The clinical notes stay with the hospital. Police only get the summary. Every step has a timestamp.” |
| 4 | `gulu.officer` *(optional)* | Paste the case URL | “A different station gets *Not found*. Isolation is enforced by the API, not just the menu.” |
| 5 | `police.supervisor` | **Family update reviews** → approve the medical message | “Nothing reaches a family automatically. A second officer approves every message.” |
| 6 | `police.officer` | Case → **Family access** → request access for `caregiver.other` as Guardian, confirm the conflict check. Then `police.supervisor` approves | “Abuse is often within the family, so a relative never gets access automatically.” |
| 7 | `police.officer` | **Change stage** → *File submitted for prosecution review*; **Make referral** → Prosecution (ODPP) | |
| 8 | `prosecutor` | Acknowledge the incoming referral → open the case → change stage to *Prosecution decision recorded* then *Court process initiated* → refer to the court registry | “The prosecutor records the decision. The system never makes one.” |
| 9 | `court.registry` | Acknowledge → **Schedule hearing** with a date, public location and a note for the family. **Add update** with a family message → `police.officer` approves it in Reviews | “The family sees a plain message and gets a discreet reminder: *You have an upcoming scheduled appointment…*” |
| 10 | `caregiver.other` | Home: journey path at *Court*, latest news, hearing card, support officer. **See everything** → **Ask for help** | “Five questions answered in simple words. No investigation, medical or evidence details. Quick exit at the top.” |
| 11 | `complainant.demo` on a phone | Welcome page → **Tell us what happened** → My child, 9–11, Kampala → Luganda → record a voice note → send. Then `police.officer` → **Reports to verify** → read the Sunbird AI summary, ask a question, register the case. Back as the complainant: answer, then follow the case | “Speak in Luganda or Acholi. Sunbird AI transcribes and summarises, but a police officer verifies everything within 24 hours.” |
| 12 | `admin` | **Anonymised analytics** (point out *fewer than 5*) → **SMS delivery** (“Simulated”) → **Audit log** (security events) → try `/app/cases` | “Admins manage the platform but cannot read cases. Small groups are hidden so no child can be identified.” |
| 13 | `complainant.demo` | **USSD** (complainant menu): choose 2 (Kiswahili) → 1 → report → note the reference and PIN; dial again → 2 → check status. Then `police.officer` → **Anonymous reports** (police only) → assess → convert to case | “No name, no ID, the number is not stored. The report stays *unverified* until an officer assesses it.” |

## Three-minute pitch

**Problem (40s).** Last year Ugandan police recorded more than ten thousand defilement cases. Most of these
children pass through five to seven institutions — police, hospital, forensic services, ODPP, court,
probation and support services. Every handoff is a place where a child can be lost: referrals go
unacknowledged, families don't know what is happening, hearings are missed, and confidential details travel
further than they should. *(Cite the 2025 UPF figures after checking them in the primary report.)*

**Solution (60s).** Tuliwamu is a secure coordination layer, not another case file. Each institution sees only
what it needs. Every referral is traceable from *sent* to *acknowledged* to *completed*. The child — or a
carefully authorised caregiver — can answer five questions in their own language: *Has my case been received?
Where is it now? What has happened? Do I need to attend anything? Where can I get help?* Every family message is
approved by two officers. For people without smartphones, anyone can report a concern anonymously from a basic
phone over USSD.

**Why we can be trusted (40s).** Isolation is enforced by the API and tested. Sensitive fields are encrypted.
SMS messages never reveal anything. Analytics suppress small groups. There is no AI deciding guilt, and humans
stay accountable for every step. It complements the police, ODPP and court systems and links to Sauti 116.

**Impact and scale (40s).** A one-district pilot with CFPU, a referral hospital, the ODPP, a court registry and
probation. Success means more referrals acknowledged within 24 hours, more families answered within 48 hours,
and more hearings with a reminder sent. Costs stay low (open-source, cloud), so it can spread district by
district through the Administration of Justice programme and development partners.

**Ask (20s).** Pilot partners, a legal and data-protection review, and qualified translators for Luganda,
Runyankole, Acholi, Ateso and Kiswahili.
