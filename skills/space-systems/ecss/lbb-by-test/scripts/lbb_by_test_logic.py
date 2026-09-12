"""
LBB demonstration by coupon or full/sub-scale test logic.
Implements ECSS-E-ST-32C clauses 5.3.3–5.3.4.
stdlib only — no external dependencies.
"""

VALID_SPECIMEN_TYPES = {"coupon", "sub-scale", "full-scale"}
MIN_BURST_FACTOR = 1.5
MIN_PROOF_FACTOR = 1.0
MIN_SUB_SCALE_FACTOR = 0.5


def validate_lbb_inputs(params):
    """Raise ValueError if any required key is missing or non-positive."""
    required = [
        "critical_crack_length_mm",
        "through_wall_crack_length_mm",
        "wall_thickness_mm",
        "burst_pressure_mpa",
        "proof_pressure_mpa",
        "meop_mpa",
        "test_specimen_type",
    ]
    missing = [k for k in required if k not in params]
    if missing:
        raise ValueError(f"Missing required parameters: {missing}")

    for key in (
        "critical_crack_length_mm",
        "through_wall_crack_length_mm",
        "wall_thickness_mm",
        "burst_pressure_mpa",
        "proof_pressure_mpa",
        "meop_mpa",
    ):
        if params[key] <= 0:
            raise ValueError(f"{key} must be positive, got {params[key]}")

    if params["test_specimen_type"] not in VALID_SPECIMEN_TYPES:
        raise ValueError(
            f"test_specimen_type must be one of {VALID_SPECIMEN_TYPES}, "
            f"got '{params['test_specimen_type']}'"
        )


def check_lbb_condition(critical_crack_length_mm, through_wall_crack_length_mm):
    """
    Return True when the through-wall (leak) crack length is strictly less than
    the critical crack length at burst pressure.  At equality the condition is
    not met — zero margin is not acceptable.
    """
    if critical_crack_length_mm <= 0:
        raise ValueError("critical_crack_length_mm must be positive")
    if through_wall_crack_length_mm <= 0:
        raise ValueError("through_wall_crack_length_mm must be positive")
    return through_wall_crack_length_mm < critical_crack_length_mm


def compute_lbb_margin(critical_crack_length_mm, through_wall_crack_length_mm):
    """
    Return the LBB margin: critical / through-wall.
    Values > 1.0 satisfy the condition; <= 1.0 do not.
    """
    if through_wall_crack_length_mm <= 0:
        raise ValueError("through_wall_crack_length_mm must be positive")
    if critical_crack_length_mm <= 0:
        raise ValueError("critical_crack_length_mm must be positive")
    return critical_crack_length_mm / through_wall_crack_length_mm


def check_pressure_factors(burst_pressure_mpa, proof_pressure_mpa, meop_mpa):
    """
    Verify pressure test factors against MEOP per ECSS-E-ST-32C clause 5.3.
    Returns a dict with computed factors and boolean pass flags.
    """
    if meop_mpa <= 0:
        raise ValueError("meop_mpa must be positive")
    if burst_pressure_mpa <= 0:
        raise ValueError("burst_pressure_mpa must be positive")
    if proof_pressure_mpa <= 0:
        raise ValueError("proof_pressure_mpa must be positive")

    burst_factor = burst_pressure_mpa / meop_mpa
    proof_factor = proof_pressure_mpa / meop_mpa

    return {
        "burst_factor": round(burst_factor, 4),
        "proof_factor": round(proof_factor, 4),
        "burst_factor_ok": burst_factor >= MIN_BURST_FACTOR,
        "proof_factor_ok": proof_factor >= MIN_PROOF_FACTOR,
    }


def evaluate_specimen(specimen_type, scale_factor):
    """
    Evaluate whether the test specimen type and scale are adequate for an
    LBB system-level demonstration per clause 5.3.4.

    - coupon: adequate only for material property derivation, not system LBB.
    - sub-scale: adequate at >= 50% scale; below that requires extra justification.
    - full-scale: always adequate.

    Returns dict with 'adequate' bool and 'notes' list.
    """
    if specimen_type not in VALID_SPECIMEN_TYPES:
        raise ValueError(
            f"specimen_type must be one of {VALID_SPECIMEN_TYPES}"
        )
    if not (0 < scale_factor <= 1.0):
        raise ValueError("scale_factor must be in the range (0, 1.0]")

    notes = []
    adequate = False

    if specimen_type == "coupon":
        notes.append(
            "Coupon testing provides material crack-growth data only; "
            "a sub-scale or full-scale test is required for system-level LBB demonstration."
        )
    elif specimen_type == "sub-scale":
        if scale_factor < MIN_SUB_SCALE_FACTOR:
            notes.append(
                f"Sub-scale specimen at {scale_factor:.0%} scale is below the 50% threshold; "
                "additional justification for size-effect validity is required."
            )
        else:
            adequate = True
            notes.append(
                f"Sub-scale specimen at {scale_factor:.0%} scale meets the 50% threshold."
            )
    else:  # full-scale
        adequate = True
        notes.append("Full-scale specimen provides the highest-fidelity LBB demonstration.")

    return {"adequate": adequate, "specimen_type": specimen_type, "scale_factor": scale_factor, "notes": notes}


