"""The baseline provisions a hybrid delivery data package has to obey.

Anchor: ECSS-Q-ST-60-05 clause 13.2.1 (the general expectations placed on the
record set that accompanies a delivered lot: the medium it is supplied on, how
long it is kept, how each document is identified, and whether what arrived is
all of what was promised).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The medium is graded against what the document has to survive being. A
  conformity declaration has to stay authentic for the life of the record; a
  supporting note does not, and holding both to the same medium demand is as
  wrong as holding neither to any.
* An editable file is not a record. It carries no evidence that what is read
  today is what was signed, so it is refused for anything that has to be
  relied on rather than merely consulted.
* Retention is measured, not asserted. The declared period is subtracted from
  the period the category demands, and any shortfall is a number of years the
  package is short by, per document, not a yes-or-no.
* Completeness is a reconciliation. The pages a document says it has, the
  pages that arrived and the pages that arrived unreadable are three different
  counts, and a package is complete only when the first equals the second and
  the third is zero.
* Identification is what lets a loose page be put back. A document with no lot
  reference, no issue status and no page totals cannot be checked for
  completeness by anyone who did not assemble it.
* The provision-compliance index is weighted credit over total weight. It
  ranks what is outstanding; an unacceptable medium, a retention shortfall or
  a page that never arrived decides the outcome on its own, at any index.
"""

from __future__ import annotations

import math

# How well each delivery medium preserves a record and its authenticity:
# 3 survives as an original, 2 as a controlled copy, 1 as a reference copy,
# 0 is not a record at all.
MEDIUM_GRADE = {
    "signed-paper-original": 3,
    "archival-pdf-with-digital-signature": 3,
    "signed-scan-pdf": 2,
    "controlled-microform": 2,
    "plain-scan-image": 1,
    "editable-office-file": 0,
    "uncontrolled-print": 0,
}

# What each document category has to be supplied on, and kept for.
DOCUMENT_CATEGORIES = {
    "certification-and-conformity": {"medium_grade": 3, "retention_years": 20.0},
    "acceptance-test-data": {"medium_grade": 2, "retention_years": 20.0},
    "process-and-inspection-records": {"medium_grade": 2, "retention_years": 10.0},
    "supporting-information": {"medium_grade": 1, "retention_years": 5.0},
}

# Identification a document has to carry to be checkable by a later reader.
IDENTIFICATION_FIELDS = (
    "carries_lot_reference",
    "carries_document_number",
    "carries_issue_status",
    "carries_page_totals",
)

IDENTIFICATION_FINDINGS = {
    "carries_lot_reference": "document-without-a-lot-reference",
    "carries_document_number": "document-without-a-document-number",
    "carries_issue_status": "document-without-an-issue-status",
    "carries_page_totals": "document-without-page-totals",
}

# Package-level provisions and the share of the general requirements each
# one supplies.
PROVISION_WEIGHTS = {
    "delivery-medium-defined": 1.0,
    "document-identification-scheme": 1.0,
    "index-of-contents": 1.0,
    "retention-period-declared": 1.0,
    "retention-custodian-named": 0.8,
    "page-numbering-convention": 0.8,
    "issue-and-copy-control": 0.8,
    "language-declared": 0.6,
    "delivery-route-and-recipient": 0.5,
}

MANDATORY_PROVISIONS = (
    "delivery-medium-defined",
    "document-identification-scheme",
    "index-of-contents",
    "retention-period-declared",
)

PROVISION_STATE_CREDIT = {
    "met": 1.0,
    "met-with-observation": 0.7,
    "deficient": 0.0,
    "not-declared": 0.0,
}

# Provision-compliance index a conforming package has to reach.
ACCEPTANCE_PROVISION_INDEX = 0.90

# Indices and year differences are sums of products; a case meant to sit
# exactly on a bound can land a few units in the last place away from it.
PROVISION_TOLERANCE = 1e-9

