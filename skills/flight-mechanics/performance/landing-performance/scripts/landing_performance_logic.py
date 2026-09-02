"""Landing performance math for transport category airplanes.

Deterministic, offline, stdlib-only helpers for landing performance:
reference approach speed from the stall speed, flare geometry (radius,
height, and horizontal distance) from the approach speed and load
factor, air distance over the 50 foot obstacle, landing ground roll and
total stopping distance from the touchdown speed, braking coefficient,
lift and drag ratios, and reverse thrust, plus the certified landing
field length per the FAR 25.125 / CS 25.125 landing distance check.
All units are SI: speeds in m/s, forces and weights in N, distances in
meters, density in kg/m^3, deceleration in m/s^2.

Contract exercised by scripts/test_landing_performance.py.
"""

import math

G0 = 9.80665  # standard gravity, m/s^2
STD_DENSITY = 1.225  # sea level ISA air density, kg/m^3
OBSTACLE_50FT = 15.24  # meters, the FAR 25.125 landing obstacle height


def stall_speed(wing_loading, rho=STD_DENSITY, cl_max=2.0):
    """Return the stall speed in m/s from the wing loading W/S in N/m^2.

    V_s = sqrt(2 * (W/S) / (rho * CL_max)). The landing reference speed
    is built on this stall speed with the 1.3 factor.

    Raises ValueError for a non-positive wing loading, density, or
    maximum lift coefficient.
    """
    if wing_loading <= 0:
        raise ValueError("wing loading must be > 0, got %r" % (wing_loading,))
    if rho <= 0:
        raise ValueError("density must be > 0, got %r" % (rho,))
    if cl_max <= 0:
        raise ValueError("CL_max must be > 0, got %r" % (cl_max,))
    return math.sqrt(2.0 * wing_loading / (rho * cl_max))


def approach_speed(stall_speed_value, factor=1.3):
    """Return the reference approach speed in m/s: factor times the stall
    speed.

    FAR 25.125 and CS 25.125 build the landing distance from a reference
    landing speed of 1.3 times the stalling speed in the landing
    configuration; 1.23 is the minimum for the stall-speed definition
    used in the demonstrated distance. The factor must be at least 1.0.

    Raises ValueError for a non-positive stall speed or a factor below 1.0.
    """
    if stall_speed_value <= 0:
        raise ValueError("stall speed must be > 0, got %r" % (stall_speed_value,))
    if factor < 1.0:
        raise ValueError("approach factor must be >= 1.0, got %r" % (factor,))
    return factor * stall_speed_value


def touchdown_speed(approach_speed_value, factor=0.95):
    """Return the touchdown speed in m/s: factor times the approach speed.

    The airplane flares and touches down below the approach speed; 0.95
    of the approach speed is a common transport convention, with the
    touchdown speed still well above the stall speed.

    Raises ValueError for a non-positive approach speed or a factor
    outside the open interval (0, 1].
    """
    if approach_speed_value <= 0:
        raise ValueError("approach speed must be > 0, got %r" % (approach_speed_value,))
    if factor <= 0 or factor > 1.0:
        raise ValueError("touchdown factor must be in (0, 1], got %r" % (factor,))
    return factor * approach_speed_value


def flare_radius(approach_speed_value, load_factor=1.2, g=G0):
    """Return the flare radius in meters: R = V^2 / (g * (n - 1)).

    The flare is modeled as a circular arc flown at load factor n (about
    1.2 in a normal transport landing) while the speed decays from the
    approach speed toward the touchdown speed.

    Raises ValueError for a non-positive approach speed, a load factor
    at or below 1.0, or a non-positive gravity.
    """
    if approach_speed_value <= 0:
        raise ValueError("approach speed must be > 0, got %r" % (approach_speed_value,))
    if load_factor <= 1.0:
        raise ValueError("load factor must be > 1.0, got %r" % (load_factor,))
    if g <= 0:
        raise ValueError("gravity must be > 0, got %r" % (g,))
    return approach_speed_value * approach_speed_value / (g * (load_factor - 1.0))


def _gamma_radians(approach_angle_deg):
    if approach_angle_deg <= 0:
        raise ValueError("approach angle must be > 0, got %r" % (approach_angle_deg,))
    if approach_angle_deg >= 90.0:
        raise ValueError("approach angle must be < 90, got %r" % (approach_angle_deg,))
    return math.radians(approach_angle_deg)


