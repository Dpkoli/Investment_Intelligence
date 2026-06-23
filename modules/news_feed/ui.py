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
        f'style="color:#0a0f1d;text-decoration:none;font-weight:600;font-size:0.81rem;line-height:1.45">'
        f'{title}</a>'
        if link else
        f'<span style="color:#0a0f1d;font-weight:600;font-size:0.81rem">{title}</span>'
    )

    ticker_chip = (
        f'<span style="background:{accent}15;color:{accent};border-radius:6px;'
        f'padding:0 5px;font-size:0.62rem;margin-left:5px;font-weight:700">{ticker}</span>'
        if ticker else ""
    )

    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-left:3px solid {accent};'
        f'border-radius:0 12px 12px 0;padding:0.6rem 0.9rem;margin-bottom:0.35rem;'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.05)">'
        f'{title_html}'
        f'<div style="display:flex;align-items:center;gap:0.5rem;margin-top:0.25rem">'
        f'<span style="color:#64748b;font-size:0.68rem">{pub}</span>'
        f'<span style="color:#cbd5e1">·</span>'
        f'<span style="color:#94a3b8;font-size:0.68rem">{time_str}</span>'
        f'{ticker_chip}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _render_category(label: str, cat_key: str, accent: str) -> None:
    sc1, sc2, sc3 = st.columns([4, 2, 1])
    with sc1:
        search = st.text_input(
            "Filter", key=f"nf_search_{cat_key}",
            placeholder="Search title or publisher…",
            label_visibility="collapsed",
        )
    with sc2:
        custom = st.text_input(
            "Extra tickers", key=f"nf_custom_{cat_key}",
            placeholder="+ TSLA, MSTR, COIN",
            label_visibility="collapsed",
        )
    with sc3:
        if st.button("🔄", key=f"nf_refresh_{cat_key}", help="Refresh news"):
            st.cache_data.clear()
            st.rerun()

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
    st.markdown(
        "<h2 style='color:#0a0f1d;font-weight:900;margin-bottom:0'>📰 News Feed</h2>"
        "<p style='color:#64748b;margin-top:2px;font-size:0.85rem'>Global market intelligence across all asset classes · refreshed every 5 min · click any headline to read</p>",
        unsafe_allow_html=True,
    )

    tabs = st.tabs([label for label, _, _ in _CATEGORIES])

    for tab_obj, (label, cat_key, accent) in zip(tabs, _CATEGORIES):
        with tab_obj:
            _render_category(label, cat_key, accent)
