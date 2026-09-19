"""Airborne particle counting against a cleanroom class limit.

Anchor: ECSS-Q-ST-70-50C airborne clause, which carries the air cleanliness
grading over to the ISO 14644-1 concentration limits. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the cleanroom class designation and the considered particle size.
2. Evaluate the maximum permitted concentration for that class and size from
   the ISO relation Cn = 10^N * (0.1 / D)^2.08, with D in micrometres and Cn
   in particles per cubic metre, rounded to three significant figures.
3. Convert a counted number of particles and a sampled air volume into a
   concentration in the same unit, so instrument output and limit are
   comparable without a hidden unit change.
4. Check that the instrument can resolve the considered size at all; a
   counter whose smallest resolvable size is above the considered size did
   not measure it.
5. Grade every location reading against the limit, absorbing the equality at
   the limit with a relative tolerance instead of relaxing the limit, and
   report the worst location, the margin and the findings.

Rounding note
-------------
The three-significant-figure rounding is done in decimal, not by scaling with
a power of ten, because 10**x is not correctly rounded and rounds differently
across platforms. The rounded limit is therefore identical everywhere.
"""

import math
from decimal import Decimal, ROUND_HALF_UP

__all__ = [
    "SIZE_EXPONENT",
    "MIN_SIZE_UM",
    "MAX_SIZE_UM",
    "MIN_CLASS",
    "MAX_CLASS",
    "SIGNIFICANT_DIGITS",
    "CONCENTRATION_TOLERANCE_REL",
    "round_significant",
    "validate_class",
    "validate_size_um",
    "validate_volume_l",
    "class_limit_per_m3",
    "concentration_per_m3",
    "instrument_resolves",
    "evaluate_location",
    "assess_airborne_counting",
]

# Slope of the ISO size-distribution relation.
SIZE_EXPONENT = 2.08

# The relation is stated over this size span; outside it the distribution
# shape is different and the relation is not the right instrument.
MIN_SIZE_UM = 0.1
MAX_SIZE_UM = 5.0

MIN_CLASS = 1.0
MAX_CLASS = 9.0

SIGNIFICANT_DIGITS = 3

# A measured concentration landing exactly on the limit is a representation
# question, not an engineering one. Absorb it here, never by moving the limit.
CONCENTRATION_TOLERANCE_REL = 1e-9


