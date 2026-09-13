#!/usr/bin/env python3
"""Purpose of the thermal cycling test applied to a solar cell assembly.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.7.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A solar cell assembly sample is cycled to assess its reliability under the
thermal stress a year of orbital eclipses imposes. Every time the spacecraft
enters and leaves eclipse the assembly swings between its cold and hot
extremes, and the materials joined into it -- welded interconnects, a
coverglass adhesive bondline, a rear metallization, a diode attachment --
respond to that swing with fatigue rather than with a single overload. The
test exists so a year of that swinging is seen on the ground before it is
seen on orbit.

Two things decide whether and why the cycling is applied:

    what the orbit does      the number of eclipse transitions a year of the
                             declared orbit produces, and the hot-to-cold
                             range each transition drives
    what the assembly is     a welded interconnect, a stress-relief loop, a
                             coverglass bondline, a rear metallization, a
                             bypass diode attachment and a cell-to-substrate
                             adhesive each carry their own thermal-fatigue
                             failure mode, and each turns into a reliability
                             objective the cycling demonstrates

The cycling only serves its purpose when it represents that orbital year:
at least as many cycles, at least as hot and at least as cold. A milder or
shorter run demonstrates nothing about the year it was bought to stand in
for.

The trigger, the coverage factor and the minimum stress range below are a
declared policy, not a physical constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FEATURE_OBJECTIVES = {
    "cell-to-interconnect-weld": "interconnect-weld-fatigue-endurance",
    "interconnect-stress-relief-loop": "stress-relief-loop-strain-accommodation",
    "coverglass-adhesive-bondline": "coverglass-bondline-integrity",
    "cell-rear-metallization": "rear-metallization-adhesion-retention",
    "bypass-diode-attachment": "bypass-diode-attachment-integrity",
    "cell-to-substrate-adhesive": "cell-substrate-adhesive-shear-retention",
}

THERMAL_FATIGUE_FEATURES = tuple(sorted(FEATURE_OBJECTIVES))

COMMON_OBJECTIVE = "sca-electrical-output-retention"

TEST_NOT_REQUIRED = "test-not-required"
CYCLING_NOT_PLANNED = "cycling-not-planned"
CYCLING_UNDER_REPRESENTATION = "cycling-under-representation"
CYCLING_REPRESENTS_ORBIT_YEAR = "cycling-represents-orbit-year"

DEFAULT_CYCLING_PURPOSE_POLICY = {
    "minutes_per_year": 525600.0,
    "cycle_trigger": 100.0,
    "minimum_stress_range_k": 20.0,
    "coverage_factor": 1.0,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(
            "%s must be a fraction between 0 and 1, got %r" % (name, value)
        )
    return number


def _require_temperature(name, value):
    number = _require_number(name, value)
    if number <= -273.15:
        raise ValueError("%s %g C is at or below absolute zero" % (name, number))
    return number


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


def validate_cycling_purpose_policy(policy):
    """Check the declared cycling-purpose policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("minutes_per_year", policy.get("minutes_per_year"))
    _require_positive("cycle_trigger", policy.get("cycle_trigger"))
    _require_positive(
        "minimum_stress_range_k", policy.get("minimum_stress_range_k")
    )
    factor = _require_positive("coverage_factor", policy.get("coverage_factor"))
    if factor < 1.0:
        raise ValueError(
            "coverage_factor %g lets the cycling fall short of the orbital "
            "year it stands in for" % factor
        )
    return policy


def eclipse_cycles_per_year(
    orbital_period_min,
    eclipsed_orbit_fraction,
    policy=DEFAULT_CYCLING_PURPOSE_POLICY,
):
    """Eclipse-driven thermal cycles a year of the declared orbit imposes.

    Every orbit that carries an eclipse gives the assembly one hot-to-cold
    swing, so a year of orbits scaled by the eclipsed fraction is the cycle
    count the ground test has to represent.
    """
    validate_cycling_purpose_policy(policy)
    period = _require_positive("orbital_period_min", orbital_period_min)
    fraction = _require_fraction(
        "eclipsed_orbit_fraction", eclipsed_orbit_fraction
    )
    orbits = float(policy["minutes_per_year"]) / period
    return orbits * fraction


