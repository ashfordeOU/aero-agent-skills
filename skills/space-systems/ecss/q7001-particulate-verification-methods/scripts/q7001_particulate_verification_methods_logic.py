"""Particulate cleanliness measurement methods and their reduction to a level.

Anchor: ECSS-Q-ST-70-01C, verification clause -- applying the particulate
measurement methods (particle fallout on a witness plate, tape lift, vacuum
sampling and optical particle counting) and reducing what each returns to a
per-area figure comparable with the requirement. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the measured size distribution: bins of (diameter in micrometres,
   count), diameters strictly increasing, counts non-negative integers.
2. Subtract the blank of the sampling medium bin by bin. A blank larger than
   the sample in a bin is a control failure, not a negative count.
3. Correct for the recovery efficiency of the method used. Tape lift and
   vacuum sampling both leave particles behind, and the fraction they leave
   depends on the surface, so the efficiency is declared per run.
4. Normalise to the sampled area to get counts per square metre, and form the
   obscuration -- the percentage of the surface the projected particle areas
   cover -- from the same distribution.
5. For a fallout plate, divide the obscuration by the exposure time to get a
   deposition rate, and project that rate over an exposure of interest.
6. Compare the corrected obscuration against the allowed value, absorbing
   representation error at the boundary with a named tolerance.
"""

import math

__all__ = [
    "OBSCURATION_TOLERANCE",
    "METHOD_RECOVERY_REQUIRED",
    "validate_bins",
    "validate_area",
    "subtract_blank",
    "apply_recovery",
    "total_count",
    "counts_per_square_metre",
    "projected_area_um2",
    "obscuration_percent",
    "largest_particle_um",
    "fallout_rate_percent_per_hour",
    "project_fallout_percent",
    "method_is_applicable",
    "assess_particulate_measurement",
]

# Obscuration is a sum of squares divided by an area; an exact equality with
# the allowed value can land a few ULPs either side. Absorb it here.
OBSCURATION_TOLERANCE = 1e-9

# Methods that lift particles off the surface never lift all of them, so a
# recovery efficiency has to be declared for them before the reading counts.
METHOD_RECOVERY_REQUIRED = ("tape-lift", "vacuum-sampling")

# Methods this module knows how to reduce.
_KNOWN_METHODS = ("tape-lift", "vacuum-sampling", "fallout-plate", "particle-counting")


