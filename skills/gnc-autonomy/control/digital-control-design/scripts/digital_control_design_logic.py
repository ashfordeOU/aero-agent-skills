#!/usr/bin/env python3
"""Sampled-data (z-domain) digital control design logic for aerospace GNC
loops: ZOH plant discretization, Tustin compensator emulation with
frequency prewarping, discrete PID coefficient forms, unit-circle
stability, and sample-rate selection (paraphrase of standard textbook
digital control methodology; ARP4754A supplies the development-assurance
context only, per standards-map.yaml).

Deterministic, stdlib-only, offline. All functions validate inputs and
raise ValueError on impossible values.

Conventions (documented in SKILL.md):
- zoh_first_order(a, T): ZOH step-invariant map of G(s) = a/(s + a)
  gives A = exp(-a*T), B = 1 - A, so A + B == 1.0 exactly (unit DC
  gain preserved).
- zoh_second_order(zeta, wn, T): ZOH map of
  G(s) = wn^2/(s^2 + 2*zeta*wn*s + wn^2) realized in the phase-variable
  companion form  Ac = [[0, 1], [-wn^2, -2*zeta*wn]],  Bc = [0, wn^2]^T
  with C = [1, 0]. The discrete state matrix A is the exact closed-form
  matrix exponential for the 2x2 case: with sigma = exp(-zeta*wn*T) and
  omega_d = wn*sqrt(1 - zeta^2),
    A11 = sigma*(cos(wd*T) + (zeta*wn/wd)*sin(wd*T))
    A12 = sigma*sin(wd*T)/wd
    A21 = -sigma*wn^2*sin(wd*T)/wd
    A22 = sigma*(cos(wd*T) - (zeta*wn/wd)*sin(wd*T))
  and the input map B = [1 - A11, sigma*wn^2*sin(wd*T)/wd]. The DC-gain
  identity C*(I - A)^-1*B = 1.0 holds exactly in the model, so the
  sampled step response settles to 1.0; the discrete pole angles are
  wd*T, so the sampled natural frequency matches the continuous
  omega_d.  (Assumption recorded per builder kit: the spec's truncated
  "A11 = sigma*cos(...)" hint describes the scaled companion variant;
  the phase-variable form above is the standard textbook realization
  and satisfies every stated validation identity.)
- tustin_emulate(cont_coeffs, T, wc=None): substitute
  s = (2/T)*(z - 1)/(z + 1) (plain bilinear) or, when wc is given,
  s = (wc/tan(wc*T/2))*(z - 1)/(z + 1) (bilinear with frequency
  prewarping at wc). Coefficient lists are in descending powers of s;
  results are returned as descending-power lists of z with a monic
  denominator. wc*T >= pi is rejected: the prewarp frequency must sit
  below the folding (Nyquist) frequency.
- discrete_pid_position(Kp, Ki, Kd, T): difference-equation
  coefficients of u(k) = Kp*e(k) + (Ki*T)*sum(e) + (Kd/T)*(e(k) - e(k-1)).
- discrete_pid_velocity(Kp, Ki, Kd, T): velocity-form coefficients of
  u(k) = u(k-1) + b0*e(k) + b1*e(k-1) + b2*e(k-2) with
  b0 = Kp + Ki*T + Kd/T, b1 = -Kp - 2*Kd/T, b2 = Kd/T, and a1 = -1 on
  u(k-1) (the 1 - z^-1 denominator of the delta form).
- unit_circle_poles(den_z): poles of the discrete denominator and the
  stability verdict, stable only when every pole has modulus strictly
  below 1. Exact closed forms for degree 1 (linear) and degree 2
  (quadratic formula with cmath); higher degrees raise ValueError
  (numeric root finding is out of scope for an offline stdlib leaf).
  A boundary epsilon of 1e-12 keeps numerically unit-modulus poles from
  ever being mislabeled stable (|z| == 1 is unstable by the strict
  rule).
- sample_rate_rule(wb, T): MINIMUM sample-rate rule, sample 10-20
  times per closed-loop cycle: w_s_min = 10*wb, T_max = 2*pi/w_s_min.
  Verdict "ok" when T <= T_max (sampling at or faster than the rule
  minimum is acceptable), "too-slow" when T > T_max. (The spec's model
  line lists the signature as sample_rate_rule(wb) but the verdict and
  the validation list require the candidate sample period; the
  implemented signature is sample_rate_rule(wb, T).)
"""

