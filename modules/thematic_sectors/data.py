"""
Thematic Sectors — comprehensive global sector and thematic ETF registry.
Covers all 11 GICS sectors + cross-sector thematics across US, Europe, and Asia.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class ThematicProduct:
    ticker: str
    name: str
    sector: str
    sub_theme: str
    region: str
    currency: str
    exchange: str
    expense_ratio: Optional[float] = None
    aum_bn: Optional[float] = None
    issuer: Optional[str] = None
    isin: Optional[str] = None
    yf_ticker: Optional[str] = None


THEMATIC_REGISTRY: list[ThematicProduct] = [
    # ── TECHNOLOGY ───────────────────────────────────────────────────────────
    ThematicProduct("XLK",   "SPDR Technology Select Sector",    "Technology", "Broad Tech",       "US",     "USD", "NYSE",   expense_ratio=0.09, aum_bn=68.2,  issuer="State Street"),
    ThematicProduct("VGT",   "Vanguard Information Technology",  "Technology", "Broad Tech",       "US",     "USD", "NYSE",   expense_ratio=0.10, aum_bn=84.1,  issuer="Vanguard"),
    ThematicProduct("IYW",   "iShares US Technology ETF",        "Technology", "Broad Tech",       "US",     "USD", "NYSE",   expense_ratio=0.39, aum_bn=18.2,  issuer="BlackRock"),
    ThematicProduct("SMH",   "VanEck Semiconductor ETF",         "Technology", "Semiconductors",   "US",     "USD", "NASDAQ", expense_ratio=0.35, aum_bn=24.8,  issuer="VanEck"),
    ThematicProduct("SOXX",  "iShares PHLX Semiconductor",       "Technology", "Semiconductors",   "US",     "USD", "NASDAQ", expense_ratio=0.35, aum_bn=12.4,  issuer="BlackRock"),
    ThematicProduct("SOXL",  "Direxion Daily Semis Bull 3×",     "Technology", "Semiconductors",   "US",     "USD", "NYSE",   expense_ratio=1.01, aum_bn=9.3,   issuer="Direxion"),
    ThematicProduct("SOXS",  "Direxion Daily Semis Bear 3×",     "Technology", "Semiconductors",   "US",     "USD", "NYSE",   expense_ratio=1.01,               issuer="Direxion"),
    ThematicProduct("HACK",  "ETFMG Prime Cyber Security",       "Technology", "Cybersecurity",    "US",     "USD", "NYSE",   expense_ratio=0.60, aum_bn=1.4,   issuer="ETFMG"),
    ThematicProduct("CIBR",  "First Trust NASDAQ Cybersecurity",  "Technology", "Cybersecurity",   "US",     "USD", "NASDAQ", expense_ratio=0.60, aum_bn=7.1,   issuer="First Trust"),
    ThematicProduct("BUG",   "Global X Cybersecurity ETF",       "Technology", "Cybersecurity",    "US",     "USD", "NASDAQ", expense_ratio=0.50, aum_bn=0.8,   issuer="Global X"),
    ThematicProduct("WCLD",  "WisdomTree Cloud Computing",       "Technology", "Cloud",            "US",     "USD", "NASDAQ", expense_ratio=0.45,               issuer="WisdomTree"),
    ThematicProduct("SKYY",  "First Trust Cloud Computing",      "Technology", "Cloud",            "US",     "USD", "NASDAQ", expense_ratio=0.60, aum_bn=4.1,   issuer="First Trust"),
    ThematicProduct("BOTZ",  "Global X Robotics & AI ETF",       "Technology", "Robotics / AI",    "US",     "USD", "NASDAQ", expense_ratio=0.68, aum_bn=2.4,   issuer="Global X"),
    ThematicProduct("AIQ",   "Global X Artificial Intelligence", "Technology", "Artificial Intel.", "US",    "USD", "NASDAQ", expense_ratio=0.68, aum_bn=1.1,   issuer="Global X"),
    ThematicProduct("IRBO",  "iShares Robotics & AI Multisector","Technology", "Robotics / AI",    "US",     "USD", "NASDAQ", expense_ratio=0.47,               issuer="BlackRock"),
    ThematicProduct("ROBO",  "ROBO Global Robotics & Automation","Technology", "Robotics",          "US",     "USD", "NYSE",   expense_ratio=0.95, aum_bn=1.5,   issuer="ROBO Global"),
    ThematicProduct("QTUM",  "Defiance Quantum ETF",             "Technology", "Quantum Computing", "US",    "USD", "NYSE",   expense_ratio=0.40,               issuer="Defiance"),
    ThematicProduct("FIVG",  "Defiance Next Gen Connectivity",   "Technology", "5G / Connectivity", "US",    "USD", "NYSE",   expense_ratio=0.30, aum_bn=0.6,   issuer="Defiance"),
    ThematicProduct("SNSR",  "Global X Internet of Things",      "Technology", "IoT",              "US",     "USD", "NASDAQ", expense_ratio=0.68,               issuer="Global X"),
    ThematicProduct("DTCR",  "WisdomTree Digital Economy",       "Technology", "Digital Economy",  "UK",     "USD", "LSE",    expense_ratio=0.45,               issuer="WisdomTree"),
    ThematicProduct("IUIT.L","iShares S&P 500 Info Technology",  "Technology", "Broad Tech (US)",  "UK",     "USD", "LSE",    expense_ratio=0.15,               issuer="BlackRock"),
    ThematicProduct("ESPO",  "VanEck Video Gaming & eSports",    "Technology", "Gaming / eSports", "US",     "USD", "NASDAQ", expense_ratio=0.55, aum_bn=0.9,   issuer="VanEck"),

    # ── ENERGY ───────────────────────────────────────────────────────────────
    ThematicProduct("XLE",   "SPDR Energy Select Sector",        "Energy", "Broad Energy",       "US",     "USD", "NYSE",   expense_ratio=0.09, aum_bn=37.2,  issuer="State Street"),
    ThematicProduct("VDE",   "Vanguard Energy ETF",              "Energy", "Broad Energy",       "US",     "USD", "NYSE",   expense_ratio=0.10, aum_bn=8.4,   issuer="Vanguard"),
    ThematicProduct("IYE",   "iShares US Energy ETF",            "Energy", "Broad Energy",       "US",     "USD", "NYSE",   expense_ratio=0.39, aum_bn=1.4,   issuer="BlackRock"),
    ThematicProduct("XOP",   "SPDR S&P Oil & Gas E&P",           "Energy", "E&P",               "US",     "USD", "NYSE",   expense_ratio=0.35, aum_bn=3.1,   issuer="State Street"),
    ThematicProduct("OIH",   "VanEck Oil Services ETF",          "Energy", "Oilfield Services",  "US",     "USD", "NASDAQ", expense_ratio=0.35, aum_bn=2.8,   issuer="VanEck"),
    ThematicProduct("AMLP",  "Alerian MLP ETF",                  "Energy", "MLP / Midstream",    "US",     "USD", "NYSE",   expense_ratio=0.87, aum_bn=9.2,   issuer="Alerian"),
    ThematicProduct("ICLN",  "iShares Global Clean Energy",      "Energy", "Clean Energy",       "Global", "USD", "NASDAQ", expense_ratio=0.40, aum_bn=3.2,   issuer="BlackRock"),
    ThematicProduct("QCLN",  "First Trust Clean Edge Green",     "Energy", "Clean Energy",       "US",     "USD", "NASDAQ", expense_ratio=0.58, aum_bn=0.9,   issuer="First Trust"),
    ThematicProduct("TAN",   "Invesco Solar ETF",                "Energy", "Solar",              "US",     "USD", "NYSE",   expense_ratio=0.69, aum_bn=1.3,   issuer="Invesco"),
    ThematicProduct("FAN",   "First Trust Global Wind Energy",   "Energy", "Wind",               "Global", "USD", "NASDAQ", expense_ratio=0.60, aum_bn=0.2,   issuer="First Trust"),
    ThematicProduct("URNM",  "Sprott Uranium Miners ETF",        "Energy", "Uranium",            "US",     "USD", "NYSE",   expense_ratio=0.83, aum_bn=1.4,   issuer="Sprott"),
    ThematicProduct("URA",   "Global X Uranium ETF",             "Energy", "Uranium",            "US",     "USD", "NYSE",   expense_ratio=0.69, aum_bn=3.8,   issuer="Global X"),
    ThematicProduct("NUKZ",  "Range Nuclear Renaissance ETF",    "Energy", "Nuclear",            "US",     "USD", "NYSE",   expense_ratio=0.85,               issuer="Range"),
    ThematicProduct("ENUC.L","WisdomTree Nuclear Energy ETF",    "Energy", "Nuclear",            "UK",     "USD", "LSE",    expense_ratio=0.45,               issuer="WisdomTree"),
    ThematicProduct("GRID",  "First Trust NASDAQ Clean Edge Grid","Energy","Power Grid / Storage","US",    "USD", "NASDAQ", expense_ratio=0.58, aum_bn=0.8,   issuer="First Trust"),
    ThematicProduct("DRLL",  "Strive US Energy ETF",             "Energy", "Broad Energy",       "US",     "USD", "NYSE",   expense_ratio=0.41,               issuer="Strive"),

    # ── HEALTHCARE ───────────────────────────────────────────────────────────
    ThematicProduct("XLV",   "SPDR Health Care Select Sector",   "Healthcare", "Broad Healthcare", "US",   "USD", "NYSE",   expense_ratio=0.09, aum_bn=42.1,  issuer="State Street"),
    ThematicProduct("VHT",   "Vanguard Health Care ETF",         "Healthcare", "Broad Healthcare", "US",   "USD", "NYSE",   expense_ratio=0.10, aum_bn=16.2,  issuer="Vanguard"),
    ThematicProduct("IYH",   "iShares US Healthcare ETF",        "Healthcare", "Broad Healthcare", "US",   "USD", "NYSE",   expense_ratio=0.39,               issuer="BlackRock"),
    ThematicProduct("IBB",   "iShares Biotechnology ETF",        "Healthcare", "Biotech",          "US",   "USD", "NASDAQ", expense_ratio=0.44, aum_bn=10.8,  issuer="BlackRock"),
    ThematicProduct("XBI",   "SPDR S&P Biotech ETF",             "Healthcare", "Biotech",          "US",   "USD", "NYSE",   expense_ratio=0.35, aum_bn=6.4,   issuer="State Street"),
    ThematicProduct("ARKG",  "ARK Genomic Revolution ETF",       "Healthcare", "Genomics",         "US",   "USD", "NYSE",   expense_ratio=0.75, aum_bn=2.8,   issuer="ARK"),
    ThematicProduct("IDNA",  "iShares Genomics Immunology Health","Healthcare","Genomics / Immuno","US",   "USD", "NASDAQ", expense_ratio=0.47,               issuer="BlackRock"),
    ThematicProduct("IHI",   "iShares US Medical Devices",       "Healthcare", "Medical Devices",  "US",   "USD", "NYSE",   expense_ratio=0.40, aum_bn=5.8,   issuer="BlackRock"),
    ThematicProduct("PJP",   "Invesco Pharmaceuticals ETF",      "Healthcare", "Pharma",           "US",   "USD", "NYSE",   expense_ratio=0.57, aum_bn=0.7,   issuer="Invesco"),
    ThematicProduct("IHF",   "iShares US Healthcare Providers",  "Healthcare", "Managed Care",     "US",   "USD", "NYSE",   expense_ratio=0.40, aum_bn=1.4,   issuer="BlackRock"),
    ThematicProduct("GENOME.L","L&G MSCI Global Genomics ETF",  "Healthcare", "Genomics",         "UK",   "USD", "LSE",    expense_ratio=0.45,               issuer="Legal & General"),
    ThematicProduct("KURE",  "KraneShares MSCI China Health",   "Healthcare", "China Healthcare",  "Asia", "USD", "NYSE",   expense_ratio=0.79,               issuer="KraneShares"),
    ThematicProduct("EDOC",  "Global X Telemedicine & Digital",  "Healthcare", "Digital Health",   "US",   "USD", "NASDAQ", expense_ratio=0.68,               issuer="Global X"),

    # ── FINANCIALS ───────────────────────────────────────────────────────────
    ThematicProduct("XLF",   "SPDR Financials Select Sector",    "Financials", "Broad Financials", "US",   "USD", "NYSE",   expense_ratio=0.09, aum_bn=46.2,  issuer="State Street"),
    ThematicProduct("VFH",   "Vanguard Financials ETF",          "Financials", "Broad Financials", "US",   "USD", "NYSE",   expense_ratio=0.10, aum_bn=11.4,  issuer="Vanguard"),
    ThematicProduct("KBE",   "SPDR S&P Bank ETF",                "Financials", "Banking",          "US",   "USD", "NYSE",   expense_ratio=0.35, aum_bn=2.4,   issuer="State Street"),
    ThematicProduct("KRE",   "SPDR S&P Regional Banking",        "Financials", "Regional Banks",   "US",   "USD", "NYSE",   expense_ratio=0.35, aum_bn=4.8,   issuer="State Street"),
    ThematicProduct("KBWB",  "Invesco KBW Bank ETF",             "Financials", "Banking",          "US",   "USD", "NASDAQ", expense_ratio=0.35,               issuer="Invesco"),
    ThematicProduct("IAI",   "iShares US Broker-Dealers & Sec.", "Financials", "Capital Markets",  "US",   "USD", "NYSE",   expense_ratio=0.40,               issuer="BlackRock"),
    ThematicProduct("FINX",  "Global X FinTech ETF",             "Financials", "FinTech",          "Global","USD","NASDAQ", expense_ratio=0.68, aum_bn=0.5,   issuer="Global X"),
    ThematicProduct("IPAY",  "ETFMG Prime Mobile Payments",      "Financials", "Payments",         "US",   "USD", "NYSE",   expense_ratio=0.75,               issuer="ETFMG"),
    ThematicProduct("ARKF",  "ARK Fintech Innovation ETF",       "Financials", "FinTech",          "US",   "USD", "NYSE",   expense_ratio=0.75, aum_bn=1.2,   issuer="ARK"),
    ThematicProduct("ISPY.L","iShares S&P 500 Financials Sector","Financials","Broad Financials", "UK",   "USD", "LSE",    expense_ratio=0.15,               issuer="BlackRock"),

    # ── CONSUMER STAPLES ─────────────────────────────────────────────────────
    ThematicProduct("XLP",   "SPDR Consumer Staples Select",     "Consumer Staples","Broad Staples","US", "USD", "NYSE",   expense_ratio=0.09, aum_bn=18.2,  issuer="State Street"),
    ThematicProduct("VDC",   "Vanguard Consumer Staples ETF",    "Consumer Staples","Broad Staples","US", "USD", "NYSE",   expense_ratio=0.10, aum_bn=7.8,   issuer="Vanguard"),
    ThematicProduct("IYK",   "iShares US Consumer Staples",      "Consumer Staples","Broad Staples","US", "USD", "NYSE",   expense_ratio=0.39,               issuer="BlackRock"),

    # ── CONSUMER DISCRETIONARY ───────────────────────────────────────────────
    ThematicProduct("XLY",   "SPDR Consumer Discret. Select",    "Consumer Discret.","Broad Discret.","US","USD","NYSE",  expense_ratio=0.09, aum_bn=22.4,  issuer="State Street"),
    ThematicProduct("VCR",   "Vanguard Consumer Discret. ETF",   "Consumer Discret.","Broad Discret.","US","USD","NYSE",  expense_ratio=0.10, aum_bn=6.8,   issuer="Vanguard"),
    ThematicProduct("ONLN",  "ProShares Online Retail ETF",      "Consumer Discret.","E-Commerce",  "US", "USD", "NYSE",   expense_ratio=0.58,               issuer="ProShares"),
    ThematicProduct("IBUY",  "Amplify Online Retail ETF",        "Consumer Discret.","E-Commerce",  "US", "USD", "NASDAQ", expense_ratio=0.65,               issuer="Amplify"),
    ThematicProduct("DRIV",  "Global X Autonomous & EV ETF",     "Consumer Discret.","Autonomous EV","US","USD","NASDAQ", expense_ratio=0.68, aum_bn=0.5,   issuer="Global X"),

    # ── INDUSTRIALS ──────────────────────────────────────────────────────────
    ThematicProduct("XLI",   "SPDR Industrials Select Sector",   "Industrials","Broad Industrial","US",   "USD", "NYSE",   expense_ratio=0.09, aum_bn=24.1,  issuer="State Street"),
    ThematicProduct("VIS",   "Vanguard Industrials ETF",         "Industrials","Broad Industrial","US",   "USD", "NYSE",   expense_ratio=0.10, aum_bn=5.4,   issuer="Vanguard"),
    ThematicProduct("ITA",   "iShares US Aerospace & Defense",   "Industrials","Aerospace/Defense","US", "USD", "NYSE",   expense_ratio=0.40, aum_bn=6.8,   issuer="BlackRock"),
    ThematicProduct("PPA",   "Invesco Aerospace & Defense ETF",  "Industrials","Aerospace/Defense","US", "USD", "NYSE",   expense_ratio=0.57, aum_bn=4.2,   issuer="Invesco"),
    ThematicProduct("XAR",   "SPDR S&P Aerospace & Defense",     "Industrials","Aerospace/Defense","US", "USD", "NYSE",   expense_ratio=0.35, aum_bn=1.8,   issuer="State Street"),
    ThematicProduct("DFEN",  "Direxion Daily Aerospace Bull 3×", "Industrials","Aerospace 3×",    "US",  "USD", "NYSE",   expense_ratio=1.01,               issuer="Direxion"),
    ThematicProduct("EUAD.L","VanEck Defence UCITS ETF",         "Industrials","European Defence", "UK",  "EUR", "LSE",    expense_ratio=0.55,               issuer="VanEck"),
    ThematicProduct("NATP.L","WisdomTree Aerospace & Defence",   "Industrials","Aerospace/Defence","UK",  "USD", "LSE",    expense_ratio=0.45,               issuer="WisdomTree"),
    ThematicProduct("JETS",  "US Global Jets ETF",               "Industrials","Airlines",         "US",  "USD", "NYSE",   expense_ratio=0.60, aum_bn=1.2,   issuer="US Global"),
    ThematicProduct("ROBT",  "First Trust Nasdaq Artifical Intel Robotics","Industrials","Robotics/AI","US","USD","NASDAQ",expense_ratio=0.65,               issuer="First Trust"),

    # ── MATERIALS ────────────────────────────────────────────────────────────
    ThematicProduct("XLB",   "SPDR Materials Select Sector",     "Materials","Broad Materials",   "US",   "USD", "NYSE",   expense_ratio=0.09, aum_bn=7.2,   issuer="State Street"),
    ThematicProduct("VAW",   "Vanguard Materials ETF",           "Materials","Broad Materials",   "US",   "USD", "NYSE",   expense_ratio=0.10, aum_bn=1.8,   issuer="Vanguard"),
    ThematicProduct("PICK",  "iShares MSCI Global Metals & Mining","Materials","Metals & Mining","Global","USD","NYSE",   expense_ratio=0.39, aum_bn=1.4,   issuer="BlackRock"),
    ThematicProduct("COPX",  "Global X Copper Miners ETF",       "Materials","Copper",            "Global","USD","NYSE",  expense_ratio=0.65, aum_bn=2.8,   issuer="Global X"),
    ThematicProduct("LIT",   "Global X Lithium & Battery Tech",  "Materials","Lithium / Battery", "Global","USD","NYSE",  expense_ratio=0.75, aum_bn=1.4,   issuer="Global X"),
    ThematicProduct("REMX",  "VanEck Rare Earth/Strategic Metals","Materials","Rare Earth Metals","Global","USD","NYSE",  expense_ratio=0.54, aum_bn=0.6,   issuer="VanEck"),
    ThematicProduct("WOOD",  "iShares Global Timber & Forestry", "Materials","Timber",            "Global","USD","NASDAQ",expense_ratio=0.41, aum_bn=0.3,   issuer="BlackRock"),
    ThematicProduct("GDX",   "VanEck Gold Miners ETF",           "Materials","Gold Mining",       "Global","USD","NYSE",  expense_ratio=0.51, aum_bn=13.2,  issuer="VanEck"),
    ThematicProduct("GDXJ",  "VanEck Junior Gold Miners",        "Materials","Junior Gold Miners", "Global","USD","NYSE",  expense_ratio=0.52, aum_bn=4.8,   issuer="VanEck"),
    ThematicProduct("SIL",   "Global X Silver Miners ETF",       "Materials","Silver Mining",      "Global","USD","NYSE",  expense_ratio=0.65, aum_bn=0.9,   issuer="Global X"),
    ThematicProduct("NNRG.L","WisdomTree Battery Solutions ETF",  "Materials","Battery Materials",  "UK",   "USD", "LSE",   expense_ratio=0.40,               issuer="WisdomTree"),

    # ── REAL ESTATE ──────────────────────────────────────────────────────────
    ThematicProduct("VNQ",   "Vanguard Real Estate ETF",         "Real Estate","Broad REIT",       "US",   "USD", "NYSE",   expense_ratio=0.12, aum_bn=32.4,  issuer="Vanguard"),
    ThematicProduct("XLRE",  "SPDR Real Estate Select Sector",   "Real Estate","Broad REIT",       "US",   "USD", "NYSE",   expense_ratio=0.09, aum_bn=6.4,   issuer="State Street"),
    ThematicProduct("IYR",   "iShares US Real Estate ETF",       "Real Estate","Broad REIT",       "US",   "USD", "NYSE",   expense_ratio=0.39, aum_bn=5.2,   issuer="BlackRock"),
    ThematicProduct("INDS",  "Pacer Benchmark Industrial REIT",  "Real Estate","Industrial REIT",  "US",   "USD", "NYSE",   expense_ratio=0.55,               issuer="Pacer"),
    ThematicProduct("REZ",   "iShares Residential & Multisector","Real Estate","Residential REIT", "US",   "USD", "NYSE",   expense_ratio=0.48,               issuer="BlackRock"),
    ThematicProduct("SRET",  "Global X SuperDividend REIT ETF",  "Real Estate","High-Yield REIT",  "Global","USD","NASDAQ", expense_ratio=0.58,               issuer="Global X"),
    ThematicProduct("VNQI",  "Vanguard Global ex-US Real Estate","Real Estate","Intl REIT",        "Global","USD","NASDAQ", expense_ratio=0.12, aum_bn=4.8,   issuer="Vanguard"),
    ThematicProduct("REM",   "iShares Mortgage Real Estate",     "Real Estate","Mortgage REIT",    "US",   "USD", "NYSE",   expense_ratio=0.48,               issuer="BlackRock"),

    # ── UTILITIES ────────────────────────────────────────────────────────────
    ThematicProduct("XLU",   "SPDR Utilities Select Sector",     "Utilities","Broad Utilities",   "US",   "USD", "NYSE",   expense_ratio=0.09, aum_bn=16.2,  issuer="State Street"),
    ThematicProduct("VPU",   "Vanguard Utilities ETF",           "Utilities","Broad Utilities",   "US",   "USD", "NYSE",   expense_ratio=0.10, aum_bn=6.4,   issuer="Vanguard"),
    ThematicProduct("IDU",   "iShares US Utilities ETF",         "Utilities","Broad Utilities",   "US",   "USD", "NYSE",   expense_ratio=0.39,               issuer="BlackRock"),
    ThematicProduct("FUTY",  "Fidelity MSCI Utilities ETF",      "Utilities","Broad Utilities",   "US",   "USD", "NYSE",   expense_ratio=0.08,               issuer="Fidelity"),

    # ── COMMUNICATION SERVICES ───────────────────────────────────────────────
    ThematicProduct("XLC",   "SPDR Communication Services",      "Communication","Broad Comms",    "US",   "USD", "NYSE",   expense_ratio=0.09, aum_bn=18.8,  issuer="State Street"),
    ThematicProduct("VOX",   "Vanguard Communication Services",  "Communication","Broad Comms",    "US",   "USD", "NYSE",   expense_ratio=0.10, aum_bn=3.8,   issuer="Vanguard"),

    # ── INFRASTRUCTURE ───────────────────────────────────────────────────────
    ThematicProduct("IGF",   "iShares Global Infrastructure",    "Infrastructure","Global Infra",   "Global","USD","NYSE",  expense_ratio=0.40, aum_bn=5.8,   issuer="BlackRock"),
    ThematicProduct("IFRA",  "iShares US Infrastructure ETF",    "Infrastructure","US Infra",       "US",   "USD", "NYSE",   expense_ratio=0.30, aum_bn=2.4,   issuer="BlackRock"),
    ThematicProduct("PAVE",  "Global X US Infrastructure Dev.",  "Infrastructure","US Infra Dev",   "US",   "USD", "NASDAQ", expense_ratio=0.47, aum_bn=8.2,   issuer="Global X"),
    ThematicProduct("GII",   "SPDR S&P Global Infrastructure",   "Infrastructure","Global Infra",   "Global","USD","NYSE",  expense_ratio=0.40, aum_bn=0.6,   issuer="State Street"),
    ThematicProduct("PHO",   "Invesco Water Resources ETF",      "Infrastructure","Water",          "US",   "USD", "NASDAQ", expense_ratio=0.60, aum_bn=1.8,   issuer="Invesco"),
    ThematicProduct("FIW",   "First Trust Water ETF",            "Infrastructure","Water",          "US",   "USD", "NASDAQ", expense_ratio=0.53, aum_bn=2.1,   issuer="First Trust"),
    ThematicProduct("CGW",   "Invesco Global Water ETF",         "Infrastructure","Water",          "Global","USD","NYSE",   expense_ratio=0.57, aum_bn=0.5,   issuer="Invesco"),
    ThematicProduct("INCO.L","iShares Global Infrastructure",    "Infrastructure","Global Infra",   "UK",   "USD", "LSE",    expense_ratio=0.65,               issuer="BlackRock"),

    # ── WATER ────────────────────────────────────────────────────────────────

    # ── DISRUPTIVE / CROSS-SECTOR THEMATICS ─────────────────────────────────
    ThematicProduct("ARKK",  "ARK Innovation ETF",               "Thematic","Disruptive Tech",     "US",   "USD", "NYSE",   expense_ratio=0.75, aum_bn=7.2,   issuer="ARK"),
    ThematicProduct("ARKW",  "ARK Next Generation Internet",     "Thematic","Next Gen Internet",   "US",   "USD", "NYSE",   expense_ratio=0.75, aum_bn=1.4,   issuer="ARK"),
    ThematicProduct("ARKQ",  "ARK Autonomous Technology",        "Thematic","Autonomous Tech",     "US",   "USD", "NYSE",   expense_ratio=0.75, aum_bn=0.8,   issuer="ARK"),
    ThematicProduct("ARKI",  "ARK Israel Innovative Technology", "Thematic","Israel Tech",         "US",   "USD", "NYSE",   expense_ratio=0.55,               issuer="ARK"),
    ThematicProduct("CLMA",  "iShares MSCI Global Climate",      "Thematic","Climate",             "Global","USD","NYSE",  expense_ratio=0.35,               issuer="BlackRock"),
    ThematicProduct("KRBN",  "KraneShares Global Carbon Strat.", "Thematic","Carbon Credits",      "Global","USD","NYSE",  expense_ratio=0.78,               issuer="KraneShares"),
    ThematicProduct("HNDL",  "Nasdaq 7 Handl Index ETF",         "Thematic","Income Strategy",     "US",   "USD", "NASDAQ", expense_ratio=0.97,               issuer="Strategy Shares"),
    ThematicProduct("METV",  "Roundhill Ball Metaverse ETF",     "Thematic","Metaverse",           "US",   "USD", "NYSE",   expense_ratio=0.59,               issuer="Roundhill"),
    ThematicProduct("NERD",  "Roundhill BITKRAFT Esports",       "Thematic","Esports",             "US",   "USD", "NYSE",   expense_ratio=0.50,               issuer="Roundhill"),
    ThematicProduct("HERO",  "Global X Video Games & Esports",   "Thematic","Gaming",              "Global","USD","NASDAQ", expense_ratio=0.50,               issuer="Global X"),
    ThematicProduct("BIOG.L","L&G Global Robotics & Automation", "Thematic","Robotics",            "UK",   "USD", "LSE",    expense_ratio=0.49,               issuer="Legal & General"),
    ThematicProduct("AIAG.L","HANetf Sprott Uranium Miners UCITS","Thematic","Uranium",            "UK",   "USD", "LSE",    expense_ratio=0.85,               issuer="HANetf"),
    ThematicProduct("SPAK",  "Defiance NextGen SPAC Derived ETF","Thematic","SPACs",              "US",   "USD", "NASDAQ", expense_ratio=0.45,               issuer="Defiance"),
    ThematicProduct("BKCH",  "Global X Blockchain ETF",          "Thematic","Blockchain",          "US",   "USD", "NASDAQ", expense_ratio=0.50, aum_bn=0.2,   issuer="Global X"),
    ThematicProduct("LEGR",  "First Trust Indxx Innovative Trans.","Thematic","Logistics Tech",    "US",   "USD", "NASDAQ", expense_ratio=0.65,               issuer="First Trust"),
    ThematicProduct("AGRI",  "iShares MSCI Global Agriculture",  "Thematic","Agriculture",         "Global","USD","NYSE",   expense_ratio=0.39,               issuer="BlackRock"),
    ThematicProduct("MOO",   "VanEck Agribusiness ETF",          "Thematic","Agribusiness",        "Global","USD","NYSE",   expense_ratio=0.52, aum_bn=0.9,   issuer="VanEck"),
    ThematicProduct("WEAT",  "Teucrium Wheat Fund",              "Thematic","Commodities",         "US",   "USD", "NYSE",   expense_ratio=1.45,               issuer="Teucrium"),
]

ALL_SECTORS = sorted(set(p.sector for p in THEMATIC_REGISTRY))
ALL_SUB_THEMES = sorted(set(p.sub_theme for p in THEMATIC_REGISTRY))


def fetch_prices(tickers: list[str]) -> dict[str, dict]:
    """yfinance price fetch with graceful fallback."""
    try:
        import yfinance as yf
        data: dict[str, dict] = {}
        batch = yf.download(tickers, period="2d", auto_adjust=True,
                            progress=False, threads=True)
        closes = batch.get("Close", batch)
        if closes is None or closes.empty:
            return data
        last  = closes.iloc[-1]
        prev  = closes.iloc[-2] if len(closes) >= 2 else closes.iloc[-1]
        import math
        for t in tickers:
            try:
                p  = float(last[t]) if t in last.index else None
                p0 = float(prev[t]) if t in prev.index else None
                # Guard against NaN values that yfinance returns for illiquid tickers
                if p is not None and math.isnan(p):
                    p = None
                if p0 is not None and math.isnan(p0):
                    p0 = None
                pct = round((p - p0) / p0 * 100, 2) if (p and p0 and p0 != 0) else None
                data[t] = {"price": round(p, 4) if p else None, "chg_pct": pct}
            except Exception:
                pass
        return data
    except Exception as exc:
        log.debug("yfinance fetch failed: %s", exc)
        return {}
