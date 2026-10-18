import json

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_fernet = Fernet(settings.CREDENTIALS_ENCRYPTION_KEY.encode())


def encrypt_credentials(credentials: dict) -> str:
    """Site access credentials (API keys, consumer secrets, app passwords)
    must never be stored in plaintext — encrypt before the row is written."""
    raw = json.dumps(credentials).encode()
    return _fernet.encrypt(raw).decode()


def decrypt_credentials(token: str) -> dict:
    try:
        raw = _fernet.decrypt(token.encode())
    except InvalidToken as exc:
        raise ValueError("无法解密站点凭据,密钥可能已更换") from exc
    return json.loads(raw)
