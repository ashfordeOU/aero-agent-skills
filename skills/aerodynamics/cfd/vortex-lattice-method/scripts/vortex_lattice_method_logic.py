#!/usr/bin/env python3
"""Vortex lattice method for straight trapezoidal wings (common knowledge).

Paraphrase of the classic elementary horseshoe vortex lattice method
(public-domain textbook material; no copied text): the half wing is
divided into spanwise panels, each carrying a horseshoe vortex whose
bound segment sits on the quarter-chord line and whose trailing legs
run downstream. The root-side leg of the root panel is dropped, the
mirror-image cancellation of the half-wing model. The no-penetration
boundary condition is enforced at three-quarter-chord control points,
giving a linear system whose unknowns are the panel circulations; the
solution yields the spanwise lift distribution, the downwash angles,
and the induced drag. Pure standard library, deterministic, offline.
"""

import math


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a):
    return math.sqrt(_dot(a, a))


def build_wing(span, root_chord, tip_chord, n_panels=8):
    """Half-wing horseshoe panel model of a straight trapezoidal wing.

    The wing lies in the z = 0 plane with the freestream along +x.
    span is the full wingspan, root_chord the chord at the centerline,
    tip_chord the chord at the wingtip. n_panels spanwise panels run
    from the root (y = 0) to the tip (y = span / 2). Returns a dict
    with 'panels' (each holding y_lo, y_hi, bound_start, bound_end,
    control, root_leg), 'area', 'aspect_ratio', and 'span'.
    """
    if span <= 0:
        raise ValueError("span must be > 0, got %r" % (span,))
    if root_chord <= 0:
        raise ValueError("root_chord must be > 0, got %r" % (root_chord,))
    if tip_chord <= 0:
        raise ValueError("tip_chord must be > 0, got %r" % (tip_chord,))
    if not isinstance(n_panels, int) or n_panels < 1:
        raise ValueError("n_panels must be an int >= 1, got %r" % (n_panels,))
    half_span = span / 2.0
    panels = []
    for k in range(n_panels):
        y_lo = k * half_span / n_panels
        y_hi = (k + 1) * half_span / n_panels
        y_c = 0.5 * (y_lo + y_hi)
        chord = root_chord + (tip_chord - root_chord) * (y_c / half_span)
        bound_start = (0.0, y_lo, 0.0)
        bound_end = (0.0, y_hi, 0.0)
        control = (chord / 2.0, y_c, 0.0)
        panels.append(
            {
                "y_lo": y_lo,
                "y_hi": y_hi,
                "bound_start": bound_start,
                "bound_end": bound_end,
                "control": control,
                "root_leg": y_lo > 0.0,
            }
        )
    area = span * (root_chord + tip_chord) / 2.0
    return {
        "panels": panels,
        "area": area,
        "aspect_ratio": span * span / area,
        "span": span,
    }


def segment_velocity(point, start, end, gamma):
    """Velocity induced at point by a straight vortex segment from start
    to end carrying circulation gamma (Biot-Savart, classic closed form).
    """
    r1 = _sub(point, start)
    r2 = _sub(point, end)
    cr = _cross(r1, r2)
    cross_sq = _dot(cr, cr)
    n1 = _norm(r1)
    n2 = _norm(r2)
    if n1 < 1e-12 or n2 < 1e-12:
        raise ValueError("point coincides with a segment endpoint")
    if cross_sq < 1e-24:
        raise ValueError("point lies on the vortex segment line")
    dot = _dot(r1, r2)
    factor = (n1 + n2 - dot * (1.0 / n1 + 1.0 / n2)) / cross_sq
    k = gamma / (4.0 * math.pi) * factor
    return (k * cr[0], k * cr[1], k * cr[2])


def trailing_leg_velocity(point, start, gamma, wake_dir=(1.0, 0.0, 0.0)):
    """Velocity induced by a semi-infinite vortex leg starting at start
    and extending to infinity along wake_dir (analytic Biot-Savart
    limit for a leg of circulation gamma).
    """
    r1 = _sub(point, start)
    cr = _cross(wake_dir, r1)
    cross_sq = _dot(cr, cr)
    n1 = _norm(r1)
    if n1 < 1e-12:
        raise ValueError("point coincides with the leg start")
    if cross_sq < 1e-24:
        raise ValueError("point lies on the trailing vortex leg")
    factor = (1.0 + _dot(r1, wake_dir) / n1) / cross_sq
    k = gamma / (4.0 * math.pi) * factor
    return (k * cr[0], k * cr[1], k * cr[2])


def horseshoe_velocity(point, bound_start, bound_end, gamma=1.0, root_leg=True):
    """Velocity induced by one horseshoe vortex: the bound segment from
    bound_start to bound_end plus two semi-infinite trailing legs. The
    bound_end-side leg trails downstream (+x) with circulation gamma;
    the bound_start-side leg trails upstream-equivalent (-x) so that
    the trailing sheet strength between adjacent panels is the bound
    circulation difference (filament continuity). root_leg=False drops
    the bound_start-side leg, the half-wing mirror cancellation.
    """
    v = segment_velocity(point, bound_start, bound_end, gamma)
    w = trailing_leg_velocity(point, bound_end, gamma, (1.0, 0.0, 0.0))
    v = (v[0] + w[0], v[1] + w[1], v[2] + w[2])
    if root_leg:
        w = trailing_leg_velocity(point, bound_start, gamma, (-1.0, 0.0, 0.0))
        v = (v[0] + w[0], v[1] + w[1], v[2] + w[2])
    return v


