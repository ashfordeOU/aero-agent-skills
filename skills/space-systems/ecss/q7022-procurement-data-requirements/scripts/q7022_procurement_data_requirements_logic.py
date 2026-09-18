"""Procurement data requirements for a limited-shelf-life material lot.

Anchor: ECSS-Q-ST-70-22C, procurement clause -- the data a purchaser has to
demand from a supplier so that the shelf life of a delivered lot is known and
auditable, and the storage evidence that has to travel with it. Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Check the delivered data package against the mandatory item set: the lot
   cannot be entered into stores at all if an item that fixes an expiry date
   is absent.
2. Parse and cross-check the date chain: manufacture, receipt and expiry have
   to be orderable, and a declared shelf-life duration has to agree with the
   interval the two dates actually span.
3. Convert the chain into remaining shelf life at receipt, expressed both in
   days and as a fraction of the full shelf life, which is the figure a
   purchase order writes its acceptance threshold against.
4. Grade the storage evidence: the temperature and humidity envelope the lot
   is recorded as having experienced in transit and at the supplier has to sit
   inside the envelope the material specification allows.
5. Close with one disposition -- accept, accept-with-actions, or reject -- and
   the findings that produced it.
"""

import datetime
import math

__all__ = [
    "MANDATORY_DATA_ITEMS",
    "TARGET_REMAINING_FRACTION",
    "FLOOR_REMAINING_FRACTION",
    "FRACTION_TOLERANCE",
    "parse_date",
    "missing_data_items",
    "validate_date_chain",
    "shelf_life_days",
    "remaining_days_at_receipt",
    "remaining_fraction",
    "declared_duration_findings",
    "storage_evidence_findings",
    "grade_remaining_life",
    "assess_procurement_package",
]

# The items without which an expiry date cannot be established or audited.
MANDATORY_DATA_ITEMS = (
    "manufacturer",
    "batch_identifier",
    "manufacture_date",
    "expiry_date",
    "conformity_certificate",
)

# A lot delivered with less than this fraction of its shelf life left is not
# refused outright, but it cannot be taken into stores without a named action.
TARGET_REMAINING_FRACTION = 0.75

# Below this fraction the lot is refused at goods-in: the usable window left
# is too short to plan work against.
FLOOR_REMAINING_FRACTION = 0.50

# Fractions here are ratios of whole-day counts, so an exact boundary is a
# representation question, not an engineering one. Absorb it with a tolerance
# instead of moving the acceptance threshold.
FRACTION_TOLERANCE = 1e-9

_DISPOSITIONS = ("accept", "accept-with-actions", "reject")


def _require_mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    return value


