"""Acceptance of a delivered batch of material or piece parts for a hybrid.

Anchor: ECSS-Q-ST-60-05C clause 9.4 (the conditions a delivered batch of
materials or piece parts satisfies before it enters hybrid manufacture).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the delivered batch record: a lot identity, a procured item
   category, real calendar manufacture and receipt dates, and for a
   limited-life material the shelf life the specification fixed.
2. Compute the batch age at receipt and the shelf life remaining, both in days
   and as the fraction of the declared life still unspent.
3. Compare the remaining life with the planned time to use, because a batch
   that is in date today and out of date at assembly is not usable material.
4. Compare the temperatures the batch was actually held at against the storage
   regime the specification declared, since a cold-chain excursion is not
   recoverable by retest.
5. Confirm the batch carries a single manufacturing lot identity unless the
   order permitted more than one.
6. Check the lot documentation the item category owes.
7. Return release, conditional-release or quarantine with every failing
   condition named, and roll several batches up into one goods-in view.
"""

import datetime

__all__ = [
    "FRACTION_TOLERANCE",
    "DEFAULT_RESERVE_FRACTION",
    "STORAGE_REGIMES",
    "LIMITED_LIFE_CATEGORIES",
    "CORE_LOT_DOCUMENTS",
    "CATEGORY_LOT_DOCUMENTS",
    "ITEM_CATEGORIES",
    "RELEASE",
    "CONDITIONAL_RELEASE",
    "QUARANTINE",
    "parse_date",
    "batch_age_days",
    "shelf_life_state",
    "storage_compliance",
    "lot_identity_state",
    "required_lot_documents",
    "missing_lot_documents",
    "validate_batch",
    "assess_batch",
    "assess_goods_in",
]

# The remaining-life fraction is a quotient of integer day counts that lands
# exactly on the reserve in the ordinary case. Comparisons absorb
# representation error here rather than by moving the reserve.
FRACTION_TOLERANCE = 1e-9

# Fraction of the declared shelf life a batch keeps at receipt before it is
# released without a restriction.
DEFAULT_RESERVE_FRACTION = 0.25

# Storage regimes a specification can declare, with the temperature window in
# degrees Celsius each one holds the batch inside.
STORAGE_REGIMES = {
    "frozen": (-80.0, -15.0),
    "refrigerated": (0.0, 10.0),
    "ambient-controlled": (15.0, 30.0),
    "ambient": (-10.0, 45.0),
}

# Categories whose items have a shelf life the specification fixes.
LIMITED_LIFE_CATEGORIES = ("adhesive", "sealing-material", "encapsulant")

# Documentation every delivered batch carries.
CORE_LOT_DOCUMENTS = (
    "certificate-of-conformity",
    "lot-identification-record",
    "storage-and-handling-record",
)

# Documentation a category adds on top of the core set.
CATEGORY_LOT_DOCUMENTS = {
    "adhesive": ("certificate-of-analysis", "batch-cure-verification-record"),
    "sealing-material": ("certificate-of-analysis", "batch-cure-verification-record"),
    "encapsulant": ("certificate-of-analysis", "batch-cure-verification-record"),
    "substrate": ("dimensional-inspection-record", "metallization-adhesion-record"),
    "bonding-wire": ("spool-test-record", "breaking-load-record"),
    "preform": ("alloy-analysis-record",),
    "package-and-lid": ("plating-thickness-record", "sealing-surface-inspection-record"),
    "piece-part": ("lot-test-data",),
}

ITEM_CATEGORIES = tuple(sorted(CATEGORY_LOT_DOCUMENTS))

RELEASE = "release"
CONDITIONAL_RELEASE = "conditional-release"
QUARANTINE = "quarantine"


