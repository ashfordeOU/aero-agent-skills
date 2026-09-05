#!/usr/bin/env python3
"""Balanced field length logic (paraphrase, common flight-mechanics
methodology).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): FAR-25 requires a multi-engine transport to show
that an engine failure on the runway does not force a takeoff that
cannot be completed or an abort that cannot be stopped within the
field. The balanced field length method balances the accelerate-stop
distance (accelerate all engines to a decision speed V1, react, then
brake to a full stop) against the accelerate-go distance (accelerate
all engines to V1, continue on the remaining engines to lift-off,
rotate, and climb over the 35-ft obstacle on the engine-out climb
gradient). The balanced decision speed is the V1 where the two
distances are equal, and the balanced field length is that common
distance. The ground roll is modelled at constant acceleration with
rolling friction opposing the thrust and no aerodynamic drag or lift
relief, mirroring the takeoff-performance pack convention. All inputs
are SI: forces in newtons, speeds in m/s, distances in m, g0 =
9.80665 m/s^2. Module constants: REACTION_TIME_S = 1.0 (pilot
recognition plus brake application allowance), ROTATION_TIME_S = 1.0,
OBSTACLE_HEIGHT_M = 10.668 (35 ft, the FAR-25.113 obstacle height,
paraphrased).
"""

import math

G0 = 9.80665
REACTION_TIME_S = 1.0
ROTATION_TIME_S = 1.0
OBSTACLE_HEIGHT_M = 10.668  # 35 ft, the certification obstacle height


def oei_thrust(thrust_all_n, engine_count):
    """One-engine-inoperative thrust (N).

    T_OEI = T_all * (engine_count - 1) / engine_count. Raises
    ValueError when thrust_all_n is non-positive or engine_count < 2
    (an OEI case needs at least two engines).
    """
    if thrust_all_n <= 0:
        raise ValueError("all-engine thrust must be > 0, got %r" % (thrust_all_n,))
    if engine_count < 2:
        raise ValueError("engine_count must be >= 2, got %r" % (engine_count,))
    return thrust_all_n * (engine_count - 1) / engine_count


def ground_acceleration(thrust_n, weight_n, mu_roll, g0=G0):
    """Constant ground-roll acceleration (m/s^2).

    a = g0 * (T - mu * W) / W with rolling friction opposing the
    thrust, no aerodynamic drag or lift relief. Raises ValueError on
    non-positive weight or thrust, mu_roll outside [0, 1), or thrust
    that does not exceed the rolling friction drag (cannot
    accelerate).
    """
    if weight_n <= 0:
        raise ValueError("weight must be > 0, got %r" % (weight_n,))
    if thrust_n <= 0:
        raise ValueError("thrust must be > 0, got %r" % (thrust_n,))
    if not (0.0 <= mu_roll < 1.0):
        raise ValueError("rolling friction mu_roll must be in [0, 1), got %r" % (mu_roll,))
    if thrust_n <= mu_roll * weight_n:
        raise ValueError(
            "thrust %r must exceed rolling friction %r" % (thrust_n, mu_roll * weight_n)
        )
    return g0 * (thrust_n - mu_roll * weight_n) / weight_n


def braking_deceleration(mu_brake, g0=G0):
    """Braking deceleration magnitude (m/s^2).

    a_brake = g0 * mu_brake with the wheels braked. Raises ValueError
    when mu_brake is outside (0, 1): zero friction cannot stop the
    aircraft and unity friction is not physical.
    """
    if not (0.0 < mu_brake < 1.0):
        raise ValueError("brake friction mu_brake must be in (0, 1), got %r" % (mu_brake,))
    return g0 * mu_brake


def accelerate_distance(v_from_ms, v_to_ms, accel_m_s2):
    """Distance to accelerate between two speeds (m).

    s = (v_to^2 - v_from^2) / (2 a). Raises ValueError when v_from is
    negative, v_to does not exceed v_from (the segment must
    accelerate), or the acceleration is non-positive.
    """
    if v_from_ms < 0:
        raise ValueError("v_from must be >= 0, got %r" % (v_from_ms,))
    if v_to_ms <= v_from_ms:
        raise ValueError("v_to must exceed v_from, got %r to %r" % (v_from_ms, v_to_ms))
    if accel_m_s2 <= 0:
        raise ValueError("acceleration must be > 0, got %r" % (accel_m_s2,))
    return (v_to_ms ** 2 - v_from_ms ** 2) / (2.0 * accel_m_s2)


