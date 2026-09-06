"""Butterworth IIR bandpass and bandstop filter design by the z-domain
digital frequency transformation.

Pure Python standard library implementation (math, cmath only) of the
closed-form LP-to-BP / LP-to-BS digital frequency transformation
(Oppenheim and Schafer / Proakis class substitution algebra). All
coefficients are computed, none looked up.

Design path: build a digital Butterworth lowpass prototype of order n
with its 3 dB point at prototype_cutoff_hz (default fs/4) by the
bilinear map of the prewarped analog poles, then substitute the
prototype variable u = z^-1 with

  u' = s * (u^2 - c1*u + c2) / (c2*u^2 - c1*u + 1),

s = -1 for the bandpass and s = +1 for the bandstop, compose the
substitution into the prototype numerator and denominator polynomials,
normalize so a[0] = 1, and scale the numerator for unity peak gain at
the bandpass center (image of the prototype DC) or unity DC gain for
the bandstop. The transformed order-2n filter has both band edges at
exactly -3.0103 dB on the magnitude response, the same prewarp-grade
guarantee the lowpass/highpass sibling delivers at a single cutoff.

The substitution polynomials keep their roles: N(u) = u^2 - c1*u + c2
(constant c2) is the numerator of the substitution and D(u) =
c2*u^2 - c1*u + 1 (constant 1) its denominator. Swapping them gives an
identical magnitude response on the unit circle but mirrors every pole
to the reciprocal location, outside the unit circle, with a divergent
direct-form recursion.

The leaf designs and applies band filters only; it does not design
lowpass or highpass coefficients (sibling digital-filter-design owns
both), does not design FIR filters, and does not estimate spectra.

Deterministic, offline, stdlib only. Non-physical inputs raise
ValueError.
"""

import cmath
import math

PI = math.pi
_EDGE_TARGET_DB = -3.010299956639812  # 20*log10(1/sqrt(2)), Butterworth 3 dB point
_EDGE_TOL_DB = 0.02                   # dB tolerance on the band-edge gain check
_MIN_ORDER = 1
_MAX_ORDER = 8


def _check_band(fs, low_cutoff_hz, high_cutoff_hz):
    """Reject non-physical sample rates and band edges."""
    if fs <= 0:
        raise ValueError("fs must be positive")
    if low_cutoff_hz <= 0:
        raise ValueError("low_cutoff_hz must be positive")
    if low_cutoff_hz >= high_cutoff_hz:
        raise ValueError("low_cutoff_hz must be below high_cutoff_hz")
    if high_cutoff_hz >= fs / 2.0:
        raise ValueError("high_cutoff_hz must be below the Nyquist frequency fs/2")


def _check_prototype_cutoff(prototype_cutoff_hz, fs):
    """Reject a prototype cutoff outside (0, fs/2)."""
    if prototype_cutoff_hz <= 0:
        raise ValueError("prototype_cutoff_hz must be positive")
    if prototype_cutoff_hz >= fs / 2.0:
        raise ValueError(
            "prototype_cutoff_hz must be below the Nyquist frequency fs/2")


def _check_order(order):
    """Reject out-of-range prototype orders (1..8)."""
    if not isinstance(order, int) or order < _MIN_ORDER or order > _MAX_ORDER:
        raise ValueError("order must be an integer in 1..%d" % _MAX_ORDER)


def _check_probe(fs, freq_hz):
    """Reject probes outside (0, fs/2]; the exact unit-circle points are valid."""
    if fs <= 0:
        raise ValueError("fs must be positive")
    if freq_hz <= 0 or freq_hz > fs / 2.0:
        raise ValueError("freq_hz must lie in (0, fs/2]")


def _check_signal(x):
    """Reject sample lists that are empty or contain non-finite values."""
    if not isinstance(x, (list, tuple)) or len(x) == 0:
        raise ValueError("samples must be a non-empty list of numbers")
    for value in x:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("samples must be finite numbers")
        if not math.isfinite(float(value)):
            raise ValueError("samples must be finite numbers")


