"""Initialisation and configuration of a simulator holding a single Schedule.

Anchor: ECSS-E-ST-40-08C clause 5.5.2 (simulator initialisation and
configuration with one Schedule). Paraphrased into an implementable
procedure; no standard text is reproduced. The clause carries four
normative items.

Procedure implemented here
--------------------------
1. The simulator walks a fixed state sequence from its creation to the
   point it is ready to run: building, connecting, initialising, standby.
   A run that skips a state, repeats one or arrives out of order is a
   sequence defect, not a shortcut.
2. Exactly one Schedule service is registered. Zero means the entry
   points have nowhere to be posted; two means the posting order between
   them is undefined and the run stops being reproducible.
3. Configuration is applied while the tree is still being built. A field
   written after the tree is published is a late write and is refused,
   because the models that already read it hold the previous value.
4. Initialisation entry points run in declared priority order, and an
   entry point that depends on another must not be posted ahead of it.
   Ties on priority fall back to declaration order so the run repeats.
"""

__all__ = [
    "NORMATIVE_ITEM_COUNT",
    "REQUIRED_STATE_SEQUENCE",
    "CONFIGURABLE_STATES",
    "NORMATIVE_ITEMS",
    "validate_state_sequence",
    "count_schedules",
    "validate_single_schedule",
    "validate_configuration_writes",
    "order_initialisation_entry_points",
    "assess_initialisation",
]

NORMATIVE_ITEM_COUNT = 4

# The states a simulator passes through between creation and the point it
# can be told to run. Publication of the model tree happens on leaving
# 'building', which is why configuration closes there.
REQUIRED_STATE_SEQUENCE = ("building", "connecting", "initialising", "standby")

# A field may only be written while the tree is not yet published.
CONFIGURABLE_STATES = ("building",)

NORMATIVE_ITEMS = (
    ("IN-01", "the simulator walks the state sequence in order, once each"),
    ("IN-02", "exactly one Schedule service is registered"),
    ("IN-03", "every configuration write lands before the tree is published"),
    ("IN-04", "initialisation entry points run in a reproducible dependency order"),
)


def _require_text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def validate_state_sequence(observed):
    """Return the findings of comparing an observed state walk with the required one."""
    if not isinstance(observed, (list, tuple)):
        raise ValueError("observed state sequence must be a list or tuple")
    if not observed:
        raise ValueError("observed state sequence must not be empty")
    walk = []
    for index, state in enumerate(observed):
        text = _require_text(state, "state[%d]" % index).lower()
        walk.append(text)
    findings = []
    unknown = [s for s in walk if s not in REQUIRED_STATE_SEQUENCE]
    if unknown:
        findings.append("state(s) outside the initialisation sequence: %s" % ", ".join(unknown))
    for state in REQUIRED_STATE_SEQUENCE:
        seen = walk.count(state)
        if seen == 0:
            findings.append("state %r was never entered" % state)
        elif seen > 1:
            findings.append("state %r was entered %d times" % (state, seen))
    positions = {}
    for index, state in enumerate(walk):
        positions.setdefault(state, index)
    ordered = [s for s in REQUIRED_STATE_SEQUENCE if s in positions]
    for i in range(1, len(ordered)):
        if positions[ordered[i]] < positions[ordered[i - 1]]:
            findings.append(
                "state %r was entered before %r" % (ordered[i], ordered[i - 1])
            )
    return {
        "walk": walk,
        "compliant": not findings,
        "findings": findings,
    }


def count_schedules(services):
    """Return how many registered services are Schedule services."""
    if not isinstance(services, (list, tuple)):
        raise ValueError("services must be a list or tuple of service records")
    total = 0
    names = []
    for index, item in enumerate(services):
        if isinstance(item, str):
            kind = _require_text(item, "services[%d]" % index).lower()
            label = kind
        elif isinstance(item, dict):
            if "kind" not in item:
                raise ValueError("services[%d] must carry a 'kind'" % index)
            kind = _require_text(item["kind"], "services[%d]['kind']" % index).lower()
            label = _require_text(item.get("name", kind), "services[%d]['name']" % index)
        else:
            raise ValueError("services[%d] must be a string or a mapping" % index)
        if kind == "schedule":
            total += 1
            names.append(label)
    return {"count": total, "names": names}


def validate_single_schedule(services):
    """Return the single-Schedule verdict for the registered service set."""
    tally = count_schedules(services)
    findings = []
    if tally["count"] == 0:
        findings.append("no Schedule service is registered; entry points have nowhere to post")
    elif tally["count"] > 1:
        findings.append(
            "%d Schedule services are registered (%s); the posting order between them is undefined"
            % (tally["count"], ", ".join(tally["names"]))
        )
    return {
        "schedule_count": tally["count"],
        "schedule_names": tally["names"],
        "compliant": not findings,
        "findings": findings,
    }


