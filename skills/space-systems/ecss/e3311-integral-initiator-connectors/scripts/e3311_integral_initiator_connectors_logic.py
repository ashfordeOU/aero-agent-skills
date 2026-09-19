"""Screen for an initiator that carries its own integral connector.

Anchor: ECSS-E-ST-33-11C clause 4.11.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An initiator with an integral connector is one part, not two. The
connector cannot be swapped, re-terminated or inspected independently
of the energetic device it is built into, so every property that would
be a harness question elsewhere becomes an initiator question here:
the mated contact resistance sits inside the firing loop, the pin
shorting provision is the only thing standing between a handling
static discharge and the bridgewire, and the keying is the only
physical barrier to firing the wrong device.

The screen runs six gates over each initiator and one gate over the
set:

    firing-loop   mated contact resistances added into the loop, the
                  delivered current graded against the all-fire
                  current, and the connector's share of the loop
    shorting      whether the pins are shorted until mate
    insulation    pin-to-shell insulation resistance
    mate-life     rated mate-demate cycles against the planned
                  handling count plus margin
    bonding       shell-to-backshell continuity for shield integrity
    sealing       leak rate across the integral seal
    keying        set-level: one keying code may serve only one
                  firing circuit, or a cross-connection is possible

Limits are declared policy, not physical constants: the defaults below
are a starting point and a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

GATES = (
    "firing-loop",
    "shorting",
    "insulation",
    "mate-life",
    "bonding",
    "sealing",
)

COMPLIANT = "connector-acceptable"
NOT_COMPLIANT = "connector-not-acceptable"

VERDICT_MET = "integral-connector-met"
VERDICT_NOT_MET = "integral-connector-not-met"

DEFAULT_CONNECTOR_POLICY = {
    "all_fire_margin": 1.50,
    "max_contact_resistance_ohm": 0.010,
    "max_connector_share_of_loop": 0.10,
    "min_insulation_resistance_mohm": 100.0,
    "mate_demate_margin": 2.0,
    "max_bonding_resistance_mohm": 10.0,
    "max_seal_leak_rate_scc_s": 1.0e-6,
    "require_pin_shorting": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_count(name, value, minimum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A connector sitting exactly on a declared limit can land a few
    units in the last place above it once the loop arithmetic has run.
    The limit is never relaxed; only the comparison tolerates the
    representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_connector_policy(policy):
    """Check a policy carries every limit the connector gates need."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "all_fire_margin",
        "max_contact_resistance_ohm",
        "max_connector_share_of_loop",
        "min_insulation_resistance_mohm",
        "mate_demate_margin",
        "max_bonding_resistance_mohm",
        "max_seal_leak_rate_scc_s",
    ):
        _require_positive("policy %s" % key, policy.get(key))
    if not _at_least(policy["all_fire_margin"], 1.0):
        raise ValueError(
            "policy all_fire_margin must be at least 1.0, got %r"
            % (policy["all_fire_margin"],)
        )
    if not _at_most(policy["max_connector_share_of_loop"], 1.0):
        raise ValueError(
            "policy max_connector_share_of_loop must not exceed 1.0, got %r"
            % (policy["max_connector_share_of_loop"],)
        )
    _require_bool("policy require_pin_shorting", policy.get("require_pin_shorting"))
    return policy


