"""Model-reference adaptive control (MRAC) for a first-order plant.

Pure stdlib, deterministic, discrete-time Euler integration. The plant
coefficient a_p is unknown to the controller; the adaptive gains are
updated online by the gradient (Lyapunov-motivated) adaptation law
driven by the tracking error e = x - xm, where xm is the state of the
stable reference model driven by the same command.

Reference model:   xm_next = xm + dt * (a_m * xm + b_m * command)
Plant model:       x_next  = x  + dt * (a_p * x  + b_p * control)
Control law:       u       = theta_x * x + theta_r * command
Adaptation law:    theta_x_new = theta_x - gamma_x * e * x * dt
                   theta_r_new = theta_r - gamma_r * e * command * dt

Ideal cancellation gains (b_p known and positive): theta_x_star =
(a_m - a_p) / b_p, theta_r_star = b_m / b_p. Single input, no noise, no
disturbance, sign of the control effectiveness known positive.
"""

MAX_STEPS_DEFAULT = 2000

# Convergence tolerances used by simulate() for the verdict.
_ERROR_WINDOW = 200  # steps over which the tracking error tail is checked
_ERROR_TOL = 1e-4    # max abs tracking error over the tail window
_GAIN_TOL = 0.05     # max abs deviation of the final gains from ideal


def reference_step(xm, command, a_m, b_m, dt):
    """Advance the reference model state by one Euler step of size dt.

    The reference model must be stable (a_m < 0) so that xm settles on
    b_m * command / (-a_m) for a constant command.
    """
    if a_m >= 0:
        raise ValueError("reference model must be stable (a_m < 0)")
    return xm + dt * (a_m * xm + b_m * command)


def plant_step(x, control, a_p, b_p, dt):
    """Advance the first-order plant state by one Euler step of size dt."""
    return x + dt * (a_p * x + b_p * control)


def control_output(theta_x, theta_r, x, command):
    """Adaptive control output u = theta_x * x + theta_r * command."""
    return theta_x * x + theta_r * command


def ideal_gains(a_p, b_p, a_m, b_m):
    """Ideal cancellation gains that make the closed loop match the model.

    Returns dict with keys theta_x_star = (a_m - a_p) / b_p and
    theta_r_star = b_m / b_p. Raises ValueError when b_p == 0 (the
    plant must be controllable, control effectiveness nonzero).
    """
    if b_p == 0:
        raise ValueError("plant control effectiveness b_p must be nonzero")
    return {
        "theta_x_star": (a_m - a_p) / b_p,
        "theta_r_star": b_m / b_p,
    }


def adaptation_step(theta_x, theta_r, error, x, command, gamma_x, gamma_r, dt):
    """One gradient adaptation update of the two adaptive gains.

    error is the tracking error x - xm (or x - x_ref); the rule is the
    discrete form of the Lyapunov-motivated gradient law for a plant
    with known-positive control effectiveness:
      theta_x_new = theta_x - gamma_x * error * x * dt
      theta_r_new = theta_r - gamma_r * error * command * dt
    """
    if gamma_x < 0 or gamma_r < 0:
        raise ValueError("adaptation rates gamma_x and gamma_r must be >= 0")
    theta_x_new = theta_x - gamma_x * error * x * dt
    theta_r_new = theta_r - gamma_r * error * command * dt
    return theta_x_new, theta_r_new


