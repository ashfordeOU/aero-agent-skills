#!/usr/bin/env python3
"""Density and porosity control for additively manufactured material.

Anchor: ECSS-Q-ST-70-80 quality clause on controlling the density and the
porosity of parts made by additive manufacturing. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

What the clause actually decides
--------------------------------
Bulk density and pore size are two different requirements on the same
material and they fail separately:

bulk density   the buoyancy measurement gives a density for the whole part.
               Expressed against the reference density of the wrought alloy
               it is a relative density, and one minus it is the porosity
               the part carries.
pore size      a part can sit comfortably above its relative-density floor
               and still hold one lack-of-fusion defect long enough to be
               the critical flaw. The size limit is graded separately, and
               on a thin wall it is the wall that sets it, not the drawing.
inspection     a tomography scan whose detection limit is coarser than the
               size limit it is meant to grade cannot find the defect it is
               looking for. A clean scan is then silence, not evidence.
agreement      buoyancy and a sectioned micrograph count different porosity.
               A disagreement between them beyond the declared tolerance is
               a measurement finding, not a rounding difference.

The verdict is the worst of the four and the driving characteristic is
named.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

VERDICT_ACCEPT = "accept"
VERDICT_REVIEW = "review"
VERDICT_REJECT = "reject"

_VERDICT_RANK = {VERDICT_ACCEPT: 0, VERDICT_REVIEW: 1, VERDICT_REJECT: 2}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12

UM_PER_MM = 1000.0

# A part reading denser than the reference by more than this is not a dense
# part; the reference or the weighing is wrong.
REFERENCE_OVERSHOOT_FRACTION = 0.005


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_count(name, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(verdicts):
    worst = VERDICT_ACCEPT
    for verdict in verdicts:
        if _VERDICT_RANK[verdict] > _VERDICT_RANK[worst]:
            worst = verdict
    return worst


def archimedes_density(dry_mass_g, suspended_mass_g, fluid_density_g_cm3):
    """Bulk density from a dry and a suspended weighing, in g/cm3."""
    dry = _require_positive("dry_mass_g", dry_mass_g)
    suspended = _require_positive("suspended_mass_g", suspended_mass_g)
    fluid = _require_positive("fluid_density_g_cm3", fluid_density_g_cm3)
    if not dry > suspended:
        raise ValueError(
            "suspended mass %.4f g is not below the dry mass %.4f g; the "
            "buoyancy measurement is not usable" % (suspended, dry)
        )
    return dry / (dry - suspended) * fluid


def relative_density(measured_g_cm3, reference_g_cm3):
    """Measured bulk density as a fraction of the reference alloy density."""
    measured = _require_positive("measured_g_cm3", measured_g_cm3)
    reference = _require_positive("reference_g_cm3", reference_g_cm3)
    fraction = measured / reference
    if not _at_most(fraction, 1.0 + REFERENCE_OVERSHOOT_FRACTION):
        raise ValueError(
            "measured density %.4f g/cm3 is %.2f%% above the %.4f g/cm3 "
            "reference; the reference or the weighing is wrong, not the part"
            % (measured, (fraction - 1.0) * 100.0, reference)
        )
    return fraction


def grade_relative_density(fraction, minimum_fraction, review_margin=0.002):
    """Grade a relative density against its floor, flagging a thin margin."""
    value = _require_positive("fraction", fraction)
    floor = _require_positive("minimum_fraction", minimum_fraction)
    margin = _require_non_negative("review_margin", review_margin)
    if floor > 1.0:
        raise ValueError("minimum_fraction must not exceed 1.0, got %r" % (floor,))
    findings = []
    if not _at_least(value, floor):
        verdict = VERDICT_REJECT
        findings.append(
            "relative density %.5f is below the %.5f floor, so the part "
            "carries %.3f%% porosity" % (value, floor, (1.0 - value) * 100.0)
        )
    elif not _at_least(value, floor + margin):
        verdict = VERDICT_REVIEW
        findings.append(
            "relative density %.5f sits inside %.5f of the floor; the build "
            "has no density margin left" % (value, margin)
        )
    else:
        verdict = VERDICT_ACCEPT
    return {
        "relative_density": value,
        "porosity_fraction": 1.0 - value,
        "minimum_fraction": floor,
        "verdict": verdict,
        "findings": findings,
    }


def governing_pore_limit(absolute_limit_um, wall_thickness_mm, max_wall_fraction):
    """Smaller of the drawing pore limit and the wall-fraction limit, in um."""
    absolute = _require_positive("absolute_limit_um", absolute_limit_um)
    wall = _require_positive("wall_thickness_mm", wall_thickness_mm)
    fraction = _require_positive("max_wall_fraction", max_wall_fraction)
    if fraction > 1.0:
        raise ValueError("max_wall_fraction must not exceed 1.0, got %r" % (fraction,))
    wall_limit = wall * UM_PER_MM * fraction
    if wall_limit < absolute:
        return {"limit_um": wall_limit, "governed_by": "wall-fraction"}
    return {"limit_um": absolute, "governed_by": "drawing"}


def grade_pore_size(largest_pore_um, absolute_limit_um, wall_thickness_mm,
                    max_wall_fraction):
    """Grade the largest pore against whichever limit governs it."""
    largest = _require_non_negative("largest_pore_um", largest_pore_um)
    governing = governing_pore_limit(
        absolute_limit_um, wall_thickness_mm, max_wall_fraction
    )
    findings = []
    acceptable = _at_most(largest, governing["limit_um"])
    if not acceptable:
        findings.append(
            "largest pore %.1f um exceeds the %.1f um limit set by the %s"
            % (largest, governing["limit_um"], governing["governed_by"])
        )
    return {
        "largest_pore_um": largest,
        "limit_um": governing["limit_um"],
        "governed_by": governing["governed_by"],
        "verdict": VERDICT_ACCEPT if acceptable else VERDICT_REJECT,
        "findings": findings,
    }


def ct_pore_population(pore_diameters_um, detection_limit_um, size_limit_um,
                       max_indications):
    """Grade a tomography pore population, and the scan that produced it.

    A scan whose detection limit is coarser than the size limit it grades
    cannot see the defect it is looking for, so a clean result from it is
    silence rather than evidence.
    """
    if not isinstance(pore_diameters_um, (list, tuple)):
        raise ValueError("pore_diameters_um must be a sequence")
    detection = _require_positive("detection_limit_um", detection_limit_um)
    size_limit = _require_positive("size_limit_um", size_limit_um)
    allowed = _require_count("max_indications", max_indications, minimum=0)
    diameters = [
        _require_non_negative("pore %d" % index, value)
        for index, value in enumerate(pore_diameters_um)
    ]
    resolved = [value for value in diameters if _at_least(value, detection)]
    oversize = [value for value in resolved if not _at_most(value, size_limit)]
    findings = []
    verdicts = [VERDICT_ACCEPT]
    if not _at_most(detection, size_limit):
        verdicts.append(VERDICT_REJECT)
        findings.append(
            "the scan resolves %.1f um while the size limit is %.1f um; it "
            "cannot see the defect it is meant to grade"
            % (detection, size_limit)
        )
    if oversize:
        verdicts.append(VERDICT_REJECT)
        findings.append(
            "%d indication(s) above the %.1f um size limit, largest %.1f um"
            % (len(oversize), size_limit, max(oversize))
        )
    if len(resolved) > allowed:
        verdicts.append(VERDICT_REVIEW)
        findings.append(
            "%d resolved indications against the %d allowed; the population "
            "has moved even where each pore is inside the size limit"
            % (len(resolved), allowed)
        )
    return {
        "resolved_count": len(resolved),
        "oversize_count": len(oversize),
        "largest_resolved_um": max(resolved) if resolved else 0.0,
        "below_detection_count": len(diameters) - len(resolved),
        "verdict": _worst(verdicts),
        "findings": findings,
    }


def method_agreement(buoyancy_fraction, sectioned_fraction, tolerance):
    """Grade buoyancy relative density against the sectioned micrograph value."""
    buoyancy = _require_positive("buoyancy_fraction", buoyancy_fraction)
    sectioned = _require_positive("sectioned_fraction", sectioned_fraction)
    band = _require_non_negative("tolerance", tolerance)
    difference = abs(buoyancy - sectioned)
    findings = []
    acceptable = _at_most(difference, band)
    if not acceptable:
        findings.append(
            "buoyancy reads %.5f and the section reads %.5f, a %.5f gap beyond "
            "the %.5f tolerance; surface-connected porosity is counted "
            "differently by the two methods"
            % (buoyancy, sectioned, difference, band)
        )
    return {
        "difference": difference,
        "tolerance": band,
        "verdict": VERDICT_ACCEPT if acceptable else VERDICT_REVIEW,
        "findings": findings,
    }


def assess_density_and_porosity(case):
    """Full density and porosity verdict for one part or build."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    measured = archimedes_density(
        case.get("dry_mass_g"),
        case.get("suspended_mass_g"),
        case.get("fluid_density_g_cm3"),
    )
    fraction = relative_density(measured, case.get("reference_density_g_cm3"))
    density = grade_relative_density(
        fraction,
        case.get("minimum_relative_density"),
        case.get("density_review_margin", 0.002),
    )
    pores = grade_pore_size(
        case.get("largest_pore_um"),
        case.get("pore_limit_um"),
        case.get("wall_thickness_mm"),
        case.get("max_pore_wall_fraction"),
    )
    population = ct_pore_population(
        case.get("ct_pore_diameters_um", []),
        case.get("ct_detection_limit_um"),
        case.get("pore_limit_um"),
        case.get("max_indications", 0),
    )
    parts = {"relative-density": density, "pore-size": pores, "pore-population": population}
    findings = []
    findings.extend("relative-density: %s" % text for text in density["findings"])
    findings.extend("pore-size: %s" % text for text in pores["findings"])
    findings.extend("pore-population: %s" % text for text in population["findings"])
    agreement = None
    if case.get("sectioned_relative_density") is not None:
        agreement = method_agreement(
            fraction,
            case.get("sectioned_relative_density"),
            case.get("method_tolerance", 0.003),
        )
        parts["method-agreement"] = agreement
        findings.extend("method-agreement: %s" % text for text in agreement["findings"])
    verdict = _worst(part["verdict"] for part in parts.values())
    driving = sorted(
        name
        for name, part in parts.items()
        if _VERDICT_RANK[part["verdict"]] == _VERDICT_RANK[verdict]
        and verdict != VERDICT_ACCEPT
    )
    return {
        "verdict": verdict,
        "driving_characteristics": driving,
        "measured_density_g_cm3": measured,
        "relative_density": density,
        "pore_size": pores,
        "pore_population": population,
        "method_agreement": agreement,
        "findings": findings,
    }
