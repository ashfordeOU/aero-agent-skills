"""Persistent position-based scheduling across successive orbits.

Anchor: ECSS-E-ST-70-41C clause 6.22.5 (persistent scheduling). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each scheduled activity: a unique request identifier, the angle
   from the ascending node it is released at, whether it persists past its
   own release, and how many orbits it is meant to survive.
2. Separate the persistent activities, which re-arm at the same angle on a
   later orbit, from the one-shot activities, which the schedule consumes at
   release.
3. Project the releases over a sweep of whole orbits, counting how often each
   activity fires and on which orbits.
4. Report the schedule that remains once the sweep ends, and the findings a
   persistent schedule earns: an activity that never fires inside the sweep,
   a repeat interval longer than the sweep, and a schedule whose residual
   occupancy has not fallen.
"""

__all__ = [
    "UNLIMITED_REPEATS",
    "normalise_activity",
    "load_schedule",
    "release_orbits",
    "release_count",
    "residual_schedule",
    "project_schedule_over_orbits",
]

# An activity declared with this repeat count persists for the whole sweep.
UNLIMITED_REPEATS = 0

DEGREES_PER_REVOLUTION = 360.0


def _require_non_negative_int(value, label):
    """Return value as a non-negative whole count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _require_positive_int(value, label):
    """Return value as a positive whole count."""
    value = _require_non_negative_int(value, label)
    if value == 0:
        raise ValueError("%s must be positive, got 0" % label)
    return value


def _require_angle(value, label):
    """Return an ascending-node angle inside one revolution."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    angle = float(value)
    if angle != angle or angle in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if angle < 0.0 or angle >= DEGREES_PER_REVOLUTION:
        raise ValueError(
            "%s %r falls outside one revolution from the ascending node"
            % (label, value)
        )
    return angle


def normalise_activity(activity, index):
    """Return one scheduled activity as a validated dict."""
    if not isinstance(activity, dict):
        raise ValueError("activity %d must be a mapping, got %r" % (index, activity))
    for key in ("request_id", "first_orbit", "angle_degrees", "persistent"):
        if key not in activity:
            raise ValueError("activity %d missing required key '%s'" % (index, key))
    request_id = activity["request_id"]
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("activity %d request_id must be a non-empty string" % index)
    persistent = activity["persistent"]
    if not isinstance(persistent, bool):
        raise ValueError("activity %d persistent must be a boolean" % index)

    orbit_interval = activity.get("orbit_interval", 1)
    repeats = activity.get("repeats", UNLIMITED_REPEATS)
    if persistent:
        orbit_interval = _require_positive_int(
            orbit_interval, "activity %d orbit_interval" % index
        )
        repeats = _require_non_negative_int(repeats, "activity %d repeats" % index)
    else:
        if activity.get("repeats", 1) not in (1, UNLIMITED_REPEATS):
            raise ValueError(
                "activity %d is one-shot; it cannot declare %r repeats"
                % (index, activity["repeats"])
            )
        orbit_interval = 0
        repeats = 1

    return {
        "request_id": request_id.strip(),
        "first_orbit": _require_non_negative_int(
            activity["first_orbit"], "activity %d first_orbit" % index
        ),
        "angle_degrees": _require_angle(
            activity["angle_degrees"], "activity %d angle_degrees" % index
        ),
        "persistent": persistent,
        "orbit_interval": orbit_interval,
        "repeats": repeats,
    }


def load_schedule(activities):
    """Return the activities validated and ordered by first orbit then angle."""
    if not isinstance(activities, (list, tuple)):
        raise ValueError("activities must be a list or tuple")
    loaded = [normalise_activity(item, i) for i, item in enumerate(activities)]
    seen = set()
    for item in loaded:
        if item["request_id"] in seen:
            raise ValueError(
                "request identifier '%s' appears more than once in the schedule"
                % item["request_id"]
            )
        seen.add(item["request_id"])
    loaded.sort(key=lambda a: (a["first_orbit"], a["angle_degrees"], a["request_id"]))
    return tuple(loaded)


def release_orbits(activity, start_orbit, orbit_count):
    """Return the orbits inside the sweep on which this activity releases."""
    start = _require_non_negative_int(start_orbit, "start_orbit")
    count = _require_positive_int(orbit_count, "orbit_count")
    last = start + count - 1

    first = activity["first_orbit"]
    if first > last:
        return ()
    if not activity["persistent"]:
        return (first,) if first >= start else ()

    orbits = []
    orbit = first
    interval = activity["orbit_interval"]
    limit = activity["repeats"]
    fired = 0
    while orbit <= last:
        if limit != UNLIMITED_REPEATS and fired >= limit:
            break
        if orbit >= start:
            orbits.append(orbit)
        fired += 1
        orbit += interval
    return tuple(orbits)


def release_count(activity, start_orbit, orbit_count):
    """Return how many times this activity releases inside the sweep."""
    return len(release_orbits(activity, start_orbit, orbit_count))


def residual_schedule(activities, start_orbit, orbit_count):
    """Return the request identifiers still held once the sweep has ended."""
    start = _require_non_negative_int(start_orbit, "start_orbit")
    count = _require_positive_int(orbit_count, "orbit_count")
    last = start + count - 1
    remaining = []
    for activity in activities:
        if not activity["persistent"]:
            # A one-shot entry is consumed by its own release.
            if activity["first_orbit"] > last:
                remaining.append(activity["request_id"])
            continue
        limit = activity["repeats"]
        if limit == UNLIMITED_REPEATS:
            remaining.append(activity["request_id"])
            continue
        fired_before_sweep_end = 0
        orbit = activity["first_orbit"]
        while orbit <= last and fired_before_sweep_end < limit:
            fired_before_sweep_end += 1
            orbit += activity["orbit_interval"]
        if fired_before_sweep_end < limit:
            remaining.append(activity["request_id"])
    return tuple(sorted(remaining))


def project_schedule_over_orbits(spec):
    """Project a clause 6.22.5 persistent schedule over a sweep of orbits.

    spec keys: activities, start_orbit, orbit_count.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("activities", "start_orbit", "orbit_count"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    loaded = load_schedule(spec["activities"])
    if not loaded:
        raise ValueError("a schedule projection needs at least one activity")
    start = _require_non_negative_int(spec["start_orbit"], "start_orbit")
    count = _require_positive_int(spec["orbit_count"], "orbit_count")
    last = start + count - 1

    releases = {}
    findings = []
    for activity in loaded:
        orbits = release_orbits(activity, start, count)
        releases[activity["request_id"]] = orbits
        if not orbits:
            findings.append(
                "activity '%s' never releases between orbit %d and orbit %d"
                % (activity["request_id"], start, last)
            )
        elif activity["persistent"] and activity["orbit_interval"] > count:
            findings.append(
                "activity '%s' repeats every %d orbits, longer than the %d orbit "
                "sweep" % (activity["request_id"], activity["orbit_interval"], count)
            )

    remaining = residual_schedule(loaded, start, count)
    persistent_ids = tuple(a["request_id"] for a in loaded if a["persistent"])
    one_shot_ids = tuple(a["request_id"] for a in loaded if not a["persistent"])

    return {
        "start_orbit": start,
        "last_orbit": last,
        "orbit_count": count,
        "persistent_activities": persistent_ids,
        "one_shot_activities": one_shot_ids,
        "releases": releases,
        "total_releases": sum(len(v) for v in releases.values()),
        "residual_schedule": remaining,
        "residual_occupancy": len(remaining),
        "schedule_drains": len(remaining) == 0,
        "findings": findings,
    }
