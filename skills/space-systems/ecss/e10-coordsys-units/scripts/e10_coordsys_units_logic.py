#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.6.5 reference coordinate system and SI unit
consistency (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): at
system level, ECSS-E-ST-10C requires that reference coordinate systems
be applied per E-ST-10-09 and that SI units be used consistently across
the programme. E-ST-10-09 owns the detailed frame definitions,
notation, and Coordinate Systems Document (CSD) content (see the
sibling e1009-* leaves); this module implements the system-level
consistency check -- that every piece of engineering data uses a frame
drawn from the programme's approved (CSD) frame set and a unit
consistent with SI, or an explicitly documented exception.
"""

SI_UNITS = {
    "length": "m",
    "mass": "kg",
    "time": "s",
    "angle": "rad",
    "velocity": "m/s",
    "acceleration": "m/s^2",
    "force": "N",
    "temperature": "K",
    "pressure": "Pa",
    "frequency": "Hz",
    "angular_rate": "rad/s",
}


def canonical_unit(quantity_type):
    """SI unit for quantity_type. Raises ValueError for an unknown
    quantity type."""
    if quantity_type not in SI_UNITS:
        raise ValueError("unknown quantity type: %r" % (quantity_type,))
    return SI_UNITS[quantity_type]


def check_unit(quantity_type, unit, exception_documented=False):
    """True if unit is the canonical SI unit for quantity_type, or a
    documented non-SI exception per clause 5.6.5. Raises ValueError for
    an unknown quantity type."""
    expected = canonical_unit(quantity_type)
    if unit == expected:
        return True
    return bool(exception_documented)


def check_frame(frame, approved_frames):
    """True if frame is present in the programme's approved reference
    frame set (the Coordinate Systems Document per E-ST-10-09)."""
    return frame in approved_frames


def verify_data_item(item, approved_frames):
    """Consistency check for one engineering data item. Required keys:
    id, quantity_type, unit, frame; optional key: exception_documented
    (defaults False). Returns a list of violation tags ('unit' and/or
    'frame'); an empty list means the item is consistent. Raises
    ValueError if 'id' is missing or quantity_type is unknown."""
    if "id" not in item:
        raise ValueError("data item is missing an id")
    violations = []
    if not check_unit(item["quantity_type"], item["unit"], item.get("exception_documented", False)):
        violations.append("unit")
    if not check_frame(item["frame"], approved_frames):
        violations.append("frame")
    return violations


def audit_programme_data(items, approved_frames):
    """Consistency audit across a set of engineering data items. Returns
    a dict of item id -> violations list, containing only items with at
    least one violation, in input order. Raises ValueError on a
    duplicate item id."""
    seen_ids = set()
    report = {}
    for item in items:
        item_id = item.get("id")
        if item_id in seen_ids:
            raise ValueError("duplicate data item id: %r" % (item_id,))
        seen_ids.add(item_id)
        violations = verify_data_item(item, approved_frames)
        if violations:
            report[item_id] = violations
    return report


def missing_frame_definitions(used_frames, approved_frames):
    """Frames referenced in engineering data but absent from the
    approved (CSD) frame set -- flags a frame introduced outside the
    CSD control loop (E-ST-10-09 clause 5.2.2/5.2.3). Returns a sorted
    list."""
    return sorted(set(used_frames) - set(approved_frames))
