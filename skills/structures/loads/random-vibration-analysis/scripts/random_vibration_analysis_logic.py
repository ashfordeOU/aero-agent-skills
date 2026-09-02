#!/usr/bin/env python3
"""Random vibration response analysis of a structure or equipment item.

Single-degree-of-freedom (SDOF) response to a base-input acceleration
power spectral density (PSD), the classic Miles equation approach, pure
Python stdlib.

Context (standards-map.yaml, far-25 reference-only): transport
certification FAR 25.301/25.303 frames the limit-loads context, and
equipment qualification practice follows MIL-STD-810H (random vibration
test method) and DO-160G Section 8 (vibration tests of airborne
equipment) for the test level definitions. This module implements only
the common engineering response model those test levels feed into; it
reproduces no standard text.

Model (acceleration response to base acceleration, input PSD G_in in
g^2/Hz, output RMS in g):

    r = f / f_n
    |H(f)|^2 = 1 / ((1 - r^2)^2 + (2 * zeta * r)^2)
    G_out(f) = |H(f)|^2 * G_in(f)
    sigma_miles = sqrt((pi / 2) * f_n * Q * G_in(f_n)),  Q = 1 / (2*zeta)

The Miles closed form assumes a flat (band-limited) input at the
resonance; when the supplied spectrum is not flat the response RMS is
sigma = sqrt(integral of G_out(f) df) evaluated with the trapezoidal
rule on the provided spectrum points. The 3-sigma peak 3*sigma assumes
a narrowband Gaussian response whose peaks reach about three standard
deviations; the equivalent static load factor n_eq = 3*sigma (in g)
rests on the same assumption plus the SDOF response-at-resonance
dominance, and is used for equipment qualification screening only.

Units: f_n and f in Hz, zeta dimensionless, G in g^2/Hz, sigma in
g_rms. Invalid inputs raise ValueError throughout.
"""

import math

# Peak factor for the 3-sigma response level: for a narrowband Gaussian
# random response the peak accelerations reach about 3*sigma. DO-160G
# Section 8 style qualification screening compares the 3-sigma level
# against the item's test-withstand level.
PEAK_FACTOR = 3.0

# Miles equation constant (pi/2) in sigma^2 = (pi/2) * f_n * Q * G.
MILES_CONSTANT = math.pi / 2.0

# zeta threshold above which |H(f)|^2 has no interior peak: the maximum
# of 1/((1-r^2)^2 + (2*zeta*r)^2) over r >= 0 sits at r^2 = 1 - 2*zeta^2
# when zeta < 1/sqrt(2), otherwise at r = 0 (f = 0 Hz).
ZETA_PEAK_LIMIT = 1.0 / math.sqrt(2.0)


def _require_positive_finite(value, name):
    if value is None:
        raise ValueError("%s is required, got None" % (name,))
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric, got %r" % (name, value))
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return value


def _require_nonnegative_finite(value, name):
    if value is None:
        raise ValueError("%s is required, got None" % (name,))
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric, got %r" % (name, value))
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("%s must be nonnegative, got %r" % (name, value))
    return value


def quality_factor(zeta):
    """Amplification factor at resonance Q = 1 / (2 * zeta)."""
    zeta = _require_positive_finite(zeta, "zeta")
    if zeta >= 1.0:
        raise ValueError("zeta must be below 1.0, got %r" % (zeta,))
    return 1.0 / (2.0 * zeta)


def transmissibility_squared(f, f_n, zeta):
    """|H(f)|^2, the acceleration response to base acceleration ratio.

    Frequency ratio r = f/f_n gives
    |H(f)|^2 = 1 / ((1 - r^2)^2 + (2 * zeta * r)^2). At f = f_n the
    value is Q^2 (the resonance amplification of the input PSD).
    """
    f = _require_nonnegative_finite(f, "f")
    f_n = _require_positive_finite(f_n, "f_n")
    zeta = _require_positive_finite(zeta, "zeta")
    if zeta >= 1.0:
        raise ValueError("zeta must be below 1.0, got %r" % (zeta,))
    r = f / f_n
    return 1.0 / ((1.0 - r * r) ** 2 + (2.0 * zeta * r) ** 2)


def transmissibility(f, f_n, zeta):
    """|H(f)|, the acceleration amplitude ratio at frequency f."""
    return math.sqrt(transmissibility_squared(f, f_n, zeta))


