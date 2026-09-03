"""Dubins shortest-path planning for heading-constrained fixed-wing poses.

Pure Python stdlib implementation of the classic Dubins set of curve
families (CSC: RSR, LSL, RSL, LSR and CCC: RLR, LRL) between a start
pose and a goal pose under a minimum turn radius rho.

Pose convention: (x, y, heading_rad) with heading measured from the
+x axis, counterclockwise positive.  Left turns (direction +1) are
counterclockwise arcs about a center offset by rho on the left normal
side; right turns (direction -1) are clockwise arcs about a center on
the right normal side.

Public API:
  arc_center(x, y, heading_rad, rho, direction) -> (cx, cy)
  tangent_points(c1, c2, turn1, turn2, rho) -> ((p1x, p1y), (p2x, p2y))
  path_length(segments, rho) -> float
  dubins_candidates(start, goal, rho) -> {type: candidate or None}
  dubins_path(start, goal, rho) -> dict

Assumptions: constant speed, no wind, forward motion only.  Clothoid
and Reeds-Shepp (reversing) extensions are out of scope.
"""

import math

TWOPI = 2.0 * math.pi
RHO_MIN = 0.0  # turn radius must be strictly positive
FAMILY_NAMES = ("LSL", "RSL", "LSR", "RSR", "LRL", "RLR")
TURN_LEFT = +1
TURN_RIGHT = -1
_FAMILY_TURNS = {
    "LSL": (TURN_LEFT, TURN_LEFT),
    "RSL": (TURN_RIGHT, TURN_LEFT),
    "LSR": (TURN_LEFT, TURN_RIGHT),
    "RSR": (TURN_RIGHT, TURN_RIGHT),
    "LRL": (TURN_LEFT, TURN_LEFT),
    "RLR": (TURN_RIGHT, TURN_RIGHT),
}


def _check_finite(value, name):
    if not math.isfinite(value):
        raise ValueError("non-finite value for " + name)


def arc_center(x, y, heading_rad, rho, direction):
    """Return the turn arc center for a pose and a turn direction.

    direction +1 (left): center at (x - rho*sin(h), y + rho*cos(h)),
    the pose plus rho times the left normal (-sin h, cos h).
    direction -1 (right): center at (x + rho*sin(h), y - rho*cos(h)).
    """
    if direction not in (TURN_LEFT, TURN_RIGHT):
        raise ValueError("direction must be +1 (left) or -1 (right)")
    _check_finite(x, "x")
    _check_finite(y, "y")
    _check_finite(heading_rad, "heading_rad")
    _check_finite(rho, "rho")
    if rho <= RHO_MIN:
        raise ValueError("minimum turn radius rho must be positive")
    if direction == TURN_LEFT:
        return (x - rho * math.sin(heading_rad),
                y + rho * math.cos(heading_rad))
    return (x + rho * math.sin(heading_rad),
            y - rho * math.cos(heading_rad))


def _arc_point(cx, cy, heading_rad, direction, rho):
    """Point reached on an arc of radius rho at a given heading."""
    return (cx + rho * direction * math.sin(heading_rad),
            cy - rho * direction * math.cos(heading_rad))


def _arc_sweep(heading_from, heading_to, direction):
    """Signed arc angle from one heading to another, in [0, TWOPI).

    Left turns sweep heading counterclockwise (increasing angle);
    right turns sweep heading clockwise (decreasing angle).
    """
    if direction == TURN_LEFT:
        return (heading_to - heading_from) % TWOPI
    return (heading_from - heading_to) % TWOPI


