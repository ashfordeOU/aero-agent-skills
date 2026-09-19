"""Specific mechanism specification register: one per mechanism, content, agreement.

Anchor: ECSS-E-ST-33-01 clause 4.2.2 with its Annex A content list -- a
specific mechanism specification is established for each individual mechanism
and agreed with the customer. Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the mechanism list and the specification documents that claim to
   cover them.
2. Map mechanisms to specifications one to one: a mechanism with no
   specification, a mechanism with two, and a specification stretched across
   several mechanisms are three distinct findings.
3. Score each specification against the Annex A content list, section by
   section, and report what is missing rather than a single pass or fail.
4. Accept a customer agreement only when it is recorded, carries a reference,
   is dated no earlier than the issue it agrees to, and is in place by the
   milestone the programme set for it.
5. Roll the register up into a coverage figure and a compliance verdict.
"""

import datetime

__all__ = [
    "ANNEX_A_SECTIONS",
    "AGREEMENT_AGREED",
    "AGREEMENT_PENDING",
    "AGREEMENT_ABSENT",
    "AGREEMENT_MISDATED",
    "AGREEMENT_LATE",
    "parse_date",
    "validate_mechanism",
    "validate_specification",
    "missing_sections",
    "content_completeness",
    "agreement_state",
    "map_register",
    "assess_specification_register",
]

# Annex A content list, paraphrased into the headings a specification has to
# carry before it can be agreed. Each one is a distinct engineering commitment,
# so a specification is scored section by section and not as one document.
ANNEX_A_SECTIONS = (
    "scope-and-applicable-documents",
    "functional-requirements",
    "performance-and-accuracy-requirements",
    "interface-requirements",
    "environmental-requirements",
    "life-and-duty-cycle-requirements",
    "materials-lubrication-and-tribology",
    "reliability-and-failure-tolerance",
    "verification-requirements",
    "handling-storage-and-operations-constraints",
)

AGREEMENT_AGREED = "agreed"
AGREEMENT_PENDING = "pending"
AGREEMENT_ABSENT = "not-submitted"
AGREEMENT_MISDATED = "dated-before-the-issue"
AGREEMENT_LATE = "agreed-after-the-milestone"


def _require_text(value, label):
    """Return a stripped non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def parse_date(value, label="date"):
    """Return an ISO-8601 calendar date as a date object."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _require_text(value, label)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO-8601 date (YYYY-MM-DD), got %r" % (label, value))


def validate_mechanism(mechanism):
    """Return a validated mechanism record."""
    if not isinstance(mechanism, dict):
        raise ValueError("mechanism must be a mapping")
    for key in ("id", "name"):
        if key not in mechanism:
            raise ValueError("mechanism missing required key '%s'" % key)
    return {
        "id": _require_text(mechanism["id"], "mechanism id"),
        "name": _require_text(mechanism["name"], "mechanism name"),
    }


def validate_specification(document):
    """Return a validated specification record."""
    if not isinstance(document, dict):
        raise ValueError("specification must be a mapping")
    for key in ("id", "mechanism_ids", "issue", "issue_date", "sections"):
        if key not in document:
            raise ValueError("specification missing required key '%s'" % key)
    mechanism_ids = document["mechanism_ids"]
    if not isinstance(mechanism_ids, (list, tuple)) or not mechanism_ids:
        raise ValueError("specification 'mechanism_ids' must be a non-empty sequence")
    ids = [_require_text(item, "covered mechanism id") for item in mechanism_ids]
    if len(set(ids)) != len(ids):
        raise ValueError("specification %r lists the same mechanism twice" % document["id"])
    sections = document["sections"]
    if not isinstance(sections, (list, tuple)):
        raise ValueError("specification 'sections' must be a sequence of section names")
    present = []
    for section in sections:
        name = _require_text(section, "section name")
        if name not in ANNEX_A_SECTIONS:
            raise ValueError(
                "section %r is not an Annex A content heading; the recognised set is %s"
                % (name, ", ".join(ANNEX_A_SECTIONS))
            )
        present.append(name)
    agreement = document.get("customer_agreement")
    if agreement is not None and not isinstance(agreement, dict):
        raise ValueError("'customer_agreement' must be a mapping when present")
    return {
        "id": _require_text(document["id"], "specification id"),
        "mechanism_ids": ids,
        "issue": _require_text(document["issue"], "issue"),
        "issue_date": parse_date(document["issue_date"], "issue_date"),
        "sections": sorted(set(present)),
        "customer_agreement": agreement,
    }


def missing_sections(document):
    """Return the Annex A headings a specification does not carry."""
    record = validate_specification(document)
    present = set(record["sections"])
    return [name for name in ANNEX_A_SECTIONS if name not in present]


