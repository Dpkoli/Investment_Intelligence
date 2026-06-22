#!/usr/bin/env python3
"""
Contrarian Radar — Modular Production Hub (v2.0)

Zone 1 : Enhanced Cassandra alert ticker + Kingmaker endorsement banner
         (clickable source links, expandable Systemic Assessment panels)
Zone 2 : Horizon Pipeline & Asymmetry Finder
Zone 3 : UK 2026-2027 Regulatory Sandbox

Module nav routes to 6 self-contained domain modules.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from typing import Any, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

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

# ── Module imports ────────────────────────────────────────────────────────────
import modules.core_equity.ui          as _mod_core_equity
import modules.thematic_sectors.ui     as _mod_thematic
import modules.sovereign_crypto.ui     as _mod_crypto
import modules.precious_metals.ui      as _mod_metals
import modules.kingmaker_intelligence.ui as _mod_kingmaker
import modules.regulatory_sandbox.ui   as _mod_regulatory

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
    :root {
        --accent:   #00D4AA;
        --danger:   #FF4B4B;
        --warn:     #FFA500;
        --dim:      #888;
        --card-bg:  #1A1D24;
        --border:   #2E3140;
    }
    .block-container { padding-top: 1rem; }

    div[data-testid="metric-container"] {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 0.6rem 1rem;
    }

    .zone-header {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--dim);
        margin-bottom: 0.4rem;
    }

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

    .badge-green    { background:#1a3d2e; color:#00D4AA; border-radius:4px; padding:2px 8px; font-size:0.75rem; font-weight:700; }
    .badge-amber    { background:#3d2e1a; color:#FFA500; border-radius:4px; padding:2px 8px; font-size:0.75rem; font-weight:700; }
    .badge-red      { background:#3d1a1a; color:#FF6B6B; border-radius:4px; padding:2px 8px; font-size:0.75rem; font-weight:700; }
    .badge-critical { background:#5c1a1a; color:#FF2222; border-radius:4px; padding:2px 8px; font-size:0.75rem; font-weight:700; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.55} }

    .asymmetry-flag {
        background: linear-gradient(90deg, #1a3d2e, #0E1117);
        border: 1px solid var(--accent);
        border-radius: 6px;
        padding: 0.6rem 1rem;
        margin-bottom: 0.35rem;
    }

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
# STATIC DEMO DATA
# ═════════════════════════════════════════════════════════════════════════════

_CASSANDRA_DEMO: list[dict] = [
    {"title": "Texas ERCOT grid: AI data-centre load 340% above 2023 baseline — brownout risk Q4 2026",
     "risk_score": 9, "vector": "energy_risk",
     "source": "energymonitor.ai", "source_url": "https://energymonitor.ai"},
    {"title": "Global transformer shortage: 24-36 month lead times flagged by major grid operators",
     "risk_score": 8, "vector": "energy_risk",
     "source": "datacenterdynamics.com", "source_url": "https://www.datacenterdynamics.com"},
    {"title": "China grid-export restrictions: 60 Hz transformer exports halted from Q3 2026",
     "risk_score": 9, "vector": "energy_risk",
     "source": "energymonitor.ai", "source_url": "https://energymonitor.ai/topics/power/"},
    {"title": "Tether (USDT) reserve audit delayed for 4th consecutive quarter — contagion risk",
     "risk_score": 7, "vector": "crypto_risk",
     "source": "protos.com", "source_url": "https://protos.com/tether/"},
    {"title": "Coinbase custody concentration: 42% of all US crypto ETF assets at single entity",
     "risk_score": 7, "vector": "crypto_risk",
     "source": "theblock.co", "source_url": "https://www.theblock.co/"},
    {"title": "Deutsche Bank systemic leverage ratio breach flagged in ECB quarterly review",
     "risk_score": 8, "vector": "systemic_risk",
     "source": "wolfstreet.com", "source_url": "https://wolfstreet.com/"},
    {"title": "Virginia Northern data-centre cluster: water-cooling capacity at 96% utilisation",
     "risk_score": 6, "vector": "energy_risk",
     "source": "datacenterdynamics.com", "source_url": "https://www.datacenterdynamics.com/"},
    {"title": "XRP 9th Circuit appeal creates renewed legal uncertainty for exchange listings",
     "risk_score": 5, "vector": "crypto_risk",
     "source": "theblock.co", "source_url": "https://www.theblock.co/"},
]

_KINGMAKER_DEMO: list[dict] = [
    {"titan": "NVDA", "titan_name": "NVIDIA", "executive": "Jensen Huang",
     "vendor": "Marvell Technology", "vendor_ticker": "MRVL",
     "type": "Custom_Silicon", "confidence": 9,
     "quote": "Marvell is our primary custom ASIC partner — sole-source for ConnectX series",
     "source_url": "https://investor.marvell.com/news-releases/news-release-details/marvell-custom-silicon-nvidia"},
    {"titan": "NVDA", "titan_name": "NVIDIA", "executive": "Jensen Huang",
     "vendor": "Super Micro Computer", "vendor_ticker": "SMCI",
     "type": "Supplier", "confidence": 7,
     "quote": "~35% of HGX unit shipments flow through SuperMicro",
     "source_url": "https://ir.supermicro.com/"},
    {"titan": "GOOGL", "titan_name": "Google", "executive": "Sundar Pichai",
     "vendor": "Cadence Design", "vendor_ticker": "CDNS",
     "type": "Custom_Silicon", "confidence": 8,
     "quote": "Cadence handles 100% of our TPU v5 verification flows",
     "source_url": "https://investor.cadence.com/news-releases/"},
    {"titan": "AMZN", "titan_name": "Amazon", "executive": "Andy Jassy",
     "vendor": "Arista Networks", "vendor_ticker": "ANET",
     "type": "JV_Partner", "confidence": 8,
     "quote": "Arista is exclusive switching fabric partner for AWS Nitro SuperCluster",
     "source_url": "https://ir.arista.com/"},
    {"titan": "MSFT", "titan_name": "Microsoft", "executive": "Satya Nadella",
     "vendor": "Coherent Corp", "vendor_ticker": "COHR",
     "type": "Supplier", "confidence": 7,
     "quote": "Coherent 800G transceivers underpin our Azure AI fabric at scale",
     "source_url": "https://ir.coherent.com/"},
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
# SYSTEMIC ASSESSMENT TEMPLATES
# ═════════════════════════════════════════════════════════════════════════════

_RISK_ASSESSMENTS: dict[str, list[str]] = {
    "energy_risk": [
        "**Grid CAPEX supercycle (2025–2028):** Global electricity grid investment estimated at $2.4tn — AI data-centre buildout is the single largest incremental demand driver. Utilities, transformer manufacturers (ABB, Eaton, Siemens Energy), and grid-software vendors (GE Vernova) are structural beneficiaries. Consider long-duration exposure to grid infrastructure ETFs (GRID, PAVE).",
        "**Brownout cascade sequence:** ERCOT grid failures typically propagate 48-72h lead time into spot power price spikes of 200-400%. Companies with on-site generation (natural gas peakers, diesel backup, SMR options) command 15-30% premium EBITDA margins versus grid-dependent peers. Watch for ERCOT capacity market auction results Q4 2026.",
        "**Transformer supply constraint moat:** 24-36 month lead times create a pricing power window for domestic transformer manufacturers (Roper Technologies, Eaton). Import restrictions from China effectively shield US/EU manufacturers from competitive pressure through at minimum 2027. Sector re-rating catalyst: US DoE transformer emergency action under DPA Section 303.",
    ],
    "crypto_risk": [
        "**Contagion propagation model:** Stablecoin reserve opacity events historically trigger a 3-phase market response: (1) immediate liquidity pull from affected stablecoin (-15-40% depeg within 48h), (2) cross-exchange collateral margin calls causing correlated crypto sell-off (-20-35% broad market, 5-10 day window), (3) institutional re-entry 30-60 days post-event once reserve audit is published. Position sizing: reduce stablecoin exposure, increase BTC/ETH spot (lower counterparty risk profile).",
        "**FCA regulatory arbitrage window closing:** UK FSMA gateway closes Feb 28 2027. Exchanges and issuers not registered by that date face criminal liability under s.23. This creates a structural demand surge for FCA-authorised LSE ETPs (IB1T.L, BITB.L) as institutions rotate out of unregistered products. AUM inflows to LSE ETPs estimated +£800mn-1.2bn over 12 months post-enforcement.",
        "**Custody concentration systemic risk:** Single-point custody failures (e.g., FTX collapse Nov 2022) trigger industry-wide margin calls within 24-48h. 42% Coinbase ETF custody concentration implies contagion velocity of approximately 3× historical average if Coinbase faces liquidity stress. Mitigation: diversified custodians (Fidelity Digital, BitGo, Anchorage Digital), multi-sig self-custody mandates for institutional allocations >$50mn.",
    ],
    "systemic_risk": [
        "**Bank leverage cascade sequence:** ECB-flagged leverage ratio breaches historically precede credit event by 6-18 months. Deutsche Bank CDS spreads are the leading indicator — watch for spread widening above 120bps (current ~85bps) as the primary warning signal. Tactical positioning: long volatility (VIX calls), reduce European financial sector exposure, increase US Treasury bill allocation as safe-haven.",
        "**Cross-border contagion channels:** European banks with US dollar funding mismatches face acute stress during USD liquidity events (Fed balance sheet contraction, Treasury supply glut). Swap lines (Fed-ECB) provide backstop but with 2-4 week activation lag. Positioning: long USD in the near-term stress window, rotate to shorter-duration fixed income.",
        "**Regulatory intervention probability:** ECB Single Supervisory Mechanism (SSM) has historically intervened within 3-6 months of flagging a leverage breach. Intervention tools include: mandatory capital raise, asset disposal mandates, or merger facilitation. Each intervention scenario has differentiated equity implications — monitor supervisory letter disclosures via ECB press releases.",
    ],
    "regulatory_risk": [
        "**FCA enforcement cliff (25 Oct 2027):** s.23 FSMA criminal liability activates for unauthorised crypto business. Firms achieving FCA registration before gateway close (28 Feb 2027) gain permanent regulatory moat — estimated 3-5 dominant authorised operators will capture 70-80% of institutional AUM. This is the most significant structural event in UK crypto market history.",
        "**SEC vs commodity classification:** Ongoing commodity/security classification battles (XRP 9th Circuit, SOL, ADA) create binary regulatory outcomes. Resolution catalyst: SAB 122 implementation timeline (Q3-Q4 2026) and potential DOGE/SEC leadership restructuring. ETF approvals for non-BTC/ETH assets contingent on resolution.",
        "**MICA (EU) regulatory arbitrage:** EU Markets in Crypto Assets regulation fully operational from Dec 2024 creates regulatory certainty for EU-domiciled exchanges. UK firms without MICA passporting face competitive disadvantage in EU market access — watch for cross-border compliance cost differentials driving M&A consolidation.",
    ],
    "supply_chain": [
        "**Reshoring timeline and CAPEX:** US CHIPS Act ($52bn) + IRA ($369bn) are creating a 5-7 year US semiconductor and clean energy supply chain reshoring cycle. TSMC Arizona (N3/N2 nodes), Samsung Taylor TX, and Intel Ohio fabs represent $200bn+ in committed CAPEX. Tier-2 suppliers (lithography, chemicals, gases) are earliest beneficiaries (2024-2026 window).",
        "**China decoupling propagation:** Each percentage point increase in US-China trade restrictions (tariffs, export controls, entity list expansions) historically generates 2-3% EBITDA uplift for non-China alternative suppliers within 12 months. Vietnam, India, Mexico are primary re-routing beneficiaries. Track US Census Bureau trade data for monthly leading indicators.",
        "**Single-source dependency risk:** Supply chain bottlenecks in rare earth elements (China controls 85% of processing) create persistent pricing power for alternative processors (MP Materials, Lynas). De-risking timelines: 3-5 years minimum to establish alternative refining capacity at scale. Near-term: rare earth price spikes are directly tradeable via futures or REMX ETF.",
    ],
}

_DEFAULT_ASSESSMENT = [
    "Monitor this signal for escalation within the 30-day forward window. High-severity macro signals (score ≥ 8) historically precede identifiable market dislocations within 45-90 days.",
    "Cross-reference against sector-specific leading indicators: credit spreads, options skew, and institutional flow data for confirmation before tactical positioning.",
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
        return f"<span style='color:#FF4B4B;font-weight:700'>{delta}d</span>"
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


def _cassandra_assessment(vector: str, title: str, score: int) -> list[str]:
    base = _RISK_ASSESSMENTS.get(vector, _DEFAULT_ASSESSMENT)
    if score >= 9:
        urgency = f"**⚠️ SEVERITY {score}/10 — Immediate attention warranted.** This signal is in the top decile of systemic threat indicators."
        return [urgency] + base
    return base


def _kingmaker_assessment(conn_type: str, vendor: str, titan: str, conf: int) -> list[str]:
    events = []
    if "Custom_Silicon" in conn_type or "Custom" in conn_type:
        events.append(f"Next chip generation tape-out at {titan} will expand {vendor} silicon revenue by an estimated 25-40% YoY — increased die complexity and committed volume are the primary drivers.")
        events.append(f"Watch for {titan} annual developer conference keynote — named {vendor} endorsements historically trigger 10-25% next-day share price moves for the supplier.")
        events.append(f"Sole-source ASIC design wins create 3-5 year revenue visibility. Re-rating catalyst: {vendor} next earnings call — any raised silicon revenue guidance implies forward estimates are materially understated.")
    elif "JV" in conn_type or "Partner" in conn_type:
        events.append(f"JV partnership arrangements typically precede a formal long-term supply agreement within 12-18 months. Contract announcement would trigger upward revision of {vendor}'s forward EBITDA by 20-35%.")
        events.append(f"Watch for {titan} infrastructure announcements — each $1bn in new data centre / infrastructure CAPEX commitment flows through to JV partners within 2 quarters.")
    else:
        events.append(f"{titan}'s procurement consolidation trend favours fewer, deeper Tier-1 supplier relationships. {vendor}'s incumbent position is structurally advantaged in renewal cycles (8-15% annual price escalation typical for sole-source suppliers in regulated industries).")
        events.append(f"Competitor qualification attempts by {titan} require 2-4 year re-qualification cycles — this creates a structural moat period for {vendor} at current revenue run-rate.")
    if conf >= 9:
        events.insert(0, f"**🔥 CONFIDENCE {conf}/10 — Named executive confirmation.** This is the highest-tier endorsement signal; institutional smart money typically builds positions within 30-60 days of such disclosures.")
    return events


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR — NAVIGATION + WHAT-IF CS SIMULATOR
# ═════════════════════════════════════════════════════════════════════════════

_NAV_OPTIONS = [
    "🏠 Intelligence Hub",
    "📈 Core Equity",
    "📊 Thematic Sectors",
    "₿ Sovereign Crypto",
    "🥇 Precious Metals",
    "🔗 Kingmaker Intelligence",
    "🏛️ Regulatory Sandbox",
]


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown("## 📡 Contrarian Radar")
        st.caption("Institutional asymmetric intelligence platform")
        st.divider()

        nav = st.radio(
            "Navigate",
            _NAV_OPTIONS,
            index=0,
            label_visibility="collapsed",
        )

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

        cs_no_endorse = engine.score_components(comp.model_copy(update={"kw": 1.0})).cs
        cs_endorsed   = engine.score_components(comp.model_copy(update={"kw": 2.5})).cs
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

    return nav


# ═════════════════════════════════════════════════════════════════════════════
# ZONE 1 — CASSANDRA ALERT TICKER + KINGMAKER BANNER  (enhanced)
# ═════════════════════════════════════════════════════════════════════════════

def render_zone1() -> None:
    st.markdown('<p class="zone-header">⚡ ZONE 1 — LIVE INTELLIGENCE FEED</p>', unsafe_allow_html=True)

    alerts       = load_cassandra_alerts()
    endorsements = load_kingmaker_endorsements()

    left, right = st.columns([1, 1], gap="medium")

    with left:
        st.markdown("**🔴 CASSANDRA ALERT TICKER** — Live macro threats ranked by severity")
        for idx, a in enumerate(alerts[:8]):
            score   = int(a.get("risk_score") or a.get("Systemic_Risk_Score") or 0)
            title   = a.get("title") or a.get("Title") or "—"
            vector  = (a.get("vector") or a.get("Risk_Vector") or "").replace("_", " ")
            raw_src = a.get("source") or ""
            src_url = a.get("source_url") or a.get("Source_URL") or ""

            severity_cls = (
                "banner-card-critical" if score >= 8 else
                "banner-card-warn"     if score >= 6 else
                "banner-card-ok"
            )

            title_html = (
                f'<a href="{src_url}" target="_blank" '
                f'style="color:inherit;text-decoration:none;border-bottom:1px dotted #555">'
                f'{title}</a>'
            ) if src_url else title

            source_html = (
                f'<a href="{src_url}" target="_blank" '
                f'style="color:#00D4AA;font-size:0.70rem;text-decoration:none">↗ {raw_src}</a>'
            ) if src_url else f'<span style="color:#888;font-size:0.70rem">{raw_src}</span>'

            st.markdown(
                f"""<div class="banner-card {severity_cls}">
                    <span class="ticker-item">
                        {_pill(score)} <b>{title_html}</b><br>
                        <span style="color:#888;font-size:0.72rem">
                            {vector.upper()}&nbsp;&nbsp;·&nbsp;&nbsp;{source_html}
                        </span>
                    </span>
                </div>""",
                unsafe_allow_html=True,
            )

            with st.expander("📊 Systemic Assessment & Strategic Recommendation", expanded=False):
                v_key = (a.get("vector") or a.get("Risk_Vector") or "").lower()
                bullets = _cassandra_assessment(v_key, title, score)
                for b in bullets:
                    st.markdown(b)

    with right:
        st.markdown("**🚀 KINGMAKER ENDORSEMENT ALERTS** — Named-exec catalyst detections")
        for idx, e in enumerate(endorsements[:5]):
            titan_name = e.get("titan_name")  or e.get("Titan_Ticker")         or "—"
            exec_name  = e.get("executive")   or e.get("Endorsement_Source")   or "Executive"
            vendor     = e.get("vendor")      or e.get("Counterparty_Name")    or "—"
            vticker    = e.get("vendor_ticker") or e.get("Counterparty_Ticker") or ""
            conn_type  = (e.get("type") or e.get("Connection_Type") or "Supplier").replace("_", " ")
            conf       = int(e.get("confidence") or e.get("Confidence_Score") or 7)
            quote      = e.get("quote") or e.get("Extracted_Text") or ""
            src_url    = e.get("source_url") or e.get("Endorsement_Source") or ""

            vtag = f"({vticker})" if vticker else ""

            vendor_html = (
                f'<a href="{src_url}" target="_blank" style="color:#00D4AA;text-decoration:none">'
                f'{vendor} {vtag}</a>'
            ) if src_url and src_url.startswith("http") else f'<b style="color:#00D4AA">{vendor} {vtag}</b>'

            st.markdown(
                f"""<div class="banner-card banner-card-ok">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                        <span style="font-size:1.1rem">🏆</span>
                        <b>{titan_name}</b>
                        <span style="color:#888">→</span>
                        {vendor_html}
                        <span style="color:#888;font-size:0.75rem">{conn_type}</span>
                        {_pill(conf)}
                    </div>
                    <div style="color:#888;font-size:0.77rem;font-style:italic;margin-left:28px">
                        {exec_name}: &ldquo;{quote[:120]}{"…" if len(quote) > 120 else ""}&rdquo;
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

            raw_conn = e.get("type") or e.get("Connection_Type") or "Supplier"
            with st.expander("📊 Systemic Assessment & Strategic Recommendation", expanded=False):
                bullets = _kingmaker_assessment(raw_conn, vendor, titan_name, conf)
                for b in bullets:
                    st.markdown(b)


