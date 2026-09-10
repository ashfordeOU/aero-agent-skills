"""Tuning-functions adaptive backstepping for a second-order strict-feedback plant.

Pure stdlib (math only). See SKILL.md for the workflow and worked example.
"""

import math

THETA_TRUE = 1.0
C1_WORKED = 2.0
C2_WORKED = 2.0
C_RATE = 4.0
GAMMA_WORKED = 5.0
GAMMA_RATE = 10.0
GAMMA_ZERO = 0.0
GAMMA_PE = 20.0
REF_SETPOINT = 1.0
SIN_AMP = 1.0
SIN_OMEGA = 1.0
INIT_X1 = 0.0
INIT_X2 = 0.0
INIT_TH = 0.0
INIT_TH_KNOWN = 1.0
DT = 0.001
SIM_TIME = 10.0
RATE_TIME = 6.0
PE_TIME = 40.0
TOL = 1e-6
KIND_CONST = "constant"
KIND_SIN = "sinusoidal"


def f1(x1):
    """Channel-1 drift shape, x1^2, multiplied by the unknown theta (workflow step 1)."""
    return x1 * x1


def df1(x1):
    """Analytic derivative of f1, 2 x1, used by the step 4 design-model derivative."""
    return 2.0 * x1


def f2(x1, x2):
    """Channel-2 drift, x1 x2, known exactly and theta-free (workflow step 1)."""
    return x1 * x2


def w1_regressor(x1):
    """Regressor of the unknown parameter in the z1 channel, w1 = f1(x1) (workflow step 2)."""
    return f1(x1)


def omega2_regressor(x1, theta_hat, c1):
    """Tuning-function regressor in the z2 channel, w2 = (c1 + theta_hat df1(x1)) w1
    (workflow step 5, the positive convention that cancels the parameter-mismatch
    terms out of z2_dot)."""
    return (c1 + theta_hat * df1(x1)) * w1_regressor(x1)


def reference(t, kind):
    """(x1d, x1d_dot, x1d_ddot) at time t for the given reference kind (workflow step 1)."""
    if kind == KIND_CONST:
        return REF_SETPOINT, 0.0, 0.0
    if kind == KIND_SIN:
        s = math.sin(SIN_OMEGA * t)
        c = math.cos(SIN_OMEGA * t)
        return SIN_AMP * s, SIN_AMP * SIN_OMEGA * c, -SIN_AMP * SIN_OMEGA * SIN_OMEGA * s
    raise ValueError(f"reference kind must be 'constant' or 'sinusoidal', got {kind!r}")


def tracking_error(x1, x1d):
    """z1 = x1 - x1d, the first error variable (workflow step 2)."""
    return x1 - x1d


def alpha1_value(z1, ref_dot, theta_hat, w1, c1):
    """Virtual control alpha1 = -c1 z1 + ref_dot - theta_hat w1 (workflow step 2)."""
    if c1 <= 0:
        raise ValueError(f"design gain c1 must be positive, got {c1}")
    return -c1 * z1 + ref_dot - theta_hat * w1


def mismatch_error(x2, alpha1):
    """z2 = x2 - alpha1, the second error variable (workflow step 3)."""
    return x2 - alpha1


def alpha1_dot_adaptive(x1, x2, ref_dot, ref_ddot, theta_hat, th_dot, c1):
    """Design-model derivative of the virtual control, evaluated with theta_hat as the
    plant coefficient since theta is unknown to the controller (workflow step 4)."""
    if c1 <= 0:
        raise ValueError(f"design gain c1 must be positive, got {c1}")
    x1_rate = x2 + theta_hat * w1_regressor(x1)
    return (-(c1 + theta_hat * df1(x1)) * x1_rate
            + c1 * ref_dot + ref_ddot - th_dot * w1_regressor(x1))


def tau1_value(z1, w1, gamma):
    """First tuning function tau1 = gamma z1 w1 (workflow step 5)."""
    return gamma * z1 * w1


