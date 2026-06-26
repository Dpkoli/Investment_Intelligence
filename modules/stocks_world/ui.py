"""Stocks & Shares World module — Streamlit renderer with deep-dive panel."""
from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from .data import STOCKS_REGISTRY, StockProduct, ALL_COUNTRIES, ALL_SECTORS, ALL_INDEXES, fetch_prices
from modules.shared import html_table as _tbl

_PAGE_SIZE = 20
_CH = "iw-tbl-sw-v1"


def _safe_num(v) -> Optional[float]:
    try:
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def _live_prices(tickers: tuple) -> dict:
    return fetch_prices(list(tickers))


@st.cache_data(ttl=900, show_spinner=False)
def _fetch_news(ticker: str) -> list[dict]:
    try:
        import yfinance as yf
        raw_news = yf.Ticker(ticker).news or []
        result = []
        for item in raw_news[:10]:
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
            provider = content.get("provider") or {}
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
            result.append({"title": title, "link": str(link).strip(), "publisher": str(publisher).strip(), "ts": ts})
        return result
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_fundamentals(ticker: str) -> dict:
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        return {
            "pe_ratio":       _safe_num(info.get("trailingPE") or info.get("forwardPE")),
            "eps":            _safe_num(info.get("trailingEps")),
            "revenue_bn":     _safe_num((info.get("totalRevenue") or 0) / 1e9),
            "net_income_bn":  _safe_num((info.get("netIncomeToCommon") or 0) / 1e9),
            "profit_margin":  _safe_num((info.get("profitMargins") or 0) * 100),
            "debt_equity":    _safe_num(info.get("debtToEquity")),
            "roe":            _safe_num((info.get("returnOnEquity") or 0) * 100),
            "dividend_yield": _safe_num((info.get("dividendYield") or 0) * 100),
            "52w_high":       _safe_num(info.get("fiftyTwoWeekHigh")),
            "52w_low":        _safe_num(info.get("fiftyTwoWeekLow")),
            "beta":           _safe_num(info.get("beta")),
            "analyst_rating": str(info.get("recommendationKey") or "—").upper(),
            "target_price":   _safe_num(info.get("targetMeanPrice")),
            "num_analysts":   info.get("numberOfAnalystOpinions") or 0,
            "description":    str(info.get("longBusinessSummary") or ""),
        }
    except Exception:
        return {}


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

        def _ret(n: int) -> Optional[float]:
            if len(closes) < n:
                return None
            past = _safe_num(closes.iloc[-n])
            if past and past != 0:
                return round((current - past) / past * 100, 2)  # type: ignore[operator]
            return None

        cur_year = closes.index[-1].year
        ytd_s = closes[closes.index.year == cur_year]
        ytd: Optional[float] = None
        if not ytd_s.empty:
            start = _safe_num(ytd_s.iloc[0])
            if start and start != 0:
                ytd = round((current - start) / start * 100, 2)  # type: ignore[operator]

        return {
            "dates":  [d.strftime("%Y-%m-%d") for d in closes.index[-252:]],
            "prices": [_safe_num(v) for v in closes.values[-252:]],
            "1M": _ret(21), "3M": _ret(63), "6M": _ret(126),
            "YTD": ytd,     "1Y": _ret(252), "5Y": _ret(1260),
        }
    except Exception:
        return {}


def _fmt_ts(ts: int) -> str:
    if not ts:
        return ""
    age_h = (time.time() - ts) / 3600
    if age_h < 1:
        return f"{int(age_h * 60)}m ago"
    if age_h < 24:
        return f"{int(age_h)}h ago"
    return f"{int(age_h / 24)}d ago"


def _pct_color(v: Optional[float]) -> str:
    if v is None:
        return "—"
    color = "#149453" if v >= 0 else "#E53535"
    arrow = "▲" if v >= 0 else "▼"
    return f'<span style="color:{color};font-weight:600">{arrow}{abs(v):.2f}%</span>'


