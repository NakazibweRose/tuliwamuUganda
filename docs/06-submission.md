# Tuliwamu — securely coordinating child-sensitive referrals and support

*Hackathon written submission (two pages). Prototype with fictional data; not an official or government-approved system.*

## 1. Problem (Uganda)
Police recorded **12,312 defilement cases in 2024 and 10,492 in 2025**. Of the 2025 cases, **4,886 reached court, 713 ended in conviction and 3,791 were still pending** (UPF Annual Crime Report 2025, as reported in the media — figures to be confirmed in the primary report). Reports are only part of the picture: the national *Violence Against Children Survey 2015* found that **about 35% of young women and 17% of young men** experienced sexual violence before age 18. Sexual-offence cases can take **2–10 years** to conclude, and aggravated defilement dominates many High Court criminal sessions.

A child victim's journey runs through the police (often the Child & Family Protection Unit), health workers, forensic services, the ODPP, courts, probation & social welfare officers and support organisations. Handoffs between them are fragmented. Families do not know where a case stands. Children may repeat their story. Hearing dates are missed. Confidential details can be overshared. Coordination is a missing layer: there is no shared, accountable trail of who referred what, to whom, and whether it was acted on. (Sources and confidence levels: `docs/05-research-and-evidence.md`.)

## 2. Research questions & objectives
**Questions:** Where do delays occur between report, care, prosecution review and hearing? Which handoffs lack acknowledgement? What does a child or caregiver need to know, in which language and channel? What is the minimum information each institution needs? Which safeguards stop family access or messages from endangering the child?

**Measurable objectives:** (1) register cases securely; (2) traceable referrals with recorded acknowledgement and completion; (3) human-recorded milestones; (4) reviewed, plain-language updates for authorised children and caregivers; (5) appointment and hearing reminders; (6) strict role-, institution- and object-level access; (7) anonymised reporting with small-cell suppression; (8) six languages; (9) feature-phone access over USSD and SMS.

## 3. Ideation rationale
We chose a **coordination layer**, not a new case-management system. Police files, the ODPP, court systems (e.g. ECCMIS) and clinical records stay authoritative. Tuliwamu records **referrals, milestones, appointments and approved messages**. It is built around the five questions a child should be able to answer: *Has my case been received? Where is it? What has happened? Do I need to attend anything? Where can I get help?*

**Deliberately excluded:** evidence and document storage, AI risk scoring, automated prosecution or guilt decisions, facial recognition, and automatic family access. **Fit for Uganda:** works on low-end phones (lazy-loaded, 6 KB of CSS gzip), anonymous USSD reporting for people without smartphones, discreet SMS for shared phones, six languages, and links to the existing **Sauti 116** helpline.

## 4. Prototype & execution
**Stack:** React + Tailwind · Django REST Framework · PostgreSQL · Africa's Talking (USSD and SMS).

**Working end to end:** police registers a case → purpose-specific medical referral → hospital acknowledges and completes it (clinical notes stay with the hospital) → a second officer approves the plain-language family message → file submitted to the ODPP → the prosecutor records milestones and hands off to court → the court schedules a hearing → the authorised caregiver sees the simplified journey and hearing date and asks for help → the request becomes a tracked follow-up → the administrator sees anonymised analytics. A **USSD simulator** uses the same engine as the live Africa's Talking callback.

**Security and safeguarding:**
- Out-of-scope IDs return 404.
- Sensitive fields are visible to the lead institution only and encrypted at rest.
- Referrals share a snapshot of only the selected fields.
- Family access is per case, needs a conflict-of-interest confirmation and two-officer approval, and can be revoked.
- Every family-facing message needs four-eyes approval.
- Quick exit, inactivity logout, no data in browser storage, httpOnly rotating refresh tokens, lockout and rate limits.
- Audit log; administrators cannot read cases.
- SMS is discreet: consent, safe number, quiet hours, and no false "delivered" status.
- USSD never stores the reporter's phone number.

**Quality:** 85 backend tests (isolation, ID tampering, beneficiary leakage, USSD, SMS), frontend unit tests, and a Playwright script that runs the full judge journey.

**Legal awareness:** designed around the Data Protection and Privacy Act, 2019 (s.8, children's data) and the Children Act. Legal review is still required.

## 5. Stakeholders & ecosystem
- **Users:** CFPU police, health workers and police surgeons, forensic services, ODPP State Attorneys, court registries, probation & social welfare officers, legal aid and psychosocial providers.
- **Beneficiaries:** child victims and authorised caregivers.
- **Institutions and regulators:** Administration of Justice programme (formerly JLOS), MGLSD (also runs Sauti 116), Personal Data Protection Office, UCC (short codes).
- **Partners:** UNICEF, UNFPA and Spotlight-type programmes; legal aid networks; Africa's Talking and mobile network operators; district local governments.

## 6. Viability, funding & success metrics
**Indicative costs (estimates, to be validated):**
- **Pilot, one district, 12 months:** cloud hosting and managed PostgreSQL (~US$50–150/month); USSD short code and SMS (operator- and volume-dependent); human translation review for 5 languages; training for ~60 officers; a part-time support engineer.
- **Scale:** per-district onboarding (training plus institution setup); costs do not grow per case.

**Funding routes:** development partners (child protection and GBV programmes), Administration of Justice programme budgets, MGLSD child-protection lines, district budgets, and CSR from telecoms (zero-rated USSD).

**Sustainability:** open source; runs on low-cost infrastructure; the system owner is housed in government.

**KPIs (all generated by the system):**
- % of referrals acknowledged, and median hours to acknowledgement
- % of referrals completed
- % of cases with a stage update in the last 30 days
- % of appointments with a reminder issued
- % of family assistance requests answered within 48 hours
- unauthorised-access attempts detected
- number of active institutions
- user satisfaction and accessibility feedback

We claim **no** reduction in backlog or change in conviction rates without pilot evidence.

## 7. Team, concept mastery & delivery
Architecture, data model, permission matrix, risks and roadmap: `docs/01-phase1-architecture.md`. Security controls mapped to tests: `docs/02-security-privacy.md`. Demo script and pitch: `docs/07-demo-script-and-pitch.md`. *(Team members: add names and contributions here — product and research, UX, frontend, backend, security and QA, legal research.)*
