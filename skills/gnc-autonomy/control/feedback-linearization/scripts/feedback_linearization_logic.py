"""Pure-stdlib input-output feedback linearization of a nonlinear plant.

Plant: xdot1 = -A11 x1 + x2, xdot2 = CUBIC x1^3 + QUAD x2^2 + x1 u,
the affine single-input model xdot = f(x) + g(x) u with g(x) = (0, x1).
Registered outputs: h2 = x2 (relative degree 1), h1 = x1 (relative
degree 2), and the synthetic "const" output (h = 1.0, no finite
relative degree) used to exercise the rejection path.
"""

import math

A11 = 1.0
CUBIC = 1.0
QUAD = 1.0
X1_0 = 0.5
X2_0 = 0.0
Y_REF = 1.0
CL_RATE_K = 2.0
SIM_DT = 0.001
SIM_TIME = 10.0
INV_EPS = 1e-12
N = 2
OUTPUTS = ("x1", "x2", "const")


def _validate_state(x):
    """Reject a state that is not a length-N tuple of real numbers."""
    if len(x) != N:
        raise ValueError("state x must have length %d, got length %d" % (N, len(x)))
    for c in x:
        if isinstance(c, bool) or not isinstance(c, (int, float)):
            raise ValueError("state components must be real numbers, got %r" % (x,))


def _validate_output(output_key):
    """Reject an output key outside the registered set."""
    if output_key not in OUTPUTS:
        raise ValueError("unknown output '%s': registered outputs are x1, x2, const" % (output_key,))


def f(x):
    """Drift vector field f(x) = (-A11 x1 + x2, CUBIC x1^3 + QUAD x2^2)."""
    _validate_state(x)
    x1, x2 = x
    return (-A11 * x1 + x2, CUBIC * x1 ** 3 + QUAD * x2 ** 2)


def g(x):
    """Control vector field g(x) = (0, x1), vanishing at x1 = 0."""
    _validate_state(x)
    return (0.0, x[0])


def Lf_power_h(output_key, x, k):
    """k-th Lie derivative L_f^k h(x) for k in {0, 1, 2}, analytic chain rule."""
    _validate_output(output_key)
    _validate_state(x)
    if k not in (0, 1, 2):
        raise ValueError("Lie derivative order k must be in 0..%d, got %s" % (N, k))
    x1, x2 = x
    f1, f2 = f(x)
    if output_key == "x1":
        if k == 0:
            return x1
        if k == 1:
            return f1
        return -A11 * f1 + f2
    if output_key == "x2":
        if k == 0:
            return x2
        if k == 1:
            return f2
        return 3.0 * CUBIC * x1 ** 2 * f1 + 2.0 * QUAD * x2 * f2
    return 1.0 if k == 0 else 0.0


def _dLf_power_h_dx2(output_key, x, k):
    """Partial derivative of L_f^k h with respect to x2, for k in {0, 1}."""
    x1, x2 = x
    if output_key == "x2":
        return 1.0 if k == 0 else 2.0 * QUAD * x2
    if output_key == "x1":
        return 0.0 if k == 0 else 1.0
    return 0.0


def Lg_Lf_power_h(output_key, x, k):
    """Relative-degree probe L_g L_f^k h(x) = <d(L_f^k h)(x), g(x)>."""
    _validate_output(output_key)
    _validate_state(x)
    if k not in range(N):
        raise ValueError("relative-degree probe order k must be in 0..%d, got %s" % (N - 1, k))
    x1 = x[0]
    return x1 * _dLf_power_h_dx2(output_key, x, k)


def relative_degree(output_key, x):
    """Relative degree r and the probe table [(k, L_g L_f^k h)] for k = 0..r-1."""
    _validate_output(output_key)
    _validate_state(x)
    table = []
    for k in range(N):
        probe = Lg_Lf_power_h(output_key, x, k)
        table.append((k, probe))
        if abs(probe) > INV_EPS:
            return k + 1, table
    raise ValueError(
        "no finite relative degree at state x = (%s, %s) for output '%s': "
        "L_g L_f^k h = 0 for every k up to the system order N = %d, so the "
        "control channel never reaches the output at this state" % (x[0], x[1], output_key, N)
    )


def decoupling_scalar(output_key, x):
    """Decoupling scalar a(x) = L_g L_f^(r-1) h, the last probe-table entry."""
    _, table = relative_degree(output_key, x)
    return table[-1][1]


def linearizing_control_from(Lf_r_h, decoupling, v):
    """Pure algebra u = (v - L_f^r h) / a; rejects a non-invertible decoupling scalar."""
    if abs(decoupling) <= INV_EPS:
        raise ValueError(
            "decoupling scalar a(x) = %s is zero (|a| <= INV_EPS = %s): the "
            "linearizing control u = (v - L_f^r h) / a(x) is not defined" % (decoupling, INV_EPS)
        )
    return (v - Lf_r_h) / decoupling


def linearizing_control(output_key, x, v):
    """State-level linearizing control: computes L_f^r h and a(x), then inverts."""
    r, table = relative_degree(output_key, x)
    Lf_r_h = Lf_power_h(output_key, x, r)
    a = table[-1][1]
    return linearizing_control_from(Lf_r_h, a, v)


def outer_command(output_key, x, y_ref=Y_REF, k=CL_RATE_K):
    """Outer linear command v on the linearized channel y^(r) = v."""
    if output_key not in ("x1", "x2"):
        raise ValueError("unknown output '%s': registered outputs are x1, x2, const" % (output_key,))
    _validate_state(x)
    x1, x2 = x
    if output_key == "x2":
        return -k * (x2 - y_ref)
    f1, _ = f(x)
    return -(k ** 2) * (x1 - y_ref) - 2.0 * k * f1


