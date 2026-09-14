"""Bare solar cell pull test: contact bond strength after environmental loading.

Anchor: ECSS-E-ST-20-08C clause 7.5.12 (bond strength of the front and rear
contacts of a bare solar cell, assessed under mechanical loading applied on top
of environmental loading). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Check the environmental block the lot owes -- the thermal cycles and the
   humidity soak -- was completed, and completed BEFORE any contact was pulled,
   because a bond pulled first reports the as-built joint rather than the joint
   the environment leaves behind.
2. Resolve every recorded pull onto the contact normal. A pull dragged off the
   normal puts part of the force into peel and shear, so the number recorded by
   the machine is not the number the bond carried; a pull too far off normal is
   rejected rather than corrected.
3. Turn the normal force and the bonded contact area into a bond strength, so
   contacts of different footprint can be compared against one requirement.
4. Sentence every cell by its weakest of the two sites, front contact and rear
   contact, since a cell is only as strong as the contact that lets go first.
5. Check the lot was sampled: fewer cells pulled than the plan carries, or a
   planned cell never pulled, means the lot was sentenced from a partial run.
6. Report per-site strengths, the per-cell weakest site, the lot spread, every
   finding and the lot verdict; the lot is conformant only with no finding.
"""

import math

__all__ = [
    "STRENGTH_TOLERANCE",
    "SITES",
    "MAX_OFF_NORMAL_DEG",
    "MIN_SAMPLE_CELLS",
    "validate_conditioning",
    "conditioning_findings",
    "sequence_findings",
    "normal_pull_force_n",
    "bond_strength_mpa",
    "evaluate_site",
    "evaluate_cell",
    "lot_statistics",
    "sample_findings",
    "assess_bare_cell_pull_test",
]

# A strength or an angle sitting exactly on a declared bound is conformant; the
# comparison absorbs representation error and the bound itself never moves.
STRENGTH_TOLERANCE = 1e-9

# The two contact sites the clause puts a bond strength on.
SITES = ("front-contact", "rear-contact")

# Beyond this much off the contact normal the recorded force is part peel and
# part shear, and no bond strength can be read out of it.
MAX_OFF_NORMAL_DEG = 5.0

# Below this many cells the spread of a lot cannot be seen at all.
MIN_SAMPLE_CELLS = 3


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, number))
    return number


def _non_negative(value, label):
    """Return value as a non-negative finite float."""
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, number))
    return number


def _count(value, label):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _name(value, label):
    """Return a trimmed, non-empty identifier string."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ValueError("%s must not be empty" % label)
    return cleaned


def validate_conditioning(thermal_cycles, humidity_soak_hours):
    """Return the validated (cycles, soak hours) the lot actually received."""
    cycles = _count(thermal_cycles, "thermal_cycles")
    soak = _non_negative(humidity_soak_hours, "humidity_soak_hours")
    return (cycles, soak)


def conditioning_findings(received, required):
    """Return findings where the environmental block fell short of the plan."""
    cycles, soak = validate_conditioning(received[0], received[1])
    need_cycles, need_soak = validate_conditioning(required[0], required[1])
    findings = []
    if cycles < need_cycles:
        findings.append(
            "the lot saw %d thermal cycles, under the %d the plan carries"
            % (cycles, need_cycles)
        )
    if soak < need_soak - STRENGTH_TOLERANCE:
        findings.append(
            "the lot soaked for %g h, under the %g h the plan carries"
            % (soak, need_soak)
        )
    return findings


def sequence_findings(steps):
    """Return findings where the pull did not follow the environmental block."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("steps must be a non-empty sequence of run steps")
    kinds = []
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError("each run step must be a mapping")
        for key in ("step", "kind"):
            if key not in step:
                raise ValueError("run step missing key '%s'" % key)
        label = _name(step["step"], "step")
        kind = _name(step["kind"], "kind").lower()
        if kind not in ("environmental", "mechanical"):
            raise ValueError(
                "step '%s' kind must be environmental or mechanical, got '%s'"
                % (label, kind)
            )
        kinds.append((label, kind))
    pulls = [index for index, item in enumerate(kinds) if item[1] == "mechanical"]
    findings = []
    if not pulls:
        return ["the run carries no mechanical pull step at all"]
    first_pull = pulls[0]
    if not any(kind == "environmental" for _, kind in kinds[:first_pull]):
        findings.append(
            "pull step '%s' runs before any environmental step, so it reads the "
            "as-built bond" % kinds[first_pull][0]
        )
    for label, kind in kinds[first_pull + 1:]:
        if kind == "environmental":
            findings.append(
                "environmental step '%s' runs after the pull, so its loading "
                "never reached the bond that was pulled" % label
            )
    return findings


