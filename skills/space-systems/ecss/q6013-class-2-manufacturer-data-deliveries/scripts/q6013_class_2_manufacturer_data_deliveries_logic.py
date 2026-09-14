"""Manufacturer data packages delivered with a lot at the middle class.

Anchor: ECSS-Q-ST-60-13C clause 5.3.11 (intermediate assurance class use of
commercial EEE components -- the documentation package the manufacturer
delivers with the lot). Paraphrased into an implementable procedure; no
standard text is reproduced.

The question the clause answers
-------------------------------
A lot arrives with a folder of paper. The folder is not the point; what the
paper says about the units in the box is. This class differs from the class
above in one structural way: an item may be delivered as a summary that
points at data the manufacturer retains, rather than as the data itself, and
that is a thinner delivery which is credited below a full one. The pointer
only counts when the retained data will still exist when it is needed.

Procedure implemented here
--------------------------
1. Fix the identity of the lot the package is offered against: its lot
   identifier and its date code. Every item is then matched against that
   identity rather than against the order.
2. Assemble the item set this delivery owes: the items every lot owes at
   this class, plus any on-request item the procurement specification called
   off for this purchase.
3. Dispose each item: delivered in full, delivered as a supported summary,
   delivered as a summary with no retained data behind it or with retention
   too short, identified incompletely, matched to another lot, delivered
   after lot acceptance, or absent.
4. Take the delivered share and the credit-weighted completeness over the
   owed item set, so that deleting a weak item can only lower the figures.
5. Close on one verdict, with every failing item named rather than the first
   one found.
"""

import math

__all__ = [
    "SHARE_TOLERANCE",
    "DEFAULT_DELIVERY_POLICY",
    "REQUIRED_ITEMS",
    "ON_REQUEST_ITEMS",
    "KNOWN_ITEMS",
    "DELIVERED_IN_FULL",
    "DELIVERED_AS_SUMMARY",
    "SUMMARY_UNSUPPORTED",
    "IDENTIFIER_INCOMPLETE",
    "LOT_MISMATCH",
    "DELIVERED_LATE",
    "ABSENT",
    "PACKAGE_NOT_DELIVERED",
    "PACKAGE_LOT_MISMATCH",
    "PACKAGE_DELIVERED_LATE",
    "PACKAGE_ITEMS_SHORT",
    "PACKAGE_MEETS_CLASS_TWO_SCOPE",
    "validate_delivery_policy",
    "validate_lot_identity",
    "validate_item_record",
    "owed_items",
    "item_disposition",
    "dispose_items",
    "items_with_disposition",
    "delivered_share",
    "weighted_completeness",
    "assess_manufacturer_data_deliveries",
]

# Shares and weighted completeness are ratios of small sums. A package
# landing exactly on a floor can come out a few ULP under it once the credit
# has been applied and divided, and the two sides round differently on
# different platforms, so the representation error is absorbed here rather
# than being allowed to fail a compliant package.
SHARE_TOLERANCE = 1e-12

DEFAULT_DELIVERY_POLICY = {
    # Every owed item has to arrive; a summary still counts as arrived.
    "min_delivered_share": 1.0,
    # A summary is a thinner delivery than the data, and this is the credit
    # it earns.
    "summary_credit": 0.7,
    "min_weighted_completeness": 0.8,
    # A summary only counts while the data behind it still exists.
    "min_retention_months": 120,
    # A treated item this close to a floor is reported as an advisory.
    "marginal_band": 0.05,
}

# The items a lot owes at this class whatever the procurement specification
# says.
REQUIRED_ITEMS = (
    "certificate-of-conformity",
    "lot-traceability-record",
    "electrical-test-data",
    "screening-and-burn-in-record",
    "construction-and-materials-data",
    "nonconformance-record",
    "packing-and-esd-record",
)

# Items owed only where the procurement specification called them off.
ON_REQUEST_ITEMS = (
    "radiation-test-data",
    "destructive-sampling-report",
    "assembly-process-change-notice",
)

KNOWN_ITEMS = frozenset(REQUIRED_ITEMS) | frozenset(ON_REQUEST_ITEMS)

