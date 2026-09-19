"""Applicability and repair types for printed-circuit-board assembly repair.

Anchor: ECSS-Q-ST-70-28C, framework clause -- which hardware the board repair
standard covers, which damage a repair category exists for, which changes are
modifications rather than repairs, and when an item has spent its repair
budget and belongs in nonconformance review instead. Paraphrased into an
implementable triage; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Test the item against the assembly types the standard covers, and name the
   other discipline when it does not.
2. Map the reported damage onto a repair category, and separate the damage for
   which no repair category exists at all.
3. Group a proposed change as a repair or as a modification, and say whether
   the modification obliges a drawing and as-built update.
4. Spend the per-category and per-board repair budgets against the repair
   history the board already carries.
5. Return the triage verdict -- repair, nonconformance review, or out of scope
   -- with every finding that drove it.
"""

import math

__all__ = [
    "IN_SCOPE_ASSEMBLIES",
    "OUT_OF_SCOPE_ASSEMBLIES",
    "DAMAGE_TO_REPAIR_CATEGORY",
    "IRREPARABLE_DAMAGE",
    "MODIFICATION_CATEGORIES",
    "MAX_REPAIRS_PER_CATEGORY",
    "MAX_REPAIRS_PER_BOARD",
    "MAX_DAMAGED_AREA_FRACTION",
    "AREA_TOLERANCE",
    "normalize_token",
    "assembly_scope",
    "repair_category",
    "modification_category",
    "repair_budget",
    "triage_item",
]

# Board constructions the repair standard speaks to.
IN_SCOPE_ASSEMBLIES = (
    "single-sided",
    "double-sided",
    "multilayer",
    "flexible",
    "rigid-flex",
)

# Hardware that looks adjacent but is governed elsewhere; the value names where
# the item actually belongs so the triage does not silently absorb it.
OUT_OF_SCOPE_ASSEMBLIES = {
    "hybrid-microcircuit": "hybrid microcircuit assembly rules",
    "wire-harness": "cable and harness workmanship rules",
    "solar-array-panel": "solar array assembly rules",
    "connector-backshell": "connector and backshell workmanship rules",
    "machined-housing": "mechanical hardware disposition",
}

# Reported damage -> the repair category that owns it.
DAMAGE_TO_REPAIR_CATEGORY = {
    "conductor-open": "conductor-repair",
    "conductor-lifted": "conductor-repair",
    "conductor-nicked": "conductor-repair",
    "land-lifted": "land-repair",
    "land-missing": "land-repair",
    "land-reduced-area": "land-repair",
    "barrel-cracked": "plated-hole-repair",
    "barrel-void": "plated-hole-repair",
    "laminate-measling": "base-material-repair",
    "laminate-gouge": "base-material-repair",
    "solder-resist-damage": "coating-repair",
    "conformal-coating-damage": "coating-repair",
    "component-cracked": "component-replacement",
    "component-wrong-part": "component-replacement",
}

# Damage for which the standard offers no repair at all; the board goes to
# nonconformance review whatever the budgets say.
IRREPARABLE_DAMAGE = {
    "carbonised-laminate": "a conductive carbon path through the base material",
    "burn-through": "loss of base material through the full board thickness",
    "internal-layer-open": "an open conductor on a buried layer, unreachable",
    "delamination-under-component-field": "separation beneath a populated area",
}

# Proposed change -> (category, does it oblige a drawing and as-built update).
MODIFICATION_CATEGORIES = {
    "jumper-wire-added": ("wiring-modification", True),
    "track-cut": ("wiring-modification", True),
    "component-added": ("component-modification", True),
    "component-removed": ("component-modification", True),
    "component-value-change": ("component-modification", True),
    "coating-extended": ("finish-modification", False),
    "marking-corrected": ("finish-modification", False),
}

# Repair budgets a single board carries over its life.
MAX_REPAIRS_PER_CATEGORY = 3
MAX_REPAIRS_PER_BOARD = 10

# The largest fraction of a feature that may be damaged and still repaired.
MAX_DAMAGED_AREA_FRACTION = 0.20

# Fractions are measured quantities; a value exactly on a bound is inside it.
AREA_TOLERANCE = 1e-9


