"""Optimal spacecraft attitude determination by the Davenport q-method.

Pure Python stdlib, deterministic, no RNG.  Convention: observations b_i
(unit vectors in the BODY frame) relate to reference vectors r_i (unit
vectors in the REFERENCE frame) by b_i = A(q) r_i with the ACTIVE rotation
convention A(q) v = q * (0, v) * q_conj under the Hamilton quaternion product,
q = (w, x, y, z) with w the scalar.  Wahba's cost

    J(q) = sum_i w_i * |b_i - A(q) r_i|^2

is minimized by the unit eigenvector of the symmetric 4x4 Davenport K matrix
for the LARGEST eigenvalue, computed with a deterministic fixed-sweep Jacobi
iteration.  The eigenvector is read SCALAR-LAST: q = (V[3][imax], V[0][imax],
V[1][imax], V[2][imax]).
"""

import math

JACOBI_MAX_SWEEPS = 60
JACOBI_TOL = 1e-13
MIN_OBSERVATIONS = 2
UNIT_TOL = 1e-6
IDENTITY_RESIDUAL_TOL = 1e-6

IDENTITY_Q = (1.0, 0.0, 0.0, 0.0)


def _norm3(v):
    """Euclidean norm of a 3-vector."""
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _is_unit(v):
    """True when the 3-vector v has norm within UNIT_TOL of one."""
    return abs(_norm3(v) - 1.0) <= UNIT_TOL


def quat_product(q, r):
    """Hamilton product of quaternions q and r, each ordered (w, x, y, z).

    w = q0*r0 - q1*r1 - q2*r2 - q3*r3
    x = q0*r1 + q1*r0 + q2*r3 - q3*r2
    y = q0*r2 - q1*r3 + q2*r0 + q3*r1
    z = q0*r3 + q1*r2 - q2*r1 + q3*r0
    """
    w0, x0, y0, z0 = q
    w1, x1, y1, z1 = r
    return (w0 * w1 - x0 * x1 - y0 * y1 - z0 * z1,
            w0 * x1 + x0 * w1 + y0 * z1 - z0 * y1,
            w0 * y1 - x0 * z1 + y0 * w1 + z0 * x1,
            w0 * z1 + x0 * y1 - y0 * x1 + z0 * w1)


def conjugate(q):
    """Conjugate of quaternion q: negate the vector part, keep the scalar."""
    return (q[0], -q[1], -q[2], -q[3])


def rotate_vector(q, v):
    """Active rotation A(q) v = quat_product(quat_product(q, (0, v)), conj(q)).

    Returns the vector part (x, y, z) of the rotated quaternion.
    """
    lifted = (0.0, v[0], v[1], v[2])
    rotated = quat_product(quat_product(q, lifted), conjugate(q))
    return (rotated[1], rotated[2], rotated[3])


