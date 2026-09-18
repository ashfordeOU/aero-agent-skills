"""Adjustable turn on threshold expressed against the maximum bus voltage.

Anchor: ECSS-E-ST-20-20C clause 5.4.4.2.1 (the adjustable turn on threshold of
the protection function is expressed against the maximum direct current bus
voltage value). Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Validate the maximum bus value, the nominal bus value and the declared
   ladder of settings. A maximum below the nominal is an input error.
2. Normalise the reference the specification quotes its settings against: the
   maximum bus value this clause asks for, the nominal bus value, or nothing
   at all.
3. Refer every setting into volts, through the maximum bus value when it is
   already quoted that way and through the nominal bus otherwise, and restate
   each setting as a fraction of the maximum bus so the ladder reads in the
   reference the clause names.
4. Report the volts a reader would shift each setting by if the wrong
   reference were taken; that shift is the practical size of the ambiguity.
5. Derive the span the ladder covers in volts and compare it with the span the
   project requires, absorbing an exact landing with a named tolerance.
6. Keep the settings sitting between the equipment turn on floor and the
   lowest steady state bus voltage: a setting outside that window is a
   position on the dial the bus never climbs through.
"""

import math

__all__ = [
    "SPAN_TOLERANCE_V",
    "REFERENCE_NAMES",
    "CLAUSE_REFERENCE",
    "normalise_reference",
    "validate_voltage",
    "validate_percent",
    "validate_bus_pair",
    "percent_of_maximum_to_volts",
    "percent_of_nominal_to_volts",
    "setting_volts",
    "restate_on_maximum_pct",
    "reference_shift_v",
    "ladder_span_v",
    "usable_settings_v",
    "assess_maximum_referenced_range",
]

# Span and window comparisons are differences of floats a design can land
# exactly on. Absorb the representation error here, not in the requirement.
SPAN_TOLERANCE_V = 1e-9

# Reference a percentage can be quoted against.
REFERENCE_NAMES = ("maximum-bus", "nominal-main-bus", "unstated")

# The reference this clause names.
CLAUSE_REFERENCE = "maximum-bus"

_REFERENCE_ALIASES = {
    "maximum": "maximum-bus",
    "maximum-bus": "maximum-bus",
    "max-bus": "maximum-bus",
    "maximum-bus-voltage": "maximum-bus",
    "maximum-dc-bus-voltage": "maximum-bus",
    "vmax": "maximum-bus",
    "nominal": "nominal-main-bus",
    "nominal-bus": "nominal-main-bus",
    "nominal-main-bus": "nominal-main-bus",
    "nominal-main-bus-voltage": "nominal-main-bus",
    "vnom": "nominal-main-bus",
    "unstated": "unstated",
    "none": "unstated",
}


def normalise_reference(reference):
    """Return the canonical name of the voltage a setting is quoted against."""
    if reference is None:
        return "unstated"
    if not isinstance(reference, str):
        raise ValueError("reference must be a string, got %r" % (reference,))
    key = reference.strip().lower()
    if not key:
        return "unstated"
    if key not in _REFERENCE_ALIASES:
        raise ValueError(
            "unknown reference %r; known: %s"
            % (reference, ", ".join(sorted(set(_REFERENCE_ALIASES.values()))))
        )
    return _REFERENCE_ALIASES[key]


def validate_voltage(value, label, allow_zero=False):
    """Return the value as a finite, non-negative float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    if number == 0.0 and not allow_zero:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def validate_percent(value, label):
    """Return a percentage of a bus reference as a float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be a positive percentage, got %g" % (label, number))
    if number > 200.0:
        raise ValueError(
            "%s of %g is outside any credible turn on setting; a fraction has "
            "to be multiplied by 100 first" % (label, number)
        )
    return number


def validate_bus_pair(nominal_v, maximum_v):
    """Return the validated (nominal, maximum) bus pair in volts."""
    nominal = validate_voltage(nominal_v, "nominal_v")
    maximum = validate_voltage(maximum_v, "maximum_v")
    if maximum < nominal and not math.isclose(
        maximum, nominal, rel_tol=0.0, abs_tol=SPAN_TOLERANCE_V
    ):
        raise ValueError(
            "maximum_v %g must not sit below nominal_v %g" % (maximum, nominal)
        )
    return (nominal, maximum)


def percent_of_maximum_to_volts(percent, maximum_v):
    """Return the volts a setting quoted against the maximum bus commands."""
    pct = validate_percent(percent, "percent")
    maximum = validate_voltage(maximum_v, "maximum_v")
    return maximum * pct / 100.0


def percent_of_nominal_to_volts(percent, nominal_v):
    """Return the volts a setting quoted against the nominal bus commands."""
    pct = validate_percent(percent, "percent")
    nominal = validate_voltage(nominal_v, "nominal_v")
    return nominal * pct / 100.0


def setting_volts(percent, reference, nominal_v, maximum_v):
    """Return the volts one setting commands, given the reference it carries.

    An unstated reference is read against the maximum bus this clause names;
    the assumption is reported by the caller rather than hidden here.
    """
    nominal, maximum = validate_bus_pair(nominal_v, maximum_v)
    canonical = normalise_reference(reference)
    if canonical == "nominal-main-bus":
        return percent_of_nominal_to_volts(percent, nominal)
    return percent_of_maximum_to_volts(percent, maximum)


