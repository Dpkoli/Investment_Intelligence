"""
Precious Metals module — Gold and Silver spot, physically-backed ETPs,
streaming & royalty equity plays, and mining equity ETFs.
Live prices via yfinance (GC=F, SI=F futures; GLD, SLV ETPs).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)


class MetalType(str, Enum):
    GOLD   = "Gold"
    SILVER = "Silver"
    PLATINUM = "Platinum"
    PALLADIUM = "Palladium"


@dataclass
class MetalProduct:
    ticker: str
    name: str
    metal: MetalType
    product_type: str     # "Spot/Futures" | "Physical ETP" | "Mining ETF" | "Streaming Equity"
    exchange: str
    currency: str
    expense_ratio: Optional[float] = None
    aum_bn: Optional[float] = None
    issuer: Optional[str] = None
    isin: Optional[str] = None
    yf_ticker: Optional[str] = None
    physically_backed: bool = False
    leverage: float = 1.0
    notes: Optional[str] = None


METALS_REGISTRY: list[MetalProduct] = [
    # ── Gold Spot / Futures ────────────────────────────────────────────────────
    MetalProduct("XAU/USD", "Gold Spot (LBMA Fix)",      MetalType.GOLD,  "Spot/Futures","OTC","USD", yf_ticker="GC=F",  notes="LBMA AM/PM benchmark; troy oz USD"),
    MetalProduct("GC=F",    "COMEX Gold Futures (front)", MetalType.GOLD,  "Spot/Futures","COMEX","USD", yf_ticker="GC=F"),
    MetalProduct("MGC=F",   "COMEX Micro Gold Futures",  MetalType.GOLD,  "Spot/Futures","COMEX","USD", yf_ticker="MGC=F", notes="1/10 oz contract"),

    # ── Gold Physical ETPs (US) ────────────────────────────────────────────────
    MetalProduct("GLD",  "SPDR Gold Shares",              MetalType.GOLD, "Physical ETP","NYSE", "USD", expense_ratio=0.40, aum_bn=70.2,  issuer="State Street",  physically_backed=True, isin="US78463V1070"),
    MetalProduct("IAU",  "iShares Gold Trust",            MetalType.GOLD, "Physical ETP","NYSE", "USD", expense_ratio=0.25, aum_bn=34.7,  issuer="BlackRock",     physically_backed=True, isin="US4642851053"),
    MetalProduct("GLDM", "SPDR Gold MiniShares",          MetalType.GOLD, "Physical ETP","NYSE", "USD", expense_ratio=0.10, aum_bn=12.4,  issuer="State Street",  physically_backed=True, notes="Lower cost alternative to GLD"),
    MetalProduct("SGOL", "abrdn Physical Gold ETC",       MetalType.GOLD, "Physical ETP","NYSE", "USD", expense_ratio=0.17, aum_bn=3.2,   issuer="abrdn",         physically_backed=True, notes="Stored in Swiss vaults"),
    MetalProduct("OUNZ", "VanEck Merk Gold Trust",        MetalType.GOLD, "Physical ETP","NYSE", "USD", expense_ratio=0.25, aum_bn=1.1,   issuer="VanEck/Merk",   physically_backed=True, notes="Investors can take physical delivery"),
    MetalProduct("BAR",  "GraniteShares Gold Trust",      MetalType.GOLD, "Physical ETP","NYSE", "USD", expense_ratio=0.10, aum_bn=1.4,   issuer="GraniteShares", physically_backed=True),

    # ── Gold Physical ETPs (LSE / Xetra) ─────────────────────────────────────
    MetalProduct("PHAU.L","WisdomTree Physical Gold",      MetalType.GOLD, "Physical ETP","LSE", "USD", expense_ratio=0.15, aum_bn=8.2,   issuer="WisdomTree",    physically_backed=True, isin="JE00B1VS3770"),
    MetalProduct("SGLN.L","iShares Physical Gold ETC",     MetalType.GOLD, "Physical ETP","LSE", "USD", expense_ratio=0.12, aum_bn=14.1,  issuer="BlackRock",     physically_backed=True, isin="IE00B4ND3602"),
    MetalProduct("GOLD.L","Invesco Physical Gold ETC",     MetalType.GOLD, "Physical ETP","LSE", "USD", expense_ratio=0.12, aum_bn=12.8,  issuer="Invesco",       physically_backed=True),
    MetalProduct("EWG2.L","Amundi Physical Gold ETC",      MetalType.GOLD, "Physical ETP","LSE", "USD", expense_ratio=0.15,               issuer="Amundi",        physically_backed=True),
    MetalProduct("4GLD.L","Xtrackers Physical Gold ETC",   MetalType.GOLD, "Physical ETP","Xetra","EUR", expense_ratio=0.25,              issuer="DWS",            physically_backed=True),

    # ── Gold Leveraged ETPs ───────────────────────────────────────────────────
    MetalProduct("UGL",  "ProShares Ultra Gold (2×)",      MetalType.GOLD, "Physical ETP","NYSE", "USD", expense_ratio=0.95, leverage=2.0, issuer="ProShares"),
    MetalProduct("GLL",  "ProShares UltraShort Gold (−2×)", MetalType.GOLD,  "Physical ETP","NYSE","USD", expense_ratio=0.95, leverage=-2.0, issuer="ProShares"),
    MetalProduct("3GOL.L","WisdomTree Gold 3× Daily ETP",  MetalType.GOLD, "Physical ETP","LSE", "USD", expense_ratio=0.99, leverage=3.0, issuer="WisdomTree",    notes="Daily-reset leveraged exposure"),
    MetalProduct("3GOS.L","WisdomTree Gold -3× Daily ETP", MetalType.GOLD, "Physical ETP","LSE", "USD", expense_ratio=0.99, leverage=-3.0, issuer="WisdomTree"),

    # ── Gold Mining Equity ETFs ────────────────────────────────────────────────
    MetalProduct("GDX",  "VanEck Gold Miners ETF",         MetalType.GOLD, "Mining ETF", "NYSE", "USD", expense_ratio=0.51, aum_bn=13.2, issuer="VanEck"),
    MetalProduct("GDXJ", "VanEck Junior Gold Miners",      MetalType.GOLD, "Mining ETF", "NYSE", "USD", expense_ratio=0.52, aum_bn=4.8,  issuer="VanEck"),
    MetalProduct("RING", "iShares MSCI Global Gold Miners", MetalType.GOLD,  "Mining ETF","NASDAQ","USD", expense_ratio=0.39, aum_bn=0.6,  issuer="BlackRock"),
    MetalProduct("SGDM", "Sprott Gold Miners ETF",         MetalType.GOLD, "Mining ETF", "NYSE", "USD", expense_ratio=0.50, aum_bn=0.3,  issuer="Sprott"),
    MetalProduct("SGDJ", "Sprott Junior Gold Miners",      MetalType.GOLD, "Mining ETF", "NYSE", "USD", expense_ratio=0.50,              issuer="Sprott"),
    MetalProduct("GOEX", "Global X Gold Explorers ETF",    MetalType.GOLD, "Mining ETF", "NYSE", "USD", expense_ratio=0.65,              issuer="Global X"),

    # ── Gold Leveraged Mining ETFs ────────────────────────────────────────────
    MetalProduct("NUGT",  "Direxion Daily Gold Miners Bull 2×",  MetalType.GOLD, "Mining ETF","NYSE","USD", expense_ratio=1.02, leverage=2.0,  issuer="Direxion", notes="2× daily leveraged GDX"),
    MetalProduct("DUST",  "Direxion Daily Gold Miners Bear 2×",  MetalType.GOLD, "Mining ETF","NYSE","USD", expense_ratio=1.02, leverage=-2.0, issuer="Direxion", notes="−2× daily inverse GDX"),
    MetalProduct("JNUG",  "Direxion Daily Jr Gold Miners Bull 2×",MetalType.GOLD,"Mining ETF","NYSE","USD", expense_ratio=1.16, leverage=2.0,  issuer="Direxion", notes="2× daily leveraged GDXJ"),
    MetalProduct("JDST",  "Direxion Daily Jr Gold Miners Bear 2×",MetalType.GOLD,"Mining ETF","NYSE","USD", expense_ratio=1.16, leverage=-2.0, issuer="Direxion", notes="−2× daily inverse GDXJ"),

    # ── Additional Gold Mining ETFs ───────────────────────────────────────────
    MetalProduct("GOAU",  "US Global GO GOLD & Precious Metal",  MetalType.GOLD, "Mining ETF","NYSE","USD", expense_ratio=0.60, issuer="US Global Investors", notes="Royalty-focused gold miners"),
    MetalProduct("BGLD",  "GraniteShares Gold Miners ETF",       MetalType.GOLD, "Mining ETF","NYSE","USD", expense_ratio=0.75, issuer="GraniteShares",       notes="Equally-weighted gold miners"),
    MetalProduct("GDMN",  "WisdomTree Gold Miners Quality Divid",MetalType.GOLD, "Mining ETF","NYSE","USD", expense_ratio=0.45, issuer="WisdomTree"),
    MetalProduct("MNRS",  "Gabelli Gold Fund (ETF share class)", MetalType.GOLD, "Mining ETF","NYSE","USD", expense_ratio=1.53, issuer="Gabelli",             notes="Active gold miners fund"),
    MetalProduct("RING",  "iShares MSCI Global Gold Miners ETF", MetalType.GOLD, "Mining ETF","NASDAQ","USD",expense_ratio=0.39, aum_bn=0.6, issuer="BlackRock"),

    # ── Broad Metals & Mining ─────────────────────────────────────────────────
    MetalProduct("PICK",  "iShares MSCI Global Met & Mining ETF",MetalType.GOLD, "Mining ETF","NYSE","USD", expense_ratio=0.39, aum_bn=1.1, issuer="BlackRock", notes="Diversified metals & mining; includes gold, copper, iron ore"),
    MetalProduct("XME",   "SPDR S&P Metals & Mining ETF",        MetalType.GOLD, "Mining ETF","NYSE","USD", expense_ratio=0.35, aum_bn=2.2, issuer="State Street", notes="Equal-weight US metals & mining"),
    MetalProduct("COPX",  "Global X Copper Miners ETF",          MetalType.GOLD, "Mining ETF","NYSE","USD", expense_ratio=0.65, aum_bn=1.8, issuer="Global X",    notes="Copper miners; benefit from EV/renewable demand"),

    # ── Gold Royalty / Streaming ──────────────────────────────────────────────
    MetalProduct("WPM",  "Wheaton Precious Metals",        MetalType.GOLD, "Streaming Equity","NYSE","USD",               notes="World's largest precious metals streamer"),
    MetalProduct("FNV",  "Franco-Nevada",                  MetalType.GOLD, "Streaming Equity","NYSE","USD",               notes="Diversified royalty company; gold-dominant"),
    MetalProduct("RGLD", "Royal Gold",                     MetalType.GOLD, "Streaming Equity","NASDAQ","USD",             notes="Royalties on gold mines globally"),
    MetalProduct("SAND", "Sandstorm Gold Royalties",       MetalType.GOLD, "Streaming Equity","NYSE","USD",               notes="Junior streaming company"),
    MetalProduct("OR",   "Osisko Gold Royalties",          MetalType.GOLD, "Streaming Equity","NYSE","USD",               notes="Canadian royalties; strong NAV/share growth"),
    MetalProduct("MAG",  "MAG Silver Corp",                MetalType.SILVER,"Streaming Equity","NYSE","USD",              notes="High-grade Mexican silver developer"),

    # ── Silver Spot / Futures ─────────────────────────────────────────────────
    MetalProduct("XAG/USD","Silver Spot (LBMA Fix)",       MetalType.SILVER,"Spot/Futures","OTC","USD", yf_ticker="SI=F"),
    MetalProduct("SI=F",   "COMEX Silver Futures (front)", MetalType.SILVER,"Spot/Futures","COMEX","USD", yf_ticker="SI=F"),
    MetalProduct("SIL=F",  "COMEX Micro Silver Futures",   MetalType.SILVER,"Spot/Futures","COMEX","USD", yf_ticker="SIL=F"),

    # ── Silver Physical ETPs ──────────────────────────────────────────────────
    MetalProduct("SLV",    "iShares Silver Trust",         MetalType.SILVER,"Physical ETP","NYSE","USD", expense_ratio=0.50, aum_bn=11.3, issuer="BlackRock",   physically_backed=True),
    MetalProduct("SIVR",   "abrdn Physical Silver ETC",    MetalType.SILVER,"Physical ETP","NYSE","USD", expense_ratio=0.30, aum_bn=0.9,  issuer="abrdn",       physically_backed=True, notes="Swiss vault storage"),
    MetalProduct("PSLV",   "Sprott Physical Silver Trust", MetalType.SILVER,"Physical ETP","NYSE","USD",                                  issuer="Sprott",      physically_backed=True, notes="Can take physical delivery; allocated storage"),
    MetalProduct("PHAG.L", "WisdomTree Physical Silver",   MetalType.SILVER,"Physical ETP","LSE","USD", expense_ratio=0.19, aum_bn=0.9,  issuer="WisdomTree",  physically_backed=True),
    MetalProduct("SSLN.L", "iShares Physical Silver ETC",  MetalType.SILVER,"Physical ETP","LSE","USD", expense_ratio=0.20,              issuer="BlackRock",   physically_backed=True),
    MetalProduct("SLVR.L", "Invesco Physical Silver ETC",  MetalType.SILVER,"Physical ETP","LSE","USD", expense_ratio=0.19,              issuer="Invesco",     physically_backed=True),

    # ── Silver Leveraged ──────────────────────────────────────────────────────
    MetalProduct("AGQ",    "ProShares Ultra Silver (2×)", MetalType.SILVER,"Physical ETP","NYSE","USD", expense_ratio=0.95, leverage=2.0,  issuer="ProShares"),
    MetalProduct("ZSL",    "ProShares UltraShort Silver", MetalType.SILVER,"Physical ETP","NYSE","USD", expense_ratio=0.95, leverage=-2.0, issuer="ProShares"),
    MetalProduct("3SIL.L", "WisdomTree Silver 3× Daily", MetalType.SILVER,"Physical ETP","LSE","USD",  expense_ratio=0.99, leverage=3.0,  issuer="WisdomTree"),

    # ── Silver Mining ─────────────────────────────────────────────────────────
    MetalProduct("SIL",    "Global X Silver Miners ETF",  MetalType.SILVER,"Mining ETF","NYSE","USD", expense_ratio=0.65, aum_bn=0.9, issuer="Global X"),
    MetalProduct("SILJ",   "ETFMG Prime Junior Silver",   MetalType.SILVER,"Mining ETF","NYSE","USD", expense_ratio=0.69,             issuer="ETFMG"),

    # ── Platinum ──────────────────────────────────────────────────────────────
    MetalProduct("PPLT",   "abrdn Physical Platinum",     MetalType.PLATINUM,"Physical ETP","NYSE","USD", expense_ratio=0.60, issuer="abrdn", physically_backed=True),
    MetalProduct("PHPT.L", "WisdomTree Physical Platinum",  MetalType.PLATINUM, "Physical ETP","LSE","USD", expense_ratio=0.49, issuer="WisdomTree", physically_backed=True),

    # ── Palladium ─────────────────────────────────────────────────────────────
    MetalProduct("PALL",   "abrdn Physical Palladium",    MetalType.PALLADIUM,"Physical ETP","NYSE","USD", expense_ratio=0.60, issuer="abrdn", physically_backed=True),
    MetalProduct("PHPD.L", "WisdomTree Physical Palladium",MetalType.PALLADIUM,"Physical ETP","LSE","USD", expense_ratio=0.49, issuer="WisdomTree", physically_backed=True),

    # ── Broad Precious Metals ─────────────────────────────────────────────────
    MetalProduct("GLTR",   "abrdn Physical Precious Metals Basket", MetalType.GOLD, "Physical ETP","NYSE","USD",
                expense_ratio=0.60, issuer="abrdn", physically_backed=True, notes="Gold+Silver+Platinum+Palladium basket"),
    MetalProduct("WITE",   "WisdomTree Physical Precious Metals",   MetalType.GOLD, "Physical ETP","NYSE","USD",
                expense_ratio=0.55, issuer="WisdomTree", physically_backed=True),
]

_SPOT_TICKERS = ["GC=F", "SI=F", "PL=F", "PA=F"]
_ETP_TICKERS_US = ["GLD", "IAU", "GLDM", "SGOL", "SLV", "SIVR"]
_ETP_TICKERS_LSE = ["PHAU.L", "SGLN.L", "PHAG.L"]


def fetch_prices(tickers: list[str] | None = None) -> dict[str, dict]:
    """Fetch spot/ETP prices from yfinance. Falls back to {} on failure."""
    import math

    def _clean(v):
        try:
            f = float(v)
            return None if (math.isnan(f) or math.isinf(f)) else f
        except Exception:
            return None

    if tickers is None:
        tickers = _SPOT_TICKERS + _ETP_TICKERS_US
    try:
        import yfinance as yf
        import pandas as pd
        data: dict[str, dict] = {}
        batch = yf.download(tickers, period="5d", auto_adjust=True,
                            progress=False, threads=True)
        closes = batch.get("Close", batch)
        if closes is None or closes.empty:
            return data
        if isinstance(closes, pd.Series):
            closes = closes.to_frame(name=tickers[0])
        closes = closes.dropna(how="all")
        if closes.empty:
            return data
        last  = closes.iloc[-1]
        prev  = closes.iloc[-2] if len(closes) >= 2 else closes.iloc[-1]
        for t in tickers:
            try:
                p  = _clean(last.get(t))
                p0 = _clean(prev.get(t))
                pct = round((p - p0) / p0 * 100, 2) if (p and p0 and p0 != 0) else None
                if p is not None:
                    data[t] = {"price": round(p, 2), "chg_pct": pct}
            except Exception:
                pass
        return data
    except Exception as exc:
        log.debug("yfinance fetch failed: %s", exc)
        return {}
