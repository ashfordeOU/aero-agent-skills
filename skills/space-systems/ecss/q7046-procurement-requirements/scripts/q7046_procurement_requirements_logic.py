"""Procurement screening for threaded fasteners: source, purchase data, certificates.

Anchor: ECSS-Q-ST-70-46C, the procurement clause (buying threaded fasteners
only from a qualified source, against purchase data that carries everything the
lot has to be reproducible by, and with the certificates that tie the delivered
lot back to that data). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the order: category, lot identifier, quantity, delivery date.
2. Confirm the manufacturer holds a qualification that is live on the order
   date and whose scope covers the ordered fastener category.
3. Score the purchase-data items the order carries against the required set
   and return the completeness ratio plus the named omissions.
4. Match every required certificate to the order: right kind, right lot,
   issued no later than delivery, signed by a named authority.
5. Combine the three into one goods-in disposition -- release, hold or reject
   -- carrying the reasons that produced it.
"""

import math
from datetime import date

__all__ = [
    "REQUIRED_PURCHASE_DATA",
    "REQUIRED_CERTIFICATES",
    "RATIO_TOLERANCE",
    "parse_iso_date",
    "validate_order",
    "purchase_data_completeness",
    "qualification_days_remaining",
    "source_check",
    "certificate_check",
    "certificate_set_check",
    "disposition_for",
    "assess_procurement_package",
]

# The purchase-data items a fastener order has to carry for the delivered lot
# to be reproducible and traceable. Anything absent is a named omission, never
# a silently defaulted value.
REQUIRED_PURCHASE_DATA = (
    "part_designation",
    "standard_reference",
    "material_and_condition",
    "property_class",
    "surface_treatment",
    "lot_identification",
    "certificate_requirement",
    "inspection_level",
)

# Certificate kinds a delivered lot has to arrive with.
REQUIRED_CERTIFICATES = (
    "material_certificate",
    "conformity_certificate",
    "mechanical_test_report",
)

# Completeness is a ratio of two small integers, but it is still a float; the
# comparison against a whole ratio absorbs representation error rather than
# relying on an exact binary value.
RATIO_TOLERANCE = 1e-12

_DISPOSITIONS = ("release", "hold", "reject")


