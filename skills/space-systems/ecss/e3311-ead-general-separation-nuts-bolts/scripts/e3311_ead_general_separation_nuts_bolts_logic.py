#!/usr/bin/env python3
"""Explosively actuated devices, separation nuts and explosive bolts.

Anchor: ECSS-E-ST-33-11C clauses 4.12.1 and 4.12.2. The procedure below
is a paraphrase into implementable steps; no standard text is reproduced.

An explosively actuated device turns one cartridge output into one
mechanical action and cannot be tested on the article that flies. The
assessment is therefore a work balance carried as a ratio:

    delivered work = cartridge rating x conversion efficiency
    required work  = the cost of the release, which depends on the kind

Device kinds and what the release costs
    separation-nut  segments driven out against the friction the clamped
                    preload generates over the segment stroke
    explosive-bolt  notch fracture energy plus the strain energy stored
                    in the stretched shank, released over the stroke
    generic-ead     direct work against the declared load over the stroke

The preload is recovered from the installation torque through the nut
factor, so it is an estimate with a wide band, not a measurement.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DEVICE_KINDS = ("separation-nut", "explosive-bolt", "generic-ead")

FUNCTION_MET = "function-margin-met"
FUNCTION_NOT_MET = "function-margin-not-met"

DEFAULT_EAD_POLICY = {
    "min_function_margin": {
        "separation-nut": 2.0,
        "explosive-bolt": 2.0,
        "generic-ead": 1.5,
    },
    "min_initiator_count": 2,
    "min_firing_circuit_count": 2,
    "max_release_time_ms": 20.0,
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
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Both sides of a work ratio are products of estimated terms, so a
    case that sits exactly on the floor can land a few units in the last
    place below it. The floor is never lowered; only the comparison
    tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit with the same representation-error tolerance."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_ead_policy(policy):
    """Check an EAD policy covers every device kind with sane numbers."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    table = policy.get("min_function_margin")
    if not isinstance(table, dict):
        raise ValueError("policy min_function_margin must be a mapping")
    missing = set(DEVICE_KINDS) - set(table)
    if missing:
        raise ValueError(
            "policy min_function_margin is missing entries: %s"
            % ", ".join(sorted(missing))
        )
    for kind in DEVICE_KINDS:
        margin = _require_positive("min_function_margin[%s]" % kind, table[kind])
        if margin < 1.0:
            raise ValueError(
                "policy min_function_margin[%s] is below unity, which asks the "
                "device to deliver less work than the release costs" % kind
            )
    _require_count("min_initiator_count", policy.get("min_initiator_count"))
    _require_count("min_firing_circuit_count", policy.get("min_firing_circuit_count"))
    _require_positive("max_release_time_ms", policy.get("max_release_time_ms"))
    return policy


def preload_from_torque_n(torque_nm, nut_factor, bolt_diameter_m):
    """Recover the joint preload from the installation torque.

    The nut factor carries the whole friction state of the joint, so the
    result is an estimate with a wide band rather than a measurement.
    """
    torque = _require_positive("torque_nm", torque_nm)
    factor = _require_positive("nut_factor", nut_factor)
    diameter = _require_positive("bolt_diameter_m", bolt_diameter_m)
    return torque / (factor * diameter)


def required_release_work_j(
    device_kind,
    preload_n,
    stroke_m,
    friction_coefficient=None,
    notch_fracture_energy_j=None,
):
    """Work the release costs, built from the term the device kind needs."""
    _require_choice("device_kind", device_kind, DEVICE_KINDS)
    preload = _require_positive("preload_n", preload_n)
    stroke = _require_positive("stroke_m", stroke_m)
    if device_kind == "separation-nut":
        if friction_coefficient is None:
            raise ValueError(
                "a separation-nut release needs a friction_coefficient; the "
                "segments are driven out against the clamped preload"
            )
        friction = _require_positive("friction_coefficient", friction_coefficient)
        return friction * preload * stroke
    if device_kind == "explosive-bolt":
        if notch_fracture_energy_j is None:
            raise ValueError(
                "an explosive-bolt release needs a notch_fracture_energy_j; the "
                "severed section is paid for before the shank relaxes"
            )
        fracture = _require_positive(
            "notch_fracture_energy_j", notch_fracture_energy_j
        )
        return fracture + 0.5 * preload * stroke
    return preload * stroke


def delivered_work_j(cartridge_energy_j, conversion_efficiency):
    """Useful mechanical work the cartridge output actually produces."""
    energy = _require_positive("cartridge_energy_j", cartridge_energy_j)
    efficiency = _require_positive("conversion_efficiency", conversion_efficiency)
    if efficiency >= 1.0:
        raise ValueError(
            "conversion_efficiency must be below unity; a cartridge does not "
            "turn its whole output into mechanical work, got %r"
            % (conversion_efficiency,)
        )
    return energy * efficiency


