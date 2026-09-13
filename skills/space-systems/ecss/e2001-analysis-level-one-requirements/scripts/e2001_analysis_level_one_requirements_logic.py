"""Applicability and content of the first (simpler) multipaction analysis level.

Anchor: ECSS-E-ST-20-01C clause 5.3.2.2.1 (design analysis -- where the first
analysis level applies and what it demands of the assessment). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Test the component against the applicability criteria of the first level:
   a chart-covered canonical geometry, a sufficiently homogeneous field in the
   critical gap, a surface material with standard secondary-emission chart
   data, no dielectric inside the gap, a single dominant propagating mode, and
   a worst-case frequency-gap product inside the charted span.
2. Any criterion that fails escalates the component to the second level; the
   failing criteria are reported, not summarised away.
3. When the first level applies, derive its demanded content: the worst-case
   gap from the dimensional tolerance stack, the charted threshold at the
   worst-case frequency-gap product, the resulting breakdown power and the
   achieved margin against the required value.
4. Check that the assessment record carries every demanded evidence item.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE_DB",
    "RATIO_TOLERANCE",
    "CANONICAL_GEOMETRIES",
    "CHARTED_MATERIALS",
    "DEFAULT_MAX_FIELD_RATIO",
    "LEVEL_ONE_CRITERIA",
    "LEVEL_ONE_EVIDENCE",
    "normalize_geometry",
    "normalize_material",
    "gap_extremes_mm",
    "field_homogeneous",
    "chart_span",
    "charted_threshold_v",
    "worst_case_gap_product",
    "evaluate_criteria",
    "select_analysis_level",
    "missing_evidence",
    "level_one_margin_db",
    "assess_level_one",
]

# Margin and ratio comparisons are differences of computed quantities; an
# exactly-compliant case can land a few ULPs the wrong side. Absorb the
# representation error here; the engineering limits stay where they are.
MARGIN_TOLERANCE_DB = 1e-9
RATIO_TOLERANCE = 1e-12

# Geometries for which standard multipactor chart data exists.
CANONICAL_GEOMETRIES = (
    "parallel-plate",
    "coaxial-line",
    "rectangular-waveguide-iris",
    "circular-waveguide-gap",
    "stepped-waveguide-gap",
)

# Surface finishes with standard secondary-emission chart data.
CHARTED_MATERIALS = (
    "silver",
    "aluminium",
    "alodine-treated-aluminium",
    "copper",
    "gold",
    "stainless-steel",
)

# The first level assumes a near-homogeneous field across the critical gap.
DEFAULT_MAX_FIELD_RATIO = 1.10

LEVEL_ONE_CRITERIA = (
    "canonical-geometry",
    "homogeneous-gap-field",
    "charted-surface-material",
    "no-dielectric-in-gap",
    "single-dominant-mode",
    "charted-frequency-gap-product",
)

LEVEL_ONE_EVIDENCE = (
    "worst-case-gap-from-tolerance-stack",
    "worst-case-in-band-frequency",
    "charted-threshold-for-actual-surface",
    "achieved-margin-statement",
)


def normalize_geometry(name):
    """Return the canonical geometry key, or raise for an unusable value."""
    if not isinstance(name, str):
        raise ValueError("geometry must be a string, got %r" % (name,))
    key = name.strip().lower()
    if not key:
        raise ValueError("geometry must not be empty")
    return key


def normalize_material(name):
    """Return the canonical surface-material key, or raise for an unusable value."""
    if not isinstance(name, str):
        raise ValueError("surface material must be a string, got %r" % (name,))
    key = name.strip().lower()
    if not key:
        raise ValueError("surface material must not be empty")
    return key


def _positive(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    if v <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, v))
    return v


def _non_negative(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    if v < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, v))
    return v


def gap_extremes_mm(nominal_mm, minus_tolerance_mm, plus_tolerance_mm):
    """Return the (minimum, maximum) critical gap from the tolerance stack."""
    nominal = _positive(nominal_mm, "nominal_mm")
    minus = _non_negative(minus_tolerance_mm, "minus_tolerance_mm")
    plus = _non_negative(plus_tolerance_mm, "plus_tolerance_mm")
    smallest = nominal - minus
    if smallest <= 0.0:
        raise ValueError(
            "minus tolerance %g mm closes the %g mm gap; the stack is not usable"
            % (minus, nominal)
        )
    return (smallest, nominal + plus)


def field_homogeneous(peak_field, mean_field, max_ratio=DEFAULT_MAX_FIELD_RATIO):
    """Return True when the gap field is homogeneous enough for the first level."""
    peak = _positive(peak_field, "peak_field")
    mean = _positive(mean_field, "mean_field")
    limit = _positive(max_ratio, "max_ratio")
    if peak < mean:
        raise ValueError("peak_field %g is below mean_field %g" % (peak, mean))
    ratio = peak / mean
    if ratio < limit:
        return True
    return math.isclose(ratio, limit, rel_tol=RATIO_TOLERANCE, abs_tol=0.0)


def _validate_chart(chart):
    if not isinstance(chart, (list, tuple)) or len(chart) < 2:
        raise ValueError("chart needs at least two (fd, threshold) points")
    points = []
    for i, entry in enumerate(chart):
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise ValueError("chart[%d] must be an (fd, threshold) pair" % i)
        fd = _positive(entry[0], "chart[%d] frequency-gap product" % i)
        volts = _positive(entry[1], "chart[%d] threshold" % i)
        points.append((fd, volts))
    for i in range(1, len(points)):
        if points[i][0] <= points[i - 1][0]:
            raise ValueError("chart abscissae must strictly increase (index %d)" % i)
    return points


def chart_span(chart):
    """Return the (lowest, highest) frequency-gap product the chart covers."""
    points = _validate_chart(chart)
    return (points[0][0], points[-1][0])


def charted_threshold_v(chart, fd_ghz_mm):
    """Return the charted breakdown-voltage threshold by log-log interpolation."""
    points = _validate_chart(chart)
    fd = _positive(fd_ghz_mm, "fd_ghz_mm")
    lo, hi = points[0][0], points[-1][0]
    if fd < lo or fd > hi:
        raise ValueError(
            "frequency-gap product %g is outside the charted span [%g, %g]" % (fd, lo, hi)
        )
    for i in range(1, len(points)):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        if fd <= x1:
            if fd == x0:
                return y0
            if fd == x1:
                return y1
            t = (math.log(fd) - math.log(x0)) / (math.log(x1) - math.log(x0))
            return math.exp(math.log(y0) + t * (math.log(y1) - math.log(y0)))
    return points[-1][1]


def worst_case_gap_product(frequency_ghz, gap_min_mm, gap_max_mm, chart):
    """Return the (fd, gap) pair giving the lowest charted threshold in the stack."""
    f = _positive(frequency_ghz, "frequency_ghz")
    lo_gap = _positive(gap_min_mm, "gap_min_mm")
    hi_gap = _positive(gap_max_mm, "gap_max_mm")
    if lo_gap > hi_gap:
        raise ValueError("gap_min_mm %g exceeds gap_max_mm %g" % (lo_gap, hi_gap))
    best = None
    for gap in (lo_gap, hi_gap):
        fd = f * gap
        threshold = charted_threshold_v(chart, fd)
        if best is None or threshold < best[2] or (
            math.isclose(threshold, best[2], rel_tol=RATIO_TOLERANCE, abs_tol=0.0)
            and gap < best[1]
        ):
            best = (fd, gap, threshold)
    return {"fd_ghz_mm": best[0], "gap_mm": best[1], "threshold_voltage_v": best[2]}


def evaluate_criteria(inputs):
    """Return the per-criterion verdicts for the first analysis level."""
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a mapping")
    for key in ("geometry", "surface_material", "peak_field", "mean_field",
                "dielectric_in_gap", "propagating_modes", "worst_case_fd_ghz_mm",
                "chart"):
        if key not in inputs:
            raise ValueError("inputs missing required key '%s'" % key)
    if not isinstance(inputs["dielectric_in_gap"], bool):
        raise ValueError("dielectric_in_gap must be a boolean")
    modes = inputs["propagating_modes"]
    if not isinstance(modes, int) or isinstance(modes, bool):
        raise ValueError("propagating_modes must be an integer")
    if modes < 1:
        raise ValueError("propagating_modes must be at least 1, got %d" % modes)
    geometry = normalize_geometry(inputs["geometry"])
    material = normalize_material(inputs["surface_material"])
    homogeneous = field_homogeneous(
        inputs["peak_field"],
        inputs["mean_field"],
        inputs.get("max_field_ratio", DEFAULT_MAX_FIELD_RATIO),
    )
    lo, hi = chart_span(inputs["chart"])
    fd = _positive(inputs["worst_case_fd_ghz_mm"], "worst_case_fd_ghz_mm")
    verdicts = {
        "canonical-geometry": geometry in CANONICAL_GEOMETRIES,
        "homogeneous-gap-field": homogeneous,
        "charted-surface-material": material in CHARTED_MATERIALS,
        "no-dielectric-in-gap": not inputs["dielectric_in_gap"],
        "single-dominant-mode": modes == 1,
        "charted-frequency-gap-product": lo <= fd <= hi,
    }
    for name in LEVEL_ONE_CRITERIA:
        if name not in verdicts:
            raise ValueError("criterion '%s' was not evaluated" % name)
    return verdicts


def select_analysis_level(verdicts):
    """Return ('level-one'|'level-two', failed-criteria) from the verdicts."""
    if not isinstance(verdicts, dict) or not verdicts:
        raise ValueError("verdicts must be a non-empty mapping")
    failed = []
    for name in LEVEL_ONE_CRITERIA:
        if name not in verdicts:
            raise ValueError("verdicts missing criterion '%s'" % name)
        if not isinstance(verdicts[name], bool):
            raise ValueError("verdict for '%s' must be a boolean" % name)
        if not verdicts[name]:
            failed.append(name)
    return ("level-two" if failed else "level-one", failed)


def missing_evidence(declared):
    """Return the demanded first-level evidence items that are absent."""
    if declared is None:
        declared = []
    if not isinstance(declared, (list, tuple)):
        raise ValueError("declared evidence must be a sequence")
    seen = []
    for entry in declared:
        if not isinstance(entry, str):
            raise ValueError("evidence entry must be a string, got %r" % (entry,))
        key = entry.strip().lower()
        if key not in LEVEL_ONE_EVIDENCE:
            raise ValueError("uncategorized evidence item '%s'" % entry)
        seen.append(key)
    return [name for name in LEVEL_ONE_EVIDENCE if name not in seen]


def level_one_margin_db(threshold_voltage_v, impedance_ohm, operating_power_w,
                        magnification=1.0):
    """Return the achieved margin in dB from the charted threshold."""
    v = _positive(threshold_voltage_v, "threshold_voltage_v")
    z = _positive(impedance_ohm, "impedance_ohm")
    p_op = _positive(operating_power_w, "operating_power_w")
    m = _positive(magnification, "magnification")
    breakdown = (v * v) / (2.0 * z * m * m)
    return 10.0 * math.log10(breakdown / p_op)


def assess_level_one(spec):
    """Run the full clause 5.3.2.2.1 assessment for one component.

    spec keys: the evaluate_criteria inputs, plus frequency_ghz, nominal_gap_mm,
    minus_tolerance_mm, plus_tolerance_mm, impedance_ohm, operating_power_w,
    required_margin_db, optional magnification and declared_evidence.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("frequency_ghz", "nominal_gap_mm", "minus_tolerance_mm",
                "plus_tolerance_mm", "impedance_ohm", "operating_power_w",
                "required_margin_db", "chart"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    gap_min, gap_max = gap_extremes_mm(
        spec["nominal_gap_mm"], spec["minus_tolerance_mm"], spec["plus_tolerance_mm"]
    )
    worst = worst_case_gap_product(
        spec["frequency_ghz"], gap_min, gap_max, spec["chart"]
    )
    criteria_inputs = dict(spec)
    criteria_inputs["worst_case_fd_ghz_mm"] = worst["fd_ghz_mm"]
    verdicts = evaluate_criteria(criteria_inputs)
    level, failed = select_analysis_level(verdicts)
    required = _non_negative(spec["required_margin_db"], "required_margin_db")
    achieved = level_one_margin_db(
        worst["threshold_voltage_v"],
        spec["impedance_ohm"],
        spec["operating_power_w"],
        spec.get("magnification", 1.0),
    )
    margin_ok = achieved > required or math.isclose(
        achieved, required, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE_DB
    )
    absent = missing_evidence(spec.get("declared_evidence"))
    findings = []
    for name in failed:
        findings.append("first-level criterion '%s' not met; escalate the assessment" % name)
    if not margin_ok:
        findings.append(
            "achieved margin %.3f dB is below the required %.3f dB at the %.4f mm gap"
            % (achieved, required, worst["gap_mm"])
        )
    for name in absent:
        findings.append("first-level assessment record is missing '%s'" % name)
    return {
        "analysis_level": level,
        "criteria": verdicts,
        "failed_criteria": failed,
        "gap_min_mm": gap_min,
        "gap_max_mm": gap_max,
        "worst_case": worst,
        "achieved_margin_db": achieved,
        "required_margin_db": required,
        "margin_ok": margin_ok,
        "missing_evidence": absent,
        "findings": findings,
        "compliant": level == "level-one" and margin_ok and not absent,
    }
