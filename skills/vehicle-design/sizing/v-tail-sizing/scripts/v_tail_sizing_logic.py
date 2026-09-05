"""V-tail empennage sizing logic (pure stdlib, deterministic).

Sizes a canted V-tail (butterfly or vee tail) empennage from
equivalent horizontal and vertical tail volume requirements under the
documented planform-area projection convention: the horizontal
equivalent area is the sum of the horizontal projections of both
canted panels, s_h_eff = s_vt * cos(Gamma), and the vertical
equivalent area is s_v_eff = s_vt * sin(Gamma), where Gamma is the
dihedral angle measured from the horizontal plane. Under that
convention the vector-sum inversion s_vt = sqrt(s_h^2 + s_v^2) with
Gamma = atan2(s_v, s_h) is exact, the equal panel split carries
(S_vt / 2) * cos(Gamma) and (S_vt / 2) * sin(Gamma) per surface, and
the effective volume coefficients of the round trip recover the
targets within VOLUME_TOL. The cos^2/sin^2 loading convention is not
used here.

Module functions map one-to-one onto the SKILL.md Workflow steps:
tail_area_from_volume_coefficient converts a target volume coefficient
into the required equivalent area (step 2), vtail_geometry resolves
the two equivalent areas onto the canted pair and derives the
per-surface panel geometry (step 3), ruddervator_sizing sizes the
movable control area as a fraction of the total V-tail area (step 4),
and effective_volume_check verifies the effective volume coefficient
round trip with its met verdicts (step 5). Every function raises
ValueError on non-physical (non-positive) inputs.
"""

import math

# Engineering defaults of the leaf, fixed module constants.
RUDDERVATOR_FRACTION = 0.35
SURFACE_ASPECT_RATIO = 4.0
VOLUME_TOL = 1e-9


def tail_area_from_volume_coefficient(v_coef, ref_len, tail_arm, s_ref):
    """Required equivalent tail area for one volume coefficient target.

    Area = v_coef * s_ref * ref_len / tail_arm, the volume-coefficient
    inverse. Call with ref_len = c_bar and tail_arm = l_h for the
    horizontal requirement (V_h), and ref_len = b and tail_arm = l_v
    for the vertical requirement (V_v).

    Raises ValueError unless every input is strictly positive.
    """
    if v_coef <= 0 or ref_len <= 0 or tail_arm <= 0 or s_ref <= 0:
        raise ValueError(
            "volume coefficient, reference length, tail arm and wing "
            "reference area must all be strictly positive")
    return v_coef * s_ref * ref_len / tail_arm


def vtail_geometry(s_h_req, s_v_req, aspect_ratio=SURFACE_ASPECT_RATIO):
    """Resolve two equivalent areas onto the canted V-tail pair.

    Returns a dict with keys s_vt, gamma_rad, gamma_deg,
    area_per_surface, span_per_surface, chord_per_surface:
    s_vt = sqrt(s_h_req^2 + s_v_req^2), gamma_rad = atan2(s_v_req,
    s_h_req) in [0, pi/2) measured from the horizontal plane,
    gamma_deg = degrees(gamma_rad), area_per_surface = s_vt / 2 (the
    equal panel split). Per-surface convention: one panel of that area
    is treated as a flat surface with its own aspect ratio, so
    span_per_surface = sqrt(aspect_ratio * area_per_surface) and
    chord_per_surface = area_per_surface / span_per_surface, the mean
    chord of one panel.

    Raises ValueError unless s_h_req, s_v_req and aspect_ratio are
    strictly positive.
    """
    if s_h_req <= 0 or s_v_req <= 0 or aspect_ratio <= 0:
        raise ValueError(
            "both equivalent areas and the aspect ratio must be "
            "strictly positive")
    s_vt = math.sqrt(s_h_req ** 2 + s_v_req ** 2)
    gamma_rad = math.atan2(s_v_req, s_h_req)
    area_per_surface = s_vt / 2.0
    span_per_surface = math.sqrt(aspect_ratio * area_per_surface)
    chord_per_surface = area_per_surface / span_per_surface
    return {
        "s_vt": s_vt,
        "gamma_rad": gamma_rad,
        "gamma_deg": math.degrees(gamma_rad),
        "area_per_surface": area_per_surface,
        "span_per_surface": span_per_surface,
        "chord_per_surface": chord_per_surface,
    }


def ruddervator_sizing(s_vt, control_fraction=RUDDERVATOR_FRACTION):
    """Ruddervator control area as a fraction of the total V-tail area.

    Total ruddervator area = control_fraction * s_vt (0.35 by default,
    the documented engineering default); per-surface area is half of
    the total because each of the two panels carries one ruddervator.
    No hinge-geometry output, area fraction only.

    Raises ValueError unless s_vt is strictly positive and
    control_fraction lies strictly between 0 and 1.
    """
    if s_vt <= 0:
        raise ValueError("total V-tail area must be strictly positive")
    if control_fraction <= 0 or control_fraction >= 1:
        raise ValueError(
            "ruddervator control fraction must lie strictly between 0 "
            "and 1")
    total = control_fraction * s_vt
    return {
        "ruddervator_area_total": total,
        "ruddervator_area_per_surface": total / 2.0,
        "control_fraction": control_fraction,
    }


def effective_volume_check(s_vt, gamma_rad, v_h_target, v_v_target,
                           s_ref, c_bar, b, l_h, l_v):
    """Effective volume coefficients of the canted tail, with verdicts.

    s_h_eff = s_vt * cos(gamma_rad), s_v_eff = s_vt * sin(gamma_rad),
    v_h_eff = s_h_eff * l_h / (s_ref * c_bar) and
    v_v_eff = s_v_eff * l_v / (s_ref * b). The met flags compare with
    the module tolerance VOLUME_TOL = 1e-9, which absorbs the
    cos/sin/atan2 round-trip error of order 1e-16: v_h_met is True
    when v_h_eff >= v_h_target - VOLUME_TOL, v_v_met likewise against
    v_v_target. A tail sized from the same targets and arms therefore
    returns both met flags True, while a genuinely undersized tail
    fails. Returns a dict with keys s_h_eff, s_v_eff, v_h_eff, v_v_eff,
    v_h_met, v_v_met.

    Raises ValueError unless every input is strictly positive.
    """
    inputs = (s_vt, gamma_rad, v_h_target, v_v_target, s_ref, c_bar,
              b, l_h, l_v)
    if any(value <= 0 for value in inputs):
        raise ValueError(
            "total V-tail area, dihedral, both target coefficients, "
            "wing reference area and chord, span and both tail arms "
            "must all be strictly positive")
    s_h_eff = s_vt * math.cos(gamma_rad)
    s_v_eff = s_vt * math.sin(gamma_rad)
    v_h_eff = s_h_eff * l_h / (s_ref * c_bar)
    v_v_eff = s_v_eff * l_v / (s_ref * b)
    return {
        "s_h_eff": s_h_eff,
        "s_v_eff": s_v_eff,
        "v_h_eff": v_h_eff,
        "v_v_eff": v_v_eff,
        "v_h_met": v_h_eff >= v_h_target - VOLUME_TOL,
        "v_v_met": v_v_eff >= v_v_target - VOLUME_TOL,
    }
