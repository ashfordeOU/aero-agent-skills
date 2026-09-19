"""What accompanies a shipped batch of hybrids, and how the pack is shaped.

Anchor: ECSS-Q-ST-60-05C clause 13.1 (the general delivery requirements: what
travels with a delivered hybrid batch and the overall shape of its delivery
package). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the delivery: the serial numbers actually shipped, the serial
   numbers the data pack holds records for, the documents in the pack, the
   packaging provisions, and the build attributes that change what is owed.
2. Assemble the documents this particular delivery owes. A base set travels
   with every batch; a nonconformance raised during the build, an enhanced
   reliability level and a hermetic package each add their own.
3. Measure serial coverage at the unit, not at the batch. A data pack is not
   complete because it is thick: it is complete when every shipped serial has
   a record, and records for serials that did not ship are their own finding.
4. Check the packaging provisions against the package type, since a
   non-hermetic hybrid carries a moisture obligation a hermetic one does not.
5. Return release or hold, with the missing documents, the uncovered serials,
   the orphan records and the packaging gaps named separately, because they
   are corrected by different people.
"""

__all__ = [
    "BASE_DELIVERY_DOCUMENTS",
    "NONCONFORMANCE_DOCUMENT",
    "ENHANCED_LEVEL_DOCUMENT",
    "HERMETIC_PACKAGE_DOCUMENT",
    "RELIABILITY_LEVELS",
    "COVERAGE_TOLERANCE",
    "normalise_name",
    "validate_delivery",
    "required_documents",
    "missing_documents",
    "uncovered_serials",
    "orphan_records",
    "serial_coverage",
    "packaging_gaps",
    "verify_delivery_package",
]

# Documents that travel with every delivered hybrid batch.
BASE_DELIVERY_DOCUMENTS = (
    "certificate-of-conformity",
    "acceptance-test-data-pack",
    "screening-data-pack",
    "lot-traceability-record",
    "packaging-and-handling-record",
    "marking-record",
)

# Added when a nonconformance was raised anywhere in the build.
NONCONFORMANCE_DOCUMENT = "nonconformance-report"

# Added when the batch was built at the enhanced reliability level.
ENHANCED_LEVEL_DOCUMENT = "construction-analysis-report"

# Added when the hybrids are hermetically sealed.
HERMETIC_PACKAGE_DOCUMENT = "hermeticity-test-record"

RELIABILITY_LEVELS = ("standard", "enhanced")

# Serial coverage is a quotient of integers landing exactly on one for a
# complete pack; the comparison absorbs representation error at that bound.
COVERAGE_TOLERANCE = 1e-9


