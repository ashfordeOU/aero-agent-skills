"""Compliance matrix for a class 3 component control plan.

Anchor: ECSS-Q-ST-60C clause 6.1.2.2 (preparing a compliance matrix against the
standard clauses for class 3 component control). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Put the declared applicable clauses into numeric clause order, rejecting a
   malformed or repeated clause identifier.
2. Read each matrix row: the clause it answers, the compliance state it
   states, the implementing reference behind a stated compliance, the
   justification behind a departure and the customer agreement behind a
   non-compliance.
3. Name every applicable clause the matrix never answers and every clause
   answered twice with different states.
4. Take matrix completeness as the share of applicable clauses answered by
   exactly one defect-free row and judge it against its floor.
5. Take the departure share and raise an advisory above the ceiling.
6. Return one disposition: matrix-ready, matrix-incomplete or
   matrix-not-agreeable.
"""

import math
import re

__all__ = [
    "BOUND_TOLERANCE",
    "COMPLIANCE_STATES",
    "DEPARTURE_STATES",
    "DEPARTURE_SHARE_CEILING",
    "MATRIX_COMPLETENESS_FLOOR",
    "parse_clause",
    "normalise_clause",
    "ordered_clauses",
    "row_clause",
    "row_state",
    "row_defects",
    "matrix_findings",
    "rows_by_clause",
    "unaddressed_clauses",
    "conflicting_clauses",
    "answered_clauses",
    "matrix_completeness",
    "completeness_meets_floor",
    "departure_share",
    "unagreed_non_compliances",
    "matrix_disposition",
    "compile_class_3_compliance_matrix",
]

# Completeness and departure share are quotients of small counts; a matrix
# sitting exactly on a bound can land a few ULP on the wrong side. Absorb the
# representation error here, never by moving the bound itself.
BOUND_TOLERANCE = 1e-9

# The states a matrix row may state against one clause.
COMPLIANCE_STATES = (
    "compliant",
    "compliant-with-deviation",
    "not-compliant",
    "not-applicable",
)

# The states that are a departure from the clause as written, and so owe a
# justification the customer can read.
DEPARTURE_STATES = ("compliant-with-deviation", "not-compliant", "not-applicable")

# States that only close the clause with an implementing reference behind them.
_IMPLEMENTED_STATES = ("compliant", "compliant-with-deviation")

# Share of applicable clauses that must be answered by a defect-free row.
MATRIX_COMPLETENESS_FLOOR = 0.95

# Departure share above this raises an advisory, never a defect: a plan may
# legitimately depart, and a plan that departs everywhere is a different plan.
DEPARTURE_SHARE_CEILING = 0.2

_CLAUSE_RE = re.compile(r"^[0-9]+(\.[0-9]+){0,4}$")


def _require_number(value, label, allow_negative=False):
    """Return a validated finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if not allow_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _require_text(value, label):
    """Return a stripped non-empty string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _is_text(value):
    return isinstance(value, str) and bool(value.strip())


def parse_clause(clause):
    """Return a clause identifier as a tuple of level numbers, or raise.

    '6.1.10' becomes (6, 1, 10), so 6.1.10 sorts after 6.1.9 rather than
    between 6.1.1 and 6.1.2 as a string sort would put it.
    """
    text = _require_text(clause, "clause")
    if not _CLAUSE_RE.match(text):
        raise ValueError("malformed clause identifier %r" % (clause,))
    return tuple(int(part) for part in text.split("."))


def normalise_clause(clause):
    """Return the canonical spelling of a clause identifier, or raise."""
    return ".".join(str(level) for level in parse_clause(clause))


def ordered_clauses(clauses):
    """Return the clauses in numeric clause order, rejecting repeats."""
    if not isinstance(clauses, (list, tuple, set, frozenset)):
        raise ValueError("clauses must be a sequence or set")
    seen = []
    for item in clauses:
        name = normalise_clause(item)
        if name in seen:
            raise ValueError("clause %r listed twice" % name)
        seen.append(name)
    return sorted(seen, key=parse_clause)


