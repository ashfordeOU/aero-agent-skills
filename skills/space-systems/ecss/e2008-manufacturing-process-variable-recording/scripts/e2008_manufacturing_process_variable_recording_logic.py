#!/usr/bin/env python3
"""Process variables that have to be identified and logged before production.

Anchor: ECSS-E-ST-20-08C clause 5.4.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Before a photovoltaic assembly goes into production, the process
variables that move assembly performance have to be named and a logging
plan fixed for each. The point of doing it first is that a variable
nobody wrote down is a variable nobody recorded, and an assembly that
under-performs six months later then has no data to explain it.

A variable earns its recording plan from the performance swing it can
produce across its own control band, compared against the performance
tolerance the assembly is held to:

    swing = |sensitivity per unit| * (band_max - band_min)
    share = swing / performance_tolerance

Recording method, strongest to weakest
    continuous-logged      every unit, logged against time
    per-lot-sampled        sampled once per production lot
    witness-coupon-only    inferred from a coupon processed alongside
    not-recorded           no record at all

A variable able to consume the whole tolerance on its own is logged
continuously; one able to consume a quarter of it is sampled per lot;
the rest still need a witness record, because clause 5.4.5 asks for the
influencing variables to be logged, not merely ranked.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

RECORDING_METHODS = (
    "continuous-logged",
    "per-lot-sampled",
    "witness-coupon-only",
    "not-recorded",
)
RECORDING_STRENGTH = {
    "continuous-logged": 3,
    "per-lot-sampled": 2,
    "witness-coupon-only": 1,
    "not-recorded": 0,
}

COMBINATION_METHODS = ("root-sum-square", "linear")

GOVERNING_SHARE = 1.0
SAMPLED_SHARE = 0.25

RECORDING_READY = "recording-ready"
RECORDING_GAP = "recording-gap"
IDENTIFICATION_LATE = "identification-late"

VERDICT_RANK = {IDENTIFICATION_LATE: 0, RECORDING_GAP: 1, RECORDING_READY: 2}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    An influence share is a quotient of two products of decimal inputs,
    so a variable that sits exactly on a recording threshold can land a
    few units in the last place below it. The thresholds themselves are
    never lowered; only the comparison tolerates the representation
    error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def control_band_width(band_min, band_max):
    """Span of the control band a variable is permitted to move over."""
    low = _require_number("band_min", band_min)
    high = _require_number("band_max", band_max)
    if high <= low:
        raise ValueError(
            "band_max %g must sit above band_min %g; a band of zero width is "
            "a fixed value, not a process variable" % (high, low)
        )
    return high - low


def potential_performance_swing(sensitivity_per_unit, band_min, band_max):
    """Performance the variable can move across its whole control band."""
    sensitivity = _require_number("sensitivity_per_unit", sensitivity_per_unit)
    return abs(sensitivity) * control_band_width(band_min, band_max)


def influence_share(swing, performance_tolerance):
    """Share of the assembly performance tolerance one variable can consume."""
    value = _require_number("swing", swing)
    if value < 0.0:
        raise ValueError("swing must not be negative, got %r" % (swing,))
    tolerance = _require_positive("performance_tolerance", performance_tolerance)
    return value / tolerance


def required_recording_method(share):
    """Logging a variable earns from the share of tolerance it can consume."""
    value = _require_number("share", share)
    if value < 0.0:
        raise ValueError("share must not be negative, got %r" % (share,))
    if _at_least(value, GOVERNING_SHARE):
        return "continuous-logged"
    if _at_least(value, SAMPLED_SHARE):
        return "per-lot-sampled"
    return "witness-coupon-only"


def recording_is_adequate(declared_method, required_method):
    """Does the declared logging reach the strength the variable needs."""
    declared = _require_choice("declared_method", declared_method, RECORDING_METHODS)
    required = _require_choice("required_method", required_method, RECORDING_METHODS)
    return RECORDING_STRENGTH[declared] >= RECORDING_STRENGTH[required]


def combined_swing(swings, method="root-sum-square"):
    """Roll several independent swings into one performance figure."""
    _require_choice("method", method, COMBINATION_METHODS)
    if not isinstance(swings, (list, tuple)):
        raise ValueError("swings must be a sequence")
    values = []
    for index, swing in enumerate(swings):
        value = _require_number("swings[%d]" % index, swing)
        if value < 0.0:
            raise ValueError("swings[%d] must not be negative" % index)
        values.append(value)
    if not values:
        return 0.0
    if method == "linear":
        return math.fsum(values)
    return math.sqrt(math.fsum(v * v for v in values))


def assess_variable(variable, performance_tolerance):
    """Judge one process variable: how much it moves, how it must be logged."""
    if not isinstance(variable, dict):
        raise ValueError("variable must be a mapping, got %r" % (variable,))
    name = _require_label("variable name", variable.get("name"))
    units = _require_label("units", variable.get("units"))
    declared_method = _require_choice(
        "recording_method", variable.get("recording_method"), RECORDING_METHODS
    )
    identified_early = _require_flag(
        "identified_before_production", variable.get("identified_before_production")
    )
    swing = potential_performance_swing(
        variable.get("sensitivity_per_unit"),
        variable.get("band_min"),
        variable.get("band_max"),
    )
    share = influence_share(swing, performance_tolerance)
    required_method = required_recording_method(share)
    adequate = recording_is_adequate(declared_method, required_method)

    findings = []
    if not identified_early:
        findings.append(
            "%s was added to the variable list after production started; the "
            "units built before it was named carry no record of it" % name
        )
    if not adequate:
        findings.append(
            "%s can move %.4f of the performance tolerance across its %g %s "
            "band and is only %s; %s is required"
            % (
                name,
                share,
                control_band_width(variable.get("band_min"), variable.get("band_max")),
                units,
                declared_method,
                required_method,
            )
        )

    if not identified_early:
        verdict = IDENTIFICATION_LATE
    elif not adequate:
        verdict = RECORDING_GAP
    else:
        verdict = RECORDING_READY

    return {
        "name": name,
        "units": units,
        "band_width": control_band_width(
            variable.get("band_min"), variable.get("band_max")
        ),
        "potential_swing": swing,
        "influence_share": share,
        "declared_recording_method": declared_method,
        "required_recording_method": required_method,
        "recording_adequate": adequate,
        "identified_before_production": identified_early,
        "verdict": verdict,
        "findings": findings,
    }


def rank_variables(assessments):
    """Order the variables by the performance swing each can produce."""
    if not assessments:
        raise ValueError("no variable assessments to rank")
    return sorted(
        assessments, key=lambda a: (-a["potential_swing"], a["name"])
    )


def plan_process_variable_recording(case):
    """Full clause 5.4.5 readiness check over the declared variable list."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    tolerance = _require_positive(
        "performance_tolerance", case.get("performance_tolerance")
    )
    variables = case.get("variables")
    if not isinstance(variables, (list, tuple)) or not variables:
        raise ValueError("case must carry a non-empty variables sequence")
    seen = set()
    assessments = []
    findings = []
    for variable in variables:
        assessment = assess_variable(variable, tolerance)
        if assessment["name"] in seen:
            raise ValueError(
                "process variable %r appears twice; one entry per variable"
                % assessment["name"]
            )
        seen.add(assessment["name"])
        assessments.append(assessment)
        findings.extend(assessment["findings"])

    ranked = rank_variables(assessments)
    total = combined_swing([a["potential_swing"] for a in assessments])
    unlogged = combined_swing(
        [
            a["potential_swing"]
            for a in assessments
            if not a["recording_adequate"] or not a["identified_before_production"]
        ]
    )
    worst = min(VERDICT_RANK[a["verdict"]] for a in assessments)
    verdict = next(k for k, v in VERDICT_RANK.items() if v == worst)
    return {
        "performance_tolerance": tolerance,
        "assessments": assessments,
        "ranked_variables": [a["name"] for a in ranked],
        "governing_variable": ranked[0]["name"],
        "combined_swing": total,
        "combined_swing_linear": combined_swing(
            [a["potential_swing"] for a in assessments], method="linear"
        ),
        "unlogged_swing": unlogged,
        "unlogged_share_of_swing": (unlogged / total) if total > 0.0 else 0.0,
        "tolerance_consumed": total / tolerance,
        "verdict": verdict,
        "findings": findings,
    }
