"""Compliance matrix for a reliability Class 2 component control plan.

Anchor: ECSS-Q-ST-60C clause 5.1.2.2 (the Class 2 component control plan is
prepared with a compliance matrix against the clauses of the standard).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the applicable clause set the matrix is written against: every
   clause identifier is a dotted numeric reference carrying a positive
   weight, and no clause is declared twice.
2. Validate and dispose of each matrix row. A row missing its identifier,
   clause or status cannot be read at all; a row against a clause outside
   the applicable set, a second row against a clause already answered, a
   malformed clause reference and an unrecognised status are each refused.
3. Apply the obligations a status carries. Claiming compliance needs an
   evidence reference; claiming anything less than compliance needs a
   justification and an approved disposition; claiming a clause does not
   apply needs a rationale, because an unjustified non-applicability is an
   unanswered clause wearing a status.
4. Take the clause row coverage as the weighted share of applicable clauses
   carrying an accepted row, so an unanswered clause is visible as the hole
   it is rather than absent from the denominator.
5. Take the compliance index as the weighted credit of the answered clauses
   over the clauses that still apply, excluding accepted non-applicability
   from both sides so tailoring neither flatters nor penalises the index.
6. Rank the findings and return one matrix verdict.
"""

import math
import re

__all__ = [
    "INDEX_TOLERANCE",
    "CLAUSE_PATTERN",
    "COMPLIANCE_STATUSES",
    "STATUS_CREDIT",
    "MANDATORY_ROW_ATTRIBUTES",
    "normalize_clause_id",
    "status_obligations",
    "status_credit",
    "row_completeness",
    "validate_applicable_clauses",
    "evaluate_row",
    "clause_row_coverage",
    "compliance_index",
    "assess_compliance_matrix",
]

# Both figures are ratios of summed integer weights. An exactly-met level can
# land a few ULPs low; absorb the representation error here rather than
# lowering the level the programme agreed.
INDEX_TOLERANCE = 1e-9

# A clause reference is a dotted numeric path: 5, 5.1, 5.1.2, 5.1.2.2.
CLAUSE_PATTERN = re.compile(r"^\d+(\.\d+)*$")

# Status -> what the row has to carry before the status may be believed.
COMPLIANCE_STATUSES = {
    "compliant": {
        "needs_evidence": True,
        "needs_justification": False,
        "needs_approval": False,
        "applies": True,
    },
    "compliant-with-comment": {
        "needs_evidence": True,
        "needs_justification": True,
        "needs_approval": False,
        "applies": True,
    },
    "partially-compliant": {
        "needs_evidence": True,
        "needs_justification": True,
        "needs_approval": True,
        "applies": True,
    },
    "not-compliant": {
        "needs_evidence": False,
        "needs_justification": True,
        "needs_approval": True,
        "applies": True,
    },
    "not-applicable": {
        "needs_evidence": False,
        "needs_justification": True,
        "needs_approval": True,
        "applies": False,
    },
    "to-be-determined": {
        "needs_evidence": False,
        "needs_justification": True,
        "needs_approval": False,
        "applies": True,
    },
}

# Status -> the credit an accepted row of that status earns in the index.
STATUS_CREDIT = {
    "compliant": 1.0,
    "compliant-with-comment": 1.0,
    "partially-compliant": 0.5,
    "not-compliant": 0.0,
    "to-be-determined": 0.0,
}

# The attributes without which a row cannot be disposed of at all.
MANDATORY_ROW_ATTRIBUTES = ("row_id", "clause", "status")

# Disposition -> severity used to rank findings. Lower sorts first.
_SEVERITY = {
    "record-incomplete": 0,
    "clause-malformed": 1,
    "status-unrecognised": 2,
    "clause-outside-applicable-set": 3,
    "duplicate-clause-row": 4,
    "justification-absent": 5,
    "approval-absent": 6,
    "evidence-absent": 7,
    "clause-unanswered": 8,
    "accepted": 9,
}

_ACCEPTED = "accepted"


def _require_text(value, label):
    """Return a non-blank stripped string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_positive_int(value, label):
    """Return a strictly positive integer, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be strictly positive, got %d" % (label, value))
    return value


def _is_present(value):
    """Return True when an optional text field actually carries something."""
    return isinstance(value, str) and bool(value.strip())


def normalize_clause_id(value):
    """Return a validated dotted-numeric clause reference."""
    text = _require_text(value, "clause")
    if not CLAUSE_PATTERN.match(text):
        raise ValueError(
            "clause %r is not a dotted numeric reference such as 5.1.2.2" % (value,)
        )
    return text


def status_obligations(status):
    """Return what a compliance status obliges the row to carry."""
    name = _require_text(status, "status").lower()
    if name not in COMPLIANCE_STATUSES:
        raise ValueError(
            "unknown status %r; known: %s"
            % (status, ", ".join(sorted(COMPLIANCE_STATUSES)))
        )
    return dict(COMPLIANCE_STATUSES[name])


