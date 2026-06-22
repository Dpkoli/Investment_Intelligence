#!/usr/bin/env python3
"""
Contrarian Radar — Production Streamlit Dashboard
Phase 4: Full UI/UX Consolidation

Zone 1 : Cassandra alert ticker  +  Kingmaker endorsement banner
Zone 2 : Poly-Exposure Taxonomy Grid (6 tabs)
Zone 3 : UK 2026-2027 Regulatory Sandbox
Sidebar : What-If Contrarian Score Simulator
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta
from typing import Any, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# ── Ensure repo root is importable ────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── Internal imports ──────────────────────────────────────────────────────────
from etl.client import SupabaseClient
from etl.config import KINGMAKER_CANDIDATES, TITANS
from analytics.scoring import ScoringEngine, ScoreResult, CSComponents
from analytics.compliance.fca_checkpoints import (
    ENFORCEMENT_DATE,
    GATEWAY_CLOSE_DATE,
    GATEWAY_OPEN_DATE,
    current_phase,
    days_to_enforcement,
    days_to_gateway_close,
    days_to_gateway_open,
    phase_narrative,
    upcoming_milestones,
)
from analytics.compliance.uk_crypto_matrix import (
    UKCryptoComplianceMatrix,
    _INSTRUMENT_REGISTRY,
)

# ═════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG  (must be the first Streamlit call)
# ═════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Contrarian Radar",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Contrarian Radar — Institutional-grade asymmetric intelligence platform."},
)

# ═════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ═════════════════════════════════════════════════════════════════════════════

st.markdown(
    """
    <style>
    /* ── Root overrides ── */
    :root {
        --accent:   #00D4AA;
        --danger:   #FF4B4B;
        --warn:     #FFA500;
        --dim:      #888;
        --card-bg:  #1A1D24;
        --border:   #2E3140;
    }
    .block-container { padding-top: 1rem; }

    /* ── Metric cards ── */
    div[data-testid="metric-container"] {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 0.6rem 1rem;
    }

    /* ── Zone headers ── */
    .zone-header {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--dim);
        margin-bottom: 0.4rem;
    }

    /* ── Banner strips ── */
    .banner-card {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
    }
    .banner-card-critical { border-left: 4px solid var(--danger); }
    .banner-card-warn     { border-left: 4px solid var(--warn); }
    .banner-card-ok       { border-left: 4px solid var(--accent); }

    /* ── Survival badges ── */
    .badge-green    { background:#1a3d2e; color:#00D4AA; border-radius:4px; padding:2px 8px; font-size:0.75rem; font-weight:700; }
    .badge-amber    { background:#3d2e1a; color:#FFA500; border-radius:4px; padding:2px 8px; font-size:0.75rem; font-weight:700; }
    .badge-red      { background:#3d1a1a; color:#FF6B6B; border-radius:4px; padding:2px 8px; font-size:0.75rem; font-weight:700; }
    .badge-critical { background:#5c1a1a; color:#FF2222; border-radius:4px; padding:2px 8px; font-size:0.75rem; font-weight:700; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.55} }

    /* ── Asymmetry flag ── */
    .asymmetry-flag {
        background: linear-gradient(90deg, #1a3d2e, #0E1117);
        border: 1px solid var(--accent);
        border-radius: 6px;
        padding: 0.6rem 1rem;
        margin-bottom: 0.35rem;
    }

    /* ── Ticker tape ── */
    .ticker-item { font-size: 0.82rem; margin-bottom: 0.3rem; }
    .score-pill {
        display: inline-block;
        border-radius: 12px;
        padding: 1px 8px;
        font-size: 0.73rem;
        font-weight: 700;
        margin-right: 0.4rem;
    }
    .pill-9 { background:#7a1a1a; color:#ff4444; }
    .pill-8 { background:#7a3d1a; color:#ff8c00; }
    .pill-7 { background:#4a3d00; color:#ffd700; }
    .pill-6 { background:#1a3d00; color:#7fff00; }
    .pill-low { background:#1a2a1a; color:#888; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ═════════════════════════════════════════════════════════════════════════════
# STATIC DEMO DATA  (used when Supabase returns empty results)
# ═════════════════════════════════════════════════════════════════════════════

_CASSANDRA_DEMO: list[dict] = [
    {"title": "Texas ERCOT grid: AI data-centre load 340% above 2023 baseline — brownout risk Q4 2026",
     "risk_score": 9, "vector": "energy_risk",    "source": "energymonitor.ai"},
    {"title": "Global transformer shortage: 24-36 month lead times flagged by major grid operators",
     "risk_score": 8, "vector": "energy_risk",    "source": "datacenterknowledge.com"},
    {"title": "China grid-export restrictions: 60 Hz transformer exports halted from Q3 2026",
     "risk_score": 9, "vector": "energy_risk",    "source": "energymonitor.ai"},
    {"title": "Tether (USDT) reserve audit delayed for 4th consecutive quarter — contagion risk",
     "risk_score": 7, "vector": "crypto_risk",    "source": "protos.com"},
    {"title": "Coinbase custody concentration: 42% of all US crypto ETF assets at single entity",
     "risk_score": 7, "vector": "crypto_risk",    "source": "theblock.co"},
    {"title": "Deutsche Bank systemic leverage ratio breach flagged in ECB quarterly review",
     "risk_score": 8, "vector": "systemic_risk",  "source": "wolfstreet.com"},
    {"title": "Virginia Northern data-centre cluster: water-cooling capacity at 96% utilisation",
     "risk_score": 6, "vector": "energy_risk",    "source": "datacenterknowledge.com"},
    {"title": "XRP 9th Circuit appeal creates renewed legal uncertainty for exchange listings",
     "risk_score": 5, "vector": "crypto_risk",    "source": "theblock.co"},
]

_KINGMAKER_DEMO: list[dict] = [
    {"titan": "NVDA", "titan_name": "NVIDIA", "executive": "Jensen Huang",
     "vendor": "Marvell Technology", "vendor_ticker": "MRVL",
     "type": "Custom_Silicon", "confidence": 9,
     "quote": "Marvell is our primary custom ASIC partner — sole-source for ConnectX series"},
    {"titan": "NVDA", "titan_name": "NVIDIA", "executive": "Jensen Huang",
     "vendor": "Super Micro Computer", "vendor_ticker": "SMCI",
     "type": "Supplier", "confidence": 7,
     "quote": "~35% of HGX unit shipments flow through SuperMicro"},
    {"titan": "GOOGL", "titan_name": "Google", "executive": "Sundar Pichai",
     "vendor": "Cadence Design", "vendor_ticker": "CDNS",
     "type": "Custom_Silicon", "confidence": 8,
     "quote": "Cadence handles 100% of our TPU v5 verification flows"},
    {"titan": "AMZN", "titan_name": "Amazon", "executive": "Andy Jassy",
     "vendor": "Arista Networks", "vendor_ticker": "ANET",
     "type": "JV_Partner", "confidence": 8,
     "quote": "Arista is exclusive switching fabric partner for AWS Nitro SuperCluster"},
    {"titan": "MSFT", "titan_name": "Microsoft", "executive": "Satya Nadella",
     "vendor": "Coherent Corp", "vendor_ticker": "COHR",
     "type": "Supplier", "confidence": 7,
     "quote": "Coherent 800G transceivers underpin our Azure AI fabric at scale"},
]

_SP500_ASSETS = [
    {"Ticker": "SPY",  "Name": "SPDR S&P 500 ETF Trust",          "AUM ($bn)": 547.2, "Exp Ratio": "0.0945%", "Type": "Index"},
    {"Ticker": "IVV",  "Name": "iShares Core S&P 500 ETF",        "AUM ($bn)": 490.1, "Exp Ratio": "0.03%",   "Type": "Index"},
    {"Ticker": "VOO",  "Name": "Vanguard S&P 500 ETF",            "AUM ($bn)": 562.8, "Exp Ratio": "0.03%",   "Type": "Index"},
    {"Ticker": "QQQ",  "Name": "Invesco QQQ Trust",               "AUM ($bn)": 311.4, "Exp Ratio": "0.20%",   "Type": "Index"},
    {"Ticker": "SSO",  "Name": "ProShares Ultra S&P 500 (2×)",    "AUM ($bn)": 4.8,   "Exp Ratio": "0.89%",   "Type": "Leveraged 2×"},
    {"Ticker": "SPXL", "Name": "Direxion Daily S&P 500 Bull 3×",  "AUM ($bn)": 2.9,   "Exp Ratio": "1.01%",   "Type": "Leveraged 3×"},
    {"Ticker": "TQQQ", "Name": "ProShares UltraPro QQQ (3×)",     "AUM ($bn)": 25.3,  "Exp Ratio": "0.88%",   "Type": "Leveraged 3×"},
    {"Ticker": "UPRO", "Name": "ProShares UltraPro S&P 500 (3×)", "AUM ($bn)": 3.4,   "Exp Ratio": "0.93%",   "Type": "Leveraged 3×"},
]

_FTSE_ASSETS = [
    {"Ticker": "ISF",  "Name": "iShares Core FTSE 100",           "AUM (£bn)": 14.2, "Exp Ratio": "0.07%", "Exchange": "LSE"},
    {"Ticker": "VMID", "Name": "Vanguard FTSE 250 ETF",           "AUM (£bn)": 2.8,  "Exp Ratio": "0.10%", "Exchange": "LSE"},
    {"Ticker": "VUKE", "Name": "Vanguard FTSE 100 ETF",           "AUM (£bn)": 4.1,  "Exp Ratio": "0.09%", "Exchange": "LSE"},
    {"Ticker": "IGLT", "Name": "iShares Core UK Gilts",           "AUM (£bn)": 5.3,  "Exp Ratio": "0.07%", "Exchange": "LSE"},
    {"Ticker": "XDUK", "Name": "Xtrackers FTSE 100 Swap ETF",     "AUM (£bn)": 1.2,  "Exp Ratio": "0.09%", "Exchange": "LSE"},
    {"Ticker": "CUKX", "Name": "iShares FTSE 100 GBP Hedged",     "AUM (£bn)": 0.8,  "Exp Ratio": "0.20%", "Exchange": "LSE"},
]

_EM_ASSETS = [
    {"Ticker": "VWO",  "Name": "Vanguard FTSE Emerging Markets",  "AUM ($bn)": 91.2,  "Region": "Global EM",  "Exp Ratio": "0.08%"},
    {"Ticker": "IEMG", "Name": "iShares Core MSCI EM",            "AUM ($bn)": 74.3,  "Region": "Global EM",  "Exp Ratio": "0.09%"},
    {"Ticker": "EEM",  "Name": "iShares MSCI EM ETF",             "AUM ($bn)": 18.4,  "Region": "Global EM",  "Exp Ratio": "0.68%"},
    {"Ticker": "INDA", "Name": "iShares MSCI India ETF",          "AUM ($bn)": 10.8,  "Region": "India",      "Exp Ratio": "0.65%"},
    {"Ticker": "EWZ",  "Name": "iShares MSCI Brazil ETF",         "AUM ($bn)": 3.1,   "Region": "Brazil",     "Exp Ratio": "0.57%"},
    {"Ticker": "GXC",  "Name": "SPDR S&P China ETF",             "AUM ($bn)": 0.7,   "Region": "China",      "Exp Ratio": "0.59%"},
    {"Ticker": "EPHE", "Name": "iShares MSCI Philippines ETF",    "AUM ($bn)": 0.15,  "Region": "Philippines","Exp Ratio": "0.57%"},
]

_METALS_ASSETS = [
    {"Ticker": "GLD",  "Name": "SPDR Gold Shares",                 "Metal": "Gold",   "AUM ($bn)": 70.2, "Exp Ratio": "0.40%", "Exchange": "NYSE"},
    {"Ticker": "IAU",  "Name": "iShares Gold Trust",               "Metal": "Gold",   "AUM ($bn)": 34.7, "Exp Ratio": "0.25%", "Exchange": "NYSE"},
    {"Ticker": "PHAU", "Name": "WisdomTree Physical Gold (LSE)",    "Metal": "Gold",   "AUM (£bn)": 8.2,  "Exp Ratio": "0.15%", "Exchange": "LSE"},
    {"Ticker": "SGOL", "Name": "abrdn Physical Gold ETC",          "Metal": "Gold",   "AUM ($bn)": 3.2,  "Exp Ratio": "0.17%", "Exchange": "NYSE"},
    {"Ticker": "SLV",  "Name": "iShares Silver Trust",             "Metal": "Silver", "AUM ($bn)": 11.3, "Exp Ratio": "0.50%", "Exchange": "NYSE"},
    {"Ticker": "SSLN", "Name": "WisdomTree Physical Silver (LSE)", "Metal": "Silver", "AUM (£bn)": 0.9,  "Exp Ratio": "0.19%", "Exchange": "LSE"},
]

_SPOT_CRYPTO = [
    {"Ticker": "BTC", "Name": "Bitcoin",      "Price (USD)": 105_234,  "Mkt Cap ($bn)": 2_087},
    {"Ticker": "ETH", "Name": "Ethereum",     "Price (USD)": 3_890,    "Mkt Cap ($bn)": 468},
    {"Ticker": "SOL", "Name": "Solana",       "Price (USD)": 188.40,   "Mkt Cap ($bn)": 89},
    {"Ticker": "XRP", "Name": "XRP (Ripple)", "Price (USD)": 2.34,     "Mkt Cap ($bn)": 134},
]

_ETP_CRYPTO = [
    {"Ticker": "IB1T", "Name": "iShares Bitcoin ETP",        "Issuer": "BlackRock",   "AUM (£mn)": 3_200, "TER": "0.15%"},
    {"Ticker": "BITB", "Name": "CoinShares Physical Bitcoin", "Issuer": "CoinShares",  "AUM (£mn)": 890,   "TER": "0.25%"},
    {"Ticker": "WBTC", "Name": "WisdomTree Physical Bitcoin", "Issuer": "WisdomTree",  "AUM (£mn)": 680,   "TER": "0.35%"},
    {"Ticker": "WETH", "Name": "WisdomTree Physical Ethereum","Issuer": "WisdomTree",  "AUM (£mn)": 240,   "TER": "0.35%"},
    {"Ticker": "ETHE", "Name": "CoinShares Physical Ethereum","Issuer": "CoinShares",  "AUM (£mn)": 310,   "TER": "0.25%"},
    {"Ticker": "SOLW", "Name": "WisdomTree Physical Solana",  "Issuer": "WisdomTree",  "AUM (£mn)": 95,    "TER": "0.50%"},
    {"Ticker": "XRPL", "Name": "WisdomTree Physical XRP",     "Issuer": "WisdomTree",  "AUM (£mn)": 42,    "TER": "0.50%"},
]

_HORIZON_PIPELINE = [
    {"Filer": "Amplify ETFs",   "Asset": "Amplify AI Power Grid ETF",            "Form": "S-1",   "Filed": "2026-06-05", "Pv": 8.3, "Cc": 0.05, "Class": "Power Grid / AI Infrastructure"},
    {"Filer": "BlackRock",      "Asset": "iShares Spot Solana ETP",              "Form": "N-1A",  "Filed": "2026-05-12", "Pv": 7.2, "Cc": 0.08, "Class": "Spot Solana ETP"},
    {"Filer": "Global X",       "Asset": "Global X Nuclear Energy ETF",          "Form": "S-1",   "Filed": "2026-05-22", "Pv": 6.1, "Cc": 0.09, "Class": "Nuclear Energy"},
    {"Filer": "VanEck",         "Asset": "VanEck Spot XRP ETF",                  "Form": "S-1/A", "Filed": "2026-04-28", "Pv": 6.8, "Cc": 0.12, "Class": "Spot XRP ETF"},
    {"Filer": "WisdomTree",     "Asset": "WisdomTree AI Infrastructure ETF",     "Form": "N-1A",  "Filed": "2026-06-01", "Pv": 5.9, "Cc": 0.15, "Class": "AI Infrastructure"},
    {"Filer": "Invesco",        "Asset": "Invesco Quantum Computing ETF",        "Form": "S-1",   "Filed": "2026-05-30", "Pv": 5.1, "Cc": 0.10, "Class": "Quantum Computing"},
    {"Filer": "ProShares",      "Asset": "ProShares Bitcoin Yield ETF",          "Form": "N-1A",  "Filed": "2026-04-10", "Pv": 4.3, "Cc": 0.18, "Class": "Bitcoin Income"},
    {"Filer": "ARK Invest",     "Asset": "ARK Next Gen Internet ETF (UK)",       "Form": "N-1A",  "Filed": "2026-03-15", "Pv": 4.5, "Cc": 0.22, "Class": "Thematic Tech"},
    {"Filer": "Franklin Temp.", "Asset": "Franklin Blockchain Leaders ETF",      "Form": "S-1",   "Filed": "2026-04-02", "Pv": 3.8, "Cc": 0.28, "Class": "Blockchain"},
    {"Filer": "Fidelity",       "Asset": "Fidelity Ethereum Income ETF",         "Form": "S-1",   "Filed": "2026-05-18", "Pv": 4.1, "Cc": 0.20, "Class": "Ethereum Income"},
]

# ═════════════════════════════════════════════════════════════════════════════
# CACHED DATA LOADERS
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def _get_db() -> Optional[SupabaseClient]:
    try:
        return SupabaseClient()
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def load_cassandra_alerts(limit: int = 20) -> list[dict]:
    db = _get_db()
    if db:
        status, rows = db.table_select(
            "Cassandra_Signals",
            filters={"Status": "Open"},
            columns="Title,Systemic_Risk_Score,Risk_Vector,Source_URL,Created_At",
            limit=limit,
        )
        if status == 200 and rows:
            return sorted(rows, key=lambda r: r.get("Systemic_Risk_Score", 0), reverse=True)
    return _CASSANDRA_DEMO


@st.cache_data(ttl=300, show_spinner=False)
def load_kingmaker_endorsements(limit: int = 10) -> list[dict]:
    db = _get_db()
    if db:
        status, rows = db.table_select(
            "NLP_Signal_Extractions",
            filters={"Endorsement_Flag": True},
            columns="Titan_Ticker,Counterparty_Name,Counterparty_Ticker,Connection_Type,Confidence_Score,Extracted_Text,Endorsement_Source",
            limit=limit,
        )
        if status == 200 and rows:
            return rows
    return _KINGMAKER_DEMO


@st.cache_data(ttl=600, show_spinner=False)
def load_compliance_matrix(ref: Optional[date] = None) -> Any:
    m = UKCryptoComplianceMatrix()
    return m.generate(reference_date=ref)


@st.cache_data(ttl=300, show_spinner=False)
def load_horizon_pipeline() -> list[dict]:
    db = _get_db()
    if db:
        status, rows = db.table_select(
            "Asset_Registry",
            filters={"Is_Pipeline": True},
            columns="Name,Issuer,Filing_Type,Filing_Date,Asset_Class",
            limit=50,
        )
        if status == 200 and rows:
            return rows
    return _HORIZON_PIPELINE


# ═════════════════════════════════════════════════════════════════════════════
# HELPER UTILITIES
# ═════════════════════════════════════════════════════════════════════════════

def _pill(score: int) -> str:
    cls = f"pill-{score}" if score >= 6 else "pill-low"
    return f'<span class="score-pill {cls}">{score}</span>'


def _badge(flag: str) -> str:
    cls_map = {"GREEN": "badge-green", "AMBER": "badge-amber",
               "RED": "badge-red",   "CRITICAL": "badge-critical"}
    cls = cls_map.get(flag, "badge-amber")
    return f'<span class="{cls}">{flag}</span>'


def _countdown(target: date, ref: date) -> str:
    delta = (target - ref).days
    if delta < 0:
        return f"<span style='color:#FF4B4B'>PASSED {abs(delta)}d ago</span>"
    if delta <= 30:
        return f"<span style='color:#FF4B4B font-weight:700'>{delta}d</span>"
    if delta <= 90:
        return f"<span style='color:#FFA500'>{delta}d</span>"
    return f"<span style='color:#00D4AA'>{delta}d</span>"


def _phase_color(phase: str) -> str:
    return {
        "PRE_GATEWAY":       "#4A7C59",
        "GATEWAY_OPEN":      "#FFA500",
        "POST_GATEWAY":      "#CC5500",
        "ENFORCEMENT_CLIFF": "#CC0000",
    }.get(phase, "#666")


def _survival_color(flag: str) -> str:
    return {"GREEN": "#00D4AA", "AMBER": "#FFA500",
            "RED": "#FF6B6B", "CRITICAL": "#FF2222"}.get(flag, "#888")


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR — WHAT-IF CS SIMULATOR
# ═════════════════════════════════════════════════════════════════════════════

def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## 📡 Contrarian Radar")
        st.caption("Institutional asymmetric intelligence platform")
        st.divider()

        st.markdown("### ⚗️ What-If CS Simulator")
        st.caption(
            "Manually set CS formula inputs to simulate the Contrarian Score "
            "for any asset scenario."
        )

        with st.expander("Formula reference", expanded=False):
            st.latex(r"CS = \frac{(P_v \cdot T_i) + \Sigma R_s + (E_m \cdot K_w)}{1 + C_c}")
            st.caption(
                "Pv = Pipeline Velocity  ·  Ti = Inflow Acceleration  ·  "
                "ΣRs = Cassandra Risk  ·  Em = Ecosystem  ·  "
                "Kw = Kingmaker Weight  ·  Cc = Crowding"
            )

        asset_label = st.text_input("Asset name / ticker", value="MRVL — Marvell Technology")

        col_a, col_b = st.columns(2)
        with col_a:
            pv = st.slider("Pv  Pipeline Velocity",   0.0, 10.0, 6.5, 0.5)
            em = st.slider("Em  Ecosystem count",      0.0, 10.0, 8.0, 0.5)
        with col_b:
            ti     = st.slider("Ti  Inflow Accel",    -2.0,  5.0, 0.35, 0.05)
            sum_rs = st.slider("ΣRs Cassandra Risk",   0.0, 80.0, 18.0, 1.0)

        endorsed = st.toggle("Kingmaker Endorsed (Kw = 2.5)", value=True)
        kw = 2.5 if endorsed else 1.0

        cc = st.slider(
            "Cc  Consensus Crowding",
            min_value=0.0, max_value=1.0, value=0.18, step=0.01,
            help="0.0 = no mainstream ownership  ·  1.0 = fully crowded",
        )

        # ── Compute ──────────────────────────────────────────────────────────
        engine = ScoringEngine()
        comp   = CSComponents(
            asset_id=0, asset_name=asset_label,
            pv=pv, ti=ti, sum_rs=sum_rs, em=em, kw=kw, cc=cc,
        )
        result = engine.score_components(comp)

        st.divider()
        cs_color = "#00D4AA" if result.cs >= 15 else "#FFA500" if result.cs >= 7 else "#888"
        st.markdown(
            f"<h2 style='text-align:center; color:{cs_color};'>"
            f"CS = {result.cs:.2f}</h2>",
            unsafe_allow_html=True,
        )

        flag_cols = st.columns(3)
        with flag_cols[0]:
            st.metric("Asymmetry Play",
                      "✅ YES" if result.is_asymmetry_play else "❌ NO")
        with flag_cols[1]:
            st.metric("Cassandra Risk",
                      "⚠️ YES" if result.is_cassandra_risk else "✅ NO")
        with flag_cols[2]:
            st.metric("Endorsed",
                      "🚀 YES" if result.is_kingmaker_endorsed else "— NO")

        # ── Cc sensitivity sparkline ──────────────────────────────────────────
        st.markdown("**Cc sensitivity** (holding all else fixed)")
        cc_vals = [i / 100 for i in range(0, 101, 5)]
        cs_vals = []
        for cc_v in cc_vals:
            c2 = comp.model_copy(update={"cc": cc_v})
            cs_vals.append(engine.score_components(c2).cs)

        fig_sens = go.Figure()
        fig_sens.add_trace(go.Scatter(
            x=cc_vals, y=cs_vals, mode="lines",
            line={"color": "#00D4AA", "width": 2},
            fill="tozeroy", fillcolor="rgba(0,212,170,0.08)",
        ))
        fig_sens.add_vline(x=cc, line_dash="dot", line_color="#FFA500", line_width=1)
        fig_sens.update_layout(
            height=140, margin={"t": 5, "b": 5, "l": 0, "r": 0},
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis={"title": "Cc", "color": "#666", "gridcolor": "#2E3140"},
            yaxis={"title": "CS", "color": "#666", "gridcolor": "#2E3140"},
            showlegend=False,
        )
        st.plotly_chart(fig_sens, use_container_width=True, config={"displayModeBar": False})

        # ── Endorsement impact comparison ─────────────────────────────────────
        cs_no_endorse  = engine.score_components(comp.model_copy(update={"kw": 1.0})).cs
        cs_endorsed    = engine.score_components(comp.model_copy(update={"kw": 2.5})).cs
        st.markdown(
            f"**Kw impact:** {cs_no_endorse:.2f} → "
            f"<span style='color:#00D4AA'>{cs_endorsed:.2f}</span> "
            f"(+{cs_endorsed - cs_no_endorse:.2f})",
            unsafe_allow_html=True,
        )

        st.divider()
        st.caption(
            f"📅 Reference date: {date.today()}  |  "
            f"Phase: **{current_phase()}**"
        )


# ═════════════════════════════════════════════════════════════════════════════
# ZONE 1 — CASSANDRA ALERT TICKER + KINGMAKER BANNER
# ═════════════════════════════════════════════════════════════════════════════

def render_zone1() -> None:
    st.markdown('<p class="zone-header">⚡ ZONE 1 — LIVE INTELLIGENCE FEED</p>', unsafe_allow_html=True)

    alerts       = load_cassandra_alerts()
    endorsements = load_kingmaker_endorsements()

    left, right = st.columns([1, 1], gap="medium")

    # ── Left: Cassandra Alert Ticker ─────────────────────────────────────────
    with left:
        st.markdown("**🔴 CASSANDRA ALERT TICKER** — Live macro threats ranked by severity")
        for a in alerts[:8]:
            score = int(a.get("risk_score") or a.get("Systemic_Risk_Score") or 0)
            title = a.get("title") or a.get("Title") or "—"
            vector = (a.get("vector") or a.get("Risk_Vector") or "").replace("_", " ")
            source = a.get("source") or a.get("Source_URL") or ""

            severity_cls = (
                "banner-card-critical" if score >= 8 else
                "banner-card-warn"     if score >= 6 else
                "banner-card-ok"
            )
            st.markdown(
                f"""<div class="banner-card {severity_cls}">
                    <span class="ticker-item">
                        {_pill(score)} <b>{title}</b><br>
                        <span style="color:#888;font-size:0.72rem">
                            {vector.upper()}&nbsp;&nbsp;·&nbsp;&nbsp;{source}
                        </span>
                    </span>
                </div>""",
                unsafe_allow_html=True,
            )

    # ── Right: Kingmaker Endorsement Alerts ──────────────────────────────────
    with right:
        st.markdown("**🚀 KINGMAKER ENDORSEMENT ALERTS** — Named-exec catalyst detections")
        for e in endorsements[:5]:
            titan_name  = e.get("titan_name")  or e.get("Titan_Ticker")   or "—"
            exec_name   = e.get("executive")   or e.get("Endorsement_Source") or "Executive"
            vendor      = e.get("vendor")      or e.get("Counterparty_Name") or "—"
            vticker     = e.get("vendor_ticker") or e.get("Counterparty_Ticker") or ""
            conn_type   = (e.get("type") or e.get("Connection_Type") or "Supplier").replace("_", " ")
            conf        = int(e.get("confidence") or e.get("Confidence_Score") or 7)
            quote       = e.get("quote") or e.get("Extracted_Text") or ""

            vtag = f"({vticker})" if vticker else ""
            st.markdown(
                f"""<div class="banner-card banner-card-ok">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                        <span style="font-size:1.1rem">🏆</span>
                        <b>{titan_name}</b>
                        <span style="color:#888">→</span>
                        <b style="color:#00D4AA">{vendor} {vtag}</b>
                        <span style="color:#888;font-size:0.75rem">{conn_type}</span>
                        {_pill(conf)}
                    </div>
                    <div style="color:#888;font-size:0.77rem;font-style:italic;margin-left:28px">
                        {exec_name}: &ldquo;{quote[:120]}{"…" if len(quote) > 120 else ""}&rdquo;
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )


# ═════════════════════════════════════════════════════════════════════════════
# ZONE 2 — POLY-EXPOSURE TAXONOMY GRID (6 TABS)
# ═════════════════════════════════════════════════════════════════════════════

def render_zone2() -> None:
    st.divider()
    st.markdown('<p class="zone-header">📊 ZONE 2 — POLY-EXPOSURE TAXONOMY GRID</p>',
                unsafe_allow_html=True)

    tabs = st.tabs([
        "🇺🇸 S&P 500 Vectors",
        "🇬🇧 FTSE / UK Sovereign",
        "🌏 Emerging Markets Alpha",
        "🪙 Precious Metals",
        "₿ Sovereign Crypto Networks",
        "🔭 Horizon Pipeline & Asymmetry",
    ])

    with tabs[0]:
        _tab_sp500()
    with tabs[1]:
        _tab_ftse()
    with tabs[2]:
        _tab_em()
    with tabs[3]:
        _tab_metals()
    with tabs[4]:
        _tab_crypto()
    with tabs[5]:
        _tab_horizon()


def _tab_sp500() -> None:
    st.markdown("#### S&P 500 Tracking Vectors — Large-Cap Indices & Leveraged Instruments")
    st.caption(
        "Core index trackers and leveraged products for tactical S&P 500 / Nasdaq exposure. "
        "Leveraged instruments carry daily-reset compounding risk."
    )

    df = pd.DataFrame(_SP500_ASSETS)

    # Colour leveraged rows differently via conditional styling
    def _row_color(row):
        if "3×" in str(row.get("Type", "")):
            return ["background-color: #2a1a1a"] * len(row)
        if "2×" in str(row.get("Type", "")):
            return ["background-color: #2a2a1a"] * len(row)
        return [""] * len(row)

    styled = df.style.apply(_row_color, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # AUM bar chart
    fig = px.bar(
        df, x="Ticker", y="AUM ($bn)", color="Type",
        color_discrete_map={
            "Index": "#00D4AA", "Leveraged 2×": "#FFA500", "Leveraged 3×": "#FF4B4B"
        },
        template="plotly_dark",
        title="AUM by Instrument Type ($bn)",
        height=300,
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin={"t": 40, "b": 20},
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _tab_ftse() -> None:
    st.markdown("#### FTSE / UK Sovereign Equities Core")
    st.caption("LSE-listed large and mid-cap UK equity trackers alongside UK gilt instruments.")

    df = pd.DataFrame(_FTSE_ASSETS)
    st.dataframe(df, use_container_width=True, hide_index=True)

    fig = px.bar(
        df, x="Ticker", y="AUM (£bn)", color_discrete_sequence=["#00D4AA"],
        template="plotly_dark", title="UK Equity ETF AUM (£bn)", height=280,
    )
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin={"t": 40, "b": 20})
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _tab_em() -> None:
    st.markdown("#### Emerging Markets Alpha — Geographic Re-Alignments & Supply-Chain Hubs")
    st.caption(
        "Factor exposure to EM supply chain beneficiaries (India, SE Asia, Brazil) "
        "and broad EM re-rating plays amid US-China decoupling."
    )

    df = pd.DataFrame(_EM_ASSETS)
    st.dataframe(df, use_container_width=True, hide_index=True)

    fig = px.treemap(
        df, path=["Region", "Ticker"], values="AUM ($bn)",
        color="AUM ($bn)", color_continuous_scale="Teal",
        template="plotly_dark", title="AUM Treemap by Region ($bn)",
        height=320,
    )
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin={"t": 40, "b": 5})
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _tab_metals() -> None:
    st.markdown("#### Precious Metals — Spot Pricing Integrated with ETP Fund Metrics")

    # Spot prices (illustrative)
    col_g, col_s = st.columns(2)
    with col_g:
        st.metric("Gold Spot (XAU/USD)", "$3,348.50", delta="+1.2%")
        st.metric("Gold Spot (XAU/GBP)", "£2,640.80", delta="+0.9%")
    with col_s:
        st.metric("Silver Spot (XAG/USD)", "$33.24", delta="+2.1%")
        st.metric("Gold/Silver Ratio",     "100.7×",  delta="-0.8%")

    st.divider()

    df = pd.DataFrame(_METALS_ASSETS)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Dual-axis: AUM by metal type
    gold_df   = df[df["Metal"] == "Gold"]
    silver_df = df[df["Metal"] == "Silver"]

    fig = make_subplots(rows=1, cols=2, subplot_titles=("Gold ETPs — AUM", "Silver ETPs — AUM"))
    fig.add_trace(
        go.Bar(x=gold_df["Ticker"], y=gold_df.get("AUM ($bn)", gold_df.get("AUM (£bn)", 0)),
               marker_color="#FFD700", name="Gold"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(x=silver_df["Ticker"], y=silver_df.get("AUM ($bn)", silver_df.get("AUM (£bn)", 0)),
               marker_color="#C0C0C0", name="Silver"),
        row=1, col=2,
    )
    fig.update_layout(
        height=280, showlegend=False, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin={"t": 40, "b": 10},
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _tab_crypto() -> None:
    st.markdown("#### Sovereign Crypto Networks — Spot Rates, LSE ETPs & Regulatory Status")

    compliance_matrix = load_compliance_matrix()
    flag_map = {r.instrument_id: r.survival_flag for r in compliance_matrix.reports}

    # Spot crypto
    st.markdown("**Spot Crypto Networks**")
    spot_df = pd.DataFrame(_SPOT_CRYPTO)
    st.dataframe(spot_df, use_container_width=True, hide_index=True)

    # LSE ETPs with compliance badge
    st.markdown("**LSE-Listed Crypto ETPs — with FCA Compliance Status**")
    etp_rows = []
    for etp in _ETP_CRYPTO:
        flag = flag_map.get(etp["Ticker"], "AMBER")
        etp_rows.append({**etp, "FCA Status": flag})

    etp_df = pd.DataFrame(etp_rows)

    def _etp_color(row):
        flag = row.get("FCA Status", "")
        colour_map = {"GREEN": "#1a3d2e", "AMBER": "#3d2e1a",
                      "RED": "#3d1a1a",   "CRITICAL": "#5c1a1a"}
        bg = colour_map.get(flag, "")
        return [f"background-color: {bg}" if bg else ""] * len(row)

    st.dataframe(
        etp_df.style.apply(_etp_color, axis=1),
        use_container_width=True, hide_index=True,
    )

    # AUM comparison chart
    aum_vals = [r["AUM (£mn)"] for r in _ETP_CRYPTO]
    colours  = [_survival_color(flag_map.get(r["Ticker"], "AMBER")) for r in _ETP_CRYPTO]
    fig = go.Figure(go.Bar(
        x=[r["Ticker"] for r in _ETP_CRYPTO],
        y=aum_vals,
        marker_color=colours,
        text=[f"£{v:,.0f}mn" for v in aum_vals],
        textposition="outside",
    ))
    fig.update_layout(
        title="LSE Crypto ETP AUM (£mn) — colour = FCA compliance flag",
        height=300, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin={"t": 40, "b": 10},
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _tab_horizon() -> None:
    st.markdown("#### Horizon Pipeline & Asymmetry Finder")
    st.caption(
        "Institutional asset registrations scraped from SEC EDGAR and the FCA Register. "
        "Asymmetry plays = Pv ≥ 4.0 **and** Cc ≤ 0.30 (institutional ramp, low crowding)."
    )

    pipeline = load_horizon_pipeline()
    df = pd.DataFrame(pipeline)

    # Ensure Pv and Cc columns exist
    if "Pv" in df.columns and "Cc" in df.columns:
        df["Asymmetry Play"] = (df["Pv"] >= 4.0) & (df["Cc"] <= 0.30)
    else:
        df["Asymmetry Play"] = False

    # ── Summary metrics ──────────────────────────────────────────────────────
    n_total     = len(df)
    n_asymmetry = int(df["Asymmetry Play"].sum()) if "Asymmetry Play" in df.columns else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Pipeline Filings", n_total)
    m2.metric("Asymmetry Plays (Pv≥4.0, Cc≤0.30)", n_asymmetry)
    m3.metric("Horizon Issuers Tracked", 17)

    # ── Asymmetry scatter ────────────────────────────────────────────────────
    if "Pv" in df.columns and "Cc" in df.columns:
        fig = px.scatter(
            df, x="Cc", y="Pv",
            color="Asymmetry Play",
            color_discrete_map={True: "#00D4AA", False: "#888"},
            hover_name=df.get("Asset") if "Asset" in df.columns else df.index,
            hover_data=["Filer", "Class"] if "Filer" in df.columns else {},
            template="plotly_dark",
            title="Asymmetry Scatter — Pv vs Cc  (top-left quadrant = deep asymmetry)",
            height=340,
            labels={"Cc": "Consensus Crowding (Cc)", "Pv": "Pipeline Velocity (Pv)"},
        )
        # Asymmetry quadrant lines
        fig.add_vline(x=0.30, line_dash="dot", line_color="#FFA500", line_width=1,
                      annotation_text="Cc ≤ 0.30", annotation_position="top")
        fig.add_hline(y=4.0, line_dash="dot",  line_color="#FFA500", line_width=1,
                      annotation_text="Pv ≥ 4.0", annotation_position="right")
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin={"t": 40, "b": 20},
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Full pipeline table (asymmetry plays first) ──────────────────────────
    st.markdown("**All Pipeline Filings**  _(Asymmetry plays highlighted in green)_")

    def _horizon_color(row):
        if row.get("Asymmetry Play"):
            return ["background-color: #1a3d2e"] * len(row)
        return [""] * len(row)

    display_cols = [c for c in ["Asset", "Filer", "Form", "Filed", "Class", "Pv", "Cc", "Asymmetry Play"] if c in df.columns]
    if display_cols:
        st.dataframe(
            df[display_cols].sort_values("Pv", ascending=False).style.apply(_horizon_color, axis=1)
            if "Pv" in df.columns else df[display_cols],
            use_container_width=True, hide_index=True,
        )
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════════════════════════════════════
# ZONE 3 — UK 2026-2027 REGULATORY SANDBOX
# ═════════════════════════════════════════════════════════════════════════════

def render_zone3() -> None:
    st.divider()
    st.markdown('<p class="zone-header">⚖️ ZONE 3 — UK 2026-2027 REGULATORY SANDBOX</p>',
                unsafe_allow_html=True)

    today  = date.today()
    phase  = current_phase(today)

    # ── Phase headline ────────────────────────────────────────────────────────
    phase_col = _phase_color(phase)
    st.markdown(
        f"<div style='background:{phase_col}22; border:1px solid {phase_col}; "
        f"border-radius:8px; padding:0.7rem 1rem; margin-bottom:1rem;'>"
        f"<b style='color:{phase_col}'>{phase.replace('_', ' ')}</b>&emsp;"
        f"<span style='color:#ccc;font-size:0.87rem'>{phase_narrative(phase)}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Countdown metrics ─────────────────────────────────────────────────────
    cd_open  = days_to_gateway_open(today)
    cd_close = days_to_gateway_close(today)
    cd_enf   = days_to_enforcement(today)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📅 Today", str(today), delta=phase.replace("_", " "))
    m2.metric(
        "🟢 Gateway Opens",
        str(GATEWAY_OPEN_DATE),
        delta=f"{cd_open}d" if cd_open else "OPEN",
        delta_color="normal" if cd_open else "off",
    )
    m3.metric(
        "🔴 Gateway Closes",
        str(GATEWAY_CLOSE_DATE),
        delta=f"{cd_close}d" if cd_close else "CLOSED",
        delta_color="inverse" if cd_close and cd_close < 60 else "normal",
    )
    m4.metric(
        "⚠️ Enforcement Cliff",
        str(ENFORCEMENT_DATE),
        delta=f"{cd_enf}d" if cd_enf else "IN EFFECT",
        delta_color="inverse" if cd_enf and cd_enf < 180 else "normal",
    )

    # ── Interactive date slider ───────────────────────────────────────────────
    st.markdown("**Time-travel: assess compliance at any reference date**")
    ref_date = st.slider(
        "Reference date",
        min_value=date(2026, 1, 1),
        max_value=date(2028, 3, 31),
        value=today,
        format="YYYY-MM-DD",
        label_visibility="collapsed",
    )

    matrix = load_compliance_matrix(ref_date)
    sim_phase = current_phase(ref_date)

    # ── FCA Timeline Gantt ────────────────────────────────────────────────────
    gantt_data = [
        {"Phase": "Pre-Gateway",      "Start": "2026-01-01",  "End": "2026-09-30", "color": "#4A7C59"},
        {"Phase": "Gateway Open",     "Start": "2026-09-30",  "End": "2027-02-28", "color": "#FFA500"},
        {"Phase": "Post-Gateway",     "Start": "2027-02-28",  "End": "2027-10-25", "color": "#CC5500"},
        {"Phase": "Enforcement Cliff","Start": "2027-10-25",  "End": "2028-03-31", "color": "#CC0000"},
    ]

    fig_gantt = go.Figure()
    for g in gantt_data:
        fig_gantt.add_trace(go.Bar(
            x=[(pd.to_datetime(g["End"]) - pd.to_datetime(g["Start"])).days],
            y=[g["Phase"]],
            base=[pd.to_datetime(g["Start"])],
            orientation="h",
            marker_color=g["color"],
            marker_opacity=0.75,
            name=g["Phase"],
            hovertemplate=f"<b>{g['Phase']}</b><br>{g['Start']} → {g['End']}<extra></extra>",
        ))

    # Milestone lines
    for milestone_date, label, colour in [
        (GATEWAY_OPEN_DATE,  "Gateway Opens",  "#00D4AA"),
        (GATEWAY_CLOSE_DATE, "Gateway Closes", "#FFA500"),
        (ENFORCEMENT_DATE,   "Cliff",          "#FF2222"),
    ]:
        fig_gantt.add_vline(
            x=pd.to_datetime(milestone_date).timestamp() * 1000,
            line_color=colour, line_dash="dash", line_width=2,
            annotation_text=label, annotation_position="top",
            annotation_font_color=colour,
        )

    # Reference date marker
    fig_gantt.add_vline(
        x=pd.to_datetime(ref_date).timestamp() * 1000,
        line_color="#FFFFFF", line_dash="dot", line_width=1.5,
        annotation_text=f"Ref: {ref_date}", annotation_position="top right",
    )

    fig_gantt.update_layout(
        height=200, barmode="overlay",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin={"t": 30, "b": 10, "l": 130, "r": 20},
        xaxis={"type": "date", "range": ["2026-01-01", "2028-03-31"]},
        yaxis={"categoryorder": "array",
               "categoryarray": ["Pre-Gateway", "Gateway Open", "Post-Gateway", "Enforcement Cliff"]},
        showlegend=False,
    )
    st.plotly_chart(fig_gantt, use_container_width=True, config={"displayModeBar": False})

    # ── Summary badge strip ───────────────────────────────────────────────────
    bm1, bm2, bm3, bm4 = st.columns(4)
    bm1.metric("🟢 GREEN",    matrix.green_count)
    bm2.metric("🟡 AMBER",    matrix.amber_count)
    bm3.metric("🔴 RED",      matrix.red_count)
    bm4.metric("🚨 CRITICAL", matrix.critical_count)

    # ── Instrument compliance table ───────────────────────────────────────────
    st.markdown(f"**Instrument Compliance Matrix** — Reference date: `{ref_date}` | Phase: `{sim_phase}`")

    table_rows = []
    for r in matrix.reports:
        dtg  = f"{r.days_to_gateway_open}d"  if r.days_to_gateway_open  else "—"
        dtc  = f"{r.days_to_gateway_close}d" if r.days_to_gateway_close else "—"
        dte  = f"{r.days_to_enforcement}d"   if r.days_to_enforcement   else "PAST"
        table_rows.append({
            "ID":           r.instrument_id,
            "Name":         r.instrument_name,
            "Category":     r.category,
            "Auth Status":  r.auth_status,
            "Flag":         r.survival_flag,
            "→ Gateway":   dtg,
            "→ Close":     dtc,
            "→ Cliff":     dte,
            "Next Action":  r.next_action[:60] + "…" if len(r.next_action) > 60 else r.next_action,
            "Deadline":     str(r.deadline) if r.deadline else "—",
        })

    table_df = pd.DataFrame(table_rows)

    _flag_bg = {"GREEN": "#1a3d2e", "AMBER": "#3d2e1a", "RED": "#3d1a1a", "CRITICAL": "#5c1a1a"}

    def _compliance_row_color(row):
        bg = _flag_bg.get(row.get("Flag", ""), "")
        return [f"background-color: {bg}"] * len(row) if bg else [""] * len(row)

    st.dataframe(
        table_df.style.apply(_compliance_row_color, axis=1),
        use_container_width=True, hide_index=True,
    )

    # ── Next upcoming milestones ──────────────────────────────────────────────
    st.markdown("**Next Regulatory Milestones**")
    milestones = upcoming_milestones(ref_date, n=4)
    for m in milestones:
        delta = (m["date"] - ref_date).days
        color = "#FF4B4B" if delta < 90 else "#FFA500" if delta < 270 else "#00D4AA"
        st.markdown(
            f"<div class='banner-card' style='border-left:4px solid {color}'>"
            f"<b style='color:{color}'>{m['date']}</b>"
            f"&emsp;<span style='color:#888;font-size:0.75rem'>[{delta:+d} days]</span>"
            f"<br><b>{m['label']}</b>"
            f"<br><span style='color:#888;font-size:0.78rem'>{m['detail'][:200]}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Critical instruments deep-dive ────────────────────────────────────────
    critical = matrix.critical_instruments
    if critical:
        with st.expander(f"🚨 {len(critical)} CRITICAL instruments — full risk narrative", expanded=False):
            for r in critical:
                st.markdown(
                    f"**{r.instrument_id}** — {r.instrument_name}  "
                    f"({r.category.replace('_', ' ')})\n\n"
                    f"> {r.risk_narrative}\n\n"
                    f"**Next action:** {r.next_action}  \n"
                    f"**Deadline:** {r.deadline} _{r.deadline_label}_",
                )
                st.divider()


# ═════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    # ── Sidebar ───────────────────────────────────────────────────────────────
    render_sidebar()

    # ── Page header ───────────────────────────────────────────────────────────
    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown(
            "<h1 style='margin-bottom:0'>📡 Contrarian Radar</h1>"
            "<p style='color:#888;margin-top:2px'>Institutional asymmetric intelligence platform</p>",
            unsafe_allow_html=True,
        )
    with h2:
        st.markdown(
            f"<div style='text-align:right;padding-top:0.5rem'>"
            f"<span style='color:#888;font-size:0.8rem'>Phase</span><br>"
            f"<b style='color:{_phase_color(current_phase())}'>"
            f"{current_phase().replace('_', ' ')}</b><br>"
            f"<span style='color:#666;font-size:0.75rem'>{date.today()}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Auto-refresh toggle ───────────────────────────────────────────────────
    refresh_col, _ = st.columns([1, 4])
    with refresh_col:
        auto_refresh = st.toggle("Auto-refresh (5 min)", value=False)
    if auto_refresh:
        st.cache_data.clear()
        st.rerun()

    # ── Render zones ──────────────────────────────────────────────────────────
    render_zone1()
    render_zone2()
    render_zone3()

    # ── Footer ────────────────────────────────────────────────────────────────
    st.divider()
    st.markdown(
        "<p style='text-align:center;color:#444;font-size:0.75rem'>"
        "Contrarian Radar · Phase 4 · Data latency ≤ 5 min · "
        "Not investment advice · Regulatory data sourced from FCA CP23/28 &amp; PS24/12"
        "</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
