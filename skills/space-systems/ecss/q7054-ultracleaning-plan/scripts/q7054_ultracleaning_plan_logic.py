#!/usr/bin/env python3
"""Ultracleaning plan for a hardware set.

Anchor: ECSS-Q-ST-70-54C programme clause. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A plan is not a list of processes. It is the answer to three questions
taken together:

    which process   each item gets one qualified process, the gentlest
                    that reaches the level the item owes and that the
                    material tolerates. Reaching for a harsher process
                    than the level needs spends surface life for nothing.

    when            the process sits at a point in the assembly and
                    integration sequence. A part cleaned before an
                    operation that dirties it again has been cleaned at
                    the wrong time, however well it was cleaned.

    verified how    a level that is claimed is a level that is measured.
                    An unverified claim is an assumption wearing a
                    number.

The coverage findings are therefore the product: an item with no
qualified process, a level claimed with nothing measuring it, and a final
verification that a later contaminating operation invalidates.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MATERIALS = (
    "aluminium-alloy",
    "stainless-steel",
    "titanium-alloy",
    "magnesium-alloy",
    "polymer-composite",
    "optical-glass",
    "silver-coating",
    "gold-coating",
)

# Qualified processes, with the state each can hold and what it damages.
# achievable_particulate_level_um  tightest surface cleanliness level reached
# achievable_nvr_mg_per_01m2       tightest residue allowance reached
# aggressiveness                   surface cost, gentlest first
PROCESS_CATALOGUE = {
    "precision-solvent-wipe": {
        "achievable_particulate_level_um": 300.0,
        "achievable_nvr_mg_per_01m2": 1.00,
        "incompatible_materials": frozenset(),
        "aggressiveness": 1,
        "wet": True,
    },
    "carbon-dioxide-snow": {
        "achievable_particulate_level_um": 100.0,
        "achievable_nvr_mg_per_01m2": 0.50,
        "incompatible_materials": frozenset({"polymer-composite"}),
        "aggressiveness": 2,
        "wet": False,
    },
    "ultraviolet-ozone": {
        "achievable_particulate_level_um": 500.0,
        "achievable_nvr_mg_per_01m2": 0.02,
        "incompatible_materials": frozenset({"silver-coating", "magnesium-alloy"}),
        "aggressiveness": 2,
        "wet": False,
    },
    "aqueous-ultrasonic": {
        "achievable_particulate_level_um": 50.0,
        "achievable_nvr_mg_per_01m2": 0.10,
        "incompatible_materials": frozenset(
            {"magnesium-alloy", "optical-glass", "silver-coating"}
        ),
        "aggressiveness": 3,
        "wet": True,
    },
    "precision-solvent-immersion": {
        "achievable_particulate_level_um": 25.0,
        "achievable_nvr_mg_per_01m2": 0.05,
        "incompatible_materials": frozenset({"polymer-composite"}),
        "aggressiveness": 4,
        "wet": True,
    },
    "plasma": {
        "achievable_particulate_level_um": 100.0,
        "achievable_nvr_mg_per_01m2": 0.01,
        "incompatible_materials": frozenset({"polymer-composite", "silver-coating"}),
        "aggressiveness": 5,
        "wet": False,
    },
}

# Levels the routine cleaning route already holds; tighter than these is a
# claim that owes a measurement.
BASELINE_PARTICULATE_LEVEL_UM = 500.0
BASELINE_NVR_MG_PER_01M2 = 2.00

PARTICULATE_VERIFICATION = "particle-count-or-obscuration"
MOLECULAR_VERIFICATION = "solvent-rinse-residue-weighing"
FINAL_VERIFICATION = "pre-delivery-cleanliness-verification"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_index(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer sequence index, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(sorted(allowed)), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, with an exact landing on the limit read as met."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _strictly_below(value, limit):
    if math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return False
    return value < limit


def validate_item(item):
    """Check one hardware item carries everything the plan needs."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping, got %r" % (item,))
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("item id must be a non-empty string, got %r" % (item_id,))
    material = _require_choice("material", item.get("material"), MATERIALS)
    level = _require_positive(
        "required_particulate_level_um", item.get("required_particulate_level_um")
    )
    nvr = _require_positive(
        "required_nvr_mg_per_01m2", item.get("required_nvr_mg_per_01m2")
    )
    sequence = _require_index("sequence", item.get("sequence"))
    return {
        "id": item_id,
        "material": material,
        "required_particulate_level_um": level,
        "required_nvr_mg_per_01m2": nvr,
        "sequence": sequence,
    }


def qualified_processes(item):
    """Processes that reach the item's levels and that its material tolerates."""
    checked = validate_item(item)
    out = []
    for name in sorted(PROCESS_CATALOGUE):
        spec = PROCESS_CATALOGUE[name]
        if checked["material"] in spec["incompatible_materials"]:
            continue
        if not _at_most(
            spec["achievable_particulate_level_um"],
            checked["required_particulate_level_um"],
        ):
            continue
        if not _at_most(
            spec["achievable_nvr_mg_per_01m2"], checked["required_nvr_mg_per_01m2"]
        ):
            continue
        out.append(name)
    return out


