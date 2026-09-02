#!/usr/bin/env python3
"""Bode frequency-response design logic (paraphrase, common knowledge).

Evaluates an open-loop transfer function G(s) = num(s) / den(s) on the
imaginary axis s = j*w and derives the classical Bode design quantities
for flight control loop analysis: magnitude, phase, gain crossover
frequency, phase crossover frequency, gain margin, phase margin, and
the closed-loop stability verdict from the margins. Standard
control-theory textbook definitions (paraphrase only; FAR-25 and CS-25
supply the airworthiness context for stability margins in certification
flight testing).

Transfer functions are represented as numerator and denominator
coefficient lists in descending powers of s, e.g. G(s) = K/(s(s+1)(s+2))
is num = [K] and den = [1, 3, 2, 0].

Canonical worked anchor: G(s) = K/(s(s+1)(s+2)) with K = 2.
  |G(jw)|            = K / (w*sqrt(w^2+1)*sqrt(w^2+4))
  arg G(jw)          = -90 deg - atan(w) - atan(w/2)   (unwrapped)
  phase crossover    w_pc = sqrt(2) ~= 1.41421356 rad/s
                       (atan(w) + atan(w/2) = 90 deg, so w^2/2 = 1)
  |G(j*w_pc)|        = K/6 = 1/3  ->  gain margin 6/K = 3.0 (9.5424 dB)
  gain crossover     w_gc ~= 0.749347 rad/s (K = 2) where the phase is
                       about -147.39 deg  ->  phase margin ~= 32.61 deg
  K = 6              gain crossover coincides with phase crossover at
                       w = sqrt(2): gain margin 0 dB, phase margin 0 deg
  verdict            stable iff gain margin > 0 dB AND phase margin > 0
                       deg (minimum-phase plants with monotone phase);
                       K < 6 stable, K = 6 marginal, K > 6 unstable.

Units: omega in rad/s, magnitude linear and in dB (20*log10), phase in
degrees, gain margin linear and dB, phase margin in degrees.

Scope: type-1 canonical plants (one pole at the origin) with
minimum-phase numerator, so |G| falls monotonically and the unwrapped
phase falls monotonically. A type-0 plant whose |G(j*0)| <= 1 reports
infinite gain crossover and infinite phase margin by convention.
"""

import bisect
import cmath
import math

_W_LO = 1e-6
_W_HI = 1e6
_GRID_N = 4000
_BISECT_ITERS = 100
_EPS = 1e-6


def _validate_poly(coeffs, label):
    if not isinstance(coeffs, (list, tuple)):
        raise ValueError("%s must be a list of coefficients, got %r" % (label, coeffs))
    if len(coeffs) == 0:
        raise ValueError("%s must be non-empty" % label)
    for c in coeffs:
        if not isinstance(c, (int, float)):
            raise ValueError("%s coefficients must be numbers, got %r" % (label, c))
    if coeffs[0] == 0:
        raise ValueError("%s leading coefficient must be non-zero, got %r" % (label, coeffs[0]))


def _validate(num, den):
    _validate_poly(num, "numerator")
    _validate_poly(den, "denominator")


def _eval_poly(coeffs, s):
    """Horner evaluation of coeffs as a polynomial at complex s."""
    val = 0.0 + 0.0j
    for c in coeffs:
        val = val * s + c
    return val


def _G(num, den, omega):
    """G(j*omega) as a complex number; omega in rad/s, omega > 0."""
    if not isinstance(omega, (int, float)):
        raise ValueError("omega must be a number, got %r" % (omega,))
    if omega < 0:
        raise ValueError("omega must be >= 0, got %r" % (omega,))
    if omega == 0:
        # Type-1 plants have a pole at the origin; G(j*0) is undefined.
        raise ValueError("G(j*omega) is singular at omega = 0 (pole at the origin)")
    s = complex(0.0, omega)
    d = _eval_poly(den, s)
    if d == 0.0j:
        raise ValueError("transfer function singular at omega = %r" % (omega,))
    return _eval_poly(num, s) / d


def _log_grid():
    """Log-spaced frequency grid from _W_LO to _W_HI rad/s."""
    return [_W_LO * (_W_HI / _W_LO) ** (i / float(_GRID_N)) for i in range(_GRID_N + 1)]


