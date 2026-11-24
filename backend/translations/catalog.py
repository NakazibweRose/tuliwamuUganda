"""Backend message catalogue for SMS, in-app notifications and USSD menus.

English is the source language. Other languages are DRAFTS that must be reviewed by competent
human speakers before production use (see REVIEW_STATUS). Any missing key falls back to English,
so a partially translated language never shows an empty message.
"""
from string import Formatter

SUPPORTED_LANGUAGES = ["en", "sw", "lg", "nyn", "ach", "teo"]
LANGUAGE_NAMES = {
    "en": "English", "sw": "Kiswahili", "lg": "Luganda",
    "nyn": "Runyankole", "ach": "Acholi", "teo": "Ateso",
}
REVIEW_STATUS = {
    "en": "source",
    "sw": "draft — needs review by a qualified speaker",
    "lg": "draft — needs review by a qualified speaker",
    "nyn": "partial draft — most text falls back to English",
    "ach": "partial draft — most text falls back to English",
    "teo": "partial draft — most text falls back to English",
}

EN = {
    # ---- Discreet notifications (in-app title/body and SMS). No case details, ever. ----
    "notif.REFERRAL_RECEIVED.title": "New referral",
    "notif.REFERRAL_RECEIVED.body": "You have a new assigned referral. Please log in to Tuliwamu to review it.",
    "notif.REFERRAL_ACKNOWLEDGED.title": "Referral acknowledged",
    "notif.REFERRAL_ACKNOWLEDGED.body": "Your submitted referral has been acknowledged. Please check Tuliwamu for the next steps.",
    "notif.REFERRAL_UPDATED.title": "Referral updated",
    "notif.REFERRAL_UPDATED.body": "A referral you are following has been updated. Please log in to Tuliwamu.",
    "notif.REFERRAL_FOLLOW_UP.title": "Referral needs follow-up",
    "notif.REFERRAL_FOLLOW_UP.body": "A referral needs your attention. Please log in to Tuliwamu.",
    "notif.APPOINTMENT_SCHEDULED.title": "Appointment scheduled",
    "notif.APPOINTMENT_SCHEDULED.body": "You have an upcoming scheduled appointment. Please contact your designated support officer for details.",
    "notif.APPOINTMENT_CHANGED.title": "Appointment changed",
    "notif.APPOINTMENT_CHANGED.body": "A scheduled appointment has changed. Please contact your designated support officer for details.",
    "notif.APPOINTMENT_REMINDER.title": "Appointment reminder",
    "notif.APPOINTMENT_REMINDER.body": "You have an upcoming scheduled appointment. Please contact your designated support officer for details.",
    "notif.APPOINTMENT_MISSED.title": "Missed appointment",
    "notif.APPOINTMENT_MISSED.body": "An appointment was recorded as missed and needs follow-up. Please log in to Tuliwamu.",
    "notif.CASE_UPDATE.title": "Important update",
    "notif.CASE_UPDATE.body": "You have an important update. Please contact your designated support officer.",
    "notif.UPDATE_NEEDS_REVIEW.title": "Update awaiting review",
    "notif.UPDATE_NEEDS_REVIEW.body": "A family-facing update is waiting for your review in Tuliwamu.",
    "notif.GRANT_NEEDS_APPROVAL.title": "Access request awaiting approval",
    "notif.GRANT_NEEDS_APPROVAL.body": "A portal access request needs a second officer's approval in Tuliwamu.",
    "notif.ASSISTANCE_REQUEST.title": "Assistance requested",
    "notif.ASSISTANCE_REQUEST.body": "Someone you support has asked for assistance. Please log in to Tuliwamu.",
    "notif.ASSISTANCE_RESPONSE.title": "Your request has a response",
    "notif.ASSISTANCE_RESPONSE.body": "There is a response to your request. Please log in or contact your designated support officer.",
    "notif.SUPPORT_COMPLETED.title": "Support service completed",
    "notif.SUPPORT_COMPLETED.body": "A support service has been recorded as completed. Please log in to Tuliwamu.",
    "notif.ANONYMOUS_REPORT.title": "New anonymous report",
    "notif.ANONYMOUS_REPORT.body": "A new unverified report is waiting for assessment in Tuliwamu.",
    "notif.FOLLOW_UP_DUE.title": "Follow-up assigned",
    "notif.FOLLOW_UP_DUE.body": "A follow-up task has been assigned to you in Tuliwamu.",

    # ---- Complainant reports ----
    "notif.COMPLAINT_RECEIVED.title": "We have received your report",
    "notif.COMPLAINT_RECEIVED.body": "Thank you for telling us. A police officer will review your report and get back to you within 24 hours. Please keep checking Tuliwamu.",
    "notif.COMPLAINT_NEEDS_INFO.title": "The police have a question",
    "notif.COMPLAINT_NEEDS_INFO.body": "A police officer needs a little more information about your report. Please open Tuliwamu to reply.",
    "notif.COMPLAINT_MESSAGE.title": "New message from the police",
    "notif.COMPLAINT_MESSAGE.body": "You have a new message from the police about your report. Please open Tuliwamu.",
    "notif.COMPLAINT_REGISTERED.title": "Your report has been verified",
    "notif.COMPLAINT_REGISTERED.body": "The police have verified your report and opened a case. Open Tuliwamu to see what happens next.",
    "notif.NEW_COMPLAINT.title": "New report to verify",
    "notif.NEW_COMPLAINT.body": "A new report is waiting for verification in Tuliwamu. Please respond within 24 hours.",
    "notif.COMPLAINT_REPLY.title": "Complainant replied",
    "notif.COMPLAINT_REPLY.body": "A complainant has replied about their report. Please log in to Tuliwamu.",
    "notif.COMPLAINT_OVERDUE.title": "Report waiting over 24 hours",
    "notif.COMPLAINT_OVERDUE.body": "A report has waited more than 24 hours for verification. Please review it in Tuliwamu.",
    "sms.COMPLAINT_RECEIVED": "You have an update on Tuliwamu. Please log in or contact your support officer.",
    "sms.COMPLAINT_NEEDS_INFO": "You have an update on Tuliwamu. Please log in or contact your support officer.",
    "sms.COMPLAINT_MESSAGE": "You have an update on Tuliwamu. Please log in or contact your support officer.",
    "sms.COMPLAINT_REGISTERED": "You have an update on Tuliwamu. Please log in or contact your support officer.",

    # ---- USSD ----
    "ussd.welcome": "WELCOME TO TULIWAMU\nChoose your language:",
    "ussd.main": "Choose:\n1. Report a child protection concern\n2. Check an anonymous report\n3. Support services\n4. Exit",
    "ussd.invalid": "Invalid choice. Try again.",
    "ussd.too_many_invalid": "Too many invalid entries. Please dial again.",
    "ussd.exit": "Thank you. Stay safe.",
    "ussd.danger": "Is a child in immediate danger now?\n1. Yes\n2. No\n3. Not sure",
    "ussd.danger_advice": "If a child is in danger now, call {emergency}",
    "ussd.category": "Type of concern:\n1. Sexual abuse\n2. Physical violence\n3. Neglect\n4. Exploitation/child labour\n5. Trafficking\n6. Other",
    "ussd.location": "Enter the district or general area (no house details):",
    "ussd.location_invalid": "Please enter 2-40 letters for the district or area.",
    "ussd.description": "Briefly describe the concern. Do not include names:",
    "ussd.description_invalid": "Please enter 5-160 characters.",
    "ussd.contact_choice": "Leave a safe phone number so an officer can call you? (optional)\n1. No\n2. Yes",
    "ussd.contact_number": "Enter a safe phone number (e.g. 07XXXXXXXX):",
    "ussd.contact_invalid": "Number not valid. Enter 07XXXXXXXX or +2567XXXXXXXX, or 0 to skip.",
    "ussd.privacy": "Privacy: your mobile network can see this session. Tuliwamu does not save your number unless you gave one. Reports are checked by an officer.\n1. Continue\n2. Cancel",
    "ussd.confirm": "Submit this report?\n1. Submit\n2. Cancel",
    "ussd.cancelled": "Report cancelled. Nothing was saved.",
    "ussd.submitted": "Report received. Ref: {reference} PIN: {pin}. Keep them private. Dial again, choose 2, to check status. {emergency}",
    "ussd.rate_limited": "We cannot accept more reports from this line today. If a child is in danger call {emergency}",
    "ussd.check_ref": "Enter your report reference (e.g. AR-ABC123):",
    "ussd.check_pin": "Enter your 4-digit PIN:",
    "ussd.check_failed": "Reference or PIN not recognised. For help call {emergency}",
    "ussd.check_locked": "Too many attempts. Please try later or call {emergency}",
    "ussd.status": "Report {reference}: {status}",
    "ussd.status.NEW": "received, waiting for an officer to assess it.",
    "ussd.status.URGENT": "being assessed as a priority.",
    "ussd.status.UNDER_REVIEW": "being reviewed by an authorised officer.",
    "ussd.status.REFERRED": "reviewed and passed to a responsible service.",
    "ussd.status.CONVERTED": "reviewed and being handled by a responsible service.",
    "ussd.status.CLOSED": "review completed. For help call the Child Helpline 116.",
    "ussd.services": "Support: {emergency} Probation & Social Welfare offices are at every district HQ. Legal aid: ask at your district office.",

    # ---- Beneficiary-facing system messages proposed for review ----
    "ben.referral_completed.MEDICAL": "A medical appointment that was arranged for you has been completed.",
    "ben.referral_completed.PSYCHOSOCIAL": "A counselling or support session has been completed.",
    "ben.referral_completed.LEGAL_AID": "Legal aid support has been provided.",
    "ben.referral_completed.SHELTER": "Protection support has been arranged.",
    "ben.referral_completed.PROBATION": "A social welfare officer has completed a follow-up.",
    "ben.referral_completed.FORENSIC": "Your case has moved to the next step.",
    "ben.referral_completed.PROSECUTION": "Your case has moved to the next step.",
    "ben.referral_completed.COURT": "Your case has moved to the next step.",
    "ben.referral_sent.MEDICAL": "A medical referral has been arranged for you.",
    "ben.referral_sent.PSYCHOSOCIAL": "Counselling support has been arranged for you.",
    "ben.referral_sent.LEGAL_AID": "Legal aid support has been arranged for you.",
    "ben.referral_sent.SHELTER": "Protection support is being arranged for you.",
    "ben.referral_sent.PROBATION": "A social welfare officer will support you.",
}

