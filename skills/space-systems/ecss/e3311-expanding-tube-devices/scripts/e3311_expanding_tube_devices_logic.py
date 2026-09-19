"""Screen for an expanding-tube contained separation device.

Anchor: ECSS-E-ST-33-11C clause 4.11.8. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An expanding-tube separation device is a flattened metal tube with an
explosive core running through it, fitted behind a notched separation
plane. On firing the tube swells; the swelling pushes the plane apart
at its notch; the tube itself never opens. That last clause is the
whole point of the device, and it is what makes the screen two-sided
rather than a sizing exercise.

Two windows come out of the arithmetic rather than out of a table:

    core load     bounded below by the expansion stroke needed to
                  fracture the ligament, and above by the pressure
                  the tube can contain without rupturing
    ligament      bounded below by the flight load the separation
                  plane must carry until firing, and above by the
                  thickness the delivered force can actually sever

Either window can be empty. When the structural demand on the
ligament exceeds what the available force will part, no thickness
satisfies both requirements and the design is not marginal, it is
impossible -- which is a finding the clause wants surfaced rather
than tuned around.

The screen closes with containment, contained-debris verification,
and the severance time of a joint fired from both ends, where the
last place to part is the meeting point of the two detonations.

Limits are declared policy, not physical constants: the defaults below
are a starting point and a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

GATES = (
    "core-load",
    "ligament",
    "containment",
    "severance-timing",
    "debris",
)

VERDICT_MET = "expanding-tube-met"
VERDICT_NOT_MET = "expanding-tube-not-met"

DEFAULT_EXPANDING_TUBE_POLICY = {
    "min_stroke_margin": 1.25,
    "min_containment_margin": 2.0,
    "min_severance_margin": 1.50,
    "min_structural_margin": 1.40,
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


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A window bound is a quotient of two products, so a design sitting
    exactly on one can land a few units in the last place outside it.
    The bound is never relaxed; only the comparison tolerates the
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


def validate_expanding_tube_policy(policy):
    """Check a policy carries all four margins the windows are built on."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "min_stroke_margin",
        "min_containment_margin",
        "min_severance_margin",
        "min_structural_margin",
    ):
        _require_positive("policy %s" % key, policy.get(key))
        if not _at_least(policy[key], 1.0):
            raise ValueError(
                "policy %s must be at least 1.0, got %r" % (key, policy[key])
            )
    return policy


def validate_device(record):
    """Normalize one expanding-tube assembly into a checked record."""
    if not isinstance(record, dict):
        raise ValueError("device must be a mapping, got %r" % (record,))
    device_id = _require_text("device id", record.get("id"))
    return {
        "id": device_id,
        "core_load_g_per_m": _require_positive(
            "device %s core_load_g_per_m" % device_id,
            record.get("core_load_g_per_m"),
        ),
        "expansion_coefficient_mm_per_g_per_m": _require_positive(
            "device %s expansion_coefficient_mm_per_g_per_m" % device_id,
            record.get("expansion_coefficient_mm_per_g_per_m"),
        ),
        "required_stroke_mm": _require_positive(
            "device %s required_stroke_mm" % device_id,
            record.get("required_stroke_mm"),
        ),
        "pressure_coefficient_mpa_per_g_per_m": _require_positive(
            "device %s pressure_coefficient_mpa_per_g_per_m" % device_id,
            record.get("pressure_coefficient_mpa_per_g_per_m"),
        ),
        "tube_burst_pressure_mpa": _require_positive(
            "device %s tube_burst_pressure_mpa" % device_id,
            record.get("tube_burst_pressure_mpa"),
        ),
        "force_coefficient_kn_per_g_per_m": _require_positive(
            "device %s force_coefficient_kn_per_g_per_m" % device_id,
            record.get("force_coefficient_kn_per_g_per_m"),
        ),
        "severance_coefficient_kn_per_mm": _require_positive(
            "device %s severance_coefficient_kn_per_mm" % device_id,
            record.get("severance_coefficient_kn_per_mm"),
        ),
        "ligament_thickness_mm": _require_positive(
            "device %s ligament_thickness_mm" % device_id,
            record.get("ligament_thickness_mm"),
        ),
        "ligament_strength_kn_per_mm": _require_positive(
            "device %s ligament_strength_kn_per_mm" % device_id,
            record.get("ligament_strength_kn_per_mm"),
        ),
        "limit_load_kn": _require_positive(
            "device %s limit_load_kn" % device_id, record.get("limit_load_kn")
        ),
        "joint_length_m": _require_positive(
            "device %s joint_length_m" % device_id, record.get("joint_length_m")
        ),
        "detonation_velocity_m_s": _require_positive(
            "device %s detonation_velocity_m_s" % device_id,
            record.get("detonation_velocity_m_s"),
        ),
        "end_a_delay_s": _require_non_negative(
            "device %s end_a_delay_s" % device_id, record.get("end_a_delay_s", 0.0)
        ),
        "end_b_delay_s": _require_non_negative(
            "device %s end_b_delay_s" % device_id, record.get("end_b_delay_s", 0.0)
        ),
        "max_severance_time_s": _require_positive(
            "device %s max_severance_time_s" % device_id,
            record.get("max_severance_time_s"),
        ),
        "debris_contained": _require_bool(
            "device %s debris_contained" % device_id,
            record.get("debris_contained", False),
        ),
    }


