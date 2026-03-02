"""AES decryption for CryptoJS-encrypted request payloads."""
import base64
import hashlib
import json

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from config import settings


def decrypt_payload(encrypted_data: str) -> dict:
    """
    Decrypt an AES-encrypted payload produced by CryptoJS on the frontend.
    CryptoJS uses the OpenSSL-compatible "Salted__" prefix format.

    Dev convenience: if the value is plain JSON (not base64-encoded CryptoJS
    output) it is accepted as-is so the API can be exercised from Swagger /
    curl without a running frontend.  Production traffic is always encrypted.
    """
    stripped = encrypted_data.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)

    raw = base64.b64decode(encrypted_data)

    if raw[:8] != b"Salted__":
        raise ValueError("Invalid encrypted data format")

    salt = raw[8:16]
    ciphertext = raw[16:]

    key, iv = _evp_bytes_to_key(settings.ENCRYPTION_KEY.encode(), salt, 32, 16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)

    return json.loads(decrypted.decode("utf-8"))


def _evp_bytes_to_key(
    password: bytes, salt: bytes, key_len: int, iv_len: int
) -> tuple[bytes, bytes]:
    """OpenSSL EVP_BytesToKey — used by CryptoJS for password-based encryption."""
    dtot = b""
    d = b""
    while len(dtot) < key_len + iv_len:
        d = hashlib.md5(d + password + salt).digest()
        dtot += d
    return dtot[:key_len], dtot[key_len : key_len + iv_len]