def _require_text(value, label):
    """Return value as a stripped non-empty string, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    stripped = value.strip()
    if not stripped:
        raise ValueError("%s must not be blank" % label)
    return stripped


def _require_positive_int(value, label):
    """Return value as a positive int, raising on anything that is not one."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _require_number(value, label):
    """Return value as a float, raising on anything that is not a real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if number != number:
        raise ValueError("%s must be a real number, got %r" % (label, value))
    return number


def parse_date(value, label):
    """Return an ISO date string as a date, raising on anything else."""
    text = _require_text(value, label)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s %r is not an ISO calendar date" % (label, value))


def batch_age_days(manufacture_date, receipt_date):
    """Return the age of a batch at goods-in, in whole days."""
    made = parse_date(manufacture_date, "manufacture_date")
    received = parse_date(receipt_date, "receipt_date")
    if received < made:
        raise ValueError("receipt_date precedes manufacture_date")
    return (received - made).days


def shelf_life_state(manufacture_date, receipt_date, shelf_life_days, days_to_use=0):
    """Return the shelf life a batch has left at goods-in and at point of use.

    The remaining fraction is what is left of the declared life at receipt. The
    cover check asks a different question: whether what is left still reaches
    the day the batch is planned to be used.
    """
    life = _require_positive_int(shelf_life_days, "shelf_life_days")
    if isinstance(days_to_use, bool) or not isinstance(days_to_use, int):
        raise ValueError("days_to_use must be an integer, got %r" % (days_to_use,))
    if days_to_use < 0:
        raise ValueError("days_to_use must not be negative")
    age = batch_age_days(manufacture_date, receipt_date)
    remaining = life - age
    return {
        "age_days": age,
        "shelf_life_days": life,
        "remaining_days": remaining,
        "remaining_fraction": remaining / float(life),
        "in_date_at_receipt": remaining > 0,
        "days_to_use": days_to_use,
        "covers_planned_use": remaining >= days_to_use and remaining > 0,
    }


def storage_compliance(regime, observed_min_c, observed_max_c):
    """Return whether the temperatures a batch was held at stayed in its regime.

    A declared regime the specification did not define cannot be graded, so an
    unrecognised regime raises rather than passing by default.
    """
    name = _require_text(regime, "storage_regime").lower().replace("_", "-")
    if name not in STORAGE_REGIMES:
        raise ValueError("unrecognised storage regime %r" % (regime,))
    lower, upper = STORAGE_REGIMES[name]
    observed_low = _require_number(observed_min_c, "observed_min_c")
    observed_high = _require_number(observed_max_c, "observed_max_c")
    if observed_high < observed_low:
        raise ValueError("observed_max_c is below observed_min_c")
    findings = []
    if observed_low < lower - FRACTION_TOLERANCE:
        findings.append(
            "storage fell to %.2f C against a %s floor of %.2f C" % (observed_low, name, lower)
        )
    if observed_high > upper + FRACTION_TOLERANCE:
        findings.append(
            "storage reached %.2f C against a %s ceiling of %.2f C" % (observed_high, name, upper)
        )
    return {
        "regime": name,
        "window_c": (lower, upper),
        "observed_c": (observed_low, observed_high),
        "within_regime": not findings,
        "findings": findings,
    }


def lot_identity_state(lot_ids, multiple_lots_permitted=False):
    """Return whether a delivered batch carries one manufacturing identity.

    Batch-dependent acceptance data characterises the lot it came from, so a
    delivery spanning two manufacturing lots carries two populations against
    one set of data unless the order allowed for it.
    """
    if isinstance(lot_ids, str) or not isinstance(lot_ids, (list, tuple)):
        raise ValueError("lot_ids must be a sequence of lot identities")
    if not lot_ids:
        raise ValueError("delivered batch carries no lot identity")
    if not isinstance(multiple_lots_permitted, bool):
        raise ValueError("multiple_lots_permitted must be a boolean")
    cleaned = []
    for index, value in enumerate(lot_ids):
        text = _require_text(value, "lot_ids[%d]" % index)
        if text.lower() in {"unknown", "tbd", "n/a", "na", "-", "none"}:
            raise ValueError("lot_ids[%d] does not identify a manufacturing lot" % index)
        if text not in cleaned:
            cleaned.append(text)
    return {
        "lot_ids": cleaned,
        "lot_count": len(cleaned),
        "single_lot": len(cleaned) == 1,
        "permitted": len(cleaned) == 1 or multiple_lots_permitted,
    }


def required_lot_documents(category):
    """Return the lot documentation a procured item category owes."""
    name = _require_text(category, "category").lower().replace("_", "-")
    if name not in CATEGORY_LOT_DOCUMENTS:
        raise ValueError("unrecognised procured item category %r" % (category,))
    return tuple(CORE_LOT_DOCUMENTS) + tuple(CATEGORY_LOT_DOCUMENTS[name])


def missing_lot_documents(provided, category):
    """Return the documents this batch did not carry, matched forgivingly.

    Names are compared insensitively to case and separator so a differently
    punctuated certificate still counts as the certificate.
    """
    required = required_lot_documents(category)
    if isinstance(provided, str) or not isinstance(provided, (list, tuple, set, frozenset)):
        raise ValueError("provided documents must be a sequence of document names")
    seen = set()
    for item in provided:
        text = _require_text(item, "document name").lower()
        seen.add(text.replace("_", "-").replace(" ", "-"))
    return [document for document in required if document not in seen]


def validate_batch(record):
    """Return a normalised delivered-batch record.

    A limited-life category without a declared shelf life is an input error:
    the condition that governs the disposition was never declared, so there is
    nothing to grade.
    """
    if not isinstance(record, dict):
        raise ValueError("batch must be a mapping")
    for key in ("batch_reference", "category", "lot_ids", "manufacture_date",
                "receipt_date", "storage_regime", "observed_min_c",
                "observed_max_c", "documents"):
        if key not in record:
            raise ValueError("batch missing required key '%s'" % key)
    category = _require_text(record["category"], "category").lower().replace("_", "-")
    if category not in CATEGORY_LOT_DOCUMENTS:
        raise ValueError("unrecognised procured item category %r" % (record["category"],))
    limited_life = category in LIMITED_LIFE_CATEGORIES
    if limited_life and record.get("shelf_life_days") is None:
        raise ValueError(
            "%s is a limited-life category and needs shelf_life_days" % category
        )
    normalised = {
        "batch_reference": _require_text(record["batch_reference"], "batch_reference"),
        "category": category,
        "limited_life": limited_life,
        "manufacture_date": parse_date(record["manufacture_date"], "manufacture_date").isoformat(),
        "receipt_date": parse_date(record["receipt_date"], "receipt_date").isoformat(),
        "shelf_life_days": record.get("shelf_life_days"),
        "days_to_use": record.get("days_to_use", 0),
        "multiple_lots_permitted": record.get("multiple_lots_permitted", False),
    }
    if normalised["shelf_life_days"] is not None:
        normalised["shelf_life_days"] = _require_positive_int(
            normalised["shelf_life_days"], "shelf_life_days"
        )
    return normalised


def assess_batch(record, reserve_fraction=DEFAULT_RESERVE_FRACTION):
    """Run the full clause 9.4 assessment of one delivered batch.

    record keys: batch_reference, category, lot_ids, manufacture_date,
    receipt_date, storage_regime, observed_min_c, observed_max_c, documents,
    optional shelf_life_days, days_to_use and multiple_lots_permitted.
    """
    reserve = _require_number(reserve_fraction, "reserve_fraction")
    if reserve < 0.0 or reserve > 1.0:
        raise ValueError("reserve_fraction must lie between 0 and 1")
    normalised = validate_batch(record)
    storage = storage_compliance(
        record["storage_regime"], record["observed_min_c"], record["observed_max_c"]
    )
    identity = lot_identity_state(record["lot_ids"], normalised["multiple_lots_permitted"])
    absent = missing_lot_documents(record["documents"], normalised["category"])

    life = None
    if normalised["shelf_life_days"] is not None:
        life = shelf_life_state(
            normalised["manufacture_date"],
            normalised["receipt_date"],
            normalised["shelf_life_days"],
            normalised["days_to_use"],
        )

    quarantine_findings = []
    restrictions = []
    if not storage["within_regime"]:
        quarantine_findings.extend(storage["findings"])
    if absent:
        quarantine_findings.append("lot documentation incomplete: %s" % ", ".join(absent))
    if not identity["permitted"]:
        quarantine_findings.append(
            "batch spans %d manufacturing lots against one set of acceptance data"
            % identity["lot_count"]
        )
    elif not identity["single_lot"]:
        restrictions.append(
            "batch spans %d manufacturing lots; keep the lots segregated in stores"
            % identity["lot_count"]
        )
    if life is not None:
        if not life["in_date_at_receipt"]:
            quarantine_findings.append(
                "batch is %d day(s) past its shelf life at receipt"
                % (life["age_days"] - life["shelf_life_days"])
            )
        else:
            if not life["covers_planned_use"]:
                restrictions.append(
                    "%d day(s) of life left against %d day(s) to planned use"
                    % (life["remaining_days"], life["days_to_use"])
                )
            if life["remaining_fraction"] < reserve - FRACTION_TOLERANCE:
                restrictions.append(
                    "only %.4f of the declared shelf life is left at receipt"
                    % life["remaining_fraction"]
                )

    if quarantine_findings:
        disposition = QUARANTINE
    elif restrictions:
        disposition = CONDITIONAL_RELEASE
    else:
        disposition = RELEASE
    return {
        "batch_reference": normalised["batch_reference"],
        "category": normalised["category"],
        "limited_life": normalised["limited_life"],
        "shelf_life": life,
        "storage": storage,
        "lot_identity": identity,
        "missing_documents": absent,
        "disposition": disposition,
        "quarantine_findings": quarantine_findings,
        "restrictions": restrictions,
        "usable": disposition != QUARANTINE,
    }


def assess_goods_in(records, reserve_fraction=DEFAULT_RESERVE_FRACTION):
    """Roll a set of delivered batches up into one goods-in view."""
    if isinstance(records, dict) or not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of delivered batches")
    if not records:
        raise ValueError("goods-in delivery contains no batches")
    verdicts = [assess_batch(record, reserve_fraction) for record in records]
    seen = set()
    for verdict in verdicts:
        key = verdict["batch_reference"].lower()
        if key in seen:
            raise ValueError("duplicate batch reference %r" % verdict["batch_reference"])
        seen.add(key)
    quarantined = [v["batch_reference"] for v in verdicts if v["disposition"] == QUARANTINE]
    restricted = [
        v["batch_reference"] for v in verdicts if v["disposition"] == CONDITIONAL_RELEASE
    ]
    return {
        "batch_count": len(verdicts),
        "batches": verdicts,
        "quarantined": quarantined,
        "restricted": restricted,
        "released": [v["batch_reference"] for v in verdicts if v["disposition"] == RELEASE],
        "released_fraction": (len(verdicts) - len(quarantined)) / float(len(verdicts)),
        "all_released_unrestricted": not quarantined and not restricted,
    }