def expansion_stroke_mm(record):
    """Tube swell the installed core load produces."""
    device = validate_device(record)
    return (
        device["core_load_g_per_m"]
        * device["expansion_coefficient_mm_per_g_per_m"]
    )


def internal_pressure_mpa(record):
    """Pressure the installed core load raises inside the tube."""
    device = validate_device(record)
    return (
        device["core_load_g_per_m"]
        * device["pressure_coefficient_mpa_per_g_per_m"]
    )


def delivered_force_kn(record):
    """Force the swelling tube applies across the separation plane."""
    device = validate_device(record)
    return (
        device["core_load_g_per_m"]
        * device["force_coefficient_kn_per_g_per_m"]
    )


def core_load_window_g_per_m(record, policy=DEFAULT_EXPANDING_TUBE_POLICY):
    """Core loads that both fracture the ligament and stay contained."""
    validate_expanding_tube_policy(policy)
    device = validate_device(record)
    low = (
        device["required_stroke_mm"]
        * policy["min_stroke_margin"]
        / device["expansion_coefficient_mm_per_g_per_m"]
    )
    high = device["tube_burst_pressure_mpa"] / (
        device["pressure_coefficient_mpa_per_g_per_m"]
        * policy["min_containment_margin"]
    )
    return {
        "low_g_per_m": low,
        "high_g_per_m": high,
        "empty": high < low and not math.isclose(
            high, low, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        ),
    }


def ligament_window_mm(record, policy=DEFAULT_EXPANDING_TUBE_POLICY):
    """Ligament thicknesses that carry flight load and still sever."""
    validate_expanding_tube_policy(policy)
    device = validate_device(record)
    low = (
        device["limit_load_kn"]
        * policy["min_structural_margin"]
        / device["ligament_strength_kn_per_mm"]
    )
    high = delivered_force_kn(record) / (
        device["severance_coefficient_kn_per_mm"] * policy["min_severance_margin"]
    )
    return {
        "low_mm": low,
        "high_mm": high,
        "empty": high < low and not math.isclose(
            high, low, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        ),
    }


def core_load_verdict(record, policy=DEFAULT_EXPANDING_TUBE_POLICY):
    """Grade the installed core load against its two-sided window."""
    validate_expanding_tube_policy(policy)
    device = validate_device(record)
    window = core_load_window_g_per_m(record, policy)
    load = device["core_load_g_per_m"]
    findings = []
    if window["empty"]:
        findings.append(
            "%s has no admissible core load: fracturing the ligament needs at "
            "least %.4f g/m and containing the tube allows at most %.4f g/m"
            % (device["id"], window["low_g_per_m"], window["high_g_per_m"])
        )
    else:
        if not _at_least(load, window["low_g_per_m"]):
            findings.append(
                "%s carries %.4f g/m, below the %.4f g/m needed to swell the "
                "tube far enough to fracture the ligament"
                % (device["id"], load, window["low_g_per_m"])
            )
        if not _at_most(load, window["high_g_per_m"]):
            findings.append(
                "%s carries %.4f g/m, above the %.4f g/m the tube can contain "
                "with margin" % (device["id"], load, window["high_g_per_m"])
            )
    return {
        "gate": "core-load",
        "window": window,
        "stroke_mm": expansion_stroke_mm(record),
        "compliant": not findings,
        "findings": findings,
    }


