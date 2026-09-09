#!/usr/bin/env python3
"""Wave-49 prep anchor: continuous-turbulence gust loads (structures/loads).

Deterministic closed-form implementation of the continuous-turbulence PSD
gust-load chain for a rigid aircraft: von Karman and Dryden vertical-gust
power spectral densities (spatial frequency), the rigid-aircraft vertical
(heave) gust-response transfer function with quasi-steady aerodynamics,
the response power spectral density |H|^2 * Phi, the rms-response ratio A
(root-mean-square incremental load factor per root-mean-square gust
velocity), the design-limit incremental load factor per the linear-model
design rule of the continuous-turbulence design condition (limit
incremental load = limit turbulence intensity U_sigma times A), and the
equivalent discrete-gust velocity handed to the discrete-gust envelope
method.

Pure stdlib (math only), deterministic, no RNG, no tables, no imports
beyond math. SI units throughout: rho kg/m^3, V m/s, W N, S m^2, cbar m,
a_lift 1/rad, L m, Omega rad/m, sigma_w m/s, U_sigma m/s (TAS).

Published anchor: the continuous-turbulence chapters of Hoblit, Gust
Loads on Aircraft (von Karman and Dryden spectral forms with the
published scale constant 1.339 and scale of turbulence 2500 ft = 762 m,
the gust-response transfer function, response PSD, rms response and the
design-intensity criterion); the linear-model design rule (limit load
equals steady load plus the limit turbulence intensity times the
rms-response ratio A, with A the square root of the integral of the
response transfer magnitude squared times the normalized turbulence
spectrum) is the continuous-turbulence design condition of the FAR/CS
transport gust-load rules, referenced by name only, never reproduced.

Worked-example parameters mirror the discrete-gust sibling's VB-class
case so the design band is directly comparable: sea level (rho = 1.225,
TAS = EAS), V = 154.33 m/s (300 KEAS class), W/S = 4800 Pa on
S = 120 m^2, cbar = 3.81 m, a_lift = 5.7/rad, turbulence scale
L = 762 m, limit turbulence intensity U_sigma = 27.432 m/s TAS
(90 ft/s, the sea-level reference intensity of the continuous-turbulence
condition taken with the flight-profile alleviation factor at 1.0, the
conservative no-alleviation convention).
"""

import math

# Module constants (published values only).
VK_A = 1.339          # von Karman spectrum constant (published, rounded)
G_MS2 = 9.80665       # standard gravity, m/s^2
RHO0 = 1.225          # standard sea-level density, kg/m^3
L_SCALE_DEFAULT = 762.0  # 2500 ft scale of turbulence in m (input default)


def _beta(p, q):
    """Beta function B(p, q) from math.lgamma (deterministic, stdlib)."""
    return math.exp(math.lgamma(p) + math.lgamma(q) - math.lgamma(p + q))


def _von_karman_exact_constant():
    """The spectrum constant that makes the von Karman Parseval closure
    exact: a_exact = J / pi with J the closed-form integral of the von
    Karman shape (1 + (8/3) x^2) / (1 + x^2)^(11/6) over x in [0, inf)
    evaluated by Beta functions:
    J = (1/2) B(1/2, 4/3) + (4/3) B(3/2, 1/3)."""
    j = 0.5 * _beta(0.5, 4.0 / 3.0) + (4.0 / 3.0) * _beta(1.5, 1.0 / 3.0)
    return j / math.pi


VK_A_EXACT = _von_karman_exact_constant()


def _check_positive(name, value):
    """ValueError unless value is a positive real number (not bool)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a positive number, got %r" % (name, value))
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("%s must be a positive number, got %s" % (name, value))


def _check_omega(name, value):
    """ValueError unless value is a finite non-negative real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a non-negative number, got %r" % (name, value))
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("%s must be a non-negative number, got %s" % (name, value))


def _check_spectrum(spectrum):
    """ValueError unless spectrum is 'von-karman' or 'dryden'."""
    if spectrum not in ("von-karman", "dryden"):
        raise ValueError(
            "spectrum must be 'von-karman' or 'dryden', got %r" % (spectrum,))


