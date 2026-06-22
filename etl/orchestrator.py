"""
ETL Orchestrator

Coordinates the three Contrarian Radar pipelines:
  1. Kingmaker  — parse transcripts/filings → load relationships
  2. Cassandra  — scrape alt-media → load risk signals
  3. Horizon    — scan EDGAR/FCA → load pipeline filings

Tracks each run as an Ingestion_Jobs row in Supabase so pipeline
health is observable via the v_pipeline_health view.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from etl.client import SupabaseClient
from etl.config import configure_logging
from etl.loaders.supabase_loader import SupabaseLoader
from etl.models import IngestionJobRecord
from etl.parsers.kingmaker_parser import KingmakerTranscriptParser
from etl.scrapers.cassandra_scraper import CassandraPipelineScraper
from etl.scrapers.horizon_scraper import HorizonRegistryScanner

log = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Summary of a single pipeline run."""
    pipeline:          str
    fetched:           int = 0
    inserted:          int = 0
    rejected:          int = 0
    elapsed_seconds:   float = 0.0
    error:             Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


@dataclass
class OrchestratorResult:
    """Aggregated result for a full ETL run."""
    pipelines: list[PipelineResult] = field(default_factory=list)
    total_elapsed: float = 0.0

    @property
    def total_inserted(self) -> int:
        return sum(p.inserted for p in self.pipelines)

    @property
    def total_rejected(self) -> int:
        return sum(p.rejected for p in self.pipelines)

    @property
    def all_succeeded(self) -> bool:
        return all(p.success for p in self.pipelines)


