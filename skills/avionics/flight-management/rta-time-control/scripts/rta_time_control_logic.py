"""RTA time control: the required-time-of-arrival speed command law of an FMS.

Pure Python stdlib, deterministic, offline. Implements the time-based
operation function of a flight management system: estimate the time of
arrival (ETA) at a downstream waypoint from the remaining distance and the
current ground speed, compute the speed adjustment needed to satisfy an RTA
time constraint at the waypoint, check the constraint against the achievable
arrival window set by the minimum and maximum cruise Mach bounds, and return
the Mach command, the predicted time error, the feasibility verdict and the
remaining time error. All inputs and outputs are SI (m, m/s, s, K).

Conventions
- Ground speed = true airspeed + wind along track (positive wind is a
  tailwind).
- eta_rel_s and the window eta_min_s / eta_max_s values are flight durations
  measured from t_now_s. rta_time_s is the required arrival time on the same
  clock as t_now_s (an absolute second count); with t_now_s = 0 it equals the
  seconds remaining until the required arrival.
- predicted_eta_s is the predicted arrival time on that clock and
  remaining_error_s = predicted_eta_s - rta_time_s (positive = late).
- Speed of sound follows the standard ISA troposphere model used by the
  flight-mechanics performance leaves: T = 288.15 - 0.0065 h below the
  11000 m tropopause, a = sqrt(GAMMA * R_GAS * T).
"""

import math

GAMMA = 1.4               # ratio of specific heats for air
R_GAS = 287.05            # specific gas constant for air, J/(kg K)
TIME_TOL_S = 5.0          # RTA met when |time error| <= tolerance, s
ISA_SL_TEMP_K = 288.15    # ISA sea level temperature, K
ISA_LAPSE_K_PER_M = 0.0065  # ISA troposphere lapse rate, K/m
TROPOPAUSE_M = 11000.0    # ISA tropopause altitude, m

VALID_SPEED_MODES = ("mach", "cas")


def _validate_altitude(altitude_m):
    """Raise ValueError when altitude_m is negative."""
    if altitude_m < 0.0:
        raise ValueError("altitude_m must be >= 0: %r" % (altitude_m,))


def _validate_distance(distance_m):
    """Raise ValueError when remaining distance is negative."""
    if distance_m < 0.0:
        raise ValueError("remaining_distance_m must be >= 0: %r" % (distance_m,))


def isa_speed_of_sound(altitude_m):
    """Return the ISA speed of sound a (m/s) at altitude_m.

    Troposphere below 11000 m: a = sqrt(GAMMA * R_GAS * (288.15 - 0.0065 h)),
    isothermal stratosphere above with T = 216.65 K.
    """
    _validate_altitude(altitude_m)
    if altitude_m <= TROPOPAUSE_M:
        temp_k = ISA_SL_TEMP_K - ISA_LAPSE_K_PER_M * altitude_m
    else:
        temp_k = ISA_SL_TEMP_K - ISA_LAPSE_K_PER_M * TROPOPAUSE_M
    return math.sqrt(GAMMA * R_GAS * temp_k)


def eta_s(remaining_distance_m, ground_speed_m_s):
    """Return the estimated flight time to the waypoint (s) from t_now.

    eta = remaining_distance / ground_speed. Rejects a negative distance and
    a non-positive ground speed.
    """
    _validate_distance(remaining_distance_m)
    if ground_speed_m_s <= 0.0:
        raise ValueError("ground_speed_m_s must be > 0: %r" % (ground_speed_m_s,))
    return remaining_distance_m / ground_speed_m_s


def time_error_s(eta_rel_s, rta_time_s, t_now_s):
    """Return the RTA time error (s): (t_now + eta) - rta, positive = late."""
    return (t_now_s + eta_rel_s) - rta_time_s


def required_ground_speed_m_s(remaining_distance_m, rta_time_s, t_now_s):
    """Return the ground speed (m/s) that lands at the waypoint at RTA time.

    required_gs = remaining_distance / (rta_time - t_now). Rejects an RTA
    time at or before t_now (the leg cannot be flown backwards in time).
    """
    _validate_distance(remaining_distance_m)
    if rta_time_s <= t_now_s:
        raise ValueError(
            "rta_time_s must be > t_now_s: %r <= %r" % (rta_time_s, t_now_s)
        )
    return remaining_distance_m / (rta_time_s - t_now_s)


def tas_from_ground_speed(ground_speed_m_s, wind_along_m_s):
    """Return the true airspeed (m/s) behind a ground speed and along wind.

    tas = ground_speed - wind_along. Rejects a headwind strong enough to
    drive the airspeed to zero or below (non-physical).
    """
    tas = ground_speed_m_s - wind_along_m_s
    if tas <= 0.0:
        raise ValueError(
            "wind_along_m_s makes true airspeed non-positive: %r"
            % (wind_along_m_s,)
        )
    return tas


def mach_from_tas(tas_m_s, altitude_m):
    """Return the Mach number of a true airspeed at altitude_m.

    mach = tas / a(altitude), with the ISA speed of sound. Rejects a
    non-positive airspeed and a negative altitude.
    """
    if tas_m_s <= 0.0:
        raise ValueError("tas_m_s must be > 0: %r" % (tas_m_s,))
    return tas_m_s / isa_speed_of_sound(altitude_m)


def _validate_envelope(mach_min, mach_max):
    """Raise ValueError when the cruise Mach envelope is non-physical."""
    if mach_min <= 0.0:
        raise ValueError("mach_min must be > 0: %r" % (mach_min,))
    if mach_max < mach_min:
        raise ValueError(
            "mach_max must be >= mach_min: %r < %r" % (mach_max, mach_min)
        )