def _von_karman_shape(y):
    """Dimensionless von Karman shape G(y) with y = Omega * L:
    (1 + (8/3) (1.339 y)^2) / (1 + (1.339 y)^2)^(11/6)."""
    a2y2 = (VK_A * y) ** 2
    return (1.0 + (8.0 / 3.0) * a2y2) / (1.0 + a2y2) ** (11.0 / 6.0)


def _dryden_shape(y):
    """Dimensionless Dryden shape G(y) with y = Omega * L:
    (1 + 3 y^2) / (1 + y^2)^2."""
    y2 = y * y
    return (1.0 + 3.0 * y2) / (1.0 + y2) ** 2


def von_karman_psd(omega, sigma_w, l):
    """One-sided von Karman vertical-gust velocity PSD in spatial
    frequency, per (m/s)^2 per (rad/m):

    Phi(Omega) = sigma_w^2 (L/pi) (1 + (8/3)(1.339 L Omega)^2)
                 / (1 + (1.339 L Omega)^2)^(11/6)

    with Omega in rad/m, L in m, sigma_w in m/s.
    ValueErrors: sigma_w or l not a positive number; omega negative.
    """
    _check_positive("sigma_w", sigma_w)
    _check_positive("L", l)
    _check_omega("Omega", omega)
    return sigma_w * sigma_w * (l / math.pi) * _von_karman_shape(l * omega)


def dryden_psd(omega, sigma_w, l):
    """One-sided Dryden vertical-gust velocity PSD in spatial frequency,
    per (m/s)^2 per (rad/m):

    Phi(Omega) = sigma_w^2 (L/pi) (1 + 3 (L Omega)^2)
                 / (1 + (L Omega)^2)^2

    Same inputs and ValueErrors as von_karman_psd.
    """
    _check_positive("sigma_w", sigma_w)
    _check_positive("L", l)
    _check_omega("Omega", omega)
    return sigma_w * sigma_w * (l / math.pi) * _dryden_shape(l * omega)


def rigid_aircraft_response_params(rho, v, w, s, a_lift, g=G_MS2):
    """Rigid-aircraft vertical (heave) gust-response parameters.

    Heave equation with quasi-steady aerodynamics: the incremental lift
    is q S a_lift (w_g - z_dot)/V, giving the first-order response
    z_ddot/w_g = h_inf * s / (s + K) in the Laplace domain with

        K     = rho V S a_lift / (2 m)          [1/s]
        h_inf = K / g = rho V S a_lift / (2 W)  [1/(m/s)]

    h_inf is the frozen-gust incremental load factor per unit gust
    velocity (the limit reached when the encounter frequency is far
    above K, so the aircraft cannot follow the gust).

    Returns dict with keys "h_inf", "k_rate" and "mass_kg".
    ValueErrors: any of rho, v, w, s, a_lift, g not a positive number.
    """
    for name, value in (("rho", rho), ("V", v), ("W", w), ("S", s),
                        ("a_lift", a_lift), ("g", g)):
        _check_positive(name, value)
    m = w / g
    k_rate = rho * v * s * a_lift / (2.0 * m)
    h_inf = rho * v * s * a_lift / (2.0 * w)
    return {"h_inf": h_inf, "k_rate": k_rate, "mass_kg": m}


def gust_response_transfer_squared(omega, rho, v, w, s, a_lift, g=G_MS2):
    """Squared magnitude of the rigid-aircraft vertical-gust response
    transfer, |H(omega)|^2 = h_inf^2 omega^2 / (omega^2 + K^2), mapping
    gust velocity (m/s) to incremental load factor. omega in rad/s.
    ValueErrors as above plus omega negative.
    """
    _check_omega("omega", omega)
    p = rigid_aircraft_response_params(rho, v, w, s, a_lift, g)
    h_inf = p["h_inf"]
    k_rate = p["k_rate"]
    return h_inf * h_inf * omega * omega / (omega * omega + k_rate * k_rate)


