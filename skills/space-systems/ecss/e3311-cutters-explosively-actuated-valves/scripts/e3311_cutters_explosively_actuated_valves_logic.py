#!/usr/bin/env python3
"""Explosive cable and pipe cutters, and explosively actuated valves.

Anchor: ECSS-E-ST-33-11C clauses 4.12.5 and 4.12.6. The procedure below
is a paraphrase into implementable steps; no standard text is reproduced.

A cutter is an energy problem. The blade travels while the section it is
severing reduces, so the quantity that decides severance is work over
travel, taken on the section the blade actually shears:

    solid-round   the full circle
    cable-bundle  the summed strand areas, not the jacket envelope
    tube          the annulus between the outer and inner diameters

    required work = shear strength x shear area x travel x engagement
    delivered work = cartridge rating x conversion efficiency

The anvil is a pass condition of its own: with no reaction opposite the
blade the member bends instead of shearing.

A valve is a force problem with a pressure term. The ram moves against
the worst-case line pressure across the seat area plus the friction of
the seals it drags, and the post-actuation leak rate is graded next to
the actuation margin, because a valve that moves and then seeps has
changed the failure rather than removed it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DEVICE_KINDS = ("cable-cutter", "pipe-cutter", "explosive-valve")
MEMBER_SECTIONS = ("solid-round", "cable-bundle", "tube")
VALVE_ACTIONS = ("normally-open-to-closed", "normally-closed-to-open")

CUT_MET = "cut-energy-margin-met"
CUT_NOT_MET = "cut-energy-margin-not-met"
RAM_MET = "ram-force-margin-met"
RAM_NOT_MET = "ram-force-margin-not-met"
LEAK_MET = "leak-rate-within-allowance"
LEAK_NOT_MET = "leak-rate-above-allowance"

DEFAULT_SEVERANCE_POLICY = {
    "min_cut_energy_margin": 2.0,
    "min_ram_force_margin": 2.0,
    "progressive_engagement_factor": 0.5,
    "seal_break_friction_factor": {
        "normally-open-to-closed": 1.0,
        "normally-closed-to-open": 1.6,
    },
    "max_leak_rate_scc_s": 1.0e-4,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least one, got %r" % (name, value))
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    An energy or force margin is a quotient of products, so a case that
    sits exactly on the floor can land a few units in the last place
    below it. The floor is never lowered; only the comparison tolerates
    the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit with the same representation-error tolerance."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_severance_policy(policy):
    """Check a severance policy covers both actions with sane numbers."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in ("min_cut_energy_margin", "min_ram_force_margin"):
        margin = _require_positive(key, policy.get(key))
        if margin < 1.0:
            raise ValueError(
                "policy %s is below unity, which asks the device to deliver "
                "less than the job costs" % key
            )
    engagement = _require_positive(
        "progressive_engagement_factor", policy.get("progressive_engagement_factor")
    )
    if engagement > 1.0:
        raise ValueError(
            "policy progressive_engagement_factor must not exceed unity; the "
            "section reduces as the blade advances"
        )
    table = policy.get("seal_break_friction_factor")
    if not isinstance(table, dict):
        raise ValueError("policy seal_break_friction_factor must be a mapping")
    missing = set(VALVE_ACTIONS) - set(table)
    if missing:
        raise ValueError(
            "policy seal_break_friction_factor is missing entries: %s"
            % ", ".join(sorted(missing))
        )
    for action in VALVE_ACTIONS:
        _require_positive("seal_break_friction_factor[%s]" % action, table[action])
    _require_positive("max_leak_rate_scc_s", policy.get("max_leak_rate_scc_s"))
    return policy