def function_margin(delivered_work, required_work):
    """Ratio of the work delivered to the work the release costs."""
    delivered = _require_positive("delivered_work", delivered_work)
    required = _require_positive("required_work", required_work)
    return delivered / required


def assess_redundancy(
    initiator_count, firing_circuit_count, policy=DEFAULT_EAD_POLICY
):
    """Name any single point of failure on a one-shot initiation."""
    validate_ead_policy(policy)
    initiators = _require_count("initiator_count", initiator_count)
    circuits = _require_count("firing_circuit_count", firing_circuit_count)
    findings = []
    if initiators < policy["min_initiator_count"]:
        findings.append(
            "%d initiator(s) against a required %d; the initiation is a single "
            "point of failure on an action with no second attempt"
            % (initiators, policy["min_initiator_count"])
        )
    if circuits < policy["min_firing_circuit_count"]:
        findings.append(
            "%d independent firing circuit(s) against a required %d; redundant "
            "initiators sharing one circuit are not redundant"
            % (circuits, policy["min_firing_circuit_count"])
        )
    return {
        "initiator_count": initiators,
        "firing_circuit_count": circuits,
        "redundant": not findings,
        "findings": findings,
    }


def assess_containment(fragments_contained, gas_path_sealed):
    """Screen the two non-function duties that ride with every EAD."""
    contained = _require_flag("fragments_contained", fragments_contained)
    sealed = _require_flag("gas_path_sealed", gas_path_sealed)
    findings = []
    if not contained:
        findings.append(
            "the device is not declared fragment-containing; released debris "
            "is a hazard to every surface in its line of sight"
        )
    if not sealed:
        findings.append(
            "the gas path is not declared sealed; combustion products vent "
            "into the compartment the device is mounted in"
        )
    return {
        "fragments_contained": contained,
        "gas_path_sealed": sealed,
        "acceptable": not findings,
        "findings": findings,
    }


def plan_ead_assessment(case, policy=DEFAULT_EAD_POLICY):
    """Full clause 4.12.1 and 4.12.2 assessment with a combined verdict."""
    validate_ead_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    device_kind = _require_choice(
        "device_kind", case.get("device_kind"), DEVICE_KINDS
    )
    if case.get("preload_n") is not None:
        preload = _require_positive("preload_n", case.get("preload_n"))
        preload_basis = "declared"
    else:
        preload = preload_from_torque_n(
            case.get("torque_nm"),
            case.get("nut_factor"),
            case.get("bolt_diameter_m"),
        )
        preload_basis = "torque-derived"
    required = required_release_work_j(
        device_kind,
        preload,
        case.get("stroke_m"),
        case.get("friction_coefficient"),
        case.get("notch_fracture_energy_j"),
    )
    delivered = delivered_work_j(
        case.get("cartridge_energy_j"), case.get("conversion_efficiency")
    )
    margin = function_margin(delivered, required)
    floor = policy["min_function_margin"][device_kind]
    margin_met = _at_least(margin, floor)
    findings = []
    if not margin_met:
        findings.append(
            "%s delivers %.4f J against a %.4f J release cost, a margin of "
            "%.3f below the required %.3f"
            % (device_kind, delivered, required, margin, floor)
        )
    if preload_basis == "torque-derived":
        findings.append(
            "the preload is recovered from the installation torque through the "
            "nut factor; the margin has to survive the upper end of that band"
        )
    redundancy = assess_redundancy(
        case.get("initiator_count", 0), case.get("firing_circuit_count", 0), policy
    )
    findings.extend(redundancy["findings"])
    containment = assess_containment(
        case.get("fragments_contained", False), case.get("gas_path_sealed", False)
    )
    findings.extend(containment["findings"])
    release_time = case.get("release_time_ms")
    if release_time is None:
        release_time_met = None
        findings.append(
            "no release time supplied; the device is not yet shown to fit the "
            "separation sequence window"
        )
    else:
        measured = _require_non_negative("release_time_ms", release_time)
        release_time_met = _at_most(measured, policy["max_release_time_ms"])
        if not release_time_met:
            findings.append(
                "release takes %.3f ms against a %.3f ms sequence allowance"
                % (measured, policy["max_release_time_ms"])
            )
    acceptable = (
        margin_met
        and redundancy["redundant"]
        and containment["acceptable"]
        and release_time_met is True
    )
    return {
        "device_kind": device_kind,
        "preload_n": preload,
        "preload_basis": preload_basis,
        "required_work_j": required,
        "delivered_work_j": delivered,
        "function_margin": margin,
        "required_function_margin": floor,
        "margin_verdict": FUNCTION_MET if margin_met else FUNCTION_NOT_MET,
        "redundancy": redundancy,
        "containment": containment,
        "release_time_met": release_time_met,
        "acceptable": acceptable,
        "verdict": "ead-acceptable" if acceptable else "ead-rework",
        "findings": findings,
    }
