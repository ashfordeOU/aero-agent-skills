"""Deadbeat digital control design for a discrete-time plant, stdlib only.

Direct deadbeat synthesis from a plant pulse transfer function G(z) =
B(z)/A(z): places every closed loop pole at the origin of the z plane so
the step response settles in a finite number of samples. Pure Python,
math module only, deterministic, no RNG, no external processes.
"""

import math

# Module constants: worked-example plants pinned to the leaf engineering spec.
FIRST_ORDER_A = [1.0, -0.5]
FIRST_ORDER_B = [0.5]
FIRST_ORDER_TS = 0.1

SECOND_ORDER_A = [1.0, -1.1, 0.24]
SECOND_ORDER_B = [0.2]
SECOND_ORDER_TS = 0.02

ZERO_A = [1.0, -1.1, 0.24]
ZERO_B = [0.1, 0.05]
ZERO_TS = 0.02

COMPLEX_POLE_A = [1.0, -1.6, 0.65]
COMPLEX_POLE_B = [0.1]

UNSTABLE_A = [1.0, -2.5, 1.0]
BOUNDARY_A = [1.0, -2.1, 1.1]
NONMINIMUM_PHASE_B = [1.0, 2.0]
BOUNDARY_ZERO_B = [1.0, -1.0]
DEG3_A = [1.0, -1.1, 0.24, 0.1]
NOT_STRICTLY_PROPER = ([1.0, -0.5], [1.0, 1.0])

N_STEPS = 40
SETTLE_TOL = 1e-9


def _validate_plant(A, B):
    """Structural checks shared by admissibility_check, deadbeat_design and steady_control."""
    if not A or not B:
        raise ValueError("plant polynomials A and B must be non-empty")
    if A[0] == 0.0:
        raise ValueError("plant denominator A must have a nonzero leading coefficient")
    n = len(A) - 1
    if n < 1 or n > 2:
        raise ValueError("plant order must be first or second order (1 <= deg A <= 2)")
    m = len(B) - 1
    if m >= n:
        raise ValueError("plant numerator degree must be strictly less than the denominator degree (strictly proper)")
    return n, m


def _at(history, idx):
    """History lookup with zero-fill for negative or not-yet-reached indices."""
    if idx < 0 or idx >= len(history):
        return 0.0
    return history[idx]


def polyval_desc(coeffs, z):
    """Horner evaluation of a descending-power polynomial at z."""
    if not coeffs:
        raise ValueError("coeffs must be non-empty")
    result = 0.0
    for c in coeffs:
        result = result * z + c
    return result


def poly_mul_desc(p, q):
    """Descending-power polynomial product (plain convolution)."""
    if not p or not q:
        raise ValueError("p and q must be non-empty")
    result = [0.0] * (len(p) + len(q) - 1)
    for i, pi in enumerate(p):
        for j, qj in enumerate(q):
            result[i + j] += pi * qj
    return result


def roots_moduli_desc(coeffs):
    """Closed-form root moduli of a descending-power polynomial, degree 1 or 2 only."""
    if not coeffs:
        raise ValueError("coeffs must be non-empty")
    degree = len(coeffs) - 1
    if degree == 0:
        return []
    if degree == 1:
        a, b = coeffs
        return [abs(-b / a)]
    if degree == 2:
        a, b, c = coeffs
        disc = b * b - 4.0 * a * c
        if disc >= 0.0:
            sign_b = 1.0 if b >= 0.0 else -1.0
            sqrt_disc = math.sqrt(disc)
            q = -0.5 * (b + sign_b * sqrt_disc)
            if q == 0.0:
                return [0.0, 0.0]
            root1 = q / a
            root2 = c / q
            return [abs(root1), abs(root2)]
        real = -b / (2.0 * a)
        imag = math.sqrt(-disc) / (2.0 * a)
        modulus = math.sqrt(real * real + imag * imag)
        return [modulus, modulus]
    raise ValueError("roots_moduli_desc supports degree 1 or 2 only")


def admissibility_check(A, B):
    """Deadbeat admissibility gate: every plant pole and zero strictly inside the unit circle."""
    _validate_plant(A, B)
    pole_moduli = roots_moduli_desc(A)
    zero_moduli = roots_moduli_desc(B)
    unstable = [x for x in pole_moduli if x >= 1.0]
    nonminimum = [x for x in zero_moduli if x >= 1.0]
    admissible = not unstable and not nonminimum
    if admissible:
        reason = "plant stable and minimum phase: every pole and zero modulus is strictly below 1.0"
    else:
        parts = []
        if unstable:
            parts.append("unstable or boundary pole modulus >= 1.0: " + str(unstable))
        if nonminimum:
            parts.append("non-minimum-phase or boundary zero modulus >= 1.0: " + str(nonminimum))
        reason = "; ".join(parts)
    return {
        "admissible": admissible,
        "pole_moduli": pole_moduli,
        "zero_moduli": zero_moduli,
        "reason": reason,
    }


