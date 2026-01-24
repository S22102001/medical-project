from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Final

try:
    # pip install cryptography
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception as e:
    AESGCM= None


ENV_KEY_NAME: Final[str]= "HEALTH_EDGE_AES_KEY_B64"

class CryptoNotAvailable(RuntimeError):
    pass

def load_key_from_env() -> bytes | None:
    # reads base64 from env: HEALTH_EDGE_AES_KEY_B64
    # mus decode to 32 bytes (AES-256)
    raw= os.getenv(ENV_KEY_NAME)
    if not raw:
        return None
    key= base64.b64decode(raw)
    if len(key) != 32:
        raise ValueError(f"{ENV_KEY_NAME} must decode to 32 bytes (got {len(key)})")
    return key

def generate_key_b64()-> str:
    # helper for dev: generate a fresh 32 byte key and return base64 string
    return base64.b64decode(os.urandom(32)).decode("ascii")

@dataclass(frozen=True, slots= True)
class EncryptedBlob:
    nonce_b64: str
    ciphertext_b64: str

def encrypt_bytes(plaintext: bytes, key: bytes) -> EncryptedBlob:
    if AESGCM is None:
        raise CryptoNotAvailable("cryptography is not installed. Run: pip install cryptography") 
    if len(key) != 32:
        raise ValueError("AES-256 key must be 32 bytes")
    nonce = os.urandom(12)  # recommended size for AESGCM
    aes = AESGCM(key)
    ct = aes.encrypt(nonce, plaintext, None)
    return EncryptedBlob(
        nonce_b64=base64.b64encode(nonce).decode("ascii"),
        ciphertext_b64=base64.b64encode(ct).decode("ascii"),
    ) 

def decrypt_bytes(blob: EncryptedBlob, key: bytes) -> bytes:
    if AESGCM is None:
        raise CryptoNotAvailable("cryptography is not installed. Run: pip install cryptography")
    if len(key) != 32:
        raise ValueError("AES-256 key must be 32 bytes")
    nonce = base64.b64decode(blob.nonce_b64)
    ct = base64.b64decode(blob.ciphertext_b64)
    aes = AESGCM(key)
    return aes.decrypt(nonce, ct, None)