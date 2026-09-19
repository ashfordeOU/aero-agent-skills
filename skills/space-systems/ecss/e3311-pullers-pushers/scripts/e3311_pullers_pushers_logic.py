#!/usr/bin/env python3
"""Explosive pin pullers and pin pushers.

Anchor: ECSS-E-ST-33-11C clauses 4.12.3 and 4.12.4. The procedure below
is a paraphrase into implementable steps; no standard text is reproduced.

A puller and a pusher are the same machine run in opposite directions: a
cartridge fills a chamber, pressure acts across a bore area, and the
piston travels a stroke. Acceptance has two independent duties.

    delivered work = mean effective pressure x bore area x stroke
    required work  = resisting force x required stroke
    resisting force = external load + friction from the side load
    required stroke = engagement depth + misalignment allowance

Peak chamber pressure is not the pressure that does the work: the gas
expands behind the moving piston, so the work integral is taken on a
mean effective pressure, a declared fraction of the peak. Whatever work
the piston does not spend on the load arrives at the end stop as kinetic
energy, which is a shock input rather than spare capability.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DEVICE_KINDS = ("pin-puller", "pin-pusher")

WORK_MET = "work-margin-met"
WORK_NOT_MET = "work-margin-not-met"
STROKE_MET = "stroke-margin-met"
STROKE_NOT_MET = "stroke-margin-not-met"
END_STOP_MET = "end-stop-energy-within-allowance"
END_STOP_NOT_MET = "end-stop-energy-above-allowance"

DEFAULT_ACTUATOR_POLICY = {
    "min_work_margin": {"pin-puller": 2.0, "pin-pusher": 2.0},
    "min_stroke_margin": 1.5,
    "max_end_stop_energy_j": 5.0,
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


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A work or stroke margin is a quotient of products, so a case that
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


def validate_actuator_policy(policy):
    """Check an actuator policy covers both device kinds with sane numbers."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    table = policy.get("min_work_margin")
    if not isinstance(table, dict):
        raise ValueError("policy min_work_margin must be a mapping")
    missing = set(DEVICE_KINDS) - set(table)
    if missing:
        raise ValueError(
            "policy min_work_margin is missing entries: %s" % ", ".join(sorted(missing))
        )
    for kind in DEVICE_KINDS:
        margin = _require_positive("min_work_margin[%s]" % kind, table[kind])
        if margin < 1.0:
            raise ValueError(
                "policy min_work_margin[%s] is below unity, which asks the "
                "piston to do less work than the release costs" % kind
            )
    stroke_margin = _require_positive(
        "min_stroke_margin", policy.get("min_stroke_margin")
    )
    if stroke_margin < 1.0:
        raise ValueError(
            "policy min_stroke_margin is below unity, which asks the piston to "
            "travel less than the release needs"
        )
    _require_positive("max_end_stop_energy_j", policy.get("max_end_stop_energy_j"))
    return policy


def bore_area_m2(bore_diameter_m):
    """Piston face area the chamber pressure acts across."""
    diameter = _require_positive("bore_diameter_m", bore_diameter_m)
    return math.pi * diameter * diameter / 4.0


def piston_force_n(pressure_pa, bore_diameter_m):
    """Axial force the chamber pressure produces across the bore."""
    pressure = _require_positive("pressure_pa", pressure_pa)
    return pressure * bore_area_m2(bore_diameter_m)


def mean_effective_pressure_pa(peak_pressure_pa, effective_fraction):
    """Pressure that actually does the work as the gas expands."""
    peak = _require_positive("peak_pressure_pa", peak_pressure_pa)
    fraction = _require_positive("effective_fraction", effective_fraction)
    if fraction >= 1.0:
        raise ValueError(
            "effective_fraction must be below unity; the gas expands behind a "
            "moving piston, got %r" % (effective_fraction,)
        )
    return peak * fraction


def delivered_work_j(
    peak_pressure_pa, bore_diameter_m, available_stroke_m, effective_fraction
):
    """Work the piston delivers over its available travel."""
    mean_pressure = mean_effective_pressure_pa(peak_pressure_pa, effective_fraction)
    stroke = _require_positive("available_stroke_m", available_stroke_m)
    return piston_force_n(mean_pressure, bore_diameter_m) * stroke


def resisting_force_n(external_load_n, side_load_n=0.0, friction_coefficient=0.0):
    """External load plus the friction the side load presses onto the pin."""
    load = _require_non_negative("external_load_n", external_load_n)
    side = _require_non_negative("side_load_n", side_load_n)
    friction = _require_non_negative("friction_coefficient", friction_coefficient)
    total = load + friction * side
    if total <= 0.0:
        raise ValueError(
            "the resisting force resolves to zero; an actuator cannot be graded "
            "against no load at all"
        )
    return total


