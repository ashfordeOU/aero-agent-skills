#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 4.2.3 electrical connector design rules
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical and electronic engineering standard requires separable
power and test connections to be designed so that no energized contact
is reachable while the connection is open. The half that remains
energized after separation carries recessed socket contacts and the
de-energized half carries pins; a scoop-proof shroud is demanded once
working voltage or contact density crosses a project threshold; the
chassis and bonding path engages first and separates last, ahead of
power return, power line and signals; test and umbilical connections
additionally carry an isolation element and a positive demate
verification; ordnance connections carry a shorting feature; and two
mateable connectors of the same shell size and insert arrangement
carry distinct keying.

This module implements connection categorization, live-side contact
style, the scoop-proof threshold decision, safety-feature derivation
and gap detection, the mating-sequence rank check, the zone-level
keying uniqueness check, and the aggregated connector review. It does
not select a connector part number, does not compute shroud depth, and
does not model contact resistance or current rating.
"""

# --- Connection taxonomy ------------------------------------------------

POWER_CONNECTIONS = frozenset({"power_source", "power_load", "battery_terminal"})
TEST_CONNECTIONS = frozenset(
    {"test_umbilical", "ground_support_access", "skin_connector"}
)
SIGNAL_CONNECTIONS = frozenset({"signal_bus", "telemetry", "command"})
ORDNANCE_CONNECTIONS = frozenset({"pyrotechnic_firing", "safe_and_arm"})

CONNECTION_FAMILIES = {
    "power": POWER_CONNECTIONS,
    "test": TEST_CONNECTIONS,
    "signal": SIGNAL_CONNECTIONS,
    "ordnance": ORDNANCE_CONNECTIONS,
}

# Families whose connection can carry energy across the separation
# plane, and therefore need a de-energized demate inhibit.
POWER_BEARING_FAMILIES = frozenset({"power", "test", "ordnance"})

CONTACT_STYLES = frozenset({"pin", "socket"})

# Project thresholds above which a scoop-proof shroud is demanded.
SCOOP_PROOF_VOLTAGE_THRESHOLD_V = 50.0
SCOOP_PROOF_CONTACT_THRESHOLD = 25

# Mating order rank: a contact role may never engage ahead of a role of
# lower rank. Chassis and bonding engages first and separates last.
MATE_ORDER_RANK = {
    "chassis_ground": 0,
    "power_return": 1,
    "power_positive": 2,
    "signal": 3,
}


def categorize_connection(connection_type):
    """Family of a connection type: "power", "test", "signal" or
    "ordnance". Raises ValueError for a connection type outside every
    known family, so an unrecognized connection is rejected before the
    review proceeds."""
    for family, members in CONNECTION_FAMILIES.items():
        if connection_type in members:
            return family
    raise ValueError(
        "unrecognized connection type %r under E-ST-20C clause 4.2.3"
        % (connection_type,)
    )


def required_contact_style(energized_when_demated):
    """Contact style the half must carry: "socket" (recessed conducting
    surfaces) on the half that stays energized once separated, "pin" on
    the de-energized half."""
    if energized_when_demated:
        return "socket"
    return "pin"


def scoop_proof_required(voltage_v, contact_count):
    """True when a scoop-proof shroud is demanded: the working voltage
    reaches the project voltage threshold, or the contact count reaches
    the project density threshold. Raises ValueError for a negative
    voltage or a non-integer or negative contact count."""
    if voltage_v < 0:
        raise ValueError("voltage_v must be >= 0, got %r" % (voltage_v,))
    if isinstance(contact_count, bool) or not isinstance(contact_count, int):
        raise ValueError("contact_count must be an int, got %r" % (contact_count,))
    if contact_count < 0:
        raise ValueError("contact_count must be >= 0, got %d" % (contact_count,))
    return (
        voltage_v >= SCOOP_PROOF_VOLTAGE_THRESHOLD_V
        or contact_count >= SCOOP_PROOF_CONTACT_THRESHOLD
    )


def required_safety_features(
    connection_type, voltage_v, contact_count, energized_when_demated
):
    """Sorted tuple of the safety features this connection demands.
    Raises ValueError (via categorize_connection and
    scoop_proof_required) for an unrecognized connection type, a
    negative voltage or a bad contact count."""
    family = categorize_connection(connection_type)
    features = {"keying"}
    if energized_when_demated:
        features.add("socket_contacts_on_energized_half")
        features.add("protective_cover")
    if family in POWER_BEARING_FAMILIES:
        features.add("de_energized_demate_inhibit")
    if scoop_proof_required(voltage_v, contact_count):
        features.add("scoop_proof_shroud")
    if family == "test":
        features.add("isolation_element")
        features.add("demate_verification")
    if family == "ordnance":
        features.add("initiator_shorting_feature")
    return tuple(sorted(features))


def missing_safety_features(
    connection_type,
    voltage_v,
    contact_count,
    energized_when_demated,
    implemented_features,
):
    """Sorted tuple of demanded features the design does not implement.
    Features implemented beyond what this connection demands are
    ignored."""
    implemented = set(implemented_features)
    return tuple(
        feature
        for feature in required_safety_features(
            connection_type, voltage_v, contact_count, energized_when_demated
        )
        if feature not in implemented
    )


def contact_style_violations(connector_id, declared_style, energized_when_demated):
    """Violation list (empty if compliant) for the contact style of one
    connector half. Raises ValueError for a declared style outside
    pin/socket -- an unreadable declaration is an input error, not a
    finding to be graded."""
    if declared_style not in CONTACT_STYLES:
        raise ValueError(
            "declared contact style %r must be one of %s"
            % (declared_style, ", ".join(sorted(CONTACT_STYLES)))
        )
    needed = required_contact_style(energized_when_demated)
    if declared_style != needed:
        issue = (
            "exposed_energized_contact"
            if energized_when_demated
            else "contact_style_inverted"
        )
        return [
            {
                "issue": issue,
                "connector": connector_id,
                "declared_style": declared_style,
                "required_style": needed,
            }
        ]
    return []


def mate_sequence_violations(connector_id, contact_sequence):
    """Violation list (empty if compliant) for the mating sequence of
    one connector: walking the contacts in mate order, a role may never
    engage ahead of a role of lower rank. Reports the first contact
    that breaks the order. Raises ValueError for an empty sequence or
    an unrecognized contact role."""
    sequence = list(contact_sequence)
    if not sequence:
        raise ValueError(
            "contact_sequence must name at least one contact role for %r"
            % (connector_id,)
        )
    previous_rank = None
    previous_role = None
    for position, role in enumerate(sequence):
        if role not in MATE_ORDER_RANK:
            raise ValueError(
                "unrecognized contact role %r (known: %s)"
                % (role, ", ".join(sorted(MATE_ORDER_RANK)))
            )
        rank = MATE_ORDER_RANK[role]
        if previous_rank is not None and rank < previous_rank:
            return [
                {
                    "issue": "mate_sequence_out_of_order",
                    "connector": connector_id,
                    "position": position,
                    "role": role,
                    "engages_after": previous_role,
                }
            ]
        previous_rank = rank
        previous_role = role
    return []


def keying_violations(connectors):
    """Violation list (empty if compliant) for keying uniqueness across
    the connectors of one zone. connectors: iterable of
    {"connector_id", "zone", "shell_size", "insert_arrangement",
    "keying"}. Two connectors in the same zone with the same shell size
    and insert arrangement must carry different keying. Raises
    ValueError for a connector missing any of those fields."""
    required_fields = (
        "connector_id",
        "zone",
        "shell_size",
        "insert_arrangement",
        "keying",
    )
    groups = {}
    for connector in connectors:
        for field in required_fields:
            if field not in connector:
                raise ValueError(
                    "connector entry missing required field %r" % (field,)
                )
        group_key = (
            connector["zone"],
            connector["shell_size"],
            connector["insert_arrangement"],
            connector["keying"],
        )
        groups.setdefault(group_key, []).append(connector["connector_id"])
    findings = []
    for group_key in sorted(groups, key=lambda k: tuple(str(part) for part in k)):
        members = groups[group_key]
        if len(members) > 1:
            findings.append(
                {
                    "issue": "cross_mateable_keying_not_unique",
                    "zone": group_key[0],
                    "shell_size": group_key[1],
                    "insert_arrangement": group_key[2],
                    "keying": group_key[3],
                    "connectors": sorted(members),
                }
            )
    return findings


def connector_design_review(connector):
    """Full clause 4.2.3 safety review of one connector.

    connector: {"connector_id": str, "connection_type": str,
    "voltage_v": float, "contact_count": int,
    "energized_when_demated": bool, "contact_style": str,
    "implemented_features": [str, ...],
    "contact_sequence": [role, ...] (optional)}.

    Returns {"connector_id", "family", "scoop_proof_required",
    "findings"}. Does not mutate the input. Raises ValueError for an
    unrecognized connection type or contact role, a bad voltage or
    contact count, an unreadable contact style, or an empty declared
    contact sequence."""
    connector_id = connector["connector_id"]
    connection_type = connector["connection_type"]
    voltage_v = connector["voltage_v"]
    contact_count = connector["contact_count"]
    energized = bool(connector.get("energized_when_demated", False))

    family = categorize_connection(connection_type)
    shroud_needed = scoop_proof_required(voltage_v, contact_count)

    findings = list(
        contact_style_violations(connector_id, connector["contact_style"], energized)
    )
    for feature in missing_safety_features(
        connection_type,
        voltage_v,
        contact_count,
        energized,
        connector.get("implemented_features", []),
    ):
        findings.append(
            {
                "issue": "safety_feature_not_implemented",
                "connector": connector_id,
                "feature": feature,
            }
        )
    if "contact_sequence" in connector:
        findings.extend(
            mate_sequence_violations(connector_id, connector["contact_sequence"])
        )

    return {
        "connector_id": connector_id,
        "family": family,
        "scoop_proof_required": shroud_needed,
        "findings": findings,
    }


def is_connector_compliant(review):
    """True when a connector_design_review result carries no findings --
    the connector satisfies clause 4.2.3 for this review. The zone-level
    keying check is separate and must also be clean."""
    return len(review["findings"]) == 0
