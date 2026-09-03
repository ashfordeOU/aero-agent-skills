#!/usr/bin/env python3
"""Shock response spectrum (SRS) of a transient base acceleration pulse.

For a grid of single-degree-of-freedom (SDOF) oscillator natural
frequencies at a fixed damping, each oscillator is integrated from rest
with fixed-step RK4 over the excitation support; the peak pseudo
acceleration wn^2 * max|x| of each oscillator forms the SRS ordinate.
Pure Python stdlib, offline, deterministic (no RNG).

Equation of motion (relative displacement x of a base-excited SDOF,
wn natural frequency in rad/s, zeta damping ratio):

    x_ddot + 2*zeta*wn*x_dot + wn^2*x = -a_base(t)

Supported base acceleration histories:

    half-sine:      a(t) = A*sin(pi*t/T)        for 0 <= t <= T
    decaying-sine:  a(t) = A*sin(2*pi*fd*t)*exp(-t/tau),  fd = 1/T

The SRS ordinate is the peak pseudo acceleration wn^2*max|x| over the
forced response, that is while the base excitation acts (the primary
response).  For the half-sine the support ends at the pulse end T; for
the decaying sine the support ends where the envelope A*exp(-t/tau)
first falls below 1% of A (ENVELOPE_FLOOR).  The ideal half-sine pulse
leaves a residual base velocity, whose low-frequency free ring after
the pulse is a known artifact of that idealization; excluding it keeps
the classical half-sine SRS shape, where a 10 g 10 ms pulse at Q 10
peaks near 80 Hz at about 16.5 g, reads about 0.31 g at 5 Hz, and
approaches the input amplitude (about 10.1 g) at 1000 Hz.

Units: amplitude in m/s^2 (g = 9.80665 m/s^2), duration in s, natural
frequencies in Hz, outputs in m/s^2 and in g.  Invalid inputs raise
ValueError throughout.

Context (standards-map.yaml far-25 reference-only): FAR/CS 25 frames
dynamic loads and equipment installation context; the relations above
are standard engineering methodology, summary-only, no standard text
reproduced.
"""

import math

# Quality factor used when the caller does not supply one (zeta = 1/(2Q)).
Q_DEFAULT = 10.0
# Standard gravity, m/s^2, the g-unit conversion factor.
G = 9.80665
# Default decay time constant for the decaying sine: tau = 3*T.
DECAY_TAU_MULTIPLIER = 3.0
# Envelope fraction at which the decaying-sine support is considered
# to have ended (the response peak of every oscillator is reached while
# the envelope is still well above this floor).
ENVELOPE_FLOOR = 0.01
# Supported pulse type names.
PULSE_TYPES = ("half-sine", "decaying-sine")
# Oscillator natural periods integrated after the excitation support
# would end in a decay-settling run (documented convention; the ordinate
# itself is the forced-response peak, see module docstring).
SETTLE_PERIODS = 5.0


def _resolve_tau(pulse_type, pulse_duration_s, decay_tau_s):
    """Return the decay time constant actually used for a pulse.

    The decaying sine defaults to tau = 3*T.  A half-sine pulse does
    not use tau at all.
    """
    if decay_tau_s is None:
        return DECAY_TAU_MULTIPLIER * pulse_duration_s
    return decay_tau_s


def base_accel(t, pulse_type, amplitude_ms2, pulse_duration_s, decay_tau_s):
    """Base acceleration amplitude at time t for the given pulse.

    Half-sine: A*sin(pi*t/T) on [0, T], zero outside.  Decaying sine:
    A*sin(2*pi*t/T)*exp(-t/tau) for t >= 0, zero before onset.
    """
    if pulse_type == "half-sine":
        if 0.0 <= t < pulse_duration_s:
            return amplitude_ms2 * math.sin(math.pi * t / pulse_duration_s)
        return 0.0
    if pulse_type == "decaying-sine":
        if t < 0.0:
            return 0.0
        fd = 1.0 / pulse_duration_s
        return (amplitude_ms2 * math.sin(2.0 * math.pi * fd * t)
                * math.exp(-t / decay_tau_s))
    raise ValueError("pulse_type must be 'half-sine' or 'decaying-sine'")


def excitation_support_end(pulse_type, pulse_duration_s, decay_tau_s):
    """End time of the excitation support of a pulse.

    Half-sine: the pulse end T.  Decaying sine: the time at which the
    envelope A*exp(-t/tau) first falls to ENVELOPE_FLOOR*A.
    """
    if pulse_type == "half-sine":
        return pulse_duration_s
    if pulse_type == "decaying-sine":
        return -decay_tau_s * math.log(ENVELOPE_FLOOR)
    raise ValueError("pulse_type must be 'half-sine' or 'decaying-sine'")


