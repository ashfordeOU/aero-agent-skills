"""Cleanliness budget allocation across system, subsystem and unit levels.

Anchor: ECSS-Q-ST-70-01C, the cleanliness *levels* clause -- turning one
end-of-life contamination allowance on a critical surface into allocations
the system, its subsystems and their units can each be held to. Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold a reserve back at system level before anything is allocated, so late
   contributors are not funded by taking allocation away from an existing one.
2. Split the remaining allowance over the contributors by declared weight, or
   accept allocations the project has already fixed.
3. Roll the tree up from the units: contamination contributions are deposited
   masses and add linearly; an uncertainty band on a contribution is combined
   in quadrature instead.
4. Close the tree at every node: the demand rolled up from a node's children
   may not exceed that node's allocation, and unspent allocation is reported
   as headroom rather than silently absorbed.
5. Report per-node allocation, rolled-up demand, headroom and the findings a
   reviewer needs: overruns, unallocated reserve, and level-order violations.
"""

import math

__all__ = [
    "CLOSURE_TOLERANCE",
    "LEVEL_ORDER",
    "validate_budget_value",
    "validate_level",
    "hold_reserve",
    "allocate_by_weight",
    "combine_linear",
    "combine_quadrature",
    "combine",
    "validate_node",
    "roll_up",
    "close_node",
    "assess_budget",
]

# Closure is an equality between a sum and an allocation, both carried in
# floating point. An exact closure can land a few ULPs either side; absorb the
# representation error here instead of relaxing the allocation.
CLOSURE_TOLERANCE = 1e-12

# Decomposition order. A node's children must sit strictly lower than it.
LEVEL_ORDER = ("system", "subsystem", "unit")


