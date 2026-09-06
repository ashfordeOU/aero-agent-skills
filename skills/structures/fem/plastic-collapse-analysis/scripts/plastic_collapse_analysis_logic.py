"""Rigid-perfectly-plastic collapse (limit) analysis of beams and frames.

Pure stdlib (math only), deterministic, SI units (m, N, Pa). Implements
the plastic section modulus Zp about the equal-area axis, the elastic
section modulus Z, the shape factor nu = Zp/Z, the fully plastic moment
Mp = sigma_y*Zp, the plastic collapse loads of the single-span beam
catalog under one central point load by the kinematic (virtual work)
theorem, the sway mechanisms of a simple rectangular frame under a top
lateral load, and the collapse load factor and FAR 25.303 ultimate
margin verdicts.

Scope: rigid-perfectly-plastic bending, doubly symmetric sections with
the plastic neutral axis in the web for the I-beam, small-deflection
mechanisms, one central point load per span case and one top lateral
load per frame case, constant Mp along each member. No elastic
stiffness-method frames, no axial-moment interaction, no strain
hardening, no unloading.
"""

import math

# Section catalog: shape name -> positional dims (metres).
_SECTION_ARITY = {"rectangle": 2, "circle": 1, "i-beam": 4}

# Beam catalog: config -> (collapse-load multiplier on Mp/span, hinge
# count, hinge station texts, mechanism description).
_BEAM_CASES = {
    "simply-supported-central": (
        4.0,
        1,
        ["x = L/2"],
        "one plastic hinge at midspan: the beam rotates as two rigid "
        "halves, hinge rotation 2*theta at a load-point deflection "
        "theta*L/2",
    ),
    "propped-cantilever-central": (
        6.0,
        2,
        ["x = 0", "x = L/2"],
        "two plastic hinges at the fixed end (rotation theta) and under "
        "the load (rotation 2*theta), the collapse mechanism of the "
        "r = 1 propped cantilever",
    ),
    "fixed-fixed-central": (
        8.0,
        3,
        ["x = 0", "x = L/2", "x = L"],
        "three plastic hinges at both supports (rotation theta each) "
        "and midspan (rotation 2*theta), the collapse mechanism of the "
        "r = 2 fixed-fixed beam",
    ),
}

# Portal catalog: base condition -> (multiplier on Mp/height, hinge
# count, hinge station texts, mechanism description).
_PORTAL_CASES = {
    "pinned": (
        2.0,
        2,
        ["top of the left column", "top of the right column"],
        "sway mechanism with plastic hinges at the two top corners: "
        "the columns rotate theta about the pinned bases",
    ),
    "fixed": (
        4.0,
        4,
        ["top of the left column", "top of the right column",
         "base of the left column", "base of the right column"],
        "sway mechanism with plastic hinges at all four corners: the "
        "columns rotate theta about the fixed bases",
    ),
}


def _checked_dims(shape, dims):
    """Validate a section shape and its positional dimensions (m).

    Raises ValueError for an unknown shape, a wrong dims arity, any
    non-positive dimension, an I-beam with d <= 2*t_f (plastic neutral
    axis outside the web) or t_w >= b (web not thinner than the
    flange). Returns the validated dims tuple.
    """
    if shape not in _SECTION_ARITY:
        raise ValueError("unknown section shape: %r" % (shape,))
    if len(dims) != _SECTION_ARITY[shape]:
        raise ValueError(
            "section %r needs %d dims, got %d"
            % (shape, _SECTION_ARITY[shape], len(dims))
        )
    for dim in dims:
        if dim <= 0.0:
            raise ValueError("section dimensions must be positive")
    if shape == "i-beam":
        depth, breadth, tf, tw = dims
        if depth <= 2.0 * tf:
            raise ValueError(
                "I-beam plastic neutral axis outside the web: "
                "d <= 2*t_f"
            )
        if tw >= breadth:
            raise ValueError("I-beam web must be thinner than the flange")
    return dims


def plastic_section_modulus(shape, *dims):
    """Zp (m^3): first moment of area about the equal-area axis.

    Closed forms: rectangle b*h**2/4, circle d**3/6, doubly symmetric
    I-beam b*t_f*(d - t_f) + t_w*(d - 2*t_f)**2/4 with the plastic
    neutral axis in the web.
    """
    dims = _checked_dims(shape, dims)
    if shape == "rectangle":
        breadth, depth = dims
        return breadth * depth ** 2 / 4.0
    if shape == "circle":
        (diameter,) = dims
        return diameter ** 3 / 6.0
    depth, breadth, tf, tw = dims
    return (
        breadth * tf * (depth - tf)
        + tw * (depth - 2.0 * tf) ** 2 / 4.0
    )


