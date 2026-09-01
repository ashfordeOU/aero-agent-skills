#!/usr/bin/env python3
"""Propeller sizing logic (paraphrase, common conceptual practice).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: reference
only, gated false): the propeller converts shaft power into thrust by
accelerating a disk of air. The key sizing quantities are the propeller
diameter D, the rotational speed n in revolutions per second, the blade
count B, the blade chord c, the disk area A = pi * D^2 / 4, the flight
speed V, and the shaft power P.

The advance ratio J = V / (n * D) sets the operating point of the disk
and drives the efficiency versus advance ratio curve. The tip speed
pi * D * n is limited by the tip Mach number (losses and noise grow as
the tip approaches the local speed of sound). The disk loading T / A
and the power loading T / (P / 1000) [N per kW] set the propulsive
efficiency: a lightly loaded disk of large diameter is more efficient
at low speed, but the diameter is constrained by the tip speed limit
and by the ground clearance (D / 2 below the hub height). Static thrust
follows from actuator disk momentum theory as
T = (2 * rho * A * P^2)^(1/3) at zero forward speed. Blade count and
blade geometry are captured by the solidity sigma = B * c / (pi * D)
and by the activity factor, a dimensionless blade loading integral
(summarized here with a constant-chord approximation). P-factor is the
yawing moment from the asymmetric thrust of the descending blade at
angle of attack. In flight the thrust follows from the power and the
propulsive efficiency as T = eta * P / V, which is the thrust versus
power trade: at low speed a given power delivers more thrust, so the
static case is the maximum.

Units are SI throughout: forces in N, powers in W, lengths in m, speeds
in m/s, rpm in revolutions per minute, densities in kg/m^3, angles in
radians, Mach numbers and efficiencies unitless. Invalid inputs raise
ValueError throughout.
"""

import math

_TAU = 2.0 * math.pi  # radians per revolution


def _require_positive(value, name):
    """Raise ValueError unless value is a positive finite number."""
    if not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (name, value))


def _require_nonnegative(value, name):
    """Raise ValueError unless value is a non-negative finite number."""
    if not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %r" % (name, value))


def _require_unit_interval(value, name):
    """Raise ValueError unless value lies in the closed interval (0, 1]."""
    if not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if not (0 < value <= 1):
        raise ValueError("%s must lie in (0, 1], got %r" % (name, value))


def advance_ratio(speed_mps, rpm, diameter_m):
    """Advance ratio J = V / (n * D) with n = rpm / 60.

    J is the distance the aircraft advances per propeller revolution
    expressed in diameters. Anchor: V = 70 m/s, rpm = 2200,
    D = 2.0 m give J = 70 / (2200 / 60 * 2.0) = 0.9545. Static flight
    (V = 0) is allowed and gives J = 0. Diameter and rpm must be
    positive.
    """
    _require_nonnegative(speed_mps, "speed")
    _require_positive(rpm, "rpm")
    _require_positive(diameter_m, "diameter")
    n = rpm / 60.0
    return speed_mps / (n * diameter_m)


def tip_speed(rpm, diameter_m):
    """Propeller tip speed V_tip = pi * D * n in m/s.

    Anchor: rpm = 2200 and D = 2.0 m give V_tip = pi * 2.0 * 2200 / 60
    = 230.38 m/s. Raises ValueError for non-positive rpm or diameter.
    """
    _require_positive(rpm, "rpm")
    _require_positive(diameter_m, "diameter")
    n = rpm / 60.0
    return math.pi * diameter_m * n


def tip_mach_number(tip_speed_mps, speed_of_sound_mps):
    """Tip Mach number M_tip = V_tip / a.

    Anchor: V_tip = 230.38 m/s at a = 340.3 m/s gives M_tip = 0.677.
    Both inputs must be positive.
    """
    _require_positive(tip_speed_mps, "tip speed")
    _require_positive(speed_of_sound_mps, "speed of sound")
    return tip_speed_mps / speed_of_sound_mps