SW = {
    "notif.REFERRAL_RECEIVED.title": "Rufaa mpya",
    "notif.REFERRAL_RECEIVED.body": "Una rufaa mpya uliyopangiwa. Tafadhali ingia Tuliwamu kuiangalia.",
    "notif.REFERRAL_ACKNOWLEDGED.title": "Rufaa imepokelewa",
    "notif.REFERRAL_ACKNOWLEDGED.body": "Rufaa uliyotuma imepokelewa. Tafadhali angalia Tuliwamu kwa hatua zinazofuata.",
    "notif.APPOINTMENT_SCHEDULED.title": "Miadi imepangwa",
    "notif.APPOINTMENT_SCHEDULED.body": "Una miadi iliyopangwa hivi karibuni. Tafadhali wasiliana na afisa wako wa msaada kwa maelezo.",
    "notif.APPOINTMENT_CHANGED.title": "Miadi imebadilika",
    "notif.APPOINTMENT_CHANGED.body": "Miadi iliyopangwa imebadilika. Tafadhali wasiliana na afisa wako wa msaada kwa maelezo.",
    "notif.APPOINTMENT_REMINDER.title": "Ukumbusho wa miadi",
    "notif.APPOINTMENT_REMINDER.body": "Una miadi iliyopangwa hivi karibuni. Tafadhali wasiliana na afisa wako wa msaada kwa maelezo.",
    "notif.CASE_UPDATE.title": "Taarifa muhimu",
    "notif.CASE_UPDATE.body": "Una taarifa muhimu. Tafadhali wasiliana na afisa wako wa msaada.",
    "notif.ASSISTANCE_RESPONSE.title": "Ombi lako limejibiwa",
    "notif.ASSISTANCE_RESPONSE.body": "Kuna jibu kwa ombi lako. Tafadhali ingia au wasiliana na afisa wako wa msaada.",
    "ussd.welcome": "KARIBU TULIWAMU\nChagua lugha:",
    "ussd.main": "Chagua:\n1. Ripoti wasiwasi kuhusu ulinzi wa mtoto\n2. Angalia ripoti isiyo na jina\n3. Huduma za msaada\n4. Toka",
    "ussd.invalid": "Chaguo si sahihi. Jaribu tena.",
    "ussd.too_many_invalid": "Makosa mengi. Tafadhali piga tena.",
    "ussd.exit": "Asante. Kaa salama.",
    "ussd.danger": "Je, mtoto yuko hatarini sasa hivi?\n1. Ndiyo\n2. Hapana\n3. Sina uhakika",
    "ussd.danger_advice": "Kama mtoto yuko hatarini sasa, piga {emergency}",
    "ussd.category": "Aina ya wasiwasi:\n1. Unyanyasaji wa kingono\n2. Ukatili wa kimwili\n3. Kutelekezwa\n4. Unyonyaji/ajira ya watoto\n5. Usafirishaji haramu\n6. Mengineyo",
    "ussd.location": "Andika wilaya au eneo kwa ujumla (bila maelezo ya nyumba):",
    "ussd.description": "Eleza wasiwasi kwa ufupi. Usiandike majina:",
    "ussd.contact_choice": "Acha namba salama ili afisa akupigie? (hiari)\n1. Hapana\n2. Ndiyo",
    "ussd.contact_number": "Andika namba salama ya simu (mf. 07XXXXXXXX):",
    "ussd.privacy": "Faragha: mtandao wako wa simu unaona kikao hiki. Tuliwamu haihifadhi namba yako isipokuwa umeitoa. Ripoti huangaliwa na afisa.\n1. Endelea\n2. Ghairi",
    "ussd.confirm": "Tuma ripoti hii?\n1. Tuma\n2. Ghairi",
    "ussd.cancelled": "Ripoti imeghairiwa. Hakuna kilichohifadhiwa.",
    "ussd.submitted": "Ripoti imepokelewa. Kumb: {reference} PIN: {pin}. Zihifadhi kwa siri. Piga tena, chagua 2, kuangalia hali. {emergency}",
    "ussd.check_ref": "Andika kumbukumbu ya ripoti (mf. AR-ABC123):",
    "ussd.check_pin": "Andika PIN yako ya tarakimu 4:",
    "ussd.check_failed": "Kumbukumbu au PIN haitambuliki. Kwa msaada piga {emergency}",
    "ussd.status": "Ripoti {reference}: {status}",
    "ussd.status.NEW": "imepokelewa, inasubiri kutathminiwa na afisa.",
    "ussd.status.UNDER_REVIEW": "inakaguliwa na afisa aliyeidhinishwa.",
    "ussd.status.REFERRED": "imekaguliwa na kupelekwa kwa huduma inayohusika.",
}

