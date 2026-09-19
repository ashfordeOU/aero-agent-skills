#!/usr/bin/env python3
"""Property degradation assessment after a sterilization-compatibility exposure.

Anchor: ECSS-Q-ST-70-53C, evaluation clauses for materials and hardware
subjected to a sterilization process. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every property record: positive finite baseline, finite exposed
   value, known evaluation category, known limit direction, positive allowable
   change, non-negative measurement resolution.
2. Form the relative change against the property's own baseline, collapsing a
   difference smaller than the measurement resolution to zero and marking the
   property resolution-limited.
3. Convert the signed change into an adverse fraction using the direction of
   the limit: loss for loss-limited, gain for gain-limited, magnitude for
   two-sided. A favourable change is not degradation.
4. Compare the adverse fraction with the allowable change, absorbing
   representation error at the boundary with a named tolerance.
5. Roll the graded records up per evaluation category and name the governing
   property as the highest utilisation of its own allowable change.
6. Report findings: properties over their limit, and evaluation categories
   that carry no measured property.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "MECHANICAL",
    "PHYSICAL",
    "FUNCTIONAL",
    "CATEGORIES",
    "LOSS_LIMITED",
    "GAIN_LIMITED",
    "TWO_SIDED",
    "DIRECTIONS",
    "validate_property_record",
    "relative_change",
    "adverse_fraction",
    "grade_property",
    "rollup_by_category",
    "governing_property",
    "assess_property_degradation",
]

# A limit comparison is a comparison of ratios: a physically exact equality can
# land a few ULPs on the wrong side. Absorb the representation error here
# instead of relaxing the specified allowable change.
LIMIT_TOLERANCE = 1e-12

MECHANICAL = "mechanical"
PHYSICAL = "physical"
FUNCTIONAL = "functional"
CATEGORIES = (MECHANICAL, PHYSICAL, FUNCTIONAL)

LOSS_LIMITED = "loss-limited"
GAIN_LIMITED = "gain-limited"
TWO_SIDED = "two-sided"
DIRECTIONS = (LOSS_LIMITED, GAIN_LIMITED, TWO_SIDED)


def _real(value, label):
    """Return value as a finite float, or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def validate_property_record(record):
    """Return a normalised property record, or raise on a malformed one."""
    if not isinstance(record, dict):
        raise ValueError("property record must be a mapping, got %r" % (record,))
    for key in ("name", "category", "direction", "allowable_change", "baseline", "exposed"):
        if key not in record:
            raise ValueError("property record missing required key '%s'" % key)
    name = record["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("property name must be a non-empty string, got %r" % (name,))
    category = record["category"]
    if category not in CATEGORIES:
        raise ValueError(
            "category must be one of %s, got %r" % (", ".join(CATEGORIES), category)
        )
    direction = record["direction"]
    if direction not in DIRECTIONS:
        raise ValueError(
            "direction must be one of %s, got %r" % (", ".join(DIRECTIONS), direction)
        )
    allowable = _real(record["allowable_change"], "allowable_change")
    if allowable <= 0.0:
        raise ValueError("allowable_change must be positive, got %g" % allowable)
    baseline = _real(record["baseline"], "baseline")
    if baseline <= 0.0:
        raise ValueError("baseline must be positive, got %g" % baseline)
    exposed = _real(record["exposed"], "exposed")
    if exposed < 0.0:
        raise ValueError("exposed must be non-negative, got %g" % exposed)
    resolution = _real(record.get("resolution", 0.0), "resolution")
    if resolution < 0.0:
        raise ValueError("resolution must be non-negative, got %g" % resolution)
    return {
        "name": name.strip(),
        "category": category,
        "direction": direction,
        "allowable_change": allowable,
        "baseline": baseline,
        "exposed": exposed,
        "resolution": resolution,
    }


def relative_change(baseline, exposed, resolution=0.0):
    """Return (change_fraction, resolution_limited) for one property."""
    base = _real(baseline, "baseline")
    if base <= 0.0:
        raise ValueError("baseline must be positive, got %g" % base)
    post = _real(exposed, "exposed")
    res = _real(resolution, "resolution")
    if res < 0.0:
        raise ValueError("resolution must be non-negative, got %g" % res)
    difference = post - base
    if res > 0.0 and abs(difference) <= res * (1.0 + LIMIT_TOLERANCE):
        return (0.0, True)
    return (difference / base, False)


def adverse_fraction(direction, change_fraction):
    """Return the degradation magnitude implied by a signed relative change."""
    if direction not in DIRECTIONS:
        raise ValueError(
            "direction must be one of %s, got %r" % (", ".join(DIRECTIONS), direction)
        )
    change = _real(change_fraction, "change_fraction")
    if direction == LOSS_LIMITED:
        return max(0.0, -change)
    if direction == GAIN_LIMITED:
        return max(0.0, change)
    return abs(change)


def grade_property(record):
    """Grade one property record against its own allowable change."""
    item = validate_property_record(record)
    change, resolution_limited = relative_change(
        item["baseline"], item["exposed"], item["resolution"]
    )
    adverse = adverse_fraction(item["direction"], change)
    allowable = item["allowable_change"]
    utilisation = adverse / allowable
    within = adverse < allowable or math.isclose(
        adverse, allowable, rel_tol=LIMIT_TOLERANCE, abs_tol=0.0
    )
    return {
        "name": item["name"],
        "category": item["category"],
        "direction": item["direction"],
        "baseline": item["baseline"],
        "exposed": item["exposed"],
        "change_fraction": change,
        "adverse_fraction": adverse,
        "allowable_change": allowable,
        "utilisation": utilisation,
        "margin_fraction": allowable - adverse,
        "resolution_limited": resolution_limited,
        "within_limit": within,
    }


def rollup_by_category(graded):
    """Group graded property records by evaluation category."""
    if not isinstance(graded, (list, tuple)) or not graded:
        raise ValueError("graded must be a non-empty sequence of graded records")
    rollup = {}
    for category in CATEGORIES:
        rollup[category] = {
            "measured": 0,
            "within_limit": True,
            "worst_property": None,
            "worst_utilisation": 0.0,
        }
    for record in graded:
        if not isinstance(record, dict) or "category" not in record:
            raise ValueError("each graded record must be a mapping carrying 'category'")
        category = record["category"]
        if category not in rollup:
            raise ValueError("unknown evaluation category %r" % (category,))
        bucket = rollup[category]
        bucket["measured"] += 1
        if not record["within_limit"]:
            bucket["within_limit"] = False
        if bucket["worst_property"] is None or record["utilisation"] > bucket["worst_utilisation"]:
            bucket["worst_property"] = record["name"]
            bucket["worst_utilisation"] = record["utilisation"]
    return rollup


def governing_property(graded):
    """Return the graded record with the highest utilisation of its own limit."""
    if not isinstance(graded, (list, tuple)) or not graded:
        raise ValueError("graded must be a non-empty sequence of graded records")
    governing = None
    for record in graded:
        if not isinstance(record, dict) or "utilisation" not in record:
            raise ValueError("each graded record must be a mapping carrying 'utilisation'")
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


def assess_property_degradation(spec):
    """Run the full ECSS-Q-ST-70-53C property-degradation evaluation.

    spec keys: item_id (optional string), properties (non-empty sequence of
    property records as accepted by validate_property_record).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "properties" not in spec:
        raise ValueError("spec missing required key 'properties'")
    properties = spec["properties"]
    if not isinstance(properties, (list, tuple)) or not properties:
        raise ValueError("spec['properties'] must be a non-empty sequence")
    graded = [grade_property(record) for record in properties]
    seen = set()
    for record in graded:
        if record["name"] in seen:
            raise ValueError("duplicate property name %r in spec" % (record["name"],))
        seen.add(record["name"])
    rollup = rollup_by_category(graded)
    governing = governing_property(graded)
    findings = []
    for record in graded:
        if not record["within_limit"]:
            findings.append(
                "property '%s' (%s) degraded by %.4f against an allowable %.4f"
                % (record["name"], record["category"],
                   record["adverse_fraction"], record["allowable_change"])
            )
    for category in CATEGORIES:
        if rollup[category]["measured"] == 0:
            findings.append(
                "evaluation category '%s' carries no measured property" % category
            )
    complete = all(rollup[category]["measured"] > 0 for category in CATEGORIES)
    return {
        "item_id": spec.get("item_id"),
        "graded": graded,
        "rollup": rollup,
        "governing_property": governing,
        "categories_complete": complete,
        "acceptable": all(record["within_limit"] for record in graded) and complete,
        "findings": findings,
    }