def ligament_verdict(record, policy=DEFAULT_EXPANDING_TUBE_POLICY):
    """Grade the ligament thickness against its two-sided window."""
    validate_expanding_tube_policy(policy)
    device = validate_device(record)
    window = ligament_window_mm(record, policy)
    thickness = device["ligament_thickness_mm"]
    findings = []
    if window["empty"]:
        findings.append(
            "%s has no admissible ligament: carrying the flight load needs at "
            "least %.4f mm and severing it allows at most %.4f mm"
            % (device["id"], window["low_mm"], window["high_mm"])
        )
    else:
        if not _at_least(thickness, window["low_mm"]):
            findings.append(
                "%s leaves a %.4f mm ligament, below the %.4f mm the flight "
                "load needs with margin"
                % (device["id"], thickness, window["low_mm"])
            )
        if not _at_most(thickness, window["high_mm"]):
            findings.append(
                "%s leaves a %.4f mm ligament, above the %.4f mm the delivered "
                "force will sever with margin"
                % (device["id"], thickness, window["high_mm"])
            )
    return {
        "gate": "ligament",
        "window": window,
        "delivered_force_kn": delivered_force_kn(record),
        "compliant": not findings,
        "findings": findings,
    }


def containment_verdict(record, policy=DEFAULT_EXPANDING_TUBE_POLICY):
    """Grade the tube against rupture, the device's defining requirement."""
    validate_expanding_tube_policy(policy)
    device = validate_device(record)
    pressure = internal_pressure_mpa(record)
    margin = device["tube_burst_pressure_mpa"] / pressure
    ok = _at_least(margin, policy["min_containment_margin"])
    findings = []
    if not ok:
        findings.append(
            "%s raises %.3f MPa inside a tube that bursts at %.3f MPa, a "
            "margin of %.3f below the required %.3f"
            % (
                device["id"],
                pressure,
                device["tube_burst_pressure_mpa"],
                margin,
                policy["min_containment_margin"],
            )
        )
    return {
        "gate": "containment",
        "internal_pressure_mpa": pressure,
        "containment_margin": margin,
        "compliant": ok,
        "findings": findings,
    }


def meeting_point_m(record):
    """Where two detonations fired from opposite ends meet, from end A."""
    device = validate_device(record)
    length = device["joint_length_m"]
    velocity = device["detonation_velocity_m_s"]
    offset = velocity * (device["end_b_delay_s"] - device["end_a_delay_s"])
    position = 0.5 * (length + offset)
    return min(length, max(0.0, position))


def severance_time_s(record):
    """Time until the last point on the joint has parted."""
    device = validate_device(record)
    position = meeting_point_m(record)
    velocity = device["detonation_velocity_m_s"]
    from_a = device["end_a_delay_s"] + position / velocity
    from_b = device["end_b_delay_s"] + (
        device["joint_length_m"] - position
    ) / velocity
    return min(from_a, from_b)


def severance_timing_verdict(record):
    """Grade the full-joint severance time against its requirement."""
    device = validate_device(record)
    elapsed = severance_time_s(record)
    ok = _at_most(elapsed, device["max_severance_time_s"])
    findings = []
    if not ok:
        findings.append(
            "%s parts its last point at %.6f s, above the %.6f s allowed"
            % (device["id"], elapsed, device["max_severance_time_s"])
        )
    return {
        "gate": "severance-timing",
        "meeting_point_m": meeting_point_m(record),
        "severance_time_s": elapsed,
        "compliant": ok,
        "findings": findings,
    }


def debris_verdict(record):
    """Grade the contained-debris verification the device exists to give."""
    device = validate_device(record)
    findings = []
    if not device["debris_contained"]:
        findings.append(
            "%s has no contained-debris verification on record, so the one "
            "property that distinguishes it from a cutting charge is unproven"
            % device["id"]
        )
    return {"gate": "debris", "compliant": not findings, "findings": findings}


def assess_expanding_tube_device(record, policy=DEFAULT_EXPANDING_TUBE_POLICY):
    """Full clause 4.11.8 screen over one expanding-tube assembly."""
    validate_expanding_tube_policy(policy)
    device = validate_device(record)
    gates = {
        "core-load": core_load_verdict(record, policy),
        "ligament": ligament_verdict(record, policy),
        "containment": containment_verdict(record, policy),
        "severance-timing": severance_timing_verdict(record),
        "debris": debris_verdict(record),
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


def assess_expanding_tube_devices(devices, policy=DEFAULT_EXPANDING_TUBE_POLICY):
    """Screen a set of expanding-tube assemblies and group the outcome."""
    validate_expanding_tube_policy(policy)
    if not isinstance(devices, (list, tuple)) or not devices:
        raise ValueError("devices must contain at least one assembly")
    results = []
    seen = set()
    for raw in devices:
        result = assess_expanding_tube_device(raw, policy)
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
