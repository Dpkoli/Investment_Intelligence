"""
Regulatory Sandbox — UK FSMA 2026/2027 FCA countdown matrix renderer.
Moved from Zone 3 of the monolithic app into a self-contained module.
"""
from __future__ import annotations

import sys
import os
from datetime import date
from typing import Any

import streamlit as st
import plotly.express as px
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
from analytics.compliance.uk_crypto_matrix import UKCryptoComplianceMatrix

_PHASE_COLOR = {
    "PRE_GATEWAY":       "#4A7C59",
    "GATEWAY_OPEN":      "#FFA500",
    "POST_GATEWAY":      "#CC5500",
    "ENFORCEMENT_CLIFF": "#CC0000",
}
_SURVIVAL_COLOR = {
    "GREEN":    "#00D4AA",
    "AMBER":    "#FFA500",
    "RED":      "#FF6B6B",
    "CRITICAL": "#FF2222",
}


def _badge(flag: str) -> str:
    cls_map = {"GREEN": "badge-green", "AMBER": "badge-amber",
               "RED": "badge-red", "CRITICAL": "badge-critical"}
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


@st.cache_data(ttl=600, show_spinner=False)
def _compliance_matrix(ref_str: str) -> Any:
    ref = date.fromisoformat(ref_str)
    m = UKCryptoComplianceMatrix()
    return m.generate(reference_date=ref)


