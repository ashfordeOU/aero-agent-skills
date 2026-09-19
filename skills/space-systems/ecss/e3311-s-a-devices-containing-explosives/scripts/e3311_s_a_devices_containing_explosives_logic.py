"""Screen for a safe and arm device that contains explosives.

Anchor: ECSS-E-ST-33-11C clause 4.11.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A safe and arm device that carries its own explosive lead is the one
component in an explosive subsystem whose job is to not work. In the
safe state it physically interrupts the train, so the donor can fire
and nothing downstream sees it; in the armed state it closes the same
train. Everything the clause asks reduces to two questions: is the
interrupt real, and can the device reach the armed state by accident.

The screen runs six gates:

    interrupt     out-of-line offset of the rotor lead, expressed
                  against the charge diameter, plus the barrier
                  thickness standing between donor and acceptor
    independence  the declared arming events, counted and then
                  checked for a shared source, because two events
                  driven from one signal are one event
    retention     the lock or detent torque against the inertial
                  torque the shock environment applies to the rotor
    monitoring    safe and armed position indication, and isolation
                  of the monitoring circuit from the firing circuit
    arming-time   the measured arming time inside its declared window
    de-arm        whether the device can be returned to safe

Limits are declared policy, not physical constants: the defaults below
are a starting point and a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STANDARD_GRAVITY_M_S2 = 9.80665

GATES = (
    "interrupt",
    "independence",
    "retention",
    "monitoring",
    "arming-time",
    "de-arm",
)

SAFE_STATE = "safe"
ARMED_STATE = "armed"
DEVICE_STATES = (SAFE_STATE, ARMED_STATE)

VERDICT_MET = "safe-and-arm-met"
VERDICT_NOT_MET = "safe-and-arm-not-met"

DEFAULT_SA_POLICY = {
    "min_interrupt_offset_ratio": 1.0,
    "min_barrier_thickness_mm": 2.0,
    "min_independent_arming_events": 2,
    "min_safe_lock_margin": 2.0,
    "min_monitor_isolation_mohm": 20.0,
    "require_de_arm": True,
    "require_both_positions_monitored": True,
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

    An offset ratio or a torque margin sitting exactly on its limit can
    land a few units in the last place the wrong side of it once the
    arithmetic has run. The limit is never relaxed; only the comparison
    tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_sa_policy(policy):
    """Check a policy carries every limit the safe-and-arm gates need."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "min_interrupt_offset_ratio",
        "min_barrier_thickness_mm",
        "min_safe_lock_margin",
        "min_monitor_isolation_mohm",
    ):
        _require_positive("policy %s" % key, policy.get(key))
    _require_count(
        "policy min_independent_arming_events",
        policy.get("min_independent_arming_events"),
        2,
    )
    _require_bool("policy require_de_arm", policy.get("require_de_arm"))
    _require_bool(
        "policy require_both_positions_monitored",
        policy.get("require_both_positions_monitored"),
    )
    return policy


def validate_arming_event(record):
    """Normalize one declared arming event into a checked record."""
    if not isinstance(record, dict):
        raise ValueError("arming event must be a mapping, got %r" % (record,))
    event_id = _require_text("arming event id", record.get("id"))
    return {
        "id": event_id,
        "stimulus": _require_text(
            "arming event %s stimulus" % event_id, record.get("stimulus")
        ),
        "source": _require_text(
            "arming event %s source" % event_id, record.get("source")
        ),
        "reversible": _require_bool(
            "arming event %s reversible" % event_id,
            record.get("reversible", False),
        ),
    }


