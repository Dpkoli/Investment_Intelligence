"""
Signal Aggregator

Pulls the raw metric values for each CS component from Supabase,
one asset at a time, and returns a populated CSComponents object.

Data sources per component:
  Pv  ← Asset_Registry (Is_Pipeline=True, Filing_Date in last 120 days, same cluster)
  Ti  ← Alt_Data_Observations (Signal_Category='Fund_Flow', Z_Score, 30-day window)
  Sum_Rs ← Cassandra_Signals (Systemic_Risk_Score, same cluster, Status='Open')
  Em  ← Corporate_Ecosystem_Connections (Asset_ID or matching Ticker)
  Kw  ← NLP_Signal_Extractions (Endorsement_Flag=True) or CEC Endorsement_Flag
  Cc  ← Asset_Alpha_Scores.Consensus_Crowding_Factor (most recent row)
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Optional

from etl.client import SupabaseClient
from analytics.scoring.models import CSComponents

log = logging.getLogger(__name__)

# Kingmaker Weight when at least one endorsement is active
KW_ENDORSED: float = 2.5

# Normalisation caps — raw values are scaled relative to these ceilings
PV_CAP:    float = 20.0   # 20 new pipeline filings in 120d → Pv = 10
EM_CAP:    float = 30.0   # 30 confirmed connections → Em = 10 (normalised)
TI_FLOOR:  float = -2.0   # 200% outflow rate → floor
TI_CEIL:   float = 5.0    # 500% inflow rate → ceiling


class SignalAggregator:
    """
    Fetches and assembles CSComponents for a given asset from Supabase.

    Usage::

        agg = SignalAggregator()
        components = agg.fetch(asset_id=42)
    """

    def __init__(self, client: Optional[SupabaseClient] = None) -> None:
        self._db = client or SupabaseClient()

    def fetch(self, asset_id: int) -> Optional[CSComponents]:
        """
        Pull all CS signal components for `asset_id`.

        Returns None if the asset cannot be found.
        """
        asset = self._get_asset(asset_id)
        if not asset:
            log.warning("SignalAggregator: asset_id=%d not found", asset_id)
            return None

        cluster_id  = asset.get("Cluster_ID")
        ticker      = asset.get("Ticker")
        name        = asset.get("Name", f"Asset_{asset_id}")

        pv,  pv_count   = self._fetch_pv(cluster_id)
        ti               = self._fetch_ti(cluster_id, asset_id)
        sum_rs, rs_count = self._fetch_sum_rs(cluster_id)
        em_raw, em_norm  = self._fetch_em(asset_id, ticker)
        kw               = self._fetch_kw(asset_id, ticker)
        cc               = self._fetch_cc(asset_id)

        return CSComponents(
            asset_id=asset_id,
            asset_name=name,
            ticker=ticker,
            pv=pv,
            ti=ti,
            sum_rs=sum_rs,
            em=em_norm,
            kw=kw,
            cc=cc,
            rs_signal_count=rs_count,
            em_connection_count=em_raw,
        )

    def fetch_all(self) -> list[CSComponents]:
        """Fetch components for every asset in the KINGMAKER cluster."""
        status, rows = self._db.table_select(
            "Asset_Registry",
            filters={"Is_Pipeline": False},
            columns="Asset_ID,Name,Ticker,Cluster_ID",
            limit=500,
        )
        if status != 200 or not rows:
            log.warning("fetch_all: could not retrieve Asset_Registry (HTTP %d)", status)
            return []

        components: list[CSComponents] = []
        for row in rows:
            c = self.fetch(row["Asset_ID"])
            if c:
                components.append(c)
        return components

    # ── Component fetchers ────────────────────────────────────────────────────

    def _get_asset(self, asset_id: int) -> Optional[dict[str, Any]]:
        status, rows = self._db.table_select(
            "Asset_Registry",
            filters={"Asset_ID": asset_id},
            columns="Asset_ID,Name,Ticker,Cluster_ID",
            limit=1,
        )
        return rows[0] if status == 200 and rows else None

    def _fetch_pv(self, cluster_id: Optional[int]) -> tuple[float, int]:
        """
        Pv = normalised count of new pipeline filings in last 120 days
             for the same Exposure_Cluster.

        Raw count is capped at PV_CAP then scaled to [0, 10].
        """
        if not cluster_id:
            return 0.0, 0

        cutoff = (date.today() - timedelta(days=120)).isoformat()
        status, rows = self._db.table_select(
            "Asset_Registry",
            filters={"Cluster_ID": cluster_id, "Is_Pipeline": True},
            columns="Asset_ID,Filing_Date",
            limit=500,
        )
        if status != 200:
            return 0.0, 0

        # Filter to those filed within window (REST API equality filter can't do date range;
        # we do it in Python after fetching)
        recent = [r for r in rows if (r.get("Filing_Date") or "") >= cutoff]
        count  = len(recent)
        pv     = round(min(count / PV_CAP, 1.0) * 10.0, 4)
        return pv, count

    def _fetch_ti(self, cluster_id: Optional[int], asset_id: int) -> float:
        """
        Ti = 30-day fund-flow rate-of-change, sourced from Alt_Data_Observations.

        Reads the two most recent 'Fund_Flow' Z-Score observations for the
        cluster and computes period-over-period change. Falls back to 0 if
        insufficient data.

        Output is clamped to [TI_FLOOR, TI_CEIL].
        """
        status, rows = self._db.table_select(
            "Alt_Data_Observations",
            filters={"Signal_Category": "Fund_Flow", "Asset_ID": asset_id},
            columns="Z_Score,Observed_At",
            limit=2,
        )
        if status == 200 and len(rows) >= 2:
            z_new = rows[0].get("Z_Score") or 0.0
            z_old = rows[1].get("Z_Score") or 0.0
            if z_old != 0:
                ti = (z_new - z_old) / abs(z_old)
            else:
                ti = z_new
            return round(max(TI_FLOOR, min(TI_CEIL, float(ti))), 4)

        # Fallback: use cluster-level Z-Score from most recent observation
        if cluster_id:
            status, rows = self._db.table_select(
                "Alt_Data_Observations",
                filters={"Signal_Category": "Fund_Flow", "Cluster_ID": cluster_id},
                columns="Z_Score",
                limit=1,
            )
            if status == 200 and rows:
                z = float(rows[0].get("Z_Score") or 0.0)
                return round(max(TI_FLOOR, min(TI_CEIL, z / 3.0)), 4)

        return 0.0

    def _fetch_sum_rs(self, cluster_id: Optional[int]) -> tuple[float, int]:
        """
        Sum_Rs = sum of Systemic_Risk_Score across all open Cassandra signals
                 linked to this cluster.
        """
        if not cluster_id:
            return 0.0, 0

        status, rows = self._db.table_select(
            "Cassandra_Signals",
            filters={"Cluster_ID": cluster_id, "Status": "Open"},
            columns="Systemic_Risk_Score",
            limit=200,
        )
        if status != 200 or not rows:
            return 0.0, 0

        scores  = [float(r.get("Systemic_Risk_Score") or 0) for r in rows]
        total   = sum(scores)
        return round(total, 2), len(scores)

    def _fetch_em(self, asset_id: int, ticker: Optional[str]) -> tuple[int, float]:
        """
        Em = normalised count of confirmed S&P 500 B2B connections.

        Raw count capped at EM_CAP, scaled to [0, 10].
        """
        filters: dict[str, Any] = {}
        if ticker:
            filters["Counterparty_Ticker"] = ticker
        else:
            filters["Asset_ID"] = asset_id

        status, rows = self._db.table_select(
            "Corporate_Ecosystem_Connections",
            filters=filters,
            columns="Connection_ID",
            limit=500,
        )
        count = len(rows) if status == 200 else 0
        em    = round(min(count / EM_CAP, 1.0) * 10.0, 4)
        return count, em

    def _fetch_kw(self, asset_id: int, ticker: Optional[str]) -> float:
        """
        Kw = KW_ENDORSED if any NLP extraction carries Endorsement_Flag=True,
             else 1.0 (neutral baseline).
        """
        filters: dict[str, Any] = {"Endorsement_Flag": True}
        if ticker:
            filters["Counterparty_Ticker"] = ticker

        status, rows = self._db.table_select(
            "NLP_Signal_Extractions",
            filters=filters,
            columns="Extraction_ID",
            limit=1,
        )
        if status == 200 and rows:
            return KW_ENDORSED

        # Also check Corporate_Ecosystem_Connections directly
        cec_filters: dict[str, Any] = {"Endorsement_Flag": True}
        if ticker:
            cec_filters["Counterparty_Ticker"] = ticker
        status, rows = self._db.table_select(
            "Corporate_Ecosystem_Connections",
            filters=cec_filters,
            columns="Connection_ID",
            limit=1,
        )
        return KW_ENDORSED if (status == 200 and rows) else 1.0

    def _fetch_cc(self, asset_id: int) -> float:
        """
        Cc = most recent Consensus_Crowding_Factor from Asset_Alpha_Scores.
        Defaults to 0.0 (no crowding data) if absent.
        """
        status, rows = self._db.table_select(
            "Asset_Alpha_Scores",
            filters={"Asset_ID": asset_id},
            columns="Consensus_Crowding_Factor,Scored_At",
            limit=1,
        )
        if status == 200 and rows:
            cc = rows[0].get("Consensus_Crowding_Factor")
            if cc is not None:
                return round(max(0.0, min(1.0, float(cc))), 4)
        return 0.0
