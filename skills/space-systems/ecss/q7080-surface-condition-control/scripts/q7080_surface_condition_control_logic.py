#!/usr/bin/env python3
"""Surface condition control for additively manufactured parts.

Anchor: ECSS-Q-ST-70-80 quality clause on controlling the surface condition
of parts made by additive manufacturing. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

What the clause actually decides
--------------------------------
An additive surface is not one surface. The same parameter set leaves a
different finish on a vertical wall, on an up-facing skin and on a shallow
down-skin, and the specification has to be read against the surface it
applies to. Four things decide it:

parameter      an Ra limit and an Rz reading are different quantities. A
               comparison between them is a category error that passes and
               fails surfaces at random.
readings       every reading on a surface is graded, not their mean. One
               shallow overhang in the middle of a face is exactly what a
               mean hides.
achievability  below a threshold overhang angle the as-built roughness grows
               with the angle. A limit below what the process leaves at that
               angle is not a failed surface, it is a requirement that needs
               a finishing operation or a support change declared.
condition      partly fused particles adhering to the surface are graded per
               unit area, because the same count on a small face and a large
               one are different results.

The verdict is the worst over every declared surface, and the surfaces
sitting at that level are named.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SURFACE_CATEGORIES = (
    "up-skin",
    "down-skin",
    "vertical-wall",
    "machined",
    "polished",
)

# Categories whose finish is produced by the build rather than by a cut, so
# the as-built roughness model applies to them.
AS_BUILT_CATEGORIES = ("up-skin", "down-skin", "vertical-wall")

ROUGHNESS_PARAMETERS = ("Ra", "Rz")

VERDICT_ACCEPT = "accept"
VERDICT_REVIEW = "review"
VERDICT_REJECT = "reject"

_VERDICT_RANK = {VERDICT_ACCEPT: 0, VERDICT_REVIEW: 1, VERDICT_REJECT: 2}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12

DEFAULT_DOWNSKIN_THRESHOLD_DEG = 45.0
DEFAULT_DOWNSKIN_GROWTH_FACTOR = 1.5


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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


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


def expected_as_built_ra(vertical_ra_um, overhang_angle_deg,
                         threshold_deg=DEFAULT_DOWNSKIN_THRESHOLD_DEG,
                         growth_factor=DEFAULT_DOWNSKIN_GROWTH_FACTOR):
    """Roughness the process leaves at an overhang angle, in micrometres.

    The angle is measured from the build plate: 90 degrees is a vertical
    wall, 0 degrees is a horizontal down-skin. Above the threshold the finish
    is the vertical-wall value; below it the unsupported melt sags into the
    powder beneath and the roughness grows as the angle falls.
    """
    baseline = _require_positive("vertical_ra_um", vertical_ra_um)
    angle = _require_non_negative("overhang_angle_deg", overhang_angle_deg)
    threshold = _require_positive("threshold_deg", threshold_deg)
    growth = _require_non_negative("growth_factor", growth_factor)
    if angle > 90.0:
        raise ValueError(
            "overhang_angle_deg is measured from the build plate and cannot "
            "exceed 90, got %r" % (overhang_angle_deg,)
        )
    if threshold > 90.0:
        raise ValueError("threshold_deg cannot exceed 90, got %r" % (threshold_deg,))
    if angle >= threshold:
        return baseline
    return baseline * (1.0 + growth * (threshold - angle) / threshold)


def grade_roughness(readings_um, limit_um, reading_parameter, limit_parameter):
    """Grade every roughness reading of one surface against its limit.

    The reading parameter and the limit parameter have to be the same
    quantity: an Rz reading compared with an Ra limit passes and fails
    surfaces for no physical reason.
    """
    _require_choice("reading_parameter", reading_parameter, ROUGHNESS_PARAMETERS)
    _require_choice("limit_parameter", limit_parameter, ROUGHNESS_PARAMETERS)
    if reading_parameter != limit_parameter:
        raise ValueError(
            "readings are %s and the limit is %s; the two are different "
            "quantities and cannot be compared"
            % (reading_parameter, limit_parameter)
        )
    if not isinstance(readings_um, (list, tuple)) or not readings_um:
        raise ValueError("readings_um must be a non-empty sequence")
    limit = _require_positive("limit_um", limit_um)
    values = [
        _require_non_negative("reading %d" % index, value)
        for index, value in enumerate(readings_um)
    ]
    over = [value for value in values if not _at_most(value, limit)]
    findings = []
    if over:
        findings.append(
            "%d of %d %s readings above the %.2f um limit (worst %.2f um)"
            % (len(over), len(values), reading_parameter, limit, max(over))
        )
    return {
        "parameter": reading_parameter,
        "count": len(values),
        "worst_um": max(values),
        "mean_um": sum(values) / len(values),
        "over_limit": len(over),
        "verdict": VERDICT_REJECT if over else VERDICT_ACCEPT,
        "findings": findings,
    }


def adhered_particle_density(count, area_cm2, limit_per_cm2):
    """Grade adhering partly fused particles per unit of surface area."""
    number = _require_count("count", count, minimum=0)
    area = _require_positive("area_cm2", area_cm2)
    limit = _require_non_negative("limit_per_cm2", limit_per_cm2)
    density = number / area
    findings = []
    acceptable = _at_most(density, limit)
    if not acceptable:
        findings.append(
            "%.2f adhering particles per cm2 over %.1f cm2 exceeds the %.2f "
            "per cm2 limit" % (density, area, limit)
        )
    return {
        "density_per_cm2": density,
        "limit_per_cm2": limit,
        "verdict": VERDICT_ACCEPT if acceptable else VERDICT_REJECT,
        "findings": findings,
    }


def grade_surface(surface, process=None):
    """Grade one declared surface on parameter, readings and achievability."""
    if not isinstance(surface, dict):
        raise ValueError("surface must be a mapping, got %r" % (surface,))
    process = process or {}
    if not isinstance(process, dict):
        raise ValueError("process must be a mapping, got %r" % (process,))
    identifier = surface.get("id", "surface")
    category = _require_choice(
        "surface %s category" % identifier, surface.get("category"),
        SURFACE_CATEGORIES,
    )
    roughness = grade_roughness(
        surface.get("readings_um"),
        surface.get("limit_um"),
        surface.get("reading_parameter", "Ra"),
        surface.get("limit_parameter", "Ra"),
    )
    findings = ["%s: %s" % (identifier, text) for text in roughness["findings"]]
    verdicts = [roughness["verdict"]]

    expected = None
    if category in AS_BUILT_CATEGORIES and "vertical_ra_um" in process:
        expected = expected_as_built_ra(
            process.get("vertical_ra_um"),
            surface.get("overhang_angle_deg", 90.0),
            process.get("downskin_threshold_deg", DEFAULT_DOWNSKIN_THRESHOLD_DEG),
            process.get("downskin_growth_factor", DEFAULT_DOWNSKIN_GROWTH_FACTOR),
        )
        if roughness["parameter"] == "Ra" and not _at_most(
            expected, _require_positive("limit_um", surface.get("limit_um"))
        ):
            verdicts.append(VERDICT_REVIEW)
            findings.append(
                "%s: the process leaves about %.2f um Ra at a %.0f degree "
                "overhang against a %.2f um limit; the limit needs a finishing "
                "operation or a support change, not a rebuild"
                % (
                    identifier,
                    expected,
                    float(surface.get("overhang_angle_deg", 90.0)),
                    float(surface.get("limit_um")),
                )
            )

    particles = None
    if surface.get("adhered_particle_count") is not None:
        particles = adhered_particle_density(
            surface.get("adhered_particle_count"),
            surface.get("area_cm2"),
            surface.get("particle_limit_per_cm2", 0.0),
        )
        verdicts.append(particles["verdict"])
        findings.extend("%s: %s" % (identifier, text) for text in particles["findings"])

    return {
        "id": identifier,
        "category": category,
        "roughness": roughness,
        "expected_as_built_ra_um": expected,
        "particles": particles,
        "verdict": _worst(verdicts),
        "findings": findings,
    }


def sampling_coverage(surfaces, declared_ids):
    """Check that every surface the specification names was actually measured."""
    if not isinstance(declared_ids, (list, tuple)) or not declared_ids:
        raise ValueError("declared_ids must be a non-empty sequence")
    if not isinstance(surfaces, (list, tuple)):
        raise ValueError("surfaces must be a sequence")
    measured = set()
    for surface in surfaces:
        if not isinstance(surface, dict):
            raise ValueError("each surface must be a mapping, got %r" % (surface,))
        readings = surface.get("readings_um")
        if isinstance(readings, (list, tuple)) and readings:
            measured.add(surface.get("id"))
    missing = [name for name in declared_ids if name not in measured]
    findings = []
    if missing:
        findings.append(
            "no reading on declared surface(s) %s; their condition is "
            "unverified" % ", ".join(str(name) for name in missing)
        )
    return {
        "declared": len(declared_ids),
        "measured": len(measured & set(declared_ids)),
        "missing": missing,
        "verdict": VERDICT_REJECT if missing else VERDICT_ACCEPT,
        "findings": findings,
    }


def assess_surface_condition(case):
    """Full surface-condition verdict over every declared surface of a part."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    surfaces = case.get("surfaces")
    if not isinstance(surfaces, (list, tuple)) or not surfaces:
        raise ValueError("case['surfaces'] must be a non-empty sequence")
    declared = case.get("declared_ids") or [
        surface.get("id") for surface in surfaces if isinstance(surface, dict)
    ]
    coverage = sampling_coverage(surfaces, declared)
    process = case.get("process", {})
    graded = [grade_surface(surface, process) for surface in surfaces]
    surface_verdict = _worst([record["verdict"] for record in graded])
    verdict = _worst([surface_verdict, coverage["verdict"]])
    driving = [
        record["id"]
        for record in graded
        if _VERDICT_RANK[record["verdict"]] == _VERDICT_RANK[verdict]
        and verdict != VERDICT_ACCEPT
    ]
    findings = []
    for record in graded:
        findings.extend(record["findings"])
    findings.extend("coverage: %s" % text for text in coverage["findings"])
    return {
        "verdict": verdict,
        "driving_surfaces": driving,
        "surfaces": graded,
        "coverage": coverage,
        "findings": findings,
    }
