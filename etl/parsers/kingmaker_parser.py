"""
Kingmaker Transcript Parser — Ecosystem Scanner

Parses unstructured text from earnings call transcripts, trade show
presentations (e.g. Computex, NVIDIA GTC), and SEC regulatory filings
(10-K Item 1A, 10-Q Item 2) to detect hidden B2B dependencies between
S&P 500 titans and niche vendor/supplier counterparties.

Pipeline:
  raw text
    → tokenise into contextual windows
    → match titan entities
    → match counterparty entities in proximity
    → classify connection type
    → estimate wallet share
    → detect executive endorsement
    → score confidence
    → return KingmakerRelationship list
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional

from etl.config import (
    CANDIDATE_ALIAS_MAP,
    KINGMAKER_CANDIDATES,
    NLP_MODEL_VERSION,
    TITAN_ALIAS_MAP,
    TITANS,
)
from etl.models import KingmakerBatch, KingmakerRelationship
from etl.parsers.nlp_patterns import (
    COMPILED_CONNECTION_RULES,
    ENDORSEMENT_PATTERNS,
    QUALITATIVE_WALLET_MAP,
    RELATIONSHIP_TRIGGER_PATTERNS,
    SPEAKER_PATTERN,
    WALLET_SHARE_PATTERNS,
)

log = logging.getLogger(__name__)

# Context window around each titan mention to search for vendor entities
_WINDOW_CHARS = 600

# Minimum confidence threshold below which relationships are discarded
_MIN_CONFIDENCE = 3


class KingmakerTranscriptParser:
    """
    Parses unstructured text for titan–vendor structural dependencies.

    Usage::

        parser = KingmakerTranscriptParser()
        batch  = parser.parse("NVIDIA Q1 2025 Earnings Call...", "NVDA_Q1_2025_transcript")
        for rel in batch.relationships:
            print(rel.titan_ticker, "→", rel.counterparty_name, rel.connection_type)
    """

    def __init__(self) -> None:
        # Pre-compile entity search patterns for all known titans and candidates
        self._titan_patterns: dict[str, re.Pattern[str]] = {
            ticker: re.compile(
                r"\b(?:" + "|".join(re.escape(a) for a in aliases) + r")\b",
                re.IGNORECASE,
            )
            for ticker, aliases in TITANS.items()
        }
        self._candidate_patterns: dict[str, re.Pattern[str]] = {
            ticker: re.compile(
                r"\b(?:" + "|".join(re.escape(a) for a in aliases) + r")\b",
                re.IGNORECASE,
            )
            for ticker, aliases in KINGMAKER_CANDIDATES.items()
        }
        log.debug(
            "KingmakerTranscriptParser initialised with %d titans, %d candidates",
            len(self._titan_patterns), len(self._candidate_patterns),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def parse(
        self,
        text: str,
        source_document: str,
        source_type: str = "earnings_call",
    ) -> KingmakerBatch:
        """
        Main entry point. Parse raw text and return a KingmakerBatch.

        Args:
            text: Raw transcript / filing text (no HTML expected; strip first).
            source_document: Identifier for the source, e.g. "NVDA_10K_2025".
            source_type: One of the KingmakerBatch.source_type literals.
        """
        t0 = time.monotonic()
        relationships: list[KingmakerRelationship] = []

        for titan_ticker, titan_pattern in self._titan_patterns.items():
            titan_aliases = TITANS[titan_ticker]
            for match in titan_pattern.finditer(text):
                window_start = max(0, match.start() - _WINDOW_CHARS // 2)
                window_end   = min(len(text), match.end() + _WINDOW_CHARS // 2)
                window       = text[window_start:window_end]

                # Only continue if a relationship trigger is also present in window
                if not self._has_relationship_trigger(window):
                    continue

                for vendor_ticker, vendor_pattern in self._candidate_patterns.items():
                    vendor_match = vendor_pattern.search(window)
                    if not vendor_match:
                        continue

                    rel = self._build_relationship(
                        text=text,
                        window=window,
                        window_start=window_start,
                        titan_ticker=titan_ticker,
                        titan_name=self._best_name(titan_ticker, TITANS),
                        vendor_ticker=vendor_ticker,
                        vendor_name=self._best_name(vendor_ticker, KINGMAKER_CANDIDATES),
                        match_start=window_start + vendor_match.start(),
                        match_end=window_start + vendor_match.end(),
                        source_document=source_document,
                    )
                    if rel and rel.confidence_score >= _MIN_CONFIDENCE:
                        relationships.append(rel)
                        log.info(
                            "[KINGMAKER] %s → %s | %s | conf=%d | wallet=%.0f%%",
                            rel.titan_ticker, rel.counterparty_name,
                            rel.connection_type, rel.confidence_score,
                            (rel.share_of_wallet_est or 0) * 100,
                        )

        # Deduplicate: keep highest-confidence per (titan, vendor, connection_type)
        relationships = self._deduplicate(relationships)

        return KingmakerBatch(
            source_document=source_document,
            source_type=source_type,  # type: ignore[arg-type]
            relationships=relationships,
            total_chars=len(text),
            elapsed_seconds=round(time.monotonic() - t0, 3),
        )

    def parse_with_unknown_vendors(
        self,
        text: str,
        source_document: str,
        source_type: str = "earnings_call",
    ) -> KingmakerBatch:
        """
        Extended parse that also captures unnamed/unknown vendor entities
        in proximity to titans using NER-style heuristics.

        Returns the same batch type; counterparty_ticker will be None
        for unresolved entities.
        """
        batch = self.parse(text, source_document, source_type)

        # Additionally scan for capitalised entity mentions near titans
        # that are NOT already in our known-candidate list
        for titan_ticker, titan_pattern in self._titan_patterns.items():
            for match in titan_pattern.finditer(text):
                window_start = max(0, match.start() - _WINDOW_CHARS // 2)
                window_end   = min(len(text), match.end() + _WINDOW_CHARS // 2)
                window       = text[window_start:window_end]

                if not self._has_relationship_trigger(window):
                    continue

                for unknown in self._extract_unknown_organisations(window):
                    # Skip if already resolved as a known candidate
                    if unknown.lower() in CANDIDATE_ALIAS_MAP:
                        continue
                    rel = KingmakerRelationship(
                        titan_ticker=titan_ticker,
                        titan_name=self._best_name(titan_ticker, TITANS),
                        counterparty_name=unknown,
                        counterparty_ticker=None,
                        connection_type=self._classify_connection(window),
                        share_of_wallet_est=self._estimate_wallet_share(window),
                        endorsement_flag=self._detect_endorsement(window),
                        endorsement_source=self._extract_speaker(window),
                        confidence_score=3,    # lower baseline for unresolved entities
                        extracted_text=window[:300],
                        source_document=source_document,
                        nlp_model_version=NLP_MODEL_VERSION,
                    )
                    if rel.confidence_score >= _MIN_CONFIDENCE:
                        batch.relationships.append(rel)

        return batch

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_relationship(
        self,
        *,
        text: str,
        window: str,
        window_start: int,
        titan_ticker: str,
        titan_name: str,
        vendor_ticker: str,
        vendor_name: str,
        match_start: int,
        match_end: int,
        source_document: str,
    ) -> Optional[KingmakerRelationship]:
        """Assemble a KingmakerRelationship from a confirmed entity-pair match."""
        connection_type = self._classify_connection(window)
        wallet_share    = self._estimate_wallet_share(window)
        endorsement     = self._detect_endorsement(window)
        speaker         = self._extract_speaker(window) if endorsement else None
        confidence      = self._score_confidence(
            window, wallet_share, endorsement, connection_type
        )

        return KingmakerRelationship(
            titan_ticker=titan_ticker,
            titan_name=titan_name,
            counterparty_name=vendor_name,
            counterparty_ticker=vendor_ticker,
            connection_type=connection_type,
            share_of_wallet_est=wallet_share,
            endorsement_flag=endorsement,
            endorsement_source=speaker,
            confidence_score=confidence,
            extracted_text=window[:500],
            source_document=source_document,
            char_offset_start=match_start,
            char_offset_end=match_end,
            nlp_model_version=NLP_MODEL_VERSION,
        )

    def _classify_connection(self, window: str) -> str:
        """
        Classify the connection type by testing compiled patterns in
        priority order (Custom_Silicon → Equity_Stake → JV_Partner → Supplier).
        """
        for ctype, patterns in COMPILED_CONNECTION_RULES:
            for pat in patterns:
                if pat.search(window):
                    return ctype
        return "Supplier"  # default

    def _estimate_wallet_share(self, window: str) -> Optional[float]:
        """
        Extract wallet share as a 0.0–1.0 float.

        Tries numeric percentage extraction first; falls back to qualitative
        adjective mapping (sole/primary/strategic etc.).
        """
        for pat in WALLET_SHARE_PATTERNS:
            m = pat.search(window)
            if m:
                try:
                    pct = float(m.group(1))
                    return round(min(pct / 100.0, 1.0), 4)
                except (IndexError, ValueError):
                    pass

        # Qualitative fallback
        lower = window.lower()
        for keyword, share in QUALITATIVE_WALLET_MAP.items():
            if keyword in lower:
                return share

        return None

    def _detect_endorsement(self, window: str) -> bool:
        """Return True if a named executive is affirmatively endorsing the vendor."""
        for pat in ENDORSEMENT_PATTERNS:
            if pat.search(window):
                return True
        return False

    def _extract_speaker(self, window: str) -> Optional[str]:
        """Extract the name of the speaker if present in the window."""
        m = SPEAKER_PATTERN.search(window)
        if m:
            first = m.group("first") or ""
            last  = m.group("last")  or ""
            name  = f"{first} {last}".strip()
            return name if name else None
        return None

    def _score_confidence(
        self,
        window: str,
        wallet_share: Optional[float],
        endorsement: bool,
        connection_type: str,
    ) -> int:
        """
        Compute confidence score (1–10) from signal density.

        Scoring logic:
          base     = 3
          +2       wallet share ≥ 0.30
          +1       wallet share present but < 0.30
          +2       endorsement flag
          +1       Custom_Silicon connection type (highest specificity)
          +1       JV_Partner connection type
          +1       relationship trigger count ≥ 2
          capped at 10
        """
        score = 3

        if wallet_share is not None:
            score += 2 if wallet_share >= 0.30 else 1

        if endorsement:
            score += 2

        if connection_type == "Custom_Silicon":
            score += 1
        elif connection_type in ("JV_Partner", "Equity_Stake"):
            score += 1

        trigger_hits = sum(
            1 for p in RELATIONSHIP_TRIGGER_PATTERNS if p.search(window)
        )
        if trigger_hits >= 2:
            score += 1

        return min(score, 10)

    def _has_relationship_trigger(self, window: str) -> bool:
        """Quick pre-filter: at least one relationship keyword must be present."""
        return any(p.search(window) for p in RELATIONSHIP_TRIGGER_PATTERNS)

    def _extract_unknown_organisations(self, window: str) -> list[str]:
        """
        Heuristic: extract capitalised multi-word phrases not in known lists
        as candidate unknown organisations.
        """
        # Pattern: 1-4 capitalised words (handles "Acme Technology Group")
        org_pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b")
        stop_words = {
            "The", "This", "Our", "Their", "Its", "We", "They", "He", "She",
            "In", "On", "At", "For", "With", "By", "From", "To", "And", "Or",
            "As", "An", "A",
        }
        seen: set[str] = set()
        results: list[str] = []
        for m in org_pattern.finditer(window):
            entity = m.group(1).strip()
            if entity not in stop_words and entity not in seen and len(entity) > 3:
                seen.add(entity)
                results.append(entity)
        return results

    def _best_name(self, ticker: str, registry: dict[str, list[str]]) -> str:
        """Return the first (canonical) alias for a ticker."""
        aliases = registry.get(ticker, [ticker])
        return aliases[0]

    def _deduplicate(
        self, relationships: list[KingmakerRelationship]
    ) -> list[KingmakerRelationship]:
        """Keep only the highest-confidence relationship per (titan, vendor, type) triple."""
        best: dict[tuple[str, str, str], KingmakerRelationship] = {}
        for rel in relationships:
            key = (rel.titan_ticker, rel.counterparty_name, rel.connection_type)
            if key not in best or rel.confidence_score > best[key].confidence_score:
                best[key] = rel
        return list(best.values())
