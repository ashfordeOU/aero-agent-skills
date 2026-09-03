"""Dynamic indicial gust response of a flexible 2-DOF typical wing section.

Pure-stdlib engineering model of the gust RESPONSE problem for a
two-degree-of-freedom (plunge h, pitch theta) typical section with
incompressible unsteady aerodynamics in indicial (lag-state) form.

Conventions (documented, used consistently everywhere):
- h positive DOWNWARD (m), theta positive nose-up (rad).
- Aerodynamic lift L per unit span is positive UPWARD (conventional
  lift); the plunge equation is m_s*h_ddot + k_h*h = -L because an
  upward force accelerates the section in the negative h direction.
- Elastic axis at fraction e of the chord measured from the leading
  edge. The lift acts at the aerodynamic center (quarter chord), so the
  nose-up moment about the elastic axis is
  M_ea = -L*(0.25 - e)*c. For e < 0.25 the aerodynamic center lies aft
  of the elastic axis and upward lift produces a nose-down restoring
  moment (statically stable section, no divergence).
- Reduced time s = 2*V*t/c with semi-chord b = c/2, so ds/dt = 2*V/c.
- Effective angle of attack at the three-quarter chord point, the
  quantity whose indicial response to a step is the Wagner function:
  alpha_m = theta + h_dot/V + (0.75 - e)*c*theta_dot/V.
  h positive down means a plunging section moving down sees an upwash
  (+h_dot/V increases incidence, giving the standard plunge damping);
  the pitch-rate term is the quasi-steady pitch damping at the
  three-quarter chord.
- Wagner lag (R.T. Jones two-term approximation) applies to the motion
  angle alpha_m; Kussner lag (classical two-term approximation) applies
  to the gust angle alpha_g = (w_g/V)*(1 - cos(2*pi*s/s_g))/2 during a
  one-minus-cosine gust of reduced-time gradient s_g = 2*H/c (H the
  gust gradient length in m). The Kussner channel models streamwise
  penetration; apparent-mass and full Theodorsen pitch-moment terms are
  neglected at this level (documented assumption).
- Lag-state (Duhamel) form: with filtered states
  x_i = low-pass of alpha at rate b_i*(2*V/c), the unsteady lift is
  L = 2*pi*rho*V^2*b*[(1-A1-A2)*alpha_m + A1*x1 + A2*x2
                      + (1-A1k-A2k)*alpha_g + A1k*xk1 + A2k*xk2].
  A step in alpha_m therefore starts at 1-A1-A2 = 0.5 of the
  quasi-steady lift (Wagner phi(0) = 0.5) and converges to the full
  value; a sharp-edge gust starts at zero (Kussner phi_k(0) = 0).
- Structure: m_s*h_ddot + k_h*h = -L and
  I_theta*theta_ddot + k_theta*theta = M_ea, undamped (documented
  assumption), integrated with RK4 in real time.
- Quasi-steady reference for the dynamic magnification factor:
  L_qs = 2*pi*rho*V*b*w_g, the rigid-section quasi-steady lift at the
  peak gust angle w_g/V.

ValueError guards: non-positive V, c, rho, m_s, I_theta, k_h, k_theta,
H, dt_real, t_max, s_g; negative w_g; elastic axis fraction outside
[0, 1]; any non-finite numeric input.
"""

import math

# Wagner function two-term exponential approximation (R.T. Jones).
WAGNER_A1 = 0.165
WAGNER_B1 = 0.0455
WAGNER_A2 = 0.335
WAGNER_B2 = 0.3

# Kussner function two-term exponential approximation (classical).
KUSSNER_A1 = 0.5
KUSSNER_B1 = 0.13
KUSSNER_A2 = 0.5
KUSSNER_B2 = 1.0


def _check_positive(name, value):
    """Raise ValueError unless value is finite and strictly positive."""
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))


def _check_non_negative(name, value):
    """Raise ValueError unless value is finite and non-negative."""
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (name, value))


