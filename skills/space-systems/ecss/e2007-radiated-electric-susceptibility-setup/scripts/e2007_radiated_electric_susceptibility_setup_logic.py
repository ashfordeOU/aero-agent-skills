#!/usr/bin/env python3
"""Radiated electric susceptibility chamber arrangement, clause 5.4.11.3.

Paraphrased procedure, no verbatim standard text. The clause describes how the
chamber is laid out so that the unit under test and the harness that leaves it
are both standing inside the field the antenna projects. This module models
exactly that:

  baseline chamber geometry + declared deltas -> derived arrangement
  antenna separation and beamwidth            -> illuminated span at the unit
  unit face and harness lateral run           -> span the exposure must cover
  realized bench measurements                 -> deviation -> category
  boolean provisions (bond, absorber, probe)  -> present or a finding
  aggregate                                   -> arrangement verdict

An exposure that reaches only part of the unit or leaves a stretch of harness
outside the illuminated span is not a weaker test, it is a test of something
other than what the report will claim, so the footprint is computed rather
than assumed.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerance. Deviations are differences of floats, so a value that
# sits exactly on a bound can land a few units in the last place either side
# of it. The tolerance absorbs that only; it never widens a bound.
TOL = 1e-9

# Parameters of the chamber arrangement the method starts from. A "nominal"
# parameter must land inside nominal +/- tolerance, a "maximum" parameter must
# not exceed its limit, a "minimum" parameter must not fall below it. Lengths
# are metres, resistances milliohm.
BASELINE_ARRANGEMENT = {
    "antenna-to-unit-separation-m": {
        "kind": "nominal",
        "nominal": 1.0,
        "tolerance": 0.05,
    },
    "antenna-boresight-height-m": {
        "kind": "nominal",
        "nominal": 0.75,
        "tolerance": 0.05,
    },
    "harness-height-above-ground-plane-m": {
        "kind": "nominal",
        "nominal": 0.05,
        "tolerance": 0.005,
    },
    "exposed-harness-run-m": {"kind": "nominal", "nominal": 1.5, "tolerance": 0.10},
    "field-probe-lateral-offset-m": {
        "kind": "nominal",
        "nominal": 0.30,
        "tolerance": 0.05,
    },
    "unit-to-plane-bond-resistance-mohm": {"kind": "maximum", "limit": 2.5},
    "absorber-to-antenna-clearance-m": {"kind": "minimum", "limit": 0.50},
}

# Provisions the arrangement must carry whatever the geometry turns out to be.
REQUIRED_PROVISIONS = (
    "chamber-walls-absorber-lined",
    "unit-bonded-to-ground-plane",
    "harness-face-presented-to-antenna",
    "field-probe-clear-of-unit-shadow",
)

# Fields describing the illumination the antenna projects at the unit plane.
ILLUMINATION_FIELDS = (
    "antenna-beamwidth-deg",
    "unit-face-width-m",
    "harness-lateral-span-m",
)

CATEGORY_CONFORMING = "conforming"
CATEGORY_DECLARED_DEVIATION = "declared-deviation"
CATEGORY_NONCONFORMING = "nonconforming"
CATEGORIES = (
    CATEGORY_CONFORMING,
    CATEGORY_DECLARED_DEVIATION,
    CATEGORY_NONCONFORMING,
)

VERDICT_CONFORMING = "arrangement-conforming"
VERDICT_REJECTED = "arrangement-rejected"


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
    """Return the recognized arrangement parameter name for a raw name."""
    if not isinstance(name, str):
        raise ValueError("parameter name must be a string, got %r" % (name,))
    key = name.strip().lower()
    if key not in BASELINE_ARRANGEMENT:
        raise ValueError(
            "unrecognized arrangement parameter %r; recognized: %s"
            % (name, ", ".join(sorted(BASELINE_ARRANGEMENT)))
        )
    return key


def parameter_bounds(name, spec=None):
    """Return the (low, high) band a parameter value has to land inside."""
    key = normalize_parameter(name)
    spec = BASELINE_ARRANGEMENT[key] if spec is None else spec
    kind = spec["kind"]
    if kind == "nominal":
        nominal = float(spec["nominal"])
        tolerance = float(spec["tolerance"])
        if tolerance <= 0.0:
            raise ValueError("%s: tolerance must be > 0, got %g" % (key, tolerance))
        return (nominal - tolerance, nominal + tolerance)
    limit = float(spec["limit"])
    if limit <= 0.0:
        raise ValueError("%s: limit must be > 0, got %g" % (key, limit))
    if kind == "maximum":
        return (0.0, limit)
    return (limit, float("inf"))


def derive_arrangement(deltas=None):
    """Apply the method's declared deltas to the baseline chamber arrangement.

    deltas: mapping of parameter name -> replacement spec. A replacement keeps
    the parameter kind of the baseline and is refused when the parameter is not
    recognized, the kind is rewritten, an unknown field appears, or the
    replacement leaves no allowed band.
    """
    derived = {}
    for key, spec in BASELINE_ARRANGEMENT.items():
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
        base = BASELINE_ARRANGEMENT[key]
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


def illuminated_span(separation_m, beamwidth_deg):
    """Width of the field footprint the antenna throws at the unit plane.

    The half-power beam subtends beamwidth_deg at the antenna, so at a
    separation d the footprint is 2*d*tan(beamwidth/2). Doubling the
    separation doubles the span, which is why a cramped chamber and a wide
    unit are not compatible however much power the amplifier can deliver.
    """
    distance = _number({"v": separation_m}, "v", "separation_m")
    beamwidth = _number({"v": beamwidth_deg}, "v", "beamwidth_deg")
    if distance <= 0.0:
        raise ValueError("separation_m must be > 0, got %g" % distance)
    if not (0.0 < beamwidth < 180.0):
        raise ValueError("beamwidth_deg must be in (0, 180), got %g" % beamwidth)
    return 2.0 * distance * math.tan(math.radians(beamwidth) / 2.0)


def required_span(unit_face_width_m, harness_lateral_span_m):
    """Width the exposure has to cover: the unit face plus the harness beside it."""
    face = _number({"v": unit_face_width_m}, "v", "unit_face_width_m")
    harness = _number({"v": harness_lateral_span_m}, "v", "harness_lateral_span_m")
    if face <= 0.0:
        raise ValueError("unit_face_width_m must be > 0, got %g" % face)
    if harness < 0.0:
        raise ValueError("harness_lateral_span_m must be >= 0, got %g" % harness)
    return face + harness


def validate_illumination(illumination):
    """Validate the illumination record and return it normalized."""
    where = "illumination"
    if not isinstance(illumination, dict):
        raise ValueError("%s: must be a mapping of field -> value" % where)
    normalized = {}
    for field in ILLUMINATION_FIELDS:
        normalized[field] = _number(illumination, field, where)
    for field in illumination:
        if field not in ILLUMINATION_FIELDS:
            raise ValueError("%s: unrecognized field %r" % (where, field))
    return normalized


def illumination_coverage(separation_m, illumination):
    """Compare the footprint the antenna projects against the span it must cover."""
    checked = validate_illumination(illumination)
    span = illuminated_span(separation_m, checked["antenna-beamwidth-deg"])
    needed = required_span(
        checked["unit-face-width-m"], checked["harness-lateral-span-m"]
    )
    margin = span - needed
    covered = margin > 0.0 or math.isclose(margin, 0.0, rel_tol=0.0, abs_tol=TOL)
    return {
        "illuminated_span_m": span,
        "required_span_m": needed,
        "margin_m": margin,
        "covered": covered,
    }


def parameter_deviation(name, value, arrangement=None):
    """Signed distance from the allowed band: 0 inside, otherwise the overrun."""
    key = normalize_parameter(name)
    spec = (arrangement or BASELINE_ARRANGEMENT)[key]
    measured = _number({"v": value}, "v", key)
    if measured < 0.0:
        raise ValueError("%s: measured value must be >= 0, got %g" % (key, measured))
    low, high = parameter_bounds(key, spec)
    if measured < low and not math.isclose(measured, low, rel_tol=0.0, abs_tol=TOL):
        return measured - low
    if high != float("inf") and measured > high:
        if not math.isclose(measured, high, rel_tol=0.0, abs_tol=TOL):
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
    """Validate the boolean provisions of the chamber and return them normalized."""
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


def assess_chamber_arrangement(
    measured,
    provisions,
    illumination,
    deltas=None,
    declared_deviations=(),
):
    """Full clause 5.4.11.3 chamber-arrangement assessment.

    measured: mapping of parameter name -> realized value in the chamber.
    provisions: mapping of the boolean provisions to their realized state.
    illumination: beamwidth and the spans the exposure has to reach.
    deltas: the method's declared changes to the baseline arrangement.
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
            "measured: the chamber record does not report %s" % ", ".join(absent)
        )

    checked = validate_provisions(provisions)
    coverage = illumination_coverage(
        normalized["antenna-to-unit-separation-m"], illumination
    )

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

    if not coverage["covered"]:
        findings.append(
            "illuminated span %g m does not reach the %g m the unit and harness "
            "occupy" % (coverage["illuminated_span_m"], coverage["required_span_m"])
        )

    worst = max(parameters, key=lambda p: (abs(p["deviation"]), p["parameter"]))
    return {
        "arrangement": arrangement,
        "parameters": parameters,
        "provisions": checked,
        "coverage": coverage,
        "counts": counts,
        "governing_parameter": worst["parameter"],
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_CONFORMING if not findings else VERDICT_REJECTED,
    }