DELIVERED_IN_FULL = "delivered-in-full"
DELIVERED_AS_SUMMARY = "delivered-as-supported-summary"
SUMMARY_UNSUPPORTED = "summary-without-retained-data"
IDENTIFIER_INCOMPLETE = "identifier-incomplete"
LOT_MISMATCH = "matched-to-another-lot"
DELIVERED_LATE = "delivered-after-lot-acceptance"
ABSENT = "absent"

PACKAGE_NOT_DELIVERED = "data-package-not-delivered"
PACKAGE_LOT_MISMATCH = "data-package-covers-another-lot"
PACKAGE_DELIVERED_LATE = "data-package-delivered-after-acceptance"
PACKAGE_ITEMS_SHORT = "data-package-items-short"
PACKAGE_MEETS_CLASS_TWO_SCOPE = "data-package-meets-class-two-scope"

_CREDITED = (DELIVERED_IN_FULL, DELIVERED_AS_SUMMARY)


def _at_or_above(value, limit):
    """True when value is at or above limit, absorbing representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=SHARE_TOLERANCE, abs_tol=0.0
    )


def _validate_fraction(value, label, allow_zero=True):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    fraction = float(value)
    if not math.isfinite(fraction):
        raise ValueError("%s must be finite" % label)
    if fraction < 0.0 or (fraction == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %r" % (label, value))
    if fraction > 1.0:
        raise ValueError("%s is a fraction and cannot exceed unity, got %r" % (label, value))
    return fraction


def _validate_count(value, label, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer" % label)
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (label, minimum, value))
    return value


def _validate_flag(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean" % label)
    return value


def _text(value, label, required=True):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError("%s must be a string" % label)
    cleaned = value.strip()
    if required and not cleaned:
        raise ValueError("%s must be a non-empty string" % label)
    return cleaned


def validate_delivery_policy(policy):
    """Validate a delivery policy and return it unchanged."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    for key in DEFAULT_DELIVERY_POLICY:
        if key not in policy:
            raise ValueError("policy missing required key '%s'" % key)
    share_floor = _validate_fraction(
        policy["min_delivered_share"], "min_delivered_share", allow_zero=False
    )
    credit = _validate_fraction(policy["summary_credit"], "summary_credit", allow_zero=False)
    completeness_floor = _validate_fraction(
        policy["min_weighted_completeness"], "min_weighted_completeness", allow_zero=False
    )
    band = _validate_fraction(policy["marginal_band"], "marginal_band")
    _validate_count(policy["min_retention_months"], "min_retention_months", minimum=1)
    if credit >= 1.0:
        raise ValueError(
            "summary_credit must sit below unity; a summary is a thinner delivery "
            "than the data it points at"
        )
    if completeness_floor > share_floor:
        raise ValueError(
            "min_weighted_completeness cannot exceed min_delivered_share; the "
            "weighted figure can never be the larger of the two"
        )
    if band >= completeness_floor:
        raise ValueError("marginal_band cannot reach the completeness floor")
    return policy


def validate_lot_identity(lot):
    """Validate the identity of the lot the package is offered against."""
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping with 'lot_identifier' and 'date_code'")
    for key in ("lot_identifier", "date_code"):
        if key not in lot:
            raise ValueError("lot missing required key '%s'" % key)
    return {
        "lot_identifier": _text(lot["lot_identifier"], "lot_identifier"),
        "date_code": _text(lot["date_code"], "date_code"),
    }


