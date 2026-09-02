#!/usr/bin/env python3
"""Breguet loiter endurance performance logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): the Breguet endurance equation estimates the
loiter endurance (holding time) of an aircraft from the specific fuel
consumption, the lift to drag ratio, and the initial and final
weights:

  E = (1 / sfc) * (L/D) * ln(W0 / W1)

with sfc in 1/s (kg of fuel per newton of thrust per second for a
jet, or per watt of shaft power per second for a propeller), weights
in newtons, endurance in seconds. All quantities are SI.
"""

import math


def _check_endurance_inputs(sfc_1_per_s, ld_ratio, w_initial_N, w_final_N):
    """Shared input checks for the endurance equations.

    Endurance requires fuel to be burned, so the final weight must be
    strictly below the initial weight (logarithm argument above 1).
    """
    if sfc_1_per_s <= 0:
        raise ValueError("specific fuel consumption must be > 0 1/s, got %r" % (sfc_1_per_s,))
    if ld_ratio <= 0:
        raise ValueError("lift to drag ratio must be > 0, got %r" % (ld_ratio,))
    if w_initial_N <= 0:
        raise ValueError("initial weight must be > 0 N, got %r" % (w_initial_N,))
    if w_final_N <= 0:
        raise ValueError("final weight must be > 0 N, got %r" % (w_final_N,))
    if w_final_N >= w_initial_N:
        raise ValueError(
            "final weight must be < initial weight, got w_final %r >= w_initial %r"
            % (w_final_N, w_initial_N)
        )


def jet_endurance(tsfc_1_per_s, ld_ratio, w_initial_N, w_final_N):
    """Loiter endurance in seconds for a jet aircraft.

    E = (1 / tsfc) * (L/D) * ln(W0 / W1), with the thrust specific
    fuel consumption in 1/s. Raises ValueError on non-positive SFC,
    L/D, or weights, and on w_final >= w_initial.
    """
    _check_endurance_inputs(tsfc_1_per_s, ld_ratio, w_initial_N, w_final_N)
    return (1.0 / tsfc_1_per_s) * ld_ratio * math.log(w_initial_N / w_final_N)


def prop_endurance(c_power_1_per_s, ld_ratio, w_initial_N, w_final_N):
    """Loiter endurance in seconds for a propeller aircraft.

    Same form as jet_endurance, with the specific fuel consumption
    referred to shaft power instead of thrust (kg per watt second),
    still expressed in 1/s. Raises the same ValueErrors.
    """
    _check_endurance_inputs(c_power_1_per_s, ld_ratio, w_initial_N, w_final_N)
    return (1.0 / c_power_1_per_s) * ld_ratio * math.log(w_initial_N / w_final_N)


def final_weight_after_endurance(w_initial_N, tsfc_1_per_s, ld_ratio, endurance_s):
    """Weight remaining after an endurance segment at constant L/D.

    W1 = W0 * exp(-E * tsfc / (L/D)). Raises ValueError on non-positive
    initial weight, SFC, or L/D, and on a negative endurance.
    """
    if w_initial_N <= 0:
        raise ValueError("initial weight must be > 0 N, got %r" % (w_initial_N,))
    if tsfc_1_per_s <= 0:
        raise ValueError("specific fuel consumption must be > 0 1/s, got %r" % (tsfc_1_per_s,))
    if ld_ratio <= 0:
        raise ValueError("lift to drag ratio must be > 0, got %r" % (ld_ratio,))
    if endurance_s < 0:
        raise ValueError("endurance must be >= 0 s, got %r" % (endurance_s,))
    return w_initial_N * math.exp(-endurance_s * tsfc_1_per_s / ld_ratio)


def endurance_fuel_burn(w_initial_N, w_final_N):
    """Fuel weight burned during an endurance segment: W0 - W1."""
    if w_final_N > w_initial_N:
        raise ValueError(
            "final weight must not exceed initial weight, got w_final %r > w_initial %r"
            % (w_final_N, w_initial_N)
        )
    return w_initial_N - w_final_N


def loiter_check(w_initial_N, w_final_N, tsfc_1_per_s, ld_ratio, required_s):
    """Check whether the achievable loiter endurance meets a requirement.

    Returns a dict with the achievable endurance (seconds), the
    required endurance (seconds), a meets boolean, and a verdict
    string. Raises the same ValueErrors as jet_endurance plus
    ValueError on a negative required endurance.
    """
    if required_s < 0:
        raise ValueError("required endurance must be >= 0 s, got %r" % (required_s,))
    achievable = jet_endurance(tsfc_1_per_s, ld_ratio, w_initial_N, w_final_N)
    meets = achievable >= required_s
    return {
        "achievable": achievable,
        "required": required_s,
        "meets": meets,
        "verdict": "meets" if meets else "does not meet",
    }