def validate_sa_device(record):
    """Normalize one safe and arm device into a checked record."""
    if not isinstance(record, dict):
        raise ValueError("device must be a mapping, got %r" % (record,))
    device_id = _require_text("device id", record.get("id"))
    events = record.get("arming_events")
    if not isinstance(events, (list, tuple)) or not events:
        raise ValueError("device %s must declare its arming events" % device_id)
    normalized_events = []
    seen = set()
    for raw in events:
        event = validate_arming_event(raw)
        if event["id"] in seen:
            raise ValueError(
                "device %s declares duplicate arming event %r"
                % (device_id, event["id"])
            )
        seen.add(event["id"])
        normalized_events.append(event)
    window = record.get("arming_time_window_s")
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError(
            "device %s arming_time_window_s must be a low-high pair" % device_id
        )
    low = _require_positive("device %s arming window low" % device_id, window[0])
    high = _require_positive("device %s arming window high" % device_id, window[1])
    if high < low:
        raise ValueError(
            "device %s arming window high is below its low bound" % device_id
        )
    return {
        "id": device_id,
        "rotor_charge_diameter_mm": _require_positive(
            "device %s rotor_charge_diameter_mm" % device_id,
            record.get("rotor_charge_diameter_mm"),
        ),
        "safe_offset_mm": _require_non_negative(
            "device %s safe_offset_mm" % device_id, record.get("safe_offset_mm")
        ),
        "barrier_thickness_mm": _require_non_negative(
            "device %s barrier_thickness_mm" % device_id,
            record.get("barrier_thickness_mm"),
        ),
        "rotor_mass_kg": _require_positive(
            "device %s rotor_mass_kg" % device_id, record.get("rotor_mass_kg")
        ),
        "rotor_offset_arm_m": _require_positive(
            "device %s rotor_offset_arm_m" % device_id,
            record.get("rotor_offset_arm_m"),
        ),
        "safe_lock_torque_nm": _require_positive(
            "device %s safe_lock_torque_nm" % device_id,
            record.get("safe_lock_torque_nm"),
        ),
        "safe_position_monitored": _require_bool(
            "device %s safe_position_monitored" % device_id,
            record.get("safe_position_monitored", False),
        ),
        "armed_position_monitored": _require_bool(
            "device %s armed_position_monitored" % device_id,
            record.get("armed_position_monitored", False),
        ),
        "monitor_isolation_mohm": _require_non_negative(
            "device %s monitor_isolation_mohm" % device_id,
            record.get("monitor_isolation_mohm"),
        ),
        "de_arm_capable": _require_bool(
            "device %s de_arm_capable" % device_id,
            record.get("de_arm_capable", False),
        ),
        "arming_time_s": _require_positive(
            "device %s arming_time_s" % device_id, record.get("arming_time_s")
        ),
        "arming_time_window_s": (low, high),
        "arming_events": normalized_events,
    }


