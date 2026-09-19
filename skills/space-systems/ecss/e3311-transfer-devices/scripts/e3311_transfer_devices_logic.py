"""Screen for an explosive transfer train and the devices in it.

Anchor: ECSS-E-ST-33-11C clause 4.11.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A transfer device moves an initiation from where it was produced to
where it is needed: a through-bulkhead initiator carries it across a
sealed wall without opening the wall, and a detonation or ignition
transfer line carries it along a route. Nothing in the train does any
useful work itself, so the whole subject is whether the initiation
arrives, arrives everywhere at once, and arrives without breaching
anything on the way.

The screen runs four kinds of gate:

    interface     each donor-to-acceptor crossing, graded as the
                  reliable transfer gap against the gap the design
                  actually presents, plus containment where the
                  crossing goes through a bulkhead
    segment       core load against the minimum that will propagate,
                  and installed bend radius against the line's own
                  minimum
    simultaneity  arrival time down every branch, from segment length
                  over propagation velocity plus interface delays,
                  and the spread between the earliest and the latest
    temperature   the qualified range against the predicted range
                  with margin on both ends

Limits are declared policy, not physical constants: the defaults below
are a starting point and a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

LINE_KINDS = (
    "detonation-transfer-line",
    "ignition-transfer-line",
    "through-bulkhead-initiator",
)

VERDICT_MET = "transfer-train-met"
VERDICT_NOT_MET = "transfer-train-not-met"

DEFAULT_TRANSFER_POLICY = {
    "min_gap_margin": 2.0,
    "min_core_load_margin": 1.25,
    "max_simultaneity_spread_s": 1.0e-3,
    "min_bend_radius_margin": 1.0,
    "min_bulkhead_pressure_margin": 2.0,
    "temperature_margin_k": 10.0,
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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    Arrival times are sums of quotients, so a branch sitting exactly on
    a spread limit can land a few units in the last place above it. The
    limit is never relaxed; only the comparison tolerates the
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


def validate_transfer_policy(policy):
    """Check a policy carries every limit the transfer gates need."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "min_gap_margin",
        "min_core_load_margin",
        "max_simultaneity_spread_s",
        "min_bend_radius_margin",
        "min_bulkhead_pressure_margin",
    ):
        _require_positive("policy %s" % key, policy.get(key))
    _require_non_negative(
        "policy temperature_margin_k", policy.get("temperature_margin_k")
    )
    if not _at_least(policy["min_gap_margin"], 1.0):
        raise ValueError(
            "policy min_gap_margin must be at least 1.0, got %r"
            % (policy["min_gap_margin"],)
        )
    return policy


def validate_segment(record):
    """Normalize one transfer line segment into a checked record."""
    if not isinstance(record, dict):
        raise ValueError("segment must be a mapping, got %r" % (record,))
    segment_id = _require_text("segment id", record.get("id"))
    return {
        "id": segment_id,
        "kind": _require_choice(
            "segment %s kind" % segment_id, record.get("kind"), LINE_KINDS
        ),
        "length_m": _require_positive(
            "segment %s length_m" % segment_id, record.get("length_m")
        ),
        "propagation_velocity_m_s": _require_positive(
            "segment %s propagation_velocity_m_s" % segment_id,
            record.get("propagation_velocity_m_s"),
        ),
        "core_load_g_per_m": _require_positive(
            "segment %s core_load_g_per_m" % segment_id,
            record.get("core_load_g_per_m"),
        ),
        "min_propagating_core_load_g_per_m": _require_positive(
            "segment %s min_propagating_core_load_g_per_m" % segment_id,
            record.get("min_propagating_core_load_g_per_m"),
        ),
        "min_bend_radius_mm": _require_positive(
            "segment %s min_bend_radius_mm" % segment_id,
            record.get("min_bend_radius_mm"),
        ),
        "installed_bend_radius_mm": _require_positive(
            "segment %s installed_bend_radius_mm" % segment_id,
            record.get("installed_bend_radius_mm"),
        ),
    }


