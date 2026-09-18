#!/usr/bin/env python3
"""Thermal vacuum test conditions for an ECSS thermal test.

Anchor: ECSS-Q-ST-70-04C, test condition clauses for thermal vacuum. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

A thermal vacuum condition is three things at once, and each one can
invalidate the other two.

Pressure. The chamber has to sit below a declared test pressure, and that
number is not arbitrary: it is the pressure at which the gas stops
carrying heat. The check that shows it is the mean free path against the
size of the item, because once the molecules travel further than the gap
they cross, convection is gone and the item exchanges heat by radiation
and conduction alone, which is the flight condition being reproduced.

Temperature. The shroud is the cold sink, so the item cannot be driven
below the shroud temperature by the chamber. A cold limit set below the
shroud is a limit the facility cannot reach, whatever the profile says.

Sequence. Cooling before the chamber is pumped down condenses whatever is
still in the gas onto the cold item, and admitting gas onto a cold item
at the end does the same thing in reverse. Both ends of the run are
guarded by the dew point, with a declared margin.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# SI defining constant, dimensionless input to the mean free path.
BOLTZMANN_J_PER_K = 1.380649e-23

DEFAULT_VACUUM_POLICY = {
    "max_test_pressure_pa": 1.3e-3,
    "free_molecular_knudsen": 10.0,
    "molecule_diameter_m": 3.7e-10,
    "dew_point_margin_k": 5.0,
    "minimum_dwell_s": 3600.0,
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
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_vacuum_policy(policy):
    """Check a thermal vacuum policy carries usable thresholds."""
    _require_mapping("policy", policy)
    _require_positive("max_test_pressure_pa", policy.get("max_test_pressure_pa"))
    _require_positive("free_molecular_knudsen", policy.get("free_molecular_knudsen"))
    _require_positive("molecule_diameter_m", policy.get("molecule_diameter_m"))
    _require_non_negative("dew_point_margin_k", policy.get("dew_point_margin_k"))
    _require_positive("minimum_dwell_s", policy.get("minimum_dwell_s"))
    if policy["max_test_pressure_pa"] > 1.0:
        raise ValueError(
            "max_test_pressure_pa above 1 Pa is not a thermal vacuum condition"
        )
    return policy


def mean_free_path_m(pressure_pa, temperature_k, policy=DEFAULT_VACUUM_POLICY):
    """Distance a molecule travels between collisions at this condition."""
    validate_vacuum_policy(policy)
    pressure = _require_positive("pressure_pa", pressure_pa)
    temperature = _require_positive("temperature_k", temperature_k)
    diameter = policy["molecule_diameter_m"]
    return BOLTZMANN_J_PER_K * temperature / (
        math.sqrt(2.0) * math.pi * diameter * diameter * pressure
    )


def knudsen_number(pressure_pa, temperature_k, characteristic_length_m,
                   policy=DEFAULT_VACUUM_POLICY):
    """Mean free path over the length the heat has to cross."""
    length = _require_positive("characteristic_length_m", characteristic_length_m)
    return mean_free_path_m(pressure_pa, temperature_k, policy) / length


def convection_is_negligible(knudsen, policy=DEFAULT_VACUUM_POLICY):
    """True once the gas no longer carries heat across the gap."""
    validate_vacuum_policy(policy)
    value = _require_positive("knudsen", knudsen)
    return _at_least(value, policy["free_molecular_knudsen"])


def assess_test_pressure(
    chamber_base_pressure_pa,
    temperature_k,
    characteristic_length_m,
    policy=DEFAULT_VACUUM_POLICY,
):
    """Whether the chamber's pressure is a valid thermal vacuum condition."""
    validate_vacuum_policy(policy)
    pressure = _require_positive(
        "chamber_base_pressure_pa", chamber_base_pressure_pa
    )
    within_policy = _at_most(pressure, policy["max_test_pressure_pa"])
    knudsen = knudsen_number(pressure, temperature_k, characteristic_length_m, policy)
    free_molecular = convection_is_negligible(knudsen, policy)
    findings = []
    if not within_policy:
        findings.append(
            "chamber base pressure %.3e Pa is above the declared test pressure "
            "%.3e Pa" % (pressure, policy["max_test_pressure_pa"])
        )
    if not free_molecular:
        findings.append(
            "Knudsen number %.3g is below the free-molecular threshold %.3g, so the "
            "residual gas still carries heat and the run is not a vacuum condition"
            % (knudsen, policy["free_molecular_knudsen"])
        )
    return {
        "pressure_pa": pressure,
        "mean_free_path_m": mean_free_path_m(pressure, temperature_k, policy),
        "knudsen": knudsen,
        "within_policy": within_policy,
        "free_molecular": free_molecular,
        "acceptable": within_policy and free_molecular,
        "findings": findings,
    }


def achievable_cold_limit_k(shroud_temperature_k, requested_min_k):
    """Coldest the chamber can drive the item to, and whether it is enough."""
    shroud = _require_positive("shroud_temperature_k", shroud_temperature_k)
    requested = _require_positive("requested_min_k", requested_min_k)
    reachable = _at_least(requested, shroud)
    return {
        "shroud_temperature_k": shroud,
        "requested_min_k": requested,
        "achievable_min_k": requested if reachable else shroud,
        "reachable": reachable,
    }


