"""Adjustable turn on threshold expressed as a percentage of the nominal bus.

Anchor: ECSS-E-ST-20-20C clause 5.4.4.1.1 (the turn on threshold of the
protection function is adjustable over a range stated as a percentage of the
nominal main bus voltage). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the nominal main bus voltage, the setting ladder and the
   percentage band the project requires the ladder to cover.
2. Normalise the reference the specification quotes its percentages against.
   This clause asks for the nominal main bus; a ladder referred to the maximum
   bus value, or to nothing at all, is reported as a reference finding.
3. Build the ladder by offsetting each step from the lowest setting, so the
   highest setting is exact rather than the sum of many additions.
4. Refer every setting into volts through the nominal main bus and derive the
   volts one adjustment step commands.
5. Test coverage at both ends of the required percentage band, absorbing an
   exact landing on a bound with a named tolerance.
6. Keep the settings whose volts fall inside the window between the equipment
   operating floor and the lowest steady state bus voltage: a setting outside
   that window exists on the dial but can never be crossed in flight.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE_PCT",
    "WINDOW_TOLERANCE_V",
    "REFERENCE_NAMES",
    "normalise_reference",
    "validate_voltage",
    "validate_percent",
    "ladder_settings_pct",
    "percent_to_volts",
    "ladder_volts",
    "ladder_span_pct",
    "step_resolution_v",
    "band_coverage",
    "usable_settings_pct",
    "assess_enable_threshold_range",
]

# Coverage is a comparison of two percentages a design can place exactly on
# each other. Absorb the representation error here, not in the requirement.
COVERAGE_TOLERANCE_PCT = 1e-9

# The same argument in volts, for the usable-window filter.
WINDOW_TOLERANCE_V = 1e-9

# Reference a percentage can be quoted against. Only the first is the one this
# clause asks for; the others are recorded so the finding can name them.
REFERENCE_NAMES = ("nominal-main-bus", "maximum-bus", "unstated")

_REFERENCE_ALIASES = {
    "nominal": "nominal-main-bus",
    "nominal-bus": "nominal-main-bus",
    "nominal-main-bus": "nominal-main-bus",
    "nominal-main-bus-voltage": "nominal-main-bus",
    "vnom": "nominal-main-bus",
    "maximum": "maximum-bus",
    "maximum-bus": "maximum-bus",
    "max-bus": "maximum-bus",
    "maximum-bus-voltage": "maximum-bus",
    "vmax": "maximum-bus",
    "unstated": "unstated",
    "none": "unstated",
}


def normalise_reference(reference):
    """Return the canonical name of the voltage a percentage is quoted against."""
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


def validate_percent(value, label, allow_zero=False):
    """Return a percentage of the reference bus as a float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0 or (number == 0.0 and not allow_zero):
        raise ValueError("%s must be a positive percentage, got %g" % (label, number))
    if number > 200.0:
        raise ValueError(
            "%s of %g is outside any credible turn on setting; a fraction has "
            "to be multiplied by 100 first" % (label, number)
        )
    return number


def ladder_settings_pct(lowest_pct, step_pct, setting_count):
    """Return the adjustment ladder as a list of percentages.

    Each setting is offset from the lowest one rather than accumulated, so the
    highest setting carries a single rounding rather than setting_count of them.
    """
    lowest = validate_percent(lowest_pct, "lowest_pct")
    step = validate_percent(step_pct, "step_pct")
    if not isinstance(setting_count, int) or isinstance(setting_count, bool):
        raise ValueError("setting_count must be an integer, got %r" % (setting_count,))
    if setting_count < 2:
        raise ValueError(
            "setting_count must be at least 2 for an adjustable threshold, got %d"
            % setting_count
        )
    return [lowest + index * step for index in range(setting_count)]


def percent_to_volts(percent, nominal_v):
    """Return the volts a percentage setting commands on the nominal bus."""
    pct = validate_percent(percent, "percent")
    nominal = validate_voltage(nominal_v, "nominal_v")
    return nominal * pct / 100.0


def ladder_volts(settings_pct, nominal_v):
    """Return every ladder setting referred into volts."""
    if not isinstance(settings_pct, (list, tuple)) or not settings_pct:
        raise ValueError("settings_pct must be a non-empty sequence")
    return [percent_to_volts(pct, nominal_v) for pct in settings_pct]


def ladder_span_pct(settings_pct):
    """Return the (lowest, highest) percentage the ladder can be set to."""
    if not isinstance(settings_pct, (list, tuple)) or not settings_pct:
        raise ValueError("settings_pct must be a non-empty sequence")
    values = [validate_percent(pct, "setting") for pct in settings_pct]
    return (min(values), max(values))


def step_resolution_v(step_pct, nominal_v):
    """Return the volts one adjustment step buys on the nominal bus."""
    return percent_to_volts(step_pct, nominal_v)