def tip_mach_check(rpm, diameter_m, speed_of_sound_mps, mach_limit=0.85):
    """Tip speed with Mach check against the tip Mach limit.

    Returns a dict with the tip speed in m/s, the tip Mach number, the
    boolean within_limit (tip Mach at or below the limit), and the
    margin_mach (limit minus tip Mach, negative when exceeded).
    Anchor: rpm = 2200, D = 2.0 m, a = 340.3 m/s at the 0.85 limit give
    tip_mach = 0.677 and within_limit True. Raises ValueError for
    non-positive inputs or a non-positive mach limit.
    """
    _require_positive(mach_limit, "mach limit")
    v = tip_speed(rpm, diameter_m)
    m = tip_mach_number(v, speed_of_sound_mps)
    return {
        "tip_speed_mps": v,
        "tip_mach": m,
        "within_limit": m <= mach_limit,
        "margin_mach": mach_limit - m,
    }


def disk_loading(thrust_N, diameter_m):
    """Disk loading T / A in N/m^2 with A = pi * D^2 / 4.

    Anchor: T = 4000 N and D = 2.0 m give DL = 4000 / pi = 1273.24
    N/m^2. Raises ValueError for non-positive thrust or diameter.
    """
    _require_positive(thrust_N, "thrust")
    _require_positive(diameter_m, "diameter")
    area = math.pi * diameter_m * diameter_m / 4.0
    return thrust_N / area


def power_loading(thrust_N, power_W):
    """Power loading T / (P / 1000) in N per kW.

    Anchor: T = 4000 N and P = 150 kW give 4000 / 150 = 26.667 N/kW.
    Raises ValueError for non-positive thrust or power.
    """
    _require_positive(thrust_N, "thrust")
    _require_positive(power_W, "power")
    return thrust_N / (power_W / 1000.0)


def static_thrust_estimate(power_W, diameter_m, rho=1.225):
    """Ideal static thrust from actuator disk momentum theory.

    T = (2 * rho * A * P^2)^(1/3) with A = pi * D^2 / 4 at zero forward
    speed (no induced or profile losses). Anchor: P = 150 kW, D = 2.0 m,
    rho = 1.225 kg/m^3 give T = 5573.99 N (computed). Raises ValueError
    for non-positive power, diameter, or density.
    """
    _require_positive(power_W, "power")
    _require_positive(diameter_m, "diameter")
    _require_positive(rho, "density")
    area = math.pi * diameter_m * diameter_m / 4.0
    return (2.0 * rho * area * power_W * power_W) ** (1.0 / 3.0)


def power_for_static_thrust(thrust_N, diameter_m, rho=1.225):
    """Shaft power needed for a target ideal static thrust.

    Inverse of the actuator disk relation: P = sqrt(T^3 / (2 * rho * A)).
    Round trip: the 5573.99 N anchor returns 150000 W for D = 2.0 m at
    rho = 1.225. Raises ValueError for non-positive inputs.
    """
    _require_positive(thrust_N, "thrust")
    _require_positive(diameter_m, "diameter")
    _require_positive(rho, "density")
    area = math.pi * diameter_m * diameter_m / 4.0
    return math.sqrt(thrust_N ** 3 / (2.0 * rho * area))


def diameter_from_tip_speed_limit(rpm, tip_speed_limit_mps):
    """Largest diameter allowed by a tip speed limit at a given rpm.

    D = V_limit / (pi * n) with n = rpm / 60. Anchor: rpm = 2200 and
    V_limit = 250 m/s give D = 250 / (pi * 2200 / 60) = 2.1703 m.
    Raises ValueError for non-positive rpm or tip speed limit.
    """
    _require_positive(rpm, "rpm")
    _require_positive(tip_speed_limit_mps, "tip speed limit")
    n = rpm / 60.0
    return tip_speed_limit_mps / (math.pi * n)


