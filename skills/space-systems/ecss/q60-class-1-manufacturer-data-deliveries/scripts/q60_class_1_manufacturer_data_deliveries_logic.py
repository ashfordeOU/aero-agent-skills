"""Manufacturer data deliveries accompanying a class 1 EEE shipment.

Anchor: ECSS-Q-ST-60C clause 4.3.11 (certificates of conformity and the
supporting manufacturer records delivered with class 1 shipments).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Derive the record set a shipment owes: the core certificates every class 1
   delivery carries, plus the conditional records the lot's radiation duty,
   delta-qualification status, approved deviations and rework history add.
2. Test each delivered record against the shipment it travels with: issuing
   authority signature, lot-code agreement, an issue date at or before
   dispatch, and coverage of the delivered quantity.
3. Walk the traceability chain the records claim and name the links that are
   not evidenced.
4. Return the completeness fraction of the owed record set.
5. Rank the findings and close with one delivery disposition: accepted,
   accepted-with-actions, or hold-shipment.
"""

import datetime
import math

__all__ = [
    "BOUND_TOLERANCE",
    "CORE_RECORDS",
    "CONDITIONAL_RECORDS",
    "TRACEABILITY_CHAIN",
    "DEFECT_SEVERITY",
    "SEVERITY_ORDER",
    "required_records",
    "record_defects",
    "traceability_gaps",
    "package_completeness",
    "defect_severity",
    "delivery_verdict",
    "assess_manufacturer_data_delivery",
]

# Completeness is a quotient of small counts and the quantity comparison is a
# difference of measured values; a case sitting exactly on a bound can land a
# few ULP on the wrong side. Absorb the representation error here, never by
# moving the bound itself.
BOUND_TOLERANCE = 1e-9

# Records every class 1 shipment carries, whatever the lot history.
CORE_RECORDS = (
    "certificate-of-conformity",
    "lot-traceability-record",
    "screening-test-data",
    "lot-acceptance-test-report",
)

# Records a shipment owes only when the matching condition holds on the lot.
CONDITIONAL_RECORDS = {
    "radiation_duty": "radiation-lot-verification-data",
    "delta_qualified": "delta-qualification-report",
    "approved_deviation": "deviation-approval-record",
    "rework_performed": "rework-and-repair-record",
}

# The identity chain a class 1 record set is expected to evidence, coarsest
# first. A break anywhere in the chain breaks the parts' traceability.
TRACEABILITY_CHAIN = (
    "wafer-lot",
    "assembly-lot",
    "date-code",
    "shipment-lot",
)

# How a defect on a delivered record is weighted. A record that cannot be tied
# to the parts in the box, or that nobody with authority stood behind, is a
# different problem from one that arrived a day late.
DEFECT_SEVERITY = {
    "missing-record": "critical",
    "lot-code-mismatch": "critical",
    "unsigned-by-issuing-authority": "critical",
    "traceability-link-not-evidenced": "critical",
    "issued-after-dispatch": "major",
    "quantity-not-covered": "major",
    "superseded-issue-delivered": "minor",
}

SEVERITY_ORDER = ("critical", "major", "minor")


def _require_number(value, label, allow_negative=False):
    """Return a validated finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if not allow_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _require_text(value, label):
    """Return a stripped non-empty string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_flag(value, label):
    """Return a validated boolean or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (label, value))
    return value


def _require_date(value, label):
    """Return a date parsed from an ISO yyyy-mm-dd string or a date object."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            raise ValueError("%s %r is not an ISO yyyy-mm-dd date" % (label, value))
    raise ValueError("%s must be an ISO date string or a date, got %r" % (label, value))


def required_records(context):
    """Return the sorted record set a class 1 shipment owes.

    context carries one boolean per conditional record trigger. An absent key
    reads as false; an unknown key is an input error rather than a silent
    no-op, because a misspelled trigger would quietly drop a required record.
    """
    if not isinstance(context, dict):
        raise ValueError("context must be a mapping, got %r" % (context,))
    owed = set(CORE_RECORDS)
    for key, value in context.items():
        if key not in CONDITIONAL_RECORDS:
            raise ValueError(
                "unknown condition %r; expected one of %r"
                % (key, sorted(CONDITIONAL_RECORDS))
            )
        if _require_flag(value, "condition '%s'" % key):
            owed.add(CONDITIONAL_RECORDS[key])
    return sorted(owed)


def record_defects(entry, shipment):
    """Return the sorted defect codes carried by one delivered record.

    entry keys: type, signed, lot_code, issue_date, quantity_covered and the
    optional superseded flag. shipment keys: lot_code, dispatch_date,
    quantity.
    """
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping, got %r" % (entry,))
    if not isinstance(shipment, dict):
        raise ValueError("shipment must be a mapping, got %r" % (shipment,))
    for key in ("type", "signed", "lot_code", "issue_date", "quantity_covered"):
        if key not in entry:
            raise ValueError("record entry missing required key '%s'" % key)
    for key in ("lot_code", "dispatch_date", "quantity"):
        if key not in shipment:
            raise ValueError("shipment missing required key '%s'" % key)

    _require_text(entry["type"], "record type")
    entry_lot = _require_text(entry["lot_code"], "record lot_code")
    shipment_lot = _require_text(shipment["lot_code"], "shipment lot_code")
    issued = _require_date(entry["issue_date"], "record issue_date")
    dispatched = _require_date(shipment["dispatch_date"], "shipment dispatch_date")
    covered = _require_number(entry["quantity_covered"], "record quantity_covered")
    shipped = _require_number(shipment["quantity"], "shipment quantity")
    if shipped <= 0.0:
        raise ValueError("shipment quantity must be positive, got %g" % shipped)

    defects = []
    if not _require_flag(entry["signed"], "record signed"):
        defects.append("unsigned-by-issuing-authority")
    if entry_lot.casefold() != shipment_lot.casefold():
        defects.append("lot-code-mismatch")
    if issued > dispatched:
        defects.append("issued-after-dispatch")
    if covered < shipped and not math.isclose(
        covered, shipped, rel_tol=0.0, abs_tol=BOUND_TOLERANCE
    ):
        defects.append("quantity-not-covered")
    if _require_flag(entry.get("superseded", False), "record superseded"):
        defects.append("superseded-issue-delivered")
    return sorted(defects)


