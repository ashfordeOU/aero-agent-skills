"""ECSS-E-ST-10-24C Annex C Interface Definition Document DRD (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the Annex C
Document Requirements Definition governs the Interface Definition Document (IDD),
which captures each interface of a product at the applicable decomposition level.
Each interface record names the interface type, the mating item, and the set of
characteristics that define the interface. When the IDD serves as a single-end
ICD it additionally carries a reference to the bilateral ICD once one exists.
An agreed interface must cite its bilateral ICD reference; a superseded interface
must cite its successor so the traceability chain is not broken.
"""

INTERFACE_TYPES = (
    "physical", "functional", "operational", "data",
    "electrical", "mechanical", "thermal", "optical", "rf",
)

INTERFACE_STATUSES = ("draft", "under_review", "agreed", "superseded")

STATUS_AGREED = "agreed"
STATUS_DRAFT = "draft"
STATUS_UNDER_REVIEW = "under_review"
STATUS_SUPERSEDED = "superseded"

FINDING_MISSING_MATING_ITEM = "missing_mating_item"
FINDING_EMPTY_CHARACTERISTICS = "characteristics_not_defined"
FINDING_AGREED_WITHOUT_ICD_REF = "agreed_interface_lacks_icd_reference"
FINDING_SUPERSEDED_WITHOUT_SUCCESSOR = "superseded_without_successor_reference"


def validate_interface_type(itype):
    """Return itype if it is a recognized ECSS-E-ST-10-24C interface type, else raise."""
    if itype not in INTERFACE_TYPES:
        raise ValueError("unknown interface type: %r" % (itype,))
    return itype


def validate_status(status):
    """Return status if it is a recognized interface lifecycle status, else raise."""
    if status not in INTERFACE_STATUSES:
        raise ValueError("unknown interface status: %r" % (status,))
    return status


def interface_record_findings(interface_id, record):
    """Finding list (empty if clean) for one interface record.

    record: {"interface_type": str, "mating_item": str | None,
             "characteristics": dict | None, "status": str,
             "icd_reference": str | None, "successor_id": str | None}

    Type and status are validated first and raise on an unrecognized value,
    because a record with an invalid type or status cannot be graded at all.
    """
    validate_interface_type(record.get("interface_type"))
    validate_status(record.get("status"))
    findings = []

    if not record.get("mating_item"):
        findings.append({"interface_id": interface_id,
                         "issue": FINDING_MISSING_MATING_ITEM})

    if not record.get("characteristics"):
        findings.append({"interface_id": interface_id,
                         "issue": FINDING_EMPTY_CHARACTERISTICS})

    if record.get("status") == STATUS_AGREED and not record.get("icd_reference"):
        findings.append({"interface_id": interface_id,
                         "issue": FINDING_AGREED_WITHOUT_ICD_REF})

    if record.get("status") == STATUS_SUPERSEDED and not record.get("successor_id"):
        findings.append({"interface_id": interface_id,
                         "issue": FINDING_SUPERSEDED_WITHOUT_SUCCESSOR})

    return findings


def type_coverage(interfaces):
    """Sorted list of distinct interface types present across a set of records."""
    return sorted({validate_interface_type(r.get("interface_type"))
                   for r in interfaces})


def status_tally(interfaces):
    """Count of interfaces per lifecycle status: {status: count}."""
    tally = {s: 0 for s in INTERFACE_STATUSES}
    for r in interfaces:
        s = validate_status(r.get("status"))
        tally[s] += 1
    return tally


def idd_review(idd):
    """Full Annex C IDD review for one product.

    idd: {"document_id": str, "product_id": str,
          "interfaces": [{"interface_id": str, "interface_type": str,
                          "mating_item": str, "characteristics": dict,
                          "status": str,
                          "icd_reference": str | None,
                          "successor_id": str | None}]}

    Returns {"document_id", "product_id", "agreed", "draft", "under_review",
             "superseded", "findings"}. Raises ValueError for a duplicate
     interface id or a record with no interface_id.
    """
    buckets = {s: [] for s in INTERFACE_STATUSES}
    findings = []
    seen = set()

    for record in idd.get("interfaces", []):
        iid = record.get("interface_id")
        if not iid:
            raise ValueError("interface record with no interface_id")
        if iid in seen:
            raise ValueError("duplicate interface_id: %s" % iid)
        seen.add(iid)
        findings += interface_record_findings(iid, record)
        buckets[validate_status(record.get("status"))].append(iid)

    return {
        "document_id": idd.get("document_id"),
        "product_id": idd.get("product_id"),
        "agreed": buckets[STATUS_AGREED],
        "draft": buckets[STATUS_DRAFT],
        "under_review": buckets[STATUS_UNDER_REVIEW],
        "superseded": buckets[STATUS_SUPERSEDED],
        "findings": findings,
    }


def is_idd_complete(review):
    """True when no interface is in draft or under_review and no finding stands.

    Agreed and superseded-with-successor are terminal valid states; a superseded
    entry whose successor is missing is already captured as a finding, so
    checking the findings list is sufficient for that case.
    """
    return (not review["draft"] and not review["under_review"]
            and not review["findings"])
