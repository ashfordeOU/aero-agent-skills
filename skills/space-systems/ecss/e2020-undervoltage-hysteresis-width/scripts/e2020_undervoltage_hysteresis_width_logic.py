"""Minimum width between the undervoltage trip point and the enable point.

Anchor: ECSS-E-ST-20-20C clause 5.4.3.5.1 (where an undervoltage protection
carries hysteresis, a minimum separation is kept between the trip point and
the point at which the function enables again). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the two thresholds, the nominal main bus voltage and the tolerance
   each threshold is set and sensed with. An enable point below the trip point
   is an input error rather than a negative width.
2. Derive the declared separation, and the same separation expressed as a
   fraction of the nominal bus so it can be compared across bus voltages.
3. Decide whether hysteresis exists at all. The clause states how wide the gap
   has to be once it is there; a design with the two points on top of each
   other falls outside it and is reported that way instead of being failed.
4. Erode the declared separation by both tolerances together: the trip
   comparator can sit at the top of its band while the enable comparator sits
   at the bottom of its own, so the guaranteed width is what is left.
5. Form the required width from the minimum fraction referred to the nominal
   bus and from any absolute floor in volts, taking whichever binds harder.
6. Compare, absorbing an exact landing on the bound with a named tolerance,
   and check that both thresholds are reachable on the bus they protect.
"""

import math

__all__ = [
    "WIDTH_TOLERANCE_V",
    "validate_voltage",
    "validate_fraction",
    "declared_separation_v",
    "separation_fraction",
    "hysteresis_declared",
    "worst_case_separation_v",
    "required_width_v",
    "width_margin_v",
    "threshold_placement_findings",
    "assess_hysteresis_width",
]

# The separation is a difference of two floats that a design can place exactly
# on the required width. Absorb the representation error here rather than
# moving the engineering limit.
WIDTH_TOLERANCE_V = 1e-9


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


