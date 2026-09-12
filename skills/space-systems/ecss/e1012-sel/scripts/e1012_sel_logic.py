"""
SEL/SESB rate prediction — ECSS-E-ST-10-12C §9.4.1.4–9.4.1.5.
Paraphrased procedure; no verbatim standard text reproduced.
stdlib only; offline; deterministic.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple

# ── Rate thresholds (events/device/day) ─────────────────────────────────────

SEL_RATE_ACCEPTABLE = 1.0e-7
SEL_RATE_MONITOR    = 1.0e-5


# ── Weibull cross-section model (heavy-ion path) ─────────────────────────────

def weibull_cross_section(
    let: float,
    let_th: float,
    sigma_sat: float,
    W: float,
    s: float,
) -> float:
    """
    Heavy-ion SEL/SESB cross-section vs LET via four-parameter Weibull fit.

    let       — LET of the ion [MeV·cm²/mg]
    let_th    — LET threshold below which no event occurs [MeV·cm²/mg]
    sigma_sat — saturation cross-section [cm²/device]
    W         — Weibull width parameter [MeV·cm²/mg]
    s         — Weibull shape exponent [dimensionless]

    Returns cross-section [cm²/device]; zero for let <= let_th.
    """
    if W <= 0.0:
        raise ValueError(f"Weibull width W must be positive, got {W}")
    if s <= 0.0:
        raise ValueError(f"Weibull shape s must be positive, got {s}")
    if sigma_sat <= 0.0:
        raise ValueError(f"sigma_sat must be positive, got {sigma_sat}")
    if let <= let_th:
        return 0.0
    return sigma_sat * (1.0 - math.exp(-((let - let_th) / W) ** s))


# ── Heavy-ion SEL/SESB rate (trapezoidal integration) ────────────────────────

def heavy_ion_sel_rate(
    let_flux_pairs: List[Tuple[float, float]],
    let_th: float,
    sigma_sat: float,
    W: float,
    s: float,
) -> float:
    """
    Integrate the Weibull cross-section over the differential LET spectrum.

    let_flux_pairs — list of (LET [MeV·cm²/mg],
                              differential flux [particles/(cm²·day·(MeV·cm²/mg))])
    Returns rate [events/device/day].
    """
    if not let_flux_pairs:
        raise ValueError("LET spectrum must contain at least one point")
    if sigma_sat <= 0.0:
        raise ValueError(f"sigma_sat must be positive, got {sigma_sat}")

    sorted_pairs = sorted(let_flux_pairs, key=lambda p: p[0])

    rate = 0.0
    for i in range(len(sorted_pairs) - 1):
        l0, f0 = sorted_pairs[i]
        l1, f1 = sorted_pairs[i + 1]
        dl = l1 - l0
        if dl <= 0.0:
            continue
        s0 = weibull_cross_section(l0, let_th, sigma_sat, W, s)
        s1 = weibull_cross_section(l1, let_th, sigma_sat, W, s)
        rate += 0.5 * (s0 * f0 + s1 * f1) * dl

    return rate


# ── Bendel two-parameter proton/neutron cross-section model ──────────────────

def bendel_proton_cross_section(
    E: float,
    A: float,
    B: float,
) -> float:
    """
    Proton/neutron SEL cross-section via the Bendel two-parameter model.

    E — proton/neutron kinetic energy [MeV]
    A — threshold energy [MeV]
    B — asymptotic cross-section [cm²/device]

    Returns cross-section [cm²/device]; zero for E <= A.
    """
    if A <= 0.0:
        raise ValueError(f"Bendel threshold A must be positive, got {A}")
    if B <= 0.0:
        raise ValueError(f"Bendel scale B must be positive, got {B}")
    if E <= A:
        return 0.0
    ratio = (18.0 / A) ** 0.5 * (E - A)
    return B * (1.0 - math.exp(-0.18 * ratio)) ** 4


# ── Proton/neutron SEL/SESB rate (trapezoidal integration) ───────────────────

def proton_sel_rate(
    energy_flux_pairs: List[Tuple[float, float]],
    A: float,
    B: float,
) -> float:
    """
    Integrate the Bendel cross-section over the differential proton spectrum.

    energy_flux_pairs — list of (E [MeV],
                                  differential flux [particles/(cm²·day·MeV)])
    Returns rate [events/device/day].
    """
    if not energy_flux_pairs:
        raise ValueError("Proton spectrum must contain at least one point")
    if A <= 0.0:
        raise ValueError(f"Bendel threshold A must be positive, got {A}")
    if B <= 0.0:
        raise ValueError(f"Bendel scale B must be positive, got {B}")

    sorted_pairs = sorted(energy_flux_pairs, key=lambda p: p[0])

    rate = 0.0
    for i in range(len(sorted_pairs) - 1):
        e0, f0 = sorted_pairs[i]
        e1, f1 = sorted_pairs[i + 1]
        de = e1 - e0
        if de <= 0.0:
            continue
        s0 = bendel_proton_cross_section(e0, A, B)
        s1 = bendel_proton_cross_section(e1, A, B)
        rate += 0.5 * (s0 * f0 + s1 * f1) * de

    return rate


# ── Severity categorization ───────────────────────────────────────────────────

def categorize_sel_rate(rate: float) -> str:
    """
    Assign a severity category to a combined SEL/SESB rate.
    Returns 'acceptable', 'monitor', or 'critical'.
    """
    if rate < 0.0:
        raise ValueError(f"SEL rate cannot be negative, got {rate}")
    if rate < SEL_RATE_ACCEPTABLE:
        return "acceptable"
    if rate < SEL_RATE_MONITOR:
        return "monitor"
    return "critical"


# ── Combined assessment dataclass ─────────────────────────────────────────────

@dataclass
class SELAssessment:
    device_id:       str
    heavy_ion_rate:  float
    proton_rate:     float
    combined_rate:   float
    severity:        str
    flags:           List[str] = field(default_factory=list)


def assess_sel(
    device_id: str,
    let_flux_pairs: List[Tuple[float, float]],
    let_th: float,
    sigma_sat: float,
    W: float,
    s_shape: float,
    energy_flux_pairs: List[Tuple[float, float]],
    A: float,
    B: float,
) -> SELAssessment:
    """
    Full SEL/SESB assessment: integrate both particle paths and categorize.

    Returns an SELAssessment with per-path rates, combined rate, severity
    category, and any advisory flags raised during the assessment.
    """
    if not device_id or not device_id.strip():
        raise ValueError("device_id must be a non-empty string")

    flags: List[str] = []

    hi_rate = heavy_ion_sel_rate(let_flux_pairs, let_th, sigma_sat, W, s_shape)
    pr_rate = proton_sel_rate(energy_flux_pairs, A, B)
    combined = hi_rate + pr_rate

    if combined == 0.0:
        flags.append("zero combined rate: verify that spectrum spans the device threshold")
    else:
        if pr_rate > 0.0 and hi_rate > pr_rate * 10.0:
            flags.append(
                "heavy-ion dominated (>10× proton): confirm proton spectrum covers full energy range"
            )
        if hi_rate > 0.0 and pr_rate > hi_rate * 10.0:
            flags.append(
                "proton dominated (>10× heavy-ion): confirm LET spectrum covers full LET range"
            )

    severity = categorize_sel_rate(combined)

    if severity == "critical":
        flags.append(
            "CRITICAL rate: device requires latch-up current limiting and power-cycle recovery"
        )
    elif severity == "monitor":
        flags.append(
            "elevated rate: review latch-up current limiting and reset design margins"
        )

    return SELAssessment(
        device_id=device_id,
        heavy_ion_rate=hi_rate,
        proton_rate=pr_rate,
        combined_rate=combined,
        severity=severity,
        flags=flags,
    )
