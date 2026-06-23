"""
Regulatory Sandbox — UK FSMA 2026/2027 FCA Compliance Intelligence Hub.
Comprehensive view of FCA authorisation requirements for all instrument types:
LSE ETPs, spot crypto, stablecoins, and asset managers.
"""
from __future__ import annotations

import sys
import os
from datetime import date
from typing import Any, Optional

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from analytics.compliance.fca_checkpoints import (
    GATEWAY_OPEN_DATE, GATEWAY_CLOSE_DATE, ENFORCEMENT_DATE,
    current_phase, phase_narrative, upcoming_milestones,
    days_to_gateway_open, days_to_gateway_close, days_to_enforcement,
)
from analytics.compliance.uk_crypto_matrix import UKCryptoComplianceMatrix, _INSTRUMENT_REGISTRY

_PHASE_COLOR = {
    "PRE_GATEWAY":       "#149453",
    "GATEWAY_OPEN":      "#E8A500",
    "POST_GATEWAY":      "#C98900",
    "ENFORCEMENT_CLIFF": "#E53535",
}


def _hex_to_rgba(hex_color: str, alpha: float = 0.27) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"
_SURVIVAL_COLOR = {
    "GREEN":    "#1AB868",
    "AMBER":    "#E8A500",
    "RED":      "#E53535",
    "CRITICAL": "#E53535",
}
_CAT_COLOR = {
    "LSE_ETP":      "#3A72A0",
    "Spot_Crypto":  "#7c3aed",
    "Stablecoin":   "#1AB868",
    "Asset_Manager":"#E8A500",
}
_CAT_LABEL = {
    "LSE_ETP":      "LSE ETP",
    "Spot_Crypto":  "Spot Crypto",
    "Stablecoin":   "Stablecoin",
    "Asset_Manager":"Asset Manager",
}
_AUTH_LABEL = {
    "Fully_Authorised":   "Fully Authorised",
    "Registered_Only":    "Registered Only",
    "Application_Pending":"Application Pending",
    "Not_Started":        "Not Started",
    "Withdrawn":          "Withdrawn",
    "Grandfathered":      "Grandfathered",
}
_AUTH_COLOR = {
    "Fully_Authorised":   "#1AB868",
    "Registered_Only":    "#E8A500",
    "Application_Pending":"#3A72A0",
    "Not_Started":        "#E53535",
    "Withdrawn":          "#E53535",
    "Grandfathered":      "#9B59B6",
}


@st.cache_data(ttl=600, show_spinner=False)
def _compliance_matrix(ref_str: str) -> Any:
    ref = date.fromisoformat(ref_str)
    m = UKCryptoComplianceMatrix()
    return m.generate(reference_date=ref)


@st.cache_data(ttl=600, show_spinner=False)
def _timeline_projection(instrument_id: str) -> list:
    m = UKCryptoComplianceMatrix()
    return m.timeline_projection(instrument_id)


def _flag_badge(flag: str, size: str = "0.75rem") -> str:
    color = _SURVIVAL_COLOR.get(flag, "#888")
    return (
        f'<span style="background:{color}22;border:1px solid {color};color:{color};'
        f'border-radius:4px;padding:0.1rem 0.45rem;font-size:{size};font-weight:700">'
        f'{flag}</span>'
    )


def _auth_badge(status: str) -> str:
    label = _AUTH_LABEL.get(status, status.replace("_", " "))
    color = _AUTH_COLOR.get(status, "#888")
    return (
        f'<span style="background:{color}22;border:1px solid {color};color:{color};'
        f'border-radius:4px;padding:0.1rem 0.45rem;font-size:0.72rem;font-weight:600">'
        f'{label}</span>'
    )


def _countdown_chip(target: date, ref: date) -> str:
    delta = (target - ref).days
    if delta < 0:
        return f"<span style='color:#E53535;font-size:0.75rem'>PASSED {abs(delta)}d ago</span>"
    if delta <= 30:
        return f"<span style='color:#E53535;font-weight:700;font-size:0.75rem'>{delta}d</span>"
    if delta <= 90:
        return f"<span style='color:#E8A500;font-size:0.75rem'>{delta}d</span>"
    return f"<span style='color:#1AB868;font-size:0.75rem'>{delta}d</span>"


def _section_header(text: str, color: str = "#5A8EBB") -> None:
    st.markdown(
        f'<p style="font-size:0.68rem;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;'
        f'color:{color};margin:1rem 0 0.45rem 0">{text}</p>',
        unsafe_allow_html=True,
    )


def _info_card(title: str, body: str, color: str = "#D9E8F5") -> None:
    st.markdown(
        f'<div style="background:#ffffff;border:1px solid {color};border-radius:8px;'
        f'padding:0.8rem 1rem;margin-bottom:0.5rem">'
        f'<div style="color:#2B5A85;font-weight:600;font-size:0.82rem;margin-bottom:0.3rem">{title}</div>'
        f'<div style="color:#5A8EBB;font-size:0.78rem;line-height:1.5">{body}</div></div>',
        unsafe_allow_html=True,
    )