def orbital_thermal_stress(hot_extreme_c, cold_extreme_c):
    """The hot-to-cold swing one eclipse transition drives on orbit."""
    hot = _require_temperature("hot_extreme_c", hot_extreme_c)
    cold = _require_temperature("cold_extreme_c", cold_extreme_c)
    if not cold < hot:
        raise ValueError(
            "cold_extreme_c %g C must be below hot_extreme_c %g C" % (cold, hot)
        )
    return {
        "hot_extreme_c": hot,
        "cold_extreme_c": cold,
        "stress_range_k": hot - cold,
    }


def thermal_fatigue_inventory(features):
    """Group the declared assembly features that carry a fatigue failure mode."""
    if not isinstance(features, (list, tuple, set, frozenset)):
        raise ValueError("features must be a collection of feature names")
    grouped = []
    for feature in features:
        if feature not in FEATURE_OBJECTIVES:
            raise ValueError(
                "unknown assembly feature %r; recognised features are %s"
                % (feature, ", ".join(THERMAL_FATIGUE_FEATURES))
            )
        if feature not in grouped:
            grouped.append(feature)
    return tuple(sorted(grouped))


def sca_cycling_objectives(features):
    """What the cycling demonstrates, given what the assembly contains."""
    grouped = thermal_fatigue_inventory(features)
    if not grouped:
        return ()
    objectives = [FEATURE_OBJECTIVES[feature] for feature in grouped]
    objectives.append(COMMON_OBJECTIVE)
    return tuple(objectives)


def cycling_represents_orbit_year(
    plan, orbit_year, policy=DEFAULT_CYCLING_PURPOSE_POLICY
):
    """Check the planned run bounds the orbital year on count and extremes."""
    validate_cycling_purpose_policy(policy)
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    if not isinstance(orbit_year, dict) or "annual_cycles" not in orbit_year:
        raise ValueError("orbit_year must carry annual_cycles and the extremes")
    planned_cycles = _require_non_negative(
        "plan cycle_count", plan.get("cycle_count")
    )
    planned_hot = _require_temperature("plan hot_extreme_c", plan.get("hot_extreme_c"))
    planned_cold = _require_temperature(
        "plan cold_extreme_c", plan.get("cold_extreme_c")
    )
    if not planned_cold < planned_hot:
        raise ValueError(
            "plan cold_extreme_c %g C must be below hot_extreme_c %g C"
            % (planned_cold, planned_hot)
        )
    required_cycles = float(orbit_year["annual_cycles"]) * float(
        policy["coverage_factor"]
    )
    findings = []
    count_ok = _at_least(planned_cycles, required_cycles)
    if not count_ok:
        findings.append(
            "planned %.0f cycles is below the %.0f a year of eclipses imposes"
            % (planned_cycles, required_cycles)
        )
    hot_ok = _at_least(planned_hot, orbit_year["hot_extreme_c"])
    if not hot_ok:
        findings.append(
            "planned hot extreme %.1f C is below the orbital hot extreme %.1f C"
            % (planned_hot, orbit_year["hot_extreme_c"])
        )
    cold_ok = _at_most(planned_cold, orbit_year["cold_extreme_c"])
    if not cold_ok:
        findings.append(
            "planned cold extreme %.1f C is above the orbital cold extreme "
            "%.1f C" % (planned_cold, orbit_year["cold_extreme_c"])
        )
    return {
        "planned_cycles": planned_cycles,
        "required_cycles": required_cycles,
        "planned_stress_range_k": planned_hot - planned_cold,
        "count_represents": count_ok,
        "hot_represents": hot_ok,
        "cold_represents": cold_ok,
        "represents_orbit_year": count_ok and hot_ok and cold_ok,
        "findings": findings,
    }


