"""Reconciling a Class 3 shipment against the manufacturer data delivered with it.

Anchor: ECSS-Q-ST-60C clause 6.3.11 (the certificates of conformity and the
supporting manufacturer records that accompany a Class 3 delivery). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Take the shipment as the sub-lots it actually contains, each with its own
   identity and its own quantity, rather than as one purchase-order line.
2. Derive the document set this delivery owes from the part profile, keeping the
   core items separate from the ones a part attribute brings in.
3. Test every delivered document for admissibility: an identifier and an issue,
   an issue date inside the delivery window, a signature where one is owed, and
   a certified specification revision matching the revision ordered.
4. Map each admissible document onto the sub-lots it names, ignoring names that
   were never shipped and reporting them.
5. Take coverage by shipped quantity rather than by document count, so a
   certificate covering two sub-lots out of five is not read as coverage.
6. Release each sub-lot only where every core item reaches it, and return one
   delivery verdict with the reasons and the releasable quantity named.
"""

import datetime

__all__ = [
    "DELIVERY_VERDICTS",
    "DOCUMENT_TYPES",
    "CORE_DOCUMENT_TYPES",
    "SIGNATURE_REQUIRED_TYPES",
    "REQUIRED_SUBLOT_FIELDS",
    "REQUIRED_DOCUMENT_FIELDS",
    "parse_iso_date",
    "conditional_document_types",
    "required_document_types",
    "document_admissibility",
    "quantity_coverage",
    "coverage_by_type",
    "releasable_sublots",
    "delivery_verdict",
    "assess_data_delivery",
]

# Verdicts, from a delivery that may go to stores whole to one that stays at the dock.
DELIVERY_VERDICTS = (
    "accept",
    "accept-pending-data",
    "partial-acceptance",
    "reject-at-dock",
)

# Every record this clause recognises as part of a delivered data package.
DOCUMENT_TYPES = (
    "certificate-of-conformity",
    "screening-test-data",
    "lot-acceptance-test-report",
    "destructive-physical-analysis-report",
    "radiation-test-report",
    "die-lot-traceability-record",
)

# The items no part attribute removes; a sub-lot they miss is not releasable.
CORE_DOCUMENT_TYPES = (
    "certificate-of-conformity",
    "screening-test-data",
)

# Items that only mean something when an accountable person has signed them.
SIGNATURE_REQUIRED_TYPES = (
    "certificate-of-conformity",
    "lot-acceptance-test-report",
)

REQUIRED_SUBLOT_FIELDS = ("sublot_id", "part_number", "quantity", "manufactured_on")

REQUIRED_DOCUMENT_FIELDS = ("doc_type", "doc_id", "issue", "issue_date", "covers")


