#!/usr/bin/env python3
"""Coating quality verification for an anodized aluminium batch.

Anchor: ECSS-Q-ST-70-03 quality clause on anodizing. The procedure below
is a paraphrase into implementable steps; no standard text is reproduced.

Four characteristics decide whether an anodized coating is acceptable,
and they fail for different reasons:

thickness      every reading has to sit inside the specified band. Thin
               is a corrosion and wear problem; thick is a dimensional
               and brittleness problem, so the band is two-sided.
coverage       an area that never took coating is bare metal, whatever
               the readings elsewhere say. Deliberate masking is
               declared and removed from the graded area; anything else
               is a coverage shortfall.
adhesion       a bend or tape check leaves the coating intact, crazed,
               flaking or detached. Crazing on a formed part is a
               conditional outcome, not a pass and not a reject.
grouped as     no-separation, crazing-only, flaking, detachment.
colour         a sealed dyed coating varies across a rack. The graded
               quantity is the spread of the sample about the reference,
               not any single point.

The verdict is the worst of the four, and the failing characteristic is
always named so the reviewer knows which tank or rack step to look at.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ADHESION_OUTCOMES = ("no-separation", "crazing-only", "flaking", "detachment")
PART_FORMS = ("flat", "formed", "machined")

VERDICT_ACCEPT = "accept"
VERDICT_REVIEW = "review"
VERDICT_REJECT = "reject"

_VERDICT_RANK = {VERDICT_ACCEPT: 0, VERDICT_REVIEW: 1, VERDICT_REJECT: 2}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A reading that was specified to land exactly on the band edge can
    evaluate a few units in the last place below it once it has been
    through a unit conversion. The limit itself is never relaxed; only
    the comparison tolerates the representation error.
    """
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


def evaluate_thickness(readings_um, min_um, max_um):
    """Grade every thickness reading against the two-sided specified band."""
    if not isinstance(readings_um, (list, tuple)) or not readings_um:
        raise ValueError("readings_um must be a non-empty sequence of readings")
    low = _require_positive("min_um", min_um)
    high = _require_positive("max_um", max_um)
    if high < low:
        raise ValueError(
            "max_um %g must not be below min_um %g; the band is inverted" % (high, low)
        )
    values = [
        _require_non_negative("reading %d" % index, value)
        for index, value in enumerate(readings_um)
    ]
    thin = [v for v in values if not _at_least(v, low)]
    thick = [v for v in values if not _at_most(v, high)]
    findings = []
    if thin:
        findings.append(
            "%d of %d readings below the %.1f um minimum (lowest %.2f um)"
            % (len(thin), len(values), low, min(thin))
        )
    if thick:
        findings.append(
            "%d of %d readings above the %.1f um maximum (highest %.2f um)"
            % (len(thick), len(values), high, max(thick))
        )
    return {
        "count": len(values),
        "min_um": min(values),
        "max_um": max(values),
        "mean_um": sum(values) / len(values),
        "below_minimum": len(thin),
        "above_maximum": len(thick),
        "in_band": len(values) - len(thin) - len(thick),
        "verdict": VERDICT_REJECT if (thin or thick) else VERDICT_ACCEPT,
        "findings": findings,
    }


def evaluate_coverage(
    total_area_mm2, masked_area_mm2=0.0, uncoated_area_mm2=0.0, max_uncoated_fraction=0.0
):
    """Coverage of the graded area once declared masking is removed."""
    total = _require_positive("total_area_mm2", total_area_mm2)
    masked = _require_non_negative("masked_area_mm2", masked_area_mm2)
    uncoated = _require_non_negative("uncoated_area_mm2", uncoated_area_mm2)
    allowance = _require_non_negative("max_uncoated_fraction", max_uncoated_fraction)
    if allowance > 1.0:
        raise ValueError("max_uncoated_fraction must not exceed 1.0")
    graded = total - masked
    if graded <= 0.0:
        raise ValueError(
            "masked area %g mm2 leaves no graded area of the %g mm2 surface"
            % (masked, total)
        )
    if uncoated > graded:
        raise ValueError(
            "uncoated area %g mm2 exceeds the graded area %g mm2" % (uncoated, graded)
        )
    fraction = uncoated / graded
    acceptable = _at_most(fraction, allowance)
    findings = []
    if not acceptable:
        findings.append(
            "uncoated fraction %.4f exceeds the %.4f allowance over %.1f mm2 graded"
            % (fraction, allowance, graded)
        )
    return {
        "graded_area_mm2": graded,
        "uncoated_fraction": fraction,
        "coverage_fraction": 1.0 - fraction,
        "verdict": VERDICT_ACCEPT if acceptable else VERDICT_REJECT,
        "findings": findings,
    }


