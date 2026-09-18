"""Cross-cut and tape adhesion verification for an applied paint system.

Anchor: ECSS-Q-ST-70-31C, Quality, using the pressure-sensitive tape method of
ECSS-Q-ST-70-13C. Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Choose the cross-cut spacing from the dry film thickness and the substrate
   hardness, and refuse a film too thick for the lattice method instead of
   cutting it anyway.
2. Derive the number of lattice squares from the cut count, so the detached
   area is a fraction of a known denominator.
3. Convert fully and partly detached squares into a detached-area percentage,
   counting a partial square by its own detached fraction rather than as a
   whole one.
4. Band the percentage into the six-step cross-cut rating, with the band
   edges inclusive of the tighter side.
5. Grade a set of test areas: every area against the worst rating allowed, a
   minimum number of areas, and the spread between areas, since a scattered
   result is a process finding even when the worst area passes.
6. Where a pull-off strength is also reported, test it against its minimum
   and fold the result into the same verdict.
"""

import math

__all__ = [
    "RATING_TOLERANCE",
    "CROSSCUT_BAND_EDGES",
    "MAX_LATTICE_DFT_UM",
    "DEFAULT_CUTS_PER_DIRECTION",
    "validate_positive",
    "cut_spacing_mm",
    "lattice_square_count",
    "detached_area_percent",
    "crosscut_rating",
    "assess_test_area",
    "pull_off_verdict",
    "assess_adhesion",
]

# A square count over a lattice lands exactly on a band edge. Absorb the
# representation error here, never by moving the band.
RATING_TOLERANCE = 1e-9

# Upper detached-area percentage of ratings 0 through 4; above the last edge
# the result is rating 5.
CROSSCUT_BAND_EDGES = (0.0, 5.0, 15.0, 35.0, 65.0)

# Above this dry film thickness the lattice method stops being meaningful.
MAX_LATTICE_DFT_UM = 250.0

DEFAULT_CUTS_PER_DIRECTION = 6


