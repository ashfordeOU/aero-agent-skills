#!/usr/bin/env python3
"""Multiaxial yield criteria logic for isotropic metal parts (wave-40).

Common-knowledge strength-of-materials summary (standards-map.yaml,
mmpsd, reference-only): for an isotropic ductile metal the classical
yield criteria reduce a multiaxial stress state to a scalar equivalent
stress that is compared with the tensile yield strength Sy. The von
Mises equivalent stress in plane stress is
vm = sqrt(sx**2 - sx*sy + sy**2 + 3*txy**2); in full 3D it is
vm = sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2)
          + 3*(txy**2 + tyz**2 + tzx**2)).
The plane-stress principal stresses follow from the Mohr circle,
(sx+sy)/2 +/- sqrt(((sx-sy)/2)**2 + txy**2), ordered sigma_1 >= sigma_2.
The Tresca equivalent stress is the largest principal stress difference;
in plane stress the out-of-plane principal is zero, so
tresca = max(sigma_1 - sigma_2, sigma_1, -sigma_2).
The yield margin is Sy/equivalent - 1 (positive below yield, zero at
yield, negative past yield). A shaft section under combined bending and
torsion has von Mises equivalent sqrt(sigma_b**2 + 3*tau**2). The von
Mises envelope in the biaxial (sx, sy) plane is
sx**2 - sx*sy + sy**2 <= Sy**2.

Units: keep every stress and the yield strength in one consistent unit
(MPa or Pa); functions do not convert.
"""

import math

SQRT_3 = math.sqrt(3.0)


def von_mises_plane_stress(sigma_x, sigma_y, tau_xy):
    """Von Mises equivalent stress for the plane-stress state (sx, sy, txy).

    Returns sqrt(sx**2 - sx*sy + sy**2 + 3*txy**2).
    """
    return math.sqrt(
        sigma_x ** 2 - sigma_x * sigma_y + sigma_y ** 2 + 3.0 * tau_xy ** 2
    )


def von_mises_3d(sigma_x, sigma_y, sigma_z, tau_xy, tau_yz, tau_zx):
    """Von Mises equivalent stress for the full 3D stress state.

    Returns sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2)
                 + 3*(txy**2 + tyz**2 + tzx**2)).
    """
    return math.sqrt(
        0.5
        * (
            (sigma_x - sigma_y) ** 2
            + (sigma_y - sigma_z) ** 2
            + (sigma_z - sigma_x) ** 2
        )
        + 3.0 * (tau_xy ** 2 + tau_yz ** 2 + tau_zx ** 2)
    )


def plane_stress_principals(sigma_x, sigma_y, tau_xy):
    """Plane-stress principal stresses from the Mohr circle.

    Returns (sigma_1, sigma_2) with sigma_1 >= sigma_2:
    (sx+sy)/2 +/- sqrt(((sx-sy)/2)**2 + txy**2).
    """
    center = (sigma_x + sigma_y) / 2.0
    radius = math.sqrt(((sigma_x - sigma_y) / 2.0) ** 2 + tau_xy ** 2)
    return center + radius, center - radius


def tresca_equivalent(sigma_1, sigma_3):
    """Tresca equivalent stress from the ordered extreme principals.

    Returns sigma_1 - sigma_3 (the maximum principal stress difference).
    Raises ValueError when sigma_1 < sigma_3 because the principals must
    be ordered.
    """
    if sigma_1 < sigma_3:
        raise ValueError(
            "principals must be ordered sigma_1 >= sigma_3, got %r < %r"
            % (sigma_1, sigma_3)
        )
    return sigma_1 - sigma_3


def tresca_plane_stress(sigma_x, sigma_y, tau_xy):
    """Tresca equivalent stress for the plane-stress state.

    The out-of-plane principal is zero in plane stress, so the maximum
    principal stress difference is the largest of sigma_1 - sigma_2,
    sigma_1 - 0 and 0 - sigma_2 over the ordered principals:
    max(sigma_1 - sigma_2, sigma_1, -sigma_2).
    """
    sigma_1, sigma_2 = plane_stress_principals(sigma_x, sigma_y, tau_xy)
    return max(sigma_1 - sigma_2, sigma_1, -sigma_2)


def yield_margin(equivalent_stress, yield_strength):
    """Yield margin of yield strength over equivalent stress, minus one.

    Returns yield_strength/equivalent_stress - 1 (positive below yield,
    zero at yield, negative past yield). Raises ValueError when either
    input is non-positive.
    """
    if equivalent_stress <= 0.0:
        raise ValueError(
            "equivalent stress must be > 0, got %r" % (equivalent_stress,)
        )
    if yield_strength <= 0.0:
        raise ValueError(
            "yield strength must be > 0, got %r" % (yield_strength,)
        )
    return yield_strength / equivalent_stress - 1.0


def combined_bending_torsion_margin(bending_stress, torsional_stress, yield_strength):
    """Yield margin for a shaft under combined bending and torsion.

    The von Mises equivalent of a bending stress sigma_b with a torsional
    stress tau is sqrt(sigma_b**2 + 3*tau**2); returns the yield margin
    of yield_strength over that equivalent. Raises ValueError exactly as
    yield_margin does.
    """
    equivalent = math.sqrt(bending_stress ** 2 + 3.0 * torsional_stress ** 2)
    return yield_margin(equivalent, yield_strength)


def is_within_von_mises_envelope(sigma_x, sigma_y, yield_strength):
    """Envelope verdict for the biaxial point (sx, sy) in stress space.

    Returns True when sx**2 - sx*sy + sy**2 <= Sy**2, i.e. the point is
    on or inside the von Mises yield envelope (on the boundary counts as
    within). Raises ValueError when the yield strength is non-positive.
    """
    if yield_strength <= 0.0:
        raise ValueError(
            "yield strength must be > 0, got %r" % (yield_strength,)
        )
    return sigma_x ** 2 - sigma_x * sigma_y + sigma_y ** 2 <= yield_strength ** 2
