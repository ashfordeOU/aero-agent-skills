"""Condition set declared for a thermal-vacuum outgassing screening run.

Anchor: ECSS-Q-ST-70-02C, procedure clause -- the screening point is a fixed
combination of specimen temperature, collector temperature, chamber pressure
and soak duration, and any departure from it is an application-specific
condition that has to be justified rather than assumed. Paraphrased into an
implementable procedure; no standard text is reproduced.

What this module decides
------------------------
Whether the condition set written on the run sheet is the screening point, a
justified alternative, or an unjustified departure -- and whether the time
booked on the chamber can actually hold it.

1. Set points. Specimen temperature, collector temperature and soak duration
   are each compared with the reference value inside its own tolerance band,
   because they are controlled by different loops and fail in different ways.
2. Pressure. The chamber pressure is a ceiling, not a set point: any pressure
   at or below the limit satisfies the condition, and only exceeding it is a
   departure.
3. Justification. A departure is allowed, but only when the run sheet names
   that parameter with a justification and an approval reference. A blanket
   note covering "the conditions" justifies nothing in particular.
4. Window. Pump-down and stabilisation happen before the soak starts, so the
   time booked on the chamber has to hold all three plus the cool-down, and
   the headroom left over is the number worth reporting.
"""

import math

__all__ = [
    "REFERENCE_SPECIMEN_TEMPERATURE_C",
    "REFERENCE_SPECIMEN_TOLERANCE_C",
    "REFERENCE_COLLECTOR_TEMPERATURE_C",
    "REFERENCE_COLLECTOR_TOLERANCE_C",
    "REFERENCE_DURATION_H",
    "REFERENCE_DURATION_TOLERANCE_H",
    "REFERENCE_PRESSURE_CEILING_PA",
    "JUSTIFIABLE_PARAMETERS",
    "deviation",
    "within_tolerance",
    "setpoint_finding",
    "pressure_finding",
    "justification_findings",
    "required_window_h",
    "window_findings",
    "assess_test_conditions",
]

# The screening point the method is written around.
REFERENCE_SPECIMEN_TEMPERATURE_C = 125.0
REFERENCE_SPECIMEN_TOLERANCE_C = 1.0
REFERENCE_COLLECTOR_TEMPERATURE_C = 25.0
REFERENCE_COLLECTOR_TOLERANCE_C = 1.0
REFERENCE_DURATION_H = 24.0
REFERENCE_DURATION_TOLERANCE_H = 0.5

# The chamber pressure is a ceiling: at or below it is the condition.
REFERENCE_PRESSURE_CEILING_PA = 1.0e-4

# Parameters a run sheet may depart from, each on its own justification.
JUSTIFIABLE_PARAMETERS = (
    "specimen_temperature_c",
    "collector_temperature_c",
    "duration_h",
    "pressure_pa",
)

# Band comparisons are inclusive; absorb representation error at the edge
# rather than widening the tolerance itself.
BAND_TOLERANCE = 1e-9


