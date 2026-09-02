#!/usr/bin/env python3
"""Static longitudinal stability logic (common flight-mechanics
methodology, paraphrase).

Common-knowledge summary (standards-map.yaml, far-25/cs-25:
reference-only regulation context): transport aeroplanes must show
positive static longitudinal stability so a disturbance in pitch
produces restoring moments. Standard practice locates the neutral
point from the wing aerodynamic center, the horizontal tail volume
coefficient, the tail-to-wing lift slope ratio, and the downwash
gradient, then measures the static margin from the center of gravity
to the neutral point. A positive static margin means the aircraft is
longitudinally stable; the minimum margin is a project-defined band.
All positions are fractions of the mean aerodynamic chord
(dimensionless).
"""


def neutral_point(h_ac_w, tail_volume_coeff, lift_slope_ratio,
                  downwash_gradient):
    """Neutral point as a fraction of mean aerodynamic chord.

    h_np = h_ac_w + V_h * (a_t / a_w) * (1 - depsilon/dalpha).

    Raises ValueError when h_ac_w is outside (0, 1), tail_volume_coeff
    is <= 0, lift_slope_ratio is <= 0, or downwash_gradient is outside
    [0, 1).
    """
    if not (0.0 < h_ac_w < 1.0):
        raise ValueError(
            "wing aerodynamic center must be in (0, 1), got %r" % (h_ac_w,)
        )
    if tail_volume_coeff <= 0:
        raise ValueError(
            "tail volume coefficient must be > 0, got %r" % (tail_volume_coeff,)
        )
    if lift_slope_ratio <= 0:
        raise ValueError(
            "lift slope ratio must be > 0, got %r" % (lift_slope_ratio,)
        )
    if not (0.0 <= downwash_gradient < 1.0):
        raise ValueError(
            "downwash gradient must be in [0, 1), got %r" % (downwash_gradient,)
        )
    return h_ac_w + tail_volume_coeff * lift_slope_ratio * (
        1.0 - downwash_gradient
    )


def static_margin(neutral_point_val, h_cg):
    """Static margin: neutral point minus center of gravity position.

    Positive margin means a stable configuration.

    Raises ValueError when neutral_point_val or h_cg is outside (0, 1).
    """
    if not (0.0 < neutral_point_val < 1.0):
        raise ValueError(
            "neutral point must be in (0, 1), got %r" % (neutral_point_val,)
        )
    if not (0.0 < h_cg < 1.0):
        raise ValueError(
            "center of gravity must be in (0, 1), got %r" % (h_cg,)
        )
    return neutral_point_val - h_cg


def longitudinally_stable(margin, min_margin=0.05):
    """True when the static margin meets the minimum stability margin.

    Raises ValueError when min_margin is negative.
    """
    if min_margin < 0:
        raise ValueError(
            "minimum margin must be >= 0, got %r" % (min_margin,)
        )
    return margin >= min_margin