LG = {
    "notif.CASE_UPDATE.title": "Amawulire amakulu",
    "notif.CASE_UPDATE.body": "Olina amawulire amakulu. Tukusaba otuukirire omukozi akuyamba.",
    "notif.APPOINTMENT_REMINDER.title": "Okujjukiza olunaku",
    "notif.APPOINTMENT_REMINDER.body": "Olina olunaku olutegekeddwa olujja. Tukusaba otuukirire omukozi akuyamba okufuna ebisingawo.",
    "notif.APPOINTMENT_SCHEDULED.title": "Olunaku lutegekeddwa",
    "notif.APPOINTMENT_SCHEDULED.body": "Olina olunaku olutegekeddwa olujja. Tukusaba otuukirire omukozi akuyamba okufuna ebisingawo.",
    "ussd.welcome": "TUKUSANYUKIDDE KU TULIWAMU\nLonda olulimi:",
    "ussd.main": "Londa:\n1. Loopa ensonga y'obukuumi bw'omwana\n2. Kebera alipoota etaliiko linnya\n3. Obuyambi obuliwo\n4. Fuluma",
    "ussd.invalid": "Ky'olonze tekituufu. Gezaako nate.",
    "ussd.exit": "Webale. Beera bulungi.",
    "ussd.danger": "Omwana ali mu kabi kati?\n1. Yee\n2. Nedda\n3. Simanyi",
    "ussd.confirm": "Weereza alipoota eno?\n1. Weereza\n2. Sazaamu",
    "ussd.cancelled": "Alipoota esaziddwamu. Tewali kyaterekeddwa.",
}

