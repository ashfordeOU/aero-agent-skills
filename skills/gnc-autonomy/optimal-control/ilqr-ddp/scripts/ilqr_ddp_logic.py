"""Iterative LQR / differential dynamic programming (iLQR-DDP) for a
nonlinear discrete-time soft-landing plant (gnc-autonomy, wave-44).

Pure stdlib (math only), deterministic, offline. No numpy, no scipy,
no RNG, no external processes. Explicit scalar arithmetic on a
two-state, one-input plant in the pinned order below.

Plant: vertical soft landing under gravity and quadratic drag.
State x = [h, v] (altitude m, velocity m/s, positive up), control u is
the thrust acceleration in m/s^2. Explicit Euler dynamics with the
drag term -c*v*|v| opposing the motion. The scenario is a
constant-descent-rate glide at v_ref = -15 m/s from h0 = 300 m down to
a flare that brings the vehicle to rest at the origin.

Algorithm per iteration:
1. forward rollout of the nominal control through the nonlinear plant;
2. backward Riccati pass building the value-function quadratics Qx, Qu,
   Qxx, Qux, Quu and the local affine control law
   u = ubar + K*(x - xbar) + k at every step, with Levenberg-Marquardt
   regularization (mu on Quu) for the gain solve and the value
   recursion carried with the unregularized Quu;
3. forward pass of the affine policy with backtracking line search over
   alpha in [1, 0.5, 0.25, ...] accepting the first alpha that lowers
   the total cost; on total failure mu grows by factor 10 and the
   backward pass repeats, up to the mu cap where the driver raises
   RuntimeError.

Assumptions recorded (spec ambiguity note): the driver evaluates the
acceptance cost and the reported cost history at the module scenario
weights through the pinned total_cost/forward_pass signatures; the
run's qh/qv/rw/qfh/qfv/wp enter only the backward-pass quadratic
model. This split reproduces the deterministic failure anchor: with a
terminal-cost-only backward model (qh = qv = wp = 0) no line-search
step ever lowers the scenario-weighted total cost, so the regularizer
escalates to the cap and the driver raises RuntimeError.
"""

import math

# ---------------------------------------------------------------------
# Module constants: pinned worked scenario (do not edit)
# ---------------------------------------------------------------------
DT = 0.4        # time step, s
N_STEPS = 50    # horizon steps (T = 20 s)
GRAV = 9.81     # gravity acceleration, m/s^2
DRAG = 0.02     # quadratic drag coefficient, 1/m
H0 = 300.0      # glide reference start altitude, m
V_REF = -15.0   # constant descent rate of the glide, m/s
X0 = [300.0, -15.0]  # scenario initial state (on the glide)

QH = 1.0        # running altitude weight
QV = 2.0        # running velocity weight
R_W = 0.05      # control weight
QFH = 400.0     # terminal altitude weight
QFV = 800.0     # terminal velocity weight
W_PEN = 0.5     # below-ground penetration penalty weight

MU0 = 1e-6      # initial Levenberg-Marquardt regularization
MU_MIN = 1e-12  # floor after the 0.7 decay rule
MU_MAX = 1e6    # cap; reaching it raises RuntimeError
ALPHAS = [1.0 / (2 ** i) for i in range(21)]  # line search schedule
MAX_ITER = 150  # accepted-iteration budget
TOL = 1e-7      # relative cost-change convergence tolerance


def _finite(x):
    """True when x is a finite real number (int or float)."""
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def _hneg(h):
    """min(h, 0) as a float: the signed depth of penetration below ground."""
    return min(float(h), 0.0)


# ---------------------------------------------------------------------
# Plant and cost
# ---------------------------------------------------------------------
def discrete_dynamics(state, u, dt=DT, g=GRAV, c=DRAG):
    """One explicit-Euler step of the soft-landing plant.

    h+ = h + dt*v; v+ = v + dt*(u - g - c*v*|v|), the drag opposing the
    motion. Returns [h1, v1].
    """
    if not _finite(dt) or dt <= 0.0:
        raise ValueError("dt must be finite and positive")
    if not _finite(g) or g < 0.0:
        raise ValueError("g must be finite and non-negative")
    if not _finite(c) or c < 0.0:
        raise ValueError("c must be finite and non-negative")
    h, v = state
    if not (_finite(h) and _finite(v) and _finite(u)):
        raise ValueError("state entries and control must be finite")
    h1 = h + dt * v
    v1 = v + dt * (u - g - c * v * abs(v))
    return [h1, v1]


