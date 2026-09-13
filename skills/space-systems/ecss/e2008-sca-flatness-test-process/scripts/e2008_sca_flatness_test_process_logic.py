#!/usr/bin/env python3
"""Running the solar cell assembly flatness measurement.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.17.2 -- the maximum deflection of the
assembly is measured while the assembly rests on an optically flat reference
surface. The procedure below is a paraphrase into implementable steps; no
standard text is reproduced.

How the run works
-----------------
The assembly is laid, unclamped, on an optical flat. Gravity does the rest:
the stack settles onto whichever points are lowest and the rest of it stands
off the flat by the amount it is bowed or twisted. A probe reads the standoff
at a pattern of points across the footprint.

Three things turn those readings into a defensible deflection:

    the seating plane   a probe zero is arbitrary. The assembly touches the
                        flat where the reading is smallest, so every reading
                        is referred to that smallest one before the largest
                        standoff is called the deflection

    the probe pattern   a bow shows most at the edges and corners, which is
                        exactly where a lazy pattern stops. A deflection read
                        from the middle of the footprint is a number about the
                        middle of the footprint, so how much of the face and
                        of its edge band the pattern reached is reported
                        before the deflection is quoted

    the uncertainties   the optical flat has a residual of its own and the
                        probe has an uncertainty of its own. Combined in
                        quadrature they guard band the deflection, so a
                        disposition downstream is made on a number that
                        already carries its own error

This module measures and reports. It does not sentence the deflection against
a limit; that is the job of the acceptance criteria of clause 6.4.3.17.3.
"""

import math

__all__ = [
    "DEFAULT_FLATNESS_RUN_POLICY",
    "RUN_UNDERSIZED",
    "RUN_COVERAGE_SHORT",
    "RUN_VALID",
    "EDGES",
    "validate_policy",
    "validate_footprint",
    "validate_reference_flat",
    "validate_readings",
    "seated_deflections",
    "maximum_deflection",
    "guard_band",
    "pattern_coverage",
    "edge_band_coverage",
    "measure_sample",
    "run_flatness_measurement",
]

EDGES = ("min-length-edge", "max-length-edge", "min-width-edge", "max-width-edge")

# A declared policy, not a physical constant: a project substitutes its own.
DEFAULT_FLATNESS_RUN_POLICY = {
    "grid_divisions": 3,
    "min_cell_coverage_fraction": 1.0,
    "edge_band_fraction": 0.15,
    "require_every_edge_band": True,
    "min_readings": 5,
    "min_subgroup_samples": 4,
}

RUN_UNDERSIZED = "run-undersized"
RUN_COVERAGE_SHORT = "run-coverage-short"
RUN_VALID = "run-valid"

_REL_TOL = 1e-9


