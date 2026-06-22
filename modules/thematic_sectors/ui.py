"""Thematic Sectors module — Streamlit renderer."""
from __future__ import annotations

from typing import Optional

import streamlit as st
import pandas as pd
import plotly.express as px

from .data import THEMATIC_REGISTRY, ThematicProduct, ALL_SECTORS, ALL_SUB_THEMES, fetch_prices

_PAGE_SIZE = 25

# ── ETF website URL resolver ──────────────────────────────────────────────────

_ISSUER_URL_MAP = {
    "blackrock":       lambda t: f"https://www.ishares.com/us/products/etf-investments#{t}",
    "ishares":         lambda t: f"https://www.ishares.com/us/products/etf-investments#{t}",
    "vanguard":        lambda t: f"https://investor.vanguard.com/investment-products/etfs/profile/{t.lower()}",
    "state street":    lambda t: f"https://www.ssga.com/us/en/intermediary/etfs/fund-finder?ticker={t}",
    "spdr":            lambda t: f"https://www.ssga.com/us/en/intermediary/etfs/fund-finder?ticker={t}",
    "invesco":         lambda t: f"https://www.invesco.com/us/financial-products/etfs/product-detail?audienceType=Investor&ticker={t}",
    "ark":             lambda t: f"https://ark-funds.com/funds/{t.lower()}/",
    "vaneck":          lambda t: f"https://www.vaneck.com/us/en/{t.lower()}/",
    "wisdomtree":      lambda t: f"https://www.wisdomtree.com/investments/etfs/{t.lower()}",
    "global x":        lambda t: f"https://www.globalxetfs.com/funds/{t.lower()}/",
    "proshares":       lambda t: f"https://www.proshares.com/our-etfs/{t.lower()}/",
    "direxion":        lambda t: f"https://www.direxion.com/products/{t.lower()}/",
    "first trust":     lambda t: f"https://www.ftportfolios.com/Retail/Etf/EtfSummary.aspx?Ticker={t}",
    "sprott":          lambda t: f"https://sprott.com/investment-strategies/etfs/{t.lower()}/",
    "amplify":         lambda t: f"https://amplifyetfs.com/funds/{t.lower()}/",
    "defiance":        lambda t: f"https://defianceetfs.com/{t.lower()}/",
    "kraneshares":     lambda t: f"https://kraneshares.com/etfs/{t.lower()}/",
    "hanetf":          lambda t: f"https://www.hanetf.com/products/{t.lower()}",
    "legal & general": lambda t: f"https://www.lgim.com/uk/en/capabilities/etfs/",
    "roundhill":       lambda t: f"https://www.roundhillinvestments.com/etf/{t.lower()}/",
    "us global":       lambda t: f"https://www.usglobaletfs.com/{t.lower()}/",
    "pacer":           lambda t: f"https://www.paceretfs.com/products/{t.lower()}",
    "strive":          lambda t: f"https://striveassetmanagement.com/products/{t.lower()}/",
    "strategy shares": lambda t: f"https://strategysharesetfs.com/etfs/{t.lower()}/",
    "alerian":         lambda t: "https://www.mlpassociation.com/amlp/",
    "robo global":     lambda t: f"https://www.roboglobal.com/funds/{t.lower()}",
    "teucrium":        lambda t: f"https://teucriumfunds.com/{t.lower()}/",
    "etfmg":           lambda t: f"https://www.etfmg.com/{t.lower()}/",
    "fidelity":        lambda t: f"https://fundresearch.fidelity.com/mutual-funds/summary/{t}",
}


def _etf_website_url(ticker: str, issuer: Optional[str], exchange: str) -> str:
    t_clean = ticker.replace(".L", "").replace(".DE", "").replace(".PA", "").upper()
    if issuer:
        for key, builder in _ISSUER_URL_MAP.items():
            if key in issuer.lower():
                return builder(t_clean)
    return f"https://finance.yahoo.com/quote/{ticker}"


def _yahoo_url(ticker: str) -> str:
    return f"https://finance.yahoo.com/quote/{ticker}"


