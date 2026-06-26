"""Precious Metals module — Streamlit renderer with fund intelligence panel."""
from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from .data import METALS_REGISTRY, MetalType, fetch_prices
from modules.shared import inject_autocomplete as _inject_autocomplete

_PAGE_SIZE = 20
_SPOT_TICKERS = ["GC=F", "SI=F", "PL=F", "PA=F"]

_METAL_COLOR = {
    MetalType.GOLD:      "#FFD700",
    MetalType.SILVER:    "#C0C0C0",
    MetalType.PLATINUM:  "#E5E4E2",
    MetalType.PALLADIUM: "#CED0DD",
}


# ── Search callbacks ──────────────────────────────────────────────────────────

def _on_pm_search_change() -> None:
    st.session_state["pm_page"] = 0
    st.session_state["pm_selected"] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_num(v) -> Optional[float]:
    try:
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def _live_prices(tickers: tuple) -> dict:
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
            pct  = _safe_num(raw) or 0.0
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
    "wisdomtree":   lambda t: f"https://www.wisdomtree.com/investments/etfs/{t.lower()}",
    "vaneck":       lambda t: f"https://www.vaneck.com/us/en/{t.lower()}/",
    "proshares":    lambda t: f"https://www.proshares.com/our-etfs/{t.lower()}/",
    "sprott":       lambda t: f"https://sprott.com/investment-strategies/etfs/{t.lower()}/",
    "global x":     lambda t: f"https://www.globalxetfs.com/funds/{t.lower()}/",
    "invesco":      lambda t: f"https://www.invesco.com/us/financial-products/etfs/product-detail?audienceType=Investor&ticker={t}",
    "abrdn":        lambda t: f"https://www.aberdeenetfs.com/",
    "direxion":     lambda t: f"https://www.direxion.com/products/{t.lower()}/",
    "etfmg":        lambda t: f"https://etfmg.com/{t.lower()}/",
    "graniteShares":lambda t: f"https://graniteshares.com/institutional/us/en-us/etfs/{t.lower()}/",
    "us global":    lambda t: f"https://www.usfunds.com/",
}


def _fund_url(ticker: str, issuer: Optional[str]) -> str:
    t_clean = ticker.split(".")[0].upper()
    if issuer:
        for key, fn in _ISSUER_URL_MAP.items():
            if key in issuer.lower():
                return fn(t_clean)
    return f"https://finance.yahoo.com/quote/{ticker}"


# ── Detail panel ──────────────────────────────────────────────────────────────

