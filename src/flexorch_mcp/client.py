from __future__ import annotations

from urllib.parse import urlparse
from typing import Any

import httpx

from .errors import FlexOrchAPIError, DownloadError, FileTooLargeError, map_api_error  # noqa: F401

_BASE_URL = "https://api.flexorch.com/v1"
_MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
_CHUNK_SIZE = 65536


def _mask_key(key: str) -> str:
    """Return dfx_xxx*** masked form for logs — never expose the full key."""
    if len(key) <= 7:
        return "***"
    return key[:7] + "***"


class FlexOrchMCPClient:
    """Async HTTP client for FlexOrch API calls within the MCP server.

    Keeps two httpx.AsyncClient instances:
    - _api: for FlexOrch API requests (carries X-API-KEY header)
    - _downloader: for external file_url downloads (no auth header)
    """

    def __init__(self, api_key: str, base_url: str = _BASE_URL) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._api = httpx.AsyncClient(
            headers={
                "X-API-KEY": api_key,
                "User-Agent": "flexorch-mcp/0.1.0",
            },
            timeout=httpx.Timeout(30.0, connect=5.0),
            max_redirects=3,
            verify=True,
        )
        self._downloader = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            max_redirects=3,
            verify=True,
            follow_redirects=True,
        )

    # ------------------------------------------------------------------
    # Core request helpers
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{self._base_url}/{path.lstrip('/')}"

    def _raise_for_response(self, response: httpx.Response) -> None:
        if not response.is_error:
            return
        retry_after: int | None = None
        error_code = ""
        try:
            body = response.json()
            error_code = body.get("error", {}).get("code", "")
        except Exception:
            pass
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
        raise FlexOrchAPIError(
            map_api_error(error_code, retry_after=retry_after),
            status_code=response.status_code,
            error_code=error_code,
            retry_after=retry_after,
        )

    def _parse(self, response: httpx.Response) -> Any:
        self._raise_for_response(response)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def get(self, path: str, **kwargs: Any) -> Any:
        response = await self._api.get(self._url(path), **kwargs)
        return self._parse(response)

    async def post(self, path: str, **kwargs: Any) -> Any:
        response = await self._api.post(self._url(path), **kwargs)
        return self._parse(response)

    async def get_raw(self, path: str, **kwargs: Any) -> tuple[bytes, str, str]:
        """Fetch binary/text response without JSON parsing.

        Returns (content_bytes, content_type, filename).
        Raises FlexOrchAPIError on HTTP errors.
        """
        response = await self._api.get(self._url(path), **kwargs)
        self._raise_for_response(response)
        content_type = response.headers.get("content-type", "application/octet-stream")
        cd = response.headers.get("content-disposition", "")
        filename = ""
        if 'filename="' in cd:
            filename = cd.split('filename="')[1].split('"')[0]
        elif "filename=" in cd:
            filename = cd.split("filename=")[1].split(";")[0].strip()
        return response.content, content_type, filename

    # ------------------------------------------------------------------
    # File download
    # ------------------------------------------------------------------

    async def download_file(self, url: str) -> tuple[bytes, str]:
        """Download a file from an external URL and return (bytes, filename).

        Validates scheme (http/https only) and enforces 50 MB size limit.
        """
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"Invalid URL scheme '{parsed.scheme}'. "
                "Only http and https URLs are supported."
            )

        chunks: list[bytes] = []
        total = 0

        async with self._downloader.stream("GET", url) as response:
            if response.is_error:
                raise DownloadError(
                    "Could not download file from provided URL. "
                    "Check that the URL is publicly accessible."
                )
            content_length = int(response.headers.get("content-length", 0))
            if content_length > _MAX_DOWNLOAD_BYTES:
                raise FileTooLargeError("File exceeds size limit. Max 50 MB.")

            async for chunk in response.aiter_bytes(_CHUNK_SIZE):
                total += len(chunk)
                if total > _MAX_DOWNLOAD_BYTES:
                    raise FileTooLargeError("File exceeds size limit. Max 50 MB.")
                chunks.append(chunk)

        content = b"".join(chunks)
        filename = (parsed.path.rstrip("/").split("/")[-1]) or "document"
        return content, filename

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def aclose(self) -> None:
        await self._api.aclose()
        await self._downloader.aclose()

    async def __aenter__(self) -> FlexOrchMCPClient:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    def masked_key(self) -> str:
        return _mask_key(self._api_key)
