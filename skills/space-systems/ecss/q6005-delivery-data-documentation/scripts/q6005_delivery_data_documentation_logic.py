"""The record set that evidences the history of a delivered hybrid lot.

Anchor: ECSS-Q-ST-60-05 clause 13.2 (the documentation assembled and handed
over with the units, so that the manufacture and test history of everything in
the shipment can be read back from the records rather than from memory).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The delivery documentation is not a pile of paper, it is a chain. Materials
  and chips, assembly, in-process inspection, screening, lot acceptance and
  final test each leave a record group behind, and a chain with a phase nobody
  evidenced does not describe the units that were shipped.
* A record group that exists is not a record group that covers the shipment.
  Every delivered serial has to appear in the traceability index; a package
  that documents forty of forty-two units documents forty units.
* Legibility and completeness are graded, not assumed. A record group supplied
  as an unreadable or partial copy earns part credit, because a reviewer can
  see that it was produced without being able to use it.
* Nonconformances and rework are part of the history, not an embarrassment
  kept out of the package. A lot that raised nonconformances and delivers no
  nonconformance records has a hole exactly where the risk is.
* The documentation-coverage index is weighted credit over total weight. It
  ranks what is outstanding; a missing mandatory group, an unevidenced phase
  or an undocumented delivered serial decides the outcome on its own, at any
  index.
* The general format, retention and cover-sheet provisions of the package, the
  certificate of conformity, and the packing the shipment travels in are
  graded separately against their own clauses.
"""

from __future__ import annotations

import math

# The ordered phases the history of a delivered lot has to span.
HISTORY_PHASES = (
    "material-and-chip-procurement",
    "assembly",
    "in-process-inspection",
    "screening",
    "lot-acceptance",
    "final-electrical-test",
)

# Record groups the package carries, and the share of the history each one
# supplies.
RECORD_GROUP_WEIGHTS = {
    "incoming-material-and-part-records": 0.9,
    "chip-lot-acceptance-records": 1.0,
    "assembly-and-process-travellers": 1.0,
    "in-process-inspection-records": 0.9,
    "screening-test-data": 1.0,
    "lot-acceptance-test-data": 1.0,
    "final-electrical-test-data": 1.0,
    "serial-to-lot-traceability-index": 1.0,
    "nonconformance-and-waiver-records": 0.9,
    "rework-and-repair-records": 0.6,
}

# Which phase of the history each record group evidences.
RECORD_GROUP_PHASE = {
    "incoming-material-and-part-records": "material-and-chip-procurement",
    "chip-lot-acceptance-records": "material-and-chip-procurement",
    "assembly-and-process-travellers": "assembly",
    "in-process-inspection-records": "in-process-inspection",
    "screening-test-data": "screening",
    "lot-acceptance-test-data": "lot-acceptance",
    "final-electrical-test-data": "final-electrical-test",
    "serial-to-lot-traceability-index": "assembly",
    "nonconformance-and-waiver-records": "in-process-inspection",
    "rework-and-repair-records": "assembly",
}

# Without these the package does not describe the shipment at all.
MANDATORY_RECORD_GROUPS = (
    "chip-lot-acceptance-records",
    "assembly-and-process-travellers",
    "screening-test-data",
    "lot-acceptance-test-data",
    "final-electrical-test-data",
    "serial-to-lot-traceability-index",
)

# Credit a supplied record group earns for the state it arrives in.
RECORD_STATE_CREDIT = {
    "supplied": 1.0,
    "supplied-with-observation": 0.7,
    "supplied-partial": 0.5,
    "supplied-illegible": 0.2,
    "not-supplied": 0.0,
}

# Documentation-coverage index a complete package has to reach.
ACCEPTANCE_COVERAGE_INDEX = 0.90

# Indices are sums of products; a case meant to sit exactly on a bound can
# land a few units in the last place away from it.
DOCUMENTATION_TOLERANCE = 1e-9

