"""SSRF guard for document.process's file_url — this MCP server downloads
the URL itself, in its own network context, before forwarding the content
to the platform. Regression: only the URL scheme (http/https) was checked;
a tenant could point file_url at an internal/private address (or a public
URL that redirects to one) with no hostname validation at all.
"""
from __future__ import annotations

import socket

import httpx
import pytest
import respx

from flexorch_mcp import ssrf_guard
from flexorch_mcp.client import FlexOrchMCPClient
from flexorch_mcp.errors import DownloadError

_TEST_KEY = "dfx_testkey_000000000"


@pytest.fixture
def client():
    return FlexOrchMCPClient(_TEST_KEY)


def _fake_public_dns(monkeypatch):
    monkeypatch.setattr(
        ssrf_guard.socket, "getaddrinfo",
        lambda *a, **kw: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )


def _fake_private_dns(monkeypatch, ip="10.0.0.5"):
    monkeypatch.setattr(
        ssrf_guard.socket, "getaddrinfo",
        lambda *a, **kw: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))],
    )


@pytest.mark.asyncio
async def test_download_rejects_private_target(client, monkeypatch):
    _fake_private_dns(monkeypatch)
    with pytest.raises(DownloadError, match="non-public"):
        await client.download_file("https://internal.example.com/file.pdf")


@pytest.mark.asyncio
async def test_download_rejects_link_local_metadata(client, monkeypatch):
    """169.254.169.254-style addresses are how cloud metadata endpoints are reached."""
    _fake_private_dns(monkeypatch, ip="169.254.169.254")
    with pytest.raises(DownloadError, match="non-public"):
        await client.download_file("https://metadata.example.com/file.pdf")


@pytest.mark.asyncio
async def test_download_allows_public_target(client, monkeypatch):
    _fake_public_dns(monkeypatch)
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://public.example.com/file.pdf").mock(
            return_value=httpx.Response(200, content=b"hello", headers={"Content-Type": "text/plain"})
        )
        content, filename = await client.download_file("https://public.example.com/file.pdf")
    assert content == b"hello"


@pytest.mark.asyncio
async def test_download_rejects_redirect_to_private_target(client, monkeypatch):
    """Public IP on the first hop, private IP after a redirect — the request
    event hook must re-check on every hop, not just the URL the caller
    originally supplied."""
    calls = {"n": 0}

    def _dns(*a, **kw):
        calls["n"] += 1
        ip = "93.184.216.34" if calls["n"] == 1 else "10.0.0.5"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

    monkeypatch.setattr(ssrf_guard.socket, "getaddrinfo", _dns)

    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://public.example.com/file.pdf").mock(
            return_value=httpx.Response(302, headers={"Location": "https://internal.example.com/secret"})
        )
        mock.get("https://internal.example.com/secret").mock(
            return_value=httpx.Response(200, content=b"leaked")
        )
        with pytest.raises(DownloadError, match="non-public"):
            await client.download_file("https://public.example.com/file.pdf")
