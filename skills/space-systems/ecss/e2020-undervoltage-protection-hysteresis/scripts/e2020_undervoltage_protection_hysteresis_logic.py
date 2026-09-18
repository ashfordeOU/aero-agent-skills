"""Hysteresis on the undervoltage trip of a current limiter.

Anchor: ECSS-E-ST-20-20C clause 5.2.5.2.1 (a hysteresis band between the
undervoltage drop-out threshold and the re-arm threshold; mandatory where the
limiter re-triggers on its own, recommended for the other limiter categories).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise the limiter category and read the obligation the clause places on
   it: a retriggerable limiter re-arms without a command, so an absent band
   leaves it oscillating between trip and re-arm at the disturbance rate and
   the band is mandatory. A latching or high-power limiter stays down until it
   is commanded, so the band is recommended and a shortfall is advisory.
2. Derive the designed band from the two declared thresholds, together with the
   band expressed as a fraction of the drop-out threshold.
3. Build the disturbance envelope the band has to clear: the peak-to-peak bus
   ripple, the sensing uncertainty counted once at each threshold, and the
   transient droop the bus shows on the largest load step.
4. Apply the design margin factor to the envelope to obtain the required band,
   and compare. An exact equality at the bound is a representation question and
   is absorbed by a named tolerance, not by relaxing the envelope.
5. Check the re-arm threshold against the nominal bus: a re-arm point at or
   above nominal can never be reached, so the limiter would stay down for good.
"""

import math

__all__ = [
    "HYSTERESIS_TOLERANCE_V",
    "LIMITER_CATEGORIES",
    "normalise_category",
    "hysteresis_obligation",
    "validate_voltage",
    "hysteresis_band_v",
    "hysteresis_fraction",
    "disturbance_envelope_v",
    "required_hysteresis_v",
    "chatter_margin_v",
    "assess_hysteresis",
]

# Threshold arithmetic is a difference of two floats that a design can place
# exactly on the required band. Absorb the representation error here instead of
# moving the engineering limit.
HYSTERESIS_TOLERANCE_V = 1e-9

# Obligation the clause places on each limiter category.
LIMITER_CATEGORIES = {
    "retriggerable": "mandatory",
    "latching": "recommended",
    "high-power": "recommended",
    "foldback": "recommended",
}

_ALIASES = {
    "rcl": "retriggerable",
    "retriggerable-limiter": "retriggerable",
    "lcl": "latching",
    "latching-current-limiter": "latching",
    "hpc": "high-power",
    "high-power-limiter": "high-power",
    "fcl": "foldback",
}


def normalise_category(category):
    """Return the canonical limiter category name."""
    if not isinstance(category, str):
        raise ValueError("category must be a string, got %r" % (category,))
    key = category.strip().lower()
    if not key:
        raise ValueError("category must not be empty")
    key = _ALIASES.get(key, key)
    if key not in LIMITER_CATEGORIES:
        raise ValueError(
            "unknown limiter category %r; known: %s"
            % (category, ", ".join(sorted(LIMITER_CATEGORIES)))
        )
    return key


def hysteresis_obligation(category):
    """Return 'mandatory' or 'recommended' for the limiter category."""
    return LIMITER_CATEGORIES[normalise_category(category)]