def _real(value, label):
    """Return a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite" % label)
    return value


def _positive(value, label):
    """Return a finite, strictly positive float or raise."""
    value = _real(value, label)
    if value <= 0.0:
        raise ValueError("%s must be positive: %g" % (label, value))
    return value


def _non_negative(value, label):
    """Return a finite, non-negative float or raise."""
    value = _real(value, label)
    if value < 0.0:
        raise ValueError("%s must not be negative: %g" % (label, value))
    return value


def _at_least(value, bound):
    """Return True when value is at or above bound, equality included."""
    if math.isclose(value, bound, rel_tol=_REL_TOL, abs_tol=0.0):
        return True
    return value > bound


def validate_policy(policy=None):
    """Return a validated run policy, defaults filled in."""
    if policy is None:
        policy = {}
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    merged = dict(DEFAULT_FLATNESS_RUN_POLICY)
    for key in policy:
        if key not in DEFAULT_FLATNESS_RUN_POLICY:
            raise ValueError("unrecognised run policy key: %s" % key)
    for key in ("grid_divisions", "min_readings", "min_subgroup_samples"):
        if key in policy:
            value = policy[key]
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError("%s must be a positive integer" % key)
            merged[key] = value
    if "min_cell_coverage_fraction" in policy:
        value = _real(policy["min_cell_coverage_fraction"], "min_cell_coverage_fraction")
        if value < 0.0 or value > 1.0:
            raise ValueError("min_cell_coverage_fraction must sit between 0 and 1")
        merged["min_cell_coverage_fraction"] = value
    if "edge_band_fraction" in policy:
        value = _real(policy["edge_band_fraction"], "edge_band_fraction")
        if value <= 0.0 or value > 0.5:
            raise ValueError("edge_band_fraction must sit above 0 and at or below 0.5")
        merged["edge_band_fraction"] = value
    if "require_every_edge_band" in policy:
        value = policy["require_every_edge_band"]
        if not isinstance(value, bool):
            raise ValueError("require_every_edge_band must be a boolean")
        merged["require_every_edge_band"] = value
    if merged["min_readings"] < 3:
        raise ValueError("min_readings must be at least 3 to define a seating plane")
    return merged


def validate_footprint(footprint):
    """Return the validated assembly footprint in millimetres."""
    if not isinstance(footprint, dict):
        raise ValueError("footprint must be a mapping")
    for key in ("length_mm", "width_mm"):
        if key not in footprint:
            raise ValueError("footprint is missing '%s'" % key)
    return {
        "length_mm": _positive(footprint["length_mm"], "length_mm"),
        "width_mm": _positive(footprint["width_mm"], "width_mm"),
    }


def validate_reference_flat(reference):
    """Return the validated optical flat and probe uncertainties."""
    if not isinstance(reference, dict):
        raise ValueError("reference flat must be a mapping")
    for key in ("flat_residual_um", "probe_uncertainty_um"):
        if key not in reference:
            raise ValueError("reference flat is missing '%s'" % key)
    return {
        "flat_residual_um": _non_negative(reference["flat_residual_um"], "flat_residual_um"),
        "probe_uncertainty_um": _non_negative(
            reference["probe_uncertainty_um"], "probe_uncertainty_um"
        ),
    }


def validate_readings(readings, footprint, policy=None):
    """Return the validated probe readings as (x_mm, y_mm, standoff_um)."""
    footprint = validate_footprint(footprint)
    policy = validate_policy(policy)
    if not isinstance(readings, (list, tuple)):
        raise ValueError("readings must be a sequence of entries")
    if len(readings) < policy["min_readings"]:
        raise ValueError(
            "a seating plane needs at least %d readings, %d given"
            % (policy["min_readings"], len(readings))
        )
    seen = set()
    out = []
    for index, entry in enumerate(readings):
        if not isinstance(entry, dict):
            raise ValueError("reading %d must be a mapping" % index)
        for key in ("x_mm", "y_mm", "standoff_um"):
            if key not in entry:
                raise ValueError("reading %d is missing '%s'" % (index, key))
        x = _real(entry["x_mm"], "x_mm of reading %d" % index)
        y = _real(entry["y_mm"], "y_mm of reading %d" % index)
        standoff = _non_negative(entry["standoff_um"], "standoff_um of reading %d" % index)
        if x < 0.0 or x > footprint["length_mm"]:
            raise ValueError("reading %d sits off the footprint in length: %g" % (index, x))
        if y < 0.0 or y > footprint["width_mm"]:
            raise ValueError("reading %d sits off the footprint in width: %g" % (index, y))
        key = (x, y)
        if key in seen:
            raise ValueError("reading %d repeats a probe point: (%g, %g)" % (index, x, y))
        seen.add(key)
        out.append((x, y, standoff))
    return out


def seated_deflections(readings, footprint, policy=None):
    """Refer every reading to the seating plane the assembly rests on."""
    points = validate_readings(readings, footprint, policy)
    datum = min(point[2] for point in points)
    return [
        {"x_mm": x, "y_mm": y, "deflection_um": standoff - datum}
        for x, y, standoff in points
    ]


def maximum_deflection(readings, footprint, policy=None):
    """Return the largest standoff above the seating plane and where it sits."""
    seated = seated_deflections(readings, footprint, policy)
    worst = max(seated, key=lambda point: point["deflection_um"])
    return {
        "max_deflection_um": worst["deflection_um"],
        "x_mm": worst["x_mm"],
        "y_mm": worst["y_mm"],
    }


def guard_band(reference):
    """Return the combined measurement uncertainty in micrometres."""
    reference = validate_reference_flat(reference)
    residual = reference["flat_residual_um"]
    probe = reference["probe_uncertainty_um"]
    # sqrt is correctly rounded under IEEE 754, so this combination is
    # reproducible on every platform the suite runs on.
    return math.sqrt(residual * residual + probe * probe)


def pattern_coverage(readings, footprint, policy=None):
    """Return how many footprint cells the probe pattern actually reached."""
    footprint = validate_footprint(footprint)
    policy = validate_policy(policy)
    points = validate_readings(readings, footprint, policy)
    divisions = policy["grid_divisions"]
    total = divisions * divisions
    reached = set()
    for x, y, _standoff in points:
        col = int(x * divisions / footprint["length_mm"])
        row = int(y * divisions / footprint["width_mm"])
        col = min(max(col, 0), divisions - 1)
        row = min(max(row, 0), divisions - 1)
        reached.add((col, row))
    unread = [
        (col, row)
        for row in range(divisions)
        for col in range(divisions)
        if (col, row) not in reached
    ]
    return {
        "grid_divisions": divisions,
        "cell_count": total,
        "cells_read": len(reached),
        "unread_cells": unread,
        "coverage_fraction": len(reached) / total,
    }


def edge_band_coverage(readings, footprint, policy=None):
    """Return which edge bands of the footprint the probe pattern reached."""
    footprint = validate_footprint(footprint)
    policy = validate_policy(policy)
    points = validate_readings(readings, footprint, policy)
    band = policy["edge_band_fraction"]
    length_band = footprint["length_mm"] * band
    width_band = footprint["width_mm"] * band
    reached = set()
    for x, y, _standoff in points:
        if x <= length_band:
            reached.add("min-length-edge")
        if x >= footprint["length_mm"] - length_band:
            reached.add("max-length-edge")
        if y <= width_band:
            reached.add("min-width-edge")
        if y >= footprint["width_mm"] - width_band:
            reached.add("max-width-edge")
    unread = [name for name in EDGES if name not in reached]
    return {
        "edge_band_fraction": band,
        "edges_read": sorted(reached),
        "unread_edges": unread,
    }


def measure_sample(sample, footprint, reference, policy=None):
    """Measure one assembly and report its deflection and pattern coverage."""
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping")
    for key in ("sample_id", "readings"):
        if key not in sample:
            raise ValueError("sample is missing '%s'" % key)
    sample_id = sample["sample_id"]
    if not isinstance(sample_id, str) or not sample_id.strip():
        raise ValueError("sample_id must be a non-empty string")
    footprint = validate_footprint(footprint)
    policy = validate_policy(policy)
    band = guard_band(reference)

    worst = maximum_deflection(sample["readings"], footprint, policy)
    cells = pattern_coverage(sample["readings"], footprint, policy)
    edges = edge_band_coverage(sample["readings"], footprint, policy)

    findings = []
    if not _at_least(cells["coverage_fraction"], policy["min_cell_coverage_fraction"]):
        findings.append(
            "the probe pattern reached %d of %d footprint cells against a floor of %.3f"
            % (cells["cells_read"], cells["cell_count"], policy["min_cell_coverage_fraction"])
        )
    if policy["require_every_edge_band"] and edges["unread_edges"]:
        findings.append(
            "the probe pattern never reached the %s, where a bow stands off most"
            % ", ".join(edges["unread_edges"])
        )
    return {
        "sample_id": sample_id,
        "reading_count": len(sample["readings"]),
        "max_deflection_um": worst["max_deflection_um"],
        "worst_point_mm": (worst["x_mm"], worst["y_mm"]),
        "guard_band_um": band,
        "guard_banded_deflection_um": worst["max_deflection_um"] + band,
        "coverage": cells,
        "edge_bands": edges,
        "findings": findings,
        "coverage_sufficient": not findings,
    }


def run_flatness_measurement(spec):
    """Run the full clause 6.4.3.17.2 measurement over a subgroup.

    spec keys: footprint, reference_flat, samples; optional policy.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("footprint", "reference_flat", "samples"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    footprint = validate_footprint(spec["footprint"])
    reference = validate_reference_flat(spec["reference_flat"])
    policy = validate_policy(spec.get("policy"))
    samples = spec["samples"]
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("samples must be a non-empty sequence")

    measured = []
    seen_ids = set()
    for sample in samples:
        result = measure_sample(sample, footprint, reference, policy)
        if result["sample_id"] in seen_ids:
            raise ValueError("sample identifier repeated: %s" % result["sample_id"])
        seen_ids.add(result["sample_id"])
        measured.append(result)

    findings = []
    if len(measured) < policy["min_subgroup_samples"]:
        verdict = RUN_UNDERSIZED
        findings.append(
            "the run read %d samples against a subgroup floor of %d"
            % (len(measured), policy["min_subgroup_samples"])
        )
    else:
        short = [r for r in measured if not r["coverage_sufficient"]]
        if short:
            verdict = RUN_COVERAGE_SHORT
            for result in short:
                for finding in result["findings"]:
                    findings.append("%s: %s" % (result["sample_id"], finding))
        else:
            verdict = RUN_VALID

    worst = max(measured, key=lambda r: r["guard_banded_deflection_um"])
    return {
        "verdict": verdict,
        "sample_count": len(measured),
        "footprint": footprint,
        "reference_flat": reference,
        "guard_band_um": measured[0]["guard_band_um"],
        "worst_sample_id": worst["sample_id"],
        "worst_max_deflection_um": worst["max_deflection_um"],
        "worst_guard_banded_deflection_um": worst["guard_banded_deflection_um"],
        "samples": measured,
        "findings": findings,
    }
