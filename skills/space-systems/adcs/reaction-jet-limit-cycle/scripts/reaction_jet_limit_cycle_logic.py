"""Reaction-jet limit-cycle propellant demand model (space-systems/adcs).

Wertz-class aggregate estimate of the RCS attitude-hold propellant
demand of a bang-bang deadband limit cycle, pure stdlib math only.
Deadband is +/-h about the reference attitude, h the half-angle in rad.
Each half oscillation is idealized as a constant-torque arc under the
control acceleration covering the full deadband width 2h from rest,
which pins the aggregate cycle period at T_cycle = 4 * sqrt(h / alpha_c)
and the crossing rate at omega = sqrt(2 * alpha_c * h). One braking
pulse of force F_t removes the crossing rate at each deadband edge, so
each limit cycle costs two pulses. Propellant follows from the pulse
linear impulse at a fixed specific impulse; blowdown, valve dynamics,
disturbance torques and coupled multiaxis sequencing are out of scope
(they belong to the propulsion hardware and control-law leaves).
"""

import math

G0 = 9.80665  # standard gravity, m/s^2


def control_accel(torque_Nm, inertia_kgm2):
    """Control angular acceleration alpha_c = torque / inertia in rad/s^2.

    Step 1 of the SKILL.md workflow, fixing the control authority.
    """
    if torque_Nm <= 0:
        raise ValueError("control torque must be positive, got %r" % (torque_Nm,))
    if inertia_kgm2 <= 0:
        raise ValueError("axis inertia must be positive, got %r" % (inertia_kgm2,))
    return torque_Nm / inertia_kgm2


def limit_cycle_rate(alpha_c, h_rad):
    """Angular rate omega at the deadband crossing, sqrt(2 * alpha_c * h).

    Step 2 of the SKILL.md workflow, the constant-torque rate gained
    from rest over the half-angle h (v^2 = 2 * a * s with s = h).
    """
    if alpha_c <= 0:
        raise ValueError("control acceleration must be positive, got %r" % (alpha_c,))
    if h_rad <= 0:
        raise ValueError("deadband half-angle must be positive, got %r" % (h_rad,))
    return math.sqrt(2.0 * alpha_c * h_rad)


def pulse_time(omega_rad_s, alpha_c):
    """Firing duration t_fire = omega / alpha_c of one braking pulse in s.

    Step 3 of the SKILL.md workflow, the rate change alpha_c * t_fire
    that removes the crossing rate omega.
    """
    if omega_rad_s <= 0:
        raise ValueError("crossing rate must be positive, got %r" % (omega_rad_s,))
    if alpha_c <= 0:
        raise ValueError("control acceleration must be positive, got %r" % (alpha_c,))
    return omega_rad_s / alpha_c


def pulse_delta_v(thrust_N, t_fire_s, mass_kg):
    """Linear delta-V of one pulse, thrust * t_fire / mass, in m/s."""
    _require_positive(thrust_N, "thrust")
    _require_positive(t_fire_s, "firing time")
    _require_positive(mass_kg, "spacecraft mass")
    return thrust_N * t_fire_s / mass_kg


def pulse_propellant(thrust_N, t_fire_s, isp_s):
    """Propellant mass of one pulse, thrust * t_fire / (isp * G0), in kg.

    Step 4 of the SKILL.md workflow, the pulse mass at fixed Isp. No
    blowdown: F_t and Isp are constants of the demand model.
    """
    _require_positive(thrust_N, "thrust")
    _require_positive(t_fire_s, "firing time")
    _require_positive(isp_s, "specific impulse")
    return thrust_N * t_fire_s / (isp_s * G0)


def delta_v_per_cycle(thrust_N, t_fire_s, mass_kg):
    """Linear delta-V of one full limit cycle (two pulses) in m/s."""
    return 2.0 * pulse_delta_v(thrust_N, t_fire_s, mass_kg)


