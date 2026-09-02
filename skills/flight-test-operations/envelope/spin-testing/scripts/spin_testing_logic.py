#!/usr/bin/env python3
"""Spin flight testing logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml: far-25 and cs-25 both
reference-only): the spin flight test probes the airplane beyond the
stall with pro-spin controls applied. The entry establishes
autorotation from a stalled condition; the incipient phase covers the
first turns while the rotation rate builds, and the developed spin is
the steady autorotation with a stabilized yaw rate. Recovery is the
standard control procedure (opposite rudder against the rotation, stick
forward to break the stall, ailerons neutral) held until rotation
stops, and a recovery check judges the turn count and altitude loss
against the program limits. The recovery parachute is the last-resort
device required when recovery is not demonstrated, when developed spin
testing is planned, or on a first flight. Spin resistance is judged
with pro-spin controls held at the stall: the airplane must not enter a
developed spin or must recover within the limits. Regulatory text is
never reproduced here; FAR 25.201 and CS-25.201 are referenced by
number only.
"""

import itertools
import math

INCIPIENT_START_TURNS = 1.0
DEVELOPED_START_TURNS = 2.0
MIN_DEVELOPED_YAW_RATE_DEG_S = 20.0

DEFAULT_CG_MIN_PCT = 15.0
DEFAULT_CG_MAX_PCT = 35.0

DEFAULT_RECOVERY_TURNS_LIMIT = 2.0
DEFAULT_RECOVERY_ALTITUDE_LIMIT_M = 3000.0

DEFAULT_RESISTANCE_TURNS_LIMIT = 1.0
DEFAULT_RESISTANCE_ALTITUDE_LIMIT_M = 1500.0


def _check_finite(name, value):
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("%s must be a finite number: %r" % (name, value))
    return float(value)


def config_combination(config, cg_pct_mac, weight_kg, altitude_m):
    """One spin test point from config, CG, weight, and altitude.

    config: non-empty configuration name (str); cg_pct_mac: CG position
    in percent mean aerodynamic chord (positive); weight_kg: gross
    weight (positive); altitude_m: pressure altitude (non-negative).
    Returns a point dict. Invalid inputs raise ValueError.
    """
    if not isinstance(config, str) or not config.strip():
        raise ValueError("config must be a non-empty string")
    cg = _check_finite("cg_pct_mac", cg_pct_mac)
    weight = _check_finite("weight_kg", weight_kg)
    altitude = _check_finite("altitude_m", altitude_m)
    if cg <= 0.0 or weight <= 0.0 or altitude < 0.0:
        raise ValueError(
            "cg and weight must be positive and altitude non-negative: "
            "(%r, %r, %r)" % (cg, weight, altitude)
        )
    return {
        "config": config.strip(),
        "cg_pct_mac": cg,
        "weight_kg": weight,
        "altitude_m": altitude,
    }


def spin_test_point_matrix(configs, cg_conditions, weights_kg, altitudes_m,
                           cg_min_pct=DEFAULT_CG_MIN_PCT,
                           cg_max_pct=DEFAULT_CG_MAX_PCT):
    """Build the spin test point matrix from the configuration grid.

    configs, cg_conditions, weights_kg, altitudes_m: non-empty lists of
    configurations, CG positions (% MAC), gross weights (kg), and
    pressure altitudes (m). Every combination is one test point. Each
    point carries a stable id and the cg_envelope_ok flag, which is
    False when the CG falls outside [cg_min_pct, cg_max_pct]; points
    outside the approved CG envelope need envelope approval or
    parachute coverage before they fly. Empty input lists raise
    ValueError.
    """
    grids = (
        ("configs", configs),
        ("cg_conditions", cg_conditions),
        ("weights_kg", weights_kg),
        ("altitudes_m", altitudes_m),
    )
    for name, grid in grids:
        if not grid:
            raise ValueError("%s must not be empty" % name)
    if cg_min_pct > cg_max_pct:
        raise ValueError(
            "cg_min_pct %r above cg_max_pct %r" % (cg_min_pct, cg_max_pct)
        )
    points = []
    for i, (config, cg, weight, altitude) in enumerate(
        itertools.product(configs, cg_conditions, weights_kg, altitudes_m)
    ):
        point = config_combination(config, cg, weight, altitude)
        point["id"] = "sp-%02d" % (i + 1)
        point["cg_envelope_ok"] = cg_min_pct <= point["cg_pct_mac"] <= cg_max_pct
        points.append(point)
    return points


def spin_phase_classify(turns, yaw_rate_deg_s):
    """Classify the spin phase: 'entry', 'incipient', or 'developed'.

    Entry: less than the first full turn while autorotation builds.
    Incipient: from the first full turn until the rotation stabilizes
    (commonly the first 1 to 2 turns). Developed: steady autorotation,
    from about 2 turns with a sustained yaw rate at or above
    MIN_DEVELOPED_YAW_RATE_DEG_S. Negative inputs raise ValueError.
    """
    turns = _check_finite("turns", turns)
    yaw_rate = _check_finite("yaw_rate_deg_s", yaw_rate_deg_s)
    if turns < 0.0 or yaw_rate < 0.0:
        raise ValueError("turns and yaw rate must be non-negative")
    if turns >= DEVELOPED_START_TURNS and yaw_rate >= MIN_DEVELOPED_YAW_RATE_DEG_S:
        return "developed"
    if turns >= INCIPIENT_START_TURNS:
        return "incipient"
    return "entry"


