"""Multipactor deliverables per design-review gate (ECSS-E-ST-20-01C Annex A).

Deterministic, offline, stdlib-only. The module answers three questions for a
multipactor verification programme:

1. which multipactor data-items are owed at a given design-review gate, for the
   verification-routes the project actually declared;
2. whether the set submitted at that gate is complete and mature enough;
3. where the first blocking gate sits across the whole review sequence.

No ECSS text is reproduced; the clause is cited as an anchor only.
"""

import math

__all__ = [
    "GATE_SEQUENCE",
    "MATURITY_LADDER",
    "ROUTES",
    "catalogue",
    "normalize_gate",
    "gate_index",
    "normalize_route",
    "normalize_routes",
    "normalize_maturity",
    "maturity_rank",
    "owed_items",
    "deliverable_window",
    "required_maturity",
    "expected_deliverables",
    "deliverable_schedule",
    "normalize_submissions",
    "evaluate_gate",
    "gate_readiness",
    "meets_readiness_threshold",
    "roll_up_reviews",
]

# Design-review gates in the order Annex A walks them.
GATE_SEQUENCE = ("srr", "pdr", "cdr", "qr", "ar")

_GATE_ALIASES = {
    "system-requirements-review": "srr",
    "preliminary-design-review": "pdr",
    "critical-design-review": "cdr",
    "qualification-review": "qr",
    "acceptance-review": "ar",
}

# Document maturity ladder: a delivery may exceed the owed rank, never fall below.
MATURITY_LADDER = ("draft", "issued", "approved")

# Verification routes a multipactor-critical item may be assigned.
ROUTES = ("multipactor-test", "susceptibility-analysis", "similarity-justification")

# data-item -> (first gate issued, gate by which it is approved)
_ROUTE_INDEPENDENT = {
    "multipactor-critical-item-list": ("srr", "cdr"),
    "multipactor-verification-plan": ("pdr", "cdr"),
    "multipactor-free-declaration": ("qr", "ar"),
}

_ROUTE_DEPENDENT = {
    "multipactor-test": {
        "multipactor-test-procedure": ("cdr", "qr"),
        "multipactor-test-report": ("qr", "qr"),
    },
    "susceptibility-analysis": {
        "multipactor-susceptibility-analysis-report": ("pdr", "cdr"),
        "secondary-emission-yield-data-package": ("pdr", "cdr"),
    },
    "similarity-justification": {
        "similarity-justification-dossier": ("pdr", "cdr"),
    },
}

_READINESS_TOLERANCE = 1e-12


def catalogue():
    """Every multipactor data-item id known to this leaf, sorted."""
    names = set(_ROUTE_INDEPENDENT)
    for items in _ROUTE_DEPENDENT.values():
        names.update(items)
    return tuple(sorted(names))


def _as_token(value, what):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (what, type(value).__name__))
    token = value.strip().lower()
    if not token:
        raise ValueError("%s must not be empty" % what)
    return token


def normalize_gate(gate):
    """Canonical short gate code ('pdr'). ValueError on an unknown milestone."""
    token = _as_token(gate, "gate")
    token = _GATE_ALIASES.get(token, token)
    if token not in GATE_SEQUENCE:
        raise ValueError(
            "unknown design-review gate %r; expected one of %s"
            % (gate, ", ".join(GATE_SEQUENCE))
        )
    return token


def gate_index(gate):
    """Position of a gate in the review sequence (0-based)."""
    return GATE_SEQUENCE.index(normalize_gate(gate))


def normalize_route(route):
    """Canonical verification-route token. ValueError on an unknown route."""
    token = _as_token(route, "verification route")
    if token not in ROUTES:
        raise ValueError(
            "unknown verification route %r; expected one of %s"
            % (route, ", ".join(ROUTES))
        )
    return token


def normalize_routes(routes):
    """Sorted, de-duplicated route tuple. ValueError on an empty declaration."""
    if isinstance(routes, str):
        routes = [routes]
    try:
        items = list(routes)
    except TypeError:
        raise ValueError("routes must be an iterable of route tokens")
    if not items:
        raise ValueError("at least one verification route must be declared")
    return tuple(sorted({normalize_route(r) for r in items}))


def normalize_maturity(status):
    """Canonical document-maturity token. ValueError outside the ladder."""
    token = _as_token(status, "maturity")
    if token not in MATURITY_LADDER:
        raise ValueError(
            "unknown document maturity %r; expected one of %s"
            % (status, ", ".join(MATURITY_LADDER))
        )
    return token


def maturity_rank(status):
    """Ordinal rank of a maturity (draft=0 < issued=1 < approved=2)."""
    return MATURITY_LADDER.index(normalize_maturity(status))


def owed_items(routes):
    """Mapping of every data-item owed by the declared routes to its window."""
    declared = normalize_routes(routes)
    owed = dict(_ROUTE_INDEPENDENT)
    for route in declared:
        owed.update(_ROUTE_DEPENDENT[route])
    return owed


def deliverable_window(deliverable, routes):
    """(first_gate, final_gate) for a data-item under the declared routes."""
    name = _as_token(deliverable, "deliverable")
    if name not in catalogue():
        raise ValueError("unknown multipactor data-item %r" % (deliverable,))
    owed = owed_items(routes)
    if name not in owed:
        raise ValueError(
            "data-item %r belongs to a verification route that was not declared"
            % (deliverable,)
        )
    return owed[name]


