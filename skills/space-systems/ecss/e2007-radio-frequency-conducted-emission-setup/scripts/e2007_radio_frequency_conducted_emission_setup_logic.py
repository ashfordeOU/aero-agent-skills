#!/usr/bin/env python3
"""Conducted-emission bench arrangement, ECSS-E-ST-20-07C clause 5.4.3.3.

Paraphrased procedure, no verbatim standard text. The clause does not describe
a bench from scratch: it takes the general equipment arrangement used across
the discipline and states the changes the higher-band conducted-emission
method makes to it. This module models exactly that:

  baseline geometry + declared deltas -> derived arrangement
  realized bench measurements         -> deviation per parameter -> category
  boolean provisions (bond, routing)  -> present or a finding
  aggregate                           -> setup verdict with findings

A delta that is not declared, or that pushes a parameter outside its allowed
band, is refused at derivation time rather than discovered later in the run.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerance. Deviations are differences of floats, so a value
# sitting exactly on a bound can land a few units in the last place either
# side of it. The tolerance absorbs that only; it never widens a bound.
TOL = 1e-9

# Parameters of the general arrangement the method starts from. A "nominal"
# parameter must land inside nominal +/- tolerance; a "maximum" parameter
# must not exceed its limit. Lengths are metres, resistances milliohm.
BASELINE_PARAMETERS = {
    "power-lead-length-m": {"kind": "nominal", "nominal": 2.0, "tolerance": 0.10},
    "lead-height-above-ground-plane-m": {
        "kind": "nominal",
        "nominal": 0.05,
        "tolerance": 0.005,
    },
    "probe-to-connector-distance-m": {
        "kind": "nominal",
        "nominal": 0.05,
        "tolerance": 0.01,
    },
    "eut-edge-to-plane-edge-m": {"kind": "nominal", "nominal": 0.10, "tolerance": 0.02},
    "power-to-signal-harness-separation-m": {
        "kind": "nominal",
        "nominal": 0.10,
        "tolerance": 0.02,
    },
    "eut-to-plane-bond-resistance-mohm": {"kind": "maximum", "limit": 2.5},
}

# Provisions the arrangement must carry regardless of geometry.
REQUIRED_PROVISIONS = (
    "ground-plane-bonded",
    "power-leads-separated-from-signal-harness",
    "probe-clamped-around-single-lead",
)

CATEGORY_CONFORMING = "conforming"
CATEGORY_DECLARED_DEVIATION = "declared-deviation"
CATEGORY_NONCONFORMING = "nonconforming"
CATEGORIES = (
    CATEGORY_CONFORMING,
    CATEGORY_DECLARED_DEVIATION,
    CATEGORY_NONCONFORMING,
)

VERDICT_CONFORMING = "setup-conforming"
VERDICT_REJECTED = "setup-rejected"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def normalize_parameter(name):
    """Return the recognized baseline parameter name for a raw name."""
    if not isinstance(name, str):
        raise ValueError("parameter name must be a string, got %r" % (name,))
    key = name.strip().lower()
    if key not in BASELINE_PARAMETERS:
        raise ValueError(
            "unrecognized arrangement parameter %r; recognized: %s"
            % (name, ", ".join(sorted(BASELINE_PARAMETERS)))
        )
    return key


def parameter_bounds(name, spec=None):
    """Return the (low, high) band a parameter value has to land inside."""
    key = normalize_parameter(name)
    spec = BASELINE_PARAMETERS[key] if spec is None else spec
    if spec["kind"] == "nominal":
        nominal = float(spec["nominal"])
        tolerance = float(spec["tolerance"])
        if tolerance <= 0.0:
            raise ValueError("%s: tolerance must be > 0, got %g" % (key, tolerance))
        return (nominal - tolerance, nominal + tolerance)
    limit = float(spec["limit"])
    if limit <= 0.0:
        raise ValueError("%s: limit must be > 0, got %g" % (key, limit))
    return (0.0, limit)


def derive_arrangement(deltas=None):
    """Apply the method's declared deltas to the general arrangement.

    deltas: mapping of parameter name -> replacement spec. Each replacement
    keeps the parameter kind of the baseline and is refused when it is not a
    recognized parameter, changes the kind, or collapses the allowed band.
    """
    derived = {}
    for key, spec in BASELINE_PARAMETERS.items():
        derived[key] = dict(spec)
    if deltas is None:
        return derived
    if not isinstance(deltas, dict):
        raise ValueError("deltas: must be a mapping of parameter -> replacement")
    for name in deltas:
        key = normalize_parameter(name)
        replacement = deltas[name]
        if not isinstance(replacement, dict):
            raise ValueError("deltas[%s]: replacement must be a mapping" % key)
        base = BASELINE_PARAMETERS[key]
        spec = dict(base)
        for field in replacement:
            if field not in base:
                raise ValueError(
                    "deltas[%s]: unknown field %r for a %s parameter"
                    % (key, field, base["kind"])
                )
            if field == "kind":
                raise ValueError(
                    "deltas[%s]: a delta may move a bound, not change the "
                    "parameter kind" % key
                )
            spec[field] = _number(replacement, field, "deltas[%s]" % key)
        low, high = parameter_bounds(key, spec)
        if high <= low:
            raise ValueError(
                "deltas[%s]: the replacement leaves no allowed band (%g-%g)"
                % (key, low, high)
            )
        derived[key] = spec
    return derived


def parameter_deviation(name, value, arrangement=None):
    """Signed distance from the allowed band: 0 inside, otherwise the overrun."""
    key = normalize_parameter(name)
    spec = (arrangement or BASELINE_PARAMETERS)[key]
    measured = _number({"v": value}, "v", key)
    if measured < 0.0:
        raise ValueError("%s: measured value must be >= 0, got %g" % (key, measured))
    low, high = parameter_bounds(key, spec)
    if measured < low and not math.isclose(measured, low, rel_tol=0.0, abs_tol=TOL):
        return measured - low
    if measured > high and not math.isclose(measured, high, rel_tol=0.0, abs_tol=TOL):
        return measured - high
    return 0.0


def categorize_parameter(name, value, arrangement=None, declared_deviations=()):
    """Categorize one realized parameter against the derived arrangement."""
    key = normalize_parameter(name)
    if not isinstance(declared_deviations, (list, tuple, set, frozenset)):
        raise ValueError("declared_deviations must be a collection of names")
    declared = set(normalize_parameter(d) for d in declared_deviations)
    deviation = parameter_deviation(key, value, arrangement)
    if math.isclose(deviation, 0.0, rel_tol=0.0, abs_tol=TOL):
        return CATEGORY_CONFORMING
    if key in declared:
        return CATEGORY_DECLARED_DEVIATION
    return CATEGORY_NONCONFORMING


def validate_provisions(provisions):
    """Validate the boolean provisions of the bench and return them normalized."""
    where = "provisions"
    if not isinstance(provisions, dict):
        raise ValueError("%s: must be a mapping of provision -> boolean" % where)
    normalized = {}
    for name in REQUIRED_PROVISIONS:
        if name not in provisions:
            raise ValueError("%s: missing required provision %r" % (where, name))
        value = provisions[name]
        if not isinstance(value, bool):
            raise ValueError(
                "%s: provision %r must be a boolean, got %r" % (where, name, value)
            )
        normalized[name] = value
    for name in provisions:
        if name not in REQUIRED_PROVISIONS:
            raise ValueError("%s: unrecognized provision %r" % (where, name))
    return normalized


def assess_bench_arrangement(
    measured,
    provisions,
    deltas=None,
    declared_deviations=(),
):
    """Full clause 5.4.3.3 bench-arrangement assessment.

    measured: mapping of parameter name -> realized value on the bench.
    provisions: mapping of the boolean provisions to their realized state.
    deltas: the method's declared changes to the general arrangement.
    declared_deviations: parameters a formally accepted departure covers.
    """
    if not isinstance(measured, dict):
        raise ValueError("measured: must be a mapping of parameter -> value")
    arrangement = derive_arrangement(deltas)
    normalized = {}
    for name in measured:
        key = normalize_parameter(name)
        if key in normalized:
            raise ValueError("measured: parameter %r given more than once" % key)
        normalized[key] = measured[name]
    absent = tuple(sorted(set(arrangement) - set(normalized)))
    if absent:
        raise ValueError(
            "measured: the bench record does not report %s" % ", ".join(absent)
        )

    checked = validate_provisions(provisions)

    parameters = []
    counts = dict((category, 0) for category in CATEGORIES)
    findings = []
    limitations = []
    for key in sorted(normalized):
        deviation = parameter_deviation(key, normalized[key], arrangement)
        category = categorize_parameter(
            key, normalized[key], arrangement, declared_deviations
        )
        counts[category] += 1
        low, high = parameter_bounds(key, arrangement[key])
        parameters.append(
            {
                "parameter": key,
                "value": float(normalized[key]),
                "allowed_band": (low, high),
                "deviation": deviation,
                "category": category,
            }
        )
        if category == CATEGORY_NONCONFORMING:
            findings.append(
                "%s is %g outside its allowed band %g-%g"
                % (key, abs(deviation), low, high)
            )
        elif category == CATEGORY_DECLARED_DEVIATION:
            limitations.append(
                "%s runs %g outside its band under a declared deviation"
                % (key, abs(deviation))
            )

    for name in REQUIRED_PROVISIONS:
        if not checked[name]:
            findings.append("required provision not in place: %s" % name)

    worst = max(parameters, key=lambda p: (abs(p["deviation"]), p["parameter"]))
    return {
        "arrangement": arrangement,
        "parameters": parameters,
        "provisions": checked,
        "counts": counts,
        "governing_parameter": worst["parameter"],
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_CONFORMING if not findings else VERDICT_REJECTED,
    }