def validate_fraction(value, label, allow_zero=True):
    """Return a fraction of the bus voltage as a float in the unit interval."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0 or (number == 0.0 and not allow_zero):
        raise ValueError("%s must be a positive fraction, got %g" % (label, number))
    if number >= 1.0:
        raise ValueError(
            "%s must be a fraction of the bus below unity, got %g; a percentage "
            "value has to be divided by 100 first" % (label, number)
        )
    return number


def declared_separation_v(trip_v, enable_v):
    """Return the separation the design declares, in volts.

    A zero separation is a real design (no hysteresis) and comes back as zero;
    an enable point below the trip point is an input error.
    """
    trip = validate_voltage(trip_v, "trip_v")
    enable = validate_voltage(enable_v, "enable_v")
    if enable < trip and not math.isclose(
        enable, trip, rel_tol=0.0, abs_tol=WIDTH_TOLERANCE_V
    ):
        raise ValueError(
            "enable_v %g must not sit below trip_v %g; the separation would be "
            "negative" % (enable, trip)
        )
    gap = enable - trip
    return gap if gap > 0.0 else 0.0


def separation_fraction(trip_v, enable_v, nominal_v):
    """Return the declared separation as a fraction of the nominal bus."""
    nominal = validate_voltage(nominal_v, "nominal_v")
    return declared_separation_v(trip_v, enable_v) / nominal


def hysteresis_declared(trip_v, enable_v):
    """Return True when the design actually separates the two points."""
    return declared_separation_v(trip_v, enable_v) > WIDTH_TOLERANCE_V


def worst_case_separation_v(trip_v, enable_v, trip_tolerance_v, enable_tolerance_v):
    """Return the width left once both comparators drift toward each other.

    The trip point can settle at the top of its band and the enable point at
    the bottom of its own, so the two tolerances subtract together. A stack
    wider than the declared gap leaves nothing and returns zero.
    """
    gap = declared_separation_v(trip_v, enable_v)
    trip_tol = validate_voltage(trip_tolerance_v, "trip_tolerance_v", allow_zero=True)
    enable_tol = validate_voltage(
        enable_tolerance_v, "enable_tolerance_v", allow_zero=True
    )
    remaining = gap - trip_tol - enable_tol
    return remaining if remaining > 0.0 else 0.0


def required_width_v(nominal_v, minimum_fraction, absolute_floor_v=0.0):
    """Return the width the design owes, in volts.

    Where a project states both a fraction of the nominal bus and an absolute
    floor, the binding requirement is the larger of the two.
    """
    nominal = validate_voltage(nominal_v, "nominal_v")
    fraction = validate_fraction(minimum_fraction, "minimum_fraction")
    floor = validate_voltage(absolute_floor_v, "absolute_floor_v", allow_zero=True)
    return max(nominal * fraction, floor)


def width_margin_v(worst_case_v, required_v):
    """Return worst case minus requirement; negative is a shortfall."""
    worst = validate_voltage(worst_case_v, "worst_case_v", allow_zero=True)
    required = validate_voltage(required_v, "required_v", allow_zero=True)
    return worst - required


def threshold_placement_findings(trip_v, enable_v, nominal_v):
    """Return findings for a threshold the protected bus can never reach."""
    trip = validate_voltage(trip_v, "trip_v")
    enable = validate_voltage(enable_v, "enable_v")
    nominal = validate_voltage(nominal_v, "nominal_v")
    findings = []
    if trip > nominal or math.isclose(
        trip, nominal, rel_tol=0.0, abs_tol=WIDTH_TOLERANCE_V
    ):
        findings.append(
            "trip point %g V is not below the nominal bus %g V; the protection "
            "would act on a healthy bus" % (trip, nominal)
        )
    if enable > nominal or math.isclose(
        enable, nominal, rel_tol=0.0, abs_tol=WIDTH_TOLERANCE_V
    ):
        findings.append(
            "enable point %g V is not below the nominal bus %g V and can never "
            "be crossed on the way up" % (enable, nominal)
        )
    return findings


def assess_hysteresis_width(spec):
    """Grade one undervoltage hysteresis width against clause 5.4.3.5.1.

    spec keys: trip_v, enable_v, nominal_v, trip_tolerance_v,
    enable_tolerance_v, minimum_fraction, optional absolute_floor_v.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (type(spec).__name__,))
    required_keys = (
        "trip_v",
        "enable_v",
        "nominal_v",
        "trip_tolerance_v",
        "enable_tolerance_v",
        "minimum_fraction",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    trip = validate_voltage(spec["trip_v"], "trip_v")
    enable = validate_voltage(spec["enable_v"], "enable_v")
    nominal = validate_voltage(spec["nominal_v"], "nominal_v")
    declared = declared_separation_v(trip, enable)
    declared_pct = 100.0 * declared / nominal
    present = declared > WIDTH_TOLERANCE_V
    worst = worst_case_separation_v(
        trip, enable, spec["trip_tolerance_v"], spec["enable_tolerance_v"]
    )
    required = required_width_v(
        nominal, spec["minimum_fraction"], spec.get("absolute_floor_v", 0.0)
    )
    margin = width_margin_v(worst, required)
    sufficient = margin > 0.0 or math.isclose(
        margin, 0.0, rel_tol=0.0, abs_tol=WIDTH_TOLERANCE_V
    )

    placement = threshold_placement_findings(trip, enable, nominal)
    findings = list(placement)
    if not present:
        findings.append(
            "no hysteresis declared: the enable point %g V sits on the trip "
            "point %g V, so the minimum width of this clause does not apply"
            % (enable, trip)
        )
    elif not sufficient:
        if worst <= WIDTH_TOLERANCE_V:
            findings.append(
                "the %g V setting and sensing tolerance stack consumes the whole "
                "declared separation of %g V" % (declared - worst, declared)
            )
        findings.append(
            "worst-case width %g V is short of the %g V required on a %g V bus"
            % (worst, required, nominal)
        )

    if placement:
        verdict = "non-compliant"
    elif not present:
        verdict = "not-applicable"
    elif sufficient:
        verdict = "compliant"
    else:
        verdict = "non-compliant"

    return {
        "declared_separation_v": declared,
        "declared_separation_pct_nominal": declared_pct,
        "hysteresis_declared": present,
        "worst_case_separation_v": worst,
        "required_width_v": required,
        "width_margin_v": margin,
        "width_sufficient": sufficient,
        "verdict": verdict,
        "findings": findings,
    }
