"""Random, non-sequential human-facing references (no ambiguous characters)."""
import secrets

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def random_code(length=6):
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def unique_reference(model, field, prefix, length=6, attempts=20):
    for _ in range(attempts):
        candidate = f"{prefix}-{random_code(length)}"
        if not model.objects.filter(**{field: candidate}).exists():
            return candidate
    raise RuntimeError("Could not generate a unique reference")