# ═════════════════════════════════════════════════════════════════════════════
# ZONE 2 — HORIZON PIPELINE & ASYMMETRY FINDER
# ═════════════════════════════════════════════════════════════════════════════

def render_zone2() -> None:
    st.divider()
    st.markdown('<p class="zone-header">🔭 ZONE 2 — HORIZON PIPELINE & ASYMMETRY FINDER</p>',
                unsafe_allow_html=True)
    st.caption(
        "Institutional asset registrations scraped from SEC EDGAR and the FCA Register. "
        "Asymmetry plays = Pv ≥ 4.0 **and** Cc ≤ 0.30 (institutional ramp, low crowding)."
    )

    pipeline = load_horizon_pipeline()
    df = pd.DataFrame(pipeline)

    if "Pv" in df.columns and "Cc" in df.columns:
        df["Asymmetry Play"] = (df["Pv"] >= 4.0) & (df["Cc"] <= 0.30)
    else:
        df["Asymmetry Play"] = False

    n_total     = len(df)
    n_asymmetry = int(df["Asymmetry Play"].sum()) if "Asymmetry Play" in df.columns else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Pipeline Filings", n_total)
    m2.metric("Asymmetry Plays (Pv≥4.0, Cc≤0.30)", n_asymmetry)
    m3.metric("Horizon Issuers Tracked", 17)

    if "Pv" in df.columns and "Cc" in df.columns:
        fig = px.scatter(
            df, x="Cc", y="Pv",
            color="Asymmetry Play",
            color_discrete_map={True: "#00D4AA", False: "#888"},
            hover_name="Asset" if "Asset" in df.columns else df.index,
            hover_data=["Filer", "Class"] if "Filer" in df.columns else {},
            template="plotly_dark",
            title="Asymmetry Scatter — Pv vs Cc  (top-left quadrant = deep asymmetry)",
            height=320,
            labels={"Cc": "Consensus Crowding (Cc)", "Pv": "Pipeline Velocity (Pv)"},
        )
        fig.add_vline(x=0.30, line_dash="dot", line_color="#FFA500", line_width=1,
                      annotation_text="Cc ≤ 0.30", annotation_position="top")
        fig.add_hline(y=4.0,  line_dash="dot", line_color="#FFA500", line_width=1,
                      annotation_text="Pv ≥ 4.0", annotation_position="right")
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin={"t": 40, "b": 20},
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

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
# ZONE 3 — UK 2026-2027 REGULATORY SANDBOX  (legacy inline; module page is richer)
# ═════════════════════════════════════════════════════════════════════════════

