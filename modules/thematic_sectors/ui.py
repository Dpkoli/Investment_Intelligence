"""Thematic Sectors module — Streamlit renderer."""
from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor
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


def _safe_num(v) -> Optional[float]:
    """Return float or None, converting NaN to None."""
    try:
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    except Exception:
        return None


# ── Cached data fetchers ──────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def _live_prices(tickers: tuple[str, ...]) -> dict:
    return fetch_prices(list(tickers))


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_holdings(ticker: str) -> list[dict]:
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        # Primary: funds_data.top_holdings (yfinance ≥ 0.2.37)
        try:
            fd = t.funds_data
            if fd is not None:
                th = getattr(fd, "top_holdings", None)
                if th is not None and not th.empty:
                    out = []
                    for _, row in th.reset_index().head(12).iterrows():
                        sym  = str(row.get("Symbol") or row.get("symbol") or row.get("Ticker") or "").strip()
                        name = str(row.get("Name") or row.get("name") or row.get("holding") or sym).strip()
                        raw  = row.get("Holding Percent") or row.get("holdingPercent") or row.get("Value") or 0
                        pct  = _safe_num(raw) or 0.0
                        if pct and pct < 1.5:   # stored as 0.0x fraction
                            pct *= 100
                        if sym:
                            out.append({"symbol": sym, "name": name, "pct": round(pct, 2)})
                    if out:
                        return out
        except Exception:
            pass
        # Fallback: info dict
        info = t.info or {}
        holdings = []
        for i in range(15):
            sym  = str(info.get(f"holdings{i}Symbol") or "").strip()
            name = str(info.get(f"holdings{i}Name") or sym).strip()
            raw  = info.get(f"holdings{i}HoldingPercent") or 0
            pct  = (_safe_num(raw) or 0.0)
            if pct and pct < 1.5:
                pct *= 100
            if sym:
                holdings.append({"symbol": sym, "name": name, "pct": round(pct, 2)})
        return holdings[:12]
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_performance(ticker: str) -> dict:
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period="1y", auto_adjust=True)
        if hist.empty or "Close" not in hist.columns:
            return {}
        closes = hist["Close"].dropna()
        if len(closes) < 5:
            return {}
        current = _safe_num(closes.iloc[-1])
        if current is None:
            return {}

        def _ret(n_days: int) -> Optional[float]:
            if len(closes) < n_days:
                return None
            past = _safe_num(closes.iloc[-n_days])
            if past and past != 0:
                return round((current - past) / past * 100, 2)
            return None

        # YTD: first trading day of current year
        cur_year = closes.index[-1].year
        ytd_series = closes[closes.index.year == cur_year]
        ytd: Optional[float] = None
        if not ytd_series.empty:
            start = _safe_num(ytd_series.iloc[0])
            if start and start != 0:
                ytd = round((current - start) / start * 100, 2)

        return {
            "dates":  [d.strftime("%Y-%m-%d") for d in closes.index],
            "prices": [_safe_num(v) for v in closes.values],
            "1M":  _ret(21),
            "3M":  _ret(63),
            "6M":  _ret(126),
            "YTD": ytd,
            "1Y":  _ret(252),
        }
    except Exception:
        return {}