def normal_pull_force_n(force_n, off_normal_deg):
    """Return the component of a recorded pull that acts along the normal."""
    force = _positive(force_n, "force_n")
    angle = _non_negative(off_normal_deg, "off_normal_deg")
    if angle >= 90.0:
        raise ValueError(
            "off_normal_deg must be under 90, got %g" % angle
        )
    return force * math.cos(math.radians(angle))


def bond_strength_mpa(force_n, area_mm2):
    """Return the bond strength a normal force over a bonded area represents."""
    force = _positive(force_n, "force_n")
    area = _positive(area_mm2, "area_mm2")
    return force / area


def evaluate_site(reading, areas, minimum_mpa,
                  max_off_normal_deg=MAX_OFF_NORMAL_DEG):
    """Return the strength and findings of one contact site of one cell."""
    if not isinstance(reading, dict):
        raise ValueError("each site reading must be a mapping")
    for key in ("site", "force_n", "off_normal_deg"):
        if key not in reading:
            raise ValueError("site reading missing key '%s'" % key)
    site = _name(reading["site"], "site")
    if site not in SITES:
        raise ValueError(
            "site must be one of %s, got '%s'" % (", ".join(SITES), site)
        )
    if not isinstance(areas, dict) or site not in areas:
        raise ValueError("no bonded area declared for site '%s'" % site)
    limit = _non_negative(max_off_normal_deg, "max_off_normal_deg")
    if limit >= 90.0:
        raise ValueError("max_off_normal_deg must be under 90, got %g" % limit)
    floor = _positive(minimum_mpa, "minimum_mpa")
    angle = _non_negative(reading["off_normal_deg"], "off_normal_deg")
    area = _positive(areas[site], "area_mm2")
    findings = []
    if angle > limit + STRENGTH_TOLERANCE:
        findings.append(
            "site '%s' was pulled %g deg off normal, over the %g deg allowance"
            % (site, angle, limit)
        )
    normal = normal_pull_force_n(reading["force_n"], angle)
    strength = bond_strength_mpa(normal, area)
    if strength < floor - STRENGTH_TOLERANCE:
        findings.append(
            "site '%s' held %.4g MPa, under the %.4g MPa the bond owes"
            % (site, strength, floor)
        )
    return {
        "site": site,
        "normal_force_n": normal,
        "area_mm2": area,
        "strength_mpa": strength,
        "off_normal_deg": angle,
        "findings": findings,
        "site_conformant": not findings,
    }


def evaluate_cell(record, areas, minimum_mpa,
                  max_off_normal_deg=MAX_OFF_NORMAL_DEG):
    """Return the per-site results and the weakest site of one bare cell."""
    if not isinstance(record, dict):
        raise ValueError("each cell record must be a mapping")
    for key in ("cell", "sites"):
        if key not in record:
            raise ValueError("cell record missing key '%s'" % key)
    cell = _name(record["cell"], "cell")
    readings = record["sites"]
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError("cell '%s' carries no site readings" % cell)
    results = []
    seen = []
    for reading in readings:
        result = evaluate_site(reading, areas, minimum_mpa, max_off_normal_deg)
        if result["site"] in seen:
            raise ValueError(
                "cell '%s' carries two readings for site '%s'"
                % (cell, result["site"])
            )
        seen.append(result["site"])
        results.append(result)
    findings = []
    for site in SITES:
        if site not in seen:
            findings.append(
                "cell '%s' was never pulled at its %s" % (cell, site)
            )
    for result in results:
        for item in result["findings"]:
            findings.append("cell '%s': %s" % (cell, item))
    weakest = min(results, key=lambda item: item["strength_mpa"])
    return {
        "cell": cell,
        "sites": results,
        "weakest_site": weakest["site"],
        "weakest_strength_mpa": weakest["strength_mpa"],
        "findings": findings,
        "cell_conformant": not findings,
    }