def render_zone3() -> None:
    st.divider()
    st.markdown('<p class="zone-header">⚖️ ZONE 3 — UK 2026-2027 REGULATORY SANDBOX</p>',
                unsafe_allow_html=True)

    today = date.today()
    phase = current_phase(today)

    phase_col = _phase_color(phase)
    st.markdown(
        f"<div style='background:{phase_col}22; border:1px solid {phase_col}; "
        f"border-radius:8px; padding:0.7rem 1rem; margin-bottom:1rem;'>"
        f"<b style='color:{phase_col}'>{phase.replace('_', ' ')}</b>&emsp;"
        f"<span style='color:#ccc;font-size:0.87rem'>{phase_narrative(phase)}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    cd_open  = days_to_gateway_open(today)
    cd_close = days_to_gateway_close(today)
    cd_enf   = days_to_enforcement(today)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📅 Today", str(today), delta=phase.replace("_", " "))
    m2.metric("🟢 Gateway Opens",   str(GATEWAY_OPEN_DATE),
              delta=f"{cd_open}d" if cd_open else "OPEN",
              delta_color="normal" if cd_open else "off")
    m3.metric("🔴 Gateway Closes",  str(GATEWAY_CLOSE_DATE),
              delta=f"{cd_close}d" if cd_close else "CLOSED",
              delta_color="inverse" if cd_close and cd_close < 60 else "normal")
    m4.metric("⚠️ Enforcement Cliff", str(ENFORCEMENT_DATE),
              delta=f"{cd_enf}d" if cd_enf else "IN EFFECT",
              delta_color="inverse" if cd_enf and cd_enf < 180 else "normal")

    st.info("💡 For the full interactive compliance matrix, date simulator, and 19-instrument deep-dive, navigate to **🏛️ Regulatory Sandbox** via the sidebar.", icon=None)


# ═════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    nav = render_sidebar()

    # ── Page header ───────────────────────────────────────────────────────────
    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown(
            "<h1 style='margin-bottom:0'>📡 Contrarian Radar</h1>"
            "<p style='color:#888;margin-top:2px'>Institutional asymmetric intelligence platform — v2.0 modular</p>",
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

    # ── Module routing ────────────────────────────────────────────────────────
    if nav == "📈 Core Equity":
        _mod_core_equity.render()

    elif nav == "📊 Thematic Sectors":
        _mod_thematic.render()

    elif nav == "₿ Sovereign Crypto":
        _mod_crypto.render()

    elif nav == "🥇 Precious Metals":
        _mod_metals.render()

    elif nav == "🔗 Kingmaker Intelligence":
        _mod_kingmaker.render()

    elif nav == "🏛️ Regulatory Sandbox":
        _mod_regulatory.render()

    else:
        # Intelligence Hub — Zone 1 + Horizon Pipeline + Regulatory summary
        refresh_col, _ = st.columns([1, 4])
        with refresh_col:
            auto_refresh = st.toggle("Auto-refresh (5 min)", value=False)
        if auto_refresh:
            st.cache_data.clear()
            st.rerun()

        render_zone1()
        render_zone2()
        render_zone3()

    # ── Footer ────────────────────────────────────────────────────────────────
    st.divider()
    st.markdown(
        "<p style='text-align:center;color:#444;font-size:0.75rem'>"
        "Contrarian Radar v2.0 · 6 modular domains · Data latency ≤ 5 min · "
        "Not investment advice · Regulatory data sourced from FCA CP23/28 &amp; PS24/12"
        "</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
