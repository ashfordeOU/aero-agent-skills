#!/usr/bin/env python3
"""Continuous-turbulence PSD gust design loads (structures/loads).

Deterministic closed-form implementation of the continuous-turbulence
PSD gust-load chain for a rigid aircraft: von Karman and Dryden
vertical-gust power spectral densities (spatial frequency), the
rigid-aircraft vertical (heave) gust-response transfer function with
quasi-steady aerodynamics, the response power spectral density
|H|^2 * Phi, the rms-response ratio A (root-mean-square incremental
load factor per root-mean-square gust velocity), the design-limit
incremental load factor per the linear-model design rule of the
continuous-turbulence design condition (limit incremental load equals
the limit turbulence intensity U_sigma times A), and the equivalent
discrete-gust velocity handed to the discrete-gust envelope method.

Pure stdlib (math only), deterministic, no RNG, no tables, no imports
beyond math. SI units throughout: rho kg/m^3, V m/s, W N, S m^2, cbar
m, a_lift 1/rad, L m, Omega rad/m, sigma_w m/s, U_sigma m/s (TAS).

Published methodology: the continuous-turbulence chapters of Hoblit,
Gust Loads on Aircraft (von Karman and Dryden spectral forms with the
published scale constant 1.339 and scale of turbulence 2500 ft = 762
m, the gust-response transfer function, response PSD, rms response
and the design-intensity criterion). The linear-model design rule
(limit load equals steady load plus the limit turbulence intensity
times the rms-response ratio A) is the continuous-turbulence design
condition of the FAR/CS transport gust-load rules, referenced by name
only, never reproduced.
"""

import math

# Module constants (published values only; every other fixed number is
# an integration-grid parameter, see _integrate_y).
VK_A = 1.339             # von Karman spectrum constant (published, rounded)
G_MS2 = 9.80665           # standard gravity, m/s^2
RHO0 = 1.225               # standard sea-level density, kg/m^3
L_SCALE_DEFAULT = 762.0    # 2500 ft scale of turbulence in m (input default)


def _beta(p, q):
    """Beta function B(p, q) from math.lgamma (deterministic, stdlib)."""
    return math.exp(math.lgamma(p) + math.lgamma(q) - math.lgamma(p + q))


def _von_karman_exact_constant():
    """The spectrum constant making the von Karman Parseval closure
    exact: a_exact = J / pi with J the closed-form integral of the von
    Karman shape (1 + (8/3) x^2) / (1 + x^2)^(11/6) over x in [0, inf),
    evaluated by Beta functions: J = (1/2)B(1/2,4/3) + (4/3)B(3/2,1/3).
    """
    j = 0.5 * _beta(0.5, 4.0 / 3.0) + (4.0 / 3.0) * _beta(1.5, 1.0 / 3.0)
    return j / math.pi


VK_A_EXACT = _von_karman_exact_constant()


def _check_positive(name, value):
    """ValueError unless value is a positive, finite, non-bool real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a positive number, got %r" % (name, value))
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("%s must be a positive number, got %s" % (name, value))


def _check_omega(name, value):
    """ValueError unless value is a finite non-negative, non-bool real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a non-negative number, got %r" % (name, value))
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("%s must be a non-negative number, got %s" % (name, value))