def assess_sca_thermal_cycling_purpose(
    case, policy=DEFAULT_CYCLING_PURPOSE_POLICY
):
    """Full clause 6.4.3.7.1 justification for one solar cell assembly."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_cycling_purpose_policy(policy)
    if "assembly_features" not in case:
        raise ValueError(
            "case is missing assembly_features; an absent inventory is not an "
            "empty one"
        )
    grouped = thermal_fatigue_inventory(case["assembly_features"])
    objectives = sca_cycling_objectives(case["assembly_features"])
    mission = case.get("mission_orbit")
    if not isinstance(mission, dict):
        raise ValueError("case is missing a mission_orbit mapping")
    annual_cycles = eclipse_cycles_per_year(
        mission.get("orbital_period_min"),
        mission.get("eclipsed_orbit_fraction"),
        policy,
    )
    stress = orbital_thermal_stress(
        mission.get("hot_extreme_c"), mission.get("cold_extreme_c")
    )
    orbit_year = {
        "annual_cycles": annual_cycles,
        "hot_extreme_c": stress["hot_extreme_c"],
        "cold_extreme_c": stress["cold_extreme_c"],
        "stress_range_k": stress["stress_range_k"],
    }
    trigger = float(policy["cycle_trigger"])
    minimum_range = float(policy["minimum_stress_range_k"])
    count_triggers = _at_least(annual_cycles, trigger)
    range_triggers = _at_least(stress["stress_range_k"], minimum_range)
    justified = bool(grouped) and count_triggers and range_triggers
    findings = []
    result = {
        "fatigue_sensitive_features": grouped,
        "objectives": objectives,
        "annual_eclipse_cycles": annual_cycles,
        "orbital_stress_range_k": stress["stress_range_k"],
        "orbital_hot_extreme_c": stress["hot_extreme_c"],
        "orbital_cold_extreme_c": stress["cold_extreme_c"],
        "cycle_trigger": trigger,
        "justified": justified,
        "findings": findings,
    }
    if not justified:
        if not grouped:
            findings.append(
                "no declared assembly feature carries a thermal-fatigue "
                "failure mode"
            )
        if not count_triggers:
            findings.append(
                "the declared orbit gives %.0f eclipse cycles a year, below "
                "the %.0f trigger" % (annual_cycles, trigger)
            )
        if not range_triggers:
            findings.append(
                "the orbital swing of %.1f K is below the %.1f K minimum "
                "stress range" % (stress["stress_range_k"], minimum_range)
            )
        result.update(
            {
                "planned_cycles": None,
                "required_cycles": None,
                "represents_orbit_year": None,
                "verdict": TEST_NOT_REQUIRED,
            }
        )
        return result
    plan = case.get("test_plan")
    if plan is None:
        findings.append(
            "the cycling is justified but no run is planned; the purpose is "
            "stated and not yet served"
        )
        result.update(
            {
                "planned_cycles": None,
                "required_cycles": annual_cycles * float(policy["coverage_factor"]),
                "represents_orbit_year": None,
                "verdict": CYCLING_NOT_PLANNED,
            }
        )
        return result
    represents = cycling_represents_orbit_year(plan, orbit_year, policy)
    findings.extend(represents["findings"])
    result.update(
        {
            "planned_cycles": represents["planned_cycles"],
            "required_cycles": represents["required_cycles"],
            "planned_stress_range_k": represents["planned_stress_range_k"],
            "count_represents": represents["count_represents"],
            "hot_represents": represents["hot_represents"],
            "cold_represents": represents["cold_represents"],
            "represents_orbit_year": represents["represents_orbit_year"],
            "verdict": (
                CYCLING_REPRESENTS_ORBIT_YEAR
                if represents["represents_orbit_year"]
                else CYCLING_UNDER_REPRESENTATION
            ),
        }
    )
    return result
