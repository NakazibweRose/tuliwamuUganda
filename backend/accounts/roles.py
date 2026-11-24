"""Platform roles. A user has exactly one role; institutional roles also need a membership."""
from django.db import models


class Role(models.TextChoices):
    POLICE = "POLICE", "Police officer / investigator"
    MEDICAL = "MEDICAL", "Medical / health professional"
    FORENSIC = "FORENSIC", "Forensic officer"
    PROSECUTOR = "PROSECUTOR", "ODPP / prosecutor"
    COURT = "COURT", "Court registry officer"
    PROBATION = "PROBATION", "Probation / social welfare officer"
    LEGAL_AID = "LEGAL_AID", "Legal aid / support service provider"
    CAREGIVER = "CAREGIVER", "Parent / guardian / authorised caregiver"
    BENEFICIARY = "BENEFICIARY", "Child victim / protected beneficiary"
    COMPLAINANT = "COMPLAINANT", "Complainant (reports a case to the police)"
    ADMIN = "ADMIN", "System administrator"


INSTITUTIONAL_ROLES = {
    Role.POLICE, Role.MEDICAL, Role.FORENSIC, Role.PROSECUTOR,
    Role.COURT, Role.PROBATION, Role.LEGAL_AID,
}
BENEFICIARY_ROLES = {Role.CAREGIVER, Role.BENEFICIARY, Role.COMPLAINANT}
COMPLAINT_REVIEW_ROLES = {Role.POLICE}
CASE_REGISTRATION_ROLES = {Role.POLICE, Role.PROBATION}
ANONYMOUS_REPORT_TRIAGE_ROLES = {Role.POLICE, Role.PROBATION}
REFERRAL_CREATOR_ROLES = {Role.POLICE, Role.MEDICAL, Role.PROSECUTOR, Role.PROBATION, Role.LEGAL_AID}
GRANT_MANAGER_ROLES = {Role.POLICE, Role.PROBATION}


class Language(models.TextChoices):
    EN = "en", "English"
    SW = "sw", "Kiswahili"
    LG = "lg", "Luganda"
    NYN = "nyn", "Runyankole"
    ACH = "ach", "Acholi"
    TEO = "teo", "Ateso"