def band_coverage(settings_pct, required_low_pct, required_high_pct):
    """Return coverage of the required band, reported at each end separately."""
    low, high = ladder_span_pct(settings_pct)
    required_low = validate_percent(required_low_pct, "required_low_pct")
    required_high = validate_percent(required_high_pct, "required_high_pct")
    if required_low > required_high:
        raise ValueError(
            "required_low_pct %g exceeds required_high_pct %g"
            % (required_low, required_high)
        )
    covers_low = low < required_low or math.isclose(
        low, required_low, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE_PCT
    )
    covers_high = high > required_high or math.isclose(
        high, required_high, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE_PCT
    )
    return {
        "ladder_low_pct": low,
        "ladder_high_pct": high,
        "covers_low": covers_low,
        "covers_high": covers_high,
        "low_shortfall_pct": 0.0 if covers_low else low - required_low,
        "high_shortfall_pct": 0.0 if covers_high else required_high - high,
    }


def usable_settings_pct(settings_pct, nominal_v, floor_v, lowest_steady_v):
    """Return the settings whose volts sit inside the crossable bus window."""
    floor = validate_voltage(floor_v, "floor_v")
    lowest_steady = validate_voltage(lowest_steady_v, "lowest_steady_v")
    if floor > lowest_steady:
        raise ValueError(
            "floor_v %g exceeds lowest_steady_v %g; the window is empty"
            % (floor, lowest_steady)
        )
    usable = []
    for pct in settings_pct:
        volts = percent_to_volts(pct, nominal_v)
        below_floor = volts < floor and not math.isclose(
            volts, floor, rel_tol=0.0, abs_tol=WINDOW_TOLERANCE_V
        )
        above_steady = volts > lowest_steady and not math.isclose(
            volts, lowest_steady, rel_tol=0.0, abs_tol=WINDOW_TOLERANCE_V
        )
        if not below_floor and not above_steady:
            usable.append(pct)
    return usable


def assess_enable_threshold_range(spec):
    """Grade one adjustable turn on threshold against clause 5.4.4.1.1.

    spec keys: nominal_v, lowest_pct, step_pct, setting_count,
    required_low_pct, required_high_pct, floor_v, lowest_steady_v, optional
    reference and optional max_step_v.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (type(spec).__name__,))
    required_keys = (
        "nominal_v",
        "lowest_pct",
        "step_pct",
        "setting_count",
        "required_low_pct",
        "required_high_pct",
        "floor_v",
        "lowest_steady_v",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    nominal = validate_voltage(spec["nominal_v"], "nominal_v")
    reference = normalise_reference(spec.get("reference", "nominal-main-bus"))
    settings = ladder_settings_pct(
        spec["lowest_pct"], spec["step_pct"], spec["setting_count"]
    )
    volts = ladder_volts(settings, nominal)
    resolution = step_resolution_v(spec["step_pct"], nominal)
    coverage = band_coverage(
        settings, spec["required_low_pct"], spec["required_high_pct"]
    )
    usable = usable_settings_pct(
        settings, nominal, spec["floor_v"], spec["lowest_steady_v"]
    )

    findings = []
    if reference != "nominal-main-bus":
        findings.append(
            "the adjustment range is quoted against the %s, not the nominal "
            "main bus this clause names" % reference.replace("-", " ")
        )
    if not coverage["covers_low"]:
        findings.append(
            "the ladder cannot be set below %g percent, %g percent short of the "
            "required low end"
            % (coverage["ladder_low_pct"], coverage["low_shortfall_pct"])
        )
    if not coverage["covers_high"]:
        findings.append(
            "the ladder stops at %g percent, %g percent short of the required "
            "high end"
            % (coverage["ladder_high_pct"], coverage["high_shortfall_pct"])
        )
    if "max_step_v" in spec:
        max_step = validate_voltage(spec["max_step_v"], "max_step_v")
        too_coarse = resolution > max_step and not math.isclose(
            resolution, max_step, rel_tol=0.0, abs_tol=WINDOW_TOLERANCE_V
        )
        if too_coarse:
            findings.append(
                "one adjustment step moves the threshold %g V, coarser than the "
                "%g V the design allows" % (resolution, max_step)
            )
    if not usable:
        findings.append(
            "no ladder setting lands between the %g V equipment floor and the "
            "%g V lowest steady state bus"
            % (
                validate_voltage(spec["floor_v"], "floor_v"),
                validate_voltage(spec["lowest_steady_v"], "lowest_steady_v"),
            )
        )

    return {
        "reference": reference,
        "settings_pct": settings,
        "settings_v": volts,
        "ladder_low_pct": coverage["ladder_low_pct"],
        "ladder_high_pct": coverage["ladder_high_pct"],
        "step_resolution_v": resolution,
        "covers_required_band": coverage["covers_low"] and coverage["covers_high"],
        "usable_settings_pct": usable,
        "usable_setting_count": len(usable),
        "verdict": "compliant" if not findings else "non-compliant",
        "findings": findings,
    }