def traceability_gaps(links_evidenced):
    """Return the chain links a record set does not evidence, coarsest first."""
    if not isinstance(links_evidenced, (list, tuple, set, frozenset)):
        raise ValueError("links_evidenced must be a sequence or set")
    evidenced = set()
    for link in links_evidenced:
        name = _require_text(link, "traceability link").casefold()
        if name not in TRACEABILITY_CHAIN:
            raise ValueError(
                "unknown traceability link %r; expected one of %r"
                % (link, list(TRACEABILITY_CHAIN))
            )
        evidenced.add(name)
    return [link for link in TRACEABILITY_CHAIN if link not in evidenced]


def package_completeness(owed, delivered_types):
    """Return the fraction of the owed record set that actually arrived."""
    if not isinstance(owed, (list, tuple)) or not owed:
        raise ValueError("owed must be a non-empty sequence of record types")
    if not isinstance(delivered_types, (list, tuple, set, frozenset)):
        raise ValueError("delivered_types must be a sequence or set")
    wanted = [_require_text(name, "owed record type").casefold() for name in owed]
    have = {_require_text(name, "delivered record type").casefold()
            for name in delivered_types}
    present = sum(1 for name in wanted if name in have)
    return present / float(len(wanted))


def defect_severity(code):
    """Return the severity weighting of a defect code."""
    name = _require_text(code, "defect code")
    if name not in DEFECT_SEVERITY:
        raise ValueError(
            "unknown defect code %r; expected one of %r"
            % (code, sorted(DEFECT_SEVERITY))
        )
    return DEFECT_SEVERITY[name]


def delivery_verdict(findings):
    """Return the delivery disposition implied by the ranked findings."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    severities = set()
    for finding in findings:
        if not isinstance(finding, dict) or "severity" not in finding:
            raise ValueError("each finding must carry a severity")
        severity = finding["severity"]
        if severity not in SEVERITY_ORDER:
            raise ValueError("severity %r is not one of %r" % (severity, SEVERITY_ORDER))
        severities.add(severity)
    if "critical" in severities:
        return "hold-shipment"
    if severities:
        return "accepted-with-actions"
    return "accepted"


def _finding(severity, topic, message):
    return {"severity": severity, "topic": topic, "message": message}


def assess_manufacturer_data_delivery(delivery):
    """Grade one class 1 data delivery against clause 4.3.11.

    delivery keys: shipment (lot_code, dispatch_date, quantity), records (a
    sequence of record entries), optional context (conditional record
    triggers) and optional traceability_links.
    """
    if not isinstance(delivery, dict):
        raise ValueError("delivery must be a mapping")
    for key in ("shipment", "records"):
        if key not in delivery:
            raise ValueError("delivery missing required key '%s'" % key)
    shipment = delivery["shipment"]
    records = delivery["records"]
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of record entries")

    owed = required_records(delivery.get("context", {}))
    delivered_types = [_require_text(entry.get("type", ""), "record type")
                       for entry in records]
    if len(set(name.casefold() for name in delivered_types)) != len(delivered_types):
        raise ValueError("the same record type was delivered twice")
    completeness = package_completeness(owed, delivered_types)
    delivered_set = {name.casefold() for name in delivered_types}
    missing = [name for name in owed if name.casefold() not in delivered_set]
    gaps = traceability_gaps(delivery.get("traceability_links", TRACEABILITY_CHAIN))

    findings = []
    for name in missing:
        findings.append(
            _finding(
                defect_severity("missing-record"),
                "record-set",
                "the shipment owes %s and it did not arrive" % name,
            )
        )
    defects_by_record = {}
    for entry in records:
        codes = record_defects(entry, shipment)
        name = _require_text(entry["type"], "record type")
        defects_by_record[name] = codes
        for code in codes:
            findings.append(
                _finding(
                    defect_severity(code),
                    "record-quality",
                    "%s carries the defect %s" % (name, code),
                )
            )
    for link in gaps:
        findings.append(
            _finding(
                defect_severity("traceability-link-not-evidenced"),
                "traceability",
                "the %s link of the identity chain is not evidenced" % link,
            )
        )

    findings.sort(key=lambda f: (SEVERITY_ORDER.index(f["severity"]), f["topic"]))
    verdict = delivery_verdict(findings)
    return {
        "required_records": owed,
        "delivered_records": sorted(delivered_types),
        "missing_records": missing,
        "completeness_fraction": completeness,
        "defects_by_record": defects_by_record,
        "traceability_gaps": gaps,
        "findings": findings,
        "verdict": verdict,
        "accepted": verdict == "accepted",
    }
