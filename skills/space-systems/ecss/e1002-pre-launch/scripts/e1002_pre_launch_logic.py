#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.4.4 pre-launch readiness verification
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
pre-launch verification stage confirms, ahead of launch, that transport
did not degrade the flight hardware, that storage conditions and
life-limited items remain within qualified limits, that the launch-site
health/functional checks required before launch have all been completed
and passed, and that the as-built launch configuration matches the
qualified/accepted baseline with no open critical non-conformance. This
module implements that readiness check; it does not replace the
qualification (clause 5.2.4.2) or acceptance (clause 5.2.4.3) stages
that precede it, and it does not plan the checks themselves (see the
Verification Plan, clause 5.2.8.1).
"""

CATEGORIES = ("transport", "storage", "launch_site", "launch_configuration")


def check_transport_readiness(transport_events):
    """Transport readiness from a list of transport-event dicts, each
    with keys 'id' and 'within_limits' (bool: measured environment
    stayed inside the qualified transport envelope). Returns a dict with
    'category', 'ready' and 'blocking_reasons' (ids of out-of-limit
    events, in input order). Raises ValueError if an event is missing a
    required key."""
    blocking = []
    for event in transport_events:
        if "id" not in event or "within_limits" not in event:
            raise ValueError("transport event missing 'id' or 'within_limits': %r" % (event,))
        if not event["within_limits"]:
            blocking.append(event["id"])
    return {"category": "transport", "ready": not blocking, "blocking_reasons": blocking}


def check_storage_readiness(storage_items, as_of_date):
    """Storage readiness from a list of storage-item dicts, each with
    keys 'id', 'shelf_life_expiry' (a date-like value comparable to
    as_of_date, or None if not life-limited) and 'within_limits' (bool:
    storage environment log stayed inside qualified limits). An item
    blocks readiness if it is expired (as_of_date > shelf_life_expiry)
    or its environment was out of limits. Returns blocking_reasons in
    input order. Raises ValueError on a missing required key."""
    blocking = []
    for item in storage_items:
        if "id" not in item or "within_limits" not in item or "shelf_life_expiry" not in item:
            raise ValueError("storage item missing a required key: %r" % (item,))
        expired = item["shelf_life_expiry"] is not None and as_of_date > item["shelf_life_expiry"]
        if expired or not item["within_limits"]:
            blocking.append(item["id"])
    return {"category": "storage", "ready": not blocking, "blocking_reasons": blocking}


def check_launch_site_activities(required_checks, completed_checks):
    """Launch-site readiness: every id in required_checks must appear in
    completed_checks (dict id -> bool passed) and be True. Returns
    blocking_reasons listing missing or failed ids, in required_checks
    order. Does not mutate either input."""
    blocking = [
        check_id
        for check_id in required_checks
        if not completed_checks.get(check_id, False)
    ]
    return {"category": "launch_site", "ready": not blocking, "blocking_reasons": blocking}


def check_launch_configuration(as_built, baseline, open_nonconformances):
    """Launch-configuration readiness: as_built (dict component -> value)
    must match baseline (dict component -> expected value) for every
    baseline key, and no open_nonconformance dict (keys 'id', 'severity',
    'dispositioned') may be an un-dispositioned 'critical' item. Returns
    blocking_reasons combining mismatched component ids and blocking
    non-conformance ids, baseline order then non-conformance order. Does
    not mutate any input."""
    blocking = [
        component
        for component, expected in baseline.items()
        if as_built.get(component) != expected
    ]
    blocking.extend(
        nc["id"]
        for nc in open_nonconformances
        if nc.get("severity") == "critical" and not nc.get("dispositioned", False)
    )
    return {"category": "launch_configuration", "ready": not blocking, "blocking_reasons": blocking}


def assess_pre_launch_readiness(
    transport_events,
    storage_items,
    as_of_date,
    required_checks,
    completed_checks,
    as_built,
    baseline,
    open_nonconformances,
):
    """Combined clause 5.2.4.4 pre-launch readiness assessment across all
    four sub-areas. Returns a dict with 'go' (bool, True only if every
    category is ready) and 'categories' (list of the four per-category
    result dicts, in CATEGORIES order)."""
    categories = [
        check_transport_readiness(transport_events),
        check_storage_readiness(storage_items, as_of_date),
        check_launch_site_activities(required_checks, completed_checks),
        check_launch_configuration(as_built, baseline, open_nonconformances),
    ]
    return {"go": all(category["ready"] for category in categories), "categories": categories}
