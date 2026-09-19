#!/usr/bin/env python3
"""Acceptance criteria for a sterilization-compatibility evaluation.

Anchor: ECSS-Q-ST-70-53C, acceptance clauses. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Resolve the item's category: a declared single category, or the most
   severe of its constituent categories under the declared severity order.
2. Select the criteria set that category carries; refuse an unknown category
   instead of falling back to a default set.
3. Check that every criterion in the set has a measurement. A criterion with
   no measurement is unevidenced and blocks the accept.
4. Apply each criterion in its own direction: a floor for a retention
   fraction, a ceiling for a loss or a change.
5. For each breach, decide whether it falls inside that criterion's deviation
   band; a breach beyond the band can never be accepted.
6. Name the governing criterion by utilisation of its own limit, and decide
   accept, accept-with-deviation (band plus a recorded deviation reference)
   or reject.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "FLOOR",
    "CEILING",
    "DIRECTIONS",
    "ACCEPT",
    "ACCEPT_WITH_DEVIATION",
    "REJECT",
    "DEFAULT_ACCEPTANCE_CRITERIA",
    "DEFAULT_CATEGORY_SEVERITY",
    "validate_criterion",
    "criteria_for_category",
    "resolve_assembly_category",
    "criterion_utilisation",
    "apply_criterion",
    "governing_criterion",
    "decide_acceptance",
]

# Criterion comparisons are ratios against a specified limit: an exact
# equality can land a few ULPs on the wrong side. Absorb the representation
# error here instead of relaxing the specified limit.
LIMIT_TOLERANCE = 1e-12

FLOOR = "floor"
CEILING = "ceiling"
DIRECTIONS = (FLOOR, CEILING)

ACCEPT = "accept"
ACCEPT_WITH_DEVIATION = "accept-with-deviation"
REJECT = "reject"

# Default criteria sets, one per material or hardware category. A project may
# substitute its own table; this one is the fallback used when none is given.
DEFAULT_ACCEPTANCE_CRITERIA = {
    "polymer": {
        "mass-loss-fraction": {"direction": CEILING, "limit": 0.02, "deviation_band": 0.005},
        "mechanical-retention-fraction": {"direction": FLOOR, "limit": 0.80, "deviation_band": 0.05},
        "dimensional-change-fraction": {"direction": CEILING, "limit": 0.01, "deviation_band": 0.002},
    },
    "metal": {
        "mass-change-fraction": {"direction": CEILING, "limit": 0.001, "deviation_band": 0.0002},
        "mechanical-retention-fraction": {"direction": FLOOR, "limit": 0.95, "deviation_band": 0.02},
    },
    "adhesive": {
        "bond-strength-retention-fraction": {"direction": FLOOR, "limit": 0.85, "deviation_band": 0.05},
        "mass-loss-fraction": {"direction": CEILING, "limit": 0.02, "deviation_band": 0.005},
    },
    "optical": {
        "transmittance-retention-fraction": {"direction": FLOOR, "limit": 0.98, "deviation_band": 0.01},
        "surface-obscuration-percent": {"direction": CEILING, "limit": 0.025, "deviation_band": 0.005},
    },
    "electronic-assembly": {
        "functional-index": {"direction": FLOOR, "limit": 1.0, "deviation_band": 0.0},
        "insulation-resistance-retention-fraction": {"direction": FLOOR, "limit": 0.90, "deviation_band": 0.05},
    },
}

# Severity order over categories, least severe first. The most severe
# constituent governs a mixed assembly.
DEFAULT_CATEGORY_SEVERITY = (
    "metal",
    "optical",
    "adhesive",
    "polymer",
    "electronic-assembly",
)


def _real(value, label):
    """Return value as a finite float, or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def validate_criterion(criterion, name="criterion"):
    """Return a normalised criterion definition, or raise."""
    if not isinstance(criterion, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, criterion))
    direction = criterion.get("direction")
    if direction not in DIRECTIONS:
        raise ValueError(
            "%s direction must be one of %s, got %r"
            % (name, ", ".join(DIRECTIONS), direction)
        )
    if "limit" not in criterion:
        raise ValueError("%s missing 'limit'" % name)
    limit = _real(criterion["limit"], "%s limit" % name)
    if limit <= 0.0:
        raise ValueError("%s limit must be positive, got %g" % (name, limit))
    band = _real(criterion.get("deviation_band", 0.0), "%s deviation_band" % name)
    if band < 0.0:
        raise ValueError("%s deviation_band must be non-negative, got %g" % (name, band))
    return {"direction": direction, "limit": limit, "deviation_band": band}


