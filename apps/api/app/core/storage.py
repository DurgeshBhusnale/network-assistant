"""Supabase Storage via its REST API with the service key (server only, never the browser)."""

import httpx

from app.core.config import Settings


class StorageError(RuntimeError):
    pass


class Storage:
    def __init__(self, settings: Settings) -> None:
        key = (
            settings.supabase_service_role_key.get_secret_value()
            if settings.supabase_service_role_key
            else ""
        )
        self._base = f"{settings.supabase_url}/storage/v1"
        self._headers = {"Authorization": f"Bearer {key}", "apikey": key}
        self.bucket = settings.storage_bucket_captures

    async def signed_upload_url(self, path: str) -> str:
        """A one-time URL the browser PUTs the file to (expires after 2 hours on Supabase)."""
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{self._base}/object/upload/sign/{self.bucket}/{path}", headers=self._headers
            )
        if r.status_code >= 300:
            raise StorageError(f"sign upload failed: {r.status_code}")
        return f"{self._base}{r.json()['url']}"

    async def download(self, path: str, max_bytes: int) -> tuple[bytes, str]:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(f"{self._base}/object/{self.bucket}/{path}", headers=self._headers)
        if r.status_code >= 300:
            raise StorageError(f"download failed: {r.status_code}")
        if len(r.content) > max_bytes:
            raise StorageError("file too large")
        return r.content, r.headers.get("content-type", "audio/webm")

    async def delete(self, paths: list[str]) -> None:
        if not paths:
            return
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.request(
                "DELETE",
                f"{self._base}/object/{self.bucket}",
                headers=self._headers,
                json={"prefixes": paths},
            )
        if r.status_code >= 300:
            raise StorageError(f"delete failed: {r.status_code}")
