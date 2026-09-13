#!/usr/bin/env python3
"""Differential-charging reduction objective (ECSS-E-ST-20-06C 6.1.2).

Deterministic, offline, stdlib-only support logic for the mission-level
objective of clause 6.1.2: hold the differential-potential between adjacent
spacecraft surfaces, and the energy an electrostatic-discharge would release,
beneath the levels the mission has declared acceptable.

Physical model
--------------
An adjacent surface-pair -- a floating outer dielectric face over (or beside)
a grounded conductor -- behaves as a parallel-plate capacitance::

    C = eps0 * eps_r * A / t

and a discharge releases the energy stored in it::

    E = 0.5 * C * dV**2

so stored energy grows linearly with coated-area, quadratically with the
differential-potential, and falls as the dielectric-thickness increases.

Comparisons against a mission level use a relative tolerance so a pair sitting
exactly at its budget reads compliant despite floating-point representation
error. The budget itself is never widened.
"""

import math

__all__ = [
    "EPSILON_0",
    "SEVERITY_BANDS",
    "REL_TOL",
    "differential_potential",
    "pair_capacitance",
    "stored_discharge_energy",
    "minimum_thickness_for_budget",
    "maximum_area_for_budget",
    "reduction_factor",
    "severity_band",
    "within_level",
    "evaluate_pair",
    "evaluate_mission",
]

EPSILON_0 = 8.8541878128e-12  # F/m

# Damage-severity bands for the energy a single discharge releases (joule).
# Upper edge of each band; the last band is open-ended.
SEVERITY_BANDS = (
    ("negligible", 1.0e-5),
    ("minor", 1.0e-4),
    ("marginal", 1.0e-3),
    ("hazardous", float("inf")),
)

REL_TOL = 1.0e-9


# --- validation helpers ---------------------------------------------------


def _real(value, label):
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    out = _real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, out))
    return out


def _non_negative(value, label):
    out = _real(value, label)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (label, out))
    return out


def _relative_permittivity(value):
    out = _real(value, "relative_permittivity")
    if out < 1.0:
        raise ValueError("relative_permittivity must be >= 1.0, got %r" % (out,))
    return out


# --- primitives -----------------------------------------------------------


def differential_potential(potential_a_v, potential_b_v):
    """Magnitude of the potential difference across an adjacent pair (V)."""
    a = _real(potential_a_v, "potential_a_v")
    b = _real(potential_b_v, "potential_b_v")
    return abs(a - b)


def pair_capacitance(coated_area_m2, dielectric_thickness_m, relative_permittivity):
    """Parallel-plate capacitance of the pair (F)."""
    area = _positive(coated_area_m2, "coated_area_m2")
    thickness = _positive(dielectric_thickness_m, "dielectric_thickness_m")
    eps_r = _relative_permittivity(relative_permittivity)
    return EPSILON_0 * eps_r * area / thickness


def stored_discharge_energy(capacitance_f, differential_potential_v):
    """Energy a discharge of this pair would release (J)."""
    cap = _positive(capacitance_f, "capacitance_f")
    dv = _non_negative(differential_potential_v, "differential_potential_v")
    return 0.5 * cap * dv * dv


def minimum_thickness_for_budget(
    coated_area_m2, relative_permittivity, differential_potential_v, energy_budget_j
):
    """Least dielectric-thickness (m) meeting the budget at the present area."""
    area = _positive(coated_area_m2, "coated_area_m2")
    eps_r = _relative_permittivity(relative_permittivity)
    dv = _non_negative(differential_potential_v, "differential_potential_v")
    budget = _positive(energy_budget_j, "energy_budget_j")
    if dv == 0.0:
        raise ValueError(
            "differential_potential_v is zero; no thickness constrains a pair "
            "that stores no energy"
        )
    return 0.5 * EPSILON_0 * eps_r * area * dv * dv / budget


def maximum_area_for_budget(
    dielectric_thickness_m, relative_permittivity, differential_potential_v, energy_budget_j
):
    """Largest coated-area (m2) meeting the budget at the present thickness."""
    thickness = _positive(dielectric_thickness_m, "dielectric_thickness_m")
    eps_r = _relative_permittivity(relative_permittivity)
    dv = _non_negative(differential_potential_v, "differential_potential_v")
    budget = _positive(energy_budget_j, "energy_budget_j")
    if dv == 0.0:
        raise ValueError(
            "differential_potential_v is zero; no area constrains a pair that "
            "stores no energy"
        )
    return 2.0 * budget * thickness / (EPSILON_0 * eps_r * dv * dv)


def reduction_factor(actual_energy_j, energy_budget_j):
    """How many times over budget the pair sits (1.0 = exactly at budget)."""
    actual = _non_negative(actual_energy_j, "actual_energy_j")
    budget = _positive(energy_budget_j, "energy_budget_j")
    return actual / budget


