#!/usr/bin/env python3
"""Energy height and specific excess power logic (common flight mechanics).

Paraphrase of common flight-mechanics methodology (stands on the
FAR-25 / CS-25 transport performance context, reference-only per
standards-map.yaml): the excess power is (T - D) * V; the specific
excess power Ps = (T - D) * V / W is the energy rate in m/s and
equals the rate of climb in steady unaccelerated flight; the
kinetic height h_k = V^2 / (2 * g0) expresses the airspeed as an
equivalent altitude; the energy height h_e = h + V^2 / (2 * g0) is
the total mechanical energy per unit weight; the zoom climb gain
is the extra altitude from converting all kinetic energy; the
speed bleed for an altitude gain is V2 = sqrt(V1^2 - 2 * g0 *
delta_h); the altitude gain from a speed bleed is delta_h =
(V1^2 - V2^2) / (2 * g0). Units: forces in N, speeds in m/s,
heights and altitudes in m, powers in watts, g0 = 9.80665 m/s^2.
"""

G0 = 9.80665  # standard gravity, m/s^2


def excess_power(thrust_n, drag_n, v_ms):
    """Excess power in watts: (T - D) * V.

    Raises ValueError on negative thrust, negative drag, or a
    non-positive speed.
    """
    if thrust_n < 0:
        raise ValueError("thrust must be >= 0 N, got %r" % (thrust_n,))
    if drag_n < 0:
        raise ValueError("drag must be >= 0 N, got %r" % (drag_n,))
    if v_ms <= 0:
        raise ValueError("speed must be > 0 m/s, got %r" % (v_ms,))
    return (thrust_n - drag_n) * v_ms


def specific_excess_power(thrust_n, drag_n, v_ms, weight_n):
    """Specific excess power in m/s: Ps = (T - D) * V / W.

    The energy rate of the aircraft, equal to the rate of climb in
    steady unaccelerated flight. Raises ValueError on a non-positive
    weight or on any excess_power input violation.
    """
    if weight_n <= 0:
        raise ValueError("weight must be > 0 N, got %r" % (weight_n,))
    p = excess_power(thrust_n, drag_n, v_ms)
    return p / weight_n


def kinetic_height(v_ms):
    """Kinetic height in m: the airspeed as an equivalent altitude V^2 / (2g)."""
    if v_ms < 0:
        raise ValueError("speed must be >= 0 m/s, got %r" % (v_ms,))
    return v_ms * v_ms / (2.0 * G0)


def energy_height(altitude_m, v_ms):
    """Energy height in m: h_e = h + V^2 / (2g), total energy per unit weight.

    Raises ValueError on a negative altitude or a negative speed.
    """
    if altitude_m < 0:
        raise ValueError("altitude must be >= 0 m, got %r" % (altitude_m,))
    return altitude_m + kinetic_height(v_ms)


def speed_from_energy_height(energy_height_m, altitude_m):
    """Speed in m/s for a target energy height: V = sqrt(2g(h_e - h)).

    Raises ValueError when the energy height is below the geometric
    altitude (negative kinetic energy) or on a negative altitude.
    """
    if altitude_m < 0:
        raise ValueError("altitude must be >= 0 m, got %r" % (altitude_m,))
    if energy_height_m < altitude_m:
        raise ValueError(
            "energy height must be >= altitude, got %r < %r"
            % (energy_height_m, altitude_m)
        )
    return (2.0 * G0 * (energy_height_m - altitude_m)) ** 0.5


def zoom_climb_gain(v_ms):
    """Zoom climb gain in m: extra altitude from converting all kinetic energy.

    Equals the kinetic height V^2 / (2g). Raises ValueError on a
    negative speed.
    """
    return kinetic_height(v_ms)


def speed_after_climb_bleed(v_ms, delta_h_m):
    """Speed in m/s left after climbing delta_h: V2 = sqrt(V1^2 - 2g*delta_h).

    The climb-cruise energy trade. Raises ValueError on a negative
    altitude gain or when the kinetic energy is insufficient for
    the climb (the radicand goes negative).
    """
    if delta_h_m < 0:
        raise ValueError("altitude gain must be >= 0 m, got %r" % (delta_h_m,))
    if v_ms < 0:
        raise ValueError("speed must be >= 0 m/s, got %r" % (v_ms,))
    radicand = v_ms * v_ms - 2.0 * G0 * delta_h_m
    if radicand < 0:
        raise ValueError(
            "insufficient kinetic energy for a %r m climb from %r m/s"
            % (delta_h_m, v_ms)
        )
    return radicand ** 0.5


def altitude_from_speed_bleed(v1_ms, v2_ms):
    """Altitude gain in m from slowing V1 to V2: delta_h = (V1^2 - V2^2) / (2g).

    Raises ValueError when the final speed exceeds the initial speed
    (that would be an energy input, not a bleed) or on a negative speed.
    """
    if v1_ms < 0 or v2_ms < 0:
        raise ValueError("speeds must be >= 0 m/s, got %r, %r" % (v1_ms, v2_ms))
    if v2_ms > v1_ms:
        raise ValueError(
            "final speed must not exceed initial speed, got %r > %r"
            % (v2_ms, v1_ms)
        )
    return (v1_ms * v1_ms - v2_ms * v2_ms) / (2.0 * G0)
