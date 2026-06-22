"""Sovereign Crypto Networks — Streamlit renderer (70+ assets + FCA compliance)."""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .data import CRYPTO_REGISTRY, CryptoTier, FCAStatus, ALL_TIERS

_PAGE_SIZE = 20
_FCA_COLOR = {
    FCAStatus.REGULATED_ETP:  "#00D4AA",
    FCAStatus.REGISTERED:     "#4ADE80",
    FCAStatus.PENDING:        "#FFA500",
    FCAStatus.GRANDFATHERED:  "#FFA500",
    FCAStatus.UNREGISTERED:   "#FF6B6B",
    FCAStatus.NOT_APPLICABLE: "#888",
}
_TIER_COLOR = {
    CryptoTier.STORE_OF_VALUE: "#F7931A",
    CryptoTier.SMART_CONTRACT: "#627EEA",
    CryptoTier.LAYER_2:        "#9F44D3",
    CryptoTier.DEFI:           "#00D4AA",
    CryptoTier.EXCHANGE_TOKEN: "#F3BA2F",
    CryptoTier.PAYMENTS:       "#26A17B",
    CryptoTier.AI_DATA:        "#61DAFB",
    CryptoTier.GAMING_NFT:     "#FF6BD6",
    CryptoTier.PRIVACY:        "#888",
    CryptoTier.STORAGE:        "#A8C7FA",
    CryptoTier.STABLECOIN:     "#2775CA",
    CryptoTier.WRAPPED:        "#E84142",
    CryptoTier.MEME:           "#FF4B4B",
    CryptoTier.LSE_ETP:        "#00D4AA",
    CryptoTier.GLOBAL_TRUST:   "#FFA500",
}


@st.cache_data(ttl=120, show_spinner=False)
def _live_prices(tickers: tuple[str, ...]) -> dict:
    try:
        import yfinance as yf
        data: dict = {}
        batch = yf.download(list(tickers), period="2d", auto_adjust=True,
                            progress=False, threads=True)
        closes = batch.get("Close", batch)
        if closes is None or closes.empty:
            return data
        last = closes.iloc[-1]
        prev = closes.iloc[-2] if len(closes) >= 2 else closes.iloc[-1]
        for t in tickers:
            try:
                p  = float(last[t]) if t in last.index else None
                p0 = float(prev[t]) if t in prev.index else None
                pct = round((p - p0) / p0 * 100, 2) if p and p0 and p0 != 0 else None
                data[t] = {"price": round(p, 6) if p else None, "chg_pct": pct}
            except Exception:
                pass
        return data
    except Exception:
        return {}


def _fca_badge(status: FCAStatus) -> str:
    color = _FCA_COLOR.get(status, "#888")
    return f'<span style="background:rgba(0,0,0,0.3);border:1px solid {color};color:{color};border-radius:4px;padding:2px 6px;font-size:0.72rem;font-weight:700">{status.value}</span>'


