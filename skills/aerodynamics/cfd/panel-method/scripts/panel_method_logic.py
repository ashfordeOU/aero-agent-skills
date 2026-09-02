#!/usr/bin/env python3
"""Surface panel method logic for incompressible potential flow.

Common-knowledge low-order panel method methodology (standards-map.yaml,
naca-tr-824: public domain reference data only): a closed body is
discretized into flat panels, and constant-strength singularity sheets
on those panels satisfy the potential-flow boundary condition at each
panel control point. The Neumann form (source panels) enforces zero
normal velocity through the surface: sum_j A_ij sigma_j =
-(V_inf dot n_i). The Dirichlet form (doublet panels) enforces zero
interior velocity potential: sum_j D_ij mu_j = -phi_inf_i. Lifting
flows fix the trailing-edge circulation with the Kutta condition, which
requires equal tangential velocities at the two trailing-edge panels.
Surface pressure comes from the Bernoulli relation for incompressible
potential flow, Cp = 1 - (V/V_inf)^2, and integrates to the force
coefficients. The sphere is the analytic validation anchor for 3D body
panel codes: Cp = 1 - (9/4) sin^2(theta), source strength 2 V_inf
cos(theta). All inputs are SI: meters, m/s, m^2/s.

Conventions: body points are ordered counter-clockwise, the last point
equals the first (closed polygon), and panel normals point outward.
"""

import math


def _require_panels(panels):
    """Return the panel record list after validating the panels dict."""
    if not isinstance(panels, dict):
        raise ValueError("panels must be a dict from build_panels, got %r" % (panels,))
    records = panels.get("panels")
    if not isinstance(records, list) or len(records) < 3:
        raise ValueError("panels must hold at least 3 panel records")
    return records


def build_panels(points):
    """Build flat panel geometry from a closed counter-clockwise point list.

    points is a list of (x, y) tuples with the last point equal to the
    first. Each panel runs from points[j] to points[j+1] and carries its
    midpoint, length, outward unit normal, unit tangent, and angle. The
    signed area is positive for counter-clockwise ordering. Returns a
    dict with 'panels' (list of dicts) and 'signed_area'. Raises
    ValueError when there are fewer than 3 panels, the polygon is not
    closed, a panel has zero length, or the ordering is clockwise.
    """
    if not isinstance(points, (list, tuple)) or len(points) < 4:
        raise ValueError("points must be a closed list with at least 4 points")
    first = points[0]
    last = points[-1]
    if abs(first[0] - last[0]) > 1e-12 or abs(first[1] - last[1]) > 1e-12:
        raise ValueError("points must be closed: first point must equal last point")
    records = []
    for j in range(len(points) - 1):
        x1, y1 = points[j]
        x2, y2 = points[j + 1]
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length <= 1e-15:
            raise ValueError("panel %d has zero length" % j)
        tx = dx / length
        ty = dy / length
        # Outward normal for counter-clockwise ordering.
        nx = dy / length
        ny = -dx / length
        records.append(
            {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "mid_x": 0.5 * (x1 + x2),
                "mid_y": 0.5 * (y1 + y2),
                "length": length,
                "tx": tx,
                "ty": ty,
                "nx": nx,
                "ny": ny,
                "angle": math.atan2(ty, tx),
            }
        )
    area = 0.0
    for j in range(len(points) - 1):
        x1, y1 = points[j]
        x2, y2 = points[j + 1]
        area += x1 * y2 - x2 * y1
    signed_area = 0.5 * area
    if signed_area <= 0.0:
        raise ValueError("points must be ordered counter-clockwise (signed area > 0)")
    return {"panels": records, "signed_area": signed_area}


def _source_velocity_at(x, y, panel):
    """Velocity at (x, y) due to a unit-strength source panel, in global axes.

    Panel-local tangential and normal velocities of a constant source
    sheet from s=0 to s=l with the point at (s, n):
    V_s = (1/4*pi) ln[(s^2 + n^2) / ((s-l)^2 + n^2)]
    V_n = (1/2*pi) (atan2(n, s-l) - atan2(n, s))
    Returns (vx, vy).
    """
    s = (x - panel["x1"]) * panel["tx"] + (y - panel["y1"]) * panel["ty"]
    n = (x - panel["x1"]) * panel["nx"] + (y - panel["y1"]) * panel["ny"]
    l = panel["length"]
    s2 = s * s
    n2 = n * n
    denom = (s - l) * (s - l) + n2
    if denom <= 0.0 or (s2 + n2) <= 0.0:
        # On the panel itself the tangential term is zero by symmetry.
        vs = 0.0
    else:
        vs = (1.0 / (4.0 * math.pi)) * math.log((s2 + n2) / denom)
    vn = (1.0 / (2.0 * math.pi)) * (
        math.atan2(n, s - l) - math.atan2(n, s)
    )
    return vs * panel["tx"] + vn * panel["nx"], vs * panel["ty"] + vn * panel["ny"]


