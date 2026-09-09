"""Sliding-mode control law for a second-order plant with matched uncertainty.

Pure stdlib (math only). See SKILL.md for the workflow and worked example.
"""

import math

LAMBDA = 2.0
ETA = 1.5
WORKED_F = 0.5
WORKED_K = 2.0
ROBUST_F = 0.9
ROBUST_K = 2.4
WORKED_PHI = 0.05
SIGN_PHI = 0.0
WORKED_D = 0.5
ROBUST_D = 0.9
REFERENCE_XD = 1.0
INIT_X = 0.0
INIT_V = 0.0
DT = 0.001
SIM_TIME = 6.0
JUMP_THRESHOLD = 0.5
TOL = 1e-6


def sliding_surface(err, err_dot, lam):
    """s = err_dot + lam * err (workflow step 1)."""
    if lam <= 0:
        raise ValueError(f"surface coefficient lambda must be positive, got {lam}")
    return err_dot + lam * err


def sat_value(s, phi):
    """Saturation of s/phi in [-1, 1]; phi = 0 gives the ideal sign (workflow step 2)."""
    if phi < 0:
        raise ValueError(f"boundary-layer thickness phi must be non-negative, got {phi}")
    if phi == 0.0:
        if s > 0:
            return 1.0
        if s < 0:
            return -1.0
        return 0.0
    if abs(s) <= phi:
        return s / phi
    return 1.0 if s > 0 else -1.0


def equivalent_control(f_nominal, ref_ddot, err_dot, lam):
    """u_eq holding s_dot = 0 on the nominal model (workflow step 3)."""
    if lam <= 0:
        raise ValueError(f"surface coefficient lambda must be positive, got {lam}")
    return -f_nominal + ref_ddot - lam * err_dot


def switched_term(s, k, phi):
    """u_sw = -k * sat(s/phi), the reaching-law switching term (workflow step 4)."""
    if phi < 0:
        raise ValueError(f"boundary-layer thickness phi must be non-negative, got {phi}")
    if k <= 0:
        raise ValueError(f"switching gain k must be positive, got {k}")
    return -k * sat_value(s, phi)


def sliding_condition_margin(s, s_dot, eta):
    """Margin of s*s_dot <= -eta*|s|; non-negative exactly when the condition holds (workflow step 5)."""
    return -(s * s_dot) - eta * abs(s)


def simulate_sliding_control(
    lam=LAMBDA,
    k=WORKED_K,
    phi=WORKED_PHI,
    bound_f=WORKED_F,
    disturbance_d=WORKED_D,
    x0=INIT_X,
    v0=INIT_V,
    xd=REFERENCE_XD,
    dt=DT,
    sim_time=SIM_TIME,
):
    """Forward-Euler closed-loop simulation under sliding control (workflow steps 1-7).

    Returns a dict of time histories, the reach sample, the sliding-condition
    audit, the surface-rate law residual and the chattering-suppression counts.
    """
    if lam <= 0:
        raise ValueError(f"surface coefficient lambda must be positive, got {lam}")
    if phi < 0:
        raise ValueError(f"boundary-layer thickness phi must be non-negative, got {phi}")
    if bound_f < 0:
        raise ValueError(f"matched-uncertainty bound F must be non-negative, got {bound_f}")
    if k <= bound_f:
        raise ValueError(
            f"switching gain k must exceed the matched-uncertainty bound F, got k {k} <= F {bound_f}"
        )
    if abs(disturbance_d) > bound_f:
        raise ValueError(
            f"disturbance magnitude D must not exceed the matched-uncertainty bound F, got D {disturbance_d} > F {bound_f}"
        )
    if dt <= 0:
        raise ValueError(f"sample time dt must be positive, got {dt}")
    if sim_time <= 0:
        raise ValueError(f"simulation time sim_time must be positive, got {sim_time}")

    n = int(round(sim_time / dt)) + 1
    eta_cert = k - bound_f

    t_hist, x_hist, v_hist, e_hist, s_hist = [], [], [], [], []
    ueq_hist, usw_hist, u_hist, sdot_hist = [], [], [], []

    x, v = x0, v0
    for i in range(n):
        t = i * dt
        e = x - xd
        s = sliding_surface(e, v, lam)
        u_eq = equivalent_control(-v, 0.0, v, lam)
        u_sw = switched_term(s, k, phi)
        u = u_eq + u_sw
        s_dot = disturbance_d + u + (lam - 1.0) * v

        t_hist.append(t)
        x_hist.append(x)
        v_hist.append(v)
        e_hist.append(e)
        s_hist.append(s)
        ueq_hist.append(u_eq)
        usw_hist.append(u_sw)
        u_hist.append(u)
        sdot_hist.append(s_dot)

        if i < n - 1:
            x_next = x + dt * v
            v_next = v + dt * (-v + disturbance_d + u)
            x, v = x_next, v_next

    reach_idx = None
    for i in range(n):
        if abs(s_hist[i]) <= phi:
            reach_idx = i
            break
    reach_t = reach_idx * dt if reach_idx is not None else None

    outside_idx = [i for i in range(n) if abs(s_hist[i]) > phi]
    outside = len(outside_idx)
    margins = [sliding_condition_margin(s_hist[i], sdot_hist[i], eta_cert) for i in outside_idx]
    worst_margin = min(margins) if margins else float("inf")
    violations = sum(1 for m in margins if m < -TOL)

    law_max_res = max(
        abs(sdot_hist[i] - (disturbance_d - k * sat_value(s_hist[i], phi))) for i in range(n)
    )

    jumps = 0
    max_du = 0.0
    sign_changes = 0
    if reach_idx is not None:
        for i in range(max(reach_idx, 1), n):
            du = abs(u_hist[i] - u_hist[i - 1])
            if du > JUMP_THRESHOLD:
                jumps += 1
            if du > max_du:
                max_du = du
            prev_s, cur_s = s_hist[i - 1], s_hist[i]
            if (prev_s < 0 and cur_s > 0) or (prev_s > 0 and cur_s < 0):
                sign_changes += 1

    return {
        "t": t_hist,
        "x": x_hist,
        "v": v_hist,
        "e": e_hist,
        "s": s_hist,
        "u_eq": ueq_hist,
        "u_sw": usw_hist,
        "u": u_hist,
        "s_dot": sdot_hist,
        "eta_cert": eta_cert,
        "reach_idx": reach_idx,
        "reach_t": reach_t,
        "outside": outside,
        "worst_margin": worst_margin,
        "violations": violations,
        "law_max_res": law_max_res,
        "jumps": jumps,
        "max_du": max_du,
        "sign_changes": sign_changes,
        "n": n,
    }