def _poly_mul(p, q):
    """Multiply two ascending-coefficient polynomials, row by row.

    Plain accumulated products in a fixed order, no generator-sum
    reassociation, so repeated calls are bitwise deterministic.
    """
    res = [0.0] * (len(p) + len(q) - 1)
    for i in range(len(p)):
        pi = p[i]
        for j in range(len(q)):
            res[i + j] += pi * q[j]
    return res


def _poly_pow(p, k):
    """Integer power of a polynomial by repeated multiplication."""
    result = [1.0]
    for _ in range(k):
        result = _poly_mul(result, p)
    return result


def _poly_from_roots(roots):
    """Coefficients of prod (x - r) over the roots, ascending in x^-1 order.

    Returns [c0, c1, ..., cn] with c0 = 1 so the list doubles as the
    ascending u-coefficients of prod (1 - r*u). Roots arrive as complex
    conjugate pairs plus possibly one real root, so the coefficients are
    real; the tiny imaginary float residue of the pair products is
    dropped.
    """
    coeffs = [1.0 + 0.0j]
    for root in roots:
        nxt = [0.0j] * (len(coeffs) + 1)
        nxt[0] = coeffs[0]
        for i in range(1, len(coeffs)):
            nxt[i] = coeffs[i] - root * coeffs[i - 1]
        nxt[-1] = -root * coeffs[-1]
        coeffs = nxt
    return [c.real for c in coeffs]


def band_transform_parameters(low_cutoff_hz, high_cutoff_hz,
                              prototype_cutoff_hz, fs):
    """Closed-form digital frequency transformation parameters.

    Returns (alpha, kappa_bp, kappa_bs) with digital frequencies
    wl = 2*pi*low_cutoff_hz/fs, wu = 2*pi*high_cutoff_hz/fs and the
    prototype 3 dB point wc = 2*pi*prototype_cutoff_hz/fs:

      alpha    = cos((wl + wu)/2) / cos((wu - wl)/2)
      kappa_bp = cot((wu - wl)/2) * tan(wc/2)   (bandpass)
      kappa_bs = tan((wu - wl)/2) * tan(wc/2)   (bandstop)

    alpha places the transformed center frequency (image of the
    prototype DC) at w0 = arccos(alpha). At the canonical prototype
    cutoff fs/4, tan(wc/2) = 1 and the two kappa values are exact
    reciprocals.
    """
    _check_band(fs, low_cutoff_hz, high_cutoff_hz)
    _check_prototype_cutoff(prototype_cutoff_hz, fs)
    wl = 2.0 * PI * low_cutoff_hz / fs
    wu = 2.0 * PI * high_cutoff_hz / fs
    wc = 2.0 * PI * prototype_cutoff_hz / fs
    half_delta = (wu - wl) / 2.0
    alpha = math.cos((wl + wu) / 2.0) / math.cos(half_delta)
    kappa_bp = (math.cos(half_delta) / math.sin(half_delta)) * \
        math.tan(wc / 2.0)
    kappa_bs = math.tan(half_delta) * math.tan(wc / 2.0)
    return alpha, kappa_bp, kappa_bs


def center_frequency_hz(low_cutoff_hz, high_cutoff_hz, fs):
    """Center frequency fs*arccos(alpha)/(2*pi), in Hz.

    The image of the prototype DC point under the transformation: the
    bandpass peak and the bandstop notch center. alpha depends only on
    the two band edges, so the canonical fs/4 prototype is used.
    """
    alpha = band_transform_parameters(low_cutoff_hz, high_cutoff_hz,
                                      fs / 4.0, fs)[0]
    return fs * math.acos(alpha) / (2.0 * PI)


def _lowpass_prototype(order, prototype_cutoff_hz, fs):
    """Digital Butterworth lowpass prototype, returns (b, a).

    Prewarped analog cutoff Omega_a = 2*fs*tan(pi*fc/fs), normalized
    left-half-plane unit-circle poles s_k = Omega_a*exp(j*pi*(2k + n -
    1)/(2n)) for k = 1..n, bilinear pole map z_k = (2*fs + s_k)/(2*fs -
    s_k), denominator A(u) = prod_k (1 - z_k*u) with a[0] = 1, and
    numerator B(u) = K*(1 + u)^n with K = sum(a)/2^n for unity DC gain.
    """
    _check_order(order)
    _check_prototype_cutoff(prototype_cutoff_hz, fs)
    omega_a = 2.0 * fs * math.tan(PI * prototype_cutoff_hz / fs)
    scaled = [
        omega_a * cmath.exp(1j * PI * (2.0 * k + order - 1.0) /
                            (2.0 * order))
        for k in range(1, order + 1)
    ]
    z_poles = [(2.0 * fs + s) / (2.0 * fs - s) for s in scaled]
    a = _poly_from_roots(z_poles)
    k_gain = sum(a) / (2.0 ** order)
    b = [k_gain * math.comb(order, k) for k in range(order + 1)]
    return b, a