def _filter_factor(y, y_c):
    """Heave filter in reduced frequency: y^2 / (y^2 + y_c^2) with the
    reduced-frequency corner y_c = K L / V; the y_c = 0 case is the
    frozen-gust limit (factor identically 1)."""
    if y_c == 0.0:
        return 1.0
    return y * y / (y * y + y_c * y_c)


def _integral_tail(spectrum, y_max, y_c):
    """Analytic tail of the y-space integrand beyond y_max.

    Von Karman shape decays as c_v y^(-5/3) with c_v = (8/3) 1.339^(-5/3)
    and Dryden as 3 y^(-2); the filter factor is 1 - y_c^2/y^2 to
    leading order. Returns the exact tail integral of the leading and
    first correction terms.
    """
    if spectrum == "von-karman":
        c_v = (8.0 / 3.0) * VK_A ** (-5.0 / 3.0)
        t = c_v * (1.5 * y_max ** (-2.0 / 3.0)
                   - y_c * y_c * (3.0 / 8.0) * y_max ** (-8.0 / 3.0))
    else:
        t = 3.0 * (1.0 / y_max - y_c * y_c / (3.0 * y_max ** 3.0))
    return t


def _integrate_y(spectrum, y_c, n=16384, y_lo=1.0e-4, y_hi=1.0e10):
    """Integral over y in (0, inf) of the filter factor y^2/(y^2 + y_c^2)
    (identically 1 for y_c = 0) times the spectrum shape G(y), by
    Simpson's rule on a uniform grid in t = ln(y) with an exact cap over
    (0, y_lo] and the analytic tail beyond y_hi. Deterministic.
    """
    shape = _von_karman_shape if spectrum == "von-karman" else _dryden_shape
    # Cap over (0, y_lo]: f(0) = G(0) = 1 when y_c == 0 else 0.
    f0 = 1.0 if y_c == 0.0 else 0.0
    t_lo = math.log(y_lo)
    t_hi = math.log(y_hi)
    total = 0.5 * y_lo * (f0 + _filter_factor(y_lo, y_c) * shape(y_lo))
    h = (t_hi - t_lo) / n
    if n % 2 != 0:
        raise ValueError("n must be even")
    # Simpson: sum over pairs of sub-intervals.
    acc = _filter_factor(y_lo, y_c) * shape(y_lo) * y_lo
    for k in range(1, n + 1):
        t = t_lo + k * h
        y = math.exp(t)
        f = _filter_factor(y, y_c) * shape(y) * y
        if k == n:
            acc += f
        elif k % 2 == 1:
            acc += 4.0 * f
        else:
            acc += 2.0 * f
    total += (h / 3.0) * acc
    total += _integral_tail(spectrum, y_hi, y_c)
    return total


def rms_response_ratio(spectrum, rho, v, w, s, a_lift, l, g=G_MS2):
    """The rms-response ratio A (per m/s of gust velocity): A^2 is the
    integral over spatial frequency of the squared response transfer
    magnitude times the normalized turbulence spectrum,

        A^2 = integral_0^inf |H(V Omega)|^2 Phi_hat(Omega) dOmega

    with Phi_hat the sigma_w = 1 m/s spectrum (the normalized power
    spectral density). A has units 1/(m/s) (dimensionless incremental
    load factor per (m/s) of rms gust velocity) and is independent of
    the turbulence intensity.

    ValueErrors: spectrum not 'von-karman' or 'dryden'; any positive
    input invalid; l not positive.
    """
    _check_spectrum(spectrum)
    _check_positive("L", l)
    p = rigid_aircraft_response_params(rho, v, w, s, a_lift, g)
    h_inf = p["h_inf"]
    k_rate = p["k_rate"]
    y_c = k_rate * l / v
    integral = _integrate_y(spectrum, y_c)
    return h_inf * math.sqrt(integral / math.pi)


