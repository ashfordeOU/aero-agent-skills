"""
Mass and inertia property measurement logic — ECSS-E-ST-32C §4.6.3.18.
Offline, deterministic, stdlib only.

Implements torsion-pendulum inertia derivation, fixture correction,
torsion-constant calibration, mass validation, CG validation, inertia-axis
comparison, inertia-tensor symmetry checking, and report aggregation.
"""

import math

TWO_PI_SQUARED = 4.0 * math.pi ** 2


# ---------------------------------------------------------------------------
# Torsion-pendulum core
# ---------------------------------------------------------------------------

def compute_moment_of_inertia(period_s: float, torsion_constant_Nm_per_rad: float) -> float:
    """
    Return the moment of inertia (kg·m²) for a single torsion-pendulum run.

    I = k · T² / (4π²)

    Raises ValueError for non-physical inputs.
    """
    if period_s <= 0.0:
        raise ValueError(f"Period must be positive; got {period_s!r}")
    if torsion_constant_Nm_per_rad <= 0.0:
        raise ValueError(
            f"Torsion constant must be positive; got {torsion_constant_Nm_per_rad!r}"
        )
    return torsion_constant_Nm_per_rad * period_s ** 2 / TWO_PI_SQUARED


def compute_fixture_corrected_inertia(
    total_period_s: float,
    fixture_period_s: float,
    torsion_constant_Nm_per_rad: float,
) -> float:
    """
    Return the item-alone MOI (kg·m²) by subtracting the fixture contribution.

    I_item = k · (T_total² − T_fixture²) / (4π²)

    Raises ValueError if the fixture period is not strictly less than the
    total period (physics requires the item to add positive inertia).
    """
    if fixture_period_s >= total_period_s:
        raise ValueError(
            f"Fixture period ({fixture_period_s}) must be less than total period "
            f"({total_period_s}); a fixture cannot contribute more inertia than "
            "the item + fixture combined."
        )
    i_total = compute_moment_of_inertia(total_period_s, torsion_constant_Nm_per_rad)
    i_fixture = compute_moment_of_inertia(fixture_period_s, torsion_constant_Nm_per_rad)
    result = i_total - i_fixture
    if result < 0.0:
        raise ValueError(
            f"Computed item inertia is negative ({result:.6g} kg·m²); "
            "check period and torsion-constant inputs."
        )
    return result


def calibrate_torsion_constant(
    reference_inertia_kgm2: float,
    reference_period_s: float,
    base_period_s: float,
) -> float:
    """
    Return the torsion constant k (N·m/rad) from a calibration reference run.

    k = I_ref · 4π² / (T_ref² − T_base²)

    The reference period must exceed the empty-table base period so that the
    denominator is positive.  Raises ValueError for non-physical inputs.
    """
    if reference_inertia_kgm2 <= 0.0:
        raise ValueError(
            f"Reference inertia must be positive; got {reference_inertia_kgm2!r}"
        )
    if reference_period_s <= base_period_s:
        raise ValueError(
            f"Reference period ({reference_period_s}) must exceed base period "
            f"({base_period_s}); the reference object must add positive inertia."
        )
    denominator = reference_period_s ** 2 - base_period_s ** 2
    return reference_inertia_kgm2 * TWO_PI_SQUARED / denominator


# ---------------------------------------------------------------------------
# Mass validation
# ---------------------------------------------------------------------------

def validate_mass(
    measured_kg: float,
    predicted_kg: float,
    tolerance_fraction: float,
) -> dict:
    """
    Compare measured mass against structural prediction.

    Returns a result dict with keys:
      measured_kg, predicted_kg, deviation_fraction, tolerance_fraction,
      pass (bool), finding (str or None).
    """
    if measured_kg < 0.0:
        raise ValueError(f"Measured mass must be non-negative; got {measured_kg!r}")
    if predicted_kg <= 0.0:
        raise ValueError(f"Predicted mass must be positive; got {predicted_kg!r}")
    if tolerance_fraction < 0.0:
        raise ValueError(
            f"Tolerance fraction must be non-negative; got {tolerance_fraction!r}"
        )
    deviation = (measured_kg - predicted_kg) / predicted_kg
    within = abs(deviation) <= tolerance_fraction
    return {
        "measured_kg": measured_kg,
        "predicted_kg": predicted_kg,
        "deviation_fraction": deviation,
        "tolerance_fraction": tolerance_fraction,
        "pass": within,
        "finding": None if within else (
            f"Mass deviation {deviation:+.2%} exceeds ±{tolerance_fraction:.2%} tolerance "
            f"(measured={measured_kg} kg, predicted={predicted_kg} kg)."
        ),
    }


# ---------------------------------------------------------------------------
# Center-of-gravity validation
# ---------------------------------------------------------------------------

