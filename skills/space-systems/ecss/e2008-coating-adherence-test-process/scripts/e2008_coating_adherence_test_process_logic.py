#!/usr/bin/env python3
"""Full-face adherence check over the coating of a coverglass subgroup.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.9.2 -- the adherence check is applied
over the whole coverglass face of the samples of a subgroup. The procedure
below is a paraphrase into implementable steps; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the coverglass face: a positive width and height in millimetres.
2. Validate the applied zones: each a rectangle on that face, carrying the
   coating area that came away under it. A zone that runs off the face is an
   input error, because the operator either mis-measured it or applied the
   check to the mount rather than to the glass.
3. Reduce the zones to the exact area they cover, by compressing their own
   edge coordinates into a grid and adding only the cells a zone contains.
   Overlapping applications therefore contribute their shared area once, and
   the coverage never reads above the face.
4. Report the untested remainder of the face and compare the coverage with the
   full-face floor, so a check that left a corner unread is visible even when
   nothing came away where it was applied.
5. Reduce each sample to the coating area that came away, as a fraction of the
   whole face, and compare it with the removal limit.
6. Sentence the subgroup only when it carries enough samples and every sample
   is both fully covered and inside its removal limit.

Areas are in square millimetres, lengths in millimetres. Standard library
only, offline, deterministic.
"""

import math

__all__ = [
    "DEFAULT_UNTESTED_ALLOWANCE",
    "DEFAULT_MAX_REMOVED_FRACTION",
    "DEFAULT_MIN_SUBGROUP_SAMPLES",
    "AREA_TOLERANCE_REL",
    "SAMPLE_ACCEPTED",
    "SAMPLE_FACE_NOT_COVERED",
    "SAMPLE_COATING_REMOVED",
    "SUBGROUP_ACCEPTED",
    "SUBGROUP_REJECTED",
    "SUBGROUP_UNDERSIZED",
    "validate_face",
    "validate_zone",
    "validate_zones",
    "face_area",
    "zone_area",
    "union_area",
    "coverage_fraction",
    "removed_fraction",
    "assess_sample_face",
    "assess_subgroup_adherence",
]

# A check is applied by hand, so a sliver of the face at the very edge is
# tolerated; anything larger is an unread region and a finding.
DEFAULT_UNTESTED_ALLOWANCE = 0.02

# The share of the face whose coating may come away before the sample is
# sentenced. A declared project limit replaces it.
DEFAULT_MAX_REMOVED_FRACTION = 0.05

# A subgroup speaks for a lot only when it carries enough samples.
DEFAULT_MIN_SUBGROUP_SAMPLES = 4

# Coverage is a sum of products of declared dimensions, so a face that is
# exactly tiled by its zones can sum a few units in the last place either side
# of the face area. The comparisons absorb that rather than moving the floor.
AREA_TOLERANCE_REL = 1e-9

SAMPLE_ACCEPTED = "sample-adherence-accepted"
SAMPLE_FACE_NOT_COVERED = "sample-face-not-covered"
SAMPLE_COATING_REMOVED = "sample-coating-removed"

SUBGROUP_ACCEPTED = "subgroup-adherence-accepted"
SUBGROUP_REJECTED = "subgroup-adherence-rejected"
SUBGROUP_UNDERSIZED = "subgroup-undersized"

_ZONE_KEYS = ("x_mm", "y_mm", "width_mm", "height_mm", "removed_area_mm2")


