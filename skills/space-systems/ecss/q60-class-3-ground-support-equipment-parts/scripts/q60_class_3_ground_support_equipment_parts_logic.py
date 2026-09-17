"""Electronic parts in ground support equipment directly connected to Class 3 flight hardware.

Anchor: ECSS-Q-ST-60C clause 6.1.5 (electronic parts inside ground support
equipment that are directly connected to Class 3 flight hardware). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the bench topology. Every ground support equipment part names the
   node it connects towards, and every isolation stage names both the node it
   connects towards and the state of its own qualification.
2. Walk each part's connection chain towards the flight interface. A bench
   that loops back on itself has no walkable chain at all and is refused as an
   input error rather than quietly reported as unconnected.
3. Break the chain only where an isolation stage is itself qualified. An
   unqualified stage, and equally a stage nobody has assessed, passes the
   connection straight through and leaves everything behind it inside the
   control boundary.
4. Keep the parts whose chain reaches the flight interface. Their distance in
   hops fixes which one sits closest to the flight hardware and therefore
   governs the control scope.
5. Raise on every in-boundary part the parts-control obligations the flight
   programme carries, read back which of them are recorded closed, and return
   the closure fraction over the whole in-boundary set.
6. Return the boundary, the governing part, the closure fraction against the
   agreed level, and findings ranked worst first.
"""

import math

__all__ = [
    "CLOSURE_TOLERANCE",
    "FLIGHT_INTERFACE",
    "INHERITED_OBLIGATIONS",
    "QUALIFICATION_STATES",
    "validate_node_id",
    "normalise_qualification_state",
    "stage_breaks_chain",
    "build_topology",
    "connection_path",
    "control_boundary",
    "part_obligation_gaps",
    "obligation_closure",
    "assess_class_3_gse_part_scope",
]

# The node every walk is trying to reach.
FLIGHT_INTERFACE = "flight-interface"

# Closure is a ratio of counted obligations. An exactly-met level can land a
# few units in the last place low; absorb that here, not by moving the level.
CLOSURE_TOLERANCE = 1e-9

# Isolation stage qualification state -> does the stage break the connection.
# Only a stage whose own qualification is established breaks it. A stage that
# nobody has assessed is not evidence of isolation and must not act as one.
QUALIFICATION_STATES = {
    "qualified": True,
    "unqualified": False,
    "not-assessed": False,
}

# What the flight programme's parts control raises on a connected part.
INHERITED_OBLIGATIONS = (
    "parts-control-plan-entry",
    "declared-components-list-entry",
    "procurement-traceability",
    "incoming-inspection-record",
    "nonconformance-reporting",
)

# Disposition -> rank used to order findings. Lower sorts first.
_SEVERITY = {
    "dangling-connection": 0,
    "isolation-stage-not-assessed": 1,
    "obligations-open": 2,
    "no-obligation-record": 3,
    "outside-control-boundary": 4,
}


