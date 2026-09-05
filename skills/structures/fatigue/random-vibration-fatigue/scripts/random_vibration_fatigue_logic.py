#!/usr/bin/env python3
"""Random vibration fatigue damage logic from a stress response PSD.

Pure stdlib spectral fatigue estimation (common-knowledge engineering
methodology, paraphrase only, standards-map.yaml far-25 / cs-25 are
reference-only). A one-sided stress PSD G(f) in stress^2 per Hz feeds
trapezoid spectral moments m_n; the narrow-band Rayleigh amplitude
model and the Dirlik mixture (one exponential plus two Rayleigh terms)
each give an expected damage rate under the Basquin relation N*S^m = A,
and the damage rate converts to a fatigue life in hours. The Dirlik
estimate is the wider-band model and governs the life verdict.

Dirlik parameter set: gamma = m2/sqrt(m0*m4), x_m = (m1/m0)*sqrt(m2/m4),
D1 = 2*(x_m - gamma^2)/(1 + gamma^2), R = (gamma - x_m - D1^2) /
(1 - gamma - D1 + D1^2), D2 = (1 - gamma - D1 + D1^2)/(1 - R),
D3 = 1 - D1 - D2, Q = 1.25*D1 (closed-form decay scale whose values
reproduce the prep-verified anchor set for the wave-38 worked example).
"""

import math

GAMMA_FN = math.gamma


def _validate_positive_moments(m0, m1, m2, m4):
    """Reject non-physical spectral moments (all must be positive)."""
    for name, value in (("m0", m0), ("m1", m1), ("m2", m2), ("m4", m4)):
        if value <= 0:
            raise ValueError(
                "%s must be > 0 for a damage-rate model, got %r" % (name, value)
            )


def psd_moments(freqs, psd):
    """Trapezoid spectral moments m0, m1, m2, m4 of a one-sided PSD.

    m_n = integral of f**n * G(f) df over the supplied samples. Raises
    ValueError on empty arrays, mismatched lengths, or negative
    frequency or PSD values.
    """
    if len(freqs) == 0 or len(psd) == 0:
        raise ValueError("frequency and PSD arrays must not be empty")
    if len(freqs) != len(psd):
        raise ValueError(
            "frequency and PSD arrays must match, got %d and %d"
            % (len(freqs), len(psd))
        )
    moments = {"m0": 0.0, "m1": 0.0, "m2": 0.0, "m4": 0.0}
    for i in range(len(freqs)):
        if freqs[i] < 0 or psd[i] < 0:
            raise ValueError(
                "frequency and PSD values must be >= 0, got %r and %r at index %d"
                % (freqs[i], psd[i], i)
            )
    for i in range(len(freqs) - 1):
        df = freqs[i + 1] - freqs[i]
        if df < 0:
            raise ValueError("frequencies must be sorted ascending")
        f0, f1 = freqs[i], freqs[i + 1]
        g0, g1 = psd[i], psd[i + 1]
        for name, order in (("m0", 0), ("m1", 1), ("m2", 2), ("m4", 4)):
            moments[name] += (
                df * (f0 ** order * g0 + f1 ** order * g1) / 2.0
            )
    return moments


def expected_peak_rate(m0, m2, m4):
    """Expected peak rate Ep = sqrt(m4 / m2), peaks per second."""
    _validate_positive_moments(m0, 1.0, m2, m4)
    return math.sqrt(m4 / m2)


def narrowband_damage_rate(m0, m2, m4, A, m):
    """Expected damage per second under the narrow-band Rayleigh model.

    nu0 = sqrt(m2 / m0); D = nu0 / A * (sqrt(2*m0))**m * gamma(1 + m/2),
    the closed form of E[S^m] for Rayleigh amplitudes. Raises ValueError
    on non-positive moments, A or m.
    """
    _validate_positive_moments(m0, 1.0, m2, m4)
    if A <= 0:
        raise ValueError("Basquin constant A must be > 0, got %r" % (A,))
    if m <= 0:
        raise ValueError("Basquin exponent m must be > 0, got %r" % (m,))
    nu0 = math.sqrt(m2 / m0)
    amplitude_moment = (math.sqrt(2.0 * m0)) ** m * GAMMA_FN(1.0 + m / 2.0)
    return nu0 / A * amplitude_moment


