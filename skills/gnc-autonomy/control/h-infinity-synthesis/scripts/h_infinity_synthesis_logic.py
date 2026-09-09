"""DGKF two-Riccati state-space H-infinity synthesis, pure stdlib (math only).

Synthesizes the central H-infinity controller of the two-state normalized
standard problem (D11 = 0, D22 = 0) by the Hamiltonian stable-invariant-
subspace method: solve the X_inf and Y_inf algebraic Riccati equations,
bisect the gamma level while the spectral-radius coupling rho(X_inf Y_inf)
< gamma^2 holds, and assemble the central controller state matrices.
"""

import math

N_STATES = 2
GAMMA_BISECT_ITER = 80
GAMMA_HI_START = 1.0
GAMMA_HI_CEIL = 1e6
GAMMA_FLOOR = 1e-6
PSD_EPS = 1e-9
IMAG_AXIS_EPS = 1e-9
DEFECT_EPS = 1e-12
COUPLING_REL_EPS = 1e-9
PEAK_W_MIN = 1e-3
PEAK_W_MAX = 1e3
PEAK_GRID_POINTS = 4001

HAM_DIM = 2 * N_STATES
REPEATED_EIG_REL_TOL = 1e-8


# --- complex arithmetic (tuples (re, im), no cmath import) -----------------

def cadd(a, b):
    return (a[0] + b[0], a[1] + b[1])


def csub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def cmul(a, b):
    return (a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0])


def cdiv(a, b):
    denom = b[0] * b[0] + b[1] * b[1]
    return ((a[0] * b[0] + a[1] * b[1]) / denom, (a[1] * b[0] - a[0] * b[1]) / denom)


def cneg(a):
    return (-a[0], -a[1])


def conj(a):
    return (a[0], -a[1])


def cabs(a):
    return math.hypot(a[0], a[1])


def csqrt(a):
    """Principal branch complex square root, hand formula, no cmath."""
    r = cabs(a)
    re = math.sqrt(max((r + a[0]) / 2.0, 0.0))
    im = math.sqrt(max((r - a[0]) / 2.0, 0.0))
    if a[1] < 0.0:
        im = -im
    return (re, im)


# --- real matrix helpers (list of lists, row major) -------------------------

def _check_shape(matrix, rows, cols, name):
    """Reject a matrix that is not the pinned rows x cols shape."""
    if len(matrix) != rows or any(len(row) != cols for row in matrix):
        raise ValueError("%s must be a %dx%d matrix" % (name, rows, cols))


def mat_mult(a, b):
    rows, inner, cols = len(a), len(a[0]), len(b[0])
    return [[sum(a[i][k] * b[k][j] for k in range(inner)) for j in range(cols)] for i in range(rows)]


def mat_add(a, b):
    return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]


def mat_sub(a, b):
    return [[a[i][j] - b[i][j] for j in range(len(a[0]))] for i in range(len(a))]


def mat_scale(a, s):
    return [[a[i][j] * s for j in range(len(a[0]))] for i in range(len(a))]


def mat_transpose(a):
    return [[a[i][j] for i in range(len(a))] for j in range(len(a[0]))]


