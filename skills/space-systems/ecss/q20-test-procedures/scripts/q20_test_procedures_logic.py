"""Quality-assurance control of test procedures.

Anchor: ECSS-Q-ST-20C clause 5.6.3.1 (review, approval and update control of
test procedures, and their consistency with the test specification and the
test-procedure baseline). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise and validate each declared test procedure: identifier, revision,
   the specification it implements, its steps and their requirement coverage,
   its approval signatures and their dates.
2. Decide the approval verdict: every mandatory approval role present, signed
   on or before the issue date, with the customer role added when the
   procedure is customer-witnessed.
3. Decide requirement coverage against the specification: which specification
   requirements no step exercises, and which steps point at a requirement the
   specification does not hold.
4. Decide baseline consistency: the specification revision cited by the
   procedure against the revision actually in force, in both directions.
5. Decide update control: a revision advance needs an approved change record
   naming both revisions and approved no later than the procedure issue date.
6. Roll the per-procedure findings into a release verdict for the set.
"""

from datetime import date

__all__ = [
    "MANDATORY_APPROVAL_ROLES",
    "CUSTOMER_ROLE",
    "normalise_identifier",
    "parse_iso_date",
    "revision_rank",
    "compare_revisions",
    "validate_procedure",
    "approval_findings",
    "coverage_findings",
    "consistency_findings",
    "update_control_findings",
    "assess_procedure",
    "assess_procedure_set",
]

# Roles whose signature a procedure carries before it may be used to run a
# test. Product assurance signs for the quality control of the procedure
# itself; engineering signs for its technical content.
MANDATORY_APPROVAL_ROLES = ("engineering", "product-assurance")

# Added to the mandatory set when the customer witnesses or has reserved
# approval of the procedure.
CUSTOMER_ROLE = "customer"

