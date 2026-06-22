"""
UK Crypto 2026/2027 Regulatory Timeline Matrix

Tracks live LSE-listed ETPs and spot crypto networks against the FCA
cryptoasset authorisation regime.  Produces per-instrument compliance
health reports and a full ranked matrix.

Covered instruments (initial universe)
──────────────────────────────────────
  LSE ETPs:
    IB1T  — iShares Bitcoin ETP (BlackRock)
    BITB  — CoinShares Physical Bitcoin ETP
    WBTC  — WisdomTree Physical Bitcoin
    WETH  — WisdomTree Physical Ethereum
    ETHE  — CoinShares Physical Ethereum ETP
    SOLW  — WisdomTree Physical Solana
    XRPL  — WisdomTree Physical XRP

  Spot crypto networks:
    BTC   — Bitcoin
    ETH   — Ethereum
    SOL   — Solana
    XRP   — Ripple / XRP Ledger

  Stablecoins:
    USDT  — Tether (USD₮)
    USDC  — USD Coin (Circle)
    GBPT  — Tether GBP (GBP-pegged)

  Asset managers (entity-level compliance):
    BLACKROCK   — BlackRock (iShares)
    COINSHARES  — CoinShares International
    WISDOMTREE  — WisdomTree Investments
    INVESCO     — Invesco (Invesco Physical range)
    21SHARES    — 21Shares AG
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from analytics.compliance.fca_checkpoints import (
    ENFORCEMENT_DATE,
    GATEWAY_CLOSE_DATE,
    GATEWAY_OPEN_DATE,
    current_phase,
    days_to_enforcement,
    days_to_gateway_close,
    days_to_gateway_open,
    phase_narrative,
    upcoming_milestones,
)
from analytics.compliance.models import (
    AuthorisationStatus,
    ComplianceHealthReport,
    ComplianceMatrix,
    CompliancePhase,
    SurvivalFlag,
    TrackedInstrument,
)

log = logging.getLogger(__name__)


# ── Static instrument registry ────────────────────────────────────────────────
# auth_status and fca_ref are updated as authorisations are granted.
# This table represents the state at the time of code publication (June 2026).

_INSTRUMENT_REGISTRY: list[TrackedInstrument] = [
    # ── LSE ETPs ──────────────────────────────────────────────────────────────
    TrackedInstrument(
        id="IB1T", name="iShares Bitcoin ETP", category="LSE_ETP",
        ticker="IB1T", isin="XS2572544272", issuer="BlackRock",
        exchange="LSE", domicile="IE",
        auth_status="Registered_Only",
        aum_gbp_mm=3_200.0, daily_vol_gbp_mm=45.0,
        has_retail_access=True,
    ),
    TrackedInstrument(
        id="BITB", name="CoinShares Physical Bitcoin", category="LSE_ETP",
        ticker="BITB", isin="GB00BLD4ZL17", issuer="CoinShares",
        exchange="LSE", domicile="JE",
        auth_status="Registered_Only",
        aum_gbp_mm=890.0, daily_vol_gbp_mm=12.0,
        has_retail_access=True,
    ),
    TrackedInstrument(
        id="WBTC", name="WisdomTree Physical Bitcoin", category="LSE_ETP",
        ticker="WBTC", isin="GB00BJYDH753", issuer="WisdomTree",
        exchange="LSE", domicile="IE",
        auth_status="Registered_Only",
        aum_gbp_mm=680.0, daily_vol_gbp_mm=8.5,
        has_retail_access=True,
    ),
    TrackedInstrument(
        id="WETH", name="WisdomTree Physical Ethereum", category="LSE_ETP",
        ticker="WETH", isin="GB00BJYDH860", issuer="WisdomTree",
        exchange="LSE", domicile="IE",
        auth_status="Registered_Only",
        aum_gbp_mm=240.0, daily_vol_gbp_mm=3.2,
        has_retail_access=True,
    ),
    TrackedInstrument(
        id="ETHE", name="CoinShares Physical Ethereum", category="LSE_ETP",
        ticker="ETHE", isin="GB00BLD4ZM24", issuer="CoinShares",
        exchange="LSE", domicile="JE",
        auth_status="Registered_Only",
        aum_gbp_mm=310.0, daily_vol_gbp_mm=4.1,
        has_retail_access=True,
    ),
    TrackedInstrument(
        id="SOLW", name="WisdomTree Physical Solana", category="LSE_ETP",
        ticker="SOLW", isin="GB00BMWC6Y65", issuer="WisdomTree",
        exchange="LSE", domicile="IE",
        auth_status="Not_Started",
        aum_gbp_mm=95.0, daily_vol_gbp_mm=1.8,
        has_retail_access=True,
    ),
    TrackedInstrument(
        id="XRPL", name="WisdomTree Physical XRP", category="LSE_ETP",
        ticker="XRPL", isin="GB00BMWC6Z72", issuer="WisdomTree",
        exchange="LSE", domicile="IE",
        auth_status="Not_Started",
        aum_gbp_mm=42.0, daily_vol_gbp_mm=0.9,
        has_retail_access=True,
    ),
    # ── Spot crypto networks ──────────────────────────────────────────────────
    TrackedInstrument(
        id="BTC", name="Bitcoin", category="Spot_Crypto",
        ticker="BTC", domicile="—",
        auth_status="Not_Started",
        has_retail_access=True,
    ),
    TrackedInstrument(
        id="ETH", name="Ethereum", category="Spot_Crypto",
        ticker="ETH", domicile="—",
        auth_status="Not_Started",
        has_retail_access=True,
    ),
    TrackedInstrument(
        id="SOL", name="Solana", category="Spot_Crypto",
        ticker="SOL", domicile="—",
        auth_status="Not_Started",
        has_retail_access=True,
    ),
    TrackedInstrument(
        id="XRP", name="XRP (Ripple)", category="Spot_Crypto",
        ticker="XRP", domicile="—",
        auth_status="Not_Started",
        has_retail_access=True,
    ),
    # ── Stablecoins ───────────────────────────────────────────────────────────
    TrackedInstrument(
        id="USDT", name="Tether USD (USDT)", category="Stablecoin",
        ticker="USDT", issuer="Tether Operations Ltd", domicile="BVI",
        auth_status="Not_Started",
        has_retail_access=True,
    ),
    TrackedInstrument(
        id="USDC", name="USD Coin (USDC)", category="Stablecoin",
        ticker="USDC", issuer="Circle Internet Financial", domicile="US",
        auth_status="Not_Started",
        has_retail_access=True,
    ),
    TrackedInstrument(
        id="GBPT", name="Tether GBP (GBPT)", category="Stablecoin",
        ticker="GBPT", issuer="Tether Operations Ltd", domicile="BVI",
        auth_status="Not_Started",
        has_retail_access=True,
    ),
    # ── Asset managers ────────────────────────────────────────────────────────
    TrackedInstrument(
        id="BLACKROCK", name="BlackRock / iShares", category="Asset_Manager",
        issuer="BlackRock Inc.", domicile="GB",
        fca_ref="119030",
        auth_status="Registered_Only",
        has_retail_access=True,
    ),
    TrackedInstrument(
        id="COINSHARES", name="CoinShares International Ltd", category="Asset_Manager",
        issuer="CoinShares International Ltd", domicile="JE",
        fca_ref="928067",
        auth_status="Registered_Only",
        has_retail_access=True,
    ),
    TrackedInstrument(
        id="WISDOMTREE", name="WisdomTree Investments (UK)", category="Asset_Manager",
        issuer="WisdomTree Europe Ltd", domicile="GB",
        fca_ref="707137",
        auth_status="Registered_Only",
        has_retail_access=True,
    ),
    TrackedInstrument(
        id="INVESCO", name="Invesco (UK)", category="Asset_Manager",
        issuer="Invesco Asset Management Ltd", domicile="GB",
        fca_ref="119223",
        auth_status="Registered_Only",
        has_retail_access=True,
    ),
    TrackedInstrument(
        id="21SHARES", name="21Shares AG", category="Asset_Manager",
        issuer="21Shares AG", domicile="CH",
        auth_status="Not_Started",
        has_retail_access=True,
    ),
]

# Quick lookup by id
_REGISTRY_MAP: dict[str, TrackedInstrument] = {
    inst.id: inst for inst in _INSTRUMENT_REGISTRY
}


class UKCryptoComplianceMatrix:
    """
    Computes and tracks FCA regulatory compliance for UK-facing crypto instruments.

    Usage::

        matrix = UKCryptoComplianceMatrix()

        # Full matrix for today
        report = matrix.generate()
        for r in report.red_or_critical:
            print(r.instrument_id, r.survival_flag, r.risk_narrative)

        # Single instrument health check
        health = matrix.check("IB1T")

        # Time-travel: assess state on a future date
        future = matrix.generate(reference_date=date(2027, 3, 1))

        # Filter: only critical instruments at enforcement cliff
        matrix.generate(reference_date=date(2027, 10, 25)).critical_instruments
    """

    def __init__(
        self,
        instruments: Optional[list[TrackedInstrument]] = None,
    ) -> None:
        self._instruments = instruments or _INSTRUMENT_REGISTRY

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(
        self,
        reference_date: Optional[date] = None,
    ) -> ComplianceMatrix:
        """
        Generate a full compliance matrix for all tracked instruments.

        Args:
            reference_date: Date to evaluate.  Defaults to today.
        """
        ref   = reference_date or date.today()
        phase = current_phase(ref)

        reports: list[ComplianceHealthReport] = []
        for inst in self._instruments:
            report = self._assess(inst, ref, phase)
            reports.append(report)

        # Sort by survival severity then name
        _severity_order = {"CRITICAL": 0, "RED": 1, "AMBER": 2, "GREEN": 3}
        reports.sort(key=lambda r: (_severity_order[r.survival_flag], r.instrument_name))

        return ComplianceMatrix(
            generated_at=date.today(),
            reference_date=ref,
            current_phase=phase,
            reports=reports,
            green_count=sum(1 for r in reports if r.survival_flag == "GREEN"),
            amber_count=sum(1 for r in reports if r.survival_flag == "AMBER"),
            red_count=sum(1 for r in reports if r.survival_flag == "RED"),
            critical_count=sum(1 for r in reports if r.survival_flag == "CRITICAL"),
        )

    def check(
        self,
        instrument_id: str,
        reference_date: Optional[date] = None,
    ) -> Optional[ComplianceHealthReport]:
        """
        Compliance health check for a single instrument.

        Returns None if the instrument is not in the registry.
        """
        inst = _REGISTRY_MAP.get(instrument_id.upper())
        if not inst:
            log.warning("UKCryptoMatrix: unknown instrument '%s'", instrument_id)
            return None
        ref   = reference_date or date.today()
        phase = current_phase(ref)
        return self._assess(inst, ref, phase)

    def survival_flags(
        self,
        reference_date: Optional[date] = None,
    ) -> dict[str, SurvivalFlag]:
        """Return a compact {instrument_id: survival_flag} dict."""
        matrix = self.generate(reference_date)
        return {r.instrument_id: r.survival_flag for r in matrix.reports}

    def timeline_projection(
        self,
        instrument_id: str,
    ) -> list[tuple[date, SurvivalFlag, str]]:
        """
        Project how an instrument's survival flag changes across all key
        regulatory checkpoints.

        Returns a list of (checkpoint_date, flag, phase_label) tuples.
        """
        inst = _REGISTRY_MAP.get(instrument_id.upper())
        if not inst:
            return []

        checkpoints = [
            date.today(),
            GATEWAY_OPEN_DATE,
            GATEWAY_CLOSE_DATE,
            ENFORCEMENT_DATE,
        ]
        results = []
        for d in checkpoints:
            phase  = current_phase(d)
            report = self._assess(inst, d, phase)
            results.append((d, report.survival_flag, phase))
        return results

    def upcoming_actions(
        self,
        reference_date: Optional[date] = None,
        severity: tuple[SurvivalFlag, ...] = ("RED", "CRITICAL"),
    ) -> list[dict]:
        """
        Return a prioritised action list for instruments that need attention,
        filtered to the specified severity levels.
        """
        matrix = self.generate(reference_date)
        actions = []
        for report in matrix.reports:
            if report.survival_flag not in severity:
                continue
            actions.append({
                "instrument":   report.instrument_id,
                "name":         report.instrument_name,
                "flag":         report.survival_flag,
                "next_action":  report.next_action,
                "deadline":     report.deadline,
                "deadline_label": report.deadline_label,
            })
        return actions

    def print_dashboard(self, reference_date: Optional[date] = None) -> None:
        """Print a human-readable compliance dashboard to stdout."""
        ref    = reference_date or date.today()
        matrix = self.generate(ref)
        phase  = matrix.current_phase

        _col = {"GREEN": "\033[92m", "AMBER": "\033[93m",
                 "RED": "\033[91m", "CRITICAL": "\033[31m"}
        _reset = "\033[0m"

        print()
        print("=" * 72)
        print("  UK CRYPTO REGULATORY COMPLIANCE MATRIX")
        print(f"  Reference date : {ref}  |  Phase: {phase}")
        print(f"  {phase_narrative(phase)[:80]}...")
        print()
        upcoming = upcoming_milestones(ref, n=3)
        for m in upcoming:
            delta = (m['date'] - ref).days
            print(f"  ⏳  {m['date']}  [{delta:+d}d]  {m['label']}")
        print()
        print(f"  {'ID':<12} {'NAME':<32} {'STATUS':<22} {'FLAG':<10} {'NEXT ACTION'}")
        print("  " + "-" * 68)
        for r in matrix.reports:
            col  = _col.get(r.survival_flag, "")
            flag = f"{col}{r.survival_flag}{_reset}"
            print(
                f"  {r.instrument_id:<12} {r.instrument_name[:31]:<32} "
                f"{r.auth_status:<22} {flag:<20} {r.next_action[:30]}"
            )
        print()
        print(
            f"  Summary: GREEN={matrix.green_count}  AMBER={matrix.amber_count}"
            f"  RED={matrix.red_count}  CRITICAL={matrix.critical_count}"
        )
        print("=" * 72)
        print()

    # ── Core assessment logic ─────────────────────────────────────────────────

    def _assess(
        self,
        inst: TrackedInstrument,
        ref: date,
        phase: CompliancePhase,
    ) -> ComplianceHealthReport:
        """
        Derive the compliance health report for a single instrument at a given date.

        Decision matrix
        ───────────────
        GREEN  : Fully_Authorised regardless of phase.
        AMBER  : Registered_Only or Application_Pending before enforcement cliff.
        RED    : Not_Started or Registered_Only after gateway closes
                 (missed application window).
        CRITICAL: Not_Started or Withdrawn at/after enforcement cliff.
        """
        flag, narrative = self._classify_risk(inst, phase, ref)

        report = ComplianceHealthReport(
            instrument_id=inst.id,
            instrument_name=inst.name,
            category=inst.category,
            reference_date=ref,
            current_phase=phase,
            days_to_gateway_open=days_to_gateway_open(ref),
            days_to_gateway_close=days_to_gateway_close(ref),
            days_to_enforcement=days_to_enforcement(ref),
            auth_status=inst.auth_status,
            fca_ref=inst.fca_ref,
            survival_flag=flag,
            risk_narrative=narrative,
            can_operate_post_cliff=inst.auth_status == "Fully_Authorised",
            requires_vop=inst.auth_status == "Registered_Only",
            retail_access_at_risk=inst.has_retail_access and flag in ("RED", "CRITICAL"),
            estimated_wind_down_risk=flag == "CRITICAL",
        )
        self._attach_next_action(report, inst, phase, ref)
        return report

    def _classify_risk(
        self,
        inst: TrackedInstrument,
        phase: CompliancePhase,
        ref: date,
    ) -> tuple[SurvivalFlag, str]:
        """Return (survival_flag, narrative) for the instrument at this phase."""

        status = inst.auth_status

        # ── Fully authorised: always green ────────────────────────────────────
        if status == "Fully_Authorised":
            return "GREEN", (
                f"{inst.name} holds confirmed Part 4A FSMA authorisation. "
                "No regulatory action required."
            )

        # ── Withdrawn: always critical ────────────────────────────────────────
        if status == "Withdrawn":
            return "CRITICAL", (
                f"{inst.name} application was withdrawn or refused. "
                "Cannot operate regulated cryptoasset activities. "
                "Wind-down or transfer of assets required immediately."
            )

        # ── Phase-conditional assessment ──────────────────────────────────────
        if phase == "PRE_GATEWAY":
            if status in ("Registered_Only", "Grandfathered"):
                return "AMBER", (
                    f"{inst.name} holds legacy FCA registration. Must prepare "
                    f"and submit a Part 4A or VoP application by "
                    f"{GATEWAY_CLOSE_DATE}. Gateway opens {GATEWAY_OPEN_DATE}."
                )
            if status == "Not_Started":
                dtg = days_to_gateway_open(ref)
                return "RED", (
                    f"{inst.name} has no FCA authorisation process underway. "
                    f"Gateway opens in {dtg} days ({GATEWAY_OPEN_DATE}). "
                    "Immediate preparation required to avoid enforcement risk."
                )
            # Application pending before gateway even opens — proactive, green
            if status == "Application_Pending":
                return "GREEN", (
                    f"{inst.name} has submitted early application — ahead of schedule. "
                    "Monitor FCA processing timeline."
                )

        elif phase == "GATEWAY_OPEN":
            if status == "Application_Pending":
                return "AMBER", (
                    f"{inst.name} application is in process during the open window. "
                    f"Gateway closes {GATEWAY_CLOSE_DATE} — ensure application is complete."
                )
            if status in ("Registered_Only", "Grandfathered"):
                dtc = days_to_gateway_close(ref)
                return "RED", (
                    f"{inst.name} has not submitted a Part 4A/VoP application. "
                    f"Gateway closes in {dtc} days ({GATEWAY_CLOSE_DATE}). "
                    "Submit immediately or face enforcement after the cliff."
                )
            if status == "Not_Started":
                dtc = days_to_gateway_close(ref)
                return "CRITICAL", (
                    f"{inst.name} has NO authorisation and the gateway is OPEN. "
                    f"Window closes in {dtc} days. Submit NOW or plan immediate wind-down."
                )

        elif phase == "POST_GATEWAY":
            if status == "Application_Pending":
                dte = days_to_enforcement(ref)
                return "AMBER", (
                    f"{inst.name} submitted within the gateway window and benefits from "
                    f"interim transitional protection. FCA decision expected before "
                    f"enforcement cliff ({dte} days, {ENFORCEMENT_DATE})."
                )
            if status in ("Registered_Only", "Not_Started", "Grandfathered"):
                dte = days_to_enforcement(ref)
                return "CRITICAL", (
                    f"{inst.name} MISSED the application gateway (closed {GATEWAY_CLOSE_DATE}). "
                    f"No transitional protection. Must cease all regulated cryptoasset "
                    f"activities. Enforcement cliff in {dte} days ({ENFORCEMENT_DATE})."
                )

        elif phase == "ENFORCEMENT_CLIFF":
            if status == "Application_Pending":
                return "CRITICAL", (
                    f"{inst.name} application was not decided before the enforcement cliff. "
                    "Operations must be suspended pending FCA determination. "
                    "Contact FCA for interim permissions."
                )
            # Any non-authorised status at or past the cliff
            return "CRITICAL", (
                f"{inst.name} is operating WITHOUT Part 4A FSMA authorisation "
                "AFTER the October 25 2027 enforcement cliff. "
                "s.23 FSMA criminal liability is active. Immediate cessation required."
            )

        # Fallback — should not be reached
        return "AMBER", f"{inst.name}: status could not be fully assessed for phase {phase}."

    def _attach_next_action(
        self,
        report: ComplianceHealthReport,
        inst: TrackedInstrument,
        phase: CompliancePhase,
        ref: date,
    ) -> None:
        """Populate next_action, deadline, and deadline_label on the report in-place."""

        status = inst.auth_status

        if status == "Fully_Authorised":
            report.next_action    = "Annual compliance review and FCA regulatory reporting"
            report.deadline       = date(ref.year + 1, 1, 31)
            report.deadline_label = "Annual review"
            return

        if status == "Withdrawn":
            report.next_action    = "Engage FCA for wind-down plan; transfer client assets"
            report.deadline       = ref
            report.deadline_label = "IMMEDIATE"
            return

        if phase == "PRE_GATEWAY":
            if status == "Not_Started":
                report.next_action    = "Engage FCA-approved compliance counsel; scope regulated activities"
                report.deadline       = GATEWAY_OPEN_DATE
                report.deadline_label = "Gateway opens"
            else:
                report.next_action    = "Prepare VoP or new Part 4A application documents"
                report.deadline       = GATEWAY_OPEN_DATE
                report.deadline_label = "Submit on gateway open"

        elif phase == "GATEWAY_OPEN":
            if status in ("Not_Started", "Registered_Only", "Grandfathered"):
                report.next_action    = "SUBMIT Part 4A or VoP application to FCA immediately"
                report.deadline       = GATEWAY_CLOSE_DATE
                report.deadline_label = "Gateway closes — HARD DEADLINE"
            else:
                report.next_action    = "Complete any FCA information requests; monitor application"
                report.deadline       = GATEWAY_CLOSE_DATE
                report.deadline_label = "Gateway closes"

        elif phase == "POST_GATEWAY":
            if status == "Application_Pending":
                report.next_action    = "Respond promptly to FCA queries; maintain interim compliance"
                report.deadline       = ENFORCEMENT_DATE
                report.deadline_label = "Enforcement cliff"
            else:
                report.next_action    = "CEASE regulated cryptoasset activities; initiate wind-down"
                report.deadline       = ref
                report.deadline_label = "IMMEDIATE — gateway closed"

        elif phase == "ENFORCEMENT_CLIFF":
            report.next_action    = "Suspend operations; engage FCA enforcement team"
            report.deadline       = ref
            report.deadline_label = "IMMEDIATE — criminal liability active"
