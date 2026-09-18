"""Expiry-date control for limited-shelf-life materials.

Anchor: ECSS-Q-ST-70-22 stock-control clause -- expiry dates are derived and
tracked, and material past its date is quarantined rather than left issuable.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Derive the nominal expiry from the manufacture date and the declared shelf
   life in months, adding calendar months with end-of-month clamping so the
   31st of a month never rolls into the following one.
2. Pull the date in for time the item spent outside controlled storage: shelf
   life is declared for the storage envelope, so time outside it is consumed at
   a declared acceleration factor, and the excess is charged to the item.
3. Add an approved extension, and only an approved one. An extension with no
   approval reference is a finding, not a date change.
4. Grade the item at a review date: in-date, expiring inside the alert window,
   or expired. A recorded storage non-conformance overrides the arithmetic --
   the shelf life presumed a storage regime the item did not get.
5. Close with a disposition per item and a store-wide quarantine list.
"""

import math
from datetime import date, timedelta

__all__ = [
    "DAY_TOLERANCE",
    "STATUSES",
    "add_months",
    "validate_item",
    "nominal_expiry",
    "out_of_store_penalty_days",
    "effective_expiry",
    "remaining_days",
    "item_status",
    "disposition_for",
    "assess_item",
    "assess_expiry_control",
]

# The out-of-store penalty is a product of a declared factor and an integer day
# count; charge the day only when it is really there, not when the product
# lands a few ULPs above an integer.
DAY_TOLERANCE = 1e-9

STATUSES = ("in-date", "expiring-soon", "expired", "storage-non-conformance")


def add_months(start, months):
    """Return start advanced by whole calendar months, clamped to month end."""
    if not isinstance(start, date):
        raise ValueError("start must be a date, got %r" % (start,))
    if not isinstance(months, int) or isinstance(months, bool):
        raise ValueError("months must be an integer, got %r" % (months,))
    if months < 0:
        raise ValueError("months must be non-negative, got %d" % months)
    total = (start.year * 12 + (start.month - 1)) + months
    year = total // 12
    month = total % 12 + 1
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)
    last_day = (next_month_first - timedelta(days=1)).day
    return date(year, month, min(start.day, last_day))


def _as_date(value, label):
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string or a date, got %r" % (label, value))
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not a valid ISO date: %r" % (label, value))


def validate_item(record):
    """Return a normalised shelf-life item record."""
    if not isinstance(record, dict):
        raise ValueError("item record must be a mapping")
    ident = record.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("item record needs a non-empty 'id'")
    material = record.get("material")
    if not isinstance(material, str) or not material.strip():
        raise ValueError("item record needs a non-empty 'material'")
    manufactured = _as_date(record.get("manufactured"), "manufactured")
    months = record.get("shelf_life_months")
    if not isinstance(months, int) or isinstance(months, bool):
        raise ValueError("shelf_life_months must be an integer, got %r" % (months,))
    if months <= 0:
        raise ValueError("shelf_life_months must be positive, got %d" % months)
    out_days = record.get("out_of_store_days", 0)
    if not isinstance(out_days, int) or isinstance(out_days, bool):
        raise ValueError("out_of_store_days must be an integer, got %r" % (out_days,))
    if out_days < 0:
        raise ValueError("out_of_store_days must be non-negative, got %d" % out_days)
    factor = record.get("out_of_store_factor", 1.0)
    if not isinstance(factor, (int, float)) or isinstance(factor, bool):
        raise ValueError("out_of_store_factor must be a real number, got %r" % (factor,))
    factor = float(factor)
    if not math.isfinite(factor) or factor < 1.0:
        raise ValueError("out_of_store_factor must be finite and at least 1.0, got %r" % (factor,))
    extension = record.get("extension_days", 0)
    if not isinstance(extension, int) or isinstance(extension, bool):
        raise ValueError("extension_days must be an integer, got %r" % (extension,))
    if extension < 0:
        raise ValueError("extension_days must be non-negative, got %d" % extension)
    approval = record.get("extension_approval")
    if approval is not None and (not isinstance(approval, str) or not approval.strip()):
        raise ValueError("extension_approval must be a non-empty string when given")
    conformance = record.get("storage_conformant", True)
    if not isinstance(conformance, bool):
        raise ValueError("storage_conformant must be true or false, got %r" % (conformance,))
    return {
        "id": ident.strip(),
        "material": material.strip(),
        "manufactured": manufactured,
        "shelf_life_months": months,
        "out_of_store_days": out_days,
        "out_of_store_factor": factor,
        "extension_days": extension,
        "extension_approval": approval.strip() if isinstance(approval, str) else None,
        "storage_conformant": conformance,
    }


