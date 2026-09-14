"""Manufacturer data delivered with a lowest assurance class commercial lot.

Anchor: ECSS-Q-ST-60-13C clause 6.3.11 (documentation a manufacturer supplies
with a shipment of commercial EEE parts procured at the lowest assurance
class). Paraphrased into an implementable procedure; no standard text is
reproduced.

The question the clause answers
-------------------------------
A commercial EEE lot arrives with a folder of manufacturer paper. The folder
is not the deliverable; what that paper says about the units in this box is.
At the lightest class the owed set is short and part of it may be dropped,
so the question becomes less about volume and more about who issued each
item and whether what they issued still points at something fixed.

What this class does differently
--------------------------------
1. The owed set splits in two. A small core of items is owed by every lot
   and no waiver reaches it. The rest are supporting items, and a supporting
   item may be dropped from the owed set where the project recorded an
   acceptance for dropping it. A waiver with no recorded acceptance behind
   it is not a waiver, it is a gap.
2. Provenance carries a credit rather than a yes or no. A manufacturer-issued
   record is worth more than one issued by a franchised distributor, which is
   worth more than a published datasheet the project archived at a named
   revision, which is worth more than the same datasheet left to move on the
   manufacturer's website.
3. A core item has a credit floor of its own. Published catalogue material
   may support a supporting item at this class; it may not stand in for a
   certificate of conformity.
4. A record issued by a source outside the franchised chain closes the
   assessment on the spot. At this class the parts are commercial, the chain
   is short and a certificate from an unfranchised source is the single
   strongest counterfeit indication the receiving bay ever sees.

Procedure implemented here
--------------------------
1. Fix the lot identity every item is matched against.
2. Assemble the owed set: the core items plus the supporting items no
   recorded acceptance has dropped.
3. Dispose each owed item -- delivered in full, delivered at reduced credit,
   unidentified, matched to another lot, issued by an unfranchised source or
   absent -- and credit it accordingly.
4. Take the provenance-weighted completeness over the owed set and compare it
   against the declared floor and the marginal band above it.
5. Return one receiving verdict with every finding that produced it.
"""

import math

__all__ = [
    "SCORE_TOLERANCE",
    "DEFAULT_DELIVERY_POLICY",
    "CORE_ITEMS",
    "SUPPORTING_ITEMS",
    "ITEM_WEIGHTS",
    "REGISTERED_ITEMS",
    "PROVENANCE_CREDIT",
    "UNFRANCHISED_SOURCE",
    "DISPOSITION_IN_FULL",
    "DISPOSITION_REDUCED",
    "DISPOSITION_UNIDENTIFIED",
    "DISPOSITION_LOT_MISMATCH",
    "DISPOSITION_UNFRANCHISED",
    "DISPOSITION_ABSENT",
    "PACKAGE_ACCEPTED",
    "PACKAGE_ACCEPTED_WITH_ACTIONS",
    "PACKAGE_REFUSED_UNFRANCHISED_SOURCE",
    "PACKAGE_REFUSED_LOT_MISMATCH",
    "PACKAGE_REFUSED_CORE_ITEM_MISSING",
    "PACKAGE_REFUSED_CORE_ITEM_UNDERCREDITED",
    "PACKAGE_REFUSED_SHORT_OF_FLOOR",
    "validate_delivery_policy",
    "lot_identity",
    "provenance_credit",
    "item_weight",
    "owed_item_set",
    "validate_delivered_items",
    "dispose_item",
    "weighted_completeness",
    "meets_floor",
    "assess_data_package",
]

# Credits and the completeness fraction are products and quotients of
# declared weights, so a package landing exactly on its floor can come out a
# few ULP on the wrong side. Absorb that here, never by lowering a floor.
SCORE_TOLERANCE = 1e-9

DEFAULT_DELIVERY_POLICY = {
    # Provenance-weighted completeness the package must reach.
    "completeness_floor": 0.75,
    # A completeness inside this band above the floor is accepted with
    # actions rather than silently.
    "marginal_band": 0.05,
    # A core item must be issued at or above this credit.
    "core_credit_floor": 0.8,
    # Whether the date code is part of the identity items are matched on.
    "require_date_code": True,
}

# Items owed by every lot at this class. No waiver reaches them.
CORE_ITEMS = (
    "certificate-of-conformity",
    "lot-identification-and-date-code",
    "part-datasheet-or-specification",
)

# Items a recorded project acceptance may drop from the owed set.
SUPPORTING_ITEMS = (
    "electrical-test-summary",
    "solderability-or-finish-declaration",
    "moisture-sensitivity-declaration",
    "material-and-substance-declaration",
    "change-notification-subscription",
)

