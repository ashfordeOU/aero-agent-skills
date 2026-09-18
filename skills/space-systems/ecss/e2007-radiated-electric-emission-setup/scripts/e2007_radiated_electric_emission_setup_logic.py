#!/usr/bin/env python3
"""Radiated electric-emission bench layout, ECSS-E-ST-20-07C clause 5.4.6.3.

Paraphrased procedure, no verbatim standard text. The clause fixes two things
at once: where the parts of the bench sit relative to each other, and how the
unit is turned to face the measuring antennas. A layout that is geometrically
perfect but only ever presents one side of the unit has not satisfied the
clause, and neither has a complete set of presentations made on a bench whose
separation or bonding is out of band. This module models both halves:

  chosen separation + declared deltas -> derived layout bounds
  realized measurements               -> deviation -> category -> governing
  presentation log                    -> face x polarization coverage
  separation vs lowest frequency      -> near-field or far-field regime
  aggregate                           -> layout verdict with findings

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerance. Deviations are differences of floats, so a value
# sitting exactly on a bound can land a few units in the last place either
# side of it. The tolerance absorbs that only; it never widens a bound.
TOL = 1e-9

# Free-space propagation speed, metres per second.
SPEED_OF_LIGHT_M_S = 299792458.0

# The clearance the absorber has to keep behind the antenna is stated as a
# fraction of the chosen antenna-to-unit separation, so it moves with it.
ABSORBER_CLEARANCE_FRACTION = 0.5

# Bench parameters of the general arrangement this method starts from.
# "nominal" must land inside nominal +/- tolerance, "maximum" must not exceed
# its limit, "minimum" must not fall below it. Lengths are metres,
# resistances milliohm.
BASELINE_PARAMETERS = {
    "antenna-to-unit-separation-m": {
        "kind": "nominal",
        "nominal": 1.0,
        "tolerance": 0.05,
    },
    "antenna-boresight-height-m": {
        "kind": "nominal",
        "nominal": 1.0,
        "tolerance": 0.05,
    },
    "unit-edge-to-plane-edge-m": {"kind": "nominal", "nominal": 0.10, "tolerance": 0.02},
    "cable-run-length-along-plane-m": {
        "kind": "nominal",
        "nominal": 2.0,
        "tolerance": 0.10,
    },
    "unit-to-plane-bond-resistance-mohm": {"kind": "maximum", "limit": 2.5},
    "absorber-to-antenna-clearance-m": {"kind": "minimum", "limit": 0.5},
}

# The faces of the unit that are turned toward the antenna in turn. A face
# never presented is a face never measured.
UNIT_FACES = ("front", "rear", "left", "right", "top")

# Every presentation is scanned in both antenna planes.
POLARIZATIONS = ("vertical", "horizontal")

CATEGORY_CONFORMING = "conforming"
CATEGORY_DECLARED_DEVIATION = "declared-deviation"
CATEGORY_NONCONFORMING = "nonconforming"
CATEGORIES = (
    CATEGORY_CONFORMING,
    CATEGORY_DECLARED_DEVIATION,
    CATEGORY_NONCONFORMING,
)

REGIME_FAR_FIELD = "far-field"
REGIME_AT_BOUNDARY = "at-near-field-boundary"
REGIME_NEAR_FIELD = "near-field"

VERDICT_CONFORMING = "layout-conforming"
VERDICT_REJECTED = "layout-rejected"


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
    """Return the recognized bench parameter name for a raw name."""
    if not isinstance(name, str):
        raise ValueError("parameter name must be a string, got %r" % (name,))
    key = name.strip().lower()
    if key not in BASELINE_PARAMETERS:
        raise ValueError(
            "unrecognized bench parameter %r; recognized: %s"
            % (name, ", ".join(sorted(BASELINE_PARAMETERS)))
        )
    return key


def normalize_face(face):
    """Return the recognized unit face for a raw designation."""
    if not isinstance(face, str):
        raise ValueError("unit face must be a string, got %r" % (face,))
    key = face.strip().lower()
    if key not in UNIT_FACES:
        raise ValueError(
            "unrecognized unit face %r; recognized: %s" % (face, ", ".join(UNIT_FACES))
        )
    return key


def normalize_polarization(polarization):
    """Return the recognized antenna polarization for a raw designation."""
    if not isinstance(polarization, str):
        raise ValueError("polarization must be a string, got %r" % (polarization,))
    key = polarization.strip().lower()
    if key not in POLARIZATIONS:
        raise ValueError(
            "unrecognized polarization %r; recognized: %s"
            % (polarization, ", ".join(POLARIZATIONS))
        )
    return key


def parameter_bounds(name, spec=None):
    """Return the (low, high) band a parameter value has to land inside."""
    key = normalize_parameter(name)
    spec = BASELINE_PARAMETERS[key] if spec is None else spec
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


def parameter_scale(name, spec=None):
    """Scale used to express a deviation as a unit-free fraction."""
    key = normalize_parameter(name)
    spec = BASELINE_PARAMETERS[key] if spec is None else spec
    if spec["kind"] == "nominal":
        return float(spec["tolerance"])
    return float(spec["limit"])


def derive_layout(separation_m=None, deltas=None):
    """Derive the bench bounds from the chosen separation and any deltas.

    The separation is the one free choice the clause leaves the bench, and the
    rest of the layout follows it: the absorber clearance behind the antenna
    is stated as a fraction of it, so moving the antenna moves that bound too.
    A delta may then shift a bound; it may not change what kind of bound it
    is, and it may not leave a parameter with no allowed band.
    """
    derived = {}
    for key, spec in BASELINE_PARAMETERS.items():
        derived[key] = dict(spec)
    if separation_m is not None:
        separation = _number({"v": separation_m}, "v", "separation_m")
        if separation <= 0.0:
            raise ValueError("separation_m must be > 0, got %g" % separation)
        derived["antenna-to-unit-separation-m"]["nominal"] = separation
        derived["absorber-to-antenna-clearance-m"]["limit"] = (
            ABSORBER_CLEARANCE_FRACTION * separation
        )
    if deltas is None:
        return derived
    if not isinstance(deltas, dict):
        raise ValueError("deltas: must be a mapping of parameter -> replacement")
    for name in deltas:
        key = normalize_parameter(name)
        replacement = deltas[name]
        if not isinstance(replacement, dict):
            raise ValueError("deltas[%s]: replacement must be a mapping" % key)
        spec = dict(derived[key])
        for field in replacement:
            if field not in BASELINE_PARAMETERS[key]:
                raise ValueError(
                    "deltas[%s]: unknown field %r for a %s parameter"
                    % (key, field, spec["kind"])
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


def parameter_deviation(name, value, layout=None):
    """Signed distance from the allowed band: 0 inside, otherwise the overrun."""
    key = normalize_parameter(name)
    spec = (layout or BASELINE_PARAMETERS)[key]
    measured = _number({"v": value}, "v", key)
    if measured < 0.0:
        raise ValueError("%s: measured value must be >= 0, got %g" % (key, measured))
    low, high = parameter_bounds(key, spec)
    if measured < low and not math.isclose(measured, low, rel_tol=0.0, abs_tol=TOL):
        return measured - low
    if math.isinf(high):
        return 0.0
    if measured > high and not math.isclose(measured, high, rel_tol=0.0, abs_tol=TOL):
        return measured - high
    return 0.0


def relative_overrun(name, value, layout=None):
    """Deviation expressed as a fraction of the parameter's own scale."""
    key = normalize_parameter(name)
    spec = (layout or BASELINE_PARAMETERS)[key]
    return abs(parameter_deviation(key, value, layout)) / parameter_scale(key, spec)