import cmath
import math

PI = math.pi
SAMPLING_RULE_LOW = 10.0
SAMPLING_RULE_HIGH = 20.0
_UNIT_CIRCLE_EPS = 1e-12


def _require_positive(value, name):
    if value is None or not math.isfinite(value) or value <= 0.0:
        raise ValueError("%s must be a positive finite number, got %r" % (name, value))


def _coeff_finite(value):
    """True when value is a finite real or a complex with finite parts."""
    if isinstance(value, complex):
        return math.isfinite(value.real) and math.isfinite(value.imag)
    return math.isfinite(float(value))


# ---------------------------------------------------------------------------
# ZOH plant discretization
# ---------------------------------------------------------------------------

def zoh_first_order(a, T):
    """Zero-order-hold step-invariant discretization of G(s) = a/(s + a).

    Returns (A, B) with A = exp(-a*T) and B = 1 - A; the identity
    A + B == 1.0 holds exactly in floating point for a*T in [0.5, 1]
    and the sampled DC gain is 1.0 like the continuous plant.
    """
    _require_positive(a, "a")
    _require_positive(T, "T")
    A = math.exp(-a * T)
    return A, 1.0 - A


def zoh_second_order(zeta, wn, T):
    """Zero-order-hold discretization of G(s) = wn^2/(s^2 + 2*zeta*wn*s + wn^2).

    Underdamped only (0 < zeta < 1). Returns (A, B) where A is the 2x2
    discrete state matrix from the exact closed-form matrix exponential
    and B the 2x1 input map, in the phase-variable companion form with
    C = [1, 0] (see module docstring). The sampled step response
    settles to 1.0 and the sampled natural frequency equals the
    continuous omega_d.
    """
    if zeta is None or not math.isfinite(zeta) or zeta <= 0.0 or zeta >= 1.0:
        raise ValueError("zeta must lie strictly in (0, 1) for the underdamped form, got %r" % (zeta,))
    _require_positive(wn, "wn")
    _require_positive(T, "T")
    wd = wn * math.sqrt(1.0 - zeta * zeta)
    sigma = math.exp(-zeta * wn * T)
    cs = math.cos(wd * T)
    sn = math.sin(wd * T)
    ratio = zeta * wn / wd
    A11 = sigma * (cs + ratio * sn)
    A12 = sigma * sn / wd
    A21 = -sigma * wn * wn * sn / wd
    A22 = sigma * (cs - ratio * sn)
    A = [[A11, A12], [A21, A22]]
    B = [1.0 - A11, sigma * wn * wn * sn / wd]
    return A, B


# ---------------------------------------------------------------------------
# Tustin (bilinear) compensator emulation
# ---------------------------------------------------------------------------