def estimate_cycles_to_leak(initial_flaw_depth_mm, wall_thickness_mm, crack_growth_rate_mm_per_cycle):
    """
    Estimate the number of load cycles for a surface crack to grow from the
    initial NDE-detectable flaw depth to a through-wall (leak) condition.

    Uses a linear crack-growth model (da/dN = constant) as a bounding estimate.
    For design-level assessments, integrate the Paris law over the stress
    intensity factor range.

    Raises ValueError if the initial flaw already penetrates the wall.
    """
    if initial_flaw_depth_mm <= 0:
        raise ValueError("initial_flaw_depth_mm must be positive")
    if wall_thickness_mm <= 0:
        raise ValueError("wall_thickness_mm must be positive")
    if crack_growth_rate_mm_per_cycle <= 0:
        raise ValueError("crack_growth_rate_mm_per_cycle must be positive")
    if initial_flaw_depth_mm >= wall_thickness_mm:
        raise ValueError(
            "initial_flaw_depth_mm must be less than wall_thickness_mm "
            "(through-wall crack already present at initial condition)"
        )

    remaining_depth_mm = wall_thickness_mm - initial_flaw_depth_mm
    cycles = remaining_depth_mm / crack_growth_rate_mm_per_cycle
    return round(cycles, 2)


def assess_lbb_demonstration(params):
    """
    Full LBB demonstration assessment aggregating all sub-checks.

    Expected keys in params (see validate_lbb_inputs for full list):
      critical_crack_length_mm, through_wall_crack_length_mm,
      wall_thickness_mm, burst_pressure_mpa, proof_pressure_mpa,
      meop_mpa, test_specimen_type.

    Optional keys:
      scale_factor (float, default 1.0 — assumed full-scale)
      initial_flaw_depth_mm, crack_growth_rate_mm_per_cycle (for cycle estimate)

    Returns a dict with 'passed' bool, sub-results, and 'findings' list.
    """
    validate_lbb_inputs(params)

    findings = []
    passed = True

    # LBB geometric condition
    lbb_ok = check_lbb_condition(
        params["critical_crack_length_mm"],
        params["through_wall_crack_length_mm"],
    )
    lbb_margin = compute_lbb_margin(
        params["critical_crack_length_mm"],
        params["through_wall_crack_length_mm"],
    )
    if not lbb_ok:
        findings.append(
            f"LBB condition not met: through-wall crack "
            f"({params['through_wall_crack_length_mm']} mm) >= critical crack "
            f"({params['critical_crack_length_mm']} mm); margin = {lbb_margin:.3f}"
        )
        passed = False

    # Pressure factors
    pressure = check_pressure_factors(
        params["burst_pressure_mpa"],
        params["proof_pressure_mpa"],
        params["meop_mpa"],
    )
    if not pressure["burst_factor_ok"]:
        findings.append(
            f"Burst pressure factor {pressure['burst_factor']:.3f} < {MIN_BURST_FACTOR} (MEOP)"
        )
        passed = False
    if not pressure["proof_factor_ok"]:
        findings.append(
            f"Proof pressure factor {pressure['proof_factor']:.3f} < {MIN_PROOF_FACTOR} (MEOP)"
        )
        passed = False

    # Specimen adequacy
    scale_factor = params.get("scale_factor", 1.0)
    specimen = evaluate_specimen(params["test_specimen_type"], scale_factor)
    if not specimen["adequate"]:
        findings.append(
            f"Specimen type '{params['test_specimen_type']}' at scale {scale_factor:.2f} "
            "is not adequate for system-level LBB demonstration without further justification."
        )
        passed = False

    result = {
        "passed": passed,
        "lbb_condition_met": lbb_ok,
        "lbb_margin": round(lbb_margin, 4),
        "pressure": pressure,
        "specimen": specimen,
        "findings": findings,
    }

    # Optional cycle estimate
    if "initial_flaw_depth_mm" in params and "crack_growth_rate_mm_per_cycle" in params:
        cycles = estimate_cycles_to_leak(
            params["initial_flaw_depth_mm"],
            params["wall_thickness_mm"],
            params["crack_growth_rate_mm_per_cycle"],
        )
        result["estimated_cycles_to_leak"] = cycles

    return result
