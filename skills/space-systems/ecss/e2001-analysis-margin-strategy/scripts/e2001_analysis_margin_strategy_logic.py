#!/usr/bin/env python3
"""Margin strategy for a multipaction analysis.

Anchor: ECSS-E-ST-20-01C clause 5.3.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Two quantities govern a multipaction prediction: the critical dimension
of the gap, and the secondary-emission yield of the electrode surface.
Neither is known perfectly, and the margin the analysis must carry is
chosen from how well each one is known.

Dimension basis, best to weakest
    measured-hardware      the flight gap was measured after build
    tolerance-worst-case   the smallest gap the drawing tolerance allows
    nominal-design         the drawing value, tolerance not stacked

Yield basis, best to weakest
    surface-measured       yield curve measured on the production finish
    material-measured      yield curve measured on the base material
    generic-literature     a tabulated curve for the material family

Each step away from a measured basis adds to the required margin, and so
does the consequence of a breakdown for the mission. The build-up is a
declared policy, not a physical constant: the default below is a
starting point and a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DIMENSION_BASES = ("measured-hardware", "tolerance-worst-case", "nominal-design")
YIELD_BASES = ("surface-measured", "material-measured", "generic-literature")
CRITICALITY_LEVELS = ("catastrophic", "critical", "major", "minor")

MEASURED_DATA_STRATEGY = "measured-data-strategy"
MIXED_BASIS_STRATEGY = "mixed-basis-strategy"
BOUNDING_ENVELOPE_STRATEGY = "bounding-envelope-strategy"

DEFAULT_MARGIN_POLICY = {
    "base_margin_db": 3.0,
    "dimension_increment_db": {
        "measured-hardware": 0.0,
        "tolerance-worst-case": 1.0,
        "nominal-design": 3.0,
    },
    "yield_increment_db": {
        "surface-measured": 0.0,
        "material-measured": 1.0,
        "generic-literature": 3.0,
    },
    "criticality_increment_db": {
        "catastrophic": 3.0,
        "critical": 2.0,
        "major": 1.0,
        "minor": 0.0,
    },
    "max_margin_db": 12.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    An achieved margin is a difference of logarithms, so a case that is
    exactly on the requirement can land a few units in the last place
    below it. The required margin is never lowered; only the comparison
    tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_margin_policy(policy):
    """Check a margin build-up policy covers every basis with sane numbers."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_non_negative("base_margin_db", policy.get("base_margin_db"))
    table_specs = (
        ("dimension_increment_db", DIMENSION_BASES),
        ("yield_increment_db", YIELD_BASES),
        ("criticality_increment_db", CRITICALITY_LEVELS),
    )
    for key, keys_needed in table_specs:
        table = policy.get(key)
        if not isinstance(table, dict):
            raise ValueError("policy %s must be a mapping" % key)
        missing = set(keys_needed) - set(table)
        if missing:
            raise ValueError(
                "policy %s is missing entries: %s" % (key, ", ".join(sorted(missing)))
            )
        for entry in keys_needed:
            _require_non_negative("policy %s[%s]" % (key, entry), table[entry])
    cap = _require_positive("max_margin_db", policy.get("max_margin_db"))
    if cap < policy["base_margin_db"]:
        raise ValueError("policy max_margin_db is below base_margin_db")
    return policy


def effective_gap_m(
    dimension_basis,
    nominal_gap_m=None,
    tolerance_m=None,
    measured_gap_m=None,
):
    """Gap the analysis has to use for the declared dimension basis."""
    _require_choice("dimension_basis", dimension_basis, DIMENSION_BASES)
    if dimension_basis == "measured-hardware":
        if measured_gap_m is None:
            raise ValueError("measured-hardware basis needs measured_gap_m")
        return _require_positive("measured_gap_m", measured_gap_m)
    nominal = _require_positive("nominal_gap_m", nominal_gap_m)
    if dimension_basis == "nominal-design":
        return nominal
    if tolerance_m is None:
        raise ValueError("tolerance-worst-case basis needs tolerance_m")
    tolerance = _require_non_negative("tolerance_m", tolerance_m)
    worst = nominal - tolerance
    if worst <= 0.0:
        raise ValueError(
            "tolerance %g m consumes the nominal gap %g m; the geometry is undefined"
            % (tolerance, nominal)
        )
    return worst


def effective_peak_yield(yield_basis, declared_peak_yield, bounding_peak_yield=None):
    """Peak secondary-emission yield the analysis has to carry.

    A generic basis is only admissible against a bounding value: the
    tabulated family curve is not a property of this surface, so the
    analysis takes whichever value is higher.
    """
    _require_choice("yield_basis", yield_basis, YIELD_BASES)
    declared = _require_positive("declared_peak_yield", declared_peak_yield)
    if yield_basis != "generic-literature":
        return {"peak_yield": declared, "bounded": False, "findings": []}
    if bounding_peak_yield is None:
        raise ValueError(
            "generic-literature basis needs a bounding_peak_yield to work against"
        )
    bounding = _require_positive("bounding_peak_yield", bounding_peak_yield)
    findings = []
    if declared < bounding:
        findings.append(
            "declared peak yield %.3f is below the bounding family value %.3f; "
            "the bounding value is carried instead" % (declared, bounding)
        )
    return {
        "peak_yield": max(declared, bounding),
        "bounded": True,
        "findings": findings,
    }