def tau2_value(z1, z2, w1, w2, gamma):
    """Second tuning function tau2 = gamma (z1 w1 + z2 w2), the single estimator
    update carried through the recursion (workflow step 5)."""
    return gamma * (z1 * w1 + z2 * w2)


def final_control(f2_value, alpha1_dot, z1, z2, c2):
    """u = -f2_value + alpha1_dot - z1 - c2 z2, the adaptive backstepping control law
    (workflow step 6)."""
    if c2 <= 0:
        raise ValueError(f"design gain c2 must be positive, got {c2}")
    return -f2_value + alpha1_dot - z1 - c2 * z2


def v2_value(z1, z2, theta_tilde, gamma):
    """Augmented Lyapunov function V2 = (z1^2 + z2^2)/2 + theta_tilde^2/(2 gamma),
    audited for monotone decay in workflow step 7."""
    if gamma <= 0:
        raise ValueError(f"adaptation gain gamma must be positive, got {gamma}")
    return 0.5 * (z1 * z1 + z2 * z2) + theta_tilde * theta_tilde / (2.0 * gamma)


def _step(x1, x2, theta_hat, t, kind, c1, c2, gamma):
    """One controller evaluation at the current state (workflow steps 1-6): forms
    z1, alpha1, z2, the tuning functions, alpha1_dot and the final control u."""
    x1d, ref_dot, ref_ddot = reference(t, kind)
    z1 = tracking_error(x1, x1d)
    w1 = w1_regressor(x1)
    alpha1 = alpha1_value(z1, ref_dot, theta_hat, w1, c1)
    z2 = mismatch_error(x2, alpha1)
    w2 = omega2_regressor(x1, theta_hat, c1)
    tau1 = tau1_value(z1, w1, gamma)
    tau2 = tau2_value(z1, z2, w1, w2, gamma)
    alpha1_dot = alpha1_dot_adaptive(x1, x2, ref_dot, ref_ddot, theta_hat, tau2, c1)
    u = final_control(f2(x1, x2), alpha1_dot, z1, z2, c2)
    return x1d, z1, alpha1, z2, tau1, tau2, alpha1_dot, u


def _audit(z1_hist, z2_hist, v2_hist, c1, c2, dt):
    """Map-residual and Lyapunov-decay audit over a completed run (workflow step 7)."""
    n = len(z1_hist)
    z1_map_max = 0.0
    z2_map_max = 0.0
    v2dot_res_max = 0.0
    v2_mono_viol = 0
    for k in range(n - 1):
        r1 = abs(z1_hist[k + 1] - (z1_hist[k] + dt * (-c1 * z1_hist[k] + z2_hist[k])))
        z1_map_max = max(z1_map_max, r1)
        r2 = abs(z2_hist[k + 1] - (z2_hist[k] + dt * (-z1_hist[k] - c2 * z2_hist[k])))
        z2_map_max = max(z2_map_max, r2)
        dv = (v2_hist[k + 1] - v2_hist[k]) / dt
        rhs = -c1 * z1_hist[k] * z1_hist[k] - c2 * z2_hist[k] * z2_hist[k]
        v2dot_res_max = max(v2dot_res_max, abs(dv - rhs))
        if v2_hist[k + 1] > v2_hist[k] + TOL:
            v2_mono_viol += 1
    return z1_map_max, z2_map_max, v2dot_res_max, v2_mono_viol


