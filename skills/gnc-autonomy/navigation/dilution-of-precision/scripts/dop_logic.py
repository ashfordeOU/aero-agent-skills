#!/usr/bin/env python3
"""Dilution of precision (DOP) logic for GPS/GNSS (stdlib only).

Position accuracy from satellite geometry. The receiver and the visible
satellites form a geometry problem: with N line-of-sight unit vectors
(east, north, up components in a local ENU frame), the N x 4 geometry
matrix H has one row [e, n, u, 1] per satellite. The extra unit column
carries the receiver clock bias, which is solved together with the
three position components.

The normal matrix A = H^T H is 4 x 4; its inverse
G = (H^T H)^-1 maps pseudorange error variance onto the state
covariance. The dilution of precision values are the square roots of
diagonal sums of G:

  gdop = sqrt(g00 + g11 + g22 + g33)   total (position + time)
  pdop = sqrt(g00 + g11 + g22)         position
  hdop = sqrt(g00 + g11)               horizontal
  vdop = sqrt(g22)                     vertical
  tdop = sqrt(g33)                     time

A measurement with pseudorange error standard deviation sigma then
gives a position error standard deviation of pdop * sigma. The inverse
is computed by Gauss-Jordan elimination with partial pivoting, so the
module has no dependency beyond the standard library.

Satellites below a visibility mask (elevation mask) are excluded
before forming H: their signals travel through more atmosphere and
carry larger errors. Satellite selection picks the k-satellite subset
with the best geometry, here the lowest PDOP, by exhaustive search
over combinations (k is small in practice).

Conventions: unit vectors are (east, north, up) in a local ENU frame;
elevation = asin(up). Angles leave and enter as radians inside the
module except the mask, which is in degrees.
"""

import itertools
import math


def _normalize(v):
    """Return v as a unit 3-vector, raising ValueError when degenerate."""
    if len(v) != 3:
        raise ValueError(
            "each satellite unit vector needs 3 components (e, n, u): got %d" % len(v)
        )
    norm = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if norm <= 0.0:
        raise ValueError("satellite unit vector has zero length")
    return (v[0] / norm, v[1] / norm, v[2] / norm)


def geometry_matrix(unit_vectors):
    """Build the N x 4 geometry matrix H from satellite unit vectors.

    Row i is [e, n, u, 1] for the i-th satellite. At least 4 satellites
    are required so that the 4 unknowns (3 position + 1 clock) are
    observable. Raises ValueError when fewer than 4 satellites are
    given or a vector is degenerate.
    """
    vecs = [_normalize(v) for v in unit_vectors]
    if len(vecs) < 4:
        raise ValueError(
            "need at least 4 satellites for a DOP estimate: got %d" % len(vecs)
        )
    return [[v[0], v[1], v[2], 1.0] for v in vecs]


def normal_matrix(h):
    """Normal matrix A = H^T H (4 x 4)."""
    a = [[0.0] * 4 for _ in range(4)]
    for row in h:
        for i in range(4):
            ri = row[i]
            for j in range(4):
                a[i][j] += ri * row[j]
    return a


def invert_4x4(a):
    """Invert a 4 x 4 matrix by Gauss-Jordan with partial pivoting.

    Returns the inverse as a list of rows, or None when the matrix is
    numerically singular (no pivot above the tolerance).
    """
    n = 4
    m = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-12:
            return None
        if pivot != col:
            m[col], m[pivot] = m[pivot], m[col]
        scale = m[col][col]
        for j in range(2 * n):
            m[col][j] /= scale
        for r in range(n):
            if r == col:
                continue
            factor = m[r][col]
            if factor != 0.0:
                for j in range(2 * n):
                    m[r][j] -= factor * m[col][j]
    return [row[n:] for row in m]


def compute_dops(unit_vectors):
    """All DOP values for the given satellite unit vectors.

    Returns a dict with keys gdop, pdop, hdop, vdop, tdop. Raises
    ValueError when fewer than 4 satellites are given or the geometry
    is singular (satellites collinear in space-time, e.g. all at the
    same azimuth).
    """
    h = geometry_matrix(unit_vectors)
    g = invert_4x4(normal_matrix(h))
    if g is None:
        raise ValueError(
            "singular satellite geometry: the normal matrix cannot be inverted"
        )
    g00, g11, g22, g33 = g[0][0], g[1][1], g[2][2], g[3][3]
    return {
        "gdop": math.sqrt(g00 + g11 + g22 + g33),
        "pdop": math.sqrt(g00 + g11 + g22),
        "hdop": math.sqrt(g00 + g11),
        "vdop": math.sqrt(g22),
        "tdop": math.sqrt(g33),
    }


def elevation_deg(unit_vector):
    """Elevation angle in degrees above the local horizon.

    Uses the up component of the (east, north, up) unit vector:
    elevation = asin(up).
    """
    v = _normalize(unit_vector)
    return math.degrees(math.asin(max(-1.0, min(1.0, v[2]))))


def apply_elevation_mask(unit_vectors, mask_deg=0.0):
    """Keep only satellites at or above the visibility mask.

    The mask (elevation mask) is a minimum elevation angle in degrees;
    satellites below it are excluded because their pseudoranges carry
    larger atmospheric errors. Raises ValueError when the mask is
    outside [-90, 90] degrees.
    """
    if mask_deg < -90.0 or mask_deg > 90.0:
        raise ValueError("elevation mask must be within [-90, 90] degrees")
    return [v for v in unit_vectors if elevation_deg(v) >= mask_deg]


def select_best_subset(unit_vectors, k, mask_deg=None):
    """Select the k-satellite subset with the lowest PDOP.

    Optionally applies the elevation mask first. Exhaustive search over
    combinations; singular subsets are skipped. Returns (best_subset,
    best_pdop). Raises ValueError when k < 4, when k exceeds the number
    of (visible) satellites, or when no usable subset exists.
    """
    pool = (
        apply_elevation_mask(unit_vectors, mask_deg)
        if mask_deg is not None
        else list(unit_vectors)
    )
    if k < 4:
        raise ValueError("need at least 4 satellites in the subset: got %d" % k)
    if k > len(pool):
        raise ValueError(
            "cannot select %d satellites from %d available" % (k, len(pool))
        )
    best = None
    best_pdop = None
    for combo in itertools.combinations(pool, k):
        try:
            pdop = compute_dops(list(combo))["pdop"]
        except ValueError:
            continue  # singular subset, not a candidate
        if best_pdop is None or pdop < best_pdop:
            best_pdop = pdop
            best = combo
    if best is None:
        raise ValueError("no non-singular %d-satellite subset available" % k)
    return list(best), best_pdop


def position_error_std(unit_vectors, uere):
    """1-sigma position error: pdop * uere.

    uere is the user equivalent range error (pseudorange noise
    standard deviation, in the same units as the desired position
    error). Raises ValueError for a negative uere.
    """
    if uere < 0.0:
        raise ValueError("uere must be non-negative")
    return compute_dops(unit_vectors)["pdop"] * uere