def round_significant(value, digits=SIGNIFICANT_DIGITS):
    """Round a positive value to a number of significant digits, in decimal."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("value must be a real number, got %r" % (value,))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("value must be finite")
    if not isinstance(digits, int) or isinstance(digits, bool):
        raise ValueError("digits must be an integer, got %r" % (digits,))
    if digits < 1:
        raise ValueError("digits must be at least 1, got %d" % digits)
    if number == 0.0:
        return 0.0
    decimal_value = Decimal(number)
    exponent = decimal_value.adjusted()
    quantum = Decimal(1).scaleb(exponent - (digits - 1))
    return float(decimal_value.quantize(quantum, rounding=ROUND_HALF_UP))


def validate_class(iso_class):
    """Return the validated cleanroom class designation as a float."""
    if not isinstance(iso_class, (int, float)) or isinstance(iso_class, bool):
        raise ValueError("iso_class must be a real number, got %r" % (iso_class,))
    value = float(iso_class)
    if not math.isfinite(value):
        raise ValueError("iso_class must be finite")
    if value < MIN_CLASS or value > MAX_CLASS:
        raise ValueError(
            "iso_class must lie in [%g, %g], got %g" % (MIN_CLASS, MAX_CLASS, value)
        )
    return value


def validate_size_um(size_um):
    """Return the validated considered particle size in micrometres."""
    if not isinstance(size_um, (int, float)) or isinstance(size_um, bool):
        raise ValueError("size_um must be a real number, got %r" % (size_um,))
    value = float(size_um)
    if not math.isfinite(value):
        raise ValueError("size_um must be finite")
    if value < MIN_SIZE_UM or value > MAX_SIZE_UM:
        raise ValueError(
            "the size relation is stated over [%g, %g] um; %g is outside it"
            % (MIN_SIZE_UM, MAX_SIZE_UM, value)
        )
    return value


def validate_volume_l(volume_l):
    """Return the validated sampled air volume in litres."""
    if not isinstance(volume_l, (int, float)) or isinstance(volume_l, bool):
        raise ValueError("volume_l must be a real number, got %r" % (volume_l,))
    value = float(volume_l)
    if not math.isfinite(value):
        raise ValueError("volume_l must be finite")
    if value <= 0.0:
        raise ValueError("volume_l must be positive, got %g" % value)
    return value


def class_limit_per_m3(iso_class, size_um, digits=SIGNIFICANT_DIGITS):
    """Return the maximum permitted concentration in particles per cubic metre."""
    number = validate_class(iso_class)
    size = validate_size_um(size_um)
    raw = math.pow(10.0, number) * math.pow(MIN_SIZE_UM / size, SIZE_EXPONENT)
    return round_significant(raw, digits)


def concentration_per_m3(counts, volume_l):
    """Convert a counted particle number and a sampled volume to per cubic metre."""
    if not isinstance(counts, (int, float)) or isinstance(counts, bool):
        raise ValueError("counts must be a real number, got %r" % (counts,))
    number = float(counts)
    if not math.isfinite(number):
        raise ValueError("counts must be finite")
    if number < 0.0:
        raise ValueError("counts must not be negative, got %g" % number)
    volume = validate_volume_l(volume_l)
    return number * 1000.0 / volume


def instrument_resolves(size_um, instrument_min_size_um):
    """Return True when the counter can resolve the considered size."""
    size = validate_size_um(size_um)
    if not isinstance(instrument_min_size_um, (int, float)) or isinstance(
        instrument_min_size_um, bool
    ):
        raise ValueError("instrument_min_size_um must be a real number")
    smallest = float(instrument_min_size_um)
    if not math.isfinite(smallest) or smallest <= 0.0:
        raise ValueError("instrument_min_size_um must be positive and finite")
    if math.isclose(smallest, size, rel_tol=CONCENTRATION_TOLERANCE_REL, abs_tol=0.0):
        return True
    return smallest < size


def evaluate_location(reading, iso_class, size_um):
    """Grade one location reading against the class limit.

    reading keys: location, counts, volume_l, optional concentration_per_m3
    (used directly when the counter already reports a concentration).
    """
    if not isinstance(reading, dict):
        raise ValueError("reading must be a mapping")
    if "location" not in reading:
        raise ValueError("reading missing required key 'location'")
    location = reading["location"]
    if not isinstance(location, str) or not location.strip():
        raise ValueError("reading['location'] must be a non-empty string")

    if "concentration_per_m3" in reading:
        measured = reading["concentration_per_m3"]
        if not isinstance(measured, (int, float)) or isinstance(measured, bool):
            raise ValueError("concentration_per_m3 must be a real number")
        measured = float(measured)
        if not math.isfinite(measured) or measured < 0.0:
            raise ValueError("concentration_per_m3 must be finite and non-negative")
    else:
        for key in ("counts", "volume_l"):
            if key not in reading:
                raise ValueError("reading missing required key '%s'" % key)
        measured = concentration_per_m3(reading["counts"], reading["volume_l"])

    limit = class_limit_per_m3(iso_class, size_um)
    at_limit = math.isclose(measured, limit, rel_tol=CONCENTRATION_TOLERANCE_REL, abs_tol=0.0)
    compliant = at_limit or measured < limit
    return {
        "location": location.strip(),
        "measured_per_m3": measured,
        "limit_per_m3": limit,
        "utilisation": measured / limit,
        "margin_per_m3": limit - measured,
        "compliant": compliant,
    }


def assess_airborne_counting(spec):
    """Grade a set of location readings against a cleanroom class.

    spec keys: iso_class, size_um, readings (sequence of reading mappings),
    optional instrument_min_size_um.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("iso_class", "size_um", "readings"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    iso_class = validate_class(spec["iso_class"])
    size = validate_size_um(spec["size_um"])
    readings = spec["readings"]
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError("spec['readings'] must be a non-empty sequence")

    findings = []
    smallest = spec.get("instrument_min_size_um")
    if smallest is not None and not instrument_resolves(size, smallest):
        findings.append(
            "the counter resolves down to %g um only; it cannot report the %g um channel"
            % (float(smallest), size)
        )

    results = []
    seen = []
    for reading in readings:
        record = evaluate_location(reading, iso_class, size)
        if record["location"] in seen:
            findings.append("location %r appears more than once in the run" % record["location"])
        else:
            seen.append(record["location"])
        results.append(record)

    worst = results[0]
    for record in results[1:]:
        if record["utilisation"] > worst["utilisation"]:
            worst = record

    failed = [r["location"] for r in results if not r["compliant"]]
    if failed:
        findings.append(
            "location(s) over the class limit: %s" % ", ".join(failed)
        )

    limit = class_limit_per_m3(iso_class, size)
    return {
        "iso_class": iso_class,
        "size_um": size,
        "limit_per_m3": limit,
        "results": results,
        "worst_location": worst,
        "failed_locations": failed,
        "compliant": not failed and not findings,
        "findings": findings,
    }
