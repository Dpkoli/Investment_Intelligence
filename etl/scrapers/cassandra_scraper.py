"""
Cassandra Pipeline Scraper

Scans financial blogs, alternative media, and regulatory feeds for signals
of systemic risk across three risk vectors:
  - AI / Data-Centre Energy Grid Constraints
  - Crypto Custody & Counterparty Centralisation
  - Macro Systemic Risk (leverage unwinds, geopolitical shocks)

Pipeline:
  seed URLs
    → rate-limited HTTP GET
    → BeautifulSoup HTML → plain text
    → run ALL_RISK_TRIGGERS against text
    → apply SEVERITY_AMPLIFIERS
    → normalise raw score → 1-10
    → return CassandraSignalPayload list
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore[assignment,misc]

from etl.client import RateLimitedHTTPClient
from etl.models import CassandraScrapeBatch, CassandraSignalPayload
from etl.parsers.nlp_patterns import (
    ALL_RISK_TRIGGERS,
    SEVERITY_AMPLIFIERS,
)

log = logging.getLogger(__name__)

# Default seed sources (public financial news / risk blogs)
DEFAULT_SEED_URLS: list[str] = [
    # Energy / AI infrastructure risk
    "https://www.energymonitor.ai/tech/data-centres/",
    "https://www.datacenterknowledge.com/",
    # Crypto custody / counterparty
    "https://protos.com/",
    "https://www.theblock.co/",
    # Macro / systemic
    "https://wolfstreet.com/",
    "https://www.zerohedge.com/markets",
]

# Snippet length to store as extracted_text
_SNIPPET_CHARS = 600

# Paragraph block tags to extract text from
_BLOCK_TAGS = ["p", "h1", "h2", "h3", "li", "blockquote"]


@dataclass
class _ArticleCandidate:
    url: str
    title: str
    body: str


class CassandraPipelineScraper:
    """
    Scrapes a list of seed URLs, scores textual content against risk triggers,
    and returns CassandraSignalPayload objects ready for the signal-submit Edge Function.

    Usage::

        scraper = CassandraPipelineScraper(seed_urls=[...])
        batch   = scraper.scrape()
        for signal in batch.signals:
            print(signal.risk_score, signal.title)
    """

    def __init__(
        self,
        seed_urls: Optional[list[str]] = None,
        requests_per_second: float = 1.5,
        min_risk_score: int = 3,
    ) -> None:
        if BeautifulSoup is None:
            raise RuntimeError(
                "beautifulsoup4 is required: pip install beautifulsoup4 lxml"
            )
        self._urls = seed_urls if seed_urls is not None else DEFAULT_SEED_URLS
        self._http = RateLimitedHTTPClient(requests_per_second=requests_per_second)
        self._min_risk_score = min_risk_score

    # ── Public API ────────────────────────────────────────────────────────────

    def scrape(self, source_label: str = "web_scrape") -> CassandraScrapeBatch:
        """
        Scrape all seed URLs and return a CassandraScrapeBatch.

        Args:
            source_label: Human-readable label stored in batch.source_url.
        """
        t0 = time.monotonic()
        signals: list[CassandraSignalPayload] = []

        for url in self._urls:
            try:
                articles = self._fetch_articles(url)
            except Exception as exc:
                log.warning("Failed to fetch %s: %s", url, exc)
                continue

            for article in articles:
                payload = self._score_article(article)
                if payload and payload.risk_score >= self._min_risk_score:
                    signals.append(payload)
                    log.info(
                        "[CASSANDRA] score=%d | vector=%s | %s",
                        payload.risk_score,
                        payload.risk_vector,
                        article.title[:80],
                    )

        log.info(
            "[CASSANDRA] scrape complete: %d signals from %d URLs in %.1fs",
            len(signals),
            len(self._urls),
            time.monotonic() - t0,
        )

        return CassandraScrapeBatch(
            source_url=source_label,
            signals=signals,
            elapsed_seconds=round(time.monotonic() - t0, 3),
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _fetch_articles(self, url: str) -> list[_ArticleCandidate]:
        """Fetch a page, parse HTML, return list of article candidates."""
        resp = self._http.get(url)
        if resp.status_code != 200:
            log.warning("HTTP %d for %s", resp.status_code, url)
            return []

        soup = BeautifulSoup(resp.text, "lxml")

        # Remove boilerplate nodes
        for tag in soup(["script", "style", "nav", "footer", "aside", "header"]):
            tag.decompose()

        # Try to find article blocks; fall back to whole body
        articles: list[_ArticleCandidate] = []
        article_nodes = soup.find_all(["article", "section"]) or [soup.body]
        for node in article_nodes[:10]:  # cap per page
            if not node:
                continue
            title = self._extract_title(node, soup)
            body  = self._extract_body(node)
            if len(body) < 100:
                continue
            articles.append(_ArticleCandidate(url=url, title=title, body=body))

        return articles

    def _extract_title(self, node, soup) -> str:
        h = node.find(["h1", "h2"])
        if h:
            return h.get_text(separator=" ", strip=True)
        title_tag = soup.find("title")
        return title_tag.get_text(strip=True) if title_tag else urlparse(node.name).path

    def _extract_body(self, node) -> str:
        parts = []
        for tag in node.find_all(_BLOCK_TAGS):
            txt = tag.get_text(separator=" ", strip=True)
            if txt:
                parts.append(txt)
        return " ".join(parts)

    def _score_article(self, article: _ArticleCandidate) -> Optional[CassandraSignalPayload]:
        """
        Score article body against ALL_RISK_TRIGGERS.

        Returns None if no triggers fire.
        """
        text  = article.title + " " + article.body
        lower = text.lower()

        raw_score        = 0.0
        triggered        : list[str] = []
        dominant_vector  = "systemic_risk"
        vector_weights   : dict[str, float] = {}

        for trigger in ALL_RISK_TRIGGERS:
            if trigger.pattern.search(lower):
                raw_score += trigger.base_weight
                triggered.append(trigger.pattern.pattern[:60])
                prev = vector_weights.get(trigger.risk_vector, 0.0)
                vector_weights[trigger.risk_vector] = prev + trigger.base_weight

        if not triggered:
            return None

        # Severity amplifiers
        multiplier = 1.0
        for amp_pat, amp_factor in SEVERITY_AMPLIFIERS:
            if amp_pat.search(lower):
                multiplier = max(multiplier, amp_factor)

        raw_score *= multiplier

        # Normalise to 1-10 (sigmoid-style clamp: 10 maps ≈ raw ≥ 8.0)
        risk_score = max(1, min(10, round(raw_score)))

        # Dominant risk vector by weight
        if vector_weights:
            dominant_vector = max(vector_weights, key=vector_weights.get)  # type: ignore[arg-type]

        snippet = (article.title + " — " + article.body)[:_SNIPPET_CHARS]

        return CassandraSignalPayload(
            title=article.title[:200] or "Untitled",
            text=snippet,
            risk_score=risk_score,
            signal_source="Anonymous_Filing",
            risk_vector=dominant_vector,
            source_url=article.url,
            triggered_keywords=triggered[:20],
            raw_severity_score=round(raw_score, 4),
        )
