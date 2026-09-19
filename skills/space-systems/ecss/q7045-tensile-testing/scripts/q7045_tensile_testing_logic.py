"""Tensile properties of a metallic specimen from its stress-strain record.

Anchor: ECSS-Q-ST-70-45, methods clause -- the tension test pulls a specimen
of declared gauge length to fracture and the record is reduced to modulus,
proof strength, ultimate strength and elongation. Paraphrased into an
implementable procedure; no standard text is reproduced.

What this module decides
------------------------
Which numbers the pulled specimen actually supports, and which of them a
reviewer is entitled to see caveated.

1. Modulus is a fit, not a ratio of two points. It is the least-squares slope
   over a declared elastic window, and it is reported with the quality of that
   fit, because a window that has crept past the knee still returns a slope.
2. Proof strength is a crossing. The offset line of slope E shifted by the
   offset strain crosses the record once; the crossing is interpolated inside
   the segment that brackets it, never snapped to the nearer sample.
3. Ultimate strength is the peak of the engineering curve, which may sit well
   before the last recorded point. The last point is fracture, not strength.
4. Elongation and reduction of area come from the broken halves, not from the
   record: the machine's final crosshead strain includes the frame.
"""

import math

__all__ = [
    "DEFAULT_OFFSET_STRAIN",
    "MIN_ELASTIC_POINTS",
    "MIN_FIT_QUALITY",
    "validate_curve",
    "elastic_modulus",
    "offset_proof_strength",
    "ultimate_tensile_strength",
    "elongation_after_fracture_pct",
    "reduction_of_area_pct",
    "assess_tensile_test",
]

# The proof strength offset the methods clause uses by default.
DEFAULT_OFFSET_STRAIN = 0.002

# A slope drawn through two points is not a fit.
MIN_ELASTIC_POINTS = 3

# Below this coefficient of determination the declared window is not elastic.
MIN_FIT_QUALITY = 0.999

# Comparisons against a specified minimum are inclusive; absorb representation
# error at the edge rather than widening the specification itself.
REL_TOLERANCE = 1e-9


