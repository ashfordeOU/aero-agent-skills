"""Delivered conformance and production data for a highest-assurance lot.

Anchor: ECSS-Q-ST-60-13C clause 4.3.11 (the conformance certificates and the
production data the manufacturer delivers with a class 1 commercial EEE lot).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise the lot identity the package is offered against: the lot code and
   the date-code window the receiving activity purchased.
2. Validate every delivered record: its kind, the lot code it carries, its
   date code, the number of units it reaches, whether it is signed by the
   manufacturer, and whether it carries variables data or an attributes-only
   summary.
3. Map the delivered kinds onto the kinds a class 1 lot owes, keeping an
   absent record, a record waived on an approved deviation and a record that
   was delivered but does not cover the lot strictly apart.
4. Compute, per required kind, the fraction of the lot the delivered data
   actually reaches, and raise a coverage finding when it falls short of the
   coverage the procurement specification demands.
5. Rank the findings by severity and return one delivery verdict:
   accepted, accepted-with-actions, or rejected.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "REQUIRED_DELIVERABLES",
    "VARIABLES_DATA_KINDS",
    "SEVERITY_ORDER",
    "normalize_lot_code",
    "parse_date_code",
    "date_code_in_window",
    "validate_delivery_item",
    "coverage_fraction",
    "item_findings",
    "deliverable_states",
    "missing_deliverables",
    "delivery_verdict",
    "assess_data_delivery",
]

# A coverage ratio is a quotient of counts; an exact-coverage case can land a
# few ULP below unity. Absorb the representation error here rather than
# lowering the coverage the procurement specification asks for.
COVERAGE_TOLERANCE = 1e-9

# The record kinds a highest-assurance (class 1) lot owes on delivery.
REQUIRED_DELIVERABLES = (
    "conformance-certificate",
    "lot-electrical-test-data",
    "screening-test-data",
    "traceability-record",
    "process-change-statement",
)

# Kinds for which a summary of pass/fail counts is not enough: the receiving
# activity has to see the measured values to judge drift inside the lot.
VARIABLES_DATA_KINDS = ("lot-electrical-test-data", "screening-test-data")

# Record states a delivered package may present.
ITEM_STATES = ("delivered", "absent", "waived", "not-applicable")

DATA_TYPES = ("variables", "attributes")

SEVERITY_ORDER = ("critical", "major", "minor")


def _require_text(value, label):
    """Return a stripped non-empty string or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _require_count(value, label, allow_zero=True):
    """Return a validated non-negative integer count or raise."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    if value == 0 and not allow_zero:
        raise ValueError("%s must be positive, got 0" % label)
    return value


def normalize_lot_code(code):
    """Return the comparison form of a manufacturer lot code."""
    text = _require_text(code, "lot code")
    kept = [ch for ch in text.upper() if ch.isalnum()]
    if not kept:
        raise ValueError("lot code %r carries no alphanumeric characters" % (code,))
    return "".join(kept)


def parse_date_code(code):
    """Return (year_of_decade_pair, week) for a four-digit YYWW date code."""
    text = _require_text(code, "date code")
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) != 4:
        raise ValueError("date code %r must reduce to four digits YYWW" % (code,))
    year = int(digits[:2])
    week = int(digits[2:])
    if week < 1 or week > 53:
        raise ValueError("date code %r carries week %d, outside 01-53" % (code, week))
    return (year, week)


def _week_index(date_code):
    """Return a monotone week index so a window can be compared as a range."""
    year, week = parse_date_code(date_code)
    return year * 53 + week


def date_code_in_window(date_code, window):
    """Return True when a date code falls inside an inclusive YYWW window."""
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("date-code window must be a (first, last) pair")
    first = _week_index(window[0])
    last = _week_index(window[1])
    if first > last:
        raise ValueError("date-code window %r runs backwards" % (window,))
    index = _week_index(date_code)
    return first <= index <= last


def validate_delivery_item(item):
    """Return a normalised delivery record or raise on a malformed one."""
    if not isinstance(item, dict):
        raise ValueError("delivery item must be a mapping, got %r" % (item,))
    kind = _require_text(item.get("kind"), "item kind")
    state = item.get("state", "delivered")
    if state not in ITEM_STATES:
        raise ValueError("item state %r is not one of %r" % (state, ITEM_STATES))
    record = {
        "kind": kind,
        "state": state,
        "lot_code": None,
        "date_code": None,
        "units_covered": 0,
        "signed": False,
        "data_type": None,
        "waiver_reference": None,
    }
    if state == "waived":
        record["waiver_reference"] = _require_text(
            item.get("waiver_reference"), "waiver reference for a waived record"
        )
        return record
    if state != "delivered":
        return record
    record["lot_code"] = normalize_lot_code(item.get("lot_code"))
    record["date_code"] = _require_text(item.get("date_code"), "item date code")
    parse_date_code(record["date_code"])
    record["units_covered"] = _require_count(
        item.get("units_covered", 0), "units_covered"
    )
    signed = item.get("signed", False)
    if not isinstance(signed, bool):
        raise ValueError("signed must be a boolean, got %r" % (signed,))
    record["signed"] = signed
    data_type = item.get("data_type")
    if data_type is not None and data_type not in DATA_TYPES:
        raise ValueError("data_type %r is not one of %r" % (data_type, DATA_TYPES))
    record["data_type"] = data_type
    return record


def coverage_fraction(units_covered, lot_units):
    """Return the fraction of the lot a delivered record reaches."""
    covered = _require_count(units_covered, "units_covered")
    total = _require_count(lot_units, "lot_units", allow_zero=False)
    if covered > total:
        raise ValueError(
            "units_covered %d exceeds the lot size %d" % (covered, total)
        )
    return covered / total


def _finding(severity, kind, message):
    if severity not in SEVERITY_ORDER:
        raise ValueError("severity %r is not one of %r" % (severity, SEVERITY_ORDER))
    return {"severity": severity, "kind": kind, "message": message}


def item_findings(record, lot):
    """Return the findings one delivered record raises against the lot."""
    if not isinstance(record, dict) or "kind" not in record:
        raise ValueError("record must be a normalised delivery record")
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping")
    kind = record["kind"]
    findings = []
    if record["state"] != "delivered":
        return findings
    lot_code = normalize_lot_code(lot["lot_code"])
    if record["lot_code"] != lot_code:
        findings.append(
            _finding(
                "critical",
                kind,
                "%s carries lot code %s, not the delivered lot %s"
                % (kind, record["lot_code"], lot_code),
            )
        )
    window = lot.get("date_code_window")
    if window is not None and not date_code_in_window(record["date_code"], window):
        findings.append(
            _finding(
                "minor",
                kind,
                "%s carries date code %s, outside the purchased window %s-%s"
                % (kind, record["date_code"], window[0], window[1]),
            )
        )
    required_coverage = float(lot.get("required_coverage", 1.0))
    reached = coverage_fraction(record["units_covered"], lot["lot_units"])
    short = reached < required_coverage and not math.isclose(
        reached, required_coverage, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    if short:
        findings.append(
            _finding(
                "major",
                kind,
                "%s reaches %.4f of the lot, below the required %.4f"
                % (kind, reached, required_coverage),
            )
        )
    if kind == "conformance-certificate" and not record["signed"]:
        findings.append(
            _finding(
                "major",
                kind,
                "conformance certificate carries no manufacturer signature",
            )
        )
    if kind in VARIABLES_DATA_KINDS and record["data_type"] == "attributes":
        findings.append(
            _finding(
                "major",
                kind,
                "%s delivered as an attributes summary; measured values are owed"
                % kind,
            )
        )
    if kind in VARIABLES_DATA_KINDS and record["data_type"] is None:
        findings.append(
            _finding(
                "minor",
                kind,
                "%s does not declare whether it carries variables data" % kind,
            )
        )
    return findings


def deliverable_states(records, required=REQUIRED_DELIVERABLES):
    """Return the state each required kind is presented in."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of normalised records")
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required deliverables must be a non-empty sequence")
    seen = {}
    for record in records:
        if not isinstance(record, dict) or "kind" not in record:
            raise ValueError("each record must be a normalised delivery record")
        seen.setdefault(record["kind"], record["state"])
    return {kind: seen.get(kind, "absent") for kind in required}


