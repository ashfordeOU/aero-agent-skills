#!/usr/bin/env python3
"""anchor_backstepping.py - deterministic prep anchor for the wave-49 leaf spec
gnc-autonomy/control/backstepping-control (repo-relative path
ops/automation/state/wave49-specs/anchors/anchor_backstepping.py).

Pure stdlib (math only), no RNG, no file IO, deterministic. Implements the
strict-feedback recursive design (integrator backstepping) pinned by the
wave-49 recon receipt gate (d) on the second-order strict-feedback plant

    x1_dot = x2 + f1(x1),   f1(x1) = x1^2
    x2_dot = u  + f2(x1, x2),  f2(x1, x2) = x1 * x2

tracking the reference x1d(t). Error-variable change of coordinates:
z1 = x1 - x1d; virtual control alpha1 = -c1 z1 + x1d_dot - f1 so the
z1-subsystem candidate V1 = z1^2/2 decays as V1_dot = -c1 z1^2 + z1 z2 with
the mismatch z2 = x2 - alpha1; final control
u = -f2 + alpha1_dot - z1 - c2 z2, alpha1_dot the analytic derivative along
the plant, giving V2 = (z1^2 + z2^2)/2 with V2_dot = -c1 z1^2 - c2 z2^2.

Closed-loop error coordinates are exactly linear (reference independent):
z1_dot = -c1 z1 + z2, z2_dot = -z1 - c2 z2, so with c1 = c2 = c the closed
form is z(t) = exp(-c t) R(t) z(0) with the rotation R(t), |z| damping at
rate c and V2(t) = V2(0) exp(-2 c t).

Worked cases (module constants):
A worked    constant reference x1d = 1.0, c1 = c2 = 2.0, x1(0) = x2(0) = 0
B rate case constant reference x1d = 1.0, c1 = c2 = 4.0, x1(0) = x2(0) = 0
C feedforward  reference x1d(t) = 1 - exp(-t), c1 = c2 = 2.0,
            x1(0) = x2(0) = 0 (exercises x1d_dot and x1d_ddot terms)

Run: python3 ops/automation/state/wave49-specs/anchors/anchor_backstepping.py
Exit 0 with all internal asserts passing, byte-identical under both
interpreters (3.9.6 and 3.13.12 within 1e-12 relative).
"""

import math

# ---------------------------------------------------------------------------
# Module constants (every fixed number used below)
# ---------------------------------------------------------------------------
C1_WORKED = 2.0      # design gain c1, worked case (1/s)
C2_WORKED = 2.0      # design gain c2, worked case (1/s)
C_RATE = 4.0         # design gain c1 = c2, rate case (1/s)
REF_SETPOINT = 1.0   # constant reference value and exponential-reference level
INIT_X1 = 0.0        # initial state of channel 1
INIT_X2 = 0.0        # initial state of channel 2
DT = 0.001           # forward-Euler sample time (s)
SIM_TIME = 6.0       # simulation horizon (s)
SETTLE_LEVEL = 0.01  # 1-percent tracking-error band for the settle time
TOL = 1e-6           # audit tolerance
KIND_CONST = "constant"
KIND_EXP = "exponential"


# ---------------------------------------------------------------------------
# Plant nonlinearities (strict-feedback drift pair)
# ---------------------------------------------------------------------------
def f1(x1):
    """f1(x1) = x1^2, the drift of channel 1."""
    return x1 * x1


def df1(x1):
    """df1/dx1 = 2 x1, the analytic derivative of f1."""
    return 2.0 * x1


def f2(x1, x2):
    """f2(x1, x2) = x1 * x2, the drift of channel 2 (independent of u)."""
    return x1 * x2


# ---------------------------------------------------------------------------
# Reference
# ---------------------------------------------------------------------------
def reference(t, kind):
    """Reference triple (x1d, x1d_dot, x1d_ddot) at time t.

    kind "constant": x1d = REF_SETPOINT (velocity and acceleration zero).
    kind "exponential": x1d = REF_SETPOINT (1 - exp(-t)), a smooth step from
    0 toward REF_SETPOINT with x1d_dot = exp(-t), x1d_ddot = -exp(-t).
    ValueError: kind not in {"constant", "exponential"}.
    """
    if kind == KIND_CONST:
        return (REF_SETPOINT, 0.0, 0.0)
    if kind == KIND_EXP:
        e = math.exp(-t)
        return (REF_SETPOINT * (1.0 - e), REF_SETPOINT * e, -REF_SETPOINT * e)
    raise ValueError(
        "reference kind must be 'constant' or 'exponential', got %r" % (kind,)
    )