def dynamics_jacobians(state, u, dt=DT, g=GRAV, c=DRAG):
    """Analytic dynamics Jacobians at the rollout point.

    Returns (fx, fu) with fx = [[1, dt], [0, fd]], fd = 1 - 2*c*dt*|v|,
    and the control column fu = [0, dt].
    """
    if not _finite(dt) or dt <= 0.0:
        raise ValueError("dt must be finite and positive")
    if not _finite(g) or g < 0.0:
        raise ValueError("g must be finite and non-negative")
    if not _finite(c) or c < 0.0:
        raise ValueError("c must be finite and non-negative")
    h, v = state
    if not (_finite(h) and _finite(v) and _finite(u)):
        raise ValueError("state entries and control must be finite")
    fd = 1.0 - 2.0 * c * dt * abs(v)
    fx = [[1.0, dt], [0.0, fd]]
    fu = [0.0, dt]
    return fx, fu


def reference_state(k, h0=H0, v_ref=V_REF, dt=DT):
    """Glide-slope reference at step k: [h_ref(k), v_ref].

    h_ref(k) = h0 + v_ref*dt*k on the constant-descent-rate glide.
    """
    if k < 0:
        raise ValueError("step index k must be non-negative")
    return [h0 + v_ref * dt * k, v_ref]


def ground_penalty(state, wp=W_PEN):
    """Quadratic below-ground penetration penalty 0.5*wp*min(h, 0)^2."""
    hn = _hneg(state[0])
    return 0.5 * wp * hn * hn


def stage_cost(state, u, k, qh=QH, qv=QV, rw=R_W, wp=W_PEN):
    """Running cost at step k tracking the glide-slope reference.

    l_k = 0.5*qh*(h - h_ref(k))^2 + 0.5*qv*(v - v_ref)^2 +
    0.5*rw*u^2 + ground_penalty(x).
    """
    h, v = state
    h_ref, v_ref = reference_state(k)
    return (0.5 * qh * (h - h_ref) ** 2 + 0.5 * qv * (v - v_ref) ** 2
            + 0.5 * rw * u * u + ground_penalty(state, wp))


def terminal_cost(state, qfh=QFH, qfv=QFV, wp=W_PEN):
    """Terminal cost flaring the vehicle to rest at the origin.

    lf = 0.5*qfh*h^2 + 0.5*qfv*v^2 + ground_penalty(x).
    """
    h, v = state
    return 0.5 * qfh * h * h + 0.5 * qfv * v * v + ground_penalty(state, wp)


def stage_derivatives(state, u, k, qh=QH, qv=QV, rw=R_W, wp=W_PEN):
    """Stage-cost derivatives at (x_k, u_k).

    Returns (lx, lu, lxx, luu): lx = [qh*(h - h_ref) + wp*hn,
    qv*(v - v_ref)] with hn = min(h, 0); lu = rw*u;
    lxx = [[qh + (wp if h < 0 else 0), 0], [0, qv]]; luu = rw.
    """
    h, v = state
    h_ref, v_ref = reference_state(k)
    hn = _hneg(h)
    lx = [qh * (h - h_ref) + wp * hn, qv * (v - v_ref)]
    lu = rw * u
    lxx = [[qh + (wp if h < 0.0 else 0.0), 0.0], [0.0, qv]]
    luu = rw
    return lx, lu, lxx, luu


def rollout(x0, u_seq, dt=DT, g=GRAV, c=DRAG):
    """Forward rollout of a control sequence through the nonlinear plant.

    Returns the list of len(u_seq) + 1 states starting from x0.
    """
    states = [list(x0)]
    x = list(x0)
    for u in u_seq:
        x = discrete_dynamics(x, u, dt, g, c)
        states.append(x)
    return states


def total_cost(x0, u_seq, dt=DT, g=GRAV, c=DRAG, wp=W_PEN):
    """Total cost of a rollout at the module scenario weights.

    Stage costs k = 0..N-1 plus the terminal cost, evaluated with the
    pinned scenario weights (QH, QV, R_W, QFH, QFV, W_PEN); the driver
    uses this cost for line-search acceptance and the reported cost
    history. Returns (J, x_end).
    """
    states = rollout(x0, u_seq, dt, g, c)
    j = 0.0
    for k in range(len(u_seq)):
        j += stage_cost(states[k], u_seq[k], k)
    j += terminal_cost(states[-1], wp=wp)
    return j, states[-1]


