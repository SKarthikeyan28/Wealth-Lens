import pytest

from backend.auth.security import check_password_strength, hash_password, verify_password
from backend.common.errors import AppError

STRONG = "Str0ng!Pass#99"


def test_hash_is_not_plain() -> None:
    assert hash_password(STRONG) != STRONG


def test_verify_correct_password() -> None:
    hashed = hash_password(STRONG)
    assert verify_password(STRONG, hashed) is True


def test_verify_wrong_password() -> None:
    hashed = hash_password(STRONG)
    assert verify_password("wrong", hashed) is False


def test_verify_tampered_hash() -> None:
    assert verify_password(STRONG, "not-a-hash") is False


def test_strength_too_short() -> None:
    with pytest.raises(AppError) as exc:
        check_password_strength("short")
    assert exc.value.code == "WEAK_PASSWORD"


def test_strength_no_special_char() -> None:
    with pytest.raises(AppError) as exc:
        check_password_strength("NoSpecialChar1234")
    assert exc.value.code == "WEAK_PASSWORD"


def test_strength_no_digit() -> None:
    with pytest.raises(AppError) as exc:
        check_password_strength("NoDigitHere!!")
    assert exc.value.code == "WEAK_PASSWORD"


def test_strong_password_passes() -> None:
    check_password_strength(STRONG)  # must not raise
