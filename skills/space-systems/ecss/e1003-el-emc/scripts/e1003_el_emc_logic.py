"""
ECSS-E-ST-10-03C §6.5.5 element electromagnetic compatibility test logic.
Covers auto-compatibility, passive intermodulation (PIM), magnetic field
measurement, and stand-alone vs embedded test-mode selection (§6.5.5.2).
Stdlib only. Offline, deterministic.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

ECSS_CLAUSE = "ECSS-E-ST-10-03C §6.5.5"


# ─── Enumerations ─────────────────────────────────────────────────────────────

class TestMode(Enum):
    STANDALONE = "standalone"
    EMBEDDED = "embedded"


class TestType(Enum):
    AUTO_COMPATIBILITY = "auto_compatibility"
    PIM = "pim"
    MAGNETIC_FIELD = "magnetic_field"
    CONDUCTED_EMISSION = "conducted_emission"
    RADIATED_EMISSION = "radiated_emission"
    CONDUCTED_SUSCEPTIBILITY = "conducted_susceptibility"
    RADIATED_SUSCEPTIBILITY = "radiated_susceptibility"


class Outcome(Enum):
    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"
    DATA_MISSING = "data_missing"


# ─── Data containers ──────────────────────────────────────────────────────────

@dataclass
class AutoCompatPair:
    """One internal emitter frequency checked against one internal receive band."""
    emitter_freq_hz: float
    rx_band_low_hz: float
    rx_band_high_hz: float
    margin_db: float          # measured isolation margin
    required_margin_db: float # minimum required margin (positive)

    def __post_init__(self) -> None:
        if self.rx_band_low_hz >= self.rx_band_high_hz:
            raise ValueError(
                "rx_band_low_hz must be strictly less than rx_band_high_hz"
            )
        if self.emitter_freq_hz <= 0:
            raise ValueError("emitter_freq_hz must be positive")


@dataclass
class PIMCarrierPair:
    """Two simultaneous RF carriers that may produce intermodulation products."""
    f1_hz: float       # first carrier frequency (Hz)
    f2_hz: float       # second carrier frequency (Hz)
    rx_low_hz: float   # receive band lower bound (Hz)
    rx_high_hz: float  # receive band upper bound (Hz)

    def __post_init__(self) -> None:
        if self.f1_hz <= 0 or self.f2_hz <= 0:
            raise ValueError("carrier frequencies must be positive")
        if self.rx_low_hz >= self.rx_high_hz:
            raise ValueError("rx_low_hz must be strictly less than rx_high_hz")


@dataclass
class MagneticMeasurement:
    """Residual magnetic dipole moment vs element-level budget."""
    measured_am2: float  # measured dipole moment magnitude (A·m²)
    budget_am2: float    # allowable maximum (A·m²)

    def __post_init__(self) -> None:
        if self.budget_am2 <= 0:
            raise ValueError("budget_am2 must be positive")
        if self.measured_am2 < 0:
            raise ValueError("measured_am2 must be non-negative")


@dataclass
class TestFinding:
    test_type: TestType
    test_mode: TestMode
    outcome: Outcome
    detail: str = ""


@dataclass
class EMCAssessmentResult:
    element_id: str
    findings: List[TestFinding] = field(default_factory=list)

    @property
    def compliant(self) -> bool:
        return all(
            f.outcome in (Outcome.PASS, Outcome.NOT_APPLICABLE)
            for f in self.findings
        )

    @property
    def open_findings(self) -> List[TestFinding]:
        return [
            f for f in self.findings
            if f.outcome in (Outcome.FAIL, Outcome.DATA_MISSING)
        ]


# ─── Auto-compatibility ───────────────────────────────────────────────────────

def check_auto_compatibility(pair: AutoCompatPair, mode: TestMode) -> TestFinding:
    """
    Return a TestFinding for one emitter–receiver pair.
    FAIL when the emitter is in-band AND margin < required.
    NOT_APPLICABLE when the emitter is outside the receive band.
    """
    in_band = pair.rx_band_low_hz <= pair.emitter_freq_hz <= pair.rx_band_high_hz

    if not in_band:
        return TestFinding(
            TestType.AUTO_COMPATIBILITY,
            mode,
            Outcome.NOT_APPLICABLE,
            f"emitter {pair.emitter_freq_hz:.4e} Hz outside rx band "
            f"[{pair.rx_band_low_hz:.4e}, {pair.rx_band_high_hz:.4e}] Hz",
        )

    if pair.margin_db >= pair.required_margin_db:
        return TestFinding(
            TestType.AUTO_COMPATIBILITY,
            mode,
            Outcome.PASS,
            f"emitter {pair.emitter_freq_hz:.4e} Hz in rx band, "
            f"margin {pair.margin_db:.1f} dB >= required {pair.required_margin_db:.1f} dB",
        )

    return TestFinding(
        TestType.AUTO_COMPATIBILITY,
        mode,
        Outcome.FAIL,
        f"emitter {pair.emitter_freq_hz:.4e} Hz in rx band "
        f"[{pair.rx_band_low_hz:.4e}, {pair.rx_band_high_hz:.4e}] Hz, "
        f"margin {pair.margin_db:.1f} dB < required {pair.required_margin_db:.1f} dB",
    )


# ─── PIM evaluation ───────────────────────────────────────────────────────────

def _odd_order_pim_products(
    f1: float, f2: float, max_order: int = 9
) -> List[Tuple[int, int, float]]:
    """
    Compute odd-order PIM products up to max_order.
    Products are m·f1 − n·f2 and m·f2 − n·f1 where m + n = order (odd),
    m >= 1, n >= 1.  Only positive-frequency results are returned.
    Returns list of (m, n, frequency_hz).
    """
    products: List[Tuple[int, int, float]] = []
    for order in range(3, max_order + 1, 2):  # 3, 5, 7, 9, ...
        for m in range(1, order):
            n = order - m
            freq_a = m * f1 - n * f2
            if freq_a > 0:
                products.append((m, n, freq_a))
            freq_b = m * f2 - n * f1
            if freq_b > 0:
                products.append((m, n, freq_b))
    return products


def check_pim(pair: PIMCarrierPair, max_order: int = 9) -> TestFinding:
    """
    Return FAIL if any odd-order PIM product falls within the receive band,
    PASS otherwise.
    """
    products = _odd_order_pim_products(pair.f1_hz, pair.f2_hz, max_order)
    in_band = [
        (m, n, f)
        for m, n, f in products
        if pair.rx_low_hz <= f <= pair.rx_high_hz
    ]

    if in_band:
        sample = in_band[:3]
        detail = (
            f"{len(in_band)} PIM product(s) fall in rx band "
            f"[{pair.rx_low_hz:.4e}, {pair.rx_high_hz:.4e}] Hz; "
            f"first: order={in_band[0][0]+in_band[0][1]}, "
            f"freq={in_band[0][2]:.4e} Hz"
        )
        return TestFinding(TestType.PIM, TestMode.STANDALONE, Outcome.FAIL, detail)

    return TestFinding(
        TestType.PIM,
        TestMode.STANDALONE,
        Outcome.PASS,
        f"No PIM products (orders 3–{max_order}) in rx band "
        f"[{pair.rx_low_hz:.4e}, {pair.rx_high_hz:.4e}] Hz",
    )


# ─── Magnetic field ────────────────────────────────────────────────────────────

def check_magnetic_field(meas: MagneticMeasurement, mode: TestMode) -> TestFinding:
    """
    Return FAIL if the measured residual dipole moment exceeds the budget.
    """
    if meas.measured_am2 > meas.budget_am2:
        return TestFinding(
            TestType.MAGNETIC_FIELD,
            mode,
            Outcome.FAIL,
            f"residual dipole {meas.measured_am2:.4e} A·m² exceeds "
            f"budget {meas.budget_am2:.4e} A·m²",
        )
    return TestFinding(
        TestType.MAGNETIC_FIELD,
        mode,
        Outcome.PASS,
        f"residual dipole {meas.measured_am2:.4e} A·m² within "
        f"budget {meas.budget_am2:.4e} A·m²",
    )


# ─── Test-mode selection (§6.5.5.2) ──────────────────────────────────────────

_STANDALONE_MANDATORY: List[TestType] = [
    TestType.AUTO_COMPATIBILITY,
    TestType.PIM,
    TestType.MAGNETIC_FIELD,
    TestType.CONDUCTED_EMISSION,
    TestType.RADIATED_EMISSION,
]

_EMBEDDED_SUPPLEMENTARY: List[TestType] = [
    TestType.CONDUCTED_SUSCEPTIBILITY,
    TestType.RADIATED_SUSCEPTIBILITY,
]


def select_test_modes(
    element_has_rf_paths: bool,
    embedded_available: bool,
) -> Dict[TestType, TestMode]:
    """
    Return the required TestMode for each applicable TestType per §6.5.5.2.

    PIM is omitted when the element carries no RF transmission paths.
    Conducted and radiated susceptibility are added in EMBEDDED mode only
    when the element is available assembled in its higher-level unit.
    Stand-alone susceptibility is not listed separately; in practice it is
    covered by the stand-alone emission and auto-compatibility suite.
    """
    result: Dict[TestType, TestMode] = {}
    for tt in _STANDALONE_MANDATORY:
        if tt is TestType.PIM and not element_has_rf_paths:
            continue
        result[tt] = TestMode.STANDALONE
    if embedded_available:
        for tt in _EMBEDDED_SUPPLEMENTARY:
            result[tt] = TestMode.EMBEDDED
    return result


# ─── Full element assessment ──────────────────────────────────────────────────

def assess_element_emc(
    element_id: str,
    mode: TestMode,
    auto_compat_pairs: Optional[List[AutoCompatPair]] = None,
    pim_pairs: Optional[List[PIMCarrierPair]] = None,
    magnetic_meas: Optional[MagneticMeasurement] = None,
) -> EMCAssessmentResult:
    """
    Aggregate EMC findings for one element.
    Raises ValueError for an empty element_id.
    Returns DATA_MISSING if no test inputs are provided.
    """
    if not element_id or not element_id.strip():
        raise ValueError("element_id must be a non-empty string")

    result = EMCAssessmentResult(element_id=element_id)

    if auto_compat_pairs:
        for pair in auto_compat_pairs:
            result.findings.append(check_auto_compatibility(pair, mode))

    if pim_pairs:
        for pair in pim_pairs:
            result.findings.append(check_pim(pair))

    if magnetic_meas is not None:
        result.findings.append(check_magnetic_field(magnetic_meas, mode))

    if not result.findings:
        result.findings.append(
            TestFinding(
                TestType.AUTO_COMPATIBILITY,
                mode,
                Outcome.DATA_MISSING,
                "No test inputs provided; element EMC cannot be assessed",
            )
        )

    return result
