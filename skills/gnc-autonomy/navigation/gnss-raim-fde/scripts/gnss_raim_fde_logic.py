"""GNSS RAIM fault detection and exclusion (pure stdlib).

Receiver autonomous integrity monitoring (RAIM) on an overdetermined
pseudorange geometry, following the RTCA DO-229 MOPS protection level
concepts in paraphrased summary form (never verbatim standard text).
Given satellite line-of-sight unit vectors and a pseudorange measurement
vector, this module builds the geometry matrix H, solves the
overdetermined least-squares navigation solution, forms the residual
test statistic and compares it against a chi-square threshold at a
chosen false-alarm probability, computes the horizontal protection level
(HPL) from the worst-case satellite slope, and identifies the faulty
satellite for exclusion by the largest normalized residual.  Produces
the detection verdict, the HPL, and the excluded-satellite
recommendation that gate an integrity assessment.

All math is stdlib (math only).  Vectors are lists, matrices are lists
of lists, floats throughout.  Deterministic and offline.
"""

import math

# Module constants (DO-229 style defaults, summary paraphrase).
PFA = 1e-5        # false-alarm probability for the chi-square threshold
SIGMA0 = 6.0      # pseudorange 1-sigma noise, metres (default argument)
G0 = 9.80665      # standard gravity, m/s^2 (declared, unused here)


def _vec_norm(v):
    """Euclidean norm of a vector."""
    return math.sqrt(sum(c * c for c in v))


def geometry_matrix(sat_dirs):
    """Build the n x 4 geometry matrix H from satellite LOS unit vectors.

    Row i is [ux, uy, uz, 1.0] where [ux, uy, uz] is the renormalized
    unit line-of-sight direction to satellite i and the final column is
    the receiver clock bias term.  Requires at least 5 satellites (one
    spare beyond the 4 unknowns) so RAIM residuals exist.  Raises
    ValueError when fewer than 5 satellites are given, any direction is
    not a length-3 vector, or any direction norm lies outside
    0.999 to 1.001 (directions are renormalized internally).
    """
    if len(sat_dirs) < 5:
        raise ValueError("geometry_matrix needs at least 5 satellites")
    rows = []
    for v in sat_dirs:
        if len(v) != 3:
            raise ValueError("each satellite direction must be [x, y, z]")
        nrm = _vec_norm(v)
        if not 0.999 <= nrm <= 1.001:
            raise ValueError("satellite directions must be unit vectors")
        ux, uy, uz = (c / nrm for c in v)
        rows.append([ux, uy, uz, 1.0])
    return rows


def _solve_square(A, b):
    """Solve A x = b for a square system by Gaussian elimination with
    partial pivoting.  Raises ValueError on a (near) singular matrix."""
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-12:
            raise ValueError("singular normal matrix, geometry not solvable")
        if piv != col:
            M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        for r in range(col + 1, n):
            f = M[r][col] / pv
            for c in range(col + 1, n + 1):
                M[r][c] -= f * M[col][c]
            M[r][col] = 0.0
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        acc = M[r][n]
        for c in range(r + 1, n):
            acc -= M[r][c] * x[c]
        x[r] = acc / M[r][r]
    return x


def _mat_transpose(A):
    """Transpose a matrix (rows become columns)."""
    return [list(col) for col in zip(*A)]


def _mat_mul(A, B):
    """Matrix product A (m x k) times B (k x p)."""
    k = len(B)
    return [[sum(A[i][t] * B[t][j] for t in range(k))
             for j in range(len(B[0]))]
            for i in range(len(A))]


def _mat_vec_mul(A, v):
    """Matrix A times vector v."""
    return [sum(A[i][j] * v[j] for j in range(len(v)))
            for i in range(len(A))]


def lsq_solve(H, y):
    """Solve the overdetermined least-squares problem H x ~= y.

    Normal equations: N = H^T H (4x4), rhs = H^T y, and
    x_hat = N^-1 rhs via Gaussian elimination with partial pivoting
    (own solver, no numpy).  Returns (x_hat, residuals, sse) where
    residuals r = y - H x_hat has length n and sse = sum r_i^2.
    Raises ValueError when y length does not match the row count of H.
    """
    if len(y) != len(H):
        raise ValueError("measurement count must equal geometry row count")
    if len(H) == 0:
        raise ValueError("empty geometry matrix")
    k = len(H[0])
    Ht = _mat_transpose(H)
    N = _mat_mul(Ht, H)
    rhs = _mat_vec_mul(Ht, y)
    x_hat = _solve_square(N, rhs)
    residuals = [y[i] - sum(H[i][j] * x_hat[j] for j in range(k))
                 for i in range(len(H))]
    sse = sum(r * r for r in residuals)
    return x_hat, residuals, sse


def normal_quantile(p):
    """Standard normal quantile by the Acklam rational approximation.

    Piecewise: p below 0.02425 uses the lower-tail expansion in
    q = sqrt(-2 ln p), the middle band uses the central rational form,
    and p above 0.97575 mirrors the lower tail.  Raises ValueError when
    p is not strictly inside (0, 1).
    """
    if not 0.0 < p < 1.0:
        raise ValueError("probability must lie strictly inside (0, 1)")
    a = (-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00)
    if p < 0.02425:
        q = math.sqrt(-2.0 * math.log(p))
        return _acklam_tail(q, c, d)
    if p <= 0.97575:
        q = p - 0.5
        r = q * q
        num = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4])
               * r + a[5]) * q
        den = (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4])
               * r + 1.0)
        return num / den
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -_acklam_tail(q, c, d)


