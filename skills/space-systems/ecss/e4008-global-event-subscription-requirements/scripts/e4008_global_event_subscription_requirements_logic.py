"""Grading of global event subscriptions made by a simulation configuration.

Anchor: ECSS-E-ST-40-08 clause 5.2.5.2 (global event subscription requirements
-- the three obligations a subscription entered by the configuration has to
meet). Paraphrased into an implementable procedure; no standard text is
reproduced.

A global event is raised by the simulation environment rather than by any one
model, so a subscription wires an environment-owned event to a model-owned
entry point. The three items below are what makes that wiring well formed, and
the resulting dispatch plan -- who is called, in what order, for each event --
is what the configuration is actually producing.

The three normative items implemented here
------------------------------------------
a. The named global event is one the simulation environment publishes, and it
   is open to subscription.
b. The named entry point is published by the target instance and takes no
   arguments: a global event carries no payload, so anything with an argument
   list cannot be dispatched to.
c. The same entry point is not subscribed to the same event twice. A repeated
   subscription either double-dispatches or is silently dropped, and which of
   the two happens is not something the configuration determines.
"""

__all__ = [
    "NORMATIVE_ITEMS",
    "NORMATIVE_ITEM_COUNT",
    "build_event_registry",
    "build_instance_registry",
    "subscription_key",
    "assess_subscription",
    "build_dispatch_plan",
    "assess_global_event_subscriptions",
]

NORMATIVE_ITEMS = (
    "global-event-published-and-open-to-subscription",
    "entry-point-published-and-argument-free",
    "subscription-not-duplicated",
)
NORMATIVE_ITEM_COUNT = len(NORMATIVE_ITEMS)


def _require_text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty or blank" % label)
    return text


def build_event_registry(global_events):
    """Return a {name: declaration} registry of the environment's global events."""
    if not isinstance(global_events, (list, tuple)):
        raise ValueError("global_events must be a sequence of declarations")
    if not global_events:
        raise ValueError("the environment must publish at least one global event")
    registry = {}
    for position, declaration in enumerate(global_events):
        if not isinstance(declaration, dict):
            raise ValueError("global_events[%d] must be a mapping" % position)
        name = _require_text(declaration.get("name"), "global_events[%d]['name']" % position)
        if name in registry:
            raise ValueError("global event %r is published twice" % name)
        subscribable = declaration.get("subscribable", True)
        if not isinstance(subscribable, bool):
            raise ValueError("global event %r 'subscribable' must be a boolean" % name)
        record = dict(declaration)
        record.update({"name": name, "subscribable": subscribable})
        registry[name] = record
    return registry


def build_instance_registry(instances):
    """Return a {path: {entry point name: declaration}} registry."""
    if not isinstance(instances, (list, tuple)):
        raise ValueError("instances must be a sequence of instance declarations")
    if not instances:
        raise ValueError("the configuration must hold at least one instance")
    registry = {}
    for position, declaration in enumerate(instances):
        if not isinstance(declaration, dict):
            raise ValueError("instances[%d] must be a mapping" % position)
        path = _require_text(declaration.get("path"), "instances[%d]['path']" % position)
        if path in registry:
            raise ValueError("instance %r is declared twice" % path)
        entry_points = declaration.get("entry_points", [])
        if not isinstance(entry_points, (list, tuple)):
            raise ValueError("instance %r entry_points must be a sequence" % path)
        by_name = {}
        for order, entry in enumerate(entry_points):
            if not isinstance(entry, dict):
                raise ValueError("instance %r entry point %d must be a mapping" % (path, order))
            name = _require_text(entry.get("name"), "instance %r entry point name" % path)
            if name in by_name:
                raise ValueError("instance %r declares entry point %r twice" % (path, name))
            arity = entry.get("arity", 0)
            if not isinstance(arity, int) or isinstance(arity, bool) or arity < 0:
                raise ValueError(
                    "instance %r entry point %r arity must be a non-negative integer"
                    % (path, name)
                )
            published = entry.get("published", True)
            if not isinstance(published, bool):
                raise ValueError(
                    "instance %r entry point %r 'published' must be a boolean" % (path, name)
                )
            record = dict(entry)
            record.update({"name": name, "arity": arity, "published": published})
            by_name[name] = record
        registry[path] = by_name
    return registry


def subscription_key(event, instance, entry_point):
    """Return the canonical key identifying one subscription."""
    return "%s->%s.%s" % (
        _require_text(event, "event"),
        _require_text(instance, "instance"),
        _require_text(entry_point, "entry point"),
    )


