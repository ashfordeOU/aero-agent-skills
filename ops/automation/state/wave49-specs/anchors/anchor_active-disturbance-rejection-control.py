#!/usr/bin/env python3
"""Anchor: linear ADRC (active disturbance rejection control) with LESO.

Wave-49 prep anchor for gnc-autonomy/control/active-disturbance-rejection-control.
Pure Python stdlib (math only), deterministic, no RNG.

Model pinned by the spec (Gao 2003 bandwidth parameterization):
- Canonical second-order design plant: y'' = f + b0 u, f the total
  disturbance (internal dynamics plus external disturbance), b0 the given
  control-effectiveness estimate.
- Third-order linear extended state observer (LESO), states z1 = y-hat,
  z2 = y'-hat, z3 = f-hat:
    z1_dot = z2 + beta1 (y - z1)
    z2_dot = z3 + beta2 (y - z1) + b0 u
    z3_dot = beta3 (y - z1)
  with the bandwidth parameterization beta = (3 w_o, 3 w_o^2, w_o^3),
  which places all three observer error poles at -w_o ((s + w_o)^3).
- Disturbance-rejection control law: u = (u0 - z3)/b0 cancels the total
  disturbance estimate; the outer loop u0 = kp (r - z1) - kd z2 with
  kp = w_c^2 and kd = 2 w_c places the tracking poles at -w_c (double).

Simulator truth plant (bookkeeping only, unknown to the controller):
  y'' = -A1 y' - A0 y + w(t) + b u
with A1 = 0.75, A0 = 0.5 and the piecewise-constant external disturbance
w(t) = W0 for t < T_STEP, w(t) = W1 for t >= T_STEP. Worked case is
gain-matched (b = b0 = 1.0); the robustness run uses b = 0.8 at the same
b0 = 1.0 design (control effectiveness over-modeled by 25 percent).

Forward Euler at dt = 1e-4 s over a 6.0 s horizon (60001 samples).
All printed numbers are real outputs; every internal assertion must pass.

Run: python3 ops/automation/state/wave49-specs/anchors/anchor_active-disturbance-rejection-control.py
"""

import math

# ---------------------------------------------------------------------------
# Module constants (worked-example configuration, pinned by the spec)
# ---------------------------------------------------------------------------
OMEGA_C = 5.0        # controller bandwidth (rad/s): tracking poles at -w_c double
OMEGA_O = 30.0       # observer bandwidth (rad/s): observer poles at -w_o triple
B0 = 1.0             # design control-effectiveness estimate used by the controller
PLANT_B_WORKED = 1.0  # true control gain, worked case (gain matched, b = b0)
PLANT_B_MISMATCH = 0.8  # true control gain, robustness case (b0 over-models by 25 percent)
PLANT_A1 = 0.75      # internal damping coefficient of the truth plant (unknown to the controller)
PLANT_A0 = 0.5       # internal stiffness coefficient of the truth plant (unknown to the controller)
W0 = 0.5             # external disturbance level before the step
W1 = 1.5             # external disturbance level after the step (step of +1.0 at T_STEP)
T_STEP = 3.0         # disturbance step time (s)
REFERENCE_R = 1.0    # constant reference command
INIT_Y = 0.0         # plant position at t = 0
INIT_V = 0.0         # plant velocity at t = 0
INIT_Z = (0.0, 0.0, 0.0)  # LESO initial estimates (z1, z2, z3)
DT = 1e-4            # sample time (s), forward Euler
SIM_TIME = 6.0       # horizon (s)
TAIL_START = 4.5     # post-step decay tail window start (s) for residual metrics
SETTLE_START = 5.5   # settled window start (s): tight residual band after the decay
RECOVERY_START = 3.0  # post-step recovery window start (s)


