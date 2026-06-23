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
            key="sidebar_nav",
            label_visibility="collapsed",
        )

    return nav


# ═════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE HUB — helpers and data
# ═════════════════════════════════════════════════════════════════════════════

_HUB_DEFAULT_CRYPTO = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"]
_HUB_DEFAULT_THEMATIC = ["BOTZ", "ARKK", "CIBR", "ICLN"]
_HUB_DEFAULT_EQUITY = ["SPY", "QQQ", "VWRP.L", "IWDA.L"]

_HUB_TICKER_META: dict[str, dict] = {
    "BTC-USD":  {"name": "Bitcoin",       "module": "₿ Sovereign Crypto"},
    "ETH-USD":  {"name": "Ethereum",      "module": "₿ Sovereign Crypto"},
    "SOL-USD":  {"name": "Solana",        "module": "₿ Sovereign Crypto"},
    "XRP-USD":  {"name": "XRP",           "module": "₿ Sovereign Crypto"},
    "BOTZ":     {"name": "BOTZ AI/Robot", "module": "📊 Thematic Sectors"},
    "ARKK":     {"name": "ARK Innovation","module": "📊 Thematic Sectors"},
    "CIBR":     {"name": "CIBR Cyber",    "module": "📊 Thematic Sectors"},
    "ICLN":     {"name": "iShares Clean Energy","module": "📊 Thematic Sectors"},
    "SPY":      {"name": "S&P 500 ETF",   "module": "📈 Core Equity"},
    "QQQ":      {"name": "Nasdaq 100",    "module": "📈 Core Equity"},
    "VWRP.L":   {"name": "Vanguard All-World","module": "📈 Core Equity"},
    "IWDA.L":   {"name": "iShares Core MSCI World","module": "📈 Core Equity"},
    "GLD":      {"name": "SPDR Gold",     "module": "🥇 Precious Metals"},
    "SLV":      {"name": "iShares Silver","module": "🥇 Precious Metals"},
    "GC=F":     {"name": "Gold Futures",  "module": "🥇 Precious Metals"},
    "SI=F":     {"name": "Silver Futures","module": "🥇 Precious Metals"},
}

_HUB_TICKER_COLOR: dict[str, str] = {
    "₿ Sovereign Crypto":  "#9B59B6",
    "📊 Thematic Sectors": "#2ECC71",
    "📈 Core Equity":      "#5B8FD4",
    "🥇 Precious Metals":  "#FFD700",
}