def propellant_per_cycle(thrust_N, t_fire_s, isp_s):
    """Propellant mass of one full limit cycle (two pulses) in kg."""
    return 2.0 * pulse_propellant(thrust_N, t_fire_s, isp_s)


def cycle_period(h_rad, alpha_c):
    """Aggregate limit-cycle period T_cycle = 4 * sqrt(h / alpha_c) in s.

    Step 5 of the SKILL.md workflow. Model idealization: each half
    oscillation is a constant-torque arc covering the full deadband
    width 2h from rest, 2h = alpha_c * tau^2 / 2, so the half period is
    2 * sqrt(h / alpha_c) and the full cycle doubles it.
    """
    if h_rad <= 0:
        raise ValueError("deadband half-angle must be positive, got %r" % (h_rad,))
    if alpha_c <= 0:
        raise ValueError("control acceleration must be positive, got %r" % (alpha_c,))
    return 4.0 * math.sqrt(h_rad / alpha_c)


def cycles_over_life(life_s, period_s):
    """Cycle count over an active duration, life / period.

    Step 6 of the SKILL.md workflow, the aggregate cycle count over the
    active (duty-scaled) mission duration.
    """
    if life_s <= 0:
        raise ValueError("life duration must be positive, got %r" % (life_s,))
    if period_s <= 0:
        raise ValueError("cycle period must be positive, got %r" % (period_s,))
    return life_s / period_s


def _require_positive(value, name):
    """Raise ValueError unless value is strictly positive."""
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (name, value))


def _axis_result(axis, life_s):
    """Compute the per-axis limit-cycle state dict for one input axis."""
    alpha_c = control_accel(axis["torque_Nm"], axis["inertia_kgm2"])
    omega = limit_cycle_rate(alpha_c, axis["deadband_half_rad"])
    t_fire = pulse_time(omega, alpha_c)
    dv_pulse = pulse_delta_v(axis["thrust_N"], t_fire, axis["mass_kg"])
    dv_cycle = delta_v_per_cycle(axis["thrust_N"], t_fire, axis["mass_kg"])
    prop_pulse = pulse_propellant(axis["thrust_N"], t_fire, axis["isp_s"])
    prop_cycle = propellant_per_cycle(axis["thrust_N"], t_fire, axis["isp_s"])
    period = cycle_period(axis["deadband_half_rad"], alpha_c)
    cycles = cycles_over_life(life_s, period)
    return {
        "alpha_c_rad_s2": alpha_c,
        "omega_rad_s": omega,
        "t_fire_s": t_fire,
        "delta_v_per_pulse_m_s": dv_pulse,
        "delta_v_per_cycle_m_s": dv_cycle,
        "propellant_per_pulse_kg": prop_pulse,
        "propellant_per_cycle_kg": prop_cycle,
        "cycle_period_s": period,
        "cycles": cycles,
        "pulses": 2.0 * cycles,
        "propellant_life_kg": cycles * prop_cycle,
    }


def propellant_budget(axes, life_s, duty_factor=1.0):
    """Three-axis lifetime reaction-jet propellant budget, aggregate.

    Step 7 of the SKILL.md workflow. Each input axis is a dict with
    keys name, mass_kg, inertia_kgm2, torque_Nm, thrust_N, isp_s and
    deadband_half_rad. The active hold duration is duty_factor * life_s;
    per-axis lifetime propellant is cycles * propellant_per_cycle and
    the total sums the per-axis lifetime propellant.
    """
    if not axes:
        raise ValueError("at least one axis is required")
    if life_s <= 0:
        raise ValueError("life duration must be positive, got %r" % (life_s,))
    if duty_factor <= 0 or duty_factor > 1.0:
        raise ValueError("duty factor must be in (0, 1], got %r" % (duty_factor,))
    active_life = duty_factor * life_s
    axis_results = {}
    total = 0.0
    for axis in axes:
        name = axis["name"]
        result = _axis_result(axis, active_life)
        axis_results[name] = result
        total += result["propellant_life_kg"]
    return {"axes": axis_results, "propellant_total_kg": total}