def sdof_peak(wn, zeta, base_accel_fn, total_time, dt):
    """Peak pseudo acceleration wn^2 * max|x| for one SDOF oscillator.

    Integrates x_ddot + 2*zeta*wn*x_dot + wn^2*x = -a_base(t) from rest
    over [0, total_time] with fixed-step RK4, where base_accel_fn(t)
    returns the base acceleration at time t.  Returns the pseudo
    acceleration of the peak absolute relative displacement in m/s^2.
    """
    if wn <= 0.0:
        raise ValueError("natural frequency wn must be positive")
    if not (0.0 < zeta < 1.0):
        raise ValueError("damping ratio zeta must be in (0, 1)")
    if total_time <= 0.0:
        raise ValueError("integration time total_time must be positive")
    if dt <= 0.0:
        raise ValueError("time step dt must be positive")

    def deriv(state, t):
        x, xd = state
        return (xd, -2.0 * zeta * wn * xd - wn * wn * x - base_accel_fn(t))

    x, xd = 0.0, 0.0
    max_abs_x = 0.0
    n = int(round(total_time / dt))
    t = 0.0
    for _ in range(n):
        k1 = deriv((x, xd), t)
        k2 = deriv((x + 0.5 * dt * k1[0], xd + 0.5 * dt * k1[1]),
                   t + 0.5 * dt)
        k3 = deriv((x + 0.5 * dt * k2[0], xd + 0.5 * dt * k2[1]),
                   t + 0.5 * dt)
        k4 = deriv((x + dt * k3[0], xd + dt * k3[1]), t + dt)
        x = x + (dt / 6.0) * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0])
        xd = xd + (dt / 6.0) * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1])
        t = t + dt
        if abs(x) > max_abs_x:
            max_abs_x = abs(x)
    return wn * wn * max_abs_x


def srs_curve(pulse_type, amplitude_ms2, pulse_duration_s,
              natural_freqs_hz, q=Q_DEFAULT, decay_tau_s=None):
    """Shock response spectrum of a base acceleration pulse.

    Integrates one SDOF oscillator per grid frequency at damping
    zeta = 1/(2Q) over the excitation support with fixed-step RK4,
    step dt = min(1/(fn*50), pulse_duration/200), and returns the SRS
    as one dict per frequency: {freq_hz, peak_ms2, peak_g}.

    Raises ValueError for a non-physical amplitude, pulse duration,
    quality factor, empty frequency grid, non-positive frequency, or a
    non-positive decay time constant for the decaying sine.
    """
    if pulse_type not in PULSE_TYPES:
        raise ValueError("pulse_type must be 'half-sine' or 'decaying-sine'")
    if amplitude_ms2 <= 0.0:
        raise ValueError("amplitude_ms2 must be positive")
    if pulse_duration_s <= 0.0:
        raise ValueError("pulse_duration_s must be positive")
    if q <= 0.5:
        raise ValueError("quality factor q must exceed 0.5")
    if not natural_freqs_hz:
        raise ValueError("natural_freqs_hz must not be empty")
    if any(f <= 0.0 for f in natural_freqs_hz):
        raise ValueError("natural frequencies must be positive")

    tau = _resolve_tau(pulse_type, pulse_duration_s, decay_tau_s)
    if pulse_type == "decaying-sine" and tau <= 0.0:
        raise ValueError("decay_tau_s must be positive for decaying-sine")

    zeta = 1.0 / (2.0 * q)
    support_end = excitation_support_end(pulse_type, pulse_duration_s, tau)
    curve = []
    for fn in natural_freqs_hz:
        wn = 2.0 * math.pi * fn
        dt = min(1.0 / (fn * 50.0), pulse_duration_s / 200.0)
        peak = sdof_peak(wn, zeta,
                         lambda t, p=pulse_type, a=amplitude_ms2,
                         d=pulse_duration_s, u=tau: base_accel(
                             t, p, a, d, u),
                         support_end, dt)
        curve.append({"freq_hz": float(fn), "peak_ms2": peak,
                      "peak_g": peak / G})
    return curve


def max_response(curve):
    """Entry of an SRS curve with the largest peak response.

    Returns a dict {freq_hz, peak_ms2, peak_g} holding the frequency of
    the maximum pseudo acceleration and its value.
    """
    if not curve:
        raise ValueError("curve must not be empty")
    return max(curve, key=lambda entry: entry["peak_ms2"])
