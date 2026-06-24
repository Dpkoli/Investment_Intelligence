"""Sovereign Crypto Networks — redesigned UI: Top-10 dashboard + crypto detail panel."""
from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from .data import CRYPTO_REGISTRY, CryptoTier, FCAStatus

# ── Top-10 tickers to feature on main page ────────────────────────────────────
_TOP10 = [
    ("BTC-USD",  "Bitcoin",     "BTC",  "₿"),
    ("ETH-USD",  "Ethereum",    "ETH",  "Ξ"),
    ("BNB-USD",  "BNB",         "BNB",  "⬡"),
    ("SOL-USD",  "Solana",      "SOL",  "◎"),
    ("XRP-USD",  "XRP",         "XRP",  "✕"),
    ("ADA-USD",  "Cardano",     "ADA",  "₳"),
    ("AVAX-USD", "Avalanche",   "AVAX", "🔺"),
    ("DOT-USD",  "Polkadot",    "DOT",  "●"),
    ("LINK-USD", "Chainlink",   "LINK", "🔗"),
    ("TRX-USD",  "TRON",        "TRX",  "♦"),
]

# ── Known institutional holders (public data) ─────────────────────────────────
_TOP_HOLDERS: dict[str, list[dict]] = {
    "BTC-USD": [
        {"name": "MicroStrategy (Strategy Inc.)", "amount": "592,345 BTC", "pct": "~2.82%"},
        {"name": "US Government (seized assets)", "amount": "~200,000 BTC", "pct": "~0.95%"},
        {"name": "Marathon Digital Holdings",      "amount": "47,531 BTC",  "pct": "~0.23%"},
        {"name": "Riot Platforms",                 "amount": "19,223 BTC",  "pct": "~0.09%"},
        {"name": "Tesla Inc.",                     "amount": "11,509 BTC",  "pct": "~0.05%"},
        {"name": "Galaxy Digital Holdings",        "amount": "~8,100 BTC",  "pct": "~0.04%"},
        {"name": "Block Inc. (Square)",            "amount": "8,027 BTC",   "pct": "~0.04%"},
        {"name": "Hut 8 Mining Corp",              "amount": "9,195 BTC",   "pct": "~0.04%"},
        {"name": "CleanSpark Inc.",                "amount": "6,710 BTC",   "pct": "~0.03%"},
        {"name": "BlackRock (IBIT ETF)",           "amount": "~550,000 BTC","pct": "~2.62%"},
    ],
    "ETH-USD": [
        {"name": "Ethereum Foundation",            "amount": "~300,000 ETH",  "pct": "~0.25%"},
        {"name": "BlackRock (ETHA ETF)",           "amount": "~1.5M ETH",     "pct": "~1.25%"},
        {"name": "Lido DAO (staked)",              "amount": "~9.8M ETH",     "pct": "~8.2%"},
        {"name": "Coinbase (custodian)",           "amount": "~2.5M ETH",     "pct": "~2.1%"},
        {"name": "Fidelity (FETH ETF)",            "amount": "~700,000 ETH",  "pct": "~0.58%"},
        {"name": "Grayscale (ETHE Trust)",         "amount": "~1.9M ETH",     "pct": "~1.6%"},
        {"name": "Vitalik Buterin (founder)",      "amount": "~240,000 ETH",  "pct": "~0.20%"},
        {"name": "Galaxy Digital",                 "amount": "~100,000 ETH",  "pct": "~0.08%"},
        {"name": "Aker ASA",                       "amount": "~1,170 ETH",    "pct": "~0.001%"},
        {"name": "ShuttleOne (SZO)",               "amount": "~14,000 ETH",   "pct": "~0.01%"},
    ],
    "BNB-USD": [
        {"name": "Binance Exchange (reserves)",    "amount": "~90M BNB",      "pct": "~60%"},
        {"name": "Changpeng Zhao (CZ)",            "amount": "~46M BNB",      "pct": "~30%"},
        {"name": "BNB Foundation",                 "amount": "~8M BNB",       "pct": "~5.3%"},
        {"name": "Institutional custodians",       "amount": "~2M BNB",       "pct": "~1.3%"},
    ],
    "SOL-USD": [
        {"name": "Solana Foundation",              "amount": "~130M SOL",     "pct": "~12.8%"},
        {"name": "Anatoly Yakovenko (co-founder)", "amount": "~32M SOL",      "pct": "~3.2%"},
        {"name": "Multicoin Capital",              "amount": "~25M SOL",      "pct": "~2.5%"},
        {"name": "FTX Estate (liquidating)",       "amount": "~41M SOL",      "pct": "~4.1%"},
        {"name": "Jump Crypto",                    "amount": "~15M SOL",      "pct": "~1.5%"},
        {"name": "a16z (Andreessen Horowitz)",     "amount": "~30M SOL",      "pct": "~3.0%"},
    ],
    "XRP-USD": [
        {"name": "Ripple Labs (escrowed)",         "amount": "~38.9B XRP",    "pct": "~38.9%"},
        {"name": "Ripple co-founders",             "amount": "~5.4B XRP",     "pct": "~5.4%"},
        {"name": "Brad Garlinghouse (CEO)",        "amount": "~3.4B XRP",     "pct": "~3.4%"},
        {"name": "Chris Larsen (co-founder)",      "amount": "~2.6B XRP",     "pct": "~2.6%"},
        {"name": "Tetragon Financial",             "amount": "Unknown",        "pct": "—"},
        {"name": "SBI Holdings (Japan)",           "amount": "Strategic stake","pct": "—"},
    ],
    "ADA-USD": [
        {"name": "IOHK / Input Output (dev)",      "amount": "~2.46B ADA",    "pct": "~8.2%"},
        {"name": "Cardano Foundation",             "amount": "~648M ADA",     "pct": "~2.2%"},
        {"name": "Emurgo",                         "amount": "~2.06B ADA",    "pct": "~6.9%"},
        {"name": "Charles Hoskinson (founder)",    "amount": "Unknown",        "pct": "—"},
        {"name": "Grayscale ADA Trust",            "amount": "Institutional", "pct": "—"},
    ],
    "AVAX-USD": [
        {"name": "Avalanche Foundation",           "amount": "~23M AVAX",     "pct": "~9.2%"},
        {"name": "Polychain Capital",              "amount": "~5M AVAX",      "pct": "~2.0%"},
        {"name": "a16z",                           "amount": "~4M AVAX",      "pct": "~1.6%"},
        {"name": "Coinbase Ventures",              "amount": "Strategic",      "pct": "—"},
    ],
    "DOT-USD": [
        {"name": "Web3 Foundation",                "amount": "~370M DOT",     "pct": "~3.7%"},
        {"name": "Parity Technologies",            "amount": "~90M DOT",      "pct": "~0.9%"},
        {"name": "Gavin Wood (co-founder)",        "amount": "~100M DOT",     "pct": "~1.0%"},
        {"name": "Polychain Capital",              "amount": "Strategic",      "pct": "—"},
    ],
    "LINK-USD": [
        {"name": "Chainlink Labs (team)",          "amount": "~350M LINK",    "pct": "~35%"},
        {"name": "Reserve (ecosystem fund)",       "amount": "~300M LINK",    "pct": "~30%"},
        {"name": "Sergey Nazarov (founder)",       "amount": "Strategic",      "pct": "—"},
        {"name": "Galaxy Digital",                 "amount": "Institutional", "pct": "—"},
    ],
    "TRX-USD": [
        {"name": "Justin Sun (founder)",           "amount": "~46.5B TRX",    "pct": "~46.5%"},
        {"name": "Tron Foundation",                "amount": "~3.4B TRX",     "pct": "~3.4%"},
        {"name": "Poloniex Exchange",              "amount": "Institutional", "pct": "—"},
    ],
}

