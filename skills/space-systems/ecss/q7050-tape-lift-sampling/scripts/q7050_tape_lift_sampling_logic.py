"""Tape-lift surface sampling: method, analysis and counting.

Anchor: ECSS-Q-ST-70-50C surface clause -- recovering particles already
resident on a hardware surface with an adhesive tape lift, counting them
under magnification and reading the surface against its stated cleanliness
level. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the lift: sampled area, recovery efficiency and the counted size
   bands, which are counts in a band of a size distribution.
2. Subtract a blank lift taken from a clean reference coupon, so the tape's
   own inclusions and the counting background leave the result.
3. Correct the counts for the recovery efficiency of the tape on that finish,
   because a lift removes a fraction of what is there and reporting the raw
   count understates the surface.
4. Accumulate the size bands from the largest downwards into a cumulative
   distribution, which is the form a surface cleanliness level is stated in.
5. Scale the cumulative counts from the lifted area onto the reference area
   the level is stated over, and grade every band against its allowance,
   reporting the governing band rather than an average.
"""

import math

__all__ = [
    "REFERENCE_AREA_CM2",
    "MIN_LIFT_AREA_CM2",
    "MIN_EFFICIENCY",
    "MAX_EFFICIENCY",
    "COUNT_TOLERANCE_REL",
    "validate_lift_area_cm2",
    "validate_efficiency",
    "validate_bands",
    "subtract_blank",
    "correct_for_efficiency",
    "cumulative_counts",
    "scale_to_reference_area",
    "grade_bands",
    "assess_tape_lift",
]

# Surface cleanliness levels are stated over this reference area.
REFERENCE_AREA_CM2 = 1000.0

# Below this lifted area the count turns on whether one particle happened to
# be inside the patch.
MIN_LIFT_AREA_CM2 = 10.0

# A recovery efficiency outside this band is not a tape lift result.
MIN_EFFICIENCY = 0.05
MAX_EFFICIENCY = 1.0

# Counts are scaled by ratios; absorb an equality at an allowance here.
COUNT_TOLERANCE_REL = 1e-9


def validate_lift_area_cm2(area_cm2, label="lift_area_cm2"):
    """Return the validated lifted surface area in square centimetres."""
    if not isinstance(area_cm2, (int, float)) or isinstance(area_cm2, bool):
        raise ValueError("%s must be a real number, got %r" % (label, area_cm2))
    value = float(area_cm2)
    if not math.isfinite(value):
        raise ValueError("%s must be finite" % label)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, value))
    return value


def validate_efficiency(efficiency):
    """Return the validated tape recovery efficiency as a fraction."""
    if not isinstance(efficiency, (int, float)) or isinstance(efficiency, bool):
        raise ValueError("efficiency must be a real number, got %r" % (efficiency,))
    value = float(efficiency)
    if not math.isfinite(value):
        raise ValueError("efficiency must be finite")
    if value < MIN_EFFICIENCY or value > MAX_EFFICIENCY:
        raise ValueError(
            "efficiency must lie in [%g, %g], got %g" % (MIN_EFFICIENCY, MAX_EFFICIENCY, value)
        )
    return value


def validate_bands(bands, name="bands"):
    """Return validated (size_um, count) bands, strictly increasing in size."""
    if not isinstance(bands, (list, tuple)) or not bands:
        raise ValueError("%s must be a non-empty sequence of (size_um, count) pairs" % name)
    rows = []
    for i, item in enumerate(bands):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("%s[%d] must be a (size_um, count) pair" % (name, i))
        size, count = item
        if not isinstance(size, (int, float)) or isinstance(size, bool):
            raise ValueError("%s[%d] size must be a real number" % (name, i))
        if not isinstance(count, (int, float)) or isinstance(count, bool):
            raise ValueError("%s[%d] count must be a real number" % (name, i))
        size = float(size)
        count = float(count)
        if not math.isfinite(size) or size <= 0.0:
            raise ValueError("%s[%d] size must be positive and finite" % (name, i))
        if not math.isfinite(count) or count < 0.0:
            raise ValueError("%s[%d] count must be finite and non-negative" % (name, i))
        rows.append((size, count))
    for i in range(1, len(rows)):
        if rows[i][0] <= rows[i - 1][0]:
            raise ValueError("%s sizes must strictly increase (index %d)" % (name, i))
    return rows


def subtract_blank(sample_bands, blank_bands):
    """Return the sample bands with a blank lift removed, band by band."""
    sample = validate_bands(sample_bands, "sample_bands")
    blank = validate_bands(blank_bands, "blank_bands")
    blank_by_size = {}
    for size, count in blank:
        blank_by_size[size] = count
    sample_sizes = [size for size, _ in sample]
    for size in blank_by_size:
        if not any(math.isclose(size, s, rel_tol=1e-12, abs_tol=0.0) for s in sample_sizes):
            raise ValueError(
                "blank band at %g um has no matching sample band; the two lifts were "
                "not counted on the same size bands" % size
            )
    corrected = []
    for size, count in sample:
        removed = 0.0
        for blank_size, blank_count in blank_by_size.items():
            if math.isclose(size, blank_size, rel_tol=1e-12, abs_tol=0.0):
                removed = blank_count
                break
        corrected.append((size, max(count - removed, 0.0)))
    return corrected


