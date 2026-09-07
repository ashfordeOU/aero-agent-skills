#!/usr/bin/env python3
"""Sears-function gust lift logic: the frequency-domain unsteady lift
response of a rigid thin airfoil to a convected sinusoidal vertical gust.

Common-knowledge summary (public-domain textbook methodology: Sears 1941,
JAS 8(3); Bisplinghoff, Ashley and Halfman, Aeroelasticity, the unsteady
incompressible gust chapter; Fung, An Introduction to the Theory of
Aeroelasticity): a rigid thin airfoil of semi-chord b in incompressible
flow at speed V encounters a frozen sinusoidal vertical gust with the
gust vertical velocity field w_g(x, t) = w_g_amp * Re{e^{i*(omega*t -
k*x/b)}}, x measured downstream from the leading edge (time convention
e^{+i*omega*t}, reduced frequency k = omega*b/V = 2*pi*f*b/V). The
complex gust lift amplitude per unit span is L_hat = 2*pi*rho*V*b*w_g_amp
* S(k), where S(k) is the complex Sears function built from the Bessel J
and Y series (Abramowitz and Stegun 9.1.10 to 9.1.11 forms, the same
published series family the flutter sibling documents for the Theodorsen
function C(k) = H1^(2)(k)/(H1^(2)(k) + i*H0^(2)(k)) with Hn^(2) = Jn -
i*Yn). Leading-edge reference: S(k) = [C(k)*(J0(k) - i*J1(k)) +
i*J1(k)]*e^(-i*k), with S(0) = 1 exactly (the quasi-steady limit) and a
phase lag phi(k) = -arg S(k) that grows monotonically from zero. By the
Bessel Wronskian J1*Y0 - J0*Y1 = 2/(pi*k) the gain admits the exact
closed form |S(k)| = (2/(pi*k))/|H1^(2)(k) + i*H0^(2)(k)| for k > 0.
The gain rolls off monotonically from 1 (quasi-steady) toward zero with
reduced frequency; this leaf also locates the half-amplitude reduced
frequency where |S(k)| = 0.5.

The FAR 25 and CS 25 gust-load rules frame the certification context by
name only, never reproduced (standards-map.yaml far-25, cs-25,
reference-only). The gust response computed here is the section
aerodynamics transfer function of the rigid airfoil: no structural
degrees of freedom, no vehicle inertia, no load factor, no PSD content.
Pure stdlib (math only), deterministic, no RNG.
"""

import math

PI = math.pi
EULER_GAMMA = 0.57721566490153286060651209  # Euler-Mascheroni constant
SERIES_TERMS_MAX = 300  # safety cap of the Bessel series loops
SERIES_TOL = 1e-18  # relative term tolerance that stops each Bessel series
BISECT_LO = 0.1  # default low end of the half-amplitude bisection bracket
BISECT_HI = 2.0  # default high end of the half-amplitude bisection bracket


def _check_positive(value, name):
    """Reject a non-finite or non-positive scalar with ValueError."""
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("%s must be finite and positive, got %r" % (name, value))


def _check_nonnegative(value, name):
    """Reject a non-finite or negative scalar with ValueError."""
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(
            "%s must be finite and nonnegative, got %r" % (name, value))


def bessel_j0(x):
    """J0(x) by the A&S 9.1.10 alternating power series (x > 0)."""
    _check_positive(x, "x")
    xh2 = (x / 2.0) ** 2
    total = 1.0
    term = 1.0
    m = 0
    while m < SERIES_TERMS_MAX:
        m += 1
        term = -term * xh2 / (m * m)
        total += term
        if abs(term) <= SERIES_TOL * abs(total):
            break
    return total


def bessel_j1(x):
    """J1(x) = (x/2) * sum_m (-1)^m (x/2)^(2m)/(m!(m+1)!), A&S 9.1.10."""
    _check_positive(x, "x")
    xh = x / 2.0
    xh2 = xh * xh
    total = 1.0
    term = 1.0
    m = 0
    while m < SERIES_TERMS_MAX:
        m += 1
        term = -term * xh2 / (m * (m + 1))
        total += term
        if abs(term) <= SERIES_TOL * abs(total):
            break
    return xh * total


def bessel_y0(x):
    """Y0(x) by the A&S 9.1.11-form log-harmonic series (x > 0)."""
    _check_positive(x, "x")
    xh2 = (x / 2.0) ** 2
    j0 = bessel_j0(x)
    total = 0.0
    p = 1.0  # (x/2)^(2m) / (m!)^2
    h = 0.0  # harmonic number H_m
    m = 0
    while m < SERIES_TERMS_MAX:
        m += 1
        h += 1.0 / m
        p *= xh2 / (m * m)
        term = p * h if m % 2 == 1 else -p * h  # carries (-1)^(m+1)
        total += term
        if abs(term) <= SERIES_TOL * abs(total):
            break
    return (2.0 / PI) * ((math.log(x / 2.0) + EULER_GAMMA) * j0 + total)