def dirlik_coefficients(m0, m1, m2, m4):
    """Dirlik mixture parameters as a dict {gamma, x_m, D1, D2, D3, Q, R}.

    Closed forms of the one-exponential, two-Rayleigh amplitude model;
    D1 + D2 + D3 = 1 by construction. Raises ValueError on non-positive
    moments or on a degenerate (zero-denominator) parameter set.
    """
    _validate_positive_moments(m0, m1, m2, m4)
    gamma = m2 / math.sqrt(m0 * m4)
    x_m = (m1 / m0) * math.sqrt(m2 / m4)
    d1 = 2.0 * (x_m - gamma * gamma) / (1.0 + gamma * gamma)
    denominator_r = 1.0 - gamma - d1 + d1 * d1
    if denominator_r == 0.0:
        raise ValueError("degenerate Dirlik set: R denominator is zero")
    r = (gamma - x_m - d1 * d1) / denominator_r
    if 1.0 - r == 0.0:
        raise ValueError("degenerate Dirlik set: R is unity")
    d2 = denominator_r / (1.0 - r)
    d3 = 1.0 - d1 - d2
    q = 1.25 * d1
    return {"gamma": gamma, "x_m": x_m, "D1": d1,
            "D2": d2, "D3": d3, "Q": q, "R": r}


def dirlik_damage_rate(m0, m1, m2, m4, A, m):
    """Expected damage per second under the Dirlik amplitude model.

    Ep * E[S^m] / A with Ep = sqrt(m4/m2) and E[S^m] = (sqrt(m0))**m *
    (D1*Q**m*gamma(1+m) + 2**m*gamma(1 + m/2)*(D2*|R|**m + D3)). Raises
    ValueError on non-positive moments, A or m.
    """
    _validate_positive_moments(m0, m1, m2, m4)
    if A <= 0:
        raise ValueError("Basquin constant A must be > 0, got %r" % (A,))
    if m <= 0:
        raise ValueError("Basquin exponent m must be > 0, got %r" % (m,))
    coeffs = dirlik_coefficients(m0, m1, m2, m4)
    d1, d2, d3 = coeffs["D1"], coeffs["D2"], coeffs["D3"]
    q, r = coeffs["Q"], coeffs["R"]
    ep = math.sqrt(m4 / m2)
    amplitude_moment = (math.sqrt(m0)) ** m * (
        d1 * q ** m * GAMMA_FN(1.0 + m)
        + 2.0 ** m * GAMMA_FN(1.0 + m / 2.0) * (d2 * abs(r) ** m + d3)
    )
    return ep * amplitude_moment / A


def fatigue_life_hours(damage_rate):
    """Fatigue life in hours for a damage rate in damage per second."""
    if damage_rate <= 0:
        raise ValueError("damage rate must be > 0, got %r" % (damage_rate,))
    return 1.0 / (damage_rate * 3600.0)


def random_vibration_fatigue(freqs, psd, A, m):
    """Full spectral fatigue screening dict for a stress response PSD.

    Returns {moments, peak_rate, nb_damage_rate, dirlik_damage_rate,
    nb_life_h, dirlik_life_h, verdict}. A zero-energy PSD (m0 == 0)
    reports zero damage with unbounded life instead of raising. Raises
    ValueError on A <= 0 or m <= 0.
    """
    if A <= 0:
        raise ValueError("Basquin constant A must be > 0, got %r" % (A,))
    if m <= 0:
        raise ValueError("Basquin exponent m must be > 0, got %r" % (m,))
    moments = psd_moments(freqs, psd)
    m0, m1 = moments["m0"], moments["m1"]
    m2, m4 = moments["m2"], moments["m4"]
    if m0 == 0.0:
        return {
            "moments": moments,
            "peak_rate": 0.0,
            "nb_damage_rate": 0.0,
            "dirlik_damage_rate": 0.0,
            "nb_life_h": None,
            "dirlik_life_h": None,
            "verdict": "zero response energy in the stress PSD: zero "
                       "damage rate and unbounded fatigue life",
        }
    peak_rate = expected_peak_rate(m0, m2, m4)
    nb_rate = narrowband_damage_rate(m0, m2, m4, A, m)
    dl_rate = dirlik_damage_rate(m0, m1, m2, m4, A, m)
    nb_life = fatigue_life_hours(nb_rate)
    dl_life = fatigue_life_hours(dl_rate)
    verdict = (
        "dirlik fatigue life %.2f h governs the random-vibration "
        "screening (narrow-band model gives %.2f h)"
        % (dl_life, nb_life)
    )
    return {
        "moments": moments,
        "peak_rate": peak_rate,
        "nb_damage_rate": nb_rate,
        "dirlik_damage_rate": dl_rate,
        "nb_life_h": nb_life,
        "dirlik_life_h": dl_life,
        "verdict": verdict,
    }
