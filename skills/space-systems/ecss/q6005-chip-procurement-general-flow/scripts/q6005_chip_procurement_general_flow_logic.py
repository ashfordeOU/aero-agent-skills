"""General arrangement for procuring bare chips used inside hybrid circuits.

Anchor: ECSS-Q-ST-60-05C clause 8.1 (the overall chip procurement
arrangement, presented as an activity flow from the procurement
specification through to release of the dice to hybrid assembly).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* Buying a bare chip is an ordered set of activities, not a purchase. The
  specification is issued, a source is selected against it, the order is
  placed, the wafer lot is accepted, the dice are probed and inspected,
  traceability is recorded, the dice are packed under an inert cover, the
  delivery is inspected on receipt and only then released to assembly.
* A proposed flow is graded against that arrangement. Every mandatory
  activity must appear, every declared predecessor must exist, the graph
  must have no cycle, and for each canonical prerequisite pair the earlier
  activity must actually be reachable from the flow's own links -- two
  activities running in parallel because a link was forgotten is the defect
  this check exists to catch.
* A valid flow is then scheduled. Durations are whole working days, every
  activity starts when its last predecessor finishes, and the longest chain
  through the graph is the critical path: the activities where a day lost is
  a day lost on the delivery.
* Ownership is graded too. Each mandatory activity has a party who normally
  carries it; a deviation is reported rather than rejected, because a
  programme may legitimately move an activity between the hybrid
  manufacturer, the die supplier and the customer.
"""

from __future__ import annotations

# The canonical arrangement: each mandatory activity and the activities it
# must follow.
MANDATORY_PREREQUISITES = {
    "procurement-specification-issue": (),
    "die-source-selection": ("procurement-specification-issue",),
    "purchase-order-placement": ("die-source-selection",),
    "wafer-lot-acceptance": ("purchase-order-placement",),
    "die-electrical-probe": ("wafer-lot-acceptance",),
    "die-visual-inspection": ("die-electrical-probe",),
    "die-lot-traceability-record": ("die-visual-inspection",),
    "inert-cover-packing-and-storage": ("die-lot-traceability-record",),
    "incoming-receipt-inspection": ("inert-cover-packing-and-storage",),
    "release-to-hybrid-assembly": ("incoming-receipt-inspection",),
}

# Activities a programme may add; they are never required.
OPTIONAL_ACTIVITIES = {
    "supplier-line-audit": ("die-source-selection",),
    "die-radiation-lot-verification": ("wafer-lot-acceptance",),
    "nonconformance-disposition": ("incoming-receipt-inspection",),
}

RESPONSIBLE_PARTIES = (
    "customer",
    "die-supplier",
    "hybrid-manufacturer",
    "procurement-agent",
)

DEFAULT_OWNERS = {
    "procurement-specification-issue": "hybrid-manufacturer",
    "die-source-selection": "hybrid-manufacturer",
    "purchase-order-placement": "procurement-agent",
    "wafer-lot-acceptance": "die-supplier",
    "die-electrical-probe": "die-supplier",
    "die-visual-inspection": "die-supplier",
    "die-lot-traceability-record": "die-supplier",
    "inert-cover-packing-and-storage": "die-supplier",
    "incoming-receipt-inspection": "hybrid-manufacturer",
    "release-to-hybrid-assembly": "hybrid-manufacturer",
}


def known_activities():
    """Every activity name the arrangement recognises, mandatory or optional."""
    names = set(MANDATORY_PREREQUISITES) | set(OPTIONAL_ACTIVITIES)
    return tuple(sorted(names))


def mandatory_activities():
    """The activities a chip procurement flow cannot omit."""
    return tuple(sorted(MANDATORY_PREREQUISITES))


def canonical_prerequisites(activity):
    """Activities the arrangement expects to precede the named one."""
    if activity in MANDATORY_PREREQUISITES:
        return MANDATORY_PREREQUISITES[activity]
    if activity in OPTIONAL_ACTIVITIES:
        return OPTIONAL_ACTIVITIES[activity]
    raise ValueError(
        "unknown activity %r (known: %s)" % (activity, ", ".join(known_activities()))
    )


def default_owner(activity):
    """The party that normally carries one mandatory activity."""
    if activity not in DEFAULT_OWNERS:
        raise ValueError(
            "no default owner for %r (mandatory activities: %s)"
            % (activity, ", ".join(mandatory_activities()))
        )
    return DEFAULT_OWNERS[activity]


