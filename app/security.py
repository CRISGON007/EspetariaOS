from __future__ import annotations

import hashlib
import hmac
import secrets


def new_salt() -> str:
    return secrets.token_hex(16)


def hash_password(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        210_000,
    )
    return derived.hex()


def verify_password(password: str, salt_hex: str, expected_hash: str) -> bool:
    actual = hash_password(password, salt_hex)
    return hmac.compare_digest(actual, expected_hash)


def new_token() -> str:
    return secrets.token_urlsafe(48)
