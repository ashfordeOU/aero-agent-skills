"""Matching solar simulator output to the air mass zero reference spectrum.

Anchor: ECSS-E-ST-20-08C clause 10.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A solar simulator is not accepted because its lamp is bright. It is
accepted when the SHAPE of what it emits follows the air mass zero
reference across the wavelengths the article under test responds in, at
the right total level, over a band set that actually spans the reference.
Three arms, and each has its own way of going quietly green.

    distribution    the shape arm. Each band's share of the total is
                    compared with the same band's share of the reference,
                    and the ratio of the two shares is the spectral match
                    in that band. The grade is the WORST band, never an
                    average: a simulator that matches in five bands and
                    misses in the sixth is a simulator that misses, and
                    averaging the six hides exactly the band a narrow
                    response would have been measured in
    level           a shape check is scale-free by construction. Dividing
                    each band by the total cancels the total, so a
                    simulator can match the reference distribution
                    perfectly at half the irradiance and the shape arm
                    will not notice. The integrated total is therefore
                    taken against the declared target separately
    coverage        the band set is an input, and a band set that spans
                    only the easy part of the reference makes both other
                    arms easy. So the reference irradiance the band set
                    encloses is taken against the reference irradiance
                    over its whole measured range

Shares, not raw irradiances, are what the distribution arm compares: the
reference curve and the simulator measurement rarely arrive in the same
units or at the same working distance, and normalising each to its own
band-set total is what makes the two comparable without pretending the
calibration is shared.

Integration is trapezoidal with the band edges interpolated onto the
measured curve, so a band boundary that falls between two measured
wavelengths is honoured rather than snapped to the nearest sample.

Standard library only, offline, deterministic. Every quantity is formed
with addition, multiplication and division alone -- no power and no
logarithm -- so the same inputs round the same way on every platform.
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_MATCH_GRADE_LIMITS",
    "MATCH_TOLERANCE",
    "OUTSIDE_MATCH_BANDS",
    "SIMULATOR_ACCEPTED",
    "SIMULATOR_REJECTED",
    "SPECTRAL_MATCH_GRADES",
    "band_fractions",
    "evaluate_spectral_distribution",
    "grade_rank",
    "grade_ratio",
    "integrate_band",
    "integrate_spectrum",
    "spectral_irradiance_at",
    "spectral_match_ratios",
    "validate_bands",
    "validate_match_grade_limits",
    "validate_spectrum",
    "worst_grade",
]

# Best first.
SPECTRAL_MATCH_GRADES = (
    "spectral-match-a",
    "spectral-match-b",
    "spectral-match-c",
)

OUTSIDE_MATCH_BANDS = "outside-every-spectral-match-grade"

# Working convention for this pack, not standard text: each grade is a
# widening band around unity that the per-band share ratio has to sit
# inside. A project with its own acceptance table passes it through the
# spec; the table is validated for nesting either way.
DEFAULT_MATCH_GRADE_LIMITS = {
    "spectral-match-a": (0.75, 1.25),
    "spectral-match-b": (0.6, 1.4),
    "spectral-match-c": (0.4, 2.0),
}

SIMULATOR_ACCEPTED = "simulator-spectrum-accepted"
SIMULATOR_REJECTED = "simulator-spectrum-rejected"

# Band edges, grade limits and integrated shares are all decimal literals
# meeting float arithmetic. A ratio that should sit exactly on a grade
# limit must not pass on one platform and fail on another, so every
# comparison absorbs representation error at a named, relative tolerance.
MATCH_TOLERANCE = 1e-9


def _identifier(value, label):
    """Return a trimmed non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _number(value, label):
    """Return a finite float, refusing a bool, a string or a non-number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _tolerance(*bounds):
    """Return the absolute tolerance to use around the given bounds."""
    span = 1.0
    for bound in bounds:
        span = max(span, abs(bound))
    return MATCH_TOLERANCE * span


def _within(value, low, high):
    """Return True when value sits inside the closed band, limits included."""
    tol = _tolerance(low, high)
    return (value >= low - tol) and (value <= high + tol)


def validate_spectrum(points, label="spectrum"):
    """Return a validated spectral irradiance curve.

    Wavelengths rise strictly: a repeated wavelength is a vertical step
    the trapezoid cannot integrate and an out-of-order pair is a curve
    nobody can interpolate on. Irradiance is never negative.
    """
    if not isinstance(points, (list, tuple)) or len(points) < 2:
        raise ValueError("%s must carry at least two sample points" % label)
    out = []
    previous = None
    for index, point in enumerate(points):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError(
                "%s[%d] must be a (wavelength_nm, irradiance) pair" % (label, index)
            )
        wavelength = _number(point[0], "%s[%d] wavelength_nm" % (label, index))
        irradiance = _number(point[1], "%s[%d] irradiance" % (label, index))
        if wavelength <= 0.0:
            raise ValueError(
                "%s[%d] wavelength_nm must be positive, got %r"
                % (label, index, wavelength)
            )
        if irradiance < 0.0:
            raise ValueError(
                "%s[%d] irradiance must not be negative, got %r"
                % (label, index, irradiance)
            )
        if previous is not None and wavelength <= previous:
            raise ValueError(
                "%s wavelengths must rise strictly; %r follows %r"
                % (label, wavelength, previous)
            )
        previous = wavelength
        out.append((wavelength, irradiance))
    return tuple(out)


def validate_bands(bands, label="bands"):
    """Return a validated contiguous band set.

    The bands are the frame the whole comparison hangs on. They rise, they
    do not overlap and they do not leave a gap: a gap is irradiance that
    belongs to neither share and silently leaves both totals.
    """
    if not isinstance(bands, (list, tuple)) or len(bands) < 2:
        raise ValueError("%s must carry at least two bands" % label)
    out = []
    previous_high = None
    for index, band in enumerate(bands):
        if not isinstance(band, (list, tuple)) or len(band) != 2:
            raise ValueError("%s[%d] must be a (low_nm, high_nm) pair" % (label, index))
        low = _number(band[0], "%s[%d] low_nm" % (label, index))
        high = _number(band[1], "%s[%d] high_nm" % (label, index))
        if low <= 0.0:
            raise ValueError(
                "%s[%d] low_nm must be positive, got %r" % (label, index, low)
            )
        if high <= low:
            raise ValueError(
                "%s[%d] high_nm %r must sit above low_nm %r" % (label, index, high, low)
            )
        if previous_high is not None:
            if not _within(low, previous_high, previous_high):
                raise ValueError(
                    "%s[%d] starts at %r where the previous band ended at %r; the "
                    "band set must be contiguous" % (label, index, low, previous_high)
                )
            low = previous_high
        previous_high = high
        out.append((low, high))
    return tuple(out)


def validate_match_grade_limits(limits):
    """Return a validated, nested grade limit table.

    Each grade is a band around unity and each grade must contain the one
    before it, or a ratio could sit in a worse grade while failing a
    better one and the ladder would no longer be a ladder.
    """
    if not isinstance(limits, dict):
        raise ValueError("match grade limits must be a mapping")
    out = {}
    previous = None
    for grade in SPECTRAL_MATCH_GRADES:
        if grade not in limits:
            raise ValueError("match grade limits missing grade '%s'" % grade)
        pair = limits[grade]
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("%s limits must be a (low, high) pair" % grade)
        low = _number(pair[0], "%s low limit" % grade)
        high = _number(pair[1], "%s high limit" % grade)
        if low <= 0.0:
            raise ValueError("%s low limit must be positive, got %r" % (grade, low))
        if not low < 1.0 < high:
            raise ValueError(
                "%s limits must straddle unity, got %r to %r" % (grade, low, high)
            )
        if previous is not None:
            if low > previous[0] + _tolerance(previous[0]) or high < previous[1] - _tolerance(
                previous[1]
            ):
                raise ValueError(
                    "%s limits %r to %r must contain the tighter grade %r to %r"
                    % (grade, low, high, previous[0], previous[1])
                )
        previous = (low, high)
        out[grade] = (low, high)
    return out


def spectral_irradiance_at(spectrum, wavelength, label="spectrum"):
    """Return the irradiance of a validated curve at one wavelength.

    Linear interpolation between the bracketing samples. A wavelength
    outside the measured range is refused rather than extrapolated: the
    simulator was not measured there and guessing is not a measurement.
    """
    curve = validate_spectrum(spectrum, label)
    target = _number(wavelength, "wavelength_nm")
    low_edge = curve[0][0]
    high_edge = curve[-1][0]
    if target < low_edge - _tolerance(low_edge) or target > high_edge + _tolerance(
        high_edge
    ):
        raise ValueError(
            "wavelength %r lies outside the measured range %r to %r of %s"
            % (target, low_edge, high_edge, label)
        )
    if target <= low_edge:
        return curve[0][1]
    if target >= high_edge:
        return curve[-1][1]
    for index in range(1, len(curve)):
        left_w, left_i = curve[index - 1]
        right_w, right_i = curve[index]
        if target <= right_w:
            span = right_w - left_w
            return left_i + (right_i - left_i) * (target - left_w) / span
    return curve[-1][1]


def integrate_band(spectrum, low, high, label="spectrum"):
    """Trapezoidal integral of a validated curve between two wavelengths.

    The band edges are interpolated onto the curve rather than snapped to
    the nearest sample, so a boundary falling between two measurements is
    honoured.
    """
    curve = validate_spectrum(spectrum, label)
    low = _number(low, "band low_nm")
    high = _number(high, "band high_nm")
    if high <= low:
        raise ValueError("band high_nm %r must sit above low_nm %r" % (high, low))
    nodes = [(low, spectral_irradiance_at(curve, low, label))]
    for wavelength, irradiance in curve:
        if wavelength > low + _tolerance(low) and wavelength < high - _tolerance(high):
            nodes.append((wavelength, irradiance))
    nodes.append((high, spectral_irradiance_at(curve, high, label)))
    total = 0.0
    for index in range(1, len(nodes)):
        left_w, left_i = nodes[index - 1]
        right_w, right_i = nodes[index]
        total += (right_w - left_w) * (left_i + right_i) / 2.0
    return total


def integrate_spectrum(spectrum, label="spectrum"):
    """Trapezoidal integral of a validated curve over its whole range."""
    curve = validate_spectrum(spectrum, label)
    return integrate_band(curve, curve[0][0], curve[-1][0], label)


def band_fractions(spectrum, bands, label="spectrum"):
    """Return each band's integral and its share of the band-set total.

    Shares, not raw irradiances, because the reference curve and the
    simulator measurement rarely share units or working distance.
    """
    curve = validate_spectrum(spectrum, label)
    band_set = validate_bands(bands)
    low_edge = curve[0][0]
    high_edge = curve[-1][0]
    if band_set[0][0] < low_edge - _tolerance(low_edge):
        raise ValueError(
            "band set starts at %r, below the measured range of %s which starts at %r"
            % (band_set[0][0], label, low_edge)
        )
    if band_set[-1][1] > high_edge + _tolerance(high_edge):
        raise ValueError(
            "band set ends at %r, above the measured range of %s which ends at %r"
            % (band_set[-1][1], label, high_edge)
        )
    integrals = [integrate_band(curve, low, high, label) for low, high in band_set]
    total = 0.0
    for value in integrals:
        total += value
    if total <= 0.0:
        raise ValueError(
            "%s carries no irradiance at all across the band set" % label
        )
    return {
        "bands": band_set,
        "integrals": tuple(integrals),
        "band_set_total": total,
        "fractions": tuple(value / total for value in integrals),
    }


def spectral_match_ratios(simulator_spectrum, reference_spectrum, bands):
    """Return the per-band share ratio of simulator against reference."""
    simulator = band_fractions(simulator_spectrum, bands, "simulator spectrum")
    reference = band_fractions(reference_spectrum, bands, "reference spectrum")
    ratios = []
    for index, band in enumerate(simulator["bands"]):
        reference_share = reference["fractions"][index]
        if reference_share <= 0.0:
            raise ValueError(
                "reference spectrum carries no irradiance in band %r to %r, so no "
                "share ratio exists there" % band
            )
        ratios.append(simulator["fractions"][index] / reference_share)
    return {
        "bands": simulator["bands"],
        "simulator": simulator,
        "reference": reference,
        "ratios": tuple(ratios),
    }


def grade_rank(grade):
    """Return the ladder position of a grade; lower is a better match."""
    ladder = SPECTRAL_MATCH_GRADES + (OUTSIDE_MATCH_BANDS,)
    if not isinstance(grade, str) or grade.strip().lower() not in ladder:
        raise ValueError(
            "unrecognized spectral match grade %r; recognized: %s"
            % (grade, ", ".join(ladder))
        )
    return ladder.index(grade.strip().lower())


def grade_ratio(ratio, limits=None):
    """Return the best grade one band's share ratio sits inside."""
    value = _number(ratio, "share ratio")
    table = validate_match_grade_limits(
        DEFAULT_MATCH_GRADE_LIMITS if limits is None else limits
    )
    for grade in SPECTRAL_MATCH_GRADES:
        low, high = table[grade]
        if _within(value, low, high):
            return grade
    return OUTSIDE_MATCH_BANDS


