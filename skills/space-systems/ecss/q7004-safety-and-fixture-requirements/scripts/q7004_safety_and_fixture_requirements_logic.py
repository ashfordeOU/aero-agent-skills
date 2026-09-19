#!/usr/bin/env python3
"""Safety and fixturing provisions for an ECSS thermal test.

Anchor: ECSS-Q-ST-70-04C, the quality-assurance clauses covering test
safety and the mechanical fixturing of the test item. The procedure
below is a paraphrase into implementable steps; no standard text is
reproduced.

A fixture is not a shelf. It is bolted to an item that is about to be
driven across a hundred kelvin or more, and over that span the fixture
and the item change length at different rates. The difference has to go
somewhere, and if the joint is stiff it goes into the item as strain.

The safety side of the same clause is three numbers and a wait. The
chamber overshoots its set point, so the over-temperature interlock sits
above the test limit by the overshoot plus a guard band, and the whole
stack still has to clear the temperature at which the item is damaged.
Afterwards the item is hot or cold long after the chamber reads ambient,
so access waits for the item's own lag to decay to a touch-safe value.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

G0_M_PER_S2 = 9.80665

DEFAULT_FIXTURE_POLICY = {
    "allowable_strain": 2.0e-3,
    "load_safety_factor": 2.0,
    "min_load_margin": 0.0,
    "chamber_overshoot_k": 3.0,
    "interlock_guard_band_k": 2.0,
    "min_interlock_clearance_k": 5.0,
    "touch_safe_hot_k": 318.15,
    "touch_safe_cold_k": 273.15,
    "cryogenic_threshold_k": 120.0,
    "hot_surface_threshold_k": 333.15,
}

HAZARD_CRYOGENIC = "cryogenic-handling"
HAZARD_HOT_SURFACE = "hot-surface-contact"
HAZARD_VACUUM = "vacuum-implosion-and-outgassing"
HAZARD_STORED_STRAIN = "stored-strain-release"
HAZARD_LIFTING = "fixture-lifting-and-mass"

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


def validate_fixture_policy(policy):
    """Check a fixturing and safety policy carries usable limits."""
    _require_mapping("policy", policy)
    _require_positive("allowable_strain", policy.get("allowable_strain"))
    factor = _require_positive(
        "load_safety_factor", policy.get("load_safety_factor")
    )
    if factor < 1.0:
        raise ValueError(
            "load_safety_factor %g would relieve the fixture rather than "
            "protect it" % factor
        )
    _require_number("min_load_margin", policy.get("min_load_margin"))
    _require_non_negative("chamber_overshoot_k", policy.get("chamber_overshoot_k"))
    _require_non_negative(
        "interlock_guard_band_k", policy.get("interlock_guard_band_k")
    )
    _require_non_negative(
        "min_interlock_clearance_k", policy.get("min_interlock_clearance_k")
    )
    hot_touch = _require_positive("touch_safe_hot_k", policy.get("touch_safe_hot_k"))
    cold_touch = _require_positive(
        "touch_safe_cold_k", policy.get("touch_safe_cold_k")
    )
    if cold_touch >= hot_touch:
        raise ValueError(
            "touch_safe_cold_k %g K must sit below touch_safe_hot_k %g K"
            % (cold_touch, hot_touch)
        )
    _require_positive("cryogenic_threshold_k", policy.get("cryogenic_threshold_k"))
    _require_positive(
        "hot_surface_threshold_k", policy.get("hot_surface_threshold_k")
    )
    return policy


def differential_expansion_strain(
    fixture_cte_per_k, item_cte_per_k, delta_t_k
):
    """Strain the mismatch drives into a stiff fixture-to-item joint.

    Both parts see the same temperature change; the difference in their
    expansion coefficients turns that change into a length difference,
    and a joint that cannot slide carries it as strain.
    """
    fixture = _require_non_negative("fixture_cte_per_k", fixture_cte_per_k)
    item = _require_non_negative("item_cte_per_k", item_cte_per_k)
    delta_t = _require_number("delta_t_k", delta_t_k)
    return abs(fixture - item) * abs(delta_t)


def expansion_strain_margin(strain, policy=DEFAULT_FIXTURE_POLICY):
    """Margin of safety of the joint against the allowable strain."""
    validate_fixture_policy(policy)
    value = _require_non_negative("strain", strain)
    allowable = policy["allowable_strain"]
    if value == 0.0:
        return float("inf")
    return allowable / value - 1.0


def fixture_load_n(mounted_mass_kg, design_load_factor_g, policy=DEFAULT_FIXTURE_POLICY):
    """Design load the fixture carries, with the policy safety factor on."""
    validate_fixture_policy(policy)
    mass = _require_positive("mounted_mass_kg", mounted_mass_kg)
    load_factor = _require_positive(
        "design_load_factor_g", design_load_factor_g
    )
    return mass * G0_M_PER_S2 * load_factor * policy["load_safety_factor"]


def fixture_load_margin(
    mounted_mass_kg,
    design_load_factor_g,
    fixture_capacity_n,
    policy=DEFAULT_FIXTURE_POLICY,
):
    """Margin of safety of the fixture against the load it carries."""
    validate_fixture_policy(policy)
    capacity = _require_positive("fixture_capacity_n", fixture_capacity_n)
    applied = fixture_load_n(mounted_mass_kg, design_load_factor_g, policy)
    return capacity / applied - 1.0


def interlock_setpoint_k(test_limit_k, policy=DEFAULT_FIXTURE_POLICY):
    """Over-temperature interlock set point above the hot test limit."""
    validate_fixture_policy(policy)
    limit = _require_positive("test_limit_k", test_limit_k)
    return limit + policy["chamber_overshoot_k"] + policy["interlock_guard_band_k"]


def interlock_clearance_k(
    test_limit_k, item_damage_limit_k, policy=DEFAULT_FIXTURE_POLICY
):
    """Gap left between the interlock set point and the item damage limit."""
    validate_fixture_policy(policy)
    damage = _require_positive("item_damage_limit_k", item_damage_limit_k)
    setpoint = interlock_setpoint_k(test_limit_k, policy)
    return {
        "setpoint_k": setpoint,
        "item_damage_limit_k": damage,
        "clearance_k": damage - setpoint,
        "acceptable": _at_least(
            damage - setpoint, policy["min_interlock_clearance_k"]
        ),
    }


def touch_safe_cooldown_s(
    time_constant_s, item_temp_k, ambient_k, touch_safe_k
):
    """Wait before an operator may handle the item after the run.

    The item's offset from ambient decays as exp(-t / tau), so reaching a
    touch-safe temperature from the test temperature takes
    tau * ln(offset_now / offset_allowed). An item already inside the
    touch-safe band needs no wait, and the arithmetic returns zero rather
    than a negative time.
    """
    tau = _require_positive("time_constant_s", time_constant_s)
    item = _require_positive("item_temp_k", item_temp_k)
    ambient = _require_positive("ambient_k", ambient_k)
    safe = _require_positive("touch_safe_k", touch_safe_k)
    offset_now = abs(item - ambient)
    offset_allowed = abs(safe - ambient)
    if offset_allowed == 0.0:
        raise ValueError(
            "touch_safe_k equals ambient, so the item never formally arrives"
        )
    if offset_now <= offset_allowed:
        return 0.0
    return tau * math.log(offset_now / offset_allowed)


def hazard_groups(case, policy=DEFAULT_FIXTURE_POLICY):
    """Hazard groups the run falls into, categorized from its conditions."""
    validate_fixture_policy(policy)
    _require_mapping("case", case)
    cold = _require_positive("test_min_k", case.get("test_min_k"))
    hot = _require_positive("test_max_k", case.get("test_max_k"))
    if hot <= cold:
        raise ValueError(
            "test_max_k %g K must sit above test_min_k %g K" % (hot, cold)
        )
    groups = []
    if cold <= policy["cryogenic_threshold_k"]:
        groups.append(HAZARD_CRYOGENIC)
    if _at_least(hot, policy["hot_surface_threshold_k"]):
        groups.append(HAZARD_HOT_SURFACE)
    if bool(case.get("vacuum", False)):
        groups.append(HAZARD_VACUUM)
    mass = _require_positive("mounted_mass_kg", case.get("mounted_mass_kg"))
    if mass >= 25.0:
        groups.append(HAZARD_LIFTING)
    strain = differential_expansion_strain(
        case.get("fixture_cte_per_k"), case.get("item_cte_per_k"), hot - cold
    )
    if expansion_strain_margin(strain, policy) < 0.0:
        groups.append(HAZARD_STORED_STRAIN)
    return tuple(sorted(set(groups)))


def assess_safety_and_fixturing(case, policy=DEFAULT_FIXTURE_POLICY):
    """Full fixturing and safety assessment for one thermal test run."""
    validate_fixture_policy(policy)
    _require_mapping("case", case)
    cold = _require_positive("test_min_k", case.get("test_min_k"))
    hot = _require_positive("test_max_k", case.get("test_max_k"))
    if hot <= cold:
        raise ValueError(
            "test_max_k %g K must sit above test_min_k %g K" % (hot, cold)
        )
    span = hot - cold
    strain = differential_expansion_strain(
        case.get("fixture_cte_per_k"), case.get("item_cte_per_k"), span
    )
    strain_margin = expansion_strain_margin(strain, policy)
    load_margin = fixture_load_margin(
        case.get("mounted_mass_kg"),
        case.get("design_load_factor_g"),
        case.get("fixture_capacity_n"),
        policy,
    )
    interlock = interlock_clearance_k(hot, case.get("item_damage_limit_k"), policy)
    ambient = _require_positive("ambient_k", case.get("ambient_k"))
    hot_wait = touch_safe_cooldown_s(
        case.get("time_constant_s"), hot, ambient, policy["touch_safe_hot_k"]
    )
    cold_wait = touch_safe_cooldown_s(
        case.get("time_constant_s"), cold, ambient, policy["touch_safe_cold_k"]
    )
    groups = hazard_groups(case, policy)

    findings = []
    duties = []
    if strain_margin < 0.0:
        findings.append(
            "the fixture-to-item expansion mismatch drives %.3e strain across the "
            "%.1f K span, past the allowable %.3e; the joint needs a sliding or "
            "flexured interface rather than a stiffer bolt"
            % (strain, span, policy["allowable_strain"])
        )
    if not _at_least(load_margin, policy["min_load_margin"]):
        findings.append(
            "the fixture load margin is %.3f against a required %.3f, so the "
            "mounted mass and load factor exceed what the fixture is rated for"
            % (load_margin, policy["min_load_margin"])
        )
    if not interlock["acceptable"]:
        findings.append(
            "the over-temperature interlock sits at %.2f K and the item is damaged "
            "at %.2f K, leaving %.2f K against a required %.2f K; either the test "
            "limit comes down or the chamber overshoot is reduced"
            % (
                interlock["setpoint_k"],
                interlock["item_damage_limit_k"],
                interlock["clearance_k"],
                policy["min_interlock_clearance_k"],
            )
        )
    if HAZARD_CRYOGENIC in groups:
        duties.append(
            "treat the cold end as a cryogenic-handling operation: the fixture "
            "stays cold long after the chamber reads ambient"
        )
    if HAZARD_VACUUM in groups:
        duties.append(
            "vent to ambient before breaking the chamber, and hold the item until "
            "it is above the dew point so condensation does not land on it"
        )
    duties.append(
        "gate operator access on the item reaching a touch-safe temperature, not "
        "on the chamber reaching one: the wait after the hot end is %.0f s and "
        "after the cold end %.0f s" % (hot_wait, cold_wait)
    )
    duties.append(
        "torque the fixture interface at the temperature the joint was analysed "
        "at, and re-check preload after the first cycle"
    )
    return {
        "span_k": span,
        "expansion_strain": strain,
        "expansion_strain_margin": strain_margin,
        "fixture_load_n": fixture_load_n(
            case.get("mounted_mass_kg"), case.get("design_load_factor_g"), policy
        ),
        "fixture_load_margin": load_margin,
        "interlock": interlock,
        "hot_access_wait_s": hot_wait,
        "cold_access_wait_s": cold_wait,
        "hazard_groups": groups,
        "duties": duties,
        "findings": findings,
        "safe_to_run": not findings,
    }
