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
    ("🌍 All",             "all",        "#888"),
    ("₿ Crypto",          "crypto",     "#9B59B6"),
    ("📈 Equities & ETFs", "equities",   "#5B8FD4"),
    ("🥇 Precious Metals", "metals",     "#FFD700"),
    ("📊 Thematic",        "thematic",   "#2ECC71"),
    ("⚖️ Regulatory",     "regulatory", "#FFA500"),
]


def _news_card(item: dict, accent: str = "#5B8FD4") -> None:
    title = item.get("title", "—")
    link  = item.get("link", "")
    pub   = item.get("publisher", "")
    ts    = item.get("ts", 0)
    ticker = item.get("ticker", "")
    time_str = format_ts(ts)

    title_html = (
        f'<a href="{link}" target="_blank" '
        f'style="color:#ddd;text-decoration:none;font-weight:600;font-size:0.81rem;line-height:1.4">'
        f'{title}</a>'
        if link else
        f'<span style="color:#ddd;font-weight:600;font-size:0.81rem">{title}</span>'
    )

    ticker_chip = (
        f'<span style="background:{accent}22;color:{accent};border-radius:3px;'
        f'padding:0 4px;font-size:0.62rem;margin-left:4px">{ticker}</span>'
        if ticker else ""
    )

    st.markdown(
        f'<div style="background:#1A1D24;border:1px solid #2E3140;border-left:3px solid {accent};'
        f'border-radius:0 6px 6px 0;padding:0.55rem 0.85rem;margin-bottom:0.3rem">'
        f'{title_html}'
        f'<div style="display:flex;align-items:center;gap:0.5rem;margin-top:0.22rem">'
        f'<span style="color:#666;font-size:0.68rem">{pub}</span>'
        f'<span style="color:#444">·</span>'
        f'<span style="color:#555;font-size:0.68rem">{time_str}</span>'
        f'{ticker_chip}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _render_category(label: str, cat_key: str, accent: str) -> None:
    top_c, refresh_c = st.columns([5, 1])
    with top_c:
        search = st.text_input(
            "Filter", key=f"nf_search_{cat_key}",
            placeholder="Search title or publisher…",
            label_visibility="collapsed",
        )
    with refresh_c:
        if st.button("🔄", key=f"nf_refresh_{cat_key}", help="Refresh news"):
            st.cache_data.clear()
            st.rerun()

    # Custom ticker override
    with st.expander("⚙️ Custom tickers for this category", expanded=False):
        default_ticks = CATEGORY_TICKERS.get(cat_key, [])
        custom = st.text_input(
            "Add extra tickers (comma-separated)",
            placeholder="e.g. TSLA, MSTR, COIN",
            key=f"nf_custom_{cat_key}",
        )
        extra_tickers = [t.strip().upper() for t in custom.split(",") if t.strip()] if custom else []

    with st.spinner("Loading news…"):
        items = fetch_category_news(cat_key)
        for extra in extra_tickers:
            extra_news = fetch_ticker_news(extra, limit=8)
            items = extra_news + items

    if search:
        q = search.lower()
        items = [i for i in items if q in i.get("title", "").lower() or q in i.get("publisher", "").lower()]

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
    st.markdown("## 📰 News Feed — Global Market Intelligence")
    st.caption(
        "Live news and views from major financial media across all asset classes. "
        "Refreshed every 5 minutes. Click any headline to read the full article."
    )

    tabs = st.tabs([label for label, _, _ in _CATEGORIES])

    for tab_obj, (label, cat_key, accent) in zip(tabs, _CATEGORIES):
        with tab_obj:
            _render_category(label, cat_key, accent)