def validate_initiator(record):
    """Normalize one initiator-with-integral-connector into a record."""
    if not isinstance(record, dict):
        raise ValueError("initiator must be a mapping, got %r" % (record,))
    initiator_id = _require_text("initiator id", record.get("id"))
    return {
        "id": initiator_id,
        "circuit_id": _require_text(
            "initiator %s circuit_id" % initiator_id, record.get("circuit_id")
        ),
        "keying_code": _require_text(
            "initiator %s keying_code" % initiator_id, record.get("keying_code")
        ),
        "bridgewire_resistance_ohm": _require_positive(
            "initiator %s bridgewire_resistance_ohm" % initiator_id,
            record.get("bridgewire_resistance_ohm"),
        ),
        "all_fire_current_a": _require_positive(
            "initiator %s all_fire_current_a" % initiator_id,
            record.get("all_fire_current_a"),
        ),
        "contact_resistance_ohm": _require_non_negative(
            "initiator %s contact_resistance_ohm" % initiator_id,
            record.get("contact_resistance_ohm"),
        ),
        "contact_count": _require_count(
            "initiator %s contact_count" % initiator_id,
            record.get("contact_count", 2),
            2,
        ),
        "insulation_resistance_mohm": _require_non_negative(
            "initiator %s insulation_resistance_mohm" % initiator_id,
            record.get("insulation_resistance_mohm"),
        ),
        "rated_mate_demate_cycles": _require_count(
            "initiator %s rated_mate_demate_cycles" % initiator_id,
            record.get("rated_mate_demate_cycles"),
            1,
        ),
        "planned_mate_demate_cycles": _require_count(
            "initiator %s planned_mate_demate_cycles" % initiator_id,
            record.get("planned_mate_demate_cycles"),
            0,
        ),
        "shell_bonding_resistance_mohm": _require_non_negative(
            "initiator %s shell_bonding_resistance_mohm" % initiator_id,
            record.get("shell_bonding_resistance_mohm"),
        ),
        "seal_leak_rate_scc_s": _require_non_negative(
            "initiator %s seal_leak_rate_scc_s" % initiator_id,
            record.get("seal_leak_rate_scc_s"),
        ),
        "pins_shorted_until_mate": _require_bool(
            "initiator %s pins_shorted_until_mate" % initiator_id,
            record.get("pins_shorted_until_mate", False),
        ),
    }


def validate_initiators(initiators):
    """Normalize an initiator list and reject duplicate identifiers."""
    if not isinstance(initiators, (list, tuple)):
        raise ValueError("initiators must be a list, got %r" % (initiators,))
    if not initiators:
        raise ValueError("initiators must contain at least one device")
    normalized = []
    seen = set()
    for raw in initiators:
        record = validate_initiator(raw)
        if record["id"] in seen:
            raise ValueError("duplicate initiator id %r" % record["id"])
        seen.add(record["id"])
        normalized.append(record)
    return normalized


def validate_firing_circuit(circuit):
    """Normalize the driving circuit the initiator is wired into."""
    if not isinstance(circuit, dict):
        raise ValueError("circuit must be a mapping, got %r" % (circuit,))
    return {
        "firing_voltage_v": _require_positive(
            "circuit firing_voltage_v", circuit.get("firing_voltage_v")
        ),
        "source_resistance_ohm": _require_non_negative(
            "circuit source_resistance_ohm", circuit.get("source_resistance_ohm", 0.0)
        ),
        "harness_resistance_ohm": _require_non_negative(
            "circuit harness_resistance_ohm", circuit.get("harness_resistance_ohm", 0.0)
        ),
    }


def connector_resistance_ohm(record):
    """Resistance the integral connector adds, summed over its contacts."""
    initiator = validate_initiator(record)
    return initiator["contact_count"] * initiator["contact_resistance_ohm"]


def firing_loop_resistance_ohm(record, circuit):
    """Total series resistance seen by the firing source."""
    initiator = validate_initiator(record)
    driver = validate_firing_circuit(circuit)
    return (
        driver["source_resistance_ohm"]
        + driver["harness_resistance_ohm"]
        + connector_resistance_ohm(record)
        + initiator["bridgewire_resistance_ohm"]
    )


def delivered_current_a(record, circuit):
    """Current the source pushes through the bridgewire, by Ohm's law."""
    loop = firing_loop_resistance_ohm(record, circuit)
    if loop <= 0.0:
        raise ValueError("firing loop resistance must be greater than zero")
    driver = validate_firing_circuit(circuit)
    return driver["firing_voltage_v"] / loop