def criteria_for_category(category, table=None):
    """Return the validated criteria set a category carries."""
    criteria_table = DEFAULT_ACCEPTANCE_CRITERIA if table is None else table
    if not isinstance(criteria_table, dict) or not criteria_table:
        raise ValueError("criteria table must be a non-empty mapping")
    if not isinstance(category, str) or not category.strip():
        raise ValueError("category must be a non-empty string, got %r" % (category,))
    key = category.strip()
    if key not in criteria_table:
        raise ValueError(
            "no acceptance criteria for category %r; known categories: %s"
            % (key, ", ".join(sorted(criteria_table)))
        )
    entries = criteria_table[key]
    if not isinstance(entries, dict) or not entries:
        raise ValueError("criteria set for category %r must be a non-empty mapping" % key)
    return {
        name: validate_criterion(definition, "criterion %r" % name)
        for name, definition in entries.items()
    }


def resolve_assembly_category(categories, severity=None, table=None):
    """Return the most severe category among an assembly's constituents."""
    order = DEFAULT_CATEGORY_SEVERITY if severity is None else severity
    if not isinstance(order, (list, tuple)) or not order:
        raise ValueError("severity order must be a non-empty sequence")
    if len(set(order)) != len(order):
        raise ValueError("severity order must not repeat a category")
    if not isinstance(categories, (list, tuple)) or not categories:
        raise ValueError("categories must be a non-empty sequence")
    resolved = None
    rank = -1
    for category in categories:
        if not isinstance(category, str) or not category.strip():
            raise ValueError("constituent category must be a non-empty string")
        key = category.strip()
        if key not in order:
            raise ValueError(
                "category %r has no place in the severity order %s"
                % (key, ", ".join(order))
            )
        # Confirm the category is actually gradable before it can govern.
        criteria_for_category(key, table)
        position = order.index(key)
        if position > rank:
            rank = position
            resolved = key
    return resolved


def criterion_utilisation(criterion, measured, name="criterion"):
    """Return how much of its own limit a measurement uses (1.0 is the limit)."""
    spec = validate_criterion(criterion, name)
    value = _real(measured, "%s measurement" % name)
    if spec["direction"] == CEILING:
        if value < 0.0:
            raise ValueError("%s measurement must be non-negative for a ceiling" % name)
        return value / spec["limit"]
    if value <= 0.0:
        raise ValueError("%s measurement must be positive for a floor" % name)
    return spec["limit"] / value


def apply_criterion(criterion, measured, name="criterion"):
    """Grade one measurement against one criterion."""
    spec = validate_criterion(criterion, name)
    value = _real(measured, "%s measurement" % name)
    limit = spec["limit"]
    band = spec["deviation_band"]
    if spec["direction"] == CEILING:
        within_limit = value < limit or math.isclose(
            value, limit, rel_tol=LIMIT_TOLERANCE, abs_tol=0.0
        )
        band_edge = limit + band
        within_band = value < band_edge or math.isclose(
            value, band_edge, rel_tol=LIMIT_TOLERANCE, abs_tol=0.0
        )
        exceedance = max(0.0, value - limit)
    else:
        within_limit = value > limit or math.isclose(
            value, limit, rel_tol=LIMIT_TOLERANCE, abs_tol=0.0
        )
        band_edge = limit - band
        within_band = value > band_edge or math.isclose(
            value, band_edge, rel_tol=LIMIT_TOLERANCE, abs_tol=0.0
        )
        exceedance = max(0.0, limit - value)
    return {
        "name": name,
        "direction": spec["direction"],
        "limit": limit,
        "deviation_band": band,
        "measured": value,
        "within_limit": within_limit,
        "within_deviation_band": within_band,
        "exceedance": exceedance,
        "utilisation": criterion_utilisation(criterion, measured, name),
    }


