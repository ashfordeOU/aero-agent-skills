#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.6.9 -- control of engineering changes and
nonconformances (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): an
engineering change or a nonconformance that affects requirements or
design must have its baseline impact assessed, be routed to the right
approval authority (the configuration control board for changes, the
non-conformance review board for nonconformances, both consistent with
M-ST-40 and Q-ST-10-09), and be dispositioned before it is implemented;
if approved and it affects the baseline, the baseline is updated before
the item is closed. This module scopes only the systems-engineering
control point (impact assessment, authority routing, disposition,
implementation gate) -- it does not replace the full Q-ST-10-09
nonconformance lifecycle (detection, classification, root-cause
analysis, CAPA, closeout, database/trend analysis), which is the
sibling q1009-* leaves, nor the baseline-establishment mechanics of the
sibling e10-config-baselines leaf (10C clause 5.4.2.2).
"""

ITEM_TYPES = ("change", "nonconformance")
DISPOSITIONS = ("approved", "rejected")


def required_authority(item_type, requires_baseline_change):
    """Approval authority for an item: 'local' when it does not touch
    the baseline; otherwise 'CCB' for a change or 'NRB' for a
    nonconformance. Raises ValueError for an unknown item_type."""
    if item_type not in ITEM_TYPES:
        raise ValueError("item_type must be one of %r: %r" % (ITEM_TYPES, item_type))
    if not requires_baseline_change:
        return "local"
    return "CCB" if item_type == "change" else "NRB"


def raise_item(item_id, item_type, description, affects_requirements, affects_design):
    """Raise a new change or nonconformance item and return a new
    register record (dict). Does not mutate any input. item_id and
    description must be non-empty strings; item_type must be 'change'
    or 'nonconformance'. requires_baseline_change is derived as
    affects_requirements or affects_design, and the approval authority
    is derived from it. The record starts with status='raised' and no
    disposition."""
    if not item_id:
        raise ValueError("item_id must be non-empty")
    if not description:
        raise ValueError("description must be non-empty")
    if item_type not in ITEM_TYPES:
        raise ValueError("item_type must be one of %r: %r" % (ITEM_TYPES, item_type))
    requires_baseline_change = bool(affects_requirements or affects_design)
    return {
        "item_id": item_id,
        "item_type": item_type,
        "description": description,
        "affects_requirements": bool(affects_requirements),
        "affects_design": bool(affects_design),
        "requires_baseline_change": requires_baseline_change,
        "authority": required_authority(item_type, requires_baseline_change),
        "status": "raised",
        "disposition": None,
        "disposition_rationale": None,
        "baseline_updated": False,
    }


def disposition_item(record, decision, rationale):
    """Return a new record with the approval authority's disposition
    recorded and status set to 'dispositioned'. Does not mutate
    record. Raises ValueError if the record is not in status 'raised',
    if decision is not 'approved'/'rejected', or if rationale is
    empty."""
    if record["status"] != "raised":
        raise ValueError(
            "item %r is %r, must be 'raised' to disposition"
            % (record["item_id"], record["status"])
        )
    if decision not in DISPOSITIONS:
        raise ValueError("decision must be one of %r: %r" % (DISPOSITIONS, decision))
    if not rationale:
        raise ValueError("rationale must be non-empty")
    updated = dict(record)
    updated["disposition"] = decision
    updated["disposition_rationale"] = rationale
    updated["status"] = "dispositioned"
    return updated


def update_baseline(record):
    """Return a new record with the configuration baseline updated
    (baseline_updated=True) and status set to 'closed'. Does not
    mutate record. Only valid for a record that is 'dispositioned',
    'approved', and requires_baseline_change; raises ValueError
    otherwise, so an approved baseline-impacting item cannot be closed
    without this step."""
    if record["status"] != "dispositioned":
        raise ValueError(
            "item %r must be dispositioned before the baseline can be updated"
            % (record["item_id"],)
        )
    if record["disposition"] != "approved":
        raise ValueError(
            "item %r disposition is %r, only approved items update the baseline"
            % (record["item_id"], record["disposition"])
        )
    if not record["requires_baseline_change"]:
        raise ValueError(
            "item %r does not require a baseline change" % (record["item_id"],)
        )
    updated = dict(record)
    updated["baseline_updated"] = True
    updated["status"] = "closed"
    return updated


def close_item(record):
    """Return a new record closed without a baseline update: valid for
    a rejected item, or an approved item that does not require a
    baseline change. Does not mutate record. Raises ValueError if the
    record is not 'dispositioned', or if it is an approved
    baseline-impacting item (which must go through update_baseline
    instead)."""
    if record["status"] != "dispositioned":
        raise ValueError(
            "item %r must be dispositioned before closing" % (record["item_id"],)
        )
    if record["disposition"] == "approved" and record["requires_baseline_change"]:
        raise ValueError(
            "item %r is approved and baseline-impacting, must be closed via update_baseline"
            % (record["item_id"],)
        )
    updated = dict(record)
    updated["status"] = "closed"
    return updated


def may_implement(record):
    """True when the change or nonconformance may be implemented: the
    record is closed, was approved, and, if it required a baseline
    change, the baseline has been updated."""
    if record["status"] != "closed" or record["disposition"] != "approved":
        return False
    if record["requires_baseline_change"] and not record["baseline_updated"]:
        return False
    return True


def register_status(records):
    """(ready, open_items) across a change/nonconformance register
    (iterable of records). ready is True only when every record is
    'closed'. open_items lists the still-open records (status
    'raised' or 'dispositioned'), in input order."""
    open_items = [record for record in records if record["status"] != "closed"]
    return (not open_items, open_items)


def items_by_type(records, item_type):
    """Records in the register of one item_type ('change' or
    'nonconformance'), in input order."""
    return [record for record in records if record["item_type"] == item_type]
