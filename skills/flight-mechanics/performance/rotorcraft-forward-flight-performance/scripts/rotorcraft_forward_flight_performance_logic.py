#!/usr/bin/env python3
"""Forward-flight rotor power breakdown for a rotorcraft rotor (SI units).

Momentum-theory inflow model: the Glauert induced velocity at a given
flight speed, ideal induced power, parasite power from the equivalent
flat-plate drag area, profile power from blade solidity and tip speed,
total power through the induced power factor, and the characteristic
speeds of a speed sweep (best endurance speed at minimum total power,
best range speed proxy at minimum power per unit speed).

All functions raise ValueError on non-physical inputs; the Glauert
fixed-point iteration raises RuntimeError if it does not converge
within max_iter iterations. Units are SI throughout: thrust T and
power P in newtons and watts, speed V and induced velocity v in m/s,
area A in m2, flat-plate area f in m2, density rho in kg/m3,
solidity and drag coefficient dimensionless.
"""

import math

# Module constants (SI).
G0 = 9.80665        # standard gravity, m/s2
RHO_SL = 1.225      # sea-level air density, kg/m3, used only as default
PI = math.pi
K_DEFAULT = 1.15    # induced power factor, matching the hover leaf
CD0_DEFAULT = 0.012  # average rotor blade drag coefficient
MAX_ITER = 60       # Glauert fixed-point iteration cap
TOL = 1e-9          # Glauert fixed-point convergence tolerance, m/s


def hover_induced_velocity(thrust, area, rho=RHO_SL):
    """Ideal momentum-theory induced velocity in hover.

    v_h = sqrt(thrust / (2 * rho * area)) in m/s.
    Units: thrust in N, area in m2, rho in kg/m3.
    Raises ValueError if thrust <= 0, area <= 0, or rho <= 0.
    """
    if thrust <= 0:
        raise ValueError("thrust must be positive (N)")
    if area <= 0:
        raise ValueError("area must be positive (m2)")
    if rho <= 0:
        raise ValueError("rho must be positive (kg/m3)")
    return math.sqrt(thrust / (2.0 * rho * area))


def glauert_induced_velocity(thrust, area, rho, speed, max_iter=MAX_ITER,
                             tol=TOL):
    """Glauert induced velocity at forward speed by fixed-point iteration.

    Solves v = thrust / (2 * rho * area * sqrt(speed**2 + v**2)),
    starting from the hover value v_h and iterating the substitution
    v_new = f(v) until |v_new - v| < tol or max_iter is exceeded. The
    substitution contracts slowly near hover (ratio about v**2 /
    (speed**2 + v**2) at the root), so each pass applies the standard
    delta-squared acceleration to the last two substitution images
    when the denominator is usable; the plain image is kept otherwise.
    Both routes converge on the same unique positive fixed point.
    Units: thrust in N, area in m2, rho in kg/m3, speed and v in m/s.
    Raises ValueError if speed < 0 (speed == 0 is allowed and returns
    the hover value), thrust <= 0, area <= 0, or rho <= 0; RuntimeError
    if the fixed point does not converge within max_iter iterations.
    """
    if speed < 0:
        raise ValueError("speed must be non-negative (m/s)")
    if thrust <= 0:
        raise ValueError("thrust must be positive (N)")
    if area <= 0:
        raise ValueError("area must be positive (m2)")
    if rho <= 0:
        raise ValueError("rho must be positive (kg/m3)")
    v = hover_induced_velocity(thrust, area, rho)
    if speed == 0.0:
        return v
    factor = thrust / (2.0 * rho * area)

    def substitute(v_cur):
        """One substitution image of the Glauert equation."""
        return factor / math.sqrt(speed * speed + v_cur * v_cur)

    i = 0
    while i < max_iter:
        v_1 = substitute(v)
        if abs(v_1 - v) < tol:
            return v_1
        v_2 = substitute(v_1)
        denom = v_2 - 2.0 * v_1 + v
        v_acc = None
        if denom != 0.0:
            cand = v - (v_1 - v) * (v_1 - v) / denom
            if cand > 0.0 and math.isfinite(cand):
                v_acc = cand
        if v_acc is None:
            v = v_1
        else:
            v = v_acc
        i += 1
    raise RuntimeError(
        "Glauert fixed-point iteration failed to converge within "
        "%d iterations" % max_iter)


def induced_power(thrust, induced_velocity):
    """Ideal induced power of the rotor at forward speed.

    P_i = thrust * induced_velocity in W.
    Units: thrust in N, induced velocity in m/s.
    Raises ValueError if thrust <= 0 or induced_velocity < 0.
    """
    if thrust <= 0:
        raise ValueError("thrust must be positive (N)")
    if induced_velocity < 0:
        raise ValueError("induced velocity must be non-negative (m/s)")
    return thrust * induced_velocity


def parasite_power(rho, speed, flat_plate_area):
    """Parasite power of the airframe at forward speed.

    P_par = 0.5 * rho * speed**3 * flat_plate_area in W, where the
    flat-plate area f = D / (0.5 * rho * speed**2) summarizes the
    airframe drag.
    Units: rho in kg/m3, speed in m/s, flat_plate_area in m2.
    Raises ValueError if speed < 0, flat_plate_area < 0, or rho <= 0.
    """
    if speed < 0:
        raise ValueError("speed must be non-negative (m/s)")
    if flat_plate_area < 0:
        raise ValueError("flat-plate area must be non-negative (m2)")
    if rho <= 0:
        raise ValueError("rho must be positive (kg/m3)")
    return 0.5 * rho * speed ** 3 * flat_plate_area


