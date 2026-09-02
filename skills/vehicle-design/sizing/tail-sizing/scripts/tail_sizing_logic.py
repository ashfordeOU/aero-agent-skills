#!/usr/bin/env python3
"""Tail volume coefficient sizing logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: gated
false): empennage sizing uses tail volume coefficients. The
horizontal tail volume coefficient V_h = S_h * L_h / (S_w * cbar)
relates the horizontal tail area S_h and tail arm L_h to the wing
reference area S_w and mean aerodynamic chord cbar. The vertical tail
volume coefficient V_v = S_v * L_v / (S_w * b) relates the vertical
tail area S_v and tail arm L_v to the wing reference area S_w and
span b. Given a target coefficient and the tail arm, the required
tail area is S_h = V_h * S_w * cbar / L_h (same form for the vertical
tail with b in place of cbar). Typical conceptual sizing ranges:
V_h from 0.5 to 1.0 (transport category about 0.7), V_v from 0.04 to
0.07 (transport category about 0.06).

Units are SI throughout: areas in m^2, arms and reference lengths in
m, coefficients unitless. Invalid inputs raise ValueError throughout.
"""


def tail_volume_coefficient(tail_area, tail_arm, ref_area, ref_length):
    """Horizontal or vertical tail volume coefficient (unitless).

    V = tail_area * tail_arm / (ref_area * ref_length). For the
    horizontal tail pass tail_area = S_h, tail_arm = L_h, ref_area =
    S_w, ref_length = cbar; for the vertical tail pass tail_area =
    S_v, tail_arm = L_v, ref_area = S_w, ref_length = b. All inputs
    are SI (m^2 and m).

    Raises ValueError if any input is not positive.
    """
    if tail_area <= 0:
        raise ValueError("tail_area must be positive, got %r" % (tail_area,))
    if tail_arm <= 0:
        raise ValueError("tail_arm must be positive, got %r" % (tail_arm,))
    if ref_area <= 0:
        raise ValueError("ref_area must be positive, got %r" % (ref_area,))
    if ref_length <= 0:
        raise ValueError("ref_length must be positive, got %r" % (ref_length,))
    return tail_area * tail_arm / (ref_area * ref_length)


def tail_area_required(volume_coeff, tail_arm, ref_area, ref_length):
    """Required tail area (m^2) for a target volume coefficient.

    S = volume_coeff * ref_area * ref_length / tail_arm, the inverse
    of the tail volume coefficient relation. For the horizontal tail
    pass ref_length = cbar, for the vertical tail ref_length = b.

    Raises ValueError if any input is not positive.
    """
    if volume_coeff <= 0:
        raise ValueError(
            "volume_coeff must be positive, got %r" % (volume_coeff,)
        )
    if tail_arm <= 0:
        raise ValueError("tail_arm must be positive, got %r" % (tail_arm,))
    if ref_area <= 0:
        raise ValueError("ref_area must be positive, got %r" % (ref_area,))
    if ref_length <= 0:
        raise ValueError("ref_length must be positive, got %r" % (ref_length,))
    return volume_coeff * ref_area * ref_length / tail_arm


def volume_coefficient_verdict(v_h, v_v):
    """Verdict on a tail volume coefficient pair (dict).

    Returns {"h_ok": bool, "v_ok": bool, "verdict": str}. h_ok is
    True when 0.5 <= v_h <= 1.0, v_ok is True when 0.04 <= v_v <=
    0.07 (typical conceptual sizing ranges; transport category about
    0.7 and 0.06). Boundaries are inclusive. Verdict strings name
    which tail, if any, falls outside its typical range.
    """
    h_ok = 0.5 <= v_h <= 1.0
    v_ok = 0.04 <= v_v <= 0.07
    if h_ok and v_ok:
        verdict = "both tails within typical ranges"
    elif not h_ok and not v_ok:
        verdict = "both tail volume coefficients outside typical ranges"
    elif not h_ok:
        verdict = "horizontal tail volume coefficient outside typical range"
    else:
        verdict = "vertical tail volume coefficient outside typical range"
    return {"h_ok": h_ok, "v_ok": v_ok, "verdict": verdict}
