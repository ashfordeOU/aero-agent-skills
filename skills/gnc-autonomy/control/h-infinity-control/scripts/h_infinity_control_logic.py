"""H-infinity mixed-sensitivity norm review of a SISO feedback loop.

Pure stdlib (math only), deterministic, no RNG, closed form. Given the
plant G, a candidate controller K and the sensitivity weight W1 and
control-effort weight W2, the module assembles the closed-loop channels
of L = G K over the characteristic polynomial, checks strict stability
by the Routh-Hurwitz first-column test, and computes the H-infinity
norms of the weighted channels by gamma iteration over the imaginary
axis: every interior peak of |H(jw)|^2 sits at a real root x = w^2 >= 0
of the stationary equation P(x) = A'(x)B(x) - A(x)B'(x) = 0, where A
and B are the hermitian squares of the numerator and denominator. The
norm is the square root of the largest of the DC magnitude, the
interior peak magnitudes and the high-frequency limit. See SKILL.md
Domain quick reference for the defining relations.

No controller is synthesized here: the two-Riccati H-infinity
controller synthesis side of the method, structured uncertainty
analysis and semidefinite formulations are out of scope (no algebraic
Riccati equation solver lives in this module). Every polynomial is a
list of float coefficients in descending powers of the variable.
"""

import math

ROUTH_PIVOT_EPS = 1e-12
ROUTH_ROW_EPS = 1e-14
SWEEP_X_MIN = 1e-8
SWEEP_X_MAX = 1e8
SWEEP_POINTS = 801
BISECT_ITER = 200
ROOT_TOL_REL = 1e-13

# Worked loop of the SKILL.md Worked example: G = 1/(s(s+1)),
# K = 8(s+1)/((s+2)(s+8)) lead-lag with K(0) = 0.5.
G_NUM = [1.0]
G_DEN = [1.0, 1.0, 0.0]
K_NUM = [8.0, 8.0]
K_DEN = [1.0, 10.0, 16.0]
W1_MS = 2.5
W1_WB = 0.3
W1_AS = 1e-3
W2_A2 = 0.1
W2_WBC = 2.0
W2_MU2 = 1.0


