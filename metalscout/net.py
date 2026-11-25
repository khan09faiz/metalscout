"""Network boundary: domain helpers, public-host check, robots.txt cache."""
from __future__ import annotations

import ipaddress
import socket
import urllib.robotparser
from urllib.parse import urlparse

import httpx
import tldextract

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
_tld = tldextract.TLDExtract(suffix_list_urls=())  # offline: bundled suffix list, no network at import


def reg_domain(url: str) -> str:
    e = _tld(url)
    return f"{e.domain}.{e.suffix}".lower() if e.suffix else (e.domain or urlparse(url).hostname or "").lower()


def host_matches(url_or_domain: str, domains) -> bool:
    d = reg_domain(url_or_domain) if "/" in url_or_domain else url_or_domain.lower()
    return any(d == x or d.endswith("." + x) for x in domains)


def is_public(url: str) -> bool:
    """Reject private, loopback, link-local and metadata addresses (SSRF guard for crawled links)."""
    host = urlparse(url).hostname
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


class Robots:
    def __init__(self):
        self.cache: dict[str, urllib.robotparser.RobotFileParser] = {}

    async def allowed(self, url: str) -> bool:
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        if base not in self.cache:
            rp = urllib.robotparser.RobotFileParser()
            try:
                async with httpx.AsyncClient(timeout=8, headers={"User-Agent": UA}, follow_redirects=True) as c:
                    r = await c.get(base + "/robots.txt")
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except Exception:
                rp.parse([])
            self.cache[base] = rp
        return self.cache[base].can_fetch(UA, url)