def evaluate_adhesion(outcome, part_form="flat"):
    """Grade a bend or tape adhesion outcome, grouped by the four results.

    Crazing on a formed part is the expected response of a hard coating
    to the forming radius, so it is a review outcome there and a reject
    on a flat or machined part where nothing should have crazed.
    """
    _require_choice("outcome", outcome, ADHESION_OUTCOMES)
    _require_choice("part_form", part_form, PART_FORMS)
    findings = []
    if outcome == "no-separation":
        verdict = VERDICT_ACCEPT
    elif outcome == "crazing-only":
        if part_form == "formed":
            verdict = VERDICT_REVIEW
            findings.append(
                "crazing on a formed part needs the forming radius reviewed "
                "against the coating thickness before acceptance"
            )
        else:
            verdict = VERDICT_REJECT
            findings.append(
                "crazing on a %s part points at an over-thick or over-aged "
                "coating rather than the geometry" % part_form
            )
    else:
        verdict = VERDICT_REJECT
        findings.append("adhesion outcome %s is a coating failure" % outcome)
    return {"outcome": outcome, "verdict": verdict, "findings": findings}


def evaluate_colour_uniformity(sample_values, reference_value, tolerance):
    """Spread of the colour sample about the declared reference value."""
    if not isinstance(sample_values, (list, tuple)) or not sample_values:
        raise ValueError("sample_values must be a non-empty sequence")
    reference = _require_number("reference_value", reference_value)
    band = _require_non_negative("tolerance", tolerance)
    values = [
        _require_number("sample %d" % index, value)
        for index, value in enumerate(sample_values)
    ]
    deviations = [abs(value - reference) for value in values]
    worst = max(deviations)
    acceptable = _at_most(worst, band)
    findings = []
    if not acceptable:
        findings.append(
            "colour deviation %.3f about the reference exceeds the %.3f tolerance"
            % (worst, band)
        )
    return {
        "max_deviation": worst,
        "mean_deviation": sum(deviations) / len(deviations),
        "spread": max(values) - min(values),
        "verdict": VERDICT_ACCEPT if acceptable else VERDICT_REJECT,
        "findings": findings,
    }


def verify_coating(case):
    """Full coating-quality verdict over the four graded characteristics."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    thickness = evaluate_thickness(
        case.get("readings_um"), case.get("min_um"), case.get("max_um")
    )
    coverage = evaluate_coverage(
        case.get("total_area_mm2"),
        masked_area_mm2=case.get("masked_area_mm2", 0.0),
        uncoated_area_mm2=case.get("uncoated_area_mm2", 0.0),
        max_uncoated_fraction=case.get("max_uncoated_fraction", 0.0),
    )
    adhesion = evaluate_adhesion(
        case.get("adhesion_outcome"), case.get("part_form", "flat")
    )
    colour = evaluate_colour_uniformity(
        case.get("colour_samples"),
        case.get("colour_reference"),
        case.get("colour_tolerance"),
    )
    parts = {
        "thickness": thickness,
        "coverage": coverage,
        "adhesion": adhesion,
        "colour": colour,
    }
    verdict = _worst(part["verdict"] for part in parts.values())
    driving = sorted(
        name
        for name, part in parts.items()
        if _VERDICT_RANK[part["verdict"]] == _VERDICT_RANK[verdict]
        and verdict != VERDICT_ACCEPT
    )
    findings = []
    for name in ("thickness", "coverage", "adhesion", "colour"):
        findings.extend("%s: %s" % (name, text) for text in parts[name]["findings"])
    return {
        "verdict": verdict,
        "driving_characteristics": driving,
        "thickness": thickness,
        "coverage": coverage,
        "adhesion": adhesion,
        "colour": colour,
        "findings": findings,
    }