def nominal_expiry(item):
    """Return the expiry date the declared shelf life gives on its own."""
    norm = validate_item(item)
    return add_months(norm["manufactured"], norm["shelf_life_months"])


def out_of_store_penalty_days(item):
    """Return the whole days of shelf life charged for time outside the store."""
    norm = validate_item(item)
    excess = (norm["out_of_store_factor"] - 1.0) * norm["out_of_store_days"]
    if excess <= DAY_TOLERANCE:
        return 0
    return int(math.ceil(excess - DAY_TOLERANCE))


def effective_expiry(item):
    """Return the expiry actually governing the item, with penalty and extension."""
    norm = validate_item(item)
    base = add_months(norm["manufactured"], norm["shelf_life_months"])
    granted = norm["extension_days"] if norm["extension_approval"] else 0
    return base - timedelta(days=out_of_store_penalty_days(norm)) + timedelta(days=granted)


def remaining_days(item, review_date):
    """Return whole days left at the review date; negative once past expiry."""
    review = _as_date(review_date, "review_date")
    return (effective_expiry(item) - review).days


def item_status(item, review_date, alert_window_days=30):
    """Return the item's shelf-life status at a review date."""
    if not isinstance(alert_window_days, int) or isinstance(alert_window_days, bool):
        raise ValueError("alert_window_days must be an integer, got %r" % (alert_window_days,))
    if alert_window_days < 0:
        raise ValueError("alert_window_days must be non-negative, got %d" % alert_window_days)
    norm = validate_item(item)
    if not norm["storage_conformant"]:
        return "storage-non-conformance"
    left = remaining_days(norm, review_date)
    if left < 0:
        return "expired"
    if left <= alert_window_days:
        return "expiring-soon"
    return "in-date"


def disposition_for(status):
    """Return the stock action a status calls for."""
    if status not in STATUSES:
        raise ValueError("unknown status %r" % (status,))
    return {
        "in-date": "issuable",
        "expiring-soon": "issue-first-or-plan-re-test",
        "expired": "quarantine",
        "storage-non-conformance": "quarantine-pending-review",
    }[status]


def assess_item(item, review_date, alert_window_days=30):
    """Grade one item: dates, status, disposition and findings."""
    norm = validate_item(item)
    status = item_status(norm, review_date, alert_window_days)
    findings = []
    if norm["extension_days"] > 0 and not norm["extension_approval"]:
        findings.append(
            "item %s carries %d extension day(s) with no approval reference; "
            "the extension is not applied" % (norm["id"], norm["extension_days"])
        )
    penalty = out_of_store_penalty_days(norm)
    if penalty > 0:
        findings.append(
            "item %s charged %d day(s) for %d day(s) outside controlled storage"
            % (norm["id"], penalty, norm["out_of_store_days"])
        )
    if not norm["storage_conformant"]:
        findings.append(
            "item %s has a recorded storage non-conformance; the derived date does not apply"
            % norm["id"]
        )
    return {
        "id": norm["id"],
        "material": norm["material"],
        "nominal_expiry": nominal_expiry(norm).isoformat(),
        "effective_expiry": effective_expiry(norm).isoformat(),
        "penalty_days": penalty,
        "granted_extension_days": norm["extension_days"] if norm["extension_approval"] else 0,
        "remaining_days": remaining_days(norm, review_date),
        "status": status,
        "disposition": disposition_for(status),
        "findings": findings,
    }


def assess_expiry_control(items, review_date, alert_window_days=30):
    """Grade a whole holding and return the quarantine list."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence of records")
    review = _as_date(review_date, "review_date")
    seen = set()
    results = []
    for item in items:
        result = assess_item(item, review, alert_window_days)
        if result["id"] in seen:
            raise ValueError("duplicate item id %r" % result["id"])
        seen.add(result["id"])
        results.append(result)
    quarantine = [r["id"] for r in results if r["disposition"].startswith("quarantine")]
    soon = [r["id"] for r in results if r["status"] == "expiring-soon"]
    counts = {}
    for status in STATUSES:
        counts[status] = len([r for r in results if r["status"] == status])
    return {
        "review_date": review.isoformat(),
        "items": results,
        "quarantine_ids": quarantine,
        "expiring_soon_ids": soon,
        "status_counts": counts,
        "all_issuable": not quarantine,
    }