def validate_shock_case(case):
    """Normalize the environment the safe state has to survive."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    return {
        "shock_acceleration_g": _require_positive(
            "case shock_acceleration_g", case.get("shock_acceleration_g")
        )
    }


def interrupt_offset_ratio(record):
    """Safe-state offset of the rotor lead, in charge diameters."""
    device = validate_sa_device(record)
    return device["safe_offset_mm"] / device["rotor_charge_diameter_mm"]


def interrupt_verdict(record, policy=DEFAULT_SA_POLICY):
    """Grade the out-of-line interrupt and the barrier behind it."""
    validate_sa_policy(policy)
    device = validate_sa_device(record)
    ratio = interrupt_offset_ratio(record)
    findings = []
    if not _at_least(ratio, policy["min_interrupt_offset_ratio"]):
        findings.append(
            "%s offsets its rotor lead by %.3f charge diameters in the safe "
            "state, below the %.3f required to interrupt the train"
            % (device["id"], ratio, policy["min_interrupt_offset_ratio"])
        )
    if not _at_least(
        device["barrier_thickness_mm"], policy["min_barrier_thickness_mm"]
    ):
        findings.append(
            "%s stands %.2f mm of barrier between donor and acceptor, below "
            "the %.2f mm required"
            % (
                device["id"],
                device["barrier_thickness_mm"],
                policy["min_barrier_thickness_mm"],
            )
        )
    return {
        "gate": "interrupt",
        "offset_ratio": ratio,
        "compliant": not findings,
        "findings": findings,
    }


def independence_verdict(record, policy=DEFAULT_SA_POLICY):
    """Count the arming events and reject any that share one source.

    Two events driven from the same source are one event with two
    names, so a device that looks doubly interlocked can still be
    armed by a single failure upstream of both.
    """
    validate_sa_policy(policy)
    device = validate_sa_device(record)
    events = device["arming_events"]
    by_source = {}
    for event in events:
        by_source.setdefault(event["source"], []).append(event["id"])
    shared = {
        source: sorted(ids) for source, ids in by_source.items() if len(ids) > 1
    }
    independent = len(by_source)
    findings = []
    if independent < policy["min_independent_arming_events"]:
        findings.append(
            "%s can be armed by %d independent event(s), below the %d required"
            % (device["id"], independent, policy["min_independent_arming_events"])
        )
    for source in sorted(shared):
        findings.append(
            "%s drives arming events %s from the single source %s, so they "
            "are not independent"
            % (device["id"], ", ".join(shared[source]), source)
        )
    return {
        "gate": "independence",
        "declared_events": len(events),
        "independent_sources": independent,
        "shared_sources": shared,
        "compliant": not findings,
        "findings": findings,
    }


def inertial_torque_nm(mass_kg, acceleration_g, arm_m):
    """Torque the shock environment applies about the rotor pivot."""
    mass = _require_positive("mass_kg", mass_kg)
    acceleration = _require_positive("acceleration_g", acceleration_g)
    arm = _require_positive("arm_m", arm_m)
    return mass * acceleration * STANDARD_GRAVITY_M_S2 * arm


def retention_verdict(record, case, policy=DEFAULT_SA_POLICY):
    """Grade the safe-position lock against the shock environment."""
    validate_sa_policy(policy)
    device = validate_sa_device(record)
    shock = validate_shock_case(case)
    applied = inertial_torque_nm(
        device["rotor_mass_kg"],
        shock["shock_acceleration_g"],
        device["rotor_offset_arm_m"],
    )
    margin = device["safe_lock_torque_nm"] / applied
    ok = _at_least(margin, policy["min_safe_lock_margin"])
    findings = []
    if not ok:
        findings.append(
            "%s locks the safe position with %.4f Nm against a %.4f Nm "
            "inertial torque, a margin of %.3f below the required %.3f"
            % (
                device["id"],
                device["safe_lock_torque_nm"],
                applied,
                margin,
                policy["min_safe_lock_margin"],
            )
        )
    return {
        "gate": "retention",
        "applied_torque_nm": applied,
        "lock_margin": margin,
        "compliant": ok,
        "findings": findings,
    }


def monitoring_verdict(record, policy=DEFAULT_SA_POLICY):
    """Grade position indication and its isolation from the firing path."""
    validate_sa_policy(policy)
    device = validate_sa_device(record)
    findings = []
    if policy["require_both_positions_monitored"]:
        if not device["safe_position_monitored"]:
            findings.append(
                "%s does not indicate its safe position" % device["id"]
            )
        if not device["armed_position_monitored"]:
            findings.append(
                "%s does not indicate its armed position" % device["id"]
            )
    if not _at_least(
        device["monitor_isolation_mohm"], policy["min_monitor_isolation_mohm"]
    ):
        findings.append(
            "%s isolates its monitoring circuit from the firing circuit at "
            "%.2f Mohm, short of the %.2f Mohm required"
            % (
                device["id"],
                device["monitor_isolation_mohm"],
                policy["min_monitor_isolation_mohm"],
            )
        )
    return {"gate": "monitoring", "compliant": not findings, "findings": findings}


def arming_time_verdict(record):
    """Grade the measured arming time inside its declared window."""
    device = validate_sa_device(record)
    low, high = device["arming_time_window_s"]
    measured = device["arming_time_s"]
    ok = _at_least(measured, low) and _at_most(measured, high)
    findings = []
    if not ok:
        findings.append(
            "%s arms in %.4f s, outside the declared %.4f s to %.4f s window"
            % (device["id"], measured, low, high)
        )
    return {
        "gate": "arming-time",
        "window_s": (low, high),
        "compliant": ok,
        "findings": findings,
    }


def de_arm_verdict(record, policy=DEFAULT_SA_POLICY):
    """Grade whether the device can be returned to the safe state."""
    validate_sa_policy(policy)
    device = validate_sa_device(record)
    findings = []
    if policy["require_de_arm"] and not device["de_arm_capable"]:
        findings.append(
            "%s cannot be returned to safe once armed, so an aborted "
            "sequence leaves the train closed" % device["id"]
        )
    return {"gate": "de-arm", "compliant": not findings, "findings": findings}


def assess_sa_device(record, case, policy=DEFAULT_SA_POLICY):
    """Full clause 4.11.5 screen over one safe and arm device."""
    validate_sa_policy(policy)
    device = validate_sa_device(record)
    gates = {
        "interrupt": interrupt_verdict(record, policy),
        "independence": independence_verdict(record, policy),
        "retention": retention_verdict(record, case, policy),
        "monitoring": monitoring_verdict(record, policy),
        "arming-time": arming_time_verdict(record),
        "de-arm": de_arm_verdict(record, policy),
    }
    findings = []
    failed = []
    for name in GATES:
        gate = gates[name]
        findings.extend(gate["findings"])
        if not gate["compliant"]:
            failed.append(name)
    compliant = not failed
    return {
        "id": device["id"],
        "gates": gates,
        "failed_gates": failed,
        "compliant": compliant,
        "verdict": VERDICT_MET if compliant else VERDICT_NOT_MET,
        "findings": findings,
    }


def assess_sa_devices(devices, case, policy=DEFAULT_SA_POLICY):
    """Screen a set of safe and arm devices and group the outcome."""
    validate_sa_policy(policy)
    if not isinstance(devices, (list, tuple)) or not devices:
        raise ValueError("devices must contain at least one device")
    results = []
    seen = set()
    for raw in devices:
        result = assess_sa_device(raw, case, policy)
        if result["id"] in seen:
            raise ValueError("duplicate device id %r" % result["id"])
        seen.add(result["id"])
        results.append(result)
    rejected = [r["id"] for r in results if not r["compliant"]]
    findings = []
    for result in results:
        findings.extend(result["findings"])
    compliant = not rejected
    return {
        "devices": results,
        "accepted": [r["id"] for r in results if r["compliant"]],
        "rejected": rejected,
        "compliant": compliant,
        "verdict": VERDICT_MET if compliant else VERDICT_NOT_MET,
        "findings": findings,
    }