def categorize_parameter(name, value, layout=None, declared_deviations=()):
    """Categorize one realized parameter against the derived layout."""
    key = normalize_parameter(name)
    if not isinstance(declared_deviations, (list, tuple, set, frozenset)):
        raise ValueError("declared_deviations must be a collection of names")
    declared = set(normalize_parameter(d) for d in declared_deviations)
    deviation = parameter_deviation(key, value, layout)
    if math.isclose(deviation, 0.0, rel_tol=0.0, abs_tol=TOL):
        return CATEGORY_CONFORMING
    if key in declared:
        return CATEGORY_DECLARED_DEVIATION
    return CATEGORY_NONCONFORMING


def near_field_boundary_m(frequency_hz):
    """Separation below which the measurement sits in the reactive near field."""
    frequency = _number({"v": frequency_hz}, "v", "frequency_hz")
    if frequency <= 0.0:
        raise ValueError("frequency_hz must be > 0, got %g" % frequency)
    wavelength = SPEED_OF_LIGHT_M_S / frequency
    return wavelength / (2.0 * math.pi)


def separation_regime(separation_m, lowest_frequency_hz):
    """Name the regime the chosen separation puts the lowest frequency in."""
    separation = _number({"v": separation_m}, "v", "separation_m")
    if separation <= 0.0:
        raise ValueError("separation_m must be > 0, got %g" % separation)
    boundary = near_field_boundary_m(lowest_frequency_hz)
    if math.isclose(separation, boundary, rel_tol=1e-9, abs_tol=0.0):
        return REGIME_AT_BOUNDARY
    if separation > boundary:
        return REGIME_FAR_FIELD
    return REGIME_NEAR_FIELD