def _phase_continuous(num, den, omega, branch):
    """Phase in degrees on the branch within 180 deg of the reference
    angle `branch` (degrees)."""
    a = math.degrees(cmath.phase(_G(num, den, omega)))
    while a - branch > 180.0:
        a -= 360.0
    while branch - a > 180.0:
        a += 360.0
    return a


def _unwrapped_phase_series(num, den, ws):
    """Unwrapped phase in degrees across the grid ws (cumulative +-360)."""
    out = []
    prev = None
    for w in ws:
        a = math.degrees(cmath.phase(_G(num, den, w)))
        if prev is None:
            out.append(a)
        else:
            d = a - prev
            while d > 180.0:
                d -= 360.0
            while d < -180.0:
                d += 360.0
            out.append(prev + d)
        prev = out[-1]
    return out


def _bisect_crossing(f, left, right):
    """Bisect f(w) on [left, right] with f(left) > 0, f(right) <= 0,
    assuming a single root; returns the root within tolerance."""
    for _ in range(_BISECT_ITERS):
        mid = 0.5 * (left + right)
        if f(mid) > 0.0:
            left = mid
        else:
            right = mid
    return 0.5 * (left + right)


def _find_gain_crossover(num, den):
    """Gain crossover: first w > 0 where |G(jw)| = 1 (0 dB). Returns
    (omega, grid_index) or (inf, None) when no crossing exists."""
    ws = _log_grid()
    vals = []
    for w in ws:
        g = _G(num, den, w)
        vals.append(20.0 * math.log10(abs(g)))
    for i in range(1, len(ws)):
        if vals[i] <= 0.0 < vals[i - 1]:
            left = ws[i - 1]
            w = _bisect_crossing(
                lambda x, n=num, d=den: 20.0 * math.log10(abs(_G(n, d, x))),
                left,
                ws[i],
            )
            return w, i - 1
    return float("inf"), None


def _find_phase_crossover(num, den):
    """Phase crossover: first w > 0 where the unwrapped phase is
    -180 deg. Returns (omega, grid_index) or (inf, None)."""
    ws = _log_grid()
    unw = _unwrapped_phase_series(num, den, ws)
    for i in range(1, len(ws)):
        if unw[i] <= -180.0 < unw[i - 1]:
            left = ws[i - 1]
            branch = unw[i - 1]
            w = _bisect_crossing(
                lambda x, n=num, d=den, b=branch: _phase_continuous(n, d, x, b) + 180.0,
                left,
                ws[i],
            )
            return w, i - 1
    return float("inf"), None


def frequency_response(num, den, omega):
    """Magnitude and phase of G(j*omega).

    Returns a dict with keys omega (rad/s), magnitude (linear),
    magnitude_db (20*log10), phase_deg (wrapped to (-180, 180]).
    Worked anchor: G(s) = 2/(s(s+1)(s+2)) at omega = 1 rad/s gives
    magnitude = 2/sqrt(10) ~= 0.63246 (-3.9794 dB) and phase
    = -90 - 45 - atan(0.5) = -161.565 deg.
    """
    _validate(num, den)
    g = _G(num, den, omega)
    mag = abs(g)
    return {
        "omega": omega,
        "magnitude": mag,
        "magnitude_db": 20.0 * math.log10(mag),
        "phase_deg": math.degrees(cmath.phase(g)),
    }


def magnitude(num, den, omega):
    """|G(j*omega)| linear. Anchor: 2/sqrt(10) ~= 0.63246 at omega = 1."""
    _validate(num, den)
    return abs(_G(num, den, omega))


def magnitude_db(num, den, omega):
    """20*log10(|G(j*omega)|) in dB. Anchor: -3.9794 dB at omega = 1."""
    _validate(num, den)
    return 20.0 * math.log10(abs(_G(num, den, omega)))


def phase_deg(num, den, omega):
    """Wrapped phase in (-180, 180] degrees.
    Anchor: -161.565 deg at omega = 1 for G = 2/(s(s+1)(s+2))."""
    _validate(num, den)
    return math.degrees(cmath.phase(_G(num, den, omega)))


def gain_crossover_frequency(num, den):
    """Frequency w_gc (rad/s) where |G(j*w_gc)| = 1 (0 dB); float('inf')
    when |G| never reaches 1. Anchor: ~0.74935 rad/s for K = 2."""
    _validate(num, den)
    w, _ = _find_gain_crossover(num, den)
    return w