def render() -> None:
    today = date.today()
    phase = current_phase(today)
    phase_color = _PHASE_COLOR.get(phase, "#666")

    st.markdown("## 🏛️ Regulatory Sandbox — UK FSMA 2026/2027 FCA Countdown Matrix")

    # ── Phase Banner ──────────────────────────────────────────────────────────
    st.markdown(
        f"""<div style="background:linear-gradient(90deg,{phase_color}22,transparent);
            border:1px solid {phase_color};border-radius:8px;padding:0.75rem 1.2rem;margin-bottom:1rem">
            <span style="color:{phase_color};font-weight:700;font-size:0.85rem;letter-spacing:0.1em">
            CURRENT REGULATORY PHASE: {phase.replace('_',' ')}
            </span><br>
            <span style="color:#aaa;font-size:0.82rem">{phase_narrative(phase)}</span>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Countdown clocks ──────────────────────────────────────────────────────
    t1, t2, t3 = st.columns(3)
    with t1:
        d = days_to_gateway_open(today)
        color = "#4A7C59" if (d is not None and d > 0) else "#888"
        label = f"{d}d" if (d is not None and d > 0) else "OPEN"
        st.markdown(
            f"""<div style="background:#1A1D24;border:1px solid #2E3140;border-top:3px solid {color};
                border-radius:8px;padding:0.75rem;text-align:center">
                <div style="font-size:0.7rem;color:#888;letter-spacing:0.1em">GATEWAY OPENS</div>
                <div style="font-size:1.6rem;font-weight:700;color:{color}">{label}</div>
                <div style="font-size:0.75rem;color:#888">{GATEWAY_OPEN_DATE}</div>
                <div style="font-size:0.68rem;color:#666">FCA registration window opens</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with t2:
        d = days_to_gateway_close(today)
        color = ("#FFA500" if (d is not None and d > 30)
                 else "#FF6B6B" if (d is not None and d > 0)
                 else "#888")
        label = f"{d}d" if (d is not None and d > 0) else "CLOSED"
        st.markdown(
            f"""<div style="background:#1A1D24;border:1px solid #2E3140;border-top:3px solid {color};
                border-radius:8px;padding:0.75rem;text-align:center">
                <div style="font-size:0.7rem;color:#888;letter-spacing:0.1em">GATEWAY CLOSES</div>
                <div style="font-size:1.6rem;font-weight:700;color:{color}">{label}</div>
                <div style="font-size:0.75rem;color:#888">{GATEWAY_CLOSE_DATE}</div>
                <div style="font-size:0.68rem;color:#666">Final registration deadline (HARD)</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with t3:
        d = days_to_enforcement(today)
        color = ("#CC0000" if (d is not None and d <= 90)
                 else "#FF6B6B" if (d is not None and d <= 180)
                 else "#FFA500" if d is not None
                 else "#CC0000")
        label = f"{d}d" if (d is not None and d > 0) else "ACTIVE"
        st.markdown(
            f"""<div style="background:#1A1D24;border:1px solid #2E3140;border-top:3px solid {color};
                border-radius:8px;padding:0.75rem;text-align:center">
                <div style="font-size:0.7rem;color:#888;letter-spacing:0.1em">ENFORCEMENT CLIFF</div>
                <div style="font-size:1.6rem;font-weight:700;color:{color}">{label}</div>
                <div style="font-size:0.75rem;color:#888">{ENFORCEMENT_DATE}</div>
                <div style="font-size:0.68rem;color:#666">s.23 FSMA criminal liability begins</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Reference date slider ─────────────────────────────────────────────────
    st.markdown("**Simulate regulatory timeline at a specific reference date:**")
    col_date, col_go = st.columns([3, 1])
    with col_date:
        ref_date = st.date_input(
            "Reference date",
            value=today,
            min_value=date(2026, 1, 1),
            max_value=date(2028, 12, 31),
        )
    with col_go:
        st.markdown("<br>", unsafe_allow_html=True)

    matrix_data = _compliance_matrix(ref_date.isoformat())

    # ── FCA Gantt chart ───────────────────────────────────────────────────────
    phases = [
        {"Phase": "PRE_GATEWAY",       "Start": "2025-01-01", "End": "2026-09-29", "Color": "#4A7C59"},
        {"Phase": "GATEWAY OPEN",      "Start": "2026-09-30", "End": "2027-02-28", "Color": "#FFA500"},
        {"Phase": "POST_GATEWAY",      "Start": "2027-03-01", "End": "2027-10-24", "Color": "#CC5500"},
        {"Phase": "ENFORCEMENT CLIFF", "Start": "2027-10-25", "End": "2028-12-31", "Color": "#CC0000"},
    ]
    fig_gantt = go.Figure()
    for ph in phases:
        fig_gantt.add_trace(go.Scatter(
            x=[ph["Start"], ph["End"], ph["End"], ph["Start"], ph["Start"]],
            y=[0.1, 0.1, 0.9, 0.9, 0.1],
            fill="toself", fillcolor=ph["Color"] + "44",
            line={"color": ph["Color"], "width": 1},
            mode="lines", name=ph["Phase"],
            hoverinfo="name+x",
        ))
    fig_gantt.add_vline(
        x=str(ref_date), line_dash="dot",
        line_color="#00D4AA", line_width=2,
        annotation_text=f"Today {ref_date}",
        annotation_font_color="#00D4AA",
    )
    fig_gantt.update_layout(
        height=150, margin={"t": 20, "b": 30, "l": 0, "r": 0},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"range": ["2025-01-01", "2028-12-31"], "color": "#666", "gridcolor": "#2E3140"},
        yaxis={"visible": False},
        showlegend=True,
        legend={"orientation": "h", "y": 1.15, "font": {"color": "#888", "size": 10}},
    )
    st.plotly_chart(fig_gantt, use_container_width=True, config={"displayModeBar": False})

    # ── Compliance matrix table ───────────────────────────────────────────────
    st.markdown(f"### {len(reports) if hasattr(matrix_data, 'reports') else 19}-Instrument Compliance Matrix")
    if hasattr(matrix_data, "reports"):
        reports = matrix_data.reports
    elif isinstance(matrix_data, dict):
        reports = matrix_data.get("reports", [])
    else:
        reports = []

    if reports:
        summary_counts: dict = {}
        table_rows = []
        d_enforcement = days_to_enforcement(ref_date)
        for r in reports:
            # survival_flag is a plain string ("RED", "AMBER", "GREEN", "CRITICAL")
            flag = str(r.survival_flag.value) if hasattr(r.survival_flag, "value") else str(r.survival_flag)
            summary_counts[flag] = summary_counts.get(flag, 0) + 1
            # category and auth_status are plain strings with underscores → prettify
            cat       = getattr(r, "category", None) or "—"
            cat       = str(cat.value) if hasattr(cat, "value") else str(cat).replace("_", " ")
            auth      = getattr(r, "auth_status", None) or "—"
            auth      = str(auth.value) if hasattr(auth, "value") else str(auth).replace("_", " ")
            phase_val = getattr(r, "current_phase", None) or getattr(r, "phase", None) or "—"
            phase_val = str(phase_val.value) if hasattr(phase_val, "value") else str(phase_val).replace("_", " ")
            table_rows.append({
                "ID":          getattr(r, "instrument_id", None) or getattr(r, "ticker", "—"),
                "Name":        getattr(r, "instrument_name", None) or getattr(r, "name", "—"),
                "Category":    cat,
                "Auth Status": auth,
                "Phase":       phase_val,
                "Survival":    flag,
                "Days Left":   str(d_enforcement) if d_enforcement is not None else "ACTIVE",
                "Action Required": getattr(r, "next_action", None) or getattr(r, "action_required", "—"),
            })

        # Summary badges
        badge_cols = st.columns(4)
        for col, (flag, count) in zip(badge_cols, [("GREEN",    summary_counts.get("GREEN", 0)),
                                                    ("AMBER",    summary_counts.get("AMBER", 0)),
                                                    ("RED",      summary_counts.get("RED", 0)),
                                                    ("CRITICAL", summary_counts.get("CRITICAL", 0))]):
            color = _SURVIVAL_COLOR.get(flag, "#888")
            with col:
                st.markdown(
                    f'<div style="background:{color}22;border:1px solid {color};border-radius:6px;'
                    f'padding:0.5rem;text-align:center"><span style="color:{color};font-size:1.2rem;font-weight:700">'
                    f'{count}</span><br><span style="color:#888;font-size:0.72rem">{flag}</span></div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)

        df_matrix = pd.DataFrame(table_rows)
        st.dataframe(
            df_matrix,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Survival":         st.column_config.TextColumn("Survival Flag"),
                "Days Left":        st.column_config.TextColumn("Days to Enforcement"),
                "Action Required":  st.column_config.TextColumn("Action Required"),
            },
        )

        # Critical instruments deep-dive
        critical_items = [r for r in table_rows if r["Survival"] in ("CRITICAL", "RED")]
        if critical_items:
            with st.expander(f"🚨 Critical & Red Instruments ({len(critical_items)}) — Immediate Action Required", expanded=True):
                for item in critical_items:
                    color = "#FF2222" if item["Survival"] == "CRITICAL" else "#FF6B6B"
                    st.markdown(
                        f"""<div style="background:#2A1A1A;border:1px solid {color};border-radius:6px;padding:0.65rem;margin-bottom:0.4rem">
                            <span style="color:{color};font-weight:700">{item['ID']} — {item['Name']}</span>
                            <span style="color:#888;font-size:0.78rem;margin-left:1rem">{item['Category']} · {item['Auth Status']}</span><br>
                            <span style="color:#aaa;font-size:0.78rem">⚡ {item['Action Required']}</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )

    # ── Upcoming milestones ───────────────────────────────────────────────────
    milestones = upcoming_milestones(ref_date)
    if milestones:
        st.divider()
        st.markdown("### ⏰ Upcoming Regulatory Milestones")
        for m in milestones[:5]:
            label = m.get("label", "—")
            dt    = m.get("date") or m.get("deadline") or "—"
            desc  = m.get("detail") or m.get("description", "")
            urgency_color = "#FF4B4B" if "ENFORCEMENT" in label.upper() else "#FFA500" if "GATEWAY" in label.upper() else "#00D4AA"
            st.markdown(
                f"""<div style="background:#1A1D24;border:1px solid #2E3140;border-left:3px solid {urgency_color};
                    border-radius:6px;padding:0.5rem 0.9rem;margin-bottom:0.3rem">
                    <span style="color:{urgency_color};font-weight:700;font-size:0.8rem">{label}</span>
                    <span style="color:#888;font-size:0.78rem;margin-left:0.5rem">{dt}</span>
                    {"<br>" + f'<span style="color:#aaa;font-size:0.75rem">{desc}</span>' if desc else ""}
                </div>""",
                unsafe_allow_html=True,
            )

    # ── Regulatory intelligence explainer ─────────────────────────────────────
    with st.expander("📖 UK Crypto Regulatory Framework — What This Means", expanded=False):
        st.markdown("""
**FSMA 2023 (Financial Services and Markets Act 2023)** expanded FCA's perimeter to all crypto asset
activities in the UK, including issuance, promotion, and exchange operations.

| Phase | Date | Implications |
|-------|------|-------------|
| **Pre-Gateway** | Before 30 Sep 2026 | Temporary registration window; existing firms may operate under sandbox rules |
| **Gateway Opens** | 30 Sep 2026 | FCA begins processing full authorisation applications under new crypto regime |
| **Gateway Closes** | 28 Feb 2027 | **HARD DEADLINE** — any firm not registered or applied for authorisation must cease regulated crypto activities |
| **Enforcement Cliff** | 25 Oct 2027 | Section 23 FSMA criminal liability activates — operating without authorisation becomes a criminal offence (up to 2 years imprisonment + unlimited fine) |

**LSE ETP Considerations:**
- Physically-backed ETPs listed on LSE are already FCA-supervised under UCITS-equivalent rules
- Stablecoins face specific Electronic Money Institution (EMI) licensing requirements
- Privacy coins (XMR, ZEC) face probable de facto prohibition under JMLSG guidance

**Strategic Implication:** Firms achieving FCA registration before gateway close gain permanent regulatory moat vs. later entrants, likely driving institutional AUM consolidation into 3-5 dominant authorised operators.
        """)
