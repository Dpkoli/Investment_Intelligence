"""
Centralised configuration for the Contrarian Radar ETL pipeline.

All secrets are read from environment variables so no credentials
appear in source code.  The only value baked in is the project URL
and the publishable (anon) key, which are not sensitive.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Final


# ── Supabase coordinates ──────────────────────────────────────────────────────

SUPABASE_URL: Final[str] = "https://axvpzbdlfbuighvaussx.supabase.co"

# Publishable key (anon-equivalent).  Safe to ship in code / CI vars.
SUPABASE_PUBLISHABLE_KEY: Final[str] = (
    "sb_publishable_FkSLNsqTl97OF6c-e-LTmA_X7ibl4FI"
)

# Service-role key is required for direct table writes (bypasses RLS).
# Must be set in environment; pipeline will warn if absent and fall back
# to publishable key (which will fail on RLS-protected inserts).
SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


# ── HTTP / retry settings ─────────────────────────────────────────────────────

HTTP_TIMEOUT_SECONDS: int = 30
HTTP_MAX_RETRIES: int = 4
HTTP_BACKOFF_FACTOR: float = 2.0     # wait = factor * (2 ** attempt)
HTTP_STATUS_FORCE_RETRY: tuple[int, ...] = (429, 500, 502, 503, 504)

# SEC Fair Access Policy: 10 req/s; we stay conservatively at 8
EDGAR_RATE_LIMIT_RPS: float = 8.0
FCA_RATE_LIMIT_RPS: float = 4.0


# ── Known S&P 500 titans tracked by Kingmaker Protocol ───────────────────────

TITANS: dict[str, list[str]] = {
    "NVDA":  ["Nvidia", "NVIDIA", "Jensen Huang", "NVDA"],
    "MSFT":  ["Microsoft", "MSFT", "Satya Nadella", "Azure"],
    "AAPL":  ["Apple", "AAPL", "Tim Cook"],
    "GOOGL": ["Google", "Alphabet", "GOOGL", "Sundar Pichai", "DeepMind"],
    "META":  ["Meta", "META", "Mark Zuckerberg", "Facebook"],
    "AMZN":  ["Amazon", "AWS", "AMZN", "Andy Jassy"],
    "AMD":   ["AMD", "Advanced Micro Devices", "Lisa Su"],
    "INTC":  ["Intel", "INTC", "Pat Gelsinger"],
    "AVGO":  ["Broadcom", "AVGO", "Hock Tan"],
    "QCOM":  ["Qualcomm", "QCOM", "Cristiano Amon"],
    "TSM":   ["TSMC", "Taiwan Semiconductor", "TSM", "C.C. Wei"],
    "ORCL":  ["Oracle", "ORCL", "Larry Ellison"],
    "CRM":   ["Salesforce", "CRM", "Marc Benioff"],
    "ASML":  ["ASML", "Peter Wennink"],
    "AMAT":  ["Applied Materials", "AMAT"],
}

# Reverse lookup: any alias → canonical ticker
TITAN_ALIAS_MAP: dict[str, str] = {
    alias.lower(): ticker
    for ticker, aliases in TITANS.items()
    for alias in aliases
}


# ── Known KINGMAKER candidates (counterparties to watch) ─────────────────────

KINGMAKER_CANDIDATES: dict[str, list[str]] = {
    "MRVL":  ["Marvell", "Marvell Technology", "MRVL"],
    "SMCI":  ["Super Micro", "SuperMicro", "SMCI"],
    "CIEN":  ["Ciena", "CIEN"],
    "ANET":  ["Arista", "Arista Networks", "ANET"],
    "CDNS":  ["Cadence", "Cadence Design", "CDNS"],
    "SNPS":  ["Synopsys", "SNPS"],
    "ARM":   ["Arm", "ARM Holdings", "ARM"],
    "COHR":  ["Coherent", "II-VI", "COHR"],
    "LITE":  ["Lumentum", "LITE"],
    "FORM":  ["FormFactor", "FORM"],
    "ONTO":  ["Onto Innovation", "ONTO"],
    "ACLS":  ["Axcelis", "ACLS"],
    "WOLF":  ["Wolfspeed", "WOLF"],
    "IPGP":  ["IPG Photonics", "IPGP"],
    "VIAV":  ["Viavi Solutions", "VIAV"],
}

CANDIDATE_ALIAS_MAP: dict[str, str] = {
    alias.lower(): ticker
    for ticker, aliases in KINGMAKER_CANDIDATES.items()
    for alias in aliases
}


# ── Passive asset managers tracked by Horizon Scanner ────────────────────────

HORIZON_ISSUERS: list[str] = [
    "BlackRock", "iShares", "VanEck", "WisdomTree", "Invesco",
    "Global X", "ProShares", "Direxion", "Amplify", "ARK Invest",
    "Franklin Templeton", "DWS", "Xtrackers", "Fidelity",
    "State Street", "SPDR", "First Trust",
]

# CIK numbers for major ETF filers on EDGAR
HORIZON_EDGAR_CIKS: dict[str, str] = {
    "BlackRock": "0001100663",
    "VanEck":    "0000088053",
    "WisdomTree":"0001023934",
    "Invesco":   "0000049600",
    "ProShares": "0001174610",
    "Global X":  "0001479026",
    "ARK Invest":"0001579982",
}


# ── NLP version tag ───────────────────────────────────────────────────────────

NLP_MODEL_VERSION: str = "regex_v1.0"


# ── Logging ───────────────────────────────────────────────────────────────────

@dataclass
class LogConfig:
    level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    format: str = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    datefmt: str = "%Y-%m-%d %H:%M:%S"


def configure_logging() -> None:
    cfg = LogConfig()
    logging.basicConfig(
        level=getattr(logging, cfg.level.upper(), logging.INFO),
        format=cfg.format,
        datefmt=cfg.datefmt,
    )


configure_logging()