# ---------------------------------------------------------------------------
# Recursion (definitions pinned by the receipt gate (d))
# ---------------------------------------------------------------------------
def tracking_error(x1, x1d):
    """Error variable z1 = x1 - x1d."""
    return x1 - x1d


def virtual_control(z1, ref_dot, f1_value, c1):
    """alpha1 = -c1 z1 + x1d_dot - f1, the virtual control of channel 1.

    With x2 = alpha1 the z1 subsystem obeys z1_dot = -c1 z1.
    ValueError: c1 <= 0 ("design gain c1 must be positive, got ...").
    """
    if c1 <= 0.0:
        raise ValueError(
            "design gain c1 must be positive, got %r" % (c1,)
        )
    return -c1 * z1 + ref_dot - f1_value


def virtual_control_derivative(x1, x2, ref_dot, ref_ddot, c1):
    """alpha1_dot, the analytic derivative of alpha1 along the plant.

    d alpha1/dt = -c1 (x1_dot - x1d_dot) + x1d_ddot - (df1/dx1) x1_dot with
    x1_dot = x2 + f1(x1) from the plant (not from the closed loop).
    ValueError: c1 <= 0 ("design gain c1 must be positive, got ...").
    """
    if c1 <= 0.0:
        raise ValueError(
            "design gain c1 must be positive, got %r" % (c1,)
        )
    x1_rate = x2 + f1(x1)
    return -c1 * (x1_rate - ref_dot) + ref_ddot - df1(x1) * x1_rate


def mismatch_error(x2, alpha1):
    """Inner-state mismatch z2 = x2 - alpha1, the second error variable."""
    return x2 - alpha1


def final_control(f2_value, alpha1_dot, z1, z2, c2):
    """u = -f2 + alpha1_dot - z1 - c2 z2, the backstepping control law.

    With this u, V2_dot = -c1 z1^2 - c2 z2^2 and z2_dot = -z1 - c2 z2.
    ValueError: c2 <= 0 ("design gain c2 must be positive, got ...").
    """
    if c2 <= 0.0:
        raise ValueError(
            "design gain c2 must be positive, got %r" % (c2,)
        )
    return -f2_value + alpha1_dot - z1 - c2 * z2


def v2_value(z1, z2):
    """V2 = (z1^2 + z2^2) / 2, the composite quadratic-Lyapunov candidate."""
    return 0.5 * (z1 * z1 + z2 * z2)


# ---------------------------------------------------------------------------
# Closed forms (equal design gains c1 = c2 = c only)
# ---------------------------------------------------------------------------
def z1_closed_form(t, z1_0, z2_0, c):
    """Closed-form z1(t) = exp(-c t) (z1_0 cos t + z2_0 sin t) of the
    exactly linear error dynamics z1_dot = -c z1 + z2, z2_dot = -z1 - c z2."""
    e = math.exp(-c * t)
    return e * (z1_0 * math.cos(t) + z2_0 * math.sin(t))


def z2_closed_form(t, z1_0, z2_0, c):
    """Closed-form z2(t) = exp(-c t) (z2_0 cos t - z1_0 sin t)."""
    e = math.exp(-c * t)
    return e * (z2_0 * math.cos(t) - z1_0 * math.sin(t))


def v2_closed_form(t, z1_0, z2_0, c):
    """Closed-form V2(t) = V2(0) exp(-2 c t)."""
    return 0.5 * (z1_0 * z1_0 + z2_0 * z2_0) * math.exp(-2.0 * c * t)


