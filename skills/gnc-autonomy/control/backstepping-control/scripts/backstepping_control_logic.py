"""Backstepping control law for a second-order strict-feedback plant.

Pure stdlib (math only). See SKILL.md for the workflow and worked example.
"""

import math

C1_WORKED = 2.0
C2_WORKED = 2.0
C_RATE = 4.0
REF_SETPOINT = 1.0
INIT_X1 = 0.0
INIT_X2 = 0.0
DT = 0.001
SIM_TIME = 6.0
SETTLE_LEVEL = 0.01
TOL = 1e-6
KIND_CONST = "constant"
KIND_EXP = "exponential"


def f1(x1):
    """Channel-1 drift, x1^2, a known plant input (workflow step 1)."""
    return x1 * x1


def df1(x1):
    """Analytic derivative of f1, 2 x1, used by the step 4 virtual-control derivative."""
    return 2.0 * x1


def f2(x1, x2):
    """Channel-2 drift, x1 x2, a known plant input (workflow step 1)."""
    return x1 * x2


def reference(t, kind):
    """(x1d, x1d_dot, x1d_ddot) at time t for the given reference kind (workflow step 1)."""
    if kind == KIND_CONST:
        return REF_SETPOINT, 0.0, 0.0
    if kind == KIND_EXP:
        decay = math.exp(-t)
        return REF_SETPOINT * (1.0 - decay), REF_SETPOINT * decay, -REF_SETPOINT * decay
    raise ValueError(f"reference kind must be 'constant' or 'exponential', got {kind!r}")


def tracking_error(x1, x1d):
    """z1 = x1 - x1d, the first error variable (workflow step 2)."""
    return x1 - x1d


def virtual_control(z1, ref_dot, f1_value, c1):
    """alpha1 = -c1 z1 + x1d_dot - f1(x1), the virtual control stabilizing the z1 subsystem (workflow step 2)."""
    if c1 <= 0:
        raise ValueError(f"design gain c1 must be positive, got {c1}")
    return -c1 * z1 + ref_dot - f1_value


def mismatch_error(x2, alpha1):
    """z2 = x2 - alpha1, the inner-state mismatch propagated as the second error variable (workflow step 3)."""
    return x2 - alpha1


def virtual_control_derivative(x1, x2, ref_dot, ref_ddot, c1):
    """alpha1_dot, the analytic derivative of the virtual control along the plant (workflow step 4)."""
    if c1 <= 0:
        raise ValueError(f"design gain c1 must be positive, got {c1}")
    x1_rate = x2 + f1(x1)
    return -c1 * (x1_rate - ref_dot) + ref_ddot - df1(x1) * x1_rate


def final_control(f2_value, alpha1_dot, z1, z2, c2):
    """u = -f2 + alpha1_dot - z1 - c2 z2, the recursive backstepping control law (workflow step 5)."""
    if c2 <= 0:
        raise ValueError(f"design gain c2 must be positive, got {c2}")
    return -f2_value + alpha1_dot - z1 - c2 * z2


def v2_value(z1, z2):
    """V2 = (z1^2 + z2^2)/2, the composite quadratic-Lyapunov function audited in the decay check (workflow step 6)."""
    return (z1 * z1 + z2 * z2) / 2.0


def z1_closed_form(t, z1_0, z2_0, c):
    """Equal-gain closed form for z1(t), e^-ct (z1_0 cos t + z2_0 sin t) (workflow step 7)."""
    decay = math.exp(-c * t)
    return decay * (z1_0 * math.cos(t) + z2_0 * math.sin(t))


def z2_closed_form(t, z1_0, z2_0, c):
    """Equal-gain closed form for z2(t), e^-ct (z2_0 cos t - z1_0 sin t) (workflow step 7)."""
    decay = math.exp(-c * t)
    return decay * (z2_0 * math.cos(t) - z1_0 * math.sin(t))


def v2_closed_form(t, z1_0, z2_0, c):
    """Equal-gain closed form for V2(t), V2(0) e^-2ct (workflow step 7)."""
    v2_0 = (z1_0 * z1_0 + z2_0 * z2_0) / 2.0
    return v2_0 * math.exp(-2.0 * c * t)


def _first_zero_crossing(z1_hist, dt):
    """First index/time where z1 changes sign, the tracking-error zero-crossing milestone (workflow step 7)."""
    for i in range(1, len(z1_hist)):
        prev, cur = z1_hist[i - 1], z1_hist[i]
        if (prev < 0 and cur >= 0) or (prev > 0 and cur <= 0):
            return i, i * dt
    return None, None