@st.cache_data(ttl=900, show_spinner=False)
def _fetch_news(ticker: str) -> list[dict]:
    try:
        import yfinance as yf
        raw_news = yf.Ticker(ticker).news or []
        result = []
        for item in raw_news[:12]:
            if not isinstance(item, dict):
                continue
            content = item.get("content") or item
            if not isinstance(content, dict):
                content = item

            title = str(
                content.get("title") or content.get("headline") or item.get("title", "")
            ).strip()
            if not title:
                continue

            canon = content.get("canonicalUrl") or {}
            click = content.get("clickThroughUrl") or {}
            link  = (
                (canon.get("url") if isinstance(canon, dict) else "")
                or (click.get("url") if isinstance(click, dict) else "")
                or item.get("link", "")
                or content.get("link", "")
            )
            link = str(link).strip()

            provider = content.get("provider") or {}
            publisher = (
                (provider.get("displayName") if isinstance(provider, dict) else str(provider or ""))
                or item.get("publisher", "")
                or content.get("publisher", "")
            )
            publisher = str(publisher or "").strip()

            ts_raw = content.get("pubDate") or item.get("providerPublishTime") or 0
            ts: int = 0
            if isinstance(ts_raw, str):
                try:
                    ts = int(datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).timestamp())
                except Exception:
                    ts = 0
            else:
                ts = int(ts_raw or 0)

            result.append({"title": title, "link": link, "publisher": publisher, "ts": ts})
        return result
    except Exception:
        return []


# ── Detail panel ──────────────────────────────────────────────────────────────

