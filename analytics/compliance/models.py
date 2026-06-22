"""
UK Crypto 2026/2027 Regulatory Timeline — data models.

Pydantic models for tracked instruments, compliance phases,
and the per-asset compliance health report.
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── Instrument registry ───────────────────────────────────────────────────────

InstrumentCategory = Literal[
    "LSE_ETP",         # Exchange-traded product listed on London Stock Exchange
    "Spot_Crypto",     # Native blockchain asset (BTC, ETH, SOL, XRP)
    "Stablecoin",      # Fiat-pegged digital asset
    "Asset_Manager",   # Fund manager / issuer entity
]

AuthorisationStatus = Literal[
    "Fully_Authorised",    # Part 4A FSMA authorisation obtained & valid
    "Registered_Only",     # FCA crypto-asset registration only (legacy)
    "Application_Pending", # Application submitted during gateway window
    "Not_Started",         # No application made yet
    "Withdrawn",           # Application withdrawn / refused
    "Grandfathered",       # Subject to transitional provisions
]


class TrackedInstrument(BaseModel):
    """A digital-asset instrument or issuer entity under FCA regulatory watch."""

    id:           str            # unique slug, e.g. "IBIT", "BTC"
    name:         str
    category:     InstrumentCategory
    ticker:       Optional[str] = None
    isin:         Optional[str] = None
    issuer:       Optional[str] = None   # e.g. "BlackRock", "CoinShares"
    exchange:     Optional[str] = None   # e.g. "LSE", "XLON"
    domicile:     str = "GB"

    # Current regulatory state
    auth_status:  AuthorisationStatus = "Not_Started"
    fca_ref:      Optional[str] = None
    application_date: Optional[date] = None
    authorisation_date: Optional[date] = None

    # Business flags
    has_retail_access: bool = True
    aum_gbp_mm:   Optional[float] = None   # AUM in millions GBP (None = unlisted)
    daily_vol_gbp_mm: Optional[float] = None


# ── Compliance phase model ────────────────────────────────────────────────────

CompliancePhase = Literal[
    "PRE_GATEWAY",        # Before Sep 30 2026 — preparation window
    "GATEWAY_OPEN",       # Sep 30 2026 – Feb 28 2027 — must apply
    "POST_GATEWAY",       # Mar 01 2027 – Oct 24 2027 — grace period
    "ENFORCEMENT_CLIFF",  # Oct 25 2027+ — hard enforcement
]

SurvivalFlag = Literal[
    "GREEN",    # Fully compliant, no material risk
    "AMBER",    # Compliant or pending but monitoring required
    "RED",      # Non-compliant or high risk of cliff-edge enforcement
    "CRITICAL", # Imminent cliff with no authorisation — likely market exit
]


class ComplianceHealthReport(BaseModel):
    """
    Per-instrument compliance health snapshot for a given reference date.
    """

    instrument_id:  str
    instrument_name: str
    category:       InstrumentCategory
    reference_date: date

    # Phase & countdown
    current_phase:         CompliancePhase
    days_to_gateway_open:  Optional[int] = None   # None once past
    days_to_gateway_close: Optional[int] = None
    days_to_enforcement:   Optional[int] = None

    # Authorisation state
    auth_status:    AuthorisationStatus
    fca_ref:        Optional[str] = None

    # Risk flags
    survival_flag:  SurvivalFlag
    risk_narrative: str = ""

    # Market impact
    can_operate_post_cliff:     bool = False
    requires_vop:               bool = False   # Variation of Permission needed
    retail_access_at_risk:      bool = False
    estimated_wind_down_risk:   bool = False

    # Recommendations
    next_action:         str = ""
    deadline:            Optional[date] = None
    deadline_label:      str = ""


class ComplianceMatrix(BaseModel):
    """Full compliance matrix across all tracked instruments."""

    generated_at:      date
    reference_date:    date
    current_phase:     CompliancePhase
    reports:           list[ComplianceHealthReport] = Field(default_factory=list)

    # Summary counts
    green_count:    int = 0
    amber_count:    int = 0
    red_count:      int = 0
    critical_count: int = 0

    @property
    def critical_instruments(self) -> list[ComplianceHealthReport]:
        return [r for r in self.reports if r.survival_flag == "CRITICAL"]

    @property
    def red_or_critical(self) -> list[ComplianceHealthReport]:
        return [r for r in self.reports if r.survival_flag in ("RED", "CRITICAL")]
