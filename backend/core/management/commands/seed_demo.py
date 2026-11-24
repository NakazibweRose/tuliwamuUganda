"""Seed an entirely FICTIONAL demonstration environment.

No real names, phone numbers, case numbers, medical records or allegations are used. Every
institution is marked as a demo institution. Run:  python manage.py seed_demo --reset
"""
import random
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from appointments.models import Appointment
from appointments.services import create_appointment
from cases import services as case_services
from cases.models import BeneficiaryStatus, CaseStatusHistory, CaseUpdate, ChildCase, FollowUp, GrantStatus
from communications.models import AnonymousReport, AnonymousReportEvent, SmsMessage, UssdSession
from django.contrib.auth.hashers import make_password
from institutions.models import Institution, InstitutionMembership
from notifications.models import Notification, NotificationPreference
from referrals import services as ref_services
from referrals.models import Referral, ReferralStatusHistory
from support_services.models import AssistanceRequest, SupportService
from audit.models import AuditLog

DEMO_PASSWORD = "Tuliwamu#Demo2026"

INSTITUTIONS = [
    # key, name, type, district, region
    ("kla_police", "Kampala Central Police Station (Demo)", "POLICE", "Kampala", "CENTRAL"),
    ("gulu_police", "Gulu Demo Police Station", "POLICE", "Gulu", "NORTHERN"),
    ("mbarara_police", "Mbarara Demo Police Station", "POLICE", "Mbarara", "WESTERN"),
    ("soroti_police", "Soroti Demo Police Station", "POLICE", "Soroti", "EASTERN"),
    ("hospital", "Nakawa Demo Referral Hospital", "HEALTH", "Kampala", "CENTRAL"),
    ("gulu_health", "Gulu Demo Health Centre IV", "HEALTH", "Gulu", "NORTHERN"),
    ("forensic", "Demo Forensic Services Unit", "FORENSIC", "Kampala", "CENTRAL"),
    ("odpp", "ODPP Demonstration Office – Kampala", "ODPP", "Kampala", "CENTRAL"),
    ("court", "Demo Family & Children Court Registry", "COURT", "Kampala", "CENTRAL"),
    ("probation", "Kampala Demo Probation & Social Welfare Office", "PROBATION", "Kampala", "CENTRAL"),
    ("legal_aid", "Demo Legal Aid Clinic", "LEGAL_AID", "Kampala", "CENTRAL"),
    ("psychosocial", "Demo Psychosocial Support Centre", "PSYCHOSOCIAL", "Kampala", "CENTRAL"),
    ("shelter", "Demo Safe Shelter", "SHELTER", "Wakiso", "CENTRAL"),
]

USERS = [
    # username, full name, role, institution key, title, supervisor
    ("police.officer", "Insp. Demo Okello", "POLICE", "kla_police", "Child & Family Protection Unit investigator", False),
    ("police.supervisor", "ASP Demo Namuli", "POLICE", "kla_police", "CFPU officer in charge", True),
    ("gulu.officer", "Sgt. Demo Ocen", "POLICE", "gulu_police", "Investigator", False),
    ("mbarara.officer", "Sgt. Demo Tumusiime", "POLICE", "mbarara_police", "Investigator", False),
    ("soroti.officer", "Sgt. Demo Okiror", "POLICE", "soroti_police", "Investigator", False),
    ("medical.officer", "Dr. Demo Nansubuga", "MEDICAL", "hospital", "Medical officer", False),
    ("gulu.medical", "Dr. Demo Akello", "MEDICAL", "gulu_health", "Clinical officer", False),
    ("forensic.officer", "Demo Forensic Analyst", "FORENSIC", "forensic", "Forensic analyst", False),
    ("prosecutor", "State Attorney Demo Kato", "PROSECUTOR", "odpp", "State attorney", True),
    ("court.registry", "Demo Court Clerk Atim", "COURT", "court", "Registry clerk", False),
    ("probation.officer", "Demo Probation Officer Mugisha", "PROBATION", "probation", "Probation & social welfare officer", True),
    ("legalaid.officer", "Demo Legal Aid Advocate Auma", "LEGAL_AID", "legal_aid", "Advocate", False),
    ("support.counsellor", "Demo Counsellor Nakato", "LEGAL_AID", "psychosocial", "Counsellor", False),
]

