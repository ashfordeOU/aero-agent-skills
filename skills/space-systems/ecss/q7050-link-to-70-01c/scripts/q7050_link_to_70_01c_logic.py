"""Handover of particle contamination monitoring results into cleanliness verification.

Anchor: the interface between particle contamination monitoring and the surface
cleanliness requirement set of ECSS-Q-ST-70-01C. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the collecting area, the monitored period and the per-size-bin
   fallout counts read off the witness plates or fallout monitors.
2. Form the per-bin fallout rate (particles per square metre per day).
3. Check the projection horizon: an exposure much longer than the monitored
   period is an unobserved environment, and the projection is refused.
4. Project each bin over the exposure duration and the exposed area.
5. Sum the projected obscured area bin by bin (the area is quadratic in the
   bin diameter) and express it as a percentage area coverage.
6. Detect the lower-bound case, where the requirement reference size is
   coarser than the coarsest monitored bin and the unmonitored coarse tail
   carries area that was never collected.
7. Read the cleanliness level met off the programme level table and compare it
   with the declared level, absorbing representation error with a named
   tolerance.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE_PERCENT",
    "DEFAULT_MAX_EXTRAPOLATION_FACTOR",
    "validate_positive",
    "validate_bins",
    "fallout_rates",
    "projection_factor",
    "project_bins",
    "bin_obscured_area_m2",
    "percentage_area_coverage",
    "coarsest_bin_um",
    "level_for_coverage",
    "assess_monitoring_handover",
]

# A coverage comparison is a difference of two floating-point sums: an exact
# equality at a level boundary can land a few ULP on the wrong side. Absorb the
# representation error here instead of moving the programme's boundary.
COVERAGE_TOLERANCE_PERCENT = 1e-9

# How far past the monitored period a measured fallout rate may be projected
# before the deposition environment counts as unobserved.
DEFAULT_MAX_EXTRAPOLATION_FACTOR = 10.0

_SQUARE_METRES_PER_SQUARE_MICROMETRE = 1e-12


def validate_positive(value, label):
    """Return value as a positive finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_bins(bins):
    """Return the monitoring bins as a list of (diameter_um, count) pairs.

    Bins are sorted by diameter. A non-positive diameter, a negative count, a
    boolean or a duplicated diameter is an input error.
    """
    if not isinstance(bins, (list, tuple)) or not bins:
        raise ValueError("bins must be a non-empty sequence of (diameter_um, count) pairs")
    cleaned = []
    for index, item in enumerate(bins):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("bins[%d] must be a (diameter_um, count) pair" % index)
        diameter, count = item
        diameter = validate_positive(diameter, "bins[%d] diameter_um" % index)
        if not isinstance(count, (int, float)) or isinstance(count, bool):
            raise ValueError("bins[%d] count must be a real number" % index)
        count = float(count)
        if not math.isfinite(count):
            raise ValueError("bins[%d] count must be finite" % index)
        if count < 0.0:
            raise ValueError("bins[%d] count must not be negative, got %r" % (index, count))
        cleaned.append((diameter, count))
    cleaned.sort(key=lambda pair: pair[0])
    for i in range(1, len(cleaned)):
        if cleaned[i][0] == cleaned[i - 1][0]:
            raise ValueError("bins carry a duplicated diameter %g um" % cleaned[i][0])
    return cleaned


def fallout_rates(bins, collecting_area_m2, monitored_days):
    """Return [(diameter_um, particles per m2 per day)] for the monitoring run."""
    cleaned = validate_bins(bins)
    area = validate_positive(collecting_area_m2, "collecting_area_m2")
    days = validate_positive(monitored_days, "monitored_days")
    return [(diameter, count / area / days) for diameter, count in cleaned]


def projection_factor(exposure_days, monitored_days):
    """Return how many monitored periods the exposure duration spans."""
    exposure = validate_positive(exposure_days, "exposure_days")
    monitored = validate_positive(monitored_days, "monitored_days")
    return exposure / monitored


def project_bins(rates, exposed_area_m2, exposure_days, monitored_days,
                 max_extrapolation_factor=DEFAULT_MAX_EXTRAPOLATION_FACTOR):
    """Project per-bin fallout rates onto the exposed area over the exposure.

    Raises when the exposure reaches further beyond the monitored period than
    max_extrapolation_factor allows: past that horizon the deposition
    environment was never observed.
    """
    if not isinstance(rates, (list, tuple)) or not rates:
        raise ValueError("rates must be a non-empty sequence of (diameter_um, rate) pairs")
    area = validate_positive(exposed_area_m2, "exposed_area_m2")
    limit = validate_positive(max_extrapolation_factor, "max_extrapolation_factor")
    factor = projection_factor(exposure_days, monitored_days)
    if factor > limit:
        raise ValueError(
            "exposure spans %.3f monitored periods; the allowed extrapolation factor "
            "is %.3f, projection refused" % (factor, limit)
        )
    exposure = float(exposure_days)
    projected = []
    for index, item in enumerate(rates):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("rates[%d] must be a (diameter_um, rate) pair" % index)
        diameter = validate_positive(item[0], "rates[%d] diameter_um" % index)
        rate = item[1]
        if not isinstance(rate, (int, float)) or isinstance(rate, bool):
            raise ValueError("rates[%d] rate must be a real number" % index)
        rate = float(rate)
        if not math.isfinite(rate) or rate < 0.0:
            raise ValueError("rates[%d] rate must be finite and non-negative" % index)
        projected.append((diameter, rate * area * exposure))
    return projected