def _render_overview(today: date, phase: str, phase_color: str) -> None:
    # Phase banner
    st.markdown(
        f"""<div style="background:linear-gradient(90deg,{phase_color}22,transparent);
            border:1px solid {phase_color};border-radius:8px;padding:0.75rem 1.2rem;margin-bottom:1rem">
            <span style="color:{phase_color};font-weight:700;font-size:0.85rem;letter-spacing:0.1em">
            CURRENT REGULATORY PHASE: {phase.replace('_',' ')}
            </span><br>
            <span style="color:#5A8EBB;font-size:0.82rem">{phase_narrative(phase)}</span>
        </div>""",
        unsafe_allow_html=True,
    )

    # Countdown clocks
    t1, t2, t3 = st.columns(3)
    with t1:
        d = days_to_gateway_open(today)
        color = "#149453" if (d is not None and d > 0) else "#5A8EBB"
        label = f"{d}d" if (d is not None and d > 0) else "OPEN"
        st.markdown(
            f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-top:3px solid {color};'
            f'border-radius:8px;padding:0.75rem;text-align:center;box-shadow:0 1px 3px rgba(7,29,53,0.05)">'
            f'<div style="font-size:0.68rem;font-weight:700;color:#5A8EBB;letter-spacing:0.1em;text-transform:uppercase">Gateway Opens</div>'
            f'<div style="font-family:\'Cormorant Garamond\',Georgia,serif;font-size:2rem;font-weight:400;color:{color};letter-spacing:-0.02em;line-height:1.1">{label}</div>'
            f'<div style="font-size:0.72rem;color:#2B5A85;font-weight:600;margin-top:0.1rem">{GATEWAY_OPEN_DATE}</div>'
            f'<div style="font-size:0.67rem;color:#5A8EBB;margin-top:0.1rem">FCA registration window opens</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with t2:
        d = days_to_gateway_close(today)
        color = ("#E8A500" if (d is not None and d > 30)
                 else "#E53535" if (d is not None and d > 0)
                 else "#5A8EBB")
        label = f"{d}d" if (d is not None and d > 0) else "CLOSED"
        st.markdown(
            f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-top:3px solid {color};'
            f'border-radius:8px;padding:0.75rem;text-align:center;box-shadow:0 1px 3px rgba(7,29,53,0.05)">'
            f'<div style="font-size:0.68rem;font-weight:700;color:#5A8EBB;letter-spacing:0.1em;text-transform:uppercase">Gateway Closes</div>'
            f'<div style="font-family:\'Cormorant Garamond\',Georgia,serif;font-size:2rem;font-weight:400;color:{color};letter-spacing:-0.02em;line-height:1.1">{label}</div>'
            f'<div style="font-size:0.72rem;color:#2B5A85;font-weight:600;margin-top:0.1rem">{GATEWAY_CLOSE_DATE}</div>'
            f'<div style="font-size:0.67rem;color:#5A8EBB;margin-top:0.1rem">Final registration deadline — hard stop</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with t3:
        d = days_to_enforcement(today)
        color = ("#E53535" if (d is not None and d <= 180)
                 else "#E8A500" if d is not None
                 else "#E53535")
        label = f"{d}d" if (d is not None and d > 0) else "ACTIVE"
        st.markdown(
            f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-top:3px solid {color};'
            f'border-radius:8px;padding:0.75rem;text-align:center;box-shadow:0 1px 3px rgba(7,29,53,0.05)">'
            f'<div style="font-size:0.68rem;font-weight:700;color:#5A8EBB;letter-spacing:0.1em;text-transform:uppercase">Enforcement Cliff</div>'
            f'<div style="font-family:\'Cormorant Garamond\',Georgia,serif;font-size:2rem;font-weight:400;color:{color};letter-spacing:-0.02em;line-height:1.1">{label}</div>'
            f'<div style="font-size:0.72rem;color:#2B5A85;font-weight:600;margin-top:0.1rem">{ENFORCEMENT_DATE}</div>'
            f'<div style="font-size:0.67rem;color:#5A8EBB;margin-top:0.1rem">s.23 FSMA criminal liability begins</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # Live compliance snapshot
    matrix = _compliance_matrix(today.isoformat())
    reports = matrix.reports if hasattr(matrix, "reports") else matrix.get("reports", [])

    _section_header("LIVE COMPLIANCE SNAPSHOT — 19 Tracked Instruments")

    col_g, col_a, col_r, col_c = st.columns(4)
    for col, flag, count in [
        (col_g, "GREEN",    matrix.green_count    if hasattr(matrix, "green_count")    else 0),
        (col_a, "AMBER",    matrix.amber_count    if hasattr(matrix, "amber_count")    else 0),
        (col_r, "RED",      matrix.red_count      if hasattr(matrix, "red_count")      else 0),
        (col_c, "CRITICAL", matrix.critical_count if hasattr(matrix, "critical_count") else 0),
    ]:
        color = _SURVIVAL_COLOR[flag]
        with col:
            st.markdown(
                f'<div style="background:{color}11;border:1px solid {color};border-radius:8px;'
                f'padding:0.7rem;text-align:center"><div style="color:{color};font-size:2rem;font-weight:700">'
                f'{count}</div><div style="color:#5A8EBB;font-size:0.72rem;letter-spacing:0.08em">{flag}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Category breakdown
    if reports:
        cats: dict[str, dict] = {}
        for r in reports:
            cat = getattr(r, "category", None) or "Unknown"
            cat = str(cat.value) if hasattr(cat, "value") else str(cat)
            flag = str(r.survival_flag.value) if hasattr(r.survival_flag, "value") else str(r.survival_flag)
            if cat not in cats:
                cats[cat] = {"GREEN": 0, "AMBER": 0, "RED": 0, "CRITICAL": 0, "total": 0}
            cats[cat][flag] = cats[cat].get(flag, 0) + 1
            cats[cat]["total"] += 1

        _section_header("COMPLIANCE BY INSTRUMENT CATEGORY")
        cat_cols = st.columns(len(cats))
        for col, (cat, counts) in zip(cat_cols, cats.items()):
            label = _CAT_LABEL.get(cat, cat.replace("_", " "))
            cat_color = _CAT_COLOR.get(cat, "#888")
            worst = ("CRITICAL" if counts["CRITICAL"] > 0 else
                     "RED"      if counts["RED"]      > 0 else
                     "AMBER"    if counts["AMBER"]    > 0 else "GREEN")
            worst_color = _SURVIVAL_COLOR[worst]
            with col:
                st.markdown(
                    f'<div style="background:#ffffff;border:1px solid {cat_color};border-top:3px solid {cat_color};'
                    f'border-radius:8px;padding:0.65rem;text-align:center">'
                    f'<div style="color:{cat_color};font-size:0.72rem;font-weight:700;letter-spacing:0.06em">{label}</div>'
                    f'<div style="color:#071D35;font-size:1.6rem;font-weight:800;margin:0.2rem 0">{counts["total"]}</div>'
                    f'<div style="color:#5A8EBB;font-size:0.68rem">instruments</div>'
                    f'<div style="margin-top:0.4rem">{_flag_badge(worst, "0.68rem")}</div>'
                    f'<div style="color:#5A8EBB;font-size:0.65rem;margin-top:0.3rem">'
                    f'<span style="color:#1AB868">G:{counts["GREEN"]}</span> '
                    f'<span style="color:#E8A500">A:{counts["AMBER"]}</span> '
                    f'<span style="color:#E53535">R:{counts["RED"]}</span> '
                    f'<span style="color:#E53535">C:{counts["CRITICAL"]}</span></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.divider()

    # Key risks + upcoming milestones side by side
    col_risks, col_ms = st.columns([1, 1])

    with col_risks:
        _section_header("KEY IMMEDIATE RISKS")
        critical_reports = [r for r in reports if str(getattr(r, "survival_flag", "")).replace("SurvivalFlag.", "") in ("CRITICAL", "RED")]
        for r in critical_reports[:6]:
            flag = str(r.survival_flag.value) if hasattr(r.survival_flag, "value") else str(r.survival_flag)
            color = _SURVIVAL_COLOR.get(flag, "#888")
            cat = getattr(r, "category", None)
            cat_str = str(cat.value) if hasattr(cat, "value") else str(cat or "")
            cat_color = _CAT_COLOR.get(cat_str, "#666")
            inst_id = getattr(r, "instrument_id", "—")
            inst_name = getattr(r, "instrument_name", "—")
            next_action = getattr(r, "next_action", "—")
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid {color};border-left:3px solid {color};'
                f'border-radius:6px;padding:0.5rem 0.8rem;margin-bottom:0.3rem">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<span style="color:{color};font-weight:700;font-size:0.8rem">{inst_id}</span>'
                f'<span style="color:{cat_color};font-size:0.65rem">{_CAT_LABEL.get(cat_str,cat_str)}</span></div>'
                f'<div style="color:#071D35;font-size:0.78rem;font-weight:600">{inst_name}</div>'
                f'<div style="color:#5A8EBB;font-size:0.73rem;margin-top:0.2rem">{next_action}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with col_ms:
        _section_header("UPCOMING MILESTONES")
        milestones = upcoming_milestones(today)
        for m in milestones[:5]:
            label = m.get("label", "—")
            dt    = m.get("date") or m.get("deadline") or "—"
            detail = m.get("detail") or m.get("description", "")
            delta = (dt - today).days if isinstance(dt, date) else None
            urgency = "#E53535" if "ENFORCEMENT" in label.upper() else "#E8A500" if "GATEWAY" in label.upper() else "#1AB868"
            delta_str = f"{delta}d" if delta is not None else ""
            detail_html = f'<div style="color:#2B5A85;font-size:0.72rem;margin-top:0.15rem;line-height:1.4">{detail}</div>' if detail else ""
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-left:3px solid {urgency};'
                f'border-radius:6px;padding:0.5rem 0.9rem;margin-bottom:0.3rem">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<span style="color:{urgency};font-weight:700;font-size:0.78rem">{label}</span>'
                f'<span style="color:{urgency};font-size:0.72rem;font-weight:700">{delta_str}</span></div>'
                f'<div style="color:#5A8EBB;font-size:0.72rem">{dt}</div>'
                f'{detail_html}'
                f'</div>',
                unsafe_allow_html=True,
            )


def _render_fca_requirements() -> None:
    st.markdown("### FCA Authorisation Requirements by Instrument Type")
    st.markdown(
        '<div style="color:#5A8EBB;font-size:0.82rem;margin-bottom:1rem">'
        'Under FSMA 2023, the FCA\'s cryptoasset perimeter expanded to cover all '
        'crypto activities in the UK. Requirements differ significantly by instrument type '
        'and legal structure.</div>',
        unsafe_allow_html=True,
    )

    # LSE ETPs
    with st.expander("LSE-Listed Crypto ETPs (Exchange-Traded Products)", expanded=True):
        col1, col2 = st.columns([1, 1])
        with col1:
            _section_header("REGULATORY PATHWAY", _CAT_COLOR["LSE_ETP"])
            st.markdown("""
**Primary Regime:** FCA Part 4A FSMA Authorisation (Cryptoasset Activities)

**Key Requirements:**
- **Part 4A Authorisation** or Variation of Permission (VoP) to add cryptoasset dealing/arranging
- **Approved Prospectus** under UK Prospectus Regulation (FCA-reviewed)
- **UCITS-equivalent** investor protection standards (diversification, liquidity, NAV reporting)
- **FCA-approved Custodian** for physical backing (cold storage, proof-of-reserves)
- **Anti-Money Laundering (AML)** registration under Money Laundering Regulations 2017
- **Market Abuse Regulation (MAR)** compliance — UK-MAR post-Brexit
- **MiFID-equivalent** best execution, order management, and trade reporting
""")
        with col2:
            _section_header("CURRENT STATUS & RISKS", _CAT_COLOR["LSE_ETP"])
            st.markdown("""
**Current Instruments:** IB1T (BlackRock), BITB, ETHE (CoinShares), WBTC, WETH, SOLW, XRPL (WisdomTree)

**Status as of June 2026:** All hold legacy FCA registration; full Part 4A authorisation not yet obtained

**Key Risks:**
- Retail access at risk if Part 4A not secured before enforcement cliff
- SOLW and XRPL — no FCA authorisation process initiated (Not Started status)
- VoP applications must be submitted during gateway window (Sep 2026 – Feb 2027)
- Failure to secure Part 4A = mandatory ETP wind-down (criminal liability under s.23 FSMA)

**Positive Note:**
- Physically-backed ETPs listed on LSE benefit from existing UCITS-equivalent oversight
- BlackRock (FCA ref: 119030), CoinShares (928067), WisdomTree (707137), Invesco (119223) all registered
""")

        st.divider()
        _section_header("FCA AUTHORISATION PATHWAY STEPS", _CAT_COLOR["LSE_ETP"])
        steps = [
            ("1. Scope Assessment", "Map all cryptoasset activities — dealing, arranging, custody, advising — to FSMA Schedule 2/RAO regulated activities.", "#149453"),
            ("2. Pre-Application Engagement", "Request early FCA interaction (EFI) to discuss application before gateway opens.", "#149453"),
            ("3. Part 4A Application / VoP", "Submit full application via Connect portal with business plan, compliance manual, SMF appointments, and financial projections.", "#E8A500"),
            ("4. FCA Review (target 6–12m)", "FCA may issue Section 165 notices requesting further information. All queries must be answered within deadlines.", "#E8A500"),
            ("5. Authorisation Grant", "Firm receives Part 4A permission. Must comply with ongoing reporting: GABRIEL, transaction reports, senior manager accountability (SMCR).", "#1AB868"),
        ]
        for title, desc, color in steps:
            st.markdown(
                f'<div style="background:#ffffff;border-left:3px solid {color};border-radius:0 6px 6px 0;'
                f'padding:0.5rem 0.8rem;margin-bottom:0.35rem">'
                f'<span style="color:{color};font-weight:700;font-size:0.8rem">{title}</span><br>'
                f'<span style="color:#5A8EBB;font-size:0.76rem">{desc}</span></div>',
                unsafe_allow_html=True,
            )

    # Spot Crypto
    with st.expander("Spot Cryptoassets (BTC, ETH, SOL, XRP)", expanded=False):
        col1, col2 = st.columns([1, 1])
        with col1:
            _section_header("REGULATORY PATHWAY", _CAT_COLOR["Spot_Crypto"])
            st.markdown("""
**Primary Regime:** FCA Cryptoasset Exchange Provider / Custodian Wallet Provider Registration

**For Exchanges & Brokers Dealing Spot:**
- **FCA MLR Registration** (Money Laundering Regulations 2017, Reg 12A)
- **Part 4A FSMA Authorisation** for any regulated activities (e.g., operating MTF, dealing as principal)
- **Travel Rule Compliance** (FATF Recommendation 16 — UK implementation via The Money Laundering and Terrorist Financing Regulations 2023)
- **Client Asset Protection (CASS)** rules for custodied crypto
- **Risk Warnings** and appropriateness tests for retail clients (FCA PS22/10)

**For Underlying Networks (BTC, ETH, SOL, XRP):**
- The network itself is not regulated — regulation applies to intermediaries/service providers
- Exchanges, brokers, custodians offering access must be FCA-authorised
""")
        with col2:
            _section_header("COMPLIANCE CONSIDERATIONS", _CAT_COLOR["Spot_Crypto"])
            st.markdown("""
**Current Registry Status:** BTC, ETH, SOL, XRP all listed as Not_Started (no direct FCA entity)

**Why They Appear in Matrix:**
- These represent the spot market exposure; FCA compliance risk flows to issuers/platforms
- UK retail platforms offering spot BTC/ETH require full MLR registration + FCA authorisation

**Key Regulatory Distinctions:**
- **BTC & ETH**: Classified as exchange tokens; no issuer, decentralised — platforms regulated
- **SOL & XRP**: Potential "transferable securities" classification under FCA review
- **XRP (Ripple)**: Ongoing SEC litigation in US has UK regulatory contagion risk
- **Privacy coins** (XMR, ZEC): Likely de facto prohibition under JMLSG guidance

**Post-Enforcement Risk:**
- UK platforms not FCA-authorised after Oct 2027 face criminal prosecution
- Overseas exchanges serving UK clients without authorisation also liable
""")

        st.divider()
        _section_header("RETAIL ACCESS RESTRICTIONS", _CAT_COLOR["Spot_Crypto"])
        st.markdown("""
Under **FCA PS22/10** (effective October 2023), firms marketing cryptoassets to UK retail must:
- Classify clients and apply **appropriateness tests** (ensure client understands risks)
- Display **mandatory risk warnings**: *"Don't invest unless you're prepared to lose all the money you invest. This is a high-risk investment and you are unlikely to be protected if something goes wrong."*
- Implement **24-hour cooling-off period** for first-time crypto buyers
- Prohibit **refer-a-friend bonuses** and similar inducements
- Ensure all financial promotions are **approved by an FCA-authorised person**
""")

    # Stablecoins
    with st.expander("Stablecoins (USDT, USDC, GBPT)", expanded=False):
        col1, col2 = st.columns([1, 1])
        with col1:
            _section_header("REGULATORY PATHWAY", _CAT_COLOR["Stablecoin"])
            st.markdown("""
**Primary Regime:** FCA Stablecoin Issuer Regime (FSMA 2023, Part 5A) + EMI Licensing

**Fiat-Backed Stablecoins (USDT, USDC, GBPT):**
- **E-Money Institution (EMI) Authorisation** for GBP-pegged coins
- **Part 5A FSMA Authorisation** (expected implementation: Jan 2026)
- **1:1 Reserve Backing** with high-quality liquid assets (gilts/cash)
- **Daily Proof-of-Reserves** attestation requirement
- **Redemption Rights**: Holders must be able to redeem at par within 1 business day
- **Systemic Stablecoin Rules** apply if coin exceeds £10bn daily transaction volume

**Foreign-Issued Stablecoins (USDT/USDC — USD-pegged):**
- Must obtain UK recognition or partner with FCA-authorised arranger
- Cannot be actively marketed to UK retail without FCA approval
""")
        with col2:
            _section_header("ISSUER STATUS & RISKS", _CAT_COLOR["Stablecoin"])
            st.markdown("""
**USDT (Tether Operations Ltd, BVI):**
- No FCA registration; no UK EMI authorisation
- Continued UK retail availability at risk post-enforcement
- Reserves historically non-transparent; regulatory scrutiny ongoing

**USDC (Circle Internet Financial, US):**
- US-regulated (NYDFS), exploring EU/UK licences
- Better reserve transparency (monthly attestations by Deloitte)
- UK authorisation path likely via PRA/FCA EMI application

**GBPT (Tether GBP — Tether Operations Ltd, BVI):**
- No EMI authorisation; directly in scope of FCA stablecoin regime
- GBP-pegged coin operated by non-UK entity without UK licence
- Highest risk profile: likely prohibited from UK circulation post-cliff

**Timeline:**
- Stablecoin regime expected: Jan 2026
- Hard enforcement: Oct 2027
""")

        st.divider()
        _section_header("EMI AUTHORISATION REQUIREMENTS", _CAT_COLOR["Stablecoin"])
        reqs = [
            ("Reserve Management", "Stablecoins must hold 100% reserves in high-quality liquid assets (gilts, BoE deposits, or insured cash). No co-mingling with operational funds."),
            ("Safeguarding", "Client funds must be safeguarded under FCA CASS rules — held separately from firm assets, with daily reconciliation."),
            ("Capital Requirements", "Minimum initial capital of €350,000 for full EMI authorisation (PSD2-equivalent UK rules)."),
            ("Governance", "Fit & Proper assessment of directors, senior managers under SMCR. At least one UK-based executive with FCA-approved function."),
            ("Reporting", "Quarterly prudential returns to FCA; transaction volume reporting; suspicious activity reports (SARs) to NCA."),
        ]
        for title, body in reqs:
            _info_card(title, body, _CAT_COLOR["Stablecoin"])

    # Asset Managers
    with st.expander("Asset Managers (BlackRock, CoinShares, WisdomTree, Invesco, 21Shares)", expanded=False):
        col1, col2 = st.columns([1, 1])
        with col1:
            _section_header("REGULATORY PATHWAY", _CAT_COLOR["Asset_Manager"])
            st.markdown("""
**Primary Regime:** FSMA Part 4A Authorisation — Investment Management + Cryptoasset Permissions

**Entity-Level Requirements:**
- **Part 4A Permission** for cryptoasset dealing, arranging, and/or managing investments
- **Senior Managers & Certification Regime (SMCR)**: All Senior Management Functions (SMFs) FCA-approved
- **ICARA Process** (Internal Capital Adequacy & Risk Assessment) under MIFIDPRU
- **Operational Resilience** standards (FCA PS21/3): Critical business services mapped; tolerances set
- **Consumer Duty** (FCA PS22/9): Retail-facing products must deliver good outcomes
- **Annual Compliance Certificate** and regulatory reporting to FCA (GABRIEL system)

**For Crypto-Specific Activities (VoP):**
- Variation of Permission to add cryptoasset dealing/arranging as new regulated activity
- Submit via Connect portal; FCA targets 6-month determination
""")
        with col2:
            _section_header("CURRENT STATUS", _CAT_COLOR["Asset_Manager"])
            managers = [
                ("BlackRock",   "119030", "Registered Only", "IB1T (£3.2bn AUM). Largest UK crypto ETP. Part 4A VoP required."),
                ("CoinShares",  "928067", "Registered Only", "BITB, ETHE. Jersey domicile adds complexity. VoP in preparation."),
                ("WisdomTree",  "707137", "Registered Only", "WBTC, WETH, SOLW, XRPL. SOLW and XRPL auth not yet started."),
                ("Invesco",     "119223", "Registered Only", "Physical crypto range. VoP submission required before Feb 2027."),
                ("21Shares AG", "N/A",    "Not Started",     "Swiss domicile; no UK FCA registration. Highest entity-level risk."),
            ]
            for name, fca_ref, status, note in managers:
                auth_color = _AUTH_COLOR.get(status.replace(" ", "_"), "#888")
                status_key = status.replace(" ", "_")
                st.markdown(
                    f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-radius:6px;'
                    f'padding:0.5rem 0.8rem;margin-bottom:0.3rem">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<span style="color:#2B5A85;font-weight:700;font-size:0.8rem">{name}</span>'
                    f'<span style="color:#5A8EBB;font-size:0.68rem">FCA: {fca_ref}</span></div>'
                    f'{_auth_badge(status_key)}'
                    f'<div style="color:#5A8EBB;font-size:0.72rem;margin-top:0.25rem">{note}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.divider()
        _section_header("SMCR REQUIREMENTS FOR CRYPTO FIRMS", _CAT_COLOR["Asset_Manager"])
        st.markdown("""
Under the **Senior Managers & Certification Regime (SMCR)**, all FCA-authorised firms managing crypto ETPs must:

| Requirement | Detail |
|-------------|--------|
| **SMF16 — Compliance Oversight** | Designated Senior Manager responsible for FCA compliance |
| **SMF17 — Money Laundering Reporting** | Nominated MLRO with direct FCA accountability |
| **SMF3 — Executive Director** | Board-level accountability for crypto strategy and risk |
| **Certification Regime** | Annual certification of fitness and propriety for key staff |
| **Conduct Rules** | All staff must understand and abide by FCA Conduct Rules (COCON) |
| **Regulatory References** | Must obtain/provide regulatory references for all certified persons |
""")

    # Cross-cutting: Financial Promotions
    with st.expander("Financial Promotions & Marketing Rules (All Instruments)", expanded=False):
        st.markdown("""
**FCA PS22/10 — Cryptoasset Financial Promotions Regime (live: 8 October 2023)**

All firms communicating or approving crypto financial promotions to UK persons must comply:

#### Who Must Comply
- UK-authorised firms promoting their own crypto products
- Firms approving promotions for unauthorised businesses (Section 21 FSMA gateway)
- Overseas firms directly marketing to UK consumers (extra-territorial reach)

#### Mandatory Requirements

| Rule | Requirement |
|------|-------------|
| **Risk Warning** | Standard FCA risk warning on all promotions |
| **Personalised Risk Warning** | On first engagement with each retail client |
| **24-Hour Cooling-Off** | Mandatory for first-time investors before purchase |
| **Appropriateness Test** | Client must demonstrate sufficient knowledge/experience |
| **No Inducements** | Refer-a-friend bonuses, free crypto, sign-up rewards prohibited |
| **Approval Chain** | Each promotion must be approved by FCA-authorised person |

#### Penalties for Non-Compliance
- FCA can require immediate withdrawal of promotions
- Financial penalties up to **£1 million or 10% of annual revenue** (whichever higher)
- Criminal liability under s.25 FSMA for communicating unapproved promotions
- Director personal liability under SMCR

#### ETF/ETP-Specific
- **Professional-client-only restrictions** lifted for FCA-authorised ETPs (since Jan 2021)
- Physically-backed ETPs listed on LSE may be sold to retail with appropriate risk warnings
- Synthetic or leveraged crypto ETPs face stricter retail access controls
""")


def _render_compliance_matrix(today: date) -> None:
    st.markdown("### Compliance Matrix — 19 Tracked Instruments")

    col_date, _ = st.columns([2, 2])
    with col_date:
        ref_date = st.date_input(
            "Simulate regulatory state at date:",
            value=today,
            min_value=date(2026, 1, 1),
            max_value=date(2028, 12, 31),
        )

    matrix_data = _compliance_matrix(ref_date.isoformat())
    reports = matrix_data.reports if hasattr(matrix_data, "reports") else matrix_data.get("reports", [])

    # Gantt chart
    phases = [
        {"Phase": "PRE_GATEWAY",       "Start": "2025-01-01", "End": "2026-09-29", "Color": "#149453"},
        {"Phase": "GATEWAY OPEN",      "Start": "2026-09-30", "End": "2027-02-28", "Color": "#E8A500"},
        {"Phase": "POST_GATEWAY",      "Start": "2027-03-01", "End": "2027-10-24", "Color": "#C98900"},
        {"Phase": "ENFORCEMENT CLIFF", "Start": "2027-10-25", "End": "2028-12-31", "Color": "#E53535"},
    ]
    fig_gantt = go.Figure()
    for ph in phases:
        fig_gantt.add_trace(go.Scatter(
            x=[ph["Start"], ph["End"], ph["End"], ph["Start"], ph["Start"]],
            y=[0.1, 0.1, 0.9, 0.9, 0.1],
            fill="toself", fillcolor=_hex_to_rgba(ph["Color"]),
            line={"color": ph["Color"], "width": 1},
            mode="lines", name=ph["Phase"],
            hoverinfo="name+x",
        ))
    fig_gantt.add_vline(
        x=str(ref_date), line_dash="dot",
        line_color="#1AB868", line_width=2,
        annotation_text=f"Ref: {ref_date}",
        annotation_font_color="#1AB868",
    )
    fig_gantt.update_layout(
        height=150, margin={"t": 20, "b": 30, "l": 0, "r": 0},
        paper_bgcolor="#EEF4FB", plot_bgcolor="#EEF4FB",
        xaxis={"range": ["2025-01-01", "2028-12-31"], "color": "#5A8EBB", "gridcolor": "#D9E8F5"},
        yaxis={"visible": False},
        showlegend=True,
        legend={"orientation": "h", "y": 1.15, "font": {"color": "#888", "size": 10}},
    )
    st.plotly_chart(fig_gantt, use_container_width=True, config={"displayModeBar": False})

    if not reports:
        st.warning("No compliance reports generated.")
        return

    # Summary badges — clickable to drill down
    if "rsb_drill_flag" not in st.session_state:
        st.session_state["rsb_drill_flag"] = None

    counts = {
        "GREEN":    matrix_data.green_count    if hasattr(matrix_data, "green_count")    else 0,
        "AMBER":    matrix_data.amber_count    if hasattr(matrix_data, "amber_count")    else 0,
        "RED":      matrix_data.red_count      if hasattr(matrix_data, "red_count")      else 0,
        "CRITICAL": matrix_data.critical_count if hasattr(matrix_data, "critical_count") else 0,
    }
    badge_cols = st.columns(4)
    for col, flag in zip(badge_cols, ["GREEN", "AMBER", "RED", "CRITICAL"]):
        color = _SURVIVAL_COLOR[flag]
        is_active = st.session_state["rsb_drill_flag"] == flag
        border_style = f"3px solid {color}" if is_active else f"1px solid {color}"
        with col:
            st.markdown(
                f'<div id="rsb_badge_{flag}" class="iw-price-card" '
                f'style="background:{color}{"22" if is_active else "0d"};border:{border_style};'
                f'border-radius:8px;padding:0.65rem;text-align:center;cursor:pointer">'
                f'<span style="color:{color};font-size:1.4rem;font-weight:800">{counts[flag]}</span><br>'
                f'<span style="color:#2B5A85;font-size:0.78rem;font-weight:600">{flag}</span><br>'
                f'<span style="color:{color};font-size:0.65rem">{"▼ hide" if is_active else "▲ view"}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "​",
                key=f"rsb_badge_btn_{flag}",
                use_container_width=True,
            ):
                st.session_state["rsb_drill_flag"] = None if is_active else flag
                st.rerun()

    # Wire badge card clicks → hidden trigger buttons
    import streamlit.components.v1 as components
    components.html("""<script>
(function(){
  var doc=window.parent.document;
  function wireBadges(){
    ['GREEN','AMBER','RED','CRITICAL'].forEach(function(flag){
      var card=doc.getElementById('rsb_badge_'+flag);
      if(!card||card._rsbWired)return;
      card._rsbWired=true;
      card.addEventListener('click',function(){
        var mc=card.closest('[data-testid="stMarkdownContainer"]');
        if(!mc)return;
        var sibling=mc.nextElementSibling;
        if(sibling){var btn=sibling.querySelector('button');if(btn){btn.click();return;}}
        var col=mc.closest('[data-testid="column"]')||mc.parentElement;
        if(col){var b=col.querySelector('[data-testid="stButton"] button');if(b)b.click();}
      });
    });
  }
  wireBadges();
  new MutationObserver(wireBadges).observe(doc.body,{childList:true,subtree:true});
})();
</script>""", height=0, scrolling=False)

    # Drill-down panel
    active_flag = st.session_state.get("rsb_drill_flag")
    if active_flag and reports:
        drilled = [r for r in reports
                   if (str(r.survival_flag.value) if hasattr(r.survival_flag, "value")
                       else str(r.survival_flag)) == active_flag]
        color = _SURVIVAL_COLOR[active_flag]
        st.markdown(
            f'<div style="background:{color}11;border:1px solid {color};border-radius:8px;'
            f'padding:0.8rem 1rem;margin:0.5rem 0">'
            f'<span style="color:{color};font-weight:700;font-size:0.85rem">'
            f'{active_flag} — {len(drilled)} Instrument{"s" if len(drilled) != 1 else ""}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        for r in drilled:
            inst_id   = getattr(r, "instrument_id", "—")
            inst_name = getattr(r, "instrument_name", "—")
            auth = getattr(r, "auth_status", None) or "—"
            auth = str(auth.value) if hasattr(auth, "value") else str(auth).replace("_", " ")
            cat = getattr(r, "category", None) or "—"
            cat = str(cat.value) if hasattr(cat, "value") else str(cat).replace("_", " ")
            next_action = getattr(r, "next_action", "—")
            retail_risk = getattr(r, "retail_access_at_risk", False)
            wind_down   = getattr(r, "estimated_wind_down_risk", False)
            risk_tags = ""
            if retail_risk:
                risk_tags += ' <span style="background:#E5353522;color:#E53535;border-radius:3px;padding:0 4px;font-size:0.65rem">Retail Risk</span>'
            if wind_down:
                risk_tags += ' <span style="background:#E5353522;color:#E53535;border-radius:3px;padding:0 4px;font-size:0.65rem">Wind-Down</span>'
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-left:3px solid {color};'
                f'border-radius:0 6px 6px 0;padding:0.55rem 0.85rem;margin-bottom:0.3rem">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<span style="color:{color};font-weight:700;font-size:0.82rem">{inst_id}</span>'
                f'<span style="color:#5A8EBB;font-size:0.68rem">{_CAT_LABEL.get(cat, cat)}</span></div>'
                f'<div style="color:#2B5A85;font-size:0.78rem">{inst_name}</div>'
                f'<div style="color:#5A8EBB;font-size:0.72rem;margin-top:0.1rem">{auth}{risk_tags}</div>'
                f'<div style="color:#5A8EBB;font-size:0.72rem;margin-top:0.15rem">{next_action}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Full matrix table
    d_enforcement = days_to_enforcement(ref_date)
    table_rows = []
    for r in reports:
        flag = str(r.survival_flag.value) if hasattr(r.survival_flag, "value") else str(r.survival_flag)
        cat  = getattr(r, "category", None) or "—"
        cat  = str(cat.value) if hasattr(cat, "value") else str(cat).replace("_", " ")
        auth = getattr(r, "auth_status", None) or "—"
        auth = str(auth.value) if hasattr(auth, "value") else str(auth).replace("_", " ")
        ph   = getattr(r, "current_phase", None) or getattr(r, "phase", None) or "—"
        ph   = str(ph.value) if hasattr(ph, "value") else str(ph).replace("_", " ")
        fca_ref = getattr(r, "fca_ref", None) or "—"
        retail_risk = "Yes" if getattr(r, "retail_access_at_risk", False) else "No"
        wind_down   = "Yes" if getattr(r, "estimated_wind_down_risk", False) else "No"
        req_vop     = "Yes" if getattr(r, "requires_vop", False) else "No"
        table_rows.append({
            "ID":              getattr(r, "instrument_id", None) or getattr(r, "ticker", "—"),
            "Name":            getattr(r, "instrument_name", None) or getattr(r, "name", "—"),
            "Category":        cat,
            "Auth Status":     auth,
            "FCA Ref":         fca_ref,
            "Phase":           ph,
            "Survival":        flag,
            "Retail at Risk":  retail_risk,
            "VoP Required":    req_vop,
            "Wind-Down Risk":  wind_down,
            "Days to Enforce": str(d_enforcement) if d_enforcement is not None else "ACTIVE",
            "Action Required": getattr(r, "next_action", None) or getattr(r, "action_required", "—"),
        })

    df_matrix = pd.DataFrame(table_rows)

    # Filter controls
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        sel_flags = st.multiselect(
            "Filter by Survival Flag",
            ["GREEN", "AMBER", "RED", "CRITICAL"],
            default=["GREEN", "AMBER", "RED", "CRITICAL"],
            key="rsb_flag_filter",
        )
    with fc2:
        sel_cats = st.multiselect(
            "Filter by Category",
            ["LSE ETP", "Spot Crypto", "Stablecoin", "Asset Manager"],
            default=["LSE ETP", "Spot Crypto", "Stablecoin", "Asset Manager"],
            key="rsb_cat_filter",
        )
    with fc3:
        sel_auth = st.multiselect(
            "Filter by Auth Status",
            ["Fully Authorised", "Registered Only", "Application Pending", "Not Started", "Withdrawn"],
            default=["Fully Authorised", "Registered Only", "Application Pending", "Not Started", "Withdrawn"],
            key="rsb_auth_filter",
        )

    df_filtered = df_matrix[
        df_matrix["Survival"].isin(sel_flags) &
        df_matrix["Category"].isin(sel_cats) &
        df_matrix["Auth Status"].isin(sel_auth)
    ]

    st.dataframe(
        df_filtered,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Survival":        st.column_config.TextColumn("Survival Flag"),
            "Retail at Risk":  st.column_config.TextColumn("Retail Risk"),
            "VoP Required":    st.column_config.TextColumn("VoP Req."),
            "Wind-Down Risk":  st.column_config.TextColumn("Wind-Down"),
            "Days to Enforce": st.column_config.TextColumn("Days to Enforcement"),
            "Action Required": st.column_config.TextColumn("Required Action"),
        },
    )

    # Critical deep-dive
    critical_items = [r for r in table_rows if r["Survival"] in ("CRITICAL", "RED")]
    if critical_items:
        with st.expander(f"Critical & Red Instruments ({len(critical_items)}) — Immediate Action Required", expanded=True):
            for item in critical_items:
                color = "#E53535"
                retail_warn = " · Retail Risk" if item["Retail at Risk"] == "Yes" else ""
                wind_warn   = " · Wind-Down Risk" if item["Wind-Down Risk"] == "Yes" else ""
                st.markdown(
                    f'<div style="background:#FEF2F2;border:1px solid {color};border-left:3px solid {color};'
                    f'border-radius:6px;padding:0.65rem;margin-bottom:0.4rem">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<span style="color:{color};font-weight:700">{item["ID"]} — {item["Name"]}</span>'
                    f'{_flag_badge(item["Survival"])}'
                    f'</div>'
                    f'<span style="color:#5A8EBB;font-size:0.78rem">{item["Category"]} · {item["Auth Status"]}{retail_warn}{wind_warn}</span><br>'
                    f'<span style="color:#5A8EBB;font-size:0.78rem">{item["Action Required"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # Individual instrument timeline projection
    st.divider()
    _section_header("INSTRUMENT TIMELINE PROJECTION")
    inst_ids = [r["ID"] for r in table_rows]
    selected_inst = st.selectbox("Select instrument to project across regulatory checkpoints:", inst_ids, key="rsb_proj_select")
    if selected_inst:
        projection = _timeline_projection(selected_inst)
        if projection:
            proj_cols = st.columns(len(projection))
            checkpoint_labels = ["Today", "Gateway Opens", "Gateway Closes", "Enforcement Cliff"]
            for col, (proj_date, proj_flag, proj_phase), cp_label in zip(proj_cols, projection, checkpoint_labels):
                flag_color = _SURVIVAL_COLOR.get(str(proj_flag), "#888")
                phase_color = _PHASE_COLOR.get(str(proj_phase), "#666")
                with col:
                    st.markdown(
                        f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-top:3px solid {flag_color};'
                        f'border-radius:8px;padding:0.6rem;text-align:center">'
                        f'<div style="font-size:0.65rem;color:#5A8EBB;letter-spacing:0.08em">{cp_label}</div>'
                        f'<div style="font-size:0.75rem;color:#5A8EBB">{proj_date}</div>'
                        f'<div style="margin:0.3rem 0">{_flag_badge(str(proj_flag))}</div>'
                        f'<div style="font-size:0.62rem;color:{phase_color}">{str(proj_phase).replace("_"," ")}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        # Risk narrative for selected instrument
        for r in reports:
            if getattr(r, "instrument_id", None) == selected_inst:
                narrative = getattr(r, "risk_narrative", "")
                if narrative:
                    st.markdown(
                        f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-left:3px solid #3A72A0;'
                        f'border-radius:0 6px 6px 0;padding:0.6rem 1rem;margin-top:0.5rem">'
                        f'<div style="color:#3A72A0;font-size:0.72rem;font-weight:700;margin-bottom:0.25rem">RISK NARRATIVE</div>'
                        f'<div style="color:#5A8EBB;font-size:0.78rem;line-height:1.5">{narrative}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                deadline = getattr(r, "deadline", None)
                deadline_label = getattr(r, "deadline_label", "")
                next_action = getattr(r, "next_action", "")
                if deadline:
                    days_left = (deadline - ref_date).days
                    dl_color = "#E53535" if days_left <= 30 else "#E8A500" if days_left <= 90 else "#1AB868"
                    st.markdown(
                        f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-radius:6px;'
                        f'padding:0.5rem 0.8rem;margin-top:0.35rem;display:flex;gap:1rem">'
                        f'<span style="color:#5A8EBB;font-size:0.75rem">Deadline:</span>'
                        f'<span style="color:{dl_color};font-weight:700;font-size:0.75rem">{deadline} ({deadline_label})</span>'
                        f'<span style="color:#5A8EBB;font-size:0.72rem">— {days_left}d remaining</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                if next_action:
                    st.markdown(
                        f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-radius:6px;'
                        f'padding:0.5rem 0.8rem;margin-top:0.25rem">'
                        f'<span style="color:#E8A500;font-size:0.72rem;font-weight:700">Required action: </span>'
                        f'<span style="color:#2B5A85;font-size:0.75rem">{next_action}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                break


def _render_timeline(today: date) -> None:
    st.markdown("### Regulatory Timeline & Upcoming Plans")

    # All 7 REGULATORY_MILESTONES
    ALL_MILESTONES = [
        {
            "date":   date(2025, 1, 1),
            "label":  "UK Crypto Financial Promotions Regime",
            "detail": "FCA PS22/10 live. All crypto financial promotions to UK persons must comply with mandatory risk warnings, cooling-off periods, and appropriateness tests.",
            "phase":  "PRE_GATEWAY",
            "status": "PASSED",
        },
        {
            "date":   date(2026, 1, 1),
            "label":  "Stablecoin Issuance Regime Expected",
            "detail": "FCA expected to publish final stablecoin issuer rules under FSMA 2023 Part 5A. Fiat-backed stablecoins require EMI authorisation or recognition.",
            "phase":  "PRE_GATEWAY",
            "status": "PASSED" if today >= date(2026, 1, 1) else "UPCOMING",
        },
        {
            "date":   GATEWAY_OPEN_DATE,
            "label":  "FCA Part 4A Crypto Gateway Opens",
            "detail": "FCA begins accepting full authorisation applications under the new cryptoasset regime. Firms should submit Part 4A or Variation of Permission (VoP) applications.",
            "phase":  "GATEWAY_OPEN",
            "status": "PASSED" if today >= GATEWAY_OPEN_DATE else "UPCOMING",
        },
        {
            "date":   date(2026, 12, 1),
            "label":  "FCA Target: 50% Applications Assessed",
            "detail": "FCA internal target to have assessed at least 50% of submitted crypto authorisation applications by this date.",
            "phase":  "GATEWAY_OPEN",
            "status": "PASSED" if today >= date(2026, 12, 1) else "UPCOMING",
        },
        {
            "date":   GATEWAY_CLOSE_DATE,
            "label":  "Gateway Closes — HARD DEADLINE",
            "detail": "Final deadline for submitting Part 4A or VoP applications. Firms not registered or applied by this date must cease regulated crypto activities. No extensions.",
            "phase":  "POST_GATEWAY",
            "status": "PASSED" if today >= GATEWAY_CLOSE_DATE else "CRITICAL",
        },
        {
            "date":   date(2027, 6, 30),
            "label":  "FCA Target: All Applications Decided",
            "detail": "FCA targets completion of all crypto authorisation decisions. Firms with applications pending receive interim transitional protection until decided.",
            "phase":  "POST_GATEWAY",
            "status": "PASSED" if today >= date(2027, 6, 30) else "UPCOMING",
        },
        {
            "date":   ENFORCEMENT_DATE,
            "label":  "Hard Enforcement Cliff — s.23 FSMA",
            "detail": "Criminal liability under s.23 FSMA activates. Operating regulated cryptoasset activities without Part 4A authorisation is a criminal offence: up to 2 years imprisonment + unlimited fine.",
            "phase":  "ENFORCEMENT_CLIFF",
            "status": "PASSED" if today >= ENFORCEMENT_DATE else "CRITICAL",
        },
    ]

    _section_header("COMPLETE REGULATORY MILESTONE CALENDAR")

    for i, m in enumerate(ALL_MILESTONES):
        days_delta = (m["date"] - today).days
        is_passed = days_delta < 0
        is_critical = m["status"] == "CRITICAL"

        if is_passed:
            border_color = "#D9E8F5"
            date_color = "#5A8EBB"
            label_color = "#5A8EBB"
            status_chip = '<span style="color:#5A8EBB;font-size:0.68rem">PASSED</span>'
            bg = "#EEF4FB"
        elif is_critical:
            border_color = "#E53535"
            date_color = "#E53535"
            label_color = "#E53535"
            status_chip = f'<span style="color:#E53535;font-weight:700;font-size:0.72rem">{days_delta}d remaining</span>'
            bg = "#FEF2F2"
        else:
            phase_col = _PHASE_COLOR.get(m["phase"], "#3A72A0")
            border_color = phase_col
            date_color = phase_col
            label_color = "#071D35"
            status_chip = f'<span style="color:{phase_col};font-size:0.72rem">{days_delta}d</span>'
            bg = "#ffffff"

        connector = '<div style="width:2px;height:1rem;background:#D9E8F5;margin-left:1.2rem"></div>' if i < len(ALL_MILESTONES) - 1 else ""

        st.markdown(
            f'<div style="background:{bg};border:1px solid {border_color};border-left:4px solid {border_color};'
            f'border-radius:0 8px 8px 0;padding:0.65rem 1rem;margin-bottom:0">'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<span style="color:{label_color};font-weight:700;font-size:0.82rem">{m["label"]}</span>'
            f'{status_chip}</div>'
            f'<div style="color:{date_color};font-size:0.72rem;margin:0.15rem 0">{m["date"]} · {m["phase"].replace("_"," ")}</div>'
            f'<div style="color:#5A8EBB;font-size:0.74rem;line-height:1.4">{m["detail"]}</div>'
            f'</div>{connector}',
            unsafe_allow_html=True,
        )

    st.divider()

    # Upcoming regulatory plans & consultations
    _section_header("UPCOMING REGULATORY PLANS & CONSULTATIONS")

    upcoming_plans = [
        {
            "title": "FCA Crypto Custody Rules Consultation",
            "expected": "Q3 2026",
            "detail": "FCA expected to publish detailed custody rules for crypto assets held by authorised firms. Will cover cold storage requirements, key management, proof-of-reserves, and insurance mandates.",
            "impact": "LSE ETPs, Asset Managers",
            "color": "#3A72A0",
        },
        {
            "title": "Stablecoin Systemic Designation",
            "expected": "Q4 2026",
            "detail": "HM Treasury / Bank of England to designate systemically important stablecoins (>£10bn daily volume). USDT likely candidate. Designated coins face enhanced prudential requirements.",
            "impact": "USDT, USDC",
            "color": "#1AB868",
        },
        {
            "title": "FCA Cryptoasset Trading Venue Rules",
            "expected": "Q1 2027",
            "detail": "Rules for UK crypto trading platforms (Multilateral Trading Facilities) — market abuse prevention, order book transparency, algorithmic trading controls.",
            "impact": "Spot Crypto Exchanges",
            "color": "#7c3aed",
        },
        {
            "title": "Digital Securities Sandbox (DSS) Expansion",
            "expected": "Ongoing",
            "detail": "Bank of England and FCA jointly operating Digital Securities Sandbox. Tokenised securities (including ETFs on DLT) can operate under modified FMI rules. Currently in live phase.",
            "impact": "LSE ETPs, Asset Managers",
            "color": "#E8A500",
        },
        {
            "title": "UK Crypto Equivalence Assessments",
            "expected": "2027",
            "detail": "HM Treasury to assess equivalence of EU MiCA regime and other major jurisdictions. Could enable cross-border recognition of authorisations, reducing dual-licensing burden.",
            "impact": "All Instrument Types",
            "color": "#E8A500",
        },
        {
            "title": "CBDC (Digital Pound) Framework",
            "expected": "2027–2028",
            "detail": "Bank of England progressing Digital Pound (retail CBDC) design phase. Will impact stablecoin market dynamics and potentially create direct competition to regulated stablecoins.",
            "impact": "Stablecoins",
            "color": "#1AB868",
        },
    ]

    plan_cols = st.columns(2)
    for i, plan in enumerate(upcoming_plans):
        with plan_cols[i % 2]:
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-top:3px solid {plan["color"]};'
                f'border-radius:8px;padding:0.7rem 0.9rem;margin-bottom:0.5rem;height:100%">'
                f'<div style="color:{plan["color"]};font-weight:700;font-size:0.8rem">{plan["title"]}</div>'
                f'<div style="color:#5A8EBB;font-size:0.7rem;margin:0.2rem 0">'
                f'Expected: <span style="color:#2B5A85;font-weight:600">{plan["expected"]}</span>'
                f' · Affects: <span style="color:#2B5A85;font-weight:600">{plan["impact"]}</span></div>'
                f'<div style="color:#2B5A85;font-size:0.75rem;line-height:1.5;margin-top:0.3rem">{plan["detail"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # Regulatory framework explainer
    with st.expander("UK Crypto Regulatory Framework — Complete Reference", expanded=False):
        st.markdown("""
### Legislative Architecture

| Legislation | Key Provisions |
|------------|----------------|
| **FSMA 2000** (as amended) | Part 4A authorisation; s.19 general prohibition; s.23 criminal liability; Schedule 2 regulated activities |
| **FSMA 2023** | Extended FCA perimeter to cryptoassets; Part 5A stablecoin regime; Digital Securities Sandbox enabling powers |
| **Money Laundering Regulations 2017** (as amended) | AML/CFT registration for crypto exchange providers and custodian wallet providers |
| **Financial Services Act 2021** | UK Financial Promotions Order amendments; cryptoasset promotion regime |
| **Proceeds of Crime Act 2002** | UK Travel Rule implementation; criminal property confiscation |

### FCA Cryptoasset Perimeter — Regulated Activities

| Activity | Regulatory Requirement |
|----------|----------------------|
| Operating a cryptoasset exchange | Part 4A FSMA + MLR registration |
| Dealing in cryptoassets as principal | Part 4A FSMA permission |
| Arranging deals in cryptoassets | Part 4A FSMA permission |
| Safeguarding cryptoassets (custody) | Part 4A FSMA + CASS compliance |
| Issuing stablecoins | Part 5A FSMA / EMI authorisation |
| Promoting cryptoassets | FCA financial promotions approval |
| Managing crypto investment portfolios | Part 4A FSMA (investment management) |

### Phase Summary

| Phase | Date Range | Implications |
|-------|-----------|-------------|
| **Pre-Gateway** | Before 30 Sep 2026 | Temporary registration; sandbox rules; prepare applications |
| **Gateway Open** | 30 Sep 2026 – 28 Feb 2027 | FCA accepts full Part 4A and VoP applications |
| **Post-Gateway** | 1 Mar 2027 – 24 Oct 2027 | Gateway closed; pending applicants protected; non-applicants must cease |
| **Enforcement Cliff** | 25 Oct 2027 onwards | s.23 FSMA criminal liability active; FCA enforcement begins |

### Strategic Implications

**Regulatory Moat**: Firms securing FCA authorisation before gateway close gain significant competitive advantage — late entrants face 2+ year wait or prohibition from UK market.

**AUM Consolidation**: Institutional AUM expected to consolidate into 3-5 FCA-authorised operators. BlackRock, WisdomTree, and CoinShares best positioned given existing registration.

**Stablecoin Market**: USDT and GBPT face highest risk of UK prohibition. USDC's US regulatory track record improves its UK authorisation prospects.

**International Firms**: Overseas firms (21Shares AG — Switzerland) must obtain direct UK FCA authorisation; EU MiCA equivalence not confirmed, so passporting not available.
""")


def render() -> None:
    today = date.today()
    phase = current_phase(today)
    phase_color = _PHASE_COLOR.get(phase, "#666")

    st.markdown("<h2 class='iw-module-header'>Regulatory Sandbox — UK FSMA 2026/2027 FCA Compliance Intelligence</h2>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "Overview",
        "FCA Requirements",
        "Compliance Matrix",
        "Timeline & Plans",
    ])

    with tab1:
        _render_overview(today, phase, phase_color)

    with tab2:
        _render_fca_requirements()

    with tab3:
        _render_compliance_matrix(today)

    with tab4:
        _render_timeline(today)
