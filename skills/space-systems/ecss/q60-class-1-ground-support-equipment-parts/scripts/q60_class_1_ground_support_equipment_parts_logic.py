"""Electronic parts in ground support equipment directly connected to Class 1 flight hardware.

Anchor: ECSS-Q-ST-60C clause 4.1.5 (electronic parts used in ground support
equipment that is directly connected to Class 1 flight hardware). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the bench topology: every node declares what it is and what it
   feeds, references resolve, and at least one node is the flight interface.
2. Walk each part's downstream chain toward that interface, refusing a loop in
   the topology instead of walking it forever, and count the hops it takes.
3. Break the chain only at an isolation stage that is itself qualified. An
   isolation stage nobody qualified is a component on the path like any other,
   so the part behind it stays inside the boundary.
4. Give every part still inside the boundary the parts-control obligations the
   Class 1 flight programme carries, scaled by whether the part can drive the
   flight side or only observe it.
5. Compare the evidence actually held against the obligations raised, form the
   closure fraction, and return one bench-level verdict with ranked findings.
"""

import math

__all__ = [
    "CLOSURE_TOLERANCE",
    "FLIGHT_INTERFACE_KIND",
    "ISOLATION_KIND",
    "NODE_KINDS",
    "MANDATORY_PART_ATTRIBUTES",
    "SOURCING_OBLIGATIONS",
    "OBSERVING_OBLIGATIONS",
    "MAX_PATH_NODES",
    "validate_node_id",
    "validate_topology",
    "connection_path",
    "qualified_isolation_on_path",
    "unqualified_isolation_on_path",
    "inherited_obligations",
    "evaluate_part",
    "obligation_closure",
    "assess_gse_parts_control",
]

# Closure is a ratio of counted obligations. An exactly-met requirement can
# land a few ULPs low; absorb the representation error here rather than
# lowering the level the project agreed.
CLOSURE_TOLERANCE = 1e-9

FLIGHT_INTERFACE_KIND = "flight-interface"
ISOLATION_KIND = "isolation-stage"
NODE_KINDS = ("bench-node", ISOLATION_KIND, FLIGHT_INTERFACE_KIND)

# A walk longer than this is a topology error, not a long bench.
MAX_PATH_NODES = 64

# The attributes without which a part cannot be placed on the bench at all.
MANDATORY_PART_ATTRIBUTES = (
    "part_id",
    "part_number",
    "node_id",
    "can_drive_flight_side",
)

# What a connected part owes, by what it can do to the flight side. A part that
# can source into the flight hardware owes the full set; one that can only
# observe still owes its identity and its lot, because a failure inside it can
# still load or short the line it watches.
SOURCING_OBLIGATIONS = (
    "part-approval",
    "lot-traceability",
    "derating-evidence",
    "handling-and-storage-record",
)
OBSERVING_OBLIGATIONS = (
    "part-approval",
    "lot-traceability",
)

# Disposition -> severity used to rank findings. Lower sorts first.
_SEVERITY = {
    "record-incomplete": 0,
    "unknown-node": 1,
    "obligations-open": 2,
    "isolation-not-qualified": 3,
    "in-scope-closed": 9,
    "out-of-scope": 9,
}


def _require_text(value, label):
    """Return a non-blank stripped string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_bool(value, label):
    """Return a real boolean, or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_node_id(value):
    """Return the validated identifier of one bench topology node."""
    return _require_text(value, "node_id")


def validate_topology(nodes):
    """Return the node index of a validated bench topology.

    Each node: node_id, kind (one of NODE_KINDS), downstream (the node it
    feeds, or None at a terminal), and for an isolation stage a boolean
    'qualified' saying whether the stage has itself been qualified.
    """
    if not isinstance(nodes, (list, tuple)) or not nodes:
        raise ValueError("nodes must be a non-empty sequence of node mappings")
    index = {}
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("each node must be a mapping")
        node_id = validate_node_id(node.get("node_id"))
        if node_id in index:
            raise ValueError("node %s is declared twice in the topology" % node_id)
        kind = _require_text(node.get("kind"), "kind").lower()
        if kind not in NODE_KINDS:
            raise ValueError(
                "unknown node kind %r; known: %s" % (node.get("kind"), ", ".join(NODE_KINDS))
            )
        downstream = node.get("downstream")
        if kind == FLIGHT_INTERFACE_KIND:
            if downstream is not None:
                raise ValueError("the flight interface node %s must not feed onward" % node_id)
        elif downstream is not None:
            validate_node_id(downstream)
        if kind == ISOLATION_KIND:
            _require_bool(node.get("qualified"), "isolation stage 'qualified'")
        index[node_id] = {
            "node_id": node_id,
            "kind": kind,
            "downstream": downstream.strip() if isinstance(downstream, str) else None,
            "qualified": node.get("qualified") if kind == ISOLATION_KIND else None,
        }
    for node_id, node in index.items():
        target = node["downstream"]
        if target is not None and target not in index:
            raise ValueError(
                "node %s feeds %s, which is not in the topology" % (node_id, target)
            )
    if not any(node["kind"] == FLIGHT_INTERFACE_KIND for node in index.values()):
        raise ValueError("the topology declares no flight interface node")
    return index