def row_clause(row):
    """Return the canonical clause a row answers, or None when it names none."""
    if not isinstance(row, dict):
        raise ValueError("row must be a mapping, got %r" % (row,))
    try:
        return normalise_clause(row.get("clause"))
    except ValueError:
        return None


def row_state(row):
    """Return the compliance state a row states, or None when it states none."""
    if not isinstance(row, dict):
        raise ValueError("row must be a mapping, got %r" % (row,))
    stated = row.get("state")
    if not _is_text(stated):
        return None
    folded = stated.strip().casefold()
    if folded not in COMPLIANCE_STATES:
        return None
    return folded


def row_defects(row, applicable_clauses):
    """Return the defect codes one matrix row carries.

    An empty list means the row answers its clause. row keys read here: clause,
    state, implementing_reference, justification and
    customer_agreement_reference.
    """
    if not isinstance(row, dict):
        raise ValueError("row must be a mapping, got %r" % (row,))
    applicable = set(ordered_clauses(applicable_clauses))
    if not applicable:
        raise ValueError("applicable_clauses must name at least one clause")
    defects = []
    clause = row_clause(row)
    if clause is None:
        defects.append("clause-not-stated")
    elif clause not in applicable:
        defects.append("clause-outside-declared-scope")
    state = row_state(row)
    if state is None:
        defects.append("compliance-state-not-stated")
        return defects
    if state in _IMPLEMENTED_STATES and not _is_text(
        row.get("implementing_reference")
    ):
        defects.append("implementing-reference-missing")
    if state in DEPARTURE_STATES and not _is_text(row.get("justification")):
        defects.append("departure-without-justification")
    if state == "not-compliant" and not _is_text(
        row.get("customer_agreement_reference")
    ):
        defects.append("non-compliance-without-customer-agreement")
    return defects


def _require_rows(rows):
    if not isinstance(rows, (list, tuple)):
        raise ValueError("rows must be a sequence")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("row must be a mapping, got %r" % (row,))
    return list(rows)


def matrix_findings(rows, applicable_clauses):
    """Return one entry per defective row, keeping matrix order."""
    entries = _require_rows(rows)
    findings = []
    for index, row in enumerate(entries):
        defects = row_defects(row, applicable_clauses)
        if defects:
            clause = row_clause(row)
            findings.append(
                {"row": clause if clause is not None else "row-%d" % index,
                 "defects": defects}
            )
    return findings


def rows_by_clause(rows):
    """Return the rows grouped under the clause each answers.

    Rows naming no readable clause are grouped under the None key, so they
    stay visible rather than being silently dropped.
    """
    entries = _require_rows(rows)
    grouped = {}
    for row in entries:
        grouped.setdefault(row_clause(row), []).append(row)
    return grouped


def unaddressed_clauses(applicable_clauses, rows):
    """Return the applicable clauses the matrix never answers, in clause order."""
    applicable = ordered_clauses(applicable_clauses)
    grouped = rows_by_clause(rows)
    return [clause for clause in applicable if not grouped.get(clause)]


def conflicting_clauses(rows):
    """Return the clauses answered more than once with different states."""
    grouped = rows_by_clause(rows)
    conflicts = []
    for clause, entries in grouped.items():
        if clause is None or len(entries) < 2:
            continue
        states = {row_state(row) for row in entries}
        if len(states) > 1:
            conflicts.append(clause)
    return sorted(conflicts, key=parse_clause)


def answered_clauses(applicable_clauses, rows):
    """Return the applicable clauses closed by a defect-free, unconflicted row."""
    applicable = ordered_clauses(applicable_clauses)
    grouped = rows_by_clause(rows)
    conflicted = set(conflicting_clauses(rows))
    answered = []
    for clause in applicable:
        if clause in conflicted:
            continue
        for row in grouped.get(clause, []):
            if not row_defects(row, applicable):
                answered.append(clause)
                break
    return answered


