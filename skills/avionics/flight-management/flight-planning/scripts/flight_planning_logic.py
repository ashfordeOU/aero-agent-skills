#!/usr/bin/env python3
"""Flight management system flight planning logic (paraphrase).

Common-knowledge summary (standards-map.yaml, do-178c: proprietary RTCA,
summary only): a flight management system builds a flight plan as a
sequence of waypoints and legs, checks the vertical profile against
crossing constraints (floor and ceiling altitudes), and computes track
distance for fuel and time planning. The functions here are the
deterministic geometry and constraint checks behind that process.
"""

import math

EARTH_RADIUS_KM = 6371.0


def _validate_lat_lon(lat, lon):
    if not (-90.0 <= lat <= 90.0):
        raise ValueError("latitude out of range %r" % (lat,))
    if not (-180.0 <= lon <= 180.0):
        raise ValueError("longitude out of range %r" % (lon,))


def leg_distance_km(lat1, lon1, lat2, lon2):
    """Great-circle distance (km) between two waypoints (haversine)."""
    _validate_lat_lon(lat1, lon1)
    _validate_lat_lon(lat2, lon2)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2.0) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


def vertical_constraint_ok(planned_alt, floor, ceiling):
    """True when planned_alt (m) is within [floor, ceiling]; None = open."""
    if floor is not None and ceiling is not None and floor > ceiling:
        raise ValueError("floor %r above ceiling %r" % (floor, ceiling))
    if floor is not None and planned_alt < floor:
        return False
    if ceiling is not None and planned_alt > ceiling:
        return False
    return True


def total_distance_km(legs):
    """Total track distance (km) over (lat1, lon1, lat2, lon2) legs."""
    if not legs:
        raise ValueError("flight plan must have at least one leg")
    return sum(leg_distance_km(*leg) for leg in legs)


def flight_plan_ok(legs, constraints, planned_alt):
    """True when every leg is valid and the planned altitude meets every
    (lat1, lon1, lat2, lon2, floor, ceiling) constraint."""
    if len(legs) != len(constraints):
        raise ValueError("legs (%d) and constraints (%d) count mismatch"
                         % (len(legs), len(constraints)))
    for leg in legs:
        leg_distance_km(*leg)
    for c in constraints:
        if not vertical_constraint_ok(planned_alt, c[4], c[5]):
            return False
    return True