# ---------------------------------------------------------------------------
# Deterministic closed-loop simulation (forward Euler, control recomputed
# every sample from the current state, exactly as the leaf will implement)
# ---------------------------------------------------------------------------
def simulate(c1, c2, kind, x1_0=INIT_X1, x2_0=INIT_X2, dt=DT,
             sim_time=SIM_TIME):
    """Closed-loop forward-Euler simulation of the strict-feedback plant
    under the recursive backstepping control tracking reference kind.

    Returns a dict with the series ("t", "x1", "x2", "z1", "z2", "alpha1",
    "alpha1_dot", "u", "V2", "x1d") and the derived audit metrics
    ("n", "z1_map_max_res", "z2_map_max_res", "v2dot_res_max",
    "first_zero_k", "first_zero_t", "settle_1pct_k", "settle_1pct_t",
    "realized_c", "max_abs_u", "final" (dict of x1, x2, z1, z2, alpha1,
    u, V2 at the final sample)).

    z1_map_max_res: max over k of |z1[k+1] - (z1[k] + dt (-c1 z1[k] +
    z2[k]))|; with a constant reference this is machine-exact (the
    definitions cancel), with a moving reference it is O(dt^2) from the
    reference Euler discretization.
    z2_map_max_res: max over k of |z2[k+1] - (z2[k] + dt (-z1[k] - c2
    z2[k]))|; the Euler curvature residual -(dt^2/2) alpha1_ddot of the
    analytic derivative (an O(1) error in alpha1_dot would show here as an
    O(dt) term).
    v2dot_res_max: max over k of |(V2[k+1] - V2[k])/dt - (-c1 z1[k]^2 -
    c2 z2[k]^2)|, the Euler curvature of the quadratic-Lyapunov audit.

    ValueErrors: c1 <= 0, c2 <= 0, dt <= 0, sim_time <= 0 (messages as in
    the leaf functions above), invalid kind (raised by reference()).
    """
    if c1 <= 0.0:
        raise ValueError(
            "design gain c1 must be positive, got %r" % (c1,)
        )
    if c2 <= 0.0:
        raise ValueError(
            "design gain c2 must be positive, got %r" % (c2,)
        )
    if dt <= 0.0:
        raise ValueError("sample time dt must be positive, got %r" % (dt,))
    if sim_time <= 0.0:
        raise ValueError(
            "simulation time sim_time must be positive, got %r" % (sim_time,)
        )
    reference(0.0, kind)  # validates the kind up front

    n = int(sim_time / dt + 0.5) + 1
    t = [0.0] * n
    x1 = [0.0] * n
    x2 = [0.0] * n
    z1 = [0.0] * n
    z2 = [0.0] * n
    alpha1 = [0.0] * n
    alpha1_dot = [0.0] * n
    u = [0.0] * n
    V2 = [0.0] * n
    x1d = [0.0] * n

    x1k = x1_0
    x2k = x2_0
    for k in range(n):
        tk = k * dt
        t[k] = tk
        r_triple = reference(tk, kind)
        x1d[k] = r_triple[0]
        ref_dot = r_triple[1]
        ref_ddot = r_triple[2]
        z1k = tracking_error(x1k, r_triple[0])
        a1k = virtual_control(z1k, ref_dot, f1(x1k), c1)
        z2k = mismatch_error(x2k, a1k)
        adotk = virtual_control_derivative(x1k, x2k, ref_dot, ref_ddot, c1)
        uk = final_control(f2(x1k, x2k), adotk, z1k, z2k, c2)
        z1[k] = z1k
        z2[k] = z2k
        alpha1[k] = a1k
        alpha1_dot[k] = adotk
        u[k] = uk
        V2[k] = v2_value(z1k, z2k)
        x1[k] = x1k
        x2[k] = x2k
        # forward-Euler plant update with the control held over the step
        x1k = x1k + dt * (x2k + f1(x1k))
        x2k = x2k + dt * (uk + f2(x1k, x2k))

    # ---- audit metrics ------------------------------------------------
    z1_map_max_res = 0.0
    z2_map_max_res = 0.0
    v2dot_res_max = 0.0
    for k in range(n - 1):
        z1_map_res = abs(z1[k + 1] - (z1[k] + dt * (-c1 * z1[k] + z2[k])))
        z2_map_res = abs(z2[k + 1] - (z2[k] + dt * (-z1[k] - c2 * z2[k])))
        v2dot_res = abs((V2[k + 1] - V2[k]) / dt
                        - (-c1 * z1[k] * z1[k] - c2 * z2[k] * z2[k]))
        if z1_map_res > z1_map_max_res:
            z1_map_max_res = z1_map_res
        if z2_map_res > z2_map_max_res:
            z2_map_max_res = z2_map_res
        if v2dot_res > v2dot_res_max:
            v2dot_res_max = v2dot_res

    first_zero_k = None
    for k in range(1, n):
        if z1[k - 1] * z1[k] < 0.0 or z1[k] == 0.0:
            first_zero_k = k
            break

    settle_1pct_k = None
    for k in range(n - 1, -1, -1):
        if abs(z1[k]) > SETTLE_LEVEL:
            settle_1pct_k = k + 1
            break
    if settle_1pct_k is None:
        settle_1pct_k = 0
    if settle_1pct_k >= n:
        settle_1pct_k = None

    max_abs_u = max(abs(v) for v in u)
    # realized V2 decay rate over the [0, 2.0 s] window (4 e-foldings of
    # V2); the full-horizon ratio carries the accumulated O(dt) Euler lag
    # for moving references, so the windowed rate is the stable witness
    w2 = int(2.0 / dt)
    realized_c = -math.log(V2[w2] / V2[0]) / (2.0 * 2.0)

    return {
        "t": t, "x1": x1, "x2": x2, "z1": z1, "z2": z2,
        "alpha1": alpha1, "alpha1_dot": alpha1_dot, "u": u, "V2": V2,
        "x1d": x1d, "n": n,
        "z1_map_max_res": z1_map_max_res,
        "z2_map_max_res": z2_map_max_res,
        "v2dot_res_max": v2dot_res_max,
        "first_zero_k": first_zero_k,
        "first_zero_t": None if first_zero_k is None else first_zero_k * dt,
        "settle_1pct_k": settle_1pct_k,
        "settle_1pct_t": None if settle_1pct_k is None
        else settle_1pct_k * dt,
        "realized_c": realized_c,
        "max_abs_u": max_abs_u,
        "final": {"x1": x1[-1], "x2": x2[-1], "z1": z1[-1], "z2": z2[-1],
                  "alpha1": alpha1[-1], "alpha1_dot": alpha1_dot[-1],
                  "u": u[-1], "V2": V2[-1]},
    }


