#!/usr/bin/env python3
"""Adherence durability check over a bare cell's antireflection coating and
its cell and diode contacts.

Anchor: ECSS-E-ST-20-08C clause 7.5.8. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The adherence method is one technique applied to three different
surfaces, and each of them fails for its own reason:

    antireflection coating  a durability question with an optical
                            price. Coating lifted off a patch leaves
                            that patch reflecting like bare
                            semiconductor, so the removed area is not
                            only a cosmetic fraction -- it is current
                            the cell will never make again
    cell contacts           the metallisation an interconnect is later
                            welded or soldered to. Metallisation that
                            lifts under the method would have lifted
                            under the joining process
    diode contacts          the same question for the bypass diode
                            metallisation, where the loss is not one
                            cell's current but a whole string's shadow
                            protection

A run that exercises one surface and reports a clean result has not
performed this check. The surfaces the specimen carries are the surfaces
the method has to reach, so an unexercised surface stops the assessment
instead of passing quietly.

Removal is graded in three steps rather than two. Nothing came away;
something came away but stayed inside the declared allowance; more came
away than the allowance covers. The middle step is a real outcome for a
coating and a warning for metallisation.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ANTIREFLECTION_COATING = "antireflection-coating"
CELL_CONTACT = "cell-contact"
DIODE_CONTACT = "diode-contact"

ADHERENCE_SURFACES = (ANTIREFLECTION_COATING, CELL_CONTACT, DIODE_CONTACT)

INTACT = "intact"
WITHIN_ALLOWANCE = "within-allowance"
OVER_ALLOWANCE = "over-allowance"

REMOVAL_CATEGORIES = (INTACT, WITHIN_ALLOWANCE, OVER_ALLOWANCE)

COATING_ADHERENCE_PASSED = "coating-adherence-passed"
COATING_ADHERENCE_FAILED = "coating-adherence-failed"
COATING_ADHERENCE_NOT_EVALUATED = "coating-adherence-not-evaluated"

COATING_ADHERENCE_VERDICTS = (
    COATING_ADHERENCE_PASSED,
    COATING_ADHERENCE_FAILED,
    COATING_ADHERENCE_NOT_EVALUATED,
)

# Declared acceptance policy: project numbers, not physical constants.
DEFAULT_COATING_ADHERENCE_POLICY = {
    "max_coating_removed_fraction": 0.02,
    "max_contact_removed_fraction": 0.005,
    "max_current_loss_fraction": 0.01,
    "max_reject_fraction": 0.10,
    "min_specimens": 3,
}

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


def _require_fraction(name, value):
    value = _require_number(name, value)
    if value < 0.0 or value >= 1.0:
        raise ValueError(
            "%s must sit in [0, 1), got %r" % (name, value)
        )
    return value


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("%s must be an integer of at least 1, got %r" % (name, value))
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A removed-area fraction and a current loss are quotients of measured
    areas, so a specimen cut exactly to an allowance can land a few units
    in the last place above it. The allowance is never raised; only the
    comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_coating_adherence_policy(policy=DEFAULT_COATING_ADHERENCE_POLICY):
    """Check an acceptance policy carries sane numbers before it is used."""
    _require_mapping("policy", policy)
    for key in ("max_coating_removed_fraction", "max_contact_removed_fraction"):
        value = _require_non_negative(key, policy.get(key))
        if value >= 1.0:
            raise ValueError("%s must sit below 1.0, got %r" % (key, value))
    loss = _require_non_negative(
        "max_current_loss_fraction", policy.get("max_current_loss_fraction")
    )
    if loss >= 1.0:
        raise ValueError(
            "max_current_loss_fraction must sit below 1.0, got %r" % (loss,)
        )
    reject = _require_non_negative(
        "max_reject_fraction", policy.get("max_reject_fraction")
    )
    if reject > 1.0:
        raise ValueError(
            "max_reject_fraction must not exceed 1.0, got %r" % (reject,)
        )
    _require_count("min_specimens", policy.get("min_specimens"))
    return policy


def surface_removal_cap(surface, policy=DEFAULT_COATING_ADHERENCE_POLICY):
    """Allowance that applies to one surface.

    The coating and the metallisation are held to different numbers: a
    coating may lose a little area and still do its job, while lifted
    metallisation is a joint nobody will be able to make later.
    """
    validate_coating_adherence_policy(policy)
    if surface == ANTIREFLECTION_COATING:
        return float(policy["max_coating_removed_fraction"])
    if surface in (CELL_CONTACT, DIODE_CONTACT):
        return float(policy["max_contact_removed_fraction"])
    raise ValueError(
        "unknown adherence surface %r; recognised: %s"
        % (surface, ", ".join(ADHERENCE_SURFACES))
    )


def removed_area_fraction(removed_area_mm2, surface_area_mm2):
    """Share of one surface that came away under the method."""
    removed = _require_non_negative("removed_area_mm2", removed_area_mm2)
    area = _require_positive("surface_area_mm2", surface_area_mm2)
    if removed > area:
        raise ValueError(
            "removed area %.4f mm2 exceeds the surface area %.4f mm2"
            % (removed, area)
        )
    return removed / area


def coating_current_loss_fraction(
    removed_fraction, coated_reflectance, bare_reflectance
):
    """Current the cell loses where the antireflection coating came away.

    A patch stripped of coating reflects like bare semiconductor, so the
    absorbed fraction over that patch drops from one minus the coated
    reflectance to one minus the bare reflectance. Referred to the
    coated cell, the loss is the stripped share times the relative fall
    in absorbed light. A bare reflectance that does not exceed the
    coated one is refused: that is not an antireflection coating, and
    taking it at face value would report coating loss as a current gain.
    """
    stripped = _require_fraction("removed_fraction", removed_fraction)
    coated = _require_fraction("coated_reflectance", coated_reflectance)
    bare = _require_fraction("bare_reflectance", bare_reflectance)
    if bare <= coated:
        raise ValueError(
            "bare_reflectance %r must exceed coated_reflectance %r for an "
            "antireflection coating" % (bare, coated)
        )
    return stripped * (bare - coated) / (1.0 - coated)


def categorize_removal(removed_fraction, cap):
    """Group one surface's removal against its allowance."""
    fraction = _require_non_negative("removed_fraction", removed_fraction)
    limit = _require_non_negative("cap", cap)
    if fraction <= 0.0:
        return INTACT
    if _at_most(fraction, limit):
        return WITHIN_ALLOWANCE
    return OVER_ALLOWANCE