def validate_interface(record):
    """Normalize one donor-to-acceptor crossing into a checked record.

    A bulkhead crossing carries two extra declarations, and they are
    required rather than defaulted: the containment case is the whole
    reason a through-bulkhead device exists.
    """
    if not isinstance(record, dict):
        raise ValueError("interface must be a mapping, got %r" % (record,))
    interface_id = _require_text("interface id", record.get("id"))
    through_bulkhead = _require_bool(
        "interface %s through_bulkhead" % interface_id,
        record.get("through_bulkhead", False),
    )
    normalized = {
        "id": interface_id,
        "through_bulkhead": through_bulkhead,
        "design_gap_mm": _require_positive(
            "interface %s design_gap_mm" % interface_id, record.get("design_gap_mm")
        ),
        "max_transfer_gap_mm": _require_positive(
            "interface %s max_transfer_gap_mm" % interface_id,
            record.get("max_transfer_gap_mm"),
        ),
        "delay_s": _require_non_negative(
            "interface %s delay_s" % interface_id, record.get("delay_s", 0.0)
        ),
        "bulkhead_proof_pressure_mpa": None,
        "peak_transfer_pressure_mpa": None,
        "seal_retained": None,
    }
    if through_bulkhead:
        normalized["bulkhead_proof_pressure_mpa"] = _require_positive(
            "interface %s bulkhead_proof_pressure_mpa" % interface_id,
            record.get("bulkhead_proof_pressure_mpa"),
        )
        normalized["peak_transfer_pressure_mpa"] = _require_positive(
            "interface %s peak_transfer_pressure_mpa" % interface_id,
            record.get("peak_transfer_pressure_mpa"),
        )
        normalized["seal_retained"] = _require_bool(
            "interface %s seal_retained" % interface_id, record.get("seal_retained")
        )
    return normalized


def validate_train(train):
    """Normalize a whole train and resolve every branch reference."""
    if not isinstance(train, dict):
        raise ValueError("train must be a mapping, got %r" % (train,))
    segments = train.get("segments")
    interfaces = train.get("interfaces")
    branches = train.get("branches")
    if not isinstance(segments, (list, tuple)) or not segments:
        raise ValueError("train must declare at least one segment")
    if not isinstance(interfaces, (list, tuple)) or not interfaces:
        raise ValueError("train must declare at least one interface")
    if not isinstance(branches, (list, tuple)) or not branches:
        raise ValueError("train must declare at least one branch")
    segment_map = {}
    for raw in segments:
        record = validate_segment(raw)
        if record["id"] in segment_map:
            raise ValueError("duplicate segment id %r" % record["id"])
        segment_map[record["id"]] = record
    interface_map = {}
    for raw in interfaces:
        record = validate_interface(raw)
        if record["id"] in interface_map:
            raise ValueError("duplicate interface id %r" % record["id"])
        interface_map[record["id"]] = record
    branch_list = []
    seen_branches = set()
    for raw in branches:
        if not isinstance(raw, dict):
            raise ValueError("branch must be a mapping, got %r" % (raw,))
        branch_id = _require_text("branch id", raw.get("id"))
        if branch_id in seen_branches:
            raise ValueError("duplicate branch id %r" % branch_id)
        seen_branches.add(branch_id)
        branch_segments = raw.get("segments")
        branch_interfaces = raw.get("interfaces", [])
        if not isinstance(branch_segments, (list, tuple)) or not branch_segments:
            raise ValueError("branch %s must route through a segment" % branch_id)
        if not isinstance(branch_interfaces, (list, tuple)):
            raise ValueError("branch %s interfaces must be a list" % branch_id)
        for ref in branch_segments:
            if ref not in segment_map:
                raise ValueError(
                    "branch %s routes through unknown segment %r" % (branch_id, ref)
                )
        for ref in branch_interfaces:
            if ref not in interface_map:
                raise ValueError(
                    "branch %s crosses unknown interface %r" % (branch_id, ref)
                )
        branch_list.append(
            {
                "id": branch_id,
                "segments": list(branch_segments),
                "interfaces": list(branch_interfaces),
            }
        )
    used_interfaces = set()
    for branch in branch_list:
        used_interfaces.update(branch["interfaces"])
    orphans = sorted(set(interface_map) - used_interfaces)
    if orphans:
        raise ValueError(
            "interfaces declared but on no branch: %s" % ", ".join(orphans)
        )
    return {
        "id": _require_text("train id", train.get("id")),
        "segments": segment_map,
        "interfaces": interface_map,
        "branches": branch_list,
        "qualified_min_temperature_k": _require_positive(
            "train qualified_min_temperature_k",
            train.get("qualified_min_temperature_k"),
        ),
        "qualified_max_temperature_k": _require_positive(
            "train qualified_max_temperature_k",
            train.get("qualified_max_temperature_k"),
        ),
    }