# Relative weight each item carries in the completeness fraction.
ITEM_WEIGHTS = {
    "certificate-of-conformity": 1.0,
    "lot-identification-and-date-code": 1.0,
    "part-datasheet-or-specification": 1.0,
    "electrical-test-summary": 0.8,
    "solderability-or-finish-declaration": 0.6,
    "moisture-sensitivity-declaration": 0.6,
    "material-and-substance-declaration": 0.4,
    "change-notification-subscription": 0.4,
}

REGISTERED_ITEMS = frozenset(ITEM_WEIGHTS)

# What each provenance is worth. A published datasheet counts only while the
# revision the project read is the revision the project kept.
PROVENANCE_CREDIT = {
    "manufacturer-issued": 1.0,
    "franchised-distributor-issued": 0.8,
    "published-datasheet-archived": 0.6,
    "published-datasheet-not-archived": 0.0,
    "absent": 0.0,
}

# Not a credit at all: a record from here closes the assessment.
UNFRANCHISED_SOURCE = "unfranchised-source"

DISPOSITION_IN_FULL = "delivered-in-full"
DISPOSITION_REDUCED = "delivered-at-reduced-credit"
DISPOSITION_UNIDENTIFIED = "delivered-without-an-issue-reference"
DISPOSITION_LOT_MISMATCH = "matched-to-another-lot"
DISPOSITION_UNFRANCHISED = "issued-by-an-unfranchised-source"
DISPOSITION_ABSENT = "absent"

PACKAGE_ACCEPTED = "data-package-meets-class-three-scope"
PACKAGE_ACCEPTED_WITH_ACTIONS = "data-package-accepted-with-actions"
PACKAGE_REFUSED_UNFRANCHISED_SOURCE = "data-package-refused-unfranchised-source"
PACKAGE_REFUSED_LOT_MISMATCH = "data-package-refused-covers-another-lot"
PACKAGE_REFUSED_CORE_ITEM_MISSING = "data-package-refused-core-item-missing"
PACKAGE_REFUSED_CORE_ITEM_UNDERCREDITED = (
    "data-package-refused-core-item-undercredited"
)
PACKAGE_REFUSED_SHORT_OF_FLOOR = "data-package-refused-short-of-completeness-floor"


def _at_or_above(value, floor):
    """True when value is at or above floor, absorbing representation error."""
    return value >= floor or math.isclose(
        value, floor, rel_tol=SCORE_TOLERANCE, abs_tol=0.0
    )


def _validate_fraction(value, label, allow_zero=True):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between zero and unity, got %r" % (label, value))
    if number == 0.0 and not allow_zero:
        raise ValueError("%s must lie above zero, got %r" % (label, value))
    return number


