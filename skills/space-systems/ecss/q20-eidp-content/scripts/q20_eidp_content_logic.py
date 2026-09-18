"""End item data package content.

Anchor: ECSS-Q-ST-20C clause 5.7.2 with the Annex B document requirements
description (the records that travel with a delivered product to prove its
conformity, and which of them each product type owes). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Resolve the document list the product type owes: the set every delivery
   carries, plus the additions that belong to that type.
2. Normalise the submitted package and refuse a malformed or duplicated entry.
3. Decide, per required document, whether it is present and approved at a
   stated revision, validly declared not applicable, or missing.
4. Refuse a not-applicable declaration on a core record, and demand a
   justification and an approver on the ones where it is admissible.
5. Check the certificate of conformity points at the as-built configuration
   list revision actually in the package.
6. Return the completeness fraction, the extras, and the package verdict.
"""

__all__ = [
    "PRODUCT_TYPES",
    "COMMON_DOCUMENTS",
    "TYPE_DOCUMENTS",
    "CORE_DOCUMENTS",
    "normalise_identifier",
    "required_documents",
    "validate_submission",
    "document_findings",
    "completeness_fraction",
    "conformity_reference_findings",
    "assemble_eidp",
]

# Product types whose data package content differs.
PRODUCT_TYPES = ("equipment", "subsystem", "system", "software", "ground-support-equipment")

# Records every delivery carries, whatever it is.
COMMON_DOCUMENTS = (
    "eidp-index",
    "certificate-of-conformity",
    "as-built-configuration-list",
    "nonconformance-summary",
    "deviation-waiver-list",
    "test-report-list",
    "open-work-list",
)

# What each type adds on top of the common set.
TYPE_DOCUMENTS = {
    "equipment": (
        "limited-life-item-list",
        "mass-properties-record",
        "acceptance-test-data-log",
    ),
    "subsystem": (
        "limited-life-item-list",
        "interface-verification-record",
        "acceptance-test-data-log",
    ),
    "system": (
        "interface-verification-record",
        "verification-control-document-status",
        "operational-limitation-list",
    ),
    "software": (
        "software-version-description",
        "software-problem-report-list",
        "software-release-note",
    ),
    "ground-support-equipment": (
        "calibration-status-record",
        "operating-manual",
        "limited-life-item-list",
    ),
}

# Records that cannot be declared not applicable: without them the package
# proves nothing about what was delivered.
CORE_DOCUMENTS = (
    "eidp-index",
    "certificate-of-conformity",
    "as-built-configuration-list",
)


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def required_documents(product_type):
    """Return the ordered document list a product type owes."""
    key = normalise_identifier(product_type, "product_type")
    if key not in PRODUCT_TYPES:
        raise ValueError(
            "product_type must be one of %s, got %r" % ("/".join(PRODUCT_TYPES), product_type)
        )
    return tuple(COMMON_DOCUMENTS) + tuple(TYPE_DOCUMENTS[key])


def validate_submission(submission):
    """Return the normalised submitted package keyed by document id."""
    if not isinstance(submission, (list, tuple)) or not submission:
        raise ValueError("submission must be a non-empty sequence")
    entries = {}
    for index, item in enumerate(submission):
        if not isinstance(item, dict):
            raise ValueError("submission[%d] must be a mapping" % index)
        doc = normalise_identifier(item.get("document"), "submission[%d].document" % index)
        if doc in entries:
            raise ValueError("document %r is submitted twice" % doc)
        not_applicable = bool(item.get("not_applicable", False))
        entry = {
            "document": doc,
            "not_applicable": not_applicable,
            "revision": None,
            "approved": False,
            "justification": None,
            "approved_by": None,
            "references": {},
        }
        if not_applicable:
            justification = item.get("justification")
            if justification is not None:
                if not isinstance(justification, str) or not justification.strip():
                    raise ValueError(
                        "submission[%d].justification must be a non-empty string" % index
                    )
                entry["justification"] = justification.strip()
            approver = item.get("approved_by")
            entry["approved_by"] = (
                None if approver is None
                else normalise_identifier(approver, "submission[%d].approved_by" % index)
            )
        else:
            entry["revision"] = normalise_identifier(
                item.get("revision"), "submission[%d].revision" % index
            )
            entry["approved"] = bool(item.get("approved", False))
            raw_refs = item.get("references", {})
            if not isinstance(raw_refs, dict):
                raise ValueError("submission[%d].references must be a mapping" % index)
            entry["references"] = {
                normalise_identifier(key, "submission[%d].references key" % index):
                    normalise_identifier(value, "submission[%d].references value" % index)
                for key, value in raw_refs.items()
            }
        entries[doc] = entry
    return entries