def _check_non_negative_a(value):
    """ValueError unless value is a finite non-negative, non-bool response ratio A."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value) or value < 0.0:
        raise ValueError("A must be a non-negative number, got %s" % (value,))


def _check_spectrum(spectrum):
    """ValueError unless spectrum is 'von-karman' or 'dryden'."""
    if spectrum not in ("von-karman", "dryden"):
        raise ValueError(
            "spectrum must be 'von-karman' or 'dryden', got %r" % (spectrum,))


def _von_karman_shape(y):
    """Dimensionless von Karman shape G(y), y = Omega * L:
    (1 + (8/3)(1.339 y)^2) / (1 + (1.339 y)^2)^(11/6)."""
    a2y2 = (VK_A * y) ** 2
    return (1.0 + (8.0 / 3.0) * a2y2) / (1.0 + a2y2) ** (11.0 / 6.0)


def _dryden_shape(y):
    """Dimensionless Dryden shape G(y), y = Omega * L:
    (1 + 3 y^2) / (1 + y^2)^2."""
    y2 = y * y
    return (1.0 + 3.0 * y2) / (1.0 + y2) ** 2


def von_karman_psd(omega, sigma_w, l):
    """Step 1 of the SKILL.md workflow: one-sided von Karman
    vertical-gust velocity PSD in spatial frequency, per (m/s)^2 per
    (rad/m):

    Phi(Omega) = sigma_w^2 (L/pi) (1 + (8/3)(1.339 L Omega)^2)
                 / (1 + (1.339 L Omega)^2)^(11/6)

    ValueErrors: sigma_w or l not a positive number; omega negative.
    """
    _check_positive("sigma_w", sigma_w)
    _check_positive("L", l)
    _check_omega("Omega", omega)
    return sigma_w * sigma_w * (l / math.pi) * _von_karman_shape(l * omega)


def dryden_psd(omega, sigma_w, l):
    """Step 1 of the SKILL.md workflow (Dryden alternative): one-sided
    Dryden vertical-gust velocity PSD in spatial frequency, per
    (m/s)^2 per (rad/m):

    Phi(Omega) = sigma_w^2 (L/pi) (1 + 3 (L Omega)^2)
                 / (1 + (L Omega)^2)^2

    Same inputs and ValueErrors as von_karman_psd.
    """
    _check_positive("sigma_w", sigma_w)
    _check_positive("L", l)
    _check_omega("Omega", omega)
    return sigma_w * sigma_w * (l / math.pi) * _dryden_shape(l * omega)


def rigid_aircraft_response_params(rho, v, w, s, a_lift, g=G_MS2):
    """Step 2 of the SKILL.md workflow: rigid-aircraft vertical (heave)
    gust-response parameters. With quasi-steady aerodynamics the
    incremental lift is q S a_lift (w_g - z_dot)/V, giving the
    first-order response z_ddot/w_g = h_inf s/(s + K) in the Laplace
    domain with

        K     = rho V S a_lift / (2 m)          [1/s]
        h_inf = K / g = rho V S a_lift / (2 W)  [1/(m/s)]

    h_inf is the frozen-gust incremental load factor per unit gust
    velocity. Returns dict with keys "h_inf", "k_rate" and "mass_kg".
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
    """Step 2 of the SKILL.md workflow: squared magnitude of the
    rigid-aircraft vertical-gust response transfer,
    |H(omega)|^2 = h_inf^2 omega^2 / (omega^2 + K^2), mapping gust
    velocity (m/s) to incremental load factor. omega in rad/s.
    ValueErrors as rigid_aircraft_response_params plus omega negative.
    """
    _check_omega("omega", omega)
    p = rigid_aircraft_response_params(rho, v, w, s, a_lift, g)
    h_inf = p["h_inf"]
    k_rate = p["k_rate"]
    return h_inf * h_inf * omega * omega / (omega * omega + k_rate * k_rate)


def _filter_factor(y, y_c):
    """Heave filter in reduced frequency: y^2 / (y^2 + y_c^2), with the
    reduced-frequency corner y_c = K L / V; y_c = 0 is the frozen-gust
    limit (factor identically 1)."""
    if y_c == 0.0:
        return 1.0
    return y * y / (y * y + y_c * y_c)


def _integral_tail(spectrum, y_max, y_c):
    """Analytic tail of the y-space integrand beyond y_max: the von
    Karman shape decays as c_v y^(-5/3) with c_v = (8/3) 1.339^(-5/3)
    and Dryden as 3 y^(-2); the filter factor is 1 - y_c^2/y^2 to
    leading order. Returns the exact tail integral of the leading and
    first correction terms."""
    if spectrum == "von-karman":
        c_v = (8.0 / 3.0) * VK_A ** (-5.0 / 3.0)
        return c_v * (1.5 * y_max ** (-2.0 / 3.0)
                      - y_c * y_c * (3.0 / 8.0) * y_max ** (-8.0 / 3.0))
    return 3.0 * (1.0 / y_max - y_c * y_c / (3.0 * y_max ** 3.0))


def _integrate_y(spectrum, y_c, n=16384, y_lo=1.0e-4, y_hi=1.0e10):
    """Step 3 of the SKILL.md workflow: integral over y in (0, inf) of
    the filter factor y^2/(y^2 + y_c^2) times the spectrum shape G(y),
    by Simpson's rule on a uniform grid in t = ln(y) with an exact cap
    over (0, y_lo] and the analytic tail beyond y_hi. Deterministic,
    fixed grid (no adaptive stopping, no RNG).
    """
    if n % 2 != 0:
        raise ValueError("n must be even")
    shape = _von_karman_shape if spectrum == "von-karman" else _dryden_shape
    f0 = 1.0 if y_c == 0.0 else 0.0
    t_lo = math.log(y_lo)
    t_hi = math.log(y_hi)
    total = 0.5 * y_lo * (f0 + _filter_factor(y_lo, y_c) * shape(y_lo))
    h = (t_hi - t_lo) / n
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
    """Step 3 of the SKILL.md workflow: the rms-response ratio A (per
    m/s of gust velocity). A^2 is the integral over spatial frequency
    of the squared response transfer magnitude times the normalized
    turbulence spectrum,

        A^2 = integral_0^inf |H(V Omega)|^2 Phi_hat(Omega) dOmega

    with Phi_hat the sigma_w = 1 m/s spectrum. A has units 1/(m/s) and
    is independent of the turbulence intensity.
    ValueErrors: spectrum not 'von-karman' or 'dryden'; l not positive;
    the aircraft inputs invalid.
    """
    _check_spectrum(spectrum)
    _check_positive("L", l)
    p = rigid_aircraft_response_params(rho, v, w, s, a_lift, g)
    h_inf = p["h_inf"]
    k_rate = p["k_rate"]
    y_c = k_rate * l / v
    integral = _integrate_y(spectrum, y_c)
    return h_inf * math.sqrt(integral / math.pi)