def segment_transit_time_s(record):
    """Time the initiation takes to run the length of one segment."""
    segment = validate_segment(record)
    return segment["length_m"] / segment["propagation_velocity_m_s"]


def gap_margin(record):
    """Reliable transfer gap over the gap the design actually presents."""
    interface = validate_interface(record)
    return interface["max_transfer_gap_mm"] / interface["design_gap_mm"]


def interface_verdict(record, policy=DEFAULT_TRANSFER_POLICY):
    """Grade one crossing on transfer margin and, if any, containment."""
    validate_transfer_policy(policy)
    interface = validate_interface(record)
    margin = gap_margin(record)
    findings = []
    if not _at_least(margin, policy["min_gap_margin"]):
        findings.append(
            "%s presents a %.3f mm gap against a %.3f mm reliable transfer "
            "gap, a margin of %.3f below the required %.3f"
            % (
                interface["id"],
                interface["design_gap_mm"],
                interface["max_transfer_gap_mm"],
                margin,
                policy["min_gap_margin"],
            )
        )
    pressure_margin = None
    if interface["through_bulkhead"]:
        pressure_margin = (
            interface["bulkhead_proof_pressure_mpa"]
            / interface["peak_transfer_pressure_mpa"]
        )
        if not _at_least(pressure_margin, policy["min_bulkhead_pressure_margin"]):
            findings.append(
                "%s holds the bulkhead to %.3f MPa against a %.3f MPa peak, a "
                "margin of %.3f below the required %.3f"
                % (
                    interface["id"],
                    interface["bulkhead_proof_pressure_mpa"],
                    interface["peak_transfer_pressure_mpa"],
                    pressure_margin,
                    policy["min_bulkhead_pressure_margin"],
                )
            )
        if not interface["seal_retained"]:
            findings.append(
                "%s does not retain its seal after firing, so the bulkhead is "
                "breached by the transfer it was meant to contain"
                % interface["id"]
            )
    return {
        "gate": "interface",
        "id": interface["id"],
        "gap_margin": margin,
        "pressure_margin": pressure_margin,
        "compliant": not findings,
        "findings": findings,
    }


def segment_verdict(record, policy=DEFAULT_TRANSFER_POLICY):
    """Grade one segment on core load and installed bend radius."""
    validate_transfer_policy(policy)
    segment = validate_segment(record)
    load_margin = (
        segment["core_load_g_per_m"] / segment["min_propagating_core_load_g_per_m"]
    )
    bend_margin = (
        segment["installed_bend_radius_mm"] / segment["min_bend_radius_mm"]
    )
    findings = []
    if not _at_least(load_margin, policy["min_core_load_margin"]):
        findings.append(
            "%s carries %.4f g/m against a %.4f g/m propagating minimum, a "
            "margin of %.3f below the required %.3f"
            % (
                segment["id"],
                segment["core_load_g_per_m"],
                segment["min_propagating_core_load_g_per_m"],
                load_margin,
                policy["min_core_load_margin"],
            )
        )
    if not _at_least(bend_margin, policy["min_bend_radius_margin"]):
        findings.append(
            "%s is installed on a %.2f mm radius against a %.2f mm minimum"
            % (
                segment["id"],
                segment["installed_bend_radius_mm"],
                segment["min_bend_radius_mm"],
            )
        )
    return {
        "gate": "segment",
        "id": segment["id"],
        "core_load_margin": load_margin,
        "bend_radius_margin": bend_margin,
        "transit_time_s": segment_transit_time_s(record),
        "compliant": not findings,
        "findings": findings,
    }


