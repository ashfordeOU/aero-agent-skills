#!/usr/bin/env python3
"""Cleanliness and contamination effects of a sterilization process.

Anchor: ECSS-Q-ST-70-53C, evaluation clauses covering the cleanliness effect
of the process on the exposed material or hardware. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the particle size distribution and the inspected area.
2. Convert the distribution into an obscuration percentage: the projected area
   of the counted particles over the area actually inspected.
3. Place the obscuration figure in the tightest declared cleanliness band
   whose ceiling it still meets; a figure dirtier than the coarsest ceiling
   has no band.
4. Compare the post-exposure band with the required level by their ceilings.
5. Take the process-attributable non-volatile-residue increase as the
   post-exposure surface density minus the pre-exposure one, floored at zero.
6. Grade the increase against its allocation and the post-exposure total
   against the surface requirement, independently.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "BAND_TOLERANCE",
    "DEFAULT_CLEANLINESS_BANDS",
    "validate_area_cm2",
    "validate_distribution",
    "projected_area_um2",
    "obscuration_percent",
    "validate_bands",
    "cleanliness_band",
    "band_ceiling",
    "band_meets_requirement",
    "residue_increase",
    "assess_contamination_effects",
]

# Band placement compares a computed area fraction with a tabulated ceiling: an
# exact equality can land a few ULPs on the wrong side. Absorb the
# representation error here instead of loosening the tabulated ceiling.
BAND_TOLERANCE = 1e-12

# Declared product-cleanliness bands, tightest first, as (name, obscuration
# percentage ceiling). The caller may substitute a project-specific table; this
# one is only the default used when none is supplied.
DEFAULT_CLEANLINESS_BANDS = (
    ("level-100", 0.0001),
    ("level-300", 0.0025),
    ("level-500", 0.0250),
    ("level-750", 0.1300),
    ("level-1000", 0.3400),
)

_SQUARE_MICROMETRES_PER_SQUARE_CENTIMETRE = 1.0e8


def _real(value, label):
    """Return value as a finite float, or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def validate_area_cm2(area_cm2):
    """Return the validated inspected area in square centimetres."""
    area = _real(area_cm2, "inspected_area_cm2")
    if area <= 0.0:
        raise ValueError("inspected_area_cm2 must be positive, got %g" % area)
    return area


def validate_distribution(distribution):
    """Return a normalised list of (diameter_um, count) bins."""
    if not isinstance(distribution, (list, tuple)):
        raise ValueError("distribution must be a sequence of size bins")
    bins = []
    for index, item in enumerate(distribution):
        if isinstance(item, dict):
            if "diameter_um" not in item or "count" not in item:
                raise ValueError(
                    "distribution[%d] needs 'diameter_um' and 'count'" % index
                )
            diameter, count = item["diameter_um"], item["count"]
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            diameter, count = item
        else:
            raise ValueError(
                "distribution[%d] must be a mapping or a (diameter_um, count) pair"
                % index
            )
        diameter = _real(diameter, "distribution[%d] diameter_um" % index)
        if diameter <= 0.0:
            raise ValueError(
                "distribution[%d] diameter_um must be positive, got %g" % (index, diameter)
            )
        if not isinstance(count, int) or isinstance(count, bool):
            raise ValueError("distribution[%d] count must be an integer" % index)
        if count < 0:
            raise ValueError(
                "distribution[%d] count must be non-negative, got %d" % (index, count)
            )
        bins.append((diameter, count))
    return bins


def projected_area_um2(distribution):
    """Return the total projected area of the counted particles, in um^2."""
    bins = validate_distribution(distribution)
    total = 0.0
    for diameter, count in bins:
        total += count * math.pi * diameter * diameter / 4.0
    return total


def obscuration_percent(distribution, inspected_area_cm2):
    """Return the obscuration of the inspected area, as a percentage."""
    area = validate_area_cm2(inspected_area_cm2)
    projected = projected_area_um2(distribution)
    inspected_um2 = area * _SQUARE_MICROMETRES_PER_SQUARE_CENTIMETRE
    return 100.0 * projected / inspected_um2


def validate_bands(bands=None):
    """Return the cleanliness band table, tightest first, as (name, ceiling)."""
    table = DEFAULT_CLEANLINESS_BANDS if bands is None else bands
    if not isinstance(table, (list, tuple)) or len(table) < 2:
        raise ValueError("band table needs at least two (name, ceiling) entries")
    out = []
    for index, item in enumerate(table):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("band[%d] must be a (name, ceiling) pair" % index)
        name, ceiling = item
        if not isinstance(name, str) or not name.strip():
            raise ValueError("band[%d] name must be a non-empty string" % index)
        ceiling = _real(ceiling, "band[%d] ceiling" % index)
        if ceiling <= 0.0:
            raise ValueError("band[%d] ceiling must be positive, got %g" % (index, ceiling))
        out.append((name.strip(), ceiling))
    for index in range(1, len(out)):
        if out[index][1] <= out[index - 1][1]:
            raise ValueError(
                "band ceilings must strictly increase, tightest first (index %d)" % index
            )
    return out