def rms_load_factor_response(sigma_w, a_ratio):
    """Step 4 of the SKILL.md workflow: root-mean-square incremental
    load factor response to a turbulence field of rms gust velocity
    sigma_w (m/s): sigma_delta_n = sigma_w A, linear in sigma_w
    (Gaussian linear model). ValueErrors: sigma_w not positive,
    a_ratio not a non-negative number.
    """
    _check_positive("sigma_w", sigma_w)
    _check_non_negative_a(a_ratio)
    return sigma_w * a_ratio


def design_incremental_load_factor(a_ratio, u_sigma):
    """Step 5 of the SKILL.md workflow: limit incremental load factor
    of the continuous-turbulence design condition (linear model),
    delta_n_limit = U_sigma A, with U_sigma the limit turbulence
    intensity in true airspeed (m/s) at the flight condition. Both
    positive and negative gusts apply. ValueErrors: u_sigma not
    positive; a_ratio not a non-negative number.
    """
    _check_positive("U_sigma", u_sigma)
    _check_non_negative_a(a_ratio)
    return u_sigma * a_ratio


def gust_alleviation_factor(ws, cbar, a_lift, rho, g=G_MS2):
    """Step 6 of the SKILL.md workflow: discrete-gust alleviation
    factor K_g = 0.88 mu_g/(5.3 + mu_g) with mu_g = 2(W/S)/(rho cbar
    a_lift g), the closed form of the discrete 1-cosine gust method,
    evaluated here only to express this leaf's continuous-turbulence
    limit increment as the equivalent discrete-gust velocity of the
    sibling envelope method (an algebraic inversion, not a claimed
    product of this leaf). ValueErrors: any input not positive.
    """
    for name, value in (("W/S", ws), ("cbar", cbar), ("a_lift", a_lift),
                        ("rho", rho), ("g", g)):
        _check_positive(name, value)
    mu = 2.0 * ws / (rho * cbar * a_lift * g)
    return 0.88 * mu / (5.3 + mu)


def equivalent_discrete_gust_velocity(delta_n, ws, v_eas, a_lift, cbar,
                                      rho, g=G_MS2):
    """Step 6 of the SKILL.md workflow: equivalent discrete-gust
    velocity U_de_eq (m/s EAS) that the discrete-gust load-factor
    method would need to reproduce the given incremental load factor
    delta_n at the flight condition,

        U_de = 2 (W/S) delta_n / (rho V_e a_lift K_g)

    the algebraic inversion of the discrete 1-cosine load-factor
    formula (sea-level condition, EAS equals TAS, rho = rho0). This is
    the hand-off value reported to the discrete-gust envelope method.
    ValueErrors: delta_n not positive; ws/v_eas/a_lift/cbar/rho/g not
    positive.
    """
    _check_positive("delta_n", delta_n)
    for name, value in (("W/S", ws), ("V_e", v_eas), ("a_lift", a_lift),
                        ("cbar", cbar), ("rho", rho), ("g", g)):
        _check_positive(name, value)
    k_g = gust_alleviation_factor(ws, cbar, a_lift, rho, g)
    return 2.0 * ws * delta_n / (rho * v_eas * a_lift * k_g)


def spectrum_psd_ordinates(spectrum, omega_grid, sigma_w, l):
    """Step 1 of the SKILL.md workflow: turbulence PSD ordinates
    Phi(Omega) at the given Omega grid (rad/m), a list of (omega, phi)
    pairs. ValueErrors as von_karman_psd/dryden_psd plus an empty grid.
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
    """Step 3 of the SKILL.md workflow: response PSD ordinates
    |H(Omega V)|^2 Phi_hat(Omega) at the given Omega grid, the
    integrand of the A-squared integral, per 1/(m/s)^2 per (rad/m).
    ValueErrors as rms_response_ratio plus an empty grid.
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
                                 u_sigma, cbar, g=G_MS2, omega_grid=None):
    """Step 7 of the SKILL.md workflow: the one-shot report dict for
    the continuous-turbulence gust-load condition. Keys: "spectrum",
    "h_inf" (1/(m/s)), "k_rate" (1/s), "y_c" (dimensionless reduced
    filter corner), "a_ratio" (1/(m/s)), "response_factor" (A/h_inf),
    "rms_delta_n_at_1mps", "delta_n_limit", "n_limit",
    "u_de_eq_mps_eas" (m/s EAS), "mu_g", "k_g", "mass_kg",
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
