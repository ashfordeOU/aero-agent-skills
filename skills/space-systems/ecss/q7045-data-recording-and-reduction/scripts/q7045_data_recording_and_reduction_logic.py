"""Recording and reduction of a mechanical-test curve into material properties.

Anchor: ECSS-Q-ST-70-45 data clause -- what a mechanical test has to record and
how the recorded curve is reduced into the properties that leave the
laboratory. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Normalise every recorded quantity into one working unit set (newtons,
   millimetres, megapascals), refusing a unit that is not in the registry
   instead of guessing at it.
2. Validate the recorded curve: enough points, finite, and monotonic in
   extension, so a reduction is not run over a rewound or duplicated trace.
3. Turn force and extension into engineering stress and strain through the
   original cross-section and the original gauge length.
4. Fit the modulus by least squares over a declared strain window and keep the
   coefficient of determination as the evidence the window was elastic.
5. Find the offset proof strength by intersecting the offset line with the
   curve, interpolating between the two points that bracket the crossing.
6. Take the tensile strength and the strain at maximum force from the curve,
   and the elongation after fracture from the reassembled specimen.
"""

import math

__all__ = [
    "FORCE_UNITS_TO_N",
    "LENGTH_UNITS_TO_MM",
    "MIN_CURVE_POINTS",
    "DEFAULT_OFFSET_STRAIN",
    "DEFAULT_MIN_R_SQUARED",
    "REDUCTION_TOLERANCE",
    "convert_force_to_n",
    "convert_length_to_mm",
    "round_cross_section_mm2",
    "rectangular_cross_section_mm2",
    "validate_curve",
    "engineering_curve",
    "least_squares_fit",
    "modulus_from_window",
    "interpolate_stress",
    "offset_proof_strength",
    "tensile_strength",
    "elongation_after_fracture_pct",
    "reduce_test_record",
]

FORCE_UNITS_TO_N = {"N": 1.0, "kN": 1000.0, "MN": 1.0e6}
LENGTH_UNITS_TO_MM = {"mm": 1.0, "m": 1000.0, "um": 0.001, "cm": 10.0}

# Below this many points a curve cannot carry an elastic fit and a proof
# strength at once.
MIN_CURVE_POINTS = 10

DEFAULT_OFFSET_STRAIN = 0.002
DEFAULT_MIN_R_SQUARED = 0.995

# Reductions are chains of divisions and a least-squares fit. A value that is
# physically exactly on a bound can land a few ULP either side of it, so the
# comparisons absorb that instead of moving the bound.
REDUCTION_TOLERANCE = 1e-12


