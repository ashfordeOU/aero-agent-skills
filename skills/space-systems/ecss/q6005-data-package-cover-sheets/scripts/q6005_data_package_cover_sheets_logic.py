"""The front sheets that say what a hybrid delivery data package contains.

Anchor: ECSS-Q-ST-60-05 clause 13.2.2 (the summary pages at the front of the
data package: which batch the package belongs to, which build standard the
units were made to, and an index of everything enclosed behind them).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* A cover sheet is a claim about a package, and a claim can be checked. The
  serial range it prints, the quantity it declares and the enclosures it lists
  are each measurable against the shipment and the binder behind it.
* The serial range is not decoration. Every delivered unit has to fall inside
  the printed range, and a range that spans numbers no delivered unit carries
  is a range somebody widened rather than counted.
* The enclosure index is reconciled both ways. A record listed and absent is
  the failure everyone looks for; a record present and unlisted is the one
  that shows the index was written from a different package.
* Quantity is a third statement of the same fact. The declared quantity, the
  number of serials handed over and the span of the printed range have to
  agree, and any two of them agreeing proves nothing about the third.
* The build standard is what makes the package mean anything. Without the
  drawing or specification issue the units were made to, the enclosed test
  data belongs to no configuration.
* The cover-sheet completeness index is weighted credit over total weight. It
  ranks what is outstanding; an unlisted enclosure, a unit outside the range
  or a quantity that does not reconcile decides the outcome on its own, at
  any index.
"""

from __future__ import annotations

import math

# Fields a cover sheet carries, and the share of the summary each supplies.
COVER_SHEET_FIELDS = {
    "batch-or-lot-identifier": 1.0,
    "part-number": 1.0,
    "build-standard-reference": 1.0,
    "quantity-delivered": 1.0,
    "serial-range": 1.0,
    "enclosure-index": 1.0,
    "purchase-order-reference": 0.9,
    "manufacturer-identity": 0.8,
    "issue-date": 0.7,
    "approval-signature": 0.9,
    "page-count-of-the-package": 0.5,
}

# Without these the front sheet identifies nothing.
MANDATORY_COVER_SHEET_FIELDS = (
    "batch-or-lot-identifier",
    "part-number",
    "build-standard-reference",
    "quantity-delivered",
    "serial-range",
    "enclosure-index",
)

FIELD_STATE_CREDIT = {
    "present": 1.0,
    "present-with-observation": 0.7,
    "illegible": 0.2,
    "absent": 0.0,
}

# Cover-sheet completeness index an acceptable front sheet has to reach.
ACCEPTANCE_COVER_SHEET_INDEX = 0.90

# Indices are sums of products; a case meant to sit exactly on a bound can
# land a few units in the last place away from it.
COVER_SHEET_TOLERANCE = 1e-9