def _dryden_response_closed_form(h_inf, y_c):
    """Exact closed form of the Dryden A^2 integral:

        A^2 = h_inf^2 B(y_c),
        B(c) = (3 c + 2) / (2 (1 + c)^2),

    derived from the partial-fraction decomposition
    (1 + 3 y^2)/(1 + y^2)^2 = 3/(1 + y^2) - 2/(1 + y^2)^2 with the
    standard integrals I_A = integral y^2/((y^2+c^2)(1+y^2)) dy
    = (pi/2)/(1 + c) and I_2 = integral y^2/((y^2+c^2)(1+y^2)^2) dy
    = pi/4 - pi c (c + 2)/(4 (1 + c)^2). Used only as the identity
    cross-check for the numerical quadrature. B(c) = (3c + 2)/(2(1+c)^2)
    -> 1 as c -> 0+ (frozen-gust limit) and -> 0 as c -> inf (the
    aircraft follows every gust).
    """
    c = y_c
    b = (3.0 * c + 2.0) / (2.0 * (1.0 + c) ** 2)
    return h_inf * h_inf * b


def rms_load_factor_response(sigma_w, a_ratio):
    """Root-mean-square incremental load factor response to a turbulence
    field of rms gust velocity sigma_w (m/s): sigma_delta_n = sigma_w A.
    Linear in sigma_w (Gaussian linear model). ValueErrors: sigma_w not
    positive, a_ratio not non-negative.
    """
    _check_positive("sigma_w", sigma_w)
    if isinstance(a_ratio, bool) or not isinstance(a_ratio, (int, float)) \
            or not math.isfinite(a_ratio) or a_ratio < 0.0:
        raise ValueError(
            "A must be a non-negative number, got %s" % (a_ratio,))
    return sigma_w * a_ratio


def design_incremental_load_factor(a_ratio, u_sigma):
    """Limit incremental load factor of the continuous-turbulence design
    condition (linear model): delta_n_limit = U_sigma A, with U_sigma the
    limit turbulence intensity in true airspeed (m/s) at the condition.
    Both positive and negative gusts apply (+/-). ValueErrors: u_sigma
    not positive; a_ratio invalid as above.
    """
    _check_positive("U_sigma", u_sigma)
    if isinstance(a_ratio, bool) or not isinstance(a_ratio, (int, float)) \
            or not math.isfinite(a_ratio) or a_ratio < 0.0:
        raise ValueError(
            "A must be a non-negative number, got %s" % (a_ratio,))
    return u_sigma * a_ratio


def gust_alleviation_factor(ws, cbar, a_lift, rho, g=G_MS2):
    """Discrete-gust alleviation factor K_g = 0.88 mu_g/(5.3 + mu_g) with
    mu_g = 2 (W/S)/(rho cbar a_lift g), the closed form of the discrete
    icosine gust method, evaluated here only to express this leaf's
    continuous-turbulence limit increment as the equivalent discrete-gust
    velocity of the sibling envelope method (algebraic inversion, not a
    claimed product of this leaf). ValueErrors as for positive inputs.
    """
    for name, value in (("W/S", ws), ("cbar", cbar), ("a_lift", a_lift),
                        ("rho", rho), ("g", g)):
        _check_positive(name, value)
    mu = 2.0 * ws / (rho * cbar * a_lift * g)
    return 0.88 * mu / (5.3 + mu)


def equivalent_discrete_gust_velocity(delta_n, ws, v_eas, a_lift, cbar,
                                      rho, g=G_MS2):
    """Equivalent discrete-gust velocity U_de_eq (m/s EAS) that the
    discrete-gust load-factor method would need to reproduce the given
    incremental load factor delta_n at the flight condition:

        U_de = 2 (W/S) delta_n / (rho V_e a_lift K_g)

    the algebraic inversion of the discrete 1-cosine load-factor formula
    (sea-level condition, where EAS equals TAS and rho = rho0). This is
    the hand-off value reported to the discrete-gust envelope method.
    ValueErrors: delta_n not positive, ws/v_eas/a_lift/cbar/rho/g not
    positive.
    """
    _check_positive("delta_n", delta_n)
    for name, value in (("W/S", ws), ("V_e", v_eas), ("a_lift", a_lift),
                        ("cbar", cbar), ("rho", rho), ("g", g)):
        _check_positive(name, value)
    k_g = gust_alleviation_factor(ws, cbar, a_lift, rho, g)
    return 2.0 * ws * delta_n / (rho * v_eas * a_lift * k_g)


