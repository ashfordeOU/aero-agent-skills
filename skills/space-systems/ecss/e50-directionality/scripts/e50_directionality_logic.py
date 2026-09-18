"""Directionality of a space link.

Anchor: ECSS-E-ST-50C Rev.2 clause 5.6.2 (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Read the declared directionality of each space link -- forward-only,
   return-only or bidirectional -- and the set of communication
   services the mission has allocated to that link.
2. Derive the directions the allocated services actually need. A
   telecommand delivery service needs a forward direction, a telemetry
   delivery service needs a return direction, and a service that closes
   a loop (two-way ranging, Doppler tracking, an acknowledged or
   retransmitting transfer) needs both. A service whose needed
   direction the link does not carry is a finding against the
   declaration, not against the service.
3. For a bidirectional link, read whether the two directions run
   simultaneously or alternate on one medium. The declaration is owed:
   a bidirectional link with no simultaneity statement cannot be
   assessed, and a simultaneity statement on a one-way link is a
   declaration error in the other direction.
4. Compute the two-way response time the link can support. On a
   simultaneous link it is the round-trip propagation time. On an
   alternating link each direction change costs a turnaround, and the
   responder may also wait for its slot, so the response time carries
   two turnarounds and the slot wait on top of the round trip.
5. Compare that response time with the allowance the services on the
   link carry, absorbing floating-point representation error at the
   boundary with a named tolerance rather than by relaxing the
   allowance.

Stdlib only, offline, deterministic.
"""

FORWARD = "forward"
RETURN = "return"
VALID_DIRECTIONS = (FORWARD, RETURN)

DIRECTION_FORWARD_ONLY = "forward-only"
DIRECTION_RETURN_ONLY = "return-only"
DIRECTION_BIDIRECTIONAL = "bidirectional"
VALID_DIRECTIONALITIES = (
    DIRECTION_FORWARD_ONLY,
    DIRECTION_RETURN_ONLY,
    DIRECTION_BIDIRECTIONAL,
)

DIRECTIONS_CARRIED = {
    DIRECTION_FORWARD_ONLY: (FORWARD,),
    DIRECTION_RETURN_ONLY: (RETURN,),
    DIRECTION_BIDIRECTIONAL: (FORWARD, RETURN),
}

DUPLEX_SIMULTANEOUS = "simultaneous"
DUPLEX_ALTERNATING = "alternating"
DUPLEX_NOT_DECLARED = "not-declared"
DUPLEX_NOT_APPLICABLE = "not-applicable"
VALID_DUPLEX = (
    DUPLEX_SIMULTANEOUS,
    DUPLEX_ALTERNATING,
    DUPLEX_NOT_DECLARED,
    DUPLEX_NOT_APPLICABLE,
)

# Direction each allocated service needs on the link that hosts it.
SERVICE_DIRECTIONS = {
    "telecommand-delivery": (FORWARD,),
    "telecommand-authentication": (FORWARD,),
    "commanding-in-the-blind": (FORWARD,),
    "forward-file-delivery": (FORWARD,),
    "telemetry-delivery": (RETURN,),
    "essential-telemetry": (RETURN,),
    "telemetry-in-the-blind": (RETURN,),
    "return-file-delivery": (RETURN,),
    "telecommand-acknowledgement": (FORWARD, RETURN),
    "guaranteed-delivery-retransmission": (FORWARD, RETURN),
    "two-way-ranging": (FORWARD, RETURN),
    "doppler-tracking": (FORWARD, RETURN),
    "isochronous-relay": (FORWARD, RETURN),
}

# Services that need both directions open at the same instant; an
# alternating link cannot host them however short its turnaround is.
SERVICES_NEEDING_SIMULTANEITY = frozenset(
    (
        "two-way-ranging",
        "doppler-tracking",
        "isochronous-relay",
    )
)

