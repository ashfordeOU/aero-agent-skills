"""Ground adjustable undervoltage trip point referred to the maximum bus voltage.

Anchor: ECSS-E-ST-20-20C clause 5.4.3.2.1 (the undervoltage trip point is
ground adjustable and is expressed against the maximum direct current bus
voltage). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Read the reference voltage the threshold specification actually used. The
   clause names one reference -- the maximum direct current bus voltage -- and
   a percentage carried against nominal or against the minimum bus voltage is
   a different number wearing the same units, so the reference is graded
   before anything is computed from it.
2. Enumerate the ground adjustable ladder from its lowest setting to its
   highest in whole adjustment steps, and refer every settable fraction back
   into volts through the maximum bus voltage.
3. Build the admissible window. Its ceiling is the lowest steady state bus
   voltage the equipment has to keep running through; its floor is the
   equipment's own operating floor, the level below which the load stops
   behaving. Sensing uncertainty eats into the window from both sides,
   because a setting is only as good as the comparator that realises it.
4. Test every settable point against that window, report which settings are
   usable, and report the volts one adjustment step buys, so a ladder that is
   coarser than the sensing uncertainty is visible as such.
"""

import math

__all__ = [
    "VOLT_TOLERANCE_V",
    "ACCEPTED_REFERENCE",
    "KNOWN_REFERENCES",
    "validate_bus",
    "validate_setting_range",
    "reference_factor",
    "setting_ladder",
    "threshold_volts",
    "adjustment_step_volts",
    "admissible_window",
    "setting_verdicts",
    "assess_threshold_range",
]

# Two voltages a design can place exactly on top of each other; absorb the
# representation error here rather than relaxing the engineering limit.
VOLT_TOLERANCE_V = 1e-9

# The one reference the clause recognises for the trip point.
ACCEPTED_REFERENCE = "maximum-bus-voltage"

# References a specification is seen to carry, and what each one multiplies a
# declared fraction by. Anything not listed is an unreadable specification.
KNOWN_REFERENCES = (
    "maximum-bus-voltage",
    "nominal-bus-voltage",
    "minimum-bus-voltage",
)


