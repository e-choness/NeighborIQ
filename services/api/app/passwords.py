"""
Password hashing: Argon2id for new hashes; bcrypt hashes from earlier releases
are still accepted and upgraded to Argon2id on the next successful login.

Earlier releases hashed with passlib + bcrypt, which silently used only the first
72 bytes of a password. Legacy verification keeps that behaviour so existing
accounts can always sign in (bcrypt >= 5 raises on longer input instead).
"""

import bcrypt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

_argon2 = PasswordHash((Argon2Hasher(),))
_BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")


def hash_password(password: str) -> str:
    return _argon2.hash(password)


def verify_password(password: str, hashed: str) -> tuple[bool, str | None]:
    """Return (matches, new_hash). new_hash is set when the stored hash should be replaced."""
    if hashed.startswith(_BCRYPT_PREFIXES):
        ok = bcrypt.checkpw(password.encode()[:72], hashed.encode())
        return ok, (hash_password(password) if ok else None)
    return _argon2.verify_and_update(password, hashed)