def deadbeat_design(A, B):
    """Solve the deadbeat design equation and return the controller and closed-loop terms."""
    n, m = _validate_plant(A, B)
    scale = A[0]
    a_desc = [a / scale for a in A]
    b_desc = [b / scale for b in B]
    verdict = admissibility_check(a_desc, b_desc)
    if not verdict["admissible"]:
        raise ValueError("plant fails deadbeat admissibility: " + verdict["reason"])
    d = n - m
    mu0 = b_desc[0]
    num_e = [a / mu0 for a in a_desc]
    beta_padded = list(b_desc) + [0.0] * d
    den_u = []
    for j in range(1, m + d + 1):
        beta_j = beta_padded[j]
        idx = j - d
        beta_jd = beta_padded[idx] if idx >= 0 else 0.0
        mu_j = beta_j - beta_jd
        den_u.append(-mu_j / mu0)
    z_dminus1_desc = [1.0] + [0.0] * (d - 1) + [-1.0]
    d_num_desc = a_desc
    d_den_desc = poly_mul_desc(b_desc, z_dminus1_desc)
    z_d_desc = [1.0] + [0.0] * d
    char_poly_desc = poly_mul_desc(poly_mul_desc(a_desc, b_desc), z_d_desc)
    u_star = polyval_desc(a_desc, 1.0) / polyval_desc(b_desc, 1.0)
    plant_dc_gain = polyval_desc(b_desc, 1.0) / polyval_desc(a_desc, 1.0)
    return {
        "n": n,
        "m": m,
        "d": d,
        "a_desc": a_desc,
        "b_desc": b_desc,
        "num_e": num_e,
        "den_u": den_u,
        "mu0": mu0,
        "d_num_desc": d_num_desc,
        "d_den_desc": d_den_desc,
        "char_poly_desc": char_poly_desc,
        "u_star": u_star,
        "plant_dc_gain": plant_dc_gain,
    }


def simulate(A, B, ts=1.0, steps=N_STEPS, r=1.0, reference="step"):
    """Closed-loop deadbeat simulation: pinned per-sample plant/error/control ordering."""
    if ts <= 0:
        raise ValueError("sample time ts must be positive")
    if steps < 2:
        raise ValueError("steps must be at least 2")
    if reference not in ("step", "impulse"):
        raise ValueError("reference must be 'step' or 'impulse'")
    design = deadbeat_design(A, B)
    n, m, d = design["n"], design["m"], design["d"]
    a_desc, b_desc = design["a_desc"], design["b_desc"]
    num_e, den_u = design["num_e"], design["den_u"]
    y, e, u = [], [], []
    for k in range(steps):
        if reference == "step":
            r_k = r
        else:
            r_k = r if k == 0 else 0.0
        y_k = -sum(a_desc[i] * _at(y, k - i) for i in range(1, n + 1))
        y_k += sum(b_desc[j] * _at(u, k - d - j) for j in range(0, m + 1))
        y.append(y_k)
        e_k = r_k - y_k
        e.append(e_k)
        u_k = sum(num_e[i] * _at(e, k - i) for i in range(0, n + 1))
        u_k += sum(den_u[j] * _at(u, k - 1 - j) for j in range(0, m + d))
        u.append(u_k)
    return {"y": y, "e": e, "u": u, "k": list(range(steps))}


def settling_report(res, d, ts, r=1.0, tol=SETTLE_TOL):
    """Settling sample, settling time and the post-settling tracking check."""
    if ts <= 0:
        raise ValueError("sample time ts must be positive")
    y = res["y"]
    e = res["e"]
    if len(y) <= d or len(e) <= d:
        raise ValueError("history too short to cover the settling sample d")
    y_at_settling = y[d]
    max_dev = max(abs(y[k] - r) for k in range(d, len(y)))
    settled = all(abs(y[k] - r) <= tol and abs(e[k]) <= tol for k in range(d, len(y)))
    return {
        "settling_sample": d,
        "settling_time_s": float(d * ts),
        "y_at_settling": y_at_settling,
        "max_dev_after_settling": max_dev,
        "settled": settled,
    }


def steady_control(A, B):
    """Steady control u* = A(1)/B(1) that holds the output at the reference."""
    _validate_plant(A, B)
    scale = A[0]
    a_desc = [a / scale for a in A]
    b_desc = [b / scale for b in B]
    b1 = polyval_desc(b_desc, 1.0)
    if b1 == 0.0:
        raise ValueError("plant DC gain is infinite: B(1) == 0")
    return polyval_desc(a_desc, 1.0) / b1


def control_effort(u):
    """Initial control sample, peak magnitude and final control sample."""
    return {"u0": u[0], "max_abs_u": max(abs(x) for x in u), "u_final": u[-1]}


def closed_loop_impulse(A, B, steps=N_STEPS):
    """Closed-loop impulse response: the pure-delay identity check."""
    return simulate(A, B, ts=1.0, steps=steps, r=1.0, reference="impulse")
