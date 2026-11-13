"""Encryption at rest for the Navidrome password."""

from __future__ import annotations

import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class SecretBox:
    def __init__(self, app_secret_key: str) -> None:
        key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"casthome-credentials",
            info=b"navidrome-password",
        ).derive(app_secret_key.encode())
        self._fernet = Fernet(base64.urlsafe_b64encode(key))

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode())

    def decrypt(self, token: bytes) -> str | None:
        """Return None when the key changed or the data is corrupt."""
        try:
            return self._fernet.decrypt(token).decode()
        except InvalidToken:
            return None