def _tangent_or_none(c1, c2, turn1, turn2, rho):
    """Common tangent between two turn circles; None when infeasible.

    Same-sign turns use the outer (external) tangent; opposite-sign
    turns use the inner (internal) tangent, which exists only when the
    center separation d is at least 2*rho.  Returns a dict with the
    tangent points, the straight segment length and the heading of the
    straight segment, or None when no inner tangent exists.
    """
    vx = c2[0] - c1[0]
    vy = c2[1] - c1[1]
    d = math.hypot(vx, vy)
    if d <= 1e-12:
        # Coincident circles of the same turn sense: any heading works,
        # take heading zero (the arc sweep splits the rotation).
        heading = 0.0
        straight = 0.0
    elif turn1 == turn2:
        heading = math.atan2(vy, vx)
        straight = d
    else:
        if d < 2.0 * rho - 1e-9:
            return None
        arg = min(1.0, 2.0 * rho / d)
        heading = math.atan2(vy, vx) + turn1 * math.asin(arg)
        straight = math.sqrt(max(d * d - 4.0 * rho * rho, 0.0))
    p1 = _arc_point(c1[0], c1[1], heading, turn1, rho)
    p2 = _arc_point(c2[0], c2[1], heading, turn2, rho)
    for point, center in ((p1, c1), (p2, c2)):
        radius = math.hypot(point[0] - center[0], point[1] - center[1])
        if abs(radius - rho) > 1e-9:
            raise AssertionError("tangent point not at radius rho")
    return {"p1": p1, "p2": p2, "straight": straight, "heading": heading}


def tangent_points(c1, c2, turn1, turn2, rho):
    """Return (p1, p2), the tangent points between two turn circles.

    Circles have radius rho and live on turn sense turn1 (about c1) and
    turn2 (about c2).  Raises ValueError when the opposite-sign inner
    tangent does not exist (center separation below 2*rho).
    """
    result = _tangent_or_none(c1, c2, turn1, turn2, rho)
    if result is None:
        raise ValueError(
            "no inner tangent exists for center separation below 2*rho")
    return (result["p1"], result["p2"])


def path_length(segments, rho):
    """Total path length: sum of rho * arc sweep plus straight lengths."""
    total = 0.0
    for segment in segments:
        if segment["kind"] == "arc":
            total += rho * segment["angle_rad"]
        else:
            total += segment["length"]
    return total


def _arc_segment(direction, angle_rad, rho):
    return {"kind": "arc", "direction": direction,
            "angle_rad": angle_rad, "length": rho * angle_rad}


def _straight_segment(length):
    return {"kind": "straight", "length": length}


def _require_pose(pose, label):
    if not isinstance(pose, dict):
        raise ValueError(label + " pose must be a dict with x, y, heading_rad")
    for key in ("x", "y", "heading_rad"):
        if key not in pose:
            raise ValueError("missing key '" + key + "' in " + label + " pose")
        _check_finite(pose[key], label + " pose " + key)


def _csc_candidate(start, goal, rho, family):
    """Candidate CSC path (arc, straight, arc) for one family or None."""
    turn1, turn2 = _FAMILY_TURNS[family]
    c1 = arc_center(start["x"], start["y"], start["heading_rad"], rho, turn1)
    c2 = arc_center(goal["x"], goal["y"], goal["heading_rad"], rho, turn2)
    tangent = _tangent_or_none(c1, c2, turn1, turn2, rho)
    if tangent is None:
        return None
    h0 = start["heading_rad"]
    hg = goal["heading_rad"]
    theta = tangent["heading"]
    a1 = _arc_sweep(h0, theta, turn1)
    a2 = _arc_sweep(theta, hg, turn2)
    segments = [_arc_segment(turn1, a1, rho),
                _straight_segment(tangent["straight"]),
                _arc_segment(turn2, a2, rho)]
    return {"type": family,
            "length": path_length(segments, rho),
            "segments": segments,
            "arc_centers": [c1, c2],
            "waypoints": [(start["x"], start["y"]),
                          tangent["p1"], tangent["p2"],
                          (goal["x"], goal["y"])],
            "feasible": True}