def validate_voltage(value, label, allow_zero=False):
    """Return the value as a finite float, rejecting bad input outright."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0 or (number == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def hysteresis_band_v(trip_v, rearm_v):
    """Return the designed hysteresis band in volts.

    A zero band is a real design (no hysteresis) and is returned as zero; a
    re-arm threshold below the drop-out threshold is an input error.
    """
    trip = validate_voltage(trip_v, "trip_v")
    rearm = validate_voltage(rearm_v, "rearm_v")
    if rearm < trip and not math.isclose(
        rearm, trip, rel_tol=0.0, abs_tol=HYSTERESIS_TOLERANCE_V
    ):
        raise ValueError(
            "rearm_v %g must not sit below trip_v %g; the band would be negative"
            % (rearm, trip)
        )
    band = rearm - trip
    return band if band > 0.0 else 0.0


def hysteresis_fraction(trip_v, rearm_v):
    """Return the hysteresis band as a fraction of the drop-out threshold."""
    trip = validate_voltage(trip_v, "trip_v")
    return hysteresis_band_v(trip, rearm_v) / trip


def disturbance_envelope_v(ripple_pk_pk_v, sensing_uncertainty_v, transient_droop_v):
    """Return the bus disturbance the band has to clear, in volts.

    The sensing uncertainty is counted once at the drop-out comparator and once
    at the re-arm comparator, because either one can move toward the other.
    """
    ripple = validate_voltage(ripple_pk_pk_v, "ripple_pk_pk_v", allow_zero=True)
    uncertainty = validate_voltage(
        sensing_uncertainty_v, "sensing_uncertainty_v", allow_zero=True
    )
    droop = validate_voltage(transient_droop_v, "transient_droop_v", allow_zero=True)
    return ripple + 2.0 * uncertainty + droop


def required_hysteresis_v(envelope_v, margin_factor=1.0):
    """Return the band the design owes: the envelope carrying its margin."""
    envelope = validate_voltage(envelope_v, "envelope_v", allow_zero=True)
    if not isinstance(margin_factor, (int, float)) or isinstance(margin_factor, bool):
        raise ValueError("margin_factor must be a real number, got %r" % (margin_factor,))
    factor = float(margin_factor)
    if not math.isfinite(factor):
        raise ValueError("margin_factor must be finite")
    if factor < 1.0 and not math.isclose(factor, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("margin_factor must be at least unity, got %g" % factor)
    return envelope * factor


def chatter_margin_v(band_v, required_v):
    """Return band minus requirement; negative means the trip can chatter."""
    band = validate_voltage(band_v, "band_v", allow_zero=True)
    required = validate_voltage(required_v, "required_v", allow_zero=True)
    return band - required


def assess_hysteresis(spec):
    """Grade one undervoltage protection design against clause 5.2.5.2.1.

    spec keys: category, trip_v, rearm_v, bus_nominal_v, ripple_pk_pk_v,
    sensing_uncertainty_v, transient_droop_v, optional margin_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "category",
        "trip_v",
        "rearm_v",
        "bus_nominal_v",
        "ripple_pk_pk_v",
        "sensing_uncertainty_v",
        "transient_droop_v",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    category = normalise_category(spec["category"])
    obligation = LIMITER_CATEGORIES[category]
    trip = validate_voltage(spec["trip_v"], "trip_v")
    rearm = validate_voltage(spec["rearm_v"], "rearm_v")
    nominal = validate_voltage(spec["bus_nominal_v"], "bus_nominal_v")
    band = hysteresis_band_v(trip, rearm)
    envelope = disturbance_envelope_v(
        spec["ripple_pk_pk_v"],
        spec["sensing_uncertainty_v"],
        spec["transient_droop_v"],
    )
    required = required_hysteresis_v(envelope, spec.get("margin_factor", 1.0))
    margin = chatter_margin_v(band, required)

    present = band > HYSTERESIS_TOLERANCE_V
    sufficient = margin > 0.0 or math.isclose(
        margin, 0.0, rel_tol=0.0, abs_tol=HYSTERESIS_TOLERANCE_V
    )

    band_findings = []
    if not present:
        band_findings.append(
            "no hysteresis between the drop-out threshold %g V and the re-arm "
            "threshold %g V" % (trip, rearm)
        )
    elif not sufficient:
        band_findings.append(
            "hysteresis band %g V is short of the %g V the bus disturbance "
            "envelope demands" % (band, required)
        )

    # Threshold placement is wrong for every limiter category; it is not
    # softened by the clause recommending rather than mandating the band.
    placement_findings = []
    if trip > nominal or math.isclose(
        trip, nominal, rel_tol=0.0, abs_tol=HYSTERESIS_TOLERANCE_V
    ):
        placement_findings.append(
            "drop-out threshold %g V is not below the nominal bus %g V; the "
            "limiter would trip on a healthy bus" % (trip, nominal)
        )
    if rearm > nominal and not math.isclose(
        rearm, nominal, rel_tol=0.0, abs_tol=HYSTERESIS_TOLERANCE_V
    ):
        placement_findings.append(
            "re-arm threshold %g V sits above the nominal bus %g V and can "
            "never be reached" % (rearm, nominal)
        )

    findings = band_findings + placement_findings
    if placement_findings:
        verdict = "non-compliant"
    elif present and sufficient:
        verdict = "compliant"
    elif obligation == "mandatory":
        verdict = "non-compliant"
    else:
        verdict = "advisory"

    return {
        "category": category,
        "obligation": obligation,
        "band_v": band,
        "band_fraction": band / trip,
        "envelope_v": envelope,
        "required_band_v": required,
        "chatter_margin_v": margin,
        "hysteresis_present": present,
        "hysteresis_sufficient": sufficient,
        "verdict": verdict,
        "findings": findings,
    }