def required_maturity(deliverable, gate, routes):
    """Maturity owed at `gate`, or None when the item is not yet due."""
    first, final = deliverable_window(deliverable, routes)
    here = gate_index(gate)
    if here < gate_index(first):
        return None
    if here >= gate_index(final):
        return "approved"
    if here == gate_index(first):
        return "draft"
    return "issued"


def expected_deliverables(gate, routes):
    """Owed data-item -> required maturity at this gate (due items only)."""
    checked = normalize_gate(gate)
    expected = {}
    for name in sorted(owed_items(routes)):
        owed = required_maturity(name, checked, routes)
        if owed is not None:
            expected[name] = owed
    return expected


def deliverable_schedule(routes):
    """Full gate -> {data-item: required maturity} schedule."""
    return {gate: expected_deliverables(gate, routes) for gate in GATE_SEQUENCE}


def normalize_submissions(entries):
    """Submitted set -> {data-item: maturity}.

    Accepts a mapping or an iterable of mappings carrying 'deliverable' and
    'maturity'. Raises ValueError on an unknown id, a missing maturity or a
    duplicate submission of the same data-item.
    """
    known = catalogue()
    result = {}

    def _record(name, status):
        item = _as_token(name, "deliverable")
        if item not in known:
            raise ValueError("unknown multipactor data-item %r" % (name,))
        if item in result:
            raise ValueError("duplicate submission for data-item %r" % (item,))
        result[item] = normalize_maturity(status)

    if entries is None:
        return result
    if isinstance(entries, dict):
        for name, status in entries.items():
            _record(name, status)
        return result
    try:
        rows = list(entries)
    except TypeError:
        raise ValueError("submissions must be a mapping or an iterable of mappings")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("submission entry must be a mapping, got %r" % (row,))
        if "deliverable" not in row:
            raise ValueError("submission entry missing 'deliverable'")
        if "maturity" not in row:
            raise ValueError(
                "submission entry for %r missing 'maturity'" % (row["deliverable"],)
            )
        _record(row["deliverable"], row["maturity"])
    return result


def evaluate_gate(gate, routes, submissions):
    """Audit one gate: missing, immature, unplanned, readiness, compliance."""
    checked = normalize_gate(gate)
    expected = expected_deliverables(checked, routes)
    delivered = normalize_submissions(submissions)

    missing = []
    immature = []
    satisfied = []
    for name in sorted(expected):
        owed = expected[name]
        if name not in delivered:
            missing.append(name)
            continue
        if maturity_rank(delivered[name]) < maturity_rank(owed):
            immature.append(
                {"deliverable": name, "owed": owed, "delivered": delivered[name]}
            )
        else:
            satisfied.append(name)

    unplanned = []
    owed_now = owed_items(routes)
    for name in sorted(delivered):
        if name in expected:
            continue
        reason = (
            "not-yet-due" if name in owed_now else "route-not-declared"
        )
        unplanned.append({"deliverable": name, "reason": reason})

    return {
        "gate": checked,
        "expected": expected,
        "satisfied": tuple(satisfied),
        "missing": tuple(missing),
        "immature": tuple(immature),
        "unplanned": tuple(unplanned),
        "compliant": not missing and not immature,
    }


def gate_readiness(result):
    """Fraction of the owed set delivered at or above its required maturity."""
    if not isinstance(result, dict) or "expected" not in result:
        raise ValueError("gate_readiness expects an evaluate_gate result mapping")
    owed = len(result["expected"])
    if owed == 0:
        return 1.0
    return len(result["satisfied"]) / float(owed)


def meets_readiness_threshold(score, threshold):
    """True when `score` reaches `threshold`, absorbing representation error.

    A gate whose owed set is fully satisfied can compute a score a few units
    in the last place below the threshold; the tolerance covers that without
    relaxing the engineering criterion.
    """
    for label, value in (("score", score), ("threshold", threshold)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a real number" % label)
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError("%s must lie in [0, 1], got %r" % (label, value))
    score = float(score)
    threshold = float(threshold)
    if score >= threshold:
        return True
    return math.isclose(score, threshold, rel_tol=0.0, abs_tol=_READINESS_TOLERANCE)


def roll_up_reviews(routes, submissions_by_gate, threshold=1.0):
    """Evaluate every gate in order and report the first blocking gate."""
    declared = normalize_routes(routes)
    if not isinstance(submissions_by_gate, dict):
        raise ValueError("submissions_by_gate must be a mapping of gate -> submissions")
    by_gate = {}
    for gate, entries in submissions_by_gate.items():
        by_gate[normalize_gate(gate)] = entries

    gates = []
    blocking = None
    for gate in GATE_SEQUENCE:
        result = evaluate_gate(gate, declared, by_gate.get(gate))
        score = gate_readiness(result)
        result["readiness"] = score
        result["meets_threshold"] = meets_readiness_threshold(score, threshold)
        gates.append(result)
        if blocking is None and not result["compliant"]:
            blocking = gate
    return {
        "routes": declared,
        "gates": tuple(gates),
        "blocking_gate": blocking,
        "compliant": blocking is None,
    }