def repressurization_temperature_k(
    item_temperature_k, dew_point_k, policy=DEFAULT_VACUUM_POLICY
):
    """Temperature the item has to reach before dry gas is admitted."""
    validate_vacuum_policy(policy)
    item = _require_positive("item_temperature_k", item_temperature_k)
    dew_point = _require_positive("dew_point_k", dew_point_k)
    guard = dew_point + policy["dew_point_margin_k"]
    safe = _at_least(item, guard)
    return {
        "guard_k": guard,
        "item_temperature_k": item,
        "required_k": item if safe else guard,
        "safe": safe,
    }


def vacuum_dwell_time_s(
    time_constant_s, initial_offset_k, tolerance_k, outgassing_soak_s,
    policy=DEFAULT_VACUUM_POLICY,
):
    """Dwell at one extreme under vacuum: stabilization plus outgassing soak."""
    validate_vacuum_policy(policy)
    tau = _require_positive("time_constant_s", time_constant_s)
    offset = _require_positive("initial_offset_k", initial_offset_k)
    tolerance = _require_positive("tolerance_k", tolerance_k)
    soak = _require_non_negative("outgassing_soak_s", outgassing_soak_s)
    stabilization = 0.0 if offset <= tolerance else tau * math.log(offset / tolerance)
    needed = stabilization + soak
    floor = policy["minimum_dwell_s"]
    set_by = "stabilization-and-soak" if _at_least(needed, floor) else "policy-floor"
    return {
        "dwell_s": needed if _at_least(needed, floor) else floor,
        "stabilization_s": stabilization,
        "outgassing_soak_s": soak,
        "set_by": set_by,
    }


def pump_down_sequence(case):
    """Ordered run sequence with both dew-point guards in place."""
    _require_mapping("case", case)
    return (
        "mount the item and hold it at ambient temperature while the chamber pumps",
        "pump down until the chamber reaches the declared test pressure and holds it",
        "only then start the first temperature transition",
        "hold each extreme for the computed dwell, measured on the controlling sensor",
        "return the item above the dew-point guard before any gas is admitted",
        "admit dry gas to repressurize, and record the pressure and the item "
        "temperature at the moment the valve opens",
    )


def define_vacuum_conditions(case, policy=DEFAULT_VACUUM_POLICY):
    """Full thermal vacuum condition set: pressure, limits, dwell, sequence."""
    validate_vacuum_policy(policy)
    _require_mapping("case", case)
    test_max = _require_positive("test_max_k", case.get("test_max_k"))
    test_min = _require_positive("test_min_k", case.get("test_min_k"))
    if test_max <= test_min:
        raise ValueError(
            "test_max_k %g K must be above test_min_k %g K" % (test_max, test_min)
        )
    pressure = assess_test_pressure(
        case.get("chamber_base_pressure_pa"),
        test_max,
        case.get("characteristic_length_m"),
        policy,
    )
    cold = achievable_cold_limit_k(case.get("shroud_temperature_k"), test_min)
    hot_dwell = vacuum_dwell_time_s(
        case.get("time_constant_s"),
        test_max - test_min,
        case.get("stabilization_tolerance_k", 1.0),
        case.get("hot_outgassing_soak_s", 0.0),
        policy,
    )
    cold_dwell = vacuum_dwell_time_s(
        case.get("time_constant_s"),
        test_max - test_min,
        case.get("stabilization_tolerance_k", 1.0),
        case.get("cold_outgassing_soak_s", 0.0),
        policy,
    )
    repressurization = repressurization_temperature_k(
        case.get("repressurization_item_temperature_k"),
        case.get("dew_point_k"),
        policy,
    )
    findings = list(pressure["findings"])
    duties = []
    if not cold["reachable"]:
        findings.append(
            "the requested cold limit %.2f K is below the shroud at %.2f K, so the "
            "chamber cannot reach it and the profile has to be restated"
            % (cold["requested_min_k"], cold["shroud_temperature_k"])
        )
    if not repressurization["safe"]:
        findings.append(
            "the item would be at %.2f K when gas is admitted, below the dew-point "
            "guard at %.2f K, so moisture would condense on it"
            % (repressurization["item_temperature_k"], repressurization["guard_k"])
        )
    duties.append(
        "hold the pressure below the declared test pressure for the whole run, not "
        "only at the moment the first transition starts"
    )
    if hot_dwell["set_by"] == "policy-floor" or cold_dwell["set_by"] == "policy-floor":
        duties.append(
            "record that a dwell is set by the policy floor rather than by the "
            "item's response and its outgassing soak"
        )
    return {
        "test_min_k": test_min,
        "test_max_k": test_max,
        "pressure": pressure,
        "cold_limit": cold,
        "hot_dwell": hot_dwell,
        "cold_dwell": cold_dwell,
        "repressurization": repressurization,
        "sequence": pump_down_sequence(case),
        "acceptable": pressure["acceptable"] and cold["reachable"] and repressurization["safe"],
        "duties": duties,
        "findings": findings,
    }