def validate_presentations(presentations):
    """Validate the presentation log and return it as normalized pairs."""
    where = "presentations"
    if not isinstance(presentations, (list, tuple)):
        raise ValueError("%s: must be a list of (face, polarization) entries" % where)
    if len(presentations) == 0:
        raise ValueError("%s: at least one presentation must be recorded" % where)
    seen = []
    for index, entry in enumerate(presentations):
        tag = "%s[%d]" % (where, index)
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise ValueError("%s: entry must be a (face, polarization) pair" % tag)
        pair = (normalize_face(entry[0]), normalize_polarization(entry[1]))
        if pair in seen:
            raise ValueError("%s: %s/%s recorded twice" % ((tag,) + pair))
        seen.append(pair)
    return tuple(seen)


def missing_presentations(presentations):
    """Return the face/polarization combinations the log never records."""
    recorded = set(validate_presentations(presentations))
    return tuple(
        (face, plane)
        for face in UNIT_FACES
        for plane in POLARIZATIONS
        if (face, plane) not in recorded
    )


def assess_bench_layout(
    measurements,
    presentations,
    separation_m=None,
    lowest_frequency_hz=30.0e6,
    deltas=None,
    declared_deviations=(),
):
    """Full clause 5.4.6.3 grading of a realized bench and its presentations."""
    if not isinstance(measurements, dict):
        raise ValueError("measurements: must be a mapping of parameter -> value")
    layout = derive_layout(separation_m, deltas)

    normalized = {}
    for name in measurements:
        key = normalize_parameter(name)
        if key in normalized:
            raise ValueError("measurements: parameter %r given more than once" % key)
        normalized[key] = measurements[name]
    absent = tuple(key for key in sorted(BASELINE_PARAMETERS) if key not in normalized)
    if absent:
        raise ValueError(
            "measurements: the bench is not fully described; missing: %s"
            % ", ".join(absent)
        )

    findings = []
    limitations = []
    graded = []
    for key in sorted(BASELINE_PARAMETERS):
        value = _number(normalized, key, "measurements")
        category = categorize_parameter(key, value, layout, declared_deviations)
        overrun = relative_overrun(key, value, layout)
        low, high = parameter_bounds(key, layout[key])
        graded.append(
            {
                "parameter": key,
                "value": value,
                "allowed_low": low,
                "allowed_high": high,
                "deviation": parameter_deviation(key, value, layout),
                "relative_overrun": overrun,
                "category": category,
            }
        )
        if category == CATEGORY_NONCONFORMING:
            findings.append(
                "%s is %g, outside the derived band %g-%g" % (key, value, low, high)
            )
        elif category == CATEGORY_DECLARED_DEVIATION:
            limitations.append(
                "%s is %g, a declared deviation from the derived band" % (key, value)
            )

    gaps = missing_presentations(presentations)
    for face, plane in gaps:
        findings.append("the %s face was never presented in %s polarization" % (face, plane))

    realized_separation = _number(normalized, "antenna-to-unit-separation-m", "measurements")
    regime = separation_regime(realized_separation, lowest_frequency_hz)
    if regime == REGIME_NEAR_FIELD:
        limitations.append(
            "at %g Hz the separation %g m sits inside the near-field boundary "
            "%g m; the recorded field does not scale by distance"
            % (
                lowest_frequency_hz,
                realized_separation,
                near_field_boundary_m(lowest_frequency_hz),
            )
        )
    elif regime == REGIME_AT_BOUNDARY:
        limitations.append(
            "at %g Hz the separation sits on the near-field boundary" % lowest_frequency_hz
        )

    governing = max(
        graded, key=lambda g: (g["relative_overrun"], g["parameter"])
    )
    return {
        "layout": layout,
        "parameters": graded,
        "governing_parameter": governing["parameter"],
        "presentation_gaps": gaps,
        "separation_regime": regime,
        "near_field_boundary_m": near_field_boundary_m(lowest_frequency_hz),
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_CONFORMING if not findings else VERDICT_REJECTED,
    }
