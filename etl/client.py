"""
HTTP client for the Contrarian Radar ETL pipeline.

Wraps all outbound calls to Supabase (REST API + Edge Functions) with:
  - Connection pooling via requests.Session
  - Exponential back-off retry on transient errors
  - Per-source rate limiting
  - Structured logging of every request/response
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from etl.config import (
    HTTP_BACKOFF_FACTOR,
    HTTP_MAX_RETRIES,
    HTTP_STATUS_FORCE_RETRY,
    HTTP_TIMEOUT_SECONDS,
    SUPABASE_PUBLISHABLE_KEY,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
)

log = logging.getLogger(__name__)


def _build_session(max_retries: int, backoff: float, statuses: tuple[int, ...]) -> requests.Session:
    """Create a requests.Session with retry + connection pool configured."""
    session = requests.Session()
    retry = Retry(
        total=max_retries,
        backoff_factor=backoff,
        status_forcelist=list(statuses),
        allowed_methods=["GET", "POST", "PATCH"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class SupabaseClient:
    """
    Thin client over the Supabase REST API and Edge Functions.

    Uses the publishable key for Edge Function calls (anon role at the
    gateway; the function body uses service_role internally).

    Uses the service_role key for direct table inserts so RLS is bypassed
    by the ETL pipeline's own write path.
    """

    def __init__(self) -> None:
        self._session = _build_session(
            HTTP_MAX_RETRIES, HTTP_BACKOFF_FACTOR, HTTP_STATUS_FORCE_RETRY
        )
        self._rest_url = f"{SUPABASE_URL}/rest/v1"
        self._fn_url = f"{SUPABASE_URL}/functions/v1"

        if not SUPABASE_SERVICE_ROLE_KEY:
            log.warning(
                "SUPABASE_SERVICE_ROLE_KEY not set — direct table writes will fail "
                "due to RLS. Set the env var or use Edge Functions for all writes."
            )

    # ── Header factories ──────────────────────────────────────────────────────

    @property
    def _anon_headers(self) -> dict[str, str]:
        """Headers for Edge Function calls (anon / publishable key)."""
        return {
            "apikey": SUPABASE_PUBLISHABLE_KEY,
            "Authorization": f"Bearer {SUPABASE_PUBLISHABLE_KEY}",
            "Content-Type": "application/json",
        }

    @property
    def _service_headers(self) -> dict[str, str]:
        """Headers for direct REST table operations (service role)."""
        key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_PUBLISHABLE_KEY
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    # ── Edge Function calls ───────────────────────────────────────────────────

    def call_edge_function(
        self,
        function_slug: str,
        payload: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        """
        POST to a Supabase Edge Function.

        Returns (http_status_code, response_json).
        Raises on network-level errors after exhausting retries.
        """
        url = f"{self._fn_url}/{function_slug}"
        log.debug("Edge Function POST → %s | payload keys: %s", url, list(payload.keys()))

        resp = self._session.post(
            url,
            json=payload,
            headers=self._anon_headers,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        body: dict[str, Any] = {}
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text}

        if resp.status_code >= 400:
            log.error(
                "Edge Function %s returned %d: %s", function_slug, resp.status_code, body
            )
        else:
            log.debug("Edge Function %s → %d", function_slug, resp.status_code)

        return resp.status_code, body

    # ── REST table operations ─────────────────────────────────────────────────

    def table_insert(
        self,
        table: str,
        row: dict[str, Any],
        on_conflict: Optional[str] = None,
    ) -> tuple[int, Any]:
        """
        INSERT (or UPSERT) a single row into a Supabase table via REST API.

        on_conflict: comma-separated column names for ON CONFLICT DO UPDATE.
        Returns (http_status_code, response_body).
        """
        url = f"{self._rest_url}/{table}"
        headers = dict(self._service_headers)
        if on_conflict:
            headers["Prefer"] = f"return=representation,resolution=merge-duplicates"
            url += f"?on_conflict={on_conflict}"

        log.debug("REST INSERT → %s", table)
        resp = self._session.post(
            url,
            json=row,
            headers=headers,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        body: Any = None
        try:
            body = resp.json()
        except Exception:
            body = resp.text

        if resp.status_code >= 400:
            log.error("REST INSERT %s → %d: %s", table, resp.status_code, body)

        return resp.status_code, body

    def table_select(
        self,
        table: str,
        filters: Optional[dict[str, Any]] = None,
        columns: str = "*",
        limit: int = 100,
    ) -> tuple[int, list[dict[str, Any]]]:
        """
        SELECT from a Supabase table via REST API.

        filters: dict of {column: value} applied as equality filters.
        Uses service headers so RLS authenticated reads work.
        """
        url = f"{self._rest_url}/{table}?select={columns}&limit={limit}"
        if filters:
            for col, val in filters.items():
                url += f"&{col}=eq.{val}"

        resp = self._session.get(
            url,
            headers=self._service_headers,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        try:
            return resp.status_code, resp.json()
        except Exception:
            return resp.status_code, []

    def rpc(self, function_name: str, params: dict[str, Any]) -> tuple[int, Any]:
        """
        Call a Postgres function via Supabase PostgREST RPC endpoint.
        """
        url = f"{self._rest_url}/rpc/{function_name}"
        resp = self._session.post(
            url,
            json=params,
            headers=self._service_headers,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        try:
            return resp.status_code, resp.json()
        except Exception:
            return resp.status_code, resp.text


class RateLimitedHTTPClient:
    """
    General-purpose HTTP client for scraping external sources.

    Enforces a minimum inter-request interval to avoid hitting rate limits
    on SEC EDGAR, FCA Register, and financial news feeds.
    """

    def __init__(self, requests_per_second: float = 2.0) -> None:
        self._session = _build_session(
            HTTP_MAX_RETRIES, HTTP_BACKOFF_FACTOR, HTTP_STATUS_FORCE_RETRY
        )
        self._min_interval = 1.0 / max(requests_per_second, 0.1)
        self._last_request_at: float = 0.0

        # SEC requires a descriptive User-Agent per Fair Access Policy
        self._session.headers.update({
            "User-Agent": (
                "Contrarian-Radar-ETL/1.0 "
                "(Investment Intelligence Research; contact@contrarian-radar.io)"
            ),
            "Accept": "application/json, text/html",
        })

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """Rate-limited GET request."""
        self._throttle()
        log.debug("External GET → %s", url)
        return self._session.get(url, timeout=HTTP_TIMEOUT_SECONDS, **kwargs)

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_at = time.monotonic()