def normalise_name(value, label):
    """Return a name normalised for case and separator, raising on an empty one."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def _normalise_serial_list(values, label):
    """Return serial numbers as an ordered list, raising on a duplicate."""
    if isinstance(values, str) or not isinstance(values, (list, tuple)):
        raise ValueError("%s must be a sequence of serial numbers" % label)
    seen = set()
    ordered = []
    for index, value in enumerate(values):
        serial = normalise_name(value, "%s[%d]" % (label, index))
        if serial in seen:
            raise ValueError("%s repeats serial number %r" % (label, serial))
        seen.add(serial)
        ordered.append(serial)
    return ordered


def validate_delivery(delivery):
    """Return the delivery normalised, raising on anything unusable.

    An absent document list or packaging record normalises to empty: a batch
    shipped with no paperwork is a real delivery to be graded, not an input
    error to be refused at the door.
    """
    if not isinstance(delivery, dict):
        raise ValueError("delivery must be a mapping")
    if "delivered_serials" not in delivery:
        raise ValueError("delivery missing required key 'delivered_serials'")
    delivered = _normalise_serial_list(delivery["delivered_serials"], "delivered_serials")
    if not delivered:
        raise ValueError("a delivery of no units has nothing to accompany")
    documented = _normalise_serial_list(
        delivery.get("data_pack_serials", ()), "data_pack_serials"
    )
    documents = delivery.get("documents", ())
    if isinstance(documents, str) or not isinstance(documents, (list, tuple, set, frozenset)):
        raise ValueError("documents must be a sequence of document names")
    document_names = {normalise_name(d, "document name") for d in documents}
    level = normalise_name(delivery.get("reliability_level", "standard"), "reliability_level")
    if level not in RELIABILITY_LEVELS:
        raise ValueError(
            "reliability_level must be one of %s" % ", ".join(RELIABILITY_LEVELS)
        )
    nonconformances = delivery.get("nonconformances_raised", 0)
    if isinstance(nonconformances, bool) or not isinstance(nonconformances, int):
        raise ValueError("nonconformances_raised must be an integer")
    if nonconformances < 0:
        raise ValueError("nonconformances_raised must not be negative")
    hermetic = delivery.get("hermetic", False)
    if not isinstance(hermetic, bool):
        raise ValueError("hermetic must be a boolean")
    packaging = delivery.get("packaging", {})
    if not isinstance(packaging, dict):
        raise ValueError("packaging must be a mapping")
    normalised_packaging = {}
    for key in ("esd_protective_packaging", "individual_unit_separation", "desiccant_and_humidity_indicator"):
        value = packaging.get(key, False)
        if not isinstance(value, bool):
            raise ValueError("packaging['%s'] must be a boolean" % key)
        normalised_packaging[key] = value
    return {
        "delivered_serials": delivered,
        "data_pack_serials": documented,
        "documents": document_names,
        "reliability_level": level,
        "nonconformances_raised": nonconformances,
        "hermetic": hermetic,
        "packaging": normalised_packaging,
    }


def required_documents(delivery):
    """Return the documents this delivery owes, in a stable order."""
    d = validate_delivery(delivery)
    documents = list(BASE_DELIVERY_DOCUMENTS)
    if d["nonconformances_raised"] > 0:
        documents.append(NONCONFORMANCE_DOCUMENT)
    if d["reliability_level"] == "enhanced":
        documents.append(ENHANCED_LEVEL_DOCUMENT)
    if d["hermetic"]:
        documents.append(HERMETIC_PACKAGE_DOCUMENT)
    return documents


def missing_documents(delivery):
    """Return the owed documents the delivery package did not carry."""
    d = validate_delivery(delivery)
    return [name for name in required_documents(delivery) if name not in d["documents"]]


def uncovered_serials(delivery):
    """Return the shipped serial numbers the data pack holds no record for."""
    d = validate_delivery(delivery)
    held = set(d["data_pack_serials"])
    return [serial for serial in d["delivered_serials"] if serial not in held]


def orphan_records(delivery):
    """Return the data pack records for serial numbers that did not ship."""
    d = validate_delivery(delivery)
    shipped = set(d["delivered_serials"])
    return [serial for serial in d["data_pack_serials"] if serial not in shipped]


def serial_coverage(delivery):
    """Return the fraction of shipped units the data pack accounts for."""
    d = validate_delivery(delivery)
    covered = len(d["delivered_serials"]) - len(uncovered_serials(delivery))
    return covered / float(len(d["delivered_serials"]))


def packaging_gaps(delivery):
    """Return the packaging provisions this delivery is short of."""
    d = validate_delivery(delivery)
    packaging = d["packaging"]
    gaps = []
    if not packaging["esd_protective_packaging"]:
        gaps.append("no electrostatic protective packaging recorded")
    if len(d["delivered_serials"]) > 1 and not packaging["individual_unit_separation"]:
        gaps.append("units are not separated inside the shipping container")
    if not d["hermetic"] and not packaging["desiccant_and_humidity_indicator"]:
        gaps.append("non-hermetic units shipped without desiccant and a humidity indicator")
    return gaps


def verify_delivery_package(delivery):
    """Run the full clause 13.1 delivery package verification for one batch."""
    d = validate_delivery(delivery)
    absent = missing_documents(delivery)
    uncovered = uncovered_serials(delivery)
    orphans = orphan_records(delivery)
    gaps = packaging_gaps(delivery)
    coverage = serial_coverage(delivery)
    fully_covered = abs(coverage - 1.0) <= COVERAGE_TOLERANCE

    holds = []
    if absent:
        holds.append("delivery documentation incomplete: %s" % ", ".join(absent))
    if uncovered:
        holds.append(
            "%d shipped unit(s) carry no data pack record: %s"
            % (len(uncovered), ", ".join(uncovered))
        )
    if orphans:
        holds.append(
            "data pack holds records for %d unit(s) that did not ship: %s"
            % (len(orphans), ", ".join(orphans))
        )
    for gap in gaps:
        holds.append(gap)

    return {
        "units_delivered": len(d["delivered_serials"]),
        "records_supplied": len(d["data_pack_serials"]),
        "required_documents": required_documents(delivery),
        "missing_documents": absent,
        "uncovered_serials": uncovered,
        "orphan_records": orphans,
        "serial_coverage": coverage,
        "fully_covered": fully_covered,
        "packaging_gaps": gaps,
        "disposition": "hold" if holds else "release",
        "releasable": not holds,
        "holds": holds,
    }
