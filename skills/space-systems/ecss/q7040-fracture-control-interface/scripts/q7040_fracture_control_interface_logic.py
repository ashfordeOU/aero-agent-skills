#!/usr/bin/env python3
"""Interface between brazing control and fracture control for brazed items.

Anchor: the interface between the ECSS-Q-ST-70-40 brazing clauses and
the fracture-control requirements of ECSS-E-ST-32-01C. The procedure
below is a paraphrase into implementable steps; no standard text is
reproduced.

Brazing and fracture control meet at one question: can the flaw that
survives inspection be shown not to grow to failure inside the service
life? For a brazement that question is harder than for a parent-metal
part, because the flaw of interest lies in a thin filler layer between
two dissimilar materials and the inspection that has to find it is
looking through one of them.

The categorisation comes first, and it is not about how important the
part feels. A part whose failure is contained, or which sits in a
load path that survives its own failure, is not a fracture-critical
item however expensive it is. A part whose failure is catastrophic and
has no redundant path is one, and a brazement inside such a part drags
the braze process into the fracture-control programme with it.

For a fracture-critical brazement the arithmetic is a comparison, not a
single number. The critical crack size follows from the fracture
toughness of the joint, the geometry factor and the peak stress. The
flaw the inspection can actually find follows from the NDI method and
from the joint being brazed rather than solid. Damage tolerance holds
when the second is smaller than the first by the required factor. When
it is not, no amount of re-inspection closes it: the routes are a proof
test that screens the flaw out by loading, a redesign into a fail-safe
path, or a joint made another way.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CATEGORY_FRACTURE_CRITICAL = "fracture-critical-item"
CATEGORY_LOW_RISK = "low-risk-fracture-part"
CATEGORY_NON_CRITICAL = "non-fracture-critical-part"

CATEGORIES = (
    CATEGORY_FRACTURE_CRITICAL,
    CATEGORY_LOW_RISK,
    CATEGORY_NON_CRITICAL,
)

NDI_RADIOGRAPHY = "radiographic-inspection"
NDI_ULTRASONIC = "ultrasonic-inspection"
NDI_PENETRANT = "penetrant-inspection"
NDI_PROOF_TEST = "proof-test-screening"

NDI_METHODS = (NDI_RADIOGRAPHY, NDI_ULTRASONIC, NDI_PENETRANT, NDI_PROOF_TEST)

# A penetrant check only reaches a flaw that breaks the surface, so it
# cannot be the demonstrating method for a buried braze-layer flaw.
_SURFACE_ONLY_METHODS = frozenset((NDI_PENETRANT,))

ROUTE_NDI_DEMONSTRATED = "damage-tolerance-demonstrated-by-inspection"
ROUTE_PROOF_TEST = "screen-the-flaw-by-proof-test"
ROUTE_REDESIGN = "redesign-to-a-fail-safe-or-contained-load-path"
ROUTE_LOW_RISK = "covered-by-the-low-risk-fracture-part-route"
ROUTE_NOT_APPLICABLE = "outside-the-fracture-control-programme"

DELIVERABLE_FCI_ENTRY = "fracture-control-item-list-entry"
DELIVERABLE_NDI_PLAN = "braze-ndi-plan-at-the-declared-detectable-flaw-size"
DELIVERABLE_DAMAGE_TOLERANCE = "brazed-joint-damage-tolerance-assessment"
DELIVERABLE_TRACEABILITY = "brazement-record-traceability-to-the-fracture-file"
DELIVERABLE_REPAIR_CONCURRENCE = "fracture-control-concurrence-before-any-rebraze"
DELIVERABLE_MATERIAL_DATA = "braze-joint-fracture-toughness-data-source"

# Required ratio between the critical crack size and the flaw the
# inspection can find, for a brazed fracture-critical item.
DEFAULT_REQUIRED_FACTOR = 4.0

# Floating-point representation tolerance on the margin comparison.
MARGIN_TOLERANCE = 1e-9


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be True or False, got %r" % (name, value))
    return value


def _require_positive(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return float(value)


def categorize_item(failure_is_catastrophic, released_mass_contained, fail_safe_path):
    """Place the brazed item against the fracture-control categories."""
    catastrophic = _require_flag(
        "failure_is_catastrophic", failure_is_catastrophic
    )
    contained = _require_flag("released_mass_contained", released_mass_contained)
    fail_safe = _require_flag("fail_safe_path", fail_safe_path)
    if not catastrophic:
        return CATEGORY_NON_CRITICAL
    if contained:
        return CATEGORY_NON_CRITICAL
    if fail_safe:
        return CATEGORY_LOW_RISK
    return CATEGORY_FRACTURE_CRITICAL


def critical_crack_size(fracture_toughness, peak_stress, geometry_factor):
    """Through-crack size at which the brazed joint runs, in metres.

    fracture_toughness in MPa*sqrt(m), peak_stress in MPa, geometry
    factor dimensionless.
    """
    k_ic = _require_positive("fracture_toughness", fracture_toughness)
    stress = _require_positive("peak_stress", peak_stress)
    beta = _require_positive("geometry_factor", geometry_factor)
    ratio = k_ic / (beta * stress)
    return (ratio * ratio) / math.pi


def detectable_flaw_size(method, base_capability_m, brazed_joint_penalty=None):
    """Flaw the method can find in a brazement, not in a solid section."""
    _require_choice("method", method, NDI_METHODS)
    base = _require_positive("base_capability_m", base_capability_m)
    penalty = (
        2.0 if brazed_joint_penalty is None
        else _require_positive("brazed_joint_penalty", brazed_joint_penalty)
    )
    if penalty < 1.0:
        raise ValueError(
            "a brazed joint cannot be easier to inspect than the solid "
            "section the capability was measured on, got a penalty of %r"
            % (brazed_joint_penalty,)
        )
    if method in _SURFACE_ONLY_METHODS:
        raise ValueError(
            "%s reaches only a surface-breaking flaw and cannot demonstrate a "
            "buried braze-layer flaw size" % method
        )
    if method == NDI_PROOF_TEST:
        raise ValueError(
            "a proof test screens flaws by loading rather than by detecting "
            "them; it has no detectable flaw size of its own"
        )
    return base * penalty


def damage_tolerance_margin(critical_size, detectable_size, required_factor=None):
    """Whether the flaw that survives inspection is small enough."""
    a_cr = _require_positive("critical_size", critical_size)
    a_ndi = _require_positive("detectable_size", detectable_size)
    factor = (
        DEFAULT_REQUIRED_FACTOR if required_factor is None
        else _require_positive("required_factor", required_factor)
    )
    if factor < 1.0:
        raise ValueError(
            "the required factor cannot ask for less than the critical size "
            "itself, got %r" % (required_factor,)
        )
    achieved = a_cr / a_ndi
    return {
        "critical_size_m": a_cr,
        "detectable_size_m": a_ndi,
        "required_factor": factor,
        "achieved_factor": achieved,
        "shortfall": factor - achieved,
        "demonstrated": achieved - factor > -MARGIN_TOLERANCE,
    }


def interface_deliverables(category):
    """What the brazing file owes the fracture-control programme."""
    _require_choice("category", category, CATEGORIES)
    if category == CATEGORY_NON_CRITICAL:
        return []
    owed = [DELIVERABLE_FCI_ENTRY, DELIVERABLE_TRACEABILITY]
    if category == CATEGORY_FRACTURE_CRITICAL:
        owed.insert(1, DELIVERABLE_NDI_PLAN)
        owed.insert(2, DELIVERABLE_DAMAGE_TOLERANCE)
        owed.append(DELIVERABLE_MATERIAL_DATA)
        owed.append(DELIVERABLE_REPAIR_CONCURRENCE)
    return owed


def assess_fracture_interface(case):
    """Route the brazed item through the fracture-control interface."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    item_id = case.get("item_id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("item_id must be a non-empty string, got %r" % (item_id,))
    category = categorize_item(
        case.get("failure_is_catastrophic"),
        case.get("released_mass_contained"),
        case.get("fail_safe_path"),
    )
    owed = interface_deliverables(category)
    findings = []

    held = case.get("deliverables_held", [])
    if not isinstance(held, (list, tuple, set)):
        raise ValueError("deliverables_held must be a sequence of names")
    missing = [name for name in owed if name not in set(held)]

    if category != CATEGORY_FRACTURE_CRITICAL:
        if missing:
            findings.append(
                "%d fracture-control deliverable(s) are not in the brazing "
                "file: %s" % (len(missing), ", ".join(missing))
            )
        return {
            "item_id": item_id,
            "category": category,
            "deliverables": owed,
            "missing_deliverables": missing,
            "margin": None,
            "route": ROUTE_NOT_APPLICABLE
            if category == CATEGORY_NON_CRITICAL
            else ROUTE_LOW_RISK,
            "findings": findings,
        }

    a_cr = critical_crack_size(
        case.get("fracture_toughness_mpa_sqrt_m"),
        case.get("peak_stress_mpa"),
        case.get("geometry_factor"),
    )
    a_ndi = detectable_flaw_size(
        _require_choice("ndi_method", case.get("ndi_method"), NDI_METHODS),
        case.get("ndi_base_capability_m"),
        case.get("brazed_joint_penalty"),
    )
    margin = damage_tolerance_margin(a_cr, a_ndi, case.get("required_factor"))
    if margin["demonstrated"]:
        route = ROUTE_NDI_DEMONSTRATED
    else:
        findings.append(
            "the inspection leaves a %.6g m flaw against a %.6g m critical "
            "size, a factor of %.3f where %.3f is required; re-inspecting to "
            "the same capability cannot close it"
            % (
                margin["detectable_size_m"],
                margin["critical_size_m"],
                margin["achieved_factor"],
                margin["required_factor"],
            )
        )
        route = (
            ROUTE_PROOF_TEST
            if _require_flag(
                "proof_test_feasible", case.get("proof_test_feasible", False)
            )
            else ROUTE_REDESIGN
        )
    if missing:
        findings.append(
            "%d fracture-control deliverable(s) are not in the brazing file: "
            "%s" % (len(missing), ", ".join(missing))
        )
    return {
        "item_id": item_id,
        "category": category,
        "deliverables": owed,
        "missing_deliverables": missing,
        "margin": margin,
        "route": route,
        "findings": findings,
    }
