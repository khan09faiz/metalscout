"""Network boundary: domain helpers, public-host check, robots.txt cache."""
from __future__ import annotations

import functools
import ipaddress
import socket
import urllib.robotparser
from urllib.parse import urljoin, urlparse

import httpx
import tldextract

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
_tld = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)  # offline bundled list; no cache writes (read-only hosts)


def reg_domain(url: str) -> str:
    e = _tld(url)
    return f"{e.domain}.{e.suffix}".lower() if e.suffix else (e.domain or urlparse(url).hostname or "").lower()


def host_matches(url_or_domain: str, domains) -> bool:
    d = reg_domain(url_or_domain) if "/" in url_or_domain else url_or_domain.lower()
    return any(d == x or d.endswith("." + x) for x in domains)


@functools.lru_cache(maxsize=4096)
def host_is_public(host: str) -> bool:
    """True only if every address the host resolves to is public. Cached per host for the process."""
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(str(info[4][0]).split("%")[0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
                or ip.is_unspecified or not ip.is_global):
            return False
    return True


def is_public(url: str) -> bool:
    """Reject private, loopback, link-local and metadata addresses (SSRF guard for crawled links)."""
    return host_is_public((urlparse(url).hostname or "").lower())


class Robots:
    def __init__(self, allow_private: bool = False):
        self.allow_private = allow_private
        self.cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def _ok(self, url: str) -> bool:
        return self.allow_private or is_public(url)

    async def _fetch(self, url: str) -> urllib.robotparser.RobotFileParser | None:
        """Parsed robots.txt, or None when a redirect leads to a non-public host (then nothing is allowed).
        Redirects are followed by hand so every hop is checked *before* it is requested."""
        rp = urllib.robotparser.RobotFileParser()
        try:
            async with httpx.AsyncClient(timeout=8, headers={"User-Agent": UA}, follow_redirects=False) as c:
                for _ in range(5):
                    if not self._ok(url):
                        return None
                    r = await c.get(url)
                    if r.is_redirect and r.headers.get("location"):
                        url = urljoin(url, r.headers["location"])
                        continue
                    rp.parse(r.text.splitlines() if r.status_code == 200 else [])
                    return rp
        except Exception:
            pass
        rp.parse([])
        return rp

    async def allowed(self, url: str) -> bool:
        if not self._ok(url):
            return False
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        if base not in self.cache:
            self.cache[base] = await self._fetch(base + "/robots.txt")
        rp = self.cache[base]
        return rp is not None and rp.can_fetch(UA, url)
