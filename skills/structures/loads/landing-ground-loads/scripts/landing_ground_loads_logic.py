"""Landing ground loads: static and limit ground reaction sets for an aircraft.

Pure stdlib reaction model for the certification landing and ground
handling conditions (FAR 25.471 to 25.511 style): static nose and main
gear reactions over the wheelbase, level landing reactions at a limit
vertical inertia load factor, the braked roll with all brakes on the
main gear, the tail-down condition with the nose gear unloaded, and the
one-wheel asymmetric level landing reaction. The limit load factor is an
input chosen from the certification basis, never asserted as a
regulation quote.

Units are SI throughout: N, m, kg (mass converted through weight_force).
"""

G0 = 9.80665
"""Standard gravity in m/s^2 (SI definition value)."""

N_LEVEL_DEFAULT = 2.5
"""Typical limit vertical inertia load factor used when a caller does
not supply one. The certification value remains an input."""


def _check_weight(weight):
    if weight <= 0:
        raise ValueError("weight must be positive, got %r" % (weight,))


def weight_force(mass_kg):
    """Convert a mass in kg to a weight force in N at standard gravity."""
    if mass_kg <= 0:
        raise ValueError("mass_kg must be positive, got %r" % (mass_kg,))
    return mass_kg * G0


def _check_geometry(dist_nose_to_cg, dist_cg_to_main):
    if dist_nose_to_cg <= 0 or dist_cg_to_main <= 0:
        raise ValueError(
            "dist_nose_to_cg and dist_cg_to_main must be positive, got "
            "%r and %r" % (dist_nose_to_cg, dist_cg_to_main))


def static_reactions(weight, dist_nose_to_cg, dist_cg_to_main):
    """Static nose and main gear reactions from the weight and CG position.

    With a = dist_nose_to_cg and b = dist_cg_to_main the wheelbase is
    a + b and R_nose = W * b / (a + b), R_main = W * a / (a + b).
    Returns {nose_N, main_N}.
    """
    _check_weight(weight)
    _check_geometry(dist_nose_to_cg, dist_cg_to_main)
    wheelbase = dist_nose_to_cg + dist_cg_to_main
    return {
        "nose_N": weight * dist_cg_to_main / wheelbase,
        "main_N": weight * dist_nose_to_cg / wheelbase,
    }


def _check_load_factor(load_factor):
    if load_factor <= 0:
        raise ValueError("load_factor must be positive, got %r" % (load_factor,))


def level_landing_reactions(weight, dist_nose_to_cg, dist_cg_to_main,
                            load_factor=N_LEVEL_DEFAULT):
    """Level landing reactions at a limit vertical inertia load factor.

    Static reactions scaled by the limit load factor.
    Returns {nose_N, main_N, total_N}.
    """
    _check_load_factor(load_factor)
    static = static_reactions(weight, dist_nose_to_cg, dist_cg_to_main)
    nose = static["nose_N"] * load_factor
    main = static["main_N"] * load_factor
    return {"nose_N": nose, "main_N": main, "total_N": nose + main}


def braked_roll(weight, dist_nose_to_cg, dist_cg_to_main, friction,
                load_factor=1.0):
    """Braked roll deceleration and ground reaction, all brakes on main gear.

    Main reaction at the given load factor: R_main = W * LF * a / (a + b).
    F_brake = friction * R_main; deceleration_g = F_brake / weight in g
    units (pure number). Returns {main_reaction_N, brake_force_N,
    deceleration_g}.
    """
    if friction < 0 or friction > 1:
        raise ValueError(
            "friction must be in [0, 1], got %r" % (friction,))
    _check_load_factor(load_factor)
    static_main = static_reactions(
        weight, dist_nose_to_cg, dist_cg_to_main)["main_N"]
    main_reaction = static_main * load_factor
    brake_force = friction * main_reaction
    return {
        "main_reaction_N": main_reaction,
        "brake_force_N": brake_force,
        "deceleration_g": brake_force / weight,
    }


def tail_down_reaction(weight, load_factor=N_LEVEL_DEFAULT):
    """Tail-down condition reaction, nose gear unloaded.

    The entire vertical reaction sits on the main gear:
    R = weight * load_factor. Returns a float in N.
    """
    _check_weight(weight)
    _check_load_factor(load_factor)
    return weight * load_factor


def one_wheel_reaction(weight, load_factor, lateral_offset, track):
    """One-wheel asymmetric level landing reaction on the loaded side.

    R = weight * load_factor * (0.5 + lateral_offset / track). A lateral
    CG offset beyond the track half width is non-physical for this
    condition. Returns a float in N.
    """
    _check_weight(weight)
    _check_load_factor(load_factor)
    if track <= 0:
        raise ValueError("track must be positive, got %r" % (track,))
    if lateral_offset < 0 or lateral_offset > track / 2:
        raise ValueError(
            "lateral_offset must lie in [0, track/2], got %r with track "
            "%r" % (lateral_offset, track))
    return weight * load_factor * (0.5 + lateral_offset / track)


def landing_loads_summary(weight, dist_nose_to_cg, dist_cg_to_main,
                          load_factor=N_LEVEL_DEFAULT, friction=0.8,
                          lateral_offset=0.0, track=5.0):
    """Landing loads summary for every gear station.

    Evaluates the static, level landing (limit load factor), braked roll
    at the 1.0 g ground-roll reaction (the braked_roll default), tail
    down and one-wheel conditions. critical_main_N is the maximum of the
    main gear vertical reactions (level, braked roll main, tail down,
    one wheel); critical_nose_N is the maximum of the nose values.
    ValueErrors propagate from the underlying checks.
    """
    static = static_reactions(weight, dist_nose_to_cg, dist_cg_to_main)
    level = level_landing_reactions(weight, dist_nose_to_cg,
                                    dist_cg_to_main, load_factor)
    brake = braked_roll(weight, dist_nose_to_cg, dist_cg_to_main, friction)
    tail_down = tail_down_reaction(weight, load_factor)
    one_wheel = one_wheel_reaction(weight, load_factor, lateral_offset, track)
    main_values = [level["main_N"], brake["main_reaction_N"], tail_down,
                   one_wheel]
    nose_values = [static["nose_N"], level["nose_N"]]
    return {
        "static_nose_N": static["nose_N"],
        "static_main_N": static["main_N"],
        "level_nose_N": level["nose_N"],
        "level_main_N": level["main_N"],
        "brake_force_N": brake["brake_force_N"],
        "deceleration_g": brake["deceleration_g"],
        "tail_down_main_N": tail_down,
        "one_wheel_main_N": one_wheel,
        "critical_main_N": max(main_values),
        "critical_nose_N": max(nose_values),
    }