def _render_deep_dive(stock: StockProduct, prices: dict) -> None:
    """Render the 5-panel deep-dive dashboard for the selected stock."""
    px_data = prices.get(stock.ticker, {})
    price   = _safe_num(px_data.get("price"))
    chg     = _safe_num(px_data.get("chg_pct"))
    price_str = f"{stock.currency} {price:,.2f}" if price else "—"
    chg_color = "#149453" if (chg is not None and chg >= 0) else "#E53535"
    chg_str   = f"{chg:+.2f}%" if chg is not None else "—"

    st.markdown(
        f'<div style="background:#071D35;border-radius:10px;padding:0.85rem 1.1rem;'
        f'margin-bottom:0.65rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap">'
        f'<div><div style="font-size:0.65rem;color:#5A8EBB;font-weight:600;letter-spacing:0.1em;text-transform:uppercase">'
        f'{stock.country} · {stock.sector}</div>'
        f'<div style="font-size:1.5rem;font-weight:800;color:#ffffff;letter-spacing:-0.02em">{stock.ticker}</div>'
        f'<div style="font-size:0.78rem;color:rgba(255,255,255,0.65)">{stock.name}</div></div>'
        f'<div style="margin-left:auto;text-align:right">'
        f'<div style="font-size:1.8rem;font-weight:700;color:#ffffff;line-height:1">{price_str}</div>'
        f'<div style="font-size:0.9rem;font-weight:700;color:{chg_color}">{chg_str} today</div>'
        f'<div style="font-size:0.65rem;color:#5A8EBB;margin-top:0.2rem">{stock.index_member}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    tab_news, tab_analysts, tab_technical, tab_financial, tab_performance = st.tabs([
        "📰 Latest News",
        "🧑‍💼 Analyst Ratings",
        "📈 Technical Analysis",
        "💰 Financial Analysis",
        "🏆 Performance",
    ])

    # ── Tab 1: Latest News ────────────────────────────────────────────────────
    with tab_news:
        with st.spinner("Loading news…"):
            news_items = _fetch_news(stock.ticker)
        if news_items:
            for item in news_items[:8]:
                title    = item.get("title", "—")
                link     = item.get("link", "")
                pub      = item.get("publisher", "")
                time_str = _fmt_ts(item.get("ts", 0))
                title_html = (
                    f'<a href="{link}" target="_blank" style="color:#071D35;text-decoration:none;'
                    f'font-weight:600;font-size:0.82rem;line-height:1.45">{title}</a>'
                    if link else
                    f'<span style="color:#071D35;font-weight:600;font-size:0.82rem">{title}</span>'
                )
                st.markdown(
                    f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-left:3px solid #1AB868;'
                    f'border-radius:0 8px 8px 0;padding:0.5rem 0.8rem;margin-bottom:0.3rem">'
                    f'{title_html}'
                    f'<div style="color:#5A8EBB;font-size:0.68rem;margin-top:0.1rem">{pub} · {time_str}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No recent news available.")

    # ── Tab 2: Analyst Ratings ────────────────────────────────────────────────
    with tab_analysts:
        with st.spinner("Loading analyst data…"):
            fund = _fetch_fundamentals(stock.ticker)

        rating    = fund.get("analyst_rating", "—")
        target    = fund.get("target_price")
        n_analysts = fund.get("num_analysts", 0)

        rating_color = {
            "BUY": "#149453", "STRONG_BUY": "#149453",
            "HOLD": "#E8A500", "NEUTRAL": "#E8A500",
            "SELL": "#E53535", "UNDERPERFORM": "#E53535",
        }.get(rating, "#5A8EBB")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-top:3px solid {rating_color};'
                f'border-radius:8px;padding:0.75rem;text-align:center">'
                f'<div style="font-size:0.65rem;color:#5A8EBB;font-weight:700;text-transform:uppercase;letter-spacing:0.1em">Consensus</div>'
                f'<div style="font-size:1.6rem;font-weight:800;color:{rating_color};margin:0.2rem 0">{rating}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with c2:
            tp_str = f"${target:,.2f}" if target else "—"
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-top:3px solid #2B5A85;'
                f'border-radius:8px;padding:0.75rem;text-align:center">'
                f'<div style="font-size:0.65rem;color:#5A8EBB;font-weight:700;text-transform:uppercase;letter-spacing:0.1em">Price Target</div>'
                f'<div style="font-size:1.6rem;font-weight:800;color:#071D35;margin:0.2rem 0">{tp_str}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-top:3px solid #3A72A0;'
                f'border-radius:8px;padding:0.75rem;text-align:center">'
                f'<div style="font-size:0.65rem;color:#5A8EBB;font-weight:700;text-transform:uppercase;letter-spacing:0.1em">No. Analysts</div>'
                f'<div style="font-size:1.6rem;font-weight:800;color:#071D35;margin:0.2rem 0">{n_analysts}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        desc = fund.get("description", "")
        if desc:
            st.markdown(
                f'<div style="background:#EEF4FB;border:1px solid #D9E8F5;border-radius:8px;'
                f'padding:0.75rem 1rem;margin-top:0.75rem;font-size:0.8rem;color:#2B5A85;line-height:1.65">'
                f'{desc[:600]}{"…" if len(desc) > 600 else ""}</div>',
                unsafe_allow_html=True,
            )

    # ── Tab 3: Technical Analysis ─────────────────────────────────────────────
    with tab_technical:
        with st.spinner("Loading price history…"):
            perf = _fetch_performance(stock.ticker)

        if perf.get("dates") and perf.get("prices"):
            fig = go.Figure()
            dates  = perf["dates"]
            prices = perf["prices"]
            clean_prices = [p for p in prices if p is not None]
            if len(clean_prices) >= 20:
                # 20-day MA
                ma20 = pd.Series(clean_prices).rolling(20).mean().tolist()
                fig.add_trace(go.Scatter(
                    x=dates, y=ma20, mode="lines",
                    line={"color": "#E8A500", "width": 1, "dash": "dot"},
                    name="20-day MA", hoverinfo="skip",
                ))
            fig.add_trace(go.Scatter(
                x=dates, y=prices, mode="lines",
                line={"color": "#1AB868", "width": 2},
                name=stock.ticker, fill="tozeroy",
                fillcolor="rgba(26,184,104,0.08)",
            ))
            fig.update_layout(
                height=280, margin={"t": 10, "b": 30, "l": 50, "r": 10},
                paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
                legend={"orientation": "h", "y": 1.08, "x": 0, "font": {"size": 10}},
                xaxis={"gridcolor": "#EEF4FB", "tickfont": {"color": "#5A8EBB", "size": 10}},
                yaxis={"gridcolor": "#EEF4FB", "tickfont": {"color": "#5A8EBB", "size": 10}},
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Price history unavailable.")

    # ── Tab 4: Financial Analysis ─────────────────────────────────────────────
    with tab_financial:
        with st.spinner("Loading fundamentals…"):
            fund = _fetch_fundamentals(stock.ticker)

        def _fmt(v, fmt=".2f", suffix=""):
            if v is None:
                return "—"
            return f"{v:{fmt}}{suffix}"

        metrics = [
            ("P/E Ratio",         _fmt(fund.get("pe_ratio"))),
            ("EPS (TTM)",         _fmt(fund.get("eps"), ".2f", f" {stock.currency}")),
            ("Revenue",           _fmt(fund.get("revenue_bn"), ".1f", "Bn")),
            ("Net Income",        _fmt(fund.get("net_income_bn"), ".2f", "Bn")),
            ("Profit Margin",     _fmt(fund.get("profit_margin"), ".1f", "%")),
            ("Return on Equity",  _fmt(fund.get("roe"), ".1f", "%")),
            ("Debt / Equity",     _fmt(fund.get("debt_equity"))),
            ("Dividend Yield",    _fmt(fund.get("dividend_yield"), ".2f", "%")),
            ("Beta",              _fmt(fund.get("beta"))),
            ("52-week High",      _fmt(fund.get("52w_high"), ".2f", f" {stock.currency}")),
            ("52-week Low",       _fmt(fund.get("52w_low"),  ".2f", f" {stock.currency}")),
        ]

        cols = st.columns(3)
        for idx, (label, val) in enumerate(metrics):
            with cols[idx % 3]:
                st.markdown(
                    f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-radius:8px;'
                    f'padding:0.55rem 0.75rem;margin-bottom:0.4rem">'
                    f'<div style="font-size:0.65rem;color:#5A8EBB;font-weight:700;text-transform:uppercase;letter-spacing:0.08em">{label}</div>'
                    f'<div style="font-size:1.1rem;font-weight:700;color:#071D35;margin-top:0.1rem">{val}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Tab 5: Performance ────────────────────────────────────────────────────
    with tab_performance:
        with st.spinner("Loading performance data…"):
            perf = _fetch_performance(stock.ticker)

        periods = [("1M", "1 Month"), ("3M", "3 Months"), ("6M", "6 Months"),
                   ("YTD", "Year to Date"), ("1Y", "1 Year"), ("5Y", "5 Years")]

        perf_cols = st.columns(len(periods))
        for col, (key, label) in zip(perf_cols, periods):
            v = _safe_num(perf.get(key))
            color = "#149453" if v and v >= 0 else "#E53535"
            val_str = f"{v:+.2f}%" if v is not None else "—"
            with col:
                st.markdown(
                    f'<div style="background:#ffffff;border:1px solid #D9E8F5;border-radius:8px;'
                    f'padding:0.6rem 0.4rem;text-align:center">'
                    f'<div style="font-size:0.6rem;color:#5A8EBB;font-weight:700;text-transform:uppercase;letter-spacing:0.06em">{label}</div>'
                    f'<div style="font-size:1.1rem;font-weight:800;color:{color};margin:0.15rem 0">{val_str}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        current_price = _safe_num(prices.get(stock.ticker, {}).get("price"))
        h52 = _safe_num(perf.get("52w_high") if False else _fetch_fundamentals.cache_clear() if False else None) or _safe_num(_fetch_fundamentals(stock.ticker).get("52w_high"))
        l52 = _safe_num(_fetch_fundamentals(stock.ticker).get("52w_low"))
        if current_price and h52 and l52 and h52 > l52:
            pct_from_high = (current_price - h52) / h52 * 100
            pct_from_low  = (current_price - l52) / l52 * 100
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(
                    f'<div style="background:#FEF2F2;border:1px solid #FBCACA;border-radius:8px;padding:0.6rem 0.9rem">'
                    f'<div style="font-size:0.65rem;color:#9B1515;font-weight:700;text-transform:uppercase">vs 52-week High</div>'
                    f'<div style="font-size:1.1rem;font-weight:800;color:#E53535">{pct_from_high:+.2f}%</div>'
                    f'<div style="font-size:0.65rem;color:#9B1515">High: ${h52:,.2f}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f'<div style="background:#EDFAF3;border:1px solid #A3E8C4;border-radius:8px;padding:0.6rem 0.9rem">'
                    f'<div style="font-size:0.65rem;color:#149453;font-weight:700;text-transform:uppercase">vs 52-week Low</div>'
                    f'<div style="font-size:1.1rem;font-weight:800;color:#149453">{pct_from_low:+.2f}%</div>'
                    f'<div style="font-size:0.65rem;color:#149453">Low: ${l52:,.2f}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


def render() -> None:
    """Main entry point for Stocks & Shares World module."""
    st.markdown("<h2 class='iw-module-header'>Stocks & Shares World — Global Public Companies</h2>", unsafe_allow_html=True)
    st.markdown(
        '<p style="font-size:0.82rem;color:#5A8EBB;margin:0 0 0.75rem 0">'
        'Browse and deep-dive into individual public companies across the US, UK, Europe, and Asia. '
        'Click any row to open a full analysis dashboard.</p>',
        unsafe_allow_html=True,
    )

    # ── Session state ─────────────────────────────────────────────────────────
    if "sw_page"     not in st.session_state: st.session_state["sw_page"]     = 0
    if "sw_selected" not in st.session_state: st.session_state["sw_selected"] = None

    # ── Filters ───────────────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        sel_countries = st.multiselect("Country", ALL_COUNTRIES, placeholder="All countries", key="sw_countries")
    with fc2:
        sel_sectors   = st.multiselect("Sector",  ALL_SECTORS,   placeholder="All sectors",   key="sw_sectors")
    with fc3:
        sel_indexes   = st.multiselect("Index",   ALL_INDEXES,   placeholder="All indexes",   key="sw_indexes")

    fs1, fs2 = st.columns([1, 3])
    with fs1:
        min_cap = st.selectbox("Min Market Cap", ["Any", ">$10Bn", ">$50Bn", ">$100Bn", ">$500Bn"], key="sw_mincap")
    with fs2:
        search_q = st.text_input("Search", placeholder="Ticker, name, sector…", key="sw_search", label_visibility="collapsed")

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = list(STOCKS_REGISTRY)
    if sel_countries:
        filtered = [s for s in filtered if s.country in sel_countries]
    if sel_sectors:
        filtered = [s for s in filtered if s.sector in sel_sectors]
    if sel_indexes:
        filtered = [s for s in filtered if any(idx in s.index_member for idx in sel_indexes)]
    cap_map = {"Any": 0, ">$10Bn": 10, ">$50Bn": 50, ">$100Bn": 100, ">$500Bn": 500}
    min_cap_val = cap_map.get(min_cap, 0)
    if min_cap_val:
        filtered = [s for s in filtered if s.market_cap_bn >= min_cap_val]
    if search_q:
        q = search_q.lower()
        filtered = [s for s in filtered if q in s.ticker.lower() or q in s.name.lower() or q in s.sector.lower() or q in s.country.lower()]

    # ── Pagination ────────────────────────────────────────────────────────────
    total    = len(filtered)
    n_pages  = max(1, math.ceil(total / _PAGE_SIZE))
    page     = min(st.session_state["sw_page"], n_pages - 1)
    page_items = filtered[page * _PAGE_SIZE : (page + 1) * _PAGE_SIZE]

    st.caption(f"**{total}** companies — click a row to open deep-dive analysis")

    # ── Live prices ───────────────────────────────────────────────────────────
    tickers = tuple(s.ticker for s in page_items)
    with st.spinner("Fetching live prices…"):
        prices = _live_prices(tickers)

    # ── Build table rows ──────────────────────────────────────────────────────
    rows = []
    for s in page_items:
        px_data = prices.get(s.ticker, {})
        price   = _safe_num(px_data.get("price"))
        chg     = _safe_num(px_data.get("chg_pct"))
        price_str = f"{s.currency} {price:,.2f}" if price else "—"
        chg_str   = f"{chg:+.2f}%" if chg is not None else "—"
        rows.append({
            "Ticker":    s.ticker,
            "Name":      s.name,
            "Country":   s.country,
            "Sector":    s.sector,
            "Index":     s.index_member or "—",
            "Mkt Cap":   f"${s.market_cap_bn:.0f}Bn" if s.market_cap_bn else "—",
            "Price":     price_str,
            "1d %":      chg_str,
        })

    # Determine selected index for highlight
    sel_ticker = st.session_state["sw_selected"]
    sel_idx = next((i for i, s in enumerate(page_items) if s.ticker == sel_ticker), None)

    # Column class mapping
    col_classes = {
        "Ticker":  "td-mono",
        "Price":   "td-mono",
    }

    # Render table
    new_sel = _tbl.render(
        rows=rows,
        columns=[
            ("Ticker", "Ticker"), ("Name", "Name"), ("Country", "Country"),
            ("Sector", "Sector"), ("Index", "Index"), ("Mkt Cap", "Mkt Cap ($Bn)"),
            ("Price", "Price"), ("1d %", "1d %"),
        ],
        channel_placeholder=_CH,
        selected_idx=sel_idx,
        col_classes=col_classes,
    )

    # Handle selection
    if new_sel is not None and 0 <= new_sel < len(page_items):
        clicked_ticker = page_items[new_sel].ticker
        if st.session_state["sw_selected"] == clicked_ticker:
            st.session_state["sw_selected"] = None
            st.session_state[f"_iwtbl_clear__iwtbl_{_CH}"] = True
            st.rerun()
        else:
            st.session_state["sw_selected"] = clicked_ticker
            st.rerun()
    elif new_sel is None and sel_idx is None:
        pass  # nothing selected, no change

    # ── Pagination controls ───────────────────────────────────────────────────
    if n_pages > 1:
        pp1, pp2, pp3 = st.columns([1, 3, 1])
        with pp1:
            if st.button("← Prev", disabled=(page == 0), key="sw_prev", use_container_width=True):
                st.session_state["sw_page"] = page - 1
                st.session_state["sw_selected"] = None
                st.rerun()
        with pp2:
            st.markdown(
                f'<p style="text-align:center;color:#5A8EBB;margin:0.4rem 0">'
                f'Page {page + 1} of {n_pages}</p>',
                unsafe_allow_html=True,
            )
        with pp3:
            if st.button("Next →", disabled=(page == n_pages - 1), key="sw_next", use_container_width=True):
                st.session_state["sw_page"] = page + 1
                st.session_state["sw_selected"] = None
                st.rerun()

    # ── Deep-dive panel ───────────────────────────────────────────────────────
    sel_ticker = st.session_state["sw_selected"]
    selected_stock = next((s for s in page_items if s.ticker == sel_ticker), None)
    if selected_stock:
        st.markdown("---")
        _render_deep_dive(selected_stock, prices)
