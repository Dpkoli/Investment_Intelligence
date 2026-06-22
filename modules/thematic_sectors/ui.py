"""Thematic Sectors module — Streamlit renderer."""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px

from .data import THEMATIC_REGISTRY, ALL_SECTORS, ALL_SUB_THEMES, fetch_prices

_PAGE_SIZE = 25


@st.cache_data(ttl=300, show_spinner=False)
def _live_prices(tickers: tuple[str, ...]) -> dict:
    return fetch_prices(list(tickers))


def render() -> None:
    st.markdown("## 📊 Thematic Sectors — Global Sector & Thematic ETF Grid")
    st.caption(f"{len(THEMATIC_REGISTRY)} products across {len(ALL_SECTORS)} sectors and {len(ALL_SUB_THEMES)} sub-themes")

    # ── Filters ───────────────────────────────────────────────────────────────
    col_s, col_t, col_r, col_ex = st.columns(4)
    with col_s:
        sel_sectors = st.multiselect("Sector", ALL_SECTORS, placeholder="All sectors")
    with col_t:
        sel_themes = st.multiselect("Sub-Theme", ALL_SUB_THEMES, placeholder="All themes")
    with col_r:
        sel_regions = st.multiselect("Region", sorted(set(p.region for p in THEMATIC_REGISTRY)), placeholder="All regions")
    with col_ex:
        sel_exchange = st.multiselect("Exchange", sorted(set(p.exchange for p in THEMATIC_REGISTRY)), placeholder="All exchanges")

    filtered = THEMATIC_REGISTRY
    if sel_sectors:
        filtered = [p for p in filtered if p.sector in sel_sectors]
    if sel_themes:
        filtered = [p for p in filtered if p.sub_theme in sel_themes]
    if sel_regions:
        filtered = [p for p in filtered if p.region in sel_regions]
    if sel_exchange:
        filtered = [p for p in filtered if p.exchange in sel_exchange]

    st.caption(f"Showing {len(filtered)} products")

    # ── Sector Treemap ────────────────────────────────────────────────────────
    sector_counts = {}
    theme_counts: dict[str, dict] = {}
    for p in THEMATIC_REGISTRY:
        sector_counts[p.sector] = sector_counts.get(p.sector, 0) + 1
        theme_counts.setdefault(p.sector, {})
        theme_counts[p.sector][p.sub_theme] = theme_counts[p.sector].get(p.sub_theme, 0) + 1

    treemap_rows = []
    for sector, themes in theme_counts.items():
        for theme, cnt in themes.items():
            treemap_rows.append({"Sector": sector, "Sub-Theme": theme, "Count": cnt})
    treemap_df = pd.DataFrame(treemap_rows)

    fig = px.treemap(
        treemap_df, path=["Sector", "Sub-Theme"], values="Count",
        color="Count", color_continuous_scale=[[0, "#1A2A3A"], [0.5, "#00896B"], [1, "#00D4AA"]],
        template="plotly_dark",
    )
    fig.update_layout(
        height=360, margin={"t": 10, "b": 10, "l": 0, "r": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False,
    )
    fig.update_traces(marker={"line": {"width": 0.5, "color": "#0E1117"}})
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.divider()

    # ── Pagination ────────────────────────────────────────────────────────────
    total_pages = max(1, (len(filtered) + _PAGE_SIZE - 1) // _PAGE_SIZE)
    page_key = "thematic_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    page = st.session_state[page_key]
    page = max(0, min(page, total_pages - 1))

    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        if st.button("← Prev", key="th_prev", disabled=page == 0):
            st.session_state[page_key] = page - 1
            st.rerun()
    with c2:
        st.caption(f"Page {page + 1} / {total_pages}")
    with c3:
        if st.button("Next →", key="th_next", disabled=page >= total_pages - 1):
            st.session_state[page_key] = page + 1
            st.rerun()

    page_items = filtered[page * _PAGE_SIZE : (page + 1) * _PAGE_SIZE]

    # ── Live prices ───────────────────────────────────────────────────────────
    tickers_yf = tuple(
        p.yf_ticker or p.ticker
        for p in page_items
        if not p.ticker.endswith(".L") and not p.ticker.endswith(".DE") and not p.ticker.endswith(".PA")
    )
    prices = _live_prices(tickers_yf) if tickers_yf else {}

    rows = []
    for p in page_items:
        yf_key = p.yf_ticker or p.ticker
        px_data = prices.get(yf_key, {})
        price   = px_data.get("price")
        chg     = px_data.get("chg_pct")
        rows.append({
            "Ticker":     p.ticker,
            "Name":       p.name,
            "Sector":     p.sector,
            "Sub-Theme":  p.sub_theme,
            "Region":     p.region,
            "Exchange":   p.exchange,
            "TER":        f"{p.expense_ratio:.2f}%" if p.expense_ratio else "—",
            "AUM ($bn)":  f"{p.aum_bn:.1f}" if p.aum_bn else "—",
            "Issuer":     p.issuer or "—",
            "Price":      f"${price:,.2f}" if price else "—",
            "1d %":       f"{chg:+.2f}%" if chg is not None else "—",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
