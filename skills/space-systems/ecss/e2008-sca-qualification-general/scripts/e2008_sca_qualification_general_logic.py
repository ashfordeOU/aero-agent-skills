#!/usr/bin/env python3
"""Every procurement lot of cell assemblies carries its own qualification.

Anchor: ECSS-E-ST-20-08C clause 6.4.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Qualification of solar cell assemblies is not held once for a design and
then spent across everything the supplier ships afterwards. It attaches to
the procurement lot, because the things that move between lots -- the cell
batch, the coverglass batch, the interconnector reel, the operator, the
line setting -- are exactly the things the qualification activities are
sensitive to. So each lot is asked four questions:

    evidence     does the lot declare a qualification campaign of its own,
                 or only a claim on some earlier lot's campaign
    provenance   were the coupons the campaign ran on drawn from this lot,
                 or from a lot that happens to be qualified already
    completeness is the required activity set closed, on enough coupons
    heritage     if a claim on an earlier lot is made, does the configuration
                 actually match, and does project policy admit the claim at
                 all

The procurement is then rolled up over the lots that are actually being
delivered. A lot nobody declared is worse than a lot declared and found
short, because the first one ships without anybody having looked.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CONFIGURATION_KEYS = ("supplier", "assembly_type", "process_baseline")

REQUIRED_LOT_ACTIVITIES = (
    "sca-visual-inspection",
    "sca-electrical-performance-measurement",
    "sca-adherence-measurement",
    "sca-thermal-cycling",
    "sca-humidity-exposure",
    "sca-electrostatic-discharge",
)

LOT_QUALIFIED = "lot-qualified"
LOT_NO_CAMPAIGN = "lot-no-campaign"
LOT_COUPON_PROVENANCE_MISMATCH = "lot-coupon-provenance-mismatch"
LOT_CAMPAIGN_INCOMPLETE = "lot-campaign-incomplete"

PROCUREMENT_FULLY_QUALIFIED = "procurement-fully-qualified"
PROCUREMENT_NOT_FULLY_QUALIFIED = "procurement-not-fully-qualified"

DEFAULT_LOT_QUALIFICATION_POLICY = {
    "admit_heritage_in_place_of_campaign": False,
    "min_coupons_per_lot": 3,
    "require_campaign_closed": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_lot_qualification_policy(policy):
    """Check a lot qualification policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_flag(
        "admit_heritage_in_place_of_campaign",
        policy.get("admit_heritage_in_place_of_campaign"),
    )
    _require_count("min_coupons_per_lot", policy.get("min_coupons_per_lot"), 1)
    _require_flag("require_campaign_closed", policy.get("require_campaign_closed"))
    return policy


def required_lot_activities():
    """The activity set a lot qualification campaign has to close."""
    return tuple(REQUIRED_LOT_ACTIVITIES)


def lot_configuration(lot):
    """The identity attributes a heritage claim is judged on."""
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    missing = sorted(k for k in CONFIGURATION_KEYS if k not in lot)
    if missing:
        raise ValueError("lot is missing %s" % ", ".join(missing))
    return {key: _require_text(key, lot[key]) for key in CONFIGURATION_KEYS}


def configuration_delta(lot, reference_lot):
    """Which identity attributes differ between two procurement lots."""
    left = lot_configuration(lot)
    right = lot_configuration(reference_lot)
    return sorted(key for key in CONFIGURATION_KEYS if left[key] != right[key])