def _render_detail_panel(p, prices: dict) -> None:
    yf_key  = p.yf_ticker or p.ticker
    px_data = prices.get(yf_key, {})
    price   = _safe_num(px_data.get("price"))
    chg     = _safe_num(px_data.get("chg_pct"))

    price_str = f"${price:,.4f}" if price else "—"
    chg_color = "#1AB868" if (chg is not None and chg >= 0) else "#E53535"
    chg_str   = f"{chg:+.2f}%" if chg is not None else "—"
    lev_str   = f"{p.leverage:+.0f}×" if p.leverage != 1.0 else "1×"

    metal_name = p.metal.value if hasattr(p.metal, "value") else str(p.metal)
    color = _METAL_COLOR.get(p.metal, "#FFD700")

    issuer_url = _fund_url(p.ticker, p.issuer)
    yahoo_url  = f"https://finance.yahoo.com/quote/{p.ticker}"

    ter_span  = f'<span>💰 TER&nbsp;<b style="color:#071D35">{p.expense_ratio:.2f}%</b></span>' if p.expense_ratio else ""
    aum_span  = f'<span>📦 AUM&nbsp;<b style="color:#071D35">${p.aum_bn:.1f}bn</b></span>'        if p.aum_bn        else ""
    isin_span = f'<span>🔢&nbsp;<b style="color:#071D35">{p.isin}</b></span>'                       if p.isin          else ""

    st.markdown(
        f"""
<div style="background:#ffffff;border:1px solid #D9E8F5;border-left:4px solid {color};
     border-radius:10px;padding:1rem 1.2rem;margin:0.4rem 0 0.75rem 0">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:0.5rem">
    <div>
      <span style="color:{color};font-size:0.68rem;font-weight:700;letter-spacing:0.12em">
        {metal_name.upper()} &middot; {p.product_type}
      </span><br>
      <span style="font-size:1.25rem;font-weight:700">{p.ticker}</span>&nbsp;
      <span style="color:#2B5A85;font-size:0.87rem">{p.name}</span>
    </div>
    <div style="text-align:right">
      <div style="font-size:1.3rem;font-weight:700">{price_str}</div>
      <div style="font-size:0.87rem;color:{chg_color}">{chg_str} today</div>
    </div>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:1rem;margin-top:0.6rem;font-size:0.75rem;color:#999">
    <span>🏢&nbsp;<b style="color:#071D35">{p.issuer or "—"}</b></span>
    <span>🏛&nbsp;<b style="color:#071D35">{p.exchange}</b></span>
    <span>💱&nbsp;<b style="color:#071D35">{p.currency}</b></span>
    <span>⚡&nbsp;<b style="color:#071D35">Leverage {lev_str}</b></span>
    {ter_span}
    {aum_span}
    {isin_span}
  </div>
</div>""",
        unsafe_allow_html=True,
    )

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
                marker_color=color,
                text=[f"{v:.1f}%" for v in h_df["pct"]],
                textposition="outside",
                hovertemplate="<b>%{customdata}</b> (%{y})<br>%{x:.2f}%<extra></extra>",
            ))
            fig_h.update_layout(
                height=max(180, len(h_df) * 28),
                margin={"t": 5, "b": 5, "l": 10, "r": 55},
                paper_bgcolor="#EEF4FB",
                plot_bgcolor="#EEF4FB",
                xaxis={"visible": False},
                yaxis={"color": "#888", "tickfont": {"size": 11}, "autorange": "reversed"},
                showlegend=False,
            )
            st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})
        else:
            st.caption("Holdings data not available for this product.")

    with col_p:
        st.markdown("##### 📈 Performance")
        if perf and perf.get("dates"):
            _TF_DAYS = {"1M": 21, "3M": 63, "6M": 126, "1Y": 252, "5Y": 1260, "All": None}
            tf = st.radio("", list(_TF_DAYS.keys()), index=3, horizontal=True,
                          key=f"pm_perf_tf_{p.ticker}")
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
                paper_bgcolor="#EEF4FB",
                plot_bgcolor="#EEF4FB",
                xaxis={"visible": False},
                yaxis={"color": "#5A8EBB", "gridcolor": "#D9E8F5", "tickformat": "$,.0f"},
                showlegend=False,
            )
            st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar": False})

            periods = [("1M", perf.get("1M")), ("3M", perf.get("3M")),
                       ("6M", perf.get("6M")), ("YTD", perf.get("YTD")),
                       ("1Y", perf.get("1Y")), ("5Y", perf.get("5Y"))]
            cells = ""
            for lbl, val in periods:
                is_tf = lbl == tf
                if val is not None:
                    v_color = "#1AB868" if val >= 0 else "#E53535"
                    val_str = f"{val:+.1f}%"
                else:
                    v_color, val_str = "#555", "—"
                border = "border-bottom:2px solid #1AB868;" if is_tf else ""
                cells += (
                    f'<div style="text-align:center;flex:1;{border}">'
                    f'<div style="font-size:0.62rem;color:#5A8EBB">{lbl}</div>'
                    f'<div style="font-size:0.8rem;font-weight:700;color:{v_color}">{val_str}</div>'
                    f'</div>'
                )
            st.markdown(
                f'<div style="display:flex;gap:0.25rem;margin-top:0.15rem">{cells}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("Performance data not available.")

    st.markdown("##### 📰 Recent News")
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

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1:
        st.link_button(f"🌐 {p.issuer or 'Fund'} Website →", issuer_url, use_container_width=True)
    with b2:
        st.link_button("📈 Yahoo Finance →", yahoo_url, use_container_width=True)


# ── Main render ───────────────────────────────────────────────────────────────

def render() -> None:
    st.markdown("<h2 class='iw-module-header'>Precious Metals — Spot, Physical ETPs & Mining Equity Intelligence</h2>", unsafe_allow_html=True)
    st.caption(f"{len(METALS_REGISTRY)} products tracked — Gold · Silver · Platinum · Palladium")

    if "pm_page" not in st.session_state:
        st.session_state["pm_page"] = 0
    if "pm_selected" not in st.session_state:
        st.session_state["pm_selected"] = None

    # ── Live Spot Prices ──────────────────────────────────────────────────────
    st.markdown("### Live Spot & Futures")
    spot_prices = _live_prices(tuple(_SPOT_TICKERS))
    sc1, sc2, sc3, sc4 = st.columns(4)
    for col, (metal, ticker, color_key) in zip(
        [sc1, sc2, sc3, sc4],
        [("Gold",      "GC=F", MetalType.GOLD),
         ("Silver",    "SI=F", MetalType.SILVER),
         ("Platinum",  "PL=F", MetalType.PLATINUM),
         ("Palladium", "PA=F", MetalType.PALLADIUM)],
    ):
        px_data   = spot_prices.get(ticker, {})
        price     = _safe_num(px_data.get("price"))
        chg       = _safe_num(px_data.get("chg_pct"))
        color     = _METAL_COLOR.get(color_key, "#FFD700")
        price_str = f"${price:,.2f}" if price else "—"
        chg_color = "#149453" if (chg is not None and chg >= 0) else "#E53535"
        chg_str   = f"{chg:+.2f}%" if chg is not None else "—"
        with col:
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid {color};border-top:3px solid {color};'
                f'border-radius:8px;padding:0.75rem 0.9rem;text-align:center;'
                f'box-shadow:0 1px 3px rgba(7,29,53,0.05)">'
                f'<div style="font-size:0.65rem;color:{color};font-weight:800;'
                f'letter-spacing:0.14em;text-transform:uppercase;margin-bottom:0.15rem">{metal}</div>'
                f'<div style="font-size:1.75rem;font-weight:800;'
                f'color:#071D35;line-height:1.1;margin:0.15rem 0">{price_str}</div>'
                f'<div style="font-size:0.82rem;font-weight:700;color:{chg_color};margin-bottom:0.1rem">{chg_str}</div>'
                f'<div style="font-size:0.64rem;color:#5A8EBB;font-family:\'JetBrains Mono\',monospace;'
                f'letter-spacing:0.04em">{ticker}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Filters ───────────────────────────────────────────────────────────────
    metals    = sorted(set(p.metal.value for p in METALS_REGISTRY))
    ptypes    = sorted(set(p.product_type for p in METALS_REGISTRY))
    exchanges = sorted(set(p.exchange for p in METALS_REGISTRY))
    issuers   = sorted(set(p.issuer for p in METALS_REGISTRY if p.issuer))

    col_m, col_pt, col_ex, col_iss = st.columns(4)
    with col_m:
        sel_metals  = st.multiselect("Metal", metals, placeholder="All metals", key="pm_metals")
    with col_pt:
        sel_types   = st.multiselect("Product Type", ptypes, placeholder="All types", key="pm_types")
    with col_ex:
        sel_ex      = st.multiselect("Exchange", exchanges, placeholder="All exchanges", key="pm_exchanges")
    with col_iss:
        sel_issuers = st.multiselect("Issuer", issuers, placeholder="All issuers", key="pm_issuers")

    col_phys, col_search = st.columns([1, 3])
    with col_phys:
        show_phys = st.toggle("Physically-backed only", value=False, key="pm_phys")
    with col_search:
        search_q = st.text_input(
            "Search products",
            value="",
            placeholder="Ticker, name, issuer…",
            key="pm_search",
            on_change=_on_pm_search_change,
        )

    # Build autocomplete items
    import json as _json
    _ac_items = []
    for _p in METALS_REGISTRY:
        _metal = _p.metal.value if hasattr(_p.metal, "value") else str(_p.metal)
        _ac_items.append({
            "l": f"{_p.ticker} — {_p.name}",
            "v": _p.ticker,
            "b": f"{_metal} · {_p.product_type}",
            "s": f"{_p.ticker.lower()} {_p.name.lower()} {(_p.issuer or '').lower()} {_p.product_type.lower()} {_metal.lower()}",
        })
    _inject_autocomplete(_json.dumps(_ac_items, ensure_ascii=False), "Ticker, name, issuer…")

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = list(METALS_REGISTRY)
    if sel_metals:
        filtered = [p for p in filtered if p.metal.value in sel_metals]
    if sel_types:
        filtered = [p for p in filtered if p.product_type in sel_types]
    if sel_ex:
        filtered = [p for p in filtered if p.exchange in sel_ex]
    if sel_issuers:
        filtered = [p for p in filtered if p.issuer in sel_issuers]
    if show_phys:
        filtered = [p for p in filtered if p.physically_backed]
    if search_q:
        q = search_q.lower()
        filtered = [
            p for p in filtered
            if q in p.ticker.lower() or q in p.name.lower()
            or q in (p.issuer or "").lower() or q in p.product_type.lower()
        ]

    st.caption(f"**{len(filtered)}** products — select a row to view fund intelligence")

    # ── Live prices ───────────────────────────────────────────────────────────
    all_yf = tuple(p.yf_ticker or p.ticker for p in filtered if (p.yf_ticker or p.ticker))
    prices = _live_prices(all_yf) if all_yf else {}

    # ── Pagination ────────────────────────────────────────────────────────────
    total_pages = max(1, (len(filtered) + _PAGE_SIZE - 1) // _PAGE_SIZE)
    page = max(0, min(st.session_state["pm_page"], total_pages - 1))

    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        if st.button("← Prev", key="pm_prev", disabled=page == 0):
            st.session_state["pm_page"] = page - 1
            st.session_state["pm_selected"] = None
            st.rerun()
    with c2:
        st.caption(f"Page {page + 1} / {total_pages}")
    with c3:
        if st.button("Next →", key="pm_next", disabled=page >= total_pages - 1):
            st.session_state["pm_page"] = page + 1
            st.session_state["pm_selected"] = None
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
            "Ticker":       p.ticker,
            "Name":         p.name,
            "Metal":        p.metal.value if hasattr(p.metal, "value") else str(p.metal),
            "Type":         p.product_type,
            "Exchange":     p.exchange,
            "Physical":     "✅" if p.physically_backed else "—",
            "Leverage":     f"{p.leverage:+.0f}×" if p.leverage != 1.0 else "1×",
            "TER":          f"{p.expense_ratio:.2f}%" if p.expense_ratio else "—",
            "AUM ($bn)":    f"{p.aum_bn:.1f}" if p.aum_bn else "—",
            "Issuer":       p.issuer or "—",
            "Price":        f"${price:,.4f}" if price is not None else "—",
            "1d %":         f"{chg:+.2f}%" if chg is not None else "—",
        })

    df = pd.DataFrame(rows)

    def _style_pm_table(df: pd.DataFrame):
        base = "background-color:#ffffff;color:#2B5A85;"
        styles = pd.DataFrame(base, index=df.index, columns=df.columns)
        styles["Ticker"] = "background-color:#ffffff;color:#071D35;font-weight:700;"
        styles["Name"]   = "background-color:#ffffff;color:#071D35;"
        styles["Price"]  = "background-color:#ffffff;color:#071D35;font-family:'JetBrains Mono',monospace;"
        for i, v in enumerate(df["1d %"]):
            s = str(v)
            if "%" in s:
                try:
                    num = float(s.replace("%", "").replace("+", ""))
                    clr = "#149453" if num > 0 else "#E53535" if num < 0 else "#5A8EBB"
                    styles.iloc[i, df.columns.get_loc("1d %")] = f"background-color:#ffffff;color:{clr};font-weight:700;"
                except ValueError:
                    pass
        return styles

    table_event = st.dataframe(
        df.style.apply(_style_pm_table, axis=None).set_table_styles([
            {"selector": "th", "props": [
                ("background-color", "#EEF4FB"), ("color", "#5A8EBB"),
                ("font-weight", "700"), ("font-size", "0.72rem"),
                ("text-transform", "uppercase"), ("letter-spacing", "0.07em"),
            ]},
        ]),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"pm_tbl_p{page}",
        column_config={
            "1d %":      st.column_config.TextColumn("1d %"),
            "AUM ($bn)": st.column_config.TextColumn("AUM ($bn)"),
            "Leverage":  st.column_config.TextColumn("Lev."),
            "Physical":  st.column_config.TextColumn("Phys."),
        },
    )

    # Full-row click selects; clicking same row again toggles off
    sel_rows = (
        table_event.selection.rows
        if table_event and table_event.selection
        else []
    )
    if sel_rows and 0 <= sel_rows[0] < len(page_items):
        clicked = page_items[sel_rows[0]].ticker
        if st.session_state.get("pm_selected") == clicked:
            st.session_state["pm_selected"] = None
            st.session_state.pop(f"pm_tbl_p{page}", None)
            st.rerun()
        else:
            st.session_state["pm_selected"] = clicked
    else:
        st.session_state["pm_selected"] = None

    # ── Fund Intelligence panel ───────────────────────────────────────────────
    sel_ticker = st.session_state["pm_selected"]
    selected_product = next(
        (p for p in page_items if p.ticker == sel_ticker), None
    ) if sel_ticker else None

    if selected_product:
        st.divider()
        st.markdown(f"### 🔍 {selected_product.ticker} — Fund Intelligence")
        _render_detail_panel(selected_product, prices)

    # ── Streaming & Royalty ───────────────────────────────────────────────────
    st.divider()
    with st.expander("💡 Streaming & Royalty Companies (Equity plays)", expanded=False):
        streaming = [p for p in METALS_REGISTRY if p.product_type == "Streaming Equity"]
        st.markdown("""
Streaming and royalty companies provide **capital-efficient** exposure to precious metals production:
- **No operational mining risk** — royalties are paid on production regardless of cost escalation
- **Natural hedge** — gold/silver price upside with capped downside (no mine cost exposure)
- **Valuation premium** — typically trade at 30-50× P/CF vs. 8-15× for miners
        """)
        for s in streaming:
            st.markdown(f"**{s.ticker}** — {s.name}: {s.notes or ''}")
