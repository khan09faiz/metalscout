"""Network boundary: domain helpers, public-host check, robots.txt cache."""
from __future__ import annotations

import functools
import ipaddress
import socket
import urllib.robotparser
from urllib.parse import urljoin, urlparse

import httpx
import tldextract

from . import __version__

# Our crawler identity: sent with robots.txt fetches and matched against robots.txt rules (`crawl.user_agent`).
BOT_UA = f"MetalScoutBot/{__version__} (+https://github.com/khan09faiz/metalscout)"
# What a desktop Chrome sends; the browser context uses it with BOT_UA appended (`crawl.browser_user_agent`).
CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
UA = BOT_UA  # backwards-compatible name


def user_agents(cfg: dict) -> tuple[str, str]:
    """(bot UA for robots.txt + httpx, UA for the Playwright context) from cfg["crawl"]."""
    c = cfg.get("crawl", {})
    bot = str(c.get("user_agent") or BOT_UA)
    return bot, str(c.get("browser_user_agent") or f"{CHROME_UA} {bot}")
_tld = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)  # offline bundled list; no cache writes (read-only hosts)


def reg_domain(url: str) -> str:
    e = _tld(url)
    return f"{e.domain}.{e.suffix}".lower() if e.suffix else (e.domain or urlparse(url).hostname or "").lower()


def homepage(url: str) -> str:
    """scheme://host[:port]/ of a URL: where a company crawl should start (not a deep search-hit page)."""
    p = urlparse(url if "://" in url else "https://" + url)
    return f"{p.scheme or 'https'}://{p.netloc.rsplit('@', 1)[-1].lower()}/"


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
    def __init__(self, allow_private: bool = False, ua: str = BOT_UA):
        self.allow_private, self.ua = allow_private, ua
        self.cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def _ok(self, url: str) -> bool:
        return self.allow_private or is_public(url)

    async def _fetch(self, url: str) -> urllib.robotparser.RobotFileParser | None:
        """Parsed robots.txt, or None when a redirect leads to a non-public host (then nothing is allowed).
        Redirects are followed by hand so every hop is checked *before* it is requested."""
        rp = urllib.robotparser.RobotFileParser()
        try:
            async with httpx.AsyncClient(timeout=8, headers={"User-Agent": self.ua}, follow_redirects=False) as c:
                for _ in range(5):
                    if not self._ok(url):
                        return None
                    r = await c.get(url)
                    if r.is_redirect and r.headers.get("location"):
                        url = urljoin(url, r.headers["location"])
                        continue
                    rp.parse(r.text.splitlines() if r.status_code == 200 else [])
                    return rp
        except Exception:  # noqa: S110  # unreachable robots.txt: falls through to 'no rules'
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
        return rp is not None and rp.can_fetch(self.ua, url)  # rules match on the first token: "MetalScoutBot"