def simulate(plant_a, plant_b, model_a, model_b, dt, gamma_x, gamma_r,
             command=1.0, x0=0.0, steps=MAX_STEPS_DEFAULT):
    """Simulate the closed loop with online adaptation and judge convergence.

    Both the plant and the reference model start at x0 with zero initial
    gains (theta_x = theta_r = 0), a documented assumption. Each step
    applies the control from the current gains, advances the plant and
    the reference model by dt, then samples the tracking error and the
    plant state after the advance and updates the gains (the discrete
    Euler ordering that drives the gains to the ideal values). Returns a
    dict with the time history lists t_list, x_list, xm_list, u_list,
    theta_x_list, theta_r_list (each steps + 1 entries, index 0 the
    initial condition), error_final, max_abs_error, and the boolean
    converged verdict. converged is True when max(abs(error)) over the
    last 200 steps is below 1e-4 and both final gains sit within 0.05 of
    the ideal cancellation gains.
    """
    if model_a >= 0:
        raise ValueError("reference model must be stable (model_a < 0)")
    if dt <= 0:
        raise ValueError("time step dt must be positive")
    if steps < 2:
        raise ValueError("steps must be at least 2")
    if gamma_x < 0 or gamma_r < 0:
        raise ValueError("adaptation rates gamma_x and gamma_r must be >= 0")
    if plant_b == 0:
        raise ValueError("plant control effectiveness plant_b must be nonzero")

    star = ideal_gains(plant_a, plant_b, model_a, model_b)
    theta_x_star = star["theta_x_star"]
    theta_r_star = star["theta_r_star"]

    x = x0
    xm = x0
    theta_x = 0.0
    theta_r = 0.0

    t_list = [0.0]
    x_list = [x0]
    xm_list = [x0]
    u_list = [control_output(theta_x, theta_r, x, command)]
    theta_x_list = [theta_x]
    theta_r_list = [theta_r]

    for i in range(steps):
        u = control_output(theta_x, theta_r, x, command)
        x = plant_step(x, u, plant_a, plant_b, dt)
        xm = reference_step(xm, command, model_a, model_b, dt)
        error = x - xm
        theta_x, theta_r = adaptation_step(
            theta_x, theta_r, error, x, command, gamma_x, gamma_r, dt
        )
        t_list.append((i + 1) * dt)
        x_list.append(x)
        xm_list.append(xm)
        u_list.append(u)
        theta_x_list.append(theta_x)
        theta_r_list.append(theta_r)

    errors = [xi - xmi for xi, xmi in zip(x_list, xm_list)]
    window = min(_ERROR_WINDOW, len(errors))
    tail_max = max(abs(e) for e in errors[-window:])
    max_abs_error = max(abs(e) for e in errors)
    error_final = errors[-1]

    gains_ok = (abs(theta_x - theta_x_star) < _GAIN_TOL and
                abs(theta_r - theta_r_star) < _GAIN_TOL)
    converged = tail_max < _ERROR_TOL and gains_ok

    return {
        "t_list": t_list,
        "x_list": x_list,
        "xm_list": xm_list,
        "u_list": u_list,
        "theta_x_list": theta_x_list,
        "theta_r_list": theta_r_list,
        "error_final": error_final,
        "max_abs_error": max_abs_error,
        "converged": converged,
    }


def gain_convergence_report(plant_a, plant_b, model_a, model_b, dt,
                            gamma_x, gamma_r, command=1.0, x0=0.0,
                            steps=MAX_STEPS_DEFAULT):
    """Convergence report on the final gains and the tracking tail.

    Runs the same closed-loop simulation as simulate() and returns the
    ideal gains, the final adaptive gains, their signed deviations from
    ideal, and the root mean square tracking error over the last 500
    steps (tracking_rmse).
    """
    result = simulate(plant_a, plant_b, model_a, model_b, dt, gamma_x,
                      gamma_r, command=command, x0=x0, steps=steps)
    star = ideal_gains(plant_a, plant_b, model_a, model_b)
    theta_x_star = star["theta_x_star"]
    theta_r_star = star["theta_r_star"]

    theta_x_final = result["theta_x_list"][-1]
    theta_r_final = result["theta_r_list"][-1]

    tail = 500
    errors = [xi - xmi for xi, xmi in zip(result["x_list"], result["xm_list"])]
    window = errors[-tail:]
    tracking_rmse = (sum(e * e for e in window) / len(window)) ** 0.5

    return {
        "theta_x_star": theta_x_star,
        "theta_r_star": theta_r_star,
        "theta_x_final": theta_x_final,
        "theta_r_final": theta_r_final,
        "theta_x_error": theta_x_final - theta_x_star,
        "theta_r_error": theta_r_final - theta_r_star,
        "tracking_rmse": tracking_rmse,
    }