def status_credit(status):
    """Return the index credit an accepted row of this status earns."""
    name = _require_text(status, "status").lower()
    if name not in COMPLIANCE_STATUSES:
        raise ValueError("unknown status %r" % (status,))
    if not COMPLIANCE_STATUSES[name]["applies"]:
        raise ValueError(
            "status %r removes the clause from the index; it earns no credit" % name
        )
    return STATUS_CREDIT[name]


def row_completeness(row):
    """Return (missing_attributes, completeness_fraction) for one matrix row."""
    if not isinstance(row, dict):
        raise ValueError("each row must be a mapping, got %r" % (type(row).__name__,))
    missing = []
    for attribute in MANDATORY_ROW_ATTRIBUTES:
        if attribute not in row:
            missing.append(attribute)
            continue
        value = row[attribute]
        if value is None:
            missing.append(attribute)
        elif isinstance(value, str) and not value.strip():
            missing.append(attribute)
    total = len(MANDATORY_ROW_ATTRIBUTES)
    return (tuple(missing), (total - len(missing)) / total)


def validate_applicable_clauses(applicable):
    """Return clause -> weight for the clause set the matrix is written against."""
    if not isinstance(applicable, (list, tuple)) or not applicable:
        raise ValueError(
            "applicable_clauses must be a non-empty sequence of clause mappings"
        )
    index = {}
    for entry in applicable:
        if not isinstance(entry, dict):
            raise ValueError("each applicable clause must be a mapping")
        clause = normalize_clause_id(entry.get("clause"))
        if clause in index:
            raise ValueError("clause %s is declared applicable twice" % clause)
        index[clause] = _require_positive_int(entry.get("weight", 1), "weight")
    return index


def evaluate_row(row, clause_index, already_answered=()):
    """Return the disposition record of one compliance matrix row."""
    if not isinstance(clause_index, dict) or not clause_index:
        raise ValueError("clause_index must be a non-empty mapping of clause -> weight")
    missing, completeness = row_completeness(row)
    raw_label = row.get("row_id")
    label = (
        raw_label.strip()
        if isinstance(raw_label, str) and raw_label.strip()
        else "<unnumbered>"
    )
    record = {
        "row_id": label,
        "clause": None,
        "status": None,
        "weight": 0,
        "credit": 0.0,
        "counts_in_index": False,
        "missing_attributes": missing,
        "completeness": completeness,
        "disposition": "record-incomplete",
        "accepted": False,
    }
    if missing:
        return record

    try:
        clause = normalize_clause_id(row["clause"])
    except ValueError:
        record["disposition"] = "clause-malformed"
        return record
    record["clause"] = clause

    status = _require_text(row["status"], "status").lower()
    record["status"] = status
    if status not in COMPLIANCE_STATUSES:
        record["disposition"] = "status-unrecognised"
        return record

    if clause not in clause_index:
        record["disposition"] = "clause-outside-applicable-set"
        return record
    record["weight"] = clause_index[clause]

    if clause in already_answered:
        record["disposition"] = "duplicate-clause-row"
        return record

    obligations = COMPLIANCE_STATUSES[status]
    if obligations["needs_justification"] and not _is_present(row.get("justification")):
        record["disposition"] = "justification-absent"
        return record
    if obligations["needs_approval"] and not _is_present(row.get("approval_reference")):
        record["disposition"] = "approval-absent"
        return record
    if obligations["needs_evidence"] and not _is_present(row.get("evidence_reference")):
        record["disposition"] = "evidence-absent"
        return record

    record["counts_in_index"] = obligations["applies"]
    record["credit"] = STATUS_CREDIT[status] if obligations["applies"] else 0.0
    record["disposition"] = _ACCEPTED
    record["accepted"] = True
    return record


def clause_row_coverage(records, clause_index):
    """Return (coverage, unanswered_clauses) over the applicable clause set."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of row records")
    if not isinstance(clause_index, dict) or not clause_index:
        raise ValueError("clause_index must be a non-empty mapping")
    answered = set()
    for record in records:
        if not isinstance(record, dict) or "disposition" not in record:
            raise ValueError("each record must be a mapping carrying 'disposition'")
        if record["disposition"] == _ACCEPTED:
            answered.add(record["clause"])
    total = sum(clause_index.values())
    covered = sum(weight for clause, weight in clause_index.items() if clause in answered)
    unanswered = tuple(
        sorted(clause for clause in clause_index if clause not in answered)
    )
    return (covered / total, unanswered)


def compliance_index(records, clause_index):
    """Return the weighted compliance credit over the clauses that still apply."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of row records")
    if not isinstance(clause_index, dict) or not clause_index:
        raise ValueError("clause_index must be a non-empty mapping")
    tailored_out = set()
    credited = {}
    for record in records:
        if record.get("disposition") != _ACCEPTED:
            continue
        if record["counts_in_index"]:
            credited[record["clause"]] = record["credit"]
        else:
            tailored_out.add(record["clause"])
    denominator = sum(
        weight for clause, weight in clause_index.items() if clause not in tailored_out
    )
    if denominator <= 0:
        raise ValueError(
            "every applicable clause was tailored out; the matrix grades nothing"
        )
    numerator = 0.0
    for clause, weight in clause_index.items():
        if clause in tailored_out:
            continue
        numerator += weight * credited.get(clause, 0.0)
    return numerator / denominator