def phase_crossover_frequency(num, den):
    """Frequency w_pc (rad/s) where the unwrapped phase reaches -180 deg;
    float('inf') when the phase never reaches -180.
    Anchor: sqrt(2) ~= 1.41421 rad/s for G = K/(s(s+1)(s+2))."""
    _validate(num, den)
    w, _ = _find_phase_crossover(num, den)
    return w


def margins(num, den):
    """Gain and phase margins of the open-loop transfer function.

    Returns a dict with keys gain_crossover_frequency (rad/s),
    phase_crossover_frequency (rad/s), gain_margin (linear, 1/|G(jw_pc)|,
    inf when no phase crossover), gain_margin_db (20*log10 of linear),
    phase_margin (deg, 180 + unwrapped phase at w_gc, inf when no gain
    crossover), gain_margin_ok (bool), phase_margin_ok (bool).

    Anchor: G = 2/(s(s+1)(s+2)) gives gain margin 3.0 (9.5424 dB) at
    w_pc = sqrt(2) and phase margin ~32.61 deg at w_gc ~0.74935 rad/s.
    """
    _validate(num, den)
    w_gc = _find_gain_crossover(num, den)[0]
    w_pc = _find_phase_crossover(num, den)[0]

    if math.isinf(w_pc):
        gain_margin = float("inf")
    else:
        gain_margin = 1.0 / magnitude(num, den, w_pc)

    if math.isinf(w_gc):
        phase_margin = float("inf")
    else:
        ws = _log_grid()
        unw = _unwrapped_phase_series(num, den, ws)
        # Branch of the unwrapped phase at the grid point at or below w_gc
        # (w_gc lies between two grid points by construction).
        branch = unw[max(0, bisect.bisect_left(ws, w_gc) - 1)]
        phase_at_gc = _phase_continuous(num, den, w_gc, branch)
        phase_margin = 180.0 + phase_at_gc

    gm_db = float("inf") if math.isinf(gain_margin) else 20.0 * math.log10(gain_margin)
    return {
        "gain_crossover_frequency": w_gc,
        "phase_crossover_frequency": w_pc,
        "gain_margin": gain_margin,
        "gain_margin_db": gm_db,
        "phase_margin": phase_margin,
        "gain_margin_ok": gain_margin > 1.0,
        "phase_margin_ok": phase_margin > 0.0,
    }


def stability_verdict(num, den):
    """Closed-loop stability verdict from the Bode margins.

    Stable when the gain margin is above 0 dB and the phase margin is
    above 0 deg (minimum-phase open loop with monotone phase fall).
    A margin within 1e-6 of zero is marginal, not stable. Returns a dict
    with keys stable (bool), gain_margin_db, phase_margin,
    gain_crossover_frequency, phase_crossover_frequency, reason (str).

    Anchor: G = K/(s(s+1)(s+2)) with K = 2 is stable (GM 9.54 dB,
    PM 32.61 deg); K = 6 is marginal (GM 0 dB, PM 0 deg); K = 8 is
    unstable (GM -2.50 dB, PM about -12.6 deg).
    """
    _validate(num, den)
    m = margins(num, den)
    gm_db = m["gain_margin_db"]
    pm = m["phase_margin"]
    gm_marginal = abs(gm_db) < _EPS if not math.isinf(gm_db) else False
    pm_marginal = abs(pm) < _EPS if not math.isinf(pm) else False
    if gm_marginal or pm_marginal:
        stable = False
        reason = (
            "marginal: gain margin %.4f dB or phase margin %.4f deg at "
            "the stability boundary" % (gm_db, pm)
        )
    else:
        stable = m["gain_margin_ok"] and m["phase_margin_ok"]
        if stable:
            reason = "stable: gain margin %.2f dB and phase margin %.2f deg" % (gm_db, pm)
        elif not m["gain_margin_ok"]:
            reason = "unstable: gain margin %.2f dB is below 0 dB" % gm_db
        else:
            reason = "unstable: phase margin %.2f deg is below 0 deg" % pm
    return {
        "stable": stable,
        "gain_margin_db": gm_db,
        "phase_margin": pm,
        "gain_crossover_frequency": m["gain_crossover_frequency"],
        "phase_crossover_frequency": m["phase_crossover_frequency"],
        "reason": reason,
    }
