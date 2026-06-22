"""
Pydantic data models for the Contrarian Radar ETL pipeline.

Each model maps 1-to-1 with a Supabase table row or an Edge Function
payload so serialisation is always clean.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ── Kingmaker ─────────────────────────────────────────────────────────────────

ConnectionType = Literal["Supplier", "JV_Partner", "Custom_Silicon", "Equity_Stake"]


class KingmakerRelationship(BaseModel):
    """A detected B2B structural dependency between a titan and a counterparty."""

    titan_ticker: str                                  # e.g. "NVDA"
    titan_name: str                                    # e.g. "Nvidia"
    counterparty_name: str                             # e.g. "Marvell Technology"
    counterparty_ticker: Optional[str] = None          # e.g. "MRVL"

    connection_type: ConnectionType = "Supplier"
    share_of_wallet_est: Optional[float] = Field(None, ge=0.0, le=1.0)
    endorsement_flag: bool = False
    endorsement_source: Optional[str] = None           # e.g. "Jensen Huang, GTC 2025"
    endorsement_date: Optional[date] = None

    confidence_score: int = Field(5, ge=1, le=10)
    revenue_impact_usd_est: Optional[float] = None

    # NLP provenance
    extracted_text: str                                # verbatim snippet that triggered extraction
    source_document: str                               # e.g. "NVDA_10K_2025_Item1A"
    char_offset_start: Optional[int] = None
    char_offset_end: Optional[int] = None
    nlp_model_version: str = "regex_v1.0"

    @field_validator("share_of_wallet_est", mode="before")
    @classmethod
    def clamp_wallet(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        return max(0.0, min(1.0, float(v)))


class KingmakerBatch(BaseModel):
    """Container for a parse run over a single source document."""

    source_document: str
    source_type: Literal[
        "earnings_call", "trade_show", "sec_10k", "sec_10q", "sec_8k", "press_release"
    ]
    parsed_at: datetime = Field(default_factory=datetime.utcnow)
    relationships: list[KingmakerRelationship] = Field(default_factory=list)
    total_chars: int = 0
    elapsed_seconds: float = 0.0


# ── Cassandra ─────────────────────────────────────────────────────────────────

SignalSource = Literal[
    "Whistleblower", "Influencer", "Regulatory_Leak",
    "Short_Seller_Report", "Anonymous_Filing"
]


class CassandraSignalPayload(BaseModel):
    """Payload dispatched to the signal-submit Edge Function."""

    # Required by signal-submit API
    title: str
    text: str
    risk_score: int = Field(..., ge=1, le=10)

    # Optional enrichment
    asset_id: Optional[int] = None
    cluster_id: Optional[int] = None
    signal_source: SignalSource = "Anonymous_Filing"
    source_handle: Optional[str] = None
    risk_vector: Optional[str] = None
    related_connection_id: Optional[int] = None
    source_url: Optional[str] = None

    # Internal pipeline metadata (not sent to API)
    triggered_keywords: list[str] = Field(default_factory=list)
    raw_severity_score: float = 0.0        # pre-normalisation float score


class CassandraScrapeBatch(BaseModel):
    """Container for a scrape run over a single source URL."""

    source_url: str
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    signals: list[CassandraSignalPayload] = Field(default_factory=list)
    elapsed_seconds: float = 0.0


# ── Horizon ───────────────────────────────────────────────────────────────────

HorizonInstrumentType = Literal["ETF", "ETP", "Corporate_Proxy", "Pipeline_Filing"]


class HorizonFilingRecord(BaseModel):
    """A newly detected prospectus or registry filing for the HORIZON cluster."""

    filer_name: str
    filing_type: str               # S-1 | DEF-14A | N-1A | FCA-ETP | 13-F
    accession_number: Optional[str] = None
    filing_date: date
    asset_name: str
    asset_class: str               # e.g. "Spot Bitcoin ETF", "AI Infrastructure ETF"
    ticker_proposed: Optional[str] = None
    listing_exchange: Optional[str] = None
    listing_timeline: Optional[str] = None   # e.g. "Q3 2026"
    domicile_country: str = "US"
    instrument_type: HorizonInstrumentType = "Pipeline_Filing"
    edgar_url: Optional[str] = None
    fca_url: Optional[str] = None
    raw_description: Optional[str] = None


class HorizonScanBatch(BaseModel):
    """Container for a registry scan run."""

    registry: Literal["SEC_EDGAR", "FCA", "BOTH"]
    scanned_at: datetime = Field(default_factory=datetime.utcnow)
    filings: list[HorizonFilingRecord] = Field(default_factory=list)
    elapsed_seconds: float = 0.0


# ── Ingestion job metadata ────────────────────────────────────────────────────

class IngestionJobRecord(BaseModel):
    """Row written to Ingestion_Jobs table on job start/completion."""

    source_id: int
    job_status: Literal["Pending", "Running", "Completed", "Failed", "Partial"] = "Pending"
    triggered_by: str = "etl_pipeline"
    records_fetched: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_rejected: int = 0
    error_message: Optional[str] = None
    retry_count: int = 0
    checkpoint_cursor: Optional[str] = None


# ── Loader results ────────────────────────────────────────────────────────────

class LoadResult(BaseModel):
    """Summarises the outcome of a single load operation."""

    success: bool
    record_id: Optional[int] = None        # PK of the inserted / updated row
    signal_id: Optional[int] = None        # Cassandra signal_id from Edge Function
    error: Optional[str] = None
    http_status: Optional[int] = None