def _as_finite_float(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _as_positive_float(value, label):
    number = _as_finite_float(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _as_non_negative_float(value, label):
    number = _as_finite_float(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def deviation(declared, reference):
    """Return the signed departure of a declared value from its reference."""
    return _as_finite_float(declared, "declared") - _as_finite_float(reference, "reference")


def within_tolerance(declared, reference, tolerance):
    """Return True when a declared value sits inside its reference band."""
    allowed = _as_positive_float(tolerance, "tolerance")
    return abs(deviation(declared, reference)) <= allowed + BAND_TOLERANCE


def setpoint_finding(name, declared, reference, tolerance, unit):
    """Return a finding when a set point left its reference band."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-blank string")
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("unit must be a non-blank string")
    if within_tolerance(declared, reference, tolerance):
        return None
    return (
        "%s is declared at %g %s, which departs from the screening point %g %s "
        "by %+g %s" % (
            name.strip(), float(declared), unit.strip(), float(reference),
            unit.strip(), deviation(declared, reference), unit.strip(),
        )
    )


def pressure_finding(declared_pa, ceiling_pa=REFERENCE_PRESSURE_CEILING_PA):
    """Return a finding when the declared chamber pressure exceeds the ceiling."""
    declared = _as_positive_float(declared_pa, "declared_pa")
    ceiling = _as_positive_float(ceiling_pa, "ceiling_pa")
    if declared <= ceiling * (1.0 + BAND_TOLERANCE):
        return None
    return (
        "chamber pressure is declared at %.3e Pa, above the %.3e Pa ceiling"
        % (declared, ceiling)
    )


def justification_findings(departed, justifications):
    """Return a finding for every departed parameter without its own justification."""
    if not isinstance(departed, (list, tuple)):
        raise ValueError("departed must be a sequence of parameter names")
    if justifications is None:
        justifications = {}
    if not isinstance(justifications, dict):
        raise ValueError("justifications must be a mapping")
    for key in justifications:
        if key not in JUSTIFIABLE_PARAMETERS:
            raise ValueError("'%s' is not a condition-set parameter" % key)
    findings = []
    for name in departed:
        if name not in JUSTIFIABLE_PARAMETERS:
            raise ValueError("'%s' is not a condition-set parameter" % name)
        entry = justifications.get(name)
        if entry is None:
            findings.append(
                "parameter '%s' departs from the screening point with no justification"
                % name
            )
            continue
        if not isinstance(entry, dict):
            raise ValueError("justification for '%s' must be a mapping" % name)
        for field in ("rationale", "approval_reference"):
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                findings.append(
                    "justification for '%s' has no %s" % (name, field.replace("_", " "))
                )
    return findings


def required_window_h(pumpdown_h, stabilisation_h, duration_h, cooldown_h):
    """Return the chamber time the declared condition set needs end to end."""
    return (
        _as_non_negative_float(pumpdown_h, "pumpdown_h")
        + _as_non_negative_float(stabilisation_h, "stabilisation_h")
        + _as_positive_float(duration_h, "duration_h")
        + _as_non_negative_float(cooldown_h, "cooldown_h")
    )


def window_findings(booked_h, required_h):
    """Return a finding when the booked chamber time cannot hold the run."""
    booked = _as_positive_float(booked_h, "booked_h")
    required = _as_positive_float(required_h, "required_h")
    if booked >= required - BAND_TOLERANCE:
        return []
    return [
        "booked chamber time of %.2f h is short of the %.2f h the condition set "
        "needs" % (booked, required)
    ]


def assess_test_conditions(spec):
    """Run the full condition-set assessment for one screening run.

    spec keys: specimen_temperature_c, collector_temperature_c, duration_h,
    pressure_pa; optional booked_window_h, pumpdown_h, stabilisation_h,
    cooldown_h, justifications, and reference overrides.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("specimen_temperature_c", "collector_temperature_c", "duration_h",
                "pressure_pa"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    checks = (
        ("specimen_temperature_c", "specimen temperature",
         spec.get("reference_specimen_temperature_c", REFERENCE_SPECIMEN_TEMPERATURE_C),
         spec.get("specimen_tolerance_c", REFERENCE_SPECIMEN_TOLERANCE_C), "C"),
        ("collector_temperature_c", "collector temperature",
         spec.get("reference_collector_temperature_c", REFERENCE_COLLECTOR_TEMPERATURE_C),
         spec.get("collector_tolerance_c", REFERENCE_COLLECTOR_TOLERANCE_C), "C"),
        ("duration_h", "soak duration",
         spec.get("reference_duration_h", REFERENCE_DURATION_H),
         spec.get("duration_tolerance_h", REFERENCE_DURATION_TOLERANCE_H), "h"),
    )
    findings = []
    departure_notes = []
    departed = []
    deviations = {}
    for key, label, reference, tolerance, unit in checks:
        value = _as_finite_float(spec[key], key)
        if key == "duration_h" and value <= 0.0:
            raise ValueError("duration_h must be positive, got %r" % (spec[key],))
        deviations[key] = deviation(value, reference)
        note = setpoint_finding(label, value, reference, tolerance, unit)
        if note:
            departure_notes.append(note)
            departed.append(key)
    ceiling = spec.get("pressure_ceiling_pa", REFERENCE_PRESSURE_CEILING_PA)
    pressure_note = pressure_finding(spec["pressure_pa"], ceiling)
    if pressure_note:
        departure_notes.append(pressure_note)
        departed.append("pressure_pa")
    findings.extend(justification_findings(departed, spec.get("justifications")))
    needed = None
    booked = spec.get("booked_window_h")
    if booked is not None:
        needed = required_window_h(
            spec.get("pumpdown_h", 0.0),
            spec.get("stabilisation_h", 0.0),
            spec["duration_h"],
            spec.get("cooldown_h", 0.0),
        )
        findings.extend(window_findings(booked, needed))
    return {
        "deviations": deviations,
        "departed_parameters": departed,
        "departure_notes": departure_notes,
        "required_window_h": needed,
        "window_headroom_h": None if needed is None else float(booked) - needed,
        "findings": findings,
        "at_screening_point": not departed,
        "conditions_accepted": not findings,
    }