def validate_cg(
    measured_xyz: tuple,
    predicted_xyz: tuple,
    tolerance_m: float,
) -> dict:
    """
    Compare measured CG position (3-D) against structural prediction.

    Each axis is checked independently against tolerance_m.  The Euclidean
    distance is also reported.  Returns a result dict with keys:
      axis (dict per 'x'/'y'/'z'), euclidean_distance_m, overall_pass, findings.
    """
    if len(measured_xyz) != 3 or len(predicted_xyz) != 3:
        raise ValueError(
            "CG vectors must have exactly 3 components (x, y, z); "
            f"got measured={len(measured_xyz)}, predicted={len(predicted_xyz)}."
        )
    if tolerance_m < 0.0:
        raise ValueError(
            f"Tolerance must be non-negative; got {tolerance_m!r}"
        )
    axis_results = {}
    for label, m_val, p_val in zip(("x", "y", "z"), measured_xyz, predicted_xyz):
        diff = m_val - p_val
        ok = abs(diff) <= tolerance_m
        axis_results[label] = {
            "measured_m": m_val,
            "predicted_m": p_val,
            "delta_m": diff,
            "pass": ok,
        }
    euclidean = math.sqrt(
        sum((m - p) ** 2 for m, p in zip(measured_xyz, predicted_xyz))
    )
    findings = [
        f"CG {ax}-axis deviation {v['delta_m']:+.4f} m exceeds ±{tolerance_m:.4f} m."
        for ax, v in axis_results.items()
        if not v["pass"]
    ]
    all_axes_pass = all(v["pass"] for v in axis_results.values())
    return {
        "axis": axis_results,
        "euclidean_distance_m": euclidean,
        "overall_pass": all_axes_pass,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# Moment-of-inertia axis validation
# ---------------------------------------------------------------------------

def validate_inertia(
    measured_kgm2: float,
    predicted_kgm2: float,
    tolerance_fraction: float,
    axis_label: str = "?",
) -> dict:
    """
    Compare measured MOI (one axis) against structural prediction.

    Returns a result dict with keys:
      axis, measured_kgm2, predicted_kgm2, deviation_fraction,
      tolerance_fraction, pass (bool), finding (str or None).
    """
    if measured_kgm2 < 0.0:
        raise ValueError(f"Measured MOI must be non-negative; got {measured_kgm2!r}")
    if predicted_kgm2 <= 0.0:
        raise ValueError(f"Predicted MOI must be positive; got {predicted_kgm2!r}")
    if tolerance_fraction < 0.0:
        raise ValueError(
            f"Tolerance fraction must be non-negative; got {tolerance_fraction!r}"
        )
    deviation = (measured_kgm2 - predicted_kgm2) / predicted_kgm2
    within = abs(deviation) <= tolerance_fraction
    return {
        "axis": axis_label,
        "measured_kgm2": measured_kgm2,
        "predicted_kgm2": predicted_kgm2,
        "deviation_fraction": deviation,
        "tolerance_fraction": tolerance_fraction,
        "pass": within,
        "finding": None if within else (
            f"MOI {axis_label} deviation {deviation:+.2%} exceeds "
            f"±{tolerance_fraction:.2%} tolerance "
            f"(measured={measured_kgm2} kg·m², predicted={predicted_kgm2} kg·m²)."
        ),
    }


# ---------------------------------------------------------------------------
# Inertia-tensor symmetry check
# ---------------------------------------------------------------------------

def check_inertia_tensor_symmetry(
    inertia_tensor: list,
    rtol: float = 1e-6,
) -> dict:
    """
    Verify a 3×3 inertia tensor is symmetric (Iij == Iji within rtol).

    inertia_tensor must be a list of 3 lists of 3 floats.
    Returns a dict with keys: symmetric (bool), findings (list of str).
    """
    if len(inertia_tensor) != 3 or any(len(row) != 3 for row in inertia_tensor):
        raise ValueError(
            "Inertia tensor must be a 3×3 matrix (list of 3 lists of 3 floats)."
        )
    findings = []
    for i in range(3):
        for j in range(i + 1, 3):
            a = float(inertia_tensor[i][j])
            b = float(inertia_tensor[j][i])
            scale = max(abs(a), abs(b), 1e-12)
            asymmetry = abs(a - b) / scale
            if asymmetry > rtol:
                findings.append(
                    f"I[{i}][{j}]={a:.6g} != I[{j}][{i}]={b:.6g} "
                    f"(relative asymmetry {asymmetry:.2e} > {rtol:.2e})"
                )
    return {"symmetric": len(findings) == 0, "findings": findings}


# ---------------------------------------------------------------------------
# Report aggregation
# ---------------------------------------------------------------------------

def aggregate_report(
    mass_result: dict,
    cg_result: dict,
    inertia_results: list,
) -> dict:
    """
    Combine mass, CG, and inertia-axis results into a single properties report.

    Returns a dict with keys:
      overall_pass (bool), findings (list of str),
      mass, cg, inertia_axes.
    """
    all_pass = (
        mass_result.get("pass", False)
        and cg_result.get("overall_pass", False)
        and all(r.get("pass", False) for r in inertia_results)
    )
    findings: list = []
    if mass_result.get("finding"):
        findings.append(mass_result["finding"])
    findings.extend(cg_result.get("findings", []))
    for r in inertia_results:
        if r.get("finding"):
            findings.append(r["finding"])
    return {
        "overall_pass": all_pass,
        "findings": findings,
        "mass": mass_result,
        "cg": cg_result,
        "inertia_axes": inertia_results,
    }
