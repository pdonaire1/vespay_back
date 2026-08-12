import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

_NONCE_SIZE = 12


def _get_key() -> bytes:
    key = getattr(settings, "VESPAY_ENCRYPTION_KEY", "")
    if not key:
        raise ValueError("VESPAY_ENCRYPTION_KEY no está configurada")
    try:
        return base64.urlsafe_b64decode(key.encode("ascii"))
    except Exception as exc:
        raise ValueError("VESPAY_ENCRYPTION_KEY no es base64 válida") from exc


def encrypt_field(plaintext: str) -> str:
    key = _get_key()
    nonce = os.urandom(_NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_field(payload: str) -> str:
    key = _get_key()
    raw = base64.urlsafe_b64decode(payload.encode("ascii"))
    nonce, ciphertext = raw[:_NONCE_SIZE], raw[_NONCE_SIZE:]
    return AESGCM(key).decrypt(nonce, ciphertext, None).decode("utf-8")