def observer_gains(omega_o):
    """Bandwidth-parameterized LESO gains beta = (3 w_o, 3 w_o^2, w_o^3).

    The three gains make det(sI - (A - beta C)) = (s + w_o)^3, placing all
    observer error poles at -omega_o. Returns (beta1, beta2, beta3).
    ValueError: omega_o <= 0.
    """
    if omega_o <= 0.0:
        raise ValueError("observer bandwidth omega_o must be positive, got %s" % omega_o)
    return (3.0 * omega_o, 3.0 * omega_o * omega_o, omega_o * omega_o * omega_o)


def controller_gains(omega_c):
    """Bandwidth-parameterized PD gains (kp, kd) = (w_c^2, 2 w_c).

    The two gains make the ideal double-integrator loop
    s^2 + kd s + kp = (s + w_c)^2, placing both tracking poles at -omega_c.
    ValueError: omega_c <= 0.
    """
    if omega_c <= 0.0:
        raise ValueError("controller bandwidth omega_c must be positive, got %s" % omega_c)
    return (omega_c * omega_c, 2.0 * omega_c)


def control_law(r, z1, z2, z3, b0, kp, kd):
    """ADRC command u = (u0 - z3)/b0 with u0 = kp (r - z1) - kd z2.

    u0 is the bandwidth-parameterized PD outer loop on the estimated
    states; the disturbance-rejection term -z3/b0 cancels the total
    disturbance estimate. Returns u.
    ValueError: b0 == 0.
    """
    if b0 == 0.0:
        raise ValueError("control-effectiveness estimate b0 must be nonzero, got 0.0")
    u0 = kp * (r - z1) - kd * z2
    return (u0 - z3) / b0


def cancellation_residual(f, u0, z3, b0):
    """Plant acceleration under the law minus u0, the cancellation witness.

    With z3 = f the identity f + b0*((u0 - z3)/b0) - u0 evaluates to zero
    to float noise, the algebraic statement that the disturbance-rejection
    term makes the plant channel behave as the double integrator y'' = u0.
    Returns the residual. ValueError: b0 == 0.
    """
    if b0 == 0.0:
        raise ValueError("control-effectiveness estimate b0 must be nonzero, got 0.0")
    u = (u0 - z3) / b0
    return f + b0 * u - u0


def total_disturbance(y, v, w):
    """Simulator-truth total disturbance f = -A1 v - A0 y + w of the pinned
    second-order plant y'' = f + b u. Bookkeeping only, never an input to
    the controller. Returns f."""
    return -PLANT_A1 * v - PLANT_A0 * y + w


def char_poly_residual(lam, omega_o):
    """det(lam I - (A - beta C)) - (lam + w_o)^3 residual at a sample lam.

    The LESO error-dynamics characteristic polynomial from the bandwidth
    parameterization is lam^3 + beta1 lam^2 + beta2 lam + beta3, which must
    equal (lam + w_o)^3 at every lam; the residual is float noise.
    """
    b1, b2, b3 = observer_gains(omega_o)
    return (lam * lam * lam + b1 * lam * lam + b2 * lam + b3) - (lam + omega_o) ** 3


