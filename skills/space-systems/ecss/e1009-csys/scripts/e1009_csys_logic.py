#!/usr/bin/env python3
"""ECSS-E-ST-10C §5.4.2 coordinate system definition checks
(paraphrase, not copy).

Common-knowledge summary: a coordinate system consists of a reference
frame type (inertial, rotating, body-fixed, orbital, topocentric), a
coordinate representation (Cartesian x/y/z, spherical r/theta/phi,
cylindrical rho/phi/z), an origin definition, and per-axis direction
references; rotating, orbital, and topocentric frame types are
inherently time-dependent because their orientation relative to an
inertial frame changes over time; body-fixed frames are time-dependent
when the body manoeuvres or spins; inertial frames are treated as
time-independent for mission timescales. A frame is fully defined only
when every required coordinate label carries a non-empty direction
string, its origin is stated, and any parent-frame reference resolves
to a known frame in the registered set.

Stdlib only -- no third-party packages.
"""

FRAME_TYPES = frozenset({
    "INERTIAL",
    "ROTATING",
    "BODY_FIXED",
    "ORBITAL",
    "TOPOCENTRIC",
})

COORD_TYPES = frozenset({"CARTESIAN", "SPHERICAL", "CYLINDRICAL"})

REQUIRED_COORDS = {
    "CARTESIAN":   frozenset({"x", "y", "z"}),
    "SPHERICAL":   frozenset({"r", "theta", "phi"}),
    "CYLINDRICAL": frozenset({"rho", "phi", "z"}),
}

_INHERENTLY_TIME_DEPENDENT = frozenset({"ROTATING", "ORBITAL", "TOPOCENTRIC"})


class CoordSystemError(ValueError):
    """Raised when a coordinate system definition violates §5.4.2 rules."""


def define_coordinate_system(name, frame_type, coord_type, origin, axes,
                              time_dependent=None, parent_frame=None):
    """Validate and return an immutable coordinate system record as a dict.

    Parameters
    ----------
    name          : unique string identifier
    frame_type    : one of FRAME_TYPES
    coord_type    : one of COORD_TYPES
    origin        : non-empty human-readable origin definition
    axes          : dict mapping coordinate label to direction string
    time_dependent: bool override; None lets the frame type decide
    parent_frame  : name of parent frame, or None for a root frame

    Raises CoordSystemError on any validation failure.
    Returns a new dict -- never mutates the caller's axes mapping.
    """
    if not name or not name.strip():
        raise CoordSystemError("Coordinate system name must be non-empty.")

    if frame_type not in FRAME_TYPES:
        raise CoordSystemError(
            "Unknown frame type %r. Valid types: %s"
            % (frame_type, sorted(FRAME_TYPES))
        )

    if coord_type not in COORD_TYPES:
        raise CoordSystemError(
            "Unknown coordinate type %r. Valid types: %s"
            % (coord_type, sorted(COORD_TYPES))
        )

    if not origin or not origin.strip():
        raise CoordSystemError(
            "Origin must be defined for coordinate system %r." % name
        )

    required = REQUIRED_COORDS[coord_type]
    provided = frozenset(axes.keys())
    missing = required - provided
    if missing:
        raise CoordSystemError(
            "Missing axes %s for %s coordinate system %r."
            % (sorted(missing), coord_type, name)
        )

    empty_axes = sorted(ax for ax in required if not axes.get(ax, "").strip())
    if empty_axes:
        raise CoordSystemError(
            "Axes %s have no direction definition in coordinate system %r."
            % (empty_axes, name)
        )

    inherent = frame_type in _INHERENTLY_TIME_DEPENDENT
    if time_dependent is False and inherent:
        raise CoordSystemError(
            "Frame type %r is inherently time-dependent; "
            "time_dependent cannot be set to False." % frame_type
        )
    resolved_td = inherent if time_dependent is None else bool(time_dependent)

    return {
        "name": name,
        "frame_type": frame_type,
        "coord_type": coord_type,
        "origin": origin,
        "axes": dict(axes),
        "time_dependent": resolved_td,
        "parent_frame": parent_frame,
    }


def check_coordinates_definable(cs):
    """Check that every coordinate in the frame has an unambiguous definition.

    cs: a dict as returned by define_coordinate_system, or a partial dict
    for testing incomplete definitions.

    Returns (ok, issues) where issues is an empty list when ok is True.
    Does not mutate cs.
    """
    issues = []
    name = cs.get("name", "<unnamed>")
    coord_type = cs.get("coord_type", "")
    axes = cs.get("axes", {})

    if coord_type not in COORD_TYPES:
        issues.append(
            "Frame %r: unknown coordinate type %r." % (name, coord_type)
        )
        return False, issues

    required = REQUIRED_COORDS[coord_type]
    provided = frozenset(axes.keys())

    missing = required - provided
    if missing:
        issues.append(
            "Frame %r: axes %s are not defined." % (name, sorted(missing))
        )

    for ax in sorted(required & provided):
        if not axes[ax].strip():
            issues.append(
                "Frame %r: axis %r direction is empty (underdefined)." % (name, ax)
            )

    return len(issues) == 0, issues


def flag_time_dependent_frames(cs_list):
    """Return names of all time-dependent frames in cs_list."""
    return [cs["name"] for cs in cs_list if cs.get("time_dependent", False)]


def categorize_frames_by_time_dependence(cs_list):
    """Split frames into (time_dependent_names, time_invariant_names).

    Returns two lists; does not mutate cs_list.
    """
    time_dep = [cs["name"] for cs in cs_list if cs.get("time_dependent", False)]
    time_inv = [cs["name"] for cs in cs_list if not cs.get("time_dependent", False)]
    return time_dep, time_inv


def get_underdefined_frames(cs_list):
    """Return list of (name, issues) for every frame that fails the definability check."""
    result = []
    for cs in cs_list:
        ok, issues = check_coordinates_definable(cs)
        if not ok:
            result.append((cs["name"], issues))
    return result


def validate_parent_frame_chain(cs_list):
    """Check that every non-root frame references a known frame in cs_list.

    Returns list of (frame_name, unknown_parent) pairs for invalid references.
    Does not mutate cs_list.
    """
    known = {cs["name"] for cs in cs_list}
    return [
        (cs["name"], cs["parent_frame"])
        for cs in cs_list
        if cs.get("parent_frame") is not None and cs["parent_frame"] not in known
    ]


def summarize_registry(cs_list):
    """Produce a compliance summary for a collection of coordinate systems.

    Returns a new dict with counts and issue lists; does not mutate cs_list.
    """
    time_dep, time_inv = categorize_frames_by_time_dependence(cs_list)
    underdefined = get_underdefined_frames(cs_list)
    bad_parents = validate_parent_frame_chain(cs_list)

    return {
        "total": len(cs_list),
        "time_dependent_count": len(time_dep),
        "time_invariant_count": len(time_inv),
        "time_dependent_frames": time_dep,
        "time_invariant_frames": time_inv,
        "underdefined_count": len(underdefined),
        "underdefined_frames": [n for n, _ in underdefined],
        "bad_parent_count": len(bad_parents),
        "bad_parent_frames": bad_parents,
        "compliant": len(underdefined) == 0 and len(bad_parents) == 0,
    }
