"""Thematic Sectors module — Streamlit renderer."""
from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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


# ── Cached data fetchers ──────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def _live_prices(tickers: tuple[str, ...]) -> dict:
    return fetch_prices(list(tickers))


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_holdings(ticker: str) -> list[dict]:
    """Fetch top ETF holdings via yfinance with multi-format fallback."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)

        # Method 1: funds_data.top_holdings (yfinance ≥ 0.2.37)
        try:
            fd = t.funds_data
            if fd is not None:
                th = getattr(fd, "top_holdings", None)
                if th is not None and not th.empty:
                    out = []
                    for _, row in th.reset_index().head(12).iterrows():
                        sym  = row.get("Symbol") or row.get("symbol") or row.get("Ticker") or ""
                        name = row.get("Name")   or row.get("name")   or row.get("holding") or sym
                        pct  = (
                            row.get("Holding Percent")
                            or row.get("holdingPercent")
                            or row.get("Value")
                            or 0
                        )
                        pct_f = float(pct or 0)
                        if pct_f and pct_f < 1.5:   # stored as 0.xxx fraction
                            pct_f *= 100
                        out.append({"symbol": str(sym), "name": str(name), "pct": round(pct_f, 2)})
                    return [h for h in out if h["symbol"]]
        except Exception:
            pass

        # Method 2: info dict (legacy keys)
        info = t.info or {}
        holdings = []
        for i in range(15):
            sym  = info.get(f"holdings{i}Symbol") or info.get(f"holding{i}Ticker") or ""
            name = info.get(f"holdings{i}Name")   or sym
            pct  = info.get(f"holdings{i}HoldingPercent") or 0
            if sym:
                pct_f = float(pct or 0)
                if pct_f and pct_f < 1.5:
                    pct_f *= 100
                holdings.append({"symbol": str(sym), "name": str(name), "pct": round(pct_f, 2)})
        return holdings[:12]
    except Exception:
        return []


@st.cache_data(ttl=900, show_spinner=False)
def _fetch_news(ticker: str) -> list[dict]:
    """Fetch recent news via yfinance with old+new format handling."""
    try:
        import yfinance as yf
        raw_news = yf.Ticker(ticker).news or []
        result = []
        for item in raw_news[:12]:
            if not isinstance(item, dict):
                continue
            # New yfinance wraps metadata in item["content"]
            content = item.get("content") or item
            if not isinstance(content, dict):
                content = item

            title = content.get("title") or content.get("headline") or item.get("title", "")
            if not title:
                continue

            # Link — try multiple locations
            canon = content.get("canonicalUrl") or {}
            click = content.get("clickThroughUrl") or {}
            link  = (
                (canon.get("url") if isinstance(canon, dict) else "")
                or (click.get("url") if isinstance(click, dict) else "")
                or item.get("link", "")
                or content.get("link", "")
            )

            # Publisher name
            provider = content.get("provider") or {}
            publisher = (
                (provider.get("displayName") if isinstance(provider, dict) else str(provider))
                or item.get("publisher", "")
                or content.get("publisher", "")
                or ""
            )

            # Timestamp (unix seconds)
            ts = (
                content.get("pubDate")
                or item.get("providerPublishTime")
                or content.get("publishedAt")
                or 0
            )
            if isinstance(ts, str):
                try:
                    ts = int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())
                except Exception:
                    ts = 0

            result.append({
                "title":     str(title),
                "link":      str(link),
                "publisher": str(publisher),
                "ts":        int(ts or 0),
            })
        return result
    except Exception:
        return []


# ── Detail panel renderer ─────────────────────────────────────────────────────

def _render_detail_panel(p: ThematicProduct, prices: dict, page: int) -> None:
    """Full fund deep-dive: summary → holdings → news."""
    yf_key  = p.yf_ticker or p.ticker
    px_data = prices.get(yf_key, {})
    price   = px_data.get("price")
    chg     = px_data.get("chg_pct")

    price_str = f"${price:,.2f}" if price else "—"
    chg_color = "#00D4AA" if (chg is not None and chg >= 0) else "#FF4B4B"
    chg_str   = f"{chg:+.2f}%" if chg is not None else "—"
    issuer_url = _etf_website_url(p.ticker, p.issuer, p.exchange)
    yahoo_url  = _yahoo_url(p.ticker)

    # ── Header card ───────────────────────────────────────────────────────────
    st.markdown(
        f"""<div style="background:#1A1D24;border:1px solid #2E3140;border-left:4px solid #00D4AA;
            border-radius:10px;padding:1rem 1.2rem;margin:0.4rem 0 0.6rem 0">
            <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:0.5rem">
                <div>
                    <span style="color:#00D4AA;font-size:0.68rem;font-weight:700;letter-spacing:0.12em">
                        {p.sector.upper()} · {p.sub_theme}
                    </span><br>
                    <span style="font-size:1.3rem;font-weight:700">{p.ticker}</span>
                    <span style="color:#bbb;font-size:0.87rem;margin-left:0.5rem">{p.name}</span>
                </div>
                <div style="text-align:right">
                    <div style="font-size:1.35rem;font-weight:700">{price_str}</div>
                    <div style="font-size:0.87rem;color:{chg_color}">{chg_str} today</div>
                </div>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:1.1rem;margin-top:0.6rem;font-size:0.76rem;color:#999">
                <span>🏢 <b style="color:#ddd">{p.issuer or "—"}</b></span>
                <span>🏛 <b style="color:#ddd">{p.exchange}</b></span>
                <span>🌍 <b style="color:#ddd">{p.region}</b></span>
                <span>💱 <b style="color:#ddd">{p.currency}</b></span>
                {"<span>💰 TER <b style='color:#ddd'>" + f"{p.expense_ratio:.2f}%" + "</b></span>" if p.expense_ratio else ""}
                {"<span>📦 AUM <b style='color:#ddd'>$" + f"{p.aum_bn:.1f}bn" + "</b></span>" if p.aum_bn else ""}
                {"<span>🔢 <b style='color:#ddd'>" + p.isin + "</b></span>" if p.isin else ""}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    btn1, btn2, btn3 = st.columns([2, 2, 1])
    with btn1:
        st.link_button(f"🌐 {p.issuer or 'Fund'} Website →", issuer_url, use_container_width=True)
    with btn2:
        st.link_button("📈 Yahoo Finance →", yahoo_url, use_container_width=True)
    with btn3:
        if st.button("✕ Close", key=f"desel_{p.ticker}_p{page}", use_container_width=True):
            st.session_state["thematic_selected_ticker"] = None
            st.rerun()

    # ── Holdings + News side by side ──────────────────────────────────────────
    col_h, col_n = st.columns([1, 1], gap="medium")

    # ── Holdings ──────────────────────────────────────────────────────────────
    with col_h:
        st.markdown("##### 🏦 Top Holdings")
        with st.spinner("Loading holdings…"):
            holdings = _fetch_holdings(p.ticker)

        if holdings:
            # Horizontal bar chart
            h_df = pd.DataFrame(holdings).head(10)
            fig = go.Figure(go.Bar(
                x=h_df["pct"],
                y=h_df["symbol"],
                orientation="h",
                marker_color="#00D4AA",
                text=[f"{v:.1f}%" for v in h_df["pct"]],
                textposition="outside",
                hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
            ))
            fig.update_layout(
                height=max(200, len(h_df) * 28),
                margin={"t": 10, "b": 10, "l": 0, "r": 50},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis={"visible": False},
                yaxis={"color": "#888", "tickfont": {"size": 11}, "autorange": "reversed"},
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            # Name + weight table beneath chart
            for h in holdings[:10]:
                pct_bar = min(int(h["pct"] / max(holdings[0]["pct"], 1) * 100), 100)
                st.markdown(
                    f"""<div style="display:flex;align-items:center;gap:0.5rem;
                        margin-bottom:0.2rem;font-size:0.76rem">
                        <span style="font-weight:700;min-width:52px;color:#ddd">{h["symbol"]}</span>
                        <div style="flex:1;background:#2E3140;border-radius:3px;height:6px">
                            <div style="width:{pct_bar}%;background:#00D4AA;border-radius:3px;height:6px"></div>
                        </div>
                        <span style="color:#00D4AA;min-width:38px;text-align:right">{h["pct"]:.1f}%</span>
                        <span style="color:#666;font-size:0.68rem;max-width:120px;overflow:hidden;
                            text-overflow:ellipsis;white-space:nowrap">{h["name"]}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Holdings data unavailable for this instrument.")

    # ── News ──────────────────────────────────────────────────────────────────
    with col_n:
        st.markdown("##### 📰 Recent News & Market Impact")
        with st.spinner("Loading news…"):
            news = _fetch_news(p.ticker)

        if news:
            for article in news:
                title     = article["title"]
                link      = article["link"]
                publisher = article["publisher"]
                ts        = article["ts"]

                # Relative time label
                if ts:
                    age_h = (time.time() - ts) / 3600
                    if age_h < 1:
                        time_label = f"{int(age_h * 60)}m ago"
                    elif age_h < 24:
                        time_label = f"{int(age_h)}h ago"
                    else:
                        time_label = f"{int(age_h / 24)}d ago"
                else:
                    time_label = ""

                title_html = (
                    f'<a href="{link}" target="_blank" rel="noopener noreferrer" '
                    f'style="color:#ddd;text-decoration:none;font-weight:600;'
                    f'border-bottom:1px dotted #555;line-height:1.4">{title}</a>'
                ) if link else f'<span style="color:#ddd;font-weight:600">{title}</span>'

                st.markdown(
                    f"""<div style="background:#14161E;border:1px solid #2E3140;border-left:3px solid #FFA500;
                        border-radius:6px;padding:0.55rem 0.75rem;margin-bottom:0.4rem">
                        <div style="font-size:0.79rem;line-height:1.4">{title_html}</div>
                        <div style="display:flex;gap:0.6rem;margin-top:0.3rem;font-size:0.68rem;color:#666">
                            <span>{publisher}</span>
                            {"<span>·</span><span>" + time_label + "</span>" if time_label else ""}
                            {"<span>·</span><a href='" + link + "' target='_blank' rel='noopener noreferrer' style='color:#00D4AA;text-decoration:none'>↗ Read</a>" if link else ""}
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No recent news available for this ticker.")


# ── Main render ───────────────────────────────────────────────────────────────

def render() -> None:
    st.markdown("## 📊 Thematic Sectors — Global Sector & Thematic ETF Grid")
    st.caption(
        f"{len(THEMATIC_REGISTRY)} products across {len(ALL_SECTORS)} sectors "
        f"and {len(ALL_SUB_THEMES)} sub-themes — "
        "**click a tile** to filter · **click again to clear** · **click a row** to explore"
    )

    # ── Session state init ────────────────────────────────────────────────────
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

    treemap_df = pd.DataFrame([
        {"Sector": sector, "Sub-Theme": theme, "Count": cnt}
        for sector, themes in theme_counts.items()
        for theme, cnt in themes.items()
    ])

    # Highlight the active selection in the treemap via a custom color column
    treemap_sel = st.session_state["thematic_treemap_sel"]
    treemap_df["Active"] = treemap_df.apply(
        lambda r: (
            2 if (treemap_sel["sub_theme"] and r["Sub-Theme"] == treemap_sel["sub_theme"] and r["Sector"] == treemap_sel["sector"])
            else 1 if (treemap_sel["sector"] and r["Sector"] == treemap_sel["sector"] and not treemap_sel["sub_theme"])
            else 0
        ),
        axis=1,
    )

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
        hovertemplate="<b>%{label}</b><br>%{value} instruments — click to filter<extra></extra>",
    )

    treemap_event = st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False},
        on_select="rerun",
        key="thematic_treemap",
    )

    # ── Process treemap click: toggle / replace / clear ───────────────────────
    prev_sel = dict(st.session_state["thematic_treemap_sel"])   # snapshot before mutation

    if treemap_event and treemap_event.selection and treemap_event.selection.get("points"):
        pt     = treemap_event.selection["points"][0]
        label  = pt.get("label", "")
        parent = pt.get("parent", "")

        if not label:
            # Click on the empty root → clear everything
            new_sel = {"sector": None, "sub_theme": None}
        elif parent in ("", None):
            if label in ALL_SECTORS:
                # Sector tile clicked
                new_sel = {"sector": label, "sub_theme": None}
                if prev_sel == new_sel:
                    new_sel = {"sector": None, "sub_theme": None}   # toggle off
            else:
                # Clicked invisible root label — clear
                new_sel = {"sector": None, "sub_theme": None}
        elif parent in ALL_SECTORS:
            # Sub-theme tile clicked
            new_sel = {"sector": parent, "sub_theme": label}
            if prev_sel == new_sel:
                # Toggle off → step back up to sector level
                new_sel = {"sector": parent, "sub_theme": None}
        else:
            new_sel = prev_sel  # unknown shape — leave unchanged

        if new_sel != prev_sel:
            st.session_state["thematic_treemap_sel"] = new_sel
            st.session_state["thematic_page"] = 0
            st.session_state["thematic_selected_ticker"] = None
            st.rerun()

    elif treemap_event and treemap_event.selection and not treemap_event.selection.get("points"):
        # Explicit deselect (click on empty canvas area) → clear
        if prev_sel != {"sector": None, "sub_theme": None}:
            st.session_state["thematic_treemap_sel"] = {"sector": None, "sub_theme": None}
            st.session_state["thematic_page"] = 0
            st.session_state["thematic_selected_ticker"] = None
            st.rerun()

    # Re-read after potential mutation
    treemap_sel = st.session_state["thematic_treemap_sel"]

    # Active filter banner
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
                    padding:0.4rem 0.9rem;font-size:0.81rem;margin-top:0.25rem">
                    🗂 <b style="color:#00D4AA">Treemap filter active:</b>
                    <span style="color:#ddd;margin-left:0.4rem">{crumb}</span>
                    <span style="color:#666;font-size:0.7rem;margin-left:0.5rem">
                        — click the same tile again to clear
                    </span>
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
            "Sector", ALL_SECTORS, default=default_sectors,
            placeholder="All sectors", key="th_sectors",
        )
    with col_t:
        default_themes = [treemap_sel["sub_theme"]] if treemap_sel["sub_theme"] else []
        sel_themes = st.multiselect(
            "Sub-Theme", ALL_SUB_THEMES, default=default_themes,
            placeholder="All themes", key="th_themes",
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

    # Build filtered list (treemap selection applied when multiselects are empty)
    filtered = list(THEMATIC_REGISTRY)
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
        f"**{len(filtered)}** products — "
        "select a row to view holdings, news and fund website links"
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

    # ── Selectable instrument table ───────────────────────────────────────────
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
            "1d %":      st.column_config.TextColumn("1d %"),
            "AUM ($bn)": st.column_config.TextColumn("AUM ($bn)"),
        },
    )

    # Update selected ticker from table click
    sel_rows = (
        table_event.selection.rows
        if table_event and table_event.selection
        else []
    )
    if sel_rows and 0 <= sel_rows[0] < len(page_items):
        new_ticker = page_items[sel_rows[0]].ticker
        if st.session_state["thematic_selected_ticker"] != new_ticker:
            st.session_state["thematic_selected_ticker"] = new_ticker

    # Resolve selected ticker back to a product on the current page
    sel_ticker = st.session_state.get("thematic_selected_ticker")
    selected_product = next(
        (p for p in page_items if p.ticker == sel_ticker), None
    ) if sel_ticker else None

    if selected_product:
        st.markdown("---")
        st.markdown(f"#### 🔍 {selected_product.ticker} — Fund Intelligence")
        _render_detail_panel(selected_product, prices, page)
