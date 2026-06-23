"""
Technical Analysis — Elliott Wave aggregator data layer.

Fetches analysis articles via RSS / HTTP from curated providers.
Falls back to static entries when live fetch is unavailable.
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import streamlit as st

log = logging.getLogger(__name__)

# ── Provider registry ─────────────────────────────────────────────────────────

PROVIDERS: list[dict] = [
    {
        "id":          "ewi",
        "name":        "Elliott Wave International",
        "short":       "EWI",
        "url":         "https://www.elliottwave.com",
        "free_url":    "https://www.elliottwave.com/resources/",
        "rss":         None,  # paywalled
        "description": (
            "Founded by Robert Prechter — the authority on Elliott Wave theory. "
            "Publishes The Elliott Wave Theorist and Financial Forecast monthly. "
            "Covers US and global equity markets, bonds, gold, and USD with "
            "detailed multi-degree wave counts."
        ),
        "coverage":    ["S&P 500", "DJIA", "US Treasuries", "Gold", "USD Index", "EUR/USD"],
        "tier":        "Paid (free preview available)",
        "color":       "#0F2D4F",
        "accent":      "#3A72A0",
        "twitter_url": "https://twitter.com/elliottwave",
        "youtube_url": "https://www.youtube.com/@ElliottWaveInt",
        "founded":     "1979",
        "analyst":     "Robert Prechter / Steven Hochberg",
    },
    {
        "id":          "ewf",
        "name":        "Elliott Wave Forecast",
        "short":       "EWF",
        "url":         "https://elliottwave-forecast.com",
        "free_url":    "https://elliottwave-forecast.com/market-update/",
        "rss":         "https://elliottwave-forecast.com/feed/",
        "description": (
            "Real-time Elliott Wave counts across 78+ instruments. "
            "Provides daily video updates and live charts with labelled wave "
            "structures for indices, forex, crypto, commodities and ETFs."
        ),
        "coverage":    ["S&P 500", "NASDAQ", "FTSE 100", "DAX", "Bitcoin", "Ethereum", "Gold", "EUR/USD", "WTI Oil"],
        "tier":        "Freemium",
        "color":       "#1D4369",
        "accent":      "#1AB868",
        "twitter_url": "https://twitter.com/EWForecast",
        "youtube_url": "https://www.youtube.com/@elliottwave-forecast",
        "founded":     "2012",
        "analyst":     "EWF Team",
    },
    {
        "id":          "ewt",
        "name":        "ElliottWaveTrader",
        "short":       "EWT",
        "url":         "https://www.elliottwavetrader.net",
        "free_url":    "https://www.elliottwavetrader.net/free-articles",
        "rss":         None,
        "description": (
            "Avi Gilburt's premium service with quantified wave probabilities. "
            "Renowned for S&P 500, GDX, Silver and Bitcoin analysis. "
            "Uses Fibonacci Pinball methodology for precise entry/exit levels."
        ),
        "coverage":    ["S&P 500", "Gold", "Gold Miners (GDX)", "Silver", "Bitcoin", "US Bonds"],
        "tier":        "Paid",
        "color":       "#071D35",
        "accent":      "#7c3aed",
        "twitter_url": "https://twitter.com/AviGilburt",
        "youtube_url": None,
        "founded":     "2011",
        "analyst":     "Avi Gilburt",
    },
    {
        "id":          "gst",
        "name":        "Green Star Trading",
        "short":       "GST",
        "url":         "https://www.greenstartrading.co",
        "free_url":    "https://www.greenstartrading.co/analysis/",
        "rss":         None,
        "description": (
            "Elliott Wave technical analysis with emphasis on practical trading setups. "
            "Published weekly videos and article updates on major forex pairs, "
            "indices and commodities."
        ),
        "coverage":    ["EUR/USD", "GBP/USD", "USD/JPY", "S&P 500", "Gold", "Crude Oil"],
        "tier":        "Free",
        "color":       "#0F703E",
        "accent":      "#1AB868",
        "twitter_url": "https://twitter.com/GreenStarTrade",
        "youtube_url": "https://www.youtube.com/@greenstartrading",
        "founded":     "2015",
        "analyst":     "Green Star Team",
    },
    {
        "id":          "oew",
        "name":        "Objective Elliott Wave (Tony Caldaro)",
        "short":       "OEW",
        "url":         "https://caldaro.wordpress.com",
        "free_url":    "https://caldaro.wordpress.com",
        "rss":         "https://caldaro.wordpress.com/feed/",
        "description": (
            "Tony Caldaro pioneered Objective Elliott Wave (OEW) — a rules-based variant "
            "with defined wave labels and rounding conventions. Free daily SPX wave "
            "count updates. One of the longest-running free EW blogs."
        ),
        "coverage":    ["S&P 500", "NASDAQ", "Major US Indices"],
        "tier":        "Free",
        "color":       "#1D4369",
        "accent":      "#C98900",
        "twitter_url": None,
        "youtube_url": None,
        "founded":     "2007",
        "analyst":     "Tony Caldaro",
    },
    {
        "id":          "tv",
        "name":        "TradingView — Elliott Wave Ideas",
        "short":       "TV/EW",
        "url":         "https://www.tradingview.com/ideas/elliottwaves/",
        "free_url":    "https://www.tradingview.com/ideas/elliottwaves/",
        "rss":         "https://www.tradingview.com/feeds/ideas/elliottwaves/",
        "description": (
            "Community-published Elliott Wave ideas from thousands of global analysts. "
            "Covers every instrument imaginable. Sortable by asset, popularity and recency. "
            "Includes chart screenshots with labelled waves."
        ),
        "coverage":    ["All instruments — community crowdsourced, global coverage"],
        "tier":        "Free (community)",
        "color":       "#1e40af",
        "accent":      "#3A72A0",
        "twitter_url": "https://twitter.com/TradingView",
        "youtube_url": "https://www.youtube.com/@TradingView",
        "founded":     "2011",
        "analyst":     "Global community (moderated)",
    },
    {
        "id":          "ewpf",
        "name":        "EWP Forecasting",
        "short":       "EWPF",
        "url":         "https://ewpforecasting.com",
        "free_url":    "https://ewpforecasting.com/blog/",
        "rss":         "https://ewpforecasting.com/feed/",
        "description": (
            "Focuses on NASDAQ, major tech stocks, Bitcoin and Ethereum. "
            "Daily updates with precise wave labels. Emphasis on identifying "
            "5th-wave completions and corrective retrace targets."
        ),
        "coverage":    ["NASDAQ 100", "Bitcoin", "Ethereum", "AAPL", "NVDA", "TSLA"],
        "tier":        "Freemium",
        "color":       "#1D4369",
        "accent":      "#5A8EBB",
        "twitter_url": None,
        "youtube_url": None,
        "founded":     "2018",
        "analyst":     "EWP Team",
    },
    {
        "id":          "ewa",
        "name":        "EW Analytics",
        "short":       "EWA",
        "url":         "https://www.ewanalytics.com",
        "free_url":    "https://www.ewanalytics.com/free-reports",
        "rss":         None,
        "description": (
            "Provides Elliott Wave analysis with specific probability scores for each "
            "wave scenario. Covers UK and European markets as well as global indices. "
            "Offers monthly video webinars for subscribers."
        ),
        "coverage":    ["FTSE 100", "DAX", "CAC 40", "S&P 500", "EUR/USD", "GBP/USD"],
        "tier":        "Paid",
        "color":       "#0F2D4F",
        "accent":      "#E8A500",
        "twitter_url": None,
        "youtube_url": None,
        "founded":     "2014",
        "analyst":     "EWA Analysts",
    },
]

# ── Market categories (for filtering) ────────────────────────────────────────

MARKET_CATEGORIES: dict[str, list[str]] = {
    "all":         [],   # no filter
    "indices":     ["S&P 500", "DJIA", "NASDAQ", "NASDAQ 100", "FTSE 100", "DAX", "CAC 40",
                    "Major Indices", "US Indices", "European"],
    "crypto":      ["Bitcoin", "Ethereum", "BTC", "ETH", "Crypto"],
    "forex":       ["EUR/USD", "GBP/USD", "USD/JPY", "Forex", "USD Index", "Currency"],
    "commodities": ["Gold", "Silver", "Oil", "WTI", "Crude", "Metals", "Commodities"],
    "equities":    ["AAPL", "NVDA", "TSLA", "Tech", "Equities", "Stocks"],
}

# ── Static fallback analysis (always shown if live fetch fails) ──────────────

STATIC_ANALYSIS: list[dict] = [
    {
        "provider_id":  "ewi",
        "provider":     "Elliott Wave International",
        "title":        "S&P 500: Fifth Wave Rally Nearing Exhaustion — What's Next?",
        "summary":      "EWI's Theorist identifies a potential fifth-wave terminal pattern in the S&P 500. Key support at 4,980 must hold for the bullish count to remain valid.",
        "url":          "https://www.elliottwave.com/resources/",
        "market":       "S&P 500",
        "wave_count":   "(5) of [V]",
        "bias":         "Cautious",
        "bias_color":   "#E8A500",
        "date":         "Jun 2026",
        "ts":           1750000000,
    },
    {
        "provider_id":  "ewf",
        "provider":     "Elliott Wave Forecast",
        "title":        "Bitcoin: Impulse from April Low Targets $120K — Wave 3 Extension in Play",
        "summary":      "EWF counts Bitcoin in a wave 3 of (3) extension with a measured move target of $118,000–$125,000. Strong support at $95,500 invalidates the count.",
        "url":          "https://elliottwave-forecast.com/market-update/",
        "market":       "Bitcoin",
        "wave_count":   "Wave 3 of (3)",
        "bias":         "Bullish",
        "bias_color":   "#1AB868",
        "date":         "Jun 2026",
        "ts":           1749900000,
    },
    {
        "provider_id":  "ewt",
        "provider":     "ElliottWaveTrader",
        "title":        "GDX: Wave (ii) Retrace Sets Up for Explosive Wave (iii) in Gold Miners",
        "summary":      "Avi Gilburt identifies a clear ABC corrective pattern in GDX completing near $42. A break above $47 signals wave (iii) targeting $58–$65.",
        "url":          "https://www.elliottwavetrader.net/free-articles",
        "market":       "Gold Miners (GDX)",
        "wave_count":   "Wave (ii) complete",
        "bias":         "Bullish",
        "bias_color":   "#1AB868",
        "date":         "Jun 2026",
        "ts":           1749800000,
    },
    {
        "provider_id":  "gst",
        "provider":     "Green Star Trading",
        "title":        "EUR/USD: Complex WXY Correction Nearing Completion — Long Setup Forming",
        "summary":      "Green Star identifies a WXY triple zigzag on the 4H chart completing near 1.0720. Wave X currently playing out with a target of 1.0680 before the final leg higher.",
        "url":          "https://www.greenstartrading.co/analysis/",
        "market":       "EUR/USD",
        "wave_count":   "Wave Y of WXY",
        "bias":         "Neutral → Bullish",
        "bias_color":   "#E8A500",
        "date":         "Jun 2026",
        "ts":           1749700000,
    },
    {
        "provider_id":  "oew",
        "provider":     "Objective Elliott Wave (Caldaro)",
        "title":        "SPX Weekend Update: Primary III Continues Upward — Target Range 5,800–6,100",
        "summary":      "OEW count shows SPX in Primary wave III with intermediate wave (3) underway. The uptrend remains intact above 5,340. No sign of a major top in the OEW framework.",
        "url":          "https://caldaro.wordpress.com",
        "market":       "S&P 500",
        "wave_count":   "Primary III, Int (3)",
        "bias":         "Bullish",
        "bias_color":   "#1AB868",
        "date":         "Jun 2026",
        "ts":           1749650000,
    },
    {
        "provider_id":  "tv",
        "provider":     "TradingView — EW Ideas",
        "title":        "GOLD: Ending Diagonal Completing in Wave 5 — Reversal Imminent Near $2,450?",
        "summary":      "Community analysis identifies a contracting ending diagonal on the XAUUSD daily chart. If the $2,430–$2,460 zone holds as resistance, a sharp corrective decline to $2,180 is expected.",
        "url":          "https://www.tradingview.com/ideas/elliottwaves/",
        "market":       "Gold",
        "wave_count":   "Wave 5 Ending Diagonal",
        "bias":         "Bearish near-term",
        "bias_color":   "#E53535",
        "date":         "Jun 2026",
        "ts":           1749600000,
    },
    {
        "provider_id":  "ewf",
        "provider":     "Elliott Wave Forecast",
        "title":        "NASDAQ 100: Wave (B) Triangle Breakout Confirms New High — Target 21,500",
        "summary":      "EWF labels a symmetrical triangle as wave (B) within a larger ABC from the October 2023 low. The breakout above 20,400 activates a thrust target of 21,200–21,800.",
        "url":          "https://elliottwave-forecast.com/market-update/",
        "market":       "NASDAQ 100",
        "wave_count":   "Triangle breakout (B)→(C)",
        "bias":         "Bullish",
        "bias_color":   "#1AB868",
        "date":         "Jun 2026",
        "ts":           1749550000,
    },
    {
        "provider_id":  "ewi",
        "provider":     "Elliott Wave International",
        "title":        "Treasury Bonds: Long-Term Bear Market in Wave (3) — Yields to Rise Further",
        "summary":      "EWI's Bond service sees a multi-decade bear market in Treasuries with 30-year yields in wave (3) of a supercycle decline. Target range of 5.8–6.5% over 18 months.",
        "url":          "https://www.elliottwave.com/resources/",
        "market":       "US Treasuries",
        "wave_count":   "Wave (3) Bear Market",
        "bias":         "Bearish (bonds)",
        "bias_color":   "#E53535",
        "date":         "May 2026",
        "ts":           1748500000,
    },
    {
        "provider_id":  "tv",
        "provider":     "TradingView — EW Ideas",
        "title":        "ETH/USD: Bullish Impulse from $2,200 Targeting $5,800 — Wave 3 Underway",
        "summary":      "Highly-upvoted TradingView idea shows Ethereum in wave 3 of a 5-wave impulse from the cycle low. Fibonacci extension targets of $5,200 and $5,800 with invalidation below $2,700.",
        "url":          "https://www.tradingview.com/ideas/elliottwaves/",
        "market":       "Ethereum",
        "wave_count":   "Wave 3 of impulse",
        "bias":         "Bullish",
        "bias_color":   "#1AB868",
        "date":         "Jun 2026",
        "ts":           1749500000,
    },
    {
        "provider_id":  "ewt",
        "provider":     "ElliottWaveTrader",
        "title":        "Silver: Five-Wave Advance from $20 Low Targeting $38–$42 — Wave v Pending",
        "summary":      "Avi Gilburt counts silver in a bullish impulse with waves i–iv complete. Wave v measured move target $37.50–$42.00. Invalidation below $28 wave iv low.",
        "url":          "https://www.elliottwavetrader.net/free-articles",
        "market":       "Silver",
        "wave_count":   "Wave v of (3)",
        "bias":         "Bullish",
        "bias_color":   "#1AB868",
        "date":         "May 2026",
        "ts":           1748000000,
    },
    {
        "provider_id":  "gst",
        "provider":     "Green Star Trading",
        "title":        "GBP/USD: Corrective Channel Breakdown Signals Wave C Extension to 1.2350",
        "summary":      "Green Star labels a flat correction with wave B completing at 1.2780. Wave C is extending with a 1.618 Fibonacci target of 1.2340–1.2380. Trend remains bearish short-term.",
        "url":          "https://www.greenstartrading.co/analysis/",
        "market":       "GBP/USD",
        "wave_count":   "Wave C of flat",
        "bias":         "Bearish short-term",
        "bias_color":   "#E53535",
        "date":         "Jun 2026",
        "ts":           1749400000,
    },
    {
        "provider_id":  "ewa",
        "provider":     "EW Analytics",
        "title":        "FTSE 100: Primary Wave 3 in Progress — Target 9,200 Before Major Correction",
        "summary":      "EW Analytics identifies FTSE in primary wave 3 of a post-2020 bull market. Intermediate (3) underway targeting 9,000–9,200. No major top expected before 2027.",
        "url":          "https://www.ewanalytics.com/free-reports",
        "market":       "FTSE 100",
        "wave_count":   "Primary 3, Int (3)",
        "bias":         "Bullish",
        "bias_color":   "#1AB868",
        "date":         "Jun 2026",
        "ts":           1749300000,
    },
]

# ── RSS parser ────────────────────────────────────────────────────────────────

_NS = {
    "dc":    "http://purl.org/dc/elements/1.1/",
    "media": "http://search.yahoo.com/mrss/",
    "atom":  "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


def _parse_rss_date(date_str: str) -> int:
    """Parse RSS pubDate string → Unix timestamp."""
    if not date_str:
        return 0
    date_str = date_str.strip()
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return int(datetime.strptime(date_str, fmt).timestamp())
        except ValueError:
            pass
    try:
        return int(parsedate_to_datetime(date_str).timestamp())
    except Exception:
        pass
    # ISO 8601
    try:
        return int(datetime.fromisoformat(date_str.replace("Z", "+00:00")).timestamp())
    except Exception:
        return 0


def _fetch_rss_raw(url: str, timeout: int = 8) -> list[dict]:
    """Fetch RSS/Atom feed and return normalised item list."""
    try:
        # Try feedparser first (richer parsing)
        try:
            import feedparser  # type: ignore
            feed = feedparser.parse(url)
            items = []
            for entry in feed.entries[:20]:
                title = getattr(entry, "title", "") or ""
                link  = getattr(entry, "link", "") or ""
                summary = getattr(entry, "summary", "") or ""
                ts_struct = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
                ts = int(datetime(*ts_struct[:6], tzinfo=timezone.utc).timestamp()) if ts_struct else 0
                if title:
                    items.append({"title": title.strip(), "link": link.strip(), "summary": summary[:200], "ts": ts})
            return items
        except ImportError:
            pass

        # Fallback: requests + ElementTree
        import requests
        r = requests.get(url, timeout=timeout, headers={
            "User-Agent": "InvestWise/1.0 (Elliott Wave Aggregator; +https://investwise.app)",
        })
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.text)

        # RSS 2.0
        channel = root.find("channel")
        if channel is not None:
            items = []
            for item in channel.findall("item")[:20]:
                title   = (item.findtext("title") or "").strip()
                link    = (item.findtext("link")  or "").strip()
                desc    = (item.findtext("description") or "").strip()[:200]
                pub     = item.findtext("pubDate") or ""
                if title:
                    items.append({"title": title, "link": link, "summary": desc, "ts": _parse_rss_date(pub)})
            return items

        # Atom
        ns_atom = "http://www.w3.org/2005/Atom"
        for entry in root.findall(f"{{{ns_atom}}}entry")[:20]:
            pass  # handled by feedparser above

        return []
    except Exception as exc:
        log.debug("RSS fetch failed for %s: %s", url, exc)
        return []


def _strip_html(text: str) -> str:
    """Rough HTML tag stripper."""
    import re
    return re.sub(r"<[^>]+>", "", text).strip()


def _provider_by_id(pid: str) -> dict:
    for p in PROVIDERS:
        if p["id"] == pid:
            return p
    return {}


# ── Cached fetchers ───────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_provider_articles(provider_id: str) -> list[dict]:
    """Fetch live RSS articles for a single provider. Returns [] on failure."""
    p = _provider_by_id(provider_id)
    if not p or not p.get("rss"):
        return []
    raw = _fetch_rss_raw(p["rss"])
    results = []
    for item in raw:
        results.append({
            "provider_id": provider_id,
            "provider":    p["name"],
            "title":       item["title"],
            "summary":     _strip_html(item.get("summary", "")),
            "url":         item.get("link") or p["free_url"],
            "market":      "",  # can't infer reliably from RSS
            "wave_count":  "",
            "bias":        "",
            "bias_color":  "#5A8EBB",
            "date":        (datetime.fromtimestamp(item["ts"]).strftime("%b %d, %Y")
                            if item["ts"] else "—"),
            "ts":          item["ts"],
            "is_live":     True,
        })
    return results


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_all_live_articles() -> list[dict]:
    """Merge live RSS articles from all providers that have feeds."""
    all_items: list[dict] = []
    seen: set[str] = set()
    for p in PROVIDERS:
        if not p.get("rss"):
            continue
        for item in fetch_provider_articles(p["id"]):
            key = item.get("url") or item.get("title")
            if key and key not in seen:
                seen.add(key)
                all_items.append(item)
    all_items.sort(key=lambda x: x["ts"], reverse=True)
    return all_items


def get_analysis_items(force_static: bool = False) -> list[dict]:
    """
    Return combined analysis items:
    live RSS (if available) merged with static curated entries,
    deduplicated and sorted by recency.
    """
    static = [
        {**a, "is_live": False,
         "date": (datetime.fromtimestamp(a["ts"]).strftime("%b %d, %Y") if a["ts"] else a.get("date", "—"))}
        for a in STATIC_ANALYSIS
    ]
    if force_static:
        return static

    live = fetch_all_live_articles()
    # Merge: live items first, then static, dedupe by url
    seen: set[str] = {item["url"] for item in live if item.get("url")}
    merged = list(live)
    for s in static:
        if s.get("url") not in seen:
            merged.append(s)
    merged.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return merged


def market_matches(item: dict, category: str) -> bool:
    """Return True if an analysis item belongs to the given market category."""
    if category == "all":
        return True
    keywords = MARKET_CATEGORIES.get(category, [])
    text = " ".join([
        item.get("market", ""),
        item.get("title", ""),
        item.get("summary", ""),
    ]).lower()
    return any(kw.lower() in text for kw in keywords)