def firing_loop_verdict(record, circuit, policy=DEFAULT_CONNECTOR_POLICY):
    """Grade delivered current and the connector's share of the loop."""
    validate_connector_policy(policy)
    initiator = validate_initiator(record)
    loop = firing_loop_resistance_ohm(record, circuit)
    current = delivered_current_a(record, circuit)
    margin = current / initiator["all_fire_current_a"]
    share = connector_resistance_ohm(record) / loop
    findings = []
    margin_ok = _at_least(margin, policy["all_fire_margin"])
    share_ok = _at_most(share, policy["max_connector_share_of_loop"])
    contact_ok = _at_most(
        initiator["contact_resistance_ohm"], policy["max_contact_resistance_ohm"]
    )
    if not margin_ok:
        findings.append(
            "%s is driven at %.4f A against an all-fire current of %.4f A, a "
            "margin of %.3f below the required %.3f"
            % (
                initiator["id"],
                current,
                initiator["all_fire_current_a"],
                margin,
                policy["all_fire_margin"],
            )
        )
    if not contact_ok:
        findings.append(
            "%s mated contacts read %.4f ohm each, above the allowed %.4f ohm"
            % (
                initiator["id"],
                initiator["contact_resistance_ohm"],
                policy["max_contact_resistance_ohm"],
            )
        )
    if not share_ok:
        findings.append(
            "%s integral connector holds %.1f%% of the firing loop, above the "
            "allowed %.1f%%"
            % (
                initiator["id"],
                100.0 * share,
                100.0 * policy["max_connector_share_of_loop"],
            )
        )
    return {
        "gate": "firing-loop",
        "loop_resistance_ohm": loop,
        "delivered_current_a": current,
        "all_fire_margin": margin,
        "connector_share": share,
        "compliant": not findings,
        "findings": findings,
    }


def shorting_verdict(record, policy=DEFAULT_CONNECTOR_POLICY):
    """Grade the provision that shorts the pins until the connector mates."""
    validate_connector_policy(policy)
    initiator = validate_initiator(record)
    findings = []
    if policy["require_pin_shorting"] and not initiator["pins_shorted_until_mate"]:
        findings.append(
            "%s leaves its pins open until mate, so nothing stands between a "
            "handling discharge and the bridgewire" % initiator["id"]
        )
    return {"gate": "shorting", "compliant": not findings, "findings": findings}


def insulation_verdict(record, policy=DEFAULT_CONNECTOR_POLICY):
    """Grade pin-to-shell insulation resistance."""
    validate_connector_policy(policy)
    initiator = validate_initiator(record)
    ok = _at_least(
        initiator["insulation_resistance_mohm"],
        policy["min_insulation_resistance_mohm"],
    )
    findings = []
    if not ok:
        findings.append(
            "%s insulates pin to shell at %.2f Mohm, short of the %.2f Mohm "
            "required"
            % (
                initiator["id"],
                initiator["insulation_resistance_mohm"],
                policy["min_insulation_resistance_mohm"],
            )
        )
    return {"gate": "insulation", "compliant": ok, "findings": findings}


def mate_life_verdict(record, policy=DEFAULT_CONNECTOR_POLICY):
    """Grade rated mate-demate cycles against the planned handling count."""
    validate_connector_policy(policy)
    initiator = validate_initiator(record)
    required = initiator["planned_mate_demate_cycles"] * policy["mate_demate_margin"]
    ok = _at_least(float(initiator["rated_mate_demate_cycles"]), required)
    findings = []
    if not ok:
        findings.append(
            "%s is rated for %d mate-demate cycles against a planned %d, short "
            "of the %.1f the margin demands"
            % (
                initiator["id"],
                initiator["rated_mate_demate_cycles"],
                initiator["planned_mate_demate_cycles"],
                required,
            )
        )
    return {
        "gate": "mate-life",
        "required_cycles": required,
        "compliant": ok,
        "findings": findings,
    }


def bonding_verdict(record, policy=DEFAULT_CONNECTOR_POLICY):
    """Grade shell-to-backshell continuity carrying the shield."""
    validate_connector_policy(policy)
    initiator = validate_initiator(record)
    ok = _at_most(
        initiator["shell_bonding_resistance_mohm"],
        policy["max_bonding_resistance_mohm"],
    )
    findings = []
    if not ok:
        findings.append(
            "%s bonds its shell at %.3f mohm, above the %.3f mohm the shield "
            "path allows"
            % (
                initiator["id"],
                initiator["shell_bonding_resistance_mohm"],
                policy["max_bonding_resistance_mohm"],
            )
        )
    return {"gate": "bonding", "compliant": ok, "findings": findings}


