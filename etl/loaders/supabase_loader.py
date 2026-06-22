"""
Supabase Loader

Routes parsed/scraped data from all three ETL pipelines to the correct
Supabase destination:

  Kingmaker relationships → fn_promote_nlp_to_connection RPC (via NLP_Signal_Extractions)
  Cassandra signals       → signal-submit Edge Function
  Horizon filings         → Asset_Registry table insert (UPSERT)

Each method returns a LoadResult so the orchestrator can track
records_inserted / records_rejected per Ingestion_Jobs row.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from etl.client import SupabaseClient
from etl.models import (
    CassandraSignalPayload,
    HorizonFilingRecord,
    KingmakerRelationship,
    LoadResult,
)

log = logging.getLogger(__name__)

# Connection type → NLP_Signal_Extractions.Signal_Type mapping
_CONNECTION_TO_SIGNAL_TYPE: dict[str, str] = {
    "Supplier":       "Kingmaker_Trigger",
    "JV_Partner":     "Kingmaker_Trigger",
    "Custom_Silicon": "Kingmaker_Trigger",
    "Equity_Stake":   "Kingmaker_Trigger",
}

# instrument_type ENUM → asset_class label for Asset_Registry
_INSTRUMENT_TYPE_TO_ASSET_CLASS: dict[str, str] = {
    "ETF":            "Equity ETF",
    "ETP":            "Exchange Traded Product",
    "Corporate_Proxy": "Equity",
    "Pipeline_Filing": "Pipeline",
}


class SupabaseLoader:
    """
    Persists ETL results to Supabase via REST API and Edge Functions.

    Usage::

        loader = SupabaseLoader()
        result = loader.load_kingmaker_relationship(rel)
        result = loader.load_cassandra_signal(signal)
        result = loader.load_horizon_filing(filing)
    """

    def __init__(self, client: Optional[SupabaseClient] = None) -> None:
        self._client = client or SupabaseClient()

    # ── Kingmaker ─────────────────────────────────────────────────────────────

    def load_kingmaker_relationship(
        self, rel: KingmakerRelationship
    ) -> LoadResult:
        """
        Persist a KingmakerRelationship via a two-step process:
          1. INSERT into NLP_Signal_Extractions (provenance record)
          2. Call fn_promote_nlp_to_connection RPC (upserts into CEC)

        Returns LoadResult with the CEC record_id if successful.
        """
        # Step 1 — insert provenance row
        nlp_row: dict[str, Any] = {
            "Signal_Type":          _CONNECTION_TO_SIGNAL_TYPE.get(rel.connection_type, "Kingmaker_Trigger"),
            "Titan_Ticker":         rel.titan_ticker,
            "Counterparty_Name":    rel.counterparty_name,
            "Counterparty_Ticker":  rel.counterparty_ticker,
            "Connection_Type":      rel.connection_type,
            "Confidence_Score":     rel.confidence_score,
            "Extracted_Text":       rel.extracted_text[:2000],
            "Source_Document":      rel.source_document,
            "Char_Offset_Start":    rel.char_offset_start,
            "Char_Offset_End":      rel.char_offset_end,
            "NLP_Model_Version":    rel.nlp_model_version,
            "Wallet_Share_Est":     rel.share_of_wallet_est,
            "Endorsement_Flag":     rel.endorsement_flag,
            "Endorsement_Source":   rel.endorsement_source,
        }

        status, body = self._client.table_insert(
            "NLP_Signal_Extractions",
            nlp_row,
            on_conflict="Source_Document,Titan_Ticker,Counterparty_Name,Connection_Type",
        )

        if status not in (200, 201):
            log.error(
                "NLP_Signal_Extractions insert failed %d: %s",
                status, body
            )
            return LoadResult(success=False, http_status=status, error=str(body)[:500])

        # Extract the new extraction_id
        extraction_id: Optional[int] = None
        if isinstance(body, list) and body:
            extraction_id = body[0].get("id") or body[0].get("Extraction_ID")
        elif isinstance(body, dict):
            extraction_id = body.get("id") or body.get("Extraction_ID")

        if not extraction_id:
            log.warning("NLP row inserted but no extraction_id returned; skipping promotion")
            return LoadResult(success=True, http_status=status)

        # Step 2 — promote to Corporate_Ecosystem_Connections
        rpc_status, rpc_body = self._client.rpc(
            "fn_promote_nlp_to_connection",
            {"p_extraction_id": extraction_id},
        )
        if rpc_status not in (200, 201):
            log.error(
                "fn_promote_nlp_to_connection failed %d: %s",
                rpc_status, rpc_body
            )
            return LoadResult(
                success=False,
                http_status=rpc_status,
                error=str(rpc_body)[:500],
            )

        connection_id: Optional[int] = None
        if isinstance(rpc_body, dict):
            connection_id = rpc_body.get("connection_id")
        elif isinstance(rpc_body, int):
            connection_id = rpc_body

        log.debug(
            "Kingmaker loaded: extraction=%s → connection=%s",
            extraction_id, connection_id
        )
        return LoadResult(success=True, record_id=connection_id, http_status=rpc_status)

    def load_kingmaker_batch(
        self, relationships: list[KingmakerRelationship]
    ) -> tuple[int, int]:
        """
        Bulk load a list of relationships.

        Returns (inserted_count, rejected_count).
        """
        inserted = rejected = 0
        for rel in relationships:
            result = self.load_kingmaker_relationship(rel)
            if result.success:
                inserted += 1
            else:
                rejected += 1
        return inserted, rejected

    # ── Cassandra ─────────────────────────────────────────────────────────────

    def load_cassandra_signal(
        self, signal: CassandraSignalPayload
    ) -> LoadResult:
        """
        POST a CassandraSignalPayload to the signal-submit Edge Function.

        Returns LoadResult with signal_id from the Edge Function response.
        """
        payload: dict[str, Any] = {
            "title":        signal.title,
            "text":         signal.text,
            "risk_score":   signal.risk_score,
            "signal_source": signal.signal_source,
        }
        if signal.asset_id is not None:
            payload["asset_id"] = signal.asset_id
        if signal.cluster_id is not None:
            payload["cluster_id"] = signal.cluster_id
        if signal.risk_vector:
            payload["risk_vector"] = signal.risk_vector
        if signal.source_url:
            payload["source_url"] = signal.source_url
        if signal.related_connection_id is not None:
            payload["related_connection_id"] = signal.related_connection_id

        status, body = self._client.call_edge_function("signal-submit", payload)

        if status not in (200, 201):
            log.error(
                "signal-submit failed %d: %s | title=%s",
                status, body, signal.title[:60]
            )
            return LoadResult(success=False, http_status=status, error=str(body)[:500])

        signal_id: Optional[int] = None
        if isinstance(body, dict):
            signal_id = body.get("signal_id")

        log.debug("Cassandra signal loaded: id=%s score=%d", signal_id, signal.risk_score)
        return LoadResult(success=True, signal_id=signal_id, http_status=status)

    def load_cassandra_batch(
        self, signals: list[CassandraSignalPayload]
    ) -> tuple[int, int]:
        """
        Bulk load Cassandra signals.

        Returns (inserted_count, rejected_count).
        """
        inserted = rejected = 0
        for signal in signals:
            result = self.load_cassandra_signal(signal)
            if result.success:
                inserted += 1
            else:
                rejected += 1
        return inserted, rejected

    # ── Horizon ───────────────────────────────────────────────────────────────

    def load_horizon_filing(self, filing: HorizonFilingRecord) -> LoadResult:
        """
        UPSERT a HorizonFilingRecord into the Asset_Registry table.

        Uses accession_number + filer_name as the conflict key so
        re-runs are idempotent.
        """
        asset_class = (
            filing.asset_class
            or _INSTRUMENT_TYPE_TO_ASSET_CLASS.get(filing.instrument_type, "Pipeline")
        )

        row: dict[str, Any] = {
            "Ticker":            filing.ticker_proposed,
            "Name":              filing.asset_name[:300],
            "Asset_Class":       asset_class,
            "Instrument_Type":   filing.instrument_type,
            "Exchange_MIC":      self._exchange_to_mic(filing.listing_exchange),
            "Domicile_Country":  filing.domicile_country,
            "Issuer":            filing.filer_name,
            "Filing_Type":       filing.filing_type,
            "Filing_Date":       filing.filing_date.isoformat() if filing.filing_date else None,
            "Accession_Number":  filing.accession_number,
            "EDGAR_URL":         filing.edgar_url,
            "FCA_URL":           filing.fca_url,
            "Listing_Timeline":  filing.listing_timeline,
            "Raw_Description":   filing.raw_description,
            "Is_Pipeline":       True,
        }
        # Remove None values to avoid overwriting existing data on upsert
        row = {k: v for k, v in row.items() if v is not None}

        status, body = self._client.table_insert(
            "Asset_Registry",
            row,
            on_conflict="Accession_Number,Issuer",
        )

        if status not in (200, 201):
            log.error(
                "Asset_Registry insert failed %d: %s | %s",
                status, body, filing.asset_name[:60]
            )
            return LoadResult(success=False, http_status=status, error=str(body)[:500])

        record_id: Optional[int] = None
        if isinstance(body, list) and body:
            record_id = body[0].get("id") or body[0].get("Asset_ID")
        elif isinstance(body, dict):
            record_id = body.get("id") or body.get("Asset_ID")

        log.debug(
            "Horizon filing loaded: id=%s | %s", record_id, filing.asset_name[:60]
        )
        return LoadResult(success=True, record_id=record_id, http_status=status)

    def load_horizon_batch(
        self, filings: list[HorizonFilingRecord]
    ) -> tuple[int, int]:
        """
        Bulk load Horizon filings.

        Returns (inserted_count, rejected_count).
        """
        inserted = rejected = 0
        for filing in filings:
            result = self.load_horizon_filing(filing)
            if result.success:
                inserted += 1
            else:
                rejected += 1
        return inserted, rejected

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def _exchange_to_mic(exchange: Optional[str]) -> Optional[str]:
        """Map common exchange names to ISO 10383 MIC codes."""
        if not exchange:
            return None
        mapping = {
            "NYSE":   "XNYS",
            "NASDAQ": "XNAS",
            "LSE":    "XLON",
            "CBOE":   "XCBO",
            "ARCA":   "ARCX",
            "BATS":   "BATS",
        }
        return mapping.get(exchange.upper(), exchange[:10])