_ALPHA = "abcdefghijklmnopqrstuvwxyz"


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def parse_iso_date(value, label):
    """Return a date from an ISO yyyy-mm-dd string or a date object."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        parts = [int(part) for part in value.strip().split("-")]
    except ValueError:
        raise ValueError("%s is not an ISO yyyy-mm-dd date: %r" % (label, value))
    if len(parts) != 3:
        raise ValueError("%s is not an ISO yyyy-mm-dd date: %r" % (label, value))
    try:
        return date(parts[0], parts[1], parts[2])
    except ValueError:
        raise ValueError("%s is not a real calendar date: %r" % (label, value))


def revision_rank(revision, label="revision"):
    """Return (scheme, rank) for a revision mark.

    Two schemes are recognised and never mixed: a bijective base-26 letter
    scheme (a, b, ... z, aa) and a decimal issue-number scheme. A mark that is
    neither is an input error, because an unordered mark cannot decide whether
    a procedure advanced.
    """
    text = normalise_identifier(revision, label)
    if all(ch in _ALPHA for ch in text):
        rank = 0
        for ch in text:
            rank = rank * 26 + (_ALPHA.index(ch) + 1)
        return ("alpha", rank)
    if text.isdigit():
        return ("numeric", int(text))
    raise ValueError(
        "%s %r is neither a letter revision nor a decimal issue number" % (label, revision)
    )


def compare_revisions(left, right, label="revision"):
    """Return -1, 0 or 1 comparing two revision marks of the same scheme."""
    left_scheme, left_rank = revision_rank(left, label)
    right_scheme, right_rank = revision_rank(right, label)
    if left_scheme != right_scheme:
        raise ValueError(
            "cannot compare %s %r (%s) with %r (%s): mixed revision schemes"
            % (label, left, left_scheme, right, right_scheme)
        )
    if left_rank < right_rank:
        return -1
    if left_rank > right_rank:
        return 1
    return 0


def _validate_steps(raw_steps):
    """Return the normalised step list of a procedure."""
    if not isinstance(raw_steps, (list, tuple)) or not raw_steps:
        raise ValueError("procedure 'steps' must be a non-empty sequence")
    steps = []
    seen = set()
    for index, item in enumerate(raw_steps):
        if not isinstance(item, dict):
            raise ValueError("steps[%d] must be a mapping" % index)
        step_id = normalise_identifier(item.get("id"), "steps[%d].id" % index)
        if step_id in seen:
            raise ValueError("duplicate step id %r" % step_id)
        seen.add(step_id)
        raw_covers = item.get("covers", [])
        if not isinstance(raw_covers, (list, tuple)):
            raise ValueError("steps[%d].covers must be a sequence" % index)
        covers = [
            normalise_identifier(req, "steps[%d].covers[%d]" % (index, j))
            for j, req in enumerate(raw_covers)
        ]
        steps.append({"id": step_id, "covers": covers})
    return steps


def _validate_approvals(raw_approvals):
    """Return the normalised approval list of a procedure."""
    if not isinstance(raw_approvals, (list, tuple)):
        raise ValueError("procedure 'approvals' must be a sequence")
    approvals = []
    seen = set()
    for index, item in enumerate(raw_approvals):
        if not isinstance(item, dict):
            raise ValueError("approvals[%d] must be a mapping" % index)
        role = normalise_identifier(item.get("role"), "approvals[%d].role" % index)
        if role in seen:
            raise ValueError("duplicate approval role %r" % role)
        seen.add(role)
        signed = parse_iso_date(item.get("date"), "approvals[%d].date" % index)
        approvals.append({"role": role, "date": signed})
    return approvals


def validate_procedure(procedure):
    """Return a normalised procedure record; raise on a malformed one."""
    if not isinstance(procedure, dict):
        raise ValueError("procedure must be a mapping")
    record = {
        "id": normalise_identifier(procedure.get("id"), "procedure id"),
        "revision": normalise_identifier(procedure.get("revision"), "procedure revision"),
        "specification_id": normalise_identifier(
            procedure.get("specification_id"), "specification_id"
        ),
        "cited_specification_revision": normalise_identifier(
            procedure.get("cited_specification_revision"), "cited_specification_revision"
        ),
        "issue_date": parse_iso_date(procedure.get("issue_date"), "issue_date"),
        "steps": _validate_steps(procedure.get("steps")),
        "approvals": _validate_approvals(procedure.get("approvals", [])),
        "customer_witnessed": bool(procedure.get("customer_witnessed", False)),
    }
    previous = procedure.get("previous_revision")
    record["previous_revision"] = (
        None if previous is None else normalise_identifier(previous, "previous_revision")
    )
    # Reject a revision mark that cannot be ordered before anything else runs.
    revision_rank(record["revision"], "procedure revision")
    return record


def approval_findings(record):
    """Return the approval findings of one normalised procedure."""
    required = list(MANDATORY_APPROVAL_ROLES)
    if record["customer_witnessed"]:
        required.append(CUSTOMER_ROLE)
    signed = {item["role"]: item["date"] for item in record["approvals"]}
    findings = []
    for role in required:
        if role not in signed:
            findings.append("missing %s approval" % role)
        elif signed[role] > record["issue_date"]:
            findings.append("%s approval is dated after the procedure issue date" % role)
    return findings


def coverage_findings(record, specification_requirements):
    """Return the requirement-coverage result of one normalised procedure."""
    if not isinstance(specification_requirements, (list, tuple)):
        raise ValueError("specification_requirements must be a sequence")
    required = []
    for index, item in enumerate(specification_requirements):
        req = normalise_identifier(item, "specification_requirements[%d]" % index)
        if req not in required:
            required.append(req)
    if not required:
        raise ValueError("specification_requirements must not be empty")
    covered = set()
    orphan = []
    for step in record["steps"]:
        for req in step["covers"]:
            if req in required:
                covered.add(req)
            elif req not in orphan:
                orphan.append(req)
    missing = [req for req in required if req not in covered]
    findings = []
    if missing:
        findings.append("specification requirements with no procedure step: %s" % ", ".join(missing))
    if orphan:
        findings.append("procedure steps cite unknown requirements: %s" % ", ".join(orphan))
    return {
        "required_count": len(required),
        "covered_count": len(covered),
        "missing": missing,
        "orphan": orphan,
        "coverage_ratio": len(covered) / float(len(required)),
        "findings": findings,
    }


def consistency_findings(record, specification_revision_in_force):
    """Return the baseline-consistency findings of one normalised procedure."""
    in_force = normalise_identifier(
        specification_revision_in_force, "specification_revision_in_force"
    )
    order = compare_revisions(
        record["cited_specification_revision"], in_force, "specification revision"
    )
    if order < 0:
        return [
            "procedure cites specification revision %s while revision %s is in force"
            % (record["cited_specification_revision"], in_force)
        ]
    if order > 0:
        return [
            "procedure cites specification revision %s, which is ahead of the %s in force"
            % (record["cited_specification_revision"], in_force)
        ]
    return []


def update_control_findings(record, change_records):
    """Return the update-control findings of one normalised procedure."""
    if change_records is None:
        change_records = []
    if not isinstance(change_records, (list, tuple)):
        raise ValueError("change_records must be a sequence")
    previous = record["previous_revision"]
    if previous is None:
        return []
    order = compare_revisions(record["revision"], previous, "procedure revision")
    if order < 0:
        return [
            "procedure revision %s is behind its previous revision %s"
            % (record["revision"], previous)
        ]
    if order == 0:
        return []
    for index, item in enumerate(change_records):
        if not isinstance(item, dict):
            raise ValueError("change_records[%d] must be a mapping" % index)
        target = normalise_identifier(
            item.get("procedure_id"), "change_records[%d].procedure_id" % index
        )
        if target != record["id"]:
            continue
        from_rev = normalise_identifier(item.get("from_revision"), "change_records[%d].from_revision" % index)
        to_rev = normalise_identifier(item.get("to_revision"), "change_records[%d].to_revision" % index)
        if from_rev != previous or to_rev != record["revision"]:
            continue
        if not bool(item.get("approved", False)):
            return ["change record for revision %s is not approved" % record["revision"]]
        approved_on = parse_iso_date(
            item.get("approval_date"), "change_records[%d].approval_date" % index
        )
        if approved_on > record["issue_date"]:
            return [
                "change record for revision %s was approved after the procedure issued"
                % record["revision"]
            ]
        return []
    return [
        "revision advanced from %s to %s with no matching change record"
        % (previous, record["revision"])
    ]


def assess_procedure(procedure, specification):
    """Assess one procedure against its specification; return its record."""
    if not isinstance(specification, dict):
        raise ValueError("specification must be a mapping")
    record = validate_procedure(procedure)
    spec_id = normalise_identifier(specification.get("id"), "specification id")
    findings = []
    if record["specification_id"] != spec_id:
        findings.append(
            "procedure implements %s but was graded against %s"
            % (record["specification_id"], spec_id)
        )
    findings.extend(approval_findings(record))
    coverage = coverage_findings(record, specification.get("requirements", []))
    findings.extend(coverage["findings"])
    findings.extend(
        consistency_findings(record, specification.get("revision_in_force"))
    )
    findings.extend(update_control_findings(record, specification.get("change_records")))
    return {
        "procedure_id": record["id"],
        "revision": record["revision"],
        "coverage_ratio": coverage["coverage_ratio"],
        "missing_requirements": coverage["missing"],
        "orphan_requirements": coverage["orphan"],
        "findings": findings,
        "released": not findings,
    }


def assess_procedure_set(specification, procedures):
    """Assess a whole procedure set and return the release verdict."""
    if not isinstance(procedures, (list, tuple)) or not procedures:
        raise ValueError("procedures must be a non-empty sequence")
    records = [assess_procedure(item, specification) for item in procedures]
    seen = set()
    for item in records:
        if item["procedure_id"] in seen:
            raise ValueError("duplicate procedure id %r in the set" % item["procedure_id"])
        seen.add(item["procedure_id"])
    required = []
    for index, item in enumerate(specification.get("requirements", [])):
        req = normalise_identifier(item, "requirements[%d]" % index)
        if req not in required:
            required.append(req)
    covered = set()
    for procedure in procedures:
        for step in validate_procedure(procedure)["steps"]:
            for req in step["covers"]:
                if req in required:
                    covered.add(req)
    uncovered = [req for req in required if req not in covered]
    held = [item["procedure_id"] for item in records if not item["released"]]
    set_findings = []
    if uncovered:
        set_findings.append(
            "no procedure in the set exercises: %s" % ", ".join(uncovered)
        )
    return {
        "procedures": records,
        "held_procedures": held,
        "set_coverage_ratio": len(covered) / float(len(required)),
        "uncovered_requirements": uncovered,
        "findings": set_findings,
        "verdict": "released" if not held and not set_findings else "hold",
    }
