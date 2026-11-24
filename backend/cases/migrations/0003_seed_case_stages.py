from django.db import migrations

STAGES = [
    ("REPORT_RECEIVED", "Report received", "Your report was received.", "REPORTED", ["POLICE", "PROBATION"], False),
    ("UNDER_INVESTIGATION", "Under investigation", "The responsible institution is looking into your case.", "INVESTIGATION", ["POLICE"], False),
    ("MEDICAL_REFERRAL_INITIATED", "Medical referral initiated", "A medical referral has been arranged.", "SUPPORT", ["POLICE", "PROBATION"], False),
    ("MEDICAL_REFERRAL_COMPLETED", "Medical referral completed", "The medical referral has been completed.", "SUPPORT", ["POLICE", "MEDICAL"], False),
    ("FORENSIC_REFERRAL_INITIATED", "Forensic referral initiated", "Your case is being handled by the responsible institution.", "INVESTIGATION", ["POLICE"], False),
    ("FORENSIC_REFERRAL_COMPLETED", "Forensic referral completed", "Your case is being handled by the responsible institution.", "INVESTIGATION", ["POLICE", "FORENSIC"], False),
    ("FILE_SUBMITTED_FOR_PROSECUTION", "File submitted for prosecution review", "Your case has moved to the next stage.", "PROSECUTION", ["POLICE"], False),
    ("AWAITING_ADDITIONAL_INFORMATION", "Awaiting additional information", "Your case is still being reviewed.", "PROSECUTION", ["PROSECUTOR"], False),
    ("PROSECUTION_DECISION_RECORDED", "Prosecution decision recorded", "A decision about the next step has been made. Your support officer can explain it.", "PROSECUTION", ["PROSECUTOR"], False),
    ("RETURNED_FOR_FURTHER_INVESTIGATION", "Returned for further investigation", "Your case is still being looked into.", "INVESTIGATION", ["PROSECUTOR"], False),
    ("COURT_PROCESS_INITIATED", "Court process initiated", "Your case has moved to court.", "COURT", ["PROSECUTOR", "COURT"], False),
    ("COURT_HEARING_SCHEDULED", "Court hearing scheduled", "A court appearance has been scheduled.", "COURT", ["COURT"], False),
    ("COURT_PROCEEDINGS_ONGOING", "Court proceedings ongoing", "Your case is being heard in court.", "COURT", ["COURT"], False),
    ("CASE_CONCLUDED", "Case concluded", "The process for your case has finished. Your support officer can explain what this means.", "CONCLUDED", ["COURT", "PROSECUTOR", "POLICE"], True),
    ("REFERRED_FOR_CONTINUED_SUPPORT", "Referred for continued support", "You are being connected to continued support.", "CONCLUDED", ["PROBATION", "POLICE"], False),
]


def seed(apps, schema_editor):
    CaseStage = apps.get_model("cases", "CaseStage")
    for order, (code, label, ben, step, roles, terminal) in enumerate(STAGES, start=1):
        CaseStage.objects.update_or_create(
            code=code,
            defaults=dict(label=label, beneficiary_label=ben, journey_step=step, order=order * 10, allowed_roles=roles, is_terminal=terminal),
        )


class Migration(migrations.Migration):
    dependencies = [("cases", "0002_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
