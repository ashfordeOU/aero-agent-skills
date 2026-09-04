#!/usr/bin/env python3
"""Metallic pin-loaded round-end lug stress analysis (paraphrase).

Standard engineering methodology summary (mmpsd and far-25 referenced
by name only per standards-map.yaml, never reproduced verbatim): a
round-end lug is a hole of diameter D centered in a round head of
radius e, so the lug width is w = 2e, with thickness t carrying an
axial pin load P. The bearing stress on the hole is
sigma_b = P / (D t). The net section tension stress across the
remaining width is sigma_nt = P / ((w - D) t). The tearout shear
stress on the two planes running from the hole tangent to the outer
contour is sigma_te = P / (2 t L_te), with each shear plane of length
L_te = sqrt(e^2 - (D/2)^2). The margin of a mode is allowable /
applied - 1, using the lug bearing ultimate F_bru for bearing, the
tension ultimate F_tu for net section tension and the shear ultimate
F_su for tearout; the governing mode is the mode with the smallest
margin, and the lug passes when that minimum margin is at least zero.
The material allowables are inputs (for example MMPDS chapter 9 lug
ultimate data for the alloy, referenced, not reproduced). All
functions are pure stdlib, deterministic and offline, in SI units
(N, m, Pa).
"""

import math

DEFAULT_E_OVER_D_LO = 0.6
DEFAULT_E_OVER_D_HI = 2.5
DEFAULT_SWEEP_STEPS = 20
GOVERNING_ORDER = ("bearing", "net_tension", "tearout")


def _check_geometry(hole_diameter_m, thickness_m, lug_width_m,
                    edge_distance_m):
    """Reject non-positive and degenerate lug geometry with ValueError."""
    if hole_diameter_m <= 0.0:
        raise ValueError("hole diameter must be positive")
    if thickness_m <= 0.0:
        raise ValueError("lug thickness must be positive")
    if lug_width_m <= 0.0:
        raise ValueError("lug width must be positive")
    if edge_distance_m <= 0.0:
        raise ValueError("edge distance must be positive")
    if edge_distance_m <= hole_diameter_m / 2.0:
        raise ValueError("edge distance must exceed half the hole diameter")
    if lug_width_m <= hole_diameter_m:
        raise ValueError("lug width must exceed the hole diameter")


def _check_allowables(f_tu_pa, f_su_pa, f_bru_pa):
    """Reject non-positive material allowables with ValueError."""
    if f_tu_pa <= 0.0:
        raise ValueError("tension allowable must be positive")
    if f_su_pa <= 0.0:
        raise ValueError("shear allowable must be positive")
    if f_bru_pa <= 0.0:
        raise ValueError("bearing allowable must be positive")


def lug_stresses(load_n, hole_diameter_m, thickness_m, lug_width_m,
                 edge_distance_m):
    """Applied lug mode stresses for an axial pin load.

    Returns a dict with bearing_pa, net_tension_pa, tearout_pa,
    tearout_plane_length_m and net_section_width_m. Raises ValueError
    for a negative load, non-positive dimensions, edge_distance not
    above hole_diameter / 2, or lug_width not above hole_diameter.
    """
    if load_n < 0.0:
        raise ValueError("lug load must be non-negative")
    _check_geometry(hole_diameter_m, thickness_m, lug_width_m,
                    edge_distance_m)
    bearing_pa = load_n / (hole_diameter_m * thickness_m)
    net_tension_pa = load_n / ((lug_width_m - hole_diameter_m) *
                               thickness_m)
    tearout_plane_length_m = math.sqrt(edge_distance_m ** 2 -
                                       (hole_diameter_m / 2.0) ** 2)
    tearout_pa = load_n / (2.0 * thickness_m * tearout_plane_length_m)
    return {
        "bearing_pa": bearing_pa,
        "net_tension_pa": net_tension_pa,
        "tearout_pa": tearout_pa,
        "tearout_plane_length_m": tearout_plane_length_m,
        "net_section_width_m": lug_width_m - hole_diameter_m,
    }


def lug_margins(stresses, f_tu_pa, f_su_pa, f_bru_pa):
    """Per-mode margins, allowable / applied - 1.

    Accepts the dict from lug_stresses and returns bearing_margin,
    net_tension_margin and tearout_margin. Raises ValueError for
    non-positive allowables.
    """
    _check_allowables(f_tu_pa, f_su_pa, f_bru_pa)
    return {
        "bearing_margin": f_bru_pa / stresses["bearing_pa"] - 1.0,
        "net_tension_margin": f_tu_pa / stresses["net_tension_pa"] - 1.0,
        "tearout_margin": f_su_pa / stresses["tearout_pa"] - 1.0,
    }


def _per_mode_margins(margins):
    """Map the flat margin dict onto governing-mode keys."""
    return {
        "bearing": margins["bearing_margin"],
        "net_tension": margins["net_tension_margin"],
        "tearout": margins["tearout_margin"],
    }


