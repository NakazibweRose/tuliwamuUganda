"""Encrypted text field (Fernet / AES-128-CBC + HMAC) for the most sensitive free text.

The key comes from settings.FIELD_ENCRYPTION_KEY. In development, if no key is set, a key is
derived from SECRET_KEY so the app still runs; production deployments must set a dedicated key
(and keep it out of the database backups' storage location).
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models

_PREFIX = "enc1:"


def _fernet():
    key = settings.FIELD_ENCRYPTION_KEY
    if not key:
        digest = hashlib.sha256(("tuliwamu-field-key:" + settings.SECRET_KEY).encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(value):
    if value in (None, ""):
        return value
    return _PREFIX + _fernet().encrypt(str(value).encode()).decode()


def decrypt_value(value):
    if value in (None, "") or not str(value).startswith(_PREFIX):
        return value
    try:
        return _fernet().decrypt(value[len(_PREFIX):].encode()).decode()
    except InvalidToken:
        return "[unreadable: encryption key mismatch]"


class EncryptedTextField(models.TextField):
    """TextField that is transparently encrypted in the database. Not searchable."""

    def from_db_value(self, value, expression, connection):
        return decrypt_value(value)

    def to_python(self, value):
        return decrypt_value(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt_value(value)