_INFLUENTIAL_PEOPLE: list[dict] = [
    {
        "name": "Jensen Huang",
        "role": "CEO, NVIDIA",
        "avatar": "🟢",
        "asset_focus": ["AI chips", "Data centres", "NVDA", "SMCI", "MRVL"],
        "latest_view": "Blackwell Ultra demand exceeds all supply constraints through 2026; data-centre CAPEX cycle is just beginning. 'We are at an iPhone moment for AI.'",
        "stance": "BULLISH",
        "stance_color": "#00D4AA",
        "source": "NVDA GTC 2026 keynote",
        "source_url": "https://www.nvidia.com/en-us/events/gtc/",
        "date": "Mar 2026",
    },
    {
        "name": "Elon Musk",
        "role": "CEO, Tesla / xAI / SpaceX",
        "avatar": "🔵",
        "asset_focus": ["DOGE", "BTC", "AI", "TSLA"],
        "latest_view": "DOGE remains 'the people's crypto'. xAI Grok integration with X could drive crypto payment adoption. Tesla not currently buying BTC.",
        "stance": "MIXED",
        "stance_color": "#FFA500",
        "source": "X (Twitter) / Tesla Q1 2026 earnings",
        "source_url": "https://twitter.com/elonmusk",
        "date": "Apr 2026",
    },
    {
        "name": "Michael J. Saylor",
        "role": "Chairman, Strategy (MicroStrategy)",
        "avatar": "🟠",
        "asset_focus": ["BTC", "MSTR"],
        "latest_view": "'Bitcoin is the apex property of the human race.' Strategy holds 214,400 BTC. Every corporation, nation, and sovereign fund will allocate to BTC within 10 years.",
        "stance": "MAX BULLISH",
        "stance_color": "#FF8C00",
        "source": "Strategy Q1 2026 investor call",
        "source_url": "https://www.microstrategy.com/investor-relations/",
        "date": "May 2026",
    },
    {
        "name": "Robert Kiyosaki",
        "role": "Author, Rich Dad Poor Dad",
        "avatar": "🟡",
        "asset_focus": ["BTC", "Gold", "Silver"],
        "latest_view": "'The US dollar is dying. Buy BTC, gold, and silver before the crash.' Predicts BTC at $300K by year-end. Warns of USD hyperinflation.",
        "stance": "BULLISH (Gold/BTC)",
        "stance_color": "#FFD700",
        "source": "X (Twitter) / Podcast",
        "source_url": "https://twitter.com/theRealKiyosaki",
        "date": "Jun 2026",
    },
    {
        "name": "Donald Trump",
        "role": "President, United States",
        "avatar": "🔴",
        "asset_focus": ["BTC", "Crypto", "USD", "DJT"],
        "latest_view": "US Strategic Bitcoin Reserve signed by executive order. 'America will be the crypto capital of the world.' Pro-deregulation stance; SEC crypto enforcement scaled back.",
        "stance": "PRO-CRYPTO",
        "stance_color": "#FF4B4B",
        "source": "White House EO / Mar-a-Lago Crypto Summit",
        "source_url": "https://www.whitehouse.gov/",
        "date": "Feb 2026",
    },
    {
        "name": "Cathie Wood",
        "role": "CEO & CIO, ARK Invest",
        "avatar": "🔵",
        "asset_focus": ["BTC", "ETH", "TSLA", "AI", "ARKK"],
        "latest_view": "'BTC will reach $1.5M by 2030.' ARK 5-year forecast: AI + crypto convergence creates largest wealth creation in history. Conviction buys in TSLA and COIN dips.",
        "stance": "BULLISH",
        "stance_color": "#00D4AA",
        "source": "ARK Big Ideas 2026",
        "source_url": "https://ark-invest.com/big-ideas-2026/",
        "date": "Jan 2026",
    },
    {
        "name": "BlackRock (Larry Fink)",
        "role": "CEO, BlackRock",
        "avatar": "⚫",
        "asset_focus": ["BTC", "IB1T", "ETFs", "Tokenisation"],
        "latest_view": "'Bitcoin is digital gold.' IB1T now $3.2bn AUM. Tokenisation of real-world assets will be the next revolution — BlackRock leading with BUIDL fund.",
        "stance": "INSTITUTIONALLY BULLISH",
        "stance_color": "#5B8FD4",
        "source": "BlackRock Q1 2026 investor letter",
        "source_url": "https://www.blackrock.com/us/individual/literature/whitepaper/bii-bitcoin-etf.pdf",
        "date": "Apr 2026",
    },
    {
        "name": "Warren Buffett / Berkshire",
        "role": "Chairman, Berkshire Hathaway",
        "avatar": "🟤",
        "asset_focus": ["AAPL", "OXY", "BAC", "Cash"],
        "latest_view": "'We don't understand crypto and don't need to.' Berkshire holds $190bn in cash. Warnings about AI valuation bubble. Still long AAPL, OXY, financial stocks.",
        "stance": "CRYPTO BEARISH",
        "stance_color": "#888",
        "source": "Berkshire Hathaway Annual Meeting 2026",
        "source_url": "https://www.berkshirehathaway.com/meet26/2026ar.pdf",
        "date": "May 2026",
    },
]