def normalize_token(value, label):
    """Return a lowercase, hyphen-normalised token, raising on anything else."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def _fraction(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (label, number))
    return number


def _count(value, label):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def assembly_scope(assembly_type):
    """Return the scope verdict for one assembly construction."""
    token = normalize_token(assembly_type, "assembly_type")
    if token in IN_SCOPE_ASSEMBLIES:
        return {"assembly_type": token, "in_scope": True, "belongs_to": None}
    if token in OUT_OF_SCOPE_ASSEMBLIES:
        return {
            "assembly_type": token,
            "in_scope": False,
            "belongs_to": OUT_OF_SCOPE_ASSEMBLIES[token],
        }
    raise ValueError(
        "unknown assembly_type '%s'; declare it before triaging the damage" % token
    )


def repair_category(damage_type):
    """Return the repair category that owns a reported damage."""
    token = normalize_token(damage_type, "damage_type")
    if token in IRREPARABLE_DAMAGE:
        return {
            "damage_type": token,
            "category": None,
            "repairable": False,
            "reason": IRREPARABLE_DAMAGE[token],
        }
    if token in DAMAGE_TO_REPAIR_CATEGORY:
        return {
            "damage_type": token,
            "category": DAMAGE_TO_REPAIR_CATEGORY[token],
            "repairable": True,
            "reason": None,
        }
    raise ValueError(
        "unknown damage_type '%s'; an undescribed damage cannot be triaged" % token
    )


def modification_category(change_type):
    """Group a proposed change and say whether the drawing set must follow."""
    token = normalize_token(change_type, "change_type")
    if token not in MODIFICATION_CATEGORIES:
        raise ValueError("unknown change_type '%s'" % token)
    category, drawing_update = MODIFICATION_CATEGORIES[token]
    return {
        "change_type": token,
        "category": category,
        "drawing_update_required": drawing_update,
        "as_built_update_required": drawing_update,
    }


def repair_budget(prior_same_category, prior_total):
    """Return what is left of the per-category and per-board repair budgets."""
    same = _count(prior_same_category, "prior_same_category")
    total = _count(prior_total, "prior_total")
    if same > total:
        raise ValueError(
            "prior_same_category (%d) cannot exceed prior_total (%d)" % (same, total)
        )
    return {
        "prior_same_category": same,
        "prior_total": total,
        "category_remaining": max(0, MAX_REPAIRS_PER_CATEGORY - same),
        "board_remaining": max(0, MAX_REPAIRS_PER_BOARD - total),
        "category_exhausted": same >= MAX_REPAIRS_PER_CATEGORY,
        "board_exhausted": total >= MAX_REPAIRS_PER_BOARD,
    }


def triage_item(item):
    """Triage one damage report and return the disposition with its findings.

    item keys: assembly_type, damage_type, optional damaged_area_fraction,
    prior_repairs_same_category, prior_repairs_total and change_type.
    """
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    for key in ("assembly_type", "damage_type"):
        if key not in item:
            raise ValueError("item missing required key '%s'" % key)

    findings = []
    scope = assembly_scope(item["assembly_type"])
    if not scope["in_scope"]:
        findings.append(
            "assembly type '%s' is outside the board repair standard; it belongs to "
            "the %s" % (scope["assembly_type"], scope["belongs_to"])
        )

    damage = repair_category(item["damage_type"])
    if not damage["repairable"]:
        findings.append(
            "damage '%s' has no repair category: %s"
            % (damage["damage_type"], damage["reason"])
        )

    fraction = _fraction(item.get("damaged_area_fraction", 0.0), "damaged_area_fraction")
    if fraction > MAX_DAMAGED_AREA_FRACTION + AREA_TOLERANCE:
        findings.append(
            "damaged area fraction of %g exceeds the %g allowed for a repair"
            % (fraction, MAX_DAMAGED_AREA_FRACTION)
        )

    budget = repair_budget(
        item.get("prior_repairs_same_category", 0), item.get("prior_repairs_total", 0)
    )
    if budget["category_exhausted"]:
        findings.append(
            "the board already carries %d repairs in this category, the limit of %d"
            % (budget["prior_same_category"], MAX_REPAIRS_PER_CATEGORY)
        )
    if budget["board_exhausted"]:
        findings.append(
            "the board already carries %d repairs in total, the limit of %d"
            % (budget["prior_total"], MAX_REPAIRS_PER_BOARD)
        )

    modification = None
    if item.get("change_type") is not None:
        modification = modification_category(item["change_type"])
        if modification["drawing_update_required"]:
            findings.append(
                "change '%s' is a %s and obliges a drawing and as-built update, not a "
                "repair record alone"
                % (modification["change_type"], modification["category"])
            )

    if not scope["in_scope"]:
        disposition = "out-of-scope"
    elif findings:
        disposition = "nonconformance-review"
    else:
        disposition = "repair"

    return {
        "assembly_type": scope["assembly_type"],
        "in_scope": scope["in_scope"],
        "damage_type": damage["damage_type"],
        "repair_category": damage["category"],
        "damage_repairable": damage["repairable"],
        "damaged_area_fraction": fraction,
        "budget": budget,
        "modification": modification,
        "disposition": disposition,
        "findings": findings,
        "ready": not findings,
    }