def _require_text(value, label):
    """Return a non-blank stripped string, or raise ValueError."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_sequence(value, label):
    """Return a list/tuple, or raise ValueError."""
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence, got %r" % (label, type(value).__name__))
    return value


def validate_node_id(value):
    """Return the validated identifier of one bench node."""
    return _require_text(value, "node identifier")


def normalise_qualification_state(value):
    """Return the lower-cased qualification state of one isolation stage."""
    state = _require_text(value, "qualification_state").lower()
    if state not in QUALIFICATION_STATES:
        raise ValueError(
            "unknown qualification_state %r; known: %s"
            % (value, ", ".join(sorted(QUALIFICATION_STATES)))
        )
    return state


def stage_breaks_chain(qualification_state):
    """Return True when an isolation stage in this state breaks the chain."""
    return QUALIFICATION_STATES[normalise_qualification_state(qualification_state)]


def build_topology(parts, stages):
    """Return (part_index, stage_index) after validating both sets."""
    parts = _require_sequence(parts, "parts")
    stages = _require_sequence(stages, "stages")
    if not parts:
        raise ValueError("parts must name at least one ground support equipment part")
    part_index = {}
    for part in parts:
        if not isinstance(part, dict):
            raise ValueError("each ground support equipment part must be a mapping")
        part_id = validate_node_id(part.get("part_id"))
        if part_id in part_index:
            raise ValueError("part %s appears twice in the bench" % part_id)
        connects_to = validate_node_id(part.get("connects_to"))
        closed = part.get("obligations_closed")
        if closed is not None:
            closed = _require_sequence(closed, "obligations_closed")
            for name in closed:
                _require_text(name, "obligation name")
        part_index[part_id] = {
            "part_id": part_id,
            "connects_to": connects_to,
            "obligations_closed": None if closed is None else tuple(closed),
        }
    stage_index = {}
    for stage in stages:
        if not isinstance(stage, dict):
            raise ValueError("each isolation stage must be a mapping")
        stage_id = validate_node_id(stage.get("stage_id"))
        if stage_id in stage_index:
            raise ValueError("isolation stage %s appears twice in the bench" % stage_id)
        if stage_id in part_index:
            raise ValueError("%s is used as both a part and an isolation stage" % stage_id)
        stage_index[stage_id] = {
            "stage_id": stage_id,
            "connects_to": validate_node_id(stage.get("connects_to")),
            "qualification_state": normalise_qualification_state(
                stage.get("qualification_state")
            ),
        }
    return (part_index, stage_index)


def connection_path(part_id, part_index, stage_index, flight_interface=FLIGHT_INTERFACE):
    """Return the walked chain of one part towards the flight interface.

    The return is a mapping carrying the ordered nodes walked, the outcome of
    the walk, the hop distance when the interface was reached, and the stage
    that broke the chain when one did. A topology that loops is an input
    error: it is refused, never reported as an unconnected part.
    """
    target = _require_text(flight_interface, "flight_interface")
    node = validate_node_id(part_id)
    if node not in part_index:
        raise ValueError("part %s is not in the bench" % node)
    walked = [node]
    seen = {node}
    current = part_index[node]["connects_to"]
    hops = 1
    while True:
        if current == target:
            walked.append(target)
            return {
                "nodes": tuple(walked),
                "outcome": "reaches-flight-interface",
                "hops": hops,
                "broken_by": None,
            }
        if current in seen:
            raise ValueError(
                "bench topology loops back on itself at node %s" % current
            )
        seen.add(current)
        walked.append(current)
        if current in stage_index:
            stage = stage_index[current]
            if QUALIFICATION_STATES[stage["qualification_state"]]:
                return {
                    "nodes": tuple(walked),
                    "outcome": "isolated",
                    "hops": None,
                    "broken_by": current,
                }
            current = stage["connects_to"]
            hops += 1
            continue
        if current in part_index:
            current = part_index[current]["connects_to"]
            hops += 1
            continue
        return {
            "nodes": tuple(walked),
            "outcome": "dangling",
            "hops": None,
            "broken_by": None,
        }


def control_boundary(part_index, stage_index, flight_interface=FLIGHT_INTERFACE):
    """Return one walk record per part, ordered by part identifier."""
    if not isinstance(part_index, dict) or not part_index:
        raise ValueError("part_index must be a non-empty mapping")
    if not isinstance(stage_index, dict):
        raise ValueError("stage_index must be a mapping")
    records = []
    for part_id in sorted(part_index):
        walk = connection_path(part_id, part_index, stage_index, flight_interface)
        unassessed = tuple(
            sorted(
                node
                for node in walk["nodes"]
                if node in stage_index
                and stage_index[node]["qualification_state"] == "not-assessed"
            )
        )
        records.append(
            {
                "part_id": part_id,
                "path": walk["nodes"],
                "outcome": walk["outcome"],
                "hops_to_interface": walk["hops"],
                "isolated_by": walk["broken_by"],
                "in_control_boundary": walk["outcome"] == "reaches-flight-interface",
                "unassessed_stages_on_path": unassessed,
            }
        )
    return tuple(records)


def part_obligation_gaps(part):
    """Return (closed, open) obligation names for one in-boundary part."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    closed = part.get("obligations_closed")
    if closed is None:
        return ((), INHERITED_OBLIGATIONS)
    recorded = set()
    for name in closed:
        text = _require_text(name, "obligation name").lower()
        if text not in INHERITED_OBLIGATIONS:
            raise ValueError(
                "unknown obligation %r; known: %s"
                % (name, ", ".join(INHERITED_OBLIGATIONS))
            )
        recorded.add(text)
    closed_names = tuple(n for n in INHERITED_OBLIGATIONS if n in recorded)
    open_names = tuple(n for n in INHERITED_OBLIGATIONS if n not in recorded)
    return (closed_names, open_names)


