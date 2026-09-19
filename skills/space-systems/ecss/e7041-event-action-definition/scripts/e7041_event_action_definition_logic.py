"""The event-action definition: what an on-board event is bound to.

Anchor: ECSS-E-ST-70-41C clause 6.19.4 (paraphrased into an
implementable procedure; no standard text is reproduced).

An event-action definition is the on-board table entry that says: when
this event report is generated, release this request. The clause fixes
two things about that entry, and both of them are about identity.

The event side is the key. A definition is identified by the
application process that generates the event report together with the
event's own definition identifier. Neither half identifies it alone:
two application processes can both define an event with the same
identifier and mean entirely different things, so a table keyed on the
event identifier by itself binds one application process's event to
another's action.

The action side is exactly one request. Not a list, not a sequence, not
a procedure to be assembled at release time -- one request, complete
at definition time. That is what makes the release deterministic: the
engine has nothing left to decide when the event arrives.

Two consequences fall out of those two facts and are the useful part
of this module. First, a definition whose action is itself an
event-action management request lets the table rewrite itself from
inside an event, which is how a table ends up in a state no operator
commanded. Second, if an action is known to generate an event, the
definitions form a directed graph, and a cycle in that graph is a
loop that runs until something else stops it. Both are detectable at
definition time, which is the only time they are cheap.

Stdlib only, offline, deterministic.
"""

APID_MAX = 2047
EVENT_ACTION_SERVICE_TYPE = 19

FINDING_DUPLICATE_KEY = "two-definitions-share-one-event-key"
FINDING_ACTION_NOT_SINGLE = "action-is-not-exactly-one-request"
FINDING_ACTION_MANAGES_THE_TABLE = "action-would-rewrite-the-event-action-table"
FINDING_SELF_TRIGGERING = "action-generates-the-event-that-releases-it"
FINDING_CYCLE = "definitions-form-a-release-cycle"
FINDING_TABLE_FULL = "definition-refused-because-the-table-is-full"
FINDING_ACTION_RAISES_UNDEFINED_EVENT = "action-generates-an-event-no-definition-covers"


def _apid(label, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer application process id, got %r"
                         % (label, value))
    if value < 0 or value > APID_MAX:
        raise ValueError("%s must be in [0, %d], got %d" % (label, APID_MAX, value))
    return value


def _event_definition_id(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("event definition id must be an integer, got %r" % (value,))
    if value < 0:
        raise ValueError("event definition id must not be negative, got %d" % value)
    return value


def event_key(apid, event_definition_id):
    """The two-part identity of an event: its source and its definition."""
    return (_apid("event source apid", apid), _event_definition_id(event_definition_id))


def normalise_action(action):
    """Validate the single request an event-action definition releases."""
    if isinstance(action, (list, tuple)):
        raise ValueError(
            "an event-action definition releases one request, got %d" % len(action)
        )
    if not isinstance(action, dict):
        raise ValueError("action must be a mapping describing one request")
    service_type = action.get("service_type")
    if isinstance(service_type, bool) or not isinstance(service_type, int):
        raise ValueError("action service type must be an integer, got %r" % (service_type,))
    if service_type < 1 or service_type > 255:
        raise ValueError("action service type must be in [1, 255], got %d" % service_type)
    subtype = action.get("message_subtype")
    if isinstance(subtype, bool) or not isinstance(subtype, int):
        raise ValueError("action message subtype must be an integer, got %r" % (subtype,))
    if subtype < 1 or subtype > 255:
        raise ValueError("action message subtype must be in [1, 255], got %d" % subtype)
    target = _apid("action target apid", action.get("target_apid"))
    raises = action.get("raises_event")
    if raises is not None:
        if not isinstance(raises, (list, tuple)) or len(raises) != 2:
            raise ValueError("raises_event must be an (apid, event definition id) pair")
        raises = event_key(raises[0], raises[1])
    return {
        "service_type": service_type,
        "message_subtype": subtype,
        "target_apid": target,
        "raises_event": raises,
    }


def normalise_definition(spec):
    """Validate one event-action definition and return it in canonical form."""
    if not isinstance(spec, dict):
        raise ValueError("definition must be a mapping, got %r" % (spec,))
    key = event_key(spec.get("apid"), spec.get("event_definition_id"))
    if "action" not in spec:
        raise ValueError("definition for event %s carries no action" % (key,))
    action = normalise_action(spec["action"])
    return {
        "key": key,
        "apid": key[0],
        "event_definition_id": key[1],
        "action": action,
        "enabled": bool(spec.get("enabled", False)),
    }


def build_definition_table(specs, capacity=None):
    """Build the on-board table, keyed on the two-part event identity."""
    if not isinstance(specs, (list, tuple)):
        raise ValueError("definitions must be a list")
    if capacity is not None:
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity must be a positive integer, got %r" % (capacity,))
    table = {}
    findings = []
    for spec in specs:
        definition = normalise_definition(spec)
        key = definition["key"]
        if key in table:
            findings.append({"finding": FINDING_DUPLICATE_KEY, "key": key})
            continue
        if capacity is not None and len(table) >= capacity:
            findings.append({"finding": FINDING_TABLE_FULL, "key": key})
            continue
        table[key] = definition
    return {"table": table, "findings": findings}


def check_action_scope(definition):
    """Findings about what a definition's single action is allowed to do."""
    findings = []
    action = definition["action"]
    if action["service_type"] == EVENT_ACTION_SERVICE_TYPE:
        findings.append(
            {"finding": FINDING_ACTION_MANAGES_THE_TABLE, "key": definition["key"]}
        )
    if action["raises_event"] is not None and action["raises_event"] == definition["key"]:
        findings.append({"finding": FINDING_SELF_TRIGGERING, "key": definition["key"]})
    return findings


def action_graph(table):
    """Directed edges from an event to the event its action generates."""
    if not isinstance(table, dict):
        raise ValueError("table must be a mapping of event keys to definitions")
    edges = {}
    for key, definition in table.items():
        raised = definition["action"]["raises_event"]
        edges[key] = [raised] if raised is not None else []
    return edges


def find_cycles(edges):
    """Every release cycle in the definition graph, each reported once."""
    if not isinstance(edges, dict):
        raise ValueError("edges must be a mapping")
    cycles = []
    seen = set()
    for start in sorted(edges):
        path = []
        position = {}
        node = start
        while node in edges and node not in position:
            position[node] = len(path)
            path.append(node)
            successors = edges[node]
            node = successors[0] if successors else None
            if node is None:
                break
        if node is not None and node in position:
            cycle = path[position[node]:]
            marker = frozenset(cycle)
            if marker not in seen:
                seen.add(marker)
                cycles.append(cycle)
    return cycles


def assess_event_action_definitions(specs, capacity=None):
    """Build and grade a whole event-action definition table."""
    built = build_definition_table(specs, capacity=capacity)
    table = built["table"]
    findings = list(built["findings"])
    for _, definition in sorted(table.items()):
        findings.extend(check_action_scope(definition))
    edges = action_graph(table)
    for key, successors in sorted(edges.items()):
        for raised in successors:
            if raised not in table and raised != key:
                findings.append(
                    {
                        "finding": FINDING_ACTION_RAISES_UNDEFINED_EVENT,
                        "key": key,
                        "raised": raised,
                    }
                )
    for cycle in find_cycles(edges):
        findings.append({"finding": FINDING_CYCLE, "cycle": cycle})
    return {
        "table": table,
        "keys": sorted(table),
        "definition_count": len(table),
        "enabled_count": sum(1 for d in table.values() if d["enabled"]),
        "findings": findings,
        "table_sound": not findings,
    }