def spin_recovery_check(turns_to_recover, altitude_loss_m,
                        turns_limit=DEFAULT_RECOVERY_TURNS_LIMIT,
                        altitude_loss_limit_m=DEFAULT_RECOVERY_ALTITUDE_LIMIT_M):
    """Judge the spin recovery against the program limits.

    Recovery is measured from the moment the recovery controls are
    applied: the additional turns until rotation stops and the altitude
    lost during recovery. The program limits (commonly 2 turns and
    3000 m in a transport program, paraphrased methodology, verify per
    program) are inputs. Returns a dict with turns_ok, altitude_ok,
    recoverable, and verdict ('recoverable' or 'unrecoverable'). A spin
    that exceeds either limit is unrecoverable by the criterion.
    Negative inputs raise ValueError.
    """
    turns = _check_finite("turns_to_recover", turns_to_recover)
    altitude = _check_finite("altitude_loss_m", altitude_loss_m)
    turns_lim = _check_finite("turns_limit", turns_limit)
    alt_lim = _check_finite("altitude_loss_limit_m", altitude_loss_limit_m)
    if turns < 0.0 or altitude < 0.0:
        raise ValueError("turns to recover and altitude loss must be non-negative")
    if turns_lim <= 0.0 or alt_lim <= 0.0:
        raise ValueError("limits must be positive")
    turns_ok = turns <= turns_lim
    altitude_ok = altitude <= alt_lim
    recoverable = turns_ok and altitude_ok
    return {
        "turns_to_recover": turns,
        "altitude_loss_m": altitude,
        "turns_ok": turns_ok,
        "altitude_ok": altitude_ok,
        "recoverable": recoverable,
        "verdict": "recoverable" if recoverable else "unrecoverable",
    }


def recovery_parachute_requirement(prior_recovery_demonstrated,
                                   developed_spin_planned,
                                   unrecoverable_predicted=False,
                                   first_flight=False):
    """Decide whether the recovery parachute is required.

    The recovery parachute (spin chute) is the last-resort recovery
    device. It is required when any reason holds: no prior recovery
    demonstration for the configuration, developed spin testing
    planned, a recovery check predicting an unrecoverable spin, or the
    first flight of a new configuration. Returns a dict with the
    required flag and the reason list (deterministic order).
    """
    reasons = []
    if first_flight:
        reasons.append("first flight of the configuration")
    if not prior_recovery_demonstrated:
        reasons.append("no prior recovery demonstration for the configuration")
    if developed_spin_planned:
        reasons.append("developed spin testing planned")
    if unrecoverable_predicted:
        reasons.append("recovery check predicts an unrecoverable spin")
    return {"required": bool(reasons), "reasons": reasons}


def spin_resistance_check(pro_spin_turns, pro_spin_altitude_loss_m,
                          max_allowed_turns=DEFAULT_RESISTANCE_TURNS_LIMIT,
                          max_allowed_altitude_loss_m=DEFAULT_RESISTANCE_ALTITUDE_LIMIT_M):
    """Judge spin resistance with pro-spin controls held at the stall.

    FAR 25.201 / CS-25.201 context (paraphrased, reference-only): the
    stall demonstration holds pro-spin controls at the stall and the
    airplane must be resistant to spinning; autorotation that stays
    within the allowed turn count and altitude loss and stops promptly
    is resistant, and a developed spin beyond the limits is not.
    Returns a dict with entered_spin, the observed turns and altitude
    loss, resistant, and verdict ('resistant' or 'not-resistant').
    Negative inputs raise ValueError.
    """
    turns = _check_finite("pro_spin_turns", pro_spin_turns)
    altitude = _check_finite("pro_spin_altitude_loss_m", pro_spin_altitude_loss_m)
    turns_lim = _check_finite("max_allowed_turns", max_allowed_turns)
    alt_lim = _check_finite("max_allowed_altitude_loss_m", max_allowed_altitude_loss_m)
    if turns < 0.0 or altitude < 0.0:
        raise ValueError("pro-spin turns and altitude loss must be non-negative")
    if turns_lim <= 0.0 or alt_lim <= 0.0:
        raise ValueError("limits must be positive")
    entered_spin = turns > 0.0
    within_turns = turns <= turns_lim
    within_altitude = altitude <= alt_lim
    resistant = within_turns and within_altitude
    return {
        "entered_spin": entered_spin,
        "pro_spin_turns": turns,
        "pro_spin_altitude_loss_m": altitude,
        "resistant": resistant,
        "verdict": "resistant" if resistant else "not-resistant",
    }