def _closed_loop_derivative(output_key, x, y_ref, k):
    """Closed-loop state derivative xdot = f(x) + g(x) u(x) with u(x) the
    state-feedback linearizing control, recomputed fresh at x (continuous
    feedback, not held from an earlier sample)."""
    v = outer_command(output_key, x, y_ref, k)
    u = linearizing_control(output_key, x, v)
    f1, f2 = f(x)
    return (f1, f2 + x[0] * u)


def _rk4_step(output_key, x, y_ref, k, dt):
    """One classical RK4 step of the closed loop, the control law evaluated
    fresh at each of the four stage states."""
    k1 = _closed_loop_derivative(output_key, x, y_ref, k)
    xb = (x[0] + dt / 2.0 * k1[0], x[1] + dt / 2.0 * k1[1])
    k2 = _closed_loop_derivative(output_key, xb, y_ref, k)
    xc = (x[0] + dt / 2.0 * k2[0], x[1] + dt / 2.0 * k2[1])
    k3 = _closed_loop_derivative(output_key, xc, y_ref, k)
    xd = (x[0] + dt * k3[0], x[1] + dt * k3[1])
    k4 = _closed_loop_derivative(output_key, xd, y_ref, k)
    nx1 = x[0] + dt / 6.0 * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0])
    nx2 = x[1] + dt / 6.0 * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1])
    return (nx1, nx2)


def closed_loop_sim(output_key, x0=None, y_ref=Y_REF, k=CL_RATE_K, dt=SIM_DT, sim_time=SIM_TIME):
    """RK4 closed-loop simulation under the active linearizing law."""
    if output_key not in ("x1", "x2"):
        raise ValueError("unknown output '%s': registered outputs are x1, x2, const" % (output_key,))
    if y_ref <= 0:
        raise ValueError("reference y_ref must be positive, got %s" % (y_ref,))
    if k <= 0:
        raise ValueError("closed-loop rate k must be positive, got %s" % (k,))
    if dt <= 0:
        raise ValueError("sample time dt must be positive, got %s" % (dt,))
    if sim_time <= 0:
        raise ValueError("simulation time sim_time must be positive, got %s" % (sim_time,))
    x0 = (X1_0, X2_0) if x0 is None else x0
    _validate_state(x0)

    n = int(round(sim_time / dt)) + 1
    t, y, x1_series, x2_series, u_series = [], [], [], [], []
    x = x0
    for i in range(n):
        v = outer_command(output_key, x, y_ref, k)
        u = linearizing_control(output_key, x, v)
        y_val = x[1] if output_key == "x2" else x[0]
        t.append(i * dt)
        y.append(y_val)
        x1_series.append(x[0])
        x2_series.append(x[1])
        u_series.append(u)
        if i < n - 1:
            x = _rk4_step(output_key, x, y_ref, k, dt)
    return {"t": t, "y": y, "x1": x1_series, "x2": x2_series, "u": u_series}


def closed_form_r1(t, x0=None, y_ref=Y_REF, k=CL_RATE_K):
    """Closed form of the r = 1 exactly linearized loop: y(t) = y_ref + (y0 - y_ref) exp(-k t)."""
    x0 = (X1_0, X2_0) if x0 is None else x0
    return y_ref + (x0[1] - y_ref) * math.exp(-k * t)


def closed_form_r2(t, x0=None, y_ref=Y_REF, k=CL_RATE_K):
    """Closed form of the r = 2 exactly linearized loop, the double-pole response."""
    x0 = (X1_0, X2_0) if x0 is None else x0
    y0 = x0[0]
    ydot0 = -A11 * x0[0] + x0[1]
    a_coeff = y0 - y_ref
    b_coeff = ydot0 + k * (y0 - y_ref)
    return y_ref + (a_coeff + b_coeff * t) * math.exp(-k * t)


def series_max_abs_error(series, closed_form, t):
    """Max over samples of |series[i] - closed_form(t[i])|."""
    return max(abs(series[i] - closed_form(t[i])) for i in range(len(t)))


def sample_series(t, series, times):
    """Series value at each requested sample time (nearest recorded sample)."""
    dt = t[1] - t[0] if len(t) > 1 else 1.0
    result = []
    for time in times:
        idx = int(round((time - t[0]) / dt))
        idx = max(0, min(len(t) - 1, idx))
        result.append(series[idx])
    return result


def measured_decay_rate(y, t, t1, t2, y_ref=Y_REF):
    """Closed-loop pole witness -(ln|e(t2)| - ln|e(t1)|) / (t2 - t1) on e = y - y_ref."""
    y1, y2 = sample_series(t, y, [t1, t2])
    e1 = y1 - y_ref
    e2 = y2 - y_ref
    return -(math.log(abs(e2)) - math.log(abs(e1))) / (t2 - t1)


def zero_dynamics_analysis(x0=None):
    """Zero-dynamics stability check of the r = 1 design: x1dot = -A11 x1."""
    x0 = (X1_0, X2_0) if x0 is None else x0
    eigenvalue = -A11
    verdict = "asymptotically stable" if eigenvalue < 0 else "unstable"
    t = [float(i) for i in range(int(SIM_TIME) + 1)]
    x1 = [x0[0] * math.exp(eigenvalue * ti) for ti in t]
    return {"eigenvalue": eigenvalue, "verdict": verdict, "t": t, "x1": x1}