VERDICTS = (
    "delivery-documentation-complete",
    "delivery-documentation-complete-with-open-actions",
    "delivery-documentation-deficient",
    "delivery-documentation-assessment-incomplete",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _flag(mapping, key):
    """Return a required boolean field of a mapping or raise."""
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (key, value))
    return value


def _serial_set(serials, label):
    """Validate a list of delivered or evidenced unit serials."""
    if not isinstance(serials, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (label, type(serials).__name__))
    cleaned = []
    for serial in serials:
        if not isinstance(serial, str) or not serial.strip():
            raise ValueError("every %s entry must be a non-empty string, got %r" % (label, serial))
        cleaned.append(serial.strip())
    if len(set(cleaned)) != len(cleaned):
        raise ValueError("%s contains a repeated serial" % label)
    return cleaned


def record_group_weight(name):
    """Weight of one record group; unknown names are rejected."""
    if name not in RECORD_GROUP_WEIGHTS:
        raise ValueError(
            "unknown record group %r (known: %s)"
            % (name, ", ".join(sorted(RECORD_GROUP_WEIGHTS)))
        )
    return RECORD_GROUP_WEIGHTS[name]


def record_state_credit(state):
    """Credit a record-group state earns."""
    if state not in RECORD_STATE_CREDIT:
        raise ValueError(
            "unknown record state %r (known: %s)"
            % (state, ", ".join(sorted(RECORD_STATE_CREDIT)))
        )
    return RECORD_STATE_CREDIT[state]