def simulate_adrc(plant_b=PLANT_B_WORKED, b0=B0, omega_c=OMEGA_C, omega_o=OMEGA_O,
                  r=REFERENCE_R, w0=W0, w1=W1, t_step=T_STEP,
                  y0=INIT_Y, v0=INIT_V, dt=DT, sim_time=SIM_TIME):
    """Closed-loop forward-Euler simulation of the ADRC law on the truth
    plant y'' = -A1 y' - A0 y + w(t) + plant_b u.

    Design values b0, omega_c, omega_o are fixed for both the worked
    (plant_b = b0 = 1.0) and the mismatch (plant_b = 0.8) runs. The LESO
    starts at the zero estimate and the disturbance steps from w0 to w1 at
    t = t_step. History[k] is the value at time k*dt, after k advances.
    Returns a dict with the time, plant, estimate and command series plus
    the metric windows. ValueErrors: b0 == 0, omega_c <= 0, omega_o <= 0,
    omega_o <= omega_c, dt <= 0, sim_time <= 0, t_step outside (0, sim_time).
    """
    if b0 == 0.0:
        raise ValueError("control-effectiveness estimate b0 must be nonzero, got 0.0")
    if omega_c <= 0.0:
        raise ValueError("controller bandwidth omega_c must be positive, got %s" % omega_c)
    if omega_o <= 0.0:
        raise ValueError("observer bandwidth omega_o must be positive, got %s" % omega_o)
    if omega_o <= omega_c:
        raise ValueError(
            "observer bandwidth omega_o must exceed the controller bandwidth omega_c, "
            "got omega_o %s <= omega_c %s" % (omega_o, omega_c))
    if dt <= 0.0:
        raise ValueError("sample time dt must be positive, got %s" % dt)
    if sim_time <= 0.0:
        raise ValueError("simulation time sim_time must be positive, got %s" % sim_time)
    if t_step <= 0.0 or t_step >= sim_time:
        raise ValueError(
            "disturbance step time t_step must lie strictly inside (0, sim_time), "
            "got t_step %s for sim_time %s" % (t_step, sim_time))

    kp, kd = controller_gains(omega_c)
    b1, b2, b3 = observer_gains(omega_o)
    n = int(sim_time / dt) + 1
    y, v, z1, z2, z3 = y0, v0, INIT_Z[0], INIT_Z[1], INIT_Z[2]
    t_hist, y_hist, v_hist, e_hist = [], [], [], []
    u_hist, u0_hist, z3_hist, f_hist = [], [], [], []
    for k in range(n):
        t = k * dt
        w = w0 if t < t_step else w1
        f = total_disturbance(y, v, w)
        u0 = kp * (r - z1) - kd * z2
        u = (u0 - z3) / b0
        t_hist.append(t)
        y_hist.append(y)
        v_hist.append(v)
        e_hist.append(y - r)
        u_hist.append(u)
        u0_hist.append(u0)
        z3_hist.append(z3)
        f_hist.append(f)
        y = y + dt * v
        v = v + dt * (f + plant_b * u)
        ey = y - z1
        z1 = z1 + dt * (z2 + b1 * ey)
        z2 = z2 + dt * (z3 + b2 * ey + b0 * u)
        z3 = z3 + dt * (b3 * ey)
    tail0 = int(TAIL_START / dt)
    rec0 = int(RECOVERY_START / dt)
    set0 = int(SETTLE_START / dt)
    max_abs_e_tail = max(abs(e) for e in e_hist[tail0:])
    max_z3_res_tail = max(abs(z3_hist[k] - f_hist[k]) for k in range(tail0, n))
    max_abs_e_rec = max(abs(e) for e in e_hist[rec0:])
    max_abs_e_settle = max(abs(e) for e in e_hist[set0:])
    max_z3_res_settle = max(abs(z3_hist[k] - f_hist[k]) for k in range(set0, n))
    return {
        "t": t_hist, "y": y_hist, "v": v_hist, "e": e_hist,
        "u": u_hist, "u0": u0_hist, "z3": z3_hist, "f": f_hist,
        "n": n, "dt": dt, "kp": kp, "kd": kd, "beta": (b1, b2, b3),
        "max_abs_e_tail": max_abs_e_tail, "max_z3_res_tail": max_z3_res_tail,
        "max_abs_e_rec": max_abs_e_rec,
        "max_abs_e_settle": max_abs_e_settle, "max_z3_res_settle": max_z3_res_settle,
    }