def connection_path(node_id, topology):
    """Return the chain of node identifiers from a part's node to its terminal."""
    start = validate_node_id(node_id)
    if not isinstance(topology, dict) or not topology:
        raise ValueError("topology must be a non-empty node index")
    if start not in topology:
        raise ValueError("node %s is not in the bench topology" % start)
    path = []
    seen = set()
    current = start
    while current is not None:
        if current in seen:
            raise ValueError("bench topology loops at node %s" % current)
        if len(path) >= MAX_PATH_NODES:
            raise ValueError("bench topology chain exceeds %d nodes" % MAX_PATH_NODES)
        seen.add(current)
        path.append(current)
        current = topology[current]["downstream"]
    return tuple(path)


def qualified_isolation_on_path(path, topology):
    """Return the first qualified isolation stage on a chain, or None."""
    if not isinstance(path, (list, tuple)) or not path:
        raise ValueError("path must be a non-empty sequence of node identifiers")
    for node_id in path:
        node = topology[node_id]
        if node["kind"] == ISOLATION_KIND and node["qualified"]:
            return node_id
    return None


def unqualified_isolation_on_path(path, topology):
    """Return the isolation stages on a chain that were never qualified."""
    if not isinstance(path, (list, tuple)) or not path:
        raise ValueError("path must be a non-empty sequence of node identifiers")
    found = []
    for node_id in path:
        node = topology[node_id]
        if node["kind"] == ISOLATION_KIND and not node["qualified"]:
            found.append(node_id)
    return tuple(found)


def inherited_obligations(can_drive_flight_side):
    """Return the obligation set a connected part inherits from the programme."""
    if _require_bool(can_drive_flight_side, "can_drive_flight_side"):
        return SOURCING_OBLIGATIONS
    return OBSERVING_OBLIGATIONS


def _part_completeness(part):
    """Return (missing_attributes, completeness_fraction) for one part."""
    if not isinstance(part, dict):
        raise ValueError("each part must be a mapping, got %r" % (type(part).__name__,))
    missing = []
    for attribute in MANDATORY_PART_ATTRIBUTES:
        if attribute not in part:
            missing.append(attribute)
            continue
        value = part[attribute]
        if value is None:
            missing.append(attribute)
        elif isinstance(value, str) and not value.strip():
            missing.append(attribute)
    total = len(MANDATORY_PART_ATTRIBUTES)
    return (tuple(missing), (total - len(missing)) / total)


def evaluate_part(part, topology):
    """Return the control record of one part fitted inside the ground equipment."""
    if not isinstance(topology, dict) or not topology:
        raise ValueError("topology must be a non-empty node index")
    missing, completeness = _part_completeness(part)
    raw = part.get("part_id") if isinstance(part, dict) else None
    label = raw.strip() if isinstance(raw, str) and raw.strip() else "<unnamed>"
    record = {
        "part_id": label,
        "missing_attributes": missing,
        "completeness": completeness,
        "path": (),
        "hops_to_flight_interface": None,
        "directly_connected": False,
        "isolation_credited": None,
        "unqualified_isolation": (),
        "required_obligations": (),
        "missing_obligations": (),
        "disposition": "record-incomplete",
        "in_scope": False,
    }
    if missing:
        return record

    node_id = validate_node_id(part["node_id"])
    if node_id not in topology:
        record["disposition"] = "unknown-node"
        return record

    path = connection_path(node_id, topology)
    record["path"] = path
    terminal = topology[path[-1]]
    reaches_flight = terminal["kind"] == FLIGHT_INTERFACE_KIND
    credited = qualified_isolation_on_path(path, topology)
    record["isolation_credited"] = credited
    record["unqualified_isolation"] = unqualified_isolation_on_path(path, topology)

    if not reaches_flight or credited is not None:
        record["disposition"] = "out-of-scope"
        return record

    record["directly_connected"] = True
    record["in_scope"] = True
    record["hops_to_flight_interface"] = len(path) - 1
    required = inherited_obligations(part["can_drive_flight_side"])
    record["required_obligations"] = required

    evidence = part.get("evidence", ())
    if isinstance(evidence, (list, tuple, set, frozenset)):
        held = {str(item).strip().lower() for item in evidence if str(item).strip()}
    else:
        raise ValueError("part 'evidence' must be a sequence of obligation names")
    absent = tuple(name for name in required if name not in held)
    record["missing_obligations"] = absent
    record["disposition"] = "obligations-open" if absent else "in-scope-closed"
    return record