def _idx(t_series, t_target):
    """Sample index of the time nearest to t_target in the series."""
    return int(round(t_target / DT))


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------
def _print_case(tag, res, c, z1_0, z2_0, x1d_ss, label):
    print("=== %s (%s) ===" % (tag, label))
    print("design gains c1 = c2 = %.1f (1/s)" % c)
    a1_0 = virtual_control(z1_0, reference(0.0, KIND_CONST)[1],
                           f1(res["x1"][0]), c)
    print("initial error variables: z1(0) = %.9f, z2(0) = %.9f (alpha1(0) "
          "= %.9f), V2(0) = %.9f" % (z1_0, z2_0, a1_0,
                                      v2_value(z1_0, z2_0)))
    print("initial command: u(0) = %.9f" % res["u"][0])
    print("closed-form z1(t) = exp(-%.1f t) (z1(0) cos t + z2(0) sin t), "
          "V2(t) = V2(0) exp(-%.2f t)" % (c, 2.0 * c))
    print("audit residuals: z1-map max |z1[k+1] - (z1[k] + dt (-c1 z1[k] + "
          "z2[k]))| = %.6e" % res["z1_map_max_res"])
    print("  z2-map max |z2[k+1] - (z2[k] + dt (-z1[k] - c2 z2[k]))| = "
          "%.6e" % res["z2_map_max_res"])
    print("  V2-dot max |(V2[k+1] - V2[k])/dt - (-c1 z1^2 - c2 z2^2)| = "
          "%.6e" % res["v2dot_res_max"])
    print("realized decay rate over [0, 2.0] s, -ln(V2(2.0)/V2(0))/(2*2.0) "
          "= %.9f vs design c = %.1f" % (res["realized_c"], c))
    fz = res["final"]
    print("final sample T = %.1f s: x1 = %.9f (x1d = %.9f), x2 = %.9f, "
          "z1 = %.6e, z2 = %.6e" % (SIM_TIME, fz["x1"], x1d_ss, fz["x2"],
                                    fz["z1"], fz["z2"]))
    print("  alpha1 = %.9f, u = %.9f, V2 = %.6e" % (fz["alpha1"], fz["u"],
                                                    fz["V2"]))
    print("first z1 zero crossing at t = %.6f s" % res["first_zero_t"])
    print("1-percent settle (|z1| <= %.2f for all later samples) at t = "
          "%.6f s" % (SETTLE_LEVEL, res["settle_1pct_t"]))
    print("max |u| over the run = %.9f" % res["max_abs_u"])
    # closed-form sample table
    print("  t      z1 sim       z1 closed    |dz1|     z2 sim       "
          "z2 closed    |dz2|")
    for tt in (0.5, 1.0, 2.0, 4.0, 6.0):
        k = _idx(res["t"], tt)
        z1c = z1_closed_form(tt, z1_0, z2_0, c)
        z2c = z2_closed_form(tt, z1_0, z2_0, c)
        print("%5.1f  %+.9f  %+.9f  %.3e  %+.9f  %+.9f  %.3e"
              % (tt, res["z1"][k], z1c, abs(res["z1"][k] - z1c),
                 res["z2"][k], z2c, abs(res["z2"][k] - z2c)))
    # V2 ratio audit
    for tt in (0.5, 1.0, 2.0, 4.0, 6.0):
        k = _idx(res["t"], tt)
        r_sim = res["V2"][k] / res["V2"][0]
        r_cf = math.exp(-2.0 * c * tt)
        print("V2 ratio t = %4.1f s: sim/closed form %s / %s (rel diff "
              "%.2e)" % (tt, "{:.6e}".format(r_sim), "{:.6e}".format(r_cf),
                         abs(r_sim - r_cf) / r_cf))
    print()


