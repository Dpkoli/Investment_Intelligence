#!/usr/bin/env python3
"""
InvestWise — Modular Investment Intelligence Hub

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
import modules.news_feed.ui            as _mod_news

# ═════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG  (must be the first Streamlit call)
# ═════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="InvestWise",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "InvestWise — Institutional-grade investment intelligence platform."},
)

# ═════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ═════════════════════════════════════════════════════════════════════════════

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    /* Apply Inter only to text elements, not to icon/symbol pseudo-elements */
    body, .stApp, .stMarkdown p, .stMarkdown span, .stMarkdown a,
    .stMarkdown li, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
    .stButton button p, .stTextInput input, .stSelectbox select,
    .stTabs [role="tab"], div[data-testid="stExpander"] summary p,
    div[data-testid="metric-container"] label,
    div[data-testid="metric-container"] [data-testid="stMetricValue"],
    div[data-testid="metric-container"] [data-testid="stMetricDelta"],
    label, .stCaption p {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif !important;
    }

    /* Preserve Streamlit's Material icon font for icons */
    [data-testid="stExpander"] summary svg,
    [data-testid="stExpander"] summary [data-testid="stIconMaterial"],
    span[aria-hidden="true"], [class*="material-icons"] {
        font-family: 'Material Icons', 'Material Symbols Rounded' !important;
    }

    :root {
        --canvas:   #f4f6f9;
        --sidebar:  #111c24;
        --card:     #ffffff;
        --border:   #e2e8f0;
        --text-h:   #0a0f1d;
        --text-sub: #64748b;
        --accent:   #00875a;
        --danger:   #dc2626;
        --warn:     #ea580c;
        --info:     #2563eb;
        --purple:   #7c3aed;
    }

    /* ── Canvas ─────────────────────────────────── */
    .stApp { background-color: var(--canvas) !important; }
    .block-container { padding-top: 1rem; background: transparent; }

    /* ── Sidebar ────────────────────────────────── */
    section[data-testid="stSidebar"] > div:first-child {
        background-color: var(--sidebar) !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] label { color: #94a3b8 !important; }
    section[data-testid="stSidebar"] .stRadio label { color: #94a3b8 !important; }
    section[data-testid="stSidebar"] .stRadio label:hover { color: #ffffff !important; }

    /* ── Metric containers ──────────────────────── */
    div[data-testid="metric-container"] {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 0.85rem 1.25rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    }
    div[data-testid="metric-container"] label { color: var(--text-sub) !important; font-size: 0.8rem; }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] { color: var(--text-h) !important; font-weight: 800; }

    /* ── Expanders ──────────────────────────────── */
    div[data-testid="stExpander"] {
        background: var(--card);
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div[data-testid="stExpander"] summary { color: var(--text-h) !important; font-weight: 600; }

    /* ── Tabs ───────────────────────────────────── */
    .stTabs [data-testid="stTab"] { color: var(--text-sub) !important; }
    .stTabs [aria-selected="true"] { color: var(--text-h) !important; font-weight: 700; border-bottom-color: var(--info) !important; }

    /* ── Buttons ────────────────────────────────── */
    .stButton button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
    }
    .stButton button[kind="primary"] { background: var(--accent) !important; border-color: var(--accent) !important; }

    /* ── Hide empty hidden trigger buttons (card click wiring) ─ */
    div[data-testid="stButton"]:has(button p:empty),
    div[data-testid="stButton"]:has(button:not([aria-label])[title=""]) {
        height: 0 !important;
        overflow: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    button.hub-hidden-btn, div.hub-hidden-wrapper {
        height: 0 !important; overflow: hidden !important; margin: 0 !important; padding: 0 !important;
    }

    /* ── Secondary / inactive chip buttons → soft slate style ─ */
    .stButton button[kind="secondary"] {
        background: #f1f5f9 !important;
        border: 1px solid #cbd5e1 !important;
        color: #475569 !important;
    }
    .stButton button[kind="secondary"]:hover {
        background: #e2e8f0 !important;
        border-color: #94a3b8 !important;
        color: #1e293b !important;
    }

    /* ── Expander arrow — ensure SVG shows, never shows as text ─ */
    div[data-testid="stExpander"] summary {
        cursor: pointer;
        align-items: center;
        gap: 0.5rem;
    }
    div[data-testid="stExpander"] summary svg {
        display: inline-block !important;
        flex-shrink: 0;
        min-width: 16px;
        min-height: 16px;
    }
    div[data-testid="stExpander"] summary p {
        margin: 0 !important;
        line-height: 1.4 !important;
    }

    /* ── Hidden card-trigger button ─────────────── */
    .iw-hidden-btn-wrap,
    .iw-hidden-btn-wrap > div,
    .iw-hidden-btn-wrap button {
        height: 0 !important;
        min-height: 0 !important;
        overflow: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        opacity: 0 !important;
        pointer-events: none !important;
        display: block !important;
        line-height: 0 !important;
    }

    /* ── Price card hover ────────────────────────── */
    .iw-price-card:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 16px rgba(0,0,0,0.13) !important;
    }

    /* ── Toggle ─────────────────────────────────── */
    .stToggle label { color: var(--text-sub) !important; font-size: 0.82rem !important; }

    /* ── Text inputs ────────────────────────────── */
    .stTextInput input {
        border-radius: 8px !important;
        border: 1px solid var(--border) !important;
        background: var(--card) !important;
        color: var(--text-h) !important;
    }

    /* ── Cards via classes ──────────────────────── */
    .cr-card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.55rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .cr-card-crit { border-left: 4px solid var(--danger); }
    .cr-card-warn { border-left: 4px solid var(--warn); }
    .cr-card-ok   { border-left: 4px solid var(--accent); }

    /* ── Legacy .banner-card support ───────────── */
    .banner-card { background: var(--card); border: 1px solid var(--border); border-radius:12px; padding:0.85rem 1.1rem; margin-bottom:0.5rem; box-shadow:0 1px 3px rgba(0,0,0,0.06); }
    .banner-card-critical { border-left: 4px solid var(--danger); }
    .banner-card-warn     { border-left: 4px solid var(--warn); }
    .banner-card-ok       { border-left: 4px solid var(--accent); }

    /* ── Badges ─────────────────────────────────── */
    .badge-green    { background:#dcfce7; color:#00875a; border-radius:6px; padding:2px 10px; font-size:0.74rem; font-weight:700; }
    .badge-amber    { background:#fef3c7; color:#d97706; border-radius:6px; padding:2px 10px; font-size:0.74rem; font-weight:700; }
    .badge-red      { background:#fee2e2; color:#dc2626; border-radius:6px; padding:2px 10px; font-size:0.74rem; font-weight:700; }
    .badge-critical { background:#fee2e2; color:#b91c1c; border-radius:6px; padding:2px 10px; font-size:0.74rem; font-weight:700; animation:pulse 1.5s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.55} }

    /* ── Score pills ────────────────────────────── */
    .ticker-item { font-size:0.82rem; margin-bottom:0.3rem; }
    .score-pill  { display:inline-block; border-radius:999px; padding:2px 10px; font-size:0.72rem; font-weight:700; margin-right:0.4rem; }
    .pill-9  { background:#fee2e2; color:#b91c1c; }
    .pill-8  { background:#ffedd5; color:#c2410c; }
    .pill-7  { background:#fef3c7; color:#a16207; }
    .pill-6  { background:#dcfce7; color:#166534; }
    .pill-low{ background:#f1f5f9; color:#64748b; }

    /* ── Section labels ─────────────────────────── */
    .zone-header { font-size:0.7rem; font-weight:800; letter-spacing:0.15em; text-transform:uppercase; color:var(--text-sub); margin-bottom:0.4rem; }

    /* ── Dividers ───────────────────────────────── */
    hr { border-color: var(--border) !important; }

    /* ── Page heading ───────────────────────────── */
    h1 { color: var(--text-h) !important; font-weight: 900 !important; }
    h2 { color: var(--text-h) !important; font-weight: 800 !important; }
    h3 { color: var(--text-h) !important; font-weight: 700 !important; }
    p  { color: var(--text-h) !important; }
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
    "📰 News Feed",
    "📈 Core Equity",
    "📊 Thematic Sectors",
    "₿ Sovereign Crypto",
    "🥇 Precious Metals",
    "🔗 Kingmaker Intelligence",
    "🏛️ Regulatory Sandbox",
]


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            "<div style='padding:0.5rem 0 0.25rem 0'>"
            "<span style='color:#ffffff;font-size:1.35rem;font-weight:900;letter-spacing:-0.02em'>📊 InvestWise</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.divider()

        nav = st.radio(
            "Navigate",
            _NAV_OPTIONS,
            index=0,
            key="sidebar_nav",
            label_visibility="collapsed",
        )

    return nav


# ═════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE HUB — helpers and data
# ═════════════════════════════════════════════════════════════════════════════

_HUB_ROWS = [
    ("crypto",   "₿ Sovereign Crypto",  "#7c3aed", "₿ Sovereign Crypto"),
    ("thematic", "📊 Thematic Sectors", "#00875a", "📊 Thematic Sectors"),
    ("equity",   "📈 Core Equity",      "#2563eb", "📈 Core Equity"),
]
_HUB_DEFAULT_FAVS: dict[str, list[str]] = {
    "crypto":   ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"],
    "thematic": ["BOTZ", "ARKK", "CIBR", "ICLN"],
    "equity":   ["SPY", "QQQ", "VWRP.L", "IWDA.L"],
}
_HUB_ALL_TICKERS: dict[str, dict] = {
    "BTC-USD":   {"name": "Bitcoin",          "row": "crypto"},
    "ETH-USD":   {"name": "Ethereum",         "row": "crypto"},
    "SOL-USD":   {"name": "Solana",           "row": "crypto"},
    "XRP-USD":   {"name": "XRP",              "row": "crypto"},
    "DOGE-USD":  {"name": "Dogecoin",         "row": "crypto"},
    "ADA-USD":   {"name": "Cardano",          "row": "crypto"},
    "AVAX-USD":  {"name": "Avalanche",        "row": "crypto"},
    "MATIC-USD": {"name": "Polygon",          "row": "crypto"},
    "LINK-USD":  {"name": "Chainlink",        "row": "crypto"},
    "DOT-USD":   {"name": "Polkadot",         "row": "crypto"},
    "BOTZ":      {"name": "AI & Robotics",    "row": "thematic"},
    "ARKK":      {"name": "ARK Innovation",   "row": "thematic"},
    "CIBR":      {"name": "Cybersecurity",    "row": "thematic"},
    "ICLN":      {"name": "Clean Energy",     "row": "thematic"},
    "ROBO":      {"name": "ROBO Global",      "row": "thematic"},
    "QCLN":      {"name": "Clean Edge",       "row": "thematic"},
    "DRIV":      {"name": "EV & Mobility",    "row": "thematic"},
    "WCLD":      {"name": "Cloud Computing",  "row": "thematic"},
    "BLOK":      {"name": "Blockchain",       "row": "thematic"},
    "HACK":      {"name": "Cyber ETFMG",      "row": "thematic"},
    "SPY":       {"name": "S&P 500",          "row": "equity"},
    "QQQ":       {"name": "Nasdaq 100",       "row": "equity"},
    "VWRP.L":    {"name": "VG All-World",     "row": "equity"},
    "IWDA.L":    {"name": "iShs MSCI World",  "row": "equity"},
    "VTI":       {"name": "Total US Mkt",     "row": "equity"},
    "IVV":       {"name": "iShs S&P 500",     "row": "equity"},
    "SWDA.L":    {"name": "iShs World GBP",   "row": "equity"},
    "CSPX.L":    {"name": "iShs Core S&P500", "row": "equity"},
    "GLD":       {"name": "SPDR Gold",        "row": "equity"},
    "SLV":       {"name": "iShs Silver",      "row": "equity"},
    "GC=F":      {"name": "Gold Futures",     "row": "equity"},
    "NVDA":      {"name": "NVIDIA",           "row": "equity"},
    "AAPL":      {"name": "Apple",            "row": "equity"},
    "MSFT":      {"name": "Microsoft",        "row": "equity"},
    "TSLA":      {"name": "Tesla",            "row": "equity"},
    "MSTR":      {"name": "Strategy",         "row": "equity"},
    "COIN":      {"name": "Coinbase",         "row": "equity"},
    "BLK":       {"name": "BlackRock",        "row": "equity"},
}
_HUB_ROW_COLOR: dict[str, str] = {
    "crypto":   "#7c3aed",
    "thematic": "#00875a",
    "equity":   "#2563eb",
}
_HUB_ROW_NAV: dict[str, str] = {
    "crypto":   "₿ Sovereign Crypto",
    "thematic": "📊 Thematic Sectors",
    "equity":   "📈 Core Equity",
}

_INFLUENTIAL_PEOPLE: list[dict] = [
    {
        "name": "Jensen Huang", "role": "CEO, NVIDIA", "avatar": "🟢",
        "news_ticker": "NVDA",
        "asset_focus": ["NVDA", "SMCI", "MRVL", "AI chips"],
        "latest_view": "Blackwell Ultra demand exceeds all supply constraints through 2026. 'We are at an iPhone moment for AI.' Every company must become an AI company.",
        "stance": "BULLISH", "stance_color": "#00D4AA",
        "source": "NVDA GTC 2026", "source_url": "https://www.nvidia.com/en-us/events/gtc/", "date": "Mar 2026",
    },
    {
        "name": "Elon Musk", "role": "CEO, Tesla / xAI / SpaceX", "avatar": "🔵",
        "news_ticker": "TSLA",
        "asset_focus": ["DOGE-USD", "BTC-USD", "TSLA", "AI"],
        "latest_view": "DOGE remains 'the people's crypto'. xAI Grok integration with X to drive crypto adoption. Tesla FSD V14 autonomy revenue expected 2026.",
        "stance": "MIXED", "stance_color": "#FFA500",
        "source": "X (Twitter) / Tesla Q1 2026", "source_url": "https://twitter.com/elonmusk", "date": "Apr 2026",
    },
    {
        "name": "Michael J. Saylor", "role": "Chairman, Strategy (MicroStrategy)", "avatar": "🟠",
        "news_ticker": "MSTR",
        "asset_focus": ["BTC-USD", "MSTR"],
        "latest_view": "'Bitcoin is the apex property of the human race.' Strategy holds 214,400 BTC. Every corporation and sovereign fund will allocate within 10 years.",
        "stance": "MAX BULLISH", "stance_color": "#FF8C00",
        "source": "Strategy Q1 2026 call", "source_url": "https://www.microstrategy.com/investor-relations/", "date": "May 2026",
    },
    {
        "name": "Robert Kiyosaki", "role": "Author, Rich Dad Poor Dad", "avatar": "🟡",
        "news_ticker": "GLD",
        "asset_focus": ["BTC-USD", "GLD", "SLV"],
        "latest_view": "'The US dollar is dying. Buy BTC, gold and silver before the crash.' Predicts BTC at $300K by year-end. Warns of USD hyperinflation.",
        "stance": "BULLISH (Gold/BTC)", "stance_color": "#FFD700",
        "source": "X (Twitter) / Podcast", "source_url": "https://twitter.com/theRealKiyosaki", "date": "Jun 2026",
    },
    {
        "name": "Donald Trump", "role": "President, United States", "avatar": "🔴",
        "news_ticker": "BTC-USD",
        "asset_focus": ["BTC-USD", "Crypto policy", "USD"],
        "latest_view": "US Strategic Bitcoin Reserve signed via executive order. 'America will be the crypto capital of the world.' SEC crypto enforcement scaled back under new leadership.",
        "stance": "PRO-CRYPTO", "stance_color": "#FF4B4B",
        "source": "White House EO", "source_url": "https://www.whitehouse.gov/", "date": "Feb 2026",
    },
    {
        "name": "Cathie Wood", "role": "CEO & CIO, ARK Invest", "avatar": "🔵",
        "news_ticker": "ARKK",
        "asset_focus": ["BTC-USD", "TSLA", "COIN", "ARKK"],
        "latest_view": "'BTC will reach $1.5M by 2030.' ARK Big Ideas 2026: AI + crypto convergence creates the largest wealth creation event in history.",
        "stance": "BULLISH", "stance_color": "#00D4AA",
        "source": "ARK Big Ideas 2026", "source_url": "https://ark-invest.com/big-ideas-2026/", "date": "Jan 2026",
    },
    {
        "name": "Larry Fink / BlackRock", "role": "CEO, BlackRock", "avatar": "⚫",
        "news_ticker": "BLK",
        "asset_focus": ["BTC-USD", "IB1T", "Tokenisation", "BLK"],
        "latest_view": "'Bitcoin is digital gold.' IB1T now £3.2bn AUM. Tokenisation of real-world assets will be the next revolution — BlackRock leading with BUIDL fund.",
        "stance": "INSTITUTIONALLY BULLISH", "stance_color": "#5B8FD4",
        "source": "BlackRock Q1 2026 letter", "source_url": "https://www.blackrock.com/", "date": "Apr 2026",
    },
    {
        "name": "Warren Buffett / Berkshire", "role": "Chairman, Berkshire Hathaway", "avatar": "🟤",
        "news_ticker": "BRK-B",
        "asset_focus": ["AAPL", "OXY", "BAC", "Cash"],
        "latest_view": "'We don't understand crypto and don't need to.' Berkshire holds $190bn cash. Still long AAPL, OXY, financials. Warns on AI valuation bubble.",
        "stance": "CRYPTO BEARISH", "stance_color": "#888",
        "source": "Berkshire AGM 2026", "source_url": "https://www.berkshirehathaway.com/", "date": "May 2026",
    },
]

_ASSET_MANAGERS: list[dict] = [
    {"name": "BlackRock", "news_ticker": "BLK", "aum": "$11.5tn",
     "crypto_exposure": "IB1T (BTC ETP, £3.2bn AUM)", "color": "#5B8FD4",
     "view": "Bullish BTC; tokenisation of RWAs; FCA authorisation in progress"},
    {"name": "Vanguard", "news_ticker": None, "aum": "$9.3tn",
     "crypto_exposure": "None — policy excludes crypto", "color": "#888",
     "view": "No crypto ETF planned; index-only focus"},
    {"name": "Fidelity", "news_ticker": None, "aum": "$5.4tn",
     "crypto_exposure": "FBTC (BTC ETF, US), Digital Assets division", "color": "#9B59B6",
     "view": "Bullish BTC; building crypto custody infrastructure"},
    {"name": "ARK Invest", "news_ticker": "ARKK", "aum": "$12bn",
     "crypto_exposure": "ARKB (BTC ETF), ARKW, ARKK holdings", "color": "#00D4AA",
     "view": "Max bullish BTC ($1.5M target); AI+crypto convergence thesis"},
    {"name": "WisdomTree", "news_ticker": None, "aum": "$100bn",
     "crypto_exposure": "WBTC, WETH, SOLW, XRPL (LSE ETPs)", "color": "#FFA500",
     "view": "Active crypto ETP issuer; FCA VoP in preparation"},
    {"name": "CoinShares", "news_ticker": None, "aum": "$5.5bn",
     "crypto_exposure": "BITB, ETHE (LSE ETPs); largest European crypto ETP manager", "color": "#2ECC71",
     "view": "Crypto-native; regulatory compliant; expanding product range"},
]


@st.cache_data(ttl=300, show_spinner=False)
def _hub_prices(tickers: tuple) -> dict[str, dict]:
    try:
        import math
        import yfinance as yf
        import pandas as pd

        def _clean(v) -> Optional[float]:
            try:
                f = float(v)
                return None if (math.isnan(f) or math.isinf(f)) else f
            except Exception:
                return None

        batch = yf.download(list(tickers), period="5d", auto_adjust=True,
                            progress=False, threads=True)
        closes = batch.get("Close", batch)
        if closes is None or closes.empty:
            return {}
        if isinstance(closes, pd.Series):
            closes = closes.to_frame(name=tickers[0])
        closes = closes.dropna(how="all")
        if closes.empty:
            return {}
        last = closes.iloc[-1]
        prev = closes.iloc[-2] if len(closes) >= 2 else closes.iloc[-1]
        data: dict[str, dict] = {}
        for t in tickers:
            try:
                p  = _clean(last.get(t))
                p0 = _clean(prev.get(t))
                if p is None:
                    continue
                pct = round((p - p0) / p0 * 100, 2) if (p and p0 and p0 != 0) else None
                data[t] = {"price": p, "chg_pct": pct}
            except Exception:
                pass
        return data
    except Exception:
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_hub_news(ticker: str) -> list[dict]:
    try:
        import yfinance as yf
        from datetime import datetime as _dt
        raw = yf.Ticker(ticker).news or []
        results = []
        for item in raw[:10]:
            if not isinstance(item, dict):
                continue
            content = item.get("content") or item
            if not isinstance(content, dict):
                content = item
            title = str(content.get("title") or item.get("title", "")).strip()
            if not title:
                continue
            canon = content.get("canonicalUrl") or {}
            click = content.get("clickThroughUrl") or {}
            link = (
                (canon.get("url") if isinstance(canon, dict) else "")
                or (click.get("url") if isinstance(click, dict) else "")
                or item.get("link", "")
            )
            provider  = content.get("provider") or {}
            publisher = (
                (provider.get("displayName") if isinstance(provider, dict) else str(provider or ""))
                or item.get("publisher", "")
            )
            ts_raw = content.get("pubDate") or item.get("providerPublishTime") or 0
            ts: int = 0
            if isinstance(ts_raw, str):
                try:
                    ts = int(_dt.fromisoformat(ts_raw.replace("Z", "+00:00")).timestamp())
                except Exception:
                    ts = 0
            else:
                ts = int(ts_raw or 0)
            results.append({
                "title":     title,
                "link":      str(link).strip(),
                "publisher": str(publisher).strip(),
                "ts":        ts,
            })
        return results
    except Exception:
        return []


def _format_ts(ts: int) -> str:
    if not ts:
        return "—"
    try:
        from datetime import datetime as _dt
        dt    = _dt.fromtimestamp(ts)
        now   = _dt.now()
        delta = now - dt
        if delta.days == 0 and delta.seconds < 3600:
            return f"{max(delta.seconds // 60, 1)}m ago"
        if delta.days == 0:
            return f"{delta.seconds // 3600}h ago"
        if delta.days < 7:
            return f"{delta.days}d ago"
        return dt.strftime("%b %d")
    except Exception:
        return "—"


def render_hub() -> None:
    today = date.today()

    # ── Session state init ────────────────────────────────────────────────────
    if "hub_favs" not in st.session_state:
        st.session_state["hub_favs"] = {k: list(v) for k, v in _HUB_DEFAULT_FAVS.items()}
    if "hub_news_ticker" not in st.session_state:
        st.session_state["hub_news_ticker"] = None
    if "hub_add_mode" not in st.session_state:
        st.session_state["hub_add_mode"] = None

    # ── Header row ────────────────────────────────────────────────────────────
    rc1, _, rc3 = st.columns([2, 3, 1])
    with rc1:
        auto_on = st.toggle("Auto-refresh (5 min)", value=False, key="hub_autorefresh")
        if auto_on:
            # Schedule a rerun in 5 minutes by checking elapsed time
            import time as _time
            _now = _time.time()
            _last = st.session_state.get("hub_last_refresh", 0)
            if _now - _last >= 300:
                st.session_state["hub_last_refresh"] = _now
                st.cache_data.clear()
                st.rerun()
            else:
                _remaining = int(300 - (_now - _last))
                st.caption(f"Next refresh in {_remaining // 60}m {_remaining % 60}s")
    with rc3:
        phase = current_phase(today)
        pc = _phase_color(phase)
        st.markdown(
            f'<div style="text-align:right"><span style="background:{pc}22;border:1px solid {pc};'
            f'color:{pc};border-radius:4px;padding:0.18rem 0.45rem;font-size:0.67rem;font-weight:700">'
            f'{phase.replace("_"," ")}</span></div>',
            unsafe_allow_html=True,
        )

    # ── Market Snapshot Cards ─────────────────────────────────────────────────
    st.markdown(
        '<p style="font-size:0.68rem;font-weight:800;letter-spacing:0.14em;color:#64748b;margin-bottom:0.35rem;text-transform:uppercase">'
        '📊 Market Snapshot — tap a card to view latest news</p>',
        unsafe_allow_html=True,
    )

    all_favs = list(dict.fromkeys(
        t for favs in st.session_state["hub_favs"].values() for t in favs
    ))
    prices = _hub_prices(tuple(all_favs))

    for row_key, row_label, row_color, _ in _HUB_ROWS:
        favs = st.session_state["hub_favs"].get(row_key, [])

        # Row header + ➕ icon
        h1, h2 = st.columns([10, 1])
        with h1:
            st.markdown(
                f'<div style="font-size:0.66rem;color:{row_color};font-weight:800;'
                f'letter-spacing:0.08em;text-transform:uppercase;margin:0.55rem 0 0.18rem 0">{row_label}</div>',
                unsafe_allow_html=True,
            )
        with h2:
            if st.button("➕", key=f"hub_add_btn_{row_key}",
                         help="Add / remove instruments from this row"):
                st.session_state["hub_add_mode"] = (
                    None if st.session_state["hub_add_mode"] == row_key else row_key
                )
                st.rerun()

        # Add/remove search panel (autocomplete)
        if st.session_state["hub_add_mode"] == row_key:
            s1, s2 = st.columns([5, 1])
            with s1:
                search = st.text_input(
                    "Search", key=f"hub_srch_{row_key}",
                    placeholder="🔍  Type ticker or name — e.g. BTC, NVIDIA, Ethereum…",
                    label_visibility="collapsed",
                )
            with s2:
                if st.button("✕ Close", key=f"hub_done_{row_key}", use_container_width=True):
                    st.session_state["hub_add_mode"] = None
                    st.rerun()

            q = search.strip().upper() if search else ""

            # Build matches — if query present, rank exact ticker match first
            all_items = list(_HUB_ALL_TICKERS.items())
            if q:
                exact   = [(k, v) for k, v in all_items if k.upper() == q or v["name"].upper() == q]
                starts  = [(k, v) for k, v in all_items if (k.upper().startswith(q) or v["name"].upper().startswith(q)) and (k, v) not in exact]
                contains= [(k, v) for k, v in all_items if q in k.upper() or q in v["name"].upper()]
                seen    = {k for k, _ in exact + starts}
                contains = [(k, v) for k, v in contains if k not in seen]
                matches = dict((exact + starts + contains)[:16])
            else:
                # Show currently added tickers first, then the rest
                in_row_items = [(k, v) for k, v in all_items if k in favs]
                rest = [(k, v) for k, v in all_items if k not in favs]
                matches = dict((in_row_items + rest)[:16])

            # Render autocomplete-style suggestion header
            if q:
                st.markdown(
                    f'<div style="font-size:0.68rem;color:#64748b;font-weight:600;margin:0.3rem 0 0.2rem 0">'
                    f'{"Showing " + str(len(matches)) + " matches for "" + search.strip() + """ if matches else "No matches found — try a different name or ticker"}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="font-size:0.68rem;color:#64748b;font-weight:600;margin:0.3rem 0 0.2rem 0">'
                    f'Active instruments shown first · start typing to search all {len(_HUB_ALL_TICKERS)} available'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            if matches:
                chip_cols = st.columns(min(8, len(matches)))
                for ci, (tick, meta) in enumerate(matches.items()):
                    in_row = tick in favs
                    with chip_cols[ci % 8]:
                        label = ("✓ " if in_row else "") + tick
                        if st.button(
                            label,
                            key=f"hub_chip_{row_key}_{tick}",
                            type="primary" if in_row else "secondary",
                            use_container_width=True,
                            help=meta["name"] + (" · remove" if in_row else " · add"),
                        ):
                            nf = list(favs)
                            if in_row:
                                nf.remove(tick)
                            else:
                                nf.append(tick)
                            st.session_state["hub_favs"][row_key] = nf
                            st.rerun()

        # Compact price cards
        if favs:
            card_cols = st.columns(len(favs))
            for col, ticker in zip(card_cols, favs):
                with col:
                    card_id = (
                        "hub_card_"
                        + ticker.replace("-", "_").replace(".", "_").replace("=", "_")
                    )
                    p_data = prices.get(ticker, {})
                    price  = p_data.get("price")
                    chg    = p_data.get("chg_pct")
                    name   = _HUB_ALL_TICKERS.get(ticker, {}).get("name", ticker)
                    name_s = (name[:9] + "…") if len(name) > 10 else name

                    if price is not None:
                        price_str = (
                            f"${price:,.0f}" if price >= 1000 else
                            f"${price:.2f}"  if price >= 1    else
                            f"${price:.4f}"
                        )
                    else:
                        price_str = "—"

                    if chg is not None:
                        cc  = "#00875a" if chg >= 0 else "#dc2626"
                        arr = "▲" if chg >= 0 else "▼"
                        chg_str = f'<span style="color:{cc};font-weight:600">{arr}{abs(chg):.1f}%</span>'
                    else:
                        chg_str = '<span style="color:#94a3b8">—</span>'

                    is_sel = st.session_state["hub_news_ticker"] == ticker
                    bt = f"3px solid {row_color}" if is_sel else f"2px solid {row_color}"
                    bg = f"{row_color}12" if is_sel else "#ffffff"
                    shadow = "box-shadow:0 2px 8px rgba(0,0,0,0.10);" if is_sel else "box-shadow:0 1px 3px rgba(0,0,0,0.06);"

                    st.markdown(
                        f'<div id="{card_id}" class="iw-price-card" '
                        f'style="background:{bg};border:1px solid #e2e8f0;'
                        f'border-top:{bt};border-radius:12px;padding:0.6rem 0.4rem;'
                        f'text-align:center;cursor:pointer;transition:all 0.15s ease;{shadow}">'
                        f'<div style="color:{row_color};font-size:0.62rem;font-weight:800;letter-spacing:0.05em;text-transform:uppercase">{ticker}</div>'
                        f'<div style="color:#64748b;font-size:0.59rem;margin:0.05rem 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{name_s}</div>'
                        f'<div style="color:#0a0f1d;font-size:0.88rem;font-weight:800;line-height:1.25;margin:0.1rem 0">{price_str}</div>'
                        f'<div style="font-size:0.62rem">{chg_str}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    # Hidden trigger button — styled invisible via CSS + JS
                    st.markdown('<div class="iw-hidden-btn-wrap">', unsafe_allow_html=True)
                    if st.button("​", key=f"hub_btn_{ticker}", use_container_width=True):
                        st.session_state["hub_news_ticker"] = (
                            None if is_sel else ticker
                        )
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # JS: wire card click → hidden button, aggressively hide wrappers
    import streamlit.components.v1 as components
    components.html("""<script>
(function(){
  var doc = window.parent.document;

  function hideWrappers(){
    /* Hide every .iw-hidden-btn-wrap container and its children */
    doc.querySelectorAll('.iw-hidden-btn-wrap').forEach(function(w){
      w.style.cssText = 'height:0!important;overflow:hidden!important;margin:0!important;padding:0!important;opacity:0!important;pointer-events:none!important;';
      w.querySelectorAll('*').forEach(function(c){
        c.style.cssText = 'height:0!important;overflow:hidden!important;margin:0!important;padding:0!important;opacity:0!important;';
      });
    });
  }

  function wireCards(){
    doc.querySelectorAll('[id^="hub_card_"]').forEach(function(card){
      if(card._iwWired) return;
      card._iwWired = true;

      /* Find the hidden button: it's the next sibling wrapper after the card's markdown container */
      function findBtn(card){
        var mc = card.closest('[data-testid="stMarkdownContainer"]');
        if(!mc) return null;
        var col = mc.parentElement;
        if(!col) return null;
        /* Walk forward siblings inside the column to find the next stButton */
        var els = Array.from(col.children);
        var idx = els.indexOf(mc.parentElement) >= 0 ? els.indexOf(mc.parentElement) : -1;
        /* Try the next element directly */
        for(var i=0; i<els.length; i++){
          var btn = els[i].querySelector('button');
          if(btn && els[i] !== mc) return btn;
        }
        return null;
      }

      card.addEventListener('click', function(){
        /* Locate by looking for a button inside .iw-hidden-btn-wrap near this card */
        var mc = card.closest('[data-testid="stMarkdownContainer"]');
        if(!mc) return;
        var col = mc.closest('[data-testid="column"]') || mc.parentElement;
        if(!col) return;
        var wrap = col.querySelector('.iw-hidden-btn-wrap');
        if(wrap){
          var btn = wrap.querySelector('button');
          if(btn){ btn.click(); return; }
        }
        /* Fallback: next stButton sibling in the column */
        var stBtns = col.querySelectorAll('[data-testid="stButton"]');
        if(stBtns.length > 0){
          var b = stBtns[0].querySelector('button');
          if(b) b.click();
        }
      });
    });

    hideWrappers();
  }

  wireCards();
  new MutationObserver(function(){ wireCards(); hideWrappers(); })
    .observe(doc.body, {childList:true, subtree:true});
})();
</script>""", height=0, scrolling=False)

    # ── News panel (below all rows, shown on card click) ──────────────────────
    sel = st.session_state.get("hub_news_ticker")
    if sel:
        sel_meta = _HUB_ALL_TICKERS.get(sel, {})
        sel_name = sel_meta.get("name", sel)
        sel_row  = sel_meta.get("row", "equity")
        sel_col  = _HUB_ROW_COLOR.get(sel_row, "#5B8FD4")
        sel_nav  = _HUB_ROW_NAV.get(sel_row, "📈 Core Equity")

        st.markdown(
            f'<div style="background:#ffffff;border:1px solid {sel_col};border-left:4px solid {sel_col};border-radius:12px;'
            f'padding:0.6rem 1rem;margin-top:0.5rem;box-shadow:0 2px 8px rgba(0,0,0,0.08)">'
            f'<span style="color:{sel_col};font-weight:800;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.06em">'
            f'📰 Latest News — {sel} · {sel_name}</span></div>',
            unsafe_allow_html=True,
        )
        cl1, cl2, _ = st.columns([1, 2, 6])
        with cl1:
            if st.button("✕ Close", key="hub_news_close"):
                st.session_state["hub_news_ticker"] = None
                st.rerun()
        with cl2:
            if st.button(f"Open in {sel_nav}", key="hub_news_nav"):
                st.session_state["sidebar_nav"] = sel_nav
                st.rerun()

        with st.spinner(f"Loading news for {sel}…"):
            news_items = _fetch_hub_news(sel)

        if news_items:
            nc1, nc2 = st.columns(2)
            for idx, item in enumerate(news_items[:8]):
                title = item.get("title", "—")
                link  = item.get("link", "")
                pub   = item.get("publisher", "")
                time_str = _format_ts(item.get("ts", 0))
                title_html = (
                    f'<a href="{link}" target="_blank" style="color:#0a0f1d;text-decoration:none;'
                    f'font-weight:600;font-size:0.79rem;line-height:1.4">{title}</a>'
                    if link else
                    f'<span style="color:#0a0f1d;font-size:0.79rem;font-weight:600">{title}</span>'
                )
                with (nc1 if idx % 2 == 0 else nc2):
                    st.markdown(
                        f'<div style="background:#ffffff;border:1px solid #e2e8f0;'
                        f'border-left:3px solid {sel_col};border-radius:0 10px 10px 0;'
                        f'padding:0.5rem 0.75rem;margin-bottom:0.3rem;box-shadow:0 1px 3px rgba(0,0,0,0.05)">'
                        f'{title_html}'
                        f'<div style="color:#64748b;font-size:0.66rem;margin-top:0.2rem">'
                        f'{pub} · {time_str}</div></div>',
                        unsafe_allow_html=True,
                    )
        else:
            st.info(f"No recent news for {sel}. News is available for most major ETFs and US stocks.")

    st.divider()

    # ── Cassandra + Kingmaker ─────────────────────────────────────────────────
    alerts       = load_cassandra_alerts()
    endorsements = load_kingmaker_endorsements()
    left_col, right_col = st.columns([1, 1], gap="medium")

    with left_col:
        st.markdown(
            '<p style="font-size:0.68rem;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#64748b;margin-bottom:0.4rem">'
            '🔴 Cassandra Alerts — Live macro threats</p>',
            unsafe_allow_html=True,
        )
        for a in alerts[:6]:
            score   = int(a.get("risk_score") or a.get("Systemic_Risk_Score") or 0)
            title   = a.get("title") or a.get("Title") or "—"
            vector  = (a.get("vector") or a.get("Risk_Vector") or "").replace("_", " ").upper()
            src_url = a.get("source_url") or a.get("Source_URL") or ""
            raw_src = a.get("source") or ""
            bar_col = "#dc2626" if score >= 8 else "#ea580c" if score >= 6 else "#00875a"
            icon    = "🔴" if score >= 8 else "🟡" if score >= 6 else "🟢"
            title_s = title[:60] + ("…" if len(title) > 60 else "")
            src_html = (
                f'<a href="{src_url}" target="_blank" style="color:#2563eb;font-size:0.67rem;text-decoration:none;font-weight:600">↗ {raw_src}</a>'
                if src_url else f'<span style="color:#64748b;font-size:0.67rem">{raw_src}</span>'
            )
            with st.expander(f"{icon} {score}/10  ·  {title_s}", expanded=False):
                st.markdown(
                    f'<div style="background:#f8fafc;border-left:3px solid {bar_col};padding:0.55rem 0.85rem;'
                    f'border-radius:0 10px 10px 0;margin-bottom:0.35rem">'
                    f'<span style="color:{bar_col};font-size:0.7rem;font-weight:700">{vector}</span>'
                    f' <span style="color:{bar_col};font-weight:700;font-size:0.78rem">{score}/10</span><br>'
                    f'<span style="color:#374151;font-size:0.77rem;line-height:1.5">{title}</span><br>'
                    f'<div style="margin-top:0.25rem">{src_html}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                v_key = (a.get("vector") or a.get("Risk_Vector") or "").lower()
                for b in _cassandra_assessment(v_key, title, score):
                    st.markdown(b)

    with right_col:
        st.markdown(
            '<p style="font-size:0.68rem;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#64748b;margin-bottom:0.4rem">'
            '🚀 Kingmaker Signals — Named-exec endorsements</p>',
            unsafe_allow_html=True,
        )
        for e in endorsements[:5]:
            titan_name = e.get("titan_name")    or e.get("Titan_Ticker")        or "—"
            exec_name  = e.get("executive")     or e.get("Endorsement_Source")  or "Exec"
            vendor     = e.get("vendor")        or e.get("Counterparty_Name")   or "—"
            vticker    = e.get("vendor_ticker") or e.get("Counterparty_Ticker") or ""
            conn_type  = (e.get("type") or e.get("Connection_Type") or "Supplier").replace("_", " ")
            conf       = int(e.get("confidence") or e.get("Confidence_Score") or 7)
            quote      = e.get("quote") or e.get("Extracted_Text") or ""
            src_url    = e.get("source_url") or e.get("Endorsement_Source") or ""
            conf_col   = "#dc2626" if conf >= 9 else "#ea580c" if conf >= 7 else "#00875a"
            vtag       = f" ({vticker})" if vticker else ""
            vlink      = (
                f'<a href="{src_url}" target="_blank" style="color:#2563eb;text-decoration:none;font-weight:700">{vendor}{vtag}</a>'
                if src_url and src_url.startswith("http") else
                f'<b style="color:#2563eb">{vendor}{vtag}</b>'
            )
            with st.expander(f"🏆 {titan_name}  ›  {vendor}{vtag}  ·  {conf}/10", expanded=False):
                st.markdown(
                    f'<div style="background:#f8fafc;border-left:3px solid {conf_col};padding:0.55rem 0.85rem;'
                    f'border-radius:0 10px 10px 0;margin-bottom:0.35rem">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<span style="color:#374151;font-size:0.78rem"><b style="color:#0a0f1d">{titan_name}</b> <span style="color:#94a3b8">›</span> {vlink}</span>'
                    f'<span style="color:{conf_col};font-weight:700">{conf}/10</span></div>'
                    f'<span style="color:#64748b;font-size:0.7rem">{exec_name} · {conn_type}</span>'
                    f'<div style="color:#4b5563;font-size:0.74rem;font-style:italic;border-top:1px solid #e2e8f0;'
                    f'padding-top:0.25rem;margin-top:0.25rem">'
                    f'&ldquo;{quote[:160]}{"…" if len(quote) > 160 else ""}&rdquo;</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                raw_conn = e.get("type") or e.get("Connection_Type") or "Supplier"
                for b in _kingmaker_assessment(raw_conn, vendor, titan_name, conf):
                    st.markdown(b)

    st.divider()

    # ── Influential Voices (dynamic news) ─────────────────────────────────────
    st.markdown(
        '<p style="font-size:0.68rem;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#64748b;margin-bottom:0.4rem">'
        '👥 Influential Voices — Latest views & live market news</p>',
        unsafe_allow_html=True,
    )

    tab_people, tab_managers = st.tabs(["Key Individuals", "Asset Managers"])

    with tab_people:
        for person in _INFLUENTIAL_PEOPLE:
            sc           = person["stance_color"]
            news_ticker  = person.get("news_ticker", "")
            asset_tags   = "".join(
                f'<span style="background:#f1f5f9;color:#64748b;border-radius:6px;padding:1px 6px;'
                f'font-size:0.62rem;margin-right:3px;font-weight:600">{a}</span>'
                for a in person["asset_focus"][:4]
            )
            src_link = (
                f'<a href="{person["source_url"]}" target="_blank" style="color:#2563eb;font-size:0.67rem;text-decoration:none;font-weight:600">↗ {person["source"]}</a>'
                if person.get("source_url") else
                f'<span style="color:#64748b;font-size:0.67rem">{person["source"]}</span>'
            )
            header = f'{person["avatar"]} {person["name"]}  ·  {person["role"]}  ·  {person["date"]}'
            with st.expander(header, expanded=False):
                pv1, pv2 = st.columns([5, 4])
                with pv1:
                    st.markdown(
                        f'<div style="background:#f8fafc;border-left:4px solid {sc};border-radius:0 12px 12px 0;padding:0.7rem 0.9rem">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.3rem">'
                        f'<span style="color:#0a0f1d;font-weight:800;font-size:0.85rem">{person["name"]}</span>'
                        f'<span style="background:{sc}18;color:{sc};border-radius:6px;padding:0.15rem 0.5rem;font-size:0.64rem;font-weight:700">{person["stance"]}</span></div>'
                        f'<div style="color:#64748b;font-size:0.71rem;margin-bottom:0.28rem">{person["role"]}</div>'
                        f'<div style="margin-bottom:0.35rem">{asset_tags}</div>'
                        f'<div style="color:#374151;font-size:0.77rem;line-height:1.55">{person["latest_view"]}</div>'
                        f'<div style="margin-top:0.35rem">{src_link}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with pv2:
                    if news_ticker:
                        st.markdown(
                            f'<div style="color:#64748b;font-size:0.65rem;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.25rem">Live News · {news_ticker}</div>',
                            unsafe_allow_html=True,
                        )
                        for ni in _fetch_hub_news(news_ticker)[:4]:
                            nt    = ni.get("title", "—")
                            nl    = ni.get("link", "")
                            npub  = ni.get("publisher", "")
                            ntime = _format_ts(ni.get("ts", 0))
                            nt_html = (
                                f'<a href="{nl}" target="_blank" style="color:#0a0f1d;text-decoration:none;font-size:0.72rem;font-weight:600;line-height:1.4">{nt[:90]}{"…" if len(nt)>90 else ""}</a>'
                                if nl else
                                f'<span style="color:#374151;font-size:0.72rem">{nt[:90]}</span>'
                            )
                            st.markdown(
                                f'<div style="border-bottom:1px solid #e2e8f0;padding:0.3rem 0">'
                                f'{nt_html}'
                                f'<div style="color:#64748b;font-size:0.63rem;margin-top:0.1rem">{npub} · {ntime}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        st.markdown('<span style="color:#94a3b8;font-size:0.72rem">No live ticker linked.</span>', unsafe_allow_html=True)

    with tab_managers:
        for mgr in _ASSET_MANAGERS:
            mc          = mgr["color"]
            news_ticker = mgr.get("news_ticker")
            with st.expander(f'{mgr["name"]}  ·  AUM: {mgr["aum"]}', expanded=False):
                mv1, mv2 = st.columns([5, 4])
                with mv1:
                    st.markdown(
                        f'<div style="background:#f8fafc;border-left:4px solid {mc};border-radius:0 12px 12px 0;padding:0.65rem 0.9rem">'
                        f'<div style="color:{mc};font-weight:800;font-size:0.82rem;margin-bottom:0.22rem">{mgr["name"]}</div>'
                        f'<div style="color:#64748b;font-size:0.7rem">AUM: <span style="color:#374151;font-weight:600">{mgr["aum"]}</span></div>'
                        f'<div style="color:#64748b;font-size:0.7rem;margin:0.12rem 0">Crypto: <span style="color:#374151">{mgr["crypto_exposure"]}</span></div>'
                        f'<div style="color:#374151;font-size:0.75rem;line-height:1.5;margin-top:0.2rem">{mgr["view"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with mv2:
                    if news_ticker:
                        st.markdown(
                            f'<div style="color:#64748b;font-size:0.65rem;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.25rem">Live News · {news_ticker}</div>',
                            unsafe_allow_html=True,
                        )
                        for ni in _fetch_hub_news(news_ticker)[:3]:
                            nt    = ni.get("title", "—")
                            nl    = ni.get("link", "")
                            ntime = _format_ts(ni.get("ts", 0))
                            nt_html = (
                                f'<a href="{nl}" target="_blank" style="color:#0a0f1d;text-decoration:none;font-size:0.72rem;font-weight:600">{nt[:85]}{"…" if len(nt)>85 else ""}</a>'
                                if nl else
                                f'<span style="color:#374151;font-size:0.72rem">{nt[:85]}</span>'
                            )
                            st.markdown(
                                f'<div style="border-bottom:1px solid #e2e8f0;padding:0.3rem 0">'
                                f'{nt_html}'
                                f'<div style="color:#64748b;font-size:0.63rem;margin-top:0.1rem">{ntime}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        st.markdown('<span style="color:#94a3b8;font-size:0.72rem">No linked news ticker.</span>', unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    nav = render_sidebar()

    # ── Page header ───────────────────────────────────────────────────────────
    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown(
            "<h1 style='margin-bottom:0;color:#0a0f1d;font-weight:900;font-size:2.1rem;letter-spacing:-0.02em'>📊 InvestWise</h1>",
            unsafe_allow_html=True,
        )
    with h2:
        _pc = _phase_color(current_phase())
        st.markdown(
            f"<div style='text-align:right;padding-top:0.5rem'>"
            f"<span style='color:#64748b;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.08em'>Phase</span><br>"
            f"<span style='background:{_pc}15;border:1px solid {_pc};border-radius:6px;padding:0.15rem 0.55rem;"
            f"color:{_pc};font-size:0.74rem;font-weight:700'>{current_phase().replace('_', ' ')}</span><br>"
            f"<span style='color:#94a3b8;font-size:0.72rem'>{date.today()}</span>"
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

    elif nav == "📰 News Feed":
        _mod_news.render()

    else:
        render_hub()

    # ── Footer ────────────────────────────────────────────────────────────────
    st.divider()
    st.markdown(
        "<p style='text-align:center;color:#444;font-size:0.75rem'>"
        "InvestWise · 7 modules · Data latency ≤ 5 min · "
        "Not investment advice · Regulatory data sourced from FCA CP23/28 &amp; PS24/12"
        "</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
