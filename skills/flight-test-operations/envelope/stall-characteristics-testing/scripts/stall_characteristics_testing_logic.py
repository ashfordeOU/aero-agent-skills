#!/usr/bin/env python3
"""Stall characteristics testing logic for flight test (paraphrase,
common knowledge).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: public
domain / free-download regulation context): the stall characteristics
flight test exercises the stall test matrix (configurations, power
settings, c.g. conditions), the entry techniques (gradual deceleration
at about one knot per second, power-on, turning, accelerated), the
stall warning onset margin (FAR 25.207 / CS-25.207 context: warning
must begin at a speed at least five percent above the stalling speed,
or three knots, whichever is greater), and the recovery characteristics
(FAR 25.203 / CS-25.203 context: no excessive pitch-up, no
uncontrollable rolling or yawing, no tendency to spin or depart, prompt
recovery with limited altitude loss). In a coordinated level turn the
load factor is n = 1/cos(bank) and the wing stalls at V = Vs * sqrt(n).
All speeds are m/s EAS unless noted otherwise.
"""

import math

KTS_TO_MPS = 0.514444  # one knot in m/s
# Typical stall entry deceleration rate, about one knot per second.
DEFAULT_ENTRY_DECEL_MPS2 = KTS_TO_MPS
# Reference warning margin (FAR 25.207 / CS-25.207 context): five
# percent above the stalling speed, or three knots, whichever greater.
DEFAULT_WARNING_MARGIN = 0.05


def accelerated_stall_speed(vs1g, load_factor):
    """Stall speed at an elevated entry load factor, m/s EAS.

    V = vs1g * sqrt(load_factor): the wing reaches CL_max at a higher
    dynamic pressure when the entry is pulled to n > 1, so the stall
    occurs above the 1g stall speed. load_factor is dimensionless,
    vs1g in m/s EAS. Raises ValueError when vs1g <= 0 or
    load_factor < 1 (a load factor below 1g is not an accelerated
    stall entry).
    """
    if vs1g <= 0:
        raise ValueError("1g stall speed must be > 0, got %r" % (vs1g,))
    if load_factor < 1:
        raise ValueError(
            "entry load factor must be >= 1, got %r" % (load_factor,)
        )
    return vs1g * math.sqrt(load_factor)


def level_turn_load_factor(bank_deg):
    """Load factor n = 1/cos(bank) of a coordinated level turn.

    bank_deg in degrees, |bank| < 90. Raises ValueError when the bank
    angle is outside (-90, 90) degrees, where the coordinated turn
    load factor is undefined.
    """
    if abs(bank_deg) >= 90.0:
        raise ValueError(
            "bank angle must be strictly between -90 and 90 degrees, got %r"
            % (bank_deg,)
        )
    return 1.0 / math.cos(math.radians(bank_deg))


def stall_warning_speed(vs1g, margin=DEFAULT_WARNING_MARGIN):
    """Speed at which stall warning must already be active, m/s EAS.

    V = vs1g * (1 + margin) with margin dimensionless (0.05 is the
    five percent reference). Raises ValueError when vs1g <= 0 or
    margin < 0.
    """
    if vs1g <= 0:
        raise ValueError("1g stall speed must be > 0, got %r" % (vs1g,))
    if margin < 0:
        raise ValueError("warning margin must be >= 0, got %r" % (margin,))
    return vs1g * (1.0 + margin)


def stall_warning_on_time(warning_speed, vs1g, margin=DEFAULT_WARNING_MARGIN):
    """Verdict dict on the stall warning onset margin.

    Checks that the observed warning onset speed is at least
    vs1g * (1 + margin), the required margin. Returns
    {'warning_in_time': bool, 'achieved_margin': float,
     'ok': bool} where achieved_margin is the observed fraction above
    the 1g stall speed. Raises ValueError when warning_speed <= 0,
    vs1g <= 0, or margin < 0.
    """
    if warning_speed <= 0:
        raise ValueError(
            "observed warning speed must be > 0, got %r" % (warning_speed,)
        )
    if vs1g <= 0:
        raise ValueError("1g stall speed must be > 0, got %r" % (vs1g,))
    if margin < 0:
        raise ValueError("warning margin must be >= 0, got %r" % (margin,))
    required = vs1g * (1.0 + margin)
    achieved = warning_speed / vs1g - 1.0
    ok = warning_speed >= required
    return {"warning_in_time": ok, "achieved_margin": achieved, "ok": ok}


def entry_deceleration_time(entry_speed, stall_speed,
                            decel_rate=DEFAULT_ENTRY_DECEL_MPS2):
    """Time to decelerate from entry speed to the stall, seconds.

    t = (entry_speed - stall_speed) / decel_rate with speeds in m/s
    EAS and decel_rate in m/s^2 (about 0.5144 m/s^2 for the one knot
    per second entry). Raises ValueError when entry_speed <=
    stall_speed (no deceleration segment), stall_speed <= 0, or
    decel_rate <= 0.
    """
    if stall_speed <= 0:
        raise ValueError("stall speed must be > 0, got %r" % (stall_speed,))
    if entry_speed <= stall_speed:
        raise ValueError(
            "entry speed must be above the stall speed, got %r vs %r"
            % (entry_speed, stall_speed)
        )
    if decel_rate <= 0:
        raise ValueError(
            "deceleration rate must be > 0, got %r" % (decel_rate,)
        )
    return (entry_speed - stall_speed) / decel_rate


def stall_recovery_verdict(altitude_loss_m, altitude_loss_limit_m,
                           pitch_up_deg, pitch_up_limit_deg,
                           roll_off_deg, roll_off_limit_deg):
    """Recovery characteristics verdict, dict of bools.

    Checks the observed recovery against the certification-style
    limits: altitude loss (m) within the allowed loss, no excessive
    pitch-up (deg), and no excessive roll-off (deg). 'ok' is True only
    when every check passes. Raises ValueError when altitude_loss_m < 0,
    roll_off_deg < 0, or any limit is <= 0.
    """
    if altitude_loss_m < 0:
        raise ValueError(
            "altitude loss must be >= 0, got %r" % (altitude_loss_m,)
        )
    if altitude_loss_limit_m <= 0:
        raise ValueError(
            "altitude loss limit must be > 0, got %r" % (altitude_loss_limit_m,)
        )
    if pitch_up_limit_deg <= 0:
        raise ValueError(
            "pitch-up limit must be > 0, got %r" % (pitch_up_limit_deg,)
        )
    if roll_off_deg < 0:
        raise ValueError(
            "roll-off must be >= 0, got %r" % (roll_off_deg,)
        )
    if roll_off_limit_deg <= 0:
        raise ValueError(
            "roll-off limit must be > 0, got %r" % (roll_off_limit_deg,)
        )
    altitude_ok = altitude_loss_m <= altitude_loss_limit_m
    pitch_ok = pitch_up_deg <= pitch_up_limit_deg
    roll_ok = roll_off_deg <= roll_off_limit_deg
    return {
        "altitude_loss_ok": altitude_ok,
        "pitch_up_ok": pitch_ok,
        "roll_off_ok": roll_ok,
        "ok": altitude_ok and pitch_ok and roll_ok,
    }
