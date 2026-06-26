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
import modules.technical_analysis.ui   as _mod_ta
import modules.stocks_world.ui         as _mod_stocks

from app.auth import (
    check_auth, is_free_module, logout,
    render_auth_gate, render_auth_page,
    wants_auth_page, request_auth_page,
)

# ═════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG  (must be the first Streamlit call)
# ═════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="InvestWise",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={"About": "InvestWise — Institutional-grade investment intelligence platform."},
)

# ═════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ═════════════════════════════════════════════════════════════════════════════

st.markdown(
    """
    <style>
    /* ── InvestWise Design System — Font Imports ─────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,600&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    body, .stApp,
    .stMarkdown p, .stMarkdown span, .stMarkdown a, .stMarkdown li,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
    .stButton button, .stTextInput input, .stSelectbox select,
    .stTabs [role="tab"], div[data-testid="stExpander"] summary p,
    div[data-testid="metric-container"] label, label, .stCaption p {
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
    }

    /* Preserve icon fonts */
    span[aria-hidden="true"], [class*="material-icons"],
    [data-testid="stExpander"] summary svg,
    [data-testid="stExpander"] summary [data-testid="stIconMaterial"] {
        font-family: 'Material Icons', 'Material Symbols Rounded' !important;
    }

    /* ── Design System Tokens ────────────────────────────────────────────────── */
    :root {
        /* Navy scale */
        --navy-50:  #EEF4FB;
        --navy-100: #D9E8F5;
        --navy-200: #B4D0E9;
        --navy-300: #87B0D2;
        --navy-400: #5A8EBB;
        --navy-500: #3A72A0;
        --navy-600: #2B5A85;
        --navy-700: #1D4369;
        --navy-800: #0F2D4F;
        --navy-900: #071D35;
        /* Emerald */
        --emerald-50:  #EDFAF3;
        --emerald-100: #D0F4E1;
        --emerald-200: #A3E8C4;
        --emerald-400: #37C87C;
        --emerald-500: #1AB868;
        --emerald-600: #149453;
        /* Coral */
        --coral-50:  #FEF2F2;
        --coral-200: #FBCACA;
        --coral-500: #E53535;
        --coral-700: #9B1515;
        /* Amber */
        --amber-50:  #FFFBEB;
        --amber-200: #FDE58A;
        --amber-500: #E8A500;
        --amber-600: #C98900;
        /* Semantic */
        --color-primary:        #1AB868;
        --color-accent:         #1AB868;
        --color-bg:             #F2F6FA;
        --color-surface:        #FFFFFF;
        --color-surface-subtle: #EEF4FB;
        --color-text-primary:   #071D35;
        --color-text-secondary: #2B5A85;
        --color-text-muted:     #5A8EBB;
        --color-positive:       #149453;
        --color-negative:       #E53535;
        --color-warning:        #E8A500;
        --color-border:         #D9E8F5;
        --color-border-strong:  #B4D0E9;
        --shadow-card:          0 1px 3px rgba(7,29,53,0.05), 0 4px 12px rgba(7,29,53,0.04);
        --shadow-card-hover:    0 2px 6px rgba(7,29,53,0.08), 0 6px 18px rgba(7,29,53,0.07);
        --font-display:         'Cormorant Garamond', Georgia, serif;
        --font-body:            'Plus Jakarta Sans', system-ui, sans-serif;
        --font-mono:            'JetBrains Mono', 'Courier New', monospace;
        /* App compatibility aliases */
        --canvas:   #F2F6FA;
        --sidebar:  #071D35;
        --card:     #FFFFFF;
        --border:   #D9E8F5;
        --text-h:   #071D35;
        --text-sub: #5A8EBB;
        --accent:   #1AB868;
        --danger:   #E53535;
        --warn:     #E8A500;
        --info:     #3A72A0;
        --purple:   #7c3aed;
    }

    /* ── Canvas ──────────────────────────────────────────────────────────────── */
    .stApp { background-color: var(--canvas) !important; }
    .block-container { padding-top: 1rem; background: transparent; }

    /* ── Sidebar ─────────────────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] > div:first-child {
        background-color: #071D35 !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] label { color: rgba(255,255,255,0.55) !important; }

    /* ── Sidebar navigation ──────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] .stRadio > div { gap: 0 !important; }
    section[data-testid="stSidebar"] .stRadio label {
        display: flex !important;
        align-items: center !important;
        padding: 0.48rem 0.9rem !important;
        border-radius: 8px !important;
        color: rgba(255,255,255,0.55) !important;
        cursor: pointer !important;
        border-left: 3px solid transparent !important;
        transition: background 0.13s, color 0.13s !important;
        font-size: 0.84rem !important;
        margin: 0.1rem 0 !important;
        font-weight: 400 !important;
        width: 100% !important;
    }
    section[data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(255,255,255,0.06) !important;
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] .stRadio label:has(input[type="radio"]:checked) {
        background: rgba(26,184,104,0.12) !important;
        color: #1AB868 !important;
        border-left-color: #1AB868 !important;
        font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] .stRadio input[type="radio"] {
        position: absolute !important;
        opacity: 0 !important; width: 0 !important;
        height: 0 !important; margin: 0 !important;
        pointer-events: none !important;
    }

    /* ── Metrics ─────────────────────────────────────────────────────────────── */
    div[data-testid="metric-container"] {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 0.85rem 1.25rem;
        box-shadow: var(--shadow-card);
    }
    div[data-testid="metric-container"] label {
        color: var(--text-sub) !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.07em !important;
        text-transform: uppercase !important;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: var(--text-h) !important;
        font-weight: 400 !important;
        font-family: var(--font-display) !important;
        font-size: 1.85rem !important;
        letter-spacing: -0.02em !important;
        line-height: 1.1 !important;
    }

    /* ── Expanders ───────────────────────────────────────────────────────────── */
    div[data-testid="stExpander"] {
        background: var(--card);
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        margin-bottom: 0.5rem;
        box-shadow: var(--shadow-card);
    }
    /* Keep summary header subtly shaded at all states — collapsed, expanded, focused */
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary:hover,
    div[data-testid="stExpander"] summary:focus,
    div[data-testid="stExpander"] summary:focus-visible,
    div[data-testid="stExpander"] summary:active,
    div[data-testid="stExpander"] details[open] > summary {
        background: var(--navy-50) !important;
        background-color: var(--navy-50) !important;
        color: var(--text-h) !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        cursor: pointer;
        align-items: center;
        gap: 0.5rem;
        border-radius: 12px !important;
        outline: none !important;
    }
    div[data-testid="stExpander"] summary svg {
        display: inline-block !important; flex-shrink: 0;
        min-width: 16px; min-height: 16px;
        color: var(--text-sub) !important;
    }
    div[data-testid="stExpander"] summary p {
        margin: 0 !important;
        line-height: 1.4 !important;
        font-size: 0.88rem !important;
        color: var(--text-h) !important;
        font-weight: 600 !important;
    }

    /* ── Tabs ────────────────────────────────────────────────────────────────── */
    .stTabs [data-testid="stTab"] { color: var(--text-sub) !important; }
    .stTabs [aria-selected="true"] {
        color: var(--text-h) !important;
        font-weight: 700;
        border-bottom-color: var(--accent) !important;
    }

    /* ── Buttons ─────────────────────────────────────────────────────────────── */
    .stButton button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        font-family: var(--font-body) !important;
        transition: background 0.13s, transform 0.1s !important;
    }
    .stButton button[kind="primary"] {
        background: var(--color-primary) !important;
        border-color: var(--color-primary) !important;
        color: #ffffff !important;
    }
    .stButton button[kind="primary"] p,
    .stButton button[kind="primary"] span,
    .stButton button[kind="primary"] div {
        color: #ffffff !important;
    }
    .stButton button[kind="primary"]:hover {
        background: var(--emerald-600) !important;
        transform: scale(0.98);
    }
    .stButton button[kind="secondary"] {
        background: var(--navy-50) !important;
        border: 1px solid var(--navy-100) !important;
        color: var(--navy-600) !important;
    }
    .stButton button[kind="secondary"] p,
    .stButton button[kind="secondary"] span,
    .stButton button[kind="secondary"] div {
        color: var(--navy-600) !important;
    }
    .stButton button[kind="secondary"]:hover {
        background: var(--navy-100) !important;
        border-color: var(--navy-200) !important;
        color: var(--navy-800) !important;
    }
    /* Sidebar buttons — always need high-contrast text on dark background */
    section[data-testid="stSidebar"] .stButton button {
        background: rgba(255,255,255,0.08) !important;
        border: 1px solid rgba(255,255,255,0.18) !important;
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] .stButton button p,
    section[data-testid="stSidebar"] .stButton button span,
    section[data-testid="stSidebar"] .stButton button div {
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255,255,255,0.14) !important;
    }
    section[data-testid="stSidebar"] .stButton button[kind="primary"] {
        background: var(--accent) !important;
        border-color: var(--accent) !important;
    }
    section[data-testid="stSidebar"] .stButton button[kind="primary"]:hover {
        background: var(--emerald-600) !important;
    }

    /* ── Link buttons ────────────────────────────────────────────────────────── */
    [data-testid="stLinkButton"] a,
    .stLinkButton a {
        background-color: var(--navy-600) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        border: none !important;
        text-decoration: none !important;
        transition: background 0.13s !important;
        font-family: var(--font-body) !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    [data-testid="stLinkButton"] a:hover,
    .stLinkButton a:hover {
        background-color: var(--navy-700) !important;
        color: #ffffff !important;
        text-decoration: none !important;
    }
    /* Override global p/span color rules inside link buttons */
    [data-testid="stLinkButton"] a p,
    [data-testid="stLinkButton"] a span,
    [data-testid="stLinkButton"] p,
    .stLinkButton a p,
    .stLinkButton p {
        color: #ffffff !important;
        font-size: 0.82rem !important;
        margin: 0 !important;
        line-height: 1 !important;
    }

    /* ── Channel inputs (tables, snaps, auth social): visually hidden but focusable ── */
    /* display:none prevents focus(), breaking synthetic React events on these inputs  */
    [data-testid="stTextInput"]:has(input[placeholder^="iw-tbl-"]),
    [data-testid="stTextInput"]:has(input[placeholder^="iw-auth-social-"]),
    [data-testid="stTextInput"]:has(input[placeholder="iw-snap-ls-v1"]),
    [data-testid="stTextInput"]:has(input[placeholder="iw-snap-click-v1"]),
    [data-testid="stTextInput"]:has(input[placeholder="iw-wi-click-v1"]) {
        position: fixed !important;
        left: -9999px !important;
        top: -9999px !important;
        width: 1px !important;
        height: 1px !important;
        overflow: hidden !important;
        opacity: 0 !important;
    }
    .snap-card, .wi-card { transition: transform 0.12s ease, box-shadow 0.12s ease !important; }
    .snap-card:hover, .wi-card:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 16px rgba(7,29,53,0.11) !important;
    }
    .wi-pct {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.82rem !important;
        font-weight: 700 !important;
    }

    /* ── Selectbox / Multiselect — control (closed state) ──────────────────── */
    .stSelectbox [data-baseweb="select"],
    .stMultiSelect [data-baseweb="select"] {
        background-color: var(--card) !important;
    }
    .stSelectbox [data-baseweb="select"] > div,
    .stMultiSelect [data-baseweb="select"] > div {
        background-color: var(--card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text-h) !important;
        font-size: 0.84rem !important;
        transition: border-color 0.15s ease !important;
    }
    /* Focused / active state — emerald accent, matching text input focus */
    .stSelectbox [data-baseweb="select"]:focus-within > div,
    .stMultiSelect [data-baseweb="select"]:focus-within > div {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px rgba(26,184,104,0.15) !important;
    }
    /* Text / value / placeholder inside the control */
    .stSelectbox [data-baseweb="select"] span,
    .stSelectbox [data-baseweb="select"] [data-baseweb="select-single-value"],
    .stSelectbox [data-baseweb="select"] [data-baseweb="placeholder"],
    .stMultiSelect [data-baseweb="select"] span,
    .stMultiSelect [data-baseweb="select"] [data-baseweb="placeholder"] {
        color: var(--text-h) !important;
    }
    /* Placeholder muted */
    [data-baseweb="placeholder"] { color: var(--text-sub) !important; }
    /* Selected single value */
    [data-baseweb="select-single-value"] { color: var(--text-h) !important; }

    /* ── Dropdown popover (opened) — covers ALL st.selectbox + st.multiselect ── */
    [data-baseweb="popover"],
    [data-baseweb="popover"] > div,
    [data-baseweb="popover"] > div > div {
        background: var(--card) !important;
        background-color: var(--card) !important;
    }
    /* st.multiselect → [data-baseweb="menu"]
       st.selectbox  → [data-baseweb="list"] or div[role="listbox"] */
    [data-baseweb="popover"] [data-baseweb="menu"],
    [data-baseweb="popover"] [data-baseweb="list"],
    [data-baseweb="popover"] ul[role="listbox"],
    [data-baseweb="popover"] div[role="listbox"],
    [data-baseweb="popover"] ul {
        background: var(--card) !important;
        background-color: var(--card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        box-shadow: var(--shadow-card-hover) !important;
    }
    /* Option items (li and div variants) */
    [data-baseweb="popover"] [role="option"],
    [data-baseweb="popover"] li[role="option"],
    [data-baseweb="popover"] div[role="option"],
    [data-baseweb="popover"] [data-baseweb="menu-item"],
    [data-baseweb="popover"] [data-baseweb="option"] {
        background: var(--card) !important;
        background-color: var(--card) !important;
        color: var(--text-h) !important;
        font-size: 0.84rem !important;
    }
    /* Hover / selected state */
    [data-baseweb="popover"] [role="option"]:hover,
    [data-baseweb="popover"] li[role="option"]:hover,
    [data-baseweb="popover"] div[role="option"]:hover,
    [data-baseweb="popover"] [aria-selected="true"],
    [data-baseweb="popover"] [data-baseweb="menu-item"]:hover,
    [data-baseweb="popover"] [data-baseweb="option"]:hover {
        background-color: var(--navy-50) !important;
        color: var(--text-h) !important;
    }
    /* Text nodes inside options */
    [data-baseweb="popover"] [role="option"] span,
    [data-baseweb="popover"] [data-baseweb="option"] span,
    [data-baseweb="popover"] [data-baseweb="menu-item"] span {
        color: var(--text-h) !important;
    }
    /* Selected tags in multiselect */
    [data-baseweb="tag"] {
        background-color: var(--navy-100) !important;
        color: var(--navy-800) !important;
        border-radius: 6px !important;
        font-size: 0.78rem !important;
    }
    [data-baseweb="tag"] span { color: var(--navy-800) !important; }

    /* ── Toggle ──────────────────────────────────────────────────────────────── */
    .stToggle label {
        color: var(--text-h) !important;
        font-size: 0.84rem !important;
        font-weight: 500 !important;
    }
    /* Off state: visible navy track */
    [data-testid="stToggleSwitch"],
    [aria-checked="false"] [data-testid="stToggleSwitch"],
    label[role="switch"] [data-testid="stToggleSwitch"] {
        background-color: var(--navy-500) !important;
        border: none !important;
        outline: none !important;
    }
    /* On state: emerald track */
    [aria-checked="true"] [data-testid="stToggleSwitch"],
    input:checked ~ * [data-testid="stToggleSwitch"] {
        background-color: var(--accent) !important;
    }
    /* White thumb always */
    [data-testid="stToggleSwitch"] span,
    [data-testid="stToggleSwitch"] > span {
        background-color: #ffffff !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.25) !important;
    }

    /* ── Text inputs ─────────────────────────────────────────────────────────── */
    .stTextInput input {
        border-radius: 8px !important;
        border: 1px solid var(--border) !important;
        background: var(--card) !important;
        color: var(--text-h) !important;
        font-family: var(--font-body) !important;
        caret-color: #000000 !important;
    }
    .stTextInput input::selection {
        background-color: var(--navy-200) !important;
        color: #000000 !important;
    }
    /* Black blinking cursor inside every selectbox / multiselect control */
    [data-baseweb="select"] input,
    .stSelectbox input,
    .stMultiSelect input {
        caret-color: #000000 !important;
        color: var(--text-h) !important;
        background: transparent !important;
    }
    [data-baseweb="select"] input::selection {
        background-color: var(--navy-200) !important;
        color: #000000 !important;
    }

    /* ── Card classes ────────────────────────────────────────────────────────── */
    .cr-card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.55rem;
        box-shadow: var(--shadow-card);
    }
    .cr-card-crit { border-left: 4px solid var(--danger); }
    .cr-card-warn { border-left: 4px solid var(--warn); }
    .cr-card-ok   { border-left: 4px solid var(--accent); }

    .banner-card { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:0.85rem 1.1rem; margin-bottom:0.5rem; box-shadow:var(--shadow-card); }
    .banner-card-critical { border-left: 4px solid var(--danger); }
    .banner-card-warn     { border-left: 4px solid var(--warn); }
    .banner-card-ok       { border-left: 4px solid var(--accent); }

    /* ── Status badges ───────────────────────────────────────────────────────── */
    .badge-green    { background:var(--emerald-50); color:var(--emerald-600); border-radius:999px; padding:2px 10px; font-size:0.74rem; font-weight:700; }
    .badge-amber    { background:var(--amber-50); color:var(--amber-600); border-radius:999px; padding:2px 10px; font-size:0.74rem; font-weight:700; }
    .badge-red      { background:var(--coral-50); color:var(--coral-500); border-radius:999px; padding:2px 10px; font-size:0.74rem; font-weight:700; }
    .badge-critical { background:var(--coral-50); color:var(--coral-700); border-radius:999px; padding:2px 10px; font-size:0.74rem; font-weight:700; animation:pulse 1.5s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.55} }

    /* ── Score pills ─────────────────────────────────────────────────────────── */
    .ticker-item { font-size:0.82rem; margin-bottom:0.3rem; }
    .score-pill  { display:inline-block; border-radius:999px; padding:2px 10px; font-size:0.72rem; font-weight:700; margin-right:0.4rem; font-family:var(--font-mono); }
    .pill-9  { background:var(--coral-50); color:var(--coral-700); }
    .pill-8  { background:#FFF0E0; color:#9A4700; }
    .pill-7  { background:var(--amber-50); color:var(--amber-600); }
    .pill-6  { background:var(--emerald-50); color:var(--emerald-600); }
    .pill-low{ background:var(--navy-50); color:var(--navy-400); }

    /* ── Section labels ──────────────────────────────────────────────────────── */
    .zone-header {
        font-size: 0.68rem; font-weight: 700;
        letter-spacing: 0.12em; text-transform: uppercase;
        color: var(--text-sub); margin-bottom: 0.4rem;
    }

    /* ── Dividers ────────────────────────────────────────────────────────────── */
    hr { border-color: var(--border) !important; }

    /* ── Page headings ───────────────────────────────────────────────────────── */
    h1 { color: var(--text-h) !important; font-weight: 700 !important; letter-spacing: -0.02em; }
    h2 { color: var(--text-h) !important; font-weight: 600 !important; }
    h3 { color: var(--text-h) !important; font-weight: 600 !important; }
    p  { color: var(--text-h) !important; }

    /* ── Markdown body text — color + size ──────────────────────────────────── */
    .stMarkdown p,
    [data-testid="stMarkdownContainer"] p {
        color: var(--color-text-secondary) !important;
        font-size: 0.84rem !important;
        line-height: 1.6 !important;
    }
    .stMarkdown li,
    [data-testid="stMarkdownContainer"] li,
    ul li, ol li {
        color: var(--color-text-secondary) !important;
        font-size: 0.84rem !important;
        line-height: 1.6 !important;
    }
    .stMarkdown strong,
    [data-testid="stMarkdownContainer"] strong {
        color: var(--color-text-primary) !important;
        font-size: inherit !important;
    }
    .stMarkdown h3, .stMarkdown h4,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4 {
        color: var(--color-text-primary) !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        margin: 0.75rem 0 0.35rem 0 !important;
    }
    .stMarkdown h5, .stMarkdown h6,
    [data-testid="stMarkdownContainer"] h5,
    [data-testid="stMarkdownContainer"] h6 {
        color: var(--color-text-primary) !important;
        font-size: 0.88rem !important;
        font-weight: 700 !important;
        margin: 0.65rem 0 0.3rem 0 !important;
        font-family: var(--font-body) !important;
    }
    /* Table text */
    .stMarkdown td,
    [data-testid="stMarkdownContainer"] td {
        color: var(--color-text-secondary) !important;
        font-size: 0.82rem !important;
    }
    .stMarkdown th,
    [data-testid="stMarkdownContainer"] th {
        color: var(--color-text-primary) !important;
        font-weight: 700 !important;
        font-size: 0.78rem !important;
    }
    /* Sidebar override — keep sidebar text white */
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] .stMarkdown li,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li {
        color: rgba(255,255,255,0.55) !important;
    }

    /* ── Module headers ──────────────────────────────────────────────────────── */
    .iw-module-header {
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        color: var(--text-h) !important;
        margin-bottom: 0 !important;
        margin-top: 0.25rem !important;
        line-height: 1.3 !important;
        letter-spacing: -0.01em !important;
    }

    /* ── DataFrames ──────────────────────────────────────────────────────────── */
    /* Outer wrapper — card border, rounded corners */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        overflow: hidden !important;
        box-shadow: var(--shadow-card) !important;
    }
    /* The glide-data-grid canvas fills the card background from the Streamlit
       theme (config.toml: secondaryBackgroundColor=#FFFFFF, textColor=#071D35).
       These CSS rules style the non-canvas overlay elements that surround it. */
    [data-testid="stDataFrame"] > div,
    [data-testid="stDataFrame"] > div > div {
        border-radius: 10px !important;
    }
    /* Ensure the resize handle / scrollbar overlay stays on-brand */
    [data-testid="stDataFrame"] [role="scrollbar"] {
        background: var(--navy-100) !important;
    }

    /* ══════════════════════════════════════════════════════════════════════════
       RESPONSIVE  —  Mobile · iPad · Desktop
    ══════════════════════════════════════════════════════════════════════════ */

    /* ── iPad / Large tablet  (769 – 1024 px) ──────────────────────────────── */
    @media screen and (max-width: 1024px) {
        .block-container {
            padding-left: 1.25rem !important;
            padding-right: 1.25rem !important;
            max-width: 100% !important;
        }
        /* Sidebar stays but slightly narrower */
        section[data-testid="stSidebar"] > div:first-child {
            padding-left: 0.85rem !important;
            padding-right: 0.85rem !important;
        }
    }

    /* ── Mobile  (≤ 768 px) ─────────────────────────────────────────────────── */
    @media screen and (max-width: 768px) {
        /* Tighter canvas */
        .block-container {
            padding: 0.5rem 0.6rem 2.5rem !important;
            max-width: 100vw !important;
        }

        /* Sidebar overlays content on mobile */
        section[data-testid="stSidebar"] {
            position: fixed !important;
            z-index: 1100 !important;
            height: 100dvh !important;
            top: 0 !important;
        }

        /* Header text */
        h1 { font-size: 1.55rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1rem !important; }

        /* Metrics */
        div[data-testid="metric-container"] {
            padding: 0.6rem 0.85rem !important;
        }
        div[data-testid="metric-container"] [data-testid="stMetricValue"] {
            font-size: 1.45rem !important;
        }

        /* Tabs: horizontally scrollable strip */
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
            -webkit-overflow-scrolling: touch !important;
            scrollbar-width: none !important;
            padding-bottom: 2px !important;
        }
        .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none !important; }
        .stTabs [data-testid="stTab"] {
            font-size: 0.76rem !important;
            padding: 0.35rem 0.7rem !important;
            white-space: nowrap !important;
            min-width: max-content !important;
        }

        /* DataFrames: horizontal scroll */
        [data-testid="stDataFrame"] > div,
        div.stDataFrame { overflow-x: auto !important; }

        /* Plotly charts */
        .js-plotly-plot, .plotly, .plot-container {
            max-width: 100% !important;
        }

        /* Expanders: tighter */
        div[data-testid="stExpander"] summary {
            padding: 0.5rem 0.75rem !important;
        }

        /* Column gap */
        [data-testid="stHorizontalBlock"] {
            gap: 0.4rem !important;
        }

        /* 3-column snap card grid → 2 per row on mobile */
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            min-width: calc(48% - 0.2rem) !important;
            flex: 0 0 calc(48% - 0.2rem) !important;
        }

        /* Buttons: bigger tap targets */
        .stButton button {
            min-height: 40px !important;
            font-size: 0.8rem !important;
        }

        /* Caption */
        .stCaption p { font-size: 0.7rem !important; }

        /* Selectbox / text input: full width feel */
        .stSelectbox, .stTextInput { width: 100% !important; }

        /* Sidebar nav items: larger tap targets */
        section[data-testid="stSidebar"] .stRadio label {
            min-height: 38px !important;
            padding: 0.55rem 0.9rem !important;
        }
    }

    /* ── Small phones  (≤ 480 px) ──────────────────────────────────────────── */
    @media screen and (max-width: 480px) {
        .block-container {
            padding: 0.35rem 0.4rem 2.5rem !important;
        }
        h1 { font-size: 1.3rem !important; }
        div[data-testid="metric-container"] [data-testid="stMetricValue"] {
            font-size: 1.25rem !important;
        }
        div[data-testid="metric-container"] label {
            font-size: 0.62rem !important;
        }
        /* Single column on very small phones */
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            min-width: 100% !important;
            flex: 0 0 100% !important;
        }
    }
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
        return f"<span style='color:#E53535'>PASSED {abs(delta)}d ago</span>"
    if delta <= 30:
        return f"<span style='color:#E53535;font-weight:700'>{delta}d</span>"
    if delta <= 90:
        return f"<span style='color:#E8A500'>{delta}d</span>"
    return f"<span style='color:#1AB868'>{delta}d</span>"


def _phase_color(phase: str) -> str:
    return {
        "PRE_GATEWAY":       "#149453",
        "GATEWAY_OPEN":      "#E8A500",
        "POST_GATEWAY":      "#C98900",
        "ENFORCEMENT_CLIFF": "#E53535",
    }.get(phase, "#5A8EBB")


def _survival_color(flag: str) -> str:
    return {"GREEN": "#1AB868", "AMBER": "#E8A500",
            "RED": "#E53535", "CRITICAL": "#E53535"}.get(flag, "#5A8EBB")


def _cassandra_assessment(vector: str, title: str, score: int) -> list[str]:
    base = _RISK_ASSESSMENTS.get(vector, _DEFAULT_ASSESSMENT)
    if score >= 9:
        urgency = f"**SEVERITY {score}/10 — Immediate attention warranted.** This signal is in the top decile of systemic threat indicators."
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
        events.insert(0, f"**CONFIDENCE {conf}/10 — Named executive confirmation.** This is the highest-tier endorsement signal; institutional smart money typically builds positions within 30-60 days of such disclosures.")
    return events


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR — NAVIGATION + WHAT-IF CS SIMULATOR
# ═════════════════════════════════════════════════════════════════════════════

_NAV_OPTIONS = [
    "Intelligence Hub",
    "News Feed",
    "Stocks & Shares World",
    "Global Index & ETFs",
    "Global Sector & ETFs",
    "Crypto Network",
    "Metals",
    "CRM Intelligence",
    "Regulatory Sandbox",
    "Technical Analysis",
]


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            "<div style='padding:0.6rem 0 0.5rem 0;display:flex;align-items:center;gap:10px'>"
            "<div style='width:32px;height:32px;border-radius:8px;background:rgba(255,255,255,0.08);"
            "display:flex;align-items:center;justify-content:center;flex-shrink:0'>"
            "<svg width='18' height='18' viewBox='0 0 32 32' fill='none'>"
            "<polyline points='3,24 9,17 14,20 20,12 28,7' stroke='#1AB868' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'/>"
            "<circle cx='28' cy='7' r='2.5' fill='#1AB868'/>"
            "</svg></div>"
            "<div><span style='color:#ffffff;font-size:1.05rem;font-weight:700;letter-spacing:-0.02em'>Invest</span>"
            "<span style='color:#1AB868;font-size:1.05rem;font-weight:300;letter-spacing:-0.02em'>Wise</span></div>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.divider()

        # When showing the dedicated auth page, keep the nav neutral (Intelligence Hub)
        if wants_auth_page():
            st.session_state["sidebar_nav"] = "Intelligence Hub"

        nav = st.radio(
            "Navigate",
            _NAV_OPTIONS,
            index=0,
            key="sidebar_nav",
            label_visibility="collapsed",
        )

        st.divider()
        if check_auth():
            user = st.session_state.get("user_name", "User")
            st.markdown(
                f'<div style="color:rgba(255,255,255,0.7);font-size:0.75rem;margin-bottom:0.5rem">'
                f'Signed in as <strong style="color:#1AB868">{user}</strong></div>',
                unsafe_allow_html=True,
            )
            if st.button("Sign Out", key="sidebar_logout", use_container_width=True):
                logout()
                st.rerun()
        else:
            st.markdown(
                '<div style="color:rgba(255,255,255,0.5);font-size:0.72rem;margin-bottom:0.4rem">'
                '🔒 Sign in to unlock all modules</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "Sign In / Sign Up",
                key="sidebar_signin_btn",
                use_container_width=True,
                type="primary",
            ):
                request_auth_page()

    return nav


# ═════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE HUB — helpers and data
# ═════════════════════════════════════════════════════════════════════════════

_HUB_ROWS = [
    ("crypto",   "Crypto Network",    "#7c3aed", "Crypto Network"),
    ("thematic", "Global Sector & ETFs", "#1AB868", "Global Sector & ETFs"),
    ("equity",   "Global Index & ETFs",  "#3A72A0", "Global Index & ETFs"),
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
    "XAU-USD":   {"name": "Gold Spot",        "row": "precious_metal"},
    "XAG-USD":   {"name": "Silver Spot",      "row": "precious_metal"},
    "XPT-USD":   {"name": "Platinum Spot",    "row": "precious_metal"},
    "XPD-USD":   {"name": "Palladium Spot",   "row": "precious_metal"},
    "SLV":       {"name": "iShs Silver",      "row": "equity"},
    "GC=F":      {"name": "Gold Futures",     "row": "equity"},
    "NVDA":      {"name": "NVIDIA",           "row": "equity"},
    "AAPL":      {"name": "Apple",            "row": "equity"},
    "MSFT":      {"name": "Microsoft",        "row": "equity"},
    "TSLA":      {"name": "Tesla",            "row": "equity"},
    "MSTR":      {"name": "Strategy",         "row": "equity"},
    "COIN":      {"name": "Coinbase",         "row": "equity"},
    "BLK":       {"name": "BlackRock",        "row": "equity"},
    # Additional sovereign crypto
    "LTC-USD":   {"name": "Litecoin",         "row": "crypto"},
    "BCH-USD":   {"name": "Bitcoin Cash",     "row": "crypto"},
    "BNB-USD":   {"name": "BNB",              "row": "crypto"},
    "UNI-USD":   {"name": "Uniswap",          "row": "crypto"},
    "ATOM-USD":  {"name": "Cosmos",           "row": "crypto"},
    "FIL-USD":   {"name": "Filecoin",         "row": "crypto"},
    "NEAR-USD":  {"name": "NEAR Protocol",    "row": "crypto"},
    "ARB-USD":   {"name": "Arbitrum",         "row": "crypto"},
    "OP-USD":    {"name": "Optimism",         "row": "crypto"},
    "INJ-USD":   {"name": "Injective",        "row": "crypto"},
}
_HUB_ROW_COLOR: dict[str, str] = {
    "crypto":          "#7c3aed",
    "thematic":        "#1AB868",
    "equity":          "#3A72A0",
    "precious_metal":  "#C98900",
}
_HUB_ROW_NAV: dict[str, str] = {
    "crypto":   "Crypto Network",
    "thematic": "Global Sector & ETFs",
    "equity":   "Global Index & ETFs",
}
_SNAP_DEFAULTS: list[str] = []

# Extend the ticker catalogue with all precious metals from the metals module
try:
    from modules.precious_metals.data import METALS_REGISTRY as _PM_REGISTRY
    for _pm in _PM_REGISTRY:
        # Skip OTC spot-price labels (XAU/USD, XAG/USD) — not valid yfinance tickers
        if "/" not in _pm.ticker and _pm.ticker not in _HUB_ALL_TICKERS:
            _HUB_ALL_TICKERS[_pm.ticker] = {
                "name": _pm.name,
                "row":  "precious_metal",
            }
except Exception:
    pass

# Extend with all Core Equity instruments (~266 entries)
try:
    from modules.core_equity.data import CORE_EQUITY_REGISTRY as _CE_REGISTRY
    for _ce in _CE_REGISTRY:
        if _ce.ticker not in _HUB_ALL_TICKERS:
            _HUB_ALL_TICKERS[_ce.ticker] = {
                "name": _ce.name,
                "row":  "equity",
            }
except Exception:
    pass

# Extend with all Thematic Sector instruments (~132 entries)
try:
    from modules.thematic_sectors.data import THEMATIC_REGISTRY as _TH_REGISTRY
    for _th in _TH_REGISTRY:
        if _th.ticker not in _HUB_ALL_TICKERS:
            _HUB_ALL_TICKERS[_th.ticker] = {
                "name": _th.name,
                "row":  "thematic",
            }
except Exception:
    pass

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


# Display ticker → yfinance ticker translation for OTC spot prices
_YF_TICKER_MAP: dict[str, str] = {
    "XAU-USD": "XAUUSD=X",
    "XAG-USD": "XAGUSD=X",
    "XPT-USD": "XPTUSD=X",
    "XPD-USD": "XPDUSD=X",
}


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

        # Translate display tickers to yfinance tickers (e.g. XAU-USD → XAUUSD=X)
        _rev_map = {v: k for k, v in _YF_TICKER_MAP.items()}
        yf_tickers = [_YF_TICKER_MAP.get(t, t) for t in tickers]

        batch = yf.download(yf_tickers, period="5d", auto_adjust=True,
                            progress=False, threads=True)
        closes = batch.get("Close", batch)
        if closes is None or closes.empty:
            return {}
        if isinstance(closes, pd.Series):
            closes = closes.to_frame(name=yf_tickers[0])
        closes = closes.dropna(how="all")
        if closes.empty:
            return {}
        last = closes.iloc[-1]
        prev = closes.iloc[-2] if len(closes) >= 2 else closes.iloc[-1]
        data: dict[str, dict] = {}
        for t in tickers:
            yf_t = _YF_TICKER_MAP.get(t, t)
            try:
                p  = _clean(last.get(yf_t))
                p0 = _clean(prev.get(yf_t))
                if p is None:
                    continue
                pct = round((p - p0) / p0 * 100, 2) if (p and p0 and p0 != 0) else None
                data[t] = {"price": p, "chg_pct": pct}
            except Exception:
                pass
        return data
    except Exception:
        return {}


_WORLD_INDEXES: list[dict] = [
    {"ticker": "^GSPC",     "name": "S&P 500",      "region": "US"},
    {"ticker": "^IXIC",     "name": "NASDAQ",        "region": "US"},
    {"ticker": "^DJI",      "name": "Dow Jones",     "region": "US"},
    {"ticker": "^FTSE",     "name": "FTSE 100",      "region": "UK"},
    {"ticker": "^GDAXI",    "name": "DAX",           "region": "EU"},
    {"ticker": "^FCHI",     "name": "CAC 40",        "region": "EU"},
    {"ticker": "^STOXX50E", "name": "Euro Stoxx 50", "region": "EU"},
    {"ticker": "^N225",     "name": "Nikkei 225",    "region": "JP"},
    {"ticker": "^HSI",      "name": "Hang Seng",     "region": "HK"},
    {"ticker": "^BSESN",    "name": "BSE Sensex",    "region": "IN"},
]


@st.cache_data(ttl=300, show_spinner=False)
def _world_index_prices() -> dict[str, dict]:
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

        tickers = [idx["ticker"] for idx in _WORLD_INDEXES]
        batch = yf.download(tickers, period="5d", auto_adjust=True,
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


    # ── Auto-refresh every 5 minutes ─────────────────────────────────────────
    import time as _time
    _now = _time.time()
    _last = st.session_state.get("hub_last_refresh", 0)
    _elapsed = _now - _last
    if _elapsed >= 300:
        st.session_state["hub_last_refresh"] = _now
        st.cache_data.clear()
        _elapsed = 0

    # JS reloads the page when the remaining cache TTL expires so data is always live
    _ms_until_refresh = max(0, int((300 - _elapsed) * 1000))
    import streamlit.components.v1 as components
    components.html(
        f"<script>setTimeout(function(){{window.parent.location.reload();}},{_ms_until_refresh});</script>",
        height=0, scrolling=False,
    )

    # ── Header row ────────────────────────────────────────────────────────────
    rc1, rc3 = st.columns([5, 1])
    with rc1:
        _remaining = int(300 - _elapsed)
        _rem_str = f"{_remaining // 60}m {_remaining % 60}s" if _remaining > 0 else "refreshing…"
        st.markdown(
            f'<span style="font-size:0.72rem;color:#5A8EBB">Live · auto-refreshes in {_rem_str}</span>',
            unsafe_allow_html=True,
        )
    with rc3:
        phase = current_phase(today)
        pc = _phase_color(phase)
        st.markdown(
            f'<div style="text-align:right"><span style="background:{pc}22;border:1px solid {pc};'
            f'color:{pc};border-radius:6px;padding:0.18rem 0.45rem;font-size:0.67rem;font-weight:700">'
            f'{phase.replace("_"," ")}</span></div>',
            unsafe_allow_html=True,
        )

    # ── Market Snapshot hero ──────────────────────────────────────────────────
    if "snap_open" not in st.session_state:
        st.session_state["snap_open"] = None
    if "wi_open" not in st.session_state:
        st.session_state["wi_open"] = None
    import streamlit.components.v1 as components

    # ── localStorage persistence channel (hidden via CSS) ─────────────────────
    _LS_PH = "iw-snap-ls-v1"
    _ls_raw = st.text_input(
        "ls", key="snap_ls_ch", placeholder=_LS_PH, label_visibility="collapsed"
    )
    # On fresh browser load, JS delivers stored favorites (or "[]") via this channel.
    # We wait for JS to deliver before marking init done — never overwrite stored favs.
    if not st.session_state.get("snap_ls_init"):
        if _ls_raw:
            # JS has delivered: adopt stored favorites if valid, then mark init done
            try:
                import json as _j2
                _stored = _j2.loads(_ls_raw)
                if isinstance(_stored, list) and _stored:
                    _valid = [t for t in _stored if t in _HUB_ALL_TICKERS]
                    if _valid:
                        st.session_state["snap_favs"] = _valid[:6]
                    else:
                        if "snap_favs" not in st.session_state:
                            st.session_state["snap_favs"] = list(_SNAP_DEFAULTS)
                else:
                    # "[]" or empty list → nothing stored, use defaults
                    if "snap_favs" not in st.session_state:
                        st.session_state["snap_favs"] = list(_SNAP_DEFAULTS)
            except Exception:
                if "snap_favs" not in st.session_state:
                    st.session_state["snap_favs"] = list(_SNAP_DEFAULTS)
            st.session_state["snap_ls_init"] = True
        else:
            # JS hasn't delivered yet (first render before iframe JS runs) — use defaults
            # but keep snap_ls_init unset so next render can adopt stored favs
            if "snap_favs" not in st.session_state:
                st.session_state["snap_favs"] = list(_SNAP_DEFAULTS)
    elif "snap_favs" not in st.session_state:
        st.session_state["snap_favs"] = list(_SNAP_DEFAULTS)

    snap_favs = st.session_state["snap_favs"]

    # ── Card click channel (hidden via CSS) ───────────────────────────────────
    if st.session_state.pop("_snap_click_clear", False):
        st.session_state.pop("snap_click_ch", None)

    _click_raw = st.text_input(
        "c", key="snap_click_ch", placeholder="iw-snap-click-v1",
        label_visibility="collapsed",
    )
    if _click_raw and _click_raw in _HUB_ALL_TICKERS:
        _prev_open = st.session_state.get("snap_open")
        st.session_state["snap_open"] = None if _prev_open == _click_raw else _click_raw
        st.session_state["_snap_click_clear"] = True
        st.rerun()

    snap_open   = st.session_state["snap_open"]
    snap_prices = _hub_prices(tuple(snap_favs))

    # ── Section label ─────────────────────────────────────────────────────────
    st.markdown(
        '<p style="font-size:0.68rem;font-weight:800;letter-spacing:0.14em;'
        'color:#5A8EBB;margin-bottom:0.3rem;text-transform:uppercase">Market Snapshot</p>',
        unsafe_allow_html=True,
    )

    # ── Always-visible instrument chips (click to remove) ─────────────────────
    if snap_favs:
        rm_cols = st.columns(min(6, max(1, len(snap_favs))))
        for ci, tick in enumerate(snap_favs):
            with rm_cols[ci]:
                if st.button(f"✕ {tick}", key=f"snap_rm_{tick}", use_container_width=True):
                    nf = [t for t in snap_favs if t != tick]
                    st.session_state["snap_favs"] = nf
                    if st.session_state["snap_open"] == tick:
                        st.session_state["snap_open"] = None
                    st.rerun()

    # ── Always-visible search bar (hidden when 6 instruments already added) ───
    if len(snap_favs) < 6:
        import json as _json
        _snap_ac_items = _json.dumps([
            {
                "l": f"{k} — {v['name']}",
                "v": k,
                "b": v.get("row", "equity").replace("_", " ").title(),
                "s": f"{k.lower()} {v['name'].lower()} {v.get('row','').replace('_',' ').lower()}",
            }
            for k, v in _HUB_ALL_TICKERS.items()
            if k not in snap_favs
        ])
        _SNAP_AC_PH = "Ticker or name — e.g. BTC, NVDA, Gold…"
        # Use flag pattern to clear the input on next render (avoids StreamlitAPIException)
        if st.session_state.pop("_snap_srch_clear", False):
            st.session_state.pop("snap_add_srch", None)
        srch = st.text_input(
            "Search", key="snap_add_srch",
            placeholder=_SNAP_AC_PH,
            label_visibility="collapsed",
        )
        if srch and srch in _HUB_ALL_TICKERS and srch not in snap_favs:
            st.session_state["snap_favs"] = list(snap_favs) + [srch]
            st.session_state["_snap_srch_clear"] = True
            st.rerun()
        from modules.shared import inject_autocomplete as _snap_inject_ac
        _snap_inject_ac(_snap_ac_items, _SNAP_AC_PH)

    st.markdown('<div style="height:0.15rem"></div>', unsafe_allow_html=True)

    # ── localStorage sync: persist favorites across page refreshes ────────────
    import json as _json_ls
    _favs_json = _json_ls.dumps(snap_favs)
    _ls_ph_esc = "iw-snap-ls-v1"
    _ls_init_done = "true" if st.session_state.get("snap_ls_init") else "false"
    components.html(f"""<script>
(function(){{
  var LS_KEY='iw_snap_favs';
  var CURRENT={_favs_json};
  var INIT_DONE={_ls_init_done};
  var doc=window.parent.document;
  var ls=window.parent.localStorage;

  if(INIT_DONE){{
    // Initialization complete — write current favorites to localStorage on every render
    ls.setItem(LS_KEY,JSON.stringify(CURRENT));
  }}else{{
    // Not yet initialized — deliver stored favorites (or "[]") so Python can adopt them.
    // Gate on INIT_DONE (a Python flag) rather than sessionStorage, because sessionStorage
    // survives page refreshes and would prevent re-delivery after a refresh.
    var stored=ls.getItem(LS_KEY);
    var toDeliver=stored||'[]';
    var PH='{_ls_ph_esc}';
    function findCh(){{
      var els=doc.querySelectorAll('[data-testid="stTextInput"] input');
      for(var i=0;i<els.length;i++){{ if(els[i].placeholder===PH) return els[i]; }}
      return null;
    }}
    function deliverStored(){{
      var ch=findCh();
      if(!ch) return;
      ch.removeAttribute('readonly');
      ch.focus();
      var setter=Object.getOwnPropertyDescriptor(
        window.parent.HTMLInputElement.prototype,'value').set;
      setter.call(ch,toDeliver);
      ch.dispatchEvent(new Event('input',{{bubbles:true,composed:true}}));
      ch.dispatchEvent(new Event('change',{{bubbles:true,composed:true}}));
      setTimeout(function(){{
        ch.dispatchEvent(new KeyboardEvent('keydown',{{
          key:'Enter',code:'Enter',keyCode:13,which:13,
          bubbles:true,cancelable:true,composed:true
        }}));
        ch.blur();
      }},80);
    }}
    var ch=findCh();
    if(ch){{ deliverStored(); }}
    else{{
      var obs=new MutationObserver(function(){{
        if(findCh()){{ obs.disconnect(); deliverStored(); }}
      }});
      obs.observe(doc.body,{{childList:true,subtree:true}});
    }}
  }}
}})();
</script>""", height=0, scrolling=False)

    # ── 3 × N card grid with inline accordion news ───────────────────────────
    SNAP_COLS = 3
    rows = [snap_favs[i:i+SNAP_COLS] for i in range(0, len(snap_favs), SNAP_COLS)]

    for row_tickers in rows:
        card_cols = st.columns(SNAP_COLS)
        for col, ticker in zip(card_cols, row_tickers):
            with col:
                meta    = _HUB_ALL_TICKERS.get(ticker, {})
                name    = meta.get("name", ticker)
                row_key = meta.get("row", "equity")
                color   = _HUB_ROW_COLOR.get(row_key, "#3A72A0")
                card_id = "snap_card_" + ticker.replace("-","_").replace(".","_").replace("=","_")

                p_data    = snap_prices.get(ticker, {})
                price     = p_data.get("price")
                chg       = p_data.get("chg_pct")
                is_open   = snap_open == ticker

                if price is not None:
                    price_str = (
                        f"${price:,.0f}" if price >= 1000 else
                        f"${price:.2f}"  if price >= 1    else
                        f"${price:.4f}"
                    )
                else:
                    price_str = "—"

                if chg is not None:
                    cc  = "#149453" if chg >= 0 else "#E53535"
                    arr = "▲" if chg >= 0 else "▼"
                    chg_html = (
                        f'<span style="color:{cc};font-weight:700;'
                        f'font-family:\'JetBrains Mono\',monospace;font-size:0.82rem">'
                        f'{arr}{abs(chg):.2f}%</span>'
                    )
                else:
                    chg_html = '<span style="color:#5A8EBB;font-size:0.82rem">—</span>'

                bg         = f"{color}0D" if is_open else "#ffffff"
                border_top = f"3px solid {color}" if is_open else f"2px solid {color}"

                st.markdown(
                    f'<div id="{card_id}" class="snap-card" data-ticker="{ticker}" style="'
                    f'background:{bg};border:1px solid #D9E8F5;border-top:{border_top};'
                    f'border-radius:10px;padding:0.9rem 0.5rem;text-align:center;cursor:pointer">'
                    f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.63rem;'
                    f'font-weight:800;color:{color};letter-spacing:0.06em;text-transform:uppercase">'
                    f'{ticker}</div>'
                    f'<div style="font-size:0.59rem;color:#5A8EBB;margin:0.07rem 0;'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{name}</div>'
                    f'<div style="font-size:1.75rem;font-weight:800;color:#071D35;'
                    f'line-height:1.1;margin:0.18rem 0">{price_str}</div>'
                    f'<div>{chg_html}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # Inline news accordion — only for the card that is open in this row
        open_in_row = snap_open if (snap_open and snap_open in row_tickers) else None
        if open_in_row:
            meta    = _HUB_ALL_TICKERS.get(open_in_row, {})
            name    = meta.get("name", open_in_row)
            row_key = meta.get("row", "equity")
            color   = _HUB_ROW_COLOR.get(row_key, "#3A72A0")

            ph, px = st.columns([11, 1])
            with ph:
                st.markdown(
                    f'<div style="margin:0.3rem 0 0.2rem;font-size:0.68rem;font-weight:800;'
                    f'text-transform:uppercase;letter-spacing:0.1em;color:{color}">'
                    f'Latest News — {open_in_row} · {name}</div>',
                    unsafe_allow_html=True,
                )
            with px:
                if st.button("×", key=f"snap_close_{open_in_row}"):
                    st.session_state["snap_open"] = None
                    st.rerun()

            with st.spinner(f"Loading news for {open_in_row}…"):
                news_items = _fetch_hub_news(open_in_row)

            if news_items:
                nc1, nc2 = st.columns(2)
                for idx, item in enumerate(news_items[:6]):
                    title    = item.get("title", "—")
                    link     = item.get("link", "")
                    pub      = item.get("publisher", "")
                    time_str = _format_ts(item.get("ts", 0))
                    title_html = (
                        f'<a href="{link}" target="_blank" style="color:#071D35;'
                        f'text-decoration:none;font-weight:600;font-size:0.78rem;line-height:1.45">'
                        f'{title}</a>'
                        if link else
                        f'<span style="color:#071D35;font-size:0.78rem;font-weight:600">{title}</span>'
                    )
                    with (nc1 if idx % 2 == 0 else nc2):
                        st.markdown(
                            f'<div style="background:#ffffff;border:1px solid #D9E8F5;'
                            f'border-left:3px solid {color};border-radius:0 10px 10px 0;'
                            f'padding:0.45rem 0.7rem;margin-bottom:0.28rem">'
                            f'{title_html}'
                            f'<div style="color:#5A8EBB;font-size:0.64rem;margin-top:0.12rem">'
                            f'{pub} · {time_str}</div></div>',
                            unsafe_allow_html=True,
                        )
            else:
                st.info(f"No recent news for {open_in_row}.")

    # JS: wire snap-card and wi-card clicks → their respective channel inputs
    components.html("""<script>
(function(){
  var doc = window.parent.document;
  var IHP = window.parent.HTMLInputElement.prototype;

  function findCh(ph){
    var els = doc.querySelectorAll('[data-testid="stTextInput"] input');
    for(var i=0;i<els.length;i++){ if(els[i].placeholder===ph) return els[i]; }
    return null;
  }

  function fireCh(ph, value){
    var inp = findCh(ph);
    if(!inp) return;
    inp.removeAttribute('readonly');
    inp.focus();
    var setter = Object.getOwnPropertyDescriptor(IHP, 'value').set;
    setter.call(inp, value);
    inp.dispatchEvent(new Event('input',  {bubbles:true, composed:true}));
    inp.dispatchEvent(new Event('change', {bubbles:true, composed:true}));
    setTimeout(function(){
      inp.dispatchEvent(new KeyboardEvent('keydown',{
        key:'Enter', code:'Enter', keyCode:13, which:13,
        bubbles:true, cancelable:true, composed:true
      }));
      inp.blur();
    }, 60);
  }

  function wireCards(){
    doc.querySelectorAll('.snap-card[data-ticker]').forEach(function(card){
      if(card._snapWired) return;
      card._snapWired = true;
      card.addEventListener('click', function(){
        var t = card.getAttribute('data-ticker');
        if(t) fireCh('iw-snap-click-v1', t);
      });
    });
    doc.querySelectorAll('.wi-card[data-wi-ticker]').forEach(function(card){
      if(card._wiWired) return;
      card._wiWired = true;
      card.addEventListener('click', function(){
        var t = card.getAttribute('data-wi-ticker');
        if(t) fireCh('iw-wi-click-v1', t);
      });
    });
  }

  function wireAll(){ wireCards(); }

  wireAll();
  new MutationObserver(function(){ wireAll(); }).observe(doc.body,{childList:true,subtree:true});
})();
</script>""", height=0, scrolling=False)

    # ── World Indexes ─────────────────────────────────────────────────────────
    st.markdown(
        '<p style="font-size:0.68rem;font-weight:800;letter-spacing:0.14em;'
        'text-transform:uppercase;color:#5A8EBB;margin:0.6rem 0 0.3rem">'
        'World Indexes</p>',
        unsafe_allow_html=True,
    )

    # Click channel for world index cards
    if st.session_state.pop("_wi_click_clear", False):
        st.session_state.pop("wi_click_ch", None)
    _wi_raw = st.text_input("wi", key="wi_click_ch", placeholder="iw-wi-click-v1",
                             label_visibility="collapsed")
    if _wi_raw:
        _wi_valid = {idx["ticker"] for idx in _WORLD_INDEXES}
        if _wi_raw in _wi_valid:
            _prev_wi = st.session_state.get("wi_open")
            st.session_state["wi_open"] = None if _prev_wi == _wi_raw else _wi_raw
            st.session_state["_wi_click_clear"] = True
            st.rerun()

    wi_open   = st.session_state["wi_open"]
    wi_prices = _world_index_prices()

    def _render_wi_card(wi_col, idx_meta):
        t       = idx_meta["ticker"]
        p_data  = wi_prices.get(t, {})
        price   = p_data.get("price")
        chg     = p_data.get("chg_pct")
        is_open = wi_open == t

        if price is not None:
            price_str = (
                f"{price:,.0f}" if price >= 1000 else
                f"{price:.2f}"  if price >= 1    else
                f"{price:.4f}"
            )
        else:
            price_str = "—"

        if chg is not None:
            chg_color = "#149453" if chg >= 0 else "#E53535"
            chg_arrow = "▲" if chg >= 0 else "▼"
            chg_html  = (
                f'<div class="wi-pct" style="color:{chg_color};margin-top:0.08rem">'
                f'{chg_arrow}{abs(chg):.2f}%</div>'
            )
            border_top = f"{'3px' if is_open else '2px'} solid {chg_color}"
        else:
            chg_html   = '<div class="wi-pct" style="color:#5A8EBB;margin-top:0.08rem">—</div>'
            border_top = "2px solid #D9E8F5"

        bg = "#EDFAF3" if is_open else "#ffffff"
        outline = "outline:2px solid #1AB868;" if is_open else ""

        with wi_col:
            st.markdown(
                f'<div class="wi-card" data-wi-ticker="{t}" style="background:{bg};'
                f'border:1px solid #D9E8F5;border-top:{border_top};border-radius:10px;'
                f'padding:0.85rem 0.6rem;text-align:center;cursor:pointer;{outline}'
                f'box-shadow:0 1px 4px rgba(7,29,53,0.07)">'
                f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.65rem;'
                f'font-weight:800;color:#071D35;letter-spacing:0.04em;text-transform:uppercase;'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
                f'{idx_meta["name"]}</div>'
                f'<div style="font-size:0.62rem;color:#5A8EBB;margin:0.1rem 0">'
                f'{idx_meta["region"]}</div>'
                f'<div style="font-size:1.75rem;font-weight:800;color:#071D35;'
                f'line-height:1.1;margin:0.2rem 0 0.05rem">{price_str}</div>'
                f'{chg_html}'
                f'</div>',
                unsafe_allow_html=True,
            )

    # 2-row × 5-card grid
    wi_row1 = st.columns(5)
    wi_row2 = st.columns(5)
    for col, idx_meta in zip(wi_row1, _WORLD_INDEXES[:5]):
        _render_wi_card(col, idx_meta)
    for col, idx_meta in zip(wi_row2, _WORLD_INDEXES[5:]):
        _render_wi_card(col, idx_meta)

    # Inline news accordion for the open world index
    if wi_open:
        wi_meta  = next((x for x in _WORLD_INDEXES if x["ticker"] == wi_open), {})
        wi_name  = wi_meta.get("name", wi_open)
        wh1, wh2 = st.columns([11, 1])
        with wh1:
            st.markdown(
                f'<div style="margin:0.3rem 0 0.2rem;font-size:0.68rem;font-weight:800;'
                f'text-transform:uppercase;letter-spacing:0.1em;color:#3A72A0">'
                f'Latest News — {wi_name}</div>',
                unsafe_allow_html=True,
            )
        with wh2:
            if st.button("×", key=f"wi_close_{wi_open}"):
                st.session_state["wi_open"] = None
                st.rerun()
        with st.spinner(f"Loading news for {wi_name}…"):
            wi_news = _fetch_hub_news(wi_open)
        if wi_news:
            wn1, wn2 = st.columns(2)
            for idx, item in enumerate(wi_news[:6]):
                title    = item.get("title", "—")
                link     = item.get("link", "")
                pub      = item.get("publisher", "")
                time_str = _format_ts(item.get("ts", 0))
                title_html = (
                    f'<a href="{link}" target="_blank" style="color:#071D35;'
                    f'text-decoration:none;font-weight:600;font-size:0.78rem;line-height:1.45">'
                    f'{title}</a>'
                    if link else
                    f'<span style="color:#071D35;font-size:0.78rem;font-weight:600">{title}</span>'
                )
                with (wn1 if idx % 2 == 0 else wn2):
                    st.markdown(
                        f'<div style="background:#ffffff;border:1px solid #D9E8F5;'
                        f'border-left:3px solid #3A72A0;border-radius:0 10px 10px 0;'
                        f'padding:0.45rem 0.7rem;margin-bottom:0.28rem">'
                        f'{title_html}'
                        f'<div style="color:#5A8EBB;font-size:0.64rem;margin-top:0.12rem">'
                        f'{pub} · {time_str}</div></div>',
                        unsafe_allow_html=True,
                    )
        else:
            st.info(f"No recent news for {wi_name}.")

    st.divider()

    # ── Cassandra + Kingmaker ─────────────────────────────────────────────────
    alerts       = load_cassandra_alerts()
    endorsements = load_kingmaker_endorsements()
    left_col, right_col = st.columns([1, 1], gap="medium")

    with left_col:
        st.markdown(
            '<p style="font-size:0.68rem;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#5A8EBB;margin-bottom:0.4rem">'
            'Cassandra Alerts — Live macro threats</p>',
            unsafe_allow_html=True,
        )
        for a in alerts[:6]:
            score   = int(a.get("risk_score") or a.get("Systemic_Risk_Score") or 0)
            title   = a.get("title") or a.get("Title") or "—"
            vector  = (a.get("vector") or a.get("Risk_Vector") or "").replace("_", " ").upper()
            src_url = a.get("source_url") or a.get("Source_URL") or ""
            raw_src = a.get("source") or ""
            bar_col = "#E53535" if score >= 8 else "#E8A500" if score >= 6 else "#149453"
            title_s = title[:60] + ("…" if len(title) > 60 else "")
            src_html = (
                f'<a href="{src_url}" target="_blank" style="color:#149453;font-size:0.67rem;text-decoration:none;font-weight:600">↗ {raw_src}</a>'
                if src_url else f'<span style="color:#5A8EBB;font-size:0.67rem">{raw_src}</span>'
            )
            with st.expander(f"{score}/10  ·  {title_s}", expanded=False):
                st.markdown(
                    f'<div style="background:#EEF4FB;border-left:3px solid {bar_col};padding:0.55rem 0.85rem;'
                    f'border-radius:0 10px 10px 0;margin-bottom:0.35rem">'
                    f'<span style="color:{bar_col};font-size:0.7rem;font-weight:700">{vector}</span>'
                    f' <span style="color:{bar_col};font-weight:700;font-size:0.78rem">{score}/10</span><br>'
                    f'<span style="color:#2B5A85;font-size:0.77rem;line-height:1.5">{title}</span><br>'
                    f'<div style="margin-top:0.25rem">{src_html}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                v_key = (a.get("vector") or a.get("Risk_Vector") or "").lower()
                for b in _cassandra_assessment(v_key, title, score):
                    st.markdown(b)

    with right_col:
        st.markdown(
            '<p style="font-size:0.68rem;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#5A8EBB;margin-bottom:0.4rem">'
            'Kingmaker Signals — Named-exec endorsements</p>',
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
            conf_col   = "#E53535" if conf >= 9 else "#E8A500" if conf >= 7 else "#149453"
            vtag       = f" ({vticker})" if vticker else ""
            vlink      = (
                f'<a href="{src_url}" target="_blank" style="color:#149453;text-decoration:none;font-weight:700">{vendor}{vtag}</a>'
                if src_url and src_url.startswith("http") else
                f'<b style="color:#3A72A0">{vendor}{vtag}</b>'
            )
            with st.expander(f"{titan_name}  ›  {vendor}{vtag}  ·  {conf}/10", expanded=False):
                st.markdown(
                    f'<div style="background:#EEF4FB;border-left:3px solid {conf_col};padding:0.55rem 0.85rem;'
                    f'border-radius:0 10px 10px 0;margin-bottom:0.35rem">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<span style="color:#2B5A85;font-size:0.78rem"><b style="color:#071D35">{titan_name}</b> <span style="color:#5A8EBB">›</span> {vlink}</span>'
                    f'<span style="color:{conf_col};font-weight:700">{conf}/10</span></div>'
                    f'<span style="color:#5A8EBB;font-size:0.7rem">{exec_name} · {conn_type}</span>'
                    f'<div style="color:#2B5A85;font-size:0.74rem;font-style:italic;border-top:1px solid #D9E8F5;'
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
        '<p style="font-size:0.68rem;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;color:#5A8EBB;margin-bottom:0.4rem">'
        'Influential Voices — Latest views &amp; live market news</p>',
        unsafe_allow_html=True,
    )

    tab_people, tab_managers = st.tabs(["Key Individuals", "Asset Managers"])

    with tab_people:
        for person in _INFLUENTIAL_PEOPLE:
            sc           = person["stance_color"]
            news_ticker  = person.get("news_ticker", "")
            asset_tags   = "".join(
                f'<span style="background:#EEF4FB;color:#5A8EBB;border-radius:6px;padding:1px 6px;'
                f'font-size:0.62rem;margin-right:3px;font-weight:600">{a}</span>'
                for a in person["asset_focus"][:4]
            )
            src_link = (
                f'<a href="{person["source_url"]}" target="_blank" style="color:#149453;font-size:0.67rem;text-decoration:none;font-weight:600">↗ {person["source"]}</a>'
                if person.get("source_url") else
                f'<span style="color:#5A8EBB;font-size:0.67rem">{person["source"]}</span>'
            )
            header = f'{person["name"]}  ·  {person["role"]}  ·  {person["date"]}'
            with st.expander(header, expanded=False):
                pv1, pv2 = st.columns([5, 4])
                with pv1:
                    st.markdown(
                        f'<div style="background:#EEF4FB;border-left:4px solid {sc};border-radius:0 12px 12px 0;padding:0.7rem 0.9rem">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.3rem">'
                        f'<span style="color:#071D35;font-weight:800;font-size:0.85rem">{person["name"]}</span>'
                        f'<span style="background:{sc}18;color:{sc};border-radius:6px;padding:0.15rem 0.5rem;font-size:0.64rem;font-weight:700">{person["stance"]}</span></div>'
                        f'<div style="color:#5A8EBB;font-size:0.71rem;margin-bottom:0.28rem">{person["role"]}</div>'
                        f'<div style="margin-bottom:0.35rem">{asset_tags}</div>'
                        f'<div style="color:#2B5A85;font-size:0.77rem;line-height:1.55">{person["latest_view"]}</div>'
                        f'<div style="margin-top:0.35rem">{src_link}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with pv2:
                    if news_ticker:
                        st.markdown(
                            f'<div style="color:#5A8EBB;font-size:0.65rem;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.25rem">Live News · {news_ticker}</div>',
                            unsafe_allow_html=True,
                        )
                        for ni in _fetch_hub_news(news_ticker)[:4]:
                            nt    = ni.get("title", "—")
                            nl    = ni.get("link", "")
                            npub  = ni.get("publisher", "")
                            ntime = _format_ts(ni.get("ts", 0))
                            nt_html = (
                                f'<a href="{nl}" target="_blank" style="color:#071D35;text-decoration:none;font-size:0.72rem;font-weight:600;line-height:1.4">{nt[:90]}{"…" if len(nt)>90 else ""}</a>'
                                if nl else
                                f'<span style="color:#2B5A85;font-size:0.72rem">{nt[:90]}</span>'
                            )
                            st.markdown(
                                f'<div style="border-bottom:1px solid #D9E8F5;padding:0.3rem 0">'
                                f'{nt_html}'
                                f'<div style="color:#5A8EBB;font-size:0.63rem;margin-top:0.1rem">{npub} · {ntime}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        st.markdown('<span style="color:#5A8EBB;font-size:0.72rem">No live ticker linked.</span>', unsafe_allow_html=True)

    with tab_managers:
        for mgr in _ASSET_MANAGERS:
            mc          = mgr["color"]
            news_ticker = mgr.get("news_ticker")
            with st.expander(f'{mgr["name"]}  ·  AUM: {mgr["aum"]}', expanded=False):
                mv1, mv2 = st.columns([5, 4])
                with mv1:
                    st.markdown(
                        f'<div style="background:#EEF4FB;border-left:4px solid {mc};border-radius:0 12px 12px 0;padding:0.65rem 0.9rem">'
                        f'<div style="color:{mc};font-weight:800;font-size:0.82rem;margin-bottom:0.22rem">{mgr["name"]}</div>'
                        f'<div style="color:#5A8EBB;font-size:0.7rem">AUM: <span style="color:#2B5A85;font-weight:600">{mgr["aum"]}</span></div>'
                        f'<div style="color:#5A8EBB;font-size:0.7rem;margin:0.12rem 0">Crypto: <span style="color:#2B5A85">{mgr["crypto_exposure"]}</span></div>'
                        f'<div style="color:#2B5A85;font-size:0.75rem;line-height:1.5;margin-top:0.2rem">{mgr["view"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with mv2:
                    if news_ticker:
                        st.markdown(
                            f'<div style="color:#5A8EBB;font-size:0.65rem;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.25rem">Live News · {news_ticker}</div>',
                            unsafe_allow_html=True,
                        )
                        for ni in _fetch_hub_news(news_ticker)[:3]:
                            nt    = ni.get("title", "—")
                            nl    = ni.get("link", "")
                            ntime = _format_ts(ni.get("ts", 0))
                            nt_html = (
                                f'<a href="{nl}" target="_blank" style="color:#071D35;text-decoration:none;font-size:0.72rem;font-weight:600">{nt[:85]}{"…" if len(nt)>85 else ""}</a>'
                                if nl else
                                f'<span style="color:#2B5A85;font-size:0.72rem">{nt[:85]}</span>'
                            )
                            st.markdown(
                                f'<div style="border-bottom:1px solid #D9E8F5;padding:0.3rem 0">'
                                f'{nt_html}'
                                f'<div style="color:#5A8EBB;font-size:0.63rem;margin-top:0.1rem">{ntime}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        st.markdown('<span style="color:#5A8EBB;font-size:0.72rem">No linked news ticker.</span>', unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    nav = render_sidebar()

    # ── Mobile swipe-to-open / swipe-to-close sidebar ─────────────────────────
    import streamlit.components.v1 as _comp
    _comp.html("""<script>
(function(){
  var win = window.parent;
  var doc = win.document;

  // Only activate on actual touch devices
  if (!win.matchMedia('(hover: none) and (pointer: coarse)').matches) return;

  // Idempotent across Streamlit reruns
  if (doc._iwSwipeInstalled) return;
  doc._iwSwipeInstalled = true;

  var sx = 0, sy = 0;
  var THRESHOLD = 65;  // min horizontal distance (px) to count as swipe
  var EDGE = 55;       // right-swipe must start within this many px of left edge

  function sidebar(){ return doc.querySelector('section[data-testid="stSidebar"]'); }

  function isOpen(){
    var sb = sidebar();
    if (!sb) return false;
    // Streamlit collapses the sidebar by translating it off-screen or hiding it;
    // when open its left edge is ≥ 0
    return sb.getBoundingClientRect().left >= -10;
  }

  function openSidebar(){
    // The collapsed-state toggle button (hamburger / chevron)
    var btn = doc.querySelector('[data-testid="collapsedControl"] button') ||
              doc.querySelector('[data-testid="collapsedControl"]');
    if (btn) btn.click();
  }

  function closeSidebar(){
    // The close / collapse button visible inside an open sidebar
    var btn = doc.querySelector('[data-testid="stSidebarCollapseButton"] button') ||
              doc.querySelector('section[data-testid="stSidebar"] button[aria-label]') ||
              doc.querySelector('section[data-testid="stSidebar"] button');
    if (btn) btn.click();
  }

  doc.addEventListener('touchstart', function(e){
    sx = e.touches[0].clientX;
    sy = e.touches[0].clientY;
  }, {passive: true});

  doc.addEventListener('touchend', function(e){
    var dx = e.changedTouches[0].clientX - sx;
    var dy = e.changedTouches[0].clientY - sy;
    // Ignore swipes that are more vertical than horizontal
    if (Math.abs(dy) > Math.abs(dx) * 0.9) return;

    if (dx > THRESHOLD && sx < EDGE && !isOpen()) {
      openSidebar();
    } else if (dx < -THRESHOLD && isOpen()) {
      closeSidebar();
    }
  }, {passive: true});
})();
</script>""", height=0, scrolling=False)

    # ── Global search-input click-to-focus ────────────────────────────────────
    _comp.html("""<script>
(function(){
  var doc = window.parent.document;
  if (doc._iwFocusInstalled) return;
  doc._iwFocusInstalled = true;

  // Placeholders belonging to hidden channel inputs — never focus-wire these
  var HIDDEN = new Set([
    'iw-snap-ls-v1', 'iw-snap-click-v1', 'iw-wi-click-v1',
    'iw-cr-click-v1', 'rsb-badge-click-v1'
  ]);

  function wireInput(inp) {
    var ph = (inp.getAttribute('placeholder') || '').trim();
    if (HIDDEN.has(ph)) return;
    var wrapper = inp.closest('[data-testid="stTextInput"]') || inp.parentElement;
    if (!wrapper || wrapper._iwFocusWired) return;
    wrapper._iwFocusWired = true;
    wrapper.style.cursor = 'text';
    wrapper.addEventListener('click', function(e) {
      if (e.target !== inp) inp.focus();
    });
  }

  function wireSelect(ctrl) {
    // The control div for [data-baseweb="select"] — clicking it should
    // focus the internal search input and show a black blinking cursor
    if (ctrl._iwSelectWired) return;
    var inp = ctrl.querySelector('input');
    if (!inp) return;
    ctrl._iwSelectWired = true;
    ctrl.style.cursor = 'text';
    ctrl.addEventListener('click', function(e) {
      if (e.target === inp) return;
      inp.focus();
    });
  }

  function wireAll() {
    // Text inputs
    doc.querySelectorAll('[data-testid="stTextInput"] input').forEach(wireInput);
    // Selectbox / Multiselect controls
    doc.querySelectorAll(
      '.stSelectbox [data-baseweb="select"], .stMultiSelect [data-baseweb="select"]'
    ).forEach(wireSelect);
  }

  wireAll();

  // Re-wire whenever Streamlit swaps in new DOM nodes (module navigation, reruns)
  new MutationObserver(function(mutations) {
    var hasNew = mutations.some(function(m) { return m.addedNodes.length > 0; });
    if (hasNew) wireAll();
  }).observe(doc.body, { childList: true, subtree: true });
})();
</script>""", height=0, scrolling=False)

    # ── Canvas full-row click → checkbox-column selection ─────────────────────
    _comp.html("""<script>
(function(){
  var doc = window.parent.document;
  if (doc._iwRowSelectInstalled) return;
  doc._iwRowSelectInstalled = true;

  var HEADER_H = 36;
  var CB_WIDTH = 52;
  var CB_X     = 26;

  function wireFrame(frame) {
    if (frame._iwRowWired) return;
    frame._iwRowWired = true;

    // Listen on the FRAME container in capture phase so we fire BEFORE
    // glide-data-grid's own canvas listeners (capture goes outer→inner).
    frame.addEventListener('mousedown', function(e) {
      if (frame._iwFiring) return;

      var canvas = frame.querySelector('canvas');
      if (!canvas) return;

      var rect = canvas.getBoundingClientRect();
      var x = e.clientX - rect.left;
      var y = e.clientY - rect.top;

      // Only intercept data-area clicks — skip header and checkbox column
      if (y < HEADER_H || x < CB_WIDTH) return;

      // stopImmediatePropagation prevents ALL other listeners (including
      // glide's own capture/bubble handlers) from seeing this event.
      e.stopImmediatePropagation();
      e.preventDefault();

      frame._iwFiring = true;
      var tx = rect.left + CB_X;
      var ty = e.clientY;

      ['mousedown', 'mouseup', 'click'].forEach(function(type) {
        canvas.dispatchEvent(new MouseEvent(type, {
          bubbles: true, cancelable: true,
          clientX: tx, clientY: ty,
          button: 0,
          buttons: type === 'mouseup' ? 0 : 1,
          view: window.parent
        }));
      });
      frame._iwFiring = false;
    }, true); // CAPTURE phase on the frame ancestor
  }

  function wireAll() {
    doc.querySelectorAll('[data-testid="stDataFrame"]').forEach(wireFrame);
  }

  wireAll();

  new MutationObserver(function(mutations) {
    if (mutations.some(function(m) { return m.addedNodes.length > 0; })) wireAll();
  }).observe(doc.body, { childList: true, subtree: true });
})();
</script>""", height=0, scrolling=False)

    # ── Page header ───────────────────────────────────────────────────────────
    _pc = _phase_color(current_phase())
    st.markdown(
        f"<div style='display:flex;align-items:center;justify-content:space-between;"
        f"flex-wrap:wrap;gap:0.4rem;margin-bottom:0.25rem'>"
        f"<h1 style='margin:0;color:#071D35;font-weight:700;font-size:2.1rem;"
        f"letter-spacing:-0.02em;flex-shrink:0'>Invest"
        f"<span style='color:#1AB868;font-weight:300'>Wise</span></h1>"
        f"<div style='text-align:right;flex-shrink:0'>"
        f"<span style='color:#5A8EBB;font-size:0.73rem;text-transform:uppercase;"
        f"letter-spacing:0.08em'>Phase</span><br>"
        f"<span style='background:{_pc}15;border:1px solid {_pc};border-radius:6px;"
        f"padding:0.15rem 0.55rem;color:{_pc};font-size:0.74rem;font-weight:700'>"
        f"{current_phase().replace('_', ' ')}</span><br>"
        f"<span style='color:#5A8EBB;font-size:0.72rem'>{date.today()}</span>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    # ── Dedicated auth page — intercepts all other routing when flag is set ──
    if wants_auth_page():
        render_auth_page()
        return

    # ── Auth gate — clean lock screen for gated modules ───────────────────────
    if not is_free_module(nav) and not check_auth():
        render_auth_gate(nav)
        return

    # ── Module routing ────────────────────────────────────────────────────────
    if nav == "Global Index & ETFs":
        _mod_core_equity.render()

    elif nav == "Global Sector & ETFs":
        _mod_thematic.render()

    elif nav == "Crypto Network":
        _mod_crypto.render()

    elif nav == "Metals":
        _mod_metals.render()

    elif nav == "CRM Intelligence":
        _mod_kingmaker.render()

    elif nav == "Regulatory Sandbox":
        _mod_regulatory.render()

    elif nav == "News Feed":
        _mod_news.render()

    elif nav == "Technical Analysis":
        _mod_ta.render()

    elif nav == "Stocks & Shares World":
        _mod_stocks.render()

    else:
        render_hub()

    # ── Footer ────────────────────────────────────────────────────────────────
    st.divider()
    st.markdown(
        "<p style='text-align:center;color:#5A8EBB;font-size:0.75rem'>"
        "InvestWise · 10 modules · Data latency ≤ 5 min · "
        "Not investment advice · Regulatory data sourced from FCA CP23/28 &amp; PS24/12"
        "</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