def _as_finite_float(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _as_positive_float(value, label):
    number = _as_finite_float(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _meets(value, minimum):
    """Return True when value reaches minimum, absorbing representation error."""
    return value >= minimum - abs(minimum) * REL_TOLERANCE - REL_TOLERANCE


def validate_curve(points):
    """Return the stress-strain record as validated pairs in strict strain order."""
    if not isinstance(points, (list, tuple)) or len(points) < MIN_ELASTIC_POINTS:
        raise ValueError(
            "a tensile record needs at least %d points" % MIN_ELASTIC_POINTS
        )
    records = []
    for i, item in enumerate(points):
        if not isinstance(item, dict):
            raise ValueError("point %d must be a mapping" % i)
        for key in ("strain", "stress_mpa"):
            if key not in item:
                raise ValueError("point %d is missing '%s'" % (i, key))
        strain = _as_finite_float(item["strain"], "point %d strain" % i)
        stress = _as_finite_float(item["stress_mpa"], "point %d stress_mpa" % i)
        if strain < 0.0:
            raise ValueError("point %d strain must not be negative" % i)
        if stress < 0.0:
            raise ValueError("point %d stress_mpa must not be negative" % i)
        records.append({"strain": strain, "stress_mpa": stress})
    for i in range(1, len(records)):
        if records[i]["strain"] <= records[i - 1]["strain"]:
            raise ValueError(
                "strain must strictly increase (point %d at %g follows %g)"
                % (i, records[i]["strain"], records[i - 1]["strain"])
            )
    return records


def elastic_modulus(points, window):
    """Return the least-squares modulus over a declared elastic strain window.

    window is a (low, high) strain pair. The result carries the slope in MPa,
    the intercept, the number of points the fit used and the coefficient of
    determination, so a window that has already passed the knee can be seen.
    """
    records = validate_curve(points)
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("window must be a (low, high) strain pair")
    low = _as_finite_float(window[0], "window low")
    high = _as_finite_float(window[1], "window high")
    if low >= high:
        raise ValueError("window low %g must be below high %g" % (low, high))
    inside = [r for r in records if low <= r["strain"] <= high]
    if len(inside) < MIN_ELASTIC_POINTS:
        raise ValueError(
            "elastic window holds %d points, at least %d are needed"
            % (len(inside), MIN_ELASTIC_POINTS)
        )
    n = float(len(inside))
    mean_x = sum(r["strain"] for r in inside) / n
    mean_y = sum(r["stress_mpa"] for r in inside) / n
    sxx = sum((r["strain"] - mean_x) * (r["strain"] - mean_x) for r in inside)
    sxy = sum((r["strain"] - mean_x) * (r["stress_mpa"] - mean_y) for r in inside)
    if sxx <= 0.0:
        raise ValueError("elastic window has no strain spread to fit against")
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    syy = sum((r["stress_mpa"] - mean_y) * (r["stress_mpa"] - mean_y)
               for r in inside)
    if syy <= 0.0:
        quality = 0.0
    else:
        residual = 0.0
        for r in inside:
            gap = r["stress_mpa"] - (intercept + slope * r["strain"])
            residual += gap * gap
        quality = 1.0 - residual / syy
    if slope <= 0.0:
        raise ValueError("elastic window returns a non-positive modulus")
    return {
        "modulus_mpa": slope,
        "intercept_mpa": intercept,
        "points_used": len(inside),
        "fit_quality": quality,
    }


def offset_proof_strength(points, modulus_mpa, offset_strain=DEFAULT_OFFSET_STRAIN):
    """Return the stress where the offset line of slope E crosses the record."""
    records = validate_curve(points)
    slope = _as_positive_float(modulus_mpa, "modulus_mpa")
    offset = _as_positive_float(offset_strain, "offset_strain")
    gaps = [r["stress_mpa"] - slope * (r["strain"] - offset) for r in records]
    for i in range(1, len(records)):
        if gaps[i] <= 0.0 < gaps[i - 1]:
            span = gaps[i - 1] - gaps[i]
            t = gaps[i - 1] / span
            return records[i - 1]["stress_mpa"] + t * (
                records[i]["stress_mpa"] - records[i - 1]["stress_mpa"]
            )
        if gaps[i] == 0.0 and gaps[i - 1] == 0.0:
            return records[i]["stress_mpa"]
    raise ValueError(
        "the offset line never crosses the record; the specimen did not yield "
        "inside the recorded range"
    )


def ultimate_tensile_strength(points):
    """Return the peak engineering stress, which need not be the last point."""
    records = validate_curve(points)
    peak = records[0]
    for record in records[1:]:
        if record["stress_mpa"] > peak["stress_mpa"]:
            peak = record
    return {"stress_mpa": peak["stress_mpa"], "strain": peak["strain"]}


def elongation_after_fracture_pct(gauge_initial_mm, gauge_final_mm):
    """Return percentage elongation measured on the reassembled broken halves."""
    initial = _as_positive_float(gauge_initial_mm, "gauge_initial_mm")
    final = _as_positive_float(gauge_final_mm, "gauge_final_mm")
    if final < initial:
        raise ValueError(
            "final gauge length %g mm is below the initial %g mm" % (final, initial)
        )
    return (final - initial) / initial * 100.0


def reduction_of_area_pct(area_initial_mm2, area_final_mm2):
    """Return percentage reduction of area at the fracture section."""
    initial = _as_positive_float(area_initial_mm2, "area_initial_mm2")
    final = _as_positive_float(area_final_mm2, "area_final_mm2")
    if final > initial:
        raise ValueError(
            "fracture area %g mm2 exceeds the initial %g mm2" % (final, initial)
        )
    return (initial - final) / initial * 100.0


def assess_tensile_test(spec):
    """Reduce one tension test and compare it with the specified minima.

    spec keys: points (stress-strain record), elastic_window, gauge_initial_mm,
    gauge_final_mm; optional area_initial_mm2, area_final_mm2, offset_strain
    and a 'minima' mapping of proof_strength_mpa, tensile_strength_mpa,
    elongation_pct, reduction_of_area_pct.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("points", "elastic_window", "gauge_initial_mm", "gauge_final_mm"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    offset = spec.get("offset_strain", DEFAULT_OFFSET_STRAIN)
    fit = elastic_modulus(spec["points"], spec["elastic_window"])
    proof = offset_proof_strength(spec["points"], fit["modulus_mpa"], offset)
    peak = ultimate_tensile_strength(spec["points"])
    elongation = elongation_after_fracture_pct(
        spec["gauge_initial_mm"], spec["gauge_final_mm"]
    )
    reduction = None
    if spec.get("area_initial_mm2") is not None:
        if spec.get("area_final_mm2") is None:
            raise ValueError("area_initial_mm2 given without area_final_mm2")
        reduction = reduction_of_area_pct(
            spec["area_initial_mm2"], spec["area_final_mm2"]
        )

    findings = []
    if fit["fit_quality"] < MIN_FIT_QUALITY:
        findings.append(
            "elastic window fit quality %.6f is below %.3f; the window has "
            "passed the knee and the modulus is not elastic"
            % (fit["fit_quality"], MIN_FIT_QUALITY)
        )
    if peak["stress_mpa"] < proof:
        findings.append(
            "peak stress %.3f MPa is below the proof strength %.3f MPa; the "
            "record is not a valid tension curve" % (peak["stress_mpa"], proof)
        )

    minima = spec.get("minima") or {}
    if not isinstance(minima, dict):
        raise ValueError("minima must be a mapping")
    measured = {
        "proof_strength_mpa": proof,
        "tensile_strength_mpa": peak["stress_mpa"],
        "elongation_pct": elongation,
        "reduction_of_area_pct": reduction,
    }
    for key, floor in minima.items():
        if key not in measured:
            raise ValueError("'%s' is not a tensile property" % key)
        limit = _as_finite_float(floor, key)
        value = measured[key]
        if value is None:
            findings.append("'%s' has a specified minimum but was not measured" % key)
        elif not _meets(value, limit):
            findings.append(
                "%s of %.3f is below the specified minimum %.3f" % (key, value, limit)
            )

    return {
        "modulus_mpa": fit["modulus_mpa"],
        "fit_quality": fit["fit_quality"],
        "points_used": fit["points_used"],
        "offset_strain": _as_positive_float(offset, "offset_strain"),
        "proof_strength_mpa": proof,
        "tensile_strength_mpa": peak["stress_mpa"],
        "uniform_strain_at_peak": peak["strain"],
        "elongation_pct": elongation,
        "reduction_of_area_pct": reduction,
        "findings": findings,
        "properties_accepted": not findings,
    }
