#!/usr/bin/env python3
"""Independence of a device status readout from its command interface.

Anchor: ECSS-E-ST-20-20C clause 5.2.9.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The requirement is that the state a device is actually in stays
readable when the interface that commands it has failed. Two things
defeat it, and only one of them is obvious.

The obvious one is a shared element: a status path that runs through
the same driver, connector, harness run or power domain as the command
chain dies with it, so the readout is a single point of failure
dressed as a measurement.

The other is a path that never sensed the device at all. A command
echo, a driver register readback or a commanded-state memory reports
the state that was ordered. When a relay welds, a latch fails to
transfer or a fuse opens, the ordered state and the achieved state
part company, and a path of this kind keeps reporting the order.

So each path is categorized as
    independent-state-sensing  senses the device and shares nothing
    state-sensing-shared       senses the device through a shared element
    command-derived            reports the ordered state, not the achieved one

and the architecture is judged on whether any independent path is left.
The elements whose single failure blinds every sensing path at once are
computed as well, because that intersection is what a redundancy claim
has to break.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

STATE_SENSING_SOURCES = (
    "device-contact",
    "independent-sensor",
    "load-current-sense",
    "position-switch",
    "output-voltage-sense",
)

COMMAND_DERIVED_SOURCES = (
    "command-echo",
    "commanded-state-memory",
    "driver-register-readback",
)

INDEPENDENT_SENSING = "independent-state-sensing"
SHARED_SENSING = "state-sensing-shared"
COMMAND_DERIVED = "command-derived"

STATUS_INDEPENDENT = "status-independent"
STATUS_SHARED_SINGLE_POINT = "status-shared-single-point"
STATUS_COMMAND_DERIVED_ONLY = "status-command-derived-only"

COMMAND_POWER_ELEMENT = "command-power-domain"


def _require_name_list(name, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence, got %r" % (name, value))
    cleaned = []
    for entry in value:
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError("%s entries must be non-empty names, got %r" % (name, entry))
        cleaned.append(entry.strip())
    return cleaned


def validate_architecture(architecture):
    """Check a status-readout architecture is complete enough to judge."""
    if not isinstance(architecture, dict):
        raise ValueError("architecture must be a mapping, got %r" % (architecture,))
    chain = _require_name_list("command_chain", architecture.get("command_chain"))
    if not chain:
        raise ValueError("command_chain is empty; there is no failure to be independent of")
    paths = architecture.get("paths")
    if not isinstance(paths, (list, tuple)) or not paths:
        raise ValueError("paths must be a non-empty sequence of status acquisition paths")
    seen = set()
    for path in paths:
        if not isinstance(path, dict):
            raise ValueError("each path must be a mapping, got %r" % (path,))
        identifier = path.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("each path needs a non-empty id, got %r" % (identifier,))
        if identifier in seen:
            raise ValueError("duplicate path id %r" % identifier)
        seen.add(identifier)
        source = path.get("source")
        if source not in STATE_SENSING_SOURCES + COMMAND_DERIVED_SOURCES:
            raise ValueError(
                "path %s has an unknown source %r; declare one of %s"
                % (
                    identifier,
                    source,
                    ", ".join(STATE_SENSING_SOURCES + COMMAND_DERIVED_SOURCES),
                )
            )
        _require_name_list(
            "path %s shared_elements" % identifier, path.get("shared_elements", [])
        )
        powered_from = path.get("powered_from")
        if powered_from is not None and (
            not isinstance(powered_from, str) or not powered_from.strip()
        ):
            raise ValueError("path %s powered_from must be a name" % identifier)
    command_power = architecture.get("command_power_domain")
    if command_power is not None and (
        not isinstance(command_power, str) or not command_power.strip()
    ):
        raise ValueError("command_power_domain must be a name")
    return architecture


def senses_device_state(source):
    """True when the source observes the device rather than the order."""
    if source in STATE_SENSING_SOURCES:
        return True
    if source in COMMAND_DERIVED_SOURCES:
        return False
    raise ValueError("unknown status source %r" % (source,))


def categorize_path(path, command_chain, command_power_domain=None):
    """Categorize one acquisition path against the command chain."""
    chain = set(_require_name_list("command_chain", command_chain))
    if not isinstance(path, dict):
        raise ValueError("path must be a mapping, got %r" % (path,))
    identifier = path.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("each path needs a non-empty id, got %r" % (identifier,))
    source = path.get("source")
    sensing = senses_device_state(source)
    declared = _require_name_list(
        "path %s shared_elements" % identifier, path.get("shared_elements", [])
    )
    shared = sorted(set(declared) & chain)
    undeclared = sorted(set(declared) - chain)
    powered_from = path.get("powered_from")
    if (
        command_power_domain is not None
        and powered_from is not None
        and powered_from == command_power_domain
    ):
        shared = sorted(set(shared) | {COMMAND_POWER_ELEMENT})
    findings = []
    for element in undeclared:
        findings.append(
            "path %s declares %r as shared but it is not in the command chain; it "
            "constrains nothing here" % (identifier, element)
        )
    if not sensing:
        category = COMMAND_DERIVED
        findings.append(
            "path %s reports the ordered state through %s, so it cannot witness a "
            "device that failed to follow the order" % (identifier, source)
        )
    elif shared:
        category = SHARED_SENSING
    else:
        category = INDEPENDENT_SENSING
    return {
        "id": identifier,
        "source": source,
        "category": category,
        "senses_device_state": sensing,
        "shared_elements": shared,
        "findings": findings,
    }


def categorize_paths(architecture):
    """Categorize every declared acquisition path."""
    validate_architecture(architecture)
    return [
        categorize_path(
            path,
            architecture["command_chain"],
            architecture.get("command_power_domain"),
        )
        for path in architecture["paths"]
    ]


def blinding_elements(architecture):
    """Elements whose single failure disables every sensing path at once."""
    categorized = categorize_paths(architecture)
    sensing = [entry for entry in categorized if entry["senses_device_state"]]
    if not sensing:
        return sorted(set(_require_name_list("command_chain", architecture["command_chain"])))
    common = set(sensing[0]["shared_elements"])
    for entry in sensing[1:]:
        common &= set(entry["shared_elements"])
    return sorted(common)


def independent_path_ids(architecture):
    """Ids of the paths that sense the device and share nothing with command."""
    return [
        entry["id"]
        for entry in categorize_paths(architecture)
        if entry["category"] == INDEPENDENT_SENSING
    ]


def assess_status_independence(architecture):
    """Full clause 5.2.9.1.1 judgement of a status readout architecture."""
    categorized = categorize_paths(architecture)
    findings = []
    for entry in categorized:
        findings.extend(entry["findings"])
    independent = [e["id"] for e in categorized if e["category"] == INDEPENDENT_SENSING]
    shared = [e["id"] for e in categorized if e["category"] == SHARED_SENSING]
    derived = [e["id"] for e in categorized if e["category"] == COMMAND_DERIVED]
    blinding = blinding_elements(architecture)
    duties = []
    if independent:
        verdict = STATUS_INDEPENDENT
    elif shared:
        verdict = STATUS_SHARED_SINGLE_POINT
        findings.append(
            "every sensing path runs through the command chain; the readout fails "
            "with the interface it is supposed to survive"
        )
        for element in blinding:
            duties.append(
                "route a sensing path clear of %s, or duplicate that element" % element
            )
    else:
        verdict = STATUS_COMMAND_DERIVED_ONLY
        findings.append(
            "no path senses the device itself; the readout repeats the order and "
            "cannot show a device that did not follow it"
        )
        duties.append(
            "add a path that senses the achieved device state rather than the order"
        )
    for entry in categorized:
        if entry["category"] == SHARED_SENSING and independent:
            duties.append(
                "record path %s as command-dependent through %s"
                % (entry["id"], ", ".join(entry["shared_elements"]))
            )
    return {
        "verdict": verdict,
        "independent_path_ids": independent,
        "shared_path_ids": shared,
        "command_derived_path_ids": derived,
        "sensing_path_count": len(independent) + len(shared),
        "independent_path_count": len(independent),
        "blinding_elements": blinding,
        "redundant": len(independent) > 1,
        "findings": findings,
        "duties": duties,
        "paths": categorized,
    }
