"""Electronic parts in ground support equipment directly connected to Class 2 flight hardware.

Anchor: ECSS-Q-ST-60C clause 5.1.5 (electronic parts used in ground support
equipment that is directly connected to Class 2 flight hardware). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the bench topology: every node declares what it is and what it
   feeds, every downstream reference resolves, an isolation stage says whether
   it was qualified, a protective element says whether it was verified, the
   flight interface feeds nothing onward, and at least one flight interface
   exists.
2. Walk each part's downstream chain toward that interface without traversing a
   qualified isolation stage, refusing a cycle in the bench rather than walking
   it forever.
3. Grade the surviving connection by how many hops separate the part from the
   flight side: a part on the flight connector is direct, a part further back is
   indirect, a part reachable only through a qualified isolation stage sits
   outside the boundary, and a part with no chain at all was never inside it.
4. Raise the Class 2 parts-control obligations that grade earns, scaled by
   whether the part can drive the flight side or only observe it, and credit a
   verified protective element by exactly one obligation tier - never below the
   identity floor a connected part always owes.
5. Compare the evidence actually held against the obligations raised, form the
   closure fraction over in-scope parts only, and return one bench-level verdict
   with ranked findings.
"""

import math

__all__ = [
    "CLOSURE_TOLERANCE",
    "FLIGHT_INTERFACE_KIND",
    "ISOLATION_KIND",
    "PROTECTIVE_KIND",
    "BENCH_KIND",
    "NODE_KINDS",
    "MAX_TOPOLOGY_NODES",
    "DIRECT_HOP_LIMIT",
    "MANDATORY_PART_ATTRIBUTES",
    "DIRECT_SOURCING_OBLIGATIONS",
    "INDIRECT_SOURCING_OBLIGATIONS",
    "OBSERVING_OBLIGATIONS",
    "IDENTITY_FLOOR_OBLIGATIONS",
    "IN_SCOPE_STATUSES",
    "validate_node_id",
    "validate_topology",
    "connection_path",
    "boundary_status",
    "obligation_tier",
    "inherited_obligations",
    "evaluate_gse_part",
    "obligation_closure",
    "assess_gse_parts_control",
]

# Closure is a ratio of counted obligations. An exactly-met requirement can land
# a few units in the last place low; absorb the representation error here rather
# than lowering the level the project agreed.
CLOSURE_TOLERANCE = 1e-9

BENCH_KIND = "bench-node"
ISOLATION_KIND = "isolation-stage"
PROTECTIVE_KIND = "protective-element"
FLIGHT_INTERFACE_KIND = "flight-interface"
NODE_KINDS = (BENCH_KIND, ISOLATION_KIND, PROTECTIVE_KIND, FLIGHT_INTERFACE_KIND)

# A bench larger than this is a modelling error, not a long bench.
MAX_TOPOLOGY_NODES = 512

# A chain of this many hops or fewer puts the part on the flight connector.
DIRECT_HOP_LIMIT = 1

# The attributes without which a part cannot be placed on the bench at all.
MANDATORY_PART_ATTRIBUTES = (
    "part_id",
    "part_number",
    "node_id",
    "can_drive_flight_side",
)

# What a connected part owes, by what it can do to the flight side and how far
# back it sits. A part that can source into the flight hardware from the
# connector itself owes the full set; one further back owes less; one that can
# only observe still owes its identity and its lot, because a failure inside it
# can load or short the line it watches.
DIRECT_SOURCING_OBLIGATIONS = (
    "part-approval",
    "lot-traceability",
    "derating-evidence",
    "handling-and-storage-record",
)
INDIRECT_SOURCING_OBLIGATIONS = (
    "part-approval",
    "lot-traceability",
    "derating-evidence",
)
OBSERVING_OBLIGATIONS = (
    "part-approval",
    "lot-traceability",
)

# The floor a connected part never drops below, whatever credit it earns.
IDENTITY_FLOOR_OBLIGATIONS = (
    "part-approval",
    "lot-traceability",
)

# The obligation ladder, heaviest first. A verified protective element moves a
# part one rung down it and no further.
_OBLIGATION_LADDER = (
    DIRECT_SOURCING_OBLIGATIONS,
    INDIRECT_SOURCING_OBLIGATIONS,
    IDENTITY_FLOOR_OBLIGATIONS,
)

