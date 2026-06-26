"""Thematic Sectors module — Streamlit renderer."""
from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from .data import THEMATIC_REGISTRY, ThematicProduct, ALL_SECTORS, ALL_SUB_THEMES, fetch_prices
from modules.shared import inject_autocomplete as _inject_autocomplete
from modules.shared import html_table as _tbl

_PAGE_SIZE = 25
_TH_CH = "iw-tbl-th-v1"

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
        hist = yf.Ticker(ticker).history(period="max", auto_adjust=True)
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
            "5Y":  _ret(1260),
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

def _render_detail_panel(p: ThematicProduct, prices: dict) -> None:
    """Fund deep-dive: header → holdings → performance → news → action buttons."""
    yf_key  = p.yf_ticker or p.ticker
    px_data = prices.get(yf_key, {})
    price   = _safe_num(px_data.get("price"))
    chg     = _safe_num(px_data.get("chg_pct"))

    price_str = f"${price:,.2f}" if price else "—"
    chg_color = "#1AB868" if (chg is not None and chg >= 0) else "#E53535"
    chg_str   = f"{chg:+.2f}%" if chg is not None else "—"

    issuer_url = _etf_website_url(p.ticker, p.issuer, p.exchange)
    yahoo_url  = _yahoo_url(p.ticker)

    # Pre-build optional metadata spans to avoid f-string conditional bugs
    ter_span  = f'<span>💰 TER&nbsp;<b style="color:#1e293b">{p.expense_ratio:.2f}%</b></span>' if p.expense_ratio else ""
    aum_span  = f'<span>📦 AUM&nbsp;<b style="color:#1e293b">${p.aum_bn:.1f}bn</b></span>'        if p.aum_bn        else ""
    isin_span = f'<span>🔢&nbsp;<b style="color:#1e293b">{p.isin}</b></span>'                       if p.isin          else ""

    # ── 1. Header ─────────────────────────────────────────────────────────────
    st.markdown(
        f"""
<div style="background:#ffffff;border:1px solid #D9E8F5;border-left:4px solid #1AB868;
     border-radius:10px;padding:1rem 1.2rem;margin:0.4rem 0 0.75rem 0">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;
       flex-wrap:wrap;gap:0.5rem">
    <div>
      <span style="color:#1AB868;font-size:0.68rem;font-weight:700;
            letter-spacing:0.12em">{p.sector.upper()} &middot; {p.sub_theme}</span><br>
      <span style="font-size:1.25rem;font-weight:700">{p.ticker}</span>&nbsp;
      <span style="color:#2B5A85;font-size:0.87rem">{p.name}</span>
    </div>
    <div style="text-align:right">
      <div style="font-size:1.3rem;font-weight:700">{price_str}</div>
      <div style="font-size:0.87rem;color:{chg_color}">{chg_str} today</div>
    </div>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:1rem;margin-top:0.6rem;
       font-size:0.75rem;color:#999">
    <span>🏢&nbsp;<b style="color:#1e293b">{p.issuer or "—"}</b></span>
    <span>🏛&nbsp;<b style="color:#1e293b">{p.exchange}</b></span>
    <span>🌍&nbsp;<b style="color:#1e293b">{p.region}</b></span>
    <span>💱&nbsp;<b style="color:#1e293b">{p.currency}</b></span>
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
                customdata=h_df["name"],
                orientation="h",
                marker_color="#1AB868",
                text=[f"{v:.1f}%" for v in h_df["pct"]],
                textposition="outside",
                hovertemplate="<b>%{customdata}</b> (%{y})<br>%{x:.2f}%<extra></extra>",
            ))
            fig_h.update_layout(
                height=max(180, len(h_df) * 28),
                margin={"t": 5, "b": 5, "l": 10, "r": 55},
                paper_bgcolor="#f4f6f9",
                plot_bgcolor="#f4f6f9",
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
            # Timeframe selector
            _TF_DAYS = {"1M": 21, "3M": 63, "6M": 126, "1Y": 252, "5Y": 1260, "All": None}
            tf = st.radio(
                "",
                list(_TF_DAYS.keys()),
                index=3,          # default: 1Y
                horizontal=True,
                key=f"perf_tf_{p.ticker}",
            )
            n_days = _TF_DAYS[tf]
            all_dates  = perf["dates"]
            all_prices = perf["prices"]
            vis_dates  = all_dates[-n_days:]  if n_days else all_dates
            vis_prices = all_prices[-n_days:] if n_days else all_prices

            # Price chart for selected window
            line_color = "#1AB868"
            if len(vis_prices) >= 2:
                p0 = next((v for v in vis_prices if v is not None), None)
                p1 = next((v for v in reversed(vis_prices) if v is not None), None)
                if p0 and p1 and p1 < p0:
                    line_color = "#E53535"

            fig_p = go.Figure(go.Scatter(
                x=vis_dates,
                y=vis_prices,
                mode="lines",
                line={"color": line_color, "width": 1.8},
                fill="tozeroy",
                fillcolor=f"rgba({'26,184,104' if line_color == '#1AB868' else '229,53,53'},0.07)",
                hovertemplate="%{x}<br>$%{y:,.2f}<extra></extra>",
            ))
            fig_p.update_layout(
                height=150,
                margin={"t": 5, "b": 5, "l": 0, "r": 0},
                paper_bgcolor="#f4f6f9",
                plot_bgcolor="#f4f6f9",
                xaxis={"visible": False},
                yaxis={"color": "#5A8EBB", "gridcolor": "#D9E8F5", "tickformat": "$,.0f"},
                showlegend=False,
            )
            st.plotly_chart(fig_p, use_container_width=True,
                            config={"displayModeBar": False})

            # Return metrics row (all periods for quick reference)
            periods = [
                ("1M",  perf.get("1M")),
                ("3M",  perf.get("3M")),
                ("6M",  perf.get("6M")),
                ("YTD", perf.get("YTD")),
                ("1Y",  perf.get("1Y")),
                ("5Y",  perf.get("5Y")),
            ]
            cells = ""
            for lbl, val in periods:
                is_active = lbl == tf
                if val is not None:
                    color   = "#1AB868" if val >= 0 else "#E53535"
                    val_str = f"{val:+.1f}%"
                else:
                    color   = "#555"
                    val_str = "—"
                border = "border-bottom:2px solid #1AB868;" if is_active else ""
                cells += (
                    f'<div style="text-align:center;flex:1;{border}">'
                    f'<div style="font-size:0.62rem;color:#5A8EBB">{lbl}</div>'
                    f'<div style="font-size:0.8rem;font-weight:700;color:{color}">{val_str}</div>'
                    f'</div>'
                )
            st.markdown(
                f'<div style="display:flex;gap:0.25rem;margin-top:0.15rem">{cells}</div>',
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
                    f'style="color:#071D35;text-decoration:none;font-weight:600;'
                    f'border-bottom:1px dotted #555;line-height:1.45">{title}</a>'
                )
                read_link = (
                    f'<span style="color:#5A8EBB">&middot;</span>'
                    f'<a href="{link}" target="_blank" rel="noopener noreferrer" '
                    f'style="color:#1AB868;text-decoration:none;font-size:0.68rem">'
                    f'&nearr; Read</a>'
                )
            else:
                headline_html = f'<span style="color:#071D35;font-weight:600">{title}</span>'
                read_link = ""

            time_html = (
                f'<span style="color:#5A8EBB">&middot;</span>'
                f'<span>{time_label}</span>'
            ) if time_label else ""

            st.markdown(
                f"""
<div style="background:#EEF4FB;border:1px solid #D9E8F5;border-left:3px solid #E8A500;
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
    btn1, btn2 = st.columns(2)
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


# ── Main render ───────────────────────────────────────────────────────────────

def _on_th_search_change() -> None:
    st.session_state["thematic_page"] = 0
    st.session_state["thematic_selected_ticker"] = None


def _apply_treemap_sel(new_sel: dict) -> None:
    """Commit a new treemap selection to session state and rerun."""
    st.session_state["thematic_treemap_sel"] = new_sel
    st.session_state["thematic_page"] = 0
    st.session_state["thematic_selected_ticker"] = None
    st.session_state.pop("th_sectors", None)
    st.session_state.pop("th_themes", None)
    st.rerun()


def render() -> None:
    st.markdown("<h2 class='iw-module-header'>Global Sector & ETFs — Sector & Thematic ETF Grid</h2>", unsafe_allow_html=True)
    st.caption(
        f"{len(THEMATIC_REGISTRY)} products across {len(ALL_SECTORS)} sectors "
        f"and {len(ALL_SUB_THEMES)} sub-themes — "
        "**click a sector button** to filter · **click sub-theme** to narrow · **click a row** to explore"
    )

    # ── Session state init ────────────────────────────────────────────────────
    if "thematic_treemap_sel" not in st.session_state:
        st.session_state["thematic_treemap_sel"] = {"sector": None, "sub_theme": None}
    if "thematic_selected_ticker" not in st.session_state:
        st.session_state["thematic_selected_ticker"] = None
    if "thematic_page" not in st.session_state:
        st.session_state["thematic_page"] = 0

    treemap_sel = st.session_state["thematic_treemap_sel"]

    # ── Sector/sub-theme counts ───────────────────────────────────────────────
    theme_counts: dict[str, dict] = {}
    for p in THEMATIC_REGISTRY:
        theme_counts.setdefault(p.sector, {})
        theme_counts[p.sector][p.sub_theme] = theme_counts[p.sector].get(p.sub_theme, 0) + 1

    # ── Sector filter chips ───────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.72rem;color:#5A8EBB;margin-bottom:0.25rem">'
        '&#x25BC; Click a sector to filter the table below</div>',
        unsafe_allow_html=True,
    )
    sector_list = sorted(ALL_SECTORS)
    _CHIP_ROW = 5  # sectors per row
    for row_start in range(0, len(sector_list), _CHIP_ROW):
        row_sectors = sector_list[row_start : row_start + _CHIP_ROW]
        cols = st.columns(len(row_sectors))
        for col, sector in zip(cols, row_sectors):
            active = treemap_sel["sector"] == sector
            count  = sum(theme_counts.get(sector, {}).values())
            with col:
                if st.button(
                    f"{'✓ ' if active else ''}{sector} ({count})",
                    key=f"sec_btn_{sector}",
                    use_container_width=True,
                    type="primary" if active else "secondary",
                ):
                    _apply_treemap_sel(
                        {"sector": None, "sub_theme": None}
                        if active
                        else {"sector": sector, "sub_theme": None}
                    )

    # ── Sub-theme chips (expand when a sector is active) ─────────────────────
    if treemap_sel["sector"]:
        sub_themes = sorted(
            set(p.sub_theme for p in THEMATIC_REGISTRY
                if p.sector == treemap_sel["sector"])
        )
        st.markdown(
            f'<div style="font-size:0.72rem;color:#5A8EBB;margin:0.35rem 0 0.2rem 0">'
            f'Sub-themes in <b style="color:#1AB868">{treemap_sel["sector"]}</b>:</div>',
            unsafe_allow_html=True,
        )
        _THEME_ROW = 6
        for row_start in range(0, len(sub_themes), _THEME_ROW):
            row_themes = sub_themes[row_start : row_start + _THEME_ROW]
            cols = st.columns(len(row_themes))
            for col, theme in zip(cols, row_themes):
                active = treemap_sel["sub_theme"] == theme
                cnt    = theme_counts.get(treemap_sel["sector"], {}).get(theme, 0)
                with col:
                    if st.button(
                        f"{'✓ ' if active else ''}{theme} ({cnt})",
                        key=f"theme_btn_{theme}",
                        use_container_width=True,
                        type="primary" if active else "secondary",
                    ):
                        _apply_treemap_sel(
                            {"sector": treemap_sel["sector"], "sub_theme": None}
                            if active
                            else {"sector": treemap_sel["sector"], "sub_theme": theme}
                        )

    # Active filter breadcrumb
    if treemap_sel["sector"]:
        crumb = (
            f"{treemap_sel['sector']} › {treemap_sel['sub_theme']}"
            if treemap_sel["sub_theme"]
            else treemap_sel["sector"]
        )
        st.markdown(
            f'<div style="background:#f0fdf4;border:1px solid #1AB868;border-radius:6px;'
            f'padding:0.35rem 0.9rem;font-size:0.79rem;margin-top:0.4rem">'
            f'&#x1F5C2; <b style="color:#1AB868">Active filter:</b> '
            f'<span style="color:#071D35">{crumb}</span> — '
            f'<span style="color:#5A8EBB;font-size:0.7rem">click ✓ button above to clear</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Filters + search ─────────────────────────────────────────────────────
    col_s, col_t, col_r, col_ex = st.columns(4)
    with col_s:
        sel_sectors = st.multiselect(
            "Sector", ALL_SECTORS,
            placeholder="All sectors", key="th_sectors",
        )
    with col_t:
        sel_themes = st.multiselect(
            "Sub-Theme", ALL_SUB_THEMES,
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

    search_q = st.text_input(
        "Search instruments",
        value="",
        placeholder="Ticker, name, theme…",
        key="th_search",
        on_change=_on_th_search_change,
    )

    import json as _json
    _ac_items = []
    for _p in THEMATIC_REGISTRY:
        _ac_items.append({
            "l": f"{_p.ticker} — {_p.name}",
            "v": _p.ticker,
            "b": _p.sub_theme,
            "s": f"{_p.ticker.lower()} {_p.name.lower()} {(_p.issuer or '').lower()} {_p.sub_theme.lower()} {_p.sector.lower()}",
        })
    _inject_autocomplete(_json.dumps(_ac_items, ensure_ascii=False), "Ticker, name, theme…")

    # Build filtered list — sector button chips take priority; dropdowns can
    # further narrow or override when the user explicitly selects something
    filtered = list(THEMATIC_REGISTRY)
    active_sector = sel_sectors[0] if len(sel_sectors) == 1 else treemap_sel["sector"]
    active_sub    = sel_themes[0]  if len(sel_themes)  == 1 else treemap_sel["sub_theme"]
    if active_sector and not sel_sectors:
        filtered = [p for p in filtered if p.sector == active_sector]
    if active_sub and not sel_themes:
        filtered = [p for p in filtered if p.sub_theme == active_sub]
    if sel_sectors:
        filtered = [p for p in filtered if p.sector in sel_sectors]
    if sel_themes:
        filtered = [p for p in filtered if p.sub_theme in sel_themes]
    if sel_regions:
        filtered = [p for p in filtered if p.region in sel_regions]
    if sel_exchange:
        filtered = [p for p in filtered if p.exchange in sel_exchange]
    if search_q:
        q = search_q.lower()
        filtered = [
            p for p in filtered
            if q in p.ticker.lower() or q in p.name.lower()
            or q in (p.issuer or "").lower() or q in p.sub_theme.lower()
            or q in p.sector.lower()
        ]

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

    sel_ticker_cur = st.session_state.get("thematic_selected_ticker")
    sel_idx = next((i for i, p in enumerate(page_items) if p.ticker == sel_ticker_cur), None)

    new_sel = _tbl.render(
        rows=rows,
        columns=[
            ("Ticker", "Ticker"), ("Name", "Name"), ("Sector", "Sector"),
            ("Sub-Theme", "Sub-Theme"), ("Region", "Region"), ("Exchange", "Exchange"),
            ("TER", "TER"), ("AUM ($bn)", "AUM ($bn)"), ("Issuer", "Issuer"),
            ("Price", "Price"), ("1d %", "1d %"),
        ],
        channel_placeholder=_TH_CH,
        selected_idx=sel_idx,
        col_classes={"Ticker": "td-mono", "Price": "td-mono"},
    )

    if new_sel is not None and 0 <= new_sel < len(page_items):
        clicked = page_items[new_sel].ticker
        if st.session_state.get("thematic_selected_ticker") == clicked:
            st.session_state["thematic_selected_ticker"] = None
            st.session_state[f"_iwtbl_clear__iwtbl_{_TH_CH}"] = True
            st.rerun()
        else:
            st.session_state["thematic_selected_ticker"] = clicked
            st.rerun()

    sel_ticker = st.session_state["thematic_selected_ticker"]
    selected_product = next(
        (p for p in page_items if p.ticker == sel_ticker), None
    ) if sel_ticker else None

    if selected_product:
        st.markdown("---")
        st.markdown(f"#### 🔍 {selected_product.ticker} — Fund Intelligence")
        _render_detail_panel(selected_product, prices)
