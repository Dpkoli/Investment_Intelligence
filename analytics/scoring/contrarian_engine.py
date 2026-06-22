"""
Contrarian Scoring (CS) Algorithmic Engine

Implements the asymmetric scoring formula:

    CS = ((Pv * Ti) + Sum_Rs + (Em * Kw)) / (1 + Cc)

Where:
  Pv      Product Pipeline Velocity          [0, 10]
  Ti      Thematic Inflow Acceleration       (-∞, +∞) practically (-2, +5)
  Sum_Rs  Cumulative Cassandra Risk Score    [0, 200+]
  Em      Ecosystem Multiplier               [0, 10]
  Kw      Kingmaker Weight                   {1.0, 2.5}
  Cc      Consensus Crowding Factor          [0.0, 1.0]

Interpretation guide
────────────────────
  CS > 20   : Strong contrarian signal — high pipeline + ecosystem activity,
              low crowding, potential kingmaker catalyst.
  10–20     : Moderate signal — monitor for acceleration.
  5–10      : Weak signal — within normal range.
  < 5       : Noise floor / mainstream-crowded or pipeline-inactive asset.

Asymmetry flag is raised independently of the raw CS score:
  is_asymmetry_play = (Pv ≥ PV_ACCEL_THRESHOLD) AND (Cc ≤ CC_LOW_THRESHOLD)

This detects assets where institutional filings are ramping but mainstream
ownership remains thin — the classic "early institutional accumulation" setup.
"""

from __future__ import annotations

import functools
import logging
import time
from typing import Optional

from etl.client import SupabaseClient
from analytics.scoring.models import (
    CSComponents,
    CSRankedBatch,
    ContrарianScoreResult,
)
from analytics.scoring.signal_aggregator import SignalAggregator

log = logging.getLogger(__name__)

# ── Module-level TTL cache (safe in both Streamlit and plain Python) ──────────
# Streamlit's @st.cache_data is unavailable outside the Streamlit runtime.
# This lightweight in-process TTL cache prevents redundant Supabase round-trips
# in the Vercel serverless context where multiple requests share a warm lambda.

_CACHE_TTL_SECONDS = 300   # 5 minutes — matches Streamlit cache TTL

def _ttl_cache(ttl: int = _CACHE_TTL_SECONDS):
    """Decorator: caches return value for `ttl` seconds using a simple dict."""
    def decorator(fn):
        _store: dict = {}
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            entry = _store.get(key)
            if entry and (time.monotonic() - entry["ts"]) < ttl:
                return entry["val"]
            result = fn(*args, **kwargs)
            _store[key] = {"val": result, "ts": time.monotonic()}
            return result
        wrapper.cache_clear = lambda: _store.clear()
        return wrapper
    return decorator

# ── Tunable thresholds ────────────────────────────────────────────────────────

# Pv ≥ this value triggers the asymmetry flag (moderate pipeline acceleration)
PV_ACCEL_THRESHOLD: float = 4.0

# Cc ≤ this triggers the asymmetry flag (less than 30% mainstream crowding)
CC_LOW_THRESHOLD: float = 0.30

# Sum_Rs above this raises a Cassandra danger flag
CASSANDRA_DANGER_THRESHOLD: float = 25.0

# CS floor below which the result is considered noise and can be suppressed
CS_NOISE_FLOOR: float = 0.5


