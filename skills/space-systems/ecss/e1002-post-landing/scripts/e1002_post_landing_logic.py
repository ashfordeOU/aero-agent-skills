#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.4.6 post-landing verification (paraphrase,
not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): where
applicable -- i.e. for an element whose mission profile physically
returns hardware to Earth (descent capsule, sample-return canister,
recoverable payload, splashdown-recovered stage) -- the post-landing
verification stage checks each recovered item's condition against its
pre-flight baseline and closes out any requirements that could only be
verified after recovery. This module implements that applicability
check, outcome classification, and close-out gate; it does not replace
the stage-list ownership of the sibling e1002-stages leaf or the
detailed method rules of clause 5.2.2.
"""

RECOVERY_ITEM_TYPES = (
    "structure",
    "mechanisms",
    "thermal_protection_system",
    "pyrotechnics",
    "propulsion_residuals",
    "payload_or_samples",
    "data_recorder",
)

RECOVERY_STATUSES = ("recovered_intact", "recovered_degraded", "not_recovered")

VERIFICATION_OUTCOMES = ("verified", "verified_with_findings", "not_verifiable")


def is_post_landing_applicable(element):
    """Whether the clause 5.2.4.6 post-landing stage applies to this
    element: only when its mission profile physically returns hardware
    to Earth. Required key: 'returns_to_earth' (bool). Raises ValueError
    if the key is missing."""
    if "returns_to_earth" not in element:
        raise ValueError("element is missing 'returns_to_earth'")
    return bool(element["returns_to_earth"])


def build_recovery_item_list(item_types):
    """Validated, ordered list of recovery item types to verify for a
    returning element. Raises ValueError for an unknown type or a
    duplicate."""
    seen = set()
    items = []
    for item_type in item_types:
        if item_type not in RECOVERY_ITEM_TYPES:
            raise ValueError("unknown recovery item type: %r" % (item_type,))
        if item_type in seen:
            raise ValueError("duplicate recovery item type: %r" % (item_type,))
        seen.add(item_type)
        items.append(item_type)
    return items


def classify_outcome(recovery_status, baseline_match):
    """Verification outcome for one recovered item: not_recovered ->
    not_verifiable (no physical evidence; needs alternate evidence);
    recovered_degraded -> verified_with_findings regardless of
    baseline_match; recovered_intact -> verified if baseline_match else
    verified_with_findings. Raises ValueError for an unknown recovery
    status."""
    if recovery_status not in RECOVERY_STATUSES:
        raise ValueError("unknown recovery status: %r" % (recovery_status,))
    if recovery_status == "not_recovered":
        return "not_verifiable"
    if recovery_status == "recovered_degraded":
        return "verified_with_findings"
    return "verified" if baseline_match else "verified_with_findings"


def assess_item(item):
    """Assessment dict for one recovered item. Required keys: id,
    item_type, recovery_status, baseline_match. Returns a new dict; does
    not mutate the input. Raises ValueError if 'id' is missing or
    item_type is unknown."""
    if "id" not in item:
        raise ValueError("item is missing an id")
    if item["item_type"] not in RECOVERY_ITEM_TYPES:
        raise ValueError("unknown recovery item type: %r" % (item["item_type"],))
    outcome = classify_outcome(item["recovery_status"], item["baseline_match"])
    return {
        "id": item["id"],
        "item_type": item["item_type"],
        "outcome": outcome,
        "safety_critical": bool(item.get("safety_critical", False)),
    }


def build_post_landing_report(element, items):
    """Post-landing verification report for an element and its recovered
    items. If the stage is not applicable (is_post_landing_applicable is
    False), returns {"applicable": False, "assessments": []} without
    processing items. Otherwise assesses every item in input order.
    Raises ValueError on a duplicate item id."""
    applicable = is_post_landing_applicable(element)
    if not applicable:
        return {"applicable": False, "assessments": []}
    assessments = []
    seen_ids = set()
    for item in items:
        assessment = assess_item(item)
        if assessment["id"] in seen_ids:
            raise ValueError("duplicate item id: %r" % (assessment["id"],))
        seen_ids.add(assessment["id"])
        assessments.append(assessment)
    return {"applicable": True, "assessments": assessments}


def find_open_findings(assessments):
    """Item ids with outcome verified_with_findings, in assessment
    order -- recovered items whose condition needs engineering
    disposition before stage close-out."""
    return [a["id"] for a in assessments if a["outcome"] == "verified_with_findings"]


def find_unverifiable_items(assessments):
    """Item ids with outcome not_verifiable, in assessment order --
    items not physically recovered that need alternate evidence instead
    of inspection."""
    return [a["id"] for a in assessments if a["outcome"] == "not_verifiable"]


def ready_for_closeout(report, dispositioned_ids):
    """Whether the post-landing stage may be closed out: an element for
    which the stage is not applicable closes out trivially (True); an
    applicable element closes out only once every open finding and
    every unverifiable item (from find_open_findings and
    find_unverifiable_items) is present in dispositioned_ids."""
    if not report["applicable"]:
        return True
    dispositioned = set(dispositioned_ids)
    gaps = find_open_findings(report["assessments"]) + find_unverifiable_items(report["assessments"])
    return all(item_id in dispositioned for item_id in gaps)
