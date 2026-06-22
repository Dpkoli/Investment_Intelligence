"""
FCA UK Crypto 2026/2027 Regulatory Checkpoints

Hardcoded timeline derived from the Financial Services and Markets Act 2000
(Cryptoassets) Regulations 2026 as communicated in FCA CP23/28, PS24/12,
and the HM Treasury consultation "Future Financial Services Regulatory Regime
for Cryptoassets" (October 2023).

Timeline Summary
────────────────
  Sep 30 2026   FCA Part 4A Gateway opens.
                All firms wishing to carry on regulated cryptoasset activities
                (operating a crypto exchange, custody, stablecoin issuance,
                crypto lending) must submit a Variation of Permission (VoP)
                or a new Part 4A application by this date to retain the right
                to operate during the interim period.

  Feb 28 2027   FCA Gateway closes.
                No new applications accepted after this date under the
                transitional provisions.  Firms that missed the window must
                cease regulated cryptoasset activity immediately.

  Oct 25 2027   Hard Enforcement Cliff.
                All interim authorisations expire.  Only firms holding a
                confirmed Part 4A FSMA cryptoasset authorisation may legally
                operate.  Criminal penalties under s.23 FSMA apply to
                unauthorised activity from this date.

Reference:
  https://www.fca.org.uk/publications/policy-statements/ps24-12-cryptoassets
  https://www.legislation.gov.uk/uksi/2024/xxx (illustrative placeholder)
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from analytics.compliance.models import CompliancePhase

# ── Checkpoint dates (hardcoded per regulation) ───────────────────────────────

GATEWAY_OPEN_DATE:  date = date(2026, 9, 30)
GATEWAY_CLOSE_DATE: date = date(2027, 2, 28)
ENFORCEMENT_DATE:   date = date(2027, 10, 25)


# ── Phase resolution ──────────────────────────────────────────────────────────

def current_phase(reference: Optional[date] = None) -> CompliancePhase:
    """
    Return the regulatory phase name for a given reference date.

    Args:
        reference: Date to evaluate.  Defaults to today.
    """
    d = reference or date.today()

    if d < GATEWAY_OPEN_DATE:
        return "PRE_GATEWAY"
    elif d <= GATEWAY_CLOSE_DATE:
        return "GATEWAY_OPEN"
    elif d < ENFORCEMENT_DATE:
        return "POST_GATEWAY"
    else:
        return "ENFORCEMENT_CLIFF"


# ── Countdown helpers ─────────────────────────────────────────────────────────

def days_to_gateway_open(reference: Optional[date] = None) -> Optional[int]:
    """Days until the gateway opens; None if already open."""
    d = reference or date.today()
    if d < GATEWAY_OPEN_DATE:
        return (GATEWAY_OPEN_DATE - d).days
    return None


def days_to_gateway_close(reference: Optional[date] = None) -> Optional[int]:
    """Days until the gateway closes; None if already closed."""
    d = reference or date.today()
    if d <= GATEWAY_CLOSE_DATE:
        return (GATEWAY_CLOSE_DATE - d).days
    return None


def days_to_enforcement(reference: Optional[date] = None) -> Optional[int]:
    """Days until the hard enforcement cliff; None if past."""
    d = reference or date.today()
    if d < ENFORCEMENT_DATE:
        return (ENFORCEMENT_DATE - d).days
    return None


# ── Phase narrative helpers ───────────────────────────────────────────────────

_PHASE_NARRATIVES: dict[CompliancePhase, str] = {
    "PRE_GATEWAY": (
        "Preparation window. Firms should be assessing regulated activities, "
        "reviewing Financial Promotions regime compliance, and preparing Part 4A "
        "or VoP applications ahead of the September 30 2026 gateway opening."
    ),
    "GATEWAY_OPEN": (
        "GATEWAY IS OPEN. Firms must submit Part 4A authorisation or Variation of "
        "Permission applications NOW. Missing this window means ceasing regulated "
        "cryptoasset activity after Feb 28 2027 without any transitional protection."
    ),
    "POST_GATEWAY": (
        "Gateway is closed. Firms with applications submitted by Feb 28 2027 "
        "benefit from interim transitional provisions and may continue operating "
        "while the FCA processes applications. Firms that missed the gateway must "
        "have already ceased regulated cryptoasset activities."
    ),
    "ENFORCEMENT_CLIFF": (
        "HARD ENFORCEMENT IN EFFECT. Only firms with confirmed Part 4A FSMA "
        "cryptoasset authorisation may operate. Criminal penalties under s.23 FSMA "
        "apply to any firm conducting unauthorised regulated cryptoasset activity."
    ),
}


def phase_narrative(phase: CompliancePhase) -> str:
    return _PHASE_NARRATIVES[phase]


# ── Specific regulatory obligation calendar ───────────────────────────────────

REGULATORY_MILESTONES: list[dict] = [
    {
        "date":  date(2025, 1, 1),
        "label": "UK Cryptoasset Financial Promotions Regime — fully live",
        "detail": (
            "All crypto communications to UK consumers must comply with FCA "
            "Financial Promotions rules (s.21 FSMA).  Firms must be FCA-registered "
            "or approved by an authorised person."
        ),
    },
    {
        "date":  date(2026, 1, 1),
        "label": "Stablecoin issuance regime expected commencement",
        "detail": (
            "HM Treasury expects the FCA stablecoin-specific authorisation "
            "requirements to take effect, requiring issuers of systemic fiat-backed "
            "stablecoins to hold e-money or payment institution authorisation."
        ),
    },
    {
        "date":  GATEWAY_OPEN_DATE,
        "label": "FCA Part 4A Cryptoasset Gateway Opens",
        "detail": (
            "Firms may begin submitting Part 4A FSMA applications and Variations "
            "of Permission for regulated cryptoasset activities including exchange "
            "operation, custody, and lending."
        ),
    },
    {
        "date":  date(2026, 12, 1),
        "label": "FCA target: 50% of complete applications assessed",
        "detail": (
            "FCA service-level target for initial assessment of complete applications. "
            "Incomplete applications returned without prejudice to re-submission."
        ),
    },
    {
        "date":  GATEWAY_CLOSE_DATE,
        "label": "FCA Part 4A Gateway Closes — HARD DEADLINE",
        "detail": (
            "Last date to submit applications under transitional provisions. "
            "Firms not in the queue by this date must cease regulated activity "
            "with immediate effect."
        ),
    },
    {
        "date":  date(2027, 6, 30),
        "label": "FCA target: all complete applications decided",
        "detail": (
            "FCA aspiration to clear the authorisation backlog by end of Q2 2027 "
            "to allow orderly market transition before the enforcement cliff."
        ),
    },
    {
        "date":  ENFORCEMENT_DATE,
        "label": "Hard Enforcement Cliff — s.23 FSMA criminal liability",
        "detail": (
            "All interim transitional protections expire. Only firms holding "
            "confirmed Part 4A authorisation may conduct regulated cryptoasset "
            "activities. s.23 FSMA imposes up to 2 years' imprisonment for "
            "unauthorised regulated activity."
        ),
    },
]


def upcoming_milestones(
    reference: Optional[date] = None,
    n: int = 3,
) -> list[dict]:
    """Return the next `n` milestones from a reference date."""
    d = reference or date.today()
    future = [m for m in REGULATORY_MILESTONES if m["date"] >= d]
    return future[:n]