def assess_compliance_matrix(spec):
    """Run the full clause 5.1.2.2 compliance matrix assessment.

    spec keys: applicable_clauses (sequence of {clause, weight}), rows
    (sequence of matrix row mappings), optional required_coverage (default
    1.0) and required_index (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("applicable_clauses", "rows"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    clause_index = validate_applicable_clauses(spec["applicable_clauses"])
    rows = spec["rows"]
    if not isinstance(rows, (list, tuple)):
        raise ValueError("spec['rows'] must be a sequence")

    required_coverage = _require_fraction(spec.get("required_coverage", 1.0), "required_coverage")
    required_index = _require_fraction(spec.get("required_index", 1.0), "required_index")

    records = []
    answered = set()
    seen_rows = set()
    for row in rows:
        record = evaluate_row(row, clause_index, already_answered=answered)
        if record["row_id"] != "<unnumbered>":
            if record["row_id"] in seen_rows:
                raise ValueError("row %s appears twice" % record["row_id"])
            seen_rows.add(record["row_id"])
        if record["disposition"] == _ACCEPTED:
            answered.add(record["clause"])
        records.append(record)

    coverage, unanswered = clause_row_coverage(records, clause_index)
    index = compliance_index(records, clause_index)

    findings = []
    for record in records:
        if record["disposition"] == _ACCEPTED:
            continue
        findings.append(
            {
                "severity": _SEVERITY.get(record["disposition"], 8),
                "reference": record["row_id"],
                "disposition": record["disposition"],
                "detail": _finding_detail(record),
            }
        )
    for clause in unanswered:
        findings.append(
            {
                "severity": _SEVERITY["clause-unanswered"],
                "reference": clause,
                "disposition": "clause-unanswered",
                "detail": "no accepted matrix row answers this applicable clause",
            }
        )
    findings.sort(key=lambda entry: (entry["severity"], entry["reference"]))

    tailored_out = tuple(
        sorted(
            record["clause"]
            for record in records
            if record["disposition"] == _ACCEPTED and not record["counts_in_index"]
        )
    )
    open_deviations = tuple(
        sorted(
            record["clause"]
            for record in records
            if record["disposition"] == _ACCEPTED
            and record["counts_in_index"]
            and record["credit"] < 1.0
        )
    )

    coverage_met = _meets(coverage, required_coverage)
    index_met = _meets(index, required_index)
    issuable = coverage_met and index_met and not findings
    return {
        "applicable_clauses": tuple(sorted(clause_index)),
        "records": records,
        "clause_row_coverage": coverage,
        "required_coverage": required_coverage,
        "compliance_index": index,
        "required_index": required_index,
        "unanswered_clauses": unanswered,
        "tailored_out_clauses": tailored_out,
        "open_deviations": open_deviations,
        "findings": findings,
        "issuable": issuable,
        "verdict": "matrix ready for issue" if issuable else "matrix incomplete",
    }


def _require_fraction(value, label):
    """Return a real number inside [0, 1], or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        raise ValueError("%s must lie in [0, 1], got %r" % (label, value))
    return number


def _meets(achieved, required):
    """Return True when achieved reaches required within the named tolerance."""
    return achieved > required or math.isclose(
        achieved, required, rel_tol=0.0, abs_tol=INDEX_TOLERANCE
    )


def _finding_detail(record):
    """Return the human-readable reason one row is not accepted."""
    disposition = record["disposition"]
    if disposition == "record-incomplete":
        return "row lacks %s; it cannot be read as an answer" % ", ".join(
            record["missing_attributes"]
        )
    if disposition == "clause-malformed":
        return "the clause reference is not a dotted numeric path"
    if disposition == "status-unrecognised":
        return "the row carries a status outside the agreed set"
    if disposition == "clause-outside-applicable-set":
        return "the row answers a clause the matrix does not declare applicable"
    if disposition == "duplicate-clause-row":
        return "a second row answers a clause already answered"
    if disposition == "justification-absent":
        return "the status claimed needs a justification and carries none"
    if disposition == "approval-absent":
        return "the deviation or tailoring was never approved"
    if disposition == "evidence-absent":
        return "compliance is claimed with no evidence reference behind it"
    return "row is not an accepted answer"
