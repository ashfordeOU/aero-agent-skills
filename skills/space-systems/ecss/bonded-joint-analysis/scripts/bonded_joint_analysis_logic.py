# bonded_joint_analysis_logic.py
# Bonded-joint shear-lag (Volkersen) and peel-stress assessment.
# Anchor: ECSS-E-ST-32C clause 4.6.2.12
# stdlib only; deterministic; offline.

import math
from typing import Any, Dict, List


VALID_JOINT_TYPES: frozenset = frozenset({"single_lap", "double_lap", "scarf"})


def validate_inputs(
    E1: float, t1: float,
    E2: float, t2: float,
    G_a: float, E_a: float, t_a: float,
    allow_shear: float, allow_peel: float,
    overlap_length: float, bond_width: float,
    applied_load: float,
    joint_type: str,
) -> None:
    """Validate all joint inputs; raise ValueError on any violation."""
    positive_params = {
        "E1": E1, "t1": t1,
        "E2": E2, "t2": t2,
        "G_a": G_a, "E_a": E_a, "t_a": t_a,
        "allow_shear": allow_shear, "allow_peel": allow_peel,
        "overlap_length": overlap_length, "bond_width": bond_width,
    }
    errors: List[str] = [
        f"{name} must be positive, got {val}"
        for name, val in positive_params.items()
        if not (isinstance(val, (int, float)) and val > 0)
    ]
    if not (isinstance(applied_load, (int, float)) and applied_load >= 0):
        errors.append(f"applied_load must be >= 0, got {applied_load}")
    if joint_type not in VALID_JOINT_TYPES:
        errors.append(
            f"joint_type must be one of {sorted(VALID_JOINT_TYPES)}, got {joint_type!r}"
        )
    if errors:
        raise ValueError("; ".join(errors))


def compute_shear_lag_parameter(
    G_a: float, t_a: float,
    E1: float, t1: float,
    E2: float, t2: float,
) -> float:
    """Return the Volkersen shear-lag parameter omega (m⁻¹).

    omega = sqrt(G_a/t_a * (1/(E1*t1) + 1/(E2*t2)))
    """
    omega_sq = (G_a / t_a) * (1.0 / (E1 * t1) + 1.0 / (E2 * t2))
    return math.sqrt(omega_sq)


def compute_peak_shear_stress(
    P: float, b: float, l: float, omega: float
) -> float:
    """Return peak shear stress (Pa) from the Volkersen shear-lag model.

    tau_max = P*omega/(2*b) * coth(omega*l/2)
    Degenerates to average shear for omega -> 0.
    """
    half_arg = omega * l / 2.0
    if half_arg < 1e-12:
        return P / (b * l) if (b * l) > 0.0 else 0.0
    coth_val = math.cosh(half_arg) / math.sinh(half_arg)
    return (P * omega / (2.0 * b)) * coth_val


def compute_average_shear_stress(P: float, b: float, l: float) -> float:
    """Return nominal (average) shear stress (Pa) over the bond area."""
    return P / (b * l)


def compute_peel_stress(
    P: float, b: float, l: float,
    t1: float, t2: float, t_a: float,
    joint_type: str,
) -> float:
    """Return peak peel stress (Pa) from the eccentric-load simplified model.

    single_lap / scarf: sigma_peel = 6*P*e / (b*l^2), e = (t1+t2)/2 + t_a
    double_lap: eccentricity cancels in symmetric geometry -> 0.
    """
    if joint_type == "double_lap":
        return 0.0
    eccentricity = (t1 + t2) / 2.0 + t_a
    return 6.0 * P * eccentricity / (b * l ** 2)


def compute_margin_of_safety(allowable: float, applied: float) -> float:
    """Return MS = allowable/applied - 1.  Returns +inf when applied is zero."""
    if applied <= 0.0:
        return float("inf")
    return allowable / applied - 1.0


def evaluate_bonded_joint(
    E1: float, t1: float,
    E2: float, t2: float,
    G_a: float, E_a: float, t_a: float,
    allow_shear: float, allow_peel: float,
    overlap_length: float, bond_width: float,
    applied_load: float,
    joint_type: str = "single_lap",
) -> Dict[str, Any]:
    """Run the full bonded-joint assessment: shear-lag + peel.

    Returns a result dict containing stresses, margins, SCF, and status.
    status is 'PASS' when both margins >= 0, 'FAIL' otherwise.
    """
    validate_inputs(
        E1, t1, E2, t2, G_a, E_a, t_a,
        allow_shear, allow_peel,
        overlap_length, bond_width, applied_load, joint_type,
    )

    P = applied_load
    b = bond_width
    l = overlap_length

    omega = compute_shear_lag_parameter(G_a, t_a, E1, t1, E2, t2)
    tau_max = compute_peak_shear_stress(P, b, l, omega)
    tau_avg = compute_average_shear_stress(P, b, l)
    sigma_peel = compute_peel_stress(P, b, l, t1, t2, t_a, joint_type)

    ms_shear = compute_margin_of_safety(allow_shear, tau_max)
    ms_peel = compute_margin_of_safety(allow_peel, sigma_peel)

    scf = tau_max / tau_avg if tau_avg > 0.0 else 1.0

    findings: List[str] = []
    if ms_shear < 0.0:
        findings.append(
            f"SHEAR FAIL: tau_max={tau_max:.4g} Pa > allowable {allow_shear:.4g} Pa"
            f" (MS={ms_shear:.4f})"
        )
    if ms_peel < 0.0:
        findings.append(
            f"PEEL FAIL: sigma_peel={sigma_peel:.4g} Pa > allowable {allow_peel:.4g} Pa"
            f" (MS={ms_peel:.4f})"
        )

    return {
        "status": "PASS" if not findings else "FAIL",
        "omega_per_m": omega,
        "tau_max_Pa": tau_max,
        "tau_avg_Pa": tau_avg,
        "sigma_peel_Pa": sigma_peel,
        "ms_shear": ms_shear,
        "ms_peel": ms_peel,
        "stress_concentration_factor": scf,
        "findings": findings,
    }
