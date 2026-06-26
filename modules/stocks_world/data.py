"""Stocks & Shares World — instrument registry and live price fetching."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import math


@dataclass
class StockProduct:
    ticker: str
    name: str
    country: str        # "US", "UK", "DE", "JP", etc.
    sector: str
    index_member: str   # "S&P 500", "NASDAQ 100", "FTSE 100", etc.
    market_cap_bn: float = 0.0
    currency: str = "USD"
    exchange: str = ""
    description: str = ""


STOCKS_REGISTRY: list[StockProduct] = [
    # ── United States ──────────────────────────────────────────────────────────
    StockProduct("AAPL",  "Apple Inc.",             "US", "Technology",       "S&P 500 / NASDAQ 100", 3200, "USD", "NASDAQ"),
    StockProduct("MSFT",  "Microsoft Corp.",         "US", "Technology",       "S&P 500 / NASDAQ 100", 3100, "USD", "NASDAQ"),
    StockProduct("NVDA",  "NVIDIA Corp.",            "US", "Technology",       "S&P 500 / NASDAQ 100", 2900, "USD", "NASDAQ"),
    StockProduct("GOOGL", "Alphabet Inc. (Google)",  "US", "Technology",       "S&P 500 / NASDAQ 100", 2200, "USD", "NASDAQ"),
    StockProduct("AMZN",  "Amazon.com Inc.",         "US", "Consumer Discret.","S&P 500 / NASDAQ 100", 2100, "USD", "NASDAQ"),
    StockProduct("META",  "Meta Platforms Inc.",     "US", "Technology",       "S&P 500 / NASDAQ 100", 1500, "USD", "NASDAQ"),
    StockProduct("TSLA",  "Tesla Inc.",              "US", "Consumer Discret.","S&P 500 / NASDAQ 100",  900, "USD", "NASDAQ"),
    StockProduct("BRK-B", "Berkshire Hathaway B",   "US", "Financials",       "S&P 500",               900, "USD", "NYSE"),
    StockProduct("JPM",   "JPMorgan Chase & Co.",   "US", "Financials",       "S&P 500",               700, "USD", "NYSE"),
    StockProduct("V",     "Visa Inc.",               "US", "Financials",       "S&P 500",               600, "USD", "NYSE"),
    StockProduct("JNJ",   "Johnson & Johnson",       "US", "Healthcare",       "S&P 500",               380, "USD", "NYSE"),
    StockProduct("UNH",   "UnitedHealth Group",      "US", "Healthcare",       "S&P 500",               480, "USD", "NYSE"),
    StockProduct("XOM",   "ExxonMobil Corp.",        "US", "Energy",           "S&P 500",               480, "USD", "NYSE"),
    StockProduct("WMT",   "Walmart Inc.",            "US", "Consumer Staples", "S&P 500",               570, "USD", "NYSE"),
    StockProduct("PG",    "Procter & Gamble",        "US", "Consumer Staples", "S&P 500",               380, "USD", "NYSE"),
    StockProduct("MA",    "Mastercard Inc.",         "US", "Financials",       "S&P 500",               470, "USD", "NYSE"),
    StockProduct("HD",    "Home Depot Inc.",         "US", "Consumer Discret.","S&P 500",               340, "USD", "NYSE"),
    StockProduct("CVX",   "Chevron Corp.",           "US", "Energy",           "S&P 500",               280, "USD", "NYSE"),
    StockProduct("ABBV",  "AbbVie Inc.",             "US", "Healthcare",       "S&P 500",               320, "USD", "NYSE"),
    StockProduct("BAC",   "Bank of America",         "US", "Financials",       "S&P 500",               320, "USD", "NYSE"),
    StockProduct("AMD",   "Advanced Micro Devices",  "US", "Technology",       "S&P 500 / NASDAQ 100",  270, "USD", "NASDAQ"),
    StockProduct("NFLX",  "Netflix Inc.",            "US", "Comm. Services",   "S&P 500 / NASDAQ 100",  370, "USD", "NASDAQ"),
    StockProduct("ADBE",  "Adobe Inc.",              "US", "Technology",       "S&P 500 / NASDAQ 100",  220, "USD", "NASDAQ"),
    StockProduct("CRM",   "Salesforce Inc.",         "US", "Technology",       "S&P 500",               310, "USD", "NYSE"),
    StockProduct("INTC",  "Intel Corp.",             "US", "Technology",       "S&P 500 / NASDAQ 100",  110, "USD", "NASDAQ"),
    StockProduct("COIN",  "Coinbase Global",         "US", "Financials",       "NASDAQ 100",             65, "USD", "NASDAQ"),
    StockProduct("MSTR",  "Strategy (MicroStrategy)","US", "Technology",       "NASDAQ 100",             90, "USD", "NASDAQ"),
    StockProduct("PLTR",  "Palantir Technologies",   "US", "Technology",       "S&P 500 / NASDAQ 100",  180, "USD", "NASDAQ"),
    # ── United Kingdom ─────────────────────────────────────────────────────────
    StockProduct("SHEL.L","Shell plc",               "UK", "Energy",           "FTSE 100",              230, "GBP", "LSE"),
    StockProduct("AZN.L", "AstraZeneca plc",         "UK", "Healthcare",       "FTSE 100",              240, "GBP", "LSE"),
    StockProduct("HSBA.L","HSBC Holdings plc",       "UK", "Financials",       "FTSE 100",              160, "GBP", "LSE"),
    StockProduct("ULVR.L","Unilever plc",            "UK", "Consumer Staples", "FTSE 100",              110, "GBP", "LSE"),
    StockProduct("BP.L",  "BP plc",                  "UK", "Energy",           "FTSE 100",               90, "GBP", "LSE"),
    StockProduct("GSK.L", "GSK plc",                 "UK", "Healthcare",       "FTSE 100",               70, "GBP", "LSE"),
    StockProduct("RIO.L", "Rio Tinto plc",           "UK", "Materials",        "FTSE 100",               90, "GBP", "LSE"),
    StockProduct("DGE.L", "Diageo plc",              "UK", "Consumer Staples", "FTSE 100",               60, "GBP", "LSE"),
    StockProduct("LLOY.L","Lloyds Banking Group",    "UK", "Financials",       "FTSE 100",               50, "GBP", "LSE"),
    StockProduct("BT-A.L","BT Group plc",            "UK", "Comm. Services",   "FTSE 100",               15, "GBP", "LSE"),
    # ── Germany ────────────────────────────────────────────────────────────────
    StockProduct("SAP",   "SAP SE",                  "DE", "Technology",       "DAX",                   240, "USD", "NYSE"),
    StockProduct("SIE.DE","Siemens AG",              "DE", "Industrials",      "DAX",                   130, "EUR", "XETRA"),
    StockProduct("BMW.DE","BMW AG",                  "DE", "Consumer Discret.","DAX",                    60, "EUR", "XETRA"),
    StockProduct("ALV.DE","Allianz SE",              "DE", "Financials",       "DAX",                   120, "EUR", "XETRA"),
    # ── Japan ──────────────────────────────────────────────────────────────────
    StockProduct("7203.T","Toyota Motor Corp.",      "JP", "Consumer Discret.","Nikkei 225",            320, "JPY", "TSE"),
    StockProduct("6758.T","Sony Group Corp.",        "JP", "Technology",       "Nikkei 225",            120, "JPY", "TSE"),
    StockProduct("9984.T","SoftBank Group",          "JP", "Technology",       "Nikkei 225",             80, "JPY", "TSE"),
    # ── China ──────────────────────────────────────────────────────────────────
    StockProduct("BABA",  "Alibaba Group",           "CN", "Consumer Discret.","",                      230, "USD", "NYSE"),
    StockProduct("TCEHY", "Tencent Holdings ADR",    "CN", "Technology",       "",                      400, "USD", "OTC"),
    StockProduct("BIDU",  "Baidu Inc. ADR",          "CN", "Technology",       "NASDAQ 100",             30, "USD", "NASDAQ"),
    # ── France ─────────────────────────────────────────────────────────────────
    StockProduct("MC.PA", "LVMH Moët Hennessy",     "FR", "Consumer Discret.","CAC 40",                290, "EUR", "Euronext"),
    StockProduct("TTE.PA","TotalEnergies SE",        "FR", "Energy",           "CAC 40",                140, "EUR", "Euronext"),
    # ── India ──────────────────────────────────────────────────────────────────
    StockProduct("RELIANCE.NS","Reliance Industries","IN", "Energy",           "Nifty 50",              230, "INR", "NSE"),
    StockProduct("INFY",  "Infosys Ltd ADR",        "IN", "Technology",       "Nifty 50",               85, "USD", "NYSE"),
]

ALL_COUNTRIES = sorted(set(s.country for s in STOCKS_REGISTRY))
ALL_SECTORS   = sorted(set(s.sector   for s in STOCKS_REGISTRY))
ALL_INDEXES   = sorted(set(s.index_member for s in STOCKS_REGISTRY if s.index_member))


def fetch_prices(tickers: list[str]) -> dict:
    """Fetch live prices and 1-day change via yfinance (best-effort)."""
    if not tickers:
        return {}
    try:
        import yfinance as yf
        data = yf.download(tickers, period="2d", auto_adjust=True, progress=False)
        closes = data["Close"] if "Close" in data.columns else data
        result: dict = {}
        for t in tickers:
            try:
                col = closes[t] if t in closes.columns else closes
                vals = col.dropna()
                if len(vals) < 1:
                    continue
                price = float(vals.iloc[-1])
                chg = None
                if len(vals) >= 2:
                    prev = float(vals.iloc[-2])
                    if prev and not math.isnan(prev):
                        chg = round((price - prev) / prev * 100, 2)
                result[t] = {"price": round(price, 2), "chg_pct": chg}
            except Exception:
                continue
        return result
    except Exception:
        return {}
