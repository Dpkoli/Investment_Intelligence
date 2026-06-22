"""
Regulatory Sandbox — UK FSMA 2026/2027 FCA countdown matrix.
Wraps analytics.compliance and adds structured accessor helpers
for the Streamlit module renderer.
"""
from __future__ import annotations

import sys
import os
from datetime import date
from typing import Any, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from analytics.compliance.fca_checkpoints import (
    GATEWAY_OPEN_DATE,
    GATEWAY_CLOSE_DATE,
    ENFORCEMENT_DATE,
    current_phase,
    days_to_gateway_open,
    days_to_gateway_close,
    days_to_enforcement,
    phase_narrative,
    upcoming_milestones,
)
from analytics.compliance.uk_crypto_matrix import UKCryptoComplianceMatrix


def get_compliance_data(reference_date: Optional[date] = None) -> Any:
    """Generate the full compliance matrix (cached externally via st.cache_data)."""
    matrix = UKCryptoComplianceMatrix()
    return matrix.generate(reference_date=reference_date)


def get_phase_summary(ref: Optional[date] = None) -> dict:
    """Return a flat dict of timeline state for the dashboard header."""
    today = ref or date.today()
    return {
        "today": today,
        "phase": current_phase(today),
        "phase_narrative": phase_narrative(today),
        "days_to_gateway_open":  days_to_gateway_open(today),
        "days_to_gateway_close": days_to_gateway_close(today),
        "days_to_enforcement":   days_to_enforcement(today),
        "gateway_open":   GATEWAY_OPEN_DATE,
        "gateway_close":  GATEWAY_CLOSE_DATE,
        "enforcement":    ENFORCEMENT_DATE,
        "milestones":     upcoming_milestones(today),
    }