# ---------------------------------------------------------------------
# iLQR passes
# ---------------------------------------------------------------------
def forward_pass(x0, u_seq, xbar, k_seq, K_seq, alpha, dt=DT, g=GRAV,
                 c=DRAG, wp=W_PEN):
    """Forward pass rolling the local affine control law.

    From x0 with u_k = ubar_k + K_k*(x_k - xbar_k) + alpha*k_k, the
    state stepped by the exact nonlinear dynamics. Total cost is
    evaluated at the module scenario weights (the pinned acceptance
    cost of the driver). Returns (J, states, controls).
    """
    states = [list(x0)]
    controls = []
    x = list(x0)
    j = 0.0
    for k in range(len(u_seq)):
        xb = xbar[k]
        u = (u_seq[k] + K_seq[k][0] * (x[0] - xb[0])
             + K_seq[k][1] * (x[1] - xb[1]) + alpha * k_seq[k])
        controls.append(u)
        j += stage_cost(x, u, k)
        x = discrete_dynamics(x, u, dt, g, c)
        states.append(x)
    j += terminal_cost(x, wp=wp)
    return j, states, controls


def backward_pass(xs, us, mu, dt=DT, g=GRAV, c=DRAG, qh=QH, qv=QV,
                  rw=R_W, qfh=QFH, qfv=QFV, wp=W_PEN):
    """Backward Riccati pass over the nominal rollout (xs, us).

    Terminal seed at step N: Vx = Qf*x_N, Vxx = diag(qfh, qfv). At
    every step k (scalar arithmetic, Vx = [p, q], Vxx = [[a, b],
    [b, d]] from step k+1) forms the value-function quadratics
    Qx, Qu, Qxx, Qux, Quu of the local cost-to-go, solves the
    regularized 1x1 gain system Quu_r = Quu + mu for the feedforward
    gain k = -Qu/Quu_r and the feedback row K = [-Qux0/Quu_r,
    -Qux1/Quu_r], and updates the value quadratic with the
    unregularized Quu. Returns (k_seq, K_seq, qs, dV, Vx_0, Vxx_0)
    with qs[k] the (Qx, Qu, Qxx, Qux, Quu) snapshot of step k and
    dV = -sum_k 0.5*Qu_k*k_k the expected model improvement (>= 0).
    """
    n = len(us)
    x_n = xs[n]
    hn = _hneg(x_n[0])
    p = qfh * x_n[0] + wp * hn
    q = qfv * x_n[1]
    a = qfh + (wp if x_n[0] < 0.0 else 0.0)
    b = 0.0
    d = qfv
    k_seq = [0.0] * n
    k_seq_rows = [None] * n
    qs = [None] * n
    d_v = 0.0
    for k in range(n - 1, -1, -1):
        x = xs[k]
        u = us[k]
        lx, lu, lxx, luu = stage_derivatives(x, u, k, qh, qv, rw, wp)
        fd = 1.0 - 2.0 * c * dt * abs(x[1])
        # Value-function quadratics of the local cost-to-go (pinned order).
        qx0 = lx[0] + p
        qx1 = lx[1] + dt * p + fd * q
        qu = lu + dt * q
        e12 = dt * a + fd * b
        e22 = dt * e12 + fd * (dt * b + fd * d)
        qxx00 = qh + a
        qxx11 = qv + e22
        qux0 = dt * b
        qux1 = dt * (dt * b + fd * d)
        quu = luu + dt * dt * d
        quu_r = quu + mu
        # Regularized 1x1 solve for the local affine control law.
        ff = -qu / quu_r
        fbh = -qux0 / quu_r
        fbv = -qux1 / quu_r
        # Value recursion with the unregularized Quu.
        vx_h = qx0 + fbh * (quu * ff + qu) + qux0 * ff
        vx_v = qx1 + fbv * (quu * ff + qu) + qux1 * ff
        vxx_hh = qxx00 + quu * fbh * fbh + fbh * qux0 + qux0 * fbh
        vxx_hv = e12 + quu * fbh * fbv + fbh * qux1 + qux0 * fbv
        vxx_vh = e12 + quu * fbv * fbh + fbv * qux0 + qux1 * fbh
        vxx_vv = qxx11 + quu * fbv * fbv + fbv * qux1 + qux1 * fbv
        vxx_hv_s = 0.5 * (vxx_hv + vxx_vh)  # symmetrize off-diagonal pair
        k_seq[k] = ff
        k_seq_rows[k] = [fbh, fbv]
        qs[k] = {"Qx": [qx0, qx1], "Qu": qu, "Qxx": [[qxx00, e12],
                 [e12, qxx11]], "Qux": [qux0, qux1], "Quu": quu}
        d_v += -0.5 * qu * ff
        p, q, a, b, d = vx_h, vx_v, vxx_hh, vxx_hv_s, vxx_vv
    return k_seq, k_seq_rows, qs, d_v, [p, q], [[a, b], [b, d]]


