#!/usr/bin/env python3
"""Inert dry-gas flushing and purging of a mechanism.

Anchor: ECSS-E-ST-33-01C clause 4.2.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Some mechanisms are designed for vacuum and merely tolerate ground
handling; others are actively harmed by it. Where operating or storing
a mechanism in ambient air degrades it -- a lubricant that oxidises, a
surface that takes up moisture, a bearing that corrodes, a tribological
pair whose friction rises in air -- the mechanism is kept under an
inert dry-gas blanket instead, and the blanket has to be sized rather
than assumed.

Two purge routes are covered:

  continuous flushing   gas flows through a well-mixed enclosure and
                        the contaminant decays by one factor of e per
                        enclosure volume exchanged
  pump-and-backfill     the enclosure is evacuated to a low pressure
                        and refilled with clean gas, each cycle
                        dividing the contaminant by the pressure ratio

Both routes are graded on the same three things: the residual
contaminant reached, the quality of the gas used, and whether the
blanket is unbroken across every ground phase. A purge that lapses
during transport has not protected anything.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DEGRADATION_DRIVERS = (
    "lubricant-oxidation",
    "moisture-uptake",
    "corrosion",
    "friction-rise-in-air",
    "particulate-ingress",
)

OXIDISING_DRIVERS = ("lubricant-oxidation", "corrosion")

PURGE_GASES = ("dry-nitrogen", "dry-argon", "dry-helium", "clean-dry-air")
INERT_GASES = ("dry-nitrogen", "dry-argon", "dry-helium")

GROUND_PHASES = (
    "assembly",
    "integration",
    "environmental-test",
    "transport",
    "storage",
    "pre-launch",
)

DEFAULT_PURGE_POLICY = {
    "target_residual_ppm": 100.0,
    "required_dew_point_c": -40.0,
    "required_purity_percent": 99.99,
    "require_inert_gas_against_oxidising_drivers": True,
    "required_phase_coverage": GROUND_PHASES,
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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _ceil_with_tolerance(value):
    """Ceiling that does not add a whole cycle for a last-place error.

    The cycle count is a ratio of logarithms, so a case that needs
    exactly three cycles can evaluate as 3.0000000000000004 and be
    rounded up to four. A value within a relative hair of an integer is
    taken as that integer.
    """
    nearest = round(value)
    if math.isclose(value, nearest, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return int(nearest)
    return int(math.ceil(value))


def validate_purge_policy(policy):
    """Check a purge policy states every limit the grading needs."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive("target_residual_ppm", policy.get("target_residual_ppm"))
    _require_number("required_dew_point_c", policy.get("required_dew_point_c"))
    purity = _require_positive(
        "required_purity_percent", policy.get("required_purity_percent")
    )
    if purity > 100.0:
        raise ValueError("required_purity_percent cannot exceed 100")
    flag = policy.get("require_inert_gas_against_oxidising_drivers")
    if not isinstance(flag, bool):
        raise ValueError("require_inert_gas_against_oxidising_drivers must be boolean")
    coverage = policy.get("required_phase_coverage")
    if not isinstance(coverage, (list, tuple)) or not coverage:
        raise ValueError("required_phase_coverage must be a non-empty sequence")
    for phase in coverage:
        _require_choice("required_phase_coverage entry", phase, GROUND_PHASES)
    return policy


def purge_required(drivers):
    """Decide whether air operation degrades the mechanism at all."""
    if not isinstance(drivers, (list, tuple)):
        raise ValueError("drivers must be a sequence, got %r" % (drivers,))
    recognised = []
    for driver in drivers:
        _require_choice("driver", driver, DEGRADATION_DRIVERS)
        if driver not in recognised:
            recognised.append(driver)
    oxidising = [d for d in recognised if d in OXIDISING_DRIVERS]
    return {
        "required": bool(recognised),
        "drivers": recognised,
        "oxidising_drivers": oxidising,
    }


def gas_is_admissible(gas, drivers, policy=DEFAULT_PURGE_POLICY):
    """Whether the proposed gas answers the drivers that were declared."""
    validate_purge_policy(policy)
    _require_choice("gas", gas, PURGE_GASES)
    need = purge_required(drivers)
    findings = []
    admissible = True
    if (
        policy["require_inert_gas_against_oxidising_drivers"]
        and need["oxidising_drivers"]
        and gas not in INERT_GASES
    ):
        admissible = False
        findings.append(
            "gas %s is not inert and the declared drivers include %s"
            % (gas, ", ".join(need["oxidising_drivers"]))
        )
    return {"gas": gas, "admissible": admissible, "findings": findings}


def dilution_volumes_required(initial_ppm, target_ppm):
    """Enclosure volume exchanges a well-mixed flush needs to reach target."""
    initial = _require_positive("initial_ppm", initial_ppm)
    target = _require_positive("target_ppm", target_ppm)
    if target >= initial:
        raise ValueError(
            "target %g ppm is not below the initial %g ppm; nothing to flush"
            % (target, initial)
        )
    return math.log(initial / target)


def residual_concentration_ppm(initial_ppm, volumes_exchanged):
    """Contaminant left after a number of well-mixed volume exchanges."""
    initial = _require_positive("initial_ppm", initial_ppm)
    volumes = _require_non_negative("volumes_exchanged", volumes_exchanged)
    return initial * math.exp(-volumes)


def purge_duration_s(enclosure_volume_m3, flow_rate_m3_per_s, initial_ppm, target_ppm):
    """Flush time at a steady flow rate to reach the residual target."""
    volume = _require_positive("enclosure_volume_m3", enclosure_volume_m3)
    flow = _require_positive("flow_rate_m3_per_s", flow_rate_m3_per_s)
    exchanges = dilution_volumes_required(initial_ppm, target_ppm)
    return volume * exchanges / flow


