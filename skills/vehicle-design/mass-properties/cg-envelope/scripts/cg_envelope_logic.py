#!/usr/bin/env python3
"""CG envelope analysis logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: gated
false): the center of gravity of a set of components is the ratio of
the summed moments to the summed weights, x_cg = sum(w_i * x_i) /
sum(w_i), and the same rule applies to the z stations. The CG
envelope is the closed region of allowed (cg station, weight)
operating points bounded by the forward and aft CG limits; an
operating point outside the polygon violates a limit. The static
margin is the distance from the CG to the neutral point normalized
by the mean aerodynamic chord, SM = (x_np - x_cg) / MAC. As fuel
burns the total weight drops and the CG shifts; the excursion is the
CG difference between the two fuel states. Invalid inputs raise
ValueError throughout.
"""


def cg_position(weights, arms):
    """Center of gravity along one axis: sum(w_i * a_i) / sum(w_i).

    Raises ValueError if the lists differ in length, are empty, any
    weight is negative, or the total weight is not positive.
    """
    if len(weights) != len(arms):
        raise ValueError(
            "weights and arms length mismatch: %d vs %d" % (len(weights), len(arms))
        )
    if len(weights) == 0:
        raise ValueError("weights and arms must not be empty")
    if any(w < 0 for w in weights):
        raise ValueError("weights must be non-negative")
    total_weight = sum(weights)
    if total_weight <= 0:
        raise ValueError("total weight must be positive: %r" % (total_weight,))
    total_moment = sum(w * a for w, a in zip(weights, arms))
    return total_moment / total_weight


def cg_position_2d(weights, xs, zs):
    """Center of gravity in two axes: (x_cg, z_cg).

    x_cg = sum(w_i * x_i) / sum(w_i) and
    z_cg = sum(w_i * z_i) / sum(w_i). Validation matches
    cg_position.
    """
    x_cg = cg_position(weights, xs)
    z_cg = cg_position(weights, zs)
    return x_cg, z_cg


def cg_limits_verdict(cg, fwd_limit, aft_limit):
    """Verdict of the CG against the forward and aft limits.

    Returns 'within' when fwd_limit <= cg <= aft_limit, 'forward'
    when the CG is ahead of the forward limit, 'aft' when behind the
    aft limit. Raises ValueError if the forward limit exceeds the
    aft limit.
    """
    if fwd_limit > aft_limit:
        raise ValueError(
            "forward limit %r exceeds aft limit %r" % (fwd_limit, aft_limit)
        )
    if cg < fwd_limit:
        return "forward"
    if cg > aft_limit:
        return "aft"
    return "within"


def static_margin(x_neutral_point, x_cg, mac):
    """Static margin: (x_neutral_point - x_cg) / mac.

    Raises ValueError if the mean aerodynamic chord is not positive.
    """
    if mac <= 0:
        raise ValueError("mac must be positive: %r" % (mac,))
    return (x_neutral_point - x_cg) / mac


def static_margin_verdict(x_neutral_point, x_cg, mac, min_margin=0.05):
    """(margin, ok): ok is True when margin >= min_margin.

    Raises ValueError if mac is not positive or min_margin is
    negative.
    """
    if min_margin < 0:
        raise ValueError("min_margin must be non-negative: %r" % (min_margin,))
    margin = static_margin(x_neutral_point, x_cg, mac)
    return margin, margin >= min_margin


def _validate_envelope_polygon(polygon):
    """Validate a convex envelope polygon; return the orientation sign.

    The polygon is a list of (x_cg, weight) vertices in order around
    the envelope; the last vertex connects back to the first. Raises
    ValueError when the polygon has fewer than three vertices, has
    zero area, or is not convex.
    """
    if not polygon or len(polygon) < 3:
        raise ValueError("envelope polygon needs at least 3 vertices")
    n = len(polygon)
    area2 = 0.0
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        area2 += x1 * y2 - x2 * y1
    if abs(area2) <= 1e-12:
        raise ValueError("envelope polygon has zero area")
    sign = 1.0 if area2 > 0 else -1.0
    for i in range(n):
        ax, ay = polygon[i]
        bx, by = polygon[(i + 1) % n]
        cx, cy = polygon[(i + 2) % n]
        cross = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        if cross * sign < -1e-9:
            raise ValueError("envelope polygon must be convex")
    return sign


def _point_inside_convex(polygon, px, py, sign):
    """True when (px, py) lies inside or on the convex polygon.

    Uses the same-side test: the point is inside when every edge
    cross product has the polygon's orientation sign (zero counts as
    on the boundary, which is inside).
    """
    n = len(polygon)
    for i in range(n):
        ax, ay = polygon[i]
        bx, by = polygon[(i + 1) % n]
        cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        if cross * sign < -1e-9:
            return False
    return True


def point_in_envelope(polygon, point):
    """(inside, violated) for an operating point (x_cg, weight).

    inside is True when the operating point lies inside or on the
    envelope polygon. violated is None when inside, 'forward' when
    the point is ahead of the envelope's forward boundary at its
    weight, 'aft' when behind the aft boundary. When the operating
    weight lies outside the envelope's weight range the violated
    limit is the side of the envelope's overall x extent the point
    falls on. Raises ValueError for a non-convex or degenerate
    polygon (see _validate_envelope_polygon).
    """
    sign = _validate_envelope_polygon(polygon)
    px, py = point
    if _point_inside_convex(polygon, px, py, sign):
        return True, None
    xs = []
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if (y1 > py) != (y2 > py):
            xs.append(x1 + (py - y1) * (x2 - x1) / (y2 - y1))
    if xs:
        xmin, xmax = min(xs), max(xs)
        if px < xmin:
            return False, "forward"
        if px > xmax:
            return False, "aft"
    all_x = [x for x, _ in polygon]
    mid = (min(all_x) + max(all_x)) / 2.0
    return False, "aft" if px >= mid else "forward"


def cg_excursion(weights_before, weights_after, arms):
    """(cg_before, cg_after, shift) across a fuel burn.

    weights_before and weights_after are the component weights in the
    two fuel states (the fuel component drops as fuel burns) and arms
    are the fixed component stations. shift = cg_after - cg_before,
    so a positive shift means the CG moved aft. Validation matches
    cg_position; all weights must be non-negative.
    """
    cg_before = cg_position(weights_before, arms)
    cg_after = cg_position(weights_after, arms)
    return cg_before, cg_after, cg_after - cg_before
