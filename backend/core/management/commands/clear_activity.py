"""Delete all activity (cases, referrals, reports, documents, messages, notifications, audit trail) while
keeping user accounts, passwords, institutions, memberships, support services and notification settings.

Usage:  python manage.py clear_activity --yes
Hosted: set CLEAR_ACTIVITY_ID on the server; it runs once per distinct value (see start.sh).
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from appointments.models import Appointment
from audit.models import AuditLog
from cases.models import (BeneficiaryAccessGrant, CaseAssignment, CaseStatusHistory, CaseUpdate, Child, ChildCase,
                          FollowUp)
from communications.models import AnonymousReport, AnonymousReportEvent, SmsMessage, UssdSession
from complaints.models import Complaint, ComplaintAudio, ComplaintEvent, ComplaintMessage
from core.models import DemoState
from documents.models import CaseDocument, DocumentAccess
from notifications.models import Notification
from referrals.models import Referral, ReferralStatusHistory
from support_services.models import AssistanceRequest

# Children before parents, so protected foreign keys never block the wipe.
ORDER = [
    DocumentAccess, CaseDocument, ComplaintAudio, ComplaintMessage, ComplaintEvent, Complaint,
    AnonymousReportEvent, AnonymousReport, UssdSession, SmsMessage, Notification,
    FollowUp, AssistanceRequest, Appointment, ReferralStatusHistory, Referral,
    CaseUpdate, CaseStatusHistory, BeneficiaryAccessGrant, CaseAssignment, ChildCase, Child, AuditLog,
]


class Command(BaseCommand):
    help = "Remove all activity data but keep accounts, institutions and services."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="Confirm the deletion.")
        parser.add_argument("--once-id", default="", help="Only run if this ID has not been applied before.")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["once_id"]:
            state = DemoState.objects.filter(key="clear_activity_id").first()
            if state and state.value == opts["once_id"]:
                self.stdout.write("Activity clear already applied; nothing to do.")
                return
        elif not opts["yes"]:
            raise CommandError("This deletes all cases, reports and documents. Re-run with --yes to confirm.")
        counts = {}
        for model in ORDER:
            n, _ = model.objects.all().delete()
            counts[model.__name__] = n
        if opts["once_id"]:
            DemoState.objects.update_or_create(key="clear_activity_id", defaults={"value": opts["once_id"]})
        AuditLog.objects.create(action="system.activity_cleared", object_type="System", is_security_event=True,
                                metadata={"deleted": {k: v for k, v in counts.items() if v}})
        self.stdout.write(self.style.SUCCESS("Activity cleared; accounts, institutions and services kept."))