def required_surfaces(specimen):
    """Surfaces this specimen has to have had the method applied to.

    Every bare cell carries a coating and cell contacts. Diode contacts
    are required only of a specimen that declares a bypass diode, so a
    cell without one is not failed for a surface it does not have.
    """
    _require_mapping("specimen", specimen)
    surfaces = [ANTIREFLECTION_COATING, CELL_CONTACT]
    if bool(specimen.get("carries_bypass_diode", False)):
        surfaces.append(DIODE_CONTACT)
    return tuple(surfaces)


def surface_coverage(specimen):
    """Did the method reach every surface this specimen carries?"""
    needed = required_surfaces(specimen)
    exercised = specimen.get("surfaces")
    _require_mapping("surfaces", exercised)
    for name in exercised:
        if name not in ADHERENCE_SURFACES:
            raise ValueError(
                "unknown adherence surface %r; recognised: %s"
                % (name, ", ".join(ADHERENCE_SURFACES))
            )
    missing = tuple(name for name in needed if name not in exercised)
    extra = tuple(
        name for name in ADHERENCE_SURFACES
        if name in exercised and name not in needed
    )
    findings = []
    if missing:
        findings.append(
            "specimen %r never had the method applied to %s, so those surfaces "
            "carry no durability evidence"
            % (specimen.get("id"), ", ".join(missing))
        )
    if extra:
        findings.append(
            "specimen %r reports %s although it declares no bypass diode"
            % (specimen.get("id"), ", ".join(extra))
        )
    return {
        "required": needed,
        "missing": missing,
        "unexpected": extra,
        "complete": not missing and not extra,
        "findings": findings,
    }