NYN = {
    "ussd.welcome": "TWAKUSIIMA KU TULIWAMU\nToorana orurimi:",
    "ussd.exit": "Webare.",
    "ussd.danger": "Omwana ari omu kabi hati?\n1. Eego\n2. Ngaaha\n3. Tindikumanya",
}

ACH = {
    "ussd.welcome": "WAJOLO I TULIWAMU\nYer leb:",
    "ussd.exit": "Apwoyo.",
    "ussd.danger": "Latin tye i peko kombedi?\n1. Eyo\n2. Pe\n3. Pe angeyo",
}

TEO = {
    "ussd.welcome": "IYALAMA KAMA TULIWAMU\nSeu akirep:",
    "ussd.exit": "Eyalama.",
}

CATALOG = {"en": EN, "sw": SW, "lg": LG, "nyn": NYN, "ach": ACH, "teo": TEO}


def t(key, lang="en", **kwargs):
    lang = lang if lang in CATALOG else "en"
    text = CATALOG[lang].get(key) or EN.get(key) or key
    if kwargs:
        names = {f for _, f, _, _ in Formatter().parse(text) if f}
        text = text.format(**{n: kwargs.get(n, "") for n in names})
    return text


def coverage():
    total = len(EN)
    return {
        lang: {
            "name": LANGUAGE_NAMES[lang],
            "translated_keys": len([k for k in CATALOG[lang] if k in EN]),
            "total_keys": total,
            "review_status": REVIEW_STATUS[lang],
        }
        for lang in SUPPORTED_LANGUAGES
    }