IN_SCOPE_STATUSES = ("direct", "indirect")

# Finding -> severity used to rank. Lower sorts first.
_SEVERITY = {
    "record-incomplete": 0,
    "open-obligations": 1,
    "unqualified-isolation-stage": 2,
    "unverified-protective-element": 3,
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
    """Return the validated identifier of one bench node."""
    return _require_text(value, "node id")


def validate_topology(topology):
    """Return the validated bench topology as node id -> normalized node."""
    if not isinstance(topology, dict) or not topology:
        raise ValueError("topology must be a non-empty mapping of node id -> node")
    if len(topology) > MAX_TOPOLOGY_NODES:
        raise ValueError(
            "topology declares %d nodes; more than %d is a modelling error"
            % (len(topology), MAX_TOPOLOGY_NODES)
        )

    normalized = {}
    for raw_id, node in topology.items():
        node_id = validate_node_id(raw_id)
        if node_id in normalized:
            raise ValueError("node %s is declared twice" % node_id)
        if not isinstance(node, dict):
            raise ValueError("node %s must be a mapping" % node_id)
        if "kind" not in node:
            raise ValueError("node %s does not declare a kind" % node_id)
        kind = _require_text(node["kind"], "node %s kind" % node_id).lower()
        if kind not in NODE_KINDS:
            raise ValueError(
                "node %s has unknown kind %r; known: %s"
                % (node_id, node["kind"], ", ".join(NODE_KINDS))
            )
        feeds_raw = node.get("feeds", ())
        if isinstance(feeds_raw, str) or not isinstance(feeds_raw, (list, tuple)):
            raise ValueError("node %s 'feeds' must be a sequence of node ids" % node_id)
        feeds = tuple(validate_node_id(item) for item in feeds_raw)
        if len(set(feeds)) != len(feeds):
            raise ValueError("node %s feeds the same node twice" % node_id)
        if node_id in feeds:
            raise ValueError("node %s feeds itself" % node_id)

        entry = {"kind": kind, "feeds": feeds}
        if kind == ISOLATION_KIND:
            if "qualified" not in node:
                raise ValueError(
                    "isolation stage %s does not say whether it was qualified" % node_id
                )
            entry["qualified"] = _require_bool(
                node["qualified"], "isolation stage %s 'qualified'" % node_id
            )
        if kind == PROTECTIVE_KIND:
            if "verified" not in node:
                raise ValueError(
                    "protective element %s does not say whether it was verified" % node_id
                )
            entry["verified"] = _require_bool(
                node["verified"], "protective element %s 'verified'" % node_id
            )
        if kind == FLIGHT_INTERFACE_KIND and feeds:
            raise ValueError(
                "flight interface %s feeds %s onward; the interface terminates the chain"
                % (node_id, ", ".join(feeds))
            )
        normalized[node_id] = entry

    for node_id, entry in normalized.items():
        for target in entry["feeds"]:
            if target not in normalized:
                raise ValueError(
                    "node %s feeds %s, which is not declared in the topology"
                    % (node_id, target)
                )
    if not any(
        entry["kind"] == FLIGHT_INTERFACE_KIND for entry in normalized.values()
    ):
        raise ValueError("topology declares no flight interface node")

    _refuse_cycles(normalized)
    return normalized


def _refuse_cycles(topology):
    """Raise when any downstream chain in the bench loops back on itself."""
    state = {}

    def walk(node_id, trail):
        mark = state.get(node_id)
        if mark == "done":
            return
        if mark == "open":
            loop = trail[trail.index(node_id):] + [node_id]
            raise ValueError("bench topology loops: %s" % " -> ".join(loop))
        state[node_id] = "open"
        trail.append(node_id)
        for target in topology[node_id]["feeds"]:
            walk(target, trail)
        trail.pop()
        state[node_id] = "done"

    for node_id in sorted(topology):
        walk(node_id, [])


def connection_path(topology, node_id, through_qualified_isolation=False):
    """Return the shortest downstream chain from a node to a flight interface.

    With through_qualified_isolation false a qualified isolation stage is not
    traversed, so the chain it stands on is broken. With it true the walk
    ignores the break, which is how a part is told to be isolated rather than
    simply unconnected.
    """
    validated = topology if _looks_normalized(topology) else validate_topology(topology)
    start = validate_node_id(node_id)
    if start not in validated:
        raise ValueError("part sits at node %s, which is not on the bench" % start)

    queue = [(start,)]
    seen = {start}
    while queue:
        path = queue.pop(0)
        tail = validated[path[-1]]
        if tail["kind"] == FLIGHT_INTERFACE_KIND:
            return path
        if (
            not through_qualified_isolation
            and len(path) > 1
            and tail["kind"] == ISOLATION_KIND
            and tail["qualified"]
        ):
            continue
        for target in sorted(tail["feeds"]):
            if target in seen:
                continue
            seen.add(target)
            queue.append(path + (target,))
    return ()


def _looks_normalized(topology):
    """Return whether a mapping has already been through validate_topology."""
    if not isinstance(topology, dict) or not topology:
        return False
    for entry in topology.values():
        if not isinstance(entry, dict):
            return False
        if not isinstance(entry.get("feeds"), tuple):
            return False
    return True


def boundary_status(topology, node_id):
    """Return (status, hops, path, flags) for a part sitting at one bench node."""
    validated = topology if _looks_normalized(topology) else validate_topology(topology)
    open_path = connection_path(validated, node_id, through_qualified_isolation=False)
    if open_path:
        path = open_path
        hops = len(path) - 1
        status = "direct" if hops <= DIRECT_HOP_LIMIT else "indirect"
    else:
        path = connection_path(validated, node_id, through_qualified_isolation=True)
        hops = (len(path) - 1) if path else None
        status = "isolated" if path else "outside-boundary"

    unqualified = []
    verified_protection = False
    unverified_protection = False
    for step in path[1:]:
        entry = validated[step]
        if entry["kind"] == ISOLATION_KIND and not entry["qualified"]:
            unqualified.append(step)
        elif entry["kind"] == PROTECTIVE_KIND:
            if entry["verified"]:
                verified_protection = True
            else:
                unverified_protection = True
    flags = {
        "unqualified_isolation": tuple(unqualified),
        "verified_protection": verified_protection,
        "unverified_protection": unverified_protection,
    }
    return (status, hops, path, flags)


def obligation_tier(status, can_drive_flight_side):
    """Return the rung of the obligation ladder a connection grade starts on."""
    _require_bool(can_drive_flight_side, "can_drive_flight_side")
    if status not in IN_SCOPE_STATUSES:
        return None
    if not can_drive_flight_side:
        return len(_OBLIGATION_LADDER) - 1
    return 0 if status == "direct" else 1


def inherited_obligations(status, can_drive_flight_side, verified_protection=False):
    """Return the Class 2 obligations one connected part carries."""
    _require_bool(verified_protection, "verified_protection")
    tier = obligation_tier(status, can_drive_flight_side)
    if tier is None:
        return ()
    if verified_protection:
        tier = min(tier + 1, len(_OBLIGATION_LADDER) - 1)
    return _OBLIGATION_LADDER[tier]


def _part_completeness(part):
    """Return (missing_attributes, completeness_fraction) for one bench part."""
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


def _held_evidence(part):
    """Return the obligation names the part actually holds evidence for."""
    raw = part.get("evidence_held", ())
    if isinstance(raw, str) or not isinstance(raw, (list, tuple, set, frozenset)):
        raise ValueError("part 'evidence_held' must be a sequence of obligation names")
    held = set()
    for item in raw:
        held.add(_require_text(item, "evidence item").lower())
    return held


def evaluate_gse_part(part, topology):
    """Return the control-scope record of one ground support equipment part."""
    validated = topology if _looks_normalized(topology) else validate_topology(topology)
    missing, completeness = _part_completeness(part)
    raw = part.get("part_id") if isinstance(part, dict) else None
    label = raw.strip() if isinstance(raw, str) and raw.strip() else "<unnamed>"
    record = {
        "part_id": label,
        "missing_attributes": missing,
        "completeness": completeness,
        "node_id": None,
        "status": "record-incomplete",
        "hops": None,
        "path": (),
        "unqualified_isolation": (),
        "protection": None,
        "obligations": (),
        "open_items": (),
        "in_scope": False,
        "findings": ("record-incomplete",),
    }
    if missing:
        return record

    node_id = validate_node_id(part["node_id"])
    can_drive = _require_bool(part["can_drive_flight_side"], "can_drive_flight_side")
    status, hops, path, flags = boundary_status(validated, node_id)

    record["node_id"] = node_id
    record["status"] = status
    record["hops"] = hops
    record["path"] = path
    record["unqualified_isolation"] = flags["unqualified_isolation"]
    if flags["verified_protection"]:
        record["protection"] = "verified"
    elif flags["unverified_protection"]:
        record["protection"] = "unverified"

    obligations = inherited_obligations(status, can_drive, flags["verified_protection"])
    record["obligations"] = obligations
    record["in_scope"] = status in IN_SCOPE_STATUSES

    held = _held_evidence(part)
    record["open_items"] = tuple(
        name for name in obligations if name.lower() not in held
    )

    findings = []
    if record["open_items"]:
        findings.append("open-obligations")
    if record["in_scope"] and flags["unqualified_isolation"]:
        findings.append("unqualified-isolation-stage")
    if record["in_scope"] and flags["unverified_protection"]:
        findings.append("unverified-protective-element")
    record["findings"] = tuple(findings)
    return record


def obligation_closure(records):
    """Return (closure_fraction, raised, open_count) over in-scope parts only."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence")
    raised = 0
    open_count = 0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each record must be a mapping")
        if not record.get("in_scope"):
            continue
        raised += len(record["obligations"])
        open_count += len(record["open_items"])
    if raised == 0:
        return (1.0, 0, 0)
    return ((raised - open_count) / raised, raised, open_count)


def assess_gse_parts_control(spec):
    """Run the full clause 5.1.5 Class 2 bench control-scope assessment.

    spec keys: topology (bench node map), parts (sequence of part mappings),
    optional required_closure (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("topology", "parts"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    topology = validate_topology(spec["topology"])
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

    records = []
    seen = set()
    for part in parts:
        record = evaluate_gse_part(part, topology)
        if record["part_id"] != "<unnamed>":
            if record["part_id"] in seen:
                raise ValueError("part %s appears twice on the bench" % record["part_id"])
            seen.add(record["part_id"])
        records.append(record)

    closure, raised, open_count = obligation_closure(records)

    findings = []
    for record in records:
        for finding in record["findings"]:
            findings.append(
                {
                    "severity": _SEVERITY.get(finding, 8),
                    "part_id": record["part_id"],
                    "finding": finding,
                    "detail": _finding_detail(record, finding),
                }
            )
    findings.sort(key=lambda entry: (entry["severity"], entry["part_id"], entry["finding"]))

    in_scope = tuple(sorted(r["part_id"] for r in records if r["in_scope"]))
    governing = None
    scored = [r for r in records if r["in_scope"] and r["open_items"]]
    if scored:
        governing = max(scored, key=lambda r: (len(r["open_items"]), r["part_id"]))["part_id"]

    meets = closure > required or math.isclose(
        closure, required, rel_tol=0.0, abs_tol=CLOSURE_TOLERANCE
    )
    acceptable = meets and not findings
    return {
        "records": records,
        "in_scope_parts": in_scope,
        "obligations_raised": raised,
        "obligations_open": open_count,
        "closure_fraction": closure,
        "required_closure": required,
        "meets_required_closure": meets,
        "governing_part": governing,
        "findings": findings,
        "acceptable": acceptable,
        "verdict": "accept" if acceptable else "hold",
    }


def _finding_detail(record, finding):
    """Return the human-readable reason a bench part carries one finding."""
    if finding == "record-incomplete":
        return "part lacks %s; its control scope cannot be decided" % ", ".join(
            record["missing_attributes"]
        )
    if finding == "open-obligations":
        return "%s raised, no evidence held for %s" % (
            record["status"],
            ", ".join(record["open_items"]),
        )
    if finding == "unqualified-isolation-stage":
        return "chain passes %s, which nobody qualified; it is not a boundary" % ", ".join(
            record["unqualified_isolation"]
        )
    return "chain passes a protective element nobody verified; it earns no credit"