def _real(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def validate_positive(value, label):
    """Return a validated strictly positive float."""
    out = _real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def cut_spacing_mm(dft_um, substrate="hard"):
    """Return the cross-cut spacing in millimetres for this film and substrate."""
    thickness = validate_positive(dft_um, "dft_um")
    if not isinstance(substrate, str):
        raise ValueError("substrate must be a string, got %r" % (substrate,))
    kind = substrate.strip().lower()
    if kind not in ("hard", "soft"):
        raise ValueError("substrate must be 'hard' or 'soft', got '%s'" % substrate)
    if thickness > MAX_LATTICE_DFT_UM + RATING_TOLERANCE:
        raise ValueError(
            "dry film thickness %g um exceeds the %g um lattice limit; use a pull-off "
            "method instead" % (thickness, MAX_LATTICE_DFT_UM)
        )
    if thickness <= 60.0 + RATING_TOLERANCE:
        return 1.0 if kind == "hard" else 2.0
    if thickness <= 120.0 + RATING_TOLERANCE:
        return 2.0
    return 3.0


def lattice_square_count(cuts_per_direction=DEFAULT_CUTS_PER_DIRECTION):
    """Return the number of squares a lattice of that many cuts produces."""
    if isinstance(cuts_per_direction, bool) or not isinstance(cuts_per_direction, int):
        raise ValueError("cuts_per_direction must be an integer, got %r" % (cuts_per_direction,))
    if cuts_per_direction < 2:
        raise ValueError(
            "cuts_per_direction must be at least two to bound a square, got %d"
            % cuts_per_direction
        )
    return (cuts_per_direction - 1) ** 2


def detached_area_percent(detached_squares, total_squares, partial_fractions=None):
    """Return the detached area as a percentage of the lattice."""
    if isinstance(detached_squares, bool) or not isinstance(detached_squares, int):
        raise ValueError("detached_squares must be an integer, got %r" % (detached_squares,))
    if isinstance(total_squares, bool) or not isinstance(total_squares, int):
        raise ValueError("total_squares must be an integer, got %r" % (total_squares,))
    if total_squares < 1:
        raise ValueError("total_squares must be at least one, got %d" % total_squares)
    if detached_squares < 0:
        raise ValueError("detached_squares must be non-negative, got %d" % detached_squares)
    fractions = list(partial_fractions or [])
    for i, raw in enumerate(fractions):
        value = _real(raw, "partial_fractions[%d]" % i)
        if value <= 0.0 or value >= 1.0:
            raise ValueError(
                "partial_fractions[%d] must lie strictly in (0, 1); a whole square is "
                "counted in detached_squares" % i
            )
        fractions[i] = value
    if detached_squares + len(fractions) > total_squares:
        raise ValueError(
            "more affected squares (%d) than the lattice holds (%d)"
            % (detached_squares + len(fractions), total_squares)
        )
    affected = detached_squares + sum(fractions)
    return 100.0 * affected / total_squares


def crosscut_rating(percent_detached):
    """Return the six-step cross-cut rating for a detached-area percentage."""
    value = _real(percent_detached, "percent_detached")
    if value < 0.0 or value > 100.0:
        raise ValueError("percent_detached must lie in [0, 100], got %g" % value)
    for rating, edge in enumerate(CROSSCUT_BAND_EDGES):
        if value <= edge + RATING_TOLERANCE:
            return rating
    return len(CROSSCUT_BAND_EDGES)


def assess_test_area(area, max_rating):
    """Grade one cross-cut test area against the worst rating allowed."""
    if not isinstance(area, dict):
        raise ValueError("test area must be a mapping")
    for key in ("name", "dft_um", "detached_squares"):
        if key not in area:
            raise ValueError("test area missing required key '%s'" % key)
    if isinstance(max_rating, bool) or not isinstance(max_rating, int):
        raise ValueError("max_rating must be an integer, got %r" % (max_rating,))
    if max_rating < 0 or max_rating > len(CROSSCUT_BAND_EDGES):
        raise ValueError(
            "max_rating must lie in [0, %d], got %d" % (len(CROSSCUT_BAND_EDGES), max_rating)
        )
    spacing = cut_spacing_mm(area["dft_um"], area.get("substrate", "hard"))
    cuts = area.get("cuts_per_direction", DEFAULT_CUTS_PER_DIRECTION)
    total = lattice_square_count(cuts)
    percent = detached_area_percent(
        area["detached_squares"], total, area.get("partial_fractions")
    )
    rating = crosscut_rating(percent)
    passed = rating <= max_rating
    findings = []
    if not passed:
        findings.append(
            "%s: cross-cut rating %d exceeds the worst rating %d allowed"
            % (str(area["name"]), rating, max_rating)
        )
    return {
        "name": str(area["name"]),
        "cut_spacing_mm": spacing,
        "lattice_squares": total,
        "percent_detached": percent,
        "rating": rating,
        "passed": passed,
        "findings": findings,
    }


def pull_off_verdict(strength_mpa, min_strength_mpa):
    """Return the pull-off record for a reported adhesion strength."""
    strength = _real(strength_mpa, "strength_mpa")
    if strength < 0.0:
        raise ValueError("strength_mpa must be non-negative, got %g" % strength)
    minimum = validate_positive(min_strength_mpa, "min_strength_mpa")
    met = strength >= minimum - RATING_TOLERANCE
    return {
        "strength_mpa": strength,
        "min_strength_mpa": minimum,
        "met": met,
        "findings": []
        if met
        else ["pull-off strength %.3f MPa is below the required %.3f MPa" % (strength, minimum)],
    }


def assess_adhesion(spec):
    """Run the full cross-cut and tape adhesion assessment.

    spec keys: test_areas, max_rating; optional min_test_areas,
    max_rating_spread, pull_off_strength_mpa and min_pull_off_mpa.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("test_areas", "max_rating"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    areas = spec["test_areas"]
    if not isinstance(areas, (list, tuple)) or not areas:
        raise ValueError("spec['test_areas'] must be a non-empty sequence")
    records = [assess_test_area(area, spec["max_rating"]) for area in areas]
    findings = [text for record in records for text in record["findings"]]

    min_areas = spec.get("min_test_areas", 1)
    if isinstance(min_areas, bool) or not isinstance(min_areas, int) or min_areas < 1:
        raise ValueError("min_test_areas must be an integer of at least one")
    coverage_met = len(records) >= min_areas
    if not coverage_met:
        findings.append(
            "%d test area(s) recorded against a required minimum of %d"
            % (len(records), min_areas)
        )

    ratings = [record["rating"] for record in records]
    spread = max(ratings) - min(ratings)
    spread_ok = True
    max_spread = spec.get("max_rating_spread")
    if max_spread is not None:
        if isinstance(max_spread, bool) or not isinstance(max_spread, int) or max_spread < 0:
            raise ValueError("max_rating_spread must be a non-negative integer")
        spread_ok = spread <= max_spread
        if not spread_ok:
            findings.append(
                "cross-cut ratings span %d steps across the test areas, over the %d allowed"
                % (spread, max_spread)
            )

    pull_off = None
    if "pull_off_strength_mpa" in spec:
        if "min_pull_off_mpa" not in spec:
            raise ValueError(
                "a reported pull-off strength needs 'min_pull_off_mpa' to be graded"
            )
        pull_off = pull_off_verdict(
            spec["pull_off_strength_mpa"], spec["min_pull_off_mpa"]
        )
        findings.extend(pull_off["findings"])

    return {
        "test_areas": records,
        "worst_rating": max(ratings),
        "rating_spread": spread,
        "coverage_met": coverage_met,
        "spread_within_limit": spread_ok,
        "pull_off": pull_off,
        "findings": findings,
        "adhesion_verified": not findings,
    }
