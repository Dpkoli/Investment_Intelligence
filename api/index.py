"""
Vercel Serverless Entry Point — Contrarian Radar

Architecture note
─────────────────
Vercel's @vercel/python runtime executes short-lived WSGI functions, which is
architecturally mismatched with Streamlit's persistent WebSocket server model.

This module bridges the gap with a two-layer strategy:

  Layer 1 — Subprocess launcher
    On cold start (module import), Streamlit is spawned as a background
    process on localhost:8080.  A threading.Event gate blocks proxy calls
    until Streamlit's health endpoint responds 200.

  Layer 2 — HTTP reverse proxy (Flask WSGI)
    All inbound Vercel requests are forwarded to the local Streamlit process
    via requests.  HTTP responses (HTML, JS, CSS, static assets, REST-style
    _stcore/ API calls) are streamed back transparently.

WebSocket constraint
─────────────────────
Vercel Hobby functions do NOT support persistent WebSocket connections.
Streamlit's interactive state updates travel over WebSocket (/_stcore/stream).
On Vercel Hobby this means:
  • The initial page loads (HTML shell + static JS/CSS) ✓
  • Static metric displays (Zone 3 table, asset grids) ✓
  • Live interactive callbacks (slider changes, tab switches) ✗

For full interactive parity, deploy on one of:
  • Streamlit Community Cloud  https://streamlit.io/cloud  (free, purpose-built)
  • Railway.app                https://railway.app         (persistent server, ~$5/mo)
  • Render.com                 https://render.com          (free tier available)
  • Google Cloud Run           (container, pay-per-use)

Vercel Hobby/Pro IS fully adequate for:
  • Serving the pre-rendered dashboard HTML for read-only embedding
  • Hosting the What-If CS Simulator (pure Python re-calc, no WebSocket needed
    if wired to a separate /api/score endpoint — see /api/score below)
  • Serving static asset bundles cached at the CDN edge
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from typing import Optional

import requests as _req
from flask import Flask, Response, request, stream_with_context

# ── Constants ─────────────────────────────────────────────────────────────────

_REPO_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_SCRIPT  = os.path.join(_REPO_ROOT, "app", "streamlit_app.py")
_ST_PORT     = int(os.environ.get("STREAMLIT_SERVER_PORT", "8080"))
_ST_BASE_URL = f"http://127.0.0.1:{_ST_PORT}"
_STARTUP_TIMEOUT = 45   # seconds to wait for Streamlit ready signal
_HEALTH_ENDPOINT = f"{_ST_BASE_URL}/_stcore/health"

log = logging.getLogger("contrarian_radar.vercel")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Streamlit process management ──────────────────────────────────────────────

_st_process: Optional[subprocess.Popen] = None
_st_ready   = threading.Event()
_st_lock    = threading.Lock()


def _launch_streamlit() -> None:
    """Spawn Streamlit as a background subprocess and signal when ready."""
    global _st_process

    cmd = [
        sys.executable, "-m", "streamlit", "run", _APP_SCRIPT,
        "--server.port",                  str(_ST_PORT),
        "--server.address",               "127.0.0.1",
        "--server.headless",              "true",
        "--server.enableCORS",            "false",
        "--server.enableXsrfProtection",  "false",
        "--server.fileWatcherType",       "none",
        "--browser.gatherUsageStats",     "false",
    ]

    env = {**os.environ, "PYTHONPATH": _REPO_ROOT}
    log.info("Launching Streamlit: %s", " ".join(cmd))

    _st_process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Poll health endpoint until Streamlit is ready or timeout
    deadline = time.monotonic() + _STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        # Check the subprocess is still alive
        if _st_process.poll() is not None:
            out, _ = _st_process.communicate()
            log.error("Streamlit exited early: %s", out)
            return

        try:
            r = _req.get(_HEALTH_ENDPOINT, timeout=2)
            if r.status_code == 200:
                log.info("Streamlit ready on port %d", _ST_PORT)
                _st_ready.set()
                return
        except _req.exceptions.ConnectionError:
            pass

        time.sleep(1)

    log.error("Streamlit did not become ready within %ds", _STARTUP_TIMEOUT)


def _ensure_streamlit() -> None:
    """Start Streamlit exactly once per process lifetime."""
    with _st_lock:
        if not _st_ready.is_set():
            t = threading.Thread(target=_launch_streamlit, daemon=True)
            t.start()


# Launch immediately on module import (Vercel imports the module on cold start)
_ensure_streamlit()

# ── Flask WSGI app ────────────────────────────────────────────────────────────

app = Flask(__name__)


@app.route("/api/health")
def api_health():
    """Liveness probe for Vercel health checks and uptime monitors."""
    st_up = _st_ready.is_set()
    return {"status": "ok", "streamlit_ready": st_up}, 200 if st_up else 503


@app.route("/api/score", methods=["POST"])
def api_score():
    """
    Stateless CS score endpoint — fully serverless-compatible.

    POST body (JSON):
        { "pv": 6.5, "ti": 0.35, "sum_rs": 18.0,
          "em": 8.0, "kw": 2.5, "cc": 0.18,
          "asset_name": "MRVL" }

    Returns:
        { "cs": 34.13, "is_asymmetry_play": true,
          "is_cassandra_risk": false, "is_kingmaker_endorsed": true }

    This endpoint powers the What-If Simulator without requiring WebSocket
    connectivity — wire the Streamlit sidebar to call /api/score via
    st.session_state + requests for a fully serverless-safe experience.
    """
    # Late import to avoid slow cold-start on non-score requests
    from analytics.scoring import ScoringEngine, CSComponents  # noqa: PLC0415

    body = request.get_json(force=True, silent=True) or {}
    try:
        comp = CSComponents(
            asset_id=0,
            asset_name=body.get("asset_name", "Unknown"),
            pv=float(body.get("pv", 0)),
            ti=float(body.get("ti", 0)),
            sum_rs=float(body.get("sum_rs", 0)),
            em=float(body.get("em", 0)),
            kw=float(body.get("kw", 1.0)),
            cc=float(body.get("cc", 0)),
        )
        result = ScoringEngine().score_components(comp)
        return {
            "cs":                    result.cs,
            "is_asymmetry_play":     result.is_asymmetry_play,
            "is_cassandra_risk":     result.is_cassandra_risk,
            "is_kingmaker_endorsed": result.is_kingmaker_endorsed,
        }, 200
    except Exception as exc:
        return {"error": str(exc)}, 400


@app.route("/api/compliance")
def api_compliance():
    """
    Stateless FCA compliance snapshot — fully serverless-compatible.

    Query params:
        ?date=2027-03-01   (optional; defaults to today)

    Returns the survival_flag dict for all 19 tracked instruments.
    """
    from datetime import date  # noqa: PLC0415
    from analytics.compliance.uk_crypto_matrix import UKCryptoComplianceMatrix  # noqa: PLC0415

    date_str = request.args.get("date")
    ref = None
    if date_str:
        try:
            ref = date.fromisoformat(date_str)
        except ValueError:
            return {"error": "invalid date format; use YYYY-MM-DD"}, 400

    matrix = UKCryptoComplianceMatrix()
    report = matrix.generate(reference_date=ref)
    return {
        "reference_date": str(report.reference_date),
        "current_phase":  report.current_phase,
        "summary": {
            "green":    report.green_count,
            "amber":    report.amber_count,
            "red":      report.red_count,
            "critical": report.critical_count,
        },
        "instruments": {
            r.instrument_id: {
                "name":         r.instrument_name,
                "flag":         r.survival_flag,
                "auth_status":  r.auth_status,
                "next_action":  r.next_action,
                "deadline":     str(r.deadline) if r.deadline else None,
            }
            for r in report.reports
        },
    }, 200


# ── Streamlit reverse proxy ───────────────────────────────────────────────────

_PROXY_SKIP_HEADERS = {
    "content-encoding", "transfer-encoding",
    "connection", "keep-alive", "upgrade",
}


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def proxy(path: str) -> Response:
    """
    Reverse proxy: forward every inbound request to the local Streamlit server.

    On first request after cold start this blocks until Streamlit is ready
    (up to _STARTUP_TIMEOUT seconds).  Subsequent requests skip the wait.
    """
    if not _st_ready.wait(timeout=_STARTUP_TIMEOUT):
        return Response(
            _cold_start_page(),
            status=503,
            mimetype="text/html",
        )

    target_url = f"{_ST_BASE_URL}/{path}"
    # Preserve query string
    if request.query_string:
        target_url += "?" + request.query_string.decode()

    # Strip hop-by-hop headers before forwarding
    fwd_headers = {
        k: v for k, v in request.headers
        if k.lower() not in ("host", "connection", "upgrade")
    }

    try:
        upstream = _req.request(
            method=request.method,
            url=target_url,
            headers=fwd_headers,
            data=request.get_data(),
            stream=True,
            timeout=55,       # stay under Vercel Pro's 60s function timeout
            allow_redirects=False,
        )
    except _req.exceptions.RequestException as exc:
        log.error("Proxy error for %s: %s", path, exc)
        return Response(f"Upstream error: {exc}", status=502)

    # Build response, stripping headers that conflict with Flask/Vercel
    resp_headers = {
        k: v for k, v in upstream.headers.items()
        if k.lower() not in _PROXY_SKIP_HEADERS
    }

    return Response(
        stream_with_context(upstream.iter_content(chunk_size=8192)),
        status=upstream.status_code,
        headers=resp_headers,
        direct_passthrough=True,
    )


def _cold_start_page() -> str:
    """HTML page shown while Streamlit is starting up on cold start."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="5">
<title>Contrarian Radar — Starting…</title>
<style>
  body { background:#0E1117; color:#FAFAFA; font-family:sans-serif;
         display:flex; align-items:center; justify-content:center;
         height:100vh; margin:0; flex-direction:column; gap:1rem; }
  .spinner { width:48px; height:48px; border:4px solid #2E3140;
             border-top-color:#00D4AA; border-radius:50%;
             animation:spin 0.9s linear infinite; }
  @keyframes spin { to { transform:rotate(360deg); } }
  p { color:#888; font-size:0.9rem; }
</style>
</head>
<body>
  <div class="spinner"></div>
  <h2 style="color:#00D4AA">📡 Contrarian Radar</h2>
  <p>Cold start in progress — Streamlit is initialising…</p>
  <p style="font-size:0.78rem">This page will refresh automatically.</p>
</body>
</html>"""


# ── Vercel WSGI handler ───────────────────────────────────────────────────────
# Vercel's @vercel/python runtime looks for a module-level callable named
# `handler` OR a WSGI app named `app`.  Both are exported here.

handler = app
