"""Reduced approval procedure for a repeat build of an approved hybrid circuit.

Anchor: ECSS-Q-ST-60-05C clause 7.3.4 (approval of recurrent hybrid circuits:
what a repeat order against an existing approval still owes, and when the
reduced procedure is no longer available).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* A repeat order rides on one earlier approval. That approval covers a part
  number, a drawing issue, a manufacturer and a production line. Any of those
  four moving means the repeat order is not the same article, and the reduced
  route does not apply.
* Continuity is a condition, not a formality. The gap in whole months between
  the approved lot and the new order must sit inside the continuity window;
  once a line has been idle longer than that, the process evidence behind the
  approval has stopped being current.
* The evidence carried forward is only as good as the lot that produced it.
  A previous lot whose defective percentage exceeded the allowable, or an
  open alert or nonconformance against the design, withdraws the credit.
* Declared changes are ranked. No change and documentation-only changes leave
  the reduced route intact; a process change keeps the route but re-opens the
  test groups touched by the changed process area; a design change ends the
  route and sends the order back to a full approval.
* The output is a route, the evidence set the order owes, the continuity gap
  that was measured, and the findings that moved it off the reduced route.
"""

from __future__ import annotations

import datetime
import math

CHANGE_RANKS = {
    "no-change": 0,
    "documentation-only": 1,
    "process-change": 2,
    "design-change": 3,
}

# Process areas a repeat order may declare, and the test groups a change in
# that area re-opens on the new lot.
PROCESS_AREA_TEST_GROUPS = {
    "die-attach": ("die-shear-strength", "thermal-cycling-endurance"),
    "wire-bonding": ("bond-pull-strength", "operating-life-endurance"),
    "sealing": ("hermeticity-and-seal", "residual-gas-and-moisture"),
    "substrate-printing": ("construction-analysis", "electrical-characterization"),
    "cleaning": ("residual-gas-and-moisture",),
    "in-process-inspection": ("construction-analysis",),
}

ROUTE_REDUCED = "recurrent-reduced-procedure"
ROUTE_PARTIAL = "recurrent-partial-requalification"
ROUTE_FULL = "full-approval-required"

BASE_EVIDENCE = (
    "change-declaration",
    "lot-acceptance-record",
    "lot-traceability-record",
)

FULL_EVIDENCE = (
    "change-declaration",
    "construction-analysis",
    "electrical-characterization",
    "full-qualification-programme",
    "lot-acceptance-record",
    "lot-traceability-record",
)

CONTINUITY_WINDOW_MONTHS = 24
DEFAULT_ALLOWABLE_DEFECTIVE_PERCENT = 10.0

# A defective percentage is a ratio of small integers scaled by a hundred; it
# can land a few units in the last place either side of a typed-in allowable.
PERCENT_TOLERANCE = 1e-9

IDENTITY_FIELDS = ("part_number", "manufacturer", "production_line")


def change_rank(kind):
    """Rank of one declared change kind; unknown kinds are rejected."""
    if kind not in CHANGE_RANKS:
        raise ValueError(
            "unknown change kind %r (known: %s)"
            % (kind, ", ".join(sorted(CHANGE_RANKS)))
        )
    return CHANGE_RANKS[kind]


def process_area_groups(area):
    """Test groups re-opened by a change in one process area."""
    if area not in PROCESS_AREA_TEST_GROUPS:
        raise ValueError(
            "unknown process area %r (known: %s)"
            % (area, ", ".join(sorted(PROCESS_AREA_TEST_GROUPS)))
        )
    return PROCESS_AREA_TEST_GROUPS[area]


