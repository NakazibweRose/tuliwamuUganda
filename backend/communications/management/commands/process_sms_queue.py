from django.core.management.base import BaseCommand

from communications.sms.services import process_queue


class Command(BaseCommand):
    help = "Send SMS deferred by quiet hours and retry failed messages (bounded attempts)."

    def handle(self, *args, **opts):
        self.stdout.write(f"Dispatched {process_queue()} SMS")