def _compose(b, a, c1, c2, sign):
    """Compose the substitution into prototype coefficient lists.

    With N(u) = u^2 - c1*u + c2 and D(u) = c2*u^2 - c1*u + 1 and the
    substitution u' = sign*N(u)/D(u), form

      numerator   = sum_k b[k] * sign^k * N^k * D^(n-k)
      denominator = sum_k a[k] * sign^k * N^k * D^(n-k),

    both degree 2n in u. sign is -1 for the bandpass and +1 for the
    bandstop.
    """
    n = len(a) - 1
    n_poly = [c2, -c1, 1.0]
    d_poly = [1.0, -c1, c2]
    n_pows = [_poly_pow(n_poly, k) for k in range(n + 1)]
    d_pows = [_poly_pow(d_poly, k) for k in range(n + 1)]
    num = [0.0] * (2 * n + 1)
    den = [0.0] * (2 * n + 1)
    s_pow = 1.0
    for k in range(n + 1):
        term_n = _poly_mul(n_pows[k], d_pows[n - k])
        term_d = term_n
        factor = s_pow
        for i in range(len(term_n)):
            num[i] += factor * b[k] * term_n[i]
            den[i] += factor * a[k] * term_d[i]
        s_pow *= sign
    return num, den


def _response_mag(b, a, w):
    """Magnitude |B(e^jw)/A(e^jw)| by complex Horner on the ascending lists."""
    u = cmath.exp(1j * w)
    num = 0.0 + 0.0j
    for coef in reversed(b):
        num = num * u + coef
    dval = 0.0 + 0.0j
    for coef in reversed(a):
        dval = dval * u + coef
    return abs(num / dval)


def _design_band(fs, low_cutoff_hz, high_cutoff_hz, order,
                 prototype_cutoff_hz, ftype):
    """Shared bandpass/bandstop design path, returns (b, a)."""
    _check_band(fs, low_cutoff_hz, high_cutoff_hz)
    _check_order(order)
    if prototype_cutoff_hz is None:
        prototype_cutoff_hz = fs / 4.0
    _check_prototype_cutoff(prototype_cutoff_hz, fs)
    b_p, a_p = _lowpass_prototype(order, prototype_cutoff_hz, fs)
    alpha, kappa_bp, kappa_bs = band_transform_parameters(
        low_cutoff_hz, high_cutoff_hz, prototype_cutoff_hz, fs)
    if ftype == "bandpass":
        kappa = kappa_bp
        c1 = 2.0 * alpha * kappa / (kappa + 1.0)
        c2 = (kappa - 1.0) / (kappa + 1.0)
        sign = -1.0
    else:
        kappa = kappa_bs
        c1 = 2.0 * alpha / (kappa + 1.0)
        c2 = (1.0 - kappa) / (1.0 + kappa)
        sign = 1.0
    num, den = _compose(b_p, a_p, c1, c2, sign)
    c0 = den[0]
    if abs(c0) < 1e-15:
        raise ValueError("degenerate composed denominator")
    num = [x / c0 for x in num]
    den = [x / c0 for x in den]
    if ftype == "bandpass":
        # Unity peak gain at the center w0 = arccos(alpha), the image of
        # the prototype DC where the prototype gain is 1 (scale is 1 to
        # float noise).
        w0 = math.acos(alpha)
        scale = _response_mag(num, den, -w0)
    else:
        # Unity DC gain at u = 1 (exact unity to float noise).
        scale = _response_mag(num, den, 0.0)
    if scale <= 0.0 or not math.isfinite(scale):
        raise ValueError("degenerate gain scale")
    num = [x / scale for x in num]
    return num, den