def required_margin_db(
    dimension_basis, yield_basis, criticality, policy=DEFAULT_MARGIN_POLICY
):
    """Build up the required multipaction margin from the data knowledge."""
    validate_margin_policy(policy)
    _require_choice("dimension_basis", dimension_basis, DIMENSION_BASES)
    _require_choice("yield_basis", yield_basis, YIELD_BASES)
    _require_choice("criticality", criticality, CRITICALITY_LEVELS)
    total = (
        policy["base_margin_db"]
        + policy["dimension_increment_db"][dimension_basis]
        + policy["yield_increment_db"][yield_basis]
        + policy["criticality_increment_db"][criticality]
    )
    return min(float(total), float(policy["max_margin_db"]))


def select_margin_strategy(dimension_basis, yield_basis):
    """Pick the strategy the two data bases jointly force, with its duties."""
    _require_choice("dimension_basis", dimension_basis, DIMENSION_BASES)
    _require_choice("yield_basis", yield_basis, YIELD_BASES)
    weakest = {"nominal-design", "generic-literature"}
    duties = []
    if dimension_basis == "nominal-design":
        duties.append("stack the drawing tolerance and rerun on the smallest gap")
    if dimension_basis == "tolerance-worst-case":
        duties.append("measure the as-built gap to retire the tolerance increment")
    if yield_basis == "generic-literature":
        duties.append("carry a bounding yield curve for the material family")
    if yield_basis == "material-measured":
        duties.append("measure the production finish to retire the yield increment")
    if dimension_basis in weakest or yield_basis in weakest:
        strategy = BOUNDING_ENVELOPE_STRATEGY
    elif dimension_basis == "measured-hardware" and yield_basis == "surface-measured":
        strategy = MEASURED_DATA_STRATEGY
    else:
        strategy = MIXED_BASIS_STRATEGY
    return {
        "strategy": strategy,
        "dimension_basis": dimension_basis,
        "yield_basis": yield_basis,
        "duties": duties,
    }


def achieved_margin_db(breakdown_power_w, operating_power_w):
    """Margin of the predicted breakdown level over the operating level."""
    breakdown = _require_positive("breakdown_power_w", breakdown_power_w)
    operating = _require_positive("operating_power_w", operating_power_w)
    return 10.0 * math.log10(breakdown / operating)


def margin_reduction_from_measurement(
    dimension_basis, yield_basis, criticality, policy=DEFAULT_MARGIN_POLICY
):
    """Decibel the requirement would drop if both bases became measured."""
    current = required_margin_db(dimension_basis, yield_basis, criticality, policy)
    best = required_margin_db(
        "measured-hardware", "surface-measured", criticality, policy
    )
    return current - best


def plan_margin_strategy(case, policy=DEFAULT_MARGIN_POLICY):
    """Full clause 5.3.3.1 strategy choice with a compliance verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    dimension_basis = _require_choice(
        "dimension_basis", case.get("dimension_basis"), DIMENSION_BASES
    )
    yield_basis = _require_choice("yield_basis", case.get("yield_basis"), YIELD_BASES)
    criticality = _require_choice(
        "criticality", case.get("criticality"), CRITICALITY_LEVELS
    )
    gap = effective_gap_m(
        dimension_basis,
        nominal_gap_m=case.get("nominal_gap_m"),
        tolerance_m=case.get("tolerance_m"),
        measured_gap_m=case.get("measured_gap_m"),
    )
    yield_result = effective_peak_yield(
        yield_basis,
        case.get("declared_peak_yield"),
        case.get("bounding_peak_yield"),
    )
    strategy = select_margin_strategy(dimension_basis, yield_basis)
    required = required_margin_db(dimension_basis, yield_basis, criticality, policy)
    findings = list(yield_result["findings"])
    result = {
        "strategy": strategy["strategy"],
        "duties": strategy["duties"],
        "effective_gap_m": gap,
        "effective_peak_yield": yield_result["peak_yield"],
        "yield_is_bounded": yield_result["bounded"],
        "required_margin_db": required,
        "margin_reduction_available_db": margin_reduction_from_measurement(
            dimension_basis, yield_basis, criticality, policy
        ),
        "findings": findings,
    }
    breakdown = case.get("predicted_breakdown_power_w")
    operating = case.get("operating_power_w")
    if breakdown is None or operating is None:
        result.update(
            {
                "achieved_margin_db": None,
                "compliant": None,
                "verdict": "margin-not-evaluated",
            }
        )
        findings.append(
            "no predicted breakdown level or operating level supplied; the "
            "strategy is fixed but the margin is not yet demonstrated"
        )
        return result
    achieved = achieved_margin_db(breakdown, operating)
    compliant = _at_least(achieved, required)
    result.update(
        {
            "achieved_margin_db": achieved,
            "compliant": compliant,
            "verdict": "margin-met" if compliant else "margin-not-met",
        }
    )
    if not compliant:
        findings.append(
            "achieved %.3f dB against a required %.3f dB on a %s"
            % (achieved, required, strategy["strategy"])
        )
    return result
