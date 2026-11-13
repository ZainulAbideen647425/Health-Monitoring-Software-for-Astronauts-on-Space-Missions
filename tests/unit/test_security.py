import pytest

from astronaut_health_monitor.core.security import (
    MINIMUM_PASSWORD_LENGTH,
    generate_session_token,
    hash_password,
    hash_session_token,
    validate_password_strength,
    verify_password,
)
from astronaut_health_monitor.domain.exceptions import InvalidUserDetailsError


def test_correct_password_verifies_and_wrong_password_does_not() -> None:
    stored = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", stored)
    assert not verify_password("correct horse battery stapl", stored)
    assert not verify_password("", stored)


def test_hash_does_not_contain_the_password_and_uses_a_new_salt_each_time() -> None:
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")
    assert "correct" not in first
    assert first != second
    assert first.startswith("scrypt$")


@pytest.mark.parametrize("broken_hash", ["", "plain-text", "md5$1$2$3$4$5", "scrypt$x$y$z$a$b", "scrypt$1$2"])
def test_malformed_stored_hash_simply_fails(broken_hash: str) -> None:
    assert verify_password("anything at all", broken_hash) is False


def test_password_strength_rules() -> None:
    assert MINIMUM_PASSWORD_LENGTH == 8
    validate_password_strength("Abcdef-1")
    validate_password_strength("Abcdefg h")
    with pytest.raises(InvalidUserDetailsError, match="at least 8"):
        validate_password_strength("Ab-1xyz")
    with pytest.raises(InvalidUserDetailsError, match="uppercase"):
        validate_password_strength("abcdef-1")
    with pytest.raises(InvalidUserDetailsError, match="lowercase"):
        validate_password_strength("ABCDEF-1")
    with pytest.raises(InvalidUserDetailsError, match="special"):
        validate_password_strength("Abcdefg1")
    with pytest.raises(InvalidUserDetailsError, match="different characters"):
        validate_password_strength("Aa-" + "a" * 8)


def test_session_tokens_are_random_and_only_their_hash_is_kept() -> None:
    first, second = generate_session_token(), generate_session_token()
    assert first != second and len(first) >= 40
    assert hash_session_token(first) != first
    assert hash_session_token(first) == hash_session_token(first)
    assert len(hash_session_token(first)) == 64