def achievable_window(remaining_distance_m, altitude_m, wind_along_m_s,
                      mach_min, mach_max):
    """Return the achievable arrival window dict for the cruise envelope.

    gs_min = mach_min * a + wind and gs_max = mach_max * a + wind bound the
    ground speed, so the arrival window relative to t_now is eta_max =
    distance / gs_min down to eta_min = distance / gs_max. Rejects a
    headwind that makes the minimum-cruise ground speed non-positive.
    """
    _validate_distance(remaining_distance_m)
    _validate_altitude(altitude_m)
    _validate_envelope(mach_min, mach_max)
    a_sound = isa_speed_of_sound(altitude_m)
    gs_min = mach_min * a_sound + wind_along_m_s
    gs_max = mach_max * a_sound + wind_along_m_s
    if gs_min <= 0.0:
        raise ValueError(
            "headwind exceeds the minimum-cruise true airspeed, ground "
            "speed would be non-positive: %r" % (wind_along_m_s,)
        )
    if remaining_distance_m == 0.0:
        eta_min_s = 0.0
        eta_max_s = 0.0
    else:
        eta_min_s = remaining_distance_m / gs_max
        eta_max_s = remaining_distance_m / gs_min
    return {
        "gs_min": gs_min,
        "gs_max": gs_max,
        "eta_min_s": eta_min_s,
        "eta_max_s": eta_max_s,
    }


def _fetch_inputs(inputs):
    """Pull and validate the rta_speed_command input dict.

    Returns (distance, gs, wind, rta, t_now, altitude, mach_min, mach_max,
    speed_mode). Optional keys default to t_now_s = 0.0 and
    speed_mode = "mach"; missing required keys raise ValueError.
    """
    required = ("remaining_distance_m", "ground_speed_m_s", "wind_along_m_s",
                "rta_time_s", "altitude_m", "mach_min", "mach_max")
    for key in required:
        if inputs.get(key) is None:
            raise ValueError("missing required input key: %r" % (key,))
    distance = inputs["remaining_distance_m"]
    gs = inputs["ground_speed_m_s"]
    wind = inputs["wind_along_m_s"]
    rta = inputs["rta_time_s"]
    t_now = inputs.get("t_now_s", 0.0)
    altitude = inputs["altitude_m"]
    mach_min = inputs["mach_min"]
    mach_max = inputs["mach_max"]
    speed_mode = inputs.get("speed_mode", "mach")
    _validate_distance(distance)
    if gs <= 0.0:
        raise ValueError("ground_speed_m_s must be > 0: %r" % (gs,))
    if rta <= t_now:
        raise ValueError(
            "rta_time_s must be > t_now_s: %r <= %r" % (rta, t_now)
        )
    _validate_altitude(altitude)
    _validate_envelope(mach_min, mach_max)
    if speed_mode not in VALID_SPEED_MODES:
        raise ValueError(
            "speed_mode must be 'mach' or 'cas': %r" % (speed_mode,)
        )
    return (distance, gs, wind, rta, t_now, altitude, mach_min, mach_max,
            speed_mode)


def rta_speed_command(inputs):
    """Return the RTA speed command dict for an FMS time constraint.

    Input dict keys: remaining_distance_m, ground_speed_m_s, wind_along_m_s,
    rta_time_s, altitude_m, mach_min, mach_max, with optional t_now_s
    (default 0.0) and speed_mode (default "mach").

    Decision law: when |time error| <= TIME_TOL_S the current speed is held
    (RTA met within tolerance); otherwise the required ground speed and Mach
    are computed and, when the required Mach falls inside [mach_min,
    mach_max], commanded with zero remaining error; outside the envelope the
    nearest bound is commanded and the remaining time error of the best
    achievable arrival is reported with verdict "rta-unfeasible".
    """
    (distance, gs, wind, rta, t_now, altitude, mach_min, mach_max,
     speed_mode) = _fetch_inputs(inputs)
    eta_rel = eta_s(distance, gs)
    err = time_error_s(eta_rel, rta, t_now)
    window = achievable_window(distance, altitude, wind, mach_min, mach_max)
    a_sound = isa_speed_of_sound(altitude)

    if abs(err) <= TIME_TOL_S:
        # Constraint already met within tolerance: hold the current speed.
        required_gs = gs
        required_mach = None
        command_mach = mach_from_tas(tas_from_ground_speed(gs, wind),
                                     altitude)
        predicted_eta = t_now + eta_rel
        remaining_error = err
        feasible = True
        verdict = "rta-feasible"
    else:
        required_gs = required_ground_speed_m_s(distance, rta, t_now)
        required_tas = tas_from_ground_speed(required_gs, wind)
        required_mach = mach_from_tas(required_tas, altitude)
        if mach_min <= required_mach <= mach_max:
            command_mach = required_mach
            feasible = True
            predicted_eta = rta
            remaining_error = 0.0
            verdict = "rta-feasible"
        else:
            command_mach = mach_max if required_mach > mach_max else mach_min
            feasible = False
            best_gs = command_mach * a_sound + wind
            best_eta = distance / best_gs
            predicted_eta = t_now + best_eta
            remaining_error = predicted_eta - rta
            verdict = "rta-unfeasible"

    return {
        "eta_rel_s": eta_rel,
        "time_error_s": err,
        "required_gs_m_s": required_gs,
        "required_mach": required_mach,
        "command_mach": command_mach,
        "feasible": feasible,
        "window": window,
        "predicted_eta_s": predicted_eta,
        "remaining_error_s": remaining_error,
        "verdict": verdict,
        "speed_mode": speed_mode,
    }
