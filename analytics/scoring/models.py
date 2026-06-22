"""
Contrarian Scoring Engine — data models.

Pydantic models representing each variable in the CS formula,
the assembled component set, and the final scored result.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── CS formula components ─────────────────────────────────────────────────────

class CSComponents(BaseModel):
    """
    Raw inputs to the Contrarian Score formula:

        CS = ((Pv * Ti) + Sum_Rs + (Em * Kw)) / (1 + Cc)

    All components are stored pre-normalisation so callers can
    inspect the raw signal values as well as the final score.
    """
    asset_id:   int
    asset_name: str
    ticker:     Optional[str] = None

    # Pv — Product Pipeline Velocity
    # Count of new Horizon pipeline filings linked to this asset's cluster
    # over the trailing 120 days, normalised to [0, 10].
    pv: float = Field(0.0, ge=0.0, description="Pipeline Velocity (0-10)")

    # Ti — Thematic Inflow Acceleration
    # 30-day fund-flow rate-of-change as a fraction.
    # +1.0 = flows doubled; -1.0 = flows halved; 0 = flat.
    ti: float = Field(0.0, description="Thematic Inflow Acceleration (-1 to +1+)")

    # Sum_Rs — Cumulative Cassandra Risk Score
    # Sum of Cassandra_Signals.Systemic_Risk_Score (1-10 each) for all
    # open signals linked to the asset's Exposure_Cluster.
    sum_rs: float = Field(0.0, ge=0.0, description="Cumulative Cassandra Risk Score")

    # Em — Ecosystem Multiplier
    # Count of confirmed S&P 500 B2B connections in Corporate_Ecosystem_Connections.
    em: float = Field(0.0, ge=0.0, description="Ecosystem Multiplier (connection count)")

    # Kw — Kingmaker Weight
    # 1.0 baseline; boosted to KW_ENDORSED when at least one
    # Endorsement_Flag=True connection exists for this asset.
    kw: float = Field(1.0, ge=1.0, description="Kingmaker Weight multiplier")

    # Cc — Consensus Crowding Factor
    # Fraction of mainstream institutional/retail ownership (0.0 → 1.0).
    cc: float = Field(0.0, ge=0.0, le=1.0, description="Consensus Crowding Factor")

    # Provenance
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    pv_window_days:   int = 120
    ti_window_days:   int = 30
    rs_signal_count:  int = 0      # how many Cassandra signals contributed to Sum_Rs
    em_connection_count: int = 0   # raw count before normalisation

    @field_validator("pv", "em", "sum_rs", mode="before")
    @classmethod
    def _floor_zero(cls, v: float) -> float:
        return max(0.0, float(v))


class ContrарianScoreResult(BaseModel):
    """Final CS score and derived analytical flags for a single asset."""

    asset_id:   int
    asset_name: str
    ticker:     Optional[str] = None

    # The headline score
    cs: float = Field(description="Contrarian Score CS = ((Pv*Ti)+Sum_Rs+(Em*Kw))/(1+Cc)")

    # Components snapshot
    components: CSComponents

    # Ranking (set by engine after batch computation)
    rank: Optional[int] = None

    # ── Analytical flags ──────────────────────────────────────────────────────
    is_asymmetry_play: bool = False
    """
    True when:
      - Pipeline Velocity is accelerating  (pv ≥ PV_ACCEL_THRESHOLD)
      - Crowding is low                    (cc ≤ CC_LOW_THRESHOLD)
    Signals a potential deep-value setup before mainstream discovery.
    """

    is_cassandra_risk: bool = False
    """True when cumulative risk score exceeds CASSANDRA_DANGER threshold."""

    is_kingmaker_endorsed: bool = False
    """True when at least one named-executive endorsement is active (kw > 1.0)."""

    cs_percentile: Optional[float] = None   # set after batch ranking
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class CSRankedBatch(BaseModel):
    """Output of a full-universe scoring run."""

    scored_at: datetime = Field(default_factory=datetime.utcnow)
    universe_size: int = 0
    results: list[ContrарianScoreResult] = Field(default_factory=list)
    elapsed_seconds: float = 0.0

    @property
    def asymmetry_plays(self) -> list[ContrарianScoreResult]:
        return [r for r in self.results if r.is_asymmetry_play]

    @property
    def top_n(self) -> list[ContrарianScoreResult]:
        return self.results[:10]