def flare_height(approach_speed_value, approach_angle_deg, load_factor=1.2, g=G0):
    """Return the flare height in meters: h_f = R * (1 - cos(gamma)).

    The height lost while rotating the flight path from the approach
    angle gamma down to the flare. gamma is the approach angle in
    degrees (3 degrees is a standard transport glideslope).

    Raises ValueError for invalid approach speed, angle, load factor,
    or gravity (see flare_radius and _gamma_radians).
    """
    gamma = _gamma_radians(approach_angle_deg)
    radius = flare_radius(approach_speed_value, load_factor, g)
    return radius * (1.0 - math.cos(gamma))


def flare_distance(approach_speed_value, approach_angle_deg, load_factor=1.2, g=G0):
    """Return the horizontal flare distance in meters: s_f = R * sin(gamma).

    The horizontal travel during the flare arc, from the point where the
    flare starts to the touchdown point.

    Raises ValueError for invalid approach speed, angle, load factor,
    or gravity.
    """
    gamma = _gamma_radians(approach_angle_deg)
    radius = flare_radius(approach_speed_value, load_factor, g)
    return radius * math.sin(gamma)


def air_distance(
    approach_speed_value,
    approach_angle_deg,
    obstacle_height=OBSTACLE_50FT,
    load_factor=1.2,
    g=G0,
):
    """Return the air distance in meters over the landing obstacle.

    The total distance from the obstacle (50 feet, 15.24 m, per FAR
    25.125) to touchdown: a straight segment at the approach angle down
    to the flare height plus the horizontal flare distance:
    s_air = (h_obs - h_f) / tan(gamma) + s_f.

    Raises ValueError for invalid inputs, or when the obstacle height
    does not exceed the flare height (the obstacle must be crossed
    before the flare arc completes).
    """
    gamma = _gamma_radians(approach_angle_deg)
    h_flare = flare_height(approach_speed_value, approach_angle_deg, load_factor, g)
    if obstacle_height <= h_flare:
        raise ValueError(
            "obstacle height %r must exceed flare height %r"
            % (obstacle_height, h_flare)
        )
    s_flare = flare_distance(approach_speed_value, approach_angle_deg, load_factor, g)
    straight = (obstacle_height - h_flare) / math.tan(gamma)
    return straight + s_flare


def ground_roll_distance(touchdown_speed_value, deceleration):
    """Return the landing ground roll in meters: s_g = V^2 / (2 * a).

    Constant deceleration model from the touchdown speed to a full stop,
    with deceleration in m/s^2 (the mean braking deceleration, which may
    come from average_deceleration or be measured directly).

    Raises ValueError for a negative touchdown speed or a non-positive
    deceleration.
    """
    if touchdown_speed_value < 0:
        raise ValueError(
            "touchdown speed must be >= 0, got %r" % (touchdown_speed_value,)
        )
    if deceleration <= 0:
        raise ValueError("deceleration must be > 0, got %r" % (deceleration,))
    return touchdown_speed_value * touchdown_speed_value / (2.0 * deceleration)


def average_deceleration(
    mu_braking,
    lift_to_weight=0.0,
    drag_to_weight=0.0,
    reverse_thrust_to_weight=0.0,
):
    """Return the mean landing deceleration ratio in g's.

    Force balance on the landing ground roll, all ratios per unit
    weight: a/g = mu * (1 - L/W) + D/W + T_rev/W, with mu the braking
    coefficient, L/W the lift ratio (unloaded wheels reduce braking
    friction), D/W the drag ratio, and T_rev/W the reverse thrust ratio.
    A firm touchdown with weight on the wheels gives L/W near zero.

    Raises ValueError for a negative braking coefficient or any negative
    force ratio.
    """
    if mu_braking < 0:
        raise ValueError("braking coefficient must be >= 0, got %r" % (mu_braking,))
    for label, value in (
        ("lift to weight", lift_to_weight),
        ("drag to weight", drag_to_weight),
        ("reverse thrust to weight", reverse_thrust_to_weight),
    ):
        if value < 0:
            raise ValueError("%s must be >= 0, got %r" % (label, value))
    return mu_braking * (1.0 - lift_to_weight) + drag_to_weight + reverse_thrust_to_weight