def missing_deliverables(records, required=REQUIRED_DELIVERABLES):
    """Return the required kinds that arrived with no record at all."""
    states = deliverable_states(records, required)
    return [kind for kind in required if states[kind] == "absent"]


def delivery_verdict(findings):
    """Return the package verdict implied by the ranked findings."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    severities = set()
    for finding in findings:
        if not isinstance(finding, dict) or "severity" not in finding:
            raise ValueError("each finding must carry a severity")
        severities.add(finding["severity"])
    if "critical" in severities:
        return "rejected"
    if "major" in severities or "minor" in severities:
        return "accepted-with-actions"
    return "accepted"


def assess_data_delivery(package):
    """Grade a delivered class 1 data package against clause 4.3.11.

    package keys: lot (mapping with lot_code, lot_units, optional
    date_code_window and required_coverage) and items (sequence of delivery
    records). Returns the normalised records, the per-kind states, the ranked
    findings and the delivery verdict.
    """
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping")
    for key in ("lot", "items"):
        if key not in package:
            raise ValueError("package missing required key '%s'" % key)
    lot = package["lot"]
    if not isinstance(lot, dict):
        raise ValueError("package['lot'] must be a mapping")
    for key in ("lot_code", "lot_units"):
        if key not in lot:
            raise ValueError("lot missing required key '%s'" % key)
    _require_count(lot["lot_units"], "lot_units", allow_zero=False)
    normalize_lot_code(lot["lot_code"])
    required_coverage = float(lot.get("required_coverage", 1.0))
    if not math.isfinite(required_coverage) or not 0.0 < required_coverage <= 1.0:
        raise ValueError(
            "required_coverage must sit in (0, 1], got %r" % (lot.get("required_coverage"),)
        )
    items = package["items"]
    if not isinstance(items, (list, tuple)):
        raise ValueError("package['items'] must be a sequence")
    required = tuple(package.get("required_deliverables", REQUIRED_DELIVERABLES))
    records = [validate_delivery_item(item) for item in items]
    findings = []
    for record in records:
        findings.extend(item_findings(record, lot))
    states = deliverable_states(records, required)
    for kind in required:
        state = states[kind]
        if state == "absent":
            findings.append(
                _finding("critical", kind, "%s was not delivered with the lot" % kind)
            )
        elif state == "waived":
            findings.append(
                _finding(
                    "minor",
                    kind,
                    "%s stands on an approved deviation, not on delivered data" % kind,
                )
            )
        elif state == "not-applicable":
            findings.append(
                _finding(
                    "major",
                    kind,
                    "%s marked not-applicable; a class 1 lot owes it" % kind,
                )
            )
    findings.sort(key=lambda f: (SEVERITY_ORDER.index(f["severity"]), f["kind"]))
    verdict = delivery_verdict(findings)
    return {
        "records": records,
        "deliverable_states": states,
        "missing": missing_deliverables(records, required),
        "findings": findings,
        "verdict": verdict,
        "accepted": verdict == "accepted",
    }