def shear_area_m2(
    section,
    outer_diameter_m=None,
    wall_thickness_m=None,
    strand_count=None,
    strand_diameter_m=None,
):
    """Section the blade actually has to shear, by member kind."""
    _require_choice("section", section, MEMBER_SECTIONS)
    if section == "cable-bundle":
        count = _require_count("strand_count", strand_count)
        diameter = _require_positive("strand_diameter_m", strand_diameter_m)
        return count * math.pi * diameter * diameter / 4.0
    outer = _require_positive("outer_diameter_m", outer_diameter_m)
    if section == "solid-round":
        return math.pi * outer * outer / 4.0
    wall = _require_positive("wall_thickness_m", wall_thickness_m)
    if wall >= outer / 2.0:
        raise ValueError(
            "a %g m wall on a %g m outer diameter leaves no bore; the member is "
            "a solid round, not a tube" % (wall, outer)
        )
    inner = outer - 2.0 * wall
    return math.pi * (outer * outer - inner * inner) / 4.0


def required_cut_energy_j(
    area_m2, shear_strength_pa, blade_travel_m, engagement_factor=0.5
):
    """Work the severance costs over the blade travel."""
    area = _require_positive("area_m2", area_m2)
    strength = _require_positive("shear_strength_pa", shear_strength_pa)
    travel = _require_positive("blade_travel_m", blade_travel_m)
    engagement = _require_positive("engagement_factor", engagement_factor)
    if engagement > 1.0:
        raise ValueError(
            "engagement_factor must not exceed unity; the section reduces as "
            "the blade advances, got %r" % (engagement_factor,)
        )
    return strength * area * travel * engagement


def delivered_cut_energy_j(cartridge_energy_j, conversion_efficiency):
    """Useful mechanical work the cartridge output actually produces."""
    energy = _require_positive("cartridge_energy_j", cartridge_energy_j)
    efficiency = _require_positive("conversion_efficiency", conversion_efficiency)
    if efficiency >= 1.0:
        raise ValueError(
            "conversion_efficiency must be below unity; a cartridge does not "
            "turn its whole output into blade work, got %r"
            % (conversion_efficiency,)
        )
    return energy * efficiency


def valve_ram_force_n(
    line_pressure_pa,
    seat_diameter_m,
    seal_friction_n,
    action,
    policy=DEFAULT_SEVERANCE_POLICY,
):
    """Force the ram must produce against pressure and seal drag."""
    validate_severance_policy(policy)
    _require_choice("action", action, VALVE_ACTIONS)
    pressure = _require_positive("line_pressure_pa", line_pressure_pa)
    diameter = _require_positive("seat_diameter_m", seat_diameter_m)
    friction = _require_non_negative("seal_friction_n", seal_friction_n)
    seat_area = math.pi * diameter * diameter / 4.0
    factor = policy["seal_break_friction_factor"][action]
    return pressure * seat_area + factor * friction


def margin_ratio(achieved, required):
    """Ratio form used for both the cut energy and the ram force duty."""
    got = _require_positive("achieved", achieved)
    need = _require_positive("required", required)
    return got / need


def assess_leak_rate(measured_scc_s, policy=DEFAULT_SEVERANCE_POLICY):
    """Grade the post-actuation seat leakage against the allowance."""
    validate_severance_policy(policy)
    measured = _require_non_negative("measured_scc_s", measured_scc_s)
    allowance = policy["max_leak_rate_scc_s"]
    met = _at_most(measured, allowance)
    return {
        "measured_scc_s": measured,
        "allowance_scc_s": allowance,
        "within_allowance": met,
        "verdict": LEAK_MET if met else LEAK_NOT_MET,
    }