def _ccc_candidate(start, goal, rho, family):
    """Candidate CCC path (arc, arc, arc) for LRL or RLR, or None."""
    if family == "LRL":
        t_end = TURN_LEFT
    else:
        t_end = TURN_RIGHT
    c1 = arc_center(start["x"], start["y"], start["heading_rad"], rho, t_end)
    c3 = arc_center(goal["x"], goal["y"], goal["heading_rad"], rho, t_end)
    vx = c3[0] - c1[0]
    vy = c3[1] - c1[1]
    d = math.hypot(vx, vy)
    if d <= 1e-12 or d > 4.0 * rho + 1e-9:
        return None
    big = 2.0 * rho
    half = math.sqrt(max(big * big - (d / 2.0) * (d / 2.0), 0.0))
    perp = (-vy / d, vx / d)
    mid = ((c1[0] + c3[0]) / 2.0, (c1[1] + c3[1]) / 2.0)
    best = None
    for sign in (-1.0, 1.0):
        cm = (mid[0] + sign * half * perp[0],
              mid[1] + sign * half * perp[1])
        w1 = (cm[0] - c1[0], cm[1] - c1[1])
        w2 = (c3[0] - cm[0], c3[1] - cm[1])
        if t_end == TURN_LEFT:
            h1 = math.atan2(w1[0], -w1[1])
            h2 = math.atan2(-w2[0], w2[1])
        else:
            h1 = math.atan2(-w1[0], w1[1])
            h2 = math.atan2(w2[0], -w2[1])
        p1 = _arc_point(c1[0], c1[1], h1, t_end, rho)
        p2 = _arc_point(c3[0], c3[1], h2, t_end, rho)
        a1 = _arc_sweep(start["heading_rad"], h1, t_end)
        am = _arc_sweep(h1, h2, -t_end)
        a3 = _arc_sweep(h2, goal["heading_rad"], t_end)
        segments = [_arc_segment(t_end, a1, rho),
                    _arc_segment(-t_end, am, rho),
                    _arc_segment(t_end, a3, rho)]
        candidate = {"type": family,
                     "length": path_length(segments, rho),
                     "segments": segments,
                     "arc_centers": [c1, cm, c3],
                     "waypoints": [(start["x"], start["y"]), p1, p2,
                                   (goal["x"], goal["y"])],
                     "feasible": True}
        if best is None or candidate["length"] < best["length"]:
            best = candidate
    return best


def dubins_candidates(start, goal, rho):
    """Evaluate all six Dubins families; returns {family: candidate}."""
    _require_pose(start, "start")
    _require_pose(goal, "goal")
    if rho <= RHO_MIN:
        raise ValueError("minimum turn radius rho must be positive")
    _check_finite(rho, "rho")
    candidates = {}
    for family in FAMILY_NAMES:
        if family in ("LSL", "RSL", "LSR", "RSR"):
            candidates[family] = _csc_candidate(start, goal, rho, family)
        else:
            candidates[family] = _ccc_candidate(start, goal, rho, family)
    return candidates


def dubins_path(start, goal, rho):
    """Plan the shortest Dubins path between two heading-constrained poses.

    Returns a dict {type, length, segments, arc_centers, waypoints,
    feasible} for the minimum length of the six CSC/CCC families.
    Segments list the arcs (kind, direction, angle_rad, length) and the
    straight (kind, length) in travel order; arc_centers and waypoints
    list the circle centers and the start, tangent and goal points.
    Always feasible (feasible True) for any positive rho.
    """
    candidates = dubins_candidates(start, goal, rho)
    feasible = [candidate for candidate in candidates.values()
                if candidate is not None]
    result = min(feasible, key=lambda candidate: candidate["length"])
    result = dict(result)
    result["feasible"] = True
    return result


if __name__ == "__main__":
    s = {"x": 0.0, "y": 0.0, "heading_rad": 0.0}
    cases = [
        (s, {"x": 100.0, "y": 0.0, "heading_rad": 0.0}, 10.0),
        (s, {"x": 0.0, "y": 40.0, "heading_rad": math.pi}, 10.0),
        (s, {"x": 0.0, "y": 10.0, "heading_rad": math.pi / 2.0}, 10.0),
    ]
    for index, (start, goal, rho) in enumerate(cases):
        path = dubins_path(start, goal, rho)
        print("case", index + 1, "type", path["type"],
              "length %.6f" % path["length"])
        cands = dubins_candidates(start, goal, rho)
        print("   families:",
              " ".join("%s=%s" % (name, "inf" if cands[name] is None
                                  else "%.3f" % cands[name]["length"])
                       for name in FAMILY_NAMES))