def damped_resonance_frequency(f_n, zeta):
    """Frequency of the |H(f)|^2 peak, f_n * sqrt(1 - 2*zeta^2).

    For zeta >= 1/sqrt(2) the transmissibility has no interior peak and
    its maximum sits at f = 0 Hz, which is returned in that case.
    """
    f_n = _require_positive_finite(f_n, "f_n")
    zeta = _require_positive_finite(zeta, "zeta")
    if zeta >= 1.0:
        raise ValueError("zeta must be below 1.0, got %r" % (zeta,))
    if zeta < ZETA_PEAK_LIMIT:
        return f_n * math.sqrt(1.0 - 2.0 * zeta * zeta)
    return 0.0


def miles_sigma(f_n, zeta, g_in_at_resonance):
    """RMS response (g_rms) from the Miles equation.

    sigma = sqrt((pi / 2) * f_n * Q * G_in(f_n)) with Q = 1 / (2*zeta),
    valid for a flat (band-limited) input PSD G_in (g^2/Hz) evaluated at
    the natural frequency f_n (Hz). The closed form follows from
    integrating |H(f)|^2 over all frequencies:
    integral of |H(f)|^2 df = (pi/2) * f_n * Q.
    """
    f_n = _require_positive_finite(f_n, "f_n")
    zeta = _require_positive_finite(zeta, "zeta")
    if zeta >= 1.0:
        raise ValueError("zeta must be below 1.0, got %r" % (zeta,))
    g = _require_nonnegative_finite(g_in_at_resonance, "g_in_at_resonance")
    q = 1.0 / (2.0 * zeta)
    return math.sqrt(MILES_CONSTANT * f_n * q * g)


def _require_spectrum(spectrum):
    """Validate a spectrum iterable of (frequency, G_in) points.

    Returns a list of (f, G) float pairs. Rejects an empty spectrum,
    non-numeric or non-finite values, negative frequencies, negative PSD
    ordinates, and frequencies that do not strictly increase.
    """
    if spectrum is None:
        raise ValueError("spectrum is required, got None")
    points = []
    try:
        iterator = iter(spectrum)
    except TypeError:
        raise ValueError("spectrum must be an iterable of (f, G) pairs")
    for pair in iterator:
        try:
            f, g = pair
        except (TypeError, ValueError):
            raise ValueError(
                "each spectrum point must be an (f, G) pair, got %r" % (pair,))
        f = _require_nonnegative_finite(f, "spectrum frequency")
        g = _require_nonnegative_finite(g, "spectrum ordinate")
        points.append((f, g))
    if not points:
        raise ValueError("spectrum must contain at least one (f, G) point")
    for prev, cur in zip(points, points[1:]):
        if cur[0] <= prev[0]:
            raise ValueError(
                "spectrum frequencies must strictly increase, got %.6g "
                "after %.6g" % (cur[0], prev[0]))
    return points


def response_psd(spectrum, f_n, zeta):
    """Response PSD points G_out(f) = |H(f)|^2 * G_in(f).

    spectrum is an iterable of (f, G_in) pairs with G_in in g^2/Hz.
    Returns a list of (f, G_out) pairs on the same frequency grid.
    """
    points = _require_spectrum(spectrum)
    f_n = _require_positive_finite(f_n, "f_n")
    zeta = _require_positive_finite(zeta, "zeta")
    if zeta >= 1.0:
        raise ValueError("zeta must be below 1.0, got %r" % (zeta,))
    return [(f, g * transmissibility_squared(f, f_n, zeta))
            for f, g in points]


def numerical_sigma(spectrum, f_n, zeta):
    """RMS response (g_rms) by trapezoidal integration of G_out(f).

    sigma^2 = integral of G_out(f) df over the supplied spectrum points
    with the trapezoidal rule on the (f, G_in) grid. At least two
    spectrum points are required. This is the correct path when the
    input PSD is not flat at the natural frequency.
    """
    points = _require_spectrum(spectrum)
    if len(points) < 2:
        raise ValueError(
            "spectrum must contain at least two points for trapezoidal "
            "integration, got %d" % len(points))
    f_n = _require_positive_finite(f_n, "f_n")
    zeta = _require_positive_finite(zeta, "zeta")
    if zeta >= 1.0:
        raise ValueError("zeta must be below 1.0, got %r" % (zeta,))
    variance = 0.0
    prev_f, prev_g = points[0]
    prev_out = prev_g * transmissibility_squared(prev_f, f_n, zeta)
    for f, g in points[1:]:
        out = g * transmissibility_squared(f, f_n, zeta)
        variance += 0.5 * (prev_out + out) * (f - prev_f)
        prev_f, prev_g, prev_out = f, g, out
    return math.sqrt(variance)