# ── Analyst price targets (sourced from public reports, as of 2025/2026) ──────
_ANALYST_TARGETS: dict[str, list[dict]] = {
    "BTC-USD": [
        {"analyst": "Cathie Wood (ARK Invest)",    "target": "$1,500,000",  "horizon": "2030",  "thesis": "Institutional adoption + spot ETF inflows drive exponential demand"},
        {"analyst": "Tom Lee (Fundstrat)",         "target": "$250,000",    "horizon": "2025",  "thesis": "Halving cycle + macro tailwinds, ETF demand exceeds miner supply"},
        {"analyst": "PlanB (S2F Model)",           "target": "$500,000",    "horizon": "2025",  "thesis": "Stock-to-flow scarcity model suggests 10× post-halving"},
        {"analyst": "Standard Chartered",          "target": "$200,000",    "horizon": "2025",  "thesis": "ETF demand of 437k BTC/yr vs. 450k new BTC/yr mined"},
        {"analyst": "VanEck Research",             "target": "$350,000",    "horizon": "2025",  "thesis": "Nation-state adoption + reserve asset narrative strengthening"},
        {"analyst": "Bernstein Research",          "target": "$200,000",    "horizon": "2025",  "thesis": "Crypto-friendly regulation + supply squeeze post-halving"},
        {"analyst": "H.C. Wainwright",             "target": "$225,000",    "horizon": "2026",  "thesis": "Mining economics + ETF AUM growth compound effect"},
        {"analyst": "Galaxy Digital",              "target": "$150,000",    "horizon": "2025",  "thesis": "Conservative estimate factoring regulatory uncertainty"},
    ],
    "ETH-USD": [
        {"analyst": "Standard Chartered",          "target": "$10,000",     "horizon": "2025",  "thesis": "EIP-4844 scalability + staking yields attract institutional capital"},
        {"analyst": "VanEck Research",             "target": "$22,000",     "horizon": "2030",  "thesis": "Ethereum as global settlement layer, capturing 70% of DeFi TVL"},
        {"analyst": "Bernstein Research",          "target": "$6,600",      "horizon": "2025",  "thesis": "Spot ETH ETF approval + Layer-2 growth multiplying addressable market"},
        {"analyst": "Coin Metrics",                "target": "$8,000",      "horizon": "2025",  "thesis": "Network revenue growth tied to DeFi expansion and staking rewards"},
        {"analyst": "ARK Invest",                  "target": "$170,000",    "horizon": "2030",  "thesis": "DeFi smart contracts capture 0.5% of global financial activity"},
        {"analyst": "Tom Lee (Fundstrat)",         "target": "$8,000",      "horizon": "2025",  "thesis": "ETH ETF flows + deflationary issuance creates supply squeeze"},
    ],
    "BNB-USD": [
        {"analyst": "CoinCodex",                   "target": "$1,200",      "horizon": "2025",  "thesis": "BNB burn mechanism + Binance ecosystem growth"},
        {"analyst": "DigitalCoinPrice",            "target": "$950",        "horizon": "2025",  "thesis": "Exchange token utility growth tied to Binance volumes"},
        {"analyst": "PricePrediction",             "target": "$850",        "horizon": "2025",  "thesis": "BSC DeFi expansion + BNB Chain developer activity"},
    ],
    "SOL-USD": [
        {"analyst": "VanEck Research",             "target": "$3,211",      "horizon": "2030",  "thesis": "Solana as Visa-scale payment rail + DeFi hub"},
        {"analyst": "Standard Chartered",          "target": "$500",        "horizon": "2025",  "thesis": "Solana spot ETF approval expected in 2025; developer momentum"},
        {"analyst": "Bernstein Research",          "target": "$600",        "horizon": "2025",  "thesis": "High-throughput chain winning DeFi and consumer app market share"},
        {"analyst": "Pantera Capital",             "target": "$1,000",      "horizon": "2026",  "thesis": "Mobile-first crypto apps (Saga) + meme coin ecosystem revenue"},
    ],
    "XRP-USD": [
        {"analyst": "Standard Chartered",          "target": "$12.50",      "horizon": "2025",  "thesis": "SEC case resolution + SWIFT alternative gaining bank adoption"},
        {"analyst": "CoinCodex",                   "target": "$8.00",       "horizon": "2025",  "thesis": "RippleNet expansion in Asia + CBDC corridors"},
        {"analyst": "Telegaon",                    "target": "$5.50",       "horizon": "2025",  "thesis": "Cross-border payment volume growth"},
    ],
    "ADA-USD": [
        {"analyst": "VanEck",                      "target": "$3.09",       "horizon": "2025",  "thesis": "Voltaire governance era + African ID and DeFi adoption"},
        {"analyst": "PricePrediction",             "target": "$2.50",       "horizon": "2025",  "thesis": "Hydra L2 scalability + regulated DeFi narrative"},
        {"analyst": "CoinCodex",                   "target": "$2.00",       "horizon": "2025",  "thesis": "Slow-and-steady academic peer-review approach vs. competitors"},
    ],
    "AVAX-USD": [
        {"analyst": "VanEck",                      "target": "$155",        "horizon": "2025",  "thesis": "Subnet scaling + enterprise blockchain use cases"},
        {"analyst": "PricePrediction",             "target": "$120",        "horizon": "2025",  "thesis": "Avalanche subnets gain traction with gaming and DeFi"},
    ],
    "DOT-USD": [
        {"analyst": "CoinCodex",                   "target": "$30",         "horizon": "2025",  "thesis": "Parachain ecosystem matures + Polkadot 2.0 JAM upgrade"},
        {"analyst": "DigitalCoinPrice",            "target": "$25",         "horizon": "2025",  "thesis": "Cross-chain interoperability narrative + developer growth"},
    ],
    "LINK-USD": [
        {"analyst": "VanEck",                      "target": "$80",         "horizon": "2025",  "thesis": "CCIP adoption by banks for tokenised asset settlement"},
        {"analyst": "Standard Chartered",          "target": "$100",        "horizon": "2026",  "thesis": "Oracle monopoly in institutional DeFi + SWIFT partnership"},
        {"analyst": "CoinCodex",                   "target": "$60",         "horizon": "2025",  "thesis": "DeFi TVL recovery drives oracle demand growth"},
    ],
    "TRX-USD": [
        {"analyst": "PricePrediction",             "target": "$0.28",       "horizon": "2025",  "thesis": "USDT on Tron dominates emerging market stablecoin flows"},
        {"analyst": "CoinCodex",                   "target": "$0.22",       "horizon": "2025",  "thesis": "Low-fee network enables micropayment use cases"},
    ],
}