VERDICTS = (
    "cover-sheet-acceptable",
    "cover-sheet-acceptable-with-open-actions",
    "cover-sheet-rejected",
    "cover-sheet-assessment-incomplete",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _count(value, label):
    """Return ``value`` as a non-negative whole count or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def _serial_numbers(serials):
    """Validate the delivered unit serial numbers as whole numbers."""
    if not isinstance(serials, (list, tuple)):
        raise ValueError(
            "delivered serials must be a list or tuple, got %r" % (type(serials).__name__,)
        )
    if len(serials) == 0:
        raise ValueError("a shipment must carry at least one unit serial")
    cleaned = []
    for serial in serials:
        cleaned.append(_count(serial, "unit serial"))
    if len(set(cleaned)) != len(cleaned):
        raise ValueError("delivered serials contain a repeated number")
    return sorted(cleaned)


def _names(values, label):
    """Validate a list of enclosure names."""
    if not isinstance(values, (list, tuple)):
        raise ValueError("%s must be a list or tuple, got %r" % (label, type(values).__name__))
    cleaned = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("every %s entry must be a non-empty string, got %r" % (label, value))
        cleaned.append(value.strip())
    if len(set(cleaned)) != len(cleaned):
        raise ValueError("%s contains a repeated entry" % label)
    return cleaned


def serial_range_coverage(first_serial, last_serial, delivered_serials):
    """Check the printed serial range against the units actually shipped."""
    first = _count(first_serial, "first_serial")
    last = _count(last_serial, "last_serial")
    if last < first:
        raise ValueError("the serial range ends before it begins")
    delivered = _serial_numbers(delivered_serials)
    outside = [serial for serial in delivered if serial < first or serial > last]
    span = last - first + 1
    unused = span - len([s for s in delivered if first <= s <= last])
    findings = []
    if outside:
        findings.append("delivered-unit-outside-the-printed-serial-range")
    if unused > 0:
        findings.append("serial-range-wider-than-the-units-delivered")
    return {
        "first_serial": first,
        "last_serial": last,
        "range_span": span,
        "delivered_count": len(delivered),
        "serials_outside_range": outside,
        "unused_numbers_in_range": unused,
        "range_matches_shipment": len(findings) == 0,
        "findings": findings,
    }


def reconcile_enclosures(listed, enclosed):
    """Reconcile the index on the cover sheet with what is behind it."""
    index = _names(listed, "listed enclosures")
    actual = _names(enclosed, "enclosed records")
    if len(index) == 0:
        raise ValueError("a cover sheet must index at least one enclosure")
    missing = [name for name in index if name not in set(actual)]
    unlisted = [name for name in actual if name not in set(index)]
    findings = []
    if missing:
        findings.append("enclosure-listed-but-not-in-the-package")
    if unlisted:
        findings.append("record-in-the-package-but-not-on-the-index")
    matched = len(index) - len(missing)
    return {
        "listed_count": len(index),
        "enclosed_count": len(actual),
        "matched_count": matched,
        "listed_but_absent": missing,
        "present_but_unlisted": unlisted,
        "index_agreement_ratio": float(matched) / float(len(index)),
        "index_reconciled": len(findings) == 0,
        "findings": findings,
    }


def quantity_reconciliation(declared_quantity, delivered_serials, coverage):
    """Check the declared quantity against the serials and the printed range."""
    declared = _count(declared_quantity, "declared_quantity")
    if declared == 0:
        raise ValueError("a cover sheet must declare a delivered quantity")
    delivered = _serial_numbers(delivered_serials)
    if not isinstance(coverage, dict):
        raise ValueError("coverage must be a mapping, got %r" % (type(coverage).__name__,))
    span = _count(coverage.get("range_span"), "range_span")
    findings = []
    if declared != len(delivered):
        findings.append("declared-quantity-differs-from-the-serials-handed-over")
    if declared != span:
        findings.append("declared-quantity-differs-from-the-printed-range-span")
    return {
        "declared_quantity": declared,
        "serial_count": len(delivered),
        "range_span": span,
        "reconciled": len(findings) == 0,
        "findings": findings,
    }


def build_standard_findings(build_standard):
    """Findings raised by the configuration the cover sheet points at."""
    if not isinstance(build_standard, dict):
        raise ValueError(
            "build_standard must be a mapping, got %r" % (type(build_standard).__name__,)
        )
    findings = []
    for key, finding in (
        ("drawing_reference", "build-standard-without-a-drawing-reference"),
        ("drawing_issue", "build-standard-without-a-drawing-issue"),
        ("specification_reference", "build-standard-without-a-specification-reference"),
    ):
        value = build_standard.get(key)
        if not isinstance(value, str) or not value.strip():
            findings.append(finding)
    return findings


def cover_sheet_field_weight(name):
    """Weight of one cover-sheet field; unknown names are rejected."""
    if name not in COVER_SHEET_FIELDS:
        raise ValueError(
            "unknown cover-sheet field %r (known: %s)"
            % (name, ", ".join(sorted(COVER_SHEET_FIELDS)))
        )
    return COVER_SHEET_FIELDS[name]


def field_state_credit(state):
    """Credit a cover-sheet field state earns."""
    if state not in FIELD_STATE_CREDIT:
        raise ValueError(
            "unknown field state %r (known: %s)" % (state, ", ".join(sorted(FIELD_STATE_CREDIT)))
        )
    return FIELD_STATE_CREDIT[state]


def normalize_field(raw):
    """Validate one cover-sheet field record and fill its default state."""
    if not isinstance(raw, dict):
        raise ValueError("field must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("field")
    cover_sheet_field_weight(name)  # validation only
    state = raw.get("state", "absent")
    field_state_credit(state)  # validation only
    return {"field": name, "state": state}


def assess_field(raw):
    """Grade one cover-sheet field into a credit and its findings."""
    record = normalize_field(raw)
    name = record["field"]
    state = record["state"]
    weight = cover_sheet_field_weight(name)
    credit = field_state_credit(state)
    findings = []
    if state == "present-with-observation":
        findings.append("cover-sheet-field-observation-open")
    elif state == "illegible":
        findings.append("cover-sheet-field-illegible")
    elif state == "absent":
        findings.append("cover-sheet-field-absent")
    mandatory = name in MANDATORY_COVER_SHEET_FIELDS
    return {
        "field": name,
        "state": state,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory": mandatory,
        "mandatory_missing": mandatory and state == "absent",
        "mandatory_illegible": mandatory and state == "illegible",
        "findings": findings,
    }


def cover_sheet_completeness_index(records):
    """Weighted credit of a set of graded fields over the total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (type(records).__name__,))
    if len(records) == 0:
        raise ValueError("a cover sheet must carry at least one field")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total cover-sheet field weight must be positive")
    return earned / total_weight