def interpolate_psd(spectrum, f):
    """Linear interpolation of the input PSD ordinate at frequency f.

    Returns None when f lies outside the spectrum frequency coverage
    (the Miles value cannot be evaluated there). A single-point spectrum
    only returns its ordinate at exactly that frequency.
    """
    points = _require_spectrum(spectrum)
    f = _require_nonnegative_finite(f, "f")
    if len(points) == 1:
        freq, g = points[0]
        return g if abs(freq - f) <= 1e-12 * max(1.0, freq) else None
    if f < points[0][0] or f > points[-1][0]:
        return None
    for (f0, g0), (f1, g1) in zip(points, points[1:]):
        if f0 <= f <= f1:
            if f1 == f0:
                return g0
            return g0 + (g1 - g0) * (f - f0) / (f1 - f0)
    return None


def peak_three_sigma(sigma_rms_g):
    """3-sigma peak response level, 3 * sigma_rms_g (g)."""
    sigma = _require_nonnegative_finite(sigma_rms_g, "sigma_rms_g")
    return PEAK_FACTOR * sigma


def equivalent_static_load_factor(sigma_rms_g):
    """Equivalent static load factor n_eq = 3 * sigma (g).

    Screening value for equipment qualification: the 3-sigma dynamic
    response level expressed as a static load factor in g. Assumes the
    response at resonance dominates and the item behaves as an SDOF
    oscillator with a narrowband Gaussian response.
    """
    return peak_three_sigma(sigma_rms_g)


def random_vibration_analysis(f_n, zeta, spectrum):
    """Full random vibration response analysis of an SDOF item.

    f_n is the natural frequency (Hz), zeta the damping ratio (0, 1),
    spectrum the input base-acceleration PSD as an iterable of
    (f, G_in) pairs (Hz, g^2/Hz).

    Returns a dict with sigma_rms_g (numerical integration of the
    response PSD over the supplied points, the primary result),
    sigma_miles_g (Miles closed form evaluated with the input PSD
    linearly interpolated at f_n, None when f_n lies outside the
    spectrum coverage), psd_response_points, f_n, q, zeta,
    dominant_response_frequency (the |H(f)|^2 peak frequency), the
    3-sigma peak level peak_3sigma_g, and the equivalent static load
    factor n_eq_g.
    """
    points = _require_spectrum(spectrum)
    if len(points) < 2:
        raise ValueError(
            "spectrum must contain at least two points for trapezoidal "
            "integration, got %d" % len(points))
    f_n = _require_positive_finite(f_n, "f_n")
    zeta = _require_positive_finite(zeta, "zeta")
    if zeta >= 1.0:
        raise ValueError("zeta must be below 1.0, got %r" % (zeta,))
    q = 1.0 / (2.0 * zeta)

    g_out = [(f, g * transmissibility_squared(f, f_n, zeta))
             for f, g in points]
    variance = 0.0
    for (f0, out0), (f1, out1) in zip(g_out, g_out[1:]):
        variance += 0.5 * (out0 + out1) * (f1 - f0)
    sigma_num = math.sqrt(variance)

    g_at_fn = interpolate_psd(points, f_n)
    sigma_miles = (miles_sigma(f_n, zeta, g_at_fn)
                   if g_at_fn is not None else None)

    return {
        "sigma_rms_g": sigma_num,
        "sigma_miles_g": sigma_miles,
        "psd_response_points": g_out,
        "f_n": f_n,
        "q": q,
        "zeta": zeta,
        "dominant_response_frequency": damped_resonance_frequency(f_n, zeta),
        "peak_3sigma_g": PEAK_FACTOR * sigma_num,
        "n_eq_g": PEAK_FACTOR * sigma_num,
    }


if __name__ == "__main__":
    # Worked example: f_n = 40 Hz, zeta = 0.05 (Q = 10), flat input
    # G = 0.01 g^2/Hz over 20-500 Hz.
    fn = 40.0
    z = 0.05
    g_flat = 0.01
    spectrum_flat = [(f, g_flat)
                     for f in [float(x) for x in range(20, 501)]]
    result = random_vibration_analysis(fn, z, spectrum_flat)
    miles = result["sigma_miles_g"]
    print("Q = %.2f" % result["q"])
    print("Miles: sigma = %.4f g_rms, 3-sigma peak = %.3f g, "
          "n_eq = %.3f g" % (miles, PEAK_FACTOR * miles, PEAK_FACTOR * miles))
    print("Numerical over 20-500 Hz (1 Hz grid): sigma = %.4f g_rms "
          "(%.2f%% vs Miles), 3-sigma peak = %.3f g"
          % (result["sigma_rms_g"],
             100.0 * (result["sigma_rms_g"] / miles - 1.0),
             result["peak_3sigma_g"]))
    print("dominant response frequency = %.2f Hz"
          % result["dominant_response_frequency"])
