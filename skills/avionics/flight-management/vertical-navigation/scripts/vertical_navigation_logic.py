#!/usr/bin/env python3
"""Vertical navigation (VNAV) logic for an FMS descent profile.

Common-knowledge summary (standards-map.yaml, do-178c: proprietary,
reference-only): an FMS builds the vertical descent profile between
altitude constraints. Units are physically real and stated per
function: altitude in feet (ft), distance in nautical miles (nm),
descent gradient in feet per nautical mile (ft/nm), flight path
angle in degrees (deg). One nautical mile equals 6076.1154 feet.
All inputs are validated; impossible values raise ValueError.

Functions:
- tod_distance: top of descent distance before a target altitude.
- descent_gradient: gradient implied by altitudes over a distance.
- fpa_deg: flight path angle from a gradient.
- altitude_at: altitude after descending a given distance.
- constraint_ok: AT or AT OR ABOVE constraint verdict.
"""

import math

NM_TO_FT = 6076.1154


def tod_distance(cruise_alt_ft, target_alt_ft, gradient_ft_nm):
    """Top of descent distance in nm before the target altitude.

    tod = (cruise_alt - target_alt) / gradient.
    """
    if cruise_alt_ft <= 0:
        raise ValueError("cruise_alt_ft must be > 0, got %r" % (cruise_alt_ft,))
    if target_alt_ft <= 0:
        raise ValueError("target_alt_ft must be > 0, got %r" % (target_alt_ft,))
    if cruise_alt_ft <= target_alt_ft:
        raise ValueError(
            "cruise_alt_ft must exceed target_alt_ft, got %r <= %r"
            % (cruise_alt_ft, target_alt_ft)
        )
    if gradient_ft_nm <= 0:
        raise ValueError("gradient_ft_nm must be > 0, got %r" % (gradient_ft_nm,))
    return (cruise_alt_ft - target_alt_ft) / gradient_ft_nm


def descent_gradient(cruise_alt_ft, target_alt_ft, distance_nm):
    """Descent gradient in ft/nm implied by altitudes over a distance."""
    if cruise_alt_ft <= 0:
        raise ValueError("cruise_alt_ft must be > 0, got %r" % (cruise_alt_ft,))
    if target_alt_ft <= 0:
        raise ValueError("target_alt_ft must be > 0, got %r" % (target_alt_ft,))
    if cruise_alt_ft <= target_alt_ft:
        raise ValueError(
            "cruise_alt_ft must exceed target_alt_ft, got %r <= %r"
            % (cruise_alt_ft, target_alt_ft)
        )
    if distance_nm <= 0:
        raise ValueError("distance_nm must be > 0, got %r" % (distance_nm,))
    return (cruise_alt_ft - target_alt_ft) / distance_nm


def fpa_deg(gradient_ft_nm):
    """Flight path angle in degrees: atan(gradient / 6076.1154)."""
    if gradient_ft_nm <= 0:
        raise ValueError("gradient_ft_nm must be > 0, got %r" % (gradient_ft_nm,))
    return math.degrees(math.atan(gradient_ft_nm / NM_TO_FT))


def altitude_at(alt_start_ft, gradient_ft_nm, distance_nm):
    """Altitude in ft after descending distance_nm along the gradient.

    alt = alt_start - gradient * distance; raises when the result
    would be below zero (the descent path ends below the surface).
    """
    if alt_start_ft <= 0:
        raise ValueError("alt_start_ft must be > 0, got %r" % (alt_start_ft,))
    if gradient_ft_nm <= 0:
        raise ValueError("gradient_ft_nm must be > 0, got %r" % (gradient_ft_nm,))
    if distance_nm < 0:
        raise ValueError("distance_nm must be >= 0, got %r" % (distance_nm,))
    alt = alt_start_ft - gradient_ft_nm * distance_nm
    if alt < 0:
        raise ValueError(
            "descent goes below zero altitude: %r ft at distance %r nm"
            % (alt, distance_nm)
        )
    return alt


def constraint_ok(alt_at_constraint_ft, constraint_ft, at_or_above, tol_ft=1.0):
    """True when the computed altitude satisfies the waypoint constraint.

    at_or_above=True means AT OR ABOVE: alt >= constraint.
    at_or_above=False means AT: alt within tol_ft of the constraint.
    """
    if alt_at_constraint_ft < 0:
        raise ValueError(
            "alt_at_constraint_ft must be >= 0, got %r" % (alt_at_constraint_ft,)
        )
    if constraint_ft <= 0:
        raise ValueError("constraint_ft must be > 0, got %r" % (constraint_ft,))
    if tol_ft < 0:
        raise ValueError("tol_ft must be >= 0, got %r" % (tol_ft,))
    if at_or_above:
        return alt_at_constraint_ft >= constraint_ft
    return abs(alt_at_constraint_ft - constraint_ft) <= tol_ft