def required_stroke_m(engagement_depth_m, misalignment_allowance_m=0.0):
    """Travel the release needs once take-up is spent."""
    depth = _require_positive("engagement_depth_m", engagement_depth_m)
    allowance = _require_non_negative(
        "misalignment_allowance_m", misalignment_allowance_m
    )
    return depth + allowance


def required_work_j(resisting_n, needed_stroke_m):
    """Work the release costs over the stroke it actually needs."""
    force = _require_positive("resisting_n", resisting_n)
    stroke = _require_positive("needed_stroke_m", needed_stroke_m)
    return force * stroke


def margin_ratio(achieved, required):
    """Ratio form used for both the work and the stroke duty."""
    got = _require_positive("achieved", achieved)
    need = _require_positive("required", required)
    return got / need


def end_stop_energy_j(delivered_work, required_work):
    """Surplus work that arrives at the end stop as a shock input."""
    delivered = _require_positive("delivered_work", delivered_work)
    required = _require_positive("required_work", required_work)
    return max(0.0, delivered - required)


def end_stop_velocity_m_s(energy_j, moving_mass_kg):
    """Impact velocity the surplus energy produces in the moving mass."""
    energy = _require_non_negative("energy_j", energy_j)
    mass = _require_positive("moving_mass_kg", moving_mass_kg)
    return math.sqrt(2.0 * energy / mass)


def plan_actuator(case, policy=DEFAULT_ACTUATOR_POLICY):
    """Full clause 4.12.3 and 4.12.4 assessment with a combined verdict."""
    validate_actuator_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    device_kind = _require_choice(
        "device_kind", case.get("device_kind"), DEVICE_KINDS
    )
    available_stroke = _require_positive(
        "available_stroke_m", case.get("available_stroke_m")
    )
    delivered = delivered_work_j(
        case.get("peak_pressure_pa"),
        case.get("bore_diameter_m"),
        available_stroke,
        case.get("effective_pressure_fraction"),
    )
    resisting = resisting_force_n(
        case.get("external_load_n", 0.0),
        case.get("side_load_n", 0.0),
        case.get("friction_coefficient", 0.0),
    )
    needed_stroke = required_stroke_m(
        case.get("engagement_depth_m"), case.get("misalignment_allowance_m", 0.0)
    )
    required = required_work_j(resisting, needed_stroke)
    work_margin = margin_ratio(delivered, required)
    stroke_margin = margin_ratio(available_stroke, needed_stroke)
    work_floor = policy["min_work_margin"][device_kind]
    stroke_floor = policy["min_stroke_margin"]
    work_met = _at_least(work_margin, work_floor)
    stroke_met = _at_least(stroke_margin, stroke_floor)
    findings = []
    if not work_met:
        findings.append(
            "%s delivers %.4f J against a %.4f J release cost, a work margin of "
            "%.3f below the required %.3f"
            % (device_kind, delivered, required, work_margin, work_floor)
        )
    if not stroke_met:
        findings.append(
            "available stroke %.5f m against a needed %.5f m, a stroke margin of "
            "%.3f below the required %.3f"
            % (available_stroke, needed_stroke, stroke_margin, stroke_floor)
        )
    surplus = end_stop_energy_j(delivered, required)
    end_stop_met = _at_most(surplus, policy["max_end_stop_energy_j"])
    if not end_stop_met:
        findings.append(
            "%.4f J of surplus work arrives at the end stop against a %.4f J "
            "shock allowance" % (surplus, policy["max_end_stop_energy_j"])
        )
    moving_mass = case.get("moving_mass_kg")
    velocity = None
    if moving_mass is not None:
        velocity = end_stop_velocity_m_s(surplus, moving_mass)
    else:
        findings.append(
            "no moving mass supplied; the end-stop impact velocity is not yet "
            "derived from the surplus energy"
        )
    acceptable = work_met and stroke_met and end_stop_met
    return {
        "device_kind": device_kind,
        "delivered_work_j": delivered,
        "required_work_j": required,
        "resisting_force_n": resisting,
        "work_margin": work_margin,
        "required_work_margin": work_floor,
        "work_verdict": WORK_MET if work_met else WORK_NOT_MET,
        "available_stroke_m": available_stroke,
        "required_stroke_m": needed_stroke,
        "stroke_margin": stroke_margin,
        "required_stroke_margin": stroke_floor,
        "stroke_verdict": STROKE_MET if stroke_met else STROKE_NOT_MET,
        "end_stop_energy_j": surplus,
        "end_stop_velocity_m_s": velocity,
        "end_stop_verdict": END_STOP_MET if end_stop_met else END_STOP_NOT_MET,
        "acceptable": acceptable,
        "verdict": "actuator-acceptable" if acceptable else "actuator-rework",
        "findings": findings,
    }
