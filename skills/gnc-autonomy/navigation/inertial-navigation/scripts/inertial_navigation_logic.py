#!/usr/bin/env python3
"""Inertial navigation error model and mechanization quantities
(common knowledge, paraphrased; no verbatim standard text).

Units: SI - meters, seconds, radians; gyro drift is accepted in deg/h
at the API boundary and converted internally to rad/s. Constants:
standard gravity g0 = 9.80665 m/s^2, mean Earth radius
R = 6371000 m (the Schuler pendulum length), Earth rotation rate
omega_e = 7.2921159e-5 rad/s.

Textbook results (Titterton and Weston, Strapdown Inertial Navigation
Technology; Groves, Principles of GNSS, Inertial, and Multisensor
Integrated Navigation Systems; Britting, Inertial Navigation Systems
Analysis): a constant accelerometer bias b gives velocity error b*t
and short-time position error 0.5*b*t^2 by double integration; a
constant gyro drift eps about a level axis tilts the computed
vertical, couples gravity, and gives cubic position growth
(1/6)*g*eps*t^3; a Schuler-tuned level loop oscillates at the Schuler
frequency sqrt(g/R) (period 84.4 min) instead of diverging, and a
constant accelerometer bias settles to the bounded offset b*R/g.

ARINC 429 (standards-map.yaml: arinc-429, gated) is the civil data
bus over which inertial reference systems broadcast attitude,
heading, position, and velocity; it is cited reference-only and never
copied here.
"""

import math

G0 = 9.80665            # m/s^2, standard gravity
R_EARTH = 6371000.0     # m, mean Earth radius (Schuler pendulum length)
OMEGA_EARTH = 7.2921159e-5  # rad/s, Earth rotation rate
DEG_PER_HOUR_TO_RAD_S = math.pi / 180.0 / 3600.0  # 1 deg/h in rad/s


def deg_per_hour_to_rad_s(deg_per_hour):
    """Convert a gyro drift in deg/h to rad/s (1 deg/h = 4.848e-6 rad/s)."""
    if deg_per_hour < 0.0:
        raise ValueError("gyro drift must be >= 0 deg/h, got %r" % (deg_per_hour,))
    return deg_per_hour * DEG_PER_HOUR_TO_RAD_S


def schuler_frequency(g=G0, r=R_EARTH):
    """Schuler frequency in rad/s: omega_s = sqrt(g/r)."""
    if g <= 0.0 or r <= 0.0:
        raise ValueError("g and r must be positive, got %r, %r" % (g, r))
    return math.sqrt(g / r)


def schuler_period(g=G0, r=R_EARTH):
    """Schuler period in seconds: T = 2*pi*sqrt(r/g), about 5064 s
    (84.4 min) at the Earth surface. Errors of a Schuler-tuned INS
    oscillate at this period instead of diverging."""
    if g <= 0.0 or r <= 0.0:
        raise ValueError("g and r must be positive, got %r, %r" % (g, r))
    return 2.0 * math.pi * math.sqrt(r / g)


def accel_bias_velocity_error(bias, t):
    """Velocity error in m/s from a constant accelerometer bias
    (m/s^2) after time t (s): dv = b*t."""
    if t < 0.0:
        raise ValueError("time must be >= 0 s, got %r" % (t,))
    return bias * t


def accel_bias_position_error(bias, t):
    """Position error in m from a constant accelerometer bias (m/s^2)
    after time t (s): dx = 0.5*b*t^2, the double-integration
    short-time model. Valid while t is short relative to the Schuler
    period (84.4 min); the Schuler loop bounds the long-time error at
    b*R/g instead (schuler_steady_state_error)."""
    if t < 0.0:
        raise ValueError("time must be >= 0 s, got %r" % (t,))
    return 0.5 * bias * t * t


def gyro_drift_position_error(gyro_bias_deg_per_hour, t, g=G0):
    """Position error in m from a constant gyro drift (deg/h) after
    time t (s): dx = (1/6)*g*eps*t^3 with eps in rad/s. The cubic
    term dominates the unaided INS error budget: 0.001 deg/h gives
    about 370 m after one hour, 0.01 deg/h about 3.7 km."""
    if t < 0.0:
        raise ValueError("time must be >= 0 s, got %r" % (t,))
    eps = deg_per_hour_to_rad_s(gyro_bias_deg_per_hour)
    return (1.0 / 6.0) * g * eps * t * t * t


def schuler_steady_state_error(bias, g=G0, r=R_EARTH):
    """Bounded position offset in m of a Schuler-tuned level loop
    under a constant accelerometer bias (m/s^2): dx = b*r/g, about
    650 m per mg. The 84.4-min oscillation rides on this offset."""
    if g <= 0.0 or r <= 0.0:
        raise ValueError("g and r must be positive, got %r, %r" % (g, r))
    return bias * r / g


def earth_rate_component(lat_rad):
    """(north, up) Earth-rate components in rad/s at geodetic
    latitude: (omega_e*cos(lat), omega_e*sin(lat)). Gyrocompassing
    alignment senses the north component, which vanishes at the
    poles."""
    if not (-math.pi / 2.0 <= lat_rad <= math.pi / 2.0):
        raise ValueError("latitude must be in [-pi/2, pi/2] rad, got %r" % (lat_rad,))
    return (OMEGA_EARTH * math.cos(lat_rad), OMEGA_EARTH * math.sin(lat_rad))


def angle_random_walk_sigma(arw_deg_per_sqrt_hour, t_hours):
    """Accumulated gyro angle error in deg from angle random walk
    (deg/sqrt(h)) over t hours: sigma = arw*sqrt(t)."""
    if arw_deg_per_sqrt_hour < 0.0 or t_hours < 0.0:
        raise ValueError(
            "arw and time must be >= 0, got %r, %r"
            % (arw_deg_per_sqrt_hour, t_hours)
        )
    return arw_deg_per_sqrt_hour * math.sqrt(t_hours)