def document_findings(product_type, entries):
    """Return the per-document result of a submitted package."""
    required = required_documents(product_type)
    missing = []
    unapproved = []
    accepted_not_applicable = []
    refused_not_applicable = []
    satisfied = 0
    for doc in required:
        entry = entries.get(doc)
        if entry is None:
            missing.append(doc)
            continue
        if entry["not_applicable"]:
            if doc in CORE_DOCUMENTS:
                refused_not_applicable.append(
                    "%s is a core record and cannot be declared not applicable" % doc
                )
                continue
            if entry["justification"] is None:
                refused_not_applicable.append(
                    "%s is declared not applicable with no justification" % doc
                )
                continue
            if entry["approved_by"] is None:
                refused_not_applicable.append(
                    "%s is declared not applicable with no approver" % doc
                )
                continue
            accepted_not_applicable.append(doc)
            satisfied += 1
            continue
        if not entry["approved"]:
            unapproved.append(doc)
            continue
        satisfied += 1
    extras = sorted(doc for doc in entries if doc not in required)
    findings = []
    if missing:
        findings.append("records the package does not carry: %s" % ", ".join(missing))
    if unapproved:
        findings.append("records present but not approved: %s" % ", ".join(unapproved))
    findings.extend(refused_not_applicable)
    return {
        "required_count": len(required),
        "satisfied_count": satisfied,
        "missing": missing,
        "unapproved": unapproved,
        "accepted_not_applicable": accepted_not_applicable,
        "extras": extras,
        "findings": findings,
    }


def completeness_fraction(result):
    """Return the satisfied fraction of the required document list."""
    if not isinstance(result, dict):
        raise ValueError("result must be the mapping returned by document_findings")
    for key in ("required_count", "satisfied_count"):
        if key not in result:
            raise ValueError("result is missing '%s'" % key)
    if result["required_count"] <= 0:
        raise ValueError("required_count must be positive")
    return result["satisfied_count"] / float(result["required_count"])


def conformity_reference_findings(entries):
    """Return findings where the certificate and the as-built list disagree."""
    certificate = entries.get("certificate-of-conformity")
    as_built = entries.get("as-built-configuration-list")
    if certificate is None or as_built is None:
        return []
    if certificate["not_applicable"] or as_built["not_applicable"]:
        return []
    cited = certificate["references"].get("as-built-configuration-list")
    if cited is None:
        return ["certificate of conformity cites no as-built configuration list revision"]
    if cited != as_built["revision"]:
        return [
            "certificate of conformity cites as-built revision %s while the package carries %s"
            % (cited, as_built["revision"])
        ]
    return []


def assemble_eidp(product_type, submission):
    """Grade a whole end item data package and return its verdict."""
    entries = validate_submission(submission)
    result = document_findings(product_type, entries)
    findings = list(result["findings"])
    findings.extend(conformity_reference_findings(entries))
    return {
        "product_type": normalise_identifier(product_type, "product_type"),
        "required_count": result["required_count"],
        "satisfied_count": result["satisfied_count"],
        "completeness_fraction": completeness_fraction(result),
        "missing": result["missing"],
        "unapproved": result["unapproved"],
        "accepted_not_applicable": result["accepted_not_applicable"],
        "extras": result["extras"],
        "findings": findings,
        "verdict": "package-complete" if not findings else "package-incomplete",
    }