def sealing_verdict(record, policy=DEFAULT_CONNECTOR_POLICY):
    """Grade the leak rate across the seal integral to the initiator body."""
    validate_connector_policy(policy)
    initiator = validate_initiator(record)
    ok = _at_most(
        initiator["seal_leak_rate_scc_s"], policy["max_seal_leak_rate_scc_s"]
    )
    findings = []
    if not ok:
        findings.append(
            "%s leaks %.3e scc/s across its integral seal, above the allowed "
            "%.3e scc/s"
            % (
                initiator["id"],
                initiator["seal_leak_rate_scc_s"],
                policy["max_seal_leak_rate_scc_s"],
            )
        )
    return {"gate": "sealing", "compliant": ok, "findings": findings}


def keying_conflicts(initiators):
    """Keying codes shared by initiators on different firing circuits.

    A keying code is the physical barrier to a cross-connection. Two
    devices that accept the same key and serve different circuits can
    be swapped by hand, so the pair is reported rather than the code.
    """
    records = validate_initiators(initiators)
    by_code = {}
    for record in records:
        by_code.setdefault(record["keying_code"], []).append(record)
    conflicts = []
    for code in sorted(by_code):
        group = by_code[code]
        circuits = {record["circuit_id"] for record in group}
        if len(circuits) > 1:
            conflicts.append(
                {
                    "keying_code": code,
                    "initiators": sorted(record["id"] for record in group),
                    "circuits": sorted(circuits),
                }
            )
    return conflicts


def assess_initiator_connector(record, circuit, policy=DEFAULT_CONNECTOR_POLICY):
    """Run the per-initiator connector gates and group the outcome."""
    validate_connector_policy(policy)
    initiator = validate_initiator(record)
    gates = {
        "firing-loop": firing_loop_verdict(record, circuit, policy),
        "shorting": shorting_verdict(record, policy),
        "insulation": insulation_verdict(record, policy),
        "mate-life": mate_life_verdict(record, policy),
        "bonding": bonding_verdict(record, policy),
        "sealing": sealing_verdict(record, policy),
    }
    findings = []
    failed = []
    for name in GATES:
        gate = gates[name]
        findings.extend(gate["findings"])
        if not gate["compliant"]:
            failed.append(name)
    return {
        "id": initiator["id"],
        "circuit_id": initiator["circuit_id"],
        "gates": gates,
        "failed_gates": failed,
        "outcome": NOT_COMPLIANT if failed else COMPLIANT,
        "findings": findings,
    }


def assess_connector_set(initiators, circuit, policy=DEFAULT_CONNECTOR_POLICY):
    """Full clause 4.11.3 screen over a set of integral-connector units."""
    validate_connector_policy(policy)
    records = validate_initiators(initiators)
    validate_firing_circuit(circuit)
    per_unit = [
        assess_initiator_connector(record, circuit, policy) for record in records
    ]
    conflicts = keying_conflicts(initiators)
    findings = []
    for result in per_unit:
        findings.extend(result["findings"])
    for conflict in conflicts:
        findings.append(
            "keying code %s is shared by %s across circuits %s, so a "
            "cross-connection is possible by hand"
            % (
                conflict["keying_code"],
                ", ".join(conflict["initiators"]),
                ", ".join(conflict["circuits"]),
            )
        )
    rejected = [r["id"] for r in per_unit if r["outcome"] == NOT_COMPLIANT]
    compliant = not rejected and not conflicts
    return {
        "units": per_unit,
        "accepted": [r["id"] for r in per_unit if r["outcome"] == COMPLIANT],
        "rejected": rejected,
        "keying_conflicts": conflicts,
        "compliant": compliant,
        "verdict": VERDICT_MET if compliant else VERDICT_NOT_MET,
        "findings": findings,
    }
