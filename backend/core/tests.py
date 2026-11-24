from django.core.management import call_command
from django.test import TestCase

from accounts.models import User
from cases.models import ChildCase
from communications.models import AnonymousReport
from complaints.models import Complaint
from institutions.models import Institution
from notifications.models import Notification
from referrals.models import Referral


class CleanSeedTests(TestCase):
    def test_default_seed_is_a_clean_start(self):
        call_command("seed_demo", verbosity=0)
        self.assertTrue(User.objects.filter(username="complainant.demo", role="COMPLAINANT").exists())
        self.assertTrue(User.objects.filter(username="police.officer").exists())
        self.assertTrue(Institution.objects.exists())
        for model in (ChildCase, Referral, AnonymousReport, Complaint, Notification):
            self.assertEqual(model.objects.count(), 0, model.__name__)

    def test_reset_id_wipes_activity_once(self):
        call_command("seed_demo", "--sample-data", "--background", "3", verbosity=0)
        self.assertGreater(ChildCase.objects.count(), 0)
        call_command("seed_demo", "--reset-id", "r1", verbosity=0)
        self.assertEqual(ChildCase.objects.count(), 0)
        # Same ID again: nothing is wiped (safe on every restart).
        police = User.objects.get(username="police.officer")
        call_command("seed_demo", "--reset-id", "r1", verbosity=0)
        self.assertTrue(User.objects.filter(pk=police.pk).exists())
