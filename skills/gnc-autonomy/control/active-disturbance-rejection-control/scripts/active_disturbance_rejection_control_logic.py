"""Active disturbance rejection control (ADRC) logic.

Linear ADRC for the canonical second-order plant y_ddot = f(y, y_dot, w)
+ b0 u, with f the total disturbance (internal dynamics plus external
disturbance, lumped and unknown to the controller). A third-order linear
extended state observer (LESO) estimates the state and the total
disturbance from bandwidth-parameterized gains beta = (3 omega_o,
3 omega_o^2, omega_o^3) placing all observer error poles at -omega_o.
The control law u = (u0 - z3) / b0 cancels the disturbance estimate so
the plant channel collapses to the ideal double integrator y_ddot = u0,
and the outer loop u0 = kp (r - z1) - kd z2 with kp = omega_c^2, kd =
2 omega_c places the tracking poles at -omega_c.

Pure stdlib, deterministic, forward-Euler discrete time. No RNG.
"""

import math

OMEGA_C = 5.0
OMEGA_O = 30.0
B0 = 1.0
PLANT_B_WORKED = 1.0
PLANT_B_MISMATCH = 0.8
PLANT_A1 = 0.75
PLANT_A0 = 0.5
W0 = 0.5
W1 = 1.5
T_STEP = 3.0
REFERENCE_R = 1.0
INIT_Y = 0.0
INIT_V = 0.0
INIT_Z = (0.0, 0.0, 0.0)
DT = 1e-4
SIM_TIME = 6.0
TAIL_START = 4.5
SETTLE_START = 5.5
RECOVERY_START = 3.0


def observer_gains(omega_o):
    """Bandwidth-parameterized LESO gains beta = (3 wo, 3 wo^2, wo^3)."""
    if omega_o <= 0:
        raise ValueError(
            "observer bandwidth omega_o must be positive, got {0}".format(omega_o)
        )
    return (3.0 * omega_o, 3.0 * omega_o ** 2, omega_o ** 3)


def controller_gains(omega_c):
    """Bandwidth-parameterized PD outer-loop gains kp = wc^2, kd = 2 wc."""
    if omega_c <= 0:
        raise ValueError(
            "controller bandwidth omega_c must be positive, got {0}".format(omega_c)
        )
    return (omega_c ** 2, 2.0 * omega_c)


def control_law(r, z1, z2, z3, b0, kp, kd):
    """Disturbance-rejection control u = (u0 - z3) / b0 on estimated states."""
    if b0 == 0:
        raise ValueError(
            "control-effectiveness estimate b0 must be nonzero, got {0}".format(b0)
        )
    u0 = kp * (r - z1) - kd * z2
    return (u0 - z3) / b0


def cancellation_residual(f, u0, z3, b0):
    """Residual f + b0 ((u0 - z3) / b0) - u0, zero when z3 = f."""
    if b0 == 0:
        raise ValueError(
            "control-effectiveness estimate b0 must be nonzero, got {0}".format(b0)
        )
    u = (u0 - z3) / b0
    return f + b0 * u - u0


def total_disturbance(y, v, w):
    """Simulator-truth total disturbance f = -A1 v - A0 y + w."""
    return -PLANT_A1 * v - PLANT_A0 * y + w


def char_poly_residual(lam, omega_o):
    """Residual of s^3 + beta1 s^2 + beta2 s + beta3 against (s + wo)^3."""
    if omega_o <= 0:
        raise ValueError(
            "observer bandwidth omega_o must be positive, got {0}".format(omega_o)
        )
    beta1, beta2, beta3 = observer_gains(omega_o)
    lhs = lam ** 3 + beta1 * lam ** 2 + beta2 * lam + beta3
    rhs = (lam + omega_o) ** 3
    return lhs - rhs


def _validate_sim_guards(b0, omega_c, omega_o, dt, sim_time, t_step):
    if b0 == 0:
        raise ValueError(
            "control-effectiveness estimate b0 must be nonzero, got {0}".format(b0)
        )
    if omega_c <= 0:
        raise ValueError(
            "controller bandwidth omega_c must be positive, got {0}".format(omega_c)
        )
    if omega_o <= 0:
        raise ValueError(
            "observer bandwidth omega_o must be positive, got {0}".format(omega_o)
        )
    if omega_o <= omega_c:
        raise ValueError(
            "observer bandwidth omega_o must exceed the controller bandwidth "
            "omega_c, got omega_o {0} <= omega_c {1}".format(omega_o, omega_c)
        )
    if dt <= 0:
        raise ValueError("sample time dt must be positive, got {0}".format(dt))
    if sim_time <= 0:
        raise ValueError(
            "simulation time sim_time must be positive, got {0}".format(sim_time)
        )
    if not (0 < t_step < sim_time):
        raise ValueError(
            "disturbance step time t_step must lie strictly inside (0, "
            "sim_time), got t_step {0} for sim_time {1}".format(t_step, sim_time)
        )


