#!/usr/bin/env python3
"""ECSS-E-ST-10C requirement analysis (5.2.1) (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
E-ST-10C clause 5.2.1 requires that customer and upper-level requirements
are analysed and that the requirement set for the system and for each
lower level is derived, generated, controlled and documented. This module
checks a requirement set against those four checkable properties:
- derived/generated: every requirement traces to a customer requirement
  or to an existing upper-level requirement (no orphans).
- controlled: every requirement carries a configuration-control status
  and controlled requirements never regress from a higher-precedence
  status to a lower one within the same check.
- documented: every requirement carries non-empty identifying text and
  rationale.
This module does not replace bidirectional bookkeeping across the full
traceability matrix (see the sibling e10-req-traceability leaf) and does
not assign verification methods (see e10-req-verif-methods).
"""

REQUIREMENT_ORIGINS = ("derived", "generated")
CONTROL_STATUSES = ("draft", "released", "baselined")
CONTROL_RANK = {status: rank for rank, status in enumerate(CONTROL_STATUSES)}
REQUIRED_FIELDS = ("id", "level", "parent", "text", "rationale", "origin", "control_status")


def validate_requirement(req):
    """Validate one requirement record has all required, non-empty
    fields and allowed enum values. req is a dict with keys 'id',
    'level', 'parent', 'text', 'rationale', 'origin', 'control_status'
    ('parent' may be None for a customer/top-level requirement). Returns
    the list of problems found (empty list means valid)."""
    problems = []
    for field in REQUIRED_FIELDS:
        if field not in req:
            problems.append("missing field: %s" % field)
    if problems:
        return problems
    for field in ("id", "level", "text", "rationale"):
        if not req[field]:
            problems.append("empty field: %s" % field)
    if req["origin"] not in REQUIREMENT_ORIGINS:
        problems.append("invalid origin: %r" % (req["origin"],))
    if req["control_status"] not in CONTROL_STATUSES:
        problems.append("invalid control_status: %r" % (req["control_status"],))
    return problems


def analyze_requirement_set(customer_requirement_ids, requirements):
    """Check derivation traceability for a requirement set. requirements
    is an iterable of requirement dicts (see validate_requirement).
    customer_requirement_ids is an iterable of the top-level customer
    requirement ids that requirements may trace to directly. Returns a
    dict of requirement id -> list of problems; a requirement with no
    problems is absent from the returned dict. A requirement is an
    orphan if its non-None parent is neither a customer requirement id
    nor another requirement id present in the set."""
    customer_ids = set(customer_requirement_ids)
    by_id = {}
    report = {}
    for req in requirements:
        problems = validate_requirement(req)
        if problems:
            report[req.get("id", "<missing id>")] = problems
            continue
        if req["id"] in by_id:
            report.setdefault(req["id"], []).append("duplicate id: %s" % req["id"])
            continue
        by_id[req["id"]] = req
    all_ids = customer_ids | set(by_id)
    for req_id, req in by_id.items():
        parent = req["parent"]
        if parent is not None and parent not in all_ids:
            report.setdefault(req_id, []).append(
                "orphan: parent %r not found in customer requirements or requirement set" % (parent,)
            )
    return report


def is_controlled(req):
    """A requirement counts as under configuration control once its
    control_status is 'released' or 'baselined' ('draft' is not yet
    controlled)."""
    return CONTROL_RANK[req["control_status"]] >= CONTROL_RANK["released"]


def control_readiness(requirements):
    """Configuration-control readiness for a requirement set: (ready,
    uncontrolled_ids). ready is True only when every requirement is
    controlled (released or baselined); uncontrolled_ids lists the
    draft ones, in input order."""
    uncontrolled = [req["id"] for req in requirements if not is_controlled(req)]
    return (not uncontrolled, uncontrolled)


def lower_level_coverage(requirements):
    """Map each level name present in the requirement set to the number
    of requirements documented at that level, preserving first-seen
    level order."""
    coverage = {}
    for req in requirements:
        level = req["level"]
        coverage[level] = coverage.get(level, 0) + 1
    return coverage