def evaluate_specimen(specimen, policy=DEFAULT_COATING_ADHERENCE_POLICY):
    """Reduce one specimen to per-surface removal, optical loss and a verdict."""
    validate_coating_adherence_policy(policy)
    coverage = surface_coverage(specimen)

    result = {
        "id": specimen.get("id"),
        "carries_bypass_diode": bool(specimen.get("carries_bypass_diode", False)),
        "surface_removed_fraction": {},
        "surface_categories": {},
        "coverage_complete": coverage["complete"],
        "missing_surfaces": coverage["missing"],
        "findings": list(coverage["findings"]),
    }

    if not coverage["complete"]:
        result.update(
            {
                "current_loss_fraction": None,
                "acceptable": None,
                "evaluated": False,
            }
        )
        return result

    surfaces = specimen["surfaces"]
    for name in ADHERENCE_SURFACES:
        if name not in surfaces:
            continue
        record = _require_mapping(name, surfaces[name])
        fraction = removed_area_fraction(
            record.get("removed_area_mm2"), record.get("surface_area_mm2")
        )
        cap = surface_removal_cap(name, policy)
        category = categorize_removal(fraction, cap)
        result["surface_removed_fraction"][name] = fraction
        result["surface_categories"][name] = category
        if category == OVER_ALLOWANCE:
            result["findings"].append(
                "specimen %r lost %.4f of its %s, past the %.4f allowance"
                % (specimen.get("id"), fraction, name, cap)
            )

    coating = surfaces[ANTIREFLECTION_COATING]
    loss = coating_current_loss_fraction(
        result["surface_removed_fraction"][ANTIREFLECTION_COATING],
        coating.get("coated_reflectance"),
        coating.get("bare_reflectance"),
    )
    loss_within = _at_most(loss, float(policy["max_current_loss_fraction"]))
    if not loss_within:
        result["findings"].append(
            "specimen %r gives up %.5f of its current where the coating came "
            "away, past the %.5f allowed"
            % (specimen.get("id"), loss, float(policy["max_current_loss_fraction"]))
        )

    over = [
        name
        for name, category in result["surface_categories"].items()
        if category == OVER_ALLOWANCE
    ]
    result.update(
        {
            "current_loss_fraction": loss,
            "current_loss_within_allowance": loss_within,
            "over_allowance_surfaces": tuple(
                name for name in ADHERENCE_SURFACES if name in over
            ),
            "acceptable": not over and loss_within,
            "evaluated": True,
        }
    )
    return result


def evaluate_cell_coating_adherence(run, policy=DEFAULT_COATING_ADHERENCE_POLICY):
    """Full clause 7.5.8 coating and contact adherence run with a verdict."""
    validate_coating_adherence_policy(policy)
    _require_mapping("run", run)

    specimens = run.get("specimens")
    if not isinstance(specimens, (list, tuple)) or not specimens:
        raise ValueError("run must carry a non-empty specimens sequence")

    evaluated = [evaluate_specimen(item, policy) for item in specimens]
    findings = []
    for record in evaluated:
        findings.extend(record["findings"])

    unevaluated = [
        record["id"] for record in evaluated if not record["evaluated"]
    ]
    too_few = len(evaluated) < int(policy["min_specimens"])

    result = {
        "lot_id": run.get("lot_id"),
        "specimens": evaluated,
        "specimen_count": len(evaluated),
        "unevaluated_specimen_ids": unevaluated,
        "findings": findings,
    }

    if too_few:
        findings.append(
            "%d specimen(s) is under the floor of %d, so the run cannot speak "
            "for the lot" % (len(evaluated), int(policy["min_specimens"]))
        )
    if unevaluated or too_few:
        result.update(
            {
                "compliant": None,
                "rejected_specimen_ids": [],
                "reject_fraction": None,
                "mean_current_loss_fraction": None,
                "verdict": COATING_ADHERENCE_NOT_EVALUATED,
            }
        )
        return result

    rejected = [record["id"] for record in evaluated if not record["acceptable"]]
    reject_fraction = len(rejected) / len(evaluated)
    mean_loss = sum(
        record["current_loss_fraction"] for record in evaluated
    ) / len(evaluated)

    reasons = []
    if not _at_most(reject_fraction, float(policy["max_reject_fraction"])):
        reasons.append(
            "rejected share %.4f exceeds the allowed %.4f"
            % (reject_fraction, float(policy["max_reject_fraction"]))
        )
    contact_losses = [
        record["id"]
        for record in evaluated
        if any(
            name in (CELL_CONTACT, DIODE_CONTACT)
            for name in record["over_allowance_surfaces"]
        )
    ]
    if contact_losses:
        reasons.append(
            "%d specimen(s) lifted metallisation past its allowance: %s"
            % (len(contact_losses), ", ".join(repr(item) for item in contact_losses))
        )

    compliant = not reasons
    findings.extend(reasons)
    result.update(
        {
            "compliant": compliant,
            "rejected_specimen_ids": rejected,
            "reject_fraction": reject_fraction,
            "mean_current_loss_fraction": mean_loss,
            "metallisation_loss_specimen_ids": contact_losses,
            "verdict": COATING_ADHERENCE_PASSED
            if compliant
            else COATING_ADHERENCE_FAILED,
        }
    )
    return result