def governing_criterion(graded):
    """Return the graded criterion with the highest utilisation of its limit."""
    if not isinstance(graded, (list, tuple)) or not graded:
        raise ValueError("graded must be a non-empty sequence of graded criteria")
    governing = None
    for record in graded:
        if not isinstance(record, dict) or "utilisation" not in record:
            raise ValueError("each graded criterion must carry 'utilisation'")
        if governing is None:
            governing = record
            continue
        if math.isclose(record["utilisation"], governing["utilisation"],
                        rel_tol=LIMIT_TOLERANCE, abs_tol=0.0):
            if record["name"] < governing["name"]:
                governing = record
        elif record["utilisation"] > governing["utilisation"]:
            governing = record
    return governing


def decide_acceptance(spec):
    """Run the full ECSS-Q-ST-70-53C acceptance decision for one item.

    spec keys: measurements (mapping of criterion name to value), and either
    category or constituent_categories. Optional: item_id, criteria_table,
    severity_order, deviation_reference.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "measurements" not in spec:
        raise ValueError("spec missing required key 'measurements'")
    measurements = spec["measurements"]
    if not isinstance(measurements, dict):
        raise ValueError("spec['measurements'] must be a mapping")
    table = spec.get("criteria_table")
    if "category" in spec and spec["category"] is not None:
        category = spec["category"]
        if "constituent_categories" in spec and spec["constituent_categories"]:
            raise ValueError("give 'category' or 'constituent_categories', not both")
        criteria_for_category(category, table)
        resolved = category.strip() if isinstance(category, str) else category
        if not isinstance(resolved, str):
            raise ValueError("category must be a string")
    elif spec.get("constituent_categories"):
        resolved = resolve_assembly_category(
            spec["constituent_categories"], spec.get("severity_order"), table
        )
    else:
        raise ValueError("spec needs 'category' or 'constituent_categories'")
    criteria = criteria_for_category(resolved, table)

    findings = []
    unevidenced = sorted(name for name in criteria if name not in measurements)
    for name in unevidenced:
        findings.append("criterion '%s' has no measurement; unevidenced, not satisfied" % name)
    unclaimed = sorted(name for name in measurements if name not in criteria)
    for name in unclaimed:
        findings.append(
            "measurement '%s' matches no criterion in category '%s'" % (name, resolved)
        )

    graded = []
    for name in sorted(criteria):
        if name in measurements:
            graded.append(apply_criterion(criteria[name], measurements[name], name))
    breaches = [record for record in graded if not record["within_limit"]]
    beyond_band = [record for record in breaches if not record["within_deviation_band"]]
    for record in breaches:
        findings.append(
            "criterion '%s' breached by %.6g against a limit of %.6g (%s the deviation band)"
            % (
                record["name"],
                record["exceedance"],
                record["limit"],
                "inside" if record["within_deviation_band"] else "beyond",
            )
        )
    reference = spec.get("deviation_reference")
    has_reference = isinstance(reference, str) and bool(reference.strip())
    if breaches and not beyond_band and not has_reference:
        findings.append(
            "every breach is inside its deviation band but no deviation reference is recorded"
        )

    if unevidenced or beyond_band:
        decision = REJECT
    elif not breaches:
        decision = ACCEPT
    elif has_reference:
        decision = ACCEPT_WITH_DEVIATION
    else:
        decision = REJECT
    return {
        "item_id": spec.get("item_id"),
        "category": resolved,
        "graded": graded,
        "unevidenced_criteria": unevidenced,
        "unclaimed_measurements": unclaimed,
        "breaches": [record["name"] for record in breaches],
        "beyond_deviation_band": [record["name"] for record in beyond_band],
        "governing_criterion": governing_criterion(graded) if graded else None,
        "deviation_reference": reference if has_reference else None,
        "decision": decision,
        "findings": findings,
    }