def simulate_ideal(plant_b=PLANT_B_WORKED, omega_c=OMEGA_C,
                   r=REFERENCE_R, y0=INIT_Y, v0=INIT_V, dt=DT, sim_time=SIM_TIME):
    """Ideal-loop comparison run: the same truth plant and the same outer
    PD law with PERFECT state knowledge and PERFECT disturbance
    cancellation at every sample (u0 = kp (r - y) - kd v, u = (u0 - f)/b
    with b = plant_b), so the plant channel is the exact double integrator
    y'' = u0 regardless of f. Same forward Euler and dt, so the difference
    against the ADRC run isolates observer error only. Returns the dict."""
    kp, kd = controller_gains(omega_c)
    n = int(sim_time / dt) + 1
    y, v = y0, v0
    t_hist, y_hist, e_hist = [], [], []
    for k in range(n):
        t = k * dt
        w = W0 if t < T_STEP else W1
        f = total_disturbance(y, v, w)
        u0 = kp * (r - y) - kd * v
        u = (u0 - f) / plant_b
        t_hist.append(t)
        y_hist.append(y)
        e_hist.append(y - r)
        y = y + dt * v
        v = v + dt * (f + plant_b * u)
    return {"t": t_hist, "y": y_hist, "e": e_hist, "n": n, "dt": dt}


def sample_at(hist, t, dt):
    """Value of a sample history at the sample time t (t must be an exact
    multiple of dt)."""
    k = int(round(t / dt))
    return hist[k]