def wagner_coefficients():
    """Return the R.T. Jones two-term Wagner coefficients as a dict.

    phi_w(s) = 1 - A1*exp(-b1*s) - A2*exp(-b2*s), with phi_w(0) = 0.5
    and phi_w(infinity) = 1.0.
    """
    return {
        "A1": WAGNER_A1, "b1": WAGNER_B1,
        "A2": WAGNER_A2, "b2": WAGNER_B2,
    }


def kussner_coefficients():
    """Return the classical two-term Kussner coefficients as a dict.

    phi_k(s) = 1 - A1k*exp(-b1k*s) - A2k*exp(-b2k*s), with
    phi_k(0) = 0.0 and phi_k(infinity) = 1.0.
    """
    return {
        "A1": KUSSNER_A1, "b1": KUSSNER_B1,
        "A2": KUSSNER_A2, "b2": KUSSNER_B2,
    }


def gust_angle_time(w_g, V, s_g, s):
    """Return the gust angle alpha_g (rad) at reduced time s.

    One-minus-cosine gust of peak velocity w_g (m/s, upward positive):
    alpha_g(s) = (w_g/V) * (1 - cos(2*pi*s/s_g)) / 2 for 0 <= s <= s_g
    and 0 beyond, with s_g the reduced-time gradient and s = 2*V*t/c.
    """
    _check_non_negative("w_g", w_g)
    _check_positive("V", V)
    _check_positive("s_g", s_g)
    _check_non_negative("s", s)
    if s > s_g:
        return 0.0
    return 0.5 * (w_g / V) * (1.0 - math.cos(2.0 * math.pi * s / s_g))


def quasi_steady_peak_lift(rho, V, c, w_g):
    """Return the rigid-section quasi-steady peak lift per unit span.

    L_qs = 2*pi*rho*V*b*w_g with b = c/2: the lift the peak gust angle
    w_g/V would produce if applied quasi-steadily to the rigid section.
    """
    _check_positive("rho", rho)
    _check_positive("V", V)
    _check_positive("c", c)
    _check_non_negative("w_g", w_g)
    return 2.0 * math.pi * rho * V * (c / 2.0) * w_g


def dynamic_magnification_factor(peak_lift, quasi_steady_peak):
    """Return DMF = peak dynamic lift over quasi-steady peak lift."""
    _check_non_negative("peak_lift", peak_lift)
    _check_positive("quasi_steady_peak", quasi_steady_peak)
    return peak_lift / quasi_steady_peak


def peak_load_verdict(peak, limit):
    """Return (verdict, margin) for peak load against a limit.

    Verdict is "PASS" when peak <= limit, else "FAIL"; margin is
    (limit/peak - 1), the fractional headroom (negative when the limit
    is exceeded).
    """
    _check_non_negative("peak", peak)
    _check_positive("limit", limit)
    margin = limit / peak - 1.0
    return ("PASS" if margin >= 0.0 else "FAIL", margin)


def lag_state_derivatives(alpha_motion, x_w1, x_w2, alpha_gust,
                          x_k1, x_k2, V, c):
    """Return the four lag-state time derivatives as a tuple.

    Filtered states follow x_dot = (2*V/c)*b_i*(alpha - x) per term;
    x_w1/x_w2 use the Wagner coefficients and follow alpha_motion,
    x_k1/x_k2 use the Kussner coefficients and follow alpha_gust.
    """
    _check_positive("V", V)
    _check_positive("c", c)
    rate_w1 = (2.0 * V / c) * WAGNER_B1
    rate_w2 = (2.0 * V / c) * WAGNER_B2
    rate_k1 = (2.0 * V / c) * KUSSNER_B1
    rate_k2 = (2.0 * V / c) * KUSSNER_B2
    return (rate_w1 * (alpha_motion - x_w1),
            rate_w2 * (alpha_motion - x_w2),
            rate_k1 * (alpha_gust - x_k1),
            rate_k2 * (alpha_gust - x_k2))