# A response time is a sum of measured floats, so a link sitting exactly
# on its allowance can land a few units in the last place above it. A
# picosecond is far below any link-budget resolution and absorbs that
# representation error without relaxing the allowance itself.
LATENCY_TOLERANCE_S = 1.0e-12


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def validate_link(link):
    """Validate one space-link record and return a normalized copy."""
    if not isinstance(link, dict):
        raise ValueError("link must be a mapping")
    link_id = link.get("id")
    if not isinstance(link_id, str) or not link_id.strip():
        raise ValueError("link needs a non-empty string id")
    directionality = link.get("directionality")
    if directionality not in VALID_DIRECTIONALITIES:
        raise ValueError(
            "link %s has unknown directionality %r (expected one of %s)"
            % (link_id, directionality, ", ".join(VALID_DIRECTIONALITIES))
        )
    duplex = link.get("duplex", DUPLEX_NOT_DECLARED)
    if duplex not in VALID_DUPLEX:
        raise ValueError(
            "link %s has unknown duplex %r (expected one of %s)"
            % (link_id, duplex, ", ".join(VALID_DUPLEX))
        )
    services = link.get("services")
    if not isinstance(services, (list, tuple)) or not services:
        raise ValueError("link %s needs a non-empty service list" % link_id)
    seen = []
    for service in services:
        if service not in SERVICE_DIRECTIONS:
            raise ValueError(
                "link %s has unknown service %r" % (link_id, service)
            )
        if service in seen:
            raise ValueError(
                "link %s lists service %r twice" % (link_id, service)
            )
        seen.append(service)
    allowance = link.get("max_response_time_s")
    if allowance is not None:
        allowance = _numeric("link %s max_response_time_s" % link_id, allowance)
        if allowance <= 0:
            raise ValueError(
                "link %s max_response_time_s must be positive" % link_id
            )
    return {
        "id": link_id,
        "directionality": directionality,
        "duplex": duplex,
        "services": list(seen),
        "one_way_propagation_s": _numeric(
            "link %s one_way_propagation_s" % link_id,
            link.get("one_way_propagation_s", 0.0),
            0.0,
        ),
        "turnaround_time_s": _numeric(
            "link %s turnaround_time_s" % link_id,
            link.get("turnaround_time_s", 0.0),
            0.0,
        ),
        "slot_wait_time_s": _numeric(
            "link %s slot_wait_time_s" % link_id,
            link.get("slot_wait_time_s", 0.0),
            0.0,
        ),
        "max_response_time_s": allowance,
    }


def declared_directions(directionality):
    """Directions the declaration says the link carries."""
    if directionality not in DIRECTIONS_CARRIED:
        raise ValueError("unknown directionality %r" % (directionality,))
    return DIRECTIONS_CARRIED[directionality]


def required_directions(services):
    """Directions the allocated services need, in canonical order."""
    if not isinstance(services, (list, tuple)) or not services:
        raise ValueError("services must be a non-empty sequence")
    needed = set()
    for service in services:
        if service not in SERVICE_DIRECTIONS:
            raise ValueError("unknown service %r" % (service,))
        needed.update(SERVICE_DIRECTIONS[service])
    return tuple(d for d in VALID_DIRECTIONS if d in needed)


def unsupported_services(link):
    """Services whose needed direction the declaration does not carry."""
    norm = validate_link(link)
    carried = set(declared_directions(norm["directionality"]))
    missing = []
    for service in norm["services"]:
        if not set(SERVICE_DIRECTIONS[service]).issubset(carried):
            missing.append(service)
    return missing


def idle_directions(link):
    """Declared directions that carry no allocated service."""
    norm = validate_link(link)
    needed = set(required_directions(norm["services"]))
    return [d for d in declared_directions(norm["directionality"]) if d not in needed]


def direction_findings(link):
    """Findings about the declared directions of one link."""
    norm = validate_link(link)
    findings = []
    if unsupported_services(norm):
        findings.append("service-needs-a-direction-the-link-does-not-carry")
    if idle_directions(norm):
        findings.append("declared-direction-carries-no-allocated-service")
    return findings