def profile_power(rho, area, solidity, drag_coefficient=CD0_DEFAULT,
                  tip_speed=220.0):
    """Rotor profile power from the average blade drag model.

    P_profile = (1/8) * rho * solidity * drag_coefficient * area *
    tip_speed**3 in W (average section drag over the rotor disk).
    Units: rho in kg/m3, area in m2, tip_speed in m/s.
    Raises ValueError if any of rho, area, solidity, drag_coefficient,
    tip_speed <= 0.
    """
    if rho <= 0:
        raise ValueError("rho must be positive (kg/m3)")
    if area <= 0:
        raise ValueError("area must be positive (m2)")
    if solidity <= 0:
        raise ValueError("solidity must be positive")
    if drag_coefficient <= 0:
        raise ValueError("drag coefficient must be positive")
    if tip_speed <= 0:
        raise ValueError("tip speed must be positive (m/s)")
    return (1.0 / 8.0) * rho * solidity * drag_coefficient * area \
        * tip_speed ** 3


def total_power(thrust, induced_velocity, profile_power, parasite_power,
                k=K_DEFAULT):
    """Total rotor power required at forward speed.

    P_total = k * thrust * induced_velocity + profile_power +
    parasite_power in W, where k is the induced power factor that
    accounts for non-uniform and tip-loss inflow.
    Units: thrust in N, induced velocity in m/s, powers in W.
    Raises ValueError if thrust <= 0, induced_velocity < 0,
    profile_power < 0, parasite_power < 0, or k <= 0.
    """
    if thrust <= 0:
        raise ValueError("thrust must be positive (N)")
    if induced_velocity < 0:
        raise ValueError("induced velocity must be non-negative (m/s)")
    if profile_power < 0:
        raise ValueError("profile power must be non-negative (W)")
    if parasite_power < 0:
        raise ValueError("parasite power must be non-negative (W)")
    if k <= 0:
        raise ValueError("induced power factor k must be positive")
    return k * thrust * induced_velocity + profile_power + parasite_power


def power_sweep(thrust, area, rho, flat_plate_area, solidity,
                drag_coefficient=CD0_DEFAULT, tip_speed=220.0, speeds=None,
                k=K_DEFAULT):
    """Total power over a forward-speed sweep.

    Returns a list of (speed, total_power) pairs, one per speed in the
    sweep. Default speeds run 5.0 to 100.0 m/s in 1.0 m/s steps
    (range(5, 101) as floats). At each speed the Glauert induced
    velocity, induced power, parasite power and (constant) profile
    power are combined into the total power.
    Units: thrust in N, area and flat_plate_area in m2, rho in kg/m3,
    speeds in m/s, powers in W. ValueErrors propagate from the model
    functions on non-physical inputs.
    """
    if speeds is None:
        speeds = [float(s) for s in range(5, 101)]
    profile = profile_power(rho, area, solidity, drag_coefficient,
                            tip_speed)
    pairs = []
    for speed in speeds:
        v = glauert_induced_velocity(thrust, area, rho, speed)
        p_induced = induced_power(thrust, v)
        p_parasite = parasite_power(rho, speed, flat_plate_area)
        p_total = total_power(thrust, v, profile, p_parasite, k=k)
        pairs.append((speed, p_total))
    return pairs


def best_endurance_speed(thrust, area, rho, flat_plate_area, solidity,
                         drag_coefficient=CD0_DEFAULT, tip_speed=220.0,
                         speeds=None, k=K_DEFAULT):
    """Speed of minimum total power over the sweep (best endurance).

    Argmin of total power over the speed sweep; if two speeds tie to
    within 1e-9 the lower speed is returned. Units as power_sweep;
    returns the speed in m/s.
    """
    pairs = power_sweep(thrust, area, rho, flat_plate_area, solidity,
                        drag_coefficient, tip_speed, speeds, k)
    best_speed = None
    best_power = None
    for speed, p_total in pairs:
        if best_power is None or p_total < best_power - 1e-9:
            best_speed = speed
            best_power = p_total
    return best_speed


def best_range_speed(thrust, area, rho, flat_plate_area, solidity,
                     drag_coefficient=CD0_DEFAULT, tip_speed=220.0,
                     speeds=None, k=K_DEFAULT):
    """Speed minimizing power per unit speed over the sweep.

    Argmin of total_power / speed over the sweep (speed 0 is skipped);
    if two speeds tie to within 1e-9 the lower speed is returned.
    Returns (speed, power_per_speed) with speed in m/s and
    power_per_speed in W per (m/s).
    """
    pairs = power_sweep(thrust, area, rho, flat_plate_area, solidity,
                        drag_coefficient, tip_speed, speeds, k)
    best_speed = None
    best_ratio = None
    for speed, p_total in pairs:
        if speed <= 0:
            continue
        ratio = p_total / speed
        if best_ratio is None or ratio < best_ratio - 1e-9:
            best_speed = speed
            best_ratio = ratio
    return (best_speed, best_ratio)
