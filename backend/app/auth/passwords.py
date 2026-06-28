"""Password hashing with argon2id.

One ``PasswordHasher`` on argon2-cffi defaults (time_cost=3, memory_cost=64
MiB, parallelism=4), above the OWASP minimum at roughly 50 ms per hash, so no
custom tuning.
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Return an argon2id hash for the given password."""
    return _hasher.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    """Verify a password against a stored hash.

    A mismatch or a corrupt stored hash is treated as a rejected login, not a
    server error, so a damaged database value cannot turn login into a 500.
    """
    try:
        _hasher.verify(stored_hash, password)
        return True
    except (VerificationError, InvalidHashError):
        return False
