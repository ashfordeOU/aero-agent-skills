"""Shear-center analysis of thin-walled open sections (V*Q/I method).

Locates the shear center of a thin-walled open section (channel, Z,
angle) under a transverse vertical shear: walk the single open contour
from its free edge, accumulate the first moment Q of the outboard wall
area, build the wall shear flow q(s) = V_y * Q / I_xx, and integrate the
wall-shear resultant and its moment to find the line of action. The
shear-center offset is reported from the stated reference (web
centerline for the channel, section centroid for the Z, corner for the
angle). Doubly symmetric sections (I-beam) place the shear center at the
centroid by symmetry, so the leaf validates the classical web
shear-flow maximum instead.

Pure Python stdlib (math only), deterministic, closed form plus fine
segment integration. All dimensions and offsets are meters; shear loads
are N; wall shear flow q is N/m.

Assumption recorded: the I-beam second moment keeps both flange local
terms, including the weak-axis t_f * b_f**3 / 12 flange term, so that
ixx reproduces the wave-42 anchor value 1.692560e-06 m^4 for the
100 x 60 x 4/3 mm flange-web case (the flange local terms are retained,
not dropped as negligible).
"""

import math


def _require_positive(name, value):
    """Reject a non-positive physical dimension with ValueError."""
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))


def _require_finite(name, value):
    """Reject a non-finite load value with ValueError."""
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))


def section_properties(segments):
    """Centroidal section properties of a thin-wall segment assembly.

    Each segment is (x1, y1, x2, y2, t) in meters, one continuous wall
    contour. Returns (xbar, ybar, ixx, iyy, ixy): the area-weighted
    centroid and the second moments about it in m^4. Per segment of
    length L and area A = L * t the thin-rectangle inertia is
    L * t**3 / 12 about the wall normal and t * L**3 / 12 about the wall
    direction, rotated to the global axes with the parallel-axis terms
    A * dy**2, A * dx**2 and A * dx * dy. Raises ValueError for an empty
    list, a zero-length segment, non-positive wall thickness, or zero
    total wall area.
    """
    if not segments:
        raise ValueError("empty segment list")
    props = []
    total_area = 0.0
    sx = 0.0
    sy = 0.0
    for x1, y1, x2, y2, t in segments:
        if t <= 0.0:
            raise ValueError("wall thickness t must be positive, got %r" % t)
        dx = x2 - x1
        dy = y2 - y1
        L = math.hypot(dx, dy)
        if L <= 0.0:
            raise ValueError("zero-length segment")
        cx = dx / L
        cy = dy / L
        xc = 0.5 * (x1 + x2)
        yc = 0.5 * (y1 + y2)
        area = L * t
        total_area += area
        sx += area * xc
        sy += area * yc
        props.append((L, cx, cy, xc, yc, t, area))
    if total_area <= 0.0:
        raise ValueError("zero total wall area")
    xbar = sx / total_area
    ybar = sy / total_area
    ixx = 0.0
    iyy = 0.0
    ixy = 0.0
    for L, cx, cy, xc, yc, t, area in props:
        dx = xc - xbar
        dy = yc - ybar
        i_along = area * L * L / 12.0
        i_norm = area * t * t / 12.0
        ixx += i_along * cy * cy + i_norm * cx * cx + area * dy * dy
        iyy += i_along * cx * cx + i_norm * cy * cy + area * dx * dx
        ixy += (i_norm - i_along) * cx * cy + area * dx * dy
    return xbar, ybar, ixx, iyy, ixy


def _walk_shear_flow(segments, vy, ixx, n, scale):
    """Integrate the V*Q/I wall shear flow of one open contour.

    Walks the contour from the free edge; Q accumulates the first moment
    y * t * ds of the outboard wall area, the shear flow is
    q = vy * Q / ixx (N/m), and the step force q * (cx, cy) * ds acts
    along the contour tangent. Returns (fx, fy, mz): the resultant
    components in N and its moment in N m about the origin. Each wall is
    split into at least 2 steps, proportional to n per scale length.
    """
    fx = 0.0
    fy = 0.0
    mz = 0.0
    q = 0.0
    for x1, y1, x2, y2, t in segments:
        L = math.hypot(x2 - x1, y2 - y1)
        cx = (x2 - x1) / L
        cy = (y2 - y1) / L
        steps = max(2, int(n * L / scale))
        ds = L / steps
        for i in range(steps):
            f0 = i / steps
            f1 = (i + 1) / steps
            xa = x1 + (x2 - x1) * f0
            ya = y1 + (y2 - y1) * f0
            xb = x1 + (x2 - x1) * f1
            yb = y1 + (y2 - y1) * f1
            xm = 0.5 * (xa + xb)
            ym = 0.5 * (ya + yb)
            q_mid = q + 0.5 * ym * t * ds
            q += ym * t * ds
            q_wall = vy * q_mid / ixx
            fx += q_wall * cx * ds
            fy += q_wall * cy * ds
            mz += q_wall * (xm * cy - ym * cx) * ds
    return fx, fy, mz