def stop_distance(v_ms, decel_m_s2):
    """Braking distance to a full stop from a speed (m).

    s = v^2 / (2 decel). Raises ValueError on a negative speed or a
    non-positive deceleration.
    """
    if v_ms < 0:
        raise ValueError("speed must be >= 0, got %r" % (v_ms,))
    if decel_m_s2 <= 0:
        raise ValueError("deceleration must be > 0, got %r" % (decel_m_s2,))
    return v_ms ** 2 / (2.0 * decel_m_s2)


def accelerate_stop_distance(v1_ms, thrust_all_n, weight_n, mu_roll,
                             mu_brake, reaction_time_s=REACTION_TIME_S,
                             g0=G0):
    """Accelerate-stop distance to the decision speed V1 (m).

    ASD = s_all(0 to V1) + V1 * t_reaction + stop_distance(V1): the
    all-engine ground roll to V1, the coast during the reaction time,
    and the brake segment to a full stop. Raises ValueError on a
    negative reaction time or a negative decision speed; at V1 = 0 the
    aircraft has not moved so ASD = 0.
    """
    if reaction_time_s < 0:
        raise ValueError("reaction time must be >= 0, got %r" % (reaction_time_s,))
    if v1_ms < 0:
        raise ValueError("V1 decision speed must be >= 0, got %r" % (v1_ms,))
    if v1_ms == 0:
        return 0.0
    a_all = ground_acceleration(thrust_all_n, weight_n, mu_roll, g0)
    s_roll = accelerate_distance(0.0, v1_ms, a_all)
    s_react = v1_ms * reaction_time_s
    s_stop = stop_distance(v1_ms, braking_deceleration(mu_brake, g0))
    return s_roll + s_react + s_stop


def accelerate_go_distance(v1_ms, thrust_all_n, engine_count, weight_n,
                           mu_roll, v_lof_ms, oei_climb_gradient,
                           obstacle_height_m=OBSTACLE_HEIGHT_M,
                           rotation_time_s=ROTATION_TIME_S, g0=G0):
    """Accelerate-go distance to the decision speed V1 (m).

    AGD = s_all(0 to V1) + s_oei(V1 to V_LOF) + V_LOF * t_rotation +
    s_air, with s_air = obstacle_height / gradient, the small-angle
    climb over the 35-ft obstacle on the engine-out climb gradient.
    A decision speed beyond lift-off is rejected (V1 at or past V_LOF
    is not a balanced decision), while a decision exactly at lift-off
    leaves a zero-length engine-out leg so that AGD(V_LOF) is the
    finite bracket value s_all(0 to V_LOF) + rotation plus air
    segments. Raises ValueError on a negative decision speed, a
    lift-off speed below V1 or non-positive, a non-positive gradient,
    a non-positive obstacle height, or a negative rotation time;
    engine-count and thrust checks propagate from oei_thrust and
    ground_acceleration.
    """
    if v1_ms < 0:
        raise ValueError("V1 decision speed must be >= 0, got %r" % (v1_ms,))
    if v_lof_ms <= 0:
        raise ValueError("lift-off speed must be > 0, got %r" % (v_lof_ms,))
    if v_lof_ms < v1_ms:
        raise ValueError(
            "lift-off speed %r must not be below decision speed %r"
            % (v_lof_ms, v1_ms)
        )
    if oei_climb_gradient <= 0:
        raise ValueError(
            "OEI climb gradient must be > 0, got %r" % (oei_climb_gradient,)
        )
    if obstacle_height_m <= 0:
        raise ValueError(
            "obstacle height must be > 0, got %r" % (obstacle_height_m,)
        )
    if rotation_time_s < 0:
        raise ValueError("rotation time must be >= 0, got %r" % (rotation_time_s,))
    t_oei = oei_thrust(thrust_all_n, engine_count)
    a_all = ground_acceleration(thrust_all_n, weight_n, mu_roll, g0)
    a_oei = ground_acceleration(t_oei, weight_n, mu_roll, g0)
    s_roll_all = 0.0 if v1_ms == 0 else accelerate_distance(0.0, v1_ms, a_all)
    s_roll_oei = 0.0 if v1_ms == v_lof_ms else accelerate_distance(v1_ms, v_lof_ms, a_oei)
    s_air = obstacle_height_m / oei_climb_gradient
    return s_roll_all + s_roll_oei + v_lof_ms * rotation_time_s + s_air