def spectrum_psd_ordinates(spectrum, omega_grid, sigma_w, l):
    """Turbulence PSD ordinates Phi(Omega) at the given Omega grid
    (rad/m), list of (omega, phi) pairs. ValueErrors as von_karman_psd
    plus a non-positive or empty grid.
    """
    _check_spectrum(spectrum)
    _check_positive("sigma_w", sigma_w)
    _check_positive("L", l)
    if not omega_grid:
        raise ValueError("omega grid must not be empty")
    fn = von_karman_psd if spectrum == "von-karman" else dryden_psd
    return [(omega, fn(omega, sigma_w, l)) for omega in omega_grid]


def response_psd_ordinates(spectrum, omega_grid, rho, v, w, s, a_lift, l,
                           g=G_MS2):
    """Response PSD ordinates |H(Omega V)|^2 Phi_hat(Omega) at the given
    Omega grid (rad/m), the integrand of the A-squared integral, per
    1/(m/s)^2 per (rad/m). ValueErrors as rms_response_ratio plus an
    empty grid.
    """
    _check_spectrum(spectrum)
    _check_positive("L", l)
    if not omega_grid:
        raise ValueError("omega grid must not be empty")
    p = rigid_aircraft_response_params(rho, v, w, s, a_lift, g)
    h_inf = p["h_inf"]
    k_rate = p["k_rate"]
    out = []
    for omega in omega_grid:
        _check_omega("Omega", omega)
        w_time = v * omega
        h2 = h_inf * h_inf * w_time * w_time / (w_time * w_time + k_rate ** 2)
        phi_hat = (l / math.pi) * (
            _von_karman_shape(l * omega)
            if spectrum == "von-karman" else _dryden_shape(l * omega))
        out.append((omega, h2 * phi_hat))
    return out


def continuous_turbulence_report(spectrum, rho, v, w, s, a_lift, l,
                                 u_sigma, cbar, g=G_MS2,
                                 omega_grid=None):
    """One-shot report dict for the continuous-turbulence gust-load
    condition. Keys: "spectrum", "h_inf" (1/(m/s)), "k_rate" (1/s),
    "y_c" (dimensionless reduced-frequency filter corner),
    "a_ratio" (1/(m/s)), "response_factor" (A/h_inf, dimensionless),
    "rms_delta_n_at_1mps" (dimensionless, sigma_w = 1 m/s),
    "delta_n_limit" (dimensionless), "n_limit" (dimensionless),
    "u_de_eq_mps_eas" (m/s), "mu_g", "k_g", "mass_kg",
    "turbulence_psd_ordinates" and "response_psd_ordinates" at the
    default Omega grid 2 pi / [1000, 500, 200, 100, 50, 25] m.
    ValueErrors as the component functions.
    """
    _check_spectrum(spectrum)
    for name, value in (("rho", rho), ("V", v), ("W", w), ("S", s),
                        ("a_lift", a_lift), ("L", l), ("U_sigma", u_sigma),
                        ("cbar", cbar), ("g", g)):
        _check_positive(name, value)
    if omega_grid is None:
        omega_grid = [2.0 * math.pi / lam for lam in (1000.0, 500.0,
                                                      200.0, 100.0,
                                                      50.0, 25.0)]
    p = rigid_aircraft_response_params(rho, v, w, s, a_lift, g)
    a_ratio = rms_response_ratio(spectrum, rho, v, w, s, a_lift, l, g)
    delta_n = design_incremental_load_factor(a_ratio, u_sigma)
    k_g = gust_alleviation_factor(w / s, cbar, a_lift, rho, g)
    mu_g = 2.0 * (w / s) / (rho * cbar * a_lift * g)
    u_de = equivalent_discrete_gust_velocity(
        delta_n, w / s, v, a_lift, cbar, rho, g)
    return {
        "spectrum": spectrum,
        "h_inf": p["h_inf"],
        "k_rate": p["k_rate"],
        "y_c": p["k_rate"] * l / v,
        "a_ratio": a_ratio,
        "response_factor": a_ratio / p["h_inf"],
        "rms_delta_n_at_1mps": rms_load_factor_response(1.0, a_ratio),
        "delta_n_limit": delta_n,
        "n_limit": 1.0 + delta_n,
        "u_de_eq_mps_eas": u_de,
        "mu_g": mu_g,
        "k_g": k_g,
        "mass_kg": p["mass_kg"],
        "turbulence_psd_ordinates": spectrum_psd_ordinates(
            spectrum, omega_grid, 1.0, l),
        "response_psd_ordinates": response_psd_ordinates(
            spectrum, omega_grid, rho, v, w, s, a_lift, l, g),
    }