VERDICTS = (
    "data-package-provisions-met",
    "data-package-provisions-met-with-open-actions",
    "data-package-provisions-not-met",
    "data-package-provisions-assessment-incomplete",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _non_negative(value, label):
    """Return ``value`` as a finite non-negative float or raise."""
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _count(value, label):
    """Return ``value`` as a non-negative whole count or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def _flag(mapping, key):
    """Return a required boolean field of a mapping or raise."""
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (key, value))
    return value


def medium_grade(medium):
    """How well one delivery medium preserves a record."""
    if medium not in MEDIUM_GRADE:
        raise ValueError(
            "unknown delivery medium %r (known: %s)" % (medium, ", ".join(sorted(MEDIUM_GRADE)))
        )
    return MEDIUM_GRADE[medium]


def category_requirements(category):
    """Medium grade and retention period one document category demands."""
    if category not in DOCUMENT_CATEGORIES:
        raise ValueError(
            "unknown document category %r (known: %s)"
            % (category, ", ".join(sorted(DOCUMENT_CATEGORIES)))
        )
    return dict(DOCUMENT_CATEGORIES[category])


def medium_is_acceptable(medium, category):
    """True when the medium reaches the grade the category demands."""
    return medium_grade(medium) >= category_requirements(category)["medium_grade"]


def retention_shortfall_years(category, declared_years):
    """Years the declared retention period falls short of the demand."""
    demanded = category_requirements(category)["retention_years"]
    declared = _non_negative(declared_years, "declared retention years")
    shortfall = demanded - declared
    if shortfall <= PROVISION_TOLERANCE:
        return 0.0
    return shortfall


def page_reconciliation(declared_pages, supplied_pages, illegible_pages):
    """Reconcile the pages promised, the pages received and the unreadable ones."""
    declared = _count(declared_pages, "declared_pages")
    supplied = _count(supplied_pages, "supplied_pages")
    illegible = _count(illegible_pages, "illegible_pages")
    if declared == 0:
        raise ValueError("a delivered document must declare at least one page")
    if illegible > supplied:
        raise ValueError("more pages are unreadable than were supplied")
    findings = []
    if supplied < declared:
        findings.append("pages-missing-from-the-document")
    if supplied > declared:
        findings.append("more-pages-supplied-than-the-document-declares")
    if illegible > 0:
        findings.append("unreadable-pages-in-the-document")
    usable = supplied - illegible
    return {
        "declared_pages": declared,
        "supplied_pages": supplied,
        "illegible_pages": illegible,
        "usable_pages": usable,
        "missing_pages": max(0, declared - supplied),
        "usable_page_ratio": float(usable) / float(declared),
        "reconciled": len(findings) == 0,
        "findings": findings,
    }


def identification_findings(document):
    """Findings raised by the identification a document does not carry."""
    if not isinstance(document, dict):
        raise ValueError("document must be a mapping, got %r" % (type(document).__name__,))
    findings = []
    for field in IDENTIFICATION_FIELDS:
        if not _flag(document, field):
            findings.append(IDENTIFICATION_FINDINGS[field])
    return findings


def assess_document(document):
    """Grade one delivered document against the general provisions."""
    if not isinstance(document, dict):
        raise ValueError("document must be a mapping, got %r" % (type(document).__name__,))
    document_id = document.get("document_id")
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("document_id must be a non-empty string, got %r" % (document_id,))
    category = document.get("category")
    medium = document.get("medium")
    acceptable = medium_is_acceptable(medium, category)
    shortfall = retention_shortfall_years(category, document.get("retention_years"))
    pages = page_reconciliation(
        document.get("declared_pages"),
        document.get("supplied_pages"),
        document.get("illegible_pages"),
    )
    identification = identification_findings(document)
    findings = list(pages["findings"]) + list(identification)
    if not acceptable:
        findings.append("delivery-medium-below-the-grade-the-category-demands")
    if shortfall > 0.0:
        findings.append("retention-period-short-of-the-demand")
    return {
        "document_id": document_id.strip(),
        "category": category,
        "medium": medium,
        "medium_grade": medium_grade(medium),
        "required_medium_grade": category_requirements(category)["medium_grade"],
        "medium_acceptable": acceptable,
        "retention_shortfall_years": shortfall,
        "pages": pages,
        "identification_findings": identification,
        "findings": findings,
        "conforming": len(findings) == 0,
    }


def provision_weight(name):
    """Weight of one package-level provision; unknown names are rejected."""
    if name not in PROVISION_WEIGHTS:
        raise ValueError(
            "unknown provision %r (known: %s)" % (name, ", ".join(sorted(PROVISION_WEIGHTS)))
        )
    return PROVISION_WEIGHTS[name]


def provision_state_credit(state):
    """Credit a provision state earns."""
    if state not in PROVISION_STATE_CREDIT:
        raise ValueError(
            "unknown provision state %r (known: %s)"
            % (state, ", ".join(sorted(PROVISION_STATE_CREDIT)))
        )
    return PROVISION_STATE_CREDIT[state]


def normalize_provision(raw):
    """Validate one provision record and fill its default state."""
    if not isinstance(raw, dict):
        raise ValueError("provision must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("provision")
    provision_weight(name)  # validation only
    state = raw.get("state", "not-declared")
    provision_state_credit(state)  # validation only
    return {"provision": name, "state": state}


def assess_provision(raw):
    """Grade one package-level provision into a credit and its findings."""
    record = normalize_provision(raw)
    name = record["provision"]
    state = record["state"]
    weight = provision_weight(name)
    credit = provision_state_credit(state)
    findings = []
    if state == "met-with-observation":
        findings.append("provision-observation-open")
    elif state == "deficient":
        findings.append("provision-deficient")
    elif state == "not-declared":
        findings.append("provision-not-declared")
    mandatory = name in MANDATORY_PROVISIONS
    return {
        "provision": name,
        "state": state,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory": mandatory,
        "mandatory_missing": mandatory and state == "not-declared",
        "mandatory_deficient": mandatory and state == "deficient",
        "findings": findings,
    }


def provision_compliance_index(records):
    """Weighted credit of a set of graded provisions over the total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (type(records).__name__,))
    if len(records) == 0:
        raise ValueError("a data package must declare at least one provision")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total provision weight must be positive")
    return earned / total_weight


