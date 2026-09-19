#!/usr/bin/env python3
"""Responsibility and authority for quality and safety in a test centre.

Anchor: ECSS-Q-ST-20-07 clause 5.3.3, the requirement that a test centre
assigns responsibility and authority for its quality and safety items:
one named holder per item, an authority level that matches what the item
demands, delegation that does not create authority the delegator never
had, and a reporting line that terminates at the centre head. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

Four things follow from what the assignment matrix is for.

An item with nobody against it is unassigned, and an item with two
holders is ambiguous. They are different defects: one needs somebody
appointed, the other needs one of two appointments withdrawn, and a
matrix that counts holders without grouping them by item reports
neither.

Authority is ordered, and the order is the whole point. An item
demanding a manager cannot be discharged by an operator however
carefully the duty is written, so the held level is compared against the
level the item's criticality demands.

Delegation cannot manufacture authority. A delegator may pass down what
they hold and no more, so a delegate carrying a level above their
delegator is an invalid delegation even when both people exist and both
levels are recognised. A delegation from somebody who holds nothing is
the same defect seen from the other end.

A reporting line has to terminate. A holder reporting to somebody the
centre does not list breaks the line, and a reporting loop never reaches
the centre head at all; both mean an escalation on a safety item has
nowhere to go.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

AUTHORITY_OPERATOR = "operator"
AUTHORITY_SUPERVISOR = "supervisor"
AUTHORITY_MANAGER = "manager"
AUTHORITY_CENTRE_HEAD = "centre-head"

AUTHORITY_ORDER = (
    AUTHORITY_OPERATOR,
    AUTHORITY_SUPERVISOR,
    AUTHORITY_MANAGER,
    AUTHORITY_CENTRE_HEAD,
)

AUTHORITY_INDEX = {name: index for index, name in enumerate(AUTHORITY_ORDER)}

CRITICALITY_ROUTINE = "routine-item"
CRITICALITY_QUALITY_CRITICAL = "quality-critical-item"
CRITICALITY_SAFETY_CRITICAL = "safety-critical-item"

RECOGNISED_CRITICALITIES = (
    CRITICALITY_ROUTINE,
    CRITICALITY_QUALITY_CRITICAL,
    CRITICALITY_SAFETY_CRITICAL,
)

DEFAULT_AUTHORITY_DEMAND = {
    CRITICALITY_ROUTINE: AUTHORITY_OPERATOR,
    CRITICALITY_QUALITY_CRITICAL: AUTHORITY_SUPERVISOR,
    CRITICALITY_SAFETY_CRITICAL: AUTHORITY_MANAGER,
}

REQUIRED_ITEM_FIELDS = ("item_id", "criticality")

REQUIRED_ASSIGNMENT_FIELDS = (
    "item_id",
    "holder",
    "authority",
    "delegated_from",
    "reports_to",
)

MATRIX_ABSENT = "responsibility-matrix-absent"
ITEMS_UNASSIGNED = "quality-and-safety-items-unassigned"
DUTY_AMBIGUOUS = "quality-and-safety-duty-ambiguous"
AUTHORITY_INSUFFICIENT = "assigned-authority-insufficient"
DELEGATION_INVALID = "authority-delegation-invalid"
REPORTING_LINE_BROKEN = "quality-and-safety-reporting-line-broken"
RESPONSIBILITIES_ASSIGNED = "responsibilities-and-authorities-assigned"


def _require_token(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty identifier, got %r" % (name, value))
    return value.strip()


def _require_authority(name, value):
    token = _require_token(name, value)
    if token not in AUTHORITY_INDEX:
        raise ValueError("unrecognised authority level '%s'" % token)
    return token


def authority_rank(level):
    """Return the ordinal position of an authority level."""
    return AUTHORITY_INDEX[_require_authority("authority", level)]


def authority_reaches(held, demanded):
    """Return True when the held authority is at or above the demanded one."""
    return authority_rank(held) >= authority_rank(demanded)


def validate_authority_demand(demand):
    """Return the validated criticality -> minimum authority mapping."""
    if demand is None:
        return dict(DEFAULT_AUTHORITY_DEMAND)
    if not isinstance(demand, dict):
        raise ValueError("authority demand must be a mapping")
    out = {}
    for criticality, level in demand.items():
        name = _require_token("criticality", criticality)
        if name not in RECOGNISED_CRITICALITIES:
            raise ValueError("unrecognised item criticality '%s'" % name)
        out[name] = _require_authority("authority demand for '%s'" % name, level)
    for name in RECOGNISED_CRITICALITIES:
        if name not in out:
            raise ValueError("authority demand does not cover criticality '%s'" % name)
    if not authority_reaches(out[CRITICALITY_SAFETY_CRITICAL], out[CRITICALITY_ROUTINE]):
        raise ValueError(
            "a safety-critical item cannot demand less authority than a routine one"
        )
    return out


def validate_item(item):
    """Return one validated quality or safety item."""
    if not isinstance(item, dict):
        raise ValueError("a quality and safety item must be a mapping, got %r" % (item,))
    for field in REQUIRED_ITEM_FIELDS:
        if field not in item:
            raise ValueError("quality and safety item missing field '%s'" % field)
    criticality = _require_token("criticality", item["criticality"])
    if criticality not in RECOGNISED_CRITICALITIES:
        raise ValueError("unrecognised item criticality '%s'" % criticality)
    return {
        "item_id": _require_token("item_id", item["item_id"]),
        "criticality": criticality,
    }


def validate_assignment(assignment):
    """Return one validated responsibility assignment."""
    if not isinstance(assignment, dict):
        raise ValueError("an assignment must be a mapping, got %r" % (assignment,))
    for field in REQUIRED_ASSIGNMENT_FIELDS:
        if field not in assignment:
            raise ValueError("assignment missing field '%s'" % field)
    holder = _require_token("holder", assignment["holder"])
    delegated_from = assignment["delegated_from"]
    if delegated_from is not None:
        delegated_from = _require_token("delegated_from", delegated_from)
        if delegated_from == holder:
            raise ValueError("'%s' cannot delegate to themselves" % holder)
    reports_to = assignment["reports_to"]
    if reports_to is not None:
        reports_to = _require_token("reports_to", reports_to)
        if reports_to == holder:
            raise ValueError("'%s' cannot report to themselves" % holder)
    return {
        "item_id": _require_token("item_id", assignment["item_id"]),
        "holder": holder,
        "authority": _require_authority("authority", assignment["authority"]),
        "delegated_from": delegated_from,
        "reports_to": reports_to,
    }


def validate_matrix(matrix):
    """Return the validated responsibility and authority matrix."""
    if not isinstance(matrix, dict):
        raise ValueError("responsibility matrix must be a mapping")
    for field in ("assigned", "items", "assignments", "centre_head"):
        if field not in matrix:
            raise ValueError("responsibility matrix missing field '%s'" % field)
    assigned = matrix["assigned"]
    if not isinstance(assigned, bool):
        raise ValueError("assigned must be a boolean")
    for name in ("items", "assignments"):
        if not isinstance(matrix[name], (list, tuple)):
            raise ValueError("%s must be a sequence" % name)
    items = [validate_item(item) for item in matrix["items"]]
    seen = set()
    for item in items:
        if item["item_id"] in seen:
            raise ValueError("item '%s' is registered twice" % item["item_id"])
        seen.add(item["item_id"])
    assignments = [validate_assignment(row) for row in matrix["assignments"]]
    pairs = set()
    for row in assignments:
        key = (row["item_id"], row["holder"])
        if key in pairs:
            raise ValueError(
                "'%s' is assigned to item '%s' twice" % (row["holder"], row["item_id"])
            )
        pairs.add(key)
        if row["item_id"] not in seen:
            raise ValueError(
                "assignment names item '%s', which the matrix does not hold" % row["item_id"]
            )
    centre_head = _require_token("centre_head", matrix["centre_head"])
    return {
        "validated_matrix": True,
        "assigned": assigned,
        "items": items,
        "assignments": assignments,
        "centre_head": centre_head,
        "item_index": {item["item_id"]: item for item in items},
    }


def _as_matrix(matrix):
    """Return the record already validated, validating a raw one first."""
    if isinstance(matrix, dict) and matrix.get("validated_matrix"):
        return matrix
    return validate_matrix(matrix)


def holders_of(matrix, item_id):
    """Return the assignments made against one item."""
    record = _as_matrix(matrix)
    wanted = _require_token("item_id", item_id)
    if wanted not in record["item_index"]:
        raise ValueError("the matrix holds no item '%s'" % wanted)
    return [row for row in record["assignments"] if row["item_id"] == wanted]


def unassigned_items(matrix):
    """Return the item ids with nobody assigned against them."""
    record = _as_matrix(matrix)
    held = {row["item_id"] for row in record["assignments"]}
    return [item["item_id"] for item in record["items"] if item["item_id"] not in held]


def ambiguous_items(matrix):
    """Return (item id, holders) for every item carrying more than one holder."""
    record = _as_matrix(matrix)
    grouped = {}
    for row in record["assignments"]:
        grouped.setdefault(row["item_id"], []).append(row["holder"])
    return [
        (item["item_id"], grouped[item["item_id"]])
        for item in record["items"]
        if len(grouped.get(item["item_id"], [])) > 1
    ]


def assignment_coverage(matrix):
    """Return the fraction of items carrying exactly one holder."""
    record = _as_matrix(matrix)
    if not record["items"]:
        return 0.0
    grouped = {}
    for row in record["assignments"]:
        grouped.setdefault(row["item_id"], []).append(row["holder"])
    clean = sum(1 for item in record["items"] if len(grouped.get(item["item_id"], [])) == 1)
    return clean / float(len(record["items"]))


def authority_shortfalls(matrix, demand=None):
    """Return (item id, holder, held, demanded) for every under-powered holder."""
    record = _as_matrix(matrix)
    demands = validate_authority_demand(demand)
    out = []
    for row in record["assignments"]:
        item = record["item_index"][row["item_id"]]
        needed = demands[item["criticality"]]
        if not authority_reaches(row["authority"], needed):
            out.append((row["item_id"], row["holder"], row["authority"], needed))
    return out


def authority_held_by(matrix, person):
    """Return the highest authority a person holds anywhere in the matrix."""
    record = _as_matrix(matrix)
    name = _require_token("person", person)
    if name == record["centre_head"]:
        return AUTHORITY_CENTRE_HEAD
    best = None
    for row in record["assignments"]:
        if row["holder"] != name:
            continue
        if best is None or authority_rank(row["authority"]) > authority_rank(best):
            best = row["authority"]
    return best


def delegation_defects(matrix):
    """Return (item id, holder, delegator) for every delegation beyond its source."""
    record = _as_matrix(matrix)
    out = []
    for row in record["assignments"]:
        delegator = row["delegated_from"]
        if delegator is None:
            continue
        source = authority_held_by(record, delegator)
        if source is None:
            out.append((row["item_id"], row["holder"], delegator, None))
            continue
        if not authority_reaches(source, row["authority"]):
            out.append((row["item_id"], row["holder"], delegator, source))
    return out


def reporting_line(matrix, holder):
    """Return the chain from a holder to the centre head, raising when it breaks."""
    record = _as_matrix(matrix)
    name = _require_token("holder", holder)
    reports = {}
    for row in record["assignments"]:
        current = reports.get(row["holder"])
        if current is not None and row["reports_to"] is not None and current != row["reports_to"]:
            raise ValueError(
                "'%s' reports to both '%s' and '%s'" % (row["holder"], current, row["reports_to"])
            )
        if row["reports_to"] is not None:
            reports[row["holder"]] = row["reports_to"]
    chain = [name]
    seen = {name}
    while chain[-1] != record["centre_head"]:
        nxt = reports.get(chain[-1])
        if nxt is None:
            raise ValueError(
                "the reporting line from '%s' stops at '%s' before the centre head"
                % (name, chain[-1])
            )
        if nxt in seen:
            raise ValueError("the reporting line from '%s' is a loop" % name)
        chain.append(nxt)
        seen.add(nxt)
    return chain


def reporting_defects(matrix):
    """Return (holder, reason) for every reporting line that never terminates."""
    record = _as_matrix(matrix)
    out = []
    for holder in sorted({row["holder"] for row in record["assignments"]}):
        try:
            reporting_line(record, holder)
        except ValueError as error:
            out.append((holder, str(error)))
    return out


def assess_responsibility(case):
    """Run the full clause 5.3.3 responsibility and authority assessment.

    case keys: matrix (the assignment matrix) and an optional authority_demand
    mapping of criticality to the minimum authority it needs.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    if "matrix" not in case:
        raise ValueError("case missing required key 'matrix'")
    demands = validate_authority_demand(case.get("authority_demand"))
    record = validate_matrix(case["matrix"])

    unassigned = unassigned_items(record)
    ambiguous = ambiguous_items(record)
    shortfalls = authority_shortfalls(record, demands)
    delegations = delegation_defects(record)
    reporting = reporting_defects(record)
    coverage = assignment_coverage(record)

    findings = []
    advisories = []

    if not record["assigned"] or not record["items"]:
        verdict = MATRIX_ABSENT
        findings.append("no responsibility and authority matrix has been assigned")
    elif unassigned:
        verdict = ITEMS_UNASSIGNED
        findings.append(
            "%d quality and safety item(s) have nobody assigned: %s"
            % (len(unassigned), ", ".join(unassigned))
        )
    elif ambiguous:
        verdict = DUTY_AMBIGUOUS
        findings.append(
            "%d item(s) carry more than one holder: %s"
            % (
                len(ambiguous),
                ", ".join("%s(%s)" % (name, "+".join(who)) for name, who in ambiguous),
            )
        )
    elif shortfalls:
        verdict = AUTHORITY_INSUFFICIENT
        findings.append(
            "%d holder(s) sit under the authority their item demands: %s"
            % (
                len(shortfalls),
                ", ".join(
                    "%s held by %s at %s, needs %s" % quad for quad in shortfalls
                ),
            )
        )
    elif delegations:
        verdict = DELEGATION_INVALID
        findings.append(
            "%d delegation(s) grant authority the delegator does not hold: %s"
            % (
                len(delegations),
                ", ".join("%s to %s from %s" % (q[0], q[1], q[2]) for q in delegations),
            )
        )
    elif reporting:
        verdict = REPORTING_LINE_BROKEN
        findings.append(
            "%d reporting line(s) never reach the centre head: %s"
            % (len(reporting), ", ".join(name for name, _ in reporting))
        )
    else:
        verdict = RESPONSIBILITIES_ASSIGNED

    if coverage < 1.0 and not unassigned and not ambiguous:
        advisories.append("assignment coverage is %.3f" % coverage)

    return {
        "verdict": verdict,
        "assigned": record["assigned"],
        "unassigned_items": unassigned,
        "ambiguous_items": ambiguous,
        "authority_shortfalls": shortfalls,
        "delegation_defects": delegations,
        "reporting_defects": reporting,
        "assignment_coverage": coverage,
        "authority_demand": demands,
        "findings": findings,
        "advisories": advisories,
    }