def parse_iso_date(value, label="date"):
    """Return an ISO date string or date object as a date."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (label, value))


def conditional_document_types(part_profile):
    """Return the items a part attribute brings into the owed set."""
    if not isinstance(part_profile, dict):
        raise ValueError("part_profile must be a mapping of attribute to bool")
    mapping = (
        ("lot_acceptance_required", "lot-acceptance-test-report"),
        ("destructive_analysis_required", "destructive-physical-analysis-report"),
        ("radiation_sensitive", "radiation-test-report"),
        ("die_level_traceability", "die-lot-traceability-record"),
    )
    known = {name for name, _ in mapping}
    for key, value in part_profile.items():
        if key not in known:
            raise ValueError("part_profile carries unknown attribute %r" % (key,))
        if not isinstance(value, bool):
            raise ValueError("part_profile[%r] must be a bool, got %r" % (key, value))
    return tuple(doc for name, doc in mapping if part_profile.get(name, False))


def required_document_types(part_profile):
    """Return the whole owed set, core items first."""
    return CORE_DOCUMENT_TYPES + conditional_document_types(part_profile)


def document_admissibility(document, ordered_spec_revision, receipt_date,
                           earliest_manufactured_on):
    """Return whether one delivered document counts, and why it does not.

    A document that is present but inadmissible is worse than one that is
    absent, because it looks like coverage in a document count and is not.
    """
    if not isinstance(document, dict):
        raise ValueError("document must be a mapping")
    for field in REQUIRED_DOCUMENT_FIELDS:
        if field not in document or document[field] in (None, "", [], ()):
            raise ValueError("document missing required field '%s'" % field)
    doc_type = str(document["doc_type"]).strip()
    if doc_type not in DOCUMENT_TYPES:
        raise ValueError("unknown document type %r" % (doc_type,))
    covers = document["covers"]
    if not isinstance(covers, (list, tuple)) or not covers:
        raise ValueError("document['covers'] must be a non-empty sequence of sub-lots")
    received = parse_iso_date(receipt_date, "receipt_date")
    earliest = parse_iso_date(earliest_manufactured_on, "earliest_manufactured_on")
    if earliest > received:
        raise ValueError("the shipment was manufactured after it was received")
    issued = parse_iso_date(document["issue_date"], "issue_date")

    reasons = []
    if issued > received:
        reasons.append("issued after the delivery arrived")
    if issued < earliest:
        reasons.append("issued before the earliest sub-lot was made")
    if doc_type in SIGNATURE_REQUIRED_TYPES:
        signer = document.get("signed_by")
        if not isinstance(signer, str) or not signer.strip():
            reasons.append("carries no accountable signature")
    if doc_type == "certificate-of-conformity":
        certified = document.get("spec_revision")
        if not isinstance(certified, str) or not certified.strip():
            reasons.append("certifies against no specification revision")
        elif certified.strip().upper() != str(ordered_spec_revision).strip().upper():
            reasons.append(
                "certifies revision %s against the ordered revision %s"
                % (certified.strip(), ordered_spec_revision)
            )
    return {"admissible": not reasons, "reasons": tuple(reasons)}


def quantity_coverage(sublots, covered_sublot_ids):
    """Return the shipped quantity the named sub-lots account for.

    Counting documents flatters a delivery; counting the parts those documents
    actually reach does not.
    """
    if not isinstance(sublots, (list, tuple)) or not sublots:
        raise ValueError("sublots must be a non-empty sequence")
    if not isinstance(covered_sublot_ids, (set, frozenset, list, tuple)):
        raise ValueError("covered_sublot_ids must be a collection of sub-lot ids")
    covered = set(covered_sublot_ids)
    total = 0
    reached = 0
    for index, sublot in enumerate(sublots):
        quantity = sublot.get("quantity") if isinstance(sublot, dict) else None
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            raise ValueError("sublots[%d]['quantity'] must be a positive integer" % index)
        total += quantity
        if str(sublot.get("sublot_id", "")).strip() in covered:
            reached += quantity
    return {
        "quantity_total": total,
        "quantity_covered": reached,
        "complete": reached == total,
        "coverage": reached / total,
    }


def coverage_by_type(sublots, documents, owed_types, ordered_spec_revision,
                     receipt_date, earliest_manufactured_on):
    """Return, per owed item, the sub-lots it reaches and the quantity that is."""
    if not isinstance(documents, (list, tuple)):
        raise ValueError("documents must be a sequence of delivered records")
    shipped_ids = {str(s["sublot_id"]).strip() for s in sublots}
    result = {}
    inadmissible = []
    unknown_references = []
    for doc_type in owed_types:
        result[doc_type] = set()
    for document in documents:
        verdict = document_admissibility(
            document, ordered_spec_revision, receipt_date, earliest_manufactured_on
        )
        doc_type = str(document["doc_type"]).strip()
        named = [str(name).strip() for name in document["covers"]]
        for name in named:
            if name not in shipped_ids:
                unknown_references.append((str(document["doc_id"]).strip(), name))
        if not verdict["admissible"]:
            inadmissible.append(
                {
                    "doc_id": str(document["doc_id"]).strip(),
                    "doc_type": doc_type,
                    "reasons": verdict["reasons"],
                }
            )
            continue
        if doc_type in result:
            result[doc_type].update(name for name in named if name in shipped_ids)
    coverage = {}
    for doc_type, covered in result.items():
        entry = quantity_coverage(sublots, covered)
        entry["covered_sublot_ids"] = tuple(sorted(covered))
        coverage[doc_type] = entry
    return {
        "coverage": coverage,
        "inadmissible": tuple(
            sorted(inadmissible, key=lambda item: (item["doc_type"], item["doc_id"]))
        ),
        "unknown_references": tuple(sorted(set(unknown_references))),
    }


def releasable_sublots(sublots, coverage):
    """Return the sub-lots every core item reaches."""
    if not isinstance(coverage, dict):
        raise ValueError("coverage must be the per-type coverage mapping")
    releasable = []
    for sublot in sublots:
        sublot_id = str(sublot["sublot_id"]).strip()
        if all(
            sublot_id in coverage.get(core, {}).get("covered_sublot_ids", ())
            for core in CORE_DOCUMENT_TYPES
        ):
            releasable.append(sublot_id)
    return tuple(sorted(releasable))


def delivery_verdict(core_complete, core_any, conditional_complete, inadmissible_count):
    """Return the verdict one delivery has earned."""
    for label, flag in (
        ("core_complete", core_complete),
        ("core_any", core_any),
        ("conditional_complete", conditional_complete),
    ):
        if not isinstance(flag, bool):
            raise ValueError("%s must be a bool, got %r" % (label, flag))
    if not isinstance(inadmissible_count, int) or isinstance(inadmissible_count, bool):
        raise ValueError("inadmissible_count must be an integer")
    if inadmissible_count < 0:
        raise ValueError("inadmissible_count must not be negative")
    if not core_any:
        return "reject-at-dock"
    if not core_complete:
        return "partial-acceptance"
    if not conditional_complete:
        return "accept-pending-data"
    return "accept"


def assess_data_delivery(sublots, documents, ordered_spec_revision, receipt_date,
                         part_profile=None):
    """Run the full clause 6.3.11 delivered-data reconciliation for one shipment."""
    if not isinstance(sublots, (list, tuple)) or not sublots:
        raise ValueError("sublots must be a non-empty sequence of sub-lot records")
    if not isinstance(ordered_spec_revision, str) or not ordered_spec_revision.strip():
        raise ValueError("ordered_spec_revision must be a non-empty string")
    profile = part_profile or {}

    seen = set()
    earliest = None
    for index, sublot in enumerate(sublots):
        if not isinstance(sublot, dict):
            raise ValueError("sublots[%d] must be a mapping" % index)
        for field in REQUIRED_SUBLOT_FIELDS:
            if field not in sublot or sublot[field] in (None, ""):
                raise ValueError("sublots[%d] missing required field '%s'" % (index, field))
        sublot_id = str(sublot["sublot_id"]).strip()
        if sublot_id in seen:
            raise ValueError("sub-lot %s appears twice in one shipment" % sublot_id)
        seen.add(sublot_id)
        made = parse_iso_date(sublot["manufactured_on"], "manufactured_on")
        earliest = made if earliest is None else min(earliest, made)

    owed = required_document_types(profile)
    mapped = coverage_by_type(
        sublots, documents, owed, ordered_spec_revision, receipt_date, earliest
    )
    coverage = mapped["coverage"]
    conditional = conditional_document_types(profile)

    core_complete = all(coverage[core]["complete"] for core in CORE_DOCUMENT_TYPES)
    core_any = all(
        coverage[core]["quantity_covered"] > 0 for core in CORE_DOCUMENT_TYPES
    )
    conditional_complete = all(coverage[item]["complete"] for item in conditional)
    released = releasable_sublots(sublots, coverage)
    verdict = delivery_verdict(
        core_complete, core_any, conditional_complete, len(mapped["inadmissible"])
    )

    findings = []
    for doc_type in owed:
        entry = coverage[doc_type]
        if not entry["complete"]:
            findings.append(
                "%s reaches %d of the %d parts shipped"
                % (doc_type, entry["quantity_covered"], entry["quantity_total"])
            )
    for item in mapped["inadmissible"]:
        findings.append(
            "%s %s is not admissible: %s"
            % (item["doc_type"], item["doc_id"], "; ".join(item["reasons"]))
        )
    for doc_id, name in mapped["unknown_references"]:
        findings.append("%s names sub-lot %s, which was not shipped" % (doc_id, name))

    quantity_total = sum(int(s["quantity"]) for s in sublots)
    quantity_released = sum(
        int(s["quantity"]) for s in sublots if str(s["sublot_id"]).strip() in released
    )
    return {
        "receipt_date": parse_iso_date(receipt_date, "receipt_date").isoformat(),
        "ordered_spec_revision": ordered_spec_revision.strip().upper(),
        "owed_document_types": owed,
        "conditional_document_types": conditional,
        "coverage": coverage,
        "inadmissible": mapped["inadmissible"],
        "unknown_references": mapped["unknown_references"],
        "releasable_sublots": released,
        "quantity_total": quantity_total,
        "quantity_released": quantity_released,
        "release_fraction": quantity_released / quantity_total,
        "verdict": verdict,
        "findings": findings,
        "package_complete": not findings,
    }