def branch_arrival_time_s(branch, segment_map, interface_map):
    """Arrival time down one branch: transit times plus crossing delays."""
    if not isinstance(branch, dict):
        raise ValueError("branch must be a mapping, got %r" % (branch,))
    total = 0.0
    for ref in branch.get("segments", []):
        if ref not in segment_map:
            raise ValueError("unknown segment %r on a branch" % (ref,))
        total += segment_transit_time_s(segment_map[ref])
    for ref in branch.get("interfaces", []):
        if ref not in interface_map:
            raise ValueError("unknown interface %r on a branch" % (ref,))
        total += interface_map[ref]["delay_s"]
    return total


def simultaneity_verdict(train, policy=DEFAULT_TRANSFER_POLICY):
    """Grade the spread between the earliest and latest branch arrival."""
    validate_transfer_policy(policy)
    checked = validate_train(train)
    arrivals = {
        branch["id"]: branch_arrival_time_s(
            branch, checked["segments"], checked["interfaces"]
        )
        for branch in checked["branches"]
    }
    spread = max(arrivals.values()) - min(arrivals.values())
    ok = _at_most(spread, policy["max_simultaneity_spread_s"])
    findings = []
    if not ok:
        earliest = min(arrivals, key=lambda key: arrivals[key])
        latest = max(arrivals, key=lambda key: arrivals[key])
        findings.append(
            "branch %s arrives %.6f s after branch %s, a spread above the "
            "allowed %.6f s"
            % (latest, spread, earliest, policy["max_simultaneity_spread_s"])
        )
    return {
        "gate": "simultaneity",
        "arrivals_s": arrivals,
        "spread_s": spread,
        "compliant": ok,
        "findings": findings,
    }


def temperature_verdict(train, case, policy=DEFAULT_TRANSFER_POLICY):
    """Grade the qualified range against the predicted range with margin."""
    validate_transfer_policy(policy)
    checked = validate_train(train)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    predicted_min = _require_positive(
        "case predicted_min_temperature_k", case.get("predicted_min_temperature_k")
    )
    predicted_max = _require_positive(
        "case predicted_max_temperature_k", case.get("predicted_max_temperature_k")
    )
    if predicted_max < predicted_min:
        raise ValueError("predicted maximum temperature is below the minimum")
    margin = policy["temperature_margin_k"]
    required_low = predicted_min - margin
    required_high = predicted_max + margin
    findings = []
    if not _at_most(checked["qualified_min_temperature_k"], required_low):
        findings.append(
            "the train is qualified down to %.2f K, short of the %.2f K the "
            "cold case plus margin demands"
            % (checked["qualified_min_temperature_k"], required_low)
        )
    if not _at_least(checked["qualified_max_temperature_k"], required_high):
        findings.append(
            "the train is qualified up to %.2f K, short of the %.2f K the hot "
            "case plus margin demands"
            % (checked["qualified_max_temperature_k"], required_high)
        )
    return {
        "gate": "temperature",
        "required_low_k": required_low,
        "required_high_k": required_high,
        "compliant": not findings,
        "findings": findings,
    }


def assess_transfer_train(train, case, policy=DEFAULT_TRANSFER_POLICY):
    """Full clause 4.11.4 screen over a transfer train."""
    validate_transfer_policy(policy)
    checked = validate_train(train)
    segment_results = [
        segment_verdict(checked["segments"][key], policy)
        for key in sorted(checked["segments"])
    ]
    interface_results = [
        interface_verdict(checked["interfaces"][key], policy)
        for key in sorted(checked["interfaces"])
    ]
    simultaneity = simultaneity_verdict(train, policy)
    temperature = temperature_verdict(train, case, policy)
    findings = []
    for result in segment_results + interface_results:
        findings.extend(result["findings"])
    findings.extend(simultaneity["findings"])
    findings.extend(temperature["findings"])
    failed_segments = [r["id"] for r in segment_results if not r["compliant"]]
    failed_interfaces = [r["id"] for r in interface_results if not r["compliant"]]
    compliant = (
        not failed_segments
        and not failed_interfaces
        and simultaneity["compliant"]
        and temperature["compliant"]
    )
    return {
        "id": checked["id"],
        "segments": segment_results,
        "interfaces": interface_results,
        "simultaneity": simultaneity,
        "temperature": temperature,
        "failed_segments": failed_segments,
        "failed_interfaces": failed_interfaces,
        "compliant": compliant,
        "verdict": VERDICT_MET if compliant else VERDICT_NOT_MET,
        "findings": findings,
    }
