"""
Horizon Registry Scanner

Polls SEC EDGAR full-text search (EFTS) and the FCA Financial Instruments
Register for new fund/ETP prospectus filings from known passive asset managers.

Pipeline:
  EDGAR EFTS query (S-1, DEF-14A, N-1A) OR FCA REST query
    → filter by HORIZON_ISSUERS
    → extract asset class, ticker, listing timeline
    → classify instrument_type
    → return HorizonScanBatch
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional
from urllib.parse import urlencode

from etl.client import RateLimitedHTTPClient
from etl.config import (
    EDGAR_RATE_LIMIT_RPS,
    FCA_RATE_LIMIT_RPS,
    HORIZON_EDGAR_CIKS,
    HORIZON_ISSUERS,
)
from etl.models import HorizonFilingRecord, HorizonScanBatch
from etl.parsers.nlp_patterns import (
    ASSET_CLASS_PATTERNS,
    FILING_TO_INSTRUMENT,
    TIMELINE_PATTERNS,
)

log = logging.getLogger(__name__)

# EDGAR full-text search API
_EFTS_BASE = "https://efts.sec.gov/LATEST/search-index"

# FCA Register authorised funds endpoint
_FCA_BASE = "https://register.fca.org.uk/services/V0.1"

# How far back to look for new filings (days)
_LOOKBACK_DAYS = 14

# Filing forms to monitor on EDGAR
_TARGET_FORMS = ["S-1", "S-1/A", "DEF-14A", "N-1A", "N-1A/A", "N-2"]


class HorizonRegistryScanner:
    """
    Scans SEC EDGAR and the FCA Register for new pipeline filings.

    Usage::

        scanner = HorizonRegistryScanner()
        batch   = scanner.scan_edgar()
        batch2  = scanner.scan_fca()
        combined = scanner.scan_all()
    """

    def __init__(self) -> None:
        self._edgar_http = RateLimitedHTTPClient(requests_per_second=EDGAR_RATE_LIMIT_RPS)
        self._fca_http   = RateLimitedHTTPClient(requests_per_second=FCA_RATE_LIMIT_RPS)

    # ── Public API ────────────────────────────────────────────────────────────

    def scan_all(self) -> HorizonScanBatch:
        """Scan both EDGAR and FCA; merge results into one batch."""
        t0 = time.monotonic()
        filings: list[HorizonFilingRecord] = []

        edgar_batch = self.scan_edgar()
        filings.extend(edgar_batch.filings)

        fca_batch = self.scan_fca()
        filings.extend(fca_batch.filings)

        log.info(
            "[HORIZON] scan_all complete: %d filings (EDGAR=%d, FCA=%d) in %.1fs",
            len(filings),
            len(edgar_batch.filings),
            len(fca_batch.filings),
            time.monotonic() - t0,
        )
        return HorizonScanBatch(
            registry="BOTH",
            filings=filings,
            elapsed_seconds=round(time.monotonic() - t0, 3),
        )

    def scan_edgar(self) -> HorizonScanBatch:
        """Poll EDGAR EFTS for new pipeline filings from known horizon issuers."""
        t0 = time.monotonic()
        filings: list[HorizonFilingRecord] = []

        for form in _TARGET_FORMS:
            try:
                results = self._query_efts(form)
            except Exception as exc:
                log.warning("EDGAR EFTS query failed for form %s: %s", form, exc)
                continue

            for hit in results:
                record = self._parse_edgar_hit(hit, form)
                if record:
                    filings.append(record)
                    log.info(
                        "[HORIZON][EDGAR] %s | %s | %s",
                        record.filer_name,
                        record.filing_type,
                        record.asset_name[:60],
                    )

        return HorizonScanBatch(
            registry="SEC_EDGAR",
            filings=self._deduplicate(filings),
            elapsed_seconds=round(time.monotonic() - t0, 3),
        )

    def scan_fca(self) -> HorizonScanBatch:
        """Poll the FCA Register for newly authorised ETP/fund products."""
        t0 = time.monotonic()
        filings: list[HorizonFilingRecord] = []

        for issuer in HORIZON_ISSUERS:
            try:
                results = self._query_fca(issuer)
            except Exception as exc:
                log.warning("FCA query failed for issuer %s: %s", issuer, exc)
                continue

            for item in results:
                record = self._parse_fca_item(item, issuer)
                if record:
                    filings.append(record)
                    log.info(
                        "[HORIZON][FCA] %s | %s",
                        record.filer_name,
                        record.asset_name[:60],
                    )

        return HorizonScanBatch(
            registry="FCA",
            filings=self._deduplicate(filings),
            elapsed_seconds=round(time.monotonic() - t0, 3),
        )

    # ── EDGAR helpers ─────────────────────────────────────────────────────────

    def _query_efts(self, form: str) -> list[dict[str, Any]]:
        """
        Query EDGAR EFTS for recent filings of a given form type.

        Uses CIK-based filtering where possible to narrow to known horizon issuers.
        Falls back to keyword search on filer names.
        """
        # Build date window (last N days)
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=_LOOKBACK_DAYS)).isoformat()

        hits: list[dict[str, Any]] = []

        # Query per known CIK for precision
        for name, cik in HORIZON_EDGAR_CIKS.items():
            params = {
                "q":          f'"{name}"',
                "dateRange":  "custom",
                "startdt":    cutoff,
                "forms":      form,
                "entity":     cik,
                "_source":    "file-index",
                "hits.hits.total.value": 1,
            }
            url  = f"{_EFTS_BASE}?{urlencode(params)}"
            resp = self._edgar_http.get(url)
            if resp.status_code != 200:
                log.debug("EFTS %s → HTTP %d", url, resp.status_code)
                continue
            data = resp.json()
            for hit in data.get("hits", {}).get("hits", []):
                hit["_horizon_issuer"] = name
                hits.append(hit)

        return hits

    def _parse_edgar_hit(
        self, hit: dict[str, Any], form: str
    ) -> Optional[HorizonFilingRecord]:
        src     = hit.get("_source", {})
        filer   = src.get("entity_name", hit.get("_horizon_issuer", "Unknown"))
        display = src.get("display_names", [{}])
        name_raw = display[0].get("name", filer) if display else filer

        # Filter: must be a known horizon issuer
        if not self._is_horizon_issuer(filer):
            return None

        # Extract filing date
        filed_str = src.get("file_date", "")
        try:
            from datetime import date
            filing_date = date.fromisoformat(filed_str[:10])
        except (ValueError, TypeError):
            from datetime import date
            filing_date = date.today()

        description = src.get("period_of_report", "") or src.get("form_type", form)
        full_text   = (src.get("file_date", "") + " " + name_raw + " " + description)

        asset_class      = self._classify_asset_class(full_text)
        ticker_proposed  = self._extract_ticker(full_text)
        listing_timeline = self._extract_timeline(full_text)
        instrument_type  = FILING_TO_INSTRUMENT.get(form, "Pipeline_Filing")

        accession = src.get("accession_no", "").replace("-", "")
        edgar_url: Optional[str] = None
        if accession:
            edgar_url = f"https://www.sec.gov/Archives/edgar/data/{src.get('entity_id','')}/{accession}"

        return HorizonFilingRecord(
            filer_name=filer,
            filing_type=form,
            accession_number=src.get("accession_no"),
            filing_date=filing_date,
            asset_name=name_raw[:300],
            asset_class=asset_class,
            ticker_proposed=ticker_proposed,
            listing_exchange=src.get("exchange"),
            listing_timeline=listing_timeline,
            domicile_country="US",
            instrument_type=instrument_type,  # type: ignore[arg-type]
            edgar_url=edgar_url,
            raw_description=description[:500] if description else None,
        )

    # ── FCA helpers ───────────────────────────────────────────────────────────

    def _query_fca(self, issuer: str) -> list[dict[str, Any]]:
        """
        Search the FCA Register for authorised collective investment schemes
        or recognised investment exchanges linked to the issuer.
        """
        params = {"q": issuer, "category": "fund", "page": "1", "per_page": "50"}
        url    = f"{_FCA_BASE}/search?{urlencode(params)}"
        resp   = self._fca_http.get(url)
        if resp.status_code != 200:
            log.debug("FCA query for %s → HTTP %d", issuer, resp.status_code)
            return []

        data = resp.json()
        return data.get("Data", [])

    def _parse_fca_item(
        self, item: dict[str, Any], issuer: str
    ) -> Optional[HorizonFilingRecord]:
        name = item.get("Name", "")
        if not name:
            return None

        status = item.get("Status", "")
        if "authoris" not in status.lower() and "recognis" not in status.lower():
            return None

        from datetime import date
        registered_str = item.get("StatusEffectiveDate", "")
        try:
            filing_date = date.fromisoformat(registered_str[:10])
        except (ValueError, TypeError):
            filing_date = date.today()

        description = item.get("Type", "") + " " + name
        asset_class = self._classify_asset_class(description)
        fca_ref     = item.get("FirmReference", "")
        fca_url: Optional[str] = None
        if fca_ref:
            fca_url = f"https://register.fca.org.uk/s/firm?id={fca_ref}"

        return HorizonFilingRecord(
            filer_name=issuer,
            filing_type="FCA-ETP",
            filing_date=filing_date,
            asset_name=name[:300],
            asset_class=asset_class,
            listing_exchange="LSE",
            domicile_country="GB",
            instrument_type="ETP",
            fca_url=fca_url,
            raw_description=description[:500],
        )

    # ── Classification helpers ────────────────────────────────────────────────

    def _classify_asset_class(self, text: str) -> str:
        lower = text.lower()
        for label, pattern in ASSET_CLASS_PATTERNS:
            if pattern.search(lower):
                return label
        return "Unknown"

    def _extract_ticker(self, text: str) -> Optional[str]:
        m = re.search(r"\b([A-Z]{2,5})\b", text)
        return m.group(1) if m else None

    def _extract_timeline(self, text: str) -> Optional[str]:
        for pat in TIMELINE_PATTERNS:
            m = pat.search(text)
            if m:
                return m.group(0)[:50]
        return None

    def _is_horizon_issuer(self, name: str) -> bool:
        lower = name.lower()
        return any(issuer.lower() in lower for issuer in HORIZON_ISSUERS)

    def _deduplicate(
        self, filings: list[HorizonFilingRecord]
    ) -> list[HorizonFilingRecord]:
        seen: set[str] = set()
        out: list[HorizonFilingRecord] = []
        for f in filings:
            key = f"{f.filer_name}|{f.asset_name}|{f.filing_type}"
            if key not in seen:
                seen.add(key)
                out.append(f)
        return out