_ASSET_MANAGERS: list[dict] = [
    {"name": "BlackRock", "aum": "$11.5tn", "crypto_exposure": "IB1T (BTC ETP, £3.2bn AUM)", "view": "Bullish BTC; tokenisation of RWAs; FCA authorisation in progress", "color": "#5B8FD4"},
    {"name": "Vanguard", "aum": "$9.3tn", "crypto_exposure": "None — policy excludes crypto", "view": "No crypto ETF planned; index focus", "color": "#888"},
    {"name": "Fidelity", "aum": "$5.4tn", "crypto_exposure": "FBTC (BTC ETF, US), Digital Assets division", "view": "Bullish BTC; building crypto custody infrastructure", "color": "#9B59B6"},
    {"name": "ARK Invest", "aum": "$12bn", "crypto_exposure": "ARKB (BTC ETF), ARKW, ARKK holdings", "view": "Max bullish BTC ($1.5M target); AI+crypto convergence thesis", "color": "#00D4AA"},
    {"name": "WisdomTree", "aum": "$100bn", "crypto_exposure": "WBTC, WETH, SOLW, XRPL (LSE ETPs)", "view": "Active crypto ETP issuer; FCA VoP in preparation", "color": "#FFA500"},
    {"name": "CoinShares", "aum": "$5.5bn", "crypto_exposure": "BITB, ETHE (LSE ETPs); largest European crypto ETP manager", "view": "Crypto-native; regulatory compliant; expanding product range", "color": "#2ECC71"},
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


def _price_card(ticker: str, prices: dict, nav_target: str) -> None:
    meta = _HUB_TICKER_META.get(ticker, {})
    name = meta.get("name", ticker)
    color = _HUB_TICKER_COLOR.get(nav_target, "#888")
    p_data = prices.get(ticker, {})
    price = p_data.get("price")
    chg   = p_data.get("chg_pct")

    if price is not None:
        if price > 1000:
            price_str = f"${price:,.0f}"
        elif price > 1:
            price_str = f"${price:,.2f}"
        else:
            price_str = f"${price:.4f}"
    else:
        price_str = "—"

    if chg is not None:
        chg_color = "#00D4AA" if chg >= 0 else "#FF4B4B"
        chg_str   = f'<span style="color:{chg_color};font-size:0.72rem">{"▲" if chg >= 0 else "▼"} {abs(chg):.2f}%</span>'
    else:
        chg_str = '<span style="color:#555;font-size:0.72rem">—</span>'

    st.markdown(
        f'<div style="background:#1A1D24;border:1px solid #2E3140;border-top:2px solid {color};'
        f'border-radius:8px;padding:0.6rem 0.75rem;text-align:center">'
        f'<div style="color:{color};font-size:0.68rem;font-weight:700;letter-spacing:0.06em">{ticker}</div>'
        f'<div style="color:#ccc;font-size:0.72rem;margin:0.1rem 0">{name}</div>'
        f'<div style="color:#fff;font-size:1.05rem;font-weight:700">{price_str}</div>'
        f'{chg_str}'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("→", key=f"hub_nav_{ticker}", use_container_width=True):
        st.session_state["sidebar_nav"] = nav_target
        st.rerun()


def render_hub() -> None:
    today = date.today()
    alerts       = load_cassandra_alerts()
    endorsements = load_kingmaker_endorsements()

    # ── Top row: refresh + phase indicator ───────────────────────────────────
    rc1, rc2, rc3 = st.columns([2, 2, 1])
    with rc1:
        auto_refresh = st.toggle("Auto-refresh (5 min)", value=False, key="hub_autorefresh")
        if auto_refresh:
            st.cache_data.clear()
            st.rerun()
    with rc3:
        phase = current_phase(today)
        phase_colors = {"PRE_GATEWAY": "#4A7C59", "GATEWAY_OPEN": "#FFA500",
                        "POST_GATEWAY": "#CC5500", "ENFORCEMENT_CLIFF": "#CC0000"}
        pc = phase_colors.get(phase, "#888")
        st.markdown(
            f'<div style="text-align:right"><span style="background:{pc}22;border:1px solid {pc};'
            f'color:{pc};border-radius:4px;padding:0.2rem 0.5rem;font-size:0.72rem;font-weight:700">'
            f'{phase.replace("_", " ")}</span></div>',
            unsafe_allow_html=True,
        )

    # ── Section 1: Market Snapshot Cards ────────────────────────────────────
    st.markdown(
        '<p style="font-size:0.72rem;font-weight:700;letter-spacing:0.12em;color:#888;margin-bottom:0.3rem">'
        '📊 MARKET SNAPSHOT</p>',
        unsafe_allow_html=True,
    )

    with st.expander("⚙️ Customise Instruments", expanded=False):
        cust_c1, cust_c2, cust_c3 = st.columns(3)
        with cust_c1:
            st.multiselect(
                "Cryptocurrencies", ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "DOGE-USD", "ADA-USD", "AVAX-USD"],
                default=st.session_state.get("hub_crypto_picks", _HUB_DEFAULT_CRYPTO),
                key="hub_crypto_picks",
            )
        with cust_c2:
            st.multiselect(
                "Thematic ETFs", ["BOTZ", "ARKK", "CIBR", "ICLN", "QCLN", "ROBO", "DRIV", "WCLD"],
                default=st.session_state.get("hub_thematic_picks", _HUB_DEFAULT_THEMATIC),
                key="hub_thematic_picks",
            )
        with cust_c3:
            st.multiselect(
                "Core Equity ETFs", ["SPY", "QQQ", "VWRP.L", "IWDA.L", "VTI", "IVV", "SWDA.L", "CSPX.L", "GLD", "SLV"],
                default=st.session_state.get("hub_equity_picks", _HUB_DEFAULT_EQUITY),
                key="hub_equity_picks",
            )

    crypto_picks   = st.session_state.get("hub_crypto_picks",   _HUB_DEFAULT_CRYPTO) or _HUB_DEFAULT_CRYPTO
    thematic_picks = st.session_state.get("hub_thematic_picks", _HUB_DEFAULT_THEMATIC) or _HUB_DEFAULT_THEMATIC
    equity_picks   = st.session_state.get("hub_equity_picks",   _HUB_DEFAULT_EQUITY) or _HUB_DEFAULT_EQUITY

    all_tickers = tuple(dict.fromkeys(crypto_picks + thematic_picks + equity_picks))
    prices = _hub_prices(all_tickers)

    for row_label, row_tickers, row_nav in [
        ("₿ Sovereign Crypto",  crypto_picks,   "₿ Sovereign Crypto"),
        ("📊 Thematic Sectors", thematic_picks, "📊 Thematic Sectors"),
        ("📈 Core Equity",      equity_picks,   "📈 Core Equity"),
    ]:
        row_color = _HUB_TICKER_COLOR.get(row_nav, "#888")
        st.markdown(
            f'<div style="font-size:0.68rem;color:{row_color};font-weight:700;'
            f'letter-spacing:0.08em;margin:0.5rem 0 0.2rem 0">{row_label}</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(len(row_tickers))
        for col, ticker in zip(cols, row_tickers):
            with col:
                nav_mod = _HUB_TICKER_META.get(ticker, {}).get("module", row_nav)
                _price_card(ticker, prices, nav_mod)

    st.divider()

    # ── Section 2 & 3: Cassandra + Kingmaker side by side ───────────────────
    left_col, right_col = st.columns([1, 1], gap="medium")

    with left_col:
        st.markdown(
            '<p style="font-size:0.72rem;font-weight:700;letter-spacing:0.12em;color:#888;margin-bottom:0.4rem">'
            '🔴 CASSANDRA ALERTS — Live macro threats</p>',
            unsafe_allow_html=True,
        )
        for a in alerts[:6]:
            score   = int(a.get("risk_score") or a.get("Systemic_Risk_Score") or 0)
            title   = a.get("title") or a.get("Title") or "—"
            vector  = (a.get("vector") or a.get("Risk_Vector") or "").replace("_", " ").upper()
            src_url = a.get("source_url") or a.get("Source_URL") or ""
            raw_src = a.get("source") or ""

            bar_color = "#FF4B4B" if score >= 8 else "#FFA500" if score >= 6 else "#4A7C59"
            bar_pct   = int(score * 10)

            title_html = (
                f'<a href="{src_url}" target="_blank" style="color:#ddd;text-decoration:none">{title}</a>'
                if src_url else f'<span style="color:#ddd">{title}</span>'
            )
            src_html = (
                f'<a href="{src_url}" target="_blank" style="color:#00D4AA;font-size:0.68rem;text-decoration:none">↗ {raw_src}</a>'
                if src_url else f'<span style="color:#666;font-size:0.68rem">{raw_src}</span>'
            )

            with st.expander(f"{'🔴' if score >= 8 else '🟡' if score >= 6 else '🟢'} {score}/10 · {title[:55]}{'…' if len(title) > 55 else ''}", expanded=False):
                st.markdown(
                    f'<div style="background:#1A1D24;border-left:3px solid {bar_color};padding:0.5rem 0.8rem;border-radius:0 6px 6px 0;margin-bottom:0.4rem">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.3rem">'
                    f'<span style="color:{bar_color};font-size:0.7rem;font-weight:700">{vector}</span>'
                    f'<span style="color:{bar_color};font-weight:700;font-size:0.8rem">{score}/10</span></div>'
                    f'<div style="background:#2E3140;border-radius:3px;height:4px;margin-bottom:0.35rem">'
                    f'<div style="background:{bar_color};width:{bar_pct}%;height:4px;border-radius:3px"></div></div>'
                    f'<div style="font-size:0.78rem;color:#bbb;line-height:1.4">{title_html}</div>'
                    f'<div style="margin-top:0.3rem">{src_html}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                v_key = (a.get("vector") or a.get("Risk_Vector") or "").lower()
                bullets = _cassandra_assessment(v_key, title, score)
                for b in bullets:
                    st.markdown(b)

    with right_col:
        st.markdown(
            '<p style="font-size:0.72rem;font-weight:700;letter-spacing:0.12em;color:#888;margin-bottom:0.4rem">'
            '🚀 KINGMAKER — Named-exec endorsement signals</p>',
            unsafe_allow_html=True,
        )
        for e in endorsements[:5]:
            titan_name = e.get("titan_name")  or e.get("Titan_Ticker")         or "—"
            exec_name  = e.get("executive")   or e.get("Endorsement_Source")   or "Executive"
            vendor     = e.get("vendor")      or e.get("Counterparty_Name")    or "—"
            vticker    = e.get("vendor_ticker") or e.get("Counterparty_Ticker") or ""
            conn_type  = (e.get("type") or e.get("Connection_Type") or "Supplier").replace("_", " ")
            conf       = int(e.get("confidence") or e.get("Confidence_Score") or 7)
            quote      = e.get("quote") or e.get("Extracted_Text") or ""
            src_url    = e.get("source_url") or e.get("Endorsement_Source") or ""

            conf_color = "#FF4B4B" if conf >= 9 else "#FFA500" if conf >= 7 else "#00D4AA"
            vtag = f" ({vticker})" if vticker else ""
            vendor_str = f"{vendor}{vtag}"

            with st.expander(f"🏆 {titan_name} → {vendor}{vtag} · {conf}/10", expanded=False):
                vendor_html = (
                    f'<a href="{src_url}" target="_blank" style="color:#00D4AA;font-weight:700;text-decoration:none">{vendor_str}</a>'
                    if src_url and src_url.startswith("http") else f'<b style="color:#00D4AA">{vendor_str}</b>'
                )
                st.markdown(
                    f'<div style="background:#1A1D24;border-left:3px solid {conf_color};padding:0.5rem 0.8rem;border-radius:0 6px 6px 0;margin-bottom:0.4rem">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.25rem">'
                    f'<span style="color:#ccc;font-size:0.78rem"><b>{titan_name}</b> <span style="color:#888">→</span> {vendor_html}</span>'
                    f'<span style="color:{conf_color};font-weight:700;font-size:0.82rem">{conf}/10</span></div>'
                    f'<div style="color:#888;font-size:0.7rem">{exec_name} · {conn_type}</div>'
                    f'<div style="color:#aaa;font-size:0.76rem;font-style:italic;margin-top:0.3rem;border-top:1px solid #2E3140;padding-top:0.3rem">'
                    f'&ldquo;{quote[:160]}{"…" if len(quote) > 160 else ""}&rdquo;</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                raw_conn = e.get("type") or e.get("Connection_Type") or "Supplier"
                bullets = _kingmaker_assessment(raw_conn, vendor, titan_name, conf)
                for b in bullets:
                    st.markdown(b)

    st.divider()

    # ── Section 4: Influential People Tracker ───────────────────────────────
    st.markdown(
        '<p style="font-size:0.72rem;font-weight:700;letter-spacing:0.12em;color:#888;margin-bottom:0.4rem">'
        '👥 INFLUENTIAL VOICES — Market movers & latest views</p>',
        unsafe_allow_html=True,
    )

    tab_people, tab_managers = st.tabs(["Key Individuals", "Asset Managers & Institutions"])

    with tab_people:
        p_cols = st.columns(2)
        for i, person in enumerate(_INFLUENTIAL_PEOPLE):
            with p_cols[i % 2]:
                sc = person["stance_color"]
                asset_tags = "".join(
                    f'<span style="background:#2E3140;color:#aaa;border-radius:3px;padding:0 5px;'
                    f'font-size:0.65rem;margin-right:3px">{a}</span>'
                    for a in person["asset_focus"][:4]
                )
                src_link = (
                    f'<a href="{person["source_url"]}" target="_blank" '
                    f'style="color:#00D4AA;font-size:0.68rem;text-decoration:none">↗ {person["source"]}</a>'
                    if person.get("source_url") else
                    f'<span style="color:#666;font-size:0.68rem">{person["source"]}</span>'
                )
                st.markdown(
                    f'<div style="background:#1A1D24;border:1px solid #2E3140;border-left:3px solid {sc};'
                    f'border-radius:0 8px 8px 0;padding:0.65rem 0.9rem;margin-bottom:0.5rem">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<span style="color:#fff;font-weight:700;font-size:0.85rem">{person["avatar"]} {person["name"]}</span>'
                    f'<span style="background:{sc}22;color:{sc};border-radius:3px;padding:0.1rem 0.4rem;'
                    f'font-size:0.66rem;font-weight:700">{person["stance"]}</span></div>'
                    f'<div style="color:#888;font-size:0.7rem;margin:0.1rem 0">{person["role"]} · {person["date"]}</div>'
                    f'<div style="margin:0.3rem 0">{asset_tags}</div>'
                    f'<div style="color:#bbb;font-size:0.76rem;line-height:1.45;margin:0.35rem 0">'
                    f'{person["latest_view"]}</div>'
                    f'<div style="margin-top:0.3rem">{src_link}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    with tab_managers:
        for mgr in _ASSET_MANAGERS:
            mc = mgr["color"]
            st.markdown(
                f'<div style="background:#1A1D24;border:1px solid #2E3140;border-left:3px solid {mc};'
                f'border-radius:0 8px 8px 0;padding:0.6rem 0.9rem;margin-bottom:0.4rem">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<span style="color:{mc};font-weight:700;font-size:0.82rem">{mgr["name"]}</span>'
                f'<span style="color:#666;font-size:0.72rem">AUM: {mgr["aum"]}</span></div>'
                f'<div style="color:#888;font-size:0.72rem;margin:0.15rem 0">Crypto: <span style="color:#aaa">{mgr["crypto_exposure"]}</span></div>'
                f'<div style="color:#bbb;font-size:0.76rem;margin-top:0.2rem">{mgr["view"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


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
        render_hub()

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
