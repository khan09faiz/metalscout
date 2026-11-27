"""Headless-Chromium site surfer (Playwright).

Opens a site the way a person would: homepage first, then the site's own links by priority
(contact > about > products > infrastructure > vendor/tender), clicks "Next" pagination,
scrolls lazy content. Same-site only, robots.txt respected, polite delays, per-site timeout.
No CAPTCHA solving: a challenge page is reported, not bypassed.
"""
from __future__ import annotations

import asyncio
import random
import re
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright
from selectolax.lexbor import LexborHTMLParser

from . import net
from .net import Robots, reg_domain, user_agents

PRIORITY = [(r"contact|reach-?us|get-?in-?touch", 100), (r"about|company|profile|who-?we-?are|overview", 80),
            (r"product|industr|application|sector|customer|client|range", 60),
            (r"infrastructure|facilit|plant|capacity|quality|certif|machin", 55),
            (r"vendor|supplier|tender|procure|rfq|enquir|purchase", 50)]
SKIP = re.compile(r"\.(pdf|jpe?g|png|gif|webp|zip|rar|docx?|xlsx?|pptx?|mp4|mp3)(\?|$)|/(login|signin|cart|checkout|wp-admin|wp-json|feed)\b"
                  r"|privacy|terms-|cookie|javascript:|whatsapp|share", re.I)
NEXT = re.compile(r"^(next|next page|›|»|>|more|load more)$", re.I)


def _links(html: str, base: str):
    out = []
    for a in LexborHTMLParser(html).css("a[href]"):
        href = (a.attributes.get("href") or "").strip()
        if not href or href.startswith(("mailto:", "tel:", "#")):
            continue
        out.append((urljoin(base, href).split("#")[0], (a.text(strip=True) or "")[:80]))
    return out


def _priority(href: str, label: str) -> int:
    best = 0
    for pat, w in PRIORITY:
        if re.search(pat, href, re.I) or re.search(pat, label, re.I):
            best = max(best, w)
    return best


async def _snapshot(page):
    for _ in range(4):
        try:
            await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(200)
        except Exception:
            break
    text = await page.evaluate("document.body ? document.body.innerText : ''")
    return page.url, text or "", await page.content()


class Surfer:
    """Async context manager owning one browser; crawl many sites with bounded concurrency."""

    def __init__(self, cfg: dict):
        self.cfg = cfg["crawl"]
        self.bot_ua, self.browser_ua = user_agents(cfg)
        self.robots = Robots(allow_private=bool(self.cfg.get("allow_private_hosts")), ua=self.bot_ua)
        self._pw = self._browser = self._ctx = None

    async def __aenter__(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=True)
        self._ctx = await self._browser.new_context(user_agent=self.browser_ua, locale="en-IN", viewport={"width": 1366, "height": 900})
        return self

    async def __aexit__(self, *exc):
        await self._browser.close()
        await self._pw.stop()

    async def _route(self, route) -> None:
        """Every request the page makes: drop heavy media, and (SSRF) anything aimed at a non-public host.
        Playwright calls this only for the first URL of a redirect chain, so callers also check page.url."""
        req = route.request
        if req.resource_type in ("image", "media", "font"):
            return await route.abort()
        u = urlparse(req.url)
        if (u.scheme in ("http", "https", "ws", "wss") and not self.cfg.get("allow_private_hosts")
                and not await asyncio.to_thread(net.host_is_public, (u.hostname or "").lower())):
            return await route.abort("blockedbyclient")
        await route.continue_()

    async def _new_page(self):
        page = await self._ctx.new_page()
        await page.route("**/*", self._route)
        return page

    def _ok_host(self, url: str) -> bool:
        return bool(self.cfg.get("allow_private_hosts")) or net.is_public(url)

    async def open(self, url: str) -> dict | None:
        """Open a single page (used for buyer-signal pages)."""
        if not self._ok_host(url) or not await self.robots.allowed(url):
            return None
        page = await self._new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            if not self._ok_host(page.url):  # redirected to a private host: discard
                return None
            await page.wait_for_timeout(500)
            final, text, html = await _snapshot(page)
            return {"url": final, "text": text, "html": html}
        except Exception:
            return None
        finally:
            await page.close()

    async def crawl(self, seed: str) -> list[dict]:
        """Best-first same-site crawl. On timeout, returns the pages read so far."""
        pages: list[dict] = []
        try:
            await asyncio.wait_for(self._crawl(seed, pages), timeout=self.cfg["site_timeout_s"])
        except asyncio.TimeoutError:
            pass
        return pages

    async def _crawl(self, seed: str, pages: list[dict]) -> None:
        c = self.cfg
        dom = reg_domain(seed)
        seen: set[str] = set()
        queue = [(1000, 0, seed)]
        pagination_budget = 3
        if not self._ok_host(seed):
            return
        page = await self._new_page()
        try:
            while queue and len(pages) < c["max_pages"]:
                queue.sort(key=lambda t: -t[0])
                _, depth, url = queue.pop(0)
                if url in seen:
                    continue
                seen.add(url)
                if not await self.robots.allowed(url):
                    continue
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                except Exception:  # noqa: S112  # an unreachable page is skipped; the crawl reports pages read
                    continue
                if not self._ok_host(page.url):  # redirected to a private host: discard and stop this site
                    break
                try:
                    await page.wait_for_timeout(600)
                    final, text, html = await _snapshot(page)
                except Exception:  # noqa: S112  # page closed or navigated mid-snapshot: skip it
                    continue
                pages.append({"url": final, "text": text, "html": html, "depth": depth})
                await asyncio.sleep(random.uniform(c["delay_min"], c["delay_max"]))
                if depth >= c["max_depth"]:
                    continue
                for href, label in _links(html, final):
                    if href in seen or SKIP.search(href) or reg_domain(href) != dom:
                        continue
                    if NEXT.match(label) and pagination_budget > 0:
                        pagination_budget -= 1
                        queue.append((90, depth, href))
                        continue
                    pr = _priority(href, label)
                    if pr or depth == 0:
                        queue.append((pr or 10, depth + 1, href))
        finally:
            await page.close()