def source_influence_matrix(panels):
    """Neumann normal-velocity influence matrix of unit source panels.

    A[i][j] is the outward normal velocity at control point i induced by
    a unit-strength source panel j. The diagonal self-influence of a
    flat source sheet at its own control point is 0.5. Returns a list of
    rows. Raises ValueError on an invalid panels dict.
    """
    records = _require_panels(panels)
    n = len(records)
    a = []
    for i in range(n):
        row = []
        pi = records[i]
        for j in range(n):
            if i == j:
                row.append(0.5)
            else:
                pj = records[j]
                vx, vy = _source_velocity_at(pi["mid_x"], pi["mid_y"], pj)
                row.append(vx * pi["nx"] + vy * pi["ny"])
        a.append(row)
    return a


def tangent_influence_matrix(panels):
    """Tangential-velocity influence matrix of unit source panels.

    B[i][j] is the velocity at control point i, induced by a unit source
    panel j, projected on panel i's tangent. The diagonal self-influence
    of a flat source sheet at its own control point is 0. Returns a list
    of rows. Raises ValueError on an invalid panels dict.
    """
    records = _require_panels(panels)
    n = len(records)
    b = []
    for i in range(n):
        row = []
        pi = records[i]
        for j in range(n):
            if i == j:
                row.append(0.0)
            else:
                pj = records[j]
                vx, vy = _source_velocity_at(pi["mid_x"], pi["mid_y"], pj)
                row.append(vx * pi["tx"] + vy * pi["ty"])
        b.append(row)
    return b


