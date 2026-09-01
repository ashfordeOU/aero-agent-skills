#!/usr/bin/env python3
"""Ground effect logic (image vortex method, common methodology).

A wing of span b at height h above an infinite ground plane is
modeled by replacing the ground with a mirror image of the vortex
system, reflected across the ground plane with circulation reversed
(impermeability boundary condition). The image system lies 2 * h
below the real system and induces an upwash that cancels part of
the wing downwash. For elliptic spanwise loading the induced drag
reduction factor (common result of the image method, e.g. Hoerner's
ground effect summary) is

  sigma = 1 / (1 + 16 * (h / b)^2)

so the in-ground-effect induced drag is C_Di,g = C_Di,inf * (1 - sigma)
and the ratio to the free-air value is 16 * (h / b)^2 / (1 + 16 * (h / b)^2).
The induced angle of attack is reduced by the same factor, which
raises the effective aspect ratio to AR / (1 - sigma) and the lift
curve slope toward the 2D section value

  a_g = a_inf / (1 + a_inf * (1 - sigma) / (pi * AR)).

All functions are deterministic, offline, and stdlib only.
"""

import math

_PI = math.pi


def _check_hb(hb):
    if not hb > 0.0:
        raise ValueError("height to span ratio h/b must be positive, got %r" % (hb,))


def _check_ar(ar):
    if not ar > 0.0:
        raise ValueError("aspect ratio AR must be positive, got %r" % (ar,))


def _check_e(e):
    if not 0.0 < e <= 1.0:
        raise ValueError("Oswald span efficiency e must be in (0, 1], got %r" % (e,))


def _check_positive(name, value):
    if not value > 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))


def ground_effect_factor(hb):
    """Induced drag reduction factor sigma for a height to span ratio.

    sigma = 1 / (1 + 16 * (h / b)^2). The induced drag and the
    induced angle of attack are multiplied by (1 - sigma) in ground
    effect. sigma = 1 at h / b = 0 (full reduction) and falls to 0
    far from the ground.
    """
    _check_hb(hb)
    return 1.0 / (1.0 + 16.0 * hb * hb)


def induced_drag_ratio(hb):
    """Ratio of in-ground-effect to free-air induced drag: 1 - sigma.

    Monotone increasing in h / b: 0 at the ground, 1 far from it.
    """
    _check_hb(hb)
    return 1.0 - ground_effect_factor(hb)


def effective_aspect_ratio(hb, ar):
    """Image method effective aspect ratio: AR / (1 - sigma).

    Equivalently AR * (1 + 16 * (h / b)^2) / (16 * (h / b)^2);
    unbounded as h / b approaches 0, matching the drag reduction.
    """
    _check_hb(hb)
    _check_ar(ar)
    return ar / induced_drag_ratio(hb)


def induced_drag(hb, cl, ar, q, s, e=1.0):
    """Induced drag force in ground effect, in newtons.

    Free-air induced drag C_Di = C_L^2 / (pi * e * AR) applied to
    the dynamic pressure q (Pa) and wing area S (m^2), scaled by the
    ratio 1 - sigma. C_L may be negative (symmetric physics).
    """
    _check_hb(hb)
    _check_ar(ar)
    _check_e(e)
    _check_positive("dynamic pressure q", q)
    _check_positive("wing area S", s)
    free = q * s * cl * cl / (_PI * e * ar)
    return free * induced_drag_ratio(hb)


def lift_curve_slope_ground(hb, ar, a_inf=2.0 * _PI):
    """Lift curve slope per radian in ground effect.

    a_g = a_inf / (1 + a_inf * (1 - sigma) / (pi * AR)) with a_inf
    the 2D section slope (default 2 * pi, thin airfoil). Tends to
    a_inf as h / b approaches 0, and to the free-air finite wing
    slope far from the ground.
    """
    _check_hb(hb)
    _check_ar(ar)
    _check_positive("2D section slope a_inf", a_inf)
    return a_inf / (1.0 + a_inf * induced_drag_ratio(hb) / (_PI * ar))


def lift_curve_slope_free(ar, a_inf=2.0 * _PI):
    """Free-air finite wing lift curve slope per radian (sigma = 0)."""
    _check_ar(ar)
    _check_positive("2D section slope a_inf", a_inf)
    return a_inf / (1.0 + a_inf / (_PI * ar))


def lift_increase_factor(hb, ar, a_inf=2.0 * _PI):
    """Ratio of in-ground-effect to free-air lift curve slope.

    Greater than 1 in ground effect; grows as h / b shrinks.
    """
    _check_hb(hb)
    _check_ar(ar)
    _check_positive("2D section slope a_inf", a_inf)
    return lift_curve_slope_ground(hb, ar, a_inf) / lift_curve_slope_free(ar, a_inf)


def image_vortex_offset(h):
    """Distance from the real vortex system to its ground image: 2 * h.

    The mirror image sits h below the ground plane, so the real to
    image separation is twice the wing height above ground.
    """
    _check_positive("height above ground h", h)
    return 2.0 * h