def _new_history():
    return {"t": [], "y": [], "v": [], "e": [], "u": [], "u0": [], "z3": [], "f": []}


def _max_abs_over(t_series, series, start, end):
    vals = [abs(s) for t, s in zip(t_series, series) if start <= t <= end]
    return max(vals) if vals else 0.0


def simulate_adrc(
    plant_b=PLANT_B_WORKED,
    b0=B0,
    omega_c=OMEGA_C,
    omega_o=OMEGA_O,
    r=REFERENCE_R,
    w0=W0,
    w1=W1,
    t_step=T_STEP,
    y0=INIT_Y,
    v0=INIT_V,
    dt=DT,
    sim_time=SIM_TIME,
):
    """Closed-loop forward-Euler ADRC simulation on the truth plant."""
    _validate_sim_guards(b0, omega_c, omega_o, dt, sim_time, t_step)
    kp, kd = controller_gains(omega_c)
    beta1, beta2, beta3 = observer_gains(omega_o)

    y, v = y0, v0
    z1, z2, z3 = INIT_Z
    n = int(sim_time / dt) + 1
    hist = _new_history()

    for k in range(n):
        t = k * dt
        w = w0 if t < t_step else w1
        f = total_disturbance(y, v, w)
        u0 = kp * (r - z1) - kd * z2
        u = (u0 - z3) / b0

        hist["t"].append(t)
        hist["y"].append(y)
        hist["v"].append(v)
        hist["e"].append(y - r)
        hist["u"].append(u)
        hist["u0"].append(u0)
        hist["z3"].append(z3)
        hist["f"].append(f)

        y = y + dt * v
        v = v + dt * (f + plant_b * u)
        ey = y - z1
        z1 = z1 + dt * (z2 + beta1 * ey)
        z2 = z2 + dt * (z3 + beta2 * ey + b0 * u)
        z3 = z3 + dt * (beta3 * ey)

    z3_res = [abs(z - fv) for z, fv in zip(hist["z3"], hist["f"])]

    return {
        "t": hist["t"],
        "y": hist["y"],
        "v": hist["v"],
        "e": hist["e"],
        "u": hist["u"],
        "u0": hist["u0"],
        "z3": hist["z3"],
        "f": hist["f"],
        "n": n,
        "dt": dt,
        "kp": kp,
        "kd": kd,
        "beta": (beta1, beta2, beta3),
        "max_abs_e_rec": _max_abs_over(hist["t"], hist["e"], RECOVERY_START, sim_time),
        "max_abs_e_tail": _max_abs_over(hist["t"], hist["e"], TAIL_START, sim_time),
        "max_z3_res_tail": max(
            (r for t, r in zip(hist["t"], z3_res) if TAIL_START <= t <= sim_time),
            default=0.0,
        ),
        "max_abs_e_settle": _max_abs_over(hist["t"], hist["e"], SETTLE_START, sim_time),
        "max_z3_res_settle": max(
            (r for t, r in zip(hist["t"], z3_res) if SETTLE_START <= t <= sim_time),
            default=0.0,
        ),
    }


def simulate_ideal(
    plant_b=PLANT_B_WORKED,
    omega_c=OMEGA_C,
    r=REFERENCE_R,
    y0=INIT_Y,
    v0=INIT_V,
    dt=DT,
    sim_time=SIM_TIME,
):
    """Ideal-loop comparison: perfect state knowledge and perfect cancellation."""
    if omega_c <= 0:
        raise ValueError(
            "controller bandwidth omega_c must be positive, got {0}".format(omega_c)
        )
    if dt <= 0:
        raise ValueError("sample time dt must be positive, got {0}".format(dt))
    if sim_time <= 0:
        raise ValueError(
            "simulation time sim_time must be positive, got {0}".format(sim_time)
        )
    kp, kd = controller_gains(omega_c)

    y, v = y0, v0
    n = int(sim_time / dt) + 1
    t_series = []
    y_series = []
    e_series = []

    for k in range(n):
        t = k * dt
        u0 = kp * (r - y) - kd * v
        # Perfect cancellation: u = (u0 - f) / plant_b makes y_ddot = u0.
        t_series.append(t)
        y_series.append(y)
        e_series.append(y - r)

        y_next = y + dt * v
        v_next = v + dt * u0
        y, v = y_next, v_next

    return {"t": t_series, "y": y_series, "e": e_series, "n": n, "dt": dt}