def validate_budget_value(value, label, allow_zero=True):
    """Return a finite, non-negative budget quantity as a float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    if v < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    if not allow_zero and v == 0.0:
        raise ValueError("%s must be strictly positive" % label)
    return v


def validate_level(level):
    """Return the index of a decomposition level name."""
    if not isinstance(level, str):
        raise ValueError("level must be a string")
    if level not in LEVEL_ORDER:
        raise ValueError("level %r must be one of %s" % (level, list(LEVEL_ORDER)))
    return LEVEL_ORDER.index(level)


def hold_reserve(total, reserve_fraction):
    """Return (allocatable, reserve) after holding a system-level reserve."""
    budget = validate_budget_value(total, "total", allow_zero=False)
    fraction = validate_budget_value(reserve_fraction, "reserve_fraction")
    if fraction >= 1.0:
        raise ValueError(
            "reserve_fraction %g leaves nothing to allocate" % fraction
        )
    reserve = budget * fraction
    return (budget - reserve, reserve)


def allocate_by_weight(allocatable, weights):
    """Split an allocatable budget over named contributors by weight."""
    pot = validate_budget_value(allocatable, "allocatable", allow_zero=False)
    if not isinstance(weights, dict) or not weights:
        raise ValueError("weights must be a non-empty mapping of name to weight")
    total_weight = 0.0
    cleaned = {}
    for name, weight in weights.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("weight key must be a non-empty string")
        w = validate_budget_value(weight, "weight for %r" % name)
        cleaned[name] = w
        total_weight += w
    if total_weight <= 0.0:
        raise ValueError("weights must not all be zero")
    return {name: pot * w / total_weight for name, w in cleaned.items()}


def combine_linear(values):
    """Add deposited-mass contributions, which superpose directly."""
    if not isinstance(values, (list, tuple)):
        raise ValueError("values must be a sequence")
    return math.fsum(
        validate_budget_value(v, "contribution[%d]" % i) for i, v in enumerate(values)
    )


def combine_quadrature(values):
    """Combine independent uncertainty bands in quadrature."""
    if not isinstance(values, (list, tuple)):
        raise ValueError("values must be a sequence")
    squares = [
        validate_budget_value(v, "contribution[%d]" % i) ** 2
        for i, v in enumerate(values)
    ]
    return math.sqrt(math.fsum(squares))


def combine(values, method="linear"):
    """Combine contributions by the named method."""
    if method == "linear":
        return combine_linear(values)
    if method == "quadrature":
        return combine_quadrature(values)
    raise ValueError("method %r must be 'linear' or 'quadrature'" % (method,))


def validate_node(node, parent_level_index=None):
    """Validate one allocation node and return its level index."""
    if not isinstance(node, dict):
        raise ValueError("each node must be a mapping")
    for key in ("name", "level", "allocation"):
        if key not in node:
            raise ValueError("node missing required key %r" % key)
    name = node["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("node name must be a non-empty string")
    index = validate_level(node["level"])
    if parent_level_index is not None and index <= parent_level_index:
        raise ValueError(
            "node %r at level %r may not sit under a %r node"
            % (name, node["level"], LEVEL_ORDER[parent_level_index])
        )
    validate_budget_value(node["allocation"], "allocation of %r" % name)
    children = node.get("children") or []
    if not isinstance(children, (list, tuple)):
        raise ValueError("children of %r must be a sequence" % name)
    seen = set()
    for child in children:
        child_name = child.get("name") if isinstance(child, dict) else None
        if child_name in seen:
            raise ValueError("node %r has two children called %r" % (name, child_name))
        seen.add(child_name)
        validate_node(child, index)
    return index


def roll_up(node, method="linear"):
    """Return the demand a node places on its parent's allocation.

    A node with children demands the combination of their rolled-up demands; a
    node without children demands its own allocation.
    """
    validate_node(node)
    children = node.get("children") or []
    if not children:
        return validate_budget_value(node["allocation"], "allocation")
    return combine([roll_up(child, method) for child in children], method)


def close_node(node, method="linear"):
    """Return the closure record for one node against its own allocation."""
    validate_node(node)
    allocation = validate_budget_value(node["allocation"], "allocation")
    children = node.get("children") or []
    demand = roll_up(node, method)
    headroom = allocation - demand
    closed = headroom > 0.0 or math.isclose(
        headroom, 0.0, rel_tol=0.0, abs_tol=CLOSURE_TOLERANCE
    )
    return {
        "name": node["name"],
        "level": node["level"],
        "allocation": allocation,
        "demand": demand,
        "headroom": headroom,
        "closed": closed,
        "children": len(children),
    }


def _walk(node, method, records, findings):
    record = close_node(node, method)
    records.append(record)
    if not record["closed"]:
        findings.append(
            "%s %r is over-subscribed: children demand %.6g against an allocation "
            "of %.6g" % (node["level"], node["name"], record["demand"], record["allocation"])
        )
    for child in node.get("children") or []:
        _walk(child, method, records, findings)


def assess_budget(spec):
    """Run the full allocation-and-closure step for a cleanliness budget.

    spec keys: total, root (an allocation node), optional reserve_fraction
    (default 0.0), optional method ('linear' or 'quadrature'), optional
    headroom_warning_fraction (report an allocation left largely unspent).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("total", "root"):
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    method = spec.get("method", "linear")
    if method not in ("linear", "quadrature"):
        raise ValueError("method %r must be 'linear' or 'quadrature'" % (method,))
    allocatable, reserve = hold_reserve(spec["total"], spec.get("reserve_fraction", 0.0))
    root = spec["root"]
    validate_node(root)
    root_allocation = validate_budget_value(root["allocation"], "root allocation")
    findings = []
    if root_allocation > allocatable and not math.isclose(
        root_allocation, allocatable, rel_tol=0.0, abs_tol=CLOSURE_TOLERANCE
    ):
        findings.append(
            "root allocation %.6g exceeds the allocatable budget %.6g left after "
            "the reserve" % (root_allocation, allocatable)
        )
    records = []
    _walk(root, method, records, findings)
    warn = spec.get("headroom_warning_fraction")
    if warn is not None:
        warn = validate_budget_value(warn, "headroom_warning_fraction")
        for record in records:
            if record["children"] and record["allocation"] > 0.0:
                unspent = record["headroom"] / record["allocation"]
                if unspent > warn:
                    findings.append(
                        "%s %r leaves %.1f%% of its allocation unallocated"
                        % (record["level"], record["name"], 100.0 * unspent)
                    )
    return {
        "total": validate_budget_value(spec["total"], "total", allow_zero=False),
        "reserve": reserve,
        "allocatable": allocatable,
        "method": method,
        "records": records,
        "closed": all(r["closed"] for r in records) and not findings,
        "findings": findings,
    }