def worst_grade(grades):
    """Return the worst grade in a set; one bad band sets the whole result.

    Never an average. Averaging six bands hides the single band a narrow
    spectral response would have been measured in, which is the band that
    mattered.
    """
    if not isinstance(grades, (list, tuple)) or not grades:
        raise ValueError("grades must be a non-empty sequence")
    worst = SPECTRAL_MATCH_GRADES[0]
    for grade in grades:
        if grade_rank(grade) > grade_rank(worst):
            worst = grade.strip().lower()
    return worst


def evaluate_spectral_distribution(spec):
    """Run the clause 10.1.1 simulator spectrum check over one measurement.

    spec keys: simulator_id, simulator_spectrum, reference_spectrum,
    bands, target_total_irradiance, total_irradiance_tolerance,
    reference_coverage_floor, and optionally required_grade and
    match_grade_limits.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "simulator_id",
        "simulator_spectrum",
        "reference_spectrum",
        "bands",
        "target_total_irradiance",
        "total_irradiance_tolerance",
        "reference_coverage_floor",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    simulator_id = _identifier(spec["simulator_id"], "simulator_id")
    limits = validate_match_grade_limits(
        DEFAULT_MATCH_GRADE_LIMITS
        if spec.get("match_grade_limits") is None
        else spec["match_grade_limits"]
    )
    required_grade = spec.get("required_grade", SPECTRAL_MATCH_GRADES[0])
    if grade_rank(required_grade) >= len(SPECTRAL_MATCH_GRADES):
        raise ValueError(
            "required_grade must name a real grade, not %r" % (required_grade,)
        )
    required_grade = required_grade.strip().lower()

    target = _number(spec["target_total_irradiance"], "target_total_irradiance")
    if target <= 0.0:
        raise ValueError(
            "target_total_irradiance must be positive, got %r" % (target,)
        )
    level_tolerance = _number(
        spec["total_irradiance_tolerance"], "total_irradiance_tolerance"
    )
    if not 0.0 < level_tolerance < 1.0:
        raise ValueError(
            "total_irradiance_tolerance must be a fraction between 0 and 1, got %r"
            % (level_tolerance,)
        )
    coverage_floor = _number(
        spec["reference_coverage_floor"], "reference_coverage_floor"
    )
    if not 0.0 < coverage_floor <= 1.0:
        raise ValueError(
            "reference_coverage_floor must lie above 0 and at most 1, got %r"
            % (coverage_floor,)
        )

    matched = spectral_match_ratios(
        spec["simulator_spectrum"], spec["reference_spectrum"], spec["bands"]
    )
    band_results = []
    for index, band in enumerate(matched["bands"]):
        ratio = matched["ratios"][index]
        grade = grade_ratio(ratio, limits)
        band_results.append(
            {
                "band": band,
                "simulator_integral": matched["simulator"]["integrals"][index],
                "reference_integral": matched["reference"]["integrals"][index],
                "simulator_fraction": matched["simulator"]["fractions"][index],
                "reference_fraction": matched["reference"]["fractions"][index],
                "share_ratio": ratio,
                "grade": grade,
                "meets_required_grade": grade_rank(grade)
                <= grade_rank(required_grade),
            }
        )

    overall = worst_grade([b["grade"] for b in band_results])
    distribution_ok = grade_rank(overall) <= grade_rank(required_grade)

    delivered = matched["simulator"]["band_set_total"]
    level_deviation = (delivered - target) / target
    level_ok = _within(level_deviation, -level_tolerance, level_tolerance)

    reference_full = integrate_spectrum(
        spec["reference_spectrum"], "reference spectrum"
    )
    if reference_full <= 0.0:
        raise ValueError("reference spectrum carries no irradiance at all")
    coverage = matched["reference"]["band_set_total"] / reference_full
    coverage_ok = coverage >= coverage_floor - _tolerance(coverage_floor)

    findings = []
    for result in band_results:
        if not result["meets_required_grade"]:
            findings.append(
                "band %g to %g nm delivers %g of the reference share, grading %s "
                "against a required %s"
                % (
                    result["band"][0],
                    result["band"][1],
                    result["share_ratio"],
                    result["grade"],
                    required_grade,
                )
            )
    if not level_ok:
        findings.append(
            "simulator delivers %g across the band set against a target of %g, a "
            "deviation of %g outside the declared tolerance of %g"
            % (delivered, target, level_deviation, level_tolerance)
        )
    if not coverage_ok:
        findings.append(
            "the band set encloses %g of the reference spectrum, below the declared "
            "coverage floor of %g, so the match was graded on part of the reference "
            "only" % (coverage, coverage_floor)
        )

    return {
        "simulator_id": simulator_id,
        "required_grade": required_grade,
        "bands": band_results,
        "overall_grade": overall,
        "distribution_acceptable": distribution_ok,
        "delivered_total_irradiance": delivered,
        "target_total_irradiance": target,
        "level_deviation": level_deviation,
        "level_acceptable": level_ok,
        "reference_coverage": coverage,
        "reference_coverage_floor": coverage_floor,
        "coverage_acceptable": coverage_ok,
        "worst_band": min(
            band_results, key=lambda b: (-grade_rank(b["grade"]), b["band"][0])
        )["band"],
        "findings": findings,
        "verdict": SIMULATOR_ACCEPTED if not findings else SIMULATOR_REJECTED,
        "accepted": not findings,
    }
