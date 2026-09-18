"""Undervoltage action on both limiter switches through independent memory.

Anchor: ECSS-E-ST-20-20C clause 5.2.13.5.1 (the undervoltage protection opens
the main switch and the extra switch of a current limiter, each open state
held in its own memory cell). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
A limiter is modelled as two series switches -- the main switch and the extra
switch -- each reached by an ordered command path. A path element carries an
identifier and a kind:

* ``sense``  -- the undervoltage detection that raises the off command. One
  detection function serving both switches is the normal architecture, so a
  shared sense element is reported rather than graded as a defect here; the
  redundancy of the detection chain itself belongs to the shared-protection
  clause, not to this one.
* ``memory`` -- the cell that holds the switch off once the command has been
  raised. This clause asks for one such cell per switch, so a memory element
  appearing in both paths is the defect the walk is looking for.
* ``drive``  -- the stage between the memory cell and the switch. Sharing it
  puts both switches behind one part again, which undoes the independence the
  separate cells were supposed to buy.

Three questions are answered:

1. Does the protection reach both switches at all? Both roles have to be
   declared and each has to have an intact path with no failure injected.
2. Is each switch's open state actually held? A path with no memory element,
   or with a cell declared not to hold state, releases the switch as soon as
   the command drops.
3. Are the two memories independent? Any element shared between the paths is
   collected; a shared memory or drive element is a finding, and a single
   failure walk names, element by element, which switches stay closed.

The architecture is conformant only when both switches are reached, both hold
their open state, and no memory or drive element is common to the two paths.
"""

__all__ = [
    "ELEMENT_KINDS",
    "SHAREABLE_KINDS",
    "REQUIRED_SWITCH_ROLES",
    "validate_protection",
    "path_ids",
    "memory_cells",
    "holds_open_state",
    "switch_opens",
    "shared_elements",
    "single_failure_points",
    "assess_undervoltage_both_switches",
]

# The kinds an element of a command path may declare.
ELEMENT_KINDS = ("sense", "memory", "drive")

# Kinds the two paths may legitimately hold in common. The detection function
# is one function; the memory and the drive behind it are not.
SHAREABLE_KINDS = ("sense",)

# The clause names two switches; both have to be declared for the walk.
REQUIRED_SWITCH_ROLES = ("main", "extra")


def _identifier(value, label):
    """Return a non-empty identifier string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def validate_protection(spec):
    """Return the protection as (unit, switches), or raise on a bad spec.

    spec keys: unit (name), switches (sequence of mappings with role, name and
    path; a path element is a mapping with id, kind and, on a memory element,
    an optional holds_state flag).
    """
    if not isinstance(spec, dict):
        raise ValueError("protection spec must be a mapping")
    for key in ("unit", "switches"):
        if key not in spec:
            raise ValueError("protection spec missing required key '%s'" % key)

    unit = _identifier(spec["unit"], "unit")

    raw_switches = spec["switches"]
    if not isinstance(raw_switches, (list, tuple)) or not raw_switches:
        raise ValueError("switches must be a non-empty sequence")

    by_role = {}
    kind_of = {}
    for i, item in enumerate(raw_switches):
        if not isinstance(item, dict):
            raise ValueError("switches[%d] must be a mapping" % i)
        for key in ("role", "name", "path"):
            if key not in item:
                raise ValueError("switches[%d] missing required key '%s'" % (i, key))
        role = _identifier(item["role"], "switches[%d]['role']" % i)
        if role not in REQUIRED_SWITCH_ROLES:
            raise ValueError(
                "switch role %r is not one of %s" % (role, ", ".join(REQUIRED_SWITCH_ROLES))
            )
        if role in by_role:
            raise ValueError("switch role %r is declared twice" % role)
        name = _identifier(item["name"], "switches[%d]['name']" % i)

        raw_path = item["path"]
        if not isinstance(raw_path, (list, tuple)) or not raw_path:
            raise ValueError("switch %r needs a non-empty command path" % name)
        path = []
        seen_ids = []
        for j, element in enumerate(raw_path):
            if not isinstance(element, dict):
                raise ValueError("switch %r path[%d] must be a mapping" % (name, j))
            for key in ("id", "kind"):
                if key not in element:
                    raise ValueError(
                        "switch %r path[%d] missing required key '%s'" % (name, j, key)
                    )
            element_id = _identifier(element["id"], "switch %r path[%d]['id']" % (name, j))
            if element_id in seen_ids:
                raise ValueError(
                    "element %r is listed twice in the path of switch %r" % (element_id, name)
                )
            seen_ids.append(element_id)
            kind = _identifier(element["kind"], "switch %r path[%d]['kind']" % (name, j))
            if kind not in ELEMENT_KINDS:
                raise ValueError(
                    "element %r declares kind %r, not one of %s"
                    % (element_id, kind, ", ".join(ELEMENT_KINDS))
                )
            if kind_of.setdefault(element_id, kind) != kind:
                raise ValueError(
                    "element %r is declared as %r in one path and %r in the other"
                    % (element_id, kind_of[element_id], kind)
                )
            holds = element.get("holds_state", True)
            if not isinstance(holds, bool):
                raise ValueError(
                    "element %r holds_state must be a boolean, got %r" % (element_id, holds)
                )
            if kind != "memory" and "holds_state" in element:
                raise ValueError(
                    "element %r is a %s element; holds_state belongs on a memory cell"
                    % (element_id, kind)
                )
            path.append({"id": element_id, "kind": kind, "holds_state": holds})
        by_role[role] = {"role": role, "name": name, "path": path}

    missing = [role for role in REQUIRED_SWITCH_ROLES if role not in by_role]
    if missing:
        raise ValueError(
            "protection spec declares no %s switch" % " or no ".join(missing)
        )
    return (unit, [by_role[role] for role in REQUIRED_SWITCH_ROLES])


def path_ids(switch):
    """Return the element identifiers of one switch's command path."""
    return [element["id"] for element in switch["path"]]


