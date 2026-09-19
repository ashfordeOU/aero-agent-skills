"""Application of particle cleanliness limits and levels to hardware and facilities.

Anchor: ECSS-Q-ST-70-50C, the clause on applying cleanliness limits and levels.
Paraphrased into an implementable procedure; no standard text is reproduced.

Model implemented here
----------------------
A product cleanliness level is not a single count. It is a curve over particle
size, whose label is the largest size the level admits at all. The allowable
cumulative count per reference area at a size x under level L follows

    log10(N_allowed) = slope * ( (log10 L)^2 - (log10 x)^2 )

so the allowance falls away steeply as the size approaches the level label and
reaches zero at x = L. Grading a size-resolved count against a level therefore
means grading every counted size channel, and assigning a level to a measured
distribution means finding the smallest level whose curve lies above every
counted point at once.

A facility class follows the same shape over airborne concentration:

    C_allowed(x) = 10^class * (reference_size / x) ^ exponent

per cubic metre. Both curves are evaluated here with their coefficients as
named parameters, so a programme that states different ones is graded against
what it stated rather than against a built-in default.
"""

import math

__all__ = [
    "COUNT_TOLERANCE",
    "DEFAULT_SLOPE",
    "DEFAULT_REFERENCE_AREA_M2",
    "DEFAULT_CLASS_REFERENCE_SIZE_UM",
    "DEFAULT_CLASS_EXPONENT",
    "require_real",
    "validate_level",
    "validate_size_um",
    "allowable_count_per_reference_area",
    "allowable_count_for_area",
    "required_level_for_point",
    "envelope_level",
    "grade_point",
    "grade_distribution",
    "airborne_limit_per_m3",
    "grade_facility_class",
    "assess_limit_application",
]

# Allowances are exponentials of quadratics in log10; an exact equality can
# land a few ULPs on either side. Absorb that here, never by raising a limit.
COUNT_TOLERANCE = 1e-9

DEFAULT_SLOPE = 0.926
DEFAULT_REFERENCE_AREA_M2 = 0.1
DEFAULT_CLASS_REFERENCE_SIZE_UM = 0.1
DEFAULT_CLASS_EXPONENT = 2.08

# A level label below this cannot carry a curve: log10 of the label would be
# non-positive and the allowance would invert.
MIN_LEVEL_UM = 1.0