def _residual_norm(q, b, r):
    """Euclidean norm of the observation residual b - A(q) r."""
    av = rotate_vector(q, r)
    dx = b[0] - av[0]
    dy = b[1] - av[1]
    dz = b[2] - av[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def attitude_profile(observations, references, weights=None):
    """Return the 3x3 attitude profile matrix B = sum_i w_i b_i r_i^T.

    observations: list of body-frame unit vectors b_i.
    references: list of reference-frame unit vectors r_i.
    weights: optional positive per-observation weights (default all ones).
    Raises ValueError on fewer than MIN_OBSERVATIONS observations, length
    mismatches, non-unit vectors (norm outside 1 +- UNIT_TOL) and
    non-positive weights.
    """
    nobs = len(observations)
    if nobs < MIN_OBSERVATIONS:
        raise ValueError("at least %d observations are required" % MIN_OBSERVATIONS)
    if len(references) != nobs:
        raise ValueError("observation and reference counts differ")
    if weights is None:
        weights = [1.0] * nobs
    if len(weights) != nobs:
        raise ValueError("weights length differs from observation count")
    for i in range(nobs):
        if not _is_unit(observations[i]):
            raise ValueError("observation vector %d is not a unit vector" % i)
        if not _is_unit(references[i]):
            raise ValueError("reference vector %d is not a unit vector" % i)
        if weights[i] <= 0.0:
            raise ValueError("weights must be strictly positive")
    b = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
    for i in range(nobs):
        w = weights[i]
        bv = observations[i]
        rv = references[i]
        for row in range(3):
            for col in range(3):
                b[row][col] += w * bv[row] * rv[col]
    return b


def davenport_k_matrix(B):
    """Return (K, sigma, z) from the attitude profile matrix B.

    sigma = trace(B); S = B + B^T;
    z = (B[2][1]-B[1][2], B[0][2]-B[2][0], B[1][0]-B[0][1]);
    K = [[S - sigma*I3, z], [z^T, sigma]].  The z sign is the one verified to
    recover the generating quaternion under the active A(q)v = q v q*
    convention; flipping it recovers the inverse rotation, so keep as written.
    """
    sigma = B[0][0] + B[1][1] + B[2][2]
    z = (B[2][1] - B[1][2], B[0][2] - B[2][0], B[1][0] - B[0][1])
    k = [[0.0] * 4 for _ in range(4)]
    for i in range(3):
        for j in range(3):
            k[i][j] = B[i][j] + B[j][i] - (sigma if i == j else 0.0)
    for i in range(3):
        k[i][3] = z[i]
        k[3][i] = z[i]
    k[3][3] = sigma
    return k, sigma, z


def _jacobi_rotation(a, v, p, q):
    """One Jacobi rotation in plane (p, q) of symmetric a; v = v * G.

    Rotation angle from tan(2*theta) = 2*a[p][q] / (a[q][q] - a[p][p]) via
    atan2, which yields theta = pi/4 when the diagonal entries are equal.
    """
    theta = 0.5 * math.atan2(2.0 * a[p][q], a[q][q] - a[p][p])
    c = math.cos(theta)
    s = math.sin(theta)
    app = a[p][p]
    aqq = a[q][q]
    apq = a[p][q]
    for k in range(4):
        if k == p or k == q:
            continue
        akp = a[k][p]
        akq = a[k][q]
        a[k][p] = a[p][k] = c * akp - s * akq
        a[k][q] = a[q][k] = s * akp + c * akq
    a[p][p] = c * c * app - 2.0 * c * s * apq + s * s * aqq
    a[q][q] = s * s * app + 2.0 * c * s * apq + c * c * aqq
    a[p][q] = a[q][p] = 0.0
    for i in range(4):
        vip = v[i][p]
        viq = v[i][q]
        v[i][p] = c * vip - s * viq
        v[i][q] = s * vip + c * viq


def jacobi_eigen_sym4(K):
    """Eigen-decompose a real symmetric 4x4 matrix by fixed-sweep Jacobi.

    Repeatedly zero the largest off-diagonal entry; stop when its magnitude
    is below JACOBI_TOL or after JACOBI_MAX_SWEEPS.  Returns (eigenvalues,
    eigenvectors) with the eigenvector columns of V ordered to match the
    returned diagonal eigenvalues.
    """
    a = [row[:] for row in K]
    v = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
    for _ in range(JACOBI_MAX_SWEEPS):
        pmax = 0
        qmax = 1
        largest = 0.0
        for i in range(4):
            for j in range(i + 1, 4):
                mag = abs(a[i][j])
                if mag > largest:
                    largest = mag
                    pmax = i
                    qmax = j
        if largest < JACOBI_TOL:
            break
        _jacobi_rotation(a, v, pmax, qmax)
    eigenvalues = [a[i][i] for i in range(4)]
    return eigenvalues, v


def attitude_matrix_from_quaternion(q):
    """3x3 attitude matrix whose rows are A(q) e_i for the reference axes."""
    axes = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    return [list(rotate_vector(q, axis)) for axis in axes]


def wahba_cost(q, observations, references, weights=None):
    """Wahba cost J(q) = sum_i w_i |b_i - A(q) r_i|^2 for an arbitrary q."""
    if weights is None:
        weights = [1.0] * len(observations)
    total = 0.0
    for i in range(len(observations)):
        res = _residual_norm(q, observations[i], references[i])
        total += weights[i] * res * res
    return total


def quest_solution(observations, references, weights=None):
    """Optimal attitude from weighted vector observations (Davenport method).

    Returns a dict with exactly the keys q_optimal (w, x, y, z), lambda_max,
    attitude_matrix (3x3), residuals (per observation), wahba_cost and
    identity_ok.  The optimal quaternion is the unit eigenvector of K for the
    largest eigenvalue, read scalar-last.  ValueErrors from the input checks
    propagate.
    """
    b = attitude_profile(observations, references, weights)
    k, _sigma, _z = davenport_k_matrix(b)
    eigenvalues, v = jacobi_eigen_sym4(k)
    imax = 0
    for i in range(1, 4):
        if eigenvalues[i] > eigenvalues[imax]:
            imax = i
    lambda_max = eigenvalues[imax]
    q_raw = (v[3][imax], v[0][imax], v[1][imax], v[2][imax])
    norm_q = math.sqrt(q_raw[0] * q_raw[0] + q_raw[1] * q_raw[1]
                       + q_raw[2] * q_raw[2] + q_raw[3] * q_raw[3])
    q = tuple(component / norm_q for component in q_raw)
    if weights is None:
        wts = [1.0] * len(observations)
    else:
        wts = weights
    residuals = [_residual_norm(q, observations[i], references[i])
                 for i in range(len(observations))]
    cost = sum(wts[i] * residuals[i] * residuals[i]
               for i in range(len(observations)))
    identity_ok = max(residuals) < IDENTITY_RESIDUAL_TOL
    return {
        "q_optimal": q,
        "lambda_max": lambda_max,
        "attitude_matrix": attitude_matrix_from_quaternion(q),
        "residuals": residuals,
        "wahba_cost": cost,
        "identity_ok": identity_ok,
    }