def _real(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(label, value):
    number = _real(label, value)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def convert_force_to_n(value, unit):
    """Return a recorded force in newtons, refusing an unknown unit."""
    if unit not in FORCE_UNITS_TO_N:
        raise ValueError(
            "force unit %r is not in the registry %s" % (unit, sorted(FORCE_UNITS_TO_N))
        )
    return _real("force", value) * FORCE_UNITS_TO_N[unit]


def convert_length_to_mm(value, unit):
    """Return a recorded length in millimetres, refusing an unknown unit."""
    if unit not in LENGTH_UNITS_TO_MM:
        raise ValueError(
            "length unit %r is not in the registry %s" % (unit, sorted(LENGTH_UNITS_TO_MM))
        )
    return _real("length", value) * LENGTH_UNITS_TO_MM[unit]


def round_cross_section_mm2(diameter_mm):
    """Return the original cross-section of a round specimen."""
    diameter = _positive("diameter_mm", diameter_mm)
    return math.pi * diameter * diameter / 4.0


def rectangular_cross_section_mm2(width_mm, thickness_mm):
    """Return the original cross-section of a flat specimen."""
    return _positive("width_mm", width_mm) * _positive("thickness_mm", thickness_mm)


def validate_curve(points):
    """Return the validated (force_n, extension_mm) record of a test."""
    if not isinstance(points, (list, tuple)):
        raise ValueError("points must be a sequence of (force, extension) pairs")
    if len(points) < MIN_CURVE_POINTS:
        raise ValueError(
            "a reduction needs at least %d recorded points, got %d"
            % (MIN_CURVE_POINTS, len(points))
        )
    cleaned = []
    for index, item in enumerate(points):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("points[%d] must be a (force, extension) pair" % index)
        force = _real("points[%d] force" % index, item[0])
        extension = _real("points[%d] extension" % index, item[1])
        if force < 0.0:
            raise ValueError("points[%d] force must not be negative" % index)
        if extension < 0.0:
            raise ValueError("points[%d] extension must not be negative" % index)
        if cleaned and extension <= cleaned[-1][1]:
            raise ValueError(
                "points[%d] extension %g does not advance on %g; the record is not "
                "monotonic and cannot be reduced" % (index, extension, cleaned[-1][1])
            )
        cleaned.append((force, extension))
    return cleaned


def engineering_curve(points, area_mm2, gauge_length_mm):
    """Return the engineering (strain, stress in MPa) curve of a test record."""
    cleaned = validate_curve(points)
    area = _positive("area_mm2", area_mm2)
    length = _positive("gauge_length_mm", gauge_length_mm)
    return [(extension / length, force / area) for force, extension in cleaned]


def least_squares_fit(pairs):
    """Return {'slope', 'intercept', 'r_squared'} of a straight-line fit."""
    if not isinstance(pairs, (list, tuple)) or len(pairs) < 3:
        raise ValueError("a straight-line fit needs at least three points")
    xs = []
    ys = []
    for index, item in enumerate(pairs):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("pairs[%d] must be an (x, y) pair" % index)
        xs.append(_real("pairs[%d] x" % index, item[0]))
        ys.append(_real("pairs[%d] y" % index, item[1]))
    n = float(len(xs))
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx <= 0.0:
        raise ValueError("fit abscissae are all equal; the slope is undefined")
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    syy = sum((y - mean_y) ** 2 for y in ys)
    r_squared = 1.0 if syy <= 0.0 else (sxy * sxy) / (sxx * syy)
    return {"slope": slope, "intercept": intercept, "r_squared": r_squared, "points": len(xs)}


def modulus_from_window(curve, strain_from, strain_to, min_r_squared=DEFAULT_MIN_R_SQUARED):
    """Fit the modulus over a strain window and report the fit quality."""
    if not isinstance(curve, (list, tuple)) or not curve:
        raise ValueError("curve must be a non-empty sequence of (strain, stress) pairs")
    low = _real("strain_from", strain_from)
    high = _real("strain_to", strain_to)
    if low < 0.0:
        raise ValueError("strain_from must not be negative, got %r" % (strain_from,))
    if high <= low:
        raise ValueError("strain_to %g must exceed strain_from %g" % (high, low))
    floor = _real("min_r_squared", min_r_squared)
    if not 0.0 < floor <= 1.0:
        raise ValueError("min_r_squared must lie in (0, 1], got %r" % (min_r_squared,))
    window = [(strain, stress) for strain, stress in curve if low <= strain <= high]
    if len(window) < 3:
        raise ValueError(
            "the strain window [%g, %g] holds %d recorded points; a fit needs three"
            % (low, high, len(window))
        )
    fit = least_squares_fit(window)
    acceptable = fit["r_squared"] > floor or math.isclose(
        fit["r_squared"], floor, rel_tol=0.0, abs_tol=REDUCTION_TOLERANCE
    )
    return {
        "modulus_mpa": fit["slope"],
        "modulus_gpa": fit["slope"] / 1000.0,
        "intercept_mpa": fit["intercept"],
        "r_squared": fit["r_squared"],
        "window_points": fit["points"],
        "window_acceptable": acceptable,
    }


def interpolate_stress(curve, strain):
    """Return the recorded stress at a strain, interpolating between points."""
    if not isinstance(curve, (list, tuple)) or len(curve) < 2:
        raise ValueError("curve needs at least two points to interpolate")
    target = _real("strain", strain)
    first = curve[0][0]
    last = curve[-1][0]
    if target < first or target > last:
        raise ValueError(
            "strain %g lies outside the recorded range [%g, %g]; extrapolation refused"
            % (target, first, last)
        )
    for index in range(1, len(curve)):
        x0, y0 = curve[index - 1]
        x1, y1 = curve[index]
        if target <= x1:
            if x1 == x0:
                return y0
            fraction = (target - x0) / (x1 - x0)
            return y0 + fraction * (y1 - y0)
    return curve[-1][1]


def offset_proof_strength(curve, modulus_mpa, offset=DEFAULT_OFFSET_STRAIN):
    """Return the proof strength at a plastic offset, or None when not reached.

    The offset line rises from the offset strain with the elastic slope; the
    proof strength is where the recorded curve first falls back through it.
    """
    if not isinstance(curve, (list, tuple)) or len(curve) < 2:
        raise ValueError("curve needs at least two points for a proof strength")
    slope = _positive("modulus_mpa", modulus_mpa)
    plastic = _real("offset", offset)
    if plastic <= 0.0:
        raise ValueError("offset must be positive, got %r" % (offset,))
    previous = None
    for strain, stress in curve:
        gap = stress - slope * (strain - plastic)
        if previous is not None:
            prev_strain, prev_gap, prev_stress = previous
            if prev_gap > 0.0 >= gap:
                span = prev_gap - gap
                fraction = 0.0 if span == 0.0 else prev_gap / span
                crossing_strain = prev_strain + fraction * (strain - prev_strain)
                crossing_stress = prev_stress + fraction * (stress - prev_stress)
                return {"strain": crossing_strain, "stress_mpa": crossing_stress}
        previous = (strain, gap, stress)
    return None


def tensile_strength(curve):
    """Return the maximum stress on the curve and the strain it occurred at."""
    if not isinstance(curve, (list, tuple)) or not curve:
        raise ValueError("curve must be a non-empty sequence of (strain, stress) pairs")
    best_strain = None
    best_stress = None
    for strain, stress in curve:
        value = _real("stress", stress)
        if best_stress is None or value > best_stress:
            best_stress = value
            best_strain = _real("strain", strain)
    return {"stress_mpa": best_stress, "strain_at_max_force": best_strain}


def elongation_after_fracture_pct(final_gauge_length_mm, original_gauge_length_mm):
    """Return the percentage elongation measured on the reassembled specimen."""
    final_length = _positive("final_gauge_length_mm", final_gauge_length_mm)
    original = _positive("original_gauge_length_mm", original_gauge_length_mm)
    if final_length < original:
        raise ValueError(
            "final gauge length %g is shorter than the original %g" % (final_length, original)
        )
    return 100.0 * (final_length - original) / original


def reduce_test_record(spec):
    """Reduce one recorded test into the properties it reports.

    spec keys: points, force_unit, length_unit, gauge_length_mm, and either
    diameter_mm or (width_mm, thickness_mm). Optional: fit_window (pair of
    strains), offset, min_r_squared, final_gauge_length_mm.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("points", "force_unit", "length_unit", "gauge_length_mm"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    if "diameter_mm" in spec:
        area = round_cross_section_mm2(spec["diameter_mm"])
    elif "width_mm" in spec and "thickness_mm" in spec:
        area = rectangular_cross_section_mm2(spec["width_mm"], spec["thickness_mm"])
    else:
        raise ValueError("spec needs either 'diameter_mm' or both 'width_mm' and 'thickness_mm'")

    force_unit = spec["force_unit"]
    length_unit = spec["length_unit"]
    normalised = [
        (convert_force_to_n(force, force_unit), convert_length_to_mm(extension, length_unit))
        for force, extension in spec["points"]
    ]
    gauge_length = convert_length_to_mm(spec["gauge_length_mm"], "mm")
    curve = engineering_curve(normalised, area, gauge_length)

    window = spec.get("fit_window", (0.0005, 0.0025))
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("fit_window must be a (strain_from, strain_to) pair")
    modulus = modulus_from_window(
        curve, window[0], window[1], spec.get("min_r_squared", DEFAULT_MIN_R_SQUARED)
    )

    findings = []
    if not modulus["window_acceptable"]:
        findings.append(
            "the elastic fit window returned r-squared %.6f, below the %.6f floor; the "
            "window is not wholly elastic" % (modulus["r_squared"], spec.get("min_r_squared", DEFAULT_MIN_R_SQUARED))
        )

    proof = offset_proof_strength(
        curve, modulus["modulus_mpa"], spec.get("offset", DEFAULT_OFFSET_STRAIN)
    )
    if proof is None:
        findings.append(
            "the recorded curve never crosses the offset line; the proof strength was "
            "not reached inside the record"
        )

    strength = tensile_strength(curve)
    elongation = None
    if spec.get("final_gauge_length_mm") is not None:
        elongation = elongation_after_fracture_pct(
            spec["final_gauge_length_mm"], gauge_length
        )

    if proof is not None and proof["stress_mpa"] > strength["stress_mpa"]:
        findings.append("the proof strength exceeds the tensile strength; the reduction is unsound")

    return {
        "area_mm2": area,
        "curve_points": len(curve),
        "modulus": modulus,
        "proof_strength": proof,
        "tensile_strength": strength,
        "elongation_after_fracture_pct": elongation,
        "findings": findings,
        "reportable": not findings,
    }