def severity_band(energy_j):
    """Damage-severity band of a single discharge of this energy."""
    energy = _non_negative(energy_j, "energy_j")
    for label, upper in SEVERITY_BANDS:
        if energy <= upper or math.isclose(energy, upper, rel_tol=REL_TOL, abs_tol=0.0):
            return label
    return SEVERITY_BANDS[-1][0]


def within_level(value, level, rel_tol=REL_TOL):
    """True when value <= level, absorbing representation error at equality."""
    v = _real(value, "value")
    lv = _real(level, "level")
    if v <= lv:
        return True
    return math.isclose(v, lv, rel_tol=rel_tol, abs_tol=0.0)


# --- pair and mission evaluation ------------------------------------------


def evaluate_pair(pair, differential_potential_limit_v, energy_budget_j):
    """Grade one adjacent surface-pair against both mission levels."""
    if not isinstance(pair, dict):
        raise ValueError("pair must be a mapping, got %r" % (type(pair).__name__,))
    name = pair.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("pair needs a non-empty 'name'")
    for key in (
        "potential_a_v",
        "potential_b_v",
        "coated_area_m2",
        "dielectric_thickness_m",
        "relative_permittivity",
    ):
        if pair.get(key) is None:
            raise ValueError("pair %r is missing required input %r" % (name, key))

    limit = _positive(differential_potential_limit_v, "differential_potential_limit_v")
    budget = _positive(energy_budget_j, "energy_budget_j")

    dv = differential_potential(pair["potential_a_v"], pair["potential_b_v"])
    cap = pair_capacitance(
        pair["coated_area_m2"],
        pair["dielectric_thickness_m"],
        pair["relative_permittivity"],
    )
    energy = stored_discharge_energy(cap, dv)

    potential_ok = within_level(dv, limit)
    energy_ok = within_level(energy, budget)
    findings = []
    if not potential_ok:
        findings.append(
            "%s: differential-potential %.1f V above limit %.1f V" % (name, dv, limit)
        )
    if not energy_ok:
        findings.append(
            "%s: stored-discharge-energy %.3e J above budget %.3e J" % (name, energy, budget)
        )

    result = {
        "name": name,
        "differential_potential_v": dv,
        "capacitance_f": cap,
        "stored_energy_j": energy,
        "severity": severity_band(energy),
        "potential_ok": potential_ok,
        "energy_ok": energy_ok,
        "compliant": potential_ok and energy_ok,
        "reduction_factor": reduction_factor(energy, budget),
        "findings": findings,
    }
    if not energy_ok and dv > 0.0:
        result["minimum_thickness_m"] = minimum_thickness_for_budget(
            pair["coated_area_m2"], pair["relative_permittivity"], dv, budget
        )
        result["maximum_area_m2"] = maximum_area_for_budget(
            pair["dielectric_thickness_m"], pair["relative_permittivity"], dv, budget
        )
    return result


def evaluate_mission(pairs, mission_levels):
    """Aggregate the clause-6.1.2 objective over every adjacent pair.

    ``mission_levels`` must carry ``differential_potential_limit_v`` and
    ``energy_budget_j``. A missing level is a finding in its own right: an
    objective graded against nothing is unverified, not satisfied.
    """
    if not isinstance(pairs, (list, tuple)) or not pairs:
        raise ValueError("pairs must be a non-empty list of pair mappings")
    if not isinstance(mission_levels, dict):
        raise ValueError("mission_levels must be a mapping")

    missing = [
        key
        for key in ("differential_potential_limit_v", "energy_budget_j")
        if mission_levels.get(key) is None
    ]
    if missing:
        return {
            "levels_declared": False,
            "pair_count": len(pairs),
            "compliant_count": 0,
            "objective_met": False,
            "open_findings": [
                "mission acceptance level %r not declared" % key for key in missing
            ],
            "pairs": [],
        }

    limit = mission_levels["differential_potential_limit_v"]
    budget = mission_levels["energy_budget_j"]
    seen = set()
    results = []
    for pair in pairs:
        result = evaluate_pair(pair, limit, budget)
        if result["name"] in seen:
            raise ValueError("duplicate pair name %r" % (result["name"],))
        seen.add(result["name"])
        results.append(result)

    open_findings = [f for r in results for f in r["findings"]]
    worst = max(results, key=lambda r: r["stored_energy_j"])
    return {
        "levels_declared": True,
        "pair_count": len(results),
        "compliant_count": sum(1 for r in results if r["compliant"]),
        "worst_pair": worst["name"],
        "worst_energy_j": worst["stored_energy_j"],
        "worst_reduction_factor": max(r["reduction_factor"] for r in results),
        "objective_met": not open_findings,
        "open_findings": open_findings,
        "pairs": results,
    }