def band_ceiling(name, bands=None):
    """Return the obscuration ceiling of a named band."""
    for band_name, ceiling in validate_bands(bands):
        if band_name == name:
            return ceiling
    raise ValueError("unknown cleanliness band %r" % (name,))


def cleanliness_band(obscuration, bands=None):
    """Return the tightest band the obscuration figure meets, or None."""
    value = _real(obscuration, "obscuration")
    if value < 0.0:
        raise ValueError("obscuration must be non-negative, got %g" % value)
    for name, ceiling in validate_bands(bands):
        if value < ceiling or math.isclose(value, ceiling, rel_tol=BAND_TOLERANCE, abs_tol=0.0):
            return name
    return None


def band_meets_requirement(achieved, required, bands=None):
    """Return True when the achieved band is no looser than the required one."""
    if achieved is None:
        return False
    achieved_ceiling = band_ceiling(achieved, bands)
    required_ceiling = band_ceiling(required, bands)
    return achieved_ceiling < required_ceiling or math.isclose(
        achieved_ceiling, required_ceiling, rel_tol=BAND_TOLERANCE, abs_tol=0.0
    )


def residue_increase(pre_mg_m2, post_mg_m2):
    """Return the process-attributable residue increase, floored at zero."""
    pre = _real(pre_mg_m2, "pre_mg_m2")
    post = _real(post_mg_m2, "post_mg_m2")
    if pre < 0.0:
        raise ValueError("pre_mg_m2 must be non-negative, got %g" % pre)
    if post < 0.0:
        raise ValueError("post_mg_m2 must be non-negative, got %g" % post)
    return max(0.0, post - pre)


def assess_contamination_effects(spec):
    """Run the full ECSS-Q-ST-70-53C cleanliness-effect evaluation.

    spec keys: inspected_area_cm2, pre_distribution, post_distribution,
    required_level, pre_nvr_mg_m2, post_nvr_mg_m2, nvr_allocation_mg_m2,
    nvr_requirement_mg_m2, optional bands.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "inspected_area_cm2",
        "pre_distribution",
        "post_distribution",
        "required_level",
        "pre_nvr_mg_m2",
        "post_nvr_mg_m2",
        "nvr_allocation_mg_m2",
        "nvr_requirement_mg_m2",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    bands = validate_bands(spec.get("bands"))
    area = validate_area_cm2(spec["inspected_area_cm2"])
    pre_obscuration = obscuration_percent(spec["pre_distribution"], area)
    post_obscuration = obscuration_percent(spec["post_distribution"], area)
    pre_band = cleanliness_band(pre_obscuration, bands)
    post_band = cleanliness_band(post_obscuration, bands)
    required_level = spec["required_level"]
    required_ceiling = band_ceiling(required_level, bands)
    level_met = band_meets_requirement(post_band, required_level, bands)

    allocation = _real(spec["nvr_allocation_mg_m2"], "nvr_allocation_mg_m2")
    if allocation < 0.0:
        raise ValueError("nvr_allocation_mg_m2 must be non-negative")
    requirement = _real(spec["nvr_requirement_mg_m2"], "nvr_requirement_mg_m2")
    if requirement <= 0.0:
        raise ValueError("nvr_requirement_mg_m2 must be positive")
    added = residue_increase(spec["pre_nvr_mg_m2"], spec["post_nvr_mg_m2"])
    total = _real(spec["post_nvr_mg_m2"], "post_nvr_mg_m2")
    within_allocation = added < allocation or math.isclose(
        added, allocation, rel_tol=BAND_TOLERANCE, abs_tol=0.0
    )
    within_requirement = total < requirement or math.isclose(
        total, requirement, rel_tol=BAND_TOLERANCE, abs_tol=0.0
    )

    findings = []
    if post_band is None:
        findings.append(
            "post-exposure obscuration %.6f %% is dirtier than the coarsest tabulated band"
            % post_obscuration
        )
    elif not level_met:
        findings.append(
            "post-exposure cleanliness band '%s' is looser than the required '%s'"
            % (post_band, required_level)
        )
    if not within_allocation:
        findings.append(
            "process added %.4f mg/m2 of residue against an allocation of %.4f mg/m2"
            % (added, allocation)
        )
    if not within_requirement:
        findings.append(
            "post-exposure residue %.4f mg/m2 exceeds the surface requirement %.4f mg/m2"
            % (total, requirement)
        )
    return {
        "inspected_area_cm2": area,
        "pre_obscuration_percent": pre_obscuration,
        "post_obscuration_percent": post_obscuration,
        "obscuration_increase_percent": max(0.0, post_obscuration - pre_obscuration),
        "pre_band": pre_band,
        "post_band": post_band,
        "required_level": required_level,
        "required_ceiling_percent": required_ceiling,
        "level_met": level_met,
        "residue_added_mg_m2": added,
        "residue_total_mg_m2": total,
        "within_allocation": within_allocation,
        "within_requirement": within_requirement,
        "acceptable": level_met and within_allocation and within_requirement,
        "findings": findings,
    }