def require_real(value, label, positive=False, non_negative=False):
    """Return value as a float, rejecting booleans, strings and non-finites."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive and result <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, result))
    if non_negative and result < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, result))
    return result


def validate_level(level_um):
    """Return the validated cleanliness level label in micrometres."""
    level = require_real(level_um, "level_um", positive=True)
    if level <= MIN_LEVEL_UM:
        raise ValueError(
            "level_um must exceed %g um to carry a curve, got %g" % (MIN_LEVEL_UM, level)
        )
    return level


def validate_size_um(size_um):
    """Return the validated particle size channel in micrometres."""
    return require_real(size_um, "size_um", positive=True)


def allowable_count_per_reference_area(level_um, size_um, slope=DEFAULT_SLOPE):
    """Return the allowable cumulative count at a size, per reference area."""
    level = validate_level(level_um)
    size = validate_size_um(size_um)
    k = require_real(slope, "slope", positive=True)
    if size > level:
        # The level label is the largest size it admits at all.
        return 0.0
    exponent = k * (math.log10(level) ** 2 - math.log10(size) ** 2)
    return math.pow(10.0, exponent)


def allowable_count_for_area(level_um, size_um, area_m2,
                             slope=DEFAULT_SLOPE,
                             reference_area_m2=DEFAULT_REFERENCE_AREA_M2):
    """Scale the reference-area allowance onto the area actually inspected."""
    area = require_real(area_m2, "area_m2", positive=True)
    reference = require_real(reference_area_m2, "reference_area_m2", positive=True)
    per_reference = allowable_count_per_reference_area(level_um, size_um, slope)
    return per_reference * (area / reference)


def required_level_for_point(count, size_um, area_m2,
                             slope=DEFAULT_SLOPE,
                             reference_area_m2=DEFAULT_REFERENCE_AREA_M2):
    """Return the smallest level label whose curve admits this counted point."""
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError("count must be an integer, got %r" % (count,))
    if count < 0:
        raise ValueError("count must be non-negative, got %d" % count)
    size = validate_size_um(size_um)
    area = require_real(area_m2, "area_m2", positive=True)
    reference = require_real(reference_area_m2, "reference_area_m2", positive=True)
    k = require_real(slope, "slope", positive=True)
    if count == 0:
        # Zero counted at this size demands nothing of the level; the size
        # itself is still the floor, since a level below it admits no particle.
        return size
    per_reference = count * (reference / area)
    inner = math.log10(per_reference) / k + math.log10(size) ** 2
    if inner < 0.0:
        # The count is so far under the curve that the size channel alone
        # drives the level.
        return size
    return math.pow(10.0, math.sqrt(inner))


def envelope_level(observations, area_m2,
                   slope=DEFAULT_SLOPE,
                   reference_area_m2=DEFAULT_REFERENCE_AREA_M2):
    """Return the smallest level enveloping every counted point, and its driver."""
    points = _validate_observations(observations)
    best_level = None
    driver = None
    for size, count in points:
        needed = required_level_for_point(count, size, area_m2, slope, reference_area_m2)
        if best_level is None or needed > best_level:
            best_level = needed
            driver = size
    return {"required_level_um": best_level, "driving_size_um": driver}


def _validate_observations(observations):
    """Return observations as a list of (size_um, count) pairs, sizes ascending."""
    if not isinstance(observations, (list, tuple)) or not observations:
        raise ValueError("observations must be a non-empty sequence of (size, count)")
    points = []
    for index, item in enumerate(observations):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("observations[%d] must be a (size_um, count) pair" % index)
        size = validate_size_um(item[0])
        count = item[1]
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError("observations[%d] count must be an integer" % index)
        if count < 0:
            raise ValueError("observations[%d] count must be non-negative" % index)
        points.append((size, count))
    points.sort(key=lambda pair: pair[0])
    for i in range(1, len(points)):
        if math.isclose(points[i][0], points[i - 1][0], rel_tol=1e-12, abs_tol=0.0):
            raise ValueError("observations repeat the size channel %g um" % points[i][0])
    # A cumulative distribution cannot rise with size.
    for i in range(1, len(points)):
        if points[i][1] > points[i - 1][1]:
            raise ValueError(
                "cumulative counts must not increase with size: %d at %g um after "
                "%d at %g um" % (points[i][1], points[i][0], points[i - 1][1],
                                 points[i - 1][0])
            )
    return points


def grade_point(count, size_um, level_um, area_m2,
                slope=DEFAULT_SLOPE,
                reference_area_m2=DEFAULT_REFERENCE_AREA_M2):
    """Grade one counted size channel against an assigned level."""
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError("count must be an integer, got %r" % (count,))
    if count < 0:
        raise ValueError("count must be non-negative, got %d" % count)
    allowed = allowable_count_for_area(
        level_um, size_um, area_m2, slope, reference_area_m2
    )
    conforming = count <= allowed or math.isclose(
        float(count), allowed, rel_tol=COUNT_TOLERANCE, abs_tol=0.0
    )
    return {
        "size_um": validate_size_um(size_um),
        "count": count,
        "allowed": allowed,
        "conforming": conforming,
        "utilisation": (float(count) / allowed) if allowed > 0.0 else None,
    }


def grade_distribution(observations, level_um, area_m2,
                       slope=DEFAULT_SLOPE,
                       reference_area_m2=DEFAULT_REFERENCE_AREA_M2):
    """Grade a whole size-resolved distribution against an assigned level."""
    points = _validate_observations(observations)
    level = validate_level(level_um)
    graded = [
        grade_point(count, size, level, area_m2, slope, reference_area_m2)
        for size, count in points
    ]
    failures = [g for g in graded if not g["conforming"]]
    worst = None
    for entry in graded:
        if entry["utilisation"] is None:
            worst = entry
            break
        if worst is None or (worst["utilisation"] is not None
                             and entry["utilisation"] > worst["utilisation"]):
            worst = entry
    return {
        "assigned_level_um": level,
        "points": graded,
        "conforming": not failures,
        "failing_sizes_um": [g["size_um"] for g in failures],
        "driving_point": worst,
    }


def airborne_limit_per_m3(iso_class, size_um,
                          reference_size_um=DEFAULT_CLASS_REFERENCE_SIZE_UM,
                          exponent=DEFAULT_CLASS_EXPONENT):
    """Return the allowable airborne concentration per cubic metre for a class."""
    klass = require_real(iso_class, "iso_class", positive=True)
    size = validate_size_um(size_um)
    reference = require_real(reference_size_um, "reference_size_um", positive=True)
    power = require_real(exponent, "exponent", positive=True)
    return math.pow(10.0, klass) * math.pow(reference / size, power)


def grade_facility_class(measurements, iso_class,
                         reference_size_um=DEFAULT_CLASS_REFERENCE_SIZE_UM,
                         exponent=DEFAULT_CLASS_EXPONENT):
    """Grade airborne concentrations per size against a facility class."""
    if not isinstance(measurements, (list, tuple)) or not measurements:
        raise ValueError("measurements must be a non-empty sequence of (size, conc)")
    graded = []
    for index, item in enumerate(measurements):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError(
                "measurements[%d] must be a (size_um, concentration_per_m3) pair" % index
            )
        size = validate_size_um(item[0])
        concentration = require_real(
            item[1], "measurements[%d] concentration" % index, non_negative=True
        )
        allowed = airborne_limit_per_m3(iso_class, size, reference_size_um, exponent)
        conforming = concentration <= allowed or math.isclose(
            concentration, allowed, rel_tol=COUNT_TOLERANCE, abs_tol=0.0
        )
        graded.append({
            "size_um": size,
            "concentration_per_m3": concentration,
            "allowed_per_m3": allowed,
            "conforming": conforming,
        })
    return {
        "iso_class": require_real(iso_class, "iso_class", positive=True),
        "points": graded,
        "conforming": all(g["conforming"] for g in graded),
    }


def assess_limit_application(spec):
    """Apply the programme's cleanliness limits to a monitoring result.

    spec keys: observations (size, cumulative count pairs), area_m2, optional
    assigned_level_um, optional facility (measurements + iso_class), optional
    slope and reference_area_m2.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("observations", "area_m2"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    slope = require_real(spec.get("slope", DEFAULT_SLOPE), "slope", positive=True)
    reference = require_real(
        spec.get("reference_area_m2", DEFAULT_REFERENCE_AREA_M2),
        "reference_area_m2",
        positive=True,
    )
    envelope = envelope_level(spec["observations"], spec["area_m2"], slope, reference)
    findings = []
    surface = None
    assigned = spec.get("assigned_level_um")
    if assigned is not None:
        surface = grade_distribution(
            spec["observations"], assigned, spec["area_m2"], slope, reference
        )
        if not surface["conforming"]:
            findings.append(
                "assigned level %g um is exceeded at size channels %s"
                % (surface["assigned_level_um"],
                   ", ".join("%g um" % s for s in surface["failing_sizes_um"]))
            )
    facility = None
    facility_spec = spec.get("facility")
    if facility_spec is not None:
        if not isinstance(facility_spec, dict):
            raise ValueError("spec['facility'] must be a mapping")
        for key in ("measurements", "iso_class"):
            if key not in facility_spec:
                raise ValueError("facility missing required key '%s'" % key)
        facility = grade_facility_class(
            facility_spec["measurements"],
            facility_spec["iso_class"],
            facility_spec.get("reference_size_um", DEFAULT_CLASS_REFERENCE_SIZE_UM),
            facility_spec.get("exponent", DEFAULT_CLASS_EXPONENT),
        )
        if not facility["conforming"]:
            findings.append(
                "airborne concentration exceeds the class %g curve"
                % facility["iso_class"]
            )
    return {
        "envelope": envelope,
        "surface": surface,
        "facility": facility,
        "findings": findings,
        "compliant": not findings,
    }