def matrix_completeness(applicable_clauses, rows):
    """Return the share of applicable clauses closed by a defect-free row."""
    applicable = ordered_clauses(applicable_clauses)
    if not applicable:
        raise ValueError("applicable_clauses must name at least one clause")
    return len(answered_clauses(applicable, rows)) / float(len(applicable))


def completeness_meets_floor(completeness, floor=MATRIX_COMPLETENESS_FLOOR):
    """Return True when the completeness share reaches its floor."""
    value = _require_number(completeness, "completeness")
    limit = _require_number(floor, "floor")
    if value > 1.0 + BOUND_TOLERANCE:
        raise ValueError("completeness must not exceed one, got %g" % value)
    return value >= limit - BOUND_TOLERANCE


def departure_share(rows):
    """Return the share of state-bearing rows that depart from the clause."""
    entries = _require_rows(rows)
    stated = 0
    departures = 0
    for row in entries:
        state = row_state(row)
        if state is None:
            continue
        stated += 1
        if state in DEPARTURE_STATES:
            departures += 1
    if stated == 0:
        raise ValueError("no row states a compliance state; no share to report")
    return departures / float(stated)


def unagreed_non_compliances(rows):
    """Return the clauses stated non-compliant with no customer agreement."""
    entries = _require_rows(rows)
    clauses = []
    for row in entries:
        if row_state(row) != "not-compliant":
            continue
        if _is_text(row.get("customer_agreement_reference")):
            continue
        clause = row_clause(row)
        if clause is not None and clause not in clauses:
            clauses.append(clause)
    return sorted(clauses, key=parse_clause)


def matrix_disposition(unaddressed, conflicts, unagreed, completeness):
    """Return the disposition implied by the matrix.

    A non-compliance the customer never agreed to cannot be submitted at all,
    so it outranks a clause the matrix simply has not reached yet.
    """
    for label, value in (("unaddressed", unaddressed),
                         ("conflicts", conflicts),
                         ("unagreed", unagreed)):
        if not isinstance(value, (list, tuple)):
            raise ValueError("%s must be a sequence, got %r" % (label, value))
    share = _require_number(completeness, "completeness")
    if unagreed:
        return "matrix-not-agreeable"
    if unaddressed or conflicts or not completeness_meets_floor(share):
        return "matrix-incomplete"
    return "matrix-ready"


def compile_class_3_compliance_matrix(plan):
    """Grade the clause 6.1.2.2 compliance matrix of one class 3 control plan.

    plan keys: applicable_clauses, rows and an optional plan_id.
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")
    applicable = ordered_clauses(plan.get("applicable_clauses", []))
    if not applicable:
        raise ValueError("applicable_clauses must name at least one clause")
    rows = _require_rows(plan.get("rows", []))
    findings = matrix_findings(rows, applicable)
    unaddressed = unaddressed_clauses(applicable, rows)
    conflicts = conflicting_clauses(rows)
    unagreed = unagreed_non_compliances(rows)
    answered = answered_clauses(applicable, rows)
    completeness = matrix_completeness(applicable, rows)
    advisories = []
    try:
        departures = departure_share(rows)
    except ValueError:
        departures = None
        advisories.append("departure-share-not-reportable")
    else:
        if departures > DEPARTURE_SHARE_CEILING + BOUND_TOLERANCE:
            advisories.append("departure-share-above-ceiling")
    disposition = matrix_disposition(unaddressed, conflicts, unagreed,
                                     completeness)
    return {
        "applicable_clauses": applicable,
        "matrix_findings": findings,
        "unaddressed_clauses": unaddressed,
        "conflicting_clauses": conflicts,
        "unagreed_non_compliances": unagreed,
        "answered_clauses": answered,
        "matrix_completeness": completeness,
        "completeness_meets_floor": completeness_meets_floor(completeness),
        "departure_share": departures,
        "advisories": advisories,
        "disposition": disposition,
        "matrix_ready": disposition == "matrix-ready",
    }