def _render_detail_panel(p: ThematicProduct, prices: dict, page: int) -> None:
    """Fund deep-dive: header → holdings → performance → news → action buttons."""
    yf_key  = p.yf_ticker or p.ticker
    px_data = prices.get(yf_key, {})
    price   = _safe_num(px_data.get("price"))
    chg     = _safe_num(px_data.get("chg_pct"))

    price_str = f"${price:,.2f}" if price else "—"
    chg_color = "#00D4AA" if (chg is not None and chg >= 0) else "#FF4B4B"
    chg_str   = f"{chg:+.2f}%" if chg is not None else "—"

    issuer_url = _etf_website_url(p.ticker, p.issuer, p.exchange)
    yahoo_url  = _yahoo_url(p.ticker)

    # Pre-build optional metadata spans to avoid f-string conditional bugs
    ter_span  = f'<span>💰 TER&nbsp;<b style="color:#ddd">{p.expense_ratio:.2f}%</b></span>' if p.expense_ratio else ""
    aum_span  = f'<span>📦 AUM&nbsp;<b style="color:#ddd">${p.aum_bn:.1f}bn</b></span>'        if p.aum_bn        else ""
    isin_span = f'<span>🔢&nbsp;<b style="color:#ddd">{p.isin}</b></span>'                       if p.isin          else ""

    # ── 1. Header ─────────────────────────────────────────────────────────────
    st.markdown(
        f"""
<div style="background:#1A1D24;border:1px solid #2E3140;border-left:4px solid #00D4AA;
     border-radius:10px;padding:1rem 1.2rem;margin:0.4rem 0 0.75rem 0">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;
       flex-wrap:wrap;gap:0.5rem">
    <div>
      <span style="color:#00D4AA;font-size:0.68rem;font-weight:700;
            letter-spacing:0.12em">{p.sector.upper()} &middot; {p.sub_theme}</span><br>
      <span style="font-size:1.25rem;font-weight:700">{p.ticker}</span>&nbsp;
      <span style="color:#bbb;font-size:0.87rem">{p.name}</span>
    </div>
    <div style="text-align:right">
      <div style="font-size:1.3rem;font-weight:700">{price_str}</div>
      <div style="font-size:0.87rem;color:{chg_color}">{chg_str} today</div>
    </div>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:1rem;margin-top:0.6rem;
       font-size:0.75rem;color:#999">
    <span>🏢&nbsp;<b style="color:#ddd">{p.issuer or "—"}</b></span>
    <span>🏛&nbsp;<b style="color:#ddd">{p.exchange}</b></span>
    <span>🌍&nbsp;<b style="color:#ddd">{p.region}</b></span>
    <span>💱&nbsp;<b style="color:#ddd">{p.currency}</b></span>
    {ter_span}
    {aum_span}
    {isin_span}
  </div>
</div>""",
        unsafe_allow_html=True,
    )

    # ── 2. Holdings  ‖  Performance ──────────────────────────────────────────
    # Fetch all three data sources in parallel to minimise wall-clock latency
    with ThreadPoolExecutor(max_workers=3) as _pool:
        _fh = _pool.submit(_fetch_holdings, p.ticker)
        _fp = _pool.submit(_fetch_performance, p.ticker)
        _fn = _pool.submit(_fetch_news, p.ticker)
        holdings = _fh.result()
        perf     = _fp.result()
        news     = _fn.result()

    col_h, col_p = st.columns([1, 1], gap="medium")

    with col_h:
        st.markdown("##### 🏦 Top Holdings")
        if holdings:
            h_df = pd.DataFrame(holdings).head(10)
            fig_h = go.Figure(go.Bar(
                x=h_df["pct"],
                y=h_df["symbol"],
                orientation="h",
                marker_color="#00D4AA",
                text=[f"{v:.1f}%" for v in h_df["pct"]],
                textposition="outside",
                hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
            ))
            fig_h.update_layout(
                height=max(180, len(h_df) * 28),
                margin={"t": 5, "b": 5, "l": 10, "r": 55},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis={"visible": False},
                yaxis={
                    "color": "#888", "tickfont": {"size": 11},
                    "autorange": "reversed",
                },
                showlegend=False,
            )
            st.plotly_chart(fig_h, use_container_width=True,
                            config={"displayModeBar": False})
        else:
            st.caption("Holdings data not available for this instrument.")

    with col_p:
        st.markdown("##### 📈 Performance")
        if perf and perf.get("dates"):
            # Sparkline price chart
            fig_p = go.Figure(go.Scatter(
                x=perf["dates"],
                y=perf["prices"],
                mode="lines",
                line={"color": "#00D4AA", "width": 1.8},
                fill="tozeroy",
                fillcolor="rgba(0,212,170,0.07)",
                hovertemplate="%{x}<br>$%{y:,.2f}<extra></extra>",
            ))
            fig_p.update_layout(
                height=160,
                margin={"t": 5, "b": 5, "l": 0, "r": 0},
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis={"visible": False},
                yaxis={"color": "#666", "gridcolor": "#2E3140",
                       "tickformat": "$,.0f"},
                showlegend=False,
            )
            st.plotly_chart(fig_p, use_container_width=True,
                            config={"displayModeBar": False})

            # Return metrics row
            periods = [("1M", perf.get("1M")), ("3M", perf.get("3M")),
                       ("6M", perf.get("6M")), ("YTD", perf.get("YTD")),
                       ("1Y", perf.get("1Y"))]
            cells = ""
            for label, val in periods:
                if val is not None:
                    color = "#00D4AA" if val >= 0 else "#FF4B4B"
                    val_str = f"{val:+.1f}%"
                else:
                    color = "#666"
                    val_str = "—"
                cells += (
                    f'<div style="text-align:center;flex:1">'
                    f'<div style="font-size:0.65rem;color:#888">{label}</div>'
                    f'<div style="font-size:0.82rem;font-weight:700;color:{color}">{val_str}</div>'
                    f'</div>'
                )
            st.markdown(
                f'<div style="display:flex;gap:0.3rem;margin-top:0.3rem">{cells}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("Performance data not available.")

    # ── 3. News ───────────────────────────────────────────────────────────────
    st.markdown("##### 📰 Recent News & Market Impact")
    if news:
        for article in news:
            title     = article["title"]
            link      = article["link"]
            publisher = article["publisher"]
            ts        = article["ts"]

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

            # Build headline HTML — link if URL exists, plain text otherwise
            if link and link.startswith("http"):
                headline_html = (
                    f'<a href="{link}" target="_blank" rel="noopener noreferrer" '
                    f'style="color:#ddd;text-decoration:none;font-weight:600;'
                    f'border-bottom:1px dotted #555;line-height:1.45">{title}</a>'
                )
                read_link = (
                    f'<span style="color:#555">&middot;</span>'
                    f'<a href="{link}" target="_blank" rel="noopener noreferrer" '
                    f'style="color:#00D4AA;text-decoration:none;font-size:0.68rem">'
                    f'&nearr; Read</a>'
                )
            else:
                headline_html = f'<span style="color:#ddd;font-weight:600">{title}</span>'
                read_link = ""

            time_html = (
                f'<span style="color:#555">&middot;</span>'
                f'<span>{time_label}</span>'
            ) if time_label else ""

            st.markdown(
                f"""
<div style="background:#14161E;border:1px solid #2E3140;border-left:3px solid #FFA500;
     border-radius:6px;padding:0.55rem 0.8rem;margin-bottom:0.4rem">
  <div style="font-size:0.79rem;line-height:1.45">{headline_html}</div>
  <div style="display:flex;gap:0.4rem;align-items:center;
       margin-top:0.28rem;font-size:0.68rem;color:#666">
    <span>{publisher}</span>
    {time_html}
    {read_link}
  </div>
</div>""",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No recent news available.")

    # ── 4. Action buttons (bottom) ────────────────────────────────────────────
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
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
        if st.button("✕ Close", key=f"desel_{p.ticker}_p{page}",
                     use_container_width=True):
            st.session_state["thematic_selected_ticker"] = None
            st.rerun()


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

    # ── Build treemap ─────────────────────────────────────────────────────────
    theme_counts: dict[str, dict] = {}
    for p in THEMATIC_REGISTRY:
        theme_counts.setdefault(p.sector, {})
        theme_counts[p.sector][p.sub_theme] = theme_counts[p.sector].get(p.sub_theme, 0) + 1

    # Build parallel arrays; customdata=[sector, sub_theme|""] for 100%-reliable event parsing
    tm_labels, tm_parents, tm_values, tm_ids, tm_custom = [], [], [], [], []
    for sector, themes in theme_counts.items():
        tm_labels.append(sector)
        tm_parents.append("")
        tm_values.append(sum(themes.values()))
        tm_ids.append(sector)
        tm_custom.append([sector, ""])
        for theme, cnt in themes.items():
            tm_labels.append(theme)
            tm_parents.append(sector)
            tm_values.append(cnt)
            tm_ids.append(f"{sector}/{theme}")
            tm_custom.append([sector, theme])

    fig = go.Figure(go.Treemap(
        ids=tm_ids,
        labels=tm_labels,
        parents=tm_parents,
        values=tm_values,
        customdata=tm_custom,
        branchvalues="total",
        hovertemplate="<b>%{label}</b><br>%{value} instruments — click to filter<extra></extra>",
        marker=dict(
            colorscale=[[0, "#1A2A3A"], [0.5, "#00896B"], [1, "#00D4AA"]],
            showscale=False,
            line=dict(width=0.5, color="#0E1117"),
        ),
        pathbar=dict(visible=True, thickness=18),
        textfont=dict(size=12),
    ))
    fig.update_layout(
        height=380, margin={"t": 10, "b": 10, "l": 0, "r": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#ddd"},
    )

    treemap_event = st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False},
        on_select="rerun",
        key="thematic_treemap",
    )

    # ── Process treemap click ─────────────────────────────────────────────────
    prev_sel = dict(st.session_state["thematic_treemap_sel"])
    new_sel  = None

    if treemap_event and treemap_event.selection:
        pts = treemap_event.selection.get("points") or []
        if pts:
            pt = pts[0]

            # --- Parse click target -----------------------------------------
            # Priority 1: customdata=[sector, sub_theme] — always present
            cd = pt.get("customdata") or []
            if cd and len(cd) >= 2:
                click_sector = str(cd[0] or "").strip() or None
                click_sub    = str(cd[1] or "").strip() or None
            else:
                # Priority 2: explicit id field ("Sector" or "Sector/Sub-Theme")
                id_val = str(pt.get("id", "") or "").strip()
                label  = str(pt.get("label", "") or "").strip()
                parent = str(pt.get("parent", "") or "").strip()

                if "/" in id_val:
                    parts = id_val.split("/", 1)
                    click_sector, click_sub = parts[0], parts[1]
                elif id_val in ALL_SECTORS:
                    click_sector, click_sub = id_val, None
                elif label in ALL_SECTORS:
                    click_sector, click_sub = label, None
                elif parent in ALL_SECTORS:
                    click_sector, click_sub = parent, label
                else:
                    click_sector, click_sub = None, None
            # ----------------------------------------------------------------

            if click_sub:
                candidate = {"sector": click_sector, "sub_theme": click_sub}
                new_sel = (
                    {"sector": click_sector, "sub_theme": None}
                    if prev_sel == candidate
                    else candidate
                )
            elif click_sector:
                candidate = {"sector": click_sector, "sub_theme": None}
                new_sel = (
                    {"sector": None, "sub_theme": None}
                    if prev_sel == candidate
                    else candidate
                )
            else:
                new_sel = {"sector": None, "sub_theme": None}
        else:
            new_sel = {"sector": None, "sub_theme": None}

        if new_sel is not None and new_sel != prev_sel:
            st.session_state["thematic_treemap_sel"] = new_sel
            st.session_state["thematic_page"] = 0
            st.session_state["thematic_selected_ticker"] = None
            # Clear dropdown keys so their defaults reflect new treemap state
            st.session_state.pop("th_sectors", None)
            st.session_state.pop("th_themes", None)
            st.rerun()

    treemap_sel = st.session_state["thematic_treemap_sel"]

    # Active filter banner
    if treemap_sel["sector"]:
        crumb = (
            f"{treemap_sel['sector']} &rsaquo; {treemap_sel['sub_theme']}"
            if treemap_sel["sub_theme"]
            else treemap_sel["sector"]
        )
        col_banner, col_clear = st.columns([6, 1])
        with col_banner:
            st.markdown(
                f'<div style="background:#1a3d2e;border:1px solid #00D4AA;border-radius:6px;'
                f'padding:0.4rem 0.9rem;font-size:0.81rem;margin-top:0.25rem">'
                f'&#x1F5C2; <b style="color:#00D4AA">Filter:</b> '
                f'<span style="color:#ddd">{crumb}</span>'
                f'<span style="color:#666;font-size:0.7rem"> — click same tile to clear</span>'
                f'</div>',
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

    # Build filtered list
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

    st.caption(f"**{len(filtered)}** products — select a row to view holdings, performance, and news")

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
        price  = _safe_num(px_d.get("price"))
        chg    = _safe_num(px_d.get("chg_pct"))
        rows.append({
            "Ticker":    p.ticker,
            "Name":      p.name,
            "Sector":    p.sector,
            "Sub-Theme": p.sub_theme,
            "Region":    p.region,
            "Exchange":  p.exchange,
            "TER":       f"{p.expense_ratio:.2f}%" if p.expense_ratio else "—",
            "AUM ($bn)": f"{p.aum_bn:.1f}"         if p.aum_bn        else "—",
            "Issuer":    p.issuer                   or "—",
            "Price":     f"${price:,.2f}"           if price is not None else "—",
            "1d %":      f"{chg:+.2f}%"             if chg  is not None else "—",
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

    # Update selected ticker from row click
    sel_rows = (
        table_event.selection.rows
        if table_event and table_event.selection
        else []
    )
    if sel_rows and 0 <= sel_rows[0] < len(page_items):
        new_ticker = page_items[sel_rows[0]].ticker
        if st.session_state["thematic_selected_ticker"] != new_ticker:
            st.session_state["thematic_selected_ticker"] = new_ticker

    # Resolve selected ticker to product on current page
    sel_ticker = st.session_state.get("thematic_selected_ticker")
    selected_product = next(
        (p for p in page_items if p.ticker == sel_ticker), None
    ) if sel_ticker else None

    if selected_product:
        st.markdown("---")
        st.markdown(f"#### 🔍 {selected_product.ticker} — Fund Intelligence")
        _render_detail_panel(selected_product, prices, page)