def render() -> None:
    st.markdown("## ₿ Sovereign Crypto Networks")
    st.caption(f"{len(CRYPTO_REGISTRY)} assets tracked — Native Tokens · LSE ETPs · Global Trusts · FCA Compliance Status")

    # ── Summary KPIs ──────────────────────────────────────────────────────────
    total = len(CRYPTO_REGISTRY)
    lse_etps   = sum(1 for a in CRYPTO_REGISTRY if a.tier == CryptoTier.LSE_ETP)
    regulated  = sum(1 for a in CRYPTO_REGISTRY if a.fca_status == FCAStatus.REGULATED_ETP)
    pending    = sum(1 for a in CRYPTO_REGISTRY if a.fca_status == FCAStatus.PENDING)
    at_risk    = sum(1 for a in CRYPTO_REGISTRY if a.fca_status == FCAStatus.UNREGISTERED and a.tier not in (CryptoTier.GLOBAL_TRUST,))

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Assets", total)
    k2.metric("LSE ETPs", lse_etps, help="FCA-supervised exchange-listed products")
    k3.metric("FCA Regulated", regulated, delta=None)
    k4.metric("FCA Pending", pending, delta=None)
    k5.metric("At Risk (Unregistered)", at_risk, delta=None)

    st.divider()

    # ── Tier composition donut ────────────────────────────────────────────────
    col_chart, col_filters = st.columns([1, 2])
    with col_chart:
        tier_counts = {}
        for a in CRYPTO_REGISTRY:
            tier_counts[a.tier.value] = tier_counts.get(a.tier.value, 0) + 1
        fig_donut = go.Figure(go.Pie(
            labels=list(tier_counts.keys()),
            values=list(tier_counts.values()),
            hole=0.62,
            marker_colors=[_TIER_COLOR.get(t, "#888") for t in [CryptoTier(k) for k in tier_counts]],
            textinfo="none",
        ))
        fig_donut.update_layout(
            height=220, margin={"t": 5, "b": 5, "l": 5, "r": 5},
            paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
            annotations=[{"text": f"<b>{total}</b><br>assets", "x": 0.5, "y": 0.5,
                          "font_size": 14, "showarrow": False, "font_color": "#fafafa"}],
        )
        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

    with col_filters:
        sel_tiers = st.multiselect("Tier", ALL_TIERS, placeholder="All tiers")
        sel_fca   = st.multiselect("FCA Status", [s.value for s in FCAStatus], placeholder="All statuses")
        col_a, col_b = st.columns(2)
        with col_a:
            sel_exchange = st.multiselect("Exchange", sorted(set(a.exchange for a in CRYPTO_REGISTRY)), placeholder="All")
        with col_b:
            search = st.text_input("Search ticker / name", "")

    # ── Filter ────────────────────────────────────────────────────────────────
    filtered = CRYPTO_REGISTRY
    if sel_tiers:
        filtered = [a for a in filtered if a.tier.value in sel_tiers]
    if sel_fca:
        filtered = [a for a in filtered if a.fca_status.value in sel_fca]
    if sel_exchange:
        filtered = [a for a in filtered if a.exchange in sel_exchange]
    if search:
        q = search.lower()
        filtered = [a for a in filtered if q in a.ticker.lower() or q in a.name.lower()]

    st.caption(f"Showing {len(filtered)} assets")

    # ── Pagination ────────────────────────────────────────────────────────────
    total_pages = max(1, (len(filtered) + _PAGE_SIZE - 1) // _PAGE_SIZE)
    page_key = "crypto_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    page = max(0, min(st.session_state[page_key], total_pages - 1))

    pc1, pc2, pc3 = st.columns([1, 3, 1])
    with pc1:
        if st.button("← Prev", key="cr_prev", disabled=page == 0):
            st.session_state[page_key] = page - 1
            st.rerun()
    with pc2:
        st.caption(f"Page {page + 1} / {total_pages}")
    with pc3:
        if st.button("Next →", key="cr_next", disabled=page >= total_pages - 1):
            st.session_state[page_key] = page + 1
            st.rerun()

    page_items = filtered[page * _PAGE_SIZE : (page + 1) * _PAGE_SIZE]

    # ── Live prices ───────────────────────────────────────────────────────────
    yf_tickers = tuple(a.yf_ticker for a in page_items if a.yf_ticker)
    prices = _live_prices(yf_tickers) if yf_tickers else {}

    # ── FCA-aware card grid ───────────────────────────────────────────────────
    for asset in page_items:
        px_data = prices.get(asset.yf_ticker or "", {})
        price   = px_data.get("price")
        chg     = px_data.get("chg_pct")
        fca_color = _FCA_COLOR.get(asset.fca_status, "#888")
        tier_color = _TIER_COLOR.get(asset.tier, "#888")

        price_str = f"${price:,.6f}".rstrip("0").rstrip(".") if price and price < 0.01 else (f"${price:,.4f}" if price and price < 1 else (f"${price:,.2f}" if price else "—"))
        chg_str   = (f'<span style="color:{"#00D4AA" if chg >= 0 else "#FF4B4B"}">{chg:+.2f}%</span>' if chg is not None else '<span style="color:#888">—</span>')

        aum_str = (f"AUM: £{asset.aum_mn:,.0f}mn" if asset.aum_mn else "")
        ter_str = (f"  ·  TER: {asset.ter:.2f}%" if asset.ter else "")
        notes_str = (f'<br><span style="color:#888;font-size:0.72rem">⚠ {asset.notes}</span>' if asset.notes else "")

        st.markdown(
            f"""<div style="background:#1A1D24;border:1px solid #2E3140;border-left:3px solid {fca_color};
                border-radius:8px;padding:0.55rem 1rem;margin-bottom:0.35rem;display:flex;align-items:center;gap:1rem">
                <span style="font-size:0.72rem;font-weight:700;color:{tier_color};min-width:90px">{asset.tier.value[:12]}</span>
                <span style="font-weight:700;min-width:80px">{asset.ticker}</span>
                <span style="flex:1">{asset.name}</span>
                <span style="min-width:90px;text-align:right">{price_str}</span>
                <span style="min-width:70px;text-align:right">{chg_str}</span>
                <span style="min-width:130px;text-align:right">{_fca_badge(asset.fca_status)}</span>
                <span style="color:#888;font-size:0.72rem;min-width:80px;text-align:right">{aum_str}{ter_str}</span>
            </div>{notes_str}""",
            unsafe_allow_html=True,
        )

    # ── LSE ETP Deep-Dive ─────────────────────────────────────────────────────
    st.divider()
    with st.expander("📋 LSE ETP Compliance Deep-Dive", expanded=False):
        lse_items = [a for a in CRYPTO_REGISTRY if a.tier == CryptoTier.LSE_ETP]
        lse_rows = [{
            "Ticker": a.ticker, "Name": a.name, "Issuer": a.issuer or "—",
            "AUM (£mn)": f"{a.aum_mn:,.0f}" if a.aum_mn else "—",
            "TER": f"{a.ter:.2f}%" if a.ter else "—",
            "FCA Status": a.fca_status.value,
            "Notes": a.notes or "—",
        } for a in lse_items]
        st.dataframe(pd.DataFrame(lse_rows), use_container_width=True, hide_index=True)

    with st.expander("🌍 Global Trusts & US-Listed Products", expanded=False):
        us_items = [a for a in CRYPTO_REGISTRY if a.tier == CryptoTier.GLOBAL_TRUST]
        us_rows = [{
            "Ticker": a.ticker, "Name": a.name, "Issuer": a.issuer or "—",
            "AUM (mn)": f"${a.aum_mn:,.0f}" if a.aum_mn else "—",
            "TER": f"{a.ter:.2f}%" if a.ter else "—",
            "Notes": a.notes or "—",
        } for a in us_items]
        st.dataframe(pd.DataFrame(us_rows), use_container_width=True, hide_index=True)
