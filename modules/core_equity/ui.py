"""Core Equity module — Streamlit renderer with fund intelligence panel."""
from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from .data import CORE_EQUITY_REGISTRY, IndexProduct, fetch_prices
from modules.shared import inject_autocomplete as _inject_autocomplete
from modules.shared import html_table as _tbl

_CE_CH = "iw-tbl-ce-v1"

_PAGE_SIZE = 20


# ── Search callbacks ──────────────────────────────────────────────────────────

def _on_ce_search_change() -> None:
    st.session_state["ce_page"] = 0
    st.session_state["ce_selected"] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_num(v) -> Optional[float]:
    try:
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def _live_prices(tickers: tuple[str, ...]) -> dict:
    return fetch_prices(list(tickers))


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_holdings(ticker: str) -> list[dict]:
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        try:
            fd = t.funds_data
            if fd is not None:
                th = getattr(fd, "top_holdings", None)
                if th is not None and not th.empty:
                    out = []
                    for _, row in th.reset_index().head(12).iterrows():
                        sym  = str(row.get("Symbol") or row.get("symbol") or "").strip()
                        name = str(row.get("Name") or row.get("name") or sym).strip()
                        raw  = row.get("Holding Percent") or row.get("holdingPercent") or 0
                        pct  = _safe_num(raw) or 0.0
                        if pct and pct < 1.5:
                            pct *= 100
                        if sym:
                            out.append({"symbol": sym, "name": name, "pct": round(pct, 2)})
                    if out:
                        return out
        except Exception:
            pass
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
            title = str(content.get("title") or content.get("headline") or item.get("title", "")).strip()
            if not title:
                continue
            canon = content.get("canonicalUrl") or {}
            click = content.get("clickThroughUrl") or {}
            link  = (
                (canon.get("url") if isinstance(canon, dict) else "")
                or (click.get("url") if isinstance(click, dict) else "")
                or item.get("link", "")
            )
            link = str(link).strip()
            provider  = content.get("provider") or {}
            publisher = (
                (provider.get("displayName") if isinstance(provider, dict) else str(provider or ""))
                or item.get("publisher", "")
            )
            ts_raw = content.get("pubDate") or item.get("providerPublishTime") or 0
            ts: int = 0
            if isinstance(ts_raw, str):
                try:
                    ts = int(datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).timestamp())
                except Exception:
                    ts = 0
            else:
                ts = int(ts_raw or 0)
            result.append({"title": title, "link": link, "publisher": str(publisher).strip(), "ts": ts})
        return result
    except Exception:
        return []


# ── Issuer URL map ────────────────────────────────────────────────────────────

_ISSUER_URL_MAP = {
    "blackrock":    lambda t: f"https://www.ishares.com/us/products/etf-investments#{t}",
    "ishares":      lambda t: f"https://www.ishares.com/us/products/etf-investments#{t}",
    "vanguard":     lambda t: f"https://investor.vanguard.com/investment-products/etfs/profile/{t.lower()}",
    "state street": lambda t: f"https://www.ssga.com/us/en/intermediary/etfs/fund-finder?ticker={t}",
    "spdr":         lambda t: f"https://www.ssga.com/us/en/intermediary/etfs/fund-finder?ticker={t}",
    "invesco":      lambda t: f"https://www.invesco.com/us/financial-products/etfs/product-detail?audienceType=Investor&ticker={t}",
    "proshares":    lambda t: f"https://www.proshares.com/our-etfs/{t.lower()}/",
    "direxion":     lambda t: f"https://www.direxion.com/products/{t.lower()}/",
    "wisdomtree":   lambda t: f"https://www.wisdomtree.com/investments/etfs/{t.lower()}",
    "schwab":       lambda t: f"https://www.schwabassetmanagement.com/products/etfs?ticker={t}",
    "vaneck":       lambda t: f"https://www.vaneck.com/us/en/{t.lower()}/",
    "first trust":  lambda t: f"https://www.ftportfolios.com/Retail/Etf/EtfSummary.aspx?Ticker={t}",
    "kraneshares":  lambda t: f"https://kraneshares.com/etfs/{t.lower()}/",
    "dws":          lambda t: f"https://etf.dws.com/en-gb/",
    "hsbc":         lambda t: f"https://www.assetmanagement.hsbc.co.uk/en/institutional-investor/etf",
    "amundi":       lambda t: f"https://www.amundietf.com/professional/product/{t.lower()}",
    "lyxor":        lambda t: f"https://www.amundietf.com/professional/product/{t.lower()}",
    "lgim":         lambda t: f"https://www.lgim.com/uk/en/capabilities/etfs/",
}