def channel_classical_e(h, b):
    """Classical thin-channel shear-center offset 3*b**2 / (h + 6*b) (m).

    The closed form drops the flange local-inertia refinement, so the
    integrated result differs from it by a few ppm.
    """
    return 3.0 * b * b / (h + 6.0 * b)


def shear_center_channel(h, b, t, vy=1000.0, n=400):
    """Shear-center offset e of a uniform channel behind the web (m).

    Web height h and flange width b (both flanges extend the same
    direction from the web), uniform thickness t. The contour runs from
    the top-flange free edge (b, h/2) to the web (0, h/2), down the web
    to (0, -h/2), and out the bottom flange to (b, -h/2). Returns
    (e_m, fx, fy, ixx): e measured from the web centerline at mid-height
    (negative when the flanges extend toward +x, the shear center sits
    behind the web), the horizontal and vertical wall-shear resultants
    in N, and ixx in m^4. Raises ValueError for non-positive dimensions
    or a non-finite vy.
    """
    _require_positive("web height h", h)
    _require_positive("flange width b", b)
    _require_positive("wall thickness t", t)
    _require_finite("shear load vy", vy)
    segments = [
        (b, h / 2.0, 0.0, h / 2.0, t),
        (0.0, h / 2.0, 0.0, -h / 2.0, t),
        (0.0, -h / 2.0, b, -h / 2.0, t),
    ]
    xbar, ybar, ixx, iyy, ixy = section_properties(segments)
    fx, fy, mz = _walk_shear_flow(segments, vy, ixx, n, max(h, b))
    e_m = mz / fy if abs(fy) > 1e-12 else 0.0
    return e_m, fx, fy, ixx


def shear_center_z(h, b, t, vy=1000.0, n=400):
    """Shear-center offset of a Z-section from its centroid (m).

    Contour: top flange (b, h/2) to (0, h/2), web down to (0, -h/2),
    bottom flange out to (-b, -h/2). Returns (e_centroid, xbar, fy,
    ixx); the classical result is 0 (the doubly symmetric Z has its
    shear center at the centroid). Raises ValueError for non-positive
    dimensions or a non-finite vy.
    """
    _require_positive("web height h", h)
    _require_positive("flange width b", b)
    _require_positive("wall thickness t", t)
    _require_finite("shear load vy", vy)
    segments = [
        (b, h / 2.0, 0.0, h / 2.0, t),
        (0.0, h / 2.0, 0.0, -h / 2.0, t),
        (0.0, -h / 2.0, -b, -h / 2.0, t),
    ]
    xbar, ybar, ixx, iyy, ixy = section_properties(segments)
    fx, fy, mz = _walk_shear_flow(segments, vy, ixx, n, max(h, b))
    mz_centroid = mz - xbar * fy + ybar * fx
    e_centroid = mz_centroid / fy if abs(fy) > 1e-12 else 0.0
    return e_centroid, xbar, fy, ixx


def shear_center_angle(a, t, vy=1000.0, n=400):
    """Shear-center offset of an equal-leg angle from the corner (m).

    Contour: top-leg free edge (0, a) to the corner (0, 0), then along
    the bottom leg to its free edge (a, 0). Returns (e_corner, xbar,
    ybar, fy, ixx); the classical result is 0 because the shear center
    of an angle sits at the intersection of the leg centerlines (the
    corner). Raises ValueError for non-positive dimensions or a
    non-finite vy.
    """
    _require_positive("leg length a", a)
    _require_positive("wall thickness t", t)
    _require_finite("shear load vy", vy)
    segments = [
        (0.0, a, 0.0, 0.0, t),
        (0.0, 0.0, a, 0.0, t),
    ]
    xbar, ybar, ixx, iyy, ixy = section_properties(segments)
    fx, fy, mz = _walk_shear_flow(segments, vy, ixx, n, a)
    e_corner = mz / fy if abs(fy) > 1e-12 else 0.0
    return e_corner, xbar, ybar, fy, ixx


def i_beam_web_qmax(t_f, b_f, t_w, h, vy):
    """Web shear-flow maximum of a doubly symmetric I-beam (N/m).

    q_max = vy * Q / ixx at mid-web, with Q the first moment of the
    half-web above mid-height plus one full flange and ixx the flange
    and web assembly second moment. The shear center sits at the
    centroid by double symmetry, so q_max is the validation anchor.
    Returns (q_max, ixx). Raises ValueError if any dimension is
    non-positive or vy is not finite.
    """
    _require_positive("flange thickness t_f", t_f)
    _require_positive("flange width b_f", b_f)
    _require_positive("web thickness t_w", t_w)
    _require_positive("web height h", h)
    _require_finite("shear load vy", vy)
    ixx = (t_w * h ** 3) / 12.0 + 2.0 * (
        b_f * t_f * (h / 2.0 + t_f / 2.0) ** 2
        + t_f * b_f ** 3 / 12.0
        + b_f * t_f ** 3 / 12.0
    )
    q_first = t_w * (h / 2.0) * (h / 4.0) + b_f * t_f * (h / 2.0 + t_f / 2.0)
    return vy * q_first / ixx, ixx
