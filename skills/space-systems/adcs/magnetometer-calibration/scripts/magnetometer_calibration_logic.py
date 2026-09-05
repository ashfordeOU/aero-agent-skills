#!/usr/bin/env python3
"""Scalar-checking batch least squares magnetometer bias calibration.

Common-knowledge estimation method (standards-map.yaml, ecss: ECSS
documents are copyright ESA and referenced, not reproduced; in-flight
magnetometer calibration by scalar checking is open ADCS literature):
the measured body-frame sample m_k = h_k + b + noise contains the true
field h_k plus the sensor bias b, and |h_k| = B_k is the known field
magnitude at sample k (the IGRF magnitude at that position, treated as
an input, in nT). Squaring the scalar-checking identity
|m_k - b|^2 = B_k^2 expands to |m_k|^2 - 2 m_k.b + |b|^2 = B_k^2, which
is LINEAR in the four unknowns x = [b_x, b_y, b_z, |b|^2] with design
row [-2*m_kx, -2*m_ky, -2*m_kz, 1] and right side
y_k = B_k^2 - |m_k|^2. The batch least squares solution of the normal
equations A^T A x = A^T y (plain matrix multiply, solved by Gaussian
elimination with partial pivoting) returns the bias from the first
three unknowns; the fourth unknown must equal |b|^2 and is reported as
a consistency check. Scale factors and cross-axis terms are a disclosed
limitation: the scalar-checking model is encoded bias-only because a
clean linear encoding of the three diagonal scale unknowns turns the
design nonlinear. Module constant: SINGULARITY_TOL = 1e-12 (relative
pivot floor of the elimination, the attitude-diversity gate).
"""

import math

SINGULARITY_TOL = 1e-12


def _transpose(matrix):
    """Transpose an m x n matrix (list of rows) to n x m."""
    return [list(col) for col in zip(*matrix)]


def _mat_vec_mul(matrix, vector):
    """Matrix times vector product, plain multiply."""
    return [sum(row[j] * vector[j] for j in range(len(vector)))
            for row in matrix]


def _mat_mul(left, right):
    """Matrix product of two matrices, plain multiply."""
    cols = len(right[0])
    return [[sum(a * b for a, b in zip(row, col))
             for col in ([right[i][j] for i in range(len(right))]
                         for j in range(cols))]
            for row in left]


def scalar_checking_design(measurements, field_magnitudes):
    """Build the scalar-checking linear system (A, y).

    Row k is [-2*m_kx, -2*m_ky, -2*m_kz, 1] and the right side is
    y_k = B_k^2 - |m_k|^2 from expanding |m_k - b|^2 = B_k^2. Raises
    ValueError when the lists differ in length, when fewer than 4
    measurements are given ("fewer than 4 measurements cannot constrain
    4 unknowns"), when a measurement is not a 3-vector, or when a field
    magnitude is <= 0.
    """
    if len(measurements) != len(field_magnitudes):
        raise ValueError("measurements and field magnitudes must have "
                         "equal length")
    if len(measurements) < 4:
        raise ValueError("fewer than 4 measurements cannot constrain "
                         "4 unknowns")
    for magnitude in field_magnitudes:
        if magnitude <= 0:
            raise ValueError("field magnitude must be positive")
    rows = []
    right = []
    for measurement, magnitude in zip(measurements, field_magnitudes):
        if len(measurement) != 3:
            raise ValueError("each measurement must be a 3-vector")
        mx, my, mz = measurement
        rows.append([-2.0 * mx, -2.0 * my, -2.0 * mz, 1.0])
        right.append(magnitude * magnitude
                     - (mx * mx + my * my + mz * mz))
    return rows, right


def solve_linear_system(matrix, vector):
    """Solve an n x n linear system by partial-pivot elimination.

    Returns the list of n unknowns. Raises ValueError with message
    "insufficient attitude diversity" when a pivot falls below
    SINGULARITY_TOL relative to the largest matrix entry (numerically
    singular system) or the matrix is all zeros.
    """
    size = len(matrix)
    augmented = [list(matrix[i]) + [vector[i]] for i in range(size)]
    largest = max(abs(entry) for row in matrix for entry in row)
    if largest == 0.0:
        raise ValueError("insufficient attitude diversity")
    for col in range(size):
        pivot_row = max(range(col, size),
                        key=lambda i: abs(augmented[i][col]))
        if abs(augmented[pivot_row][col]) < SINGULARITY_TOL * largest:
            raise ValueError("insufficient attitude diversity")
        if pivot_row != col:
            augmented[col], augmented[pivot_row] = (
                augmented[pivot_row], augmented[col])
        pivot = augmented[col][col]
        for row in range(col + 1, size):
            factor = augmented[row][col] / pivot
            for entry in range(col, size + 1):
                augmented[row][entry] -= factor * augmented[col][entry]
    unknowns = [0.0] * size
    for row in range(size - 1, -1, -1):
        total = augmented[row][size] - sum(
            augmented[row][j] * unknowns[j] for j in range(row + 1, size))
        unknowns[row] = total / augmented[row][row]
    return unknowns


def least_squares_solve(rows, right):
    """Batch least squares over the scalar-checking rows.

    Forms the normal equations A^T A x = A^T y with plain matrix
    multiply and solves them with solve_linear_system, so the rank
    check on A^T A is the attitude-diversity gate. Returns the 4
    unknowns x = [b_x, b_y, b_z, |b|^2].
    """
    transposed = _transpose(rows)
    normal = _mat_mul(transposed, rows)
    normal_right = _mat_vec_mul(transposed, right)
    return solve_linear_system(normal, normal_right)


def residual_norm(rows, right, unknowns):
    """Max over samples of |(A x)_k - y_k|, the fit quality in nT^2."""
    worst = 0.0
    for row, value in zip(rows, right):
        fit = sum(row[j] * unknowns[j] for j in range(len(unknowns)))
        worst = max(worst, abs(fit - value))
    return worst


def estimate_bias(measurements, field_magnitudes):
    """Estimate the in-flight bias vector by scalar checking.

    Returns a dict with keys bias (3-tuple b_x, b_y, b_z, nT),
    bias_norm_nt (recovered |b|), expected_sq_norm (the fourth unknown
    x[3], nT^2, a consistency check that must equal the recovered
    |b|^2), and max_residual (nT^2). Raises ValueError for the design
    or diversity failures of scalar_checking_design and
    least_squares_solve.
    """
    rows, right = scalar_checking_design(measurements, field_magnitudes)
    unknowns = least_squares_solve(rows, right)
    bx, by, bz, expected_sq = unknowns
    bias = (bx, by, bz)
    bias_norm = math.sqrt(bx * bx + by * by + bz * bz)
    return {
        "bias": bias,
        "bias_norm_nt": bias_norm,
        "expected_sq_norm": expected_sq,
        "max_residual": residual_norm(rows, right, unknowns),
    }


def calibrate_measurement(measurement, bias):
    """Subtract the bias elementwise: returns tuple m - b.

    Raises ValueError when the vector lengths differ. The cleaned
    sample estimates the true field h_k and can feed attitude
    determination.
    """
    if len(measurement) != len(bias):
        raise ValueError("measurement and bias vectors must have equal "
                         "length")
    return tuple(mi - bi for mi, bi in zip(measurement, bias))