def validate_configuration_writes(writes):
    """Return the findings of grading configuration writes against publication."""
    if not isinstance(writes, (list, tuple)):
        raise ValueError("writes must be a list or tuple of configuration writes")
    findings = []
    applied = []
    late = []
    for index, item in enumerate(writes):
        if not isinstance(item, dict):
            raise ValueError("writes[%d] must be a mapping" % index)
        for key in ("field", "state"):
            if key not in item:
                raise ValueError("writes[%d] must carry '%s'" % (index, key))
        field = _require_text(item["field"], "writes[%d]['field']" % index)
        state = _require_text(item["state"], "writes[%d]['state']" % index).lower()
        if state not in REQUIRED_STATE_SEQUENCE:
            raise ValueError(
                "writes[%d] names state %r, which is not part of the sequence" % (index, state)
            )
        if state in CONFIGURABLE_STATES:
            applied.append(field)
        else:
            late.append(field)
            findings.append(
                "field %r was written in state %r, after the tree was published" % (field, state)
            )
    return {
        "applied": applied,
        "late": late,
        "compliant": not findings,
        "findings": findings,
    }


def order_initialisation_entry_points(entry_points):
    """Return the initialisation entry points in the order they must be posted."""
    if not isinstance(entry_points, (list, tuple)):
        raise ValueError("entry_points must be a list or tuple")
    if not entry_points:
        raise ValueError("entry_points must not be empty")
    records = []
    seen = set()
    for index, item in enumerate(entry_points):
        if not isinstance(item, dict):
            raise ValueError("entry_points[%d] must be a mapping" % index)
        if "name" not in item:
            raise ValueError("entry_points[%d] must carry a 'name'" % index)
        name = _require_text(item["name"], "entry_points[%d]['name']" % index)
        if name in seen:
            raise ValueError("entry point %r is declared twice" % name)
        seen.add(name)
        priority = item.get("priority", 0)
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise ValueError("entry_points[%d]['priority'] must be an integer" % index)
        depends = item.get("depends_on", ())
        if isinstance(depends, str):
            raise ValueError("entry_points[%d]['depends_on'] must be a sequence, not a string" % index)
        if not isinstance(depends, (list, tuple)):
            raise ValueError("entry_points[%d]['depends_on'] must be a sequence" % index)
        deps = [_require_text(d, "entry_points[%d] dependency" % index) for d in depends]
        records.append({
            "name": name,
            "priority": priority,
            "depends_on": deps,
            "declared": index,
        })
    for record in records:
        for dep in record["depends_on"]:
            if dep not in seen:
                raise ValueError(
                    "entry point %r depends on %r, which is not declared"
                    % (record["name"], dep)
                )
    # Deterministic topological walk: lowest priority number first, ties on
    # declaration order, and never before a dependency.
    remaining = list(records)
    done = set()
    ordered = []
    while remaining:
        ready = [r for r in remaining if all(d in done for d in r["depends_on"])]
        if not ready:
            stuck = sorted(r["name"] for r in remaining)
            raise ValueError("initialisation entry points form a dependency cycle: %s"
                             % ", ".join(stuck))
        ready.sort(key=lambda r: (r["priority"], r["declared"]))
        chosen = ready[0]
        ordered.append(chosen)
        done.add(chosen["name"])
        remaining.remove(chosen)
    return ordered


def assess_initialisation(spec):
    """Grade a simulator initialisation run against the four normative items.

    spec keys: states (required), services (required), configuration_writes,
    entry_points (required).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("states", "services", "entry_points"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    sequence = validate_state_sequence(spec["states"])
    schedule = validate_single_schedule(spec["services"])
    writes = validate_configuration_writes(spec.get("configuration_writes", ()))
    order = order_initialisation_entry_points(spec["entry_points"])
    posted = spec.get("posted_order")
    entry_findings = []
    if posted is not None:
        if not isinstance(posted, (list, tuple)):
            raise ValueError("posted_order must be a list or tuple when given")
        posted_names = [_require_text(n, "posted_order entry") for n in posted]
        expected = [r["name"] for r in order]
        if posted_names != expected:
            entry_findings.append(
                "entry points were posted as %s but the dependency order is %s"
                % (", ".join(posted_names), ", ".join(expected))
            )
    verdicts = {
        "IN-01": sequence["compliant"],
        "IN-02": schedule["compliant"],
        "IN-03": writes["compliant"],
        "IN-04": not entry_findings,
    }
    items = []
    findings = []
    detail = {
        "IN-01": sequence["findings"],
        "IN-02": schedule["findings"],
        "IN-03": writes["findings"],
        "IN-04": entry_findings,
    }
    for item_id, title in NORMATIVE_ITEMS:
        items.append({
            "id": item_id,
            "title": title,
            "status": "satisfied" if verdicts[item_id] else "violated",
            "findings": list(detail[item_id]),
        })
        findings.extend(detail[item_id])
    return {
        "items": items,
        "item_count": len(items),
        "state_sequence": sequence,
        "schedule": schedule,
        "configuration": writes,
        "entry_point_order": [r["name"] for r in order],
        "violations": [i["id"] for i in items if i["status"] == "violated"],
        "findings": findings,
        "compliant": not findings,
    }