def bin_obscured_area_m2(diameter_um, count):
    """Return the area obscured by count particles of the bin diameter."""
    diameter = validate_positive(diameter_um, "diameter_um")
    if not isinstance(count, (int, float)) or isinstance(count, bool):
        raise ValueError("count must be a real number")
    number = float(count)
    if not math.isfinite(number) or number < 0.0:
        raise ValueError("count must be finite and non-negative, got %r" % (count,))
    disc_um2 = math.pi * diameter * diameter / 4.0
    return number * disc_um2 * _SQUARE_METRES_PER_SQUARE_MICROMETRE


def percentage_area_coverage(bins, area_m2):
    """Return the percentage of area_m2 obscured by the bin population."""
    cleaned = validate_bins(bins)
    area = validate_positive(area_m2, "area_m2")
    obscured = sum(bin_obscured_area_m2(diameter, count) for diameter, count in cleaned)
    return 100.0 * obscured / area


def coarsest_bin_um(bins):
    """Return the largest monitored bin diameter."""
    return validate_bins(bins)[-1][0]


def level_for_coverage(coverage_percent, level_table,
                       tolerance=COVERAGE_TOLERANCE_PERCENT):
    """Return the first level whose coverage allowance holds the coverage.

    level_table is the programme table as a sequence of
    (max_coverage_percent, level_name) pairs. None is returned when the
    coverage exceeds every tabulated level.
    """
    if not isinstance(coverage_percent, (int, float)) or isinstance(coverage_percent, bool):
        raise ValueError("coverage_percent must be a real number")
    value = float(coverage_percent)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("coverage_percent must be finite and non-negative")
    if not isinstance(level_table, (list, tuple)) or not level_table:
        raise ValueError("level_table must be a non-empty sequence of (max_percent, name)")
    entries = []
    for index, item in enumerate(level_table):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("level_table[%d] must be a (max_percent, name) pair" % index)
        ceiling = validate_positive(item[0], "level_table[%d] max_percent" % index)
        name = item[1]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("level_table[%d] name must be a non-empty string" % index)
        entries.append((ceiling, name))
    entries.sort(key=lambda pair: pair[0])
    tol = float(tolerance)
    for ceiling, name in entries:
        if value <= ceiling + tol:
            return name
    return None


def _level_ceiling(level_table, level_name):
    for item in level_table:
        if item[1] == level_name:
            return float(item[0])
    raise ValueError("declared level %r is not in the level table" % (level_name,))


def assess_monitoring_handover(spec):
    """Run the monitoring-to-verification handover.

    spec keys: bins, collecting_area_m2, monitored_days, exposed_area_m2,
    exposure_days, level_table, declared_level, requirement_reference_um,
    optional max_extrapolation_factor.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "bins",
        "collecting_area_m2",
        "monitored_days",
        "exposed_area_m2",
        "exposure_days",
        "level_table",
        "declared_level",
        "requirement_reference_um",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    cleaned = validate_bins(spec["bins"])
    rates = fallout_rates(cleaned, spec["collecting_area_m2"], spec["monitored_days"])
    projected = project_bins(
        rates,
        spec["exposed_area_m2"],
        spec["exposure_days"],
        spec["monitored_days"],
        spec.get("max_extrapolation_factor", DEFAULT_MAX_EXTRAPOLATION_FACTOR),
    )
    coverage = percentage_area_coverage(projected, spec["exposed_area_m2"])
    level_met = level_for_coverage(coverage, spec["level_table"])
    declared_ceiling = _level_ceiling(spec["level_table"], spec["declared_level"])
    reference_um = validate_positive(spec["requirement_reference_um"], "requirement_reference_um")
    coarsest = coarsest_bin_um(cleaned)
    lower_bound = reference_um > coarsest
    findings = []
    meets_declared = coverage <= declared_ceiling + COVERAGE_TOLERANCE_PERCENT
    if not meets_declared:
        findings.append(
            "projected coverage %.6f percent exceeds the %.6f percent allowed by the "
            "declared level %s" % (coverage, declared_ceiling, spec["declared_level"])
        )
    if level_met is None:
        findings.append("projected coverage sits above every tabulated cleanliness level")
    if lower_bound:
        findings.append(
            "requirement reference size %.3f um is coarser than the coarsest monitored "
            "bin %.3f um; the coverage is a lower bound" % (reference_um, coarsest)
        )
    return {
        "fallout_rates": rates,
        "projected_bins": projected,
        "projection_factor": projection_factor(spec["exposure_days"], spec["monitored_days"]),
        "coverage_percent": coverage,
        "level_met": level_met,
        "declared_level": spec["declared_level"],
        "declared_ceiling_percent": declared_ceiling,
        "lower_bound": lower_bound,
        "meets_declared_level": meets_declared,
        "verified": meets_declared and not lower_bound,
        "findings": findings,
    }