def _print_equilibrium_check(res, x1d_ss, u_ss):
    fz = res["final"]
    print("equilibrium identity at T = %.1f s: |x1 - x1d_ss| = %.3e, "
          "|x2 + f1(x1)| = %.3e (x1 rate), |u - u_ss| = %.3e (u_ss = "
          "%.9f)" % (SIM_TIME, abs(fz["x1"] - x1d_ss),
                     abs(fz["x2"] + f1(fz["x1"])), abs(fz["u"] - u_ss),
                     u_ss))


def main():
    print("anchor_backstepping.py: deterministic prep anchor for the wave-49 "
          "leaf spec")
    print("gnc-autonomy/control/backstepping-control")
    print("plant x1_dot = x2 + x1^2, x2_dot = u + x1 x2 (strict feedback), "
          "z1 = x1 - x1d,")
    print("alpha1 = -c1 z1 + x1d_dot - x1^2, z2 = x2 - alpha1, u = -x1 x2 + "
          "alpha1_dot - z1 - c2 z2")
    print("forward Euler dt = %.3f s over %.1f s (%d samples)"
          % (DT, SIM_TIME, int(SIM_TIME / DT + 0.5) + 1))
    print()

    # ---- case A: worked example (receipt gate (d) anchor parameters) ----
    z1_0a = tracking_error(INIT_X1, REF_SETPOINT)          # -1.0
    a1_0a = virtual_control(z1_0a, 0.0, f1(INIT_X1), C1_WORKED)  # 2.0
    z2_0a = mismatch_error(INIT_X2, a1_0a)                 # -2.0
    res_a = simulate(C1_WORKED, C2_WORKED, KIND_CONST)
    _print_case("CASE A worked", res_a, C1_WORKED, z1_0a, z2_0a,
                REF_SETPOINT, "constant reference x1d = 1.0, c1 = c2 = 2.0")
    _print_equilibrium_check(res_a, REF_SETPOINT, 1.0)  # u_ss = -f2 = 1.0

    # ---- case B: rate case (c1 = c2 = 4, doubled gains) ----------------
    z1_0b = tracking_error(INIT_X1, REF_SETPOINT)          # -1.0
    a1_0b = virtual_control(z1_0b, 0.0, f1(INIT_X1), C_RATE)  # 4.0
    z2_0b = mismatch_error(INIT_X2, a1_0b)                 # -4.0
    res_b = simulate(C_RATE, C_RATE, KIND_CONST)
    _print_case("CASE B rate", res_b, C_RATE, z1_0b, z2_0b, REF_SETPOINT,
                "constant reference x1d = 1.0, c1 = c2 = 4.0")
    _print_equilibrium_check(res_b, REF_SETPOINT, 1.0)

    # ---- case C: feedforward case (moving reference) --------------------
    res_c = simulate(C1_WORKED, C2_WORKED, KIND_EXP)
    z1_0c = tracking_error(INIT_X1, 0.0)                   # 0.0
    a1_0c = virtual_control(z1_0c, 1.0, f1(INIT_X1), C1_WORKED)  # 1.0
    z2_0c = mismatch_error(INIT_X2, a1_0c)                 # -1.0
    print("=== CASE C feedforward (reference x1d(t) = 1 - exp(-t), "
          "c1 = c2 = 2.0) ===")
    print("initial error variables: z1(0) = %.9f, z2(0) = %.9f (alpha1(0) = "
          "%.9f), V2(0) = %.9f" % (z1_0c, z2_0c, a1_0c,
                                   v2_value(z1_0c, z2_0c)))
    print("initial command: u(0) = %.9f" % res_c["u"][0])
    print("reference at t = 0: x1d(0) = 0, x1d_dot(0) = 1, x1d_ddot(0) = -1 "
          "(feedforward terms live)")
    # maximum tracking error from the closed form z1 = -exp(-2t) sin t
    t_peak = math.atan(0.5)
    z1_peak = z1_closed_form(t_peak, z1_0c, z2_0c, C1_WORKED)
    k_peak = _idx(res_c["t"], t_peak)
    print("max |z1|: closed form %.9f at t = %.6f s; sim z1(%.3f s) = "
          "%.9f" % (abs(z1_peak), t_peak, res_c["t"][k_peak],
                    res_c["z1"][k_peak]))
    fz_c = res_c["final"]
    x1d_6 = REF_SETPOINT * (1.0 - math.exp(-SIM_TIME))
    print("final sample T = 6.0 s: x1d = %.9f, x1 = %.9f, x2 = %.9f, "
          "z1 = %.6e, z2 = %.6e" % (x1d_6, fz_c["x1"], fz_c["x2"],
                                    fz_c["z1"], fz_c["z2"]))
    print("  alpha1 = %.9f, u = %.9f, V2 = %.6e" % (fz_c["alpha1"],
                                                    fz_c["u"], fz_c["V2"]))
    print("first z1 zero crossing at t = %.6f s" % res_c["first_zero_t"])
    print("1-percent settle (|z1| <= %.2f for all later samples) at t = "
          "%.6f s" % (SETTLE_LEVEL, res_c["settle_1pct_t"]))
    print("max |u| over the run = %.9f" % res_c["max_abs_u"])
    print("realized decay rate over [0, 2.0] s, -ln(V2(2.0)/V2(0))/(2*2.0) "
          "= %.9f vs design c = 2.0" % res_c["realized_c"])
    print("audit residuals: z1-map max = %.6e (reference Euler "
          "discretization), z2-map max = %.6e, V2-dot max = %.6e"
          % (res_c["z1_map_max_res"], res_c["z2_map_max_res"],
             res_c["v2dot_res_max"]))
    for tt in (0.5, 1.0, 2.0, 4.0, 6.0):
        k = _idx(res_c["t"], tt)
        z1c = z1_closed_form(tt, z1_0c, z2_0c, C1_WORKED)
        z2c = z2_closed_form(tt, z1_0c, z2_0c, C1_WORKED)
        print("sample t = %4.1f s: x1 %.9f, x2 %+.9f, z1 %+.9f (closed "
              "%.9f), z2 %+.9f (closed %.9f), u %+.9f"
              % (tt, res_c["x1"][k], res_c["x2"][k], res_c["z1"][k], z1c,
                 res_c["z2"][k], z2c, res_c["u"][k]))
    r0 = res_c["V2"][0]
    for tt in (0.5, 1.0, 2.0, 4.0, 6.0):
        k = _idx(res_c["t"], tt)
        r_sim = res_c["V2"][k] / r0
        r_cf = math.exp(-4.0 * tt)
        print("V2 ratio t = %4.1f s: sim/closed form %s / %s (rel diff "
              "%.2e)" % (tt, "{:.6e}".format(r_sim), "{:.6e}".format(r_cf),
                         abs(r_sim - r_cf) / r_cf))
    print()

    # ---- equilibrium checks for cases A and B (constant reference) ------
    print("=== equilibrium identity (cases A and B) ===")
    _print_equilibrium_check(res_a, REF_SETPOINT, 1.0)
    _print_equilibrium_check(res_b, REF_SETPOINT, 1.0)
    print()

    # ---- sample points, worked case (module output style) ---------------
    print("=== worked-case sample points (module output) ===")
    for tt in (0.5, 1.0, 2.0, 4.0, 6.0):
        k = _idx(res_a["t"], tt)
        print("t = %.1f s: x1 %.9f, x2 %.9f, z1 %.9f, z2 %.9f, alpha1 %.9f, "
              "alpha1_dot %+.9f, u %+.9f" % (tt, res_a["x1"][k],
                                             res_a["x2"][k], res_a["z1"][k],
                                             res_a["z2"][k],
                                             res_a["alpha1"][k],
                                             res_a["alpha1_dot"][k],
                                             res_a["u"][k]))
    print()

    # ---- zero-crossing closed forms (equal-gain theory) -----------------
    print("=== zero-crossing closed forms (z1_0 cos t + z2_0 sin t = 0) ===")
    print("case A z1(0) = -1, z2(0) = -2: first zero t* = pi + atan(0.5/-1) "
          "= %.6f s" % (math.pi + math.atan(-(-1.0) / -2.0)))
    print("case B z1(0) = -1, z2(0) = -4: first zero t* = pi + atan(0.25/-1) "
          "= %.6f s" % (math.pi + math.atan(-(-1.0) / -4.0)))
    print("case C z1(0) = 0: first zero of sin t at t* = pi = %.6f s"
          % math.pi)
    print()

    # ---- ValueErrors with real messages --------------------------------
    print("=== ValueErrors (real messages) ===")
    cases = [
        ("virtual_control(0.1, 0.0, 0.1, 0.0)",
         lambda: virtual_control(0.1, 0.0, 0.1, 0.0)),
        ("virtual_control_derivative(0.1, 0.0, 0.0, 0.0, 0.0)",
         lambda: virtual_control_derivative(0.1, 0.0, 0.0, 0.0, 0.0)),
        ("final_control(0.1, 0.0, 0.1, 0.1, 0.0)",
         lambda: final_control(0.1, 0.0, 0.1, 0.1, 0.0)),
        ("simulate(c1 = 0.0)",
         lambda: simulate(c1=0.0, c2=C2_WORKED, kind=KIND_CONST)),
        ("simulate(c2 = 0.0)",
         lambda: simulate(c1=C1_WORKED, c2=0.0, kind=KIND_CONST)),
        ("simulate(dt = 0.0)",
         lambda: simulate(C1_WORKED, C2_WORKED, KIND_CONST, dt=0.0)),
        ("simulate(sim_time = 0.0)",
         lambda: simulate(C1_WORKED, C2_WORKED, KIND_CONST, sim_time=0.0)),
        ("reference(0.5, 'ramp')",
         lambda: reference(0.5, "ramp")),
    ]
    for label, fn in cases:
        try:
            fn()
            print("%s -> NO ERROR (bug)" % label)
        except ValueError as exc:
            print("%s raises %r" % (label, str(exc)))
    print()

    # ---- internal sanity asserts (all must pass, exit 0) ----------------
    assert abs(z1_0a - (-1.0)) < TOL and abs(z2_0a - (-2.0)) < TOL
    assert abs(v2_value(z1_0a, z2_0a) - 2.5) < TOL
    assert abs(res_a["u"][0] - 5.0) < TOL
    assert res_a["z1_map_max_res"] < 1e-9
    assert res_a["z2_map_max_res"] < 1e-3
    assert res_b["z2_map_max_res"] < 1e-3
    assert abs(res_a["final"]["x1"] - REF_SETPOINT) < 1e-3
    assert abs(res_b["final"]["x1"] - REF_SETPOINT) < 1e-3
    assert res_a["settle_1pct_t"] is not None
    assert abs(res_a["realized_c"] - C1_WORKED) < 0.01 * C1_WORKED
    assert abs(res_b["realized_c"] - C_RATE) < 0.01 * C_RATE
    assert abs(res_c["realized_c"] - C1_WORKED) < 0.01 * C1_WORKED
    assert res_c["settle_1pct_t"] is not None
    assert res_c["z1_map_max_res"] < 1e-5
    k_peak = _idx(res_c["t"], t_peak)
    assert abs(abs(res_c["z1"][k_peak]) - abs(z1_peak)) < 2e-4
    assert abs(res_c["final"]["x1"]
               - REF_SETPOINT * (1.0 - math.exp(-SIM_TIME))) < 1e-3
    v2a_cf = v2_closed_form(SIM_TIME, z1_0a, z2_0a, C1_WORKED)
    assert abs(res_a["V2"][-1] - v2a_cf) < 0.05 * v2a_cf
    # determinism: identical outputs run to run
    res_a2 = simulate(C1_WORKED, C2_WORKED, KIND_CONST)
    assert res_a["z1"] == res_a2["z1"] and res_a["u"] == res_a2["u"]
    print("anchor exit 0: all internal asserts passed")


if __name__ == "__main__":
    main()
