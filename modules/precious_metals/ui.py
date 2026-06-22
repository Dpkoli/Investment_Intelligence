"""Precious Metals module — Streamlit renderer."""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from .data import METALS_REGISTRY, MetalType, fetch_prices, _SPOT_TICKERS, _ETP_TICKERS_US

_METAL_COLOR = {
    MetalType.GOLD:      "#FFD700",
    MetalType.SILVER:    "#C0C0C0",
    MetalType.PLATINUM:  "#E5E4E2",
    MetalType.PALLADIUM: "#CED0DD",
}


@st.cache_data(ttl=120, show_spinner=False)
def _prices() -> dict:
    return fetch_prices()


def _price_card(metal: str, yf_ticker: str, prices: dict) -> None:
    px_data = prices.get(yf_ticker, {})
    price   = px_data.get("price")
    chg     = px_data.get("chg_pct")
    mt = MetalType(metal) if metal in [m.value for m in MetalType] else MetalType.GOLD
    color = _METAL_COLOR.get(mt, "#FFD700")
    price_str = f"${price:,.2f}" if price else "—"
    chg_color = "#00D4AA" if (chg is not None and chg >= 0) else "#FF4B4B"
    chg_str   = f"{chg:+.2f}%" if chg is not None else "—"
    st.markdown(
        f"""<div style="background:#1A1D24;border:1px solid #2E3140;border-left:3px solid {color};
            border-radius:8px;padding:0.75rem 1.2rem;text-align:center">
            <div style="font-size:0.72rem;color:{color};font-weight:700;letter-spacing:0.1em">{metal.upper()}</div>
            <div style="font-size:1.5rem;font-weight:700;margin:0.2rem 0">{price_str}</div>
            <div style="font-size:0.85rem;color:{chg_color}">{chg_str}</div>
            <div style="font-size:0.68rem;color:#888;margin-top:0.2rem">troy oz {yf_ticker}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def render() -> None:
    st.markdown("## 🥇 Precious Metals — Spot, Physical ETPs & Mining Equity")
    st.caption(f"{len(METALS_REGISTRY)} products tracked — Gold · Silver · Platinum · Palladium")

    prices = _prices()

    # ── Live Spot Prices ──────────────────────────────────────────────────────
    st.markdown("### Live Spot & Futures")
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        _price_card("Gold",      "GC=F",  prices)
    with sc2:
        _price_card("Silver",    "SI=F",  prices)
    with sc3:
        _price_card("Platinum",  "PL=F",  prices)
    with sc4:
        _price_card("Palladium", "PA=F",  prices)

    st.divider()

    # ── Filters ───────────────────────────────────────────────────────────────
    metals  = sorted(set(p.metal.value for p in METALS_REGISTRY))
    ptypes  = sorted(set(p.product_type for p in METALS_REGISTRY))
    exchanges = sorted(set(p.exchange for p in METALS_REGISTRY))

    col_m, col_pt, col_ex = st.columns(3)
    with col_m:
        sel_metals = st.multiselect("Metal", metals, placeholder="All metals")
    with col_pt:
        sel_types = st.multiselect("Product Type", ptypes, placeholder="All types")
    with col_ex:
        sel_ex = st.multiselect("Exchange", exchanges, placeholder="All exchanges")

    show_phys = st.toggle("Physically-backed only", value=False)

    filtered = METALS_REGISTRY
    if sel_metals:
        filtered = [p for p in filtered if p.metal.value in sel_metals]
    if sel_types:
        filtered = [p for p in filtered if p.product_type in sel_types]
    if sel_ex:
        filtered = [p for p in filtered if p.exchange in sel_ex]
    if show_phys:
        filtered = [p for p in filtered if p.physically_backed]

    st.caption(f"Showing {len(filtered)} products")

    # ── ETP Price Cards ───────────────────────────────────────────────────────
    top_etps = [p for p in filtered if p.product_type == "Physical ETP" and p.yf_ticker and p.aum_bn and p.aum_bn >= 1.0][:6]
    if top_etps:
        cols = st.columns(len(top_etps))
        for col, etp in zip(cols, top_etps):
            px_data = prices.get(etp.yf_ticker, {})
            price   = px_data.get("price")
            chg     = px_data.get("chg_pct")
            color   = _METAL_COLOR.get(etp.metal, "#FFD700")
            with col:
                st.markdown(
                    f"""<div style="background:#1A1D24;border:1px solid {color}33;border-top:2px solid {color};
                        border-radius:6px;padding:0.5rem;text-align:center">
                        <div style="font-size:0.7rem;color:{color};font-weight:700">{etp.ticker}</div>
                        <div style="font-weight:700">${price:,.2f}</div>
                        <div style="font-size:0.75rem;color:{'#00D4AA' if (chg or 0) >= 0 else '#FF4B4B'}">{f'{chg:+.2f}%' if chg is not None else '—'}</div>
                        <div style="font-size:0.65rem;color:#888">{etp.issuer}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── Product Table ─────────────────────────────────────────────────────────
    rows = []
    for p in filtered:
        yf_key = p.yf_ticker or ""
        px_data = prices.get(yf_key, {})
        price   = px_data.get("price")
        chg     = px_data.get("chg_pct")
        rows.append({
            "Ticker":      p.ticker,
            "Name":        p.name,
            "Metal":       p.metal.value,
            "Type":        p.product_type,
            "Exchange":    p.exchange,
            "Phys. Backed":("✅" if p.physically_backed else "—"),
            "Lev.":        (f"{p.leverage:+.0f}×" if p.leverage != 1.0 else "1×"),
            "TER":         (f"{p.expense_ratio:.2f}%" if p.expense_ratio else "—"),
            "AUM ($bn)":   (f"{p.aum_bn:.1f}" if p.aum_bn else "—"),
            "Issuer":      (p.issuer or "—"),
            "Price":       (f"${price:,.2f}" if price else "—"),
            "1d %":        (f"{chg:+.2f}%" if chg is not None else "—"),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Notes on Streaming / Royalty ─────────────────────────────────────────
    st.divider()
    with st.expander("💡 Streaming & Royalty Companies (Equity plays)", expanded=False):
        streaming = [p for p in METALS_REGISTRY if p.product_type == "Streaming Equity"]
        st.markdown("""
Streaming and royalty companies provide **capital-efficient** exposure to precious metals production:
- **No operational mining risk** — royalties are paid on production regardless of cost escalation
- **Natural hedge** — gold/silver price upside with capped downside (no mine cost exposure)
- **Valuation premium** — typically trade at 30-50× P/CF vs. 8-15× for miners
        """)
        for s in streaming:
            st.markdown(f"**{s.ticker}** — {s.name}: {s.notes or ''}")