SERVICES = [
    ("psychosocial", "PSYCHOSOCIAL", "Child counselling sessions", "Free, confidential counselling for children and families.", ["en", "lg", "sw"]),
    ("legal_aid", "LEGAL_AID", "Free legal advice for families", "Explains the court process and supports children who are witnesses.", ["en", "lg"]),
    ("shelter", "SHELTER", "Temporary safe shelter", "Short-term safe accommodation arranged through a probation officer.", ["en", "lg"]),
    ("probation", "PROBATION", "Probation & social welfare support", "Home visits, welfare assessments and help to attend appointments.", ["en", "lg", "sw"]),
    ("hospital", "MEDICAL", "Child-friendly medical care", "Examination and treatment in a private room.", ["en", "lg", "sw"]),
]

CATEGORIES = ["SEXUAL_ABUSE"] * 9 + ["PHYSICAL_VIOLENCE"] * 6 + ["NEGLECT"] * 5 + ["EXPLOITATION"] * 3 + ["TRAFFICKING", "EMOTIONAL_ABUSE", "OTHER"]
AGES = ["5-8", "9-11", "12-14", "15-17", "0-4"]


class Command(BaseCommand):
    help = "Create fictional institutions, users and cases for demonstration."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing demo data first.")
        parser.add_argument("--background", type=int, default=48, help="Number of background cases for analytics.")
        parser.add_argument("--if-empty", action="store_true", help="Only seed when no institutions exist (safe on every start).")

    def handle(self, *args, **opts):
        if opts["if_empty"] and Institution.objects.exists():
            self.stdout.write("Data already present; skipping demo seed.")
            return
        self.rng = random.Random(2026)
        with transaction.atomic():
            if opts["reset"]:
                self.reset()
            self.inst = self.create_institutions()
            self.users = self.create_users()
            self.create_services()
            self.background_cases(opts["background"])
            # Start the demo story with clean inboxes.
            Notification.objects.all().delete()
            SmsMessage.objects.all().delete()
            self.story()
            self.anonymous_reports()
        self.stdout.write(self.style.SUCCESS(f"Demo data ready. All demo accounts use the password: {DEMO_PASSWORD}"))

    # ------------------------------------------------------------------
    def reset(self):
        for model in [AuditLog, Notification, SmsMessage, UssdSession, AnonymousReportEvent, AnonymousReport, FollowUp,
                      AssistanceRequest, Appointment, ReferralStatusHistory, Referral, CaseUpdate, CaseStatusHistory]:
            model.objects.all().delete()
        ChildCase.objects.all().delete()
        from cases.models import Child

        Child.objects.all().delete()
        SupportService.objects.all().delete()
        NotificationPreference.objects.all().delete()
        InstitutionMembership.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        Institution.objects.all().delete()

    def create_institutions(self):
        out = {}
        for idx, (key, name, typ, district, region) in enumerate(INSTITUTIONS):
            out[key], _ = Institution.objects.update_or_create(
                name=name, defaults=dict(type=typ, district=district, region=region, is_demo=True,
                                         public_contact=f"Demo desk line {101 + idx} (fictional)"),
            )
        return out

    def _user(self, username, full_name, role, **extra):
        user, created = User.objects.get_or_create(username=username, defaults=dict(full_name=full_name, role=role, email=f"{username}@demo.tuliwamu.example", **extra))
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
        return user

    def create_users(self):
        users = {}
        for username, name, role, inst, title, sup in USERS:
            u = self._user(username, name, role)
            InstitutionMembership.objects.update_or_create(user=u, institution=self.inst[inst], defaults=dict(title=title, is_supervisor=sup, is_active=True))
            users[username] = u
        users["admin"] = self._user("admin", "Demo System Administrator", "ADMIN")
        users["caregiver.demo"] = self._user("caregiver.demo", "Demo Caregiver (Aunt of Demo Child A)", "CAREGIVER", preferred_language="lg")
        users["child.demo"] = self._user("child.demo", "Demo Child A", "BENEFICIARY")
        users["caregiver.other"] = self._user("caregiver.other", "Demo Caregiver (no grants)", "CAREGIVER")
        # Discreet SMS preference for the caregiver. Placeholder number is only set while the mock
        # provider (or the Africa's Talking sandbox) is in use, so seed data can never text a real phone.
        safe_mode = settings.SMS_PROVIDER != "africastalking" or settings.AFRICASTALKING_ENVIRONMENT == "sandbox"
        NotificationPreference.objects.update_or_create(
            user=users["caregiver.demo"],
            defaults=dict(preferred_channel="SMS", preferred_language="lg", sms_consent=True,
                          safe_phone="+256700000001" if safe_mode else "", quiet_hours_start=22, quiet_hours_end=6,
                          consent_reference="DEMO-CONSENT-001 (recorded by probation officer, fictional)",
                          consent_recorded_by=users["probation.officer"], consent_recorded_at=timezone.now()),
        )
        return users

    def create_services(self):
        for key, cat, name, desc, langs in SERVICES:
            SupportService.objects.update_or_create(
                name=name, defaults=dict(institution=self.inst[key], category=cat, description=desc, languages=langs,
                                         public_contact=self.inst[key].public_contact, hours="Mon–Fri 8:00–17:00",
                                         districts=["Kampala", "Wakiso"]),
            )
        SupportService.objects.update_or_create(
            name="National child helpline (verify number before go-live)",
            defaults=dict(institution=self.inst["probation"], category="HELPLINE",
                          description="Toll-free helpline for children. Listed here for demonstration; confirm current details with MGLSD.",
                          public_contact="116", hours="24 hours", languages=["en", "lg", "sw"]),
        )

    # ------------------------------------------------------------------
    def _register(self, officer, pseudonym, age, category, district, region, days_ago, **extra):
        data = dict(child_pseudonym=pseudonym, age_range=age, preferred_language=extra.pop("lang", "en"),
                    date_reported=timezone.localdate() - timedelta(days=days_ago), incident_category=category,
                    district=district, region=region, confirm_not_duplicate=True, **extra)
        case = case_services.register_case(officer, data)
        stamp = timezone.now() - timedelta(days=days_ago)
        ChildCase.objects.filter(pk=case.pk).update(created_at=stamp)
        CaseUpdate.objects.filter(case=case).update(created_at=stamp)
        CaseStatusHistory.objects.filter(case=case).update(created_at=stamp)
        return case

    def _refer(self, sender, case, receiver_key, category, *, ack_by=None, complete_by=None, ack_hours=None, days_ago=0, shared=None):
        r = ref_services.create_referral(sender, case, dict(
            receiving_institution=self.inst[receiver_key], category=category, priority="URGENT" if category == "MEDICAL" else "ROUTINE",
            purpose=f"Demo {category.lower()} referral.", shared_fields=shared or ["age_range", "preferred_language", "incident_category"],
            visible_to_beneficiary=category in {"MEDICAL", "PSYCHOSOCIAL", "LEGAL_AID"},
        ))
        sent = timezone.now() - timedelta(days=days_ago)
        Referral.objects.filter(pk=r.pk).update(sent_at=sent, created_at=sent)
        if ack_by:
            ref_services.transition(ack_by, r, "acknowledge")
            Referral.objects.filter(pk=r.pk).update(acknowledged_at=sent + timedelta(hours=ack_hours or 6))
            if complete_by:
                ref_services.transition(complete_by, r, "complete", outcome_summary="Service provided (demo summary).",
                                        restricted_notes="Fictional restricted notes — visible only to the receiving institution.")
                Referral.objects.filter(pk=r.pk).update(completed_at=sent + timedelta(hours=(ack_hours or 6) + 30))
        return r

    def background_cases(self, n):
        rng = self.rng
        stations = [
            ("police.officer", "Kampala", "CENTRAL", "hospital"),
            ("gulu.officer", "Gulu", "NORTHERN", "gulu_health"),
            ("mbarara.officer", "Mbarara", "WESTERN", "hospital"),
            ("soroti.officer", "Soroti", "EASTERN", "hospital"),
        ]
        weights = [0.45, 0.25, 0.18, 0.12]
        for i in range(n):
            officer_key, district, region, hospital = rng.choices(stations, weights)[0]
            officer = self.users[officer_key]
            case = self._register(officer, f"Background Demo Child {i + 1:02d}", rng.choice(AGES), rng.choice(CATEGORIES),
                                  district, region, days_ago=rng.randint(5, 170))
            if rng.random() < 0.8:
                hosp_user = self.users["gulu.medical" if hospital == "gulu_health" else "medical.officer"]
                roll = rng.random()
                self._refer(officer, case, hospital, "MEDICAL",
                            ack_by=hosp_user if roll < 0.85 else None,
                            complete_by=hosp_user if roll < 0.65 else None,
                            ack_hours=rng.choice([2, 4, 8, 20, 30, 50]), days_ago=rng.randint(1, 4))
            if rng.random() < 0.45:
                roll = rng.random()
                self._refer(officer, case, "probation", "PROBATION",
                            ack_by=self.users["probation.officer"] if roll < 0.7 else None,
                            complete_by=self.users["probation.officer"] if roll < 0.4 else None,
                            ack_hours=rng.choice([12, 24, 48, 72]), days_ago=rng.randint(2, 10))
            if rng.random() < 0.3:
                self._refer(officer, case, "psychosocial", "PSYCHOSOCIAL",
                            ack_by=self.users["support.counsellor"] if rng.random() < 0.6 else None,
                            ack_hours=rng.choice([24, 96]), days_ago=rng.randint(10, 30))
            if rng.random() < 0.35:
                case_services.change_stage(officer, case, "UNDER_INVESTIGATION")
                if rng.random() < 0.6:
                    case_services.change_stage(officer, case, "FILE_SUBMITTED_FOR_PROSECUTION")
                    pros = self.users["prosecutor"]
                    roll = rng.random()
                    self._refer(officer, case, "odpp", "PROSECUTION", ack_by=pros if roll < 0.8 else None,
                                complete_by=pros if roll < 0.5 else None, ack_hours=rng.choice([24, 72, 120]), days_ago=rng.randint(3, 20))
                    if roll < 0.3:
                        case_services.change_stage(pros, case, "PROSECUTION_DECISION_RECORDED")
                        case_services.change_stage(pros, case, "COURT_PROCESS_INITIATED")

    # ------------------------------------------------------------------
    def story(self):
        """The two cases judges see first: Demo Child A (well advanced) and Demo Child B (new)."""
        u = self.users
        police, sup, med, pros, court, prob = (u["police.officer"], u["police.supervisor"], u["medical.officer"],
                                               u["prosecutor"], u["court.registry"], u["probation.officer"])
        case = self._register(police, "Demo Child A", "15-17", "SEXUAL_ABUSE", "Kampala", "CENTRAL", days_ago=40,
                              lang="lg", immediate_risk=True, referral_needs=["MEDICAL", "PROBATION", "PSYCHOSOCIAL", "PROSECUTION"],
                              location_detail="Fictional village, Kampala (demo)",
                              protection_concerns="Fictional: child staying with aunt while concerns are assessed.",
                              external_reference="DEMO-SD-001")
        self._refer(police, case, "hospital", "MEDICAL", ack_by=med, complete_by=med, ack_hours=3, days_ago=39,
                    shared=["age_range", "preferred_language", "incident_category", "immediate_risk"])
        self._refer(police, case, "probation", "PROBATION", ack_by=prob, ack_hours=20, days_ago=38)
        case_services.change_stage(police, case, "UNDER_INVESTIGATION", "Statements being recorded (demo).")
        case_services.change_stage(police, case, "FILE_SUBMITTED_FOR_PROSECUTION")
        self._refer(police, case, "odpp", "PROSECUTION", ack_by=pros, complete_by=pros, ack_hours=48, days_ago=20)
        case_services.change_stage(pros, case, "PROSECUTION_DECISION_RECORDED", "Decision recorded by the prosecutor (demo).")
        case_services.change_stage(pros, case, "COURT_PROCESS_INITIATED")
        self._refer(pros, case, "court", "COURT", ack_by=court, ack_hours=24, days_ago=10)
        case_services.change_stage(court, case, "COURT_HEARING_SCHEDULED")
        when = (timezone.localtime() + timedelta(days=12)).replace(hour=9, minute=30, second=0, microsecond=0)
        create_appointment(court, dict(case=case, type="COURT_HEARING", scheduled_for=when,
                                       public_location="Demo Family & Children Court, Room 2",
                                       beneficiary_note="Your support officer will meet you at the entrance 30 minutes before.",
                                       internal_note="Child-friendly room requested (demo).", visible_to_beneficiary=True))
        # Approve every pending family-facing message with a second officer.
        for upd in CaseUpdate.objects.filter(case=case, beneficiary_status=BeneficiaryStatus.PENDING):
            case_services.review_update(sup, upd, True)
        upd = case_services.add_update(court, case, dict(
            category="COURT", note="Hearing date fixed (demo).", visibility="CASE_TEAM",
            beneficiary_message="A court appearance has been scheduled. Your support officer will explain what to expect and help you get there.",
            beneficiary_journey_step="COURT"))
        case_services.review_update(police, upd, True)
        for who, rel, basis in [
            (u["caregiver.demo"], "CAREGIVER", "Aunt currently caring for the child; probation assessment found no conflict of interest (fictional)."),
            (u["child.demo"], "SELF", "Child aged 15–17 asked to follow her own case; agreed with probation officer (fictional)."),
        ]:
            g = case_services.create_grant(police, case, who, dict(relationship=rel, basis=basis, conflict_check_confirmed=True))
            case_services.approve_grant(sup, g)

        # Demo Child B: freshly registered with a medical referral awaiting acknowledgement.
        case_b = self._register(police, "Demo Child B", "9-11", "PHYSICAL_VIOLENCE", "Kampala", "CENTRAL", days_ago=1,
                                referral_needs=["MEDICAL", "PSYCHOSOCIAL"], protection_concerns="Fictional demo concern.")
        self._refer(police, case_b, "hospital", "MEDICAL", days_ago=0)
        Notification.objects.filter(recipient=police).delete()

    def anonymous_reports(self):
        samples = [
            ("SEXUAL_ABUSE", "YES", "Wakiso", "Fictional demo report: a neighbour's child seems afraid to go home.", "URGENT", "lg"),
            ("NEGLECT", "NO", "Gulu", "Fictional demo report: young children often left alone at night.", "NEW", "ach"),
            ("EXPLOITATION", "UNSURE", "Mbale", "Fictional demo report: children working at a quarry during school hours.", "UNDER_REVIEW", "en"),
        ]
        from core.references import unique_reference

        for cat, danger, loc, desc, status, lang in samples:
            AnonymousReport.objects.create(
                reference_code=unique_reference(AnonymousReport, "reference_code", "AR", 6),
                pin_hash=make_password("1234"), channel="SIMULATOR", category=cat, immediate_danger=danger,
                general_location=loc, description=desc, preferred_language=lang, review_status=status,
            )