def assess_data_package_provisions(package_id, documents, provisions):
    """Grade a whole delivery data package against clause 13.2.1 and name a verdict."""
    if not isinstance(package_id, str) or not package_id.strip():
        raise ValueError("package_id must be a non-empty string, got %r" % (package_id,))
    if not isinstance(documents, (list, tuple)):
        raise ValueError("documents must be a list or tuple, got %r" % (type(documents).__name__,))
    if len(documents) == 0:
        raise ValueError("a data package must carry at least one document")
    if not isinstance(provisions, (list, tuple)):
        raise ValueError(
            "provisions must be a list or tuple, got %r" % (type(provisions).__name__,)
        )

    graded_documents = []
    seen = set()
    for document in documents:
        record = assess_document(document)
        if record["document_id"] in seen:
            raise ValueError("duplicate document identifier %r" % (record["document_id"],))
        seen.add(record["document_id"])
        graded_documents.append(record)

    declared = {}
    for raw in provisions:
        record = normalize_provision(raw)
        if record["provision"] in declared:
            raise ValueError("duplicate provision %r" % (record["provision"],))
        declared[record["provision"]] = record
    graded_provisions = []
    for name in sorted(PROVISION_WEIGHTS):
        graded_provisions.append(assess_provision(declared.get(name, {"provision": name})))
    index = provision_compliance_index(graded_provisions)

    findings = []
    for record in graded_documents:
        for finding in record["findings"]:
            findings.append(
                {"item": record["document_id"], "finding": finding, "detail": record["category"]}
            )
    for record in graded_provisions:
        for finding in record["findings"]:
            findings.append(
                {"item": record["provision"], "finding": finding, "detail": record["state"]}
            )

    worst_shortfall = 0.0
    for record in graded_documents:
        worst_shortfall = max(worst_shortfall, record["retention_shortfall_years"])

    incomplete = any(record["mandatory_missing"] for record in graded_provisions)
    not_met = (
        any(not record["conforming"] for record in graded_documents)
        or any(record["mandatory_deficient"] for record in graded_provisions)
        or index < ACCEPTANCE_PROVISION_INDEX - PROVISION_TOLERANCE
    )
    if incomplete:
        verdict = "data-package-provisions-assessment-incomplete"
    elif not_met:
        verdict = "data-package-provisions-not-met"
    elif findings:
        verdict = "data-package-provisions-met-with-open-actions"
    else:
        verdict = "data-package-provisions-met"
    return {
        "package_id": package_id,
        "documents": graded_documents,
        "provisions": graded_provisions,
        "provision_compliance_index": index,
        "worst_retention_shortfall_years": worst_shortfall,
        "findings": findings,
        "verdict": verdict,
        "package_accepted": verdict
        in (
            "data-package-provisions-met",
            "data-package-provisions-met-with-open-actions",
        ),
    }