def assess_subscription(subscription, events, instances, seen=None):
    """Grade one global event subscription against the three clause 5.2.5.2 items."""
    if not isinstance(subscription, dict):
        raise ValueError("subscription must be a mapping")
    for key in ("event", "instance", "entry_point"):
        if key not in subscription:
            raise ValueError("subscription is missing required key '%s'" % key)
    if not isinstance(events, dict) or not events:
        raise ValueError("events must be the registry returned by build_event_registry")
    if not isinstance(instances, dict) or not instances:
        raise ValueError(
            "instances must be the registry returned by build_instance_registry"
        )
    if seen is None:
        seen = set()
    if not isinstance(seen, set):
        raise ValueError("seen must be a set of subscription keys")

    event = _require_text(subscription["event"], "subscription['event']")
    path = _require_text(subscription["instance"], "subscription['instance']")
    entry_name = _require_text(subscription["entry_point"], "subscription['entry_point']")

    items = {key: True for key in NORMATIVE_ITEMS}
    findings = []

    declaration = events.get(event)
    if declaration is None:
        items[NORMATIVE_ITEMS[0]] = False
        findings.append("the environment publishes no global event named %r" % event)
    elif not declaration["subscribable"]:
        items[NORMATIVE_ITEMS[0]] = False
        findings.append("global event %r is published but is not open to subscription" % event)

    entry_points = instances.get(path)
    if entry_points is None:
        items[NORMATIVE_ITEMS[1]] = False
        findings.append("the configuration holds no instance at %r" % path)
    else:
        entry = entry_points.get(entry_name)
        if entry is None:
            items[NORMATIVE_ITEMS[1]] = False
            findings.append(
                "instance %r publishes no entry point %r" % (path, entry_name)
            )
        elif not entry["published"]:
            items[NORMATIVE_ITEMS[1]] = False
            findings.append(
                "entry point %r of instance %r is not published" % (entry_name, path)
            )
        elif entry["arity"] != 0:
            items[NORMATIVE_ITEMS[1]] = False
            findings.append(
                "entry point %r of instance %r takes %d arguments; a global event "
                "carries no payload" % (entry_name, path, entry["arity"])
            )

    key = subscription_key(event, path, entry_name)
    if key in seen:
        items[NORMATIVE_ITEMS[2]] = False
        findings.append("subscription %s is entered more than once" % key)
    else:
        seen.add(key)

    satisfied = sum(1 for ok in items.values() if ok)
    return {
        "event": event,
        "instance": path,
        "entry_point": entry_name,
        "key": key,
        "items": items,
        "findings": findings,
        "satisfied": satisfied,
        "compliant": satisfied == NORMATIVE_ITEM_COUNT,
    }


def build_dispatch_plan(records):
    """Return {event: [instance.entry_point]} for the compliant subscriptions.

    Subscribers keep the order the configuration entered them in, which is
    what makes the dispatch order reproducible from the document alone.
    """
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of subscription records")
    plan = {}
    for position, record in enumerate(records):
        if not isinstance(record, dict) or "compliant" not in record:
            raise ValueError("records[%d] is not a subscription record" % position)
        if not record["compliant"]:
            continue
        target = "%s.%s" % (record["instance"], record["entry_point"])
        plan.setdefault(record["event"], []).append(target)
    return plan


def assess_global_event_subscriptions(spec):
    """Run the clause 5.2.5.2 assessment over a configuration's subscriptions.

    spec keys: 'global_events', 'instances', 'subscriptions'.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("global_events", "instances", "subscriptions"):
        if key not in spec:
            raise ValueError("spec is missing required key '%s'" % key)
    subscriptions = spec["subscriptions"]
    if not isinstance(subscriptions, (list, tuple)):
        raise ValueError("spec['subscriptions'] must be a sequence")
    if not subscriptions:
        raise ValueError("spec['subscriptions'] must hold at least one subscription")
    events = build_event_registry(spec["global_events"])
    instances = build_instance_registry(spec["instances"])

    seen = set()
    records = [assess_subscription(s, events, instances, seen) for s in subscriptions]
    findings = []
    for record in records:
        findings.extend(record["findings"])
    satisfied = sum(r["satisfied"] for r in records)
    plan = build_dispatch_plan(records)
    return {
        "records": records,
        "subscription_count": len(records),
        "item_count": NORMATIVE_ITEM_COUNT,
        "satisfied": satisfied,
        "graded": NORMATIVE_ITEM_COUNT * len(records),
        "dispatch_plan": plan,
        "subscribed_event_count": len(plan),
        "findings": findings,
        "compliant": all(r["compliant"] for r in records),
    }
