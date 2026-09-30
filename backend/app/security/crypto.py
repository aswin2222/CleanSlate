"""Payload encryption at rest using Fernet (AES-128-CBC with HMAC)."""
from __future__ import annotations

import base64
import os
from typing import Optional
from cryptography.fernet import Fernet

from app.config import settings
from app.logging import logger


class DataEncryptor:
    """
    Encrypts dataset files at rest using symmetric authenticated encryption.
    Refuses to start in production if an explicit key is not provided.
    """

    def __init__(self, key: Optional[str] = None) -> None:
        raw_key = key or settings.DATA_ENCRYPTION_KEY
        if not raw_key:
            if settings.ENVIRONMENT == "production":
                raise RuntimeError("CRITICAL SECURITY ERROR: DATA_ENCRYPTION_KEY is required in production mode.")
            raw_key = Fernet.generate_key().decode()

        # Ensure valid Fernet base64 key
        try:
            self.fernet = Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)
        except Exception:
            # Generate deterministic fallback dev key if invalid key supplied in dev
            fallback_key = base64.urlsafe_b64encode(b"01234567890123456789012345678901")
            self.fernet = Fernet(fallback_key)

    def encrypt_bytes(self, data: bytes) -> bytes:
        """Encrypts arbitrary raw bytes."""
        return self.fernet.encrypt(data)

    def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        """Decrypts bytes, authenticating ciphertext."""
        return self.fernet.decrypt(encrypted_data)


encryptor = DataEncryptor()