def obligation_closure(records):
    """Return the fraction of raised obligations that carry evidence."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of part records")
    raised = 0
    closed = 0
    for record in records:
        if not isinstance(record, dict) or "disposition" not in record:
            raise ValueError("each record must be a mapping carrying 'disposition'")
        if not record.get("in_scope"):
            continue
        required = record["required_obligations"]
        raised += len(required)
        closed += len(required) - len(record["missing_obligations"])
    if raised == 0:
        return 1.0
    return closed / raised


def assess_gse_parts_control(spec):
    """Run the full clause 4.1.5 ground support equipment parts assessment.

    spec keys: nodes (bench topology), parts (sequence of part mappings),
    optional required_closure (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("nodes", "parts"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    topology = validate_topology(spec["nodes"])
    parts = spec["parts"]
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("spec['parts'] must be a non-empty sequence")

    required = spec.get("required_closure", 1.0)
    if isinstance(required, bool) or not isinstance(required, (int, float)):
        raise ValueError("required_closure must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError(
            "required_closure must lie in [0, 1], got %r" % (spec["required_closure"],)
        )

    records = [evaluate_part(part, topology) for part in parts]
    closure = obligation_closure(records)

    findings = []
    for record in records:
        disposition = record["disposition"]
        if disposition in ("in-scope-closed", "out-of-scope"):
            pass
        else:
            findings.append(
                {
                    "severity": _SEVERITY.get(disposition, 8),
                    "part_id": record["part_id"],
                    "disposition": disposition,
                    "detail": _finding_detail(record),
                }
            )
        if record["in_scope"] and record["unqualified_isolation"]:
            findings.append(
                {
                    "severity": _SEVERITY["isolation-not-qualified"],
                    "part_id": record["part_id"],
                    "disposition": "isolation-not-qualified",
                    "detail": "chain passes %s, which was never qualified and so breaks nothing"
                    % ", ".join(record["unqualified_isolation"]),
                }
            )
    findings.sort(key=lambda entry: (entry["severity"], entry["part_id"]))

    in_scope = tuple(record["part_id"] for record in records if record["in_scope"])
    governing = None
    open_records = [r for r in records if r["in_scope"] and r["missing_obligations"]]
    if open_records:
        governing = max(
            open_records, key=lambda r: (len(r["missing_obligations"]), r["part_id"])
        )["part_id"]

    meets = closure > required or math.isclose(
        closure, required, rel_tol=0.0, abs_tol=CLOSURE_TOLERANCE
    )
    controlled = meets and not findings
    return {
        "parts_in_scope": in_scope,
        "records": records,
        "obligation_closure": closure,
        "required_closure": required,
        "governing_part": governing,
        "findings": findings,
        "controlled": controlled,
        "verdict": "accept" if controlled else "hold",
    }


def _finding_detail(record):
    """Return the human-readable reason a part is not yet controlled."""
    disposition = record["disposition"]
    if disposition == "record-incomplete":
        return "part lacks %s; it cannot be placed on the bench topology" % ", ".join(
            record["missing_attributes"]
        )
    if disposition == "unknown-node":
        return "part sits on a node that is not in the declared bench topology"
    if disposition == "obligations-open":
        return "connected part holds no evidence for %s" % ", ".join(
            record["missing_obligations"]
        )
    return "part is outside the directly connected boundary"
