#!/usr/bin/env python3
"""Second-level single-carrier multipactor threshold by field scaling and
electron tracking (ECSS-E-ST-20-01C clause 5.3.2.3.3).

Offline, deterministic, stdlib only.  The three-dimensional field solution is
represented by a sampled field amplitude at the susceptible gap together with
the power it was normalised to; the module rescales that amplitude, integrates
electron trajectories across the gap over the radio-frequency cycle, applies a
secondary-electron-yield curve at every wall impact, and bisects the field
amplitude for the single-carrier threshold where the tracked population stops
decaying.  Convergence of the seeding and of the field mesh is graded
separately.

Paraphrased procedure only; the standard clause is the anchor, not the text.
"""

from __future__ import annotations

import math

__all__ = [
    "ELECTRON_CHARGE_C",
    "ELECTRON_MASS_KG",
    "DEFAULT_STEPS_PER_PERIOD",
    "DEFAULT_TRACKED_PERIODS",
    "DEFAULT_SEED_PHASES",
    "MIN_SEED_PHASES",
    "MIN_TRACKED_PERIODS",
    "MAX_MESH_DELTA",
    "MAX_SEED_SENSITIVITY",
    "scale_field_to_power",
    "gap_voltage",
    "energy_to_speed",
    "speed_to_energy_ev",
    "secondary_yield",
    "seed_phases",
    "track_electron",
    "effective_yield",
    "single_carrier_threshold_field",
    "threshold_power_w",
    "multipactor_margin_db",
    "check_convergence",
    "assess_single_carrier_run",
]

ELECTRON_CHARGE_C = 1.602176634e-19
ELECTRON_MASS_KG = 9.1093837015e-31

DEFAULT_STEPS_PER_PERIOD = 120
DEFAULT_TRACKED_PERIODS = 6
DEFAULT_SEED_PHASES = 16
DEFAULT_SEED_ENERGY_EV = 2.0

MIN_SEED_PHASES = 12
MIN_TRACKED_PERIODS = 4
MAX_MESH_DELTA = 0.05
MAX_SEED_SENSITIVITY = 0.05

COMPARISON_TOLERANCE = 1e-9
_CURVE_KEYS = ("sigma_max", "e_max_ev")

_RUN_KEYS = (
    "item_id",
    "gap_m",
    "frequency_hz",
    "reference_field_v_per_m",
    "reference_power_w",
    "operating_power_w",
    "required_margin_db",
    "yield_curve",
)


def _at_least(value, limit):
    """Inclusive >= that absorbs float representation error."""
    return value > limit or math.isclose(
        value, limit, rel_tol=COMPARISON_TOLERANCE, abs_tol=COMPARISON_TOLERANCE
    )