def lug_analysis(load_n, hole_diameter_m, thickness_m, lug_width_m,
                 edge_distance_m, f_tu_pa, f_su_pa, f_bru_pa):
    """Full lug margin check: stresses, margins, governing mode.

    Returns a dict with bearing_stress_pa, net_tension_stress_pa,
    tearout_stress_pa, bearing_margin, net_tension_margin,
    tearout_margin, governing_mode, min_margin, passes, e_over_d,
    d_over_t, tearout_plane_length_m and net_section_width_m. The
    governing mode is the mode with the smallest margin; passes is
    True when min_margin >= 0.
    """
    stresses = lug_stresses(load_n, hole_diameter_m, thickness_m,
                            lug_width_m, edge_distance_m)
    margins = lug_margins(stresses, f_tu_pa, f_su_pa, f_bru_pa)
    per_mode = _per_mode_margins(margins)
    governing_mode = GOVERNING_ORDER[0]
    for mode in GOVERNING_ORDER[1:]:
        if per_mode[mode] < per_mode[governing_mode]:
            governing_mode = mode
    min_margin = per_mode[governing_mode]
    return {
        "bearing_stress_pa": stresses["bearing_pa"],
        "net_tension_stress_pa": stresses["net_tension_pa"],
        "tearout_stress_pa": stresses["tearout_pa"],
        "bearing_margin": margins["bearing_margin"],
        "net_tension_margin": margins["net_tension_margin"],
        "tearout_margin": margins["tearout_margin"],
        "governing_mode": governing_mode,
        "min_margin": min_margin,
        "passes": min_margin >= 0.0,
        "e_over_d": edge_distance_m / hole_diameter_m,
        "d_over_t": hole_diameter_m / thickness_m,
        "tearout_plane_length_m": stresses["tearout_plane_length_m"],
        "net_section_width_m": stresses["net_section_width_m"],
    }


def lug_allowable_capacity(hole_diameter_m, thickness_m, edge_distance_m,
                           f_tu_pa, f_su_pa, f_bru_pa):
    """Per-mode allowable lug loads at the round-end geometry.

    Uses the round-end convention w = 2e. Each per-mode capacity is
    the load that makes that mode margin exactly zero: bearing
    F_bru D t, net section tension F_tu (w - D) t and tearout
    F_su 2 t L_te. Returns a dict with bearing_capacity_n,
    net_tension_capacity_n, tearout_capacity_n, limiting_mode and
    limiting_capacity_n, where the limiting mode has the smallest
    capacity.
    """
    _check_geometry(hole_diameter_m, thickness_m,
                    2.0 * edge_distance_m, edge_distance_m)
    _check_allowables(f_tu_pa, f_su_pa, f_bru_pa)
    lug_width_m = 2.0 * edge_distance_m
    tearout_plane_length_m = math.sqrt(edge_distance_m ** 2 -
                                       (hole_diameter_m / 2.0) ** 2)
    bearing_capacity_n = f_bru_pa * hole_diameter_m * thickness_m
    net_tension_capacity_n = (f_tu_pa *
                              (lug_width_m - hole_diameter_m) *
                              thickness_m)
    tearout_capacity_n = (f_su_pa * 2.0 * thickness_m *
                          tearout_plane_length_m)
    per_mode = {
        "bearing": bearing_capacity_n,
        "net_tension": net_tension_capacity_n,
        "tearout": tearout_capacity_n,
    }
    limiting_mode = GOVERNING_ORDER[0]
    for mode in GOVERNING_ORDER[1:]:
        if per_mode[mode] < per_mode[limiting_mode]:
            limiting_mode = mode
    return {
        "bearing_capacity_n": bearing_capacity_n,
        "net_tension_capacity_n": net_tension_capacity_n,
        "tearout_capacity_n": tearout_capacity_n,
        "limiting_mode": limiting_mode,
        "limiting_capacity_n": per_mode[limiting_mode],
    }


def lug_governing_map(hole_diameter_m, thickness_m, f_tu_pa, f_su_pa,
                      f_bru_pa, e_over_d_lo=DEFAULT_E_OVER_D_LO,
                      e_over_d_hi=DEFAULT_E_OVER_D_HI,
                      steps=DEFAULT_SWEEP_STEPS):
    """Governing-mode and capacity sweep over the edge distance ratio.

    Sweeps e/D from e_over_d_lo to e_over_d_hi inclusive at fixed D
    and t with e = ratio * D and w = 2e, steps intervals. Returns a
    list of dicts with e_over_d, governing_mode and capacity_n. For
    typical aluminum allowables the map shows net section tension
    governing at low e/D, tearout in the middle band and bearing at
    high e/D.
    """
    if hole_diameter_m <= 0.0 or thickness_m <= 0.0:
        raise ValueError("diameter and thickness must be positive")
    _check_allowables(f_tu_pa, f_su_pa, f_bru_pa)
    if steps < 1:
        raise ValueError("steps must be at least one interval")
    if e_over_d_lo <= 0.5:
        raise ValueError("sweep lower bound must exceed 0.5")
    if e_over_d_hi <= e_over_d_lo:
        raise ValueError("sweep upper bound must exceed the lower bound")
    rows = []
    for index in range(steps + 1):
        e_over_d = (e_over_d_lo +
                    (e_over_d_hi - e_over_d_lo) * index / steps)
        capacity = lug_allowable_capacity(
            hole_diameter_m, thickness_m, e_over_d * hole_diameter_m,
            f_tu_pa, f_su_pa, f_bru_pa)
        rows.append({
            "e_over_d": e_over_d,
            "governing_mode": capacity["limiting_mode"],
            "capacity_n": capacity["limiting_capacity_n"],
        })
    return rows
