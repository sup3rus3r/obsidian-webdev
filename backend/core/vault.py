"""Fernet-based secrets vault utilities.

Key derivation strategy:
  - One FERNET_MASTER_KEY for the whole application (env var).
  - A unique Fernet key is derived per user via PBKDF2-HMAC-SHA256.
  - Rotating the master key requires re-encrypting all secrets (use key_version for future rotation).

The encrypted value (Fernet token) is safe to store in the database — it is
self-authenticating (includes HMAC) and cannot be decrypted without the master key.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status

from config import settings

CURRENT_KEY_VERSION = 1


def _require_master_key() -> None:
    if not settings.FERNET_MASTER_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vault is not configured. Set FERNET_MASTER_KEY in the environment.",
        )


def _derive_key(user_id: str, version: int = CURRENT_KEY_VERSION) -> Fernet:
    """Derive a per-user Fernet key from the app master key using PBKDF2."""
    salt = f"webdev-ai:vault:{user_id}:v{version}".encode()
    key_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        settings.FERNET_MASTER_KEY.encode(),
        salt,
        iterations=100_000,
        dklen=32,
    )
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def encrypt_secret(user_id: str, plaintext: str, version: int = CURRENT_KEY_VERSION) -> str:
    """Encrypt a plaintext secret for a given user. Returns a Fernet token string."""
    _require_master_key()
    return _derive_key(user_id, version).encrypt(plaintext.encode()).decode()


def decrypt_secret(user_id: str, ciphertext: str, version: int = CURRENT_KEY_VERSION) -> str:
    """Decrypt a Fernet token back to plaintext. Raises 422 on tampered/wrong-key data."""
    _require_master_key()
    try:
        return _derive_key(user_id, version).decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to decrypt secret — token is invalid or the master key has changed.",
        )