def panel_downwash(point, panel, gamma):
    """Downwash (z velocity) at point from one panel horseshoe."""
    return horseshoe_velocity(
        point, panel["bound_start"], panel["bound_end"], gamma, panel["root_leg"]
    )[2]


def influence_matrix(wing):
    """Influence coefficient matrix A with A[i][j] the downwash at the
    control point of panel i from a unit-circulation horseshoe on
    panel j."""
    return [
        [panel_downwash(p["control"], q, 1.0) for q in wing["panels"]]
        for p in wing["panels"]
    ]


def _solve_linear(A, b):
    """Gaussian elimination with partial pivoting (stdlib, exact)."""
    n = len(A)
    if n == 0:
        raise ValueError("empty system")
    if any(len(row) != n for row in A):
        raise ValueError("influence matrix must be square")
    if len(b) != n:
        raise ValueError("right-hand side length mismatch")
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[pivot] = M[pivot], M[col]
        pv = M[col][col]
        if abs(pv) < 1e-14:
            raise ValueError("singular influence matrix")
        for row in range(col + 1, n):
            f = M[row][col] / pv
            for c in range(col, n + 1):
                M[row][c] -= f * M[col][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = M[i][n] - sum(M[i][j] * x[j] for j in range(i + 1, n))
        x[i] = s / M[i][i]
    return x


def solve_circulations(wing, v_inf, alpha_deg):
    """Panel circulations satisfying the no-penetration condition
    w_induced = -v_inf * sin(alpha) at every control point."""
    if v_inf <= 0:
        raise ValueError("v_inf must be > 0, got %r" % (v_inf,))
    if abs(alpha_deg) >= 45.0:
        raise ValueError("alpha must satisfy |alpha| < 45 deg, got %r" % (alpha_deg,))
    A = influence_matrix(wing)
    rhs = [-v_inf * math.sin(math.radians(alpha_deg))] * len(wing["panels"])
    return _solve_linear(A, rhs)


def lift_distribution(wing, circulations, v_inf, rho=1.225):
    """Per-panel lift of the full wing (both halves) from the Kutta-
    Joukowski law L = rho * v_inf * gamma * span_extent."""
    if v_inf <= 0:
        raise ValueError("v_inf must be > 0, got %r" % (v_inf,))
    if rho <= 0:
        raise ValueError("rho must be > 0, got %r" % (rho,))
    if len(circulations) != len(wing["panels"]):
        raise ValueError("circulations length must match panel count")
    out = []
    for g, p in zip(circulations, wing["panels"]):
        out.append(2.0 * rho * v_inf * g * (p["y_hi"] - p["y_lo"]))
    return out


def downwash_angles(wing, circulations, v_inf):
    """Per-panel induced downwash angle (radians) at the bound vortex
    midpoint, from the trailing legs only (near-field estimate)."""
    if v_inf <= 0:
        raise ValueError("v_inf must be > 0, got %r" % (v_inf,))
    if len(circulations) != len(wing["panels"]):
        raise ValueError("circulations length must match panel count")
    angles = []
    for p in wing["panels"]:
        mid = (
            (p["bound_start"][0] + p["bound_end"][0]) / 2.0,
            (p["bound_start"][1] + p["bound_end"][1]) / 2.0,
            0.0,
        )
        w = 0.0
        for g, q in zip(circulations, wing["panels"]):
            w += trailing_leg_velocity(mid, q["bound_end"], g, (1.0, 0.0, 0.0))[2]
            if q["root_leg"]:
                w += trailing_leg_velocity(mid, q["bound_start"], g, (-1.0, 0.0, 0.0))[2]
        angles.append(-w / v_inf)
    return angles


def induced_drag_coefficient(wing, circulations, v_inf, rho=1.225):
    """Induced drag coefficient from the near-field estimate
    D_i = L_i * alpha_i summed over both halves."""
    if v_inf <= 0:
        raise ValueError("v_inf must be > 0, got %r" % (v_inf,))
    if rho <= 0:
        raise ValueError("rho must be > 0, got %r" % (rho,))
    lifts = lift_distribution(wing, circulations, v_inf, rho)
    angles = downwash_angles(wing, circulations, v_inf)
    drag = sum(l * a for l, a in zip(lifts, angles))
    q_inf = 0.5 * rho * v_inf * v_inf
    return drag / (q_inf * wing["area"])


def wing_coefficients(wing, v_inf, alpha_deg, rho=1.225):
    """Lift coefficient, induced drag coefficient, and span efficiency
    for the wing at angle of attack alpha_deg. span_efficiency is None
    when the induced drag vanishes (zero lift)."""
    circulations = solve_circulations(wing, v_inf, alpha_deg)
    q_inf = 0.5 * rho * v_inf * v_inf
    cl = sum(lift_distribution(wing, circulations, v_inf, rho)) / (q_inf * wing["area"])
    cdi = induced_drag_coefficient(wing, circulations, v_inf, rho)
    efficiency = None
    if cdi > 1e-12:
        efficiency = cl * cl / (math.pi * wing["aspect_ratio"] * cdi)
    return {
        "cl": cl,
        "cdi": cdi,
        "span_efficiency": efficiency,
        "circulations": circulations,
    }
