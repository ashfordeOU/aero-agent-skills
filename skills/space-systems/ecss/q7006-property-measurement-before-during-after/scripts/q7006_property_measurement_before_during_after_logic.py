"""Particle and UV radiation testing: the property-measurement schedule.

Anchor: ECSS-Q-ST-70-06C, the measurement clause of particle and UV
radiation testing for space materials (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. A radiation exposure is only useful if the property of interest was
   measured against the exposure axis, not once at the end. The schedule
   names the points -- a pristine baseline before any exposure,
   intermediate points while the fluence or the UV dose accumulates, and
   a final point at the planned total.
2. A baseline is not optional. Degradation is a difference, and without
   a pre-exposure value every later number is an absolute reading that
   no design can use.
3. The intermediate points carry the shape of the degradation curve. One
   point in the middle distinguishes a saturating curve from a linear
   one; none leaves the two indistinguishable, and a long stretch of the
   exposure axis with no point in it hides whatever happened there.
4. Each property family is measured with enough replicates to separate a
   real change from specimen scatter, and the change the run is looking
   for has to be larger than the measurement uncertainty that will be
   quoted against it. A property whose expected change sits inside its
   own uncertainty band is being measured with the wrong instrument.
5. The plan is executable only when the point set, the property coverage,
   the replicate counts and the resolvability all hold together.

Stdlib only, offline, deterministic.
"""

# Property families a radiation exposure is normally read out on, with
# the direction in which a change is a degradation and the replicate
# floor that separates a change from specimen scatter.
PROPERTY_FAMILIES = {
    "solar-absorptance": {
        "kind": "thermo-optical",
        "direction": "increase-is-degradation",
        "min_replicates": 3,
    },
    "infrared-emittance": {
        "kind": "thermo-optical",
        "direction": "decrease-is-degradation",
        "min_replicates": 3,
    },
    "optical-transmittance": {
        "kind": "optical",
        "direction": "decrease-is-degradation",
        "min_replicates": 3,
    },
    "tensile-strength": {
        "kind": "mechanical",
        "direction": "decrease-is-degradation",
        "min_replicates": 5,
    },
    "elongation-at-break": {
        "kind": "mechanical",
        "direction": "decrease-is-degradation",
        "min_replicates": 5,
    },
}

BASELINE_FRACTION = 0.0
FINAL_FRACTION = 1.0

# The exposure axis is undersampled when two consecutive points are
# further apart than this fraction of the planned total exposure.
MAX_DOSE_GAP = 0.5

# A change is resolvable when it is at least this multiple of the
# expanded uncertainty quoted against the value.
RESOLUTION_FACTOR = 2.0

MIN_INTERMEDIATE_POINTS = 1

