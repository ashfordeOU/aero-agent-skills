#!/usr/bin/env python3
"""Banked-turn rotor power and sustained maneuver for a rotorcraft (SI units).

Uniform-inflow momentum theory for a steady coordinated level turn at
true airspeed V and load factor n >= 1. The rotor disk banks so the
thrust axis carries the resultant n * W, and the free stream stays in
the disk plane, so the inflow equation keeps the level-flight Glauert
form at the raised thrust:

    T = n * W = 2 * rho * A * v_i * sqrt(V**2 + v_i**2),  v_i >= 0

with W = m * g0 the weight and A = pi * R**2 the disk area. The turning
induced velocity v_i is the unique root (the left side is strictly
increasing on v_i >= 0), found by a FIXED-COUNT bisection on
[0.0, sqrt(n * W / (2 * rho * A))] (BISECT_ITER = 120 iterations, no
tolerance-based early exit). At n = 1 the solve reproduces the
level-flight Glauert value of the rotorcraft-forward-flight-performance
leaf exactly; at V = 0 it returns sqrt(n * W / (2 * rho * A)) =
sqrt(n) * v_h, the hover identity of the rotorcraft-hover-performance
leaf at n = 1.

The turn power breaks into the induced term k * T * v_i (induced power
factor k = K_DEFAULT = 1.15, the hover and forward-flight convention),
the profile term (1/8) * rho * solidity * Cd * A * V_tip**3 at the
fixed rotor speed, and the parasite term 0.5 * rho * V**3 * f.
sustained_load_factor inverts the strictly increasing total power to
find the power-sustained load factor n_s by FIXED-COUNT bisection on
[1.0, N_CEILING], and the bank angle acos(1 / n), turn rate and turn
radius close the maneuver with the standard level-turn kinematics.

All functions raise ValueError on non-physical inputs. Units are SI
throughout: thrust and weight in N, powers in W, speeds and induced
velocities in m/s, area and flat-plate area in m2, density in kg/m3,
angles in rad.
"""

import math

# Module constants (SI).
G0 = 9.80665          # standard gravity, m/s2
K_DEFAULT = 1.15      # induced power factor, hover and forward-flight convention
CD0_DEFAULT = 0.012   # average rotor blade drag coefficient
N_CEILING = 10.0      # bisection ceiling for the sustained load factor
BISECT_ITER = 120     # fixed iteration count for every bisection solve
PI = math.pi


