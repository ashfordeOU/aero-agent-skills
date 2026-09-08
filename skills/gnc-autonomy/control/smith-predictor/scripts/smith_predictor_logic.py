"""Smith predictor dead-time compensation for a single feedback loop.

Pure stdlib (math only), deterministic, no RNG, closed form and exact
sampled first-order recurrence. See SKILL.md Domain quick reference for
the defining relations.
"""

import math

PLANT_GAIN_K = 1.0
PLANT_TAU = 1.0
WORKED_THETA = 2.0
ROBUST_THETA = 5.0
CONTROLLER_KP = 0.5
CONTROLLER_KI = 0.5
SAMPLE_DT = 0.01
SIM_TIME = 60.0
REFERENCE = 1.0
SETTLE_BAND = 0.02
STEPS_EPS = 1e-6
CL_POLE_RATE = 0.5
CL_TAU = 2.0


def first_order_lag_recurrence(gain, tau, dt):
    """Exact sampled recurrence coefficients (a, b) of gain / (tau s + 1) at dt."""
    if gain <= 0:
        raise ValueError(f"plant gain K must be positive, got {gain}")
    if tau <= 0:
        raise ValueError(f"plant time constant tau must be positive, got {tau}")
    if dt <= 0:
        raise ValueError(f"sample time dt must be positive, got {dt}")
    a = math.exp(-dt / tau)
    b = gain * (1.0 - a)
    return a, b


def delay_steps(dead_time, dt):
    """Integer pure-delay line length D = round(dead_time / dt)."""
    if dead_time < 0:
        raise ValueError(f"dead time theta must be non-negative, got {dead_time}")
    if dt <= 0:
        raise ValueError(f"sample time dt must be positive, got {dt}")
    ratio = dead_time / dt
    nearest = round(ratio)
    if abs(ratio - nearest) > STEPS_EPS:
        raise ValueError(
            f"dead time theta must be an integer multiple of dt, got theta {dead_time} at dt {dt}"
        )
    return int(nearest)


def pi_output(error, integral, dt, kp, ki):
    """One PI step: forward integral accumulation then the control law."""
    if kp <= 0:
        raise ValueError(f"proportional gain kp must be positive, got {kp}")
    if ki < 0:
        raise ValueError(f"integral gain ki must be non-negative, got {ki}")
    if dt <= 0:
        raise ValueError(f"sample time dt must be positive, got {dt}")
    integral_next = integral + error * dt
    u = kp * error + ki * integral_next
    return u, integral_next


def step_metrics(t, y, reference=REFERENCE, band=SETTLE_BAND):
    """Overshoot, peak time, settling time and final deviation of a step response."""
    if len(y) == 0:
        raise ValueError("response series is empty")
    peak_val = max(y)
    overshoot_pct = max(0.0, (peak_val - reference) / reference) * 100.0
    peak_idx = y.index(peak_val)
    peak_time = t[peak_idx]
    tol = band * reference
    last_viol = None
    for k in range(len(y) - 1, -1, -1):
        if abs(y[k] - reference) > tol:
            last_viol = k
            break
    if last_viol is None:
        settling_time = t[0]
    elif last_viol == len(y) - 1:
        settling_time = None
    else:
        settling_time = t[last_viol + 1]
    final_deviation = abs(y[-1] - reference)
    return {
        "overshoot_pct": overshoot_pct,
        "peak_time": peak_time,
        "settling_time": settling_time,
        "final_deviation": final_deviation,
    }


def _simulate_series(gain, tau, dead_time, kp, ki, dt, sim_time, predictor, reference):
    a, b = first_order_lag_recurrence(gain, tau, dt)
    d_steps = delay_steps(dead_time, dt)
    n_steps = int(round(sim_time / dt))

    y = [0.0] * (n_steps + 1)
    ym = [0.0] * (n_steps + 1)
    u_hist = [0.0] * n_steps
    t = [k * dt for k in range(n_steps + 1)]
    controller_error = [0.0] * (n_steps + 1)

    integral = 0.0
    for k in range(n_steps):
        if predictor:
            ym_delayed = ym[k - d_steps] if k - d_steps >= 0 else 0.0
            error = reference - y[k] - ym[k] + ym_delayed
        else:
            error = reference - y[k]
        controller_error[k] = error
        u, integral = pi_output(error, integral, dt, kp, ki)
        u_hist[k] = u

        u_delayed = u_hist[k - d_steps] if k - d_steps >= 0 else 0.0
        y[k + 1] = a * y[k] + b * u_delayed
        ym[k + 1] = a * ym[k] + b * u

    if predictor:
        ym_delayed_last = ym[n_steps - d_steps] if n_steps - d_steps >= 0 else 0.0
        controller_error[n_steps] = reference - y[n_steps] - ym[n_steps] + ym_delayed_last
    else:
        controller_error[n_steps] = reference - y[n_steps]

    return t, y, controller_error, d_steps


def simulate_closed_loop(
    gain=PLANT_GAIN_K,
    tau=PLANT_TAU,
    dead_time=WORKED_THETA,
    kp=CONTROLLER_KP,
    ki=CONTROLLER_KI,
    dt=SAMPLE_DT,
    sim_time=SIM_TIME,
    predictor=True,
    reference=REFERENCE,
):
    """Discrete closed-loop step simulation of the FOPDT plant under the PI controller."""
    if sim_time <= 0:
        raise ValueError(f"simulation time sim_time must be positive, got {sim_time}")
    t, y, controller_error, d_steps = _simulate_series(
        gain, tau, dead_time, kp, ki, dt, sim_time, predictor, reference
    )
    metrics = step_metrics(t, y, reference=reference)
    return {
        "t": t,
        "y": y,
        "controller_error": controller_error,
        "metrics": metrics,
        "d_steps": d_steps,
    }


def delay_shift_max_error(y_predictor, y_delay_free, d_steps):
    """Max abs error between the predictor loop and the delay-free loop shifted by d_steps."""
    if len(y_predictor) != len(y_delay_free):
        raise ValueError("response series lengths differ")
    n = len(y_predictor)
    if d_steps < 0 or d_steps >= n:
        raise ValueError("d_steps outside the alignment window")
    max_err = 0.0
    for k in range(d_steps, n):
        err = abs(y_predictor[k] - y_delay_free[k - d_steps])
        if err > max_err:
            max_err = err
    return max_err
