from django.core.management.base import BaseCommand

from communications.ussd.engine import purge_expired_sessions


class Command(BaseCommand):
    help = "Delete expired USSD session state (run every few minutes)."

    def handle(self, *args, **opts):
        self.stdout.write(f"Purged {purge_expired_sessions()} expired USSD sessions")
