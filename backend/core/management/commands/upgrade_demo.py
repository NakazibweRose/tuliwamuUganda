"""Idempotent, non-destructive upgrade of an existing demo database (safe to run on every start).

* Renames the old `child.demo` account to `complainant.demo` with the Complainant role and removes its
  case access, so it starts on the welcome page.
* Adds the `complainant.two` account if missing (no data).
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from cases.models import BeneficiaryAccessGrant
from institutions.models import Institution


class Command(BaseCommand):
    help = "Bring an existing demo database up to date without deleting data."

    @transaction.atomic
    def handle(self, *args, **opts):
        if not Institution.objects.filter(is_demo=True).exists():
            self.stdout.write("No demo data; nothing to upgrade.")
            return
        old = User.objects.filter(username="child.demo").first()
        if old and not User.objects.filter(username="complainant.demo").exists():
            BeneficiaryAccessGrant.objects.filter(user=old).delete()
            old.username, old.role, old.full_name = "complainant.demo", "COMPLAINANT", "Demo Complainant"
            old.save(update_fields=["username", "role", "full_name"])
            self.stdout.write("Renamed child.demo -> complainant.demo")
        if not User.objects.filter(username="complainant.two").exists():
            from core.management.commands.seed_demo import DEMO_PASSWORD, Command as Seed

            seed = Seed()
            seed.users = {"complainant.two": seed._user("complainant.two", "Demo Complainant Two", "COMPLAINANT", preferred_language="ach")}
            if User.objects.filter(username="complainant.demo").exists() is False:
                seed._user("complainant.demo", "Demo Complainant", "COMPLAINANT")
            seed.inst = {"kla_police": Institution.objects.filter(type="POLICE", is_demo=True).order_by("created_at").first()}
            self.stdout.write(f"Added complainant.two (password {DEMO_PASSWORD})")