def correct_for_efficiency(bands, efficiency):
    """Return the bands scaled up by the tape recovery efficiency."""
    rows = validate_bands(bands)
    factor = validate_efficiency(efficiency)
    return [(size, count / factor) for size, count in rows]


def cumulative_counts(bands):
    """Return counts at or above each size, accumulated from the largest down."""
    rows = validate_bands(bands)
    running = 0.0
    result = [None] * len(rows)
    for index in range(len(rows) - 1, -1, -1):
        running += rows[index][1]
        result[index] = (rows[index][0], running)
    return result


def scale_to_reference_area(bands, lift_area_cm2, reference_area_cm2=REFERENCE_AREA_CM2):
    """Scale per-lift counts onto the reference area a level is stated over."""
    rows = validate_bands(bands)
    lifted = validate_lift_area_cm2(lift_area_cm2)
    reference = validate_lift_area_cm2(reference_area_cm2, "reference_area_cm2")
    factor = reference / lifted
    return [(size, count * factor) for size, count in rows]


def grade_bands(cumulative, allowances):
    """Grade cumulative counts per band against per-band allowances."""
    rows = validate_bands(cumulative, "cumulative")
    limits = validate_bands(allowances, "allowances")
    limit_by_size = {}
    for size, count in limits:
        limit_by_size[size] = count
    graded = []
    for size, count in rows:
        allowed = None
        for limit_size, limit_count in limit_by_size.items():
            if math.isclose(size, limit_size, rel_tol=1e-12, abs_tol=0.0):
                allowed = limit_count
                break
        if allowed is None:
            raise ValueError(
                "no allowance stated for the %g um band; the level does not cover the "
                "bands that were counted" % size
            )
        at_limit = math.isclose(count, allowed, rel_tol=COUNT_TOLERANCE_REL, abs_tol=0.0)
        graded.append(
            {
                "size_um": size,
                "count": count,
                "allowed": allowed,
                "utilisation": count / allowed if allowed > 0.0 else float("inf"),
                "compliant": at_limit or count < allowed,
            }
        )
    return graded


def assess_tape_lift(spec):
    """Run the full tape-lift analysis and grade the surface.

    spec keys: lift_area_cm2, efficiency, bands, allowances; optional
    blank_bands, reference_area_cm2, lift_count.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lift_area_cm2", "efficiency", "bands", "allowances"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    lift_area = validate_lift_area_cm2(spec["lift_area_cm2"])
    efficiency = validate_efficiency(spec["efficiency"])
    reference = validate_lift_area_cm2(
        spec.get("reference_area_cm2", REFERENCE_AREA_CM2), "reference_area_cm2"
    )
    lift_count = spec.get("lift_count", 1)
    if not isinstance(lift_count, int) or isinstance(lift_count, bool) or lift_count < 1:
        raise ValueError("lift_count must be an integer of at least 1, got %r" % (lift_count,))

    findings = []
    bands = validate_bands(spec["bands"])
    blank_bands = spec.get("blank_bands")
    if blank_bands is None:
        findings.append(
            "no blank lift reported; the tape's own inclusions and the counting "
            "background remain inside the result"
        )
    else:
        bands = subtract_blank(bands, blank_bands)

    corrected = correct_for_efficiency(bands, efficiency)
    cumulative = cumulative_counts(corrected)
    total_area = lift_area * lift_count
    scaled = scale_to_reference_area(cumulative, total_area, reference)
    graded = grade_bands(scaled, spec["allowances"])

    if total_area < MIN_LIFT_AREA_CM2:
        findings.append(
            "total lifted area %g cm2 is below the %g cm2 minimum; the count turns on "
            "whether one particle fell inside the patch" % (total_area, MIN_LIFT_AREA_CM2)
        )
    if efficiency < 0.5:
        findings.append(
            "recovery efficiency %g means over half the resident particles stayed on "
            "the surface; the correction is doing more work than the measurement"
            % efficiency
        )

    failed = [g for g in graded if not g["compliant"]]
    if failed:
        findings.append(
            "band(s) over the stated level: %s"
            % ", ".join("%g um" % g["size_um"] for g in failed)
        )

    governing = graded[0]
    for entry in graded[1:]:
        if entry["utilisation"] > governing["utilisation"]:
            governing = entry

    return {
        "lift_area_cm2": lift_area,
        "lift_count": lift_count,
        "total_area_cm2": total_area,
        "efficiency": efficiency,
        "reference_area_cm2": reference,
        "net_bands": bands,
        "corrected_bands": corrected,
        "cumulative_per_reference_area": scaled,
        "graded": graded,
        "governing_band": governing,
        "compliant": not failed,
        "findings": findings,
    }