def main():
    # Bandwidth parameterization and closed-form polynomial identities
    b1, b2, b3 = observer_gains(OMEGA_O)
    kp, kd = controller_gains(OMEGA_C)
    print("Design (module output):")
    print("  omega_c = %.1f rad/s, omega_o = %.1f rad/s, ratio omega_o/omega_c = %.1f"
          % (OMEGA_C, OMEGA_O, OMEGA_O / OMEGA_C))
    print("  b0 = %.1f (worked plant gain b = %.1f matched; robustness b = %.1f)"
          % (B0, PLANT_B_WORKED, PLANT_B_MISMATCH))
    print("  observer_gains(%.1f) = (%.9f, %.9f, %.9f)" % (OMEGA_O, b1, b2, b3))
    print("  controller_gains(%.1f) = (%.9f, %.9f)" % (OMEGA_C, kp, kd))
    print("  char-poly residuals det(sI - (A - beta C)) - (s + w_o)^3:")
    for lam in (-OMEGA_O, -3.0, -1.0, 0.5):
        print("    at s = %8.3f: %.3e" % (lam, char_poly_residual(lam, OMEGA_O)))
    assert abs(char_poly_residual(-OMEGA_O, OMEGA_O)) < 1e-9
    assert abs(char_poly_residual(-3.0, OMEGA_O)) < 1e-9
    assert char_poly_residual(-OMEGA_O, OMEGA_O) == 0.0  # exact: integer float arithmetic

    # Disturbance-cancellation algebraic identity at the phase equilibria
    f1 = total_disturbance(1.0, 0.0, W0)
    f2 = total_disturbance(1.0, 0.0, W1)
    res1 = cancellation_residual(f1, 0.0, f1, B0)
    res2 = cancellation_residual(f2, 0.0, f2, B0)
    print("Fixed points of the cancelled loop (y = r = 1.0, v = 0, u0 = 0):")
    print("  phase 1 (w = %.1f): f = %.9f, u = (0 - z3)/b0 = %.9f, f + b0 u = %.3e"
          % (W0, f1, -f1 / B0, res1))
    print("  phase 2 (w = %.1f): f = %.9f, u = (0 - z3)/b0 = %.9f, f + b0 u = %.3e"
          % (W1, f2, -f2 / B0, res2))
    print("  cancellation_residual(f, u0, z3, b0) with z3 = f: %.3e and %.3e" % (res1, res2))
    assert abs(res1) < 1e-12 and abs(res2) < 1e-12
    assert abs(f1 - 0.0) < 1e-12 and abs(f2 - 1.0) < 1e-12

    # Exact closed-form ideal double-integrator step response, 1 - (1 + w_c t) e^-w_c t
    e5 = math.exp(-5.0)
    e1 = math.exp(-1.0)
    e2p5 = math.exp(-2.5)
    y_exact_02 = 1.0 - 2.0 * e1          # t = 1/w_c = 0.2 s
    y_exact_05 = 1.0 - 3.5 * e2p5        # t = 0.5 s
    y_exact_1 = 1.0 - 6.0 * e5           # t = 1.0 s
    print("Exact ideal closed-form step response 1 - (1 + w_c t) exp(-w_c t):")
    print("  t = 0.2 s (1/w_c): %.12f   t = 0.5 s: %.12f   t = 1.0 s: %.12f"
          % (y_exact_02, y_exact_05, y_exact_1))

    # Worked run: gain-matched, disturbance step +1.0 at t = 3.0 s
    sim = simulate_adrc()
    e_hist, y_hist, u_hist, z3_hist, f_hist = sim["e"], sim["y"], sim["u"], sim["z3"], sim["f"]
    print("Worked run (b = b0 = 1.0), Euler dt = %.1e s, %d samples:" % (DT, sim["n"]))
    for tt in (0.2, 0.5, 1.0, 2.0, 3.0):
        k = int(round(tt / DT))
        print("  t = %.2f s: y %.12f  e %.12f  u %.12f  z3 %.12f"
              % (tt, y_hist[k], e_hist[k], u_hist[k], z3_hist[k]))
    print("  disturbance step at t = %.1f s (w: %.1f -> %.1f):" % (T_STEP, W0, W1))
    for tt in (3.05, 3.1, 3.25, 3.5, 4.0, 5.0, 6.0):
        k = int(round(tt / DT))
        print("  t = %.2f s: y %.12f  e %.12f  u %.12f  z3 %.12f"
              % (tt, y_hist[k], e_hist[k], u_hist[k], z3_hist[k]))
    print("  worked metrics: e(6.0) %.3e  max|e| over [%.1f, 6.0] %.3e"
          % (e_hist[-1], RECOVERY_START, sim["max_abs_e_rec"]))
    print("    max|e| over [%.1f, 6.0] %.3e  (decay tail, outer pole at -w_c)"
          % (TAIL_START, sim["max_abs_e_tail"]))
    print("    max|e| over [%.1f, 6.0] %.3e  max|z3 - f_truth| over [%.1f, 6.0] %.3e"
          % (SETTLE_START, sim["max_abs_e_settle"], SETTLE_START, sim["max_z3_res_settle"]))
    print("    z3(6.0) %.12f  f_truth(6.0) %.12f  u(6.0) %.12f  u0(6.0) %.3e"
          % (z3_hist[-1], f_hist[-1], u_hist[-1], sim["u0"][-1]))
    # Worked sample assertions (headline numbers the contract test asserts)
    k6 = int(round(6.0 / DT))
    assert abs(y_hist[k6] - 1.0) < 1e-6
    assert abs(e_hist[k6]) < 1e-6
    assert abs(z3_hist[k6] - 1.0) < 1e-5
    assert abs(u_hist[k6] + 1.0) < 1e-5
    assert sim["max_abs_e_settle"] < 1e-5
    assert sim["max_z3_res_settle"] < 1e-4

    # Ideal-loop comparison: ADRC minus perfect-cancellation double integrator
    ide = simulate_ideal()
    d_full = max(abs(y_hist[k] - ide["y"][k]) for k in range(sim["n"]))
    tail0 = int(TAIL_START / DT)
    set0 = int(SETTLE_START / DT)
    d_tail = max(abs(y_hist[k] - ide["y"][k]) for k in range(tail0, sim["n"]))
    d_settle = max(abs(y_hist[k] - ide["y"][k]) for k in range(set0, sim["n"]))
    k1 = int(round(1.0 / DT))
    lag_deficit = y_hist[k1] - ide["y"][k1]
    dev_ideal_exact = abs(ide["y"][k1] - y_exact_1)
    print("Ideal-loop comparison (same Euler, perfect cancellation):")
    print("  max|y_adrc - y_ideal| over [0.0, 6.0] %.3e ; over [%.1f, 6.0] %.3e"
          % (d_full, TAIL_START, d_tail))
    print("  max|y_adrc - y_ideal| over [%.1f, 6.0] %.3e (observer-lag cost of the step)"
          % (SETTLE_START, d_settle))
    print("  observer-lag deficit y_adrc(1.0) - y_ideal(1.0) = %.12f"
          % lag_deficit)
    print("  |y_ideal(1.0) - exact 1 - 6 e^-5| = %.3e (Euler truncation witness)"
          % dev_ideal_exact)
    assert d_full < 2e-2 and d_tail < 2e-3 and d_settle < 1e-5
    assert dev_ideal_exact < 5e-4

    # Robustness run: true gain b = 0.8 against the b0 = 1.0 design
    rob = simulate_adrc(plant_b=PLANT_B_MISMATCH)
    rb = int(round(3.0 / DT))
    r6 = int(round(6.0 / DT))
    print("Mismatch robustness run (b = 0.8, b0 = 1.0, 25 percent over-modeled):")
    print("  y(3.0) %.12f  y(6.0) %.12f  e(6.0) %.3e  z3(6.0) %.12f  u(6.0) %.12f"
          % (rob["y"][rb], rob["y"][r6], rob["e"][r6], rob["z3"][r6], rob["u"][r6]))
    print("  max|z3 - f_truth| over [%.1f, 6.0] %.3e  max|e| over [%.1f, 6.0] %.3e"
          % (TAIL_START, rob["max_z3_res_tail"], RECOVERY_START, rob["max_abs_e_rec"]))
    print("  max|e| over [%.1f, 6.0] %.3e  max|z3 - f_truth| over [%.1f, 6.0] %.3e"
          % (SETTLE_START, rob["max_abs_e_settle"], SETTLE_START, rob["max_z3_res_settle"]))
    print("  fixed point under mismatch: z3 = -b0 u = %.9f vs f_truth = %.9f"
          % (-B0 * rob["u"][r6], rob["f"][r6]))
    assert abs(rob["y"][r6] - 1.0) < 1e-5
    assert abs(rob["u"][r6] + 1.25) < 1e-3
    assert abs(rob["z3"][r6] - 1.25) < 1e-3

    # ValueErrors with the real messages
    def expect_value_error(label, fn):
        try:
            fn()
        except ValueError as exc:
            print("ValueError %s: %s" % (label, exc))
            return
        raise AssertionError("no ValueError raised for %s" % label)

    print("ValueError guards (module output, real messages):")
    expect_value_error("observer_gains(0.0)", lambda: observer_gains(0.0))
    expect_value_error("controller_gains(0.0)", lambda: controller_gains(0.0))
    expect_value_error("control_law b0 = 0.0",
                       lambda: control_law(1.0, 0.0, 0.0, 0.0, 0.0, kp, kd))
    expect_value_error("cancellation_residual b0 = 0.0",
                       lambda: cancellation_residual(0.5, 0.0, 0.5, 0.0))
    expect_value_error("simulate_adrc b0 = 0.0", lambda: simulate_adrc(b0=0.0))
    expect_value_error("simulate_adrc omega_c = 0.0", lambda: simulate_adrc(omega_c=0.0))
    expect_value_error("simulate_adrc omega_o = 0.0", lambda: simulate_adrc(omega_o=0.0))
    expect_value_error("simulate_adrc omega_o = omega_c",
                       lambda: simulate_adrc(omega_c=5.0, omega_o=5.0))
    expect_value_error("simulate_adrc dt = 0.0", lambda: simulate_adrc(dt=0.0))
    expect_value_error("simulate_adrc sim_time = 0.0", lambda: simulate_adrc(sim_time=0.0))
    expect_value_error("simulate_adrc t_step = sim_time",
                       lambda: simulate_adrc(t_step=SIM_TIME))

    print("ALL INTERNAL ASSERTS PASSED")


if __name__ == "__main__":
    main()