def content_completeness(document):
    """Return the fraction of the Annex A content list a specification carries."""
    absent = missing_sections(document)
    return (len(ANNEX_A_SECTIONS) - len(absent)) / float(len(ANNEX_A_SECTIONS))


def agreement_state(document, milestone_date=None):
    """Return the state of the customer agreement on a specification."""
    record = validate_specification(document)
    agreement = record["customer_agreement"]
    if not agreement:
        return AGREEMENT_ABSENT
    status = agreement.get("status")
    if not isinstance(status, str) or status.strip().lower() != AGREEMENT_AGREED:
        return AGREEMENT_PENDING
    if "date" not in agreement:
        raise ValueError("an agreed customer agreement must carry a 'date'")
    _require_text(agreement.get("reference", ""), "customer agreement reference")
    agreed_on = parse_date(agreement["date"], "customer agreement date")
    if agreed_on < record["issue_date"]:
        return AGREEMENT_MISDATED
    if milestone_date is not None:
        milestone = parse_date(milestone_date, "milestone_date")
        if agreed_on > milestone:
            return AGREEMENT_LATE
    return AGREEMENT_AGREED


def map_register(mechanisms, specifications):
    """Return the mechanism-to-specification mapping and the structural findings."""
    if not isinstance(mechanisms, (list, tuple)) or not mechanisms:
        raise ValueError("mechanisms must be a non-empty sequence")
    if not isinstance(specifications, (list, tuple)):
        raise ValueError("specifications must be a sequence")
    mechanism_records = [validate_mechanism(item) for item in mechanisms]
    mechanism_ids = [record["id"] for record in mechanism_records]
    if len(set(mechanism_ids)) != len(mechanism_ids):
        raise ValueError("the mechanism list repeats an identifier")
    specification_records = [validate_specification(item) for item in specifications]
    specification_ids = [record["id"] for record in specification_records]
    if len(set(specification_ids)) != len(specification_ids):
        raise ValueError("the specification list repeats an identifier")

    mapping = {identifier: [] for identifier in mechanism_ids}
    findings = []
    for record in specification_records:
        if len(record["mechanism_ids"]) > 1:
            findings.append(
                "specification %s covers %d mechanisms; each mechanism owes its own"
                % (record["id"], len(record["mechanism_ids"]))
            )
        for covered in record["mechanism_ids"]:
            if covered not in mapping:
                findings.append(
                    "specification %s covers mechanism %s, which is not in the register"
                    % (record["id"], covered)
                )
            else:
                mapping[covered].append(record["id"])
    for identifier in mechanism_ids:
        count = len(mapping[identifier])
        if count == 0:
            findings.append("mechanism %s has no specific mechanism specification" % identifier)
        elif count > 1:
            findings.append(
                "mechanism %s is covered by %d specifications: %s"
                % (identifier, count, ", ".join(sorted(mapping[identifier])))
            )
    return {
        "mechanisms": mechanism_records,
        "specifications": specification_records,
        "mapping": mapping,
        "findings": findings,
    }


def assess_specification_register(spec):
    """Assess a whole specification register against clause 4.2.2 and Annex A.

    spec keys: mechanisms, specifications, optional milestone_date.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("mechanisms", "specifications"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    register = map_register(spec["mechanisms"], spec["specifications"])
    milestone = spec.get("milestone_date")
    findings = list(register["findings"])
    by_id = {record["id"]: record for record in register["specifications"]}
    documents = {}
    for document in spec["specifications"]:
        documents[validate_specification(document)["id"]] = document

    records = []
    for record in register["specifications"]:
        document = documents[record["id"]]
        absent = missing_sections(document)
        completeness = content_completeness(document)
        state = agreement_state(document, milestone)
        if absent:
            findings.append(
                "specification %s is missing %d Annex A headings: %s"
                % (record["id"], len(absent), ", ".join(absent))
            )
        if state != AGREEMENT_AGREED:
            findings.append(
                "specification %s has no usable customer agreement (%s)"
                % (record["id"], state)
            )
        records.append({
            "specification_id": record["id"],
            "mechanism_ids": record["mechanism_ids"],
            "issue": record["issue"],
            "missing_sections": absent,
            "content_completeness": completeness,
            "agreement_state": state,
            "ready": not absent and state == AGREEMENT_AGREED,
        })

    ready_ids = {
        item["specification_id"] for item in records if item["ready"]
    }
    covered = 0
    for identifier, specification_ids in register["mapping"].items():
        if len(specification_ids) == 1 and specification_ids[0] in ready_ids:
            covered += 1
    total = len(register["mapping"])
    coverage = covered / float(total) if total else 0.0
    return {
        "records": records,
        "mapping": register["mapping"],
        "mechanism_count": total,
        "covered_mechanism_count": covered,
        "coverage_fraction": coverage,
        "findings": findings,
        "compliant": not findings and covered == total,
        "unused": sorted(set(by_id) - ready_ids),
    }
