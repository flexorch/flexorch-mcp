"""SSRF guard for the file_url download path.

document.process's file_url is fetched by this MCP server process, in its
own network context (separate from the main flexorch API container) — an
unvalidated URL/hostname here could reach internal services or cloud
metadata endpoints reachable from wherever this server runs. Mirrors the
platform's app/core/ssrf_guard.py.
"""
import ipaddress
import socket

from .errors import DownloadError


def reject_private_target(hostname: str | None) -> None:
    """Resolve hostname and reject any address that isn't publicly routable."""
    if not hostname:
        raise DownloadError("URL must include a hostname.")

    try:
        addrinfo = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise DownloadError("Could not resolve the file URL's hostname.")

    for family, _, _, _, sockaddr in addrinfo:
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise DownloadError(
                "The file URL resolves to a non-public address and cannot be downloaded."
            )
