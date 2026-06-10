import re

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from backend.common.errors import AppError

# 64 MB RAM per attempt — makes GPU brute-force expensive (each GPU core has little RAM)
_ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)

_MIN_LEN = 12
_STRENGTH_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*]).{12,}$"
)


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def check_password_strength(plain: str) -> None:
    if len(plain) < _MIN_LEN:
        raise AppError(
            "WEAK_PASSWORD",
            f"Password must be at least {_MIN_LEN} characters.",
            422,
        )
    if not _STRENGTH_RE.match(plain):
        raise AppError(
            "WEAK_PASSWORD",
            "Password must contain uppercase, lowercase, a digit, and a special character (!@#$%^&*).",
            422,
        )
