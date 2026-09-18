"""End item data package document requirements description.

Anchor: ECSS-Q-ST-20C Annex B (normative), the document requirements
description for the end item data package: the package is built as an ordered
document set grouped by category -- design data, manufacturing data, test data
and acceptance data -- and the DRD fixes which document belongs in which
category and in what order the package presents them. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the DRD assignment of every recognised document to its category.
2. Emit the DRD table of contents: categories in order, documents numbered
   inside their category.
3. Normalise a submitted package, refusing a malformed or duplicated entry.
4. Group each submitted document under the category the DRD assigns it, and
   raise a document filed under the wrong category as its own finding.
5. Name the documents each category is short of, and list unrecognised
   documents as extras rather than failing on them.
6. Return the per-category and whole-package completeness, and the verdict.
"""

__all__ = [
    "DRD_CATEGORIES",
    "CATEGORY_DOCUMENTS",
    "DOCUMENT_CATEGORY",
    "normalise_identifier",
    "category_of",
    "drd_table_of_contents",
    "validate_documents",
    "group_submission",
    "category_findings",
    "misfiled_findings",
    "package_completeness",
    "assess_eidp_drd",
]

# The package is presented in this order; the order is part of the DRD.
DRD_CATEGORIES = ("design", "manufacturing", "test", "acceptance")

# The document set each category owes, in the order the DRD lists them.
CATEGORY_DOCUMENTS = {
    "design": (
        "design-definition-file-index",
        "as-designed-configuration-list",
        "drawing-and-part-list",
        "deviation-and-waiver-register",
    ),
    "manufacturing": (
        "as-built-configuration-list",
        "manufacturing-route-card-set",
        "material-and-process-certificate-set",
        "limited-life-item-register",
    ),
    "test": (
        "test-procedure-index",
        "test-report-index",
        "test-data-log",
        "calibration-certificate-set",
    ),
    "acceptance": (
        "acceptance-review-minutes",
        "certificate-of-conformity",
        "open-work-and-nonconformance-status",
        "delivery-note",
    ),
}

# Reverse lookup built once: document -> the category the DRD puts it in.
DOCUMENT_CATEGORY = {
    document: category
    for category, documents in CATEGORY_DOCUMENTS.items()
    for document in documents
}


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower().replace("_", "-")
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def category_of(document):
    """Return the DRD category of a document, or None if unrecognised."""
    return DOCUMENT_CATEGORY.get(normalise_identifier(document, "document"))


def drd_table_of_contents():
    """Return the DRD table of contents: categories in order, numbered."""
    contents = []
    for index, category in enumerate(DRD_CATEGORIES, start=1):
        entries = []
        for sub_index, document in enumerate(CATEGORY_DOCUMENTS[category], start=1):
            entries.append(
                {"number": "%d.%d" % (index, sub_index), "document": document}
            )
        contents.append(
            {"number": str(index), "category": category, "documents": tuple(entries)}
        )
    return tuple(contents)


def validate_documents(submission):
    """Return the normalised submitted document set keyed by document id."""
    if not isinstance(submission, (list, tuple)) or not submission:
        raise ValueError("submission must be a non-empty sequence")
    entries = {}
    for index, item in enumerate(submission):
        if not isinstance(item, dict):
            raise ValueError("submission[%d] must be a mapping" % index)
        document = normalise_identifier(
            item.get("document"), "submission[%d].document" % index
        )
        if document in entries:
            raise ValueError("document %r is submitted twice" % document)
        identifier = normalise_identifier(
            item.get("identifier"), "submission[%d].identifier" % index
        )
        issue = item.get("issue")
        if not isinstance(issue, int) or isinstance(issue, bool) or issue < 1:
            raise ValueError(
                "submission[%d].issue must be an integer of at least 1, got %r"
                % (index, issue)
            )
        declared = item.get("category")
        entries[document] = {
            "document": document,
            "identifier": identifier,
            "issue": issue,
            "declared_category": (
                None
                if declared is None
                else normalise_identifier(declared, "submission[%d].category" % index)
            ),
        }
    return entries


def group_submission(entries):
    """Return the submitted documents grouped under their DRD category."""
    if not isinstance(entries, dict):
        raise ValueError("entries must be the mapping returned by validate_documents")
    grouped = {category: [] for category in DRD_CATEGORIES}
    unassigned = []
    for document in sorted(entries):
        category = DOCUMENT_CATEGORY.get(document)
        if category is None:
            unassigned.append(document)
        else:
            grouped[category].append(document)
    grouped["unassigned"] = unassigned
    return grouped


def misfiled_findings(entries):
    """Return findings where a document is filed under the wrong category."""
    findings = []
    for document in sorted(entries):
        declared = entries[document]["declared_category"]
        if declared is None:
            continue
        owed = DOCUMENT_CATEGORY.get(document)
        if owed is None:
            if declared not in DRD_CATEGORIES:
                findings.append(
                    "%s is filed under %s, which is not a package category"
                    % (document, declared)
                )
            continue
        if declared != owed:
            findings.append(
                "%s is filed under %s but belongs to the %s data of the package"
                % (document, declared, owed)
            )
    return findings


def category_findings(entries):
    """Return the per-category completeness of a submitted package."""
    grouped = group_submission(entries)
    result = {}
    satisfied_total = 0
    required_total = 0
    missing_any = []
    for category in DRD_CATEGORIES:
        owed = CATEGORY_DOCUMENTS[category]
        present = [document for document in owed if document in entries]
        absent = [document for document in owed if document not in entries]
        required_total += len(owed)
        satisfied_total += len(present)
        if absent:
            missing_any.append(
                "%s data is short of %s" % (category, ", ".join(absent))
            )
        result[category] = {
            "required_count": len(owed),
            "present_count": len(present),
            "missing": absent,
            "fraction": len(present) / float(len(owed)),
        }
    return {
        "categories": result,
        "required_count": required_total,
        "present_count": satisfied_total,
        "extras": grouped["unassigned"],
        "findings": missing_any,
    }


def package_completeness(result):
    """Return the present fraction of the whole DRD document set."""
    if not isinstance(result, dict):
        raise ValueError("result must be the mapping returned by category_findings")
    for key in ("required_count", "present_count"):
        if key not in result:
            raise ValueError("result is missing '%s'" % key)
    if result["required_count"] <= 0:
        raise ValueError("required_count must be positive")
    return result["present_count"] / float(result["required_count"])


def assess_eidp_drd(submission):
    """Grade a package against the Annex B DRD document set and order."""
    entries = validate_documents(submission)
    result = category_findings(entries)
    findings = list(result["findings"])
    findings.extend(misfiled_findings(entries))
    return {
        "required_count": result["required_count"],
        "present_count": result["present_count"],
        "completeness_fraction": package_completeness(result),
        "categories": result["categories"],
        "grouped": group_submission(entries),
        "extras": result["extras"],
        "findings": findings,
        "verdict": "package-drd-conformant" if not findings else "package-drd-nonconformant",
    }