# ── Price cache ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def _live_prices(tickers: tuple[str, ...]) -> dict:
    return fetch_prices(list(tickers))


# ── Detail panel ──────────────────────────────────────────────────────────────

def _render_detail_panel(p: ThematicProduct, prices: dict, page: int) -> None:
    yf_key  = p.yf_ticker or p.ticker
    px_data = prices.get(yf_key, {})
    price   = px_data.get("price")
    chg     = px_data.get("chg_pct")

    price_str = f"${price:,.2f}" if price else "—"
    chg_color = "#00D4AA" if (chg is not None and chg >= 0) else "#FF4B4B"
    chg_str   = f"{chg:+.2f}%" if chg is not None else "—"

    issuer_url = _etf_website_url(p.ticker, p.issuer, p.exchange)
    yahoo_url  = _yahoo_url(p.ticker)

    st.markdown(
        f"""<div style="background:#1A1D24;border:1px solid #2E3140;border-left:4px solid #00D4AA;
            border-radius:10px;padding:1rem 1.2rem;margin:0.5rem 0 0.75rem 0">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:0.5rem">
                <div>
                    <span style="color:#00D4AA;font-size:0.7rem;font-weight:700;letter-spacing:0.1em">
                        {p.sector.upper()} · {p.sub_theme}
                    </span><br>
                    <span style="font-size:1.25rem;font-weight:700">{p.ticker}</span>
                    <span style="color:#aaa;font-size:0.88rem;margin-left:0.5rem">{p.name}</span>
                </div>
                <div style="text-align:right">
                    <div style="font-size:1.3rem;font-weight:700">{price_str}</div>
                    <div style="font-size:0.88rem;color:{chg_color}">{chg_str} today</div>
                </div>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:1.2rem;margin-top:0.65rem;font-size:0.78rem;color:#aaa">
                <span>🏢 Issuer: <b style="color:#ddd">{p.issuer or "—"}</b></span>
                <span>🏛 Exchange: <b style="color:#ddd">{p.exchange}</b></span>
                <span>🌍 Region: <b style="color:#ddd">{p.region}</b></span>
                <span>💱 Currency: <b style="color:#ddd">{p.currency}</b></span>
                {"<span>💰 TER: <b style='color:#ddd'>" + f"{p.expense_ratio:.2f}%" + "</b></span>" if p.expense_ratio else ""}
                {"<span>📦 AUM: <b style='color:#ddd'>$" + f"{p.aum_bn:.1f}bn" + "</b></span>" if p.aum_bn else ""}
                {"<span>🔢 ISIN: <b style='color:#ddd'>" + p.isin + "</b></span>" if p.isin else ""}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    btn1, btn2, btn3 = st.columns([2, 2, 1])
    with btn1:
        st.link_button(
            f"🌐 {p.issuer or 'Fund'} Website →",
            issuer_url,
            use_container_width=True,
        )
    with btn2:
        st.link_button(
            "📈 Yahoo Finance →",
            yahoo_url,
            use_container_width=True,
        )
    with btn3:
        if st.button("✕ Deselect", key=f"desel_{p.ticker}_p{page}", use_container_width=True):
            st.session_state["thematic_selected_ticker"] = None
            st.rerun()


# ── Main render ───────────────────────────────────────────────────────────────

def render() -> None:
    st.markdown("## 📊 Thematic Sectors — Global Sector & Thematic ETF Grid")
    st.caption(
        f"{len(THEMATIC_REGISTRY)} products across {len(ALL_SECTORS)} sectors "
        f"and {len(ALL_SUB_THEMES)} sub-themes — "
        "**click a tile** to filter · **click a row** to explore"
    )

    # ── Session state initialisation ──────────────────────────────────────────
    if "thematic_treemap_sel" not in st.session_state:
        st.session_state["thematic_treemap_sel"] = {"sector": None, "sub_theme": None}
    if "thematic_selected_ticker" not in st.session_state:
        st.session_state["thematic_selected_ticker"] = None
    if "thematic_page" not in st.session_state:
        st.session_state["thematic_page"] = 0

    # ── Treemap ───────────────────────────────────────────────────────────────
    theme_counts: dict[str, dict] = {}
    for p in THEMATIC_REGISTRY:
        theme_counts.setdefault(p.sector, {})
        theme_counts[p.sector][p.sub_theme] = theme_counts[p.sector].get(p.sub_theme, 0) + 1

    treemap_rows = [
        {"Sector": sector, "Sub-Theme": theme, "Count": cnt}
        for sector, themes in theme_counts.items()
        for theme, cnt in themes.items()
    ]
    treemap_df = pd.DataFrame(treemap_rows)

    fig = px.treemap(
        treemap_df, path=["Sector", "Sub-Theme"], values="Count",
        color="Count",
        color_continuous_scale=[[0, "#1A2A3A"], [0.5, "#00896B"], [1, "#00D4AA"]],
        template="plotly_dark",
    )
    fig.update_layout(
        height=380, margin={"t": 10, "b": 10, "l": 0, "r": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False,
    )
    fig.update_traces(
        marker={"line": {"width": 0.5, "color": "#0E1117"}},
        hovertemplate="<b>%{label}</b><br>%{value} instruments<extra></extra>",
    )

    treemap_event = st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False},
        on_select="rerun",
        key="thematic_treemap",
    )

    # Process treemap click
    if (
        treemap_event
        and treemap_event.selection
        and treemap_event.selection.get("points")
    ):
        pt     = treemap_event.selection["points"][0]
        label  = pt.get("label", "")
        parent = pt.get("parent", "")
        if label:
            if parent in ("", None) and label in ALL_SECTORS:
                # Sector tile clicked
                st.session_state["thematic_treemap_sel"] = {"sector": label, "sub_theme": None}
                st.session_state["thematic_page"] = 0
                st.session_state["thematic_selected_ticker"] = None
            elif parent in ALL_SECTORS:
                # Sub-theme tile clicked
                st.session_state["thematic_treemap_sel"] = {"sector": parent, "sub_theme": label}
                st.session_state["thematic_page"] = 0
                st.session_state["thematic_selected_ticker"] = None

    treemap_sel = st.session_state["thematic_treemap_sel"]

    # Active treemap filter banner
    if treemap_sel["sector"]:
        crumb = (
            f"{treemap_sel['sector']} › {treemap_sel['sub_theme']}"
            if treemap_sel["sub_theme"]
            else treemap_sel["sector"]
        )
        col_banner, col_clear = st.columns([6, 1])
        with col_banner:
            st.markdown(
                f"""<div style="background:#1a3d2e;border:1px solid #00D4AA;border-radius:6px;
                    padding:0.4rem 0.9rem;font-size:0.82rem;margin-top:0.3rem">
                    🗂 <b style="color:#00D4AA">Treemap filter:</b>
                    <span style="color:#ddd;margin-left:0.4rem">{crumb}</span>
                </div>""",
                unsafe_allow_html=True,
            )
        with col_clear:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✕ Clear", key="clear_treemap"):
                st.session_state["thematic_treemap_sel"] = {"sector": None, "sub_theme": None}
                st.session_state["thematic_page"] = 0
                st.session_state["thematic_selected_ticker"] = None
                st.rerun()

    st.divider()

    # ── Manual dropdown filters ───────────────────────────────────────────────
    col_s, col_t, col_r, col_ex = st.columns(4)
    with col_s:
        default_sectors = [treemap_sel["sector"]] if treemap_sel["sector"] else []
        sel_sectors = st.multiselect(
            "Sector", ALL_SECTORS,
            default=default_sectors, placeholder="All sectors", key="th_sectors",
        )
    with col_t:
        default_themes = [treemap_sel["sub_theme"]] if treemap_sel["sub_theme"] else []
        sel_themes = st.multiselect(
            "Sub-Theme", ALL_SUB_THEMES,
            default=default_themes, placeholder="All themes", key="th_themes",
        )
    with col_r:
        sel_regions = st.multiselect(
            "Region", sorted(set(p.region for p in THEMATIC_REGISTRY)),
            placeholder="All regions", key="th_regions",
        )
    with col_ex:
        sel_exchange = st.multiselect(
            "Exchange", sorted(set(p.exchange for p in THEMATIC_REGISTRY)),
            placeholder="All exchanges", key="th_exchange",
        )

    # Build filtered list
    filtered = list(THEMATIC_REGISTRY)

    # Apply treemap selection first (multiselects override if used)
    if not sel_sectors and treemap_sel["sector"]:
        filtered = [p for p in filtered if p.sector == treemap_sel["sector"]]
    if not sel_themes and treemap_sel["sub_theme"]:
        filtered = [p for p in filtered if p.sub_theme == treemap_sel["sub_theme"]]

    if sel_sectors:
        filtered = [p for p in filtered if p.sector in sel_sectors]
    if sel_themes:
        filtered = [p for p in filtered if p.sub_theme in sel_themes]
    if sel_regions:
        filtered = [p for p in filtered if p.region in sel_regions]
    if sel_exchange:
        filtered = [p for p in filtered if p.exchange in sel_exchange]

    st.caption(
        f"**{len(filtered)}** products shown — "
        "click a row to open fund details and website links"
    )

    # ── Pagination ────────────────────────────────────────────────────────────
    total_pages = max(1, (len(filtered) + _PAGE_SIZE - 1) // _PAGE_SIZE)
    page = max(0, min(st.session_state["thematic_page"], total_pages - 1))

    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        if st.button("← Prev", key="th_prev", disabled=page == 0):
            st.session_state["thematic_page"] = page - 1
            st.session_state["thematic_selected_ticker"] = None
            st.rerun()
    with c2:
        st.caption(f"Page {page + 1} / {total_pages}")
    with c3:
        if st.button("Next →", key="th_next", disabled=page >= total_pages - 1):
            st.session_state["thematic_page"] = page + 1
            st.session_state["thematic_selected_ticker"] = None
            st.rerun()

    page_items = filtered[page * _PAGE_SIZE : (page + 1) * _PAGE_SIZE]

    # ── Live prices ───────────────────────────────────────────────────────────
    tickers_yf = tuple(
        p.yf_ticker or p.ticker
        for p in page_items
        if not p.ticker.endswith(".DE") and not p.ticker.endswith(".PA")
    )
    prices = _live_prices(tickers_yf) if tickers_yf else {}

    # ── Table with selectable rows ────────────────────────────────────────────
    rows = []
    for p in page_items:
        yf_key = p.yf_ticker or p.ticker
        px_d   = prices.get(yf_key, {})
        price  = px_d.get("price")
        chg    = px_d.get("chg_pct")
        rows.append({
            "Ticker":    p.ticker,
            "Name":      p.name,
            "Sector":    p.sector,
            "Sub-Theme": p.sub_theme,
            "Region":    p.region,
            "Exchange":  p.exchange,
            "TER":       f"{p.expense_ratio:.2f}%" if p.expense_ratio else "—",
            "AUM ($bn)": f"{p.aum_bn:.1f}" if p.aum_bn else "—",
            "Issuer":    p.issuer or "—",
            "Price":     f"${price:,.2f}" if price else "—",
            "1d %":      f"{chg:+.2f}%" if chg is not None else "—",
        })

    df = pd.DataFrame(rows)

    table_event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"thematic_tbl_p{page}",
        column_config={
            "1d %": st.column_config.TextColumn("1d %"),
            "AUM ($bn)": st.column_config.TextColumn("AUM ($bn)"),
        },
    )

    # Handle row selection
    sel_rows = (
        table_event.selection.rows
        if table_event and table_event.selection
        else []
    )
    if sel_rows:
        selected_p = page_items[sel_rows[0]]
        st.session_state["thematic_selected_ticker"] = selected_p.ticker

    # Resolve selected ticker back to product on page
    sel_ticker = st.session_state.get("thematic_selected_ticker")
    selected_product = next(
        (p for p in page_items if p.ticker == sel_ticker), None
    ) if sel_ticker else None

    if selected_product:
        st.markdown("#### 🔍 Instrument Details")
        _render_detail_panel(selected_product, prices, page)