def campaign_completeness(campaign, lot_id, policy=DEFAULT_LOT_QUALIFICATION_POLICY):
    """Is a declared campaign closed, on this lot's coupons, on enough of them."""
    validate_lot_qualification_policy(policy)
    if not isinstance(campaign, dict):
        raise ValueError("campaign must be a mapping, got %r" % (campaign,))
    owner = _require_text("lot_id", lot_id)
    coupon_lot = _require_text("coupon_lot_id", campaign.get("coupon_lot_id"))
    coupons = _require_count("coupon_count", campaign.get("coupon_count"), 0)
    closed = _require_flag("closed", campaign.get("closed"))
    activities = campaign.get("activities")
    if not isinstance(activities, (list, tuple)):
        raise ValueError("campaign activities must be a sequence, got %r" % (activities,))
    declared = []
    for activity in activities:
        name = _require_text("activity", activity)
        if name not in REQUIRED_LOT_ACTIVITIES:
            raise ValueError("campaign declares an unknown activity %s" % name)
        if name in declared:
            raise ValueError("campaign declares %s twice" % name)
        declared.append(name)
    missing = sorted(set(REQUIRED_LOT_ACTIVITIES) - set(declared))
    minimum = int(policy["min_coupons_per_lot"])
    enough_coupons = coupons >= minimum
    provenance_ok = coupon_lot == owner
    findings = []
    if not provenance_ok:
        findings.append(
            "the campaign ran on coupons drawn from lot %s, not from lot %s"
            % (coupon_lot, owner)
        )
    if missing:
        findings.append(
            "the campaign leaves %s unrun" % ", ".join(missing)
        )
    if not enough_coupons:
        findings.append(
            "the campaign ran on %d coupons against a required %d"
            % (coupons, minimum)
        )
    if policy["require_campaign_closed"] and not closed:
        findings.append("the campaign is still open")
    return {
        "lot_id": owner,
        "coupon_lot_id": coupon_lot,
        "coupon_count": coupons,
        "required_coupon_count": minimum,
        "declared_activities": sorted(declared),
        "missing_activities": missing,
        "coupons_sufficient": enough_coupons,
        "coupon_provenance_matches": provenance_ok,
        "closed": closed,
        "complete": not missing
        and enough_coupons
        and (closed or not policy["require_campaign_closed"]),
        "findings": findings,
    }


def heritage_admissibility(
    lot, lots_by_id, policy=DEFAULT_LOT_QUALIFICATION_POLICY
):
    """Can a claim on an earlier lot stand in for this lot's own campaign."""
    validate_lot_qualification_policy(policy)
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    if not isinstance(lots_by_id, dict):
        raise ValueError("lots_by_id must be a mapping, got %r" % (lots_by_id,))
    claimed = lot.get("heritage_lot_id")
    findings = []
    if claimed is None:
        return {
            "claimed": False,
            "heritage_lot_id": None,
            "configuration_delta": [],
            "configuration_matches": False,
            "admitted": False,
            "findings": findings,
        }
    reference_id = _require_text("heritage_lot_id", claimed)
    own_id = _require_text("lot_id", lot.get("lot_id"))
    if reference_id == own_id:
        raise ValueError("lot %s claims heritage on itself" % own_id)
    reference = lots_by_id.get(reference_id)
    if reference is None:
        findings.append(
            "lot %s claims heritage on lot %s, which the procurement does not "
            "declare" % (own_id, reference_id)
        )
        return {
            "claimed": True,
            "heritage_lot_id": reference_id,
            "configuration_delta": sorted(CONFIGURATION_KEYS),
            "configuration_matches": False,
            "admitted": False,
            "findings": findings,
        }
    delta = configuration_delta(lot, reference)
    matches = not delta
    if not matches:
        findings.append(
            "lot %s claims heritage on lot %s but differs in %s"
            % (own_id, reference_id, ", ".join(delta))
        )
    admitted = matches and bool(policy["admit_heritage_in_place_of_campaign"])
    if matches and not policy["admit_heritage_in_place_of_campaign"]:
        findings.append(
            "lot %s matches lot %s but every procurement lot owes a "
            "qualification of its own" % (own_id, reference_id)
        )
    return {
        "claimed": True,
        "heritage_lot_id": reference_id,
        "configuration_delta": delta,
        "configuration_matches": matches,
        "admitted": admitted,
        "findings": findings,
    }