def simulate(c1, c2, gamma, kind, x1_0=INIT_X1, x2_0=INIT_X2, th_0=INIT_TH,
             dt=DT, sim_time=SIM_TIME):
    """Forward-Euler closed-loop simulation under tuning-functions adaptive
    backstepping control (workflow steps 1-7). The plant is integrated with the
    true parameter THETA_TRUE; the controller sees only theta_hat.

    Returns a dict of time histories, the map-residual and augmented-Lyapunov
    audits described in the SKILL.md workflow.
    """
    if c1 <= 0:
        raise ValueError(f"design gain c1 must be positive, got {c1}")
    if c2 <= 0:
        raise ValueError(f"design gain c2 must be positive, got {c2}")
    if gamma < 0:
        raise ValueError(f"adaptation gain gamma must be non-negative, got {gamma}")
    if dt <= 0:
        raise ValueError(f"sample time dt must be positive, got {dt}")
    if sim_time <= 0:
        raise ValueError(f"simulation time sim_time must be positive, got {sim_time}")
    reference(0.0, kind)

    n = int(round(sim_time / dt)) + 1
    x1_hist = [0.0] * n
    x2_hist = [0.0] * n
    th_hist = [0.0] * n
    z1_hist = [0.0] * n
    z2_hist = [0.0] * n
    alpha1_hist = [0.0] * n
    a1d_hist = [0.0] * n
    u_hist = [0.0] * n
    v2_hist = [0.0] * n
    tau1_hist = [0.0] * n
    tau2_hist = [0.0] * n
    x1d_hist = [0.0] * n

    x1, x2, th = x1_0, x2_0, th_0
    for k in range(n):
        t = k * dt
        x1d, z1, alpha1, z2, tau1, tau2, a1d, u = _step(x1, x2, th, t, kind, c1, c2, gamma)
        theta_tilde = THETA_TRUE - th
        v2 = v2_value(z1, z2, theta_tilde, gamma) if gamma > 0 else 0.5 * (z1 * z1 + z2 * z2)

        x1_hist[k], x2_hist[k], th_hist[k] = x1, x2, th
        z1_hist[k], z2_hist[k] = z1, z2
        alpha1_hist[k], a1d_hist[k], u_hist[k] = alpha1, a1d, u
        v2_hist[k], tau1_hist[k], tau2_hist[k] = v2, tau1, tau2
        x1d_hist[k] = x1d

        if k < n - 1:
            x1_next = x1 + dt * (x2 + THETA_TRUE * f1(x1))
            x2_next = x2 + dt * (u + f2(x1, x2))
            th_next = th + dt * tau2
            x1, x2, th = x1_next, x2_next, th_next

    z1_map_max, z2_map_max, v2dot_res_max, v2_mono_viol = _audit(
        z1_hist, z2_hist, v2_hist, c1, c2, dt)

    return {
        "n": n, "x1": x1_hist, "x2": x2_hist, "th": th_hist,
        "z1": z1_hist, "z2": z2_hist, "alpha1": alpha1_hist, "a1d": a1d_hist,
        "u": u_hist, "v2": v2_hist, "tau1": tau1_hist, "tau2": tau2_hist,
        "x1d": x1d_hist,
        "z1_map_max": z1_map_max, "z2_map_max": z2_map_max,
        "v2dot_res_max": v2dot_res_max, "v2_mono_viol": v2_mono_viol,
    }


def state_decay_rate(res, t0, t1, dt=DT):
    """Realized decay rate of the state error energy (z1^2 + z2^2)/2 over
    [t0, t1] (workflow step 7 rate audit)."""
    k0 = int(round(t0 / dt))
    k1 = int(round(t1 / dt))
    v0 = 0.5 * (res["z1"][k0] ** 2 + res["z2"][k0] ** 2)
    v1 = 0.5 * (res["z1"][k1] ** 2 + res["z2"][k1] ** 2)
    return -math.log(v1 / v0) / (2.0 * (t1 - t0))


def sample(res, t, dt=DT):
    """Snapshot dict at the sample time t, nearest index (workflow step 7)."""
    k = int(round(t / dt))
    return {
        "t": k * dt, "k": k, "x1": res["x1"][k], "x2": res["x2"][k],
        "th": res["th"][k], "z1": res["z1"][k], "z2": res["z2"][k],
        "alpha1": res["alpha1"][k], "a1d": res["a1d"][k], "u": res["u"][k],
        "v2": res["v2"][k], "x1d": res["x1d"][k],
        "tau1": res["tau1"][k], "tau2": res["tau2"][k],
    }