def solve_linear_system(matrix, rhs):
    """Solve matrix * x = rhs with Gaussian elimination and partial pivoting.

    Returns the solution list. Raises ValueError when the matrix is
    singular or the rhs length mismatches the matrix size.
    """
    n = len(matrix)
    if n == 0:
        raise ValueError("matrix must be non-empty")
    if len(rhs) != n:
        raise ValueError("rhs length %d != matrix size %d" % (len(rhs), n))
    aug = [list(row) + [rhs[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-14:
            raise ValueError("matrix is singular at column %d" % col)
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        pivot_val = aug[col][col]
        for c in range(col, n + 1):
            aug[col][c] /= pivot_val
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor == 0.0:
                continue
            for c in range(col, n + 1):
                aug[r][c] -= factor * aug[col][c]
    return [aug[i][n] for i in range(n)]


def neumann_source_solution(panels, v_inf_x, v_inf_y):
    """Source strengths for a non-lifting body with the Neumann condition.

    Solves sum_j A_ij sigma_j = -(V_inf dot n_i) for the constant source
    strength on every panel. Returns the list of source strengths.
    Raises ValueError on invalid panels or a zero freestream.
    """
    records = _require_panels(panels)
    if math.hypot(v_inf_x, v_inf_y) <= 0.0:
        raise ValueError("freestream speed must be > 0")
    a = source_influence_matrix(panels)
    rhs = [
        -(v_inf_x * p["nx"] + v_inf_y * p["ny"]) for p in records
    ]
    return solve_linear_system(a, rhs)


def surface_velocity_and_cp(panels, source_strengths, v_inf_x, v_inf_y):
    """Tangential surface velocities and pressure coefficients.

    V_t_i = V_inf dot t_i + sum_j sigma_j B_ij, Cp_i = 1 - (V_t/V_inf)^2.
    Returns a list of dicts with 'velocity' and 'cp' per panel. Raises
    ValueError when the strengths count mismatches the panel count or
    the freestream is zero.
    """
    records = _require_panels(panels)
    v_inf = math.hypot(v_inf_x, v_inf_y)
    if v_inf <= 0.0:
        raise ValueError("freestream speed must be > 0")
    if len(source_strengths) != len(records):
        raise ValueError(
            "source_strengths length %d != panel count %d"
            % (len(source_strengths), len(records))
        )
    b = tangent_influence_matrix(panels)
    out = []
    for i, p in enumerate(records):
        vt = v_inf_x * p["tx"] + v_inf_y * p["ty"]
        for j in range(len(records)):
            vt += source_strengths[j] * b[i][j]
        out.append({"velocity": vt, "cp": 1.0 - (vt / v_inf) ** 2})
    return out


def force_coefficients(panels, cp_values, chord):
    """Lift and drag coefficients from the surface pressure integral.

    c_l = -(1/chord) sum Cp_i l_i n_y_i, c_d = -(1/chord) sum Cp_i l_i
    n_x_i over the closed body. Returns a dict with 'cl' and 'cd'.
    Raises ValueError on an invalid panels dict, a mismatched cp list,
    or a non-positive chord.
    """
    records = _require_panels(panels)
    if chord <= 0.0:
        raise ValueError("chord must be > 0, got %r" % (chord,))
    if len(cp_values) != len(records):
        raise ValueError(
            "cp_values length %d != panel count %d" % (len(cp_values), len(records))
        )
    cl = 0.0
    cd = 0.0
    for p, cp in zip(records, cp_values):
        cl -= cp * p["length"] * p["ny"]
        cd -= cp * p["length"] * p["nx"]
    return {"cl": cl / chord, "cd": cd / chord}


def dirichlet_doublet_matrix(panels):
    """Doublet potential influence matrix for the Dirichlet condition.

    D[i][j] is the velocity potential at control point i induced by a
    unit-strength doublet panel j, phi_d = (1/2*pi) times the signed
    angle the panel subtends at the control point, computed from the
    cross and dot products of the endpoint vectors so no branch cut is
    crossed. The diagonal self-influence is the half-space solid angle
    0.5 of a sheet at its own surface point. Returns a list of rows.
    Raises ValueError on an invalid panels dict.
    """
    records = _require_panels(panels)
    n = len(records)
    d = []
    for i in range(n):
        row = []
        pi = records[i]
        for j in range(n):
            if i == j:
                row.append(0.5)
            else:
                pj = records[j]
                ax = pj["x1"] - pi["mid_x"]
                ay = pj["y1"] - pi["mid_y"]
                bx = pj["x2"] - pi["mid_x"]
                by = pj["y2"] - pi["mid_y"]
                cross = ax * by - ay * bx
                dot = ax * bx + ay * by
                row.append(math.atan2(cross, dot) / (2.0 * math.pi))
        d.append(row)
    return d


def dirichlet_doublet_solution(panels, v_inf_x, v_inf_y):
    """Doublet strengths for a closed body with the Dirichlet condition.

    The doublets enforce zero interior velocity potential,
    sum_j D_ij mu_j = -phi_inf_i with phi_inf = V_inf dot r, the
    freestream potential at each control point. The doublet strength
    equals the surface velocity potential, so the surface velocity
    follows from d(mu)/ds. Returns the list of doublet strengths.
    Raises ValueError on invalid panels or a zero freestream.
    """
    records = _require_panels(panels)
    if math.hypot(v_inf_x, v_inf_y) <= 0.0:
        raise ValueError("freestream speed must be > 0")
    d = dirichlet_doublet_matrix(panels)
    rhs = [
        -(v_inf_x * p["mid_x"] + v_inf_y * p["mid_y"]) for p in records
    ]
    return solve_linear_system(d, rhs)


def surface_velocity_from_doublets(panels, doublet_strengths):
    """Tangential surface velocities from a doublet distribution.

    In the Dirichlet formulation the doublet strength equals the
    surface velocity potential, so V_t = -d(mu)/ds with the derivative
    taken as a cyclic central difference along the surface. Returns a
    list of velocities. Raises ValueError on a mismatched strengths
    count.
    """
    records = _require_panels(panels)
    if len(doublet_strengths) != len(records):
        raise ValueError(
            "doublet_strengths length %d != panel count %d"
            % (len(doublet_strengths), len(records))
        )
    n = len(records)
    out = []
    for i, p in enumerate(records):
        mu_prev = doublet_strengths[(i - 1) % n]
        mu_next = doublet_strengths[(i + 1) % n]
        arc = records[(i - 1) % n]["length"] + p["length"]
        dmu_ds = (mu_next - mu_prev) / arc
        out.append(-dmu_ds)
    return out


def kutta_condition_check(v_upper_te, v_lower_te, tol=1e-9):
    """Check the Kutta condition at a trailing edge.

    The Kutta condition requires the tangential velocities on the upper
    and lower trailing-edge panels to be equal. Returns a dict with
    'satisfied', 'velocity_jump' (lower minus upper), and
    'equalized_velocity' (the mean the Kutta condition enforces). Raises
    ValueError when tol is negative.
    """
    if tol < 0.0:
        raise ValueError("tol must be >= 0, got %r" % (tol,))
    jump = v_lower_te - v_upper_te
    return {
        "satisfied": abs(jump) <= tol,
        "velocity_jump": jump,
        "equalized_velocity": 0.5 * (v_upper_te + v_lower_te),
    }


def flat_plate_circulation(alpha_rad, chord, v_inf):
    """Circulation of a flat plate at angle of attack (thin-airfoil result).

    Gamma = pi * chord * V_inf * sin(alpha). This is the circulation the
    Kutta condition fixes for a sharp trailing edge. Raises ValueError
    when chord or v_inf is not positive.
    """
    if chord <= 0.0:
        raise ValueError("chord must be > 0, got %r" % (chord,))
    if v_inf <= 0.0:
        raise ValueError("v_inf must be > 0, got %r" % (v_inf,))
    return math.pi * chord * v_inf * math.sin(alpha_rad)


def cl_from_circulation(circulation, chord, v_inf):
    """Lift coefficient from the Kutta-Joukowski circulation.

    c_l = 2 * Gamma / (chord * V_inf). Raises ValueError when chord or
    v_inf is not positive.
    """
    if chord <= 0.0:
        raise ValueError("chord must be > 0, got %r" % (chord,))
    if v_inf <= 0.0:
        raise ValueError("v_inf must be > 0, got %r" % (v_inf,))
    return 2.0 * circulation / (chord * v_inf)


def sphere_potential_flow_cp(theta_deg):
    """Analytic pressure coefficient on a sphere in uniform flow.

    Cp = 1 - (9/4) sin^2(theta) with theta the polar angle from the
    stagnation point. The validation anchor for 3D source panel codes.
    Raises ValueError when theta_deg is outside [0, 180].
    """
    if not 0.0 <= theta_deg <= 180.0:
        raise ValueError("theta_deg must be in [0, 180], got %r" % (theta_deg,))
    theta = math.radians(theta_deg)
    return 1.0 - 2.25 * math.sin(theta) ** 2


def sphere_source_strength(theta_deg, v_inf):
    """Analytic source strength on a sphere for 3D panel code validation.

    sigma = 2 * V_inf * cos(theta). Raises ValueError when theta_deg is
    outside [0, 180] or v_inf is not positive.
    """
    if not 0.0 <= theta_deg <= 180.0:
        raise ValueError("theta_deg must be in [0, 180], got %r" % (theta_deg,))
    if v_inf <= 0.0:
        raise ValueError("v_inf must be > 0, got %r" % (v_inf,))
    return 2.0 * v_inf * math.cos(math.radians(theta_deg))


def quad_panel_properties(vertices):
    """Area, centroid, and unit normal of a planar 3D quadrilateral panel.

    vertices is a list of four (x, y, z) tuples ordered around the
    panel; the normal follows the right-hand rule of that ordering.
    Returns a dict with 'area', 'centroid', and 'normal'. Raises
    ValueError when there are not exactly 4 vertices or the panel is
    degenerate (zero area).
    """
    if not isinstance(vertices, (list, tuple)) or len(vertices) != 4:
        raise ValueError("vertices must hold exactly 4 (x, y, z) tuples")
    d1 = [
        vertices[2][k] - vertices[0][k] for k in range(3)
    ]
    d2 = [
        vertices[3][k] - vertices[1][k] for k in range(3)
    ]
    cross = [
        d1[1] * d2[2] - d1[2] * d2[1],
        d1[2] * d2[0] - d1[0] * d2[2],
        d1[0] * d2[1] - d1[1] * d2[0],
    ]
    mag = math.sqrt(cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2)
    if mag <= 1e-15:
        raise ValueError("quad panel is degenerate (zero area)")
    centroid = [
        sum(vertices[k][i] for k in range(4)) / 4.0 for i in range(3)
    ]
    return {
        "area": 0.5 * mag,
        "centroid": centroid,
        "normal": [cross[0] / mag, cross[1] / mag, cross[2] / mag],
    }