# Dose fractions and uncertainty ratios are built from decimal literals,
# so a value sitting exactly on a bound can land a few units in the last
# place past it. This tolerance absorbs that representation error only;
# no bound is ever relaxed.
FRACTION_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None, maximum=None):
    """Return value as a float, raising on anything that is not a number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    val = float(value)
    if minimum is not None and val < minimum - FRACTION_TOLERANCE:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    if maximum is not None and val > maximum + FRACTION_TOLERANCE:
        raise ValueError("%s must be <= %r, got %r" % (label, maximum, value))
    return val


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def known_property(name):
    """True when a property name is one the measurement schedule knows."""
    return _text("property", name) in PROPERTY_FAMILIES


def property_direction(name):
    """The direction in which a change in this property is a degradation."""
    key = _text("property", name)
    if key not in PROPERTY_FAMILIES:
        raise ValueError("unknown property family %r" % (key,))
    return PROPERTY_FAMILIES[key]["direction"]


def validate_point(point):
    """Normalize one measurement point, raising on a malformed record."""
    if not isinstance(point, dict):
        raise ValueError("each measurement point must be a mapping")
    label = _text("point label", point.get("label"))
    fraction = _numeric("dose_fraction", point.get("dose_fraction"), 0.0, 1.0)
    properties = point.get("properties")
    if not isinstance(properties, (list, tuple)) or not properties:
        raise ValueError("point %s must measure at least one property" % label)
    names = []
    for name in properties:
        key = _text("property", name)
        if key not in PROPERTY_FAMILIES:
            raise ValueError("unknown property family %r" % (key,))
        if key in names:
            raise ValueError("property %r repeated at point %s" % (key, label))
        names.append(key)
    replicates = point.get("replicates")
    if not isinstance(replicates, int) or isinstance(replicates, bool):
        raise ValueError("point %s replicates must be a whole number" % label)
    if replicates < 1:
        raise ValueError("point %s must have at least one replicate" % label)
    return {
        "label": label,
        "dose_fraction": fraction,
        "properties": names,
        "replicates": replicates,
    }


def normalize_schedule(points):
    """Validate and order a measurement schedule by accumulated exposure."""
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("schedule must be a non-empty sequence of points")
    normalized = [validate_point(p) for p in points]
    normalized.sort(key=lambda p: p["dose_fraction"])
    for earlier, later in zip(normalized, normalized[1:]):
        if abs(later["dose_fraction"] - earlier["dose_fraction"]) <= FRACTION_TOLERANCE:
            raise ValueError(
                "two measurement points share dose fraction %r"
                % (earlier["dose_fraction"],)
            )
    return normalized


def point_at(points, fraction):
    """The normalized point sitting at one dose fraction, or None."""
    target = _numeric("fraction", fraction, 0.0, 1.0)
    for point in points:
        if abs(point["dose_fraction"] - target) <= FRACTION_TOLERANCE:
            return point
    return None


def intermediate_points(points):
    """Points strictly between the baseline and the final exposure."""
    return [
        p for p in points
        if p["dose_fraction"] > BASELINE_FRACTION + FRACTION_TOLERANCE
        and p["dose_fraction"] < FINAL_FRACTION - FRACTION_TOLERANCE
    ]


def largest_dose_gap(points):
    """Widest stretch of the exposure axis with no measurement point in it."""
    if len(points) < 2:
        raise ValueError("a gap needs at least two measurement points")
    return max(
        later["dose_fraction"] - earlier["dose_fraction"]
        for earlier, later in zip(points, points[1:])
    )


def properties_missing_at(points, fraction, families):
    """Requested property families not measured at one dose fraction."""
    wanted = [_text("property", f) for f in families]
    point = point_at(points, fraction)
    if point is None:
        return sorted(set(wanted))
    return sorted(set(wanted) - set(point["properties"]))


def replicate_shortfalls(points):
    """Points whose replicate count sits under the floor of a family on it."""
    shortfalls = []
    for point in points:
        needed = max(
            PROPERTY_FAMILIES[name]["min_replicates"] for name in point["properties"]
        )
        if point["replicates"] < needed:
            shortfalls.append((point["label"], point["replicates"], needed))
    return shortfalls


def change_resolvable(expected_change, expanded_uncertainty):
    """True when an expected change stands clear of its own uncertainty."""
    change = abs(_numeric("expected_change", expected_change))
    unc = _numeric("expanded_uncertainty", expanded_uncertainty, 0.0)
    if unc == 0.0:
        return change > 0.0
    return change + FRACTION_TOLERANCE >= RESOLUTION_FACTOR * unc


def assess_measurement_plan(plan):
    """Assess one property-measurement schedule for a radiation exposure."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")

    families = plan.get("property_families")
    if not isinstance(families, (list, tuple)) or not families:
        raise ValueError("plan must name at least one property family")
    wanted = []
    for name in families:
        key = _text("property", name)
        if key not in PROPERTY_FAMILIES:
            raise ValueError("unknown property family %r" % (key,))
        if key not in wanted:
            wanted.append(key)

    points = normalize_schedule(plan.get("points"))
    findings = []

    if point_at(points, BASELINE_FRACTION) is None:
        findings.append("no-pristine-baseline-measurement")
    if point_at(points, FINAL_FRACTION) is None:
        findings.append("no-measurement-at-the-planned-total-exposure")

    if len(intermediate_points(points)) < MIN_INTERMEDIATE_POINTS:
        findings.append("no-intermediate-measurement-point")

    missing_baseline = properties_missing_at(points, BASELINE_FRACTION, wanted)
    missing_final = properties_missing_at(points, FINAL_FRACTION, wanted)
    if missing_baseline:
        findings.append("property-without-a-pre-exposure-value")
    if missing_final:
        findings.append("property-without-a-post-exposure-value")

    gap = largest_dose_gap(points) if len(points) >= 2 else None
    if gap is not None and gap > MAX_DOSE_GAP + FRACTION_TOLERANCE:
        findings.append("exposure-axis-undersampled")

    shortfalls = replicate_shortfalls(points)
    if shortfalls:
        findings.append("replicate-count-under-the-family-floor")

    unresolvable = []
    budget = plan.get("expected_change", {})
    uncertainty = plan.get("expanded_uncertainty", {})
    if not isinstance(budget, dict) or not isinstance(uncertainty, dict):
        raise ValueError("expected_change and expanded_uncertainty must be mappings")
    for name in wanted:
        if name in budget and name in uncertainty:
            if not change_resolvable(budget[name], uncertainty[name]):
                unresolvable.append(name)
        else:
            findings.append("resolvability-not-demonstrated")
            break
    if unresolvable:
        findings.append("expected-change-inside-the-measurement-uncertainty")

    return {
        "plan_id": plan.get("plan_id"),
        "property_families": wanted,
        "point_labels": [p["label"] for p in points],
        "dose_fractions": [p["dose_fraction"] for p in points],
        "intermediate_point_count": len(intermediate_points(points)),
        "largest_dose_gap": gap,
        "missing_at_baseline": missing_baseline,
        "missing_at_final": missing_final,
        "replicate_shortfalls": shortfalls,
        "unresolvable_properties": sorted(unresolvable),
        "findings": findings,
        "executable": not findings,
    }