def solidity(blade_count, chord_m, diameter_m):
    """Integrated solidity sigma = B * c / (pi * D).

    The solidity is the fraction of the disk covered by the blades;
    the constant-chord summary uses the mean blade chord. Anchor:
    B = 3, c = 0.25 m, D = 2.0 m give sigma = 0.75 / (2 * pi) =
    0.11937. Raises ValueError for non-positive inputs or a blade count
    that is not a positive integer.
    """
    if not isinstance(blade_count, int) or blade_count <= 0:
        raise ValueError(
            "blade count must be a positive integer, got %r" % (blade_count,))
    _require_positive(chord_m, "chord")
    _require_positive(diameter_m, "diameter")
    return blade_count * chord_m / (math.pi * diameter_m)


def activity_factor(blade_count, chord_m, diameter_m, hub_fraction=0.15):
    """Total activity factor from a constant-chord summary.

    The activity factor is a dimensionless blade loading integral over
    the radius fraction x = r / R; the constant-chord summary integrates
    x^3 from the hub fraction to the tip:
    AF = B * (100000 / 16) * (c / D) * (1 - x_hub^4) / 4.
    Anchor: B = 3, c = 0.25 m, D = 2.0 m, x_hub = 0.15 give
    AF = 585.63. Raises ValueError for non-positive inputs, a non
    positive integer blade count, or a hub fraction outside (0, 1).
    """
    if not isinstance(blade_count, int) or blade_count <= 0:
        raise ValueError(
            "blade count must be a positive integer, got %r" % (blade_count,))
    _require_positive(chord_m, "chord")
    _require_positive(diameter_m, "diameter")
    _require_unit_interval(hub_fraction, "hub fraction")
    per_blade = (100000.0 / 16.0) * (chord_m / diameter_m) \
        * (1.0 - hub_fraction ** 4) / 4.0
    return blade_count * per_blade


def efficiency_at_advance_ratio(advance_ratio, design_advance_ratio,
                                max_efficiency):
    """Propeller efficiency versus advance ratio (parabolic model).

    eta = eta_max * (1 - ((J - J_design) / J_design)^2) for J in
    [0, 2 * J_design], and 0 outside that range. The model peaks at the
    design advance ratio and falls to zero at the static point (J = 0,
    no useful work) and at J = 2 * J_design. Anchor: J_design = 0.9 and
    eta_max = 0.85 give eta(0.9) = 0.85, eta(0) = 0.0, eta(1.8) = 0.0,
    and eta(0.45) = 0.6375. Raises ValueError for a non-negative
    advance ratio, a non-positive design advance ratio, or a max
    efficiency outside (0, 1].
    """
    _require_nonnegative(advance_ratio, "advance ratio")
    _require_positive(design_advance_ratio, "design advance ratio")
    _require_unit_interval(max_efficiency, "max efficiency")
    if advance_ratio > 2.0 * design_advance_ratio:
        return 0.0
    offset = (advance_ratio - design_advance_ratio) / design_advance_ratio
    return max_efficiency * (1.0 - offset * offset)


def ground_clearance_check(diameter_m, hub_height_m, min_clearance_m):
    """Ground clearance of the propeller tip.

    The tip sits at hub_height - D / 2 above the ground; returns a dict
    with the clearance in m and the boolean ok (clearance at or above
    the minimum). Anchor: D = 2.0 m at a hub height of 1.6 m gives
    0.6 m of clearance, ok against a 0.2 m minimum; D = 3.0 m gives
    0.1 m, below the 0.2 m minimum. Raises ValueError for non-positive
    inputs.
    """
    _require_positive(diameter_m, "diameter")
    _require_positive(hub_height_m, "hub height")
    _require_nonnegative(min_clearance_m, "min clearance")
    clearance = hub_height_m - diameter_m / 2.0
    return {
        "clearance_m": clearance,
        "ok": clearance >= min_clearance_m,
    }