def restate_on_maximum_pct(percent, reference, nominal_v, maximum_v):
    """Return the same threshold quoted as a fraction of the maximum bus."""
    nominal, maximum = validate_bus_pair(nominal_v, maximum_v)
    volts = setting_volts(percent, reference, nominal, maximum)
    return 100.0 * volts / maximum


def reference_shift_v(percent, nominal_v, maximum_v):
    """Return the volts the same number moves by when the reference changes."""
    nominal, maximum = validate_bus_pair(nominal_v, maximum_v)
    pct = validate_percent(percent, "percent")
    return (maximum - nominal) * pct / 100.0


def ladder_span_v(settings_v):
    """Return the span in volts between the lowest and highest setting."""
    if not isinstance(settings_v, (list, tuple)) or not settings_v:
        raise ValueError("settings_v must be a non-empty sequence")
    values = [validate_voltage(v, "setting_v") for v in settings_v]
    return max(values) - min(values)


def usable_settings_v(settings_v, floor_v, lowest_steady_v):
    """Return the settings whose volts sit inside the crossable bus window."""
    if not isinstance(settings_v, (list, tuple)) or not settings_v:
        raise ValueError("settings_v must be a non-empty sequence")
    floor = validate_voltage(floor_v, "floor_v")
    lowest_steady = validate_voltage(lowest_steady_v, "lowest_steady_v")
    if floor > lowest_steady:
        raise ValueError(
            "floor_v %g exceeds lowest_steady_v %g; the window is empty"
            % (floor, lowest_steady)
        )
    usable = []
    for volts in settings_v:
        value = validate_voltage(volts, "setting_v")
        below = value < floor and not math.isclose(
            value, floor, rel_tol=0.0, abs_tol=SPAN_TOLERANCE_V
        )
        above = value > lowest_steady and not math.isclose(
            value, lowest_steady, rel_tol=0.0, abs_tol=SPAN_TOLERANCE_V
        )
        if not below and not above:
            usable.append(value)
    return usable


def assess_maximum_referenced_range(spec):
    """Grade one adjustable turn on threshold against clause 5.4.4.2.1.

    spec keys: nominal_v, maximum_v, settings_pct, floor_v, lowest_steady_v,
    optional reference and optional required_span_v.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (type(spec).__name__,))
    required_keys = (
        "nominal_v",
        "maximum_v",
        "settings_pct",
        "floor_v",
        "lowest_steady_v",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    nominal, maximum = validate_bus_pair(spec["nominal_v"], spec["maximum_v"])
    settings_pct = spec["settings_pct"]
    if not isinstance(settings_pct, (list, tuple)) or len(settings_pct) < 2:
        raise ValueError(
            "settings_pct must hold at least 2 settings for an adjustable "
            "threshold"
        )
    reference = normalise_reference(spec.get("reference", CLAUSE_REFERENCE))

    volts = [setting_volts(pct, reference, nominal, maximum) for pct in settings_pct]
    restated = [
        restate_on_maximum_pct(pct, reference, nominal, maximum)
        for pct in settings_pct
    ]
    shifts = [reference_shift_v(pct, nominal, maximum) for pct in settings_pct]
    span = ladder_span_v(volts)
    usable = usable_settings_v(volts, spec["floor_v"], spec["lowest_steady_v"])

    findings = []
    if reference == "unstated":
        findings.append(
            "the settings carry no stated reference; they are read against the "
            "maximum bus of %g V as a working assumption" % maximum
        )
    elif reference != CLAUSE_REFERENCE:
        findings.append(
            "the settings are quoted against the nominal bus of %g V, so each "
            "one sits up to %g V away from the same number read against the "
            "maximum bus this clause names" % (nominal, max(shifts))
        )
    unreachable = [
        volt
        for volt in volts
        if volt > maximum
        and not math.isclose(volt, maximum, rel_tol=0.0, abs_tol=SPAN_TOLERANCE_V)
    ]
    if unreachable:
        findings.append(
            "%d setting(s) ask for an enable point above the %g V maximum bus, "
            "which the bus never reaches" % (len(unreachable), maximum)
        )
    if "required_span_v" in spec:
        required_span = validate_voltage(spec["required_span_v"], "required_span_v")
        short = span < required_span and not math.isclose(
            span, required_span, rel_tol=0.0, abs_tol=SPAN_TOLERANCE_V
        )
        if short:
            findings.append(
                "the ladder spans %g V, short of the %g V of adjustment required"
                % (span, required_span)
            )
    if not usable:
        findings.append(
            "no setting lands between the %g V equipment turn on floor and the "
            "%g V lowest steady state bus"
            % (
                validate_voltage(spec["floor_v"], "floor_v"),
                validate_voltage(spec["lowest_steady_v"], "lowest_steady_v"),
            )
        )

    return {
        "reference": reference,
        "clause_reference": CLAUSE_REFERENCE,
        "settings_v": volts,
        "settings_pct_of_maximum": restated,
        "reference_shift_v": shifts,
        "ladder_span_v": span,
        "usable_settings_v": usable,
        "usable_setting_count": len(usable),
        "verdict": "compliant" if not findings else "non-compliant",
        "findings": findings,
    }
