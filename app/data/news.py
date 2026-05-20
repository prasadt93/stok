"""Fetch recent news headlines for Indian stocks.

Strategy:
  1. Google News RSS (stock-specific query) — primary, 100 results
  2. LiveMint RSS — filtered for company name mentions (fallback)
  3. Moneycontrol RSS — filtered for company name mentions (second fallback)

macOS Python 3.14 ships without the system CA bundle wired in, so we use an
unverified SSL context for outbound RSS fetches. This is acceptable for a
read-only, local-dev news feed; add certificate pinning before production use.
"""
from __future__ import annotations

import ssl
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List
from urllib.parse import quote_plus

import feedparser

# ── SSL context ────────────────────────────────────────────────────────────────
# Python 3.14 on macOS lacks bundled CA certs, causing CERTIFICATE_VERIFY_FAILED.
# We bypass verification for these read-only RSS feeds only.
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# ── URLs ───────────────────────────────────────────────────────────────────────
_GOOGLE_RSS = "https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
_LIVEMINT_RSS = "https://www.livemint.com/rss/markets"
_MONEYCONTROL_RSS = "https://www.moneycontrol.com/rss/marketreports.xml"


@dataclass
class NewsItem:
    title: str
    summary: str
    published: datetime
    link: str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fetch_raw(url: str) -> bytes:
    try:
        req = urllib.request.urlopen(url, timeout=8, context=_SSL_CTX)
        return req.read()
    except Exception:
        return b""


def _parse_dt(struct_time) -> datetime | None:
    if not struct_time:
        return None
    try:
        return datetime(*struct_time[:6], tzinfo=timezone.utc)
    except Exception:
        return None


def _entries_to_items(
    entries,
    cutoff: datetime,
    seen: set,
    keyword_filter: str | None = None,
) -> List[NewsItem]:
    items: List[NewsItem] = []
    kw = keyword_filter.lower() if keyword_filter else None
    for entry in entries[:60]:
        title = entry.get("title", "").strip()
        if not title or title in seen:
            continue
        # When keyword_filter is set (general feeds), require keyword in title
        if kw and kw not in title.lower():
            continue
        published = _parse_dt(entry.get("published_parsed"))
        if published is None or published < cutoff:
            continue
        seen.add(title)
        items.append(
            NewsItem(
                title=title,
                summary=entry.get("summary", "").strip(),
                published=published,
                link=entry.get("link", ""),
            )
        )
    return items


def _company_short_name(query_hint: str | None, ticker: str) -> str:
    base = query_hint or ticker.split(".")[0]
    # Use the first meaningful word (skip common prefixes like "The", "Ltd")
    words = [w for w in base.split() if len(w) > 2]
    return words[0] if words else base


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_news(
    ticker: str,
    query_hint: str | None = None,
    lookback_days: int = 14,
) -> List[NewsItem]:
    """Return recent news items for the given stock.

    Tries Google News first (stock-specific), then falls back to general
    Indian financial RSS feeds filtered by company name.
    """
    base_name = query_hint or ticker.split(".")[0]
    short = _company_short_name(query_hint, ticker)
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    seen: set = set()
    all_items: List[NewsItem] = []

    # 1 — Google News: two queries (specific → broader)
    for q in [f"{base_name} NSE stock", f"{short} stock India"]:
        url = _GOOGLE_RSS.format(q=quote_plus(q))
        fd = feedparser.parse(_fetch_raw(url))
        all_items.extend(_entries_to_items(fd.entries, cutoff, seen))
        if len(all_items) >= 5:
            break

    # 2 — LiveMint fallback
    if len(all_items) < 3:
        fd = feedparser.parse(_fetch_raw(_LIVEMINT_RSS))
        all_items.extend(_entries_to_items(fd.entries, cutoff, seen, keyword_filter=short))

    # 3 — Moneycontrol fallback
    if len(all_items) < 3:
        fd = feedparser.parse(_fetch_raw(_MONEYCONTROL_RSS))
        all_items.extend(_entries_to_items(fd.entries, cutoff, seen, keyword_filter=short))

    return all_items