def _poly_mul(a, b):
    """Convolution product of two coefficient lists in descending powers."""
    out = [0.0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        if ai == 0.0:
            continue
        for j, bj in enumerate(b):
            out[i + j] += ai * bj
    return out


def _poly_add(a, b):
    """Sum of two coefficient lists in descending powers."""
    if len(a) < len(b):
        a = [0.0] * (len(b) - len(a)) + a
    elif len(b) < len(a):
        b = [0.0] * (len(a) - len(b)) + b
    return [x + y for x, y in zip(a, b)]


def _poly_sub(a, b):
    """Difference a - b of two coefficient lists in descending powers."""
    if len(a) < len(b):
        a = [0.0] * (len(b) - len(a)) + a
    elif len(b) < len(a):
        b = [0.0] * (len(a) - len(b)) + b
    return [x - y for x, y in zip(a, b)]


def _poly_deriv(coeffs):
    """Derivative of a polynomial, coefficients in descending powers."""
    n = len(coeffs) - 1
    if n <= 0:
        return [0.0]
    return [coeffs[k] * (n - k) for k in range(n)]


def _poly_eval(coeffs, x):
    """Horner evaluation of a descending-powers polynomial at x."""
    acc = 0.0
    for c in coeffs:
        acc = acc * x + c
    return acc


def _hermitian_square_desc(coeffs):
    """Polynomial in x = w^2 equal to |p(jw)|^2 for p given in descending s.

    With ascending coefficients q[m] (coefficient of s^m), the
    coefficient of x^m is (-1)^m times the alternating sum over
    i + j = 2m of q[i] q[j] (-1)^i; all odd-power coefficients vanish.
    """
    deg = len(coeffs) - 1
    q = coeffs[::-1]
    asc = [0.0] * (deg + 1)
    for m in range(deg + 1):
        acc = 0.0
        for i in range(2 * m + 1):
            j = 2 * m - i
            if i <= deg and j <= deg:
                acc += q[i] * q[j] * (-1.0) ** i
        asc[m] = (-1.0) ** m * acc
    return asc[::-1]


def _geom_grid(x_min, x_max, points):
    """Geometrically spaced grid from x_min to x_max inclusive."""
    if points <= 1:
        return [x_min]
    ratio = (x_max / x_min) ** (1.0 / (points - 1))
    return [x_min * ratio ** k for k in range(points)]


def routh_stable(coeffs):
    """Routh-Hurwitz strict stability of a real polynomial, coefficients descending.

    False for an empty or all-zero list, a non-positive constant
    polynomial, any first-column element at or below ROUTH_PIVOT_EPS,
    and any all-zero computed row (max |entry| at most ROUTH_ROW_EPS,
    the marginal-stability case). A polynomial with a negative leading
    coefficient is multiplied by -1 before the table. Verdicts only,
    no ValueError.
    """
    if not coeffs or all(c == 0.0 for c in coeffs):
        return False
    if len(coeffs) == 1:
        return coeffs[0] > ROUTH_PIVOT_EPS
    c = list(coeffs)
    if c[0] < 0.0:
        c = [-x for x in c]
    degree = len(c) - 1
    row1 = c[0::2]
    row2 = c[1::2]
    if row1[0] <= ROUTH_PIVOT_EPS or row2[0] <= ROUTH_PIVOT_EPS:
        return False
    table = [row1, row2]
    for _ in range(degree - 1):
        upper = table[-2]
        lower = table[-1]
        if max(abs(v) for v in lower) <= ROUTH_ROW_EPS:
            return False
        nxt = []
        for j in range(len(upper) - 1):
            low_j1 = lower[j + 1] if j + 1 < len(lower) else 0.0
            nxt.append((lower[0] * upper[j + 1] - upper[0] * low_j1) / lower[0])
        if nxt[0] <= ROUTH_PIVOT_EPS:
            return False
        table.append(nxt)
    return True


def eval_transfer(num, den, s):
    """Evaluate num(s)/den(s) at complex s by Horner on both coefficient lists."""
    n_val = _poly_eval(num, s)
    d_val = _poly_eval(den, s)
    if d_val == 0.0:
        raise ValueError(f"transfer function denominator is zero at s = {s}")
    return n_val / d_val


def loop_channels(g_num, g_den, k_num, k_den):
    """Assemble the S, T and KS channels of L = G K over the common denominator.

    Returns {"char_poly", "s_num", "s_den", "t_num", "t_den", "ks_num",
    "ks_den"} with char_poly = g_den k_den + g_num k_num, s_num = g_den
    k_den, t_num = g_num k_num, ks_num = k_num g_den, and every channel
    denominator equal to char_poly. The identity S + T = 1 holds
    exactly as polynomials, s_num + t_num = char_poly.
    """
    gd_kd = _poly_mul(g_den, k_den)
    gn_kn = _poly_mul(g_num, k_num)
    char_poly = _poly_add(gd_kd, gn_kn)
    return {
        "char_poly": char_poly,
        "s_num": gd_kd,
        "s_den": list(char_poly),
        "t_num": gn_kn,
        "t_den": list(char_poly),
        "ks_num": _poly_mul(k_num, g_den),
        "ks_den": list(char_poly),
    }


def sensitivity_weight(ms, wb, as_):
    """Sensitivity weight W1(s) = (s/ms + wb)/(s + wb as_) from its corners.

    |W1(j0)| = 1/as_, |W1(j wb)| = sqrt(1 + 1/ms^2)/sqrt(1 + as_^2) and
    |W1(j inf)| = 1/ms. All parameters must be strictly positive.
    """
    if ms <= 0:
        raise ValueError(f"sensitivity weight ms must be positive, got {ms}")
    if wb <= 0:
        raise ValueError(f"sensitivity weight wb must be positive, got {wb}")
    if as_ <= 0:
        raise ValueError(f"sensitivity weight as_ must be positive, got {as_}")
    return [1.0 / ms, wb], [1.0, wb * as_]


def control_weight(a2, wbc, mu2):
    """Control-effort weight W2(s) = (s + wbc a2)/(s/mu2 + wbc) from its corners.

    |W2(j0)| = a2 and |W2(j inf)| = mu2. All parameters must be
    strictly positive.
    """
    if a2 <= 0:
        raise ValueError(f"control weight a2 must be positive, got {a2}")
    if wbc <= 0:
        raise ValueError(f"control weight wbc must be positive, got {wbc}")
    if mu2 <= 0:
        raise ValueError(f"control weight mu2 must be positive, got {mu2}")
    return [1.0, wbc * a2], [1.0 / mu2, wbc]


def _bisect_root(poly_p, lo, hi, flo):
    """Refine a stationary-point bracket [lo, hi] of P to ROOT_TOL_REL."""
    for _ in range(BISECT_ITER):
        mid = 0.5 * (lo + hi)
        if hi - lo <= ROOT_TOL_REL * (1.0 + abs(mid)):
            return mid
        fm = _poly_eval(poly_p, mid)
        if fm == 0.0:
            return mid
        if (flo < 0.0) == (fm < 0.0):
            lo = mid
            flo = fm
        else:
            hi = mid
    return 0.5 * (lo + hi)


def hinfinity_norm(num, den):
    """H-infinity norm of the stable proper SISO transfer function num/den.

    Gamma-iteration search: |H(jw)|^2 = A(x)/B(x) with x = w^2 is a
    rational function whose interior peaks sit at real roots x >= 0 of
    the stationary equation P(x) = A'(x)B(x) - A(x)B'(x) = 0 on the
    geometric grid from SWEEP_X_MIN to SWEEP_X_MAX, each bracket
    refined by bisection to ROOT_TOL_REL. The norm is the square root
    of the largest of the DC value A(0)/B(0), the interior peak values
    and the high-frequency limit (lead-ratio squared when the degrees
    are equal, else 0). ValueError when the transfer function is
    improper or the denominator is not strictly stable.
    """
    if len(num) - 1 > len(den) - 1:
        raise ValueError(
            f"transfer function must be proper: numerator degree {len(num) - 1} "
            f"above denominator degree {len(den) - 1}"
        )
    if not routh_stable(den):
        raise ValueError(
            "H-infinity norm requires a strictly stable denominator "
            "(all poles in the open left half plane)"
        )
    a_poly = _hermitian_square_desc(num)
    b_poly = _hermitian_square_desc(den)
    p_poly = _poly_sub(
        _poly_mul(_poly_deriv(a_poly), b_poly),
        _poly_mul(a_poly, _poly_deriv(b_poly)),
    )
    b_dc = b_poly[-1]
    candidates = [a_poly[-1] / b_dc]
    if len(num) == len(den):
        lead_ratio = num[0] / den[0]
        candidates.append(lead_ratio * lead_ratio)
    grid = _geom_grid(SWEEP_X_MIN, SWEEP_X_MAX, SWEEP_POINTS)
    p_vals = [_poly_eval(p_poly, x) for x in grid]
    for k in range(len(grid) - 1):
        p_lo = p_vals[k]
        p_hi = p_vals[k + 1]
        crossed = (p_lo == 0.0) or (p_hi == 0.0) or (p_lo < 0.0) != (p_hi < 0.0)
        if not crossed:
            continue
        root = _bisect_root(p_poly, grid[k], grid[k + 1], p_lo)
        candidates.append(_poly_eval(a_poly, root) / _poly_eval(b_poly, root))
    return math.sqrt(max(candidates))


def mixed_sensitivity_gamma(channels, w1, w2):
    """Achieved gamma of the S/KS mixed-sensitivity weighting of a loop.

    channels is a loop_channels dict; w1 and w2 are (num, den) tuples.
    Returns {"w1s_norm": ||W1 S||_inf, "w2ks_norm": ||W2 KS||_inf,
    "gamma": the larger of the two, "verdict": gamma < 1.0}. An
    unstable characteristic polynomial raises through the first
    weighted-norm call; callers wanting the stability verdict check
    routh_stable(channels["char_poly"]) first.
    """
    char_poly = channels["char_poly"]
    w1s_norm = hinfinity_norm(
        _poly_mul(w1[0], channels["s_num"]),
        _poly_mul(w1[1], char_poly),
    )
    w2ks_norm = hinfinity_norm(
        _poly_mul(w2[0], channels["ks_num"]),
        _poly_mul(w2[1], char_poly),
    )
    gamma = max(w1s_norm, w2ks_norm)
    return {
        "w1s_norm": w1s_norm,
        "w2ks_norm": w2ks_norm,
        "gamma": gamma,
        "verdict": gamma < 1.0,
    }
