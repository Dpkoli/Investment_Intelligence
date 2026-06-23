"""
Core Equity — comprehensive global index and ETF registry.
Covers S&P 500, NASDAQ, FTSE 100/250, Russell, Dow Jones, Europe (DAX/CAC/
EuroStoxx), Japan (Nikkei), China/HK, India, Korea, EM, Ex-US, ESG, Factor.
Live prices fetched via yfinance with graceful fallback.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class IndexProduct:
    ticker: str
    name: str
    region: str
    index_tracked: str
    currency: str
    exchange: str
    product_type: str           # "ETF" | "ETP" | "Index"
    leverage: float = 1.0
    is_inverse: bool = False
    expense_ratio: Optional[float] = None   # %
    aum_bn: Optional[float] = None          # billion USD or local
    issuer: Optional[str] = None
    isin: Optional[str] = None
    yf_ticker: Optional[str] = None         # override when different from ticker


CORE_EQUITY_REGISTRY: list[IndexProduct] = [
    # ── S&P 500 ──────────────────────────────────────────────────────────────
    IndexProduct("SPY",   "SPDR S&P 500 ETF Trust",              "US", "S&P 500",      "USD", "NYSE",   "ETF", aum_bn=547.2, expense_ratio=0.0945, issuer="State Street"),
    IndexProduct("IVV",   "iShares Core S&P 500",                "US", "S&P 500",      "USD", "NYSE",   "ETF", aum_bn=490.1, expense_ratio=0.03,   issuer="BlackRock"),
    IndexProduct("VOO",   "Vanguard S&P 500 ETF",                "US", "S&P 500",      "USD", "NYSE",   "ETF", aum_bn=562.8, expense_ratio=0.03,   issuer="Vanguard"),
    IndexProduct("SPLG",  "SPDR Portfolio S&P 500",              "US", "S&P 500",      "USD", "NYSE",   "ETF", aum_bn=52.1,  expense_ratio=0.02,   issuer="State Street"),
    IndexProduct("SSO",   "ProShares Ultra S&P 500 (2×)",        "US", "S&P 500",      "USD", "NYSE",   "ETF", leverage=2.0, aum_bn=4.8,  expense_ratio=0.91, issuer="ProShares"),
    IndexProduct("UPRO",  "ProShares UltraPro S&P 500 (3×)",     "US", "S&P 500",      "USD", "NYSE",   "ETF", leverage=3.0, aum_bn=3.4,  expense_ratio=0.93, issuer="ProShares"),
    IndexProduct("SPXL",  "Direxion Daily S&P 500 Bull 3×",      "US", "S&P 500",      "USD", "NYSE",   "ETF", leverage=3.0, aum_bn=2.9,  expense_ratio=1.01, issuer="Direxion"),
    IndexProduct("SH",    "ProShares Short S&P 500",             "US", "S&P 500",      "USD", "NYSE",   "ETF", leverage=-1.0, is_inverse=True, expense_ratio=0.88, issuer="ProShares"),
    IndexProduct("SDS",   "ProShares UltraShort S&P 500 (−2×)",  "US", "S&P 500",      "USD", "NYSE",   "ETF", leverage=-2.0, is_inverse=True, expense_ratio=0.90, issuer="ProShares"),
    IndexProduct("SPXU",  "ProShares UltraPro Short S&P 500 (−3×)","US","S&P 500",    "USD", "NYSE",   "ETF", leverage=-3.0, is_inverse=True, expense_ratio=0.90, issuer="ProShares"),
    IndexProduct("SPXS",  "Direxion Daily S&P 500 Bear 3×",      "US", "S&P 500",      "USD", "NYSE",   "ETF", leverage=-3.0, is_inverse=True, expense_ratio=1.01, issuer="Direxion"),

    # ── NASDAQ-100 ───────────────────────────────────────────────────────────
    IndexProduct("QQQ",   "Invesco QQQ Trust",                   "US", "NASDAQ-100",   "USD", "NASDAQ", "ETF", aum_bn=311.4, expense_ratio=0.20, issuer="Invesco"),
    IndexProduct("QQQM",  "Invesco NASDAQ-100 ETF",              "US", "NASDAQ-100",   "USD", "NASDAQ", "ETF", aum_bn=35.2,  expense_ratio=0.15, issuer="Invesco"),
    IndexProduct("TQQQ",  "ProShares UltraPro QQQ (3×)",         "US", "NASDAQ-100",   "USD", "NASDAQ", "ETF", leverage=3.0, aum_bn=25.3, expense_ratio=0.88, issuer="ProShares"),
    IndexProduct("QLD",   "ProShares Ultra QQQ (2×)",            "US", "NASDAQ-100",   "USD", "NASDAQ", "ETF", leverage=2.0, aum_bn=5.1,  expense_ratio=0.95, issuer="ProShares"),
    IndexProduct("SQQQ",  "ProShares UltraPro Short QQQ (−3×)",  "US", "NASDAQ-100",   "USD", "NASDAQ", "ETF", leverage=-3.0, is_inverse=True, expense_ratio=0.95, issuer="ProShares"),
    IndexProduct("PSQ",   "ProShares Short QQQ",                 "US", "NASDAQ-100",   "USD", "NASDAQ", "ETF", leverage=-1.0, is_inverse=True, expense_ratio=0.95, issuer="ProShares"),

    # ── Russell / Small-Cap ──────────────────────────────────────────────────
    IndexProduct("IWM",   "iShares Russell 2000 ETF",            "US", "Russell 2000", "USD", "NYSE",   "ETF", aum_bn=68.4, expense_ratio=0.19, issuer="BlackRock"),
    IndexProduct("VB",    "Vanguard Small-Cap ETF",              "US", "CRSP US Small Cap", "USD", "NYSE", "ETF", aum_bn=51.2, expense_ratio=0.05, issuer="Vanguard"),
    IndexProduct("TNA",   "Direxion Daily Small Cap Bull 3×",    "US", "Russell 2000", "USD", "NYSE",   "ETF", leverage=3.0, expense_ratio=1.10, issuer="Direxion"),
    IndexProduct("TZA",   "Direxion Daily Small Cap Bear 3×",    "US", "Russell 2000", "USD", "NYSE",   "ETF", leverage=-3.0, is_inverse=True, expense_ratio=1.10, issuer="Direxion"),

    # ── Dow Jones ────────────────────────────────────────────────────────────
    IndexProduct("DIA",   "SPDR Dow Jones Industrial Average",   "US", "DJIA",         "USD", "NYSE",   "ETF", aum_bn=34.1, expense_ratio=0.16, issuer="State Street"),
    IndexProduct("DDM",   "ProShares Ultra Dow 30 (2×)",         "US", "DJIA",         "USD", "NYSE",   "ETF", leverage=2.0, expense_ratio=0.95, issuer="ProShares"),
    IndexProduct("UDOW",  "ProShares UltraPro Dow 30 (3×)",      "US", "DJIA",         "USD", "NYSE",   "ETF", leverage=3.0, expense_ratio=0.95, issuer="ProShares"),

    # ── FTSE 100 (LSE) ──────────────────────────────────────────────────────
    IndexProduct("ISF.L",  "iShares Core FTSE 100",              "UK", "FTSE 100",     "GBP", "LSE",    "ETF", aum_bn=14.2, expense_ratio=0.07, issuer="BlackRock",   isin="IE0031442068"),
    IndexProduct("VUKE.L", "Vanguard FTSE 100 ETF",             "UK", "FTSE 100",     "GBP", "LSE",    "ETF", aum_bn=4.1,  expense_ratio=0.09, issuer="Vanguard",    isin="IE00B810Q511"),
    IndexProduct("CUKX.L", "iShares FTSE 100 USD Hedged ETF",   "UK", "FTSE 100",     "USD", "LSE",    "ETF", expense_ratio=0.20, issuer="BlackRock"),
    IndexProduct("3UKL.L", "Leverage Shares 3× FTSE 100 ETP",  "UK", "FTSE 100",     "GBP", "LSE",    "ETP", leverage=3.0, issuer="Leverage Shares"),
    IndexProduct("XDUK.L", "Xtrackers FTSE 100 Swap ETF",      "UK", "FTSE 100",     "GBP", "LSE",    "ETF", expense_ratio=0.09, issuer="DWS"),

    # ── FTSE 250 / All-Share ─────────────────────────────────────────────────
    IndexProduct("MIDD.L", "iShares FTSE 250 ETF",              "UK", "FTSE 250",     "GBP", "LSE",    "ETF", aum_bn=2.8,  expense_ratio=0.40, issuer="BlackRock"),
    IndexProduct("VMID.L", "Vanguard FTSE 250 ETF",             "UK", "FTSE 250",     "GBP", "LSE",    "ETF", aum_bn=2.1,  expense_ratio=0.10, issuer="Vanguard",    isin="IE00BKX55S42"),
    IndexProduct("VAGS.L", "Vanguard FTSE UK All Share",        "UK", "FTSE All-Share","GBP","LSE",    "ETF", expense_ratio=0.06, issuer="Vanguard"),

    # ── Europe ───────────────────────────────────────────────────────────────
    IndexProduct("VWRL.L", "Vanguard FTSE All-World ETF",       "Global", "FTSE All-World",  "USD", "LSE", "ETF", aum_bn=42.1, expense_ratio=0.22, issuer="Vanguard"),
    IndexProduct("VWRP.L", "Vanguard FTSE All-World (GBP Acc)", "Global", "FTSE All-World",  "GBP", "LSE", "ETF", aum_bn=28.5, expense_ratio=0.22, issuer="Vanguard"),
    IndexProduct("VGK",    "Vanguard FTSE Europe ETF",          "Europe", "FTSE Developed Europe","USD","NYSE","ETF", aum_bn=22.3, expense_ratio=0.09, issuer="Vanguard"),
    IndexProduct("EZU",    "iShares MSCI Eurozone ETF",         "Europe", "MSCI EMU",    "USD", "NYSE",   "ETF", aum_bn=10.8, expense_ratio=0.51, issuer="BlackRock"),
    IndexProduct("FEZ",    "SPDR Euro Stoxx 50",                "Europe", "Euro Stoxx 50","USD","NYSE",   "ETF", aum_bn=6.2,  expense_ratio=0.29, issuer="State Street"),
    IndexProduct("IEUR",   "iShares Core MSCI Europe ETF",      "Europe", "MSCI Europe", "USD", "NYSE",   "ETF", aum_bn=12.1, expense_ratio=0.09, issuer="BlackRock"),
    IndexProduct("HEZU",   "iShares MSCI Eurozone USD Hedged",  "Europe", "MSCI EMU",    "USD", "NYSE",   "ETF", expense_ratio=0.51, issuer="BlackRock"),

    # ── Germany DAX ──────────────────────────────────────────────────────────
    IndexProduct("EWG",    "iShares MSCI Germany ETF",          "Europe", "MSCI Germany","USD", "NYSE",   "ETF", aum_bn=3.8, expense_ratio=0.50, issuer="BlackRock"),
    IndexProduct("DBXD.DE","Xtrackers DAX ETF",                "Europe", "DAX",          "EUR", "XETRA",  "ETF", expense_ratio=0.09, issuer="DWS"),
    IndexProduct("3DAL.L", "Leverage Shares 3× DAX ETP",       "Europe", "DAX",          "EUR", "LSE",    "ETP", leverage=3.0, issuer="Leverage Shares"),

    # ── France CAC 40 ────────────────────────────────────────────────────────
    IndexProduct("EWQ",    "iShares MSCI France ETF",           "Europe", "MSCI France", "USD", "NYSE",   "ETF", expense_ratio=0.50, issuer="BlackRock"),
    IndexProduct("CAC.PA", "Lyxor CAC 40 ETF",                 "Europe", "CAC 40",       "EUR", "Euronext","ETF", expense_ratio=0.25, issuer="Lyxor"),

    # ── Japan / Nikkei ───────────────────────────────────────────────────────
    IndexProduct("EWJ",    "iShares MSCI Japan ETF",            "Asia", "MSCI Japan",   "USD", "NYSE",   "ETF", aum_bn=14.2, expense_ratio=0.50, issuer="BlackRock"),
    IndexProduct("DXJ",    "WisdomTree Japan Hedged Equity",    "Asia", "WisdomTree Japan Hedged","USD","NYSE","ETF", aum_bn=6.9, expense_ratio=0.48, issuer="WisdomTree"),
    IndexProduct("JPXN",   "iShares JPX-Nikkei 400 ETF",       "Asia", "JPX-Nikkei 400","USD","NYSE",   "ETF", expense_ratio=0.48, issuer="BlackRock"),
    IndexProduct("DBJP",   "Xtrackers MSCI Japan Hedged ETF",  "Asia", "MSCI Japan",   "USD", "NYSE",   "ETF", expense_ratio=0.45, issuer="DWS"),

    # ── China / Hong Kong ────────────────────────────────────────────────────
    IndexProduct("FXI",    "iShares China Large-Cap ETF",       "Asia", "FTSE China 50","USD", "NYSE",   "ETF", aum_bn=7.3, expense_ratio=0.74, issuer="BlackRock"),
    IndexProduct("KWEB",   "KraneShares CSI China Internet",    "Asia", "CSI Overseas China Internet","USD","NYSE","ETF", aum_bn=4.8, expense_ratio=0.76, issuer="KraneShares"),
    IndexProduct("EWH",    "iShares MSCI Hong Kong ETF",        "Asia", "MSCI Hong Kong","USD","NYSE",   "ETF", aum_bn=2.1, expense_ratio=0.50, issuer="BlackRock"),
    IndexProduct("GXC",    "SPDR S&P China ETF",                "Asia", "S&P China BMI","USD","NYSE",   "ETF", expense_ratio=0.59, issuer="State Street"),
    IndexProduct("ASHR",   "Xtrackers Harvest CSI 300 ETF",    "Asia", "CSI 300",      "USD", "NYSE",   "ETF", expense_ratio=0.65, issuer="DWS"),

    # ── South Korea ──────────────────────────────────────────────────────────
    IndexProduct("EWY",    "iShares MSCI South Korea ETF",      "Asia", "MSCI Korea",   "USD", "NYSE",   "ETF", aum_bn=4.4, expense_ratio=0.58, issuer="BlackRock"),

    # ── India ────────────────────────────────────────────────────────────────
    IndexProduct("INDA",   "iShares MSCI India ETF",            "Asia", "MSCI India",   "USD", "NYSE",   "ETF", aum_bn=10.8, expense_ratio=0.65, issuer="BlackRock"),
    IndexProduct("INDY",   "iShares India 50 ETF",              "Asia", "Nifty 50",     "USD", "NASDAQ", "ETF", expense_ratio=0.93, issuer="BlackRock"),
    IndexProduct("SMIN",   "iShares MSCI India Small-Cap",      "Asia", "MSCI India Small Cap","USD","NYSE","ETF", expense_ratio=0.74, issuer="BlackRock"),
    IndexProduct("NFTY",   "First Trust India NIFTY 50 ETF",   "Asia", "NIFTY 50",     "USD", "NASDAQ", "ETF", expense_ratio=0.80, issuer="First Trust"),

    # ── Southeast Asia / Pacific ─────────────────────────────────────────────
    IndexProduct("EWA",    "iShares MSCI Australia ETF",        "Pacific","MSCI Australia","USD","NYSE",  "ETF", expense_ratio=0.50, issuer="BlackRock"),
    IndexProduct("EWS",    "iShares MSCI Singapore ETF",        "Asia", "MSCI Singapore","USD","NYSE",   "ETF", expense_ratio=0.50, issuer="BlackRock"),
    IndexProduct("EWT",    "iShares MSCI Taiwan ETF",           "Asia", "MSCI Taiwan",  "USD", "NYSE",   "ETF", expense_ratio=0.57, issuer="BlackRock"),
    IndexProduct("EPHE",   "iShares MSCI Philippines ETF",      "Asia", "MSCI Philippines","USD","NYSE", "ETF", expense_ratio=0.57, issuer="BlackRock"),
    IndexProduct("THD",    "iShares MSCI Thailand ETF",         "Asia", "MSCI Thailand","USD", "NYSE",   "ETF", expense_ratio=0.57, issuer="BlackRock"),
    IndexProduct("VNM",    "VanEck Vietnam ETF",                "Asia", "MVIS Vietnam",  "USD","NYSE",   "ETF", expense_ratio=0.66, issuer="VanEck"),

    # ── Latin America ────────────────────────────────────────────────────────
    IndexProduct("EWZ",    "iShares MSCI Brazil ETF",           "LatAm","MSCI Brazil",  "USD", "NYSE",   "ETF", aum_bn=3.1, expense_ratio=0.57, issuer="BlackRock"),
    IndexProduct("EWW",    "iShares MSCI Mexico ETF",           "LatAm","MSCI Mexico",  "USD", "NYSE",   "ETF", expense_ratio=0.50, issuer="BlackRock"),
    IndexProduct("ECH",    "iShares MSCI Chile ETF",            "LatAm","MSCI Chile",   "USD", "NYSE",   "ETF", expense_ratio=0.57, issuer="BlackRock"),
    IndexProduct("GXG",    "Global X MSCI Colombia ETF",        "LatAm","MSCI Colombia","USD", "NYSE",   "ETF", expense_ratio=0.61, issuer="Global X"),

    # ── Middle East / Africa ─────────────────────────────────────────────────
    IndexProduct("EZA",    "iShares MSCI South Africa ETF",     "Africa","MSCI South Africa","USD","NYSE","ETF", expense_ratio=0.59, issuer="BlackRock"),
    IndexProduct("KSA",    "iShares MSCI Saudi Arabia ETF",     "MENA", "MSCI Saudi Arabia","USD","NYSE", "ETF", expense_ratio=0.74, issuer="BlackRock"),
    IndexProduct("UAE",    "iShares MSCI UAE ETF",              "MENA", "MSCI UAE",     "USD", "NYSE",   "ETF", expense_ratio=0.60, issuer="BlackRock"),
    IndexProduct("EGPT",   "VanEck Egypt Index ETF",            "MENA", "Market Vectors Egypt","USD","NYSE","ETF", expense_ratio=0.94, issuer="VanEck"),

    # ── Emerging Markets Broad ───────────────────────────────────────────────
    IndexProduct("VWO",    "Vanguard FTSE Emerging Markets",    "EM",   "FTSE EM",      "USD", "NYSE",   "ETF", aum_bn=91.2, expense_ratio=0.08, issuer="Vanguard"),
    IndexProduct("IEMG",   "iShares Core MSCI Emerging Markets","EM",   "MSCI EM IMI",  "USD", "NYSE",   "ETF", aum_bn=74.3, expense_ratio=0.09, issuer="BlackRock"),
    IndexProduct("EEM",    "iShares MSCI EM ETF",               "EM",   "MSCI EM",      "USD", "NYSE",   "ETF", aum_bn=18.4, expense_ratio=0.68, issuer="BlackRock"),
    IndexProduct("EEMS",   "iShares MSCI EM Small-Cap",         "EM",   "MSCI EM Small Cap","USD","NYSE", "ETF", expense_ratio=0.71, issuer="BlackRock"),
    IndexProduct("EMXC",   "iShares MSCI EM ex China",          "EM",   "MSCI EM ex China","USD","NYSE", "ETF", expense_ratio=0.25, issuer="BlackRock"),

    # ── Developed Ex-US ──────────────────────────────────────────────────────
    IndexProduct("VEA",    "Vanguard FTSE Developed Markets",   "Developed Ex-US","FTSE Dev All Cap ex US","USD","NYSE","ETF", aum_bn=142.1, expense_ratio=0.05, issuer="Vanguard"),
    IndexProduct("EFA",    "iShares MSCI EAFE ETF",             "Developed Ex-US","MSCI EAFE","USD","NYSE","ETF", aum_bn=63.2, expense_ratio=0.32, issuer="BlackRock"),
    IndexProduct("IEFA",   "iShares Core MSCI EAFE",            "Developed Ex-US","MSCI EAFE IMI","USD","NYSE","ETF", aum_bn=115.2, expense_ratio=0.07, issuer="BlackRock"),
    IndexProduct("EFG",    "iShares MSCI EAFE Growth",          "Developed Ex-US","MSCI EAFE Growth","USD","NYSE","ETF", expense_ratio=0.39, issuer="BlackRock"),
    IndexProduct("EFV",    "iShares MSCI EAFE Value",           "Developed Ex-US","MSCI EAFE Value","USD","NYSE","ETF", expense_ratio=0.35, issuer="BlackRock"),

    # ── Factor / Style ───────────────────────────────────────────────────────
    IndexProduct("MTUM",   "iShares MSCI USA Momentum",         "US", "MSCI USA Momentum","USD","NASDAQ","ETF", expense_ratio=0.15, issuer="BlackRock"),
    IndexProduct("VLUE",   "iShares MSCI USA Value Factor",     "US", "MSCI USA Enhanced Value","USD","NYSE","ETF", expense_ratio=0.15, issuer="BlackRock"),
    IndexProduct("QUAL",   "iShares MSCI USA Quality Factor",   "US", "MSCI USA Quality","USD","NYSE","ETF", expense_ratio=0.15, issuer="BlackRock"),
    IndexProduct("USMV",   "iShares MSCI USA Min Vol",          "US", "MSCI USA Min Volatility","USD","NYSE","ETF", expense_ratio=0.15, issuer="BlackRock"),
    IndexProduct("IWF",    "iShares Russell 1000 Growth",       "US", "Russell 1000 Growth","USD","NYSE","ETF", expense_ratio=0.19, issuer="BlackRock"),
    IndexProduct("IWD",    "iShares Russell 1000 Value",        "US", "Russell 1000 Value","USD","NYSE","ETF", expense_ratio=0.19, issuer="BlackRock"),

    # ── Dividend ──────────────────────────────────────────────────────────────
    IndexProduct("VYM",    "Vanguard High Dividend Yield",      "US", "FTSE High Dividend Yield","USD","NYSE","ETF", aum_bn=64.1, expense_ratio=0.06, issuer="Vanguard"),
    IndexProduct("SCHD",   "Schwab US Dividend Equity",         "US", "Dow Jones US Dividend 100","USD","NYSE","ETF", aum_bn=62.8, expense_ratio=0.06, issuer="Schwab"),
    IndexProduct("DVY",    "iShares Select Dividend ETF",       "US", "Dow Jones US Select Dividend","USD","NASDAQ","ETF", expense_ratio=0.38, issuer="BlackRock"),
    IndexProduct("VIGI",   "Vanguard Intl Dividend Appreciation","Global","NASDAQ Intl Div Achievers","USD","NASDAQ","ETF", expense_ratio=0.15, issuer="Vanguard"),

    # ── ESG ──────────────────────────────────────────────────────────────────
    IndexProduct("ESGU",   "iShares MSCI USA ESG Optimized",    "US", "MSCI USA ESG Focus","USD","NASDAQ","ETF", expense_ratio=0.15, issuer="BlackRock"),
    IndexProduct("ESGV",   "Vanguard ESG US Stock ETF",         "US", "FTSE US All Cap Choice","USD","NYSE","ETF", expense_ratio=0.09, issuer="Vanguard"),
    IndexProduct("SUSL",   "iShares MSCI USA ESG Select",       "US", "MSCI USA ESG Select","USD","NASDAQ","ETF", expense_ratio=0.25, issuer="BlackRock"),
    IndexProduct("ESGE",   "iShares MSCI EM ESG Optimized",     "EM", "MSCI EM ESG Focus","USD","NYSE","ETF", expense_ratio=0.25, issuer="BlackRock"),

    # ── Total Market (US-listed) ──────────────────────────────────────────────
    IndexProduct("VTI",  "Vanguard Total Stock Market ETF",     "US", "CRSP US Total Market","USD","NYSE","ETF", aum_bn=441.2, expense_ratio=0.03, issuer="Vanguard"),
    IndexProduct("ITOT", "iShares Core S&P Total US Stock",     "US", "S&P Total Market","USD","NASDAQ","ETF", aum_bn=60.8, expense_ratio=0.03, issuer="BlackRock"),
    IndexProduct("SCHB", "Schwab US Broad Market ETF",          "US", "Dow Jones US Broad Market","USD","NYSE","ETF", aum_bn=28.3, expense_ratio=0.03, issuer="Schwab"),

    # ── Global (US-listed) ────────────────────────────────────────────────────
    IndexProduct("VT",   "Vanguard Total World Stock ETF",      "Global","FTSE Global All Cap","USD","NYSE","ETF", aum_bn=47.8, expense_ratio=0.07, issuer="Vanguard"),
    IndexProduct("ACWI", "iShares MSCI ACWI ETF",               "Global","MSCI ACWI","USD","NASDAQ","ETF", aum_bn=22.1, expense_ratio=0.32, issuer="BlackRock"),
    IndexProduct("ACWX", "iShares MSCI ACWI ex US ETF",         "Global","MSCI ACWI ex USA","USD","NASDAQ","ETF", aum_bn=4.8, expense_ratio=0.32, issuer="BlackRock"),
    IndexProduct("URTH", "iShares MSCI World ETF",               "Global","MSCI World","USD","NYSE","ETF", aum_bn=5.2, expense_ratio=0.24, issuer="BlackRock"),

    # ── LSE — S&P 500 ETFs ───────────────────────────────────────────────────
    IndexProduct("VUSA.L",  "Vanguard S&P 500 UCITS ETF (USD Dist)",    "US", "S&P 500", "USD", "LSE", "ETF", aum_bn=42.1, expense_ratio=0.07, issuer="Vanguard", isin="IE00B3XXRP09"),
    IndexProduct("VUAG.L",  "Vanguard S&P 500 UCITS ETF (GBP Acc)",     "US", "S&P 500", "GBP", "LSE", "ETF", aum_bn=35.6, expense_ratio=0.07, issuer="Vanguard", isin="IE00BFMXXD54"),
    IndexProduct("CSPX.L",  "iShares Core S&P 500 UCITS ETF USD Acc",   "US", "S&P 500", "USD", "LSE", "ETF", aum_bn=88.4, expense_ratio=0.07, issuer="BlackRock", isin="IE00B5BMR087"),
    IndexProduct("IUSA.L",  "iShares Core S&P 500 UCITS ETF USD Dist",  "US", "S&P 500", "USD", "LSE", "ETF", aum_bn=12.3, expense_ratio=0.07, issuer="BlackRock", isin="IE0031442068"),
    IndexProduct("SPXP.L",  "Invesco S&P 500 UCITS ETF Acc",            "US", "S&P 500", "USD", "LSE", "ETF", aum_bn=8.2,  expense_ratio=0.05, issuer="Invesco",   isin="IE00B3YCGJ38"),
    IndexProduct("SPYL.L",  "SPDR S&P 500 UCITS ETF",                   "US", "S&P 500", "USD", "LSE", "ETF", aum_bn=6.1,  expense_ratio=0.03, issuer="State Street", isin="IE00BJYDH287"),
    IndexProduct("XSPS.L",  "Xtrackers S&P 500 Swap UCITS ETF",         "US", "S&P 500", "GBP", "LSE", "ETF", aum_bn=5.8,  expense_ratio=0.15, issuer="DWS",       isin="IE00BJYDH287"),

    # ── LSE — MSCI World / Global ETFs ───────────────────────────────────────
    IndexProduct("SWDA.L",  "iShares Core MSCI World UCITS ETF",        "Global", "MSCI World", "USD", "LSE", "ETF", aum_bn=72.8, expense_ratio=0.20, issuer="BlackRock", isin="IE00B4L5Y983"),
    IndexProduct("IWDG.L",  "iShares Core MSCI World GBP Hedged ETF",   "Global", "MSCI World", "GBP", "LSE", "ETF", aum_bn=9.4,  expense_ratio=0.30, issuer="BlackRock", isin="IE00B4L5YX21"),
    IndexProduct("HMWO.L",  "HSBC MSCI World UCITS ETF",                "Global", "MSCI World", "USD", "LSE", "ETF", aum_bn=6.2,  expense_ratio=0.15, issuer="HSBC",      isin="IE00B4X9L533"),
    IndexProduct("VEVE.L",  "Vanguard FTSE Developed World UCITS ETF",  "Global", "FTSE Dev World","USD","LSE","ETF", aum_bn=8.9,  expense_ratio=0.12, issuer="Vanguard",  isin="IE00BKX55R35"),
    IndexProduct("ISAC.L",  "iShares MSCI ACWI UCITS ETF",              "Global", "MSCI ACWI",  "USD", "LSE", "ETF", aum_bn=14.6, expense_ratio=0.20, issuer="BlackRock", isin="IE00B6R52259"),
    IndexProduct("XDWD.L",  "Xtrackers MSCI World Swap UCITS ETF",      "Global", "MSCI World", "USD", "LSE", "ETF", aum_bn=10.1, expense_ratio=0.19, issuer="DWS",       isin="IE00BJ0KDQ92"),
    IndexProduct("HMCX.L",  "HSBC MSCI World GBP Hedged UCITS ETF",     "Global", "MSCI World", "GBP", "LSE", "ETF", aum_bn=4.1,  expense_ratio=0.15, issuer="HSBC",      isin="IE00BMCZMD63"),

    # ── LSE — Emerging Markets (GBP accessible) ───────────────────────────────
    IndexProduct("VFEM.L",  "Vanguard FTSE Emerging Markets UCITS ETF", "EM", "FTSE EM",    "USD", "LSE", "ETF", aum_bn=4.8,  expense_ratio=0.22, issuer="Vanguard",  isin="IE00B3VVMM84"),
    IndexProduct("EMIM.L",  "iShares Core MSCI EM IMI UCITS ETF",       "EM", "MSCI EM IMI","USD", "LSE", "ETF", aum_bn=18.4, expense_ratio=0.18, issuer="BlackRock", isin="IE00BKM4GZ66"),
    IndexProduct("XMEM.L",  "Xtrackers MSCI EM Swap UCITS ETF",         "EM", "MSCI EM",    "USD", "LSE", "ETF", aum_bn=5.1,  expense_ratio=0.20, issuer="DWS",       isin="IE00BTJRMP35"),
    IndexProduct("HMEM.L",  "HSBC MSCI Emerging Markets UCITS ETF",     "EM", "MSCI EM",    "USD", "LSE", "ETF", aum_bn=3.6,  expense_ratio=0.15, issuer="HSBC",      isin="IE00B3VVMM84"),

    # ── LSE — Regional ETFs ───────────────────────────────────────────────────
    IndexProduct("VHYL.L",  "Vanguard FTSE All-World High Div Yield",   "Global", "FTSE AW High Div","USD","LSE","ETF", aum_bn=5.6, expense_ratio=0.29, issuer="Vanguard",  isin="IE00B8GKDB10"),
    IndexProduct("VJPN.L",  "Vanguard FTSE Japan UCITS ETF",            "Asia",   "FTSE Japan", "JPY", "LSE", "ETF", aum_bn=1.2, expense_ratio=0.15, issuer="Vanguard",  isin="IE00B95PGT31"),
    IndexProduct("VERX.L",  "Vanguard FTSE Dev Europe ex UK UCITS ETF", "Europe", "FTSE Dev Europe ex UK","EUR","LSE","ETF", aum_bn=2.8, expense_ratio=0.10, issuer="Vanguard", isin="IE00B945VV12"),
    IndexProduct("VAPX.L",  "Vanguard FTSE Dev Asia Pacific ex JP ETF", "Pacific","FTSE Dev Asia Pacific","USD","LSE","ETF", aum_bn=1.1, expense_ratio=0.15, issuer="Vanguard", isin="IE00B9F5YL18"),
    IndexProduct("IDJG.L",  "iShares Core MSCI Japan IMI UCITS ETF",    "Asia",   "MSCI Japan IMI","JPY","LSE","ETF", aum_bn=4.1, expense_ratio=0.12, issuer="BlackRock", isin="IE00B4L5YC18"),
    IndexProduct("IBTS.L",  "iShares $ Treasury Bond 1-3yr ETF",        "US",     "ICE US Treasury 1-3Y","USD","LSE","ETF", aum_bn=8.2, expense_ratio=0.07, issuer="BlackRock", isin="IE00B14X4S71"),

    # ── LSE — Leverage / Inverse ─────────────────────────────────────────────
    IndexProduct("3USL.L",  "Leverage Shares 3× US 500 ETP",            "US", "S&P 500",    "GBP", "LSE", "ETP", leverage=3.0, expense_ratio=0.75, issuer="Leverage Shares"),
    IndexProduct("3USS.L",  "Leverage Shares -3× US 500 ETP",           "US", "S&P 500",    "GBP", "LSE", "ETP", leverage=-3.0, is_inverse=True, expense_ratio=0.75, issuer="Leverage Shares"),
    IndexProduct("3NQL.L",  "Leverage Shares 3× Nasdaq 100 ETP",        "US", "NASDAQ-100", "GBP", "LSE", "ETP", leverage=3.0, expense_ratio=0.75, issuer="Leverage Shares"),
    IndexProduct("QQQ3.L",  "WisdomTree NASDAQ 100 3× Daily ETP",       "US", "NASDAQ-100", "USD", "LSE", "ETP", leverage=3.0, expense_ratio=0.75, issuer="WisdomTree"),
    IndexProduct("SP3L.L",  "WisdomTree S&P 500 3× Daily ETP",          "US", "S&P 500",    "USD", "LSE", "ETP", leverage=3.0, expense_ratio=0.75, issuer="WisdomTree"),

    # ── US Sector ETFs — SPDR Select Sector ─────────────────────────────────
    IndexProduct("XLK",  "Technology Select Sector SPDR",         "US", "S&P 500 Tech",          "USD","NYSE","ETF", aum_bn=72.4, expense_ratio=0.09, issuer="State Street"),
    IndexProduct("XLF",  "Financial Select Sector SPDR",          "US", "S&P 500 Financials",    "USD","NYSE","ETF", aum_bn=44.1, expense_ratio=0.09, issuer="State Street"),
    IndexProduct("XLE",  "Energy Select Sector SPDR",             "US", "S&P 500 Energy",        "USD","NYSE","ETF", aum_bn=32.8, expense_ratio=0.09, issuer="State Street"),
    IndexProduct("XLV",  "Health Care Select Sector SPDR",        "US", "S&P 500 Health Care",   "USD","NYSE","ETF", aum_bn=38.9, expense_ratio=0.09, issuer="State Street"),
    IndexProduct("XLI",  "Industrial Select Sector SPDR",         "US", "S&P 500 Industrials",   "USD","NYSE","ETF", aum_bn=22.1, expense_ratio=0.09, issuer="State Street"),
    IndexProduct("XLY",  "Consumer Discretionary Select Sector",  "US", "S&P 500 Cons. Disc.",   "USD","NYSE","ETF", aum_bn=21.4, expense_ratio=0.09, issuer="State Street"),
    IndexProduct("XLP",  "Consumer Staples Select Sector SPDR",   "US", "S&P 500 Cons. Staples", "USD","NYSE","ETF", aum_bn=14.8, expense_ratio=0.09, issuer="State Street"),
    IndexProduct("XLU",  "Utilities Select Sector SPDR",          "US", "S&P 500 Utilities",     "USD","NYSE","ETF", aum_bn=14.2, expense_ratio=0.09, issuer="State Street"),
    IndexProduct("XLB",  "Materials Select Sector SPDR",          "US", "S&P 500 Materials",     "USD","NYSE","ETF", aum_bn=7.8,  expense_ratio=0.09, issuer="State Street"),
    IndexProduct("XLRE", "Real Estate Select Sector SPDR",        "US", "S&P 500 Real Estate",   "USD","NYSE","ETF", aum_bn=6.9,  expense_ratio=0.09, issuer="State Street"),
    IndexProduct("XLC",  "Communication Services Select Sector",  "US", "S&P 500 Comm. Svcs.",   "USD","NYSE","ETF", aum_bn=17.3, expense_ratio=0.09, issuer="State Street"),

    # ── US Sector ETFs — iShares / Invesco ──────────────────────────────────
    IndexProduct("SMH",  "VanEck Semiconductor ETF",              "US", "MVIS US Listed Semi 25","USD","NASDAQ","ETF", aum_bn=22.8, expense_ratio=0.35, issuer="VanEck"),
    IndexProduct("SOXX", "iShares Semiconductor ETF",             "US", "PHLX Semiconductor",    "USD","NASDAQ","ETF", aum_bn=13.4, expense_ratio=0.35, issuer="BlackRock"),
    IndexProduct("IGV",  "iShares Expanded Tech-Software Sector", "US", "S&P N. Amer. Tech-SW",  "USD","CBOE", "ETF", aum_bn=8.1,  expense_ratio=0.41, issuer="BlackRock"),
    IndexProduct("IYW",  "iShares US Technology ETF",             "US", "Russell 1000 Tech RIC", "USD","NYSE", "ETF", aum_bn=16.2, expense_ratio=0.40, issuer="BlackRock"),
    IndexProduct("IHI",  "iShares US Medical Devices ETF",        "US", "Dow Jones US Med. Dev.", "USD","NYSE", "ETF", aum_bn=5.4,  expense_ratio=0.40, issuer="BlackRock"),
    IndexProduct("IBB",  "iShares Biotechnology ETF",             "US", "Nasdaq Biotechnology",  "USD","NASDAQ","ETF", aum_bn=8.8, expense_ratio=0.44, issuer="BlackRock"),
    IndexProduct("IYF",  "iShares US Financials ETF",             "US", "Dow Jones US Financials","USD","NYSE","ETF", aum_bn=3.4,  expense_ratio=0.40, issuer="BlackRock"),
    IndexProduct("IYE",  "iShares US Energy ETF",                 "US", "Dow Jones US Energy",   "USD","NYSE","ETF", aum_bn=1.6,  expense_ratio=0.40, issuer="BlackRock"),
    IndexProduct("IYR",  "iShares US Real Estate ETF",            "US", "Dow Jones US Real Est.", "USD","NYSE","ETF", aum_bn=4.5,  expense_ratio=0.40, issuer="BlackRock"),
    IndexProduct("ARKK", "ARK Innovation ETF",                    "US", "ARK Innovation",         "USD","NYSE","ETF", aum_bn=6.2,  expense_ratio=0.75, issuer="ARK"),
    IndexProduct("BOTZ", "Global X Robotics & Artificial Intel.", "US", "Indxx Global Robotics",  "USD","NASDAQ","ETF",aum_bn=2.1,  expense_ratio=0.68, issuer="Global X"),

    # ── US Total Market ──────────────────────────────────────────────────────
    IndexProduct("IJH",  "iShares Core S&P Mid-Cap ETF",          "US", "S&P MidCap 400",        "USD","NYSE","ETF", aum_bn=82.3, expense_ratio=0.05, issuer="BlackRock"),
    IndexProduct("IJR",  "iShares Core S&P Small-Cap ETF",        "US", "S&P SmallCap 600",      "USD","NYSE","ETF", aum_bn=77.1, expense_ratio=0.06, issuer="BlackRock"),
    IndexProduct("VO",   "Vanguard Mid-Cap ETF",                  "US", "CRSP US Mid Cap",        "USD","NYSE","ETF", aum_bn=60.2, expense_ratio=0.04, issuer="Vanguard"),
    IndexProduct("VBR",  "Vanguard Small-Cap Value ETF",          "US", "CRSP US Small Cap Value","USD","NYSE","ETF", aum_bn=22.1, expense_ratio=0.07, issuer="Vanguard"),
    IndexProduct("VBK",  "Vanguard Small-Cap Growth ETF",         "US", "CRSP US Small Cap Growth","USD","NYSE","ETF",aum_bn=14.8, expense_ratio=0.07, issuer="Vanguard"),
    IndexProduct("VIOO", "Vanguard S&P Small-Cap 600 ETF",        "US", "S&P SmallCap 600",       "USD","NYSE","ETF", aum_bn=4.2,  expense_ratio=0.10, issuer="Vanguard"),
    IndexProduct("MGK",  "Vanguard Mega Cap Growth ETF",          "US", "US Mega Cap Growth",     "USD","NYSE","ETF", aum_bn=21.4, expense_ratio=0.07, issuer="Vanguard"),
    IndexProduct("MGV",  "Vanguard Mega Cap Value ETF",           "US", "US Mega Cap Value",      "USD","NYSE","ETF", aum_bn=6.8,  expense_ratio=0.07, issuer="Vanguard"),
    IndexProduct("VV",   "Vanguard Large-Cap ETF",                "US", "CRSP US Large Cap",      "USD","NYSE","ETF", aum_bn=38.4, expense_ratio=0.04, issuer="Vanguard"),
    IndexProduct("VXF",  "Vanguard Extended Market ETF",          "US", "S&P Completion Index",   "USD","NYSE","ETF", aum_bn=15.6, expense_ratio=0.06, issuer="Vanguard"),
    IndexProduct("SCHX", "Schwab US Large-Cap ETF",               "US", "Dow Jones US Large-Cap", "USD","NYSE","ETF", aum_bn=45.2, expense_ratio=0.03, issuer="Schwab"),
    IndexProduct("SCHA", "Schwab US Small-Cap ETF",               "US", "Dow Jones US Small-Cap", "USD","NYSE","ETF", aum_bn=16.8, expense_ratio=0.04, issuer="Schwab"),
    IndexProduct("SCHM", "Schwab US Mid-Cap ETF",                 "US", "Dow Jones US Mid-Cap",   "USD","NYSE","ETF", aum_bn=11.2, expense_ratio=0.04, issuer="Schwab"),
    IndexProduct("SCHG", "Schwab US Large-Cap Growth ETF",        "US", "Dow Jones US Large-Cap Growth","USD","NYSE","ETF",aum_bn=31.4,expense_ratio=0.04,issuer="Schwab"),
    IndexProduct("SCHV", "Schwab US Large-Cap Value ETF",         "US", "Dow Jones US Large-Cap Value", "USD","NYSE","ETF",aum_bn=12.1,expense_ratio=0.04,issuer="Schwab"),

    # ── Income / Dividend ────────────────────────────────────────────────────
    IndexProduct("JEPI", "JPMorgan Equity Premium Income ETF",    "US", "S&P 500 Covered Call",  "USD","NYSE","ETF", aum_bn=36.8, expense_ratio=0.35, issuer="JPMorgan"),
    IndexProduct("JEPQ", "JPMorgan NASDAQ Equity Premium Income", "US", "NASDAQ-100 Covered Call","USD","NYSE","ETF", aum_bn=18.4, expense_ratio=0.35, issuer="JPMorgan"),
    IndexProduct("SPYD", "SPDR Portfolio S&P 500 High Dividend",  "US", "S&P 500 High Div",      "USD","NYSE","ETF", aum_bn=7.2,  expense_ratio=0.07, issuer="State Street"),
    IndexProduct("HDV",  "iShares Core High Dividend ETF",        "US", "Morningstar Div Yield", "USD","NYSE","ETF", aum_bn=8.4,  expense_ratio=0.08, issuer="BlackRock"),
    IndexProduct("PFF",  "iShares Preferred & Income Securities", "US", "ICE Preferred Sec.",     "USD","NASDAQ","ETF",aum_bn=13.1,expense_ratio=0.46, issuer="BlackRock"),
    IndexProduct("SDIV", "Global X SuperDividend ETF",            "Global","Solactive Glb SuperDiv","USD","NYSE","ETF",aum_bn=0.8, expense_ratio=0.58, issuer="Global X"),
    IndexProduct("DIVO", "Amplify CWP Enhanced Dividend Income",  "US", "Covered Call Dividend",  "USD","NYSE","ETF", aum_bn=3.2,  expense_ratio=0.56, issuer="Amplify"),
    IndexProduct("FDVV", "Fidelity High Dividend ETF",            "US", "Fidelity High Div",      "USD","NYSE","ETF", aum_bn=1.8,  expense_ratio=0.29, issuer="Fidelity"),

    # ── US Fixed Income / Bonds ──────────────────────────────────────────────
    IndexProduct("AGG",  "iShares Core US Aggregate Bond",        "US", "Bloomberg US Agg",      "USD","NYSE","ETF", aum_bn=112.4, expense_ratio=0.03, issuer="BlackRock"),
    IndexProduct("BND",  "Vanguard Total Bond Market ETF",        "US", "Bloomberg US Agg Float","USD","NYSE","ETF", aum_bn=110.8, expense_ratio=0.03, issuer="Vanguard"),
    IndexProduct("TLT",  "iShares 20+ Year Treasury Bond ETF",    "US", "ICE US Treasury 20+Y",  "USD","NASDAQ","ETF",aum_bn=52.1, expense_ratio=0.15, issuer="BlackRock"),
    IndexProduct("IEF",  "iShares 7-10 Year Treasury Bond ETF",   "US", "ICE US Treasury 7-10Y", "USD","NASDAQ","ETF",aum_bn=28.4, expense_ratio=0.15, issuer="BlackRock"),
    IndexProduct("SHY",  "iShares 1-3 Year Treasury Bond ETF",    "US", "ICE US Treasury 1-3Y",  "USD","NASDAQ","ETF",aum_bn=24.8, expense_ratio=0.15, issuer="BlackRock"),
    IndexProduct("GOVT", "iShares US Treasury Bond ETF",          "US", "ICE US Treasury Core",  "USD","NYSE","ETF", aum_bn=28.1, expense_ratio=0.05, issuer="BlackRock"),
    IndexProduct("LQD",  "iShares iBoxx Invmt Grade Corp Bond",   "US", "Markit iBoxx USD LiqIG","USD","NYSE","ETF", aum_bn=33.4, expense_ratio=0.14, issuer="BlackRock"),
    IndexProduct("HYG",  "iShares iBoxx $ High Yield Corp Bond",  "US", "Markit iBoxx USD HY",   "USD","NYSE","ETF", aum_bn=16.8, expense_ratio=0.48, issuer="BlackRock"),
    IndexProduct("JNK",  "SPDR Bloomberg High Yield Bond ETF",    "US", "Bloomberg HY Very Liqd","USD","NYSE","ETF", aum_bn=9.2,  expense_ratio=0.40, issuer="State Street"),
    IndexProduct("TIP",  "iShares TIPS Bond ETF",                 "US", "Bloomberg US TIPS",     "USD","NYSE","ETF", aum_bn=18.2, expense_ratio=0.19, issuer="BlackRock"),
    IndexProduct("VTIP", "Vanguard Short-Term Inflation-Protect.", "US", "Bloomberg US 0-5Y TIPS","USD","NASDAQ","ETF",aum_bn=14.1,expense_ratio=0.04, issuer="Vanguard"),
    IndexProduct("VCIT", "Vanguard Interm-Term Corporate Bond",   "US", "Bloomberg US 5-10Y Corp","USD","NASDAQ","ETF",aum_bn=46.2,expense_ratio=0.04, issuer="Vanguard"),
    IndexProduct("VCSH", "Vanguard Short-Term Corporate Bond",    "US", "Bloomberg US 1-5Y Corp", "USD","NASDAQ","ETF",aum_bn=36.8,expense_ratio=0.04, issuer="Vanguard"),
    IndexProduct("VGSH", "Vanguard Short-Term Treasury ETF",      "US", "Bloomberg US 1-3Y Tsy", "USD","NASDAQ","ETF",aum_bn=22.4,expense_ratio=0.04, issuer="Vanguard"),
    IndexProduct("VGLT", "Vanguard Long-Term Treasury ETF",       "US", "Bloomberg US Long Tsy", "USD","NASDAQ","ETF",aum_bn=6.8, expense_ratio=0.04, issuer="Vanguard"),
    IndexProduct("MUB",  "iShares National Muni Bond ETF",        "US", "ICE AMT-Free US Muni",  "USD","NYSE","ETF", aum_bn=36.4, expense_ratio=0.07, issuer="BlackRock"),
    IndexProduct("EMB",  "iShares JP Morgan USD EM Bond ETF",     "EM", "JPMorgan EMBI Glb Core","USD","NYSE","ETF", aum_bn=16.2, expense_ratio=0.39, issuer="BlackRock"),
    IndexProduct("BNDX", "Vanguard Total Intl Bond ETF (Hdgd)",   "Global","Bloomberg Glb Agg ex-US","USD","NASDAQ","ETF",aum_bn=60.4,expense_ratio=0.07,issuer="Vanguard"),

    # ── Real Estate / REIT ───────────────────────────────────────────────────
    IndexProduct("VNQ",  "Vanguard Real Estate ETF",              "US", "MSCI US REIT",          "USD","NYSE","ETF", aum_bn=34.8, expense_ratio=0.12, issuer="Vanguard"),
    IndexProduct("USRT", "iShares Core US REIT ETF",              "US", "FTSE NAREIT All Equity","USD","NYSE","ETF", aum_bn=2.4,  expense_ratio=0.08, issuer="BlackRock"),
    IndexProduct("REET", "iShares Global REIT ETF",               "Global","FTSE EPRA NAREIT Glb","USD","NYSE","ETF", aum_bn=3.2,  expense_ratio=0.14, issuer="BlackRock"),
    IndexProduct("RWR",  "SPDR Dow Jones REIT ETF",               "US", "Dow Jones US Select REIT","USD","NYSE","ETF",aum_bn=2.1,  expense_ratio=0.25, issuer="State Street"),

    # ── Factor / Smart Beta — Advanced ───────────────────────────────────────
    IndexProduct("AVUV", "Avantis US Small Cap Value ETF",        "US", "US Small Cap Value",    "USD","NYSE","ETF", aum_bn=11.4, expense_ratio=0.25, issuer="Avantis"),
    IndexProduct("AVDV", "Avantis Intl Small Cap Value ETF",      "Developed Ex-US","Intl Small Cap Val","USD","CBOE","ETF",aum_bn=6.2,expense_ratio=0.36,issuer="Avantis"),
    IndexProduct("DFAC", "Dimensional US Core Equity 2 ETF",      "US", "US Core Equity 2",      "USD","NYSE","ETF", aum_bn=27.4, expense_ratio=0.17, issuer="DFA"),
    IndexProduct("DFAX", "Dimensional World ex US Core Equity 2", "Global","World ex US Core Eq2","USD","NYSE","ETF",aum_bn=11.8, expense_ratio=0.23, issuer="DFA"),
    IndexProduct("DFSV", "Dimensional US Small Cap Value ETF",    "US", "US Small Cap Value",    "USD","NYSE","ETF", aum_bn=5.2,  expense_ratio=0.30, issuer="DFA"),
    IndexProduct("COWZ", "Pacer US Cash Cows 100 ETF",            "US", "Pacer US Cash Cows 100","USD","CBOE","ETF", aum_bn=23.1, expense_ratio=0.49, issuer="Pacer"),
    IndexProduct("QQQE", "Direxion NASDAQ-100 Equal Weighted",    "US", "NASDAQ-100 Equal Wt.",  "USD","NASDAQ","ETF",aum_bn=1.8,  expense_ratio=0.35, issuer="Direxion"),
    IndexProduct("RSP",  "Invesco S&P 500 Equal Weight ETF",      "US", "S&P 500 Equal Wt.",     "USD","NYSE","ETF", aum_bn=57.4, expense_ratio=0.20, issuer="Invesco"),
    IndexProduct("EQAL", "Invesco Russell 1000 Equal Weight ETF", "US", "Russell 1000 Equal Wt.","USD","NYSE","ETF", aum_bn=0.8,  expense_ratio=0.20, issuer="Invesco"),

    # ── China / Emerging Markets expanded ───────────────────────────────────
    IndexProduct("MCHI", "iShares MSCI China ETF",                "Asia","MSCI China",           "USD","NASDAQ","ETF",aum_bn=6.1,  expense_ratio=0.59, issuer="BlackRock"),
    IndexProduct("CNYA", "iShares MSCI China A Shares ETF",       "Asia","MSCI China A Inc",     "USD","NYSE","ETF", aum_bn=0.9,  expense_ratio=0.60, issuer="BlackRock"),
    IndexProduct("PGJ",  "Invesco Golden Dragon China ETF",        "Asia","NASDAQ Golden Dragon", "USD","NASDAQ","ETF",aum_bn=0.4,  expense_ratio=0.70, issuer="Invesco"),
    IndexProduct("FLCH", "Franklin FTSE China ETF",               "Asia","FTSE China RIC Cappe", "USD","NYSE","ETF", aum_bn=0.3,  expense_ratio=0.19, issuer="Franklin"),
    IndexProduct("FLIA", "Franklin FTSE Asia ex Japan ETF",       "Asia","FTSE Asia Pacific ex JP","USD","NYSE","ETF",aum_bn=0.2,  expense_ratio=0.19, issuer="Franklin"),

    # ── Europe / Global expanded ─────────────────────────────────────────────
    IndexProduct("SCHF", "Schwab International Equity ETF",       "Developed Ex-US","FTSE Dev Ex-US","USD","NYSE","ETF",aum_bn=42.1,expense_ratio=0.06,issuer="Schwab"),
    IndexProduct("SCHE", "Schwab Emerging Markets Equity ETF",    "EM","FTSE EM",                 "USD","NYSE","ETF", aum_bn=10.4, expense_ratio=0.11, issuer="Schwab"),
    IndexProduct("SPDW", "SPDR Portfolio Dev World ex-US ETF",    "Developed Ex-US","S&P Dev ex-US","USD","NYSE","ETF",aum_bn=18.2,expense_ratio=0.04, issuer="State Street"),
    IndexProduct("SPEM", "SPDR Portfolio Emerging Markets ETF",   "EM","S&P EM BMI",              "USD","NYSE","ETF", aum_bn=8.4,  expense_ratio=0.07, issuer="State Street"),
    IndexProduct("VPL",  "Vanguard FTSE Pacific ETF",             "Pacific","FTSE Pacific",       "USD","NYSE","ETF", aum_bn=5.1,  expense_ratio=0.08, issuer="Vanguard"),
    IndexProduct("ILF",  "iShares Latin America 40 ETF",          "LatAm","S&P Latin America 40","USD","NYSE","ETF", aum_bn=1.2,  expense_ratio=0.48, issuer="BlackRock"),

    # ── Mutual Funds (US index funds) ────────────────────────────────────────
    IndexProduct("FXAIX", "Fidelity 500 Index Fund",              "US","S&P 500",                "USD","OTC","Fund", aum_bn=580.1,expense_ratio=0.015,issuer="Fidelity"),
    IndexProduct("VFIAX", "Vanguard 500 Index Fund Admiral",      "US","S&P 500",                "USD","OTC","Fund", aum_bn=492.3,expense_ratio=0.04, issuer="Vanguard"),
    IndexProduct("SWPPX", "Schwab S&P 500 Index Fund",            "US","S&P 500",                "USD","OTC","Fund", aum_bn=88.4, expense_ratio=0.02, issuer="Schwab"),
    IndexProduct("FSKAX", "Fidelity Total Market Index Fund",     "US","Fidelity US Total Mkt",  "USD","OTC","Fund", aum_bn=72.1, expense_ratio=0.015,issuer="Fidelity"),
    IndexProduct("VTSAX", "Vanguard Total Stock Mkt Index Admiral","US","CRSP US Total Market",  "USD","OTC","Fund", aum_bn=392.1,expense_ratio=0.04, issuer="Vanguard"),
    IndexProduct("FZROX", "Fidelity ZERO Total Market Index Fund","US","Fidelity US Total Mkt",  "USD","OTC","Fund", aum_bn=14.2, expense_ratio=0.00, issuer="Fidelity"),
    IndexProduct("FZILX", "Fidelity ZERO International Index",    "Global","Fidelity Global ex-US","USD","OTC","Fund",aum_bn=6.4,  expense_ratio=0.00, issuer="Fidelity"),
    IndexProduct("VTIAX", "Vanguard Total Intl Stock Index Admiral","Global","FTSE Global All Cap ex US","USD","OTC","Fund",aum_bn=184.2,expense_ratio=0.11,issuer="Vanguard"),
    IndexProduct("VBTLX", "Vanguard Total Bond Market Index Admrl","US","Bloomberg US Float-Adj Agg","USD","OTC","Fund",aum_bn=306.4,expense_ratio=0.05,issuer="Vanguard"),
    IndexProduct("FCNTX", "Fidelity Contrafund",                  "US","Active Growth",          "USD","OTC","Fund", aum_bn=102.4,expense_ratio=0.39, issuer="Fidelity"),
    IndexProduct("VWELX", "Vanguard Wellington Fund Admiral",     "US","Balanced 65/35",         "USD","OTC","Fund", aum_bn=92.1, expense_ratio=0.17, issuer="Vanguard"),
    IndexProduct("PRWCX", "T. Rowe Price Capital Appreciation",  "US","Balanced Growth",         "USD","OTC","Fund", aum_bn=52.4, expense_ratio=0.71, issuer="T. Rowe Price"),
    IndexProduct("DODGX", "Dodge & Cox Stock Fund",               "US","Active US Large-Cap Val","USD","OTC","Fund", aum_bn=86.2, expense_ratio=0.51, issuer="Dodge & Cox"),
    IndexProduct("PRGFX", "T. Rowe Price Growth Stock Fund",      "US","Active US Large-Cap Grw","USD","OTC","Fund", aum_bn=68.1, expense_ratio=0.64, issuer="T. Rowe Price"),
    IndexProduct("AGTHX", "American Funds Growth Fund of America","US","Active US Large-Cap Grw","USD","OTC","Fund", aum_bn=214.2,expense_ratio=0.64, issuer="American Funds"),
    IndexProduct("AIVSX", "American Funds Investment Co. of Amer.","US","Active US Large-Cap Bld","USD","OTC","Fund",aum_bn=146.8,expense_ratio=0.57, issuer="American Funds"),
    IndexProduct("CWGIX", "American Funds Capital World Grwth Inc","Global","Active Global Blend","USD","OTC","Fund",aum_bn=98.1, expense_ratio=0.76, issuer="American Funds"),
    IndexProduct("ANCFX", "American Funds Fundamental Investors", "US","Active US Blend",        "USD","OTC","Fund", aum_bn=102.4,expense_ratio=0.59, issuer="American Funds"),

    # ── Allocation / Multi-Asset ─────────────────────────────────────────────
    IndexProduct("AOR",  "iShares Core Growth Allocation ETF",    "Global","Core Growth 60/40",  "USD","NYSE","ETF", aum_bn=2.1,  expense_ratio=0.15, issuer="BlackRock"),
    IndexProduct("AOA",  "iShares Core Aggressive Allocation ETF","Global","Core Aggressive 80/20","USD","NYSE","ETF",aum_bn=1.8,  expense_ratio=0.15, issuer="BlackRock"),
    IndexProduct("AOM",  "iShares Core Moderate Allocation ETF",  "Global","Core Moderate 40/60","USD","NYSE","ETF", aum_bn=0.9,  expense_ratio=0.15, issuer="BlackRock"),
    IndexProduct("AOK",  "iShares Core Conservative Allocation",  "Global","Core Conservative 30/70","USD","NYSE","ETF",aum_bn=0.6,expense_ratio=0.15, issuer="BlackRock"),
    IndexProduct("VBIAX","Vanguard Balanced Index Admiral",        "US","60/40 US Blend",         "USD","OTC", "Fund",aum_bn=46.8, expense_ratio=0.07, issuer="Vanguard"),

    # ── Commodities ──────────────────────────────────────────────────────────
    IndexProduct("GSG",  "iShares S&P GSCI Commodity-Indexed",   "Global","S&P GSCI",            "USD","NYSE","ETF", aum_bn=1.2,  expense_ratio=0.75, issuer="BlackRock"),
    IndexProduct("PDBC", "Invesco Optimum Yield Diversified Comm","Global","DBIQ Optimum Yd Div", "USD","NASDAQ","ETF",aum_bn=5.4, expense_ratio=0.59, issuer="Invesco"),
    IndexProduct("DJP",  "iPath Bloomberg Commodity Index TR ETN","Global","Bloomberg Commodity", "USD","NYSE","ETN", aum_bn=0.8,  expense_ratio=0.70, issuer="Barclays"),
    IndexProduct("BCI",  "abrdn Bloomberg All Commodity Strategy","Global","Bloomberg All Commod.","USD","NYSE","ETF", aum_bn=0.4,  expense_ratio=0.25, issuer="abrdn"),

    # ── S&P 500 Style / Factor splits ────────────────────────────────────────
    IndexProduct("IVW",  "iShares S&P 500 Growth ETF",           "US","S&P 500 Growth",          "USD","NYSE","ETF", aum_bn=38.4, expense_ratio=0.18, issuer="BlackRock"),
    IndexProduct("IVE",  "iShares S&P 500 Value ETF",            "US","S&P 500 Value",           "USD","NYSE","ETF", aum_bn=20.1, expense_ratio=0.18, issuer="BlackRock"),
    IndexProduct("VOOG", "Vanguard S&P 500 Growth ETF",          "US","S&P 500 Growth",          "USD","NYSE","ETF", aum_bn=14.2, expense_ratio=0.10, issuer="Vanguard"),
    IndexProduct("VOOV", "Vanguard S&P 500 Value ETF",           "US","S&P 500 Value",           "USD","NYSE","ETF", aum_bn=5.8,  expense_ratio=0.10, issuer="Vanguard"),
    IndexProduct("SPGP", "Invesco S&P 500 GARP ETF",             "US","S&P 500 GARP",            "USD","NYSE","ETF", aum_bn=2.8,  expense_ratio=0.36, issuer="Invesco"),
    IndexProduct("SPVU", "Invesco S&P 500 Enhanced Value ETF",   "US","S&P 500 Enhanced Value",  "USD","NYSE","ETF", aum_bn=0.4,  expense_ratio=0.13, issuer="Invesco"),
    IndexProduct("SPMO", "Invesco S&P 500 Momentum ETF",         "US","S&P 500 Momentum",        "USD","NYSE","ETF", aum_bn=1.8,  expense_ratio=0.13, issuer="Invesco"),
    IndexProduct("SPLV", "Invesco S&P 500 Low Volatility ETF",   "US","S&P 500 Low Volatility",  "USD","NYSE","ETF", aum_bn=6.2,  expense_ratio=0.25, issuer="Invesco"),
    IndexProduct("SPHQ", "Invesco S&P 500 Quality ETF",          "US","S&P 500 Quality",         "USD","NYSE","ETF", aum_bn=5.4,  expense_ratio=0.15, issuer="Invesco"),
    IndexProduct("SPHD", "Invesco S&P 500 High Dividend Low Vol","US","S&P 500 High Div Low Vol","USD","NYSE","ETF", aum_bn=2.8,  expense_ratio=0.30, issuer="Invesco"),
    IndexProduct("XSLV", "Invesco S&P SmallCap Low Volatility",  "US","S&P 600 Low Volatility",  "USD","NYSE","ETF", aum_bn=0.8,  expense_ratio=0.25, issuer="Invesco"),
    IndexProduct("XMHQ", "Invesco S&P MidCap Quality ETF",       "US","S&P MidCap 400 Quality",  "USD","NYSE","ETF", aum_bn=1.2,  expense_ratio=0.25, issuer="Invesco"),

    # ── S&P 500 Options-Enhanced / Buffer ETFs ────────────────────────────────
    IndexProduct("NUSI", "Nationwide Risk-Managed Income ETF",   "US","Nasdaq Covered Call",     "USD","NYSE","ETF", aum_bn=0.8,  expense_ratio=0.68, issuer="Nationwide"),
    IndexProduct("XYLD", "Global X S&P 500 Covered Call ETF",    "US","S&P 500 Covered Call",    "USD","NYSE","ETF", aum_bn=2.6,  expense_ratio=0.60, issuer="Global X"),
    IndexProduct("QYLD", "Global X NASDAQ Covered Call ETF",     "US","NASDAQ-100 Covered Call", "USD","NASDAQ","ETF",aum_bn=7.8, expense_ratio=0.60, issuer="Global X"),
    IndexProduct("RYLD", "Global X Russell 2000 Covered Call",   "US","Russell 2000 Covered Call","USD","NYSE","ETF",aum_bn=1.3, expense_ratio=0.60, issuer="Global X"),

    # ── LSE — Additional unique ETFs ──────────────────────────────────────────
    IndexProduct("SSAC.L","iShares Core MSCI World ACWI ETF",    "Global","MSCI ACWI",           "USD","LSE","ETF", aum_bn=12.1, expense_ratio=0.20, issuer="BlackRock"),
    IndexProduct("WPEA.L","Invesco MSCI World ETF (Acc)",        "Developed","MSCI World",       "USD","LSE","ETF", aum_bn=4.2,  expense_ratio=0.19, issuer="Invesco"),
]


def fetch_prices(tickers: list[str]) -> dict[str, dict]:
    """Fetch latest close price + 1d % change from yfinance. Returns {} on failure."""
    import math

    def _clean(v) -> Optional[float]:
        try:
            f = float(v)
            return None if (math.isnan(f) or math.isinf(f)) else f
        except Exception:
            return None

    try:
        import yfinance as yf
        data: dict[str, dict] = {}
        batch = yf.download(tickers, period="5d", auto_adjust=True,
                            progress=False, threads=True)
        closes = batch.get("Close", batch)
        if closes is None or closes.empty:
            return data

        # yf.download with a single ticker returns a Series for Close; wrap it
        import pandas as pd
        if isinstance(closes, pd.Series):
            closes = closes.to_frame(name=tickers[0])

        # Drop rows where ALL values are NaN, then take last two valid rows
        closes = closes.dropna(how="all")
        if closes.empty:
            return data

        last = closes.iloc[-1]
        prev = closes.iloc[-2] if len(closes) >= 2 else closes.iloc[-1]

        for t in tickers:
            try:
                p  = _clean(last.get(t))
                p0 = _clean(prev.get(t))
                pct = round((p - p0) / p0 * 100, 2) if (p and p0 and p0 != 0) else None
                if p is not None:
                    data[t] = {"price": round(p, 4), "chg_pct": pct}
            except Exception:
                pass
        return data
    except Exception as exc:
        log.debug("yfinance fetch failed: %s", exc)
        return {}