class ContrаrianScoringEngine:
    """
    Calculates and ranks Contrarian Scores for all tracked assets.

    Usage::

        engine = ContrаrianScoringEngine()

        # Score a single asset
        result = engine.score_asset(asset_id=42)

        # Score and rank the full KINGMAKER universe
        batch  = engine.score_all()
        for r in batch.asymmetry_plays:
            print(r.ticker, r.cs, r.rank)

        # Persist scores back to Asset_Alpha_Scores
        engine.persist_batch(batch)
    """

    def __init__(
        self,
        client: Optional[SupabaseClient] = None,
        pv_accel_threshold: float = PV_ACCEL_THRESHOLD,
        cc_low_threshold: float = CC_LOW_THRESHOLD,
        cassandra_danger_threshold: float = CASSANDRA_DANGER_THRESHOLD,
    ) -> None:
        self._client     = client or SupabaseClient()
        self._aggregator = SignalAggregator(client=self._client)
        self.pv_accel    = pv_accel_threshold
        self.cc_low      = cc_low_threshold
        self.cassandra_danger = cassandra_danger_threshold

    # ── Public API ────────────────────────────────────────────────────────────

    @_ttl_cache(ttl=_CACHE_TTL_SECONDS)
    def score_asset(self, asset_id: int) -> Optional[ContrарianScoreResult]:
        """
        Compute CS for a single asset.

        Result is cached for _CACHE_TTL_SECONDS to prevent redundant
        Supabase round-trips on warm Vercel lambda invocations.
        Returns None if the asset cannot be found in the database.
        """
        components = self._aggregator.fetch(asset_id)
        if not components:
            return None
        return self._compute(components)

    def score_components(self, components: CSComponents) -> ContrарianScoreResult:
        """
        Compute CS from a pre-built CSComponents object.

        Useful for unit tests and what-if simulations without hitting the DB.
        """
        return self._compute(components)

    @_ttl_cache(ttl=_CACHE_TTL_SECONDS)
    def score_all(self, suppress_noise: bool = True) -> CSRankedBatch:
        """
        Score and rank the full tracked universe.

        Result is cached for _CACHE_TTL_SECONDS.  On Vercel this prevents the
        multi-table Supabase join from running on every request, keeping
        response times well inside the 60-second Pro function timeout.

        Args:
            suppress_noise: If True, assets with CS < CS_NOISE_FLOOR are
                            excluded from the batch (but still counted in
                            universe_size).

        Returns a CSRankedBatch sorted descending by CS.
        """
        t0 = time.monotonic()
        all_components = self._aggregator.fetch_all()
        universe_size  = len(all_components)

        results: list[ContrарianScoreResult] = []
        for comp in all_components:
            result = self._compute(comp)
            if suppress_noise and result.cs < CS_NOISE_FLOOR:
                continue
            results.append(result)

        # Sort descending by CS
        results.sort(key=lambda r: r.cs, reverse=True)

        # Assign ranks + percentiles
        n = len(results)
        for i, r in enumerate(results, start=1):
            r.rank = i
            r.cs_percentile = round((n - i) / max(n - 1, 1) * 100, 1)

        elapsed = round(time.monotonic() - t0, 3)
        log.info(
            "[CS ENGINE] score_all complete: universe=%d scored=%d asymmetry=%d in %.1fs",
            universe_size,
            n,
            sum(1 for r in results if r.is_asymmetry_play),
            elapsed,
        )
        return CSRankedBatch(
            universe_size=universe_size,
            results=results,
            elapsed_seconds=elapsed,
        )

    def flag_asymmetry_plays(
        self,
        batch: Optional[CSRankedBatch] = None,
    ) -> list[ContrарianScoreResult]:
        """
        Return assets flagged as deep asymmetry plays from a batch
        (or run score_all if no batch supplied), sorted by CS descending.
        """
        if batch is None:
            batch = self.score_all()
        return batch.asymmetry_plays

    def persist_batch(self, batch: CSRankedBatch) -> tuple[int, int]:
        """
        Write CS results back into Asset_Alpha_Scores via the
        fn_compute_kingmaker_alpha RPC pattern.

        Uses direct table upsert so scores are available immediately
        without re-running the SQL scoring function.

        Returns (inserted, rejected) counts.
        """
        inserted = rejected = 0
        for result in batch.results:
            row = {
                "Asset_ID":              result.asset_id,
                "KA_Score":              round(result.cs, 4),
                "CS_Rank":               result.rank,
                "CS_Percentile":         result.cs_percentile,
                "Is_Asymmetry_Play":     result.is_asymmetry_play,
                "Is_Cassandra_Risk":     result.is_cassandra_risk,
                "Is_Kingmaker_Endorsed": result.is_kingmaker_endorsed,
                "Pv":                    result.components.pv,
                "Ti":                    result.components.ti,
                "Sum_Rs":                result.components.sum_rs,
                "Em":                    result.components.em,
                "Kw":                    result.components.kw,
                "Cc":                    result.components.cc,
                "Scored_At":             result.computed_at.isoformat(),
            }
            status, _ = self._client.table_insert(
                "Asset_Alpha_Scores",
                row,
                on_conflict="Asset_ID",
            )
            if status in (200, 201):
                inserted += 1
            else:
                rejected += 1

        log.info("[CS ENGINE] persist_batch: inserted=%d rejected=%d", inserted, rejected)
        return inserted, rejected

    # ── Core formula ──────────────────────────────────────────────────────────

    def _compute(self, c: CSComponents) -> ContrарianScoreResult:
        """
        Apply the CS formula and derive analytical flags.

            CS = ((Pv * Ti) + Sum_Rs + (Em * Kw)) / (1 + Cc)

        Arithmetic notes
        ────────────────
        • (Pv * Ti): momentum term.  Positive when pipeline is growing AND
          flows are accelerating.  Zero or negative when either is absent.
          A strong pipeline combined with negative inflows (Ti < 0) produces
          a drag — intentional; it models crowded-short setups.

        • Sum_Rs: additive risk term.  Higher Cassandra signal load pushes
          CS upward because the engine is *contrarian* — it values mis-priced
          risk, not safety.  This term can be large for highly controversial
          assets (crypto, AI energy).

        • (Em * Kw): ecosystem leverage term.  Scaled connections × kingmaker
          multiplier.  Named-exec endorsement (Kw = 2.5) can nearly triple
          the ecosystem contribution.

        • (1 + Cc): denominator dampens the score for mainstream-owned assets.
          At Cc = 1.0 (100% mainstream owned), CS is halved.  At Cc = 0.0
          (no mainstream ownership), denominator = 1 → full score passes through.
        """
        numerator = (c.pv * c.ti) + c.sum_rs + (c.em * c.kw)
        cs_raw    = numerator / (1.0 + c.cc)
        cs        = round(cs_raw, 4)

        is_asymmetry  = (c.pv >= self.pv_accel) and (c.cc <= self.cc_low)
        is_cass_risk  = c.sum_rs >= self.cassandra_danger
        is_endorsed   = c.kw > 1.0

        if is_asymmetry:
            log.info(
                "[CS ENGINE] ASYMMETRY PLAY: %s (%s) CS=%.2f Pv=%.1f Cc=%.2f",
                c.asset_name, c.ticker or "—", cs, c.pv, c.cc,
            )

        return ContrарianScoreResult(
            asset_id=c.asset_id,
            asset_name=c.asset_name,
            ticker=c.ticker,
            cs=cs,
            components=c,
            is_asymmetry_play=is_asymmetry,
            is_cassandra_risk=is_cass_risk,
            is_kingmaker_endorsed=is_endorsed,
        )

    # ── Simulation helpers ────────────────────────────────────────────────────

    def simulate(
        self,
        asset_id: int,
        *,
        pv: Optional[float] = None,
        ti: Optional[float] = None,
        sum_rs: Optional[float] = None,
        em: Optional[float] = None,
        kw: Optional[float] = None,
        cc: Optional[float] = None,
    ) -> Optional[ContrарianScoreResult]:
        """
        What-if simulator: fetch live components then override specified values.

        Useful for stress testing ("what happens if Jensen Huang endorses this?"):

            engine.simulate(asset_id=7, kw=2.5, cc=0.05)
        """
        base = self._aggregator.fetch(asset_id)
        if not base:
            return None

        overridden = base.model_copy(update={
            k: v for k, v in {
                "pv": pv, "ti": ti, "sum_rs": sum_rs,
                "em": em, "kw": kw, "cc": cc,
            }.items() if v is not None
        })
        return self._compute(overridden)

    def sensitivity_table(
        self,
        asset_id: int,
        variable: str,
        values: list[float],
    ) -> list[tuple[float, float]]:
        """
        Return a list of (variable_value, cs) tuples showing how CS changes
        as `variable` is swept across `values`, holding all other components fixed.

        Example::

            engine.sensitivity_table(7, "cc", [0.0, 0.1, 0.2, 0.5, 1.0])
            # → [(0.0, 32.4), (0.1, 29.5), ...]
        """
        if asset_id is None:
            return []
        base = self._aggregator.fetch(asset_id)
        if not base:
            return []

        results: list[tuple[float, float]] = []
        for v in values:
            override = {variable: v}
            comp = base.model_copy(update=override)
            result = self._compute(comp)
            results.append((v, result.cs))
        return results