def assess_procurement_lot(
    lot, lots_by_id=None, policy=DEFAULT_LOT_QUALIFICATION_POLICY
):
    """Verdict for one procurement lot of cell assemblies."""
    validate_lot_qualification_policy(policy)
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    lot_id = _require_text("lot_id", lot.get("lot_id"))
    lot_configuration(lot)
    index = {} if lots_by_id is None else lots_by_id
    heritage = heritage_admissibility(lot, index, policy)
    campaign = lot.get("campaign")
    findings = list(heritage["findings"])
    record = {
        "lot_id": lot_id,
        "configuration": lot_configuration(lot),
        "heritage": heritage,
        "campaign": None,
    }
    if campaign is None:
        record["campaign"] = None
        if heritage["admitted"]:
            record["verdict"] = LOT_QUALIFIED
        else:
            record["verdict"] = LOT_NO_CAMPAIGN
            findings.append(
                "lot %s declares no qualification campaign of its own" % lot_id
            )
    else:
        completeness = campaign_completeness(campaign, lot_id, policy)
        record["campaign"] = completeness
        findings.extend(completeness["findings"])
        if not completeness["coupon_provenance_matches"]:
            record["verdict"] = LOT_COUPON_PROVENANCE_MISMATCH
        elif not completeness["complete"]:
            record["verdict"] = LOT_CAMPAIGN_INCOMPLETE
        else:
            record["verdict"] = LOT_QUALIFIED
    record["qualified"] = record["verdict"] == LOT_QUALIFIED
    record["findings"] = findings
    return record


def assess_procurement_qualification(case, policy=DEFAULT_LOT_QUALIFICATION_POLICY):
    """Full clause 6.4.1 sweep over the lots a procurement delivers."""
    validate_lot_qualification_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    lots = case.get("lots")
    if not isinstance(lots, (list, tuple)) or not lots:
        raise ValueError("case lots must be a non-empty sequence of mappings")
    index = {}
    for lot in lots:
        if not isinstance(lot, dict):
            raise ValueError("lot must be a mapping, got %r" % (lot,))
        lot_id = _require_text("lot_id", lot.get("lot_id"))
        if lot_id in index:
            raise ValueError("case declares lot %s twice" % lot_id)
        index[lot_id] = lot
    delivered = case.get("delivered_lot_ids")
    if delivered is None:
        delivered_ids = sorted(index)
    else:
        if not isinstance(delivered, (list, tuple)) or not delivered:
            raise ValueError(
                "case delivered_lot_ids must be a non-empty sequence when given"
            )
        delivered_ids = sorted({_require_text("delivered lot id", d) for d in delivered})
    records = [assess_procurement_lot(index[lot_id], index, policy) for lot_id in sorted(index)]
    findings = []
    for record in records:
        findings.extend(record["findings"])
    undeclared = sorted(set(delivered_ids) - set(index))
    for lot_id in undeclared:
        findings.append(
            "lot %s is delivered but the procurement declares no qualification "
            "status for it at all" % lot_id
        )
    considered = [record for record in records if record["lot_id"] in delivered_ids]
    qualified = [record["lot_id"] for record in considered if record["qualified"]]
    grouped = {}
    for record in records:
        grouped.setdefault(record["verdict"], []).append(record["lot_id"])
    total = len(delivered_ids)
    coverage = len(qualified) / float(total) if total else 0.0
    open_lots = sorted(
        set(undeclared)
        | {record["lot_id"] for record in considered if not record["qualified"]}
    )
    return {
        "verdict": PROCUREMENT_FULLY_QUALIFIED
        if not open_lots
        else PROCUREMENT_NOT_FULLY_QUALIFIED,
        "lot_records": records,
        "grouped_by_verdict": grouped,
        "delivered_lot_ids": delivered_ids,
        "undeclared_lot_ids": undeclared,
        "qualified_lot_ids": sorted(qualified),
        "open_lot_ids": open_lots,
        "qualified_fraction": coverage,
        "every_lot_qualified": _at_least(coverage, 1.0) and not undeclared,
        "findings": findings,
    }