def parse_iso_date(value, label="date"):
    """Return a date from an ISO yyyy-mm-dd string or a date object."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string or a date, got %r" % (label, value))
    parts = value.split("-")
    if len(parts) != 3:
        raise ValueError("%s must look like yyyy-mm-dd, got %r" % (label, value))
    try:
        year, month, day = (int(p) for p in parts)
    except ValueError:
        raise ValueError("%s must look like yyyy-mm-dd, got %r" % (label, value))
    try:
        return date(year, month, day)
    except ValueError:
        raise ValueError("%s is not a real calendar date: %r" % (label, value))


def validate_order(order):
    """Return the validated order fields needed by every downstream check."""
    if not isinstance(order, dict):
        raise ValueError("order must be a mapping")
    for key in ("category", "lot_id", "quantity", "delivery_date"):
        if key not in order:
            raise ValueError("order missing required key '%s'" % key)
    category = order["category"]
    lot_id = order["lot_id"]
    if not isinstance(category, str) or not category.strip():
        raise ValueError("order category must be a non-empty string")
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("order lot_id must be a non-empty string")
    quantity = order["quantity"]
    if not isinstance(quantity, int) or isinstance(quantity, bool):
        raise ValueError("order quantity must be an integer")
    if quantity <= 0:
        raise ValueError("order quantity must be positive, got %d" % quantity)
    return {
        "category": category.strip(),
        "lot_id": lot_id.strip(),
        "quantity": quantity,
        "delivery_date": parse_iso_date(order["delivery_date"], "delivery_date"),
    }


def purchase_data_completeness(purchase_data, required=REQUIRED_PURCHASE_DATA):
    """Return the completeness ratio of the purchase data and its omissions."""
    if not isinstance(purchase_data, dict):
        raise ValueError("purchase_data must be a mapping")
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required purchase-data item list must be non-empty")
    present = []
    missing = []
    for item in required:
        value = purchase_data.get(item)
        if value is None:
            missing.append(item)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(item)
            continue
        present.append(item)
    unrecognised = sorted(k for k in purchase_data if k not in required)
    ratio = float(len(present)) / float(len(required))
    return {
        "present": present,
        "missing": missing,
        "unrecognised": unrecognised,
        "completeness_ratio": ratio,
        "complete": math.isclose(ratio, 1.0, rel_tol=0.0, abs_tol=RATIO_TOLERANCE),
    }


def qualification_days_remaining(source, reference_date):
    """Return whole days of qualification validity left on the reference date."""
    if not isinstance(source, dict):
        raise ValueError("source must be a mapping")
    if "qualification_expiry" not in source:
        raise ValueError("source missing 'qualification_expiry'")
    expiry = parse_iso_date(source["qualification_expiry"], "qualification_expiry")
    reference = parse_iso_date(reference_date, "reference_date")
    return (expiry - reference).days


def source_check(source, order_view):
    """Judge whether the manufacturer may be bought from for this order."""
    if not isinstance(source, dict):
        raise ValueError("source must be a mapping")
    for key in ("name", "qualification_status", "qualified_categories", "qualification_expiry"):
        if key not in source:
            raise ValueError("source missing required key '%s'" % key)
    name = source["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("source name must be a non-empty string")
    status = source["qualification_status"]
    if status not in ("qualified", "conditional", "suspended", "none"):
        raise ValueError("unknown qualification_status %r" % (status,))
    categories = source["qualified_categories"]
    if not isinstance(categories, (list, tuple)):
        raise ValueError("qualified_categories must be a sequence")
    remaining = qualification_days_remaining(source, order_view["delivery_date"])
    covers = order_view["category"] in [str(c) for c in categories]
    reasons = []
    if status == "none":
        reasons.append("manufacturer holds no qualification")
    elif status == "suspended":
        reasons.append("manufacturer qualification is suspended")
    if remaining < 0:
        reasons.append("qualification expired %d days before delivery" % abs(remaining))
    if not covers:
        reasons.append(
            "qualification scope does not cover category '%s'" % order_view["category"]
        )
    acceptable = not reasons
    return {
        "name": name.strip(),
        "status": status,
        "covers_category": covers,
        "days_remaining": remaining,
        "conditional": status == "conditional" and acceptable,
        "acceptable": acceptable,
        "reasons": reasons,
    }


def certificate_check(certificate, order_view):
    """Judge one certificate against the order it is supposed to belong to."""
    if not isinstance(certificate, dict):
        raise ValueError("certificate must be a mapping")
    for key in ("kind", "lot_id", "issue_date", "signatory"):
        if key not in certificate:
            raise ValueError("certificate missing required key '%s'" % key)
    kind = certificate["kind"]
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("certificate kind must be a non-empty string")
    issue = parse_iso_date(certificate["issue_date"], "issue_date")
    signatory = certificate["signatory"]
    reasons = []
    if str(certificate["lot_id"]).strip() != order_view["lot_id"]:
        reasons.append(
            "%s cites lot '%s', order lot is '%s'"
            % (kind, certificate["lot_id"], order_view["lot_id"])
        )
    if issue > order_view["delivery_date"]:
        reasons.append("%s is dated after delivery" % kind)
    if not isinstance(signatory, str) or not signatory.strip():
        reasons.append("%s carries no named signatory" % kind)
    return {
        "kind": kind.strip(),
        "issue_date": issue,
        "acceptable": not reasons,
        "reasons": reasons,
    }


def certificate_set_check(certificates, order_view, required=REQUIRED_CERTIFICATES):
    """Judge the whole certificate pack: kinds present, each one consistent."""
    if not isinstance(certificates, (list, tuple)):
        raise ValueError("certificates must be a sequence")
    results = [certificate_check(c, order_view) for c in certificates]
    seen = set(r["kind"] for r in results if r["acceptable"])
    missing = [kind for kind in required if kind not in seen]
    reasons = []
    for result in results:
        reasons.extend(result["reasons"])
    for kind in missing:
        reasons.append("no acceptable %s in the pack" % kind)
    return {
        "results": results,
        "missing_kinds": missing,
        "acceptable": not reasons,
        "reasons": reasons,
    }


def disposition_for(source_result, data_result, certificate_result):
    """Combine the three checks into a goods-in disposition."""
    for label, result in (
        ("source_result", source_result),
        ("data_result", data_result),
        ("certificate_result", certificate_result),
    ):
        if not isinstance(result, dict):
            raise ValueError("%s must be a mapping" % label)
    if not source_result.get("acceptable"):
        return "reject"
    if not data_result.get("complete"):
        return "hold"
    if not certificate_result.get("acceptable"):
        return "hold"
    if source_result.get("conditional"):
        return "hold"
    return "release"


def assess_procurement_package(package):
    """Run the whole procurement screen over an order, source and certificates.

    package keys: order (mapping), source (mapping), purchase_data (mapping),
    certificates (sequence of mappings).
    """
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping")
    for key in ("order", "source", "purchase_data", "certificates"):
        if key not in package:
            raise ValueError("package missing required key '%s'" % key)
    order_view = validate_order(package["order"])
    source_result = source_check(package["source"], order_view)
    data_result = purchase_data_completeness(package["purchase_data"])
    certificate_result = certificate_set_check(package["certificates"], order_view)
    findings = list(source_result["reasons"])
    for item in data_result["missing"]:
        findings.append("purchase data omits '%s'" % item)
    findings.extend(certificate_result["reasons"])
    disposition = disposition_for(source_result, data_result, certificate_result)
    if disposition not in _DISPOSITIONS:
        raise ValueError("internal disposition error: %r" % (disposition,))
    return {
        "order": order_view,
        "source": source_result,
        "purchase_data": data_result,
        "certificates": certificate_result,
        "disposition": disposition,
        "findings": findings,
    }