def bandpass_design(fs, low_cutoff_hz, high_cutoff_hz, order,
                    prototype_cutoff_hz=None):
    """Design a digital Butterworth IIR bandpass filter, returns (b, a).

    order is the PROTOTYPE order; the transformed filter has 2*order
    poles and coefficient vectors of length 2*order + 1 with a[0] = 1
    and unity peak gain at the center frequency. prototype_cutoff_hz
    defaults to fs/4, the canonical bilinear image of the unit-cutoff
    analog prototype.
    """
    return _design_band(fs, low_cutoff_hz, high_cutoff_hz, order,
                        prototype_cutoff_hz, "bandpass")


def bandstop_design(fs, low_cutoff_hz, high_cutoff_hz, order,
                    prototype_cutoff_hz=None):
    """Design a digital Butterworth IIR bandstop filter, returns (b, a).

    Same contract as bandpass_design with unity DC gain; at the
    canonical fs/4 prototype and an even prototype order the bandstop
    shares the bandpass denominator.
    """
    return _design_band(fs, low_cutoff_hz, high_cutoff_hz, order,
                        prototype_cutoff_hz, "bandstop")


def frequency_response_db(b, a, freq_hz, fs):
    """Magnitude response 20*log10(|H|) in dB at freq_hz in (0, fs/2].

    H is evaluated on the unit circle at u = exp(-j*2*pi*freq_hz/fs) by
    complex Horner on the ascending coefficient lists. The exact
    unit-circle points are allowed: the bandstop unity Nyquist gain and
    the bandpass exact null floor can be probed at fs/2 itself. An
    exact zero magnitude (float floor of a structural null) reports
    -inf dB.
    """
    _check_probe(fs, freq_hz)
    if len(b) == 0 or len(a) == 0:
        raise ValueError("b and a must be non-empty")
    mag = _response_mag(b, a, -2.0 * PI * freq_hz / fs)
    if mag == 0.0:
        return -float("inf")
    return 20.0 * math.log10(mag)


def apply_filter(b, a, samples):
    """Filter samples with the direct-form difference equation.

    y[n] = (sum_k b[k]*x[n-k] - sum_{k>=1} a[k]*y[n-k]) / a[0] with zero
    initial conditions; the output length equals the input length.
    """
    _check_signal(samples)
    if len(b) == 0 or len(a) == 0:
        raise ValueError("b and a must be non-empty")
    if len(b) != len(a):
        raise ValueError("b and a must have equal length")
    if abs(a[0]) < 1e-15:
        raise ValueError("a[0] must be non-zero")
    x = [float(v) for v in samples]
    n_out = len(x)
    nb = len(b)
    na = len(a)
    a0 = a[0]
    y = [0.0] * n_out
    for n in range(n_out):
        acc = b[0] * x[n]
        for k in range(1, nb):
            if n - k >= 0:
                acc += b[k] * x[n - k]
        for k in range(1, na):
            if n - k >= 0:
                acc -= a[k] * y[n - k]
        y[n] = acc / a0
    return y