def lift_from_lag_states(alpha_motion, x_w1, x_w2, alpha_gust,
                         x_k1, x_k2, rho, V, c):
    """Return the unsteady circulatory lift per unit span (positive up).

    Duhamel superposition in lag-state form: the motion angle alpha_m
    enters through the Wagner-lagged states and the gust angle through
    the Kussner-lagged states. A step in alpha_m starts at half the
    quasi-steady value (phi_w(0) = 0.5); a sharp-edge gust starts at
    zero (phi_k(0) = 0).
    """
    _check_positive("rho", rho)
    _check_positive("V", V)
    _check_positive("c", c)
    b = c / 2.0
    w0 = 1.0 - WAGNER_A1 - WAGNER_A2
    k0 = 1.0 - KUSSNER_A1 - KUSSNER_A2
    return (2.0 * math.pi * rho * V * V * b) * (
        w0 * alpha_motion + WAGNER_A1 * x_w1 + WAGNER_A2 * x_w2
        + k0 * alpha_gust + KUSSNER_A1 * x_k1 + KUSSNER_A2 * x_k2)


def _state_derivatives(t, y, p):
    """Full 8-state right hand side: [h, hd, th, thd, x1, x2, xk1, xk2]."""
    V, c, rho, m_s, I_th, k_h, k_th, e = (p["V"], p["c"], p["rho"],
                                          p["m_s"], p["I_theta"],
                                          p["k_h"], p["k_theta"], p["e"])
    w_g, H = p["w_g"], p["H"]
    h, hd, th, thd = y[0], y[1], y[2], y[3]
    x1, x2, xk1, xk2 = y[4], y[5], y[6], y[7]
    s_g = 2.0 * H / c
    s = 2.0 * V * t / c
    alpha_g = gust_angle_time(w_g, V, s_g, s)
    alpha_m = th + hd / V + (0.75 - e) * c * thd / V
    lift = lift_from_lag_states(alpha_m, x1, x2, alpha_g, xk1, xk2,
                                rho, V, c)
    hdd = (-k_h * h - lift) / m_s
    m_ea = -lift * (0.25 - e) * c
    thdd = (-k_th * th + m_ea) / I_th
    dx1, dx2, dxk1, dxk2 = lag_state_derivatives(
        alpha_m, x1, x2, alpha_g, xk1, xk2, V, c)
    return (hd, hdd, thd, thdd, dx1, dx2, dxk1, dxk2)


def _validate_params(params):
    """Validate the section parameter dict, returning it with w_g, H set."""
    if not isinstance(params, dict):
        raise ValueError("params must be a dict of section parameters")
    p = dict(params)
    required = ("V", "c", "rho", "m_s", "I_theta", "k_h", "k_theta", "e")
    missing = [k for k in required if k not in p]
    if missing:
        raise ValueError("params missing required keys: %s"
                         % ", ".join(missing))
    _check_positive("V", p["V"])
    _check_positive("c", p["c"])
    _check_positive("rho", p["rho"])
    _check_positive("m_s", p["m_s"])
    _check_positive("I_theta", p["I_theta"])
    _check_positive("k_h", p["k_h"])
    _check_positive("k_theta", p["k_theta"])
    if not math.isfinite(p["e"]) or not (0.0 <= p["e"] <= 1.0):
        raise ValueError("elastic axis fraction e must be in [0, 1], "
                         "got %r" % (p["e"],))
    for key in ("h0", "h_dot0", "theta0", "theta_dot0"):
        if key not in p:
            p[key] = 0.0
        elif not math.isfinite(p[key]):
            raise ValueError("%s must be finite, got %r" % (key, p[key]))
    return p


