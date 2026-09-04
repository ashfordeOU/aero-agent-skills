#!/usr/bin/env python3
"""Test point matrix design logic (paraphrase, common flight-test
methodology).

Common-knowledge summary (standards-map.yaml, far-25/cs-25 reference-only
context): a flight test program is flown against a test point matrix, in
which the test conditions vary along one axis at a time. The matrix is
the cartesian product of the altitude, speed, and weight sweeps across
the aircraft configurations, a fraction of the points is repeated for
data quality, the points are sequenced so configuration changes and
altitude hops are minimized, and each flown point is checked against the
steady state tolerance of its planned condition.
"""


def build_test_matrix(altitudes, speeds, weights, configurations):
    """Expand the condition sweeps into the full grid of test points.

    altitudes, speeds, and weights are lists of numeric levels (int or
    float, not bool); configurations is a list of non-empty strings.
    The grid is the cartesian product, ordered altitude-major, then
    speed, then weight, then configuration, so the result is
    deterministic. Each point is a dict with:
      - "id": "tp1" .. "tpN" in grid order (1-based)
      - "altitude", "speed", "weight": the planned condition levels
      - "configuration": the aircraft configuration label
      - "repeat": False until add_repeat_points marks it

    Returns a dict with:
      - "points": the list of test point dicts in grid order
      - "count": number of test points

    Raises ValueError on an empty or non-list sweep, a non-numeric or
    bool altitude/speed/weight level, a negative altitude, a zero or
    negative speed, a zero or negative weight, a non-string or blank
    configuration, or an empty configurations list.
    """
    for label, values in (("altitudes", altitudes), ("speeds", speeds),
                          ("weights", weights)):
        if not isinstance(values, list) or len(values) == 0:
            raise ValueError(
                "%s must be a non-empty list, got %r" % (label, values)
            )
        for v in values:
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise ValueError(
                    "%s levels must be numeric, got %r" % (label, v)
                )
    for v in altitudes:
        if v < 0:
            raise ValueError("altitude levels must be >= 0, got %r" % (v,))
    for v in speeds:
        if v <= 0:
            raise ValueError("speed levels must be > 0, got %r" % (v,))
    for v in weights:
        if v <= 0:
            raise ValueError("weight levels must be > 0, got %r" % (v,))
    if not isinstance(configurations, list) or len(configurations) == 0:
        raise ValueError(
            "configurations must be a non-empty list, got %r"
            % (configurations,)
        )
    for c in configurations:
        if not isinstance(c, str) or not c:
            raise ValueError(
                "configuration labels must be non-empty strings, got %r"
                % (c,)
            )
    points = []
    idx = 0
    for altitude in altitudes:
        for speed in speeds:
            for weight in weights:
                for config in configurations:
                    idx += 1
                    points.append(
                        {
                            "id": "tp%d" % idx,
                            "altitude": altitude,
                            "speed": speed,
                            "weight": weight,
                            "configuration": config,
                            "repeat": False,
                        }
                    )
    return {"points": points, "count": len(points)}


def add_repeat_points(points, repeat_interval):
    """Mark every repeat_interval-th point (1-based grid order) as a repeat.

    points is a list of point dicts as produced by build_test_matrix
    (each with a non-empty string "id" and a bool "repeat" key).
    repeat_interval is an int >= 2. Returns a new list of dicts with
    the same fields and the repeat flag set on the marked points; the
    input list is not modified.

    Raises ValueError on an empty or non-list points value, a non-dict
    point, a missing or non-string id, a missing or non-bool repeat
    key, a duplicate id, or a repeat_interval that is not an int >= 2.
    """
    if not isinstance(points, list) or len(points) == 0:
        raise ValueError("points must be a non-empty list, got %r" % (points,))
    if isinstance(repeat_interval, bool) or not isinstance(
        repeat_interval, int
    ):
        raise ValueError(
            "repeat_interval must be an int, got %r" % (repeat_interval,)
        )
    if repeat_interval < 2:
        raise ValueError(
            "repeat_interval must be >= 2, got %r" % (repeat_interval,)
        )
    seen = set()
    for pt in points:
        if not isinstance(pt, dict):
            raise ValueError("each test point must be a dict, got %r" % (pt,))
        pid = pt.get("id")
        if not isinstance(pid, str) or not pid:
            raise ValueError(
                "test point id must be a non-empty string, got %r" % (pid,)
            )
        if pid in seen:
            raise ValueError("duplicate test point id %r" % (pid,))
        seen.add(pid)
        if "repeat" not in pt or not isinstance(pt["repeat"], bool):
            raise ValueError(
                "test point %r needs a bool repeat key" % (pid,)
            )
    out = []
    for i, pt in enumerate(points, 1):
        copy = dict(pt)
        if i % repeat_interval == 0:
            copy["repeat"] = True
        out.append(copy)
    return out