def _bisect_root(low, high, excess):
    """Fixed-count bisection root of a strictly increasing excess function.

    excess(mid) is the signed residual to zero; the root is bracketed on
    [low, high] with excess(low) <= 0 <= excess(high). Runs exactly
    BISECT_ITER iterations and returns the final midpoint, with no
    tolerance-based early exit.
    """
    lo, hi = low, high
    for _ in range(BISECT_ITER):
        mid = 0.5 * (lo + hi)
        if excess(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def thrust_for_turn(load_factor, weight):
    """Rotor thrust of the banked level turn: T = n * W in N.

    The disk thrust axis carries the resultant load: at load factor n
    the turn thrust is n times the weight W = m * g0.
    Raises ValueError if load_factor < 1.0 or weight <= 0.
    """
    if load_factor < 1.0:
        raise ValueError("load_factor must be >= 1.0 for a level turn")
    if weight <= 0:
        raise ValueError("weight must be positive (N)")
    return load_factor * weight


def generalized_induced_velocity(load_factor, weight, area, rho, speed):
    """Turning induced velocity v_i in m/s for the banked level turn.

    Fixed-count bisection root of 2 * rho * area * v_i *
    sqrt(speed**2 + v_i**2) - load_factor * weight on v_i >= 0. The
    bracket is [0.0, sqrt(load_factor * weight / (2 * rho * area))] and
    the root is unique because the left side is strictly increasing.
    Speed zero is valid and returns the sqrt(n) * v_h hover value.
    Raises ValueError if load_factor < 1.0, weight <= 0, area <= 0,
    rho <= 0 or speed < 0.
    """
    if load_factor < 1.0:
        raise ValueError("load_factor must be >= 1.0 for a level turn")
    if weight <= 0:
        raise ValueError("weight must be positive (N)")
    if area <= 0:
        raise ValueError("area must be positive (m2)")
    if rho <= 0:
        raise ValueError("rho must be positive (kg/m3)")
    if speed < 0:
        raise ValueError("speed must be non-negative (m/s)")
    target = load_factor * weight
    hi = math.sqrt(target / (2.0 * rho * area))

    def _excess(v):
        return (2.0 * rho * area * v
                * math.sqrt(speed * speed + v * v)) - target

    return _bisect_root(0.0, hi, _excess)


def induced_power(load_factor, weight, induced_velocity, k=K_DEFAULT):
    """Turn induced power: P_i = k * n * W * v_i in W.

    Uses the induced power factor k = 1.15 convention of the hover and
    forward-flight leaves. Raises ValueError if k <= 0, load_factor <
    1.0, weight <= 0 or induced_velocity < 0.
    """
    if k <= 0:
        raise ValueError("induced power factor k must be positive")
    if load_factor < 1.0:
        raise ValueError("load_factor must be >= 1.0 for a level turn")
    if weight <= 0:
        raise ValueError("weight must be positive (N)")
    if induced_velocity < 0:
        raise ValueError("induced velocity must be non-negative (m/s)")
    return k * load_factor * weight * induced_velocity


def profile_power(rho, area, solidity, drag_coefficient=CD0_DEFAULT,
                  tip_speed=220.0):
    """Rotor profile power in W from the average-section-drag model.

    P_prof = (1/8) * rho * solidity * drag_coefficient * area *
    tip_speed**3, shared verbatim with the hover and forward-flight
    leaves; the turn model keeps the rotor speed fixed, so the profile
    power of the turn equals the level-flight value.
    Raises ValueError if any input is <= 0.
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


def parasite_power(rho, speed, flat_plate_area):
    """Parasite power: P_par = 0.5 * rho * speed**3 * f in W.

    Raises ValueError if rho <= 0, speed < 0 or flat_plate_area < 0.
    """
    if rho <= 0:
        raise ValueError("rho must be positive (kg/m3)")
    if speed < 0:
        raise ValueError("speed must be non-negative (m/s)")
    if flat_plate_area < 0:
        raise ValueError("flat-plate area must be non-negative (m2)")
    return 0.5 * rho * speed ** 3 * flat_plate_area


def turn_power(load_factor, weight, area, rho, speed, solidity,
               drag_coefficient, tip_speed, flat_plate_area, k=K_DEFAULT):
    """Turn power breakdown dict for the banked level turn.

    Computed in the fixed order thrust_for_turn,
    generalized_induced_velocity, induced_power, profile_power,
    parasite_power, then total = induced + profile + parasite. Total
    power is strictly increasing in load_factor because both n * W and
    v_i rise with n. Dict keys exactly: load_factor, thrust,
    induced_velocity, induced_power, profile_power, parasite_power,
    total_power. Propagates every component ValueError.
    """
    thrust = thrust_for_turn(load_factor, weight)
    v_i = generalized_induced_velocity(load_factor, weight, area, rho,
                                       speed)
    p_ind = induced_power(load_factor, weight, v_i, k)
    p_prof = profile_power(rho, area, solidity, drag_coefficient,
                           tip_speed)
    p_par = parasite_power(rho, speed, flat_plate_area)
    return {
        "load_factor": load_factor,
        "thrust": thrust,
        "induced_velocity": v_i,
        "induced_power": p_ind,
        "profile_power": p_prof,
        "parasite_power": p_par,
        "total_power": p_ind + p_prof + p_par,
    }


def sustained_load_factor(available_power, weight, area, rho, speed,
                          solidity, drag_coefficient, tip_speed,
                          flat_plate_area, k=K_DEFAULT, ceiling=N_CEILING):
    """Power-sustained load factor of the banked level turn.

    h(n) = total turn power at n minus available_power is strictly
    increasing, so a FIXED-COUNT bisection on [1.0, ceiling]
    (BISECT_ITER = 120 iterations) finds the power-sustained load
    factor n_s: the largest n whose turn power the available power
    covers, and the required power at the returned n equals the
    available power. When the total power at n = ceiling stays below
    available_power the function returns load_factor = ceiling with
    note "power-excess above ceiling"; otherwise note "power-limited".
    bank_angle = acos(1 / load_factor) in rad closes the level turn.
    Returns a dict with keys exactly: load_factor, bank_angle,
    induced_velocity, induced_power, profile_power, parasite_power,
    total_power, note.
    Raises ValueError when the total power at n = 1 exceeds
    available_power (level flight cannot be sustained at this speed),
    when available_power <= 0, when ceiling <= 1.0, and on every
    non-positive rotor input (weight, area, rho, solidity, drag
    coefficient, tip_speed, k) and on speed < 0.
    """
    if available_power <= 0:
        raise ValueError("available power must be positive (W)")
    if ceiling <= 1.0:
        raise ValueError("ceiling must be above 1.0")
    p_prof = profile_power(rho, area, solidity, drag_coefficient,
                           tip_speed)
    p_par = parasite_power(rho, speed, flat_plate_area)

    def _turn_total(n):
        v_i = generalized_induced_velocity(n, weight, area, rho, speed)
        return induced_power(n, weight, v_i, k) + p_prof + p_par

    level_total = _turn_total(1.0)
    if level_total > available_power:
        raise ValueError(
            "available power cannot sustain level flight at this speed")
    ceiling_total = _turn_total(ceiling)
    if ceiling_total < available_power:
        n_s = ceiling
        note = "power-excess above ceiling"
    else:
        n_s = _bisect_root(1.0, ceiling,
                           lambda n: _turn_total(n) - available_power)
        note = "power-limited"
    v_i = generalized_induced_velocity(n_s, weight, area, rho, speed)
    p_ind = induced_power(n_s, weight, v_i, k)
    return {
        "load_factor": n_s,
        "bank_angle": math.acos(1.0 / n_s),
        "induced_velocity": v_i,
        "induced_power": p_ind,
        "profile_power": p_prof,
        "parasite_power": p_par,
        "total_power": p_ind + p_prof + p_par,
        "note": note,
    }


def bank_from_load_factor(load_factor):
    """Bank angle of the level turn: acos(1 / load_factor) in rad.

    Raises ValueError if load_factor < 1.0 (the n >= 1 domain of the
    level turn).
    """
    if load_factor < 1.0:
        raise ValueError("load_factor must be >= 1.0 for a level turn")
    return math.acos(1.0 / load_factor)


def turn_rate(load_factor, speed):
    """Turn rate omega = G0 * sqrt(n**2 - 1) / V in rad/s.

    Standard level-turn kinematics shared with the turn-performance
    leaf. Raises ValueError if load_factor < 1.0 or speed <= 0.
    """
    if load_factor < 1.0:
        raise ValueError("load_factor must be >= 1.0 for a level turn")
    if speed <= 0:
        raise ValueError("speed must be positive (m/s)")
    return G0 * math.sqrt(load_factor ** 2 - 1.0) / speed


def turn_radius(load_factor, speed):
    """Turn radius R = V**2 / (G0 * sqrt(n**2 - 1)) in m.

    Standard level-turn kinematics shared with the turn-performance
    leaf. Raises ValueError if load_factor < 1.0 or speed <= 0.
    """
    if load_factor < 1.0:
        raise ValueError("load_factor must be >= 1.0 for a level turn")
    if speed <= 0:
        raise ValueError("speed must be positive (m/s)")
    return speed ** 2 / (G0 * math.sqrt(load_factor ** 2 - 1.0))


def max_bank_from_power(available_power, weight, area, rho, speed,
                        solidity, drag_coefficient, tip_speed,
                        flat_plate_area, k=K_DEFAULT, ceiling=N_CEILING):
    """Maximum bank angle in rad from one sustained_load_factor solve.

    Returns acos(1 / load_factor) with the load factor from the single
    sustained solve (no double iteration) and propagates the same
    ValueErrors.
    """
    result = sustained_load_factor(available_power, weight, area, rho,
                                   speed, solidity, drag_coefficient,
                                   tip_speed, flat_plate_area, k, ceiling)
    return result["bank_angle"]