def _settle_index(z1_hist, level, dt):
    """First index from which |z1| stays <= level for every later sample, the settle milestone (workflow step 7)."""
    n = len(z1_hist)
    for i in range(n):
        if all(abs(z1_hist[j]) <= level for j in range(i, n)):
            return i, i * dt
    return None, None


def simulate(c1, c2, kind, x1_0=INIT_X1, x2_0=INIT_X2, dt=DT, sim_time=SIM_TIME):
    """Forward-Euler closed-loop simulation under recursive backstepping control (workflow steps 1-6).

    Returns a dict of time histories, the map-residual and Lyapunov-decay
    audits, the closed-form comparison milestones and the final-sample state.
    """
    if c1 <= 0:
        raise ValueError(f"design gain c1 must be positive, got {c1}")
    if c2 <= 0:
        raise ValueError(f"design gain c2 must be positive, got {c2}")
    if dt <= 0:
        raise ValueError(f"sample time dt must be positive, got {dt}")
    if sim_time <= 0:
        raise ValueError(f"simulation time sim_time must be positive, got {sim_time}")
    reference(0.0, kind)

    n = int(round(sim_time / dt)) + 1

    t_hist, x1_hist, x2_hist = [], [], []
    z1_hist, z2_hist, alpha1_hist, alpha1_dot_hist, u_hist, v2_hist, x1d_hist = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )

    x1, x2 = x1_0, x2_0
    for i in range(n):
        t = i * dt
        x1d, ref_dot, ref_ddot = reference(t, kind)
        f1_value = f1(x1)
        f2_value = f2(x1, x2)
        z1 = tracking_error(x1, x1d)
        alpha1 = virtual_control(z1, ref_dot, f1_value, c1)
        z2 = mismatch_error(x2, alpha1)
        alpha1_dot = virtual_control_derivative(x1, x2, ref_dot, ref_ddot, c1)
        u = final_control(f2_value, alpha1_dot, z1, z2, c2)
        v2 = v2_value(z1, z2)

        t_hist.append(t)
        x1_hist.append(x1)
        x2_hist.append(x2)
        z1_hist.append(z1)
        z2_hist.append(z2)
        alpha1_hist.append(alpha1)
        alpha1_dot_hist.append(alpha1_dot)
        u_hist.append(u)
        v2_hist.append(v2)
        x1d_hist.append(x1d)

        if i < n - 1:
            x1_next = x1 + dt * (x2 + f1_value)
            x2_next = x2 + dt * (u + f2_value)
            x1, x2 = x1_next, x2_next

    z1_map_max_res = max(
        abs(z1_hist[i + 1] - (z1_hist[i] + dt * (-c1 * z1_hist[i] + z2_hist[i])))
        for i in range(n - 1)
    )
    z2_map_max_res = max(
        abs(z2_hist[i + 1] - (z2_hist[i] + dt * (-z1_hist[i] - c2 * z2_hist[i])))
        for i in range(n - 1)
    )
    v2dot_res_max = max(
        abs((v2_hist[i + 1] - v2_hist[i]) / dt - (-c1 * z1_hist[i] ** 2 - c2 * z2_hist[i] ** 2))
        for i in range(n - 1)
    )

    first_zero_k, first_zero_t = _first_zero_crossing(z1_hist, dt)
    settle_1pct_k, settle_1pct_t = _settle_index(z1_hist, SETTLE_LEVEL, dt)

    idx_2s = round(2.0 / dt)
    realized_c = -math.log(v2_hist[idx_2s] / v2_hist[0]) / (2.0 * 2.0)

    max_abs_u = max(abs(u) for u in u_hist)

    return {
        "t": t_hist,
        "x1": x1_hist,
        "x2": x2_hist,
        "z1": z1_hist,
        "z2": z2_hist,
        "alpha1": alpha1_hist,
        "alpha1_dot": alpha1_dot_hist,
        "u": u_hist,
        "V2": v2_hist,
        "x1d": x1d_hist,
        "n": n,
        "z1_map_max_res": z1_map_max_res,
        "z2_map_max_res": z2_map_max_res,
        "v2dot_res_max": v2dot_res_max,
        "first_zero_k": first_zero_k,
        "first_zero_t": first_zero_t,
        "settle_1pct_k": settle_1pct_k,
        "settle_1pct_t": settle_1pct_t,
        "realized_c": realized_c,
        "max_abs_u": max_abs_u,
        "final": {
            "x1": x1_hist[-1],
            "x2": x2_hist[-1],
            "z1": z1_hist[-1],
            "z2": z2_hist[-1],
            "alpha1": alpha1_hist[-1],
            "alpha1_dot": alpha1_dot_hist[-1],
            "u": u_hist[-1],
            "V2": v2_hist[-1],
        },
    }