_FCA_COLOR = {
    FCAStatus.REGULATED_ETP:  "#1AB868",
    FCAStatus.REGISTERED:     "#4ADE80",
    FCAStatus.PENDING:        "#E8A500",
    FCAStatus.GRANDFATHERED:  "#E8A500",
    FCAStatus.UNREGISTERED:   "#E53535",
    FCAStatus.NOT_APPLICABLE: "#888",
}

_CRYPTO_COLOR = {
    "BTC-USD":  "#F7931A",
    "ETH-USD":  "#627EEA",
    "BNB-USD":  "#F3BA2F",
    "SOL-USD":  "#9945FF",
    "XRP-USD":  "#00AAE4",
    "ADA-USD":  "#0033AD",
    "AVAX-USD": "#E84142",
    "DOT-USD":  "#E6007A",
    "LINK-USD": "#2A5ADA",
    "TRX-USD":  "#FF0013",
}


# ── Data fetching ─────────────────────────────────────────────────────────────

def _safe_num(v) -> Optional[float]:
    try:
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    except Exception:
        return None


@st.cache_data(ttl=60, show_spinner=False)
def _live_prices(tickers: tuple[str, ...]) -> dict:
    try:
        import yfinance as yf
        data: dict = {}
        batch = yf.download(list(tickers), period="2d", auto_adjust=True,
                            progress=False, threads=True)
        closes = batch.get("Close", batch)
        if closes is None or closes.empty:
            return data
        last = closes.iloc[-1]
        prev = closes.iloc[-2] if len(closes) >= 2 else closes.iloc[-1]
        for t in tickers:
            try:
                p  = _safe_num(last[t]) if t in last.index else None
                p0 = _safe_num(prev[t]) if t in prev.index else None
                pct = round((p - p0) / p0 * 100, 2) if (p and p0 and p0 != 0) else None
                data[t] = {"price": round(p, 6) if p else None, "chg_pct": pct}
            except Exception:
                pass
        return data
    except Exception:
        return {}


