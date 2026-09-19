#!/usr/bin/env python3
"""Re-brazing and repair of a rejected brazement: limits and process control.

Anchor: ECSS-Q-ST-70-40 repair clause on brazing of space hardware. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

A rejected brazement is not automatically a repair. Three separate
questions decide it, and answering only the first is the usual mistake.

The defect has to be one a second heating can actually cure. Short
fillets, entrapped flux, porosity and incomplete wetting are wetting and
flow problems, and re-flowing the joint addresses them. Base-metal
erosion, filler depletion into the parent material and a crack that has
run out of the fillet into the parent are losses of parent material; a
second heating deepens them rather than reversing them.

The joint has a repair-cycle budget. Every re-braze is another full
excursion above the filler liquidus, and each excursion dissolves a
little more parent metal into the filler and diffuses a little more
filler into the parent. The budget is therefore counted twice: as a
number of cycles the joint category allows, and as a cumulative dwell
above liquidus the material pair allows. A joint can be inside the cycle
count and outside the dwell budget, or the reverse.

The repair needs a qualified repair procedure of its own, and the
repaired joint owes the original inspection again, plus a destructive
metallographic check when the repair consumes the last permitted cycle.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

DEFECT_INSUFFICIENT_FILLET = "insufficient-fillet"
DEFECT_POROSITY = "fillet-porosity"
DEFECT_FLUX_ENTRAPMENT = "entrapped-flux-residue"
DEFECT_INCOMPLETE_WETTING = "incomplete-wetting"
DEFECT_EXCESS_FILLER = "excess-filler-runout"
DEFECT_BASE_METAL_EROSION = "base-metal-erosion"
DEFECT_FILLER_DEPLETION = "filler-alloy-depletion"
DEFECT_PARENT_CRACK = "crack-into-parent-metal"
DEFECT_DISTORTION = "thermal-distortion-out-of-tolerance"

DEFECT_TYPES = (
    DEFECT_INSUFFICIENT_FILLET,
    DEFECT_POROSITY,
    DEFECT_FLUX_ENTRAPMENT,
    DEFECT_INCOMPLETE_WETTING,
    DEFECT_EXCESS_FILLER,
    DEFECT_BASE_METAL_EROSION,
    DEFECT_FILLER_DEPLETION,
    DEFECT_PARENT_CRACK,
    DEFECT_DISTORTION,
)

# Defects a further heating of the same joint can actually cure.
_REFLOW_CURABLE = frozenset(
    (
        DEFECT_INSUFFICIENT_FILLET,
        DEFECT_POROSITY,
        DEFECT_FLUX_ENTRAPMENT,
        DEFECT_INCOMPLETE_WETTING,
        DEFECT_EXCESS_FILLER,
    )
)

JOINT_CATEGORIES = ("critical", "major", "minor")

# Re-braze cycles permitted on one joint, over and above the first braze.
_CYCLE_LIMIT = {"critical": 1, "major": 2, "minor": 3}

MATERIAL_PAIRS = (
    "stainless-steel-nickel-filler",
    "nickel-alloy-nickel-filler",
    "aluminium-alloy-aluminium-filler",
    "copper-alloy-silver-filler",
    "titanium-alloy-titanium-filler",
)

# Cumulative minutes above the filler liquidus the pair tolerates before
# erosion and diffusion take the joint out of its qualified condition.
_DWELL_BUDGET_MINUTES = {
    "stainless-steel-nickel-filler": 30.0,
    "nickel-alloy-nickel-filler": 45.0,
    "aluminium-alloy-aluminium-filler": 12.0,
    "copper-alloy-silver-filler": 40.0,
    "titanium-alloy-titanium-filler": 20.0,
}

DISPOSITION_REBRAZE = "repair-by-rebraze"
DISPOSITION_SCRAP = "scrap-and-remake"
DISPOSITION_BOARD = "raise-nonconformance-for-board"

INSPECTION_VISUAL = "post-repair-visual-inspection"
INSPECTION_DIMENSIONAL = "post-repair-dimensional-check"
INSPECTION_RADIOGRAPHY = "post-repair-radiographic-inspection"
INSPECTION_PROOF = "post-repair-proof-load-or-pressure-test"
INSPECTION_METALLOGRAPHY = "post-repair-destructive-metallographic-check"

# Floating-point representation tolerance on a dwell budget comparison.
DWELL_TOLERANCE_MINUTES = 1e-9


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_number(name, value, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be at least %s, got %r" % (name, minimum, value))
    return float(value)


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be True or False, got %r" % (name, value))
    return value


def is_reflow_curable(defect):
    """Whether a further heating of the same joint can cure this defect."""
    _require_choice("defect", defect, DEFECT_TYPES)
    return defect in _REFLOW_CURABLE


def cycle_limit(joint_category):
    """Re-braze cycles the joint category permits beyond the first braze."""
    _require_choice("joint_category", joint_category, JOINT_CATEGORIES)
    return _CYCLE_LIMIT[joint_category]


def remaining_cycles(joint_category, cycles_used):
    """Re-braze cycles still available on the joint."""
    limit = cycle_limit(joint_category)
    if isinstance(cycles_used, bool) or not isinstance(cycles_used, int):
        raise ValueError("cycles_used must be an integer, got %r" % (cycles_used,))
    if cycles_used < 0:
        raise ValueError("cycles_used cannot be negative, got %d" % cycles_used)
    return max(0, limit - cycles_used)


def cumulative_dwell(thermal_history):
    """Minutes the joint has already spent above the filler liquidus."""
    if not isinstance(thermal_history, (list, tuple)):
        raise ValueError("thermal_history must be a sequence of cycle mappings")
    total = 0.0
    for index, cycle in enumerate(thermal_history):
        if not isinstance(cycle, dict):
            raise ValueError(
                "thermal history entry %d must be a mapping, got %r" % (index, cycle)
            )
        dwell = _require_number(
            "dwell_minutes of cycle %d" % index, cycle.get("dwell_minutes"), 0.0
        )
        peak = _require_number(
            "peak_temperature_c of cycle %d" % index, cycle.get("peak_temperature_c")
        )
        liquidus = _require_number(
            "liquidus_temperature_c of cycle %d" % index,
            cycle.get("liquidus_temperature_c"),
        )
        if peak < liquidus:
            raise ValueError(
                "cycle %d never reached the filler liquidus (%.1f C peak against "
                "%.1f C liquidus); it is not a braze cycle at all"
                % (index, peak, liquidus)
            )
        total += dwell
    return total


def remaining_dwell_budget(material_pair, thermal_history):
    """Minutes above liquidus still available to the material pair."""
    _require_choice("material_pair", material_pair, MATERIAL_PAIRS)
    used = cumulative_dwell(thermal_history)
    return _DWELL_BUDGET_MINUTES[material_pair] - used


def reinspection_set(joint_category, cycles_after_repair):
    """Inspections the repaired joint owes before it may be offered again."""
    _require_choice("joint_category", joint_category, JOINT_CATEGORIES)
    if isinstance(cycles_after_repair, bool) or not isinstance(
        cycles_after_repair, int
    ):
        raise ValueError(
            "cycles_after_repair must be an integer, got %r" % (cycles_after_repair,)
        )
    if cycles_after_repair < 1:
        raise ValueError(
            "a repaired joint has taken at least one re-braze cycle, got %d"
            % cycles_after_repair
        )
    required = [INSPECTION_VISUAL, INSPECTION_DIMENSIONAL]
    if joint_category in ("critical", "major"):
        required.append(INSPECTION_RADIOGRAPHY)
    if joint_category == "critical":
        required.append(INSPECTION_PROOF)
    if cycles_after_repair >= cycle_limit(joint_category):
        required.append(INSPECTION_METALLOGRAPHY)
    return required


def assess_repair(case):
    """Decide between a re-braze, a remake and a nonconformance board."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    joint_id = case.get("joint_id")
    if not isinstance(joint_id, str) or not joint_id.strip():
        raise ValueError("joint_id must be a non-empty string, got %r" % (joint_id,))
    category = _require_choice(
        "joint_category", case.get("joint_category"), JOINT_CATEGORIES
    )
    defect = _require_choice("defect", case.get("defect"), DEFECT_TYPES)
    pair = _require_choice("material_pair", case.get("material_pair"), MATERIAL_PAIRS)
    history = case.get("thermal_history", [])
    planned = _require_number(
        "planned_dwell_minutes", case.get("planned_dwell_minutes"), 0.0
    )
    qualified = _require_flag(
        "repair_procedure_qualified", case.get("repair_procedure_qualified")
    )
    cycles_used = len(history) - 1 if history else 0
    if cycles_used < 0:
        cycles_used = 0

    used_dwell = cumulative_dwell(history)
    budget = _DWELL_BUDGET_MINUTES[pair]
    projected = used_dwell + planned
    overshoot = projected - budget
    budget_exceeded = overshoot > DWELL_TOLERANCE_MINUTES
    left = remaining_cycles(category, cycles_used)

    findings = []
    curable = is_reflow_curable(defect)
    if not curable:
        findings.append(
            "%s is a loss of parent material; a further heating deepens it "
            "rather than curing it" % defect
        )
    if left == 0:
        findings.append(
            "the joint has taken %d of the %d re-braze cycles its %s category "
            "allows" % (cycles_used, cycle_limit(category), category)
        )
    if budget_exceeded:
        findings.append(
            "the planned cycle would put the joint %.3f min past the %.1f min "
            "dwell budget of %s" % (overshoot, budget, pair)
        )
    if not qualified:
        findings.append(
            "no qualified repair procedure covers this joint; the repair "
            "cannot be worked to an unqualified process"
        )

    if not curable or budget_exceeded:
        disposition = DISPOSITION_SCRAP
    elif left == 0 or not qualified:
        disposition = DISPOSITION_BOARD
    else:
        disposition = DISPOSITION_REBRAZE

    return {
        "joint_id": joint_id,
        "joint_category": category,
        "defect": defect,
        "reflow_curable": curable,
        "cycles_used": cycles_used,
        "cycle_limit": cycle_limit(category),
        "remaining_cycles": left,
        "cumulative_dwell_minutes": used_dwell,
        "projected_dwell_minutes": projected,
        "dwell_budget_minutes": budget,
        "remaining_dwell_minutes": budget - used_dwell,
        "dwell_budget_exceeded": budget_exceeded,
        "repair_procedure_qualified": qualified,
        "disposition": disposition,
        "reinspection_required": (
            reinspection_set(category, cycles_used + 1)
            if disposition == DISPOSITION_REBRAZE
            else []
        ),
        "findings": findings,
    }