def validate_item_record(record):
    """Validate one delivered data item and return it normalised."""
    if not isinstance(record, dict):
        raise ValueError("each delivered item must be a mapping")
    for key in (
        "item",
        "document_reference",
        "issue",
        "lot_identifier",
        "date_code",
        "delivered_before_acceptance",
        "summary_only",
    ):
        if key not in record:
            raise ValueError("delivered item missing required key '%s'" % key)
    item = _text(record["item"], "item").lower()
    if item not in KNOWN_ITEMS:
        raise ValueError(
            "data item '%s' is not in the register; add it to the register rather "
            "than letting an unrecognised item satisfy a required one" % item
        )
    summary_only = _validate_flag(record["summary_only"], "summary_only")
    normalised = {
        "item": item,
        "document_reference": _text(
            record["document_reference"], "document_reference", required=False
        ),
        "issue": _text(record["issue"], "issue", required=False),
        "lot_identifier": _text(record["lot_identifier"], "lot_identifier", required=False),
        "date_code": _text(record["date_code"], "date_code", required=False),
        "delivered_before_acceptance": _validate_flag(
            record["delivered_before_acceptance"], "delivered_before_acceptance"
        ),
        "summary_only": summary_only,
        "underlying_data_retained": _validate_flag(
            record.get("underlying_data_retained", False), "underlying_data_retained"
        ),
        "retention_months": _validate_count(
            record.get("retention_months", 0), "retention_months"
        ),
    }
    return normalised


def owed_items(requested=None):
    """Return the ordered item set a delivery owes.

    Every lot owes the required items; an on-request item joins them only
    where the procurement specification called it off for this purchase.
    """
    if requested is None:
        requested = ()
    if not isinstance(requested, (list, tuple, set, frozenset)):
        raise ValueError("requested must be a sequence of on-request item names")
    extra = []
    for name in requested:
        key = _text(name, "requested item").lower()
        if key not in ON_REQUEST_ITEMS:
            raise ValueError(
                "'%s' is not an on-request item; a required item cannot be requested "
                "and an unregistered one cannot be owed" % key
            )
        if key not in extra:
            extra.append(key)
    return list(REQUIRED_ITEMS) + sorted(extra)


def item_disposition(record, lot, policy=None):
    """Return the disposition of one delivered item against the lot."""
    policy = validate_delivery_policy(DEFAULT_DELIVERY_POLICY if policy is None else policy)
    lot = validate_lot_identity(lot)
    record = validate_item_record(record)
    if not record["document_reference"] or not record["issue"]:
        return IDENTIFIER_INCOMPLETE
    if (
        record["lot_identifier"].lower() != lot["lot_identifier"].lower()
        or record["date_code"].lower() != lot["date_code"].lower()
    ):
        return LOT_MISMATCH
    if not record["delivered_before_acceptance"]:
        return DELIVERED_LATE
    if record["summary_only"]:
        if not record["underlying_data_retained"]:
            return SUMMARY_UNSUPPORTED
        if record["retention_months"] < policy["min_retention_months"]:
            return SUMMARY_UNSUPPORTED
        return DELIVERED_AS_SUMMARY
    return DELIVERED_IN_FULL


def dispose_items(delivered, lot, requested=None, policy=None):
    """Return the disposition of every owed item, absent ones included."""
    policy = validate_delivery_policy(DEFAULT_DELIVERY_POLICY if policy is None else policy)
    if not isinstance(delivered, (list, tuple)):
        raise ValueError("delivered must be a sequence of item records")
    owed = owed_items(requested)
    dispositions = {name: ABSENT for name in owed}
    seen = set()
    for record in delivered:
        normalised = validate_item_record(record)
        name = normalised["item"]
        if name in seen:
            raise ValueError("data item '%s' is delivered twice" % name)
        seen.add(name)
        if name not in dispositions:
            # Delivered but not owed: recorded, never credited against an
            # item the lot actually owes.
            continue
        dispositions[name] = item_disposition(record, lot, policy)
    return {"owed": owed, "dispositions": dispositions, "delivered_not_owed": sorted(seen - set(owed))}


def items_with_disposition(dispositions, owed, wanted):
    """Return the owed items carrying one of the wanted dispositions."""
    if not isinstance(dispositions, dict):
        raise ValueError("dispositions must be a mapping")
    if not isinstance(owed, (list, tuple)) or not owed:
        raise ValueError("owed must be a non-empty sequence")
    if isinstance(wanted, str):
        wanted = (wanted,)
    return [name for name in owed if dispositions.get(name) in tuple(wanted)]