def _real(value, label):
    """Return a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite" % label)
    return value


def _not_above(value, limit):
    """Return True when value does not exceed limit, boundary absorbed."""
    if math.isclose(value, limit, rel_tol=AREA_TOLERANCE_REL, abs_tol=0.0):
        return True
    return value < limit


def _reaches(value, target):
    """Return True when value reaches target, boundary absorbed."""
    if math.isclose(value, target, rel_tol=AREA_TOLERANCE_REL, abs_tol=0.0):
        return True
    return value > target


def validate_face(face):
    """Return the validated coverglass face dimensions."""
    if not isinstance(face, dict):
        raise ValueError("coverglass face must be a mapping")
    for key in ("width_mm", "height_mm"):
        if key not in face:
            raise ValueError("coverglass face is missing '%s'" % key)
    width = _real(face["width_mm"], "face width_mm")
    height = _real(face["height_mm"], "face height_mm")
    if width <= 0.0 or height <= 0.0:
        raise ValueError("coverglass face dimensions must be positive")
    return {"width_mm": width, "height_mm": height}


def face_area(face):
    """Return the area of the coverglass face."""
    face = validate_face(face)
    return face["width_mm"] * face["height_mm"]


def validate_zone(zone, index, face):
    """Return one validated applied zone, checked against the face it sits on."""
    face = validate_face(face)
    if not isinstance(zone, dict):
        raise ValueError("applied zone %d must be a mapping" % index)
    for key in _ZONE_KEYS:
        if key not in zone:
            raise ValueError("applied zone %d is missing '%s'" % (index, key))
    record = dict((key, _real(zone[key], "applied zone %d '%s'" % (index, key)))
                  for key in _ZONE_KEYS)
    if record["width_mm"] <= 0.0 or record["height_mm"] <= 0.0:
        raise ValueError("applied zone %d must have positive dimensions" % index)
    if record["x_mm"] < 0.0 or record["y_mm"] < 0.0:
        raise ValueError("applied zone %d starts outside the coverglass face" % index)
    if not _not_above(record["x_mm"] + record["width_mm"], face["width_mm"]):
        raise ValueError("applied zone %d runs off the face in width" % index)
    if not _not_above(record["y_mm"] + record["height_mm"], face["height_mm"]):
        raise ValueError("applied zone %d runs off the face in height" % index)
    area = record["width_mm"] * record["height_mm"]
    if record["removed_area_mm2"] < 0.0:
        raise ValueError("applied zone %d reports a negative removed area" % index)
    if not _not_above(record["removed_area_mm2"], area):
        raise ValueError(
            "applied zone %d reports %g mm2 removed from a zone of %g mm2"
            % (index, record["removed_area_mm2"], area)
        )
    record["index"] = index
    return record


def validate_zones(zones, face):
    """Return the validated list of applied zones."""
    if not isinstance(zones, (list, tuple)) or not zones:
        raise ValueError("a sample needs at least one applied zone")
    return [validate_zone(zone, i, face) for i, zone in enumerate(zones)]


def zone_area(zone):
    """Return the area of one applied zone."""
    if not isinstance(zone, dict):
        raise ValueError("applied zone must be a mapping")
    for key in ("width_mm", "height_mm"):
        if key not in zone:
            raise ValueError("applied zone is missing '%s'" % key)
    width = _real(zone["width_mm"], "zone width_mm")
    height = _real(zone["height_mm"], "zone height_mm")
    if width <= 0.0 or height <= 0.0:
        raise ValueError("applied zone must have positive dimensions")
    return width * height


def union_area(zones, face):
    """Return the exact area the applied zones cover, counting overlap once.

    The zone edges are compressed into a grid and a cell is added when any zone
    contains it, so two applications over the same patch of glass contribute
    their shared area once rather than twice.
    """
    rows = validate_zones(zones, face)
    xs = sorted(set([r["x_mm"] for r in rows] + [r["x_mm"] + r["width_mm"] for r in rows]))
    ys = sorted(set([r["y_mm"] for r in rows] + [r["y_mm"] + r["height_mm"] for r in rows]))
    cells = []
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        for j in range(len(ys) - 1):
            y0, y1 = ys[j], ys[j + 1]
            for row in rows:
                if (
                    row["x_mm"] <= x0
                    and x1 <= row["x_mm"] + row["width_mm"]
                    and row["y_mm"] <= y0
                    and y1 <= row["y_mm"] + row["height_mm"]
                ):
                    cells.append((x1 - x0) * (y1 - y0))
                    break
    return math.fsum(cells)


def coverage_fraction(zones, face):
    """Return the share of the coverglass face the applied zones reached."""
    return union_area(zones, face) / face_area(face)


def removed_fraction(zones, face):
    """Return the share of the coverglass face whose coating came away."""
    rows = validate_zones(zones, face)
    return math.fsum(row["removed_area_mm2"] for row in rows) / face_area(face)


def assess_sample_face(sample, index=0, untested_allowance=DEFAULT_UNTESTED_ALLOWANCE,
                       max_removed_fraction=DEFAULT_MAX_REMOVED_FRACTION):
    """Return the adherence accounting and verdict of one subgroup sample."""
    if not isinstance(sample, dict):
        raise ValueError("subgroup sample %d must be a mapping" % index)
    for key in ("sample_id", "face", "applied_zones"):
        if key not in sample:
            raise ValueError("subgroup sample %d is missing '%s'" % (index, key))
    sample_id = sample["sample_id"]
    if not isinstance(sample_id, str) or not sample_id.strip():
        raise ValueError("subgroup sample %d needs a non-empty sample_id" % index)
    allowance = _real(untested_allowance, "untested_allowance")
    if allowance < 0.0 or allowance >= 1.0:
        raise ValueError("untested_allowance must sit in [0, 1)")
    removal_limit = _real(max_removed_fraction, "max_removed_fraction")
    if removal_limit < 0.0 or removal_limit > 1.0:
        raise ValueError("max_removed_fraction must sit between 0 and 1")

    face = validate_face(sample["face"])
    rows = validate_zones(sample["applied_zones"], face)
    total = face_area(face)
    covered = union_area(rows, face)
    coverage = covered / total
    removed = math.fsum(row["removed_area_mm2"] for row in rows) / total
    floor = 1.0 - allowance

    findings = []
    covered_enough = _reaches(coverage, floor)
    if not covered_enough:
        findings.append(
            "sample %s was checked over %.4f of its coverglass face against a full-face "
            "floor of %.4f" % (sample_id.strip(), coverage, floor)
        )
    within_removal = _not_above(removed, removal_limit)
    if not within_removal:
        findings.append(
            "sample %s lost the coating over %.4f of its face against a limit of %.4f"
            % (sample_id.strip(), removed, removal_limit)
        )

    if not covered_enough:
        verdict = SAMPLE_FACE_NOT_COVERED
    elif not within_removal:
        verdict = SAMPLE_COATING_REMOVED
    else:
        verdict = SAMPLE_ACCEPTED

    return {
        "sample_id": sample_id.strip(),
        "face_area_mm2": total,
        "applied_area_mm2": math.fsum(zone_area(row) for row in rows),
        "tested_area_mm2": covered,
        "untested_area_mm2": total - covered,
        "coverage_fraction": coverage,
        "coverage_floor": floor,
        "removed_fraction": removed,
        "max_removed_fraction": removal_limit,
        "zone_count": len(rows),
        "verdict": verdict,
        "findings": findings,
    }


def assess_subgroup_adherence(spec):
    """Run the full clause 6.4.3.9.2 subgroup adherence check.

    spec keys: samples; optional untested_allowance, max_removed_fraction and
    min_subgroup_samples.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "samples" not in spec:
        raise ValueError("spec missing required key 'samples'")
    samples = spec["samples"]
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("the subgroup needs at least one sample")
    minimum = spec.get("min_subgroup_samples", DEFAULT_MIN_SUBGROUP_SAMPLES)
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
        raise ValueError("min_subgroup_samples must be a positive integer")
    allowance = spec.get("untested_allowance", DEFAULT_UNTESTED_ALLOWANCE)
    removal_limit = spec.get("max_removed_fraction", DEFAULT_MAX_REMOVED_FRACTION)

    results = []
    findings = []
    seen = set()
    for index, sample in enumerate(samples):
        accounting = assess_sample_face(sample, index, allowance, removal_limit)
        if accounting["sample_id"] in seen:
            raise ValueError("duplicate sample_id in the subgroup: %s" % accounting["sample_id"])
        seen.add(accounting["sample_id"])
        findings.extend(accounting["findings"])
        results.append(accounting)

    if len(results) < minimum:
        verdict = SUBGROUP_UNDERSIZED
        findings.insert(
            0,
            "the subgroup carries %d samples against a floor of %d" % (len(results), minimum),
        )
    elif any(r["verdict"] != SAMPLE_ACCEPTED for r in results):
        verdict = SUBGROUP_REJECTED
    else:
        verdict = SUBGROUP_ACCEPTED

    return {
        "verdict": verdict,
        "sample_count": len(results),
        "min_subgroup_samples": minimum,
        "coverage_floor": 1.0 - _real(allowance, "untested_allowance"),
        "max_removed_fraction": _real(removal_limit, "max_removed_fraction"),
        "worst_coverage_fraction": min(r["coverage_fraction"] for r in results),
        "worst_removed_fraction": max(r["removed_fraction"] for r in results),
        "samples": results,
        "findings": findings,
    }