def gust_response_history(params, w_g, H, dt_real, t_max):
    """Integrate the 2-DOF typical-section gust response with RK4.

    Params dict keys: V, c, rho, m_s, I_theta, k_h, k_theta, e (elastic
    axis fraction from the leading edge) plus optional initial
    conditions h0, h_dot0, theta0, theta_dot0. The one-minus-cosine
    gust of velocity w_g (m/s, upward positive) and gradient length H
    (m) starts at t = 0. Returns a dict with the t, s, h, h_dot, theta,
    theta_dot, lift (positive up, per unit span), alpha_gust and
    alpha_motion histories plus the peak absolute lift and its time.
    """
    p = _validate_params(params)
    _check_non_negative("w_g", w_g)
    _check_positive("H", H)
    _check_positive("dt_real", dt_real)
    _check_positive("t_max", t_max)
    p["w_g"] = w_g
    p["H"] = H

    y = [p["h0"], p["h_dot0"], p["theta0"], p["theta_dot0"],
         0.0, 0.0, 0.0, 0.0]
    n_steps = int(math.floor(t_max / dt_real))
    t = [0.0]
    h_hist = [y[0]]
    hd_hist = [y[1]]
    th_hist = [y[2]]
    thd_hist = [y[3]]
    lift_hist = []
    alpha_g_hist = []
    alpha_m_hist = []
    s_hist = []
    peak_abs_lift = 0.0
    peak_time = 0.0

    def lift_now(tt, yy):
        s_g = 2.0 * p["H"] / p["c"]
        s_now = 2.0 * p["V"] * tt / p["c"]
        alpha_g_now = gust_angle_time(p["w_g"], p["V"], s_g, s_now)
        alpha_m_now = (yy[2] + yy[1] / p["V"]
                       + (0.75 - p["e"]) * p["c"] * yy[3] / p["V"])
        return lift_from_lag_states(alpha_m_now, yy[4], yy[5],
                                    alpha_g_now, yy[6], yy[7],
                                    p["rho"], p["V"], p["c"])

    for i in range(n_steps):
        tt = i * dt_real
        k1 = _state_derivatives(tt, y, p)
        k2 = _state_derivatives(tt + 0.5 * dt_real,
                                [y[j] + 0.5 * dt_real * k1[j]
                                 for j in range(8)], p)
        k3 = _state_derivatives(tt + 0.5 * dt_real,
                                [y[j] + 0.5 * dt_real * k2[j]
                                 for j in range(8)], p)
        k4 = _state_derivatives(tt + dt_real,
                                [y[j] + dt_real * k3[j]
                                 for j in range(8)], p)
        y = [y[j] + (dt_real / 6.0) * (k1[j] + 2.0 * k2[j]
                                        + 2.0 * k3[j] + k4[j])
             for j in range(8)]
        t_next = (i + 1) * dt_real
        t.append(t_next)
        h_hist.append(y[0])
        hd_hist.append(y[1])
        th_hist.append(y[2])
        thd_hist.append(y[3])
        s_hist.append(2.0 * p["V"] * t_next / p["c"])
        lift_next = lift_now(t_next, y)
        lift_hist.append(lift_next)
        s_g = 2.0 * p["H"] / p["c"]
        alpha_g_hist.append(gust_angle_time(p["w_g"], p["V"], s_g,
                                            s_hist[-1]))
        alpha_m_hist.append(y[2] + y[1] / p["V"]
                            + (0.75 - p["e"]) * p["c"] * y[3] / p["V"])
        if abs(lift_next) > peak_abs_lift:
            peak_abs_lift = abs(lift_next)
            peak_time = t_next

    return {
        "t": t, "s": s_hist, "h": h_hist, "h_dot": hd_hist,
        "theta": th_hist, "theta_dot": thd_hist, "lift": lift_hist,
        "alpha_gust": alpha_g_hist, "alpha_motion": alpha_m_hist,
        "peak_lift": peak_abs_lift, "peak_time": peak_time,
        "n_steps": n_steps,
    }