def _finite(label, value):
    """Return value as a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def validate_area(area_m2):
    """Return a positive sampled area in square metres."""
    area = _finite("area_m2", area_m2)
    if area <= 0.0:
        raise ValueError("area_m2 must be positive, got %r" % (area_m2,))
    return area


def validate_bins(bins, name="bins"):
    """Return the size distribution as a list of (diameter_um, count) pairs."""
    if not isinstance(bins, (list, tuple)) or not bins:
        raise ValueError("%s must be a non-empty sequence of (diameter_um, count)" % name)
    result = []
    for index, item in enumerate(bins):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("%s[%d] must be a (diameter_um, count) pair" % (name, index))
        diameter = _finite("%s[%d] diameter_um" % (name, index), item[0])
        if diameter <= 0.0:
            raise ValueError("%s[%d] diameter_um must be positive" % (name, index))
        count = item[1]
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError("%s[%d] count must be a non-negative integer" % (name, index))
        if count < 0:
            raise ValueError("%s[%d] count must not be negative" % (name, index))
        result.append((diameter, count))
    for index in range(1, len(result)):
        if result[index][0] <= result[index - 1][0]:
            raise ValueError("%s diameters must strictly increase (index %d)" % (name, index))
    return result


def subtract_blank(sample_bins, blank_bins):
    """Return the sample distribution with the medium blank removed bin by bin."""
    sample = validate_bins(sample_bins, "sample_bins")
    blank = validate_bins(blank_bins, "blank_bins")
    blank_map = dict(blank)
    for diameter in blank_map:
        if not any(math.isclose(diameter, d, rel_tol=1e-12, abs_tol=1e-12) for d, _ in sample):
            raise ValueError(
                "blank bin %g um has no matching sample bin; align the bin edges" % diameter
            )
    corrected = []
    for diameter, count in sample:
        removed = 0
        for blank_diameter, blank_count in blank:
            if math.isclose(diameter, blank_diameter, rel_tol=1e-12, abs_tol=1e-12):
                removed = blank_count
                break
        if removed > count:
            raise ValueError(
                "blank count %d exceeds the sample count %d at %g um; the sampling "
                "medium control failed" % (removed, count, diameter)
            )
        corrected.append((diameter, count - removed))
    return corrected


def apply_recovery(bins, recovery_fraction):
    """Return counts scaled up for the fraction the method leaves on the surface."""
    records = validate_bins(bins)
    recovery = _finite("recovery_fraction", recovery_fraction)
    if recovery <= 0.0 or recovery > 1.0:
        raise ValueError(
            "recovery_fraction must lie in (0, 1], got %r" % (recovery_fraction,)
        )
    return [(diameter, count / recovery) for diameter, count in records]


def total_count(bins):
    """Return the total particle count across the distribution."""
    if not isinstance(bins, (list, tuple)) or not bins:
        raise ValueError("bins must be a non-empty sequence")
    total = 0.0
    for item in bins:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("each bin must be a (diameter_um, count) pair")
        total += float(item[1])
    return total


def counts_per_square_metre(bins, area_m2):
    """Return the distribution normalised to one square metre of surface."""
    area = validate_area(area_m2)
    if not isinstance(bins, (list, tuple)) or not bins:
        raise ValueError("bins must be a non-empty sequence")
    return [(float(d), float(n) / area) for d, n in bins]


def projected_area_um2(bins):
    """Return the summed projected area of the distribution in square micrometres."""
    if not isinstance(bins, (list, tuple)) or not bins:
        raise ValueError("bins must be a non-empty sequence")
    total = 0.0
    for item in bins:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("each bin must be a (diameter_um, count) pair")
        diameter = _finite("diameter_um", item[0])
        if diameter <= 0.0:
            raise ValueError("diameter_um must be positive, got %r" % (item[0],))
        count = _finite("count", item[1])
        if count < 0.0:
            raise ValueError("count must not be negative, got %r" % (item[1],))
        total += count * math.pi * diameter * diameter / 4.0
    return total


def obscuration_percent(bins, area_m2):
    """Return the percentage of the sampled area covered by projected particles."""
    area = validate_area(area_m2)
    # One square metre is 1e12 square micrometres.
    return 100.0 * projected_area_um2(bins) / (area * 1.0e12)


def largest_particle_um(bins):
    """Return the diameter of the largest bin carrying a non-zero count."""
    if not isinstance(bins, (list, tuple)) or not bins:
        raise ValueError("bins must be a non-empty sequence")
    largest = None
    for item in bins:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("each bin must be a (diameter_um, count) pair")
        if float(item[1]) > 0.0:
            diameter = _finite("diameter_um", item[0])
            if largest is None or diameter > largest:
                largest = diameter
    if largest is None:
        raise ValueError("distribution carries no particles; nothing to size")
    return largest


def fallout_rate_percent_per_hour(obscuration, exposure_hours):
    """Return the fallout plate deposition rate in obscuration percent per hour."""
    value = _finite("obscuration", obscuration)
    if value < 0.0:
        raise ValueError("obscuration must not be negative, got %r" % (obscuration,))
    hours = _finite("exposure_hours", exposure_hours)
    if hours <= 0.0:
        raise ValueError("exposure_hours must be positive, got %r" % (exposure_hours,))
    return value / hours


def project_fallout_percent(rate_percent_per_hour, hours):
    """Return the obscuration a constant fallout rate accumulates over an exposure."""
    rate = _finite("rate_percent_per_hour", rate_percent_per_hour)
    if rate < 0.0:
        raise ValueError("rate_percent_per_hour must not be negative")
    span = _finite("hours", hours)
    if span < 0.0:
        raise ValueError("hours must not be negative")
    return rate * span


def method_is_applicable(method, surface):
    """Return (applicable, reason) for a method against a surface description."""
    if not isinstance(method, str) or method.strip().lower() not in _KNOWN_METHODS:
        raise ValueError("method must be one of %s, got %r" % (_KNOWN_METHODS, method))
    if not isinstance(surface, dict):
        raise ValueError("surface must be a mapping")
    name = method.strip().lower()
    accessible = bool(surface.get("accessible", True))
    adhesive_safe = bool(surface.get("adhesive_safe", True))
    area = validate_area(surface.get("area_m2", 1.0))
    if not accessible and name != "fallout-plate":
        return (False, "surface is not reachable; only a witness plate can stand in")
    if name == "tape-lift" and not adhesive_safe:
        return (False, "surface does not tolerate an adhesive lift")
    if name == "vacuum-sampling" and area < 0.1:
        return (False, "sampled area %.4g m2 is below the vacuum method minimum" % area)
    return (True, "applicable")


def assess_particulate_measurement(spec):
    """Reduce one particulate measurement and grade it against the allowed value.

    spec keys: method, bins, area_m2, allowed_obscuration_percent, optional
    blank_bins, recovery_fraction, exposure_hours, projection_hours.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("method", "bins", "area_m2", "allowed_obscuration_percent"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    method = spec["method"]
    if not isinstance(method, str) or method.strip().lower() not in _KNOWN_METHODS:
        raise ValueError("method must be one of %s, got %r" % (_KNOWN_METHODS, method))
    method = method.strip().lower()
    allowed = _finite("allowed_obscuration_percent", spec["allowed_obscuration_percent"])
    if allowed <= 0.0:
        raise ValueError("allowed_obscuration_percent must be positive")
    bins = validate_bins(spec["bins"])
    findings = []
    if spec.get("blank_bins") is not None:
        bins = subtract_blank(bins, spec["blank_bins"])
    recovery = spec.get("recovery_fraction")
    if method in METHOD_RECOVERY_REQUIRED:
        if recovery is None:
            raise ValueError(
                "method %s removes particles from the surface; declare "
                "recovery_fraction" % method
            )
        bins = apply_recovery(bins, recovery)
    elif recovery is not None:
        findings.append(
            "recovery_fraction declared for %s, which samples without removal; "
            "it was not applied" % method
        )
    area = validate_area(spec["area_m2"])
    obscuration = obscuration_percent(bins, area)
    result = {
        "method": method,
        "obscuration_percent": obscuration,
        "counts_per_square_metre": counts_per_square_metre(bins, area),
        "total_count": total_count(bins),
        "allowed_obscuration_percent": allowed,
    }
    if method == "fallout-plate":
        if "exposure_hours" not in spec:
            raise ValueError("a fallout-plate reading needs exposure_hours")
        rate = fallout_rate_percent_per_hour(obscuration, spec["exposure_hours"])
        result["fallout_rate_percent_per_hour"] = rate
        if spec.get("projection_hours") is not None:
            result["projected_obscuration_percent"] = project_fallout_percent(
                rate, spec["projection_hours"]
            )
    compliant = obscuration < allowed or math.isclose(
        obscuration, allowed, rel_tol=OBSCURATION_TOLERANCE, abs_tol=0.0
    )
    if not compliant:
        findings.append(
            "obscuration %.6g%% exceeds the allowed %.6g%%" % (obscuration, allowed)
        )
    result["compliant"] = compliant
    result["findings"] = findings
    return result
