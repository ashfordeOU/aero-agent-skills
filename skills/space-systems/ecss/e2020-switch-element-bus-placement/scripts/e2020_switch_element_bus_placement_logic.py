#!/usr/bin/env python3
"""Switching element on the energised main bus side of a protection device.

Anchor: ECSS-E-ST-20-20C clause 5.2.3.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A protection device on a distribution branch -- a latching current
limiter, a heater latching current limiter, a fold-back limiter or a
latching relay -- contains a series pass element that opens the branch.
Which end of the device that pass element sits at decides what the open
device actually achieves. Placed on the energised main bus side, it
puts itself between the bus and everything it protects, so opening it
leaves the harness, the connectors and the load at return potential.
Placed on the return side, opening it leaves every one of those still
tied to the energised bus: the load case floats up to bus potential, a
downstream short to structure finds a return path that never passes
through the open element, and the branch is not isolated at all even
though the device reports itself off.

The branch is modelled as an ordered chain from the main bus, along the
energised rail, through the load, and back along the return rail to the
bus return. Every element declares the rail it sits on, the load is the
single crossing point between the rails, and the position of the
switching element in that order is the whole question the clause asks.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

RAIL_ENERGISED = "energised"
RAIL_LOAD = "load"
RAIL_RETURN = "return"
RAILS = (RAIL_ENERGISED, RAIL_LOAD, RAIL_RETURN)

MAIN_BUS = "main-bus"
BUS_RETURN = "bus-return"
SWITCHING_ELEMENT = "switching-element"
LOAD = "load"

ELEMENT_KINDS = (
    MAIN_BUS,
    SWITCHING_ELEMENT,
    "current-sensor",
    "fuse",
    "filter",
    "connector",
    "harness",
    LOAD,
    BUS_RETURN,
)

# Interfaces a technician or a stray conductor can reach; these are the
# ones that matter when something stays live behind an open device.
EXPOSED_KINDS = ("connector", "harness")

# Elements that exist exactly once in a well-formed branch chain.
UNIQUE_KINDS = (MAIN_BUS, BUS_RETURN, SWITCHING_ELEMENT, LOAD)

PLACEMENT_COMPLIANT = "switch-placement-compliant"
PLACEMENT_NON_COMPLIANT = "switch-placement-non-compliant"

DEFAULT_MAX_LIVE_STUB_M = 0.25

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A stub length summed in metres from millimetre entries can land a few
    units in the last place either side of a limit written in metres. The
    limit is never relaxed; only the comparison tolerates the
    representation error, which is why no caller uses a bare <= on a
    derived float.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_chain(chain):
    """Check a branch chain and return it as a tuple of plain mappings.

    The chain runs main bus -> energised rail -> load -> return rail ->
    bus return. Anything that cannot be read in that order is refused
    here rather than silently producing a placement verdict about a
    topology nobody described.
    """
    if not isinstance(chain, (list, tuple)) or not chain:
        raise ValueError("chain must be a non-empty sequence of elements, got %r" % (chain,))
    if len(chain) < 3:
        raise ValueError(
            "chain needs at least a main bus, a load and a bus return, got %d elements"
            % (len(chain),)
        )

    elements = []
    seen_ids = set()
    for index, raw in enumerate(chain):
        if not isinstance(raw, dict):
            raise ValueError("chain element %d must be a mapping, got %r" % (index, raw))
        element_id = raw.get("id")
        if not isinstance(element_id, str) or not element_id.strip():
            raise ValueError("chain element %d needs a non-empty id, got %r" % (index, element_id))
        if element_id in seen_ids:
            raise ValueError("duplicate chain element id %r" % (element_id,))
        seen_ids.add(element_id)
        kind = raw.get("kind")
        if kind not in ELEMENT_KINDS:
            raise ValueError(
                "chain element %r has unknown kind %r; known kinds are %s"
                % (element_id, kind, ", ".join(ELEMENT_KINDS))
            )
        rail = raw.get("rail")
        if rail not in RAILS:
            raise ValueError(
                "chain element %r sits on unknown rail %r; rails are %s"
                % (element_id, rail, ", ".join(RAILS))
            )
        length_m = _require_non_negative(
            "length_m of %s" % (element_id,), raw.get("length_m", 0.0)
        )
        elements.append(
            {"id": element_id, "kind": kind, "rail": rail, "length_m": length_m}
        )

    for kind in UNIQUE_KINDS:
        count = sum(1 for e in elements if e["kind"] == kind)
        if count != 1:
            raise ValueError("chain must hold exactly one %s element, found %d" % (kind, count))

    if elements[0]["kind"] != MAIN_BUS:
        raise ValueError("chain must start at the main bus, starts at %r" % (elements[0]["kind"],))
    if elements[0]["rail"] != RAIL_ENERGISED:
        raise ValueError("the main bus must sit on the energised rail")
    if elements[-1]["kind"] != BUS_RETURN:
        raise ValueError("chain must end at the bus return, ends at %r" % (elements[-1]["kind"],))
    if elements[-1]["rail"] != RAIL_RETURN:
        raise ValueError("the bus return must sit on the return rail")

    crossing = [i for i, e in enumerate(elements) if e["rail"] == RAIL_LOAD]
    if len(crossing) != 1:
        raise ValueError(
            "exactly one element crosses between the rails, found %d" % (len(crossing),)
        )
    load_at = crossing[0]
    if elements[load_at]["kind"] != LOAD:
        raise ValueError(
            "the crossing element must be the load, found %r" % (elements[load_at]["kind"],)
        )
    for index, element in enumerate(elements):
        if index < load_at and element["rail"] != RAIL_ENERGISED:
            raise ValueError(
                "element %r sits before the load and must be on the energised rail"
                % (element["id"],)
            )
        if index > load_at and element["rail"] != RAIL_RETURN:
            raise ValueError(
                "element %r sits after the load and must be on the return rail"
                % (element["id"],)
            )
    return tuple(elements)


def _index_of_kind(elements, kind):
    for index, element in enumerate(elements):
        if element["kind"] == kind:
            return index
    raise ValueError("chain holds no %s element" % (kind,))


def switching_element_index(chain):
    """Position of the series pass element in the branch order."""
    return _index_of_kind(validate_chain(chain), SWITCHING_ELEMENT)


def load_index(chain):
    """Position of the load, which is where the two rails meet."""
    return _index_of_kind(validate_chain(chain), LOAD)


def switch_on_energised_rail(chain):
    """Whether the pass element sits on the energised main bus side."""
    elements = validate_chain(chain)
    return elements[_index_of_kind(elements, SWITCHING_ELEMENT)]["rail"] == RAIL_ENERGISED


def live_when_open(chain):
    """Ids that stay tied to the energised bus once the device opens."""
    elements = validate_chain(chain)
    switch_at = _index_of_kind(elements, SWITCHING_ELEMENT)
    return tuple(e["id"] for e in elements[: switch_at + 1])


def isolated_when_open(chain):
    """Ids the open device actually separates from the energised bus."""
    elements = validate_chain(chain)
    switch_at = _index_of_kind(elements, SWITCHING_ELEMENT)
    return tuple(e["id"] for e in elements[switch_at + 1 :])


def protected_elements(chain):
    """Ids the device exists to isolate: the branch minus its own ends."""
    elements = validate_chain(chain)
    excluded = (MAIN_BUS, BUS_RETURN, SWITCHING_ELEMENT)
    return tuple(e["id"] for e in elements if e["kind"] not in excluded)


def isolation_coverage_fraction(chain):
    """Share of the protected elements the open device de-energises."""
    protected = protected_elements(chain)
    if not protected:
        raise ValueError("chain holds nothing for the device to protect")
    isolated = set(isolated_when_open(chain))
    return sum(1 for element_id in protected if element_id in isolated) / float(len(protected))


def exposed_live_interfaces(chain):
    """Reachable connectors and harness runs left live behind the open device."""
    elements = validate_chain(chain)
    live = set(live_when_open(chain))
    return tuple(
        e["id"] for e in elements if e["id"] in live and e["kind"] in EXPOSED_KINDS
    )


def live_stub_length_m(chain):
    """Harness length upstream of the pass element that stays energised."""
    elements = validate_chain(chain)
    live = set(live_when_open(chain))
    return sum(e["length_m"] for e in elements if e["id"] in live and e["kind"] == "harness")


def bypass_feeds_downstream(chain, bypass_feeds):
    """Extra feeds injecting past the pass element, which it cannot open.

    A cross-strapped redundant bus landing downstream of the switch keeps
    the branch energised whatever the device reports, so the feed is named
    rather than folded into the coverage number.
    """
    elements = validate_chain(chain)
    if bypass_feeds is None:
        return ()
    if not isinstance(bypass_feeds, (list, tuple)):
        raise ValueError("bypass_feeds must be a sequence, got %r" % (bypass_feeds,))
    positions = {e["id"]: i for i, e in enumerate(elements)}
    switch_at = _index_of_kind(elements, SWITCHING_ELEMENT)
    offenders = []
    for index, feed in enumerate(bypass_feeds):
        if not isinstance(feed, dict):
            raise ValueError("bypass feed %d must be a mapping, got %r" % (index, feed))
        feed_id = feed.get("id")
        if not isinstance(feed_id, str) or not feed_id.strip():
            raise ValueError("bypass feed %d needs a non-empty id" % (index,))
        node = feed.get("injects_at")
        if node not in positions:
            raise ValueError(
                "bypass feed %r injects at %r, which is not an element of the chain"
                % (feed_id, node)
            )
        if positions[node] > switch_at:
            offenders.append(feed_id)
    return tuple(offenders)


def assess_switch_placement(branch):
    """Full clause 5.2.3.2.1 judgement of one protection device branch."""
    if not isinstance(branch, dict):
        raise ValueError("branch must be a mapping, got %r" % (branch,))
    elements = validate_chain(branch.get("chain"))
    max_stub = _require_non_negative(
        "max_live_stub_m", branch.get("max_live_stub_m", DEFAULT_MAX_LIVE_STUB_M)
    )

    switch_at = _index_of_kind(elements, SWITCHING_ELEMENT)
    load_at = _index_of_kind(elements, LOAD)
    switch = elements[switch_at]
    on_bus_side = switch["rail"] == RAIL_ENERGISED
    chain = [dict(e) for e in elements]

    live = live_when_open(chain)
    isolated = isolated_when_open(chain)
    coverage = isolation_coverage_fraction(chain)
    exposed = exposed_live_interfaces(chain)
    stub = live_stub_length_m(chain)
    bypasses = bypass_feeds_downstream(chain, branch.get("bypass_feeds"))

    findings = []
    if not on_bus_side:
        findings.append(
            "switching element %s sits on the %s rail; move it to the energised main bus side so opening it separates the branch from the bus"
            % (switch["id"], switch["rail"])
        )
    if switch_at > load_at:
        findings.append(
            "switching element %s sits downstream of the load, which therefore stays tied to the energised bus while the device reports itself off"
            % (switch["id"],)
        )
    if not _at_least(coverage, 1.0):
        findings.append(
            "open device de-energises %.0f%% of the protected elements; %s stay live"
            % (
                coverage * 100.0,
                ", ".join(element_id for element_id in protected_elements(chain) if element_id in set(live)),
            )
        )
    if exposed:
        findings.append(
            "reachable interfaces left live behind the open device: %s" % (", ".join(exposed),)
        )
    if not _at_most(stub, max_stub):
        findings.append(
            "energised harness stub upstream of the switching element is %.3f m, above the %.3f m limit"
            % (stub, max_stub)
        )
    if bypasses:
        findings.append(
            "feeds inject downstream of the switching element and it cannot open them: %s"
            % (", ".join(bypasses),)
        )

    compliant = not findings
    return {
        "branch_id": branch.get("branch_id"),
        "switch_id": switch["id"],
        "switch_rail": switch["rail"],
        "switch_on_energised_rail": on_bus_side,
        "switch_index": switch_at,
        "load_index": load_at,
        "live_when_open": live,
        "isolated_when_open": isolated,
        "isolation_coverage_fraction": coverage,
        "exposed_live_interfaces": exposed,
        "live_stub_length_m": stub,
        "max_live_stub_m": max_stub,
        "bypass_feeds_downstream": bypasses,
        "verdict": PLACEMENT_COMPLIANT if compliant else PLACEMENT_NON_COMPLIANT,
        "compliant": compliant,
        "findings": findings,
    }