def p_factor_moment(thrust_N, diameter_m, angle_of_attack_rad):
    """P-factor yawing moment, first-order estimate.

    At angle of attack the descending blade sees a higher relative
    velocity and produces more thrust than the ascending blade, which
    shifts the effective thrust center outboard by about D / 4. The
    first-order estimate is N_p = T * (D / 4) * sin(alpha). Anchor:
    T = 4000 N, D = 2.0 m at alpha = 10 deg give
    N_p = 4000 * 0.5 * sin(10 deg) = 347.30 N m. Detailed analyses use
    blade element theory; this estimate is for the conceptual sizing
    loop. Raises ValueError for non-positive thrust or diameter or an
    angle of attack outside [0, pi / 2] radians.
    """
    _require_positive(thrust_N, "thrust")
    _require_positive(diameter_m, "diameter")
    if not isinstance(angle_of_attack_rad, (int, float)):
        raise ValueError("angle of attack must be a number, got %r"
                         % (angle_of_attack_rad,))
    if not (0.0 <= angle_of_attack_rad <= math.pi / 2.0):
        raise ValueError(
            "angle of attack must lie in [0, pi/2] radians, got %r"
            % (angle_of_attack_rad,))
    return thrust_N * (diameter_m / 4.0) * math.sin(angle_of_attack_rad)


def thrust_from_power_in_flight(power_W, speed_mps, efficiency):
    """Thrust delivered by shaft power at flight speed.

    T = eta * P / V: the thrust-versus-power trade. At low speed a
    given power delivers more thrust, and the static thrust from
    actuator disk theory is the maximum. Anchor: P = 150 kW at
    V = 70 m/s with eta = 0.8 give T = 0.8 * 150000 / 70 = 1714.29 N.
    Raises ValueError for non-positive power or speed or an efficiency
    outside (0, 1].
    """
    _require_positive(power_W, "power")
    _require_positive(speed_mps, "speed")
    _require_unit_interval(efficiency, "efficiency")
    return efficiency * power_W / speed_mps


def demonstrate():
    """Print a demonstration sizing across the module functions."""
    print("advance_ratio(70, 2200, 2.0) = %.4f" % advance_ratio(70, 2200, 2.0))
    print("tip_speed(2200, 2.0) = %.2f m/s" % tip_speed(2200, 2.0))
    print("tip_mach_check(2200, 2.0, 340.3) = %s"
          % tip_mach_check(2200, 2.0, 340.3))
    print("disk_loading(4000, 2.0) = %.2f N/m^2" % disk_loading(4000, 2.0))
    print("power_loading(4000, 150000) = %.3f N/kW"
          % power_loading(4000, 150000))
    print("static_thrust_estimate(150000, 2.0) = %.2f N"
          % static_thrust_estimate(150000, 2.0))
    print("power_for_static_thrust(5575.64, 2.0) = %.2f W"
          % power_for_static_thrust(5575.64, 2.0))
    print("diameter_from_tip_speed_limit(2200, 250) = %.4f m"
          % diameter_from_tip_speed_limit(2200, 250))
    print("solidity(3, 0.25, 2.0) = %.5f" % solidity(3, 0.25, 2.0))
    print("activity_factor(3, 0.25, 2.0) = %.2f" % activity_factor(3, 0.25, 2.0))
    print("efficiency_at_advance_ratio(0.9, 0.9, 0.85) = %.4f"
          % efficiency_at_advance_ratio(0.9, 0.9, 0.85))
    print("efficiency_at_advance_ratio(0.45, 0.9, 0.85) = %.4f"
          % efficiency_at_advance_ratio(0.45, 0.9, 0.85))
    print("ground_clearance_check(2.0, 1.6, 0.2) = %s"
          % ground_clearance_check(2.0, 1.6, 0.2))
    print("p_factor_moment(4000, 2.0, %r) = %.2f N m"
          % (10 * math.pi / 180, p_factor_moment(4000, 2.0, 10 * math.pi / 180)))
    print("thrust_from_power_in_flight(150000, 70, 0.8) = %.2f N"
          % thrust_from_power_in_flight(150000, 70, 0.8))


if __name__ == "__main__":
    demonstrate()