@st.cache_data(ttl=900, show_spinner=False)
def _fetch_news(ticker: str) -> list[dict]:
    try:
        import yfinance as yf
        raw_news = yf.Ticker(ticker).news or []
        result = []
        for item in raw_news[:15]:
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
            return round((current - past) / past * 100, 2) if past and past != 0 else None

        return {
            "dates":  [d.strftime("%Y-%m-%d") for d in closes.index],
            "prices": [_safe_num(v) for v in closes.values],
            "1M":  _ret(21),
            "3M":  _ret(63),
            "6M":  _ret(126),
            "1Y":  _ret(252),
            "5Y":  _ret(1260),
        }
    except Exception:
        return {}


def _render_news_item(article: dict) -> None:
    title, link, publisher, ts = (
        article["title"], article["link"],
        article["publisher"], article["ts"],
    )
    if ts:
        age_h = (time.time() - ts) / 3600
        time_label = (
            f"{int(age_h * 60)}m ago" if age_h < 1
            else f"{int(age_h)}h ago" if age_h < 24
            else f"{int(age_h / 24)}d ago"
        )
    else:
        time_label = ""

    if link and link.startswith("http"):
        headline_html = (
            f'<a href="{link}" target="_blank" rel="noopener noreferrer" '
            f'style="color:#071D35;text-decoration:none;font-weight:600;border-bottom:1px dotted #555">'
            f'{title}</a>'
        )
        read_link = (
            f'<span style="color:#5A8EBB">&middot;</span>'
            f'<a href="{link}" target="_blank" rel="noopener noreferrer" '
            f'style="color:#1AB868;text-decoration:none;font-size:0.68rem">&nearr; Read</a>'
        )
    else:
        headline_html = f'<span style="color:#071D35;font-weight:600">{title}</span>'
        read_link = ""

    time_html = (
        f'<span style="color:#5A8EBB">&middot;</span><span>{time_label}</span>'
        if time_label else ""
    )

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