class ETLOrchestrator:
    """
    Top-level coordinator for the Contrarian Radar ETL suite.

    Usage::

        orch = ETLOrchestrator()

        # Run a specific pipeline
        result = orch.run_kingmaker(text="NVIDIA Q1...", source_doc="NVDA_Q1_2025")
        result = orch.run_cassandra()
        result = orch.run_horizon()

        # Run all three
        full = orch.run_all(kingmaker_sources=[...])
    """

    def __init__(
        self,
        client: Optional[SupabaseClient] = None,
        cassandra_seed_urls: Optional[list[str]] = None,
        cassandra_rps: float = 1.5,
        min_cassandra_risk_score: int = 3,
    ) -> None:
        configure_logging()
        self._client  = client or SupabaseClient()
        self._loader  = SupabaseLoader(client=self._client)
        self._parser  = KingmakerTranscriptParser()
        self._scraper = CassandraPipelineScraper(
            seed_urls=cassandra_seed_urls,
            requests_per_second=cassandra_rps,
            min_risk_score=min_cassandra_risk_score,
        )
        self._horizon = HorizonRegistryScanner()

    # ── Pipeline runners ──────────────────────────────────────────────────────

    def run_kingmaker(
        self,
        text: str,
        source_doc: str,
        source_type: str = "earnings_call",
        include_unknown_vendors: bool = False,
        source_id: int = 1,
    ) -> PipelineResult:
        """
        Run the Kingmaker parser on a single document and load results.

        Args:
            text:                    Raw transcript / filing text.
            source_doc:              Identifier e.g. "NVDA_10K_2025".
            source_type:             One of the KingmakerBatch.source_type literals.
            include_unknown_vendors: Also extract unresolved entity mentions.
            source_id:               Data_Source_Registry PK for Ingestion_Jobs tracking.
        """
        t0 = time.monotonic()
        job_id = self._start_job(source_id, "Kingmaker")

        try:
            if include_unknown_vendors:
                batch = self._parser.parse_with_unknown_vendors(text, source_doc, source_type)
            else:
                batch = self._parser.parse(text, source_doc, source_type)

            fetched  = len(batch.relationships)
            inserted, rejected = self._loader.load_kingmaker_batch(batch.relationships)

            elapsed = round(time.monotonic() - t0, 3)
            self._complete_job(job_id, fetched, inserted, 0, rejected)

            log.info(
                "[ORCH] Kingmaker done: fetched=%d inserted=%d rejected=%d %.1fs",
                fetched, inserted, rejected, elapsed,
            )
            return PipelineResult(
                pipeline="Kingmaker",
                fetched=fetched,
                inserted=inserted,
                rejected=rejected,
                elapsed_seconds=elapsed,
            )

        except Exception as exc:
            self._fail_job(job_id, str(exc))
            log.exception("[ORCH] Kingmaker pipeline error")
            return PipelineResult(
                pipeline="Kingmaker",
                elapsed_seconds=round(time.monotonic() - t0, 3),
                error=str(exc),
            )

    def run_cassandra(self, source_id: int = 2) -> PipelineResult:
        """
        Run the Cassandra scraper and load all scored signals above threshold.

        Args:
            source_id: Data_Source_Registry PK for Ingestion_Jobs tracking.
        """
        t0 = time.monotonic()
        job_id = self._start_job(source_id, "Cassandra")

        try:
            batch    = self._scraper.scrape()
            fetched  = len(batch.signals)
            inserted, rejected = self._loader.load_cassandra_batch(batch.signals)

            elapsed = round(time.monotonic() - t0, 3)
            self._complete_job(job_id, fetched, inserted, 0, rejected)

            log.info(
                "[ORCH] Cassandra done: fetched=%d inserted=%d rejected=%d %.1fs",
                fetched, inserted, rejected, elapsed,
            )
            return PipelineResult(
                pipeline="Cassandra",
                fetched=fetched,
                inserted=inserted,
                rejected=rejected,
                elapsed_seconds=elapsed,
            )

        except Exception as exc:
            self._fail_job(job_id, str(exc))
            log.exception("[ORCH] Cassandra pipeline error")
            return PipelineResult(
                pipeline="Cassandra",
                elapsed_seconds=round(time.monotonic() - t0, 3),
                error=str(exc),
            )

    def run_horizon(self, registry: str = "BOTH", source_id: int = 3) -> PipelineResult:
        """
        Run the Horizon registry scanner and load new pipeline filings.

        Args:
            registry:  "EDGAR", "FCA", or "BOTH".
            source_id: Data_Source_Registry PK for Ingestion_Jobs tracking.
        """
        t0 = time.monotonic()
        job_id = self._start_job(source_id, "Horizon")

        try:
            if registry == "EDGAR":
                batch = self._horizon.scan_edgar()
            elif registry == "FCA":
                batch = self._horizon.scan_fca()
            else:
                batch = self._horizon.scan_all()

            fetched  = len(batch.filings)
            inserted, rejected = self._loader.load_horizon_batch(batch.filings)

            elapsed = round(time.monotonic() - t0, 3)
            self._complete_job(job_id, fetched, inserted, 0, rejected)

            log.info(
                "[ORCH] Horizon done: fetched=%d inserted=%d rejected=%d %.1fs",
                fetched, inserted, rejected, elapsed,
            )
            return PipelineResult(
                pipeline="Horizon",
                fetched=fetched,
                inserted=inserted,
                rejected=rejected,
                elapsed_seconds=elapsed,
            )

        except Exception as exc:
            self._fail_job(job_id, str(exc))
            log.exception("[ORCH] Horizon pipeline error")
            return PipelineResult(
                pipeline="Horizon",
                elapsed_seconds=round(time.monotonic() - t0, 3),
                error=str(exc),
            )

    def run_all(
        self,
        kingmaker_sources: Optional[list[tuple[str, str, str]]] = None,
        horizon_registry: str = "BOTH",
    ) -> OrchestratorResult:
        """
        Run all three pipelines sequentially and aggregate results.

        Args:
            kingmaker_sources: List of (text, source_doc, source_type) tuples.
            horizon_registry:  "EDGAR", "FCA", or "BOTH".
        """
        t0       = time.monotonic()
        results  : list[PipelineResult] = []

        # Kingmaker — one run per supplied document
        if kingmaker_sources:
            for text, source_doc, source_type in kingmaker_sources:
                res = self.run_kingmaker(text, source_doc, source_type)
                results.append(res)
        else:
            log.info("[ORCH] No Kingmaker sources supplied; skipping Kingmaker pipeline")

        # Cassandra
        results.append(self.run_cassandra())

        # Horizon
        results.append(self.run_horizon(registry=horizon_registry))

        total = round(time.monotonic() - t0, 3)
        log.info(
            "[ORCH] run_all complete in %.1fs | total inserted=%d rejected=%d",
            total,
            sum(r.inserted for r in results),
            sum(r.rejected for r in results),
        )
        return OrchestratorResult(pipelines=results, total_elapsed=total)

    # ── Ingestion_Jobs tracking ───────────────────────────────────────────────

    def _start_job(self, source_id: int, pipeline_name: str) -> Optional[int]:
        """Insert a Pending → Running Ingestion_Jobs row; return job PK."""
        row = IngestionJobRecord(
            source_id=source_id,
            job_status="Running",
            triggered_by=f"etl_orchestrator:{pipeline_name}",
        ).model_dump()

        status, body = self._client.table_insert("Ingestion_Jobs", row)
        if status in (200, 201):
            if isinstance(body, list) and body:
                return body[0].get("Job_ID") or body[0].get("id")
            if isinstance(body, dict):
                return body.get("Job_ID") or body.get("id")
        log.warning("Could not create Ingestion_Jobs row for %s: %d", pipeline_name, status)
        return None

    def _complete_job(
        self,
        job_id: Optional[int],
        fetched: int,
        inserted: int,
        updated: int,
        rejected: int,
    ) -> None:
        if not job_id:
            return
        self._client.rpc(
            "fn_update_ingestion_job",
            {
                "p_job_id":            job_id,
                "p_status":            "Completed",
                "p_records_fetched":   fetched,
                "p_records_inserted":  inserted,
                "p_records_updated":   updated,
                "p_records_rejected":  rejected,
            },
        )

    def _fail_job(self, job_id: Optional[int], error_message: str) -> None:
        if not job_id:
            return
        self._client.rpc(
            "fn_update_ingestion_job",
            {
                "p_job_id":        job_id,
                "p_status":        "Failed",
                "p_error_message": error_message[:1000],
            },
        )
