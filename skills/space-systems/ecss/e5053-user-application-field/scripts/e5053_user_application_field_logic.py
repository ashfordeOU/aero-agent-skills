#!/usr/bin/env python3
"""User application field of a packet transfer protocol data unit.

Anchor: ECSS-E-ST-50-53C clause 5.3.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The target logical address gets the unit to a node. It does not get the
unit to a user of the protocol inside that node. One octet after the
reserved field does that: it names which application behind the
destination address the packet is for, so several users can share one
logical address without sharing a packet stream.

That makes the field an allocation problem as much as a parsing one.
The identifier space is one octet wide, it is administered per node
rather than per network, and two applications given the same identifier
behind one address is an undetectable defect at run time -- both see
each other's packets and neither sees an error. So the allocation is
refused at registration rather than diagnosed later.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

OCTET_MAX = 255
IDENTIFIER_SPACE = OCTET_MAX + 1

DELIVER = "deliver-to-user-application"
DISCARD_UNREGISTERED = "discard-unregistered-user-application"


def _require_octet(name, value):
    """One unsigned octet, rejecting bools and anything out of range."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer octet, got %r" % (name, value))
    if value < 0 or value > OCTET_MAX:
        raise ValueError("%s must lie in 0..%d, got %d" % (name, OCTET_MAX, value))
    return value


def _require_table(table):
    if not isinstance(table, dict):
        raise ValueError("table must be a mapping, got %r" % (table,))
    for key, name in table.items():
        _require_octet("user application identifier", key)
        if not isinstance(name, str) or not name:
            raise ValueError(
                "user application %r must be named by a non-empty string, got %r"
                % (key, name)
            )
    return table


def user_application_offset(path_length):
    """Index of the user application octet for this many path bytes."""
    if isinstance(path_length, bool) or not isinstance(path_length, int):
        raise ValueError("path_length must be an integer, got %r" % (path_length,))
    if path_length < 0:
        raise ValueError("path_length must not be negative, got %d" % path_length)
    return path_length + 3


def validate_user_application_identifier(value):
    """One octet, nothing wider, nothing signed."""
    return _require_octet("user application identifier", value)


def register_user_application(table, identifier, name):
    """Add one application to a node's table, refusing either collision."""
    _require_table(table)
    _require_octet("identifier", identifier)
    if not isinstance(name, str) or not name:
        raise ValueError("name must be a non-empty string, got %r" % (name,))
    if identifier in table:
        raise ValueError(
            "identifier %d is already held by %r behind this address; two "
            "applications on one identifier cannot be separated at run time"
            % (identifier, table[identifier])
        )
    if name in table.values():
        raise ValueError(
            "application %r is already registered on another identifier; a "
            "second entry splits its packet stream" % name
        )
    updated = dict(table)
    updated[identifier] = name
    return updated


def allocate_user_application_identifier(table, preferred=None):
    """Pick a free identifier, honouring a preference where it is free."""
    _require_table(table)
    if preferred is not None:
        _require_octet("preferred identifier", preferred)
        if preferred in table:
            raise ValueError(
                "preferred identifier %d is already held by %r"
                % (preferred, table[preferred])
            )
        return preferred
    for candidate in range(IDENTIFIER_SPACE):
        if candidate not in table:
            return candidate
    raise ValueError(
        "every one of the %d identifiers behind this address is taken"
        % IDENTIFIER_SPACE
    )


def resolve_user_application(table, identifier):
    """Decide which application a received unit belongs to, or that it is dropped."""
    _require_table(table)
    _require_octet("identifier", identifier)
    if identifier in table:
        return {
            "identifier": identifier,
            "application": table[identifier],
            "disposition": DELIVER,
            "findings": [],
        }
    return {
        "identifier": identifier,
        "application": None,
        "disposition": DISCARD_UNREGISTERED,
        "findings": [
            "identifier %d names no application behind this address, so the "
            "packet is dropped rather than handed to a neighbour" % identifier
        ],
    }


def read_user_application_field(octets, path_length):
    """Pull the user application octet out of a received unit."""
    try:
        data = list(octets)
    except TypeError:
        raise ValueError("octets must be a sequence, got %r" % (octets,))
    offset = user_application_offset(path_length)
    if len(data) <= offset:
        raise ValueError(
            "unit of %d octets is too short to hold a user application field "
            "at offset %d" % (len(data), offset)
        )
    return _require_octet("user application identifier", data[offset])


def audit_user_application_table(table):
    """Report how much of a node's identifier space is committed."""
    _require_table(table)
    used = len(table)
    return {
        "registered": used,
        "free": IDENTIFIER_SPACE - used,
        "utilisation": used / float(IDENTIFIER_SPACE),
        "exhausted": used == IDENTIFIER_SPACE,
        "next_free": None if used == IDENTIFIER_SPACE
        else allocate_user_application_identifier(table),
    }


def assess_user_application_field(case):
    """Full clause 5.3.5 decision for one received unit."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    octets = case.get("octets")
    if octets is None:
        raise ValueError("case must carry the received octets")
    path_length = case.get("path_length", 0)
    table = case.get("table")
    if table is None:
        raise ValueError("case must carry the node's user application table")
    identifier = read_user_application_field(octets, path_length)
    routed = resolve_user_application(table, identifier)
    return {
        "identifier": identifier,
        "identifier_offset": user_application_offset(path_length),
        "application": routed["application"],
        "disposition": routed["disposition"],
        "verdict": (
            "user-application-resolved"
            if routed["disposition"] == DELIVER
            else "user-application-unresolved"
        ),
        "findings": list(routed["findings"]),
    }
