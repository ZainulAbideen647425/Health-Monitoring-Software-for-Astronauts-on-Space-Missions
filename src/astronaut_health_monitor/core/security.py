"""Password hashing and session token helpers. Uses only the Python standard library."""

import base64
import hashlib
import hmac
import secrets

from astronaut_health_monitor.domain.exceptions import InvalidUserDetailsError

SCRYPT_COST = 2**14
SCRYPT_BLOCK_SIZE = 8
SCRYPT_PARALLELISM = 1
HASH_LENGTH_BYTES = 32
SALT_LENGTH_BYTES = 16
MINIMUM_PASSWORD_LENGTH = 8


def validate_password_strength(password: str) -> None:
    """Reject passwords that are too short, miss a required kind of character, or are too repetitive."""
    if len(password) < MINIMUM_PASSWORD_LENGTH:
        raise InvalidUserDetailsError(f"Password must be at least {MINIMUM_PASSWORD_LENGTH} characters long.")
    if not any(character.isupper() for character in password):
        raise InvalidUserDetailsError("Password must contain an uppercase letter.")
    if not any(character.islower() for character in password):
        raise InvalidUserDetailsError("Password must contain a lowercase letter.")
    if all(character.isalnum() for character in password):
        raise InvalidUserDetailsError("Password must contain a special character, for example ! @ # - _ or a space.")
    if len(set(password)) < 5:
        raise InvalidUserDetailsError("Password must use at least five different characters.")


def _derive_hash(password: str, salt: bytes, cost: int, block_size: int, parallelism: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=cost,
        r=block_size,
        p=parallelism,
        dklen=HASH_LENGTH_BYTES,
        maxmem=64 * 1024 * 1024,
    )


def hash_password(password: str) -> str:
    """Return 'scrypt$cost$block$parallelism$salt$hash' so the settings travel with the hash."""
    salt = secrets.token_bytes(SALT_LENGTH_BYTES)
    derived = _derive_hash(password, salt, SCRYPT_COST, SCRYPT_BLOCK_SIZE, SCRYPT_PARALLELISM)
    return "$".join(
        [
            "scrypt",
            str(SCRYPT_COST),
            str(SCRYPT_BLOCK_SIZE),
            str(SCRYPT_PARALLELISM),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(derived).decode("ascii"),
        ]
    )


def verify_password(password: str, stored_hash: str) -> bool:
    """Check a password in constant time. A malformed stored hash simply fails."""
    try:
        algorithm, cost, block_size, parallelism, salt_text, hash_text = stored_hash.split("$")
        if algorithm != "scrypt":
            return False
        expected = base64.b64decode(hash_text)
        actual = _derive_hash(password, base64.b64decode(salt_text), int(cost), int(block_size), int(parallelism))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def generate_session_token() -> str:
    """A long random token. Only its hash is ever stored on the server."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