def sequence_for_efficiency(points):
    """Order the points for efficient flying.

    points is a list of point dicts with a non-empty string
    "configuration", a numeric "altitude", and a numeric "speed" key.
    The order groups by configuration in order of first appearance (so
    the aircraft is reconfigured once per group), then by altitude
    ascending (so altitude is swept once per group), then by speed
    ascending (so the speed levels are flown in order). The result is
    deterministic: the sort is stable and the group order comes from
    the input.

    Returns a new list of point dicts in the efficiency order; the
    input list is not modified.

    Raises ValueError on an empty or non-list points value, a non-dict
    point, a missing or blank configuration label, or a non-numeric or
    bool altitude or speed.
    """
    if not isinstance(points, list) or len(points) == 0:
        raise ValueError("points must be a non-empty list, got %r" % (points,))
    for pt in points:
        if not isinstance(pt, dict):
            raise ValueError("each test point must be a dict, got %r" % (pt,))
        cfg = pt.get("configuration")
        if not isinstance(cfg, str) or not cfg:
            raise ValueError(
                "test point configuration must be a non-empty string, got %r"
                % (cfg,)
            )
        for key in ("altitude", "speed"):
            val = pt.get(key)
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(
                    "test point %r %s must be numeric, got %r"
                    % (pt.get("id"), key, val)
                )
    order = {}
    for pt in points:
        cfg = pt["configuration"]
        if cfg not in order:
            order[cfg] = len(order)
    return sorted(
        points,
        key=lambda pt: (
            order[pt["configuration"]],
            pt["altitude"],
            pt["speed"],
        ),
    )


def steady_state_check(points, tolerances, observed):
    """Check every flown point against the steady state tolerance band.

    points is a list of point dicts as produced by build_test_matrix
    (each with a non-empty string "id" and numeric "altitude", "speed",
    and "weight" keys). tolerances is a dict with the "altitude",
    "speed", and "weight" keys, each a numeric value >= 0 (not bool).
    observed maps every point id to a dict with the same three keys
    holding the measured steady state values.

    A point is valid when each observed value lies within the tolerance
    band of its planned condition:
      |observed - planned| <= tolerance
    for altitude, speed, and weight.

    Returns a dict with:
      - "valid": ids of the valid points in point order
      - "invalid": ids of the invalid points in point order
      - "verdict": "all-valid" or "invalid-points"

    Raises ValueError on an empty or non-list points value, a non-dict
    point, a missing or non-string id, a duplicate id, a non-numeric or
    bool condition or tolerance, a negative tolerance, a missing
    tolerance key, an observation missing for a point, an observation
    for an unknown point id, or a non-dict or non-numeric reading.
    """
    if not isinstance(points, list) or len(points) == 0:
        raise ValueError("points must be a non-empty list, got %r" % (points,))
    for key in ("altitude", "speed", "weight"):
        if key not in tolerances:
            raise ValueError("tolerances missing required key %r" % (key,))
        tol = tolerances[key]
        if isinstance(tol, bool) or not isinstance(tol, (int, float)):
            raise ValueError(
                "tolerance %r must be numeric, got %r" % (key, tol)
            )
        if tol < 0:
            raise ValueError("tolerance %r must be >= 0, got %r" % (key, tol))
    if not isinstance(observed, dict):
        raise ValueError(
            "observed must be a dict mapping point ids to readings, got %r"
            % (observed,)
        )
    planned = {}
    for pt in points:
        if not isinstance(pt, dict):
            raise ValueError("each test point must be a dict, got %r" % (pt,))
        pid = pt.get("id")
        if not isinstance(pid, str) or not pid:
            raise ValueError(
                "test point id must be a non-empty string, got %r" % (pid,)
            )
        if pid in planned:
            raise ValueError("duplicate test point id %r" % (pid,))
        for key in ("altitude", "speed", "weight"):
            val = pt.get(key)
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(
                    "test point %r %s must be numeric, got %r"
                    % (pid, key, val)
                )
        planned[pid] = pt
    for pid in planned:
        if pid not in observed:
            raise ValueError(
                "observed has no reading for test point %r" % (pid,)
            )
    for pid, reading in observed.items():
        if pid not in planned:
            raise ValueError(
                "observed has a reading for unknown test point %r" % (pid,)
            )
        if not isinstance(reading, dict):
            raise ValueError(
                "observed reading for %r must be a dict, got %r"
                % (pid, reading)
            )
        for key in ("altitude", "speed", "weight"):
            val = reading.get(key)
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(
                    "observed %r %s must be numeric, got %r"
                    % (pid, key, val)
                )
    valid = []
    invalid = []
    for pid, pt in planned.items():
        ok = all(
            abs(observed[pid][key] - pt[key]) <= tolerances[key]
            for key in ("altitude", "speed", "weight")
        )
        if ok:
            valid.append(pid)
        else:
            invalid.append(pid)
    verdict = "all-valid" if not invalid else "invalid-points"
    return {"valid": valid, "invalid": invalid, "verdict": verdict}
