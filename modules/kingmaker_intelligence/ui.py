"""
Kingmaker Intelligence — interactive multi-sector supply-chain drawer.
Features: sector filter, anchor selector, valuation matrix, clickable sources,
expandable systemic assessment panel for each supplier link.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from .data import SUPPLY_CHAIN_REGISTRY, SupplyChainLink, ALL_SECTORS, SECTOR_ANCHORS

_CONN_COLOR = {
    "Custom_Silicon":  "#00D4AA",
    "JV_Partner":      "#FFA500",
    "Sole_Supplier":   "#FF4B4B",
    "Preferred_Supplier": "#4ADE80",
    "Subcontractor":   "#A78BFA",
    "CRO":             "#60A5FA",
    "CDMO":            "#F472B6",
}
_WALLET_COLOR = {
    "Critical (>50%)":     "#FF2222",
    "Major (30-50%)":      "#FF8C00",
    "Significant (15-30%)":"#FFA500",
    "Notable (5-15%)":     "#4ADE80",
}


def _conn_badge(ct: str) -> str:
    color = _CONN_COLOR.get(ct, "#888")
    return (
        f'<span style="background:rgba(0,0,0,0.3);border:1px solid {color};color:{color};'
        f'border-radius:4px;padding:2px 6px;font-size:0.70rem;font-weight:700">{ct.replace("_"," ")}</span>'
    )


def _wallet_badge(q: str) -> str:
    color = _WALLET_COLOR.get(q, "#888")
    return (
        f'<span style="color:{color};font-size:0.72rem;font-weight:700">{q}</span>'
    )


def _valuation_delta_bar(anchor_val: float | None, supplier_val: float | None,
                         label: str) -> go.Figure | None:
    if anchor_val is None or supplier_val is None:
        return None
    discount = (supplier_val - anchor_val) / anchor_val * 100
    color = "#00D4AA" if discount < 0 else "#FF6B6B"
    fig = go.Figure(go.Bar(
        x=[anchor_val, supplier_val],
        y=["Anchor", "Supplier"],
        orientation="h",
        marker_color=["#e2e8f0", color],
        text=[f"{anchor_val:.1f}×", f"{supplier_val:.1f}×  ({discount:+.0f}%)"],
        textposition="outside",
        hoverinfo="skip",
    ))
    fig.update_layout(
        height=90, margin={"t": 5, "b": 5, "l": 60, "r": 80},
        paper_bgcolor="#f4f6f9", plot_bgcolor="#f4f6f9",
        xaxis={"visible": False}, yaxis={"color": "#888", "tickfont": {"size": 10}},
        showlegend=False,
        title={"text": label, "font": {"size": 11, "color": "#888"}, "x": 0},
    )
    return fig


def _render_link_card(link: SupplyChainLink, idx: int) -> None:
    sector_icon = {
        "Technology": "💻", "Energy": "⚡", "Consumer": "🛒",
        "Defense": "🛡️", "Healthcare": "🏥", "Materials": "⛏️",
    }.get(link.sector, "🔗")

    wallet_pct_str = (f" — {link.wallet_share_pct:.0f}% revenue dependency"
                      if link.wallet_share_pct else "")

    source_link = (
        f'<a href="{link.source_url}" target="_blank" style="color:#00D4AA;font-size:0.72rem;text-decoration:none">'
        f'↗ Source IR</a>'
        if link.source_url else ""
    )

    renewal_str = (f"Renewal cliff: <b>{link.renewal_cliff}</b>" if link.renewal_cliff else "")

    st.markdown(
        f"""<div style="background:#ffffff;border:1px solid #e2e8f0;border-left:3px solid {_CONN_COLOR.get(link.connection_type,'#888')};
            border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.5rem">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem">
                <div>
                    <span style="font-size:0.75rem;color:#64748b">{sector_icon} {link.sector} · {link.anchor_index}</span><br>
                    <span style="font-size:1rem;font-weight:700">{link.anchor_ticker} → {link.supplier_ticker}</span>
                    <span style="color:#64748b;margin:0 0.5rem">|</span>
                    <span style="font-size:0.85rem">{link.anchor_name} → <b>{link.supplier_name}</b></span>
                </div>
                <div style="display:flex;gap:0.5rem;align-items:center;flex-wrap:wrap">
                    {_conn_badge(link.connection_type)}
                    {_wallet_badge(link.wallet_share_qual)}
                    {source_link}
                </div>
            </div>
            <div style="margin-top:0.4rem;font-size:0.78rem;color:#64748b">
                <b>Supply Layer:</b> {link.supply_layer}{wallet_pct_str}
                {"  ·  " + renewal_str if renewal_str else ""}
                {"  ·  Contract: " + str(link.contract_years) + "y" if link.contract_years else ""}
            </div>
            {f'<div style="margin-top:0.35rem;font-size:0.75rem;font-style:italic;color:#64748b">" {link.exec_quote} "</div>' if link.exec_quote else ""}
        </div>""",
        unsafe_allow_html=True,
    )

    with st.expander("📊 Systemic Assessment & Strategic Recommendation", expanded=False):
        # Valuation delta bars
        if link.ev_ebitda_anchor or link.ev_ebitda_supplier:
            col_v1, col_v2, col_v3 = st.columns(3)
            with col_v1:
                fig = _valuation_delta_bar(link.ev_ebitda_anchor, link.ev_ebitda_supplier, "EV/EBITDA ×")
                if fig:
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            with col_v2:
                fig2 = _valuation_delta_bar(link.pe_anchor, link.pe_supplier, "P/E ×")
                if fig2:
                    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            with col_v3:
                fig3 = _valuation_delta_bar(link.ps_anchor, link.ps_supplier, "P/S ×")
                if fig3:
                    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

        # Valuation narrative
        if link.valuation_narrative:
            st.markdown(f"**Relative Valuation Analysis:**\n\n{link.valuation_narrative}")

        # Wallet share risk assessment
        ws = link.wallet_share_pct or 0
        if ws >= 50:
            st.error(f"🔴 **CRITICAL concentration risk** — {ws:.0f}% of {link.supplier_name}'s estimated revenue flows from {link.anchor_name}. Any procurement shift or anchor diversification represents an existential risk event.")
        elif ws >= 30:
            st.warning(f"⚠️ **HIGH concentration** — {ws:.0f}% revenue dependency. Monitor {link.renewal_cliff or 'contract renewal'} closely. Anchor diversification at {link.supplier_name} is a key de-risking catalyst.")
        elif ws >= 15:
            st.info(f"ℹ️ **SIGNIFICANT dependency** — {ws:.0f}% revenue from {link.anchor_name}. Manageable but warrants tracking alongside anchor earnings guidance.")

        # Strategic prediction
        renewal_narrative = (
            f"Contract renewal cliff in **{link.renewal_cliff}** creates a binary re-pricing event. "
            f"If {link.anchor_name} maintains or extends the relationship, expect {link.supplier_ticker} "
            f"to rerate 15-35% on forward estimates within 2 quarters of renewal announcement."
        ) if link.renewal_cliff else ""

        tactical_events = _tactical_predictions(link)
        if tactical_events:
            st.markdown("**Expected Tactical Events (6-24 month horizon):**")
            for event in tactical_events:
                st.markdown(f"• {event}")

        if renewal_narrative:
            st.caption(renewal_narrative)

        if link.notes:
            st.caption(f"📌 {link.notes}")


def _tactical_predictions(link: SupplyChainLink) -> list[str]:
    """Generate sector-specific tactical event predictions based on link attributes."""
    events = []
    ws = link.wallet_share_pct or 0

    if link.connection_type == "Custom_Silicon":
        events.append(f"Next chip generation tape-out by {link.anchor_name} will expand {link.supplier_name} silicon revenue by an estimated 25-40% YoY, given increased die complexity and volume commitments.")
        events.append(f"Watch for {link.anchor_name} annual developer conference keynote — named {link.supplier_name} endorsements historically trigger 10-25% next-day share price moves.")

    if link.connection_type == "Sole_Supplier":
        events.append(f"{link.supplier_name} has pricing leverage at renewal — sole-source status in regulated industries typically enables 8-15% per-annum contract price escalation.")
        events.append(f"Competitor qualification attempts by {link.anchor_name} (2-4 year qualification cycle) are structural moat protection periods for {link.supplier_name}.")

    if link.sector == "Energy":
        events.append("Energy market CAPEX uplift cycle (2025-2027) driven by AI data centre power demand creates structural services volume uplift across oilfield and grid-infrastructure supply chains.")
        events.append(f"Carbon pricing mechanisms (CBAM, UK ETS) increasingly favour low-emission service providers — monitor {link.supplier_name}'s ESG certification progress for contract preference scoring.")

    if link.sector == "Defense":
        events.append(f"NATO 2% GDP pledge compliance by European members (2024-2026 acceleration) creates structural demand uplift for {link.anchor_name} prime contract book, propagating to tier-2 suppliers.")
        events.append(f"Watch for US DoD supplemental appropriations bill — each $1bn incremental defense spend typically generates $80-120mn in tier-2 supplier contract flow for platforms using {link.supply_layer.split('(')[0].strip()}.")

    if link.sector == "Healthcare":
        events.append(f"FDA PDUFA date pipeline for {link.anchor_name} creates near-term approval catalysts — each NDA approval historically doubles service revenue for CRO/CDMO partners over the subsequent 18 months.")
        events.append("Post-COVID CRO/CDMO demand normalisation complete by 2026 — sector now entering re-acceleration phase driven by GLP-1, oncology, and rare disease pipeline proliferation.")

    if link.sector == "Consumer":
        events.append(f"E-commerce penetration reaching 30-35% of total retail by 2027 structurally increases packaging and logistics demand — {link.supplier_name} positioned at the intersection of both trends.")

    if link.sector == "Materials":
        events.append(f"EV adoption trajectory (IEA: 45% new car sales by 2030) creates 5-10× demand growth for battery materials — {link.supplier_name}'s supply position is structurally under-priced at current multiples.")

    if ws >= 30:
        events.append(f"Wallet-share concentration ({ws:.0f}%) creates M&A attractiveness — {link.anchor_name} may pursue vertical integration to secure supply chain, implying potential acquisition premium for {link.supplier_name}.")

    return events


def render() -> None:
    st.markdown("## 🔗 Kingmaker Intelligence — Global Supply-Chain Dependency Mapping")
    st.caption(f"{len(SUPPLY_CHAIN_REGISTRY)} verified B2B relationships · {len(ALL_SECTORS)} sectors · "
               f"Click any supplier card to reveal valuation analysis and tactical predictions")

    # ── Summary metrics ───────────────────────────────────────────────────────
    endorsed = sum(1 for l in SUPPLY_CHAIN_REGISTRY if l.endorsement_flag)
    critical = sum(1 for l in SUPPLY_CHAIN_REGISTRY if l.wallet_share_qual.startswith("Critical"))
    sole_sup = sum(1 for l in SUPPLY_CHAIN_REGISTRY if l.connection_type == "Sole_Supplier")
    sectors_n = len(ALL_SECTORS)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Links", len(SUPPLY_CHAIN_REGISTRY))
    k2.metric("Endorsed Relationships", endorsed, help="Named executive confirmation")
    k3.metric("Sole-Source Dependencies", sole_sup, help="No qualified substitute supplier")
    k4.metric("Critical Concentration (>50%)", critical, help="Supplier >50% dependent on single anchor")

    st.divider()

    # ── Sector tabs ───────────────────────────────────────────────────────────
    sector_tabs = st.tabs([f"{'💻' if s=='Technology' else '⚡' if s=='Energy' else '🛒' if s=='Consumer' else '🛡️' if s=='Defense' else '🏥' if s=='Healthcare' else '⛏️'} {s}" for s in ALL_SECTORS])

    for tab, sector in zip(sector_tabs, ALL_SECTORS):
        with tab:
            sector_links = [l for l in SUPPLY_CHAIN_REGISTRY if l.sector == sector]
            anchors = sorted(set(l.anchor_ticker for l in sector_links))

            # Anchor filter
            col_a, col_ct, col_ws = st.columns([2, 2, 2])
            with col_a:
                sel_anchors = st.multiselect("Anchor", anchors, placeholder="All anchors", key=f"anchor_{sector}")
            with col_ct:
                sel_ct = st.multiselect("Connection Type", sorted(set(l.connection_type for l in sector_links)),
                                        placeholder="All types", key=f"ct_{sector}")
            with col_ws:
                sel_endorsed = st.toggle("Endorsed only", value=False, key=f"end_{sector}")

            filtered = sector_links
            if sel_anchors:
                filtered = [l for l in filtered if l.anchor_ticker in sel_anchors]
            if sel_ct:
                filtered = [l for l in filtered if l.connection_type in sel_ct]
            if sel_endorsed:
                filtered = [l for l in filtered if l.endorsement_flag]

            st.caption(f"{len(filtered)} supply-chain links in {sector}")

            # Valuation overview chart
            if any(l.ev_ebitda_anchor and l.ev_ebitda_supplier for l in filtered):
                chart_data = [
                    {"Supplier": l.supplier_ticker,
                     "Anchor EV/EBITDA": l.ev_ebitda_anchor,
                     "Supplier EV/EBITDA": l.ev_ebitda_supplier,
                     "Discount %": round((l.ev_ebitda_supplier - l.ev_ebitda_anchor) / l.ev_ebitda_anchor * 100, 1)
                     if l.ev_ebitda_anchor else None}
                    for l in filtered
                    if l.ev_ebitda_anchor and l.ev_ebitda_supplier
                ]
                if chart_data:
                    cd_df = pd.DataFrame(chart_data).sort_values("Discount %")
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        name="Anchor EV/EBITDA",
                        x=cd_df["Supplier"], y=cd_df["Anchor EV/EBITDA"],
                        marker_color="#cbd5e1",
                    ))
                    fig.add_trace(go.Bar(
                        name="Supplier EV/EBITDA",
                        x=cd_df["Supplier"], y=cd_df["Supplier EV/EBITDA"],
                        marker_color="#00D4AA",
                        text=[f"{d:+.0f}%" if d is not None else "" for d in cd_df["Discount %"]],
                        textposition="outside",
                    ))
                    fig.update_layout(
                        barmode="group", height=220,
                        margin={"t": 20, "b": 30, "l": 0, "r": 0},
                        paper_bgcolor="#f4f6f9", plot_bgcolor="#f4f6f9",
                        legend={"orientation": "h", "y": 1.1, "font": {"color": "#888", "size": 10}},
                        xaxis={"color": "#888"}, yaxis={"color": "#888", "title": "EV/EBITDA ×"},
                        title={"text": "Valuation Delta: Anchor vs. Supplier", "font": {"color": "#888", "size": 11}},
                    )
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            for i, link in enumerate(filtered):
                _render_link_card(link, i)