def _real(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _positive(value, label):
    value = _real(value, label)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def _positive_int(value, label, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def scale_field_to_power(reference_field_v_per_m, reference_power_w, target_power_w):
    """Rescale a field-model amplitude to another carrier power (E ~ sqrt(P))."""
    field = _positive(reference_field_v_per_m, "reference_field_v_per_m")
    p_ref = _positive(reference_power_w, "reference_power_w")
    p_tgt = _positive(target_power_w, "target_power_w")
    return field * math.sqrt(p_tgt / p_ref)


def gap_voltage(field_v_per_m, gap_m):
    """Peak voltage across the susceptible gap for a uniform local field."""
    return _positive(field_v_per_m, "field_v_per_m") * _positive(gap_m, "gap_m")


def energy_to_speed(energy_ev):
    """Non-relativistic electron speed for a kinetic energy in electronvolt."""
    energy = _real(energy_ev, "energy_ev")
    if energy < 0.0:
        raise ValueError("energy_ev must not be negative, got %r" % (energy,))
    return math.sqrt(2.0 * energy * ELECTRON_CHARGE_C / ELECTRON_MASS_KG)


def speed_to_energy_ev(speed_m_per_s):
    """Kinetic energy in electronvolt for a non-relativistic electron speed."""
    speed = _real(speed_m_per_s, "speed_m_per_s")
    return 0.5 * ELECTRON_MASS_KG * speed * speed / ELECTRON_CHARGE_C


def _validate_curve(curve):
    if not isinstance(curve, dict):
        raise ValueError("yield_curve must be a mapping, got %r" % (curve,))
    for key in _CURVE_KEYS:
        if key not in curve:
            raise ValueError("yield_curve missing required key %r" % (key,))
    sigma_max = _positive(curve["sigma_max"], "sigma_max")
    if sigma_max <= 1.0:
        raise ValueError("sigma_max must exceed unity for a multipacting surface")
    e_max = _positive(curve["e_max_ev"], "e_max_ev")
    threshold = _real(curve.get("threshold_energy_ev", 0.0), "threshold_energy_ev")
    if threshold < 0.0 or threshold >= e_max:
        raise ValueError("threshold_energy_ev must sit in [0, e_max_ev)")
    return {"sigma_max": sigma_max, "e_max_ev": e_max, "threshold_energy_ev": threshold}


def secondary_yield(curve, impact_energy_ev):
    """Secondary-electron-yield at a wall impact, from the curve parameters."""
    record = _validate_curve(curve)
    energy = _real(impact_energy_ev, "impact_energy_ev")
    if energy < 0.0:
        raise ValueError("impact_energy_ev must not be negative, got %r" % (energy,))
    e0 = record["threshold_energy_ev"]
    if energy <= e0:
        return 0.0
    v = (energy - e0) / (record["e_max_ev"] - e0)
    if v > 3.6:
        return record["sigma_max"] * 1.125 / (v ** 0.35)
    k = 0.56 if v <= 1.0 else 0.25
    return record["sigma_max"] * ((v * math.exp(1.0 - v)) ** k)


def seed_phases(count=DEFAULT_SEED_PHASES):
    """Deterministic launch phases spread over one radio-frequency cycle."""
    n = _positive_int(count, "count")
    return [2.0 * math.pi * i / n for i in range(n)]


def track_electron(
    gap_m,
    field_amplitude_v_per_m,
    frequency_hz,
    launch_phase_rad,
    initial_energy_ev=DEFAULT_SEED_ENERGY_EV,
    steps_per_period=DEFAULT_STEPS_PER_PERIOD,
    tracked_periods=DEFAULT_TRACKED_PERIODS,
):
    """Integrate one electron trajectory across the gap until it hits a wall."""
    gap = _positive(gap_m, "gap_m")
    amplitude = _positive(field_amplitude_v_per_m, "field_amplitude_v_per_m")
    frequency = _positive(frequency_hz, "frequency_hz")
    phase = _real(launch_phase_rad, "launch_phase_rad")
    steps = _positive_int(steps_per_period, "steps_per_period", minimum=8)
    periods = _positive_int(tracked_periods, "tracked_periods")
    speed = energy_to_speed(initial_energy_ev)

    omega = 2.0 * math.pi * frequency
    accel = ELECTRON_CHARGE_C * amplitude / ELECTRON_MASS_KG
    dt = 1.0 / (frequency * steps)
    total_steps = steps * periods

    position = 0.0
    velocity = speed
    time = 0.0
    acceleration = accel * math.sin(phase)
    for _ in range(total_steps):
        position += velocity * dt + 0.5 * acceleration * dt * dt
        time += dt
        next_acceleration = accel * math.sin(omega * time + phase)
        velocity += 0.5 * (acceleration + next_acceleration) * dt
        acceleration = next_acceleration
        if position >= gap or position <= 0.0:
            wall = "opposite" if position >= gap else "launch"
            return {
                "impacted": True,
                "wall": wall,
                "impact_energy_ev": speed_to_energy_ev(abs(velocity)),
                "transit_time_s": time,
                "transit_periods": time * frequency,
            }
    return {
        "impacted": False,
        "wall": None,
        "impact_energy_ev": 0.0,
        "transit_time_s": time,
        "transit_periods": time * frequency,
    }


def effective_yield(
    gap_m,
    field_amplitude_v_per_m,
    frequency_hz,
    curve,
    phases=None,
    initial_energy_ev=DEFAULT_SEED_ENERGY_EV,
    steps_per_period=DEFAULT_STEPS_PER_PERIOD,
    tracked_periods=DEFAULT_TRACKED_PERIODS,
):
    """Mean secondaries per seeded electron over one tracked generation."""
    launch = seed_phases() if phases is None else list(phases)
    if len(launch) == 0:
        raise ValueError("at least one launch phase is required")
    _validate_curve(curve)
    total = 0.0
    impacts = 0
    for phase in launch:
        outcome = track_electron(
            gap_m,
            field_amplitude_v_per_m,
            frequency_hz,
            phase,
            initial_energy_ev=initial_energy_ev,
            steps_per_period=steps_per_period,
            tracked_periods=tracked_periods,
        )
        if outcome["impacted"]:
            impacts += 1
            total += secondary_yield(curve, outcome["impact_energy_ev"])
    return total / len(launch) if impacts else 0.0


def single_carrier_threshold_field(
    gap_m,
    frequency_hz,
    curve,
    field_low_v_per_m,
    field_high_v_per_m,
    phases=None,
    initial_energy_ev=DEFAULT_SEED_ENERGY_EV,
    steps_per_period=DEFAULT_STEPS_PER_PERIOD,
    tracked_periods=DEFAULT_TRACKED_PERIODS,
    scan_points=40,
    relative_tolerance=1e-4,
    max_iterations=40,
):
    """Locate the lower edge of the single-carrier susceptibility band.

    A multipactor susceptibility band is bounded on both sides, so a plain
    two-point bracket over the whole field range is not enough: the search
    walks a geometric ladder upwards from a field that demonstrably decays
    until the tracked population first sustains itself, then bisects that
    interval for the threshold.
    """
    low = _positive(field_low_v_per_m, "field_low_v_per_m")
    high = _positive(field_high_v_per_m, "field_high_v_per_m")
    if not low < high:
        raise ValueError("field_low_v_per_m must sit below field_high_v_per_m")
    rel_tol = _positive(relative_tolerance, "relative_tolerance")
    iterations = _positive_int(max_iterations, "max_iterations")
    rungs = _positive_int(scan_points, "scan_points", minimum=4)

    def growth(field):
        return effective_yield(
            gap_m,
            field,
            frequency_hz,
            curve,
            phases=phases,
            initial_energy_ev=initial_energy_ev,
            steps_per_period=steps_per_period,
            tracked_periods=tracked_periods,
        )

    if growth(low) >= 1.0:
        raise ValueError("lower bracket already sustains multipactor growth")
    ratio = high / low
    lo = low
    hi = None
    for step in range(1, rungs + 1):
        field = low * (ratio ** (step / rungs))
        if growth(field) >= 1.0:
            hi = field
            break
        lo = field
    if hi is None:
        raise ValueError("no multipactor growth found across the searched field range")
    used = 0
    for _ in range(iterations):
        used += 1
        mid = 0.5 * (lo + hi)
        if growth(mid) < 1.0:
            lo = mid
        else:
            hi = mid
        if (hi - lo) / hi <= rel_tol:
            break
    threshold = 0.5 * (lo + hi)
    return {
        "threshold_field_v_per_m": threshold,
        "threshold_gap_voltage_v": gap_voltage(threshold, gap_m),
        "bracket_v_per_m": (lo, hi),
        "iterations": used,
        "scan_points": rungs,
    }


def threshold_power_w(
    threshold_field_v_per_m, reference_field_v_per_m, reference_power_w
):
    """Carrier power at the threshold field, from the field-model normalisation."""
    threshold = _positive(threshold_field_v_per_m, "threshold_field_v_per_m")
    field = _positive(reference_field_v_per_m, "reference_field_v_per_m")
    power = _positive(reference_power_w, "reference_power_w")
    ratio = threshold / field
    return power * ratio * ratio


def multipactor_margin_db(threshold_power, operating_power):
    """Single-carrier multipactor-margin in decibel above the operating point."""
    p_th = _positive(threshold_power, "threshold_power")
    p_op = _positive(operating_power, "operating_power")
    return 10.0 * math.log10(p_th / p_op)


def check_convergence(run):
    """Grade the seeding and field-mesh convergence of a tracked run."""
    if not isinstance(run, dict):
        raise ValueError("run record must be a mapping, got %r" % (run,))
    findings = []
    seeds = run.get("seed_phase_count")
    if seeds is None:
        findings.append("seed-phase-count-not-recorded")
    elif _positive_int(seeds, "seed_phase_count") < MIN_SEED_PHASES:
        findings.append("seed-phase-count-below-minimum")
    periods = run.get("tracked_periods")
    if periods is None:
        findings.append("tracked-periods-not-recorded")
    elif _positive_int(periods, "tracked_periods") < MIN_TRACKED_PERIODS:
        findings.append("tracked-periods-below-minimum")
    mesh = run.get("mesh_convergence_delta")
    if mesh is None:
        findings.append("field-mesh-convergence-not-recorded")
    else:
        mesh = abs(_real(mesh, "mesh_convergence_delta"))
        if not _at_least(MAX_MESH_DELTA, mesh):
            findings.append("field-mesh-not-converged")
    sensitivity = run.get("seed_sensitivity")
    if sensitivity is None:
        findings.append("seed-sensitivity-not-recorded")
    else:
        sensitivity = abs(_real(sensitivity, "seed_sensitivity"))
        if not _at_least(MAX_SEED_SENSITIVITY, sensitivity):
            findings.append("threshold-still-moving-with-seed-count")
    return {"converged": not findings, "findings": findings}


def assess_single_carrier_run(run):
    """Full clause-5.3.2.3.3 verdict for one susceptible gap."""
    if not isinstance(run, dict):
        raise ValueError("run record must be a mapping, got %r" % (run,))
    for key in _RUN_KEYS:
        if key not in run:
            raise ValueError("run record missing required key %r" % (key,))
    if not isinstance(run["item_id"], str) or not run["item_id"].strip():
        raise ValueError("item_id must be a non-blank string")
    gap = _positive(run["gap_m"], "gap_m")
    frequency = _positive(run["frequency_hz"], "frequency_hz")
    ref_field = _positive(run["reference_field_v_per_m"], "reference_field_v_per_m")
    ref_power = _positive(run["reference_power_w"], "reference_power_w")
    operating = _positive(run["operating_power_w"], "operating_power_w")
    required = _positive(run["required_margin_db"], "required_margin_db")

    phase_count = run.get("seed_phase_count", DEFAULT_SEED_PHASES)
    phases = seed_phases(phase_count)
    solved = single_carrier_threshold_field(
        gap,
        frequency,
        run["yield_curve"],
        run.get("field_low_v_per_m", 0.01 * ref_field),
        run.get("field_high_v_per_m", 10.0 * ref_field),
        phases=phases,
        steps_per_period=run.get("steps_per_period", DEFAULT_STEPS_PER_PERIOD),
        tracked_periods=run.get("tracked_periods", DEFAULT_TRACKED_PERIODS),
    )
    p_threshold = threshold_power_w(
        solved["threshold_field_v_per_m"], ref_field, ref_power
    )
    margin = multipactor_margin_db(p_threshold, operating)
    convergence = check_convergence(
        {
            "seed_phase_count": phase_count,
            "tracked_periods": run.get("tracked_periods", DEFAULT_TRACKED_PERIODS),
            "mesh_convergence_delta": run.get("mesh_convergence_delta"),
            "seed_sensitivity": run.get("seed_sensitivity"),
        }
    )
    findings = list(convergence["findings"])
    if not _at_least(margin, required):
        findings.append("single-carrier-margin-shortfall")
    return {
        "item_id": run["item_id"].strip(),
        "threshold_field_v_per_m": solved["threshold_field_v_per_m"],
        "threshold_gap_voltage_v": solved["threshold_gap_voltage_v"],
        "threshold_power_w": p_threshold,
        "margin_db": margin,
        "converged": convergence["converged"],
        "findings": findings,
        "compliant": not findings,
    }