def pressure_cycle_residual_ppm(initial_ppm, low_pressure_pa, high_pressure_pa, cycles):
    """Contaminant left after a number of pump-and-backfill cycles."""
    initial = _require_positive("initial_ppm", initial_ppm)
    low = _require_positive("low_pressure_pa", low_pressure_pa)
    high = _require_positive("high_pressure_pa", high_pressure_pa)
    if not isinstance(cycles, int) or isinstance(cycles, bool) or cycles < 0:
        raise ValueError("cycles must be a non-negative integer, got %r" % (cycles,))
    if low >= high:
        raise ValueError(
            "low pressure %g Pa is not below the backfill pressure %g Pa; the "
            "cycle dilutes nothing" % (low, high)
        )
    return initial * (low / high) ** cycles


def cycles_to_target(initial_ppm, target_ppm, low_pressure_pa, high_pressure_pa):
    """Whole pump-and-backfill cycles needed to reach the residual target."""
    exchanges = dilution_volumes_required(initial_ppm, target_ppm)
    low = _require_positive("low_pressure_pa", low_pressure_pa)
    high = _require_positive("high_pressure_pa", high_pressure_pa)
    if low >= high:
        raise ValueError("low pressure must sit below the backfill pressure")
    return _ceil_with_tolerance(exchanges / math.log(high / low))


def assess_gas_quality(dew_point_c, purity_percent, policy=DEFAULT_PURGE_POLICY):
    """Grade the supplied gas against the dew-point and purity limits."""
    validate_purge_policy(policy)
    dew = _require_number("dew_point_c", dew_point_c)
    purity = _require_positive("purity_percent", purity_percent)
    if purity > 100.0:
        raise ValueError("purity_percent cannot exceed 100")
    findings = []
    dew_ok = _at_most(dew, policy["required_dew_point_c"])
    if not dew_ok:
        findings.append(
            "dew point %.1f C is above the required %.1f C"
            % (dew, policy["required_dew_point_c"])
        )
    purity_ok = purity >= policy["required_purity_percent"] or math.isclose(
        purity, policy["required_purity_percent"], rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )
    if not purity_ok:
        findings.append(
            "purity %.4f%% is below the required %.4f%%"
            % (purity, policy["required_purity_percent"])
        )
    return {"dew_point_ok": dew_ok, "purity_ok": purity_ok, "findings": findings}


def phase_coverage_gaps(covered_phases, policy=DEFAULT_PURGE_POLICY):
    """Ground phases the blanket is required to cover but does not."""
    validate_purge_policy(policy)
    if not isinstance(covered_phases, (list, tuple)):
        raise ValueError("covered_phases must be a sequence")
    for phase in covered_phases:
        _require_choice("covered phase", phase, GROUND_PHASES)
    covered = set(covered_phases)
    return [p for p in policy["required_phase_coverage"] if p not in covered]


def plan_purge(case, policy=DEFAULT_PURGE_POLICY):
    """Full clause 4.2.6 purge decision, sizing and adequacy verdict."""
    validate_purge_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    need = purge_required(case.get("degradation_drivers", []))
    if not need["required"]:
        return {
            "purge_required": False,
            "verdict": "purge-not-required",
            "adequate": True,
            "findings": [
                "no declared driver degrades the mechanism in air; a blanket "
                "is not imposed by this clause"
            ],
        }
    route = _require_choice(
        "route", case.get("route"), ("continuous-flush", "pump-and-backfill")
    )
    target = _require_positive(
        "target_residual_ppm",
        case.get("target_residual_ppm", policy["target_residual_ppm"]),
    )
    initial = _require_positive("initial_ppm", case.get("initial_ppm"))
    findings = []
    gas_check = gas_is_admissible(case.get("gas"), need["drivers"], policy)
    findings.extend(gas_check["findings"])
    quality = assess_gas_quality(
        case.get("dew_point_c"), case.get("purity_percent"), policy
    )
    findings.extend(quality["findings"])
    gaps = phase_coverage_gaps(case.get("covered_phases", []), policy)
    if gaps:
        findings.append(
            "the blanket is not maintained through %s" % ", ".join(gaps)
        )
    sizing = {"route": route}
    if route == "continuous-flush":
        exchanges = dilution_volumes_required(initial, target)
        duration = purge_duration_s(
            case.get("enclosure_volume_m3"),
            case.get("flow_rate_m3_per_s"),
            initial,
            target,
        )
        sizing["volume_exchanges"] = exchanges
        sizing["duration_s"] = duration
        available = case.get("available_duration_s")
        if available is not None:
            available = _require_positive("available_duration_s", available)
            if not _at_most(duration, available):
                findings.append(
                    "the flush needs %.0f s and only %.0f s is available"
                    % (duration, available)
                )
    else:
        cycles = cycles_to_target(
            initial,
            target,
            case.get("low_pressure_pa"),
            case.get("high_pressure_pa"),
        )
        sizing["cycles_required"] = cycles
        planned = case.get("planned_cycles")
        if planned is not None:
            if not isinstance(planned, int) or isinstance(planned, bool):
                raise ValueError("planned_cycles must be an integer")
            sizing["planned_cycles"] = planned
            if planned < cycles:
                findings.append(
                    "the plan plots %d cycles and the target needs %d"
                    % (planned, cycles)
                )
    adequate = not findings
    return {
        "purge_required": True,
        "drivers": need["drivers"],
        "gas_admissible": gas_check["admissible"],
        "gas_quality_ok": quality["dew_point_ok"] and quality["purity_ok"],
        "phase_coverage_gaps": gaps,
        "sizing": sizing,
        "adequate": adequate,
        "verdict": "purge-plan-adequate" if adequate else "purge-plan-deficient",
        "findings": findings,
    }
