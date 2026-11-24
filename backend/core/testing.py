"""Shared test fixtures: a small fictional world with two police stations and service providers."""
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from cases import services as case_services
from institutions.models import Institution, InstitutionMembership

PASSWORD = "Test#Password2026"


class World(APITestCase):
    def setUp(self):
        cache.clear()
        mk = lambda name, typ, district="Kampala", region="CENTRAL": Institution.objects.create(
            name=name, type=typ, district=district, region=region, public_contact="Demo line"
        )
        self.kla = mk("Test Police KLA", "POLICE")
        self.gulu = mk("Test Police Gulu", "POLICE", "Gulu", "NORTHERN")
        self.hospital = mk("Test Hospital", "HEALTH")
        self.other_hospital = mk("Other Test Hospital", "HEALTH", "Gulu", "NORTHERN")
        self.forensic = mk("Test Forensic", "FORENSIC")
        self.odpp = mk("Test ODPP", "ODPP")
        self.court = mk("Test Court", "COURT")
        self.probation = mk("Test Probation", "PROBATION")

        self.police = self.user("police", "POLICE", self.kla)
        self.police2 = self.user("police2", "POLICE", self.kla, supervisor=True)
        self.gulu_police = self.user("gulupolice", "POLICE", self.gulu)
        self.medic = self.user("medic", "MEDICAL", self.hospital)
        self.other_medic = self.user("othermedic", "MEDICAL", self.other_hospital)
        self.forensic_officer = self.user("forensic", "FORENSIC", self.forensic)
        self.prosecutor = self.user("prosecutor", "PROSECUTOR", self.odpp)
        self.clerk = self.user("clerk", "COURT", self.court)
        self.probation_officer = self.user("probation", "PROBATION", self.probation, supervisor=True)
        self.admin = self.user("admin", "ADMIN")
        self.caregiver = self.user("caregiver", "CAREGIVER")
        self.other_caregiver = self.user("othercaregiver", "CAREGIVER")
        self.child_user = self.user("childuser", "BENEFICIARY")

        self.case = self.register(self.police, pseudonym="Test Child A", age="15-17")

    def user(self, username, role, institution=None, supervisor=False):
        u = User.objects.create_user(username=username, password=PASSWORD, role=role, full_name=f"Test {username}")
        if institution:
            InstitutionMembership.objects.create(user=u, institution=institution, is_supervisor=supervisor)
        return u

    def register(self, officer, pseudonym="Test Child", age="9-11", category="SEXUAL_ABUSE", **extra):
        data = dict(child_pseudonym=pseudonym, age_range=age, preferred_language="en",
                    date_reported=timezone.localdate() - timedelta(days=1), incident_category=category,
                    district="Kampala", region="CENTRAL", protection_concerns="SECRET-CONCERN fictional",
                    location_detail="SECRET-LOCATION fictional", confirm_not_duplicate=True)
        data.update(extra)
        return case_services.register_case(officer, data)

    def client_for(self, user):
        c = APIClient()
        c.force_authenticate(user)
        return c

    def refer(self, sender, case, receiver, category="MEDICAL", **extra):
        from referrals import services as ref_services

        data = dict(receiving_institution=receiver, category=category, purpose="Test referral",
                    shared_fields=["age_range", "incident_category"])
        data.update(extra)
        return ref_services.create_referral(sender, case, data)