def parse_date(value, label):
    """Read one ISO calendar date; anything else is rejected."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError("%s is not a valid ISO date: %s" % (label, exc))


def months_between(earlier, later):
    """Whole months from one ISO date to a later one; a reversed pair is rejected."""
    start = parse_date(earlier, "earlier date")
    end = parse_date(later, "later date")
    if end < start:
        raise ValueError("later date %s precedes earlier date %s" % (later, earlier))
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(0, months)


def defective_percent(defectives, lot_size):
    """Percentage of a lot found defective; both counts are validated."""
    for value, label in ((defectives, "defectives"), (lot_size, "lot_size")):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("%s must be a whole number, got %r" % (label, value))
        if value < 0:
            raise ValueError("%s must not be negative, got %r" % (label, value))
    if lot_size == 0:
        raise ValueError("lot_size must be greater than zero")
    if defectives > lot_size:
        raise ValueError(
            "defectives %d cannot exceed lot_size %d" % (defectives, lot_size)
        )
    return 100.0 * float(defectives) / float(lot_size)


def lot_acceptance_holds(defectives, lot_size, allowable_percent):
    """True when the previous lot stayed at or under the allowable percentage."""
    if isinstance(allowable_percent, bool) or not isinstance(
        allowable_percent, (int, float)
    ):
        raise ValueError(
            "allowable_percent must be a real number, got %r" % (allowable_percent,)
        )
    allowable = float(allowable_percent)
    if not math.isfinite(allowable) or allowable < 0.0 or allowable > 100.0:
        raise ValueError(
            "allowable_percent must be finite and within 0 to 100, got %r"
            % (allowable_percent,)
        )
    return defective_percent(defectives, lot_size) <= allowable + PERCENT_TOLERANCE


def normalize_change(raw, order_id):
    """Validate one declared change entry on a repeat order."""
    if not isinstance(raw, dict):
        raise ValueError(
            "change on %r must be a mapping, got %r" % (order_id, type(raw).__name__)
        )
    kind = raw.get("kind")
    change_rank(kind)  # validation only
    area = raw.get("area")
    if kind == "process-change":
        process_area_groups(area)  # validation only
    elif area is not None:
        process_area_groups(area)  # validation only
    return {"kind": kind, "area": area}


def normalize_order(raw):
    """Validate one repeat order and the approval it claims to ride on."""
    if not isinstance(raw, dict):
        raise ValueError("order must be a mapping, got %r" % (type(raw).__name__,))
    order_id = raw.get("order_id")
    if not isinstance(order_id, str) or not order_id.strip():
        raise ValueError("order needs a non-empty order_id, got %r" % (order_id,))
    approval = raw.get("previous_approval")
    if not isinstance(approval, dict):
        raise ValueError("previous_approval of %r must be a mapping" % (order_id,))
    current = raw.get("current_build")
    if not isinstance(current, dict):
        raise ValueError("current_build of %r must be a mapping" % (order_id,))
    for side, label in ((approval, "previous_approval"), (current, "current_build")):
        for field in IDENTITY_FIELDS + ("drawing_issue",):
            value = side.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    "%s of %r needs a non-empty %s, got %r"
                    % (label, order_id, field, value)
                )
    approved_on = parse_date(
        approval.get("approved_lot_date"), "approved_lot_date of %r" % (order_id,)
    )
    ordered_on = parse_date(
        current.get("order_date"), "order_date of %r" % (order_id,)
    )
    if ordered_on < approved_on:
        raise ValueError(
            "order %r is dated before the approval it rides on" % (order_id,)
        )
    lot_size = approval.get("lot_size")
    defectives = approval.get("lot_defectives")
    defective_percent(defectives, lot_size)  # validation only
    allowable = approval.get(
        "allowable_defective_percent", DEFAULT_ALLOWABLE_DEFECTIVE_PERCENT
    )
    lot_acceptance_holds(defectives, lot_size, allowable)  # validation only
    open_alert = raw.get("open_alert", False)
    if not isinstance(open_alert, bool):
        raise ValueError(
            "open_alert of %r must be a boolean, got %r" % (order_id, open_alert)
        )
    raw_changes = raw.get("changes", [])
    if not isinstance(raw_changes, (list, tuple)):
        raise ValueError("changes of %r must be a list" % (order_id,))
    changes = [normalize_change(c, order_id) for c in raw_changes]
    return {
        "order_id": order_id,
        "previous_approval": dict(approval),
        "current_build": dict(current),
        "approved_lot_date": approval["approved_lot_date"],
        "order_date": current["order_date"],
        "lot_size": lot_size,
        "lot_defectives": defectives,
        "allowable_defective_percent": float(allowable),
        "open_alert": open_alert,
        "changes": changes,
    }


def identity_findings(order):
    """Identity fields that moved between the approval and the repeat order."""
    record = normalize_order(order)
    findings = []
    for field in IDENTITY_FIELDS:
        if record["previous_approval"][field] != record["current_build"][field]:
            findings.append("%s-changed" % field.replace("_", "-"))
    return findings


def continuity_gap_months(order):
    """Whole months between the approved lot and the repeat order."""
    record = normalize_order(order)
    return months_between(record["approved_lot_date"], record["order_date"])


def worst_change_rank(changes):
    """Rank of the most disruptive declared change; no change ranks zero."""
    if not isinstance(changes, (list, tuple)):
        raise ValueError(
            "changes must be a list or tuple, got %r" % (type(changes).__name__,)
        )
    ranks = [change_rank(c["kind"]) for c in changes]
    return max(ranks) if ranks else 0


def reopened_test_groups(changes):
    """Test groups the declared process changes re-open, deduplicated."""
    if not isinstance(changes, (list, tuple)):
        raise ValueError(
            "changes must be a list or tuple, got %r" % (type(changes).__name__,)
        )
    groups = set()
    for change in changes:
        if change_rank(change["kind"]) == CHANGE_RANKS["process-change"]:
            groups.update(process_area_groups(change["area"]))
    return tuple(sorted(groups))


def assess_recurrent_order(order):
    """Decide the approval route for one repeat order and size what it owes."""
    record = normalize_order(order)
    findings = list(identity_findings(record))
    gap = continuity_gap_months(record)
    if gap > CONTINUITY_WINDOW_MONTHS:
        findings.append("continuity-window-exceeded")
    if not lot_acceptance_holds(
        record["lot_defectives"],
        record["lot_size"],
        record["allowable_defective_percent"],
    ):
        findings.append("previous-lot-above-allowable-defectives")
    if record["open_alert"]:
        findings.append("open-alert-against-the-design")
    rank = worst_change_rank(record["changes"])
    if rank == CHANGE_RANKS["design-change"]:
        findings.append("design-change-declared")
    issue_moved = (
        record["previous_approval"]["drawing_issue"]
        != record["current_build"]["drawing_issue"]
    )
    if issue_moved and rank <= CHANGE_RANKS["documentation-only"]:
        findings.append("drawing-issue-advanced-without-design-change")
    groups = reopened_test_groups(record["changes"])
    blocking = [f for f in findings if f != "drawing-issue-advanced-without-design-change"]
    if blocking:
        route = ROUTE_FULL
        evidence = tuple(FULL_EVIDENCE)
        owed_groups = ()
    elif groups:
        route = ROUTE_PARTIAL
        evidence = tuple(sorted(set(BASE_EVIDENCE) | set(groups)))
        owed_groups = groups
    else:
        route = ROUTE_REDUCED
        evidence = tuple(BASE_EVIDENCE)
        owed_groups = ()
    result = dict(record)
    result.update(
        {
            "route": route,
            "continuity_gap_months": gap,
            "defective_percent": defective_percent(
                record["lot_defectives"], record["lot_size"]
            ),
            "reopened_test_groups": owed_groups,
            "evidence_set": evidence,
            "findings": findings,
            "reduced_route_available": route != ROUTE_FULL,
        }
    )
    return result


def assess_order_book(orders):
    """Assess a book of repeat orders and summarise what the campaign owes.

    The return carries one record per order, a count per route, the orders
    pushed back to a full approval with their reasons, and the union of the
    test groups the partial orders re-opened.
    """
    if not isinstance(orders, (list, tuple)):
        raise ValueError(
            "orders must be a list or tuple, got %r" % (type(orders).__name__,)
        )
    if len(orders) == 0:
        raise ValueError("at least one repeat order is required")
    records = [assess_recurrent_order(o) for o in orders]
    seen = set()
    for record in records:
        if record["order_id"] in seen:
            raise ValueError("duplicate order_id %r" % (record["order_id"],))
        seen.add(record["order_id"])
    counts = {}
    for record in records:
        counts[record["route"]] = counts.get(record["route"], 0) + 1
    pushed_back = [
        {"order_id": r["order_id"], "findings": r["findings"]}
        for r in sorted(records, key=lambda r: r["order_id"])
        if not r["reduced_route_available"]
    ]
    campaign_groups = set()
    for record in records:
        campaign_groups.update(record["reopened_test_groups"])
    return {
        "records": records,
        "route_counts": counts,
        "pushed_to_full_approval": pushed_back,
        "campaign_reopened_groups": tuple(sorted(campaign_groups)),
        "all_on_reduced_route": all(
            r["route"] == ROUTE_REDUCED for r in records
        ),
    }