def parse_date(value, label="date"):
    """Return an ISO date string or date object as a datetime.date."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO yyyy-mm-dd string or a date, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    try:
        parts = text.split("-")
        if len(parts) != 3:
            raise ValueError("three components expected")
        year, month, day = (int(p) for p in parts)
        return datetime.date(year, month, day)
    except Exception:
        raise ValueError("%s must be an ISO yyyy-mm-dd date, got %r" % (label, value))


def missing_data_items(package):
    """Return the mandatory procurement data items the package does not carry."""
    _require_mapping(package, "package")
    missing = []
    for item in MANDATORY_DATA_ITEMS:
        value = package.get(item)
        if value is None:
            missing.append(item)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(item)
        elif value is False:
            missing.append(item)
    return missing


def validate_date_chain(manufacture_date, receipt_date, expiry_date):
    """Return the parsed (manufacture, receipt, expiry) triple plus its findings."""
    manufacture = parse_date(manufacture_date, "manufacture_date")
    receipt = parse_date(receipt_date, "receipt_date")
    expiry = parse_date(expiry_date, "expiry_date")
    findings = []
    if expiry <= manufacture:
        findings.append(
            "expiry date %s does not follow the manufacture date %s; the declared "
            "shelf life is not a usable interval" % (expiry.isoformat(), manufacture.isoformat())
        )
    if receipt < manufacture:
        findings.append(
            "receipt date %s precedes the manufacture date %s; the date chain is "
            "not self-consistent" % (receipt.isoformat(), manufacture.isoformat())
        )
    if receipt > expiry:
        findings.append(
            "lot was already past its expiry date %s when received on %s"
            % (expiry.isoformat(), receipt.isoformat())
        )
    return (manufacture, receipt, expiry), findings


def shelf_life_days(manufacture_date, expiry_date):
    """Return the full declared shelf life of the lot in whole days."""
    manufacture = parse_date(manufacture_date, "manufacture_date")
    expiry = parse_date(expiry_date, "expiry_date")
    span = (expiry - manufacture).days
    if span <= 0:
        raise ValueError(
            "shelf life must be a positive number of days; expiry %s is not after "
            "manufacture %s" % (expiry.isoformat(), manufacture.isoformat())
        )
    return span


def remaining_days_at_receipt(receipt_date, expiry_date):
    """Return the days of shelf life left when the lot arrived (negative if past)."""
    receipt = parse_date(receipt_date, "receipt_date")
    expiry = parse_date(expiry_date, "expiry_date")
    return (expiry - receipt).days


def remaining_fraction(manufacture_date, receipt_date, expiry_date):
    """Return remaining shelf life at receipt as a fraction of the full shelf life."""
    total = shelf_life_days(manufacture_date, expiry_date)
    left = remaining_days_at_receipt(receipt_date, expiry_date)
    return float(left) / float(total)


def declared_duration_findings(package):
    """Compare a declared shelf-life duration with the interval the dates span."""
    _require_mapping(package, "package")
    declared = package.get("declared_shelf_life_days")
    if declared is None:
        return []
    if not isinstance(declared, (int, float)) or isinstance(declared, bool):
        raise ValueError("declared_shelf_life_days must be a real number, got %r" % (declared,))
    declared = float(declared)
    if not math.isfinite(declared) or declared <= 0.0:
        raise ValueError("declared_shelf_life_days must be positive and finite")
    actual = float(shelf_life_days(package["manufacture_date"], package["expiry_date"]))
    if math.isclose(declared, actual, rel_tol=0.0, abs_tol=1.0):
        return []
    return [
        "declared shelf life of %g days disagrees with the %g days the manufacture "
        "and expiry dates span" % (declared, actual)
    ]


def _envelope(value, label):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("%s must be a (low, high) pair" % label)
    low, high = value
    for name, item in ((label + " low", low), (label + " high", high)):
        if not isinstance(item, (int, float)) or isinstance(item, bool):
            raise ValueError("%s must be a real number" % name)
        if not math.isfinite(float(item)):
            raise ValueError("%s must be finite" % name)
    low = float(low)
    high = float(high)
    if low > high:
        raise ValueError("%s low %g exceeds high %g" % (label, low, high))
    return (low, high)


def storage_evidence_findings(package):
    """Grade the recorded storage envelope against the specified allowable one."""
    _require_mapping(package, "package")
    findings = []
    pairs = (
        ("temperature", "recorded_storage_temperature_c", "specified_storage_temperature_c", "degC"),
        ("humidity", "recorded_storage_humidity_pct", "specified_storage_humidity_pct", "%RH"),
    )
    any_recorded = False
    for quantity, recorded_key, specified_key, unit in pairs:
        recorded = package.get(recorded_key)
        specified = package.get(specified_key)
        if recorded is None:
            continue
        any_recorded = True
        if specified is None:
            findings.append(
                "%s evidence supplied with no specified %s limit to grade it against"
                % (quantity, quantity)
            )
            continue
        r_low, r_high = _envelope(recorded, recorded_key)
        s_low, s_high = _envelope(specified, specified_key)
        if r_low < s_low - FRACTION_TOLERANCE:
            findings.append(
                "recorded %s fell to %g %s, below the specified %g %s"
                % (quantity, r_low, unit, s_low, unit)
            )
        if r_high > s_high + FRACTION_TOLERANCE:
            findings.append(
                "recorded %s reached %g %s, above the specified %g %s"
                % (quantity, r_high, unit, s_high, unit)
            )
    if not any_recorded:
        findings.append(
            "no storage evidence delivered; the conditions the lot saw before "
            "receipt are unknown and cannot be assumed nominal"
        )
    return findings


def grade_remaining_life(fraction):
    """Categorize remaining shelf life at receipt against the two thresholds."""
    if not isinstance(fraction, (int, float)) or isinstance(fraction, bool):
        raise ValueError("fraction must be a real number")
    value = float(fraction)
    if not math.isfinite(value):
        raise ValueError("fraction must be finite")
    if value > TARGET_REMAINING_FRACTION or math.isclose(
        value, TARGET_REMAINING_FRACTION, rel_tol=0.0, abs_tol=FRACTION_TOLERANCE
    ):
        return "adequate"
    if value > FLOOR_REMAINING_FRACTION or math.isclose(
        value, FLOOR_REMAINING_FRACTION, rel_tol=0.0, abs_tol=FRACTION_TOLERANCE
    ):
        return "short"
    return "insufficient"


def assess_procurement_package(package):
    """Assess one delivered shelf-life data package and return its disposition.

    package keys: manufacturer, batch_identifier, manufacture_date, expiry_date,
    conformity_certificate, receipt_date, optional declared_shelf_life_days,
    optional recorded/specified storage temperature and humidity envelopes.
    """
    _require_mapping(package, "package")
    findings = []
    missing = missing_data_items(package)
    if missing:
        findings.append("mandatory procurement data items absent: %s" % ", ".join(missing))
        return {
            "missing_items": missing,
            "shelf_life_days": None,
            "remaining_days": None,
            "remaining_fraction": None,
            "remaining_grade": "unknown",
            "storage_findings": [],
            "findings": findings,
            "disposition": "reject",
        }
    if "receipt_date" not in package or package.get("receipt_date") is None:
        raise ValueError("package missing required key 'receipt_date'")

    (_, _, _), chain_findings = validate_date_chain(
        package["manufacture_date"], package["receipt_date"], package["expiry_date"]
    )
    findings.extend(chain_findings)
    if chain_findings:
        return {
            "missing_items": [],
            "shelf_life_days": None,
            "remaining_days": None,
            "remaining_fraction": None,
            "remaining_grade": "unknown",
            "storage_findings": [],
            "findings": findings,
            "disposition": "reject",
        }

    total = shelf_life_days(package["manufacture_date"], package["expiry_date"])
    left = remaining_days_at_receipt(package["receipt_date"], package["expiry_date"])
    fraction = float(left) / float(total)
    grade = grade_remaining_life(fraction)
    findings.extend(declared_duration_findings(package))
    storage_findings = storage_evidence_findings(package)
    findings.extend(storage_findings)

    if grade == "insufficient":
        findings.append(
            "only %d of %d shelf-life days remained at receipt (%.3f of the full life), "
            "below the acceptance floor" % (left, total, fraction)
        )
        disposition = "reject"
    elif any("above the specified" in f or "below the specified" in f for f in storage_findings):
        disposition = "reject"
    elif grade == "short" or findings:
        disposition = "accept-with-actions"
        if grade == "short":
            findings.append(
                "remaining shelf life at receipt is %.3f of the full life, under the "
                "%.2f target; plan the work against the shortened window"
                % (fraction, TARGET_REMAINING_FRACTION)
            )
    else:
        disposition = "accept"

    if disposition not in _DISPOSITIONS:
        raise ValueError("internal disposition error: %r" % (disposition,))
    return {
        "missing_items": [],
        "shelf_life_days": total,
        "remaining_days": left,
        "remaining_fraction": fraction,
        "remaining_grade": grade,
        "storage_findings": storage_findings,
        "findings": findings,
        "disposition": disposition,
    }