def ground_roll_from_forces(
    touchdown_speed_value,
    mu_braking,
    lift_to_weight=0.0,
    drag_to_weight=0.0,
    reverse_thrust_to_weight=0.0,
    g=G0,
):
    """Return the landing ground roll in meters from the force ratios.

    Combines average_deceleration and ground_roll_distance: the mean
    deceleration in g's is converted to m/s^2 and applied over the
    touchdown speed.

    Raises ValueError for invalid force ratios, touchdown speed,
    deceleration, or gravity.
    """
    ratio = average_deceleration(
        mu_braking, lift_to_weight, drag_to_weight, reverse_thrust_to_weight
    )
    if ratio <= 0:
        raise ValueError(
            "net deceleration ratio must be > 0, got %r" % (ratio,)
        )
    if g <= 0:
        raise ValueError("gravity must be > 0, got %r" % (g,))
    return ground_roll_distance(touchdown_speed_value, ratio * g)


def landing_distance(air_distance_m, ground_roll_m):
    """Return the total landing distance in meters: air distance over the
    obstacle plus the ground roll.

    Raises ValueError for a negative air distance or ground roll.
    """
    if air_distance_m < 0:
        raise ValueError("air distance must be >= 0, got %r" % (air_distance_m,))
    if ground_roll_m < 0:
        raise ValueError("ground roll must be >= 0, got %r" % (ground_roll_m,))
    return air_distance_m + ground_roll_m


def certified_landing_distance(actual_distance, factor=1.67):
    """Return the certified landing field length: factor times the actual
    landing distance.

    FAR 25.125 and CS 25.125 require the certified landing distance,
    measured from 50 feet above the runway to a full stop, to be
    multiplied by a 1.67 safety factor for the published field length
    (the same 1.67 factor applies to the dry-runway demonstration).

    Raises ValueError for a negative actual distance or a factor below 1.0.
    """
    if actual_distance < 0:
        raise ValueError("actual distance must be >= 0, got %r" % (actual_distance,))
    if factor < 1.0:
        raise ValueError("certification factor must be >= 1.0, got %r" % (factor,))
    return factor * actual_distance


def required_braking_coefficient(
    touchdown_speed_value,
    ground_roll_m,
    lift_to_weight=0.0,
    drag_to_weight=0.0,
    reverse_thrust_to_weight=0.0,
    g=G0,
):
    """Return the braking coefficient needed to stop in the given ground
    roll.

    Inverts the force balance: the required deceleration ratio is
    V^2 / (2 * g * s), and the braking coefficient follows as
    mu = (ratio - D/W - T_rev/W) / (1 - L/W). This sizes the runway
    friction demand (dry, wet, or contaminated) for a target stop
    distance.

    Raises ValueError for invalid inputs, or when the drag and reverse
    thrust alone already stop the airplane (the required coefficient
    would be negative).
    """
    if touchdown_speed_value < 0:
        raise ValueError(
            "touchdown speed must be >= 0, got %r" % (touchdown_speed_value,)
        )
    if ground_roll_m <= 0:
        raise ValueError("ground roll must be > 0, got %r" % (ground_roll_m,))
    if g <= 0:
        raise ValueError("gravity must be > 0, got %r" % (g,))
    if lift_to_weight >= 1.0:
        raise ValueError("lift to weight must be < 1.0, got %r" % (lift_to_weight,))
    for label, value in (
        ("drag to weight", drag_to_weight),
        ("reverse thrust to weight", reverse_thrust_to_weight),
    ):
        if value < 0:
            raise ValueError("%s must be >= 0, got %r" % (label, value))
    ratio = touchdown_speed_value * touchdown_speed_value / (2.0 * g * ground_roll_m)
    mu = (ratio - drag_to_weight - reverse_thrust_to_weight) / (1.0 - lift_to_weight)
    if mu < 0:
        raise ValueError(
            "drag and reverse thrust alone stop the airplane, required mu = %r" % (mu,)
        )
    return mu


def stop_time(touchdown_speed_value, deceleration):
    """Return the ground roll time in seconds: t = V / a.

    Constant deceleration model. Raises ValueError for a negative
    touchdown speed or a non-positive deceleration.
    """
    if touchdown_speed_value < 0:
        raise ValueError(
            "touchdown speed must be >= 0, got %r" % (touchdown_speed_value,)
        )
    if deceleration <= 0:
        raise ValueError("deceleration must be > 0, got %r" % (deceleration,))
    return touchdown_speed_value / deceleration