def _fmt(x):
    """Repr-like formatting at full float precision."""
    return repr(x)


def main():
    # ------------------------------------------------------------------
    # Worked example: typical transport, VB-class sea-level condition
    # ------------------------------------------------------------------
    rho = 1.225          # kg/m^3, sea level (TAS = EAS)
    v = 154.33           # m/s, 300 KEAS class
    ws = 4800.0          # Pa (100 psf class)
    s = 120.0            # m^2
    w = ws * s           # N
    cbar = 3.81          # m
    a_lift = 5.7         # 1/rad
    l = 762.0            # m, 2500 ft scale of turbulence
    u_sigma = 27.432     # m/s TAS, 90 ft/s sea-level reference intensity

    print("wave-49 continuous-turbulence gust loads anchor")
    print("worked example: rho=%s V=%s W/S=%s S=%s cbar=%s a=%s L=%s U_sigma=%s"
          % (rho, v, ws, s, cbar, a_lift, l, u_sigma))

    # --- von Karman report -------------------------------------------
    r_vk = continuous_turbulence_report(
        "von-karman", rho, v, w, s, a_lift, l, u_sigma, cbar)
    print("von karman: h_inf=%s k_rate=%s y_c=%s" % (
        _fmt(r_vk["h_inf"]), _fmt(r_vk["k_rate"]), _fmt(r_vk["y_c"])))
    print("von karman: a_ratio=%s response_factor=%s" % (
        _fmt(r_vk["a_ratio"]), _fmt(r_vk["response_factor"])))
    print("von karman: rms_delta_n_at_1mps=%s" %
          _fmt(r_vk["rms_delta_n_at_1mps"]))
    print("von karman: rms_delta_n_at_0.4_u_sigma_field=%s" % _fmt(
        rms_load_factor_response(0.4 * u_sigma, r_vk["a_ratio"])))
    print("von karman: delta_n_limit=%s n_limit=%s" % (
        _fmt(r_vk["delta_n_limit"]), _fmt(r_vk["n_limit"])))
    print("von karman: u_de_eq_mps_eas=%s mu_g=%s k_g=%s" % (
        _fmt(r_vk["u_de_eq_mps_eas"]), _fmt(r_vk["mu_g"]), _fmt(r_vk["k_g"])))
    print("von karman: turbulence psd ordinates (sigma_w = 1 m/s):")
    for omega, phi in r_vk["turbulence_psd_ordinates"]:
        print("  Omega=%s Phi=%s" % (_fmt(omega), _fmt(phi)))
    print("von karman: response psd ordinates (|H|^2 Phi_hat):")
    for omega, rpsd in r_vk["response_psd_ordinates"]:
        print("  Omega=%s R=%s" % (_fmt(omega), _fmt(rpsd)))

    # --- Dryden report ------------------------------------------------
    r_d = continuous_turbulence_report(
        "dryden", rho, v, w, s, a_lift, l, u_sigma, cbar)
    print("dryden: a_ratio=%s response_factor=%s" % (
        _fmt(r_d["a_ratio"]), _fmt(r_d["response_factor"])))
    print("dryden: delta_n_limit=%s n_limit=%s" % (
        _fmt(r_d["delta_n_limit"]), _fmt(r_d["n_limit"])))
    print("dryden: u_de_eq_mps_eas=%s" % _fmt(r_d["u_de_eq_mps_eas"]))

    # --- Parseval / identity checks -----------------------------------
    print("identity: von karman exact constant a_exact=%s" %
          _fmt(VK_A_EXACT))
    # DC level: both one-sided spectra equal sigma_w^2 L/pi at Omega = 0.
    phi_dc_vk = von_karman_psd(0.0, 1.0, l)
    phi_dc_d = dryden_psd(0.0, 1.0, l)
    print("identity: spectrum DC ordinate Phi(0) = sigma^2 L/pi: vk=%s "
          "dryden=%s" % (_fmt(phi_dc_vk), _fmt(phi_dc_d)))
    assert phi_dc_vk == phi_dc_d, "spectrum DC ordinates agree"
    assert abs(phi_dc_vk - l / math.pi) < 1.0e-12 * (l / math.pi), \
        "DC ordinate closed form"
    # Closure of the normalized von Karman spectrum with the published
    # rounded constant: integral Phi_hat dOmega = a_exact/1.339.
    closure_vk = VK_A_EXACT / VK_A
    print("identity: von karman closure ratio vs 1.0 = %s" %
          _fmt(closure_vk))
    assert abs(closure_vk - 1.0) < 1.0e-3, "von karman closure ratio"
    assert abs(VK_A_EXACT - VK_A) < 1.5e-4, "von karman constant"
    # Dryden closure exact: integral (1+3y^2)/(1+y^2)^2 dy = pi.
    closure_d_numeric = _integrate_y("dryden", 0.0) / math.pi
    print("identity: dryden closure ratio vs 1.0 (numeric) = %s" %
          _fmt(closure_d_numeric))
    assert abs(closure_d_numeric - 1.0) < 1.0e-6, "dryden closure numeric"
    closure_vk_numeric = _integrate_y("von-karman", 0.0) / math.pi
    print("identity: von karman closure ratio (numeric) = %s" %
          _fmt(closure_vk_numeric))
    assert abs(closure_vk_numeric - closure_vk) < 1.0e-6, \
        "von karman closure numeric vs analytic"

    # Dryden quadrature vs closed form for the worked A integral.
    p = rigid_aircraft_response_params(rho, v, w, s, a_lift)
    y_c = p["k_rate"] * l / v
    a_d_closed = math.sqrt(_dryden_response_closed_form(p["h_inf"], y_c))
    print("identity: dryden A closed form=%s numeric=%s" % (
        _fmt(a_d_closed), _fmt(r_d["a_ratio"])))
    assert abs(a_d_closed - r_d["a_ratio"]) < 1.0e-9 * a_d_closed, \
        "dryden closed form vs quadrature"

    # Grid convergence: doubling the Simpson panel count changes every
    # integral by less than 1e-9 relative.
    for spectrum in ("von-karman", "dryden"):
        i1 = _integrate_y(spectrum, y_c)
        i2 = _integrate_y(spectrum, y_c, n=32768)
        rel = abs(i2 - i1) / i2
        print("identity: %s grid convergence rel diff (N vs 2N) = %s"
              % (spectrum, _fmt(rel)))
        assert rel < 1.0e-9, "grid convergence %s" % spectrum

    # Ordering: von Karman carries more high-frequency energy than
    # Dryden (slower high-frequency decay), so A_vK > A_Dryden; both sit
    # below the frozen-gust bound h_inf.
    print("identity: A_vK=%s A_D=%s h_inf=%s" % (
        _fmt(r_vk["a_ratio"]), _fmt(r_d["a_ratio"]), _fmt(r_vk["h_inf"])))
    ratio_ad = r_vk["a_ratio"] / r_d["a_ratio"]
    print("identity: A_vK / A_D = %s (von karman %s percent above "
          "dryden)" % (_fmt(ratio_ad), _fmt(100.0 * (ratio_ad - 1.0))))
    print("identity: A_vK^2=%s A_D^2=%s" % (
        _fmt(r_vk["a_ratio"] ** 2), _fmt(r_d["a_ratio"] ** 2)))
    print("identity: limit / rms_at_0.4u_sigma quotient = %s" % _fmt(
        r_vk["delta_n_limit"] / rms_load_factor_response(
            0.4 * u_sigma, r_vk["a_ratio"])))
    assert r_vk["a_ratio"] > r_d["a_ratio"], "von karman above dryden"
    assert r_vk["a_ratio"] < r_vk["h_inf"], "rigid response bound"
    assert r_d["a_ratio"] < r_d["h_inf"], "rigid response bound dryden"
    # Closed-form response factor limits: B(c) -> 1 as c -> 0+ (frozen
    # gust, very heavy aircraft) and B(c) -> 0 as c -> inf (the aircraft
    # follows every gust).
    b_small = (3.0 * 1.0e-6 + 2.0) / (2.0 * (1.0 + 1.0e-6) ** 2)
    b_large = (3.0 * 1.0e12 + 2.0) / (2.0 * (1.0 + 1.0e12) ** 2)
    print("identity: B(c) limits c->0: %s, c->inf: %s" % (
        _fmt(b_small), _fmt(b_large)))
    assert abs(b_small - 1.0) < 1.0e-5, "dryden factor small-c limit"
    assert abs(b_large) < 1.0e-9, "dryden factor large-c limit"

    # Linearity in the turbulence intensity.
    n_2 = 1.0 + design_incremental_load_factor(r_vk["a_ratio"], 2.0 * u_sigma)
    print("identity: n_limit scales linearly with U_sigma (2x case): n=%s"
          % _fmt(n_2))
    assert abs(n_2 - (1.0 + 2.0 * r_vk["delta_n_limit"])) < 1.0e-12, \
        "linear scaling"

    # Determinism.
    r2 = continuous_turbulence_report(
        "von-karman", rho, v, w, s, a_lift, l, u_sigma, cbar)
    assert r2 == r_vk, "report determinism"

    # ValueErrors.
    cases = [
        ("spectrum", lambda: von_karman_psd(0.01, 1.0, -1.0)),
        ("dryden", lambda: dryden_psd(0.01, 0.0, 762.0)),
        ("omega", lambda: von_karman_psd(-0.1, 1.0, 762.0)),
        ("rho", lambda: rigid_aircraft_response_params(0.0, 154.33, w, s,
                                                       a_lift)),
        ("weight", lambda: rigid_aircraft_response_params(1.225, 154.33,
                                                          -w, s, a_lift)),
        ("bool", lambda: gust_response_transfer_squared(0.1, True, 154.33,
                                                        w, s, a_lift)),
        ("spectrum string", lambda: rms_response_ratio("kolmogorov", rho, v,
                                                       w, s, a_lift, l)),
        ("L", lambda: rms_response_ratio("dryden", rho, v, w, s, a_lift,
                                         0.0)),
        ("U_sigma", lambda: design_incremental_load_factor(
            r_vk["a_ratio"], -1.0)),
        ("A", lambda: design_incremental_load_factor(-0.5, u_sigma)),
        ("sigma_w", lambda: rms_load_factor_response(-1.0,
                                                     r_vk["a_ratio"])),
        ("cbar", lambda: gust_alleviation_factor(4800.0, -3.81, a_lift,
                                                 rho)),
        ("delta_n", lambda: equivalent_discrete_gust_velocity(
            0.0, ws, v, a_lift, cbar, rho)),
        ("empty grid", lambda: spectrum_psd_ordinates(
            "von-karman", [], 1.0, l)),
    ]
    for name, fn in cases:
        try:
            fn()
        except ValueError as exc:
            print("valueerror %s: %s" % (name, exc))
        else:
            raise AssertionError("missing ValueError for %s" % name)

    print("ALL ANCHOR ASSERTS PASS")


if __name__ == "__main__":
    main()