def _real(label, value):
    """Return value as a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(label, value):
    """Return value as a strictly positive finite float or raise."""
    out = _real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def _non_negative(label, value):
    """Return value as a non-negative finite float or raise."""
    out = _real(label, value)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return out


def _fraction(label, value):
    """Return value as a fraction inside (0, 1] or raise."""
    out = _real(label, value)
    if out <= 0.0 or out > 1.0:
        raise ValueError("%s must sit in (0, 1], got %r" % (label, value))
    return out


def validate_bus(spec):
    """Return the bus description as a mapping of floats, or raise.

    spec keys: bus_maximum_v, bus_steady_minimum_v, equipment_floor_v and
    sensing_uncertainty_v.
    """
    if not isinstance(spec, dict):
        raise ValueError("bus spec must be a mapping")
    required = (
        "bus_maximum_v",
        "bus_steady_minimum_v",
        "equipment_floor_v",
        "sensing_uncertainty_v",
    )
    for key in required:
        if key not in spec:
            raise ValueError("bus spec missing required key '%s'" % key)

    bus = {
        "bus_maximum_v": _positive("bus_maximum_v", spec["bus_maximum_v"]),
        "bus_steady_minimum_v": _positive(
            "bus_steady_minimum_v", spec["bus_steady_minimum_v"]
        ),
        "equipment_floor_v": _positive("equipment_floor_v", spec["equipment_floor_v"]),
        "sensing_uncertainty_v": _non_negative(
            "sensing_uncertainty_v", spec["sensing_uncertainty_v"]
        ),
    }
    if bus["bus_steady_minimum_v"] > bus["bus_maximum_v"] + VOLT_TOLERANCE_V:
        raise ValueError(
            "bus_steady_minimum_v %r cannot exceed bus_maximum_v %r"
            % (bus["bus_steady_minimum_v"], bus["bus_maximum_v"])
        )
    if bus["equipment_floor_v"] > bus["bus_steady_minimum_v"] + VOLT_TOLERANCE_V:
        raise ValueError(
            "equipment_floor_v %r cannot exceed bus_steady_minimum_v %r"
            % (bus["equipment_floor_v"], bus["bus_steady_minimum_v"])
        )
    return bus


def validate_setting_range(spec):
    """Return the ground adjustable ladder as (lowest, highest, step), or raise.

    spec keys: fraction_minimum, fraction_maximum, fraction_step, reference.
    """
    if not isinstance(spec, dict):
        raise ValueError("setting range spec must be a mapping")
    for key in ("fraction_minimum", "fraction_maximum", "fraction_step"):
        if key not in spec:
            raise ValueError("setting range spec missing required key '%s'" % key)
    low = _fraction("fraction_minimum", spec["fraction_minimum"])
    high = _fraction("fraction_maximum", spec["fraction_maximum"])
    step = _positive("fraction_step", spec["fraction_step"])
    if high < low - VOLT_TOLERANCE_V:
        raise ValueError(
            "fraction_maximum %r sits below fraction_minimum %r" % (high, low)
        )
    span = high - low
    if span > VOLT_TOLERANCE_V and step > span + VOLT_TOLERANCE_V:
        raise ValueError(
            "fraction_step %r is wider than the whole adjustment span %r"
            % (step, span)
        )
    return (low, high, step)


def reference_factor(reference, bus):
    """Return the volts one unit of declared fraction stands for.

    A fraction means nothing until the reference behind it is named, and the
    three references a specification is seen to carry give three different
    trip voltages for the same printed percentage.
    """
    if not isinstance(reference, str):
        raise ValueError("reference must be a string, got %r" % (reference,))
    token = reference.strip().lower()
    if token not in KNOWN_REFERENCES:
        raise ValueError(
            "reference %r is not one of %s" % (reference, ", ".join(KNOWN_REFERENCES))
        )
    if token == "maximum-bus-voltage":
        return bus["bus_maximum_v"]
    if token == "minimum-bus-voltage":
        return bus["bus_steady_minimum_v"]
    nominal = bus.get("bus_nominal_v")
    if nominal is None:
        raise ValueError(
            "reference 'nominal-bus-voltage' needs bus_nominal_v in the bus spec"
        )
    return _positive("bus_nominal_v", nominal)


def setting_ladder(low, high, step):
    """Return every settable fraction from the lowest setting upward."""
    span = high - low
    if span <= VOLT_TOLERANCE_V:
        return [low]
    count = int(math.floor(span / step + 1e-9))
    return [low + index * step for index in range(count + 1)]


def threshold_volts(fraction, factor):
    """Return the trip voltage one settable fraction stands for."""
    return _fraction("fraction", fraction) * _positive("factor", factor)


def adjustment_step_volts(step, factor):
    """Return the volts one whole adjustment step moves the trip point."""
    return _positive("step", step) * _positive("factor", factor)


def admissible_window(bus):
    """Return (floor_v, ceiling_v) the trip point has to sit between.

    The ceiling keeps a healthy bus out of the trip band; the floor keeps the
    trip ahead of the load's own collapse. Sensing uncertainty closes the
    window from both ends because the comparator only realises the setting to
    within its own error.
    """
    floor_v = bus["equipment_floor_v"] + bus["sensing_uncertainty_v"]
    ceiling_v = bus["bus_steady_minimum_v"] - bus["sensing_uncertainty_v"]
    return (floor_v, ceiling_v)


def setting_verdicts(ladder, factor, bus):
    """Return one admissibility record per settable point on the ladder."""
    floor_v, ceiling_v = admissible_window(bus)
    records = []
    for fraction in ladder:
        volts = threshold_volts(fraction, factor)
        below = volts < floor_v - VOLT_TOLERANCE_V
        above = volts > ceiling_v + VOLT_TOLERANCE_V
        if below:
            reason = "trips below the equipment operating floor"
        elif above:
            reason = "trips inside the steady state bus band"
        else:
            reason = "inside the admissible window"
        records.append(
            {
                "fraction": fraction,
                "volts": volts,
                "admissible": not (below or above),
                "reason": reason,
            }
        )
    return records


def assess_threshold_range(spec):
    """Grade a ground adjustable undervoltage trip point against clause 5.4.3.2.1."""
    if not isinstance(spec, dict):
        raise ValueError("threshold spec must be a mapping")
    for key in ("bus", "setting_range"):
        if key not in spec:
            raise ValueError("threshold spec missing required key '%s'" % key)

    bus = validate_bus(spec["bus"])
    if "bus_nominal_v" in spec["bus"]:
        bus["bus_nominal_v"] = _positive("bus_nominal_v", spec["bus"]["bus_nominal_v"])

    low, high, step = validate_setting_range(spec["setting_range"])
    reference = spec["setting_range"].get("reference", ACCEPTED_REFERENCE)
    factor = reference_factor(reference, bus)
    token = reference.strip().lower()

    findings = []
    if token != ACCEPTED_REFERENCE:
        findings.append(
            "trip point is expressed against the %s; the clause refers it to "
            "the maximum direct current bus voltage, so the printed setting "
            "does not mean the volts it appears to" % token.replace("-", " ")
        )

    ladder = setting_ladder(low, high, step)
    adjustable = len(ladder) > 1
    if not adjustable:
        findings.append(
            "the setting range holds one point, so the trip point is fixed "
            "rather than ground adjustable"
        )

    records = setting_verdicts(ladder, factor, bus)
    usable = [record for record in records if record["admissible"]]
    floor_v, ceiling_v = admissible_window(bus)
    window_open = ceiling_v >= floor_v - VOLT_TOLERANCE_V
    if not window_open:
        findings.append(
            "sensing uncertainty closes the admissible window entirely; no "
            "trip point can sit above the equipment floor and below the "
            "steady state band at once"
        )

    if not usable:
        findings.append(
            "no settable point lands inside the admissible window; the ladder "
            "spans %.3f V to %.3f V against a window of %.3f V to %.3f V"
            % (records[0]["volts"], records[-1]["volts"], floor_v, ceiling_v)
        )
    else:
        for record in records:
            if not record["admissible"]:
                findings.append(
                    "setting %.4f (%.3f V) %s"
                    % (record["fraction"], record["volts"], record["reason"])
                )

    step_v = adjustment_step_volts(step, factor)
    resolution_adequate = step_v <= bus["sensing_uncertainty_v"] + VOLT_TOLERANCE_V
    if adjustable and not resolution_adequate:
        findings.append(
            "one adjustment step moves the trip point %.3f V, coarser than "
            "the %.3f V sensing uncertainty it has to be set within"
            % (step_v, bus["sensing_uncertainty_v"])
        )

    compliant = (
        token == ACCEPTED_REFERENCE
        and adjustable
        and window_open
        and len(usable) == len(records)
        and resolution_adequate
    )
    return {
        "reference": token,
        "reference_accepted": token == ACCEPTED_REFERENCE,
        "reference_volts": factor,
        "ground_adjustable": adjustable,
        "window_floor_v": floor_v,
        "window_ceiling_v": ceiling_v,
        "window_open": window_open,
        "setting_count": len(records),
        "usable_setting_count": len(usable),
        "lowest_trip_v": records[0]["volts"],
        "highest_trip_v": records[-1]["volts"],
        "adjustment_step_v": step_v,
        "resolution_adequate": resolution_adequate,
        "settings": records,
        "verdict": "compliant" if compliant else "non-compliant",
        "findings": findings,
    }