def assess_cutter(case, policy=DEFAULT_SEVERANCE_POLICY):
    """Grade a cable or pipe cutter on energy and on anvil support."""
    validate_severance_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    section = _require_choice("section", case.get("section"), MEMBER_SECTIONS)
    area = shear_area_m2(
        section,
        outer_diameter_m=case.get("outer_diameter_m"),
        wall_thickness_m=case.get("wall_thickness_m"),
        strand_count=case.get("strand_count"),
        strand_diameter_m=case.get("strand_diameter_m"),
    )
    required = required_cut_energy_j(
        area,
        case.get("shear_strength_pa"),
        case.get("blade_travel_m"),
        policy["progressive_engagement_factor"],
    )
    delivered = delivered_cut_energy_j(
        case.get("cartridge_energy_j"), case.get("conversion_efficiency")
    )
    margin = margin_ratio(delivered, required)
    floor = policy["min_cut_energy_margin"]
    energy_met = _at_least(margin, floor)
    anvil = _require_flag("anvil_supported", case.get("anvil_supported", False))
    findings = []
    if not energy_met:
        findings.append(
            "the blade delivers %.4f J against a %.4f J severance cost, a "
            "margin of %.3f below the required %.3f"
            % (delivered, required, margin, floor)
        )
    if not anvil:
        findings.append(
            "no anvil is declared opposite the blade; the member bends out of "
            "the way instead of shearing and extra cartridge energy does not "
            "supply the missing reaction"
        )
    return {
        "section": section,
        "shear_area_m2": area,
        "required_energy_j": required,
        "delivered_energy_j": delivered,
        "cut_energy_margin": margin,
        "required_cut_energy_margin": floor,
        "anvil_supported": anvil,
        "energy_verdict": CUT_MET if energy_met else CUT_NOT_MET,
        "acceptable": energy_met and anvil,
        "findings": findings,
    }


def assess_valve(case, policy=DEFAULT_SEVERANCE_POLICY):
    """Grade an explosively actuated valve on ram force and on leakage."""
    validate_severance_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    action = _require_choice("action", case.get("action"), VALVE_ACTIONS)
    required = valve_ram_force_n(
        case.get("line_pressure_pa"),
        case.get("seat_diameter_m"),
        case.get("seal_friction_n", 0.0),
        action,
        policy,
    )
    delivered = _require_positive(
        "delivered_ram_force_n", case.get("delivered_ram_force_n")
    )
    margin = margin_ratio(delivered, required)
    floor = policy["min_ram_force_margin"]
    force_met = _at_least(margin, floor)
    findings = []
    if not force_met:
        findings.append(
            "the ram delivers %.2f N against a %.2f N demand, a margin of %.3f "
            "below the required %.3f" % (delivered, required, margin, floor)
        )
    leak = case.get("post_actuation_leak_scc_s")
    if leak is None:
        leak_result = None
        leak_met = None
        findings.append(
            "no post-actuation leak rate supplied; the valve is not yet shown "
            "to hold its new seat"
        )
    else:
        leak_result = assess_leak_rate(leak, policy)
        leak_met = leak_result["within_allowance"]
        if not leak_met:
            findings.append(
                "the seat leaks %.3e scc/s against a %.3e scc/s allowance; the "
                "valve has changed the failure rather than removed it"
                % (leak_result["measured_scc_s"], leak_result["allowance_scc_s"])
            )
    return {
        "action": action,
        "required_ram_force_n": required,
        "delivered_ram_force_n": delivered,
        "ram_force_margin": margin,
        "required_ram_force_margin": floor,
        "force_verdict": RAM_MET if force_met else RAM_NOT_MET,
        "leak": leak_result,
        "acceptable": bool(force_met and leak_met),
        "findings": findings,
    }


def plan_severance_device(case, policy=DEFAULT_SEVERANCE_POLICY):
    """Full clause 4.12.5 and 4.12.6 assessment, dispatched by device kind."""
    validate_severance_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    device_kind = _require_choice(
        "device_kind", case.get("device_kind"), DEVICE_KINDS
    )
    if device_kind == "explosive-valve":
        if case.get("section") is not None:
            raise ValueError(
                "a valve case carries an action, a seat diameter and a line "
                "pressure, not a member section"
            )
        detail = assess_valve(case, policy)
    else:
        if case.get("action") is not None:
            raise ValueError(
                "a cutter case carries a member section and its dimensions, "
                "not a valve action"
            )
        detail = assess_cutter(case, policy)
        if device_kind == "pipe-cutter" and detail["section"] == "cable-bundle":
            raise ValueError(
                "a pipe-cutter case cannot declare a cable-bundle section"
            )
    return {
        "device_kind": device_kind,
        "detail": detail,
        "acceptable": detail["acceptable"],
        "verdict": "severance-acceptable"
        if detail["acceptable"]
        else "severance-rework",
        "findings": list(detail["findings"]),
    }
