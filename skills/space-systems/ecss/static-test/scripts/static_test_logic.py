#!/usr/bin/env python3
"""ECSS-E-ST-32C clause 4.6.3.7 static structural test assessment
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
ECSS structures standard's static test clause covers three concerns:
(1) test objectives -- whether the test is a qualification test to
demonstrate structural integrity to ultimate/yield levels or an
acceptance test to proof-load flight hardware; (2) load application
-- incremental step loading from zero to the target test load with a
minimum of three steps and a hold period at each step; and (3) success
criteria -- no fracture at the test load (margin of safety >= 0),
residual deformation after unloading within the specified allowable,
and measured stiffness within a tolerance band of the analysis model
prediction. This module implements test-load computation, load-step
generation, margin-of-safety calculation, residual-deformation
checking, stiffness-correlation checking, and a full assessment
aggregator. It does not implement dynamic load time histories,
fatigue cycle counting, or nonlinear large-deformation solvers.
"""

LOAD_CASE_TYPES = frozenset({
    "tension",
    "compression",
    "shear",
    "bending",
    "torsion",
    "combined",
    "pressure",
    "thermal_mechanical",
})

TEST_TYPES = frozenset({"qualification", "acceptance"})

# Multipliers applied to the design limit load to derive the target test load.
LOAD_FACTORS = {
    "qualification_ultimate": 1.5,
    "qualification_yield": 1.1,
    "acceptance_proof": 1.1,
}

# Default factor type used when a test type is provided without an explicit factor.
_DEFAULT_FACTOR_FOR_TEST_TYPE = {
    "qualification": "qualification_ultimate",
    "acceptance": "acceptance_proof",
}

DEFAULT_STIFFNESS_TOLERANCE_PCT = 10.0

MIN_LOAD_STEPS = 3


def categorize_load_case(load_case_type):
    """Return load_case_type if it is a recognized structural load-case
    category. Raises ValueError for types outside the known set, so
    unrecognized cases fail explicitly rather than being silently dropped."""
    if load_case_type in LOAD_CASE_TYPES:
        return load_case_type
    raise ValueError(
        "unrecognized load-case type %r; must be one of %s"
        % (load_case_type, sorted(LOAD_CASE_TYPES))
    )


def compute_test_load(design_limit_load_n, factor_type):
    """Target test load in Newtons: design_limit_load_n multiplied by the
    factor for factor_type. factor_type must be a key of LOAD_FACTORS.
    Raises ValueError for a non-positive design_limit_load_n or an
    unrecognized factor_type."""
    if design_limit_load_n <= 0:
        raise ValueError(
            "design_limit_load_n must be > 0, got %r" % (design_limit_load_n,)
        )
    if factor_type not in LOAD_FACTORS:
        raise ValueError(
            "unrecognized factor_type %r; must be one of %s"
            % (factor_type, sorted(LOAD_FACTORS))
        )
    return design_limit_load_n * LOAD_FACTORS[factor_type]


def margin_of_safety(allowable_n, applied_n):
    """Margin of safety = (allowable_n / applied_n) - 1. A non-negative
    result means the load case passes; a negative result is a failure.
    Raises ValueError if applied_n <= 0 or either argument is negative."""
    if allowable_n < 0:
        raise ValueError("allowable_n must be >= 0, got %r" % (allowable_n,))
    if applied_n <= 0:
        raise ValueError("applied_n must be > 0, got %r" % (applied_n,))
    return (allowable_n / applied_n) - 1.0


def generate_load_steps(target_load_n, num_steps):
    """List of num_steps evenly-spaced load levels from
    target_load_n/num_steps up to target_load_n, representing the
    incremental load-application sequence. The pre-load baseline at 0 N
    is recorded before this sequence begins and is not included here.
    Raises ValueError if num_steps < MIN_LOAD_STEPS or target_load_n <= 0."""
    if target_load_n <= 0:
        raise ValueError(
            "target_load_n must be > 0, got %r" % (target_load_n,)
        )
    if num_steps < MIN_LOAD_STEPS:
        raise ValueError(
            "num_steps must be >= %d, got %r" % (MIN_LOAD_STEPS, num_steps)
        )
    step_size = target_load_n / num_steps
    return [step_size * i for i in range(1, num_steps + 1)]


def check_residual_deformation(measured_mm, allowable_mm):
    """True if the post-test residual deformation (measured_mm) is within
    the specified allowable (allowable_mm); False if it exceeds the
    allowable. Raises ValueError for negative inputs."""
    if measured_mm < 0:
        raise ValueError(
            "measured_mm must be >= 0, got %r" % (measured_mm,)
        )
    if allowable_mm < 0:
        raise ValueError(
            "allowable_mm must be >= 0, got %r" % (allowable_mm,)
        )
    return measured_mm <= allowable_mm