def assign_process(item):
    """Gentlest qualified process, or None with the reason none qualifies."""
    checked = validate_item(item)
    candidates = qualified_processes(item)
    if not candidates:
        tolerated = [
            name
            for name, spec in PROCESS_CATALOGUE.items()
            if checked["material"] not in spec["incompatible_materials"]
        ]
        if not tolerated:
            reason = "no catalogued process is compatible with %s" % checked["material"]
        else:
            reason = (
                "no process compatible with %s reaches level %g um and %g mg per "
                "0.1 m2 together"
                % (
                    checked["material"],
                    checked["required_particulate_level_um"],
                    checked["required_nvr_mg_per_01m2"],
                )
            )
        return {"process": None, "reason": reason, "candidates": []}
    chosen = min(
        candidates, key=lambda name: (PROCESS_CATALOGUE[name]["aggressiveness"], name)
    )
    return {
        "process": chosen,
        "reason": "gentlest of %d qualified process(es)" % len(candidates),
        "candidates": candidates,
    }


def verification_points_for(item):
    """Measurements the item's claims oblige, in a stable order."""
    checked = validate_item(item)
    points = []
    if _strictly_below(
        checked["required_particulate_level_um"], BASELINE_PARTICULATE_LEVEL_UM
    ):
        points.append(PARTICULATE_VERIFICATION)
    if _strictly_below(checked["required_nvr_mg_per_01m2"], BASELINE_NVR_MG_PER_01M2):
        points.append(MOLECULAR_VERIFICATION)
    return points


def validate_operation(operation):
    """Check one assembly or integration operation entry."""
    if not isinstance(operation, dict):
        raise ValueError("operation must be a mapping, got %r" % (operation,))
    name = operation.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("operation name must be a non-empty string, got %r" % (name,))
    sequence = _require_index("sequence", operation.get("sequence"))
    contaminating = operation.get("contaminating", False)
    if not isinstance(contaminating, bool):
        raise ValueError(
            "operation contaminating flag must be a boolean, got %r" % (contaminating,)
        )
    return {"name": name, "sequence": sequence, "contaminating": contaminating}


def build_ultracleaning_plan(items, operations=()):
    """Ordered plan with a process and verification points per item."""
    if isinstance(items, dict) or not isinstance(items, (list, tuple)):
        raise ValueError("items must be a list or tuple of mappings, got %r" % (items,))
    if not items:
        raise ValueError("items must not be empty; a plan covers at least one item")
    if isinstance(operations, dict) or not isinstance(operations, (list, tuple)):
        raise ValueError("operations must be a list or tuple, got %r" % (operations,))
    checked_items = [validate_item(item) for item in items]
    ids = [entry["id"] for entry in checked_items]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(
            "duplicate item ids in the plan: %s" % ", ".join(duplicates)
        )
    checked_ops = [validate_operation(op) for op in operations]
    dirty_after = [op for op in checked_ops if op["contaminating"]]

    entries = []
    findings = []
    for checked in sorted(checked_items, key=lambda e: (e["sequence"], e["id"])):
        assignment = assign_process(checked)
        points = verification_points_for(checked)
        later_dirty = sorted(
            (op["name"] for op in dirty_after if op["sequence"] > checked["sequence"])
        )
        entries.append(
            {
                "id": checked["id"],
                "material": checked["material"],
                "sequence": checked["sequence"],
                "required_particulate_level_um": checked[
                    "required_particulate_level_um"
                ],
                "required_nvr_mg_per_01m2": checked["required_nvr_mg_per_01m2"],
                "process": assignment["process"],
                "process_reason": assignment["reason"],
                "verification_points": points,
                "contaminated_after_cleaning_by": later_dirty,
            }
        )
        if assignment["process"] is None:
            findings.append(
                "%s has no qualified process: %s" % (checked["id"], assignment["reason"])
            )
        if points and assignment["process"] is None:
            findings.append(
                "%s claims a level beyond the standard route with no process "
                "behind it" % checked["id"]
            )
        if later_dirty:
            findings.append(
                "%s is cleaned at step %d but %s runs afterwards; the claim does "
                "not survive to delivery without a recleaning step"
                % (checked["id"], checked["sequence"], ", ".join(later_dirty))
            )
        if not points:
            findings.append(
                "%s claims nothing beyond the standard route; confirm it belongs "
                "in the ultracleaning plan at all" % checked["id"]
            )
    entries.append(
        {
            "id": FINAL_VERIFICATION,
            "material": None,
            "sequence": max(
                [e["sequence"] for e in checked_items]
                + [op["sequence"] for op in checked_ops]
            )
            + 1,
            "required_particulate_level_um": min(
                e["required_particulate_level_um"] for e in checked_items
            ),
            "required_nvr_mg_per_01m2": min(
                e["required_nvr_mg_per_01m2"] for e in checked_items
            ),
            "process": None,
            "process_reason": "closing verification, not a cleaning step",
            "verification_points": [PARTICULATE_VERIFICATION, MOLECULAR_VERIFICATION],
            "contaminated_after_cleaning_by": [],
        }
    )
    return {"entries": entries, "findings": findings}


def plan_coverage(plan):
    """Counts a reviewer reads first, and whether the plan closes."""
    if not isinstance(plan, dict) or "entries" not in plan:
        raise ValueError("plan must be the mapping returned by build_ultracleaning_plan")
    cleaning = [e for e in plan["entries"] if e["id"] != FINAL_VERIFICATION]
    assigned = [e for e in cleaning if e["process"] is not None]
    points = sum(len(e["verification_points"]) for e in plan["entries"])
    return {
        "items": len(cleaning),
        "items_with_process": len(assigned),
        "items_without_process": len(cleaning) - len(assigned),
        "verification_points": points,
        "findings": len(plan["findings"]),
        "plan_closes": len(plan["findings"]) == 0,
    }