def _render_detail_panel(yf_ticker: str, symbol: str, name: str, prices: dict) -> None:
    accent = _CRYPTO_COLOR.get(yf_ticker, "#1AB868")
    px_data = prices.get(yf_ticker, {})
    price   = _safe_num(px_data.get("price"))
    chg     = _safe_num(px_data.get("chg_pct"))

    price_str = (
        f"${price:,.6f}".rstrip("0").rstrip(".")
        if price and price < 0.01 else
        f"${price:,.4f}" if price and price < 1 else
        f"${price:,.2f}" if price else "—"
    )
    chg_color = "#1AB868" if (chg is not None and chg >= 0) else "#E53535"
    chg_str   = f"{chg:+.2f}%" if chg is not None else "—"

    st.markdown(
        f"""<div style="background:#ffffff;border:1px solid #D9E8F5;border-left:4px solid {accent};
 border-radius:10px;padding:1rem 1.2rem;margin:0.4rem 0 0.8rem 0">
  <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:0.5rem">
    <div>
      <span style="color:{accent};font-size:2rem;font-weight:700">{symbol}</span>&nbsp;
      <span style="color:#2B5A85;font-size:1rem">{name}</span>
    </div>
    <div style="text-align:right">
      <div style="font-size:1.6rem;font-weight:700">{price_str}</div>
      <div style="font-size:0.95rem;color:{chg_color}">{chg_str} today</div>
    </div>
  </div>
</div>""",
        unsafe_allow_html=True,
    )

    # Fetch in parallel
    with ThreadPoolExecutor(max_workers=3) as pool:
        _fn = pool.submit(_fetch_news, yf_ticker)
        _fp = pool.submit(_fetch_performance, yf_ticker)
        news = _fn.result()
        perf = _fp.result()

    # ── Tab layout ────────────────────────────────────────────────────────────
    tab_holders, tab_perf, tab_news, tab_analyst = st.tabs(
        ["🏦 Top Holders", "📈 Performance", "📰 News", "🔮 Analyst Predictions"]
    )

    with tab_holders:
        holders = _TOP_HOLDERS.get(yf_ticker, [])
        if holders:
            st.markdown(f"##### Known institutional & insider holders of {symbol}")
            for i, h in enumerate(holders, 1):
                pct_color = "#1AB868" if h["pct"] not in ("—", "") else "#888"
                st.markdown(
                    f"""<div style="background:#EEF4FB;border:1px solid #D9E8F5;
  border-left:3px solid {accent};border-radius:6px;padding:0.5rem 0.9rem;
  margin-bottom:0.35rem;display:flex;align-items:center;gap:1rem">
  <span style="color:#5A8EBB;min-width:22px;font-size:0.75rem">#{i}</span>
  <span style="flex:1;font-weight:600;font-size:0.85rem">{h["name"]}</span>
  <span style="color:#071D35;font-size:0.8rem;min-width:120px;text-align:right">{h["amount"]}</span>
  <span style="color:{pct_color};font-size:0.8rem;min-width:60px;text-align:right;font-weight:700">{h["pct"]}</span>
</div>""",
                    unsafe_allow_html=True,
                )
            st.caption("⚠ Holdings data is indicative and sourced from public disclosures. Figures may not reflect most recent filings.")
        else:
            st.info("Institutional holder data not available for this asset.")

    with tab_perf:
        st.markdown(f"##### {symbol} Price Performance")
        if perf and perf.get("dates"):
            _TF_DAYS = {"1M": 21, "3M": 63, "6M": 126, "1Y": 252, "5Y": 1260, "All": None}
            tf = st.radio("", list(_TF_DAYS.keys()), index=3, horizontal=True,
                          key=f"cr_perf_{yf_ticker}")
            n_days = _TF_DAYS[tf]
            vis_dates  = perf["dates"][-n_days:]  if n_days else perf["dates"]
            vis_prices = perf["prices"][-n_days:] if n_days else perf["prices"]

            line_color = accent
            if len(vis_prices) >= 2:
                p0v = next((v for v in vis_prices if v is not None), None)
                p1v = next((v for v in reversed(vis_prices) if v is not None), None)
                if p0v and p1v and p1v < p0v:
                    line_color = "#E53535"

            fig_p = go.Figure(go.Scatter(
                x=vis_dates, y=vis_prices, mode="lines",
                line={"color": line_color, "width": 1.8},
                fill="tozeroy",
                fillcolor="rgba(26,184,104,0.06)" if line_color == accent else "rgba(229,53,53,0.06)",
                hovertemplate="%{x}<br>$%{y:,.4f}<extra></extra>",
            ))
            fig_p.update_layout(
                height=220,
                margin={"t": 5, "b": 5, "l": 0, "r": 0},
                paper_bgcolor="#EEF4FB", plot_bgcolor="#EEF4FB",
                xaxis={"visible": False},
                yaxis={"color": "#5A8EBB", "gridcolor": "#D9E8F5", "tickformat": "$,.2f"},
                showlegend=False,
            )
            st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar": False})

            periods = [("1M", perf.get("1M")), ("3M", perf.get("3M")),
                       ("6M", perf.get("6M")), ("1Y", perf.get("1Y")), ("5Y", perf.get("5Y"))]
            cells = ""
            for lbl, val in periods:
                is_active = lbl == tf
                if val is not None:
                    clr     = "#1AB868" if val >= 0 else "#E53535"
                    val_str = f"{val:+.1f}%"
                else:
                    clr, val_str = "#555", "—"
                border = "border-bottom:2px solid #1AB868;" if is_active else ""
                cells += (
                    f'<div style="text-align:center;flex:1;{border}">'
                    f'<div style="font-size:0.62rem;color:#5A8EBB">{lbl}</div>'
                    f'<div style="font-size:0.8rem;font-weight:700;color:{clr}">{val_str}</div>'
                    f'</div>'
                )
            st.markdown(
                f'<div style="display:flex;gap:0.25rem;margin-top:0.15rem">{cells}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("Performance data not available.")

    with tab_news:
        st.markdown(f"##### Latest {symbol} News")
        if news:
            for article in news:
                _render_news_item(article)
        else:
            st.info(f"No recent news found for {symbol}. Try refreshing.")

    with tab_analyst:
        targets = _ANALYST_TARGETS.get(yf_ticker, [])
        if targets:
            st.markdown(f"##### {symbol} — Analyst Price Targets & Research")
            st.caption("⚠ Price targets are forward-looking estimates from public analyst reports. Not financial advice.")
            for t in targets:
                st.markdown(
                    f"""<div style="background:#EEF4FB;border:1px solid #D9E8F5;
  border-left:3px solid {accent};border-radius:8px;padding:0.65rem 1rem;
  margin-bottom:0.4rem">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;flex-wrap:wrap">
    <div>
      <span style="font-weight:700;font-size:0.88rem">{t["analyst"]}</span><br>
      <span style="color:#5A8EBB;font-size:0.73rem">{t["thesis"]}</span>
    </div>
    <div style="text-align:right;white-space:nowrap">
      <div style="font-size:1.05rem;font-weight:700;color:{accent}">{t["target"]}</div>
      <div style="font-size:0.7rem;color:#5A8EBB">Target · {t["horizon"]}</div>
    </div>
  </div>
</div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.info(f"Analyst prediction data not yet available for {symbol}.")


# ── Main render ───────────────────────────────────────────────────────────────

def render() -> None:
    st.markdown("<h2 class='iw-module-header'>Sovereign Crypto Networks</h2>", unsafe_allow_html=True)
    st.caption("Top-10 digital assets · Institutional holders · Live prices · Analyst predictions")

    # Session state
    if "cr_selected" not in st.session_state:
        st.session_state["cr_selected"] = None

    # ── Click channel (deferred clear) ───────────────────────────────────────
    if st.session_state.pop("_cr_click_clear", False):
        st.session_state.pop("cr_click_ch", None)

    st.markdown("""<style>
[data-testid="stTextInput"]:has(input[placeholder="iw-cr-click-v1"]) {
  position: fixed !important;
  left: -9999px !important;
  top: -9999px !important;
  width: 1px !important;
  height: 1px !important;
  overflow: hidden !important;
  opacity: 0 !important;
}
</style>""", unsafe_allow_html=True)

    _click_raw = st.text_input("c", key="cr_click_ch", placeholder="iw-cr-click-v1",
                                label_visibility="collapsed")
    if _click_raw and any(_click_raw == t for t, *_ in _TOP10):
        _prev = st.session_state.get("cr_selected")
        st.session_state["cr_selected"] = None if _prev == _click_raw else _click_raw
        st.session_state["_cr_click_clear"] = True
        st.rerun()

    # Fetch live prices for top 10
    top10_tickers = tuple(t for t, *_ in _TOP10)
    prices = _live_prices(top10_tickers)

    # ── Summary metrics ───────────────────────────────────────────────────────
    gainers = sum(
        1 for yf_t, *_ in _TOP10
        if (_safe_num((prices.get(yf_t) or {}).get("chg_pct")) or 0) > 0
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Assets Tracked", len(CRYPTO_REGISTRY))
    m2.metric("Featured Top-10", 10)
    m3.metric("Gaining Today", gainers, delta=f"{gainers}/10")
    m4.metric("Data Refresh", "60s cache", help="Live prices cached for 60 seconds")

    st.divider()

    # ── Top-10 price cards ────────────────────────────────────────────────────
    st.markdown("### Top 10 Cryptocurrencies")
    selected = st.session_state["cr_selected"]

    for idx in range(0, len(_TOP10), 2):
        row_entries = _TOP10[idx: idx + 2]
        row_tickers = [e[0] for e in row_entries]
        col_a, col_b = st.columns(2)
        for col, entry in zip([col_a, col_b], row_entries):
            yf_t, name, sym, icon = entry
            accent  = _CRYPTO_COLOR.get(yf_t, "#888")
            px_data = prices.get(yf_t, {})
            price   = _safe_num(px_data.get("price"))
            chg     = _safe_num(px_data.get("chg_pct"))

            price_str = (
                f"${price:,.6f}".rstrip("0").rstrip(".")
                if price and price < 0.01 else
                f"${price:,.4f}" if price and price < 1 else
                f"${price:,.2f}" if price else "—"
            )
            chg_color = "#1AB868" if (chg is not None and chg >= 0) else "#E53535"
            chg_str   = f"{chg:+.2f}%" if chg is not None else "—"
            is_active = selected == yf_t

            with col:
                card_id = f"cr_card_{yf_t.replace('-', '_')}"
                bg     = f"{accent}12" if is_active else "#ffffff"
                border = f"2px solid {accent}" if is_active else "1px solid #D9E8F5"
                shadow = "box-shadow:0 3px 10px rgba(0,0,0,0.10);" if is_active else "box-shadow:0 1px 3px rgba(0,0,0,0.06);"
                st.markdown(
                    f'<div id="{card_id}" class="iw-price-card" data-ticker="{yf_t}"'
                    f' style="background:{bg};border:{border};border-radius:10px;'
                    f'padding:0.65rem 0.85rem;margin-bottom:0.3rem;cursor:pointer;{shadow}">'
                    f'<div style="display:flex;align-items:center;gap:0.4rem;margin-bottom:0.2rem">'
                    f'<span style="font-size:1.1rem">{icon}</span>'
                    f'<span style="font-weight:700;font-size:0.88rem;color:{accent}">{sym}</span>'
                    f'<span style="color:#5A8EBB;font-size:0.68rem;margin-left:auto">{name}</span>'
                    f'</div>'
                    f'<div style="font-size:1.15rem;font-weight:800;color:#071D35">{price_str}</div>'
                    f'<div style="font-size:0.75rem;color:{chg_color};margin-top:0.05rem">{chg_str} today</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # ── Inline accordion: render detail panel below this row if selected ──
        open_ticker = selected if selected in row_tickers else None
        if open_ticker:
            open_entry = next(e for e in _TOP10 if e[0] == open_ticker)
            _ot, _oname, _osym, _ = open_entry
            st.markdown(f"#### 🔍 {_osym} ({_oname}) — Deep Dive")
            _render_detail_panel(_ot, _osym, _oname, prices)

    # ── Make cards clickable via JS (click-channel pattern) ──────────────────
    import streamlit.components.v1 as components
    components.html("""<script>
(function(){
  var doc=window.parent.document;
  var PH="iw-cr-click-v1";

  function setReactVal(inp,val){
    var setter=Object.getOwnPropertyDescriptor(
      window.parent.HTMLInputElement.prototype,'value').set;
    setter.call(inp,val);
    inp.dispatchEvent(new Event('input',{bubbles:true,composed:true}));
  }

  function findChannel(){
    var els=doc.querySelectorAll('[data-testid="stTextInput"] input');
    for(var i=0;i<els.length;i++){if(els[i].placeholder===PH)return els[i];}
    return null;
  }

  function wireCards(){
    doc.querySelectorAll('.iw-price-card[data-ticker]').forEach(function(card){
      if(card._crWired)return;
      card._crWired=true;
      card.addEventListener('click',function(){
        var ticker=card.getAttribute('data-ticker');
        if(!ticker)return;
        var ch=findChannel();
        if(!ch)return;
        ch.focus();
        setReactVal(ch,ticker);
        ch.dispatchEvent(new Event('change',{bubbles:true,composed:true}));
        setTimeout(function(){
          ch.dispatchEvent(new KeyboardEvent('keydown',{
            key:'Enter',code:'Enter',keyCode:13,which:13,
            bubbles:true,cancelable:true,composed:true
          }));
          setTimeout(function(){ch.blur();},50);
        },80);
      });
    });
  }

  wireCards();
  new MutationObserver(wireCards).observe(doc.body,{childList:true,subtree:true});
})();
</script>""", height=0, scrolling=False)

    # ── Global Crypto News ────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🌐 Global Crypto News")
    st.caption("Aggregated from Bitcoin, Ethereum, and broader crypto market sources")

    with st.spinner("Loading crypto news…"):
        btc_news = _fetch_news("BTC-USD")
        eth_news = _fetch_news("ETH-USD")

    all_news = sorted(btc_news + eth_news, key=lambda x: x["ts"], reverse=True)
    seen: set[str] = set()
    deduped = []
    for item in all_news:
        if item["title"] not in seen:
            seen.add(item["title"])
            deduped.append(item)

    if deduped:
        for article in deduped[:15]:
            _render_news_item(article)
    else:
        st.info("No news available right now. Try refreshing the page.")

    # ── Full registry expander ────────────────────────────────────────────────
    st.divider()
    with st.expander(f"📋 Full Registry — All {len(CRYPTO_REGISTRY)} Tracked Assets", expanded=False):
        search = st.text_input("🔍 Search", "", key="cr_full_search", placeholder="Ticker or name…")
        filtered = CRYPTO_REGISTRY
        if search:
            q = search.lower()
            filtered = [a for a in filtered if q in a.ticker.lower() or q in a.name.lower()]
        rows = [{
            "Ticker": a.ticker,
            "Name": a.name,
            "Tier": a.tier.value,
            "Exchange": a.exchange,
            "FCA Status": a.fca_status.value,
            "AUM (£mn)": f"{a.aum_mn:,.0f}" if a.aum_mn else "—",
            "TER": f"{a.ter:.2f}%" if a.ter else "—",
        } for a in filtered]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