def normalize_activity(raw):
    """Validate one activity entry of a proposed procurement flow."""
    if not isinstance(raw, dict):
        raise ValueError("activity must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("activity")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("activity needs a non-empty name, got %r" % (name,))
    canonical_prerequisites(name)  # validation only: rejects unknown names
    duration = raw.get("duration_days")
    if isinstance(duration, bool) or not isinstance(duration, int):
        raise ValueError(
            "duration_days of %r must be a whole number of days, got %r"
            % (name, duration)
        )
    if duration <= 0:
        raise ValueError(
            "duration_days of %r must be greater than zero, got %d" % (name, duration)
        )
    owner = raw.get("owner")
    if owner not in RESPONSIBLE_PARTIES:
        raise ValueError(
            "owner of %r must be one of %s, got %r"
            % (name, ", ".join(RESPONSIBLE_PARTIES), owner)
        )
    predecessors = raw.get("predecessors", [])
    if not isinstance(predecessors, (list, tuple)):
        raise ValueError("predecessors of %r must be a list" % (name,))
    seen = []
    for ref in predecessors:
        if not isinstance(ref, str) or not ref.strip():
            raise ValueError(
                "predecessor of %r must be a non-empty string, got %r" % (name, ref)
            )
        if ref == name:
            raise ValueError("activity %r cannot precede itself" % (name,))
        if ref in seen:
            raise ValueError("activity %r repeats predecessor %r" % (name, ref))
        seen.append(ref)
    return {
        "activity": name,
        "duration_days": duration,
        "owner": owner,
        "predecessors": list(seen),
    }


def build_flow(activities):
    """Turn a list of activity entries into a validated flow graph."""
    if not isinstance(activities, (list, tuple)):
        raise ValueError(
            "activities must be a list or tuple, got %r" % (type(activities).__name__,)
        )
    if len(activities) == 0:
        raise ValueError("a procurement flow needs at least one activity")
    flow = {}
    for raw in activities:
        record = normalize_activity(raw)
        if record["activity"] in flow:
            raise ValueError("duplicate activity %r" % (record["activity"],))
        flow[record["activity"]] = record
    for record in flow.values():
        for ref in record["predecessors"]:
            if ref not in flow:
                raise ValueError(
                    "activity %r names predecessor %r which is not in the flow"
                    % (record["activity"], ref)
                )
    return flow


def topological_order(flow):
    """Activity order that respects every declared link; a cycle is rejected."""
    if not isinstance(flow, dict) or not flow:
        raise ValueError("flow must be a non-empty mapping of activity records")
    remaining = {name: set(rec["predecessors"]) for name, rec in flow.items()}
    order = []
    while remaining:
        ready = sorted(n for n, preds in remaining.items() if not preds)
        if not ready:
            raise ValueError(
                "the flow contains a cycle among: %s" % (", ".join(sorted(remaining)),)
            )
        for name in ready:
            order.append(name)
            del remaining[name]
        for preds in remaining.values():
            preds.difference_update(ready)
    return order


def reachable_from(flow, source):
    """Every activity that follows the named one through the declared links."""
    if source not in flow:
        raise ValueError("activity %r is not in the flow" % (source,))
    successors = {name: [] for name in flow}
    for name, record in flow.items():
        for ref in record["predecessors"]:
            successors[ref].append(name)
    seen = set()
    stack = list(successors[source])
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        stack.extend(successors[name])
    return seen


def schedule_flow(flow):
    """Earliest start and finish, in working days, for every activity."""
    order = topological_order(flow)
    schedule = {}
    for name in order:
        record = flow[name]
        start = 0
        for ref in record["predecessors"]:
            start = max(start, schedule[ref]["finish_day"])
        schedule[name] = {
            "start_day": start,
            "finish_day": start + record["duration_days"],
        }
    return schedule


def flow_duration_days(flow):
    """Total working days from the first activity to the last finish."""
    schedule = schedule_flow(flow)
    return max(entry["finish_day"] for entry in schedule.values())


def critical_path(flow):
    """The longest chain of activities; a day lost on it is a day delivered late."""
    schedule = schedule_flow(flow)
    total = flow_duration_days(flow)
    end = sorted(
        n for n, entry in schedule.items() if entry["finish_day"] == total
    )[0]
    path = [end]
    current = end
    while flow[current]["predecessors"]:
        driver = None
        for ref in sorted(flow[current]["predecessors"]):
            if schedule[ref]["finish_day"] == schedule[current]["start_day"]:
                driver = ref
                break
        if driver is None:
            break
        path.append(driver)
        current = driver
    path.reverse()
    return path


def audit_flow(flow):
    """Grade a built flow against the canonical arrangement."""
    if not isinstance(flow, dict) or not flow:
        raise ValueError("flow must be a non-empty mapping of activity records")
    findings = []
    for name in mandatory_activities():
        if name not in flow:
            findings.append({"activity": name, "finding": "mandatory-activity-missing"})
    for name in sorted(flow):
        for prerequisite in canonical_prerequisites(name):
            if prerequisite not in flow:
                continue
            if name not in reachable_from(flow, prerequisite):
                findings.append(
                    {
                        "activity": name,
                        "finding": "prerequisite-link-missing",
                        "prerequisite": prerequisite,
                    }
                )
    for name in sorted(flow):
        if name in DEFAULT_OWNERS and flow[name]["owner"] != DEFAULT_OWNERS[name]:
            findings.append({"activity": name, "finding": "owner-deviation"})
    return findings


def plan_chip_procurement(activities):
    """Build, grade and schedule a bare-chip procurement flow.

    The return carries the validated flow, its activity order, the per
    activity schedule in working days, the total duration, the critical path,
    the audit findings and whether the arrangement is complete.
    """
    flow = build_flow(activities)
    order = topological_order(flow)
    schedule = schedule_flow(flow)
    findings = audit_flow(flow)
    blocking = [
        f
        for f in findings
        if f["finding"] in ("mandatory-activity-missing", "prerequisite-link-missing")
    ]
    return {
        "flow": flow,
        "activity_order": order,
        "schedule": schedule,
        "total_duration_days": flow_duration_days(flow),
        "critical_path": critical_path(flow),
        "findings": findings,
        "owner_deviations": [
            f["activity"] for f in findings if f["finding"] == "owner-deviation"
        ],
        "arrangement_complete": len(blocking) == 0,
    }


def canonical_flow(duration_days=2):
    """The arrangement itself as a runnable flow, for use as a starting point."""
    if isinstance(duration_days, bool) or not isinstance(duration_days, int):
        raise ValueError(
            "duration_days must be a whole number of days, got %r" % (duration_days,)
        )
    if duration_days <= 0:
        raise ValueError("duration_days must be greater than zero")
    return [
        {
            "activity": name,
            "duration_days": duration_days,
            "owner": DEFAULT_OWNERS[name],
            "predecessors": list(MANDATORY_PREREQUISITES[name]),
        }
        for name in mandatory_activities()
    ]