def _poly_mul(a, b):
    """Multiply two polynomials given as descending-power coefficient lists."""
    out = [0.0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        for j, bj in enumerate(b):
            out[i + j] += ai * bj
    return out


def _poly_add(a, b):
    """Add two descending-power polynomials, aligning the constant terms."""
    n = max(len(a), len(b))
    out = [0.0] * n
    for i in range(n):
        ia = len(a) - 1 - i
        ib = len(b) - 1 - i
        out[n - 1 - i] = (a[ia] if ia >= 0 else 0.0) + (b[ib] if ib >= 0 else 0.0)
    return out


def _binom_poly(n, c1, c2):
    """Descending-power coefficients of (c1*z + c2)^n via the binomial theorem."""
    if n < 0:
        raise ValueError("negative binomial degree")
    return [math.comb(n, m) * (c1 ** (n - m)) * (c2 ** m) for m in range(n + 1)]


def _map_poly_to_z(coeffs, c, deg):
    """Map one s-polynomial through s = c*(z-1)/(z+1) and clear denominators.

    coeffs[k] multiplies s^(nd - k) with nd = len(coeffs) - 1. The
    result (z + 1)^nd * poly(c*(z-1)/(z+1)) is a degree-nd polynomial
    in z returned in descending powers; it is then padded to total
    degree `deg` with (z + 1)^(deg - nd) by the caller.
    """
    nd = len(coeffs) - 1
    result = None
    for k, a in enumerate(coeffs):
        p = nd - k
        term = _poly_mul(_binom_poly(p, 1.0, -1.0), _binom_poly(k, 1.0, 1.0))
        scale = a * (c ** p)
        term = [t * scale for t in term]
        result = term if result is None else _poly_add(result, term)
    if result is None:
        result = [0.0]
    return result


def _pad_to_degree(poly, deg):
    """Multiply a z-polynomial by (z + 1)^(deg - (len(poly) - 1))."""
    extra = deg - (len(poly) - 1)
    if extra < 0:
        raise ValueError("polynomial exceeds the common degree")
    if extra == 0:
        return list(poly)
    return _poly_mul(poly, _binom_poly(extra, 1.0, 1.0))


def _eval_poly(coeffs, x):
    """Horner evaluation of a descending-power polynomial at x."""
    acc = 0.0 + 0.0j if isinstance(x, complex) else 0.0
    for c in coeffs:
        acc = acc * x + c
    return acc


def tustin_emulate(cont_coeffs, T, wc=None):
    """Emulate a continuous compensator in discrete time with the bilinear
    (Tustin) transform, optionally prewarped at frequency wc (rad/s).

    cont_coeffs: {"num": [...], "den": [...]} in descending powers of s.
    Returns {"num_z": [...], "den_z": [...]} in descending powers of z
    with a monic denominator (den_z[0] == 1.0). Prewarping maps the
    s-plane point j*wc exactly onto z = exp(j*wc*T), so the emulated
    compensator's phase at wc matches the continuous phase.
    """
    if not isinstance(cont_coeffs, dict) or "num" not in cont_coeffs or "den" not in cont_coeffs:
        raise ValueError("cont_coeffs must be a dict with num and den coefficient lists")
    num = cont_coeffs["num"]
    den = cont_coeffs["den"]
    if not num or not den:
        raise ValueError("num and den must be non-empty coefficient lists")
    if any(not math.isfinite(float(v)) for v in num + den):
        raise ValueError("all coefficients must be finite numbers")
    _require_positive(T, "T")
    if wc is None:
        c = 2.0 / T
    else:
        _require_positive(wc, "wc")
        if wc * T >= PI:
            raise ValueError("prewarp frequency wc must be below the folding frequency pi/T")
        c = wc / math.tan(wc * T / 2.0)
    deg = max(len(num), len(den)) - 1
    num_z = _pad_to_degree(_map_poly_to_z(num, c, deg), deg)
    den_z = _pad_to_degree(_map_poly_to_z(den, c, deg), deg)
    lead = den_z[0]
    if abs(lead) < 1e-15:
        raise ValueError("mapped denominator is degenerate (zero leading coefficient)")
    num_z = [v / lead for v in num_z]
    den_z = [v / lead for v in den_z]
    return {"num_z": num_z, "den_z": den_z}


def tustin_frequency_check(cont_coeffs, z_coeffs, wc, T):
    """Phase error in degrees at wc between the continuous compensator and
    its Tustin-emulated discrete version.

    Evaluates the continuous transfer function at s = j*wc and the
    discrete one at z = exp(j*wc*T) with stdlib complex arithmetic and
    returns the absolute wrapped phase difference in degrees.
    """
    _require_positive(wc, "wc")
    _require_positive(T, "T")
    s = 1j * wc
    z = cmath.exp(1j * wc * T)
    cont = _eval_poly(cont_coeffs["num"], s) / _eval_poly(cont_coeffs["den"], s)
    disc = _eval_poly(z_coeffs["num_z"], z) / _eval_poly(z_coeffs["den_z"], z)
    err = math.degrees(cmath.phase(cont) - cmath.phase(disc))
    while err > 180.0:
        err -= 360.0
    while err <= -180.0:
        err += 360.0
    return abs(err)


# ---------------------------------------------------------------------------
# Discrete PID coefficient forms
# ---------------------------------------------------------------------------

def discrete_pid_position(Kp, Ki, Kd, T):
    """Coefficient triple {kp, ki, kd} of the position-form discrete PID

    u(k) = Kp*e(k) + Ki*T*sum(e) + Kd*(e(k) - e(k-1))/T, i.e. the
    constants that multiply the error, the accumulated error and the
    one-step error difference in the difference equation.
    """
    for gain in (Kp, Ki, Kd):
        if not math.isfinite(gain):
            raise ValueError("PID gains must be finite numbers")
    _require_positive(T, "T")
    return {"kp": Kp, "ki": Ki * T, "kd": Kd / T}


def discrete_pid_velocity(Kp, Ki, Kd, T):
    """Velocity-form discrete PID coefficients {b0, b1, b2, a1} of

    u(k) = u(k-1) + b0*e(k) + b1*e(k-1) + b2*e(k-2) with
    b0 = Kp + Ki*T + Kd/T, b1 = -Kp - 2*Kd/T, b2 = Kd/T and a1 = -1
    (the 1 - z^-1 denominator of the delta-u form). Constant-error
    steady state therefore injects Ki*T*e per step since
    b0 + b1 + b2 = Ki*T.
    """
    for gain in (Kp, Ki, Kd):
        if not math.isfinite(gain):
            raise ValueError("PID gains must be finite numbers")
    _require_positive(T, "T")
    b0 = Kp + Ki * T + Kd / T
    b1 = -Kp - 2.0 * Kd / T
    b2 = Kd / T
    return {"b0": b0, "b1": b1, "b2": b2, "a1": -1.0}


# ---------------------------------------------------------------------------
# Stability and sample-rate rules
# ---------------------------------------------------------------------------

def unit_circle_poles(den_z):
    """Poles of a discrete denominator and the unit-circle stability verdict.

    den_z is a descending-power coefficient list. Returns {"poles":
    [complex], "stable": bool}; stable requires every pole modulus to be
    strictly below 1 (a pole exactly on the unit circle is unstable).
    A boundary epsilon of 1e-12 treats numerically unit-modulus poles as
    boundary, hence unstable. Degrees 1 and 2 use exact closed forms;
    higher degrees raise ValueError.
    """
    if not den_z:
        raise ValueError("den_z must be a non-empty coefficient list")
    if any(not _coeff_finite(v) for v in den_z):
        raise ValueError("all denominator coefficients must be finite numbers")
    lead = den_z[0]
    if abs(lead) < 1e-15:
        raise ValueError("denominator has a zero leading coefficient")
    coeffs = [v / lead for v in den_z]
    order = len(coeffs) - 1
    if order == 0:
        poles = []
    elif order == 1:
        poles = [complex(-coeffs[1], 0.0)]
    elif order == 2:
        disc = cmath.sqrt(coeffs[1] * coeffs[1] - 4.0 * coeffs[2])
        poles = [(-coeffs[1] + disc) / 2.0, (-coeffs[1] - disc) / 2.0]
    else:
        raise ValueError("unit_circle_poles supports degree 1 and 2 denominators, got degree %d" % order)
    stable = all(abs(p) < 1.0 - _UNIT_CIRCLE_EPS for p in poles)
    return {"poles": poles, "stable": stable}


def sample_rate_rule(wb, T):
    """Sample-rate verdict for a closed-loop bandwidth wb (rad/s) and a
    candidate sample period T (s).

    Minimum-rate rule: sample 10-20 times per closed-loop cycle, so
    w_s_min = SAMPLING_RULE_LOW*wb and T_max = 2*pi/w_s_min. Verdict is
    "ok" when T <= T_max (sampling at or faster than the rule minimum)
    and "too-slow" when T > T_max. Returns exactly the keys
    {w_s_min_rad_s, t_max_s, verdict}.
    """
    _require_positive(wb, "wb")
    _require_positive(T, "T")
    w_s_min = SAMPLING_RULE_LOW * wb
    t_max = 2.0 * PI / w_s_min
    verdict = "ok" if T <= t_max else "too-slow"
    return {"w_s_min_rad_s": w_s_min, "t_max_s": t_max, "verdict": verdict}