def _acklam_tail(q, c, d):
    """Shared rational tail form of the Acklam approximation."""
    num = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4])
           * q + c[5])
    den = ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    return num / den


def chi2_quantile(df, p):
    """Chi-square quantile by the Wilson-Hilferty approximation.

    x = df * (1 - 2/(9 df) + z sqrt(2/(9 df)))^3 with z the standard
    normal quantile at p.  Raises ValueError when df < 1.
    """
    if df < 1:
        raise ValueError("chi-square degrees of freedom must be >= 1")
    z = normal_quantile(p)
    return df * (1.0 - 2.0 / (9.0 * df)
                 + z * math.sqrt(2.0 / (9.0 * df))) ** 3


def fault_detect(sse, n, sigma, pfa=PFA):
    """RAIM fault detection test on the sum of squared residuals.

    Test statistic T = sse / sigma^2 is compared against the threshold
    chi2_quantile(n - 4, 1 - pfa).  Returns a dict with test_statistic,
    threshold and detected (True when T exceeds the threshold).  Raises
    ValueError when n < 5 or sigma is not positive.
    """
    if n < 5:
        raise ValueError("fault detection needs at least 5 satellites")
    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    test = sse / (sigma * sigma)
    threshold = chi2_quantile(n - 4, 1.0 - pfa)
    return {"test_statistic": test, "threshold": threshold,
            "detected": test > threshold}


def _influence(H):
    """Return (A, S) with A = (H^T H)^-1 H^T (k x n) and the residual
    sensitivity matrix S = I - H A (n x n)."""
    n = len(H)
    k = len(H[0])
    Ht = _mat_transpose(H)
    N = _mat_mul(Ht, H)
    a_cols = [_solve_square(N, [Ht[r][c] for r in range(k)])
              for c in range(n)]
    A = _mat_transpose(a_cols)
    S = [[(1.0 if i == j else 0.0)
          - sum(H[i][t] * A[t][j] for t in range(k))
          for j in range(n)]
         for i in range(n)]
    return A, S


def residual_sensitivity(H):
    """Residual sensitivity matrix S = I - H (H^T H)^-1 H^T (n x n)."""
    return _influence(H)[1]


def raim_hpl(H, sigma, pfa=PFA):
    """Horizontal protection level from the worst-case satellite slope.

    With A = (H^T H)^-1 H^T and S = residual_sensitivity(H), the
    satellite slope is slope_j = sqrt(A[0][j]^2 + A[1][j]^2) /
    sqrt(S[j][j]) and HPL = max_j slope_j * sigma *
    sqrt(chi2_quantile(n - 4, 1 - pfa)).  Raises ValueError when fewer
    than 5 satellites are present, sigma is not positive, or any
    residual sensitivity S[j][j] is at or below 1e-12 (no redundancy
    left in that satellite direction).
    """
    n = len(H)
    if n < 5:
        raise ValueError("HPL needs at least 5 satellites")
    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    A, S = _influence(H)
    diag = [S[j][j] for j in range(n)]
    if any(s <= 1e-12 for s in diag):
        raise ValueError("residual sensitivity vanishes for a satellite")
    threshold = chi2_quantile(n - 4, 1.0 - pfa)
    slopes = [math.sqrt(A[0][j] ** 2 + A[1][j] ** 2) / math.sqrt(S[j][j])
              for j in range(n)]
    return max(slopes) * sigma * math.sqrt(threshold)


def exclude_faulty(H, y, sigma=SIGMA0):
    """Identify the faulty satellite by the largest normalized residual.

    Normalized residual nr_i = |r_i| / (sigma * sqrt(S[i][i])) with r
    the least-squares residuals and S the residual sensitivity; the
    worst index is the argmax over n.  Returns a dict with worst_sat
    (the index), normalized_residuals (the full list) and
    recommended_exclusion True.  Raises ValueError when fewer than 6
    satellites are present (need at least one spare satellite after
    exclusion) or sigma is not positive.
    """
    n = len(H)
    if n < 6:
        raise ValueError("exclusion needs at least 6 satellites")
    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    _, residuals, _sse = lsq_solve(H, y)
    _, S = _influence(H)
    diag = [S[j][j] for j in range(n)]
    if any(s <= 1e-12 for s in diag):
        raise ValueError("residual sensitivity vanishes for a satellite")
    nrs = [abs(residuals[j]) / (sigma * math.sqrt(S[j][j]))
           for j in range(n)]
    worst = max(range(n), key=lambda j: nrs[j])
    return {"worst_sat": worst, "normalized_residuals": nrs,
            "recommended_exclusion": True}


def availability_verdict(hpl, hal):
    """Availability verdict: "available" when HPL <= HAL, otherwise
    "unavailable"."""
    return "available" if hpl <= hal else "unavailable"