def check_stiffness_correlation(
    measured_n_per_mm,
    predicted_n_per_mm,
    tolerance_pct=DEFAULT_STIFFNESS_TOLERANCE_PCT,
):
    """(within_tolerance: bool, deviation_pct: float).

    deviation_pct = (measured - predicted) / predicted * 100.
    within_tolerance is True when abs(deviation_pct) <= tolerance_pct.
    Raises ValueError for non-positive stiffness values or negative
    tolerance."""
    if measured_n_per_mm <= 0:
        raise ValueError(
            "measured_n_per_mm must be > 0, got %r" % (measured_n_per_mm,)
        )
    if predicted_n_per_mm <= 0:
        raise ValueError(
            "predicted_n_per_mm must be > 0, got %r" % (predicted_n_per_mm,)
        )
    if tolerance_pct < 0:
        raise ValueError(
            "tolerance_pct must be >= 0, got %r" % (tolerance_pct,)
        )
    deviation_pct = (measured_n_per_mm - predicted_n_per_mm) / predicted_n_per_mm * 100.0
    within_tolerance = abs(deviation_pct) <= tolerance_pct
    return within_tolerance, deviation_pct


def evaluate_load_case(
    load_case_id,
    allowable_n,
    applied_n,
    residual_mm=None,
    allowable_residual_mm=None,
    measured_stiffness_n_per_mm=None,
    predicted_stiffness_n_per_mm=None,
    stiffness_tolerance_pct=DEFAULT_STIFFNESS_TOLERANCE_PCT,
):
    """Violation list for one load case. Checks:
    (1) margin of safety -- must be >= 0;
    (2) residual deformation -- if both residual_mm and allowable_residual_mm
        are provided, measured must not exceed allowable;
    (3) stiffness correlation -- if both stiffness values are provided,
        deviation must be within tolerance_pct.
    Returns a list of violation dicts; an empty list means compliant.
    Does not mutate any input."""
    violations = []

    ms = margin_of_safety(allowable_n, applied_n)
    if ms < 0:
        violations.append({
            "issue": "negative_margin_of_safety",
            "load_case_id": load_case_id,
            "margin_of_safety": ms,
            "allowable_n": allowable_n,
            "applied_n": applied_n,
        })

    if residual_mm is not None and allowable_residual_mm is not None:
        if not check_residual_deformation(residual_mm, allowable_residual_mm):
            violations.append({
                "issue": "residual_deformation_exceeded",
                "load_case_id": load_case_id,
                "measured_mm": residual_mm,
                "allowable_mm": allowable_residual_mm,
            })

    if (
        measured_stiffness_n_per_mm is not None
        and predicted_stiffness_n_per_mm is not None
    ):
        within, deviation = check_stiffness_correlation(
            measured_stiffness_n_per_mm,
            predicted_stiffness_n_per_mm,
            stiffness_tolerance_pct,
        )
        if not within:
            violations.append({
                "issue": "stiffness_correlation_out_of_band",
                "load_case_id": load_case_id,
                "deviation_pct": deviation,
                "tolerance_pct": stiffness_tolerance_pct,
            })

    return violations


def assess_static_test(test_data):
    """Full static test assessment across all load cases.

    test_data keys:
      "test_type"            : str -- "qualification" or "acceptance"
      "design_limit_load_n"  : float -- design limit load in Newtons
      "load_cases"           : list of dicts, each with:
          "load_case_id"               : str
          "load_case_type"             : str (must be in LOAD_CASE_TYPES)
          "allowable_n"                : float
          "applied_n"                  : float
          "residual_mm"                : float | None
          "allowable_residual_mm"      : float | None
          "measured_stiffness_n_per_mm": float | None
          "predicted_stiffness_n_per_mm": float | None

    Returns:
      {
        "test_type"         : str,
        "factor_type"       : str,
        "target_test_load_n": float,
        "violations"        : [...],
        "compliant"         : bool,
      }

    Raises ValueError for an unrecognized test_type, unrecognized
    load_case_type, or invalid numeric inputs."""
    test_type = test_data["test_type"]
    if test_type not in TEST_TYPES:
        raise ValueError(
            "unrecognized test_type %r; must be one of %s"
            % (test_type, sorted(TEST_TYPES))
        )

    factor_type = _DEFAULT_FACTOR_FOR_TEST_TYPE[test_type]
    target_load = compute_test_load(test_data["design_limit_load_n"], factor_type)

    all_violations = []
    for lc in test_data.get("load_cases", []):
        categorize_load_case(lc["load_case_type"])
        lc_violations = evaluate_load_case(
            load_case_id=lc["load_case_id"],
            allowable_n=lc["allowable_n"],
            applied_n=lc["applied_n"],
            residual_mm=lc.get("residual_mm"),
            allowable_residual_mm=lc.get("allowable_residual_mm"),
            measured_stiffness_n_per_mm=lc.get("measured_stiffness_n_per_mm"),
            predicted_stiffness_n_per_mm=lc.get("predicted_stiffness_n_per_mm"),
        )
        all_violations.extend(lc_violations)

    return {
        "test_type": test_type,
        "factor_type": factor_type,
        "target_test_load_n": target_load,
        "violations": all_violations,
        "compliant": len(all_violations) == 0,
    }