def elastic_section_modulus(shape, *dims):
    """Z (m^3): elastic section modulus of the extreme fibre.

    Closed forms: rectangle b*h**2/6, circle pi*d**3/32, I-beam
    Z = 2*I/d with I = (b*d**3 - (b - t_w)*(d - 2*t_f)**3)/12.
    """
    dims = _checked_dims(shape, dims)
    if shape == "rectangle":
        breadth, depth = dims
        return breadth * depth ** 2 / 6.0
    if shape == "circle":
        (diameter,) = dims
        return math.pi * diameter ** 3 / 32.0
    depth, breadth, tf, tw = dims
    inertia = (
        breadth * depth ** 3
        - (breadth - tw) * (depth - 2.0 * tf) ** 3
    ) / 12.0
    return 2.0 * inertia / depth


def shape_factor(shape, *dims):
    """nu = Zp/Z: the reserve between first yield and full plasticity.

    Exactly 3/2 for the rectangle, 16/(3*pi) for the circle and the
    quotient of the two I-beam closed forms otherwise.
    """
    zp = plastic_section_modulus(shape, *dims)
    z = elastic_section_modulus(shape, *dims)
    return zp / z


def fully_plastic_moment(sigma_y, zp):
    """Mp (N m) = sigma_y*Zp of a section at the fully plastic state."""
    if sigma_y <= 0.0:
        raise ValueError("yield stress must be positive")
    if zp <= 0.0:
        raise ValueError("plastic section modulus must be positive")
    return sigma_y * zp


def collapse_load_beam(config, span, mp):
    """Plastic collapse load (N) of a single-span beam by kinematics.

    One central point load, rigid-perfectly-plastic hinge mechanisms
    with r + 1 hinges for r-fold static indeterminacy: 4*Mp/span
    (simply supported), 6*Mp/span (propped cantilever), 8*Mp/span
    (fixed-fixed). Returns a dict with the case, collapse load, hinge
    count, hinge station texts and mechanism description.
    """
    if config not in _BEAM_CASES:
        raise ValueError("unknown beam case: %r" % (config,))
    if span <= 0.0:
        raise ValueError("span must be positive")
    if mp <= 0.0:
        raise ValueError("fully plastic moment must be positive")
    multiplier, hinges, stations, mechanism = _BEAM_CASES[config]
    return {
        "case": config,
        "collapse_load": multiplier * mp / span,
        "plastic_hinges": hinges,
        "hinge_locations": list(stations),
        "mechanism": mechanism,
    }


def portal_sway_collapse_load(height, mp, base="pinned"):
    """Plastic collapse load (N) of a portal sway mechanism.

    Top lateral load on a rectangular frame of column height h:
    2*Mp/h with pinned bases (hinges at the two top corners), 4*Mp/h
    with fixed bases (hinges at all four corners).
    """
    if base not in _PORTAL_CASES:
        raise ValueError("unknown frame base: %r" % (base,))
    if height <= 0.0:
        raise ValueError("column height must be positive")
    if mp <= 0.0:
        raise ValueError("fully plastic moment must be positive")
    multiplier, hinges, stations, mechanism = _PORTAL_CASES[base]
    return {
        "case": "portal-sway-" + base,
        "collapse_load": multiplier * mp / height,
        "plastic_hinges": hinges,
        "hinge_locations": list(stations),
        "mechanism": mechanism,
    }


def collapse_load_factor(limit_load, collapse_load):
    """lambda = collapse load / applied (limit) load, dimensionless."""
    if limit_load <= 0.0:
        raise ValueError("limit load must be positive")
    if collapse_load <= 0.0:
        raise ValueError("collapse load must be positive")
    return collapse_load / limit_load


def ultimate_margin(limit_load, collapse_load, ultimate_factor=1.5):
    """FAR 25.303 ultimate check: collapse load factor vs 1.5 factor.

    ultimate_load_required = ultimate_factor*limit_load; the margin is
    the collapse load factor divided by the ultimate factor and the
    verdict is adequate when the collapse load clears the ultimate load
    required, else inadequate.
    """
    if ultimate_factor <= 0.0:
        raise ValueError("ultimate factor must be positive")
    factor = collapse_load_factor(limit_load, collapse_load)
    required = ultimate_factor * limit_load
    return {
        "collapse_load_factor": factor,
        "ultimate_load_required": required,
        "ultimate_margin": factor / ultimate_factor,
        "verdict": (
            "adequate" if collapse_load >= required else "inadequate"
        ),
    }
