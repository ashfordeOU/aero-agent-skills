#!/usr/bin/env python3
"""Star tracker attitude determination logic (stdlib only).

Star identification and boresight geometry for an ADCS star tracker:
normalize catalog and measured unit vectors, compute the angular
separation theta = acos(dot(u, v)) between a measured centroid and a
catalog star, find the best catalog match inside the field of view,
and decide between lost in space and tracking mode. Paraphrase of the
standard star tracker methodology; ECSS is the pack's reference
standard (standards-map.yaml) and this logic is generic ADCS geometry,
not RTCA or SAE content.

Conventions: all vectors are 3D unit vectors. The field of view FOV
is a square angular window; a catalog star is inside it when its
separation from the measured centroid is within the FOV half-angle
fov/2. Angular separations are returned in degrees; the boresight
error is returned in arcseconds (1 degree = 3600 arcseconds).
"""

import math


def unit_vector(v):
    """Normalize a 3D vector to unit length; ValueError on zero.

    norm = sqrt(x^2 + y^2 + z^2); each component is divided by norm.
    """
    norm = math.sqrt(sum(c * c for c in v))
    if norm == 0.0:
        raise ValueError("zero vector has no direction")
    return tuple(c / norm for c in v)


def angular_separation(u, v):
    """Angular separation in degrees between unit vectors u and v.

    theta = acos(dot(u, v)) with the dot product clamped to [-1, 1]
    so floating point round-off cannot drive acos out of its domain.
    """
    dot = sum(a * b for a, b in zip(u, v))
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


def fov_half_angle(fov_deg):
    """Half-angle of the field of view: fov_deg / 2."""
    return fov_deg / 2.0


def identify_star(catalog, measured, fov_deg):
    """Match a measured centroid to the nearest catalog star in the FOV.

    catalog: iterable of (star_id, unit_vector) entries. measured: any
    nonzero 3D vector, normalized internally. Returns (star_id,
    separation_deg) for the catalog star with the smallest angular
    separation from the measured centroid when that separation is
    within the FOV half-angle; returns (None, None) when no catalog
    star is inside the field of view.
    """
    measured_u = unit_vector(measured)
    best_id = None
    best_sep = None
    for star_id, vec in catalog:
        sep = angular_separation(unit_vector(vec), measured_u)
        if best_sep is None or sep < best_sep:
            best_id = star_id
            best_sep = sep
    if best_sep is None or best_sep > fov_half_angle(fov_deg):
        return None, None
    return best_id, best_sep


def boresight_error(boresight, measured):
    """Pointing error in arcseconds between the boresight unit vector
    and a measured centroid unit vector.

    Cross-boresight pointing accuracy is bounded by this separation;
    1 degree = 3600 arcseconds.
    """
    return angular_separation(unit_vector(boresight), unit_vector(measured)) * 3600.0


def select_mode(has_prior, nearest_sep_deg, tracking_radius_deg):
    """Choose 'tracking' or 'lost-in-space' mode.

    Tracking mode is valid when a prior attitude exists and the nearest
    catalog match is within the tracking radius; otherwise the tracker
    must identify stars in lost in space mode against the full catalog.
    """
    if has_prior and nearest_sep_deg <= tracking_radius_deg:
        return "tracking"
    return "lost-in-space"
