from django.core.management.base import BaseCommand

from appointments.services import send_due_reminders


class Command(BaseCommand):
    help = "Send discreet reminders for appointments in the next N hours (default 48). Schedule hourly."

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=48)

    def handle(self, *args, **opts):
        self.stdout.write(f"Reminders sent: {send_due_reminders(opts['hours'])}")