def bessel_y1(x):
    """Y1(x) by the A&S 9.1.11-form log-harmonic series (x > 0)."""
    _check_positive(x, "x")
    xh = x / 2.0
    xh2 = xh * xh
    j1 = bessel_j1(x)
    total = 0.0
    q = xh  # (x/2)^(2m+1) / (m!(m+1)!)
    h_prev = 0.0  # H_m, H_0 = 0
    h_curr = 0.0  # H_{m+1}
    m = 0
    while m < SERIES_TERMS_MAX:
        if m > 0:
            h_prev += 1.0 / m
        h_curr = h_prev + 1.0 / (m + 1)
        term = q * (h_prev + h_curr)
        if m % 2 == 1:
            term = -term
        total += term
        if abs(term) <= SERIES_TOL * abs(total):
            break
        m += 1
        q *= xh2 / (m * (m + 1))
    return (2.0 / PI) * ((math.log(x / 2.0) + EULER_GAMMA) * j1 - 1.0 / x) - total / PI


def _hankel_second(k):
    """Complex Hankel functions of the second kind (H0^(2), H1^(2)) at k."""
    _check_positive(k, "k")
    j0 = bessel_j0(k)
    j1 = bessel_j1(k)
    y0 = bessel_y0(k)
    y1 = bessel_y1(k)
    return complex(j0, -y0), complex(j1, -y1)


def theodorsen_c(k):
    """Theodorsen lift-deficiency function C(k) = H1^(2)/(H1^(2) + i*H0^(2)).

    Workflow step 3 of the SKILL.md (evaluate the complex sears function)
    starts here: C(k) enters S(k) through the Sears combination. C = 1 at
    k = 0 exactly, and |C| falls toward the high-k limit 1/2.
    """
    _check_nonnegative(k, "k")
    if k == 0.0:
        return 1.0 + 0.0j
    h0, h1 = _hankel_second(k)
    return h1 / (h1 + 1.0j * h0)


def sears_function(k):
    """Complex Sears function S(k) at reduced frequency k >= 0.

    Leading-edge gust reference: S(k) = [C(k)*(J0(k) - i*J1(k)) +
    i*J1(k)]*e^(-i*k). S(0) = 1 + 0j exactly, the quasi-steady limit.
    """
    _check_nonnegative(k, "k")
    if k == 0.0:
        return 1.0 + 0.0j
    c = theodorsen_c(k)
    j0 = bessel_j0(k)
    j1 = bessel_j1(k)
    s_mid = c * (j0 - 1.0j * j1) + 1.0j * j1
    return s_mid * complex(math.cos(k), -math.sin(k))


def sears_gain(k):
    """Gust gain |S(k)|, the unsteady-load ratio to the quasi-steady
    2*pi*rho*V*b*w_g reference amplitude."""
    return abs(sears_function(k))


def sears_phase_lag(k):
    """Phase lag phi(k) = -arg S(k) = atan2(-Im S, Re S) in radians."""
    s = sears_function(k)
    return math.atan2(-s.imag, s.real)


def reduced_frequency(freq_hz, v, b):
    """Reduced frequency k = 2*pi*freq_hz*b/v of the sinusoidal gust."""
    _check_positive(freq_hz, "freq_hz")
    _check_positive(v, "v")
    _check_positive(b, "b")
    return 2.0 * PI * freq_hz * b / v


def quasi_steady_gust_lift(rho, v, b, w_g_amp):
    """Quasi-steady reference L_qs = 2*pi*rho*V*b*w_g_amp (N/m per unit
    span), the amplitude the gust would produce at k = 0."""
    _check_positive(rho, "rho")
    _check_positive(v, "v")
    _check_positive(b, "b")
    _check_nonnegative(w_g_amp, "w_g_amp")
    return 2.0 * PI * rho * v * b * w_g_amp


def unsteady_gust_load(rho, v, b, w_g_amp, k):
    """Unsteady gust-load amplitude L_hat = L_qs*|S(k)| (N/m per unit
    span): the rigid-section sinusoidal-gust load for the structural
    estimate."""
    _check_positive(rho, "rho")
    _check_positive(v, "v")
    _check_positive(b, "b")
    _check_nonnegative(w_g_amp, "w_g_amp")
    _check_nonnegative(k, "k")
    return quasi_steady_gust_lift(rho, v, b, w_g_amp) * sears_gain(k)


def half_gain_reduced_frequency(k_lo=BISECT_LO, k_hi=BISECT_HI):
    """Reduced frequency where |S(k)| = 0.5 by deterministic bisection.

    The gain is monotone decreasing, so 120 bisection iterations over
    [k_lo, k_hi] locate the half-amplitude crossing to machine precision.
    Raises ValueError when 0.5 is not bracketed (gain(k_lo) <= 0.5 or
    gain(k_hi) >= 0.5), which also rejects a reversed bracket.
    """
    if sears_gain(k_lo) <= 0.5 or sears_gain(k_hi) >= 0.5:
        raise ValueError(
            "half gain 0.5 not bracketed on [%g, %g]" % (k_lo, k_hi))
    lo, hi = k_lo, k_hi
    for _ in range(120):
        mid = 0.5 * (lo + hi)
        if sears_gain(mid) > 0.5:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