def _validate_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def _validate_flag(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean" % label)
    return value


def validate_delivery_policy(policy):
    """Validate a delivery policy and return it unchanged."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    for key in DEFAULT_DELIVERY_POLICY:
        if key not in policy:
            raise ValueError("policy missing required key '%s'" % key)
    floor = _validate_fraction(
        policy["completeness_floor"], "completeness_floor", allow_zero=False
    )
    band = _validate_fraction(policy["marginal_band"], "marginal_band")
    core_floor = _validate_fraction(
        policy["core_credit_floor"], "core_credit_floor", allow_zero=False
    )
    _validate_flag(policy["require_date_code"], "require_date_code")
    if floor + band > 1.0:
        raise ValueError(
            "the marginal band reaches past a complete package; floor %g plus band %g"
            % (floor, band)
        )
    if core_floor < floor:
        raise ValueError(
            "core_credit_floor %g sits below the package completeness floor %g; a "
            "core item cannot be the weakest thing in the folder" % (core_floor, floor)
        )
    return policy


def lot_identity(lot_identifier, date_code, policy=None):
    """Return the identity every delivered item is matched against."""
    policy = validate_delivery_policy(
        DEFAULT_DELIVERY_POLICY if policy is None else policy
    )
    identity = {"lot_identifier": _validate_text(lot_identifier, "lot_identifier")}
    if policy["require_date_code"]:
        identity["date_code"] = _validate_text(date_code, "date_code")
    else:
        identity["date_code"] = date_code.strip() if isinstance(date_code, str) else ""
    identity["reference"] = "%s/%s" % (
        identity["lot_identifier"],
        identity["date_code"] or "no-date-code",
    )
    return identity


def provenance_credit(provenance):
    """Return the credit a provenance earns, refusing an unfranchised source."""
    key = _validate_text(provenance, "provenance").lower()
    if key == UNFRANCHISED_SOURCE:
        raise ValueError(
            "an unfranchised source is not a credit level; dispose the item rather "
            "than scoring it"
        )
    if key not in PROVENANCE_CREDIT:
        raise ValueError("provenance '%s' is not in the register" % key)
    return PROVENANCE_CREDIT[key]


def item_weight(item):
    """Return the weight a registered data item carries."""
    key = _validate_text(item, "item").lower()
    if key not in ITEM_WEIGHTS:
        raise ValueError("data item '%s' is not in the register" % key)
    return ITEM_WEIGHTS[key]


def owed_item_set(waivers=None):
    """Return the ordered set of items this lot owes.

    waivers maps a supporting item to the project acceptance reference that
    dropped it. A core item, an unregistered item or a waiver with no
    recorded acceptance behind it is refused.
    """
    dropped = {}
    if waivers is not None:
        if not isinstance(waivers, dict):
            raise ValueError("waivers must be a mapping of item to acceptance record")
        for item, acceptance in waivers.items():
            key = _validate_text(item, "waived item").lower()
            if key not in REGISTERED_ITEMS:
                raise ValueError("waived item '%s' is not in the register" % key)
            if key in CORE_ITEMS:
                raise ValueError(
                    "core item '%s' cannot be waived at any class" % key
                )
            dropped[key] = _validate_text(
                acceptance, "acceptance record for '%s'" % key
            )
    owed = list(CORE_ITEMS)
    owed.extend(name for name in SUPPORTING_ITEMS if name not in dropped)
    return owed


def validate_delivered_items(records, owed):
    """Validate the delivered records against the owed set.

    Each record carries an item name, a provenance, the lot reference it is
    offered against and an issue reference.
    """
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of delivered item records")
    if not isinstance(owed, (list, tuple)) or not owed:
        raise ValueError("owed must be a non-empty sequence of item names")
    cleaned = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each delivered record must be a mapping")
        for key in ("item", "provenance", "lot_reference", "issue"):
            if key not in record:
                raise ValueError("delivered record missing required key '%s'" % key)
        name = _validate_text(record["item"], "item").lower()
        if name not in REGISTERED_ITEMS:
            raise ValueError("delivered item '%s' is not in the register" % name)
        if name in cleaned:
            raise ValueError("data item '%s' is delivered twice" % name)
        provenance = _validate_text(record["provenance"], "provenance").lower()
        if provenance != UNFRANCHISED_SOURCE and provenance not in PROVENANCE_CREDIT:
            raise ValueError("provenance '%s' is not in the register" % provenance)
        cleaned[name] = {
            "item": name,
            "provenance": provenance,
            "lot_reference": record["lot_reference"],
            "issue": record["issue"],
        }
    unowed = sorted(set(cleaned) - set(owed))
    missing = [name for name in owed if name not in cleaned]
    return {"records": cleaned, "unowed": unowed, "missing": missing}


def dispose_item(record, identity, policy=None):
    """Return the disposition and credit of one delivered item."""
    policy = validate_delivery_policy(
        DEFAULT_DELIVERY_POLICY if policy is None else policy
    )
    if record is None:
        return {"disposition": DISPOSITION_ABSENT, "credit": 0.0}
    if not isinstance(identity, dict) or "reference" not in identity:
        raise ValueError("identity must be a lot identity mapping")
    provenance = record["provenance"]
    if provenance == UNFRANCHISED_SOURCE:
        return {"disposition": DISPOSITION_UNFRANCHISED, "credit": 0.0}
    issue = record["issue"]
    if not isinstance(issue, str) or not issue.strip():
        return {"disposition": DISPOSITION_UNIDENTIFIED, "credit": 0.0}
    reference = record["lot_reference"]
    if not isinstance(reference, str) or reference.strip() != identity["reference"]:
        return {"disposition": DISPOSITION_LOT_MISMATCH, "credit": 0.0}
    credit = provenance_credit(provenance)
    if credit >= 1.0:
        return {"disposition": DISPOSITION_IN_FULL, "credit": credit}
    if credit <= 0.0:
        return {"disposition": DISPOSITION_ABSENT, "credit": 0.0}
    return {"disposition": DISPOSITION_REDUCED, "credit": credit}


def weighted_completeness(credits, owed):
    """Return the provenance-weighted completeness over the owed set.

    The denominator is the whole owed set, so an item delivered as nothing
    lowers the fraction rather than dropping out of it. Dropping an item
    legitimately is a waiver, and a waiver leaves the owed set before this
    point.
    """
    if not isinstance(credits, dict):
        raise ValueError("credits must be a mapping of item to credit")
    if not isinstance(owed, (list, tuple)) or not owed:
        raise ValueError("owed must be a non-empty sequence of item names")
    total = 0.0
    earned = 0.0
    for name in owed:
        weight = item_weight(name)
        total += weight
        credit = credits.get(name, 0.0)
        if not isinstance(credit, (int, float)) or isinstance(credit, bool):
            raise ValueError("credit for '%s' must be a real number" % name)
        credit = float(credit)
        if credit < 0.0 or credit > 1.0:
            raise ValueError(
                "credit for '%s' must lie between zero and unity, got %g"
                % (name, credit)
            )
        earned += weight * credit
    if total <= 0.0:
        raise ValueError("the owed set carries no weight")
    return earned / total


def meets_floor(value, floor):
    """True when a fraction reaches its floor, boundary included."""
    number = _validate_fraction(value, "value")
    limit = _validate_fraction(floor, "floor")
    return _at_or_above(number, limit)


def assess_data_package(case, policy=None):
    """Run the clause 6.3.11 receiving assessment for one delivered folder.

    case keys: lot_identifier, date_code, delivered_items, waivers.
    """
    policy = validate_delivery_policy(
        DEFAULT_DELIVERY_POLICY if policy is None else policy
    )
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("lot_identifier", "date_code", "delivered_items", "waivers"):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)
    identity = lot_identity(case["lot_identifier"], case["date_code"], policy)
    owed = owed_item_set(case["waivers"])
    checked = validate_delivered_items(case["delivered_items"], owed)
    findings = []
    dispositions = {}
    credits = {}
    for name in owed:
        outcome = dispose_item(checked["records"].get(name), identity, policy)
        dispositions[name] = outcome["disposition"]
        credits[name] = outcome["credit"]
    result = {
        "identity": identity["reference"],
        "owed_items": owed,
        "waived_items": sorted(case["waivers"] or {}),
        "unowed_items": checked["unowed"],
        "dispositions": dispositions,
        "credits": credits,
        "completeness": 0.0,
        "findings": findings,
    }
    if checked["unowed"]:
        findings.append(
            "the folder carries %s, which this lot does not owe; recorded, not "
            "credited" % ", ".join(checked["unowed"])
        )
    unfranchised = [
        name for name in owed if dispositions[name] == DISPOSITION_UNFRANCHISED
    ]
    if unfranchised:
        findings.append(
            "%s came from outside the franchised chain; the lot is held pending an "
            "authenticity investigation" % ", ".join(unfranchised)
        )
        result["verdict"] = PACKAGE_REFUSED_UNFRANCHISED_SOURCE
        result["accepted"] = False
        return result
    mismatched = [
        name for name in owed if dispositions[name] == DISPOSITION_LOT_MISMATCH
    ]
    if mismatched:
        findings.append(
            "%s is offered against another lot than %s"
            % (", ".join(mismatched), identity["reference"])
        )
        result["verdict"] = PACKAGE_REFUSED_LOT_MISMATCH
        result["accepted"] = False
        return result
    core_missing = [
        name
        for name in CORE_ITEMS
        if dispositions[name]
        in (DISPOSITION_ABSENT, DISPOSITION_UNIDENTIFIED)
    ]
    if core_missing:
        findings.append(
            "core item(s) %s were not delivered in any usable form"
            % ", ".join(core_missing)
        )
        result["verdict"] = PACKAGE_REFUSED_CORE_ITEM_MISSING
        result["accepted"] = False
        return result
    core_floor = float(policy["core_credit_floor"])
    undercredited = [
        name for name in CORE_ITEMS if not _at_or_above(credits[name], core_floor)
    ]
    if undercredited:
        findings.append(
            "core item(s) %s arrived below the %g credit a core item owes; published "
            "material does not stand in for them" % (", ".join(undercredited), core_floor)
        )
        result["verdict"] = PACKAGE_REFUSED_CORE_ITEM_UNDERCREDITED
        result["accepted"] = False
        return result
    completeness = weighted_completeness(credits, owed)
    result["completeness"] = completeness
    floor = float(policy["completeness_floor"])
    if not _at_or_above(completeness, floor):
        findings.append(
            "provenance-weighted completeness of %.4f is under the %g floor"
            % (completeness, floor)
        )
        result["verdict"] = PACKAGE_REFUSED_SHORT_OF_FLOOR
        result["accepted"] = False
        return result
    band_top = floor + float(policy["marginal_band"])
    if not _at_or_above(completeness, band_top):
        findings.append(
            "completeness of %.4f sits inside the marginal band above the %g floor; "
            "accept and chase the weak items" % (completeness, floor)
        )
        result["verdict"] = PACKAGE_ACCEPTED_WITH_ACTIONS
        result["accepted"] = True
        return result
    findings.append(
        "provenance-weighted completeness of %.4f meets the scope this class asks of "
        "a delivered folder" % completeness
    )
    result["verdict"] = PACKAGE_ACCEPTED
    result["accepted"] = True
    return result