def lot_statistics(values):
    """Return the mean, spread, lowest and highest of a lot's strengths."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("values must be a non-empty sequence of strengths")
    numbers = [_positive(value, "strength_mpa") for value in values]
    count = len(numbers)
    mean = sum(numbers) / count
    if count > 1:
        variance = sum((value - mean) ** 2 for value in numbers) / (count - 1)
    else:
        variance = 0.0
    return {
        "count": count,
        "mean_mpa": mean,
        "spread_mpa": math.sqrt(variance),
        "lowest_mpa": min(numbers),
        "highest_mpa": max(numbers),
    }


def sample_findings(planned_cells, pulled_cells,
                    min_sample_cells=MIN_SAMPLE_CELLS):
    """Return findings where the lot was sentenced from a partial sample."""
    for label, value in (("planned_cells", planned_cells),
                         ("pulled_cells", pulled_cells)):
        if not isinstance(value, (list, tuple)):
            raise ValueError("%s must be a sequence of cell names" % label)
    minimum = _count(min_sample_cells, "min_sample_cells")
    if minimum < 1:
        raise ValueError("min_sample_cells must be at least 1")
    planned = [_name(item, "planned cell") for item in planned_cells]
    pulled = [_name(item, "pulled cell") for item in pulled_cells]
    if not planned:
        raise ValueError("planned_cells must name at least one cell")
    findings = []
    for cell in planned:
        if cell not in pulled:
            findings.append("planned cell '%s' was never pulled" % cell)
    for cell in sorted({item for item in pulled if item not in planned}):
        findings.append("cell '%s' was pulled but is not on the plan" % cell)
    for cell in sorted({item for item in pulled if pulled.count(item) > 1}):
        findings.append(
            "cell '%s' carries two pull records, so its result is ambiguous"
            % cell
        )
    if len(pulled) < minimum:
        findings.append(
            "only %d cells were pulled, under the %d a lot spread needs"
            % (len(pulled), minimum)
        )
    return findings


def assess_bare_cell_pull_test(spec):
    """Run the full clause 7.5.12 bare-cell contact pull assessment.

    spec keys: planned_cells, cell_records (cell, sites), contact_areas_mm2,
    minimum_strength_mpa, conditioning_received (cycles, soak hours),
    conditioning_required (cycles, soak hours), run_sequence; optional
    max_off_normal_deg, min_sample_cells.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "planned_cells",
        "cell_records",
        "contact_areas_mm2",
        "minimum_strength_mpa",
        "conditioning_received",
        "conditioning_required",
        "run_sequence",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    records = spec["cell_records"]
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("cell_records must be a non-empty sequence")
    for label in ("conditioning_received", "conditioning_required"):
        pair = spec[label]
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError(
                "%s must be a (thermal_cycles, humidity_soak_hours) pair" % label
            )

    findings = list(
        conditioning_findings(
            spec["conditioning_received"], spec["conditioning_required"]
        )
    )
    findings.extend(sequence_findings(spec["run_sequence"]))
    findings.extend(
        sample_findings(
            spec["planned_cells"],
            [record["cell"] for record in records],
            spec.get("min_sample_cells", MIN_SAMPLE_CELLS),
        )
    )

    cells = []
    for record in records:
        result = evaluate_cell(
            record,
            spec["contact_areas_mm2"],
            spec["minimum_strength_mpa"],
            spec.get("max_off_normal_deg", MAX_OFF_NORMAL_DEG),
        )
        cells.append(result)
        findings.extend(result["findings"])
    statistics = lot_statistics(
        [cell["weakest_strength_mpa"] for cell in cells]
    )
    return {
        "cells": cells,
        "statistics": statistics,
        "pulled_count": len(cells),
        "planned_count": len(spec["planned_cells"]),
        "findings": findings,
        "lot_conformant": not findings,
    }