def obligation_closure(records, part_index):
    """Return the closed fraction of the obligations the boundary raises."""
    records = _require_sequence(records, "records")
    raised = 0
    closed = 0
    for record in records:
        if not isinstance(record, dict) or "in_control_boundary" not in record:
            raise ValueError("each record must carry 'in_control_boundary'")
        if not record["in_control_boundary"]:
            continue
        part = part_index[record["part_id"]]
        done, _open = part_obligation_gaps(part)
        raised += len(INHERITED_OBLIGATIONS)
        closed += len(done)
    if raised == 0:
        raise ValueError(
            "no part reaches the flight interface, so the boundary raises nothing"
        )
    return closed / raised


def assess_class_3_gse_part_scope(spec):
    """Run the full clause 6.1.5 control-scope assessment over one bench.

    spec keys: parts (sequence of ground support equipment part mappings),
    stages (sequence of isolation stage mappings), optional flight_interface
    (default the module constant) and optional required_closure (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("parts", "stages"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    interface = _require_text(
        spec.get("flight_interface", FLIGHT_INTERFACE), "flight_interface"
    )
    required = spec.get("required_closure", 1.0)
    if isinstance(required, bool) or not isinstance(required, (int, float)):
        raise ValueError("required_closure must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError(
            "required_closure must lie in [0, 1], got %r" % (spec["required_closure"],)
        )

    part_index, stage_index = build_topology(spec["parts"], spec["stages"])
    records = control_boundary(part_index, stage_index, interface)

    in_boundary = tuple(r["part_id"] for r in records if r["in_control_boundary"])
    if not in_boundary:
        raise ValueError(
            "no ground support equipment part reaches the flight interface; "
            "the bench as described raises no control scope"
        )

    governing = min(
        (r for r in records if r["in_control_boundary"]),
        key=lambda r: (r["hops_to_interface"], r["part_id"]),
    )["part_id"]

    findings = []
    for record in records:
        part_id = record["part_id"]
        if record["outcome"] == "dangling":
            findings.append(
                {
                    "severity": _SEVERITY["dangling-connection"],
                    "reference": part_id,
                    "disposition": "dangling-connection",
                    "detail": "the chain ends on a node the bench never declares",
                }
            )
            continue
        if not record["in_control_boundary"]:
            continue
        for stage_id in record["unassessed_stages_on_path"]:
            findings.append(
                {
                    "severity": _SEVERITY["isolation-stage-not-assessed"],
                    "reference": "%s@%s" % (part_id, stage_id),
                    "disposition": "isolation-stage-not-assessed",
                    "detail": "an unassessed stage was walked through, not treated as isolation",
                }
            )
        part = part_index[part_id]
        done, open_names = part_obligation_gaps(part)
        if part.get("obligations_closed") is None:
            findings.append(
                {
                    "severity": _SEVERITY["no-obligation-record"],
                    "reference": part_id,
                    "disposition": "no-obligation-record",
                    "detail": "a connected part carries no parts-control record at all",
                }
            )
        elif open_names:
            findings.append(
                {
                    "severity": _SEVERITY["obligations-open"],
                    "reference": part_id,
                    "disposition": "obligations-open",
                    "detail": "still open: %s" % ", ".join(open_names),
                }
            )
    findings.sort(key=lambda entry: (entry["severity"], entry["reference"]))

    closure = obligation_closure(records, part_index)
    meets = closure > required or math.isclose(
        closure, required, rel_tol=0.0, abs_tol=CLOSURE_TOLERANCE
    )
    confirmed = meets and not findings
    return {
        "records": records,
        "control_boundary": in_boundary,
        "governing_part": governing,
        "obligation_closure": closure,
        "required_closure": required,
        "findings": findings,
        "scope_confirmed": confirmed,
        "verdict": "control-scope-confirmed" if confirmed else "hold",
    }