def normalize_record_group(raw):
    """Validate one record-group entry and fill its default state."""
    if not isinstance(raw, dict):
        raise ValueError("record group must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("group")
    record_group_weight(name)  # validation only
    state = raw.get("state", "not-supplied")
    record_state_credit(state)  # validation only
    return {"group": name, "state": state}


def assess_record_group(raw):
    """Grade one record group into a credit and its findings."""
    record = normalize_record_group(raw)
    name = record["group"]
    state = record["state"]
    weight = record_group_weight(name)
    credit = record_state_credit(state)
    findings = []
    if state == "supplied-with-observation":
        findings.append("record-group-observation-open")
    elif state == "supplied-partial":
        findings.append("record-group-supplied-partial")
    elif state == "supplied-illegible":
        findings.append("record-group-illegible")
    elif state == "not-supplied":
        findings.append("record-group-not-supplied")
    mandatory = name in MANDATORY_RECORD_GROUPS
    usable = state in ("supplied", "supplied-with-observation")
    return {
        "group": name,
        "state": state,
        "phase": RECORD_GROUP_PHASE[name],
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory": mandatory,
        "mandatory_missing": mandatory and state == "not-supplied",
        "mandatory_unusable": mandatory and state in ("supplied-partial", "supplied-illegible"),
        "evidences_phase": usable,
        "findings": findings,
    }


def documentation_coverage_index(records):
    """Weighted credit of a set of graded record groups over the total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (type(records).__name__,))
    if len(records) == 0:
        raise ValueError("a delivery data package must carry at least one record group")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total record-group weight must be positive")
    return earned / total_weight


def unevidenced_phases(records):
    """History phases no usable record group in the package speaks for."""
    covered = set()
    for record in records:
        if record["evidences_phase"]:
            covered.add(record["phase"])
    return [phase for phase in HISTORY_PHASES if phase not in covered]


def serial_evidence(delivered_serials, evidenced_serials):
    """How much of the shipment the traceability index actually reaches."""
    delivered = _serial_set(delivered_serials, "delivered_serials")
    if len(delivered) == 0:
        raise ValueError("a delivered lot must carry at least one unit serial")
    evidenced = set(_serial_set(evidenced_serials, "evidenced_serials"))
    undocumented = [serial for serial in delivered if serial not in evidenced]
    stray = sorted(serial for serial in evidenced if serial not in set(delivered))
    ratio = float(len(delivered) - len(undocumented)) / float(len(delivered))
    return {
        "delivered_count": len(delivered),
        "documented_count": len(delivered) - len(undocumented),
        "undocumented_serials": undocumented,
        "serials_documented_but_not_delivered": stray,
        "serial_evidence_ratio": ratio,
        "all_delivered_units_documented": len(undocumented) == 0,
    }


def nonconformance_findings(lot_history, records):
    """Findings raised by what the lot went through against what it hands over."""
    if not isinstance(lot_history, dict):
        raise ValueError("lot_history must be a mapping, got %r" % (type(lot_history).__name__,))
    states = {record["group"]: record["state"] for record in records}
    findings = []
    if _flag(lot_history, "nonconformances_raised") and states.get(
        "nonconformance-and-waiver-records", "not-supplied"
    ) == "not-supplied":
        findings.append("nonconformances-raised-but-no-nonconformance-records")
    if _flag(lot_history, "units_reworked") and states.get(
        "rework-and-repair-records", "not-supplied"
    ) == "not-supplied":
        findings.append("units-reworked-but-no-rework-records")
    if _flag(lot_history, "waivers_approved") and not _flag(lot_history, "waiver_references_listed"):
        findings.append("approved-waivers-not-referenced-in-the-package")
    return findings


def assess_delivery_documentation(
    lot_id, delivered_serials, evidenced_serials, record_groups, lot_history
):
    """Grade a whole delivery data package and name one verdict."""
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("lot_id must be a non-empty string, got %r" % (lot_id,))
    if not isinstance(record_groups, (list, tuple)):
        raise ValueError(
            "record_groups must be a list or tuple, got %r" % (type(record_groups).__name__,)
        )

    declared = {}
    for raw in record_groups:
        record = normalize_record_group(raw)
        if record["group"] in declared:
            raise ValueError("duplicate record group %r" % (record["group"],))
        declared[record["group"]] = record
    graded = []
    for name in sorted(RECORD_GROUP_WEIGHTS):
        graded.append(assess_record_group(declared.get(name, {"group": name})))

    index = documentation_coverage_index(graded)
    gaps = unevidenced_phases(graded)
    serials = serial_evidence(delivered_serials, evidenced_serials)
    history = nonconformance_findings(lot_history, graded)

    findings = []
    for record in graded:
        for finding in record["findings"]:
            findings.append(
                {"item": record["group"], "finding": finding, "detail": record["state"]}
            )
    for phase in gaps:
        findings.append(
            {"item": phase, "finding": "history-phase-not-evidenced", "detail": lot_id}
        )
    for serial in serials["undocumented_serials"]:
        findings.append(
            {"item": serial, "finding": "delivered-unit-absent-from-the-records", "detail": lot_id}
        )
    for serial in serials["serials_documented_but_not_delivered"]:
        findings.append(
            {"item": serial, "finding": "record-for-a-unit-not-in-the-shipment", "detail": lot_id}
        )
    for finding in history:
        findings.append({"item": "lot-history", "finding": finding, "detail": lot_id})

    incomplete = any(record["mandatory_missing"] for record in graded)
    deficient = (
        bool(gaps)
        or not serials["all_delivered_units_documented"]
        or bool(serials["serials_documented_but_not_delivered"])
        or bool(history)
        or any(record["mandatory_unusable"] for record in graded)
        or index < ACCEPTANCE_COVERAGE_INDEX - DOCUMENTATION_TOLERANCE
    )
    if incomplete:
        verdict = "delivery-documentation-assessment-incomplete"
    elif deficient:
        verdict = "delivery-documentation-deficient"
    elif findings:
        verdict = "delivery-documentation-complete-with-open-actions"
    else:
        verdict = "delivery-documentation-complete"
    return {
        "lot_id": lot_id,
        "record_groups": graded,
        "documentation_coverage_index": index,
        "unevidenced_phases": gaps,
        "serials": serials,
        "history_findings": history,
        "findings": findings,
        "verdict": verdict,
        "package_accepted": verdict
        in (
            "delivery-documentation-complete",
            "delivery-documentation-complete-with-open-actions",
        ),
    }