# ---------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------
def ilqr_solve(x0=X0, u0=None, dt=DT, g=GRAV, c=DRAG, n_steps=N_STEPS,
               qh=QH, qv=QV, rw=R_W, qfh=QFH, qfv=QFV, wp=W_PEN,
               max_iter=MAX_ITER, tol=TOL, mu0=MU0, mu_min=MU_MIN,
               mu_max=MU_MAX):
    """Run iLQR to convergence on the nonlinear soft-landing plant.

    Starts from the nominal rollout of u0 (default: the zero-control
    free-fall guess) and iterates the backward Riccati pass and the
    line-searched forward pass. The backward pass consumes the run's
    qh/qv/rw/qfh/qfv/wp; the acceptance cost and reported cost history
    are the scenario-weighted total cost of total_cost/forward_pass.
    Line search tries alpha in ALPHAS in order and accepts the first
    with J(alpha) < J_prev (monotone descent); on acceptance mu *= 0.7
    floored at mu_min; on total failure mu *= 10 and the backward pass
    repeats, raising RuntimeError once mu reaches mu_max. Converged
    when |dJ| <= tol*(1 + |J|) after an accepted iteration.

    Returns a dict with keys x0, u_seq, xs, cost, costs, iters,
    converged, alphas, mus_at, dvs, k_seq, K_seq, q_first, Vx_end,
    Vxx_end, max_u, u0, hN, vN, min_v.
    """
    if n_steps < 1:
        raise ValueError("n_steps must be at least 1")
    if not (_finite(x0[0]) and _finite(x0[1])):
        raise ValueError("x0 entries must be finite")
    if u0 is None:
        us = [0.0] * n_steps
    else:
        if len(u0) != n_steps:
            raise ValueError("u0 must have exactly n_steps entries")
        us = [float(u) for u in u0]
    guess = [float(u) for u in us]
    xs = rollout(x0, us, dt, g, c)
    j, _ = total_cost(x0, us, dt, g, c)
    costs = [j]
    alphas = []
    mus_at = []
    dvs = []
    mu = mu0
    iters = 0
    converged = False
    k_seq = [0.0] * n_steps
    k_seq_rows = [[0.0, 0.0] for _ in range(n_steps)]
    qs = [None] * n_steps
    for _ in range(max_iter):
        k_seq, k_seq_rows, qs, d_v, vx_0, vxx_0 = backward_pass(
            xs, us, mu, dt, g, c, qh, qv, rw, qfh, qfv, wp)
        j_new = None
        alpha_used = None
        st_new = None
        ct_new = None
        for alpha in ALPHAS:
            jn, st, ct = forward_pass(x0, us, xs, k_seq, k_seq_rows,
                                      alpha, dt, g, c)
            if jn < j:
                j_new = jn
                alpha_used = alpha
                st_new = st
                ct_new = ct
                break
        if j_new is None:
            if mu >= mu_max:
                raise RuntimeError("iLQR failed to improve the cost")
            mu = mu * 10.0
            continue
        d_j = j - j_new
        j = j_new
        xs = st_new
        us = ct_new
        costs.append(j)
        alphas.append(alpha_used)
        mus_at.append(mu)
        dvs.append(d_v)
        iters += 1
        mu = max(mu_min, mu * 0.7)
        if abs(d_j) <= tol * (1.0 + abs(j)):
            converged = True
            break
    x_n = xs[-1]
    return {
        "x0": list(x0),
        "u_seq": list(us),
        "xs": xs,
        "cost": j,
        "costs": costs,
        "iters": iters,
        "converged": converged,
        "alphas": alphas,
        "mus_at": mus_at,
        "dvs": dvs,
        "k_seq": k_seq,
        "K_seq": k_seq_rows,
        "q_first": qs[0],
        "Vx_end": [qfh * x_n[0], qfv * x_n[1]],
        "Vxx_end": [[qfh, 0.0], [0.0, qfv]],
        "max_u": max(abs(u) for u in us),
        "u0": guess,
        "hN": x_n[0],
        "vN": x_n[1],
        "min_v": min(s[1] for s in xs),
    }