def mat_eye(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def mat_trace(a):
    return sum(a[i][i] for i in range(len(a)))


def hstack(a, b):
    return [list(a[i]) + list(b[i]) for i in range(len(a))]


def vstack(a, b):
    return [list(row) for row in a] + [list(row) for row in b]


def mat2_inv(a):
    """Closed-form real 2x2 inverse."""
    det = a[0][0] * a[1][1] - a[0][1] * a[1][0]
    if abs(det) < 1e-300:
        raise ValueError("singular 2x2 matrix")
    return [[a[1][1] / det, -a[0][1] / det], [-a[1][0] / det, a[0][0] / det]]


def eigs2x2(a):
    """Closed-form eigenvalues of a real 2x2 matrix as two complex tuples."""
    tr2 = (a[0][0] + a[1][1]) / 2.0
    disc = ((a[0][0] - a[1][1]) / 2.0) ** 2 + a[0][1] * a[1][0]
    sq = csqrt((disc, 0.0))
    return [(tr2 + sq[0], sq[1]), (tr2 - sq[0], -sq[1])]


def spectral_radius(m):
    """Spectral radius of a real 2x2 matrix by the closed-form eigenvalue pair."""
    return max(cabs(e) for e in eigs2x2(m))


# --- Faddeev-LeVerrier characteristic polynomial (general n) ----------------

def fl_char_poly(h):
    """Coefficients c1..cn of det(lambda I - H) = lambda^n + c1 l^(n-1) + ... + cn."""
    n = len(h)
    m = mat_eye(n)
    coeffs = []
    for k in range(1, n + 1):
        am = mat_mult(h, m)
        ck = -mat_trace(am) / k
        coeffs.append(ck)
        m = mat_add(am, mat_scale(mat_eye(n), ck))
    return coeffs


# --- complex matrix helpers for the 4x4 Hamiltonian eigenproblem ------------

def to_complex_matrix(real_m):
    return [[(v, 0.0) for v in row] for row in real_m]


def cmat_sub(a, b):
    return [[csub(a[i][j], b[i][j]) for j in range(len(a[0]))] for i in range(len(a))]


def cmat_mult(a, b):
    rows, inner, cols = len(a), len(a[0]), len(b[0])
    out = []
    for i in range(rows):
        row = []
        for j in range(cols):
            acc = (0.0, 0.0)
            for k in range(inner):
                acc = cadd(acc, cmul(a[i][k], b[k][j]))
            row.append(acc)
        out.append(row)
    return out


def complex_scaled_identity(lam, n):
    return [[lam if i == j else (0.0, 0.0) for j in range(n)] for i in range(n)]


def complex_axis_identity(w, n):
    return [[(0.0, w) if i == j else (0.0, 0.0) for j in range(n)] for i in range(n)]


def det3x3c(m):
    """3x3 complex determinant by cofactor expansion along row 0."""
    term0 = cmul(m[0][0], csub(cmul(m[1][1], m[2][2]), cmul(m[1][2], m[2][1])))
    term1 = cmul(m[0][1], csub(cmul(m[1][0], m[2][2]), cmul(m[1][2], m[2][0])))
    term2 = cmul(m[0][2], csub(cmul(m[1][0], m[2][1]), cmul(m[1][1], m[2][0])))
    return csub(cadd(term0, term2), term1)


def minor4x4(m, drop_row, drop_col):
    return [[m[r][c] for c in range(4) if c != drop_col] for r in range(4) if r != drop_row]


def adjugate4x4(m):
    """Adjugate of a 4x4 complex matrix by cofactor expansion, no linear solver."""
    adj = [[(0.0, 0.0)] * 4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            sign = 1.0 if (i + j) % 2 == 0 else -1.0
            cof = det3x3c(minor4x4(m, i, j))
            adj[j][i] = (sign * cof[0], sign * cof[1])
    return adj


def cmat_solve(a_complex, b_complex):
    """Solve A X = B for square complex A via Gauss-Jordan with partial pivoting."""
    n = len(a_complex)
    width = len(b_complex[0])
    aug = [list(a_complex[i]) + list(b_complex[i]) for i in range(n)]
    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: cabs(aug[r][col]))
        if cabs(aug[pivot_row][col]) < 1e-300:
            raise ValueError("singular 4x4 solve")
        aug[col], aug[pivot_row] = aug[pivot_row], aug[col]
        pivot_val = aug[col][col]
        aug[col] = [cdiv(v, pivot_val) for v in aug[col]]
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor != (0.0, 0.0):
                aug[r] = [csub(aug[r][k], cmul(factor, aug[col][k])) for k in range(n + width)]
    return [row[n:] for row in aug]


def sigma_max_2x2(m):
    """Largest singular value of a 2x2 complex matrix by the Hermitian eigenvalue formula."""
    mh = [[conj(m[j][i]) for j in range(2)] for i in range(2)]
    mhm = cmat_mult(mh, m)
    a, d = mhm[0][0][0], mhm[1][1][0]
    b = mhm[0][1]
    babs2 = b[0] * b[0] + b[1] * b[1]
    tr2 = (a + d) / 2.0
    disc = ((a - d) / 2.0) ** 2 + babs2
    lam_max = tr2 + math.sqrt(max(disc, 0.0))
    return math.sqrt(max(lam_max, 0.0))


# --- Hamiltonian stable-invariant-subspace Riccati solver --------------------

def build_hamiltonian(m, s, q):
    """H = [[M, S], [-Q, -M']] for the Riccati equation M'X + XM + XSX + Q = 0."""
    top = hstack(m, s)
    bot = hstack(mat_scale(q, -1.0), mat_scale(mat_transpose(m), -1.0))
    return vstack(top, bot)


def _hamiltonian_eigenvalues(h):
    """Four eigenvalues of the 4x4 Hamiltonian from its even characteristic polynomial."""
    coeffs = fl_char_poly(h)
    c2, c4 = coeffs[1], coeffs[3]
    disc = c2 * c2 - 4.0 * c4
    sqrt_disc = csqrt((disc, 0.0))
    mu1 = ((-c2 + sqrt_disc[0]) / 2.0, sqrt_disc[1] / 2.0)
    mu2 = ((-c2 - sqrt_disc[0]) / 2.0, -sqrt_disc[1] / 2.0)
    eigenvalues = []
    for mu in (mu1, mu2):
        root = csqrt(mu)
        eigenvalues.append(root)
        eigenvalues.append(cneg(root))
    return eigenvalues


def _stable_subspace_eigenvector(h_complex, lam):
    """Largest-magnitude adjugate column of H - lambda I, the stable eigenvector."""
    shifted = cmat_sub(h_complex, complex_scaled_identity(lam, HAM_DIM))
    adj = adjugate4x4(shifted)
    best_col, best_norm = None, -1.0
    for j in range(HAM_DIM):
        norm2 = sum(cabs(adj[i][j]) ** 2 for i in range(HAM_DIM))
        if norm2 > best_norm:
            best_norm, best_col = norm2, [adj[i][j] for i in range(HAM_DIM)]
    return best_col, best_norm


def solve_riccati(m, s, q):
    """Stabilizing PSD solution of M'X + XM + XSX + Q = 0, or None if infeasible."""
    h = build_hamiltonian(m, s, q)
    eigenvalues = _hamiltonian_eigenvalues(h)
    if any(abs(lam[0]) <= IMAG_AXIS_EPS * (1.0 + cabs(lam)) for lam in eigenvalues):
        return None
    stable = [lam for lam in eigenvalues if lam[0] < -IMAG_AXIS_EPS * (1.0 + cabs(lam))]
    if len(stable) != 2:
        return None
    if cabs(csub(stable[0], stable[1])) < REPEATED_EIG_REL_TOL * max(1.0, cabs(stable[0])):
        return None

    h_complex = to_complex_matrix(h)
    vectors = []
    for lam in stable:
        vec, norm2 = _stable_subspace_eigenvector(h_complex, lam)
        if norm2 < DEFECT_EPS:
            return None
        vectors.append(vec)

    u1 = [[vectors[0][i], vectors[1][i]] for i in range(N_STATES)]
    u2 = [[vectors[0][i], vectors[1][i]] for i in range(N_STATES, HAM_DIM)]
    det_u1 = csub(cmul(u1[0][0], u1[1][1]), cmul(u1[0][1], u1[1][0]))
    if cabs(det_u1) < DEFECT_EPS:
        return None
    u1_inv = [
        [cdiv(u1[1][1], det_u1), cdiv(cneg(u1[0][1]), det_u1)],
        [cdiv(cneg(u1[1][0]), det_u1), cdiv(u1[0][0], det_u1)],
    ]
    x_complex = cmat_mult(u2, u1_inv)
    x_real = [[x_complex[i][j][0] for j in range(N_STATES)] for i in range(N_STATES)]
    x_sym = mat_scale(mat_add(x_real, mat_transpose(x_real)), 0.5)

    if any(e[0] < -PSD_EPS for e in eigs2x2(x_sym)):
        return None
    closed_loop = mat_add(m, mat_mult(s, x_sym))
    if any(e[0] >= -IMAG_AXIS_EPS for e in eigs2x2(closed_loop)):
        return None
    return x_sym


# --- public synthesis API ----------------------------------------------------

def are_x_inf(a, b1, b2, c1, gamma):
    """Stabilizing PSD solution X_inf of the regulator-side algebraic Riccati equation."""
    _check_shape(a, N_STATES, N_STATES, "A")
    _check_shape(b1, N_STATES, N_STATES, "B1")
    _check_shape(b2, N_STATES, 1, "B2")
    _check_shape(c1, N_STATES, N_STATES, "C1")
    if gamma <= 0.0:
        raise ValueError("gamma level must be strictly positive: received gamma = %r" % (gamma,))
    s_x = mat_sub(mat_scale(mat_mult(b1, mat_transpose(b1)), gamma ** -2), mat_mult(b2, mat_transpose(b2)))
    q = mat_mult(mat_transpose(c1), c1)
    x_inf = solve_riccati(a, s_x, q)
    if x_inf is None:
        raise ValueError("no stabilizing PSD solution of the X_inf algebraic Riccati equation at gamma = %r" % (gamma,))
    return x_inf


def are_y_inf(a, b1, b2, c1, c2, gamma):
    """Stabilizing PSD solution Y_inf of the estimator-side algebraic Riccati equation."""
    _check_shape(a, N_STATES, N_STATES, "A")
    _check_shape(b1, N_STATES, N_STATES, "B1")
    _check_shape(b2, N_STATES, 1, "B2")
    _check_shape(c1, N_STATES, N_STATES, "C1")
    _check_shape(c2, 1, N_STATES, "C2")
    if gamma <= 0.0:
        raise ValueError("gamma level must be strictly positive: received gamma = %r" % (gamma,))
    s_y = mat_sub(mat_scale(mat_mult(mat_transpose(c1), c1), gamma ** -2), mat_mult(mat_transpose(c2), c2))
    q = mat_mult(b1, mat_transpose(b1))
    y_inf = solve_riccati(mat_transpose(a), s_y, q)
    if y_inf is None:
        raise ValueError("no stabilizing PSD solution of the Y_inf algebraic Riccati equation at gamma = %r" % (gamma,))
    return y_inf


def gamma_feasible(a, b1, b2, c1, c2, gamma):
    """Feasibility verdict of the gamma level: both stabilizing AREs plus the coupling check."""
    try:
        x_inf = are_x_inf(a, b1, b2, c1, gamma)
    except ValueError as exc:
        if "strictly positive" in str(exc):
            raise
        return {"feasible": False, "reason": "x-are-no-stabilizing-solution", "x": None, "y": None, "rho": None}
    try:
        y_inf = are_y_inf(a, b1, b2, c1, c2, gamma)
    except ValueError as exc:
        if "strictly positive" in str(exc):
            raise
        return {"feasible": False, "reason": "y-are-no-stabilizing-solution", "x": x_inf, "y": None, "rho": None}
    rho = spectral_radius(mat_mult(x_inf, y_inf))
    if rho * (1.0 + COUPLING_REL_EPS) < gamma * gamma:
        return {"feasible": True, "reason": "", "x": x_inf, "y": y_inf, "rho": rho}
    return {"feasible": False, "reason": "spectral-radius-coupling-fails", "x": x_inf, "y": y_inf, "rho": rho}


def central_controller(a, b1, b2, c1, c2, gamma):
    """Central H-infinity controller state matrices at the declared working level gamma."""
    if gamma <= 0.0:
        raise ValueError("gamma level must be strictly positive: received gamma = %r" % (gamma,))
    x_inf = are_x_inf(a, b1, b2, c1, gamma)
    y_inf = are_y_inf(a, b1, b2, c1, c2, gamma)
    rho = spectral_radius(mat_mult(x_inf, y_inf))
    if not (rho * (1.0 + COUPLING_REL_EPS) < gamma * gamma):
        raise ValueError(
            "spectral-radius coupling condition rho(X_inf Y_inf) < gamma^2 fails: rho = %r at gamma = %r (rho * gamma^-2 = %r)"
            % (rho, gamma, rho / (gamma * gamma))
        )
    f_inf = mat_scale(mat_mult(mat_transpose(b2), x_inf), -1.0)
    h_inf = mat_scale(mat_mult(y_inf, mat_transpose(c2)), -1.0)
    z_inf = mat2_inv(mat_sub(mat_eye(N_STATES), mat_scale(mat_mult(y_inf, x_inf), gamma ** -2)))
    b1b1t = mat_mult(b1, mat_transpose(b1))
    a_k = mat_add(
        mat_add(mat_add(a, mat_scale(b1b1t, gamma ** -2)), mat_mult(b2, f_inf)),
        mat_mult(z_inf, mat_mult(h_inf, c2)),
    )
    b_k = mat_scale(mat_mult(z_inf, h_inf), -1.0)
    c_k = f_inf
    d_k = [[0.0]]
    return {
        "x_inf": x_inf, "y_inf": y_inf, "rho": rho,
        "f_inf": f_inf, "h_inf": h_inf, "z_inf": z_inf,
        "a_k": a_k, "b_k": b_k, "c_k": c_k, "d_k": d_k, "gamma": gamma,
    }


def gamma_iteration(a, b1, b2, c1, c2):
    """Bisect the infimum feasible gamma level over the Riccati feasibility of the plant."""
    gamma_hi = GAMMA_HI_START
    while not gamma_feasible(a, b1, b2, c1, c2, gamma_hi)["feasible"]:
        gamma_hi *= 2.0
        if gamma_hi > GAMMA_HI_CEIL:
            raise ValueError(
                "no feasible gamma level up to the ceiling 1000000: the generalized plant admits no suboptimal H-infinity controller"
            )
    feas_result = gamma_feasible(a, b1, b2, c1, c2, gamma_hi)
    candidate = gamma_hi
    while True:
        half = candidate / 2.0
        if half < GAMMA_FLOOR:
            raise ValueError("generalized plant feasible at the gamma floor 1e-06: rescale the problem or lower the floor")
        res = gamma_feasible(a, b1, b2, c1, c2, half)
        if res["feasible"]:
            candidate = half
            feas_result = res
        else:
            gamma_lo = half
            gamma_hi = candidate
            break
    for _ in range(GAMMA_BISECT_ITER):
        mid = (gamma_hi + gamma_lo) / 2.0
        res = gamma_feasible(a, b1, b2, c1, c2, mid)
        if res["feasible"]:
            gamma_hi = mid
            feas_result = res
        else:
            gamma_lo = mid
    return {
        "gamma_inf": gamma_hi, "gamma_lo": gamma_lo,
        "x_inf": feas_result["x"], "y_inf": feas_result["y"], "rho": feas_result["rho"],
    }


def closed_loop_peak(a, b1, b2, c1, c2, ctrl):
    """Fixed-grid maximum of sigma_max Tzw(jw) of the plant plus the central controller."""
    _check_shape(a, N_STATES, N_STATES, "A")
    _check_shape(b1, N_STATES, N_STATES, "B1")
    _check_shape(b2, N_STATES, 1, "B2")
    _check_shape(c1, N_STATES, N_STATES, "C1")
    _check_shape(c2, 1, N_STATES, "C2")
    a_k, b_k, c_k = ctrl["a_k"], ctrl["b_k"], ctrl["c_k"]
    d12 = [[0.0], [1.0]]
    d21 = [[0.0, 1.0]]
    a_cl = vstack(hstack(a, mat_mult(b2, c_k)), hstack(mat_mult(b_k, c2), a_k))
    b_cl = vstack(b1, mat_mult(b_k, d21))
    c_cl = hstack(c1, mat_mult(d12, c_k))
    a_cl_c = to_complex_matrix(a_cl)
    b_cl_c = to_complex_matrix(b_cl)
    c_cl_c = to_complex_matrix(c_cl)

    log_lo, log_hi = math.log(PEAK_W_MIN), math.log(PEAK_W_MAX)
    peak, w_peak = -1.0, PEAK_W_MIN
    for i in range(PEAK_GRID_POINTS):
        frac = i / (PEAK_GRID_POINTS - 1)
        w = math.exp(log_lo + frac * (log_hi - log_lo))
        jw_i = complex_axis_identity(w, HAM_DIM)
        solved = cmat_solve(cmat_sub(jw_i, a_cl_c), b_cl_c)
        tzw = cmat_mult(c_cl_c, solved)
        sigma = sigma_max_2x2(tzw)
        if sigma > peak:
            peak, w_peak = sigma, w
    return {"peak": peak, "w_peak": w_peak}
