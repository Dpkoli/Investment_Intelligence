"""
News Feed Module — global market news, views, and analytics,
categorised by asset class and searchable.
"""
from __future__ import annotations

import sys
import os

import streamlit as st

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from modules.news_feed.data import (
    fetch_category_news, fetch_ticker_news, format_ts,
    CATEGORY_TICKERS,
)

_CATEGORIES = [
    ("All",             "all",        "#5A8EBB"),
    ("Crypto",          "crypto",     "#7c3aed"),
    ("Equities & ETFs", "equities",   "#3A72A0"),
    ("Precious Metals", "metals",     "#C98900"),
    ("Thematic",        "thematic",   "#1AB868"),
    ("Regulatory",      "regulatory", "#E8A500"),
]

# Known instruments for ticker-aware search suggestions
_KNOWN_INSTRUMENTS: dict[str, str] = {
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "SOL-USD": "Solana",
    "XRP-USD": "XRP", "DOGE-USD": "Dogecoin", "ADA-USD": "Cardano",
    "BNB-USD": "BNB", "AVAX-USD": "Avalanche", "LINK-USD": "Chainlink",
    "SPY": "S&P 500 ETF", "QQQ": "Nasdaq 100 ETF", "NVDA": "NVIDIA",
    "AAPL": "Apple", "MSFT": "Microsoft", "AMZN": "Amazon",
    "GOOGL": "Alphabet", "TSLA": "Tesla", "META": "Meta",
    "BOTZ": "AI & Robotics ETF", "ARKK": "ARK Innovation ETF",
    "CIBR": "Cybersecurity ETF", "ICLN": "Clean Energy ETF",
    "BLOK": "Blockchain ETF", "ROBO": "ROBO Global ETF",
    "GLD": "SPDR Gold", "SLV": "iShares Silver", "GC=F": "Gold Futures",
    "MSTR": "MicroStrategy", "COIN": "Coinbase", "MARA": "Marathon Digital",
    "VWRP.L": "Vanguard All-World", "IWDA.L": "iShares MSCI World",
}


def _news_card(item: dict, accent: str = "#5B8FD4") -> None:
    title = item.get("title", "—")
    link  = item.get("link", "")
    pub   = item.get("publisher", "")
    ts    = item.get("ts", 0)
    ticker = item.get("ticker", "")
    time_str = format_ts(ts)

    title_html = (
        f'<a href="{link}" target="_blank" '
        f'style="color:#071D35;text-decoration:none;font-weight:600;font-size:0.81rem;line-height:1.45">'
        f'{title}</a>'
        if link else
        f'<span style="color:#071D35;font-weight:600;font-size:0.81rem">{title}</span>'
    )

    ticker_chip = (
        f'<span style="background:{accent}15;color:{accent};border-radius:6px;'
        f'padding:0 5px;font-size:0.62rem;margin-left:5px;font-weight:700">{ticker}</span>'
        if ticker else ""
    )

    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-left:3px solid {accent};'
        f'border-radius:0 12px 12px 0;padding:0.6rem 0.9rem;margin-bottom:0.35rem;'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.05)">'
        f'{title_html}'
        f'<div style="display:flex;align-items:center;gap:0.5rem;margin-top:0.25rem">'
        f'<span style="color:#5A8EBB;font-size:0.68rem">{pub}</span>'
        f'<span style="color:#cbd5e1">·</span>'
        f'<span style="color:#5A8EBB;font-size:0.68rem">{time_str}</span>'
        f'{ticker_chip}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _match_ticker_in_query(q: str) -> list[str]:
    """Return any known tickers that match the search query."""
    q_up = q.upper().strip()
    matched = []
    for ticker, name in _KNOWN_INSTRUMENTS.items():
        if q_up == ticker or q_up in ticker or q_up in name.upper():
            matched.append(ticker)
    return matched[:4]


def _render_category(label: str, cat_key: str, accent: str) -> None:
    sb1, sb2 = st.columns([8, 1])
    with sb1:
        search = st.text_input(
            "Search", key=f"nf_search_{cat_key}",
            placeholder="🔍  Search by title, publisher, ticker or ETF — e.g. Bitcoin, NVDA, Gold…",
            label_visibility="collapsed",
        )
    with sb2:
        if st.button("🔄", key=f"nf_refresh_{cat_key}", help="Refresh news"):
            st.cache_data.clear()
            st.rerun()

    q = (search or "").strip()

    # Detect if query looks like a ticker/instrument and fetch its news too
    extra_tickers: list[str] = []
    if q and len(q) >= 2:
        extra_tickers = _match_ticker_in_query(q)
        # Also support raw comma-separated tickers: "TSLA, COIN"
        if "," in q:
            for part in q.split(","):
                t = part.strip().upper()
                if t and t not in extra_tickers:
                    extra_tickers.append(t)

    with st.spinner("Loading news…"):
        items = fetch_category_news(cat_key)
        seen_titles: set[str] = {i["title"] for i in items}
        for tick in extra_tickers:
            for ni in fetch_ticker_news(tick, limit=8):
                if ni["title"] not in seen_titles:
                    seen_titles.add(ni["title"])
                    items.insert(0, ni)

    # Show typeahead suggestion if query matches instruments
    if extra_tickers and q and "," not in q:
        matched_names = [_KNOWN_INSTRUMENTS.get(t, t) for t in extra_tickers[:3]]
        st.markdown(
            f'<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;'
            f'padding:0.35rem 0.75rem;margin-bottom:0.4rem;font-size:0.75rem;color:#166534">'
            f'📡 Fetching live news for: <b>{", ".join(matched_names)}</b></div>',
            unsafe_allow_html=True,
        )

    if q:
        ql = q.lower()
        items = [
            i for i in items
            if ql in i.get("title", "").lower()
            or ql in i.get("publisher", "").lower()
            or ql in i.get("ticker", "").lower()
            or any(ql in n.lower() for n in [_KNOWN_INSTRUMENTS.get(i.get("ticker", ""), "")])
        ]

    if not items:
        st.info(f"No news available for {label}. Markets may be closed or data unavailable.")
        return

    st.caption(f"{len(items)} articles · sorted by recency")

    if cat_key == "all":
        c1, c2 = st.columns(2)
        for idx, item in enumerate(items):
            with (c1 if idx % 2 == 0 else c2):
                _news_card(item, accent)
    else:
        for item in items:
            _news_card(item, accent)


def render() -> None:
    st.markdown(
        "<h2 class='iw-module-header'>News Feed</h2>"
        "<p style='color:#5A8EBB;margin-top:2px;font-size:0.82rem'>Global market intelligence across all asset classes · refreshed every 5 min · click any headline to read</p>",
        unsafe_allow_html=True,
    )

    tabs = st.tabs([label for label, _, _ in _CATEGORIES])

    for tab_obj, (label, cat_key, accent) in zip(tabs, _CATEGORIES):
        with tab_obj:
            _render_category(label, cat_key, accent)