def simultaneity_declaration_findings(link):
    """Findings about the simultaneity statement of one link."""
    norm = validate_link(link)
    findings = []
    bidirectional = norm["directionality"] == DIRECTION_BIDIRECTIONAL
    duplex = norm["duplex"]
    if bidirectional and duplex in (DUPLEX_NOT_DECLARED, DUPLEX_NOT_APPLICABLE):
        findings.append("bidirectional-link-without-a-declared-simultaneity")
    if not bidirectional and duplex in (DUPLEX_SIMULTANEOUS, DUPLEX_ALTERNATING):
        findings.append("simultaneity-declared-on-a-one-way-link")
    return findings


def simultaneous_only_services(link):
    """Allocated services that need both directions open at once."""
    norm = validate_link(link)
    return [s for s in norm["services"] if s in SERVICES_NEEDING_SIMULTANEITY]


def alternating_response_time_s(one_way_propagation_s, turnaround_time_s, slot_wait_time_s):
    """Two-way response time of an alternating link, in seconds."""
    one_way = _numeric("one_way_propagation_s", one_way_propagation_s, 0.0)
    turnaround = _numeric("turnaround_time_s", turnaround_time_s, 0.0)
    slot_wait = _numeric("slot_wait_time_s", slot_wait_time_s, 0.0)
    return 2.0 * one_way + 2.0 * turnaround + slot_wait


def response_time_s(link):
    """Two-way response time of one link, or None when it has no loop."""
    norm = validate_link(link)
    if norm["directionality"] != DIRECTION_BIDIRECTIONAL:
        return None
    if norm["duplex"] == DUPLEX_SIMULTANEOUS:
        return 2.0 * norm["one_way_propagation_s"]
    if norm["duplex"] == DUPLEX_ALTERNATING:
        return alternating_response_time_s(
            norm["one_way_propagation_s"],
            norm["turnaround_time_s"],
            norm["slot_wait_time_s"],
        )
    return None


def response_time_findings(link):
    """Findings about the two-way timing of one link."""
    norm = validate_link(link)
    findings = []
    if norm["duplex"] == DUPLEX_ALTERNATING and simultaneous_only_services(norm):
        findings.append("simultaneous-two-way-service-on-an-alternating-link")
    achieved = response_time_s(norm)
    allowance = norm["max_response_time_s"]
    if achieved is not None and allowance is not None:
        if achieved > allowance + LATENCY_TOLERANCE_S:
            findings.append("two-way-response-time-exceeds-the-service-allowance")
    return findings


def assess_link(link):
    """Assess one space link against clause 5.6.2."""
    norm = validate_link(link)
    findings = list(direction_findings(norm))
    findings.extend(simultaneity_declaration_findings(norm))
    findings.extend(response_time_findings(norm))
    return {
        "id": norm["id"],
        "directionality": norm["directionality"],
        "duplex": norm["duplex"],
        "declared_directions": list(declared_directions(norm["directionality"])),
        "required_directions": list(required_directions(norm["services"])),
        "unsupported_services": unsupported_services(norm),
        "idle_directions": idle_directions(norm),
        "response_time_s": response_time_s(norm),
        "max_response_time_s": norm["max_response_time_s"],
        "findings": findings,
        "compliant": not findings,
    }


def assess_directionality(links):
    """Run the clause 5.6.2 assessment over every declared space link."""
    if not isinstance(links, list) or not links:
        raise ValueError("links must be a non-empty list")
    results = []
    seen = set()
    for link in links:
        result = assess_link(link)
        if result["id"] in seen:
            raise ValueError("duplicate link id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    non_compliant = [r["id"] for r in results if not r["compliant"]]
    return {
        "links": results,
        "bidirectional_ids": [
            r["id"] for r in results if r["directionality"] == DIRECTION_BIDIRECTIONAL
        ],
        "one_way_ids": [
            r["id"] for r in results if r["directionality"] != DIRECTION_BIDIRECTIONAL
        ],
        "non_compliant_ids": non_compliant,
        "compliant": not non_compliant,
    }