def delivered_share(dispositions, owed):
    """Return the share of owed items that arrived at all."""
    credited = items_with_disposition(dispositions, owed, _CREDITED)
    return len(credited) / float(len(owed))


def weighted_completeness(dispositions, owed, policy=None):
    """Return the completeness of the package with a summary credited below one."""
    policy = validate_delivery_policy(DEFAULT_DELIVERY_POLICY if policy is None else policy)
    if not isinstance(owed, (list, tuple)) or not owed:
        raise ValueError("owed must be a non-empty sequence")
    credit = float(policy["summary_credit"])
    weights = []
    for name in owed:
        disposition = dispositions.get(name)
        if disposition == DELIVERED_IN_FULL:
            weights.append(1.0)
        elif disposition == DELIVERED_AS_SUMMARY:
            weights.append(credit)
    return math.fsum(weights) / float(len(owed))


def assess_manufacturer_data_deliveries(case, policy=None):
    """Run the clause 5.3.11 assessment for one delivered data package.

    case keys: lot, delivered; optional requested.
    """
    policy = validate_delivery_policy(DEFAULT_DELIVERY_POLICY if policy is None else policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("lot", "delivered"):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)
    lot = validate_lot_identity(case["lot"])
    resolved = dispose_items(case["delivered"], lot, case.get("requested"), policy)
    owed = resolved["owed"]
    dispositions = resolved["dispositions"]
    absent = items_with_disposition(dispositions, owed, ABSENT)
    mismatched = items_with_disposition(dispositions, owed, LOT_MISMATCH)
    late = items_with_disposition(dispositions, owed, DELIVERED_LATE)
    incomplete = items_with_disposition(dispositions, owed, IDENTIFIER_INCOMPLETE)
    unsupported = items_with_disposition(dispositions, owed, SUMMARY_UNSUPPORTED)
    summaries = items_with_disposition(dispositions, owed, DELIVERED_AS_SUMMARY)
    share = delivered_share(dispositions, owed)
    completeness = weighted_completeness(dispositions, owed, policy)
    findings = []
    for name in mismatched:
        findings.append("data item '%s' is matched to another lot" % name)
    for name in late:
        findings.append("data item '%s' arrived after lot acceptance" % name)
    for name in incomplete:
        findings.append("data item '%s' carries no reference or no issue" % name)
    for name in unsupported:
        findings.append(
            "data item '%s' is a summary with no retained data behind it" % name
        )
    for name in absent:
        findings.append("data item '%s' was not delivered" % name)
    for name in resolved["delivered_not_owed"]:
        findings.append(
            "data item '%s' was delivered but is not owed by this lot" % name
        )
    advisories = []
    band = float(policy["marginal_band"])
    if _at_or_above(completeness, float(policy["min_weighted_completeness"])) and (
        completeness - float(policy["min_weighted_completeness"]) < band
    ):
        advisories.append(
            "weighted completeness %.4f sits inside the marginal band above its floor"
            % completeness
        )
    if all(dispositions[name] == ABSENT for name in owed):
        verdict = PACKAGE_NOT_DELIVERED
    elif mismatched:
        verdict = PACKAGE_LOT_MISMATCH
    elif late:
        verdict = PACKAGE_DELIVERED_LATE
    elif not _at_or_above(share, float(policy["min_delivered_share"])) or not _at_or_above(
        completeness, float(policy["min_weighted_completeness"])
    ):
        verdict = PACKAGE_ITEMS_SHORT
    else:
        verdict = PACKAGE_MEETS_CLASS_TWO_SCOPE
    return {
        "lot": lot,
        "owed_items": owed,
        "dispositions": dispositions,
        "absent_items": absent,
        "mismatched_items": mismatched,
        "late_items": late,
        "identifier_incomplete_items": incomplete,
        "unsupported_summary_items": unsupported,
        "summary_items": summaries,
        "delivered_not_owed": resolved["delivered_not_owed"],
        "delivered_share": share,
        "weighted_completeness": completeness,
        "advisories": advisories,
        "findings": findings,
        "verdict": verdict,
        "accepted": verdict == PACKAGE_MEETS_CLASS_TWO_SCOPE,
    }