def _fund_url(ticker: str, issuer: Optional[str]) -> str:
    t_clean = ticker.split(".")[0].upper()
    if issuer:
        for key, fn in _ISSUER_URL_MAP.items():
            if key in issuer.lower():
                return fn(t_clean)
    return f"https://finance.yahoo.com/quote/{ticker}"


# ── Detail panel ──────────────────────────────────────────────────────────────

def _render_detail_panel(p: IndexProduct, prices: dict) -> None:
    yf_key  = p.yf_ticker or p.ticker
    px_data = prices.get(yf_key, {})
    price   = _safe_num(px_data.get("price"))
    chg     = _safe_num(px_data.get("chg_pct"))

    price_str = f"${price:,.4f}" if price else "—"
    chg_color = "#1AB868" if (chg is not None and chg >= 0) else "#E53535"
    chg_str   = f"{chg:+.2f}%" if chg is not None else "—"
    lev_str   = f"{p.leverage:+.0f}×" if p.leverage != 1.0 else "1×"

    issuer_url = _fund_url(p.ticker, p.issuer)
    yahoo_url  = f"https://finance.yahoo.com/quote/{p.ticker}"

    ter_span  = f'<span>💰 TER&nbsp;<b style="color:#1e293b">{p.expense_ratio:.2f}%</b></span>' if p.expense_ratio else ""
    aum_span  = f'<span>📦 AUM&nbsp;<b style="color:#1e293b">${p.aum_bn:.1f}bn</b></span>'        if p.aum_bn        else ""
    isin_span = f'<span>🔢&nbsp;<b style="color:#1e293b">{p.isin}</b></span>'                       if p.isin          else ""

    st.markdown(
        f"""
<div style="background:#ffffff;border:1px solid #D9E8F5;border-left:4px solid #1AB868;
     border-radius:10px;padding:1rem 1.2rem;margin:0.4rem 0 0.75rem 0">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:0.5rem">
    <div>
      <span style="color:#1AB868;font-size:0.68rem;font-weight:700;letter-spacing:0.12em">
        {p.region.upper()} &middot; {p.index_tracked}
      </span><br>
      <span style="font-size:1.25rem;font-weight:700;color:#071D35">{p.ticker}</span>&nbsp;
      <span style="color:#2B5A85;font-size:0.87rem">{p.name}</span>
    </div>
    <div style="text-align:right">
      <div style="font-size:1.3rem;font-weight:700;color:#071D35">{price_str}</div>
      <div style="font-size:0.87rem;color:{chg_color}">{chg_str} today</div>
    </div>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:1rem;margin-top:0.6rem;font-size:0.75rem;color:#999">
    <span>🏢&nbsp;<b style="color:#1e293b">{p.issuer or "—"}</b></span>
    <span>🏛&nbsp;<b style="color:#1e293b">{p.exchange}</b></span>
    <span>💱&nbsp;<b style="color:#1e293b">{p.currency}</b></span>
    <span>⚡&nbsp;<b style="color:#1e293b">Leverage {lev_str}</b></span>
    {ter_span}
    {aum_span}
    {isin_span}
  </div>
</div>""",
        unsafe_allow_html=True,
    )

    # Fetch all data in parallel
    with ThreadPoolExecutor(max_workers=3) as _pool:
        _fh = _pool.submit(_fetch_holdings, yf_key)
        _fp = _pool.submit(_fetch_performance, yf_key)
        _fn = _pool.submit(_fetch_news, yf_key)
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
                textfont={"color": "#071D35", "size": 11},
                hovertemplate="<b>%{customdata}</b> (%{y})<br>%{x:.2f}%<extra></extra>",
            ))
            fig_h.update_layout(
                height=max(180, len(h_df) * 28),
                margin={"t": 5, "b": 5, "l": 10, "r": 55},
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                xaxis={"visible": False},
                yaxis={"color": "#2B5A85", "tickfont": {"size": 11, "color": "#2B5A85"}, "autorange": "reversed"},
                showlegend=False,
            )
            st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("Holdings data not available.")

    with col_p:
        st.markdown("##### 📈 Performance")
        if perf and perf.get("dates"):
            _TF_DAYS = {"1M": 21, "3M": 63, "6M": 126, "1Y": 252, "5Y": 1260, "All": None}
            tf = st.radio("", list(_TF_DAYS.keys()), index=3, horizontal=True,
                          key=f"ce_perf_tf_{p.ticker}")
            n_days     = _TF_DAYS[tf]
            all_dates  = perf["dates"]
            all_prices = perf["prices"]
            vis_dates  = all_dates[-n_days:]  if n_days else all_dates
            vis_prices = all_prices[-n_days:] if n_days else all_prices

            line_color = "#1AB868"
            if len(vis_prices) >= 2:
                p0v = next((v for v in vis_prices if v is not None), None)
                p1v = next((v for v in reversed(vis_prices) if v is not None), None)
                if p0v and p1v and p1v < p0v:
                    line_color = "#E53535"

            fig_p = go.Figure(go.Scatter(
                x=vis_dates, y=vis_prices, mode="lines",
                line={"color": line_color, "width": 1.8},
                fill="tozeroy",
                fillcolor=f"rgba({'26,184,104' if line_color == '#1AB868' else '229,53,53'},0.07)",
                hovertemplate="%{x}<br>$%{y:,.2f}<extra></extra>",
            ))
            fig_p.update_layout(
                height=150,
                margin={"t": 5, "b": 5, "l": 0, "r": 0},
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                xaxis={"visible": False},
                yaxis={"color": "#2B5A85", "gridcolor": "#D9E8F5", "tickformat": "$,.0f", "tickfont": {"color": "#2B5A85", "size": 10}},
                showlegend=False,
            )
            st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar": False})

            periods = [("1M", perf.get("1M")), ("3M", perf.get("3M")),
                       ("6M", perf.get("6M")), ("YTD", perf.get("YTD")),
                       ("1Y", perf.get("1Y")), ("5Y", perf.get("5Y"))]
            cells = ""
            for lbl, val in periods:
                is_active = lbl == tf
                if val is not None:
                    color   = "#1AB868" if val >= 0 else "#E53535"
                    val_str = f"{val:+.1f}%"
                else:
                    color, val_str = "#555", "—"
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

    # News
    st.markdown("##### 📰 Recent News & Market Impact")
    if news:
        for article in news:
            title, link, publisher, ts = (
                article["title"], article["link"],
                article["publisher"], article["ts"]
            )
            if ts:
                age_h = (time.time() - ts) / 3600
                time_label = (f"{int(age_h * 60)}m ago" if age_h < 1
                              else f"{int(age_h)}h ago" if age_h < 24
                              else f"{int(age_h / 24)}d ago")
            else:
                time_label = ""

            if link and link.startswith("http"):
                headline_html = (
                    f'<a href="{link}" target="_blank" rel="noopener noreferrer" '
                    f'style="color:#071D35;text-decoration:none;font-weight:600;'
                    f'border-bottom:1px dotted #555">{title}</a>'
                )
                read_link = (
                    f'<span style="color:#5A8EBB">&middot;</span>'
                    f'<a href="{link}" target="_blank" rel="noopener noreferrer" '
                    f'style="color:#1AB868;text-decoration:none;font-size:0.68rem">&nearr; Read</a>'
                )
            else:
                headline_html = f'<span style="color:#071D35;font-weight:600">{title}</span>'
                read_link = ""

            time_html = (f'<span style="color:#5A8EBB">&middot;</span><span>{time_label}</span>'
                         if time_label else "")

            st.markdown(
                f"""<div style="background:#EEF4FB;border:1px solid #D9E8F5;border-left:3px solid #E8A500;
     border-radius:6px;padding:0.55rem 0.8rem;margin-bottom:0.4rem">
  <div style="font-size:0.79rem">{headline_html}</div>
  <div style="display:flex;gap:0.4rem;align-items:center;margin-top:0.28rem;font-size:0.68rem;color:#666">
    <span>{publisher}</span>{time_html}{read_link}
  </div>
</div>""",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No recent news available.")

    # Action buttons
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1:
        st.link_button(f"🌐 {p.issuer or 'Fund'} Website →", issuer_url, use_container_width=True)
    with b2:
        st.link_button("📈 Yahoo Finance →", yahoo_url, use_container_width=True)


# ── Main render ───────────────────────────────────────────────────────────────

def render() -> None:
    # Module-scoped CSS fixes
    st.markdown("""
<style>
/* ── Core Equity: toggle wrapper visibility ── */
.stToggle,
div[data-testid="stToggle"],
label[data-baseweb="checkbox"] {
    background: var(--navy-50) !important;
    border: 1.5px solid var(--navy-200) !important;
    border-radius: 10px !important;
    padding: 0.35rem 0.65rem !important;
    width: 100% !important;
    box-sizing: border-box !important;
}
/* ── Core Equity: radio buttons (performance timeframe) ── */
div[data-testid="stRadio"] label {
    font-size: 0.75rem !important;
    color: var(--text-h) !important;
    background: none !important;
    border: none !important;
    padding: 0 !important;
}
</style>
""", unsafe_allow_html=True)

    st.markdown("<h2 class='iw-module-header'>Global Index & ETFs — Index & ETF Intelligence</h2>", unsafe_allow_html=True)
    st.caption(f"{len(CORE_EQUITY_REGISTRY)} instruments tracked across 25+ countries and regions")

    # ── Session state ─────────────────────────────────────────────────────────
    if "ce_page" not in st.session_state:
        st.session_state["ce_page"] = 0
    if "ce_selected" not in st.session_state:
        st.session_state["ce_selected"] = None

    # ── Filters ───────────────────────────────────────────────────────────────
    regions = sorted(set(p.region for p in CORE_EQUITY_REGISTRY))
    types   = sorted(set(p.product_type for p in CORE_EQUITY_REGISTRY))
    issuers = sorted(set(p.issuer for p in CORE_EQUITY_REGISTRY if p.issuer))

    col_r, col_t, col_i, col_lev = st.columns([2, 2, 2, 1])
    with col_r:
        sel_regions = st.multiselect("Region", regions, placeholder="All regions", key="ce_regions")
    with col_t:
        sel_types = st.multiselect("Product Type", types, placeholder="All types", key="ce_types")
    with col_i:
        sel_issuers = st.multiselect("Issuer", issuers, placeholder="All issuers", key="ce_issuers")
    with col_lev:
        show_leveraged = st.toggle("Include Leveraged", value=True, key="ce_lev")

    search_q = st.text_input(
        "Search instruments",
        value="",
        placeholder="Ticker, name, index…",
        key="ce_search",
        on_change=_on_ce_search_change,
    )

    import json as _json
    _ac_items = []
    for _p in CORE_EQUITY_REGISTRY:
        _ac_items.append({
            "l": f"{_p.ticker} — {_p.name}",
            "v": _p.ticker,
            "b": f"{_p.region} · {_p.product_type}",
            "s": f"{_p.ticker.lower()} {_p.name.lower()} {(_p.issuer or '').lower()} {_p.index_tracked.lower()}",
        })
    _inject_autocomplete(_json.dumps(_ac_items, ensure_ascii=False), "Ticker, name, index…")

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = list(CORE_EQUITY_REGISTRY)
    if sel_regions:
        filtered = [p for p in filtered if p.region in sel_regions]
    if sel_types:
        filtered = [p for p in filtered if p.product_type in sel_types]
    if sel_issuers:
        filtered = [p for p in filtered if p.issuer in sel_issuers]
    if not show_leveraged:
        filtered = [p for p in filtered if abs(p.leverage) == 1.0]
    if search_q:
        q = search_q.lower()
        filtered = [
            p for p in filtered
            if q in p.ticker.lower() or q in p.name.lower()
            or q in p.index_tracked.lower() or q in (p.issuer or "").lower()
        ]

    st.caption(f"**{len(filtered)}** instruments — select a row to view fund intelligence")

    # ── Live prices ───────────────────────────────────────────────────────────
    tickers_yf = tuple(p.yf_ticker or p.ticker for p in filtered)
    prices = _live_prices(tickers_yf) if tickers_yf else {}

    # ── Pagination ────────────────────────────────────────────────────────────
    total_pages = max(1, (len(filtered) + _PAGE_SIZE - 1) // _PAGE_SIZE)
    page = max(0, min(st.session_state["ce_page"], total_pages - 1))

    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        if st.button("← Prev", key="ce_prev", disabled=page == 0):
            st.session_state["ce_page"] = page - 1
            st.session_state["ce_selected"] = None
            st.rerun()
    with c2:
        st.caption(f"Page {page + 1} / {total_pages}")
    with c3:
        if st.button("Next →", key="ce_next", disabled=page >= total_pages - 1):
            st.session_state["ce_page"] = page + 1
            st.session_state["ce_selected"] = None
            st.rerun()

    page_items = filtered[page * _PAGE_SIZE : (page + 1) * _PAGE_SIZE]

    # ── Selectable table ──────────────────────────────────────────────────────
    rows = []
    for p in page_items:
        yf_key  = p.yf_ticker or p.ticker
        px_data = prices.get(yf_key, {})
        price   = _safe_num(px_data.get("price"))
        chg     = _safe_num(px_data.get("chg_pct"))
        rows.append({
            "Ticker":    p.ticker,
            "Name":      p.name,
            "Region":    p.region,
            "Index":     p.index_tracked,
            "Type":      p.product_type,
            "Leverage":  f"{p.leverage:+.0f}×" if p.leverage != 1.0 else "1×",
            "TER":       f"{p.expense_ratio:.2f}%" if p.expense_ratio else "—",
            "AUM ($bn)": f"{p.aum_bn:.1f}"         if p.aum_bn        else "—",
            "Issuer":    p.issuer                   or "—",
            "Price":     f"${price:,.4f}"           if price is not None else "—",
            "1d %":      f"{chg:+.2f}%"             if chg  is not None else "—",
        })

    sel_ticker_cur = st.session_state.get("ce_selected")
    sel_idx = next((i for i, p in enumerate(page_items) if p.ticker == sel_ticker_cur), None)

    new_sel = _tbl.render(
        rows=rows,
        columns=[
            ("Ticker", "Ticker"), ("Name", "Name"), ("Region", "Region"),
            ("Index", "Index"), ("Type", "Type"), ("Leverage", "Lev."),
            ("TER", "TER"), ("AUM ($bn)", "AUM ($bn)"), ("Issuer", "Issuer"),
            ("Price", "Price"), ("1d %", "1d %"),
        ],
        channel_placeholder=_CE_CH,
        selected_idx=sel_idx,
        col_classes={"Ticker": "td-mono", "Price": "td-mono"},
    )

    if new_sel is not None and 0 <= new_sel < len(page_items):
        clicked = page_items[new_sel].ticker
        if st.session_state.get("ce_selected") == clicked:
            st.session_state["ce_selected"] = None
            st.session_state[f"_iwtbl_clear__iwtbl_{_CE_CH}"] = True
            st.rerun()
        else:
            st.session_state["ce_selected"] = clicked
            st.rerun()

    # ── Fund Intelligence panel ───────────────────────────────────────────────
    sel_ticker = st.session_state["ce_selected"]
    selected_product = next(
        (p for p in page_items if p.ticker == sel_ticker), None
    ) if sel_ticker else None

    if selected_product:
        st.markdown("---")
        st.markdown(f"#### 🔍 {selected_product.ticker} — Fund Intelligence")
        _render_detail_panel(selected_product, prices)
