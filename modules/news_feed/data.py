"""
News Feed — shared data-fetching layer for market news across all categories.
Uses the same yfinance news parsing pattern as core_equity / thematic_sectors.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import streamlit as st

log = logging.getLogger(__name__)

# ── Category → representative tickers ─────────────────────────────────────────

CATEGORY_TICKERS: dict[str, list[str]] = {
    "crypto":    ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "DOGE-USD"],
    "equities":  ["SPY", "QQQ", "NVDA", "AAPL", "MSFT", "AMZN"],
    "thematic":  ["BOTZ", "ARKK", "CIBR", "ICLN", "BLOK"],
    "metals":    ["GLD", "SLV", "GC=F"],
    "regulatory":["BTC-USD", "ETH-USD"],
}
CATEGORY_TICKERS["all"] = list(dict.fromkeys(
    CATEGORY_TICKERS["crypto"] +
    CATEGORY_TICKERS["equities"] +
    CATEGORY_TICKERS["thematic"] +
    CATEGORY_TICKERS["metals"]
))


def _parse_news_item(item: dict, source_ticker: str = "") -> Optional[dict]:
    """Normalise a raw yfinance news item into a consistent dict."""
    if not isinstance(item, dict):
        return None
    content = item.get("content") or item
    if not isinstance(content, dict):
        content = item

    title = str(content.get("title") or content.get("headline") or item.get("title", "")).strip()
    if not title:
        return None

    canon = content.get("canonicalUrl") or {}
    click = content.get("clickThroughUrl") or {}
    link = (
        (canon.get("url") if isinstance(canon, dict) else "")
        or (click.get("url") if isinstance(click, dict) else "")
        or item.get("link", "")
    )

    provider  = content.get("provider") or {}
    publisher = (
        (provider.get("displayName") if isinstance(provider, dict) else str(provider or ""))
        or item.get("publisher", "")
    )

    ts_raw = content.get("pubDate") or item.get("providerPublishTime") or 0
    ts: int = 0
    if isinstance(ts_raw, str):
        try:
            ts = int(datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).timestamp())
        except Exception:
            ts = 0
    else:
        ts = int(ts_raw or 0)

    return {
        "title":     title,
        "link":      str(link).strip(),
        "publisher": str(publisher).strip(),
        "ts":        ts,
        "ticker":    source_ticker,
    }


def format_ts(ts: int) -> str:
    """Convert Unix timestamp to human-readable relative string."""
    if not ts:
        return "—"
    try:
        dt  = datetime.fromtimestamp(ts)
        now = datetime.now()
        delta = now - dt
        if delta.seconds < 3600 and delta.days == 0:
            return f"{max(delta.seconds // 60, 1)}m ago"
        if delta.days == 0:
            return f"{delta.seconds // 3600}h ago"
        if delta.days < 7:
            return f"{delta.days}d ago"
        return dt.strftime("%b %d")
    except Exception:
        return "—"


@st.cache_data(ttl=300, show_spinner=False)
def fetch_ticker_news(ticker: str, limit: int = 10) -> list[dict]:
    """Fetch and parse news for a single ticker."""
    try:
        import yfinance as yf
        raw = yf.Ticker(ticker).news or []
        results = []
        for item in raw[:limit]:
            parsed = _parse_news_item(item, ticker)
            if parsed:
                results.append(parsed)
        return results
    except Exception as exc:
        log.debug("News fetch failed for %s: %s", ticker, exc)
        return []


@st.cache_data(ttl=300, show_spinner=False)
def fetch_category_news(category: str, max_items: int = 40) -> list[dict]:
    """Fetch, merge, deduplicate and sort news for a category."""
    tickers = CATEGORY_TICKERS.get(category, [])
    seen: set[str] = set()
    items: list[dict] = []
    for ticker in tickers:
        for item in fetch_ticker_news(ticker, limit=12):
            key = item["link"] or item["title"]
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
    items.sort(key=lambda x: x["ts"], reverse=True)
    return items[:max_items]