def _uplane_poles(fs, low_cutoff_hz, high_cutoff_hz, order, ftype):
    """Magnitudes of the transformed u-plane poles, canonical prototype.

    The prototype u-plane poles p_k = 1/z_k (roots of the prototype
    denominator, all |p_k| > 1) map to the transformed u-plane poles,
    the roots of

      sign*(u^2 - c1*u + c2) - p_k*(c2*u^2 - c1*u + 1) = 0,

    two per prototype pole from the quadratic formula, at the canonical
    prototype cutoff fs/4. All 2*order roots lie strictly outside the
    unit circle (equivalently all z-plane poles z = 1/u strictly
    inside), the closed-form stability evidence. Returns the pole
    magnitudes, ascending.
    """
    _check_band(fs, low_cutoff_hz, high_cutoff_hz)
    _check_order(order)
    if ftype not in ("bandpass", "bandstop"):
        raise ValueError("ftype must be 'bandpass' or 'bandstop'")
    wl = 2.0 * PI * low_cutoff_hz / fs
    wu = 2.0 * PI * high_cutoff_hz / fs
    half_delta = (wu - wl) / 2.0
    alpha = math.cos((wl + wu) / 2.0) / math.cos(half_delta)
    if ftype == "bandpass":
        kappa = math.cos(half_delta) / math.sin(half_delta)  # wc = pi/2
        c1 = 2.0 * alpha * kappa / (kappa + 1.0)
        c2 = (kappa - 1.0) / (kappa + 1.0)
        sign = -1.0
    else:
        kappa = math.tan(half_delta)                         # wc = pi/2
        c1 = 2.0 * alpha / (kappa + 1.0)
        c2 = (1.0 - kappa) / (1.0 + kappa)
        sign = 1.0
    # Prototype z-plane poles from the bilinear map at fs/4 (prewarp
    # exactly 2*fs, tan(pi/4) = 1), u-plane poles p_k = 1/z_k.
    poles = []
    for k in range(1, order + 1):
        s = 2.0 * fs * cmath.exp(1j * PI * (2.0 * k + order - 1.0) /
                                 (2.0 * order))
        z_k = (2.0 * fs + s) / (2.0 * fs - s)
        p_k = 1.0 / z_k
        qa = sign - p_k * c2
        qb = c1 * (p_k - sign)
        qc = sign * c2 - p_k
        disc = cmath.sqrt(qb * qb - 4.0 * qa * qc)
        poles.append(abs((-qb + disc) / (2.0 * qa)))
        poles.append(abs((-qb - disc) / (2.0 * qa)))
    poles.sort()
    return poles


def band_edge_checks(b, a, fs, low_cutoff_hz, high_cutoff_hz, ftype):
    """Verify a band design: edge gains, passband gain, verdict.

    Both band-edge gains must lie within 0.02 dB of -3.010299956639812
    dB (20*log10(1/sqrt(2))); for ftype 'bandpass' the center gain must
    lie within 0.02 dB of 0 dB (extra holds it); for ftype 'bandstop'
    the near-DC and near-Nyquist gains must lie within 0.02 dB of 0 dB
    (extra holds the pair). verdict is 'PASS' only if all checks hold.
    """
    if ftype not in ("bandpass", "bandstop"):
        raise ValueError("ftype must be 'bandpass' or 'bandstop'")
    _check_band(fs, low_cutoff_hz, high_cutoff_hz)
    if len(b) == 0 or len(a) != len(b):
        raise ValueError("b and a must be non-empty vectors of equal length")
    low_edge_db = frequency_response_db(b, a, low_cutoff_hz, fs)
    high_edge_db = frequency_response_db(b, a, high_cutoff_hz, fs)
    low_edge_ok = abs(low_edge_db - _EDGE_TARGET_DB) <= _EDGE_TOL_DB
    high_edge_ok = abs(high_edge_db - _EDGE_TARGET_DB) <= _EDGE_TOL_DB
    if ftype == "bandpass":
        center = center_frequency_hz(low_cutoff_hz, high_cutoff_hz, fs)
        extra = frequency_response_db(b, a, center, fs)
        passband_ok = abs(extra) <= _EDGE_TOL_DB
    else:
        extra = (frequency_response_db(b, a, 1e-9, fs),
                 frequency_response_db(b, a, fs / 2.0 - 1e-9, fs))
        passband_ok = abs(extra[0]) <= _EDGE_TOL_DB and \
            abs(extra[1]) <= _EDGE_TOL_DB
    ok = low_edge_ok and high_edge_ok and passband_ok
    if ok:
        verdict = "PASS"
    else:
        verdict = ("FAIL: low edge %.3f dB, high edge %.3f dB, passband "
                   "extra %r, target %.4f dB, tolerance %.2f dB"
                   % (low_edge_db, high_edge_db, extra,
                      _EDGE_TARGET_DB, _EDGE_TOL_DB))
    return {
        "low_edge_db": low_edge_db,
        "high_edge_db": high_edge_db,
        "target_db": _EDGE_TARGET_DB,
        "low_edge_ok": low_edge_ok,
        "high_edge_ok": high_edge_ok,
        "passband_ok": passband_ok,
        "extra": extra,
        "verdict": verdict,
    }
