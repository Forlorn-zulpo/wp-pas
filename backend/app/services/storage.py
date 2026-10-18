import os
import uuid
from pathlib import Path

from app.core.config import settings


class StorageService:
    """Minimal interface any backend (local disk now, S3 later) must satisfy.
    Only two operations are needed by the asset pipeline so far: write bytes
    under a generated key, and delete by key."""

    def save(self, content: bytes, *, extension: str) -> str:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def path_for(self, key: str) -> str:
        raise NotImplementedError


class LocalDiskStorage(StorageService):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _full_path(self, key: str) -> Path:
        # key is always a flat generated uuid filename — never derived from
        # user input — so there is no path-traversal surface here.
        return self.base_path / key

    def save(self, content: bytes, *, extension: str) -> str:
        key = f"{uuid.uuid4().hex}{extension}"
        full_path = self._full_path(key)
        full_path.write_bytes(content)
        return key

    def delete(self, key: str) -> None:
        full_path = self._full_path(key)
        if full_path.exists():
            os.remove(full_path)

    def path_for(self, key: str) -> str:
        return str(self._full_path(key))


def get_storage_service() -> StorageService:
    # Swap point for Phase 5+: if S3 credentials are configured, return an
    # S3-backed implementation here instead. Nothing above this function
    # needs to change.
    return LocalDiskStorage(settings.LOCAL_STORAGE_PATH)