def assess_cover_sheet(batch_id, sheet, delivered_serials, enclosed_records, fields):
    """Grade a whole data-package cover sheet and name one verdict."""
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("batch_id must be a non-empty string, got %r" % (batch_id,))
    if not isinstance(sheet, dict):
        raise ValueError("sheet must be a mapping, got %r" % (type(sheet).__name__,))
    if not isinstance(fields, (list, tuple)):
        raise ValueError("fields must be a list or tuple, got %r" % (type(fields).__name__,))

    coverage = serial_range_coverage(
        sheet.get("first_serial"), sheet.get("last_serial"), delivered_serials
    )
    enclosures = reconcile_enclosures(sheet.get("listed_enclosures"), enclosed_records)
    quantity = quantity_reconciliation(
        sheet.get("declared_quantity"), delivered_serials, coverage
    )
    build = build_standard_findings(sheet.get("build_standard"))

    declared = {}
    for raw in fields:
        record = normalize_field(raw)
        if record["field"] in declared:
            raise ValueError("duplicate cover-sheet field %r" % (record["field"],))
        declared[record["field"]] = record
    graded = []
    for name in sorted(COVER_SHEET_FIELDS):
        graded.append(assess_field(declared.get(name, {"field": name})))
    index = cover_sheet_completeness_index(graded)

    findings = []
    for finding in coverage["findings"]:
        findings.append({"item": "serial-range", "finding": finding, "detail": batch_id})
    for finding in enclosures["findings"]:
        findings.append({"item": "enclosure-index", "finding": finding, "detail": batch_id})
    for finding in quantity["findings"]:
        findings.append({"item": "quantity-delivered", "finding": finding, "detail": batch_id})
    for finding in build:
        findings.append({"item": "build-standard", "finding": finding, "detail": batch_id})
    for record in graded:
        for finding in record["findings"]:
            findings.append(
                {"item": record["field"], "finding": finding, "detail": record["state"]}
            )

    incomplete = any(record["mandatory_missing"] for record in graded)
    rejected = (
        not coverage["range_matches_shipment"]
        or not enclosures["index_reconciled"]
        or not quantity["reconciled"]
        or bool(build)
        or any(record["mandatory_illegible"] for record in graded)
        or index < ACCEPTANCE_COVER_SHEET_INDEX - COVER_SHEET_TOLERANCE
    )
    if incomplete:
        verdict = "cover-sheet-assessment-incomplete"
    elif rejected:
        verdict = "cover-sheet-rejected"
    elif findings:
        verdict = "cover-sheet-acceptable-with-open-actions"
    else:
        verdict = "cover-sheet-acceptable"
    return {
        "batch_id": batch_id,
        "serial_range": coverage,
        "enclosures": enclosures,
        "quantity": quantity,
        "build_standard_findings": build,
        "fields": graded,
        "cover_sheet_completeness_index": index,
        "findings": findings,
        "verdict": verdict,
        "cover_sheet_accepted": verdict
        in ("cover-sheet-acceptable", "cover-sheet-acceptable-with-open-actions"),
    }
