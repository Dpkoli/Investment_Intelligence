"""Core Equity module — Streamlit renderer."""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px

from .data import CORE_EQUITY_REGISTRY, IndexProduct, fetch_prices

_PAGE_SIZE = 20


def _color_chg(v):
    if v is None:
        return "color: #888"
    return "color: #00D4AA" if v >= 0 else "color: #FF4B4B"


@st.cache_data(ttl=300, show_spinner=False)
def _live_prices(tickers: tuple[str, ...]) -> dict:
    return fetch_prices(list(tickers))


def render() -> None:
    st.markdown("## 🌐 Core Equity — Global Index & ETF Intelligence")
    st.caption(f"{len(CORE_EQUITY_REGISTRY)} instruments tracked across 25 countries")

    # ── Filters ───────────────────────────────────────────────────────────────
    regions = sorted(set(p.region for p in CORE_EQUITY_REGISTRY))
    types   = sorted(set(p.product_type for p in CORE_EQUITY_REGISTRY))
    issuers = sorted(set(p.issuer for p in CORE_EQUITY_REGISTRY if p.issuer))

    col_r, col_t, col_i, col_lev = st.columns([2, 2, 2, 1])
    with col_r:
        sel_regions = st.multiselect("Region", regions, placeholder="All regions")
    with col_t:
        sel_types = st.multiselect("Product Type", types, placeholder="All types")
    with col_i:
        sel_issuers = st.multiselect("Issuer", issuers, placeholder="All issuers")
    with col_lev:
        show_leveraged = st.toggle("Include Leveraged", value=True)

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = CORE_EQUITY_REGISTRY
    if sel_regions:
        filtered = [p for p in filtered if p.region in sel_regions]
    if sel_types:
        filtered = [p for p in filtered if p.product_type in sel_types]
    if sel_issuers:
        filtered = [p for p in filtered if p.issuer in sel_issuers]
    if not show_leveraged:
        filtered = [p for p in filtered if abs(p.leverage) == 1.0]

    st.caption(f"Showing {len(filtered)} instruments")

    # ── Live prices ───────────────────────────────────────────────────────────
    tickers_yf = tuple(p.yf_ticker or p.ticker for p in filtered if not p.ticker.endswith(".L"))
    prices = _live_prices(tickers_yf) if tickers_yf else {}

    # ── Pagination ────────────────────────────────────────────────────────────
    total_pages = max(1, (len(filtered) + _PAGE_SIZE - 1) // _PAGE_SIZE)
    page_key = "core_equity_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    page = st.session_state[page_key]
    page = max(0, min(page, total_pages - 1))

    c_prev, c_info, c_next = st.columns([1, 3, 1])
    with c_prev:
        if st.button("← Prev", key="ce_prev", disabled=page == 0):
            st.session_state[page_key] = page - 1
            st.rerun()
    with c_info:
        st.caption(f"Page {page + 1} / {total_pages}")
    with c_next:
        if st.button("Next →", key="ce_next", disabled=page >= total_pages - 1):
            st.session_state[page_key] = page + 1
            st.rerun()

    page_items = filtered[page * _PAGE_SIZE : (page + 1) * _PAGE_SIZE]

    # ── Table ─────────────────────────────────────────────────────────────────
    rows = []
    for p in page_items:
        yf_key = p.yf_ticker or p.ticker
        px_data = prices.get(yf_key, {})
        price   = px_data.get("price")
        chg     = px_data.get("chg_pct")
        rows.append({
            "Ticker":     p.ticker,
            "Name":       p.name,
            "Region":     p.region,
            "Index":      p.index_tracked,
            "Type":       p.product_type,
            "Leverage":   f"{p.leverage:+.0f}×" if p.leverage != 1.0 else "1×",
            "Exp Ratio":  f"{p.expense_ratio:.2f}%" if p.expense_ratio else "—",
            "AUM ($bn)":  f"{p.aum_bn:.1f}" if p.aum_bn else "—",
            "Issuer":     p.issuer or "—",
            "Price":      f"${price:,.2f}" if price else "—",
            "1d %":       f"{chg:+.2f}%" if chg is not None else "—",
        })

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "1d %": st.column_config.TextColumn("1d %"),
            "Leverage": st.column_config.TextColumn("Lev."),
        },
    )

    # ── Region Breakdown Chart ────────────────────────────────────────────────
    st.divider()
    st.markdown("### Regional distribution")
    region_counts = {}
    for p in CORE_EQUITY_REGISTRY:
        region_counts[p.region] = region_counts.get(p.region, 0) + 1
    chart_df = pd.DataFrame(
        [{"Region": k, "Count": v} for k, v in sorted(region_counts.items(), key=lambda x: -x[1])]
    )
    fig = px.bar(
        chart_df, x="Region", y="Count", color="Count",
        color_continuous_scale=[[0, "#2E3140"], [1, "#00D4AA"]],
        template="plotly_dark",
    )
    fig.update_layout(
        height=260, margin={"t": 10, "b": 40, "l": 0, "r": 0},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