def memory_cells(switch):
    """Return the memory elements of one switch's command path."""
    return [element for element in switch["path"] if element["kind"] == "memory"]


def holds_open_state(switch):
    """Return True when the switch has at least one cell that holds it off."""
    cells = memory_cells(switch)
    if not cells:
        return False
    return all(cell["holds_state"] for cell in cells)


def switch_opens(switch, failed_ids=()):
    """Return True when the off command still reaches the switch."""
    failed = set(failed_ids)
    return not any(element_id in failed for element_id in path_ids(switch))


def shared_elements(switches):
    """Return the elements common to more than one command path."""
    seen = {}
    order = []
    for switch in switches:
        for element in switch["path"]:
            entry = seen.get(element["id"])
            if entry is None:
                entry = {"id": element["id"], "kind": element["kind"], "roles": []}
                seen[element["id"]] = entry
                order.append(entry)
            entry["roles"].append(switch["role"])
    return [entry for entry in order if len(entry["roles"]) > 1]


def single_failure_points(switches):
    """Return, per element, the switch roles that stay closed when it fails."""
    order = []
    kinds = {}
    for switch in switches:
        for element in switch["path"]:
            if element["id"] not in kinds:
                kinds[element["id"]] = element["kind"]
                order.append(element["id"])
    points = []
    for element_id in order:
        blocked = [
            switch["role"]
            for switch in switches
            if not switch_opens(switch, {element_id})
        ]
        if blocked:
            points.append(
                {"element": element_id, "kind": kinds[element_id], "roles_blocked": blocked}
            )
    return points


def assess_undervoltage_both_switches(spec):
    """Assess a limiter undervoltage action against clause 5.2.13.5.1."""
    unit, switches = validate_protection(spec)

    findings = []
    notes = []

    reached = [switch["role"] for switch in switches if switch_opens(switch)]
    acts_on_both = len(reached) == len(REQUIRED_SWITCH_ROLES)

    for switch in switches:
        cells = memory_cells(switch)
        if not cells:
            findings.append(
                "the %s switch %s has no memory cell, so its open state is not held"
                % (switch["role"], switch["name"])
            )
            continue
        released = [cell["id"] for cell in cells if not cell["holds_state"]]
        if released:
            findings.append(
                "memory cell %s of the %s switch %s does not hold the open state"
                % ("/".join(released), switch["role"], switch["name"])
            )

    shared = shared_elements(switches)
    shared_memory = [entry for entry in shared if entry["kind"] == "memory"]
    shared_drive = [entry for entry in shared if entry["kind"] == "drive"]
    shared_sense = [entry for entry in shared if entry["kind"] in SHAREABLE_KINDS]

    for entry in shared_memory:
        findings.append(
            "memory cell %s is common to the %s command paths, so one cell holds both"
            % (entry["id"], " and ".join(entry["roles"]))
        )
    for entry in shared_drive:
        findings.append(
            "drive element %s is common to the %s command paths, so the separate "
            "memory cells reach the switches through one part"
            % (entry["id"], " and ".join(entry["roles"]))
        )
    for entry in shared_sense:
        notes.append(
            "detection element %s serves both command paths; a shared detection is "
            "the expected architecture and its redundancy is graded elsewhere"
            % entry["id"]
        )

    walk = single_failure_points(switches)
    common_mode = [
        point["element"]
        for point in walk
        if len(point["roles_blocked"]) == len(REQUIRED_SWITCH_ROLES)
    ]

    memory_independent = not shared_memory and not shared_drive
    conformant = acts_on_both and memory_independent and not findings
    return {
        "unit": unit,
        "switch_roles": [switch["role"] for switch in switches],
        "switch_names": {switch["role"]: switch["name"] for switch in switches},
        "memory_cells": {
            switch["role"]: [cell["id"] for cell in memory_cells(switch)]
            for switch in switches
        },
        "acts_on_both_switches": acts_on_both,
        "open_state_held": {
            switch["role"]: holds_open_state(switch) for switch in switches
        },
        "memory_independent": memory_independent,
        "shared_elements": shared,
        "common_mode_points": common_mode,
        "single_failure_points": walk,
        "findings": findings,
        "notes": notes,
        "verdict": "compliant" if conformant else "non-compliant",
    }