def balanced_v1(thrust_all_n, engine_count, weight_n, mu_roll, mu_brake,
                v_lof_ms, oei_climb_gradient,
                reaction_time_s=REACTION_TIME_S,
                obstacle_height_m=OBSTACLE_HEIGHT_M,
                rotation_time_s=ROTATION_TIME_S, g0=G0):
    """Balanced decision speed V1 where ASD equals AGD (m/s).

    Solves ASD(V1) = AGD(V1) exactly as the positive root of
    A V1^2 + B V1 + C = 0 with A = 1/(2 a_brake) + 1/(2 a_oei),
    B = reaction_time_s and C = -(V_LOF^2/(2 a_oei) + V_LOF *
    rotation_time_s + obstacle_height / gradient); the root is unique
    because A > 0 and C < 0. Raises ValueError when the root falls
    outside [0, V_LOF], meaning no balanced decision exists in the
    physical range (the caller discloses this); input checks propagate
    from the sub-calculations.
    """
    if v_lof_ms <= 0:
        raise ValueError("lift-off speed must be > 0, got %r" % (v_lof_ms,))
    if reaction_time_s < 0:
        raise ValueError("reaction time must be >= 0, got %r" % (reaction_time_s,))
    if rotation_time_s < 0:
        raise ValueError("rotation time must be >= 0, got %r" % (rotation_time_s,))
    if obstacle_height_m <= 0:
        raise ValueError(
            "obstacle height must be > 0, got %r" % (obstacle_height_m,)
        )
    t_oei = oei_thrust(thrust_all_n, engine_count)
    a_oei = ground_acceleration(t_oei, weight_n, mu_roll, g0)
    a_brake = braking_deceleration(mu_brake, g0)
    a_coeff = 1.0 / (2.0 * a_brake) + 1.0 / (2.0 * a_oei)
    b_coeff = reaction_time_s
    c_coeff = -(
        v_lof_ms ** 2 / (2.0 * a_oei)
        + v_lof_ms * rotation_time_s
        + obstacle_height_m / oei_climb_gradient
    )
    discriminant = b_coeff ** 2 - 4.0 * a_coeff * c_coeff
    v1 = (-b_coeff + math.sqrt(discriminant)) / (2.0 * a_coeff)
    if not (0.0 <= v1 <= v_lof_ms):
        raise ValueError(
            "balanced V1 %r falls outside the physical bracket [0, %r]; "
            "no balanced decision exists for this case" % (v1, v_lof_ms)
        )
    return v1


def balanced_field_length(v1_ms, thrust_all_n, engine_count, weight_n,
                          mu_roll, mu_brake, v_lof_ms, oei_climb_gradient,
                          reaction_time_s=REACTION_TIME_S,
                          obstacle_height_m=OBSTACLE_HEIGHT_M,
                          rotation_time_s=ROTATION_TIME_S, g0=G0):
    """Balanced field length (m).

    The balanced field length is the common value ASD(V1) = AGD(V1) at
    the balanced decision speed, computed here as the accelerate-stop
    distance at the V1 the caller passes (normally the value from
    balanced_v1). The ASD == AGD identity at balance is exercised by
    the contract test.
    """
    if v_lof_ms <= 0:
        raise ValueError("lift-off speed must be > 0, got %r" % (v_lof_ms,))
    if oei_climb_gradient <= 0:
        raise ValueError(
            "OEI climb gradient must be > 0, got %r" % (oei_climb_gradient,)
        )
    if obstacle_height_m <= 0:
        raise ValueError(
            "obstacle height must be > 0, got %r" % (obstacle_height_m,)
        )
    if rotation_time_s < 0:
        raise ValueError("rotation time must be >= 0, got %r" % (rotation_time_s,))
    # Balanced field length is the accelerate-stop distance at balance;
    # the remaining arguments mirror the accelerate_go_distance
    # signature so the identity can be checked with one call set.
    return accelerate_stop_distance(
        v1_ms, thrust_all_n, weight_n, mu_roll, mu_brake,
        reaction_time_s, g0,
    )
