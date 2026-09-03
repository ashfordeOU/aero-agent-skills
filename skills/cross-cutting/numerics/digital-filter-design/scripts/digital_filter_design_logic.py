"""Digital filter design: Butterworth IIR lowpass and highpass filters.

Pure Python standard library implementation (math, cmath) of the
bilinear-transform design of Butterworth frequency-selective filters.

Design path: prewarp the analog cutoff Omega_a = 2*fs*tan(pi*fc/fs),
place the normalized Butterworth lowpass poles on the unit circle in the
left half plane, scale them by Omega_a, map each pole s to
z = (2*fs + s)/(2*fs - s) (bilinear transform), form the denominator
polynomial a from the mapped poles (real coefficients from conjugate
pairs, a[0] = 1), and build the numerator from the binomial expansion
of (1 + z^-1)^order (lowpass, DC gain 1) or (1 - z^-1)^order
(highpass, Nyquist gain 1).

Prewarping places the analog 3 dB point of the Butterworth prototype
exactly at the digital cutoff frequency, so |H| at the cutoff is
1/sqrt(2), that is -3.0103 dB. All magnitudes are returned in dB.

The leaf designs and applies filters only; it does not estimate states,
does not smooth flight-test traces, and does not compute frequency
content (see the SKILL body boundaries).

Deterministic, offline, stdlib only. Non-physical inputs raise
ValueError.
"""

import cmath
import math

PI = 3.141592653589793
TOL_3DB = 0.02          # dB tolerance on the -3.0103 dB cutoff check
CUTOFF_DB = 3.0103      # 20*log10(sqrt(2)), the Butterworth 3 dB point
_MAX_POLE_ORDER = 10    # butterworth_poles upper order
_MAX_DESIGN_ORDER = 8   # design_lowpass / design_highpass upper order
_MAX_JURY_ORDER = 4     # Schur-Jury stability table upper order


def _check_fs_cutoff(fs, cutoff_hz):
    """Reject non-physical sample rates and cutoffs (shared validator)."""
    if fs <= 0:
        raise ValueError("fs must be positive")
    if cutoff_hz <= 0:
        raise ValueError("cutoff_hz must be positive")
    if cutoff_hz >= fs / 2.0:
        raise ValueError("cutoff_hz must be below the Nyquist frequency fs/2")


def _check_order(order, upper):
    """Reject out-of-range filter orders."""
    if not isinstance(order, int) or order < 1 or order > upper:
        raise ValueError("order must be an integer in 1..%d" % upper)


def _check_signal(x):
    """Reject x that is not a non-empty list of finite numbers."""
    if not isinstance(x, (list, tuple)) or len(x) == 0:
        raise ValueError("x must be a non-empty list of samples")
    for value in x:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("x samples must be finite numbers")
        if not math.isfinite(float(value)):
            raise ValueError("x samples must be finite numbers")


def _binomial(n, k):
    """Binomial coefficient C(n, k) from the standard library."""
    return math.comb(n, k)


def _poly_from_roots(roots):
    """Monic polynomial coefficients of prod (x - r) over the roots.

    Returns [c0, c1, ..., cn] with c0 = 1 for the polynomial
    c0*x^n + c1*x^(n-1) + ... + cn. Roots arrive as complex conjugate
    pairs plus possibly one real root, so the coefficients are real;
    the tiny imaginary float residue of the pair products is dropped.
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


def _normalize_a(coeffs):
    """Scale the denominator so a[0] equals exactly 1."""
    lead = coeffs[0]
    if abs(lead) < 1e-15:
        raise ValueError("degenerate denominator polynomial")
    return [c / lead for c in coeffs]


def prewarp(cutoff_hz, fs):
    """Analog prewarped cutoff Omega_a = 2*fs*tan(pi*cutoff_hz/fs)."""
    _check_fs_cutoff(fs, cutoff_hz)
    return 2.0 * fs * math.tan(PI * cutoff_hz / fs)


def butterworth_poles(order):
    """Normalized Butterworth lowpass poles on the unit circle (LHP).

    s_k = exp(1j*pi*(2*k + order - 1)/(2*order)) for k = 1..order.
    Every pole has a strictly negative real part.
    """
    _check_order(order, _MAX_POLE_ORDER)
    return [
        cmath.exp(1j * PI * (2.0 * k + order - 1.0) / (2.0 * order))
        for k in range(1, order + 1)
    ]


def analog_scale(poles, omega_a):
    """Scale the normalized analog poles by the prewarped cutoff."""
    if omega_a <= 0:
        raise ValueError("omega_a must be positive")
    return [pole * omega_a for pole in poles]


def bilinear_pole(s, fs):
    """Map an analog pole s to the z-plane: z = (2*fs + s)/(2*fs - s)."""
    if fs <= 0:
        raise ValueError("fs must be positive")
    return (2.0 * fs + s) / (2.0 * fs - s)


def _digital_poles_from_analog(analog_poles, fs):
    """Map a list of analog poles through the bilinear transform."""
    return [bilinear_pole(s, fs) for s in analog_poles]


def _denominator_from_poles(z_poles):
    """Real denominator a from mapped digital poles, normalized a[0] = 1."""
    return _normalize_a(_poly_from_roots(z_poles))


def design_lowpass(fs, cutoff_hz, order):
    """Design a Butterworth IIR lowpass filter, returns (b, a).

    The digital transfer function is H(z) = K*(1 + z^-1)^n / A(z) with
    the denominator A(z) built from the bilinear-mapped, prewarped
    analog poles and K = sum(a)/2^n chosen so the DC gain (z = 1) is 1.
    The prewarped pole placement puts the -3.0103 dB point exactly at
    cutoff_hz.
    """
    _check_order(order, _MAX_DESIGN_ORDER)
    _check_fs_cutoff(fs, cutoff_hz)
    omega_a = prewarp(cutoff_hz, fs)
    scaled = analog_scale(butterworth_poles(order), omega_a)
    z_poles = _digital_poles_from_analog(scaled, fs)
    a = _denominator_from_poles(z_poles)
    k_gain = sum(a) / (2.0 ** order)
    b = [k_gain * _binomial(order, k) for k in range(order + 1)]
    return b, a


def design_highpass(fs, cutoff_hz, order):
    """Design a Butterworth IIR highpass filter, returns (b, a).

    Highpass poles come from the prototype substitution s -> Omega_a^2/s
    applied to the scaled lowpass poles: p_hp = Omega_a^2 / p_lp. The
    reciprocal of a left-half-plane pole stays in the left half plane,
    so every mirrored pole is kept. The numerator is
    K*(1 - z^-1)^n with coefficients b_k = K*C(n,k)*(-1)^k and
    K = sum(a[k]*(-1)^k)/2^n chosen so the Nyquist gain (z = -1) is 1.
    """
    _check_order(order, _MAX_DESIGN_ORDER)
    _check_fs_cutoff(fs, cutoff_hz)
    omega_a = prewarp(cutoff_hz, fs)
    scaled = analog_scale(butterworth_poles(order), omega_a)
    mirrored = [omega_a * omega_a / s for s in scaled]
    z_poles = _digital_poles_from_analog(mirrored, fs)
    a = _denominator_from_poles(z_poles)
    alt = 0.0
    for k in range(order + 1):
        alt += a[k] * ((-1.0) ** k)
    k_gain = alt / (2.0 ** order)
    b = [k_gain * _binomial(order, k) * ((-1.0) ** k)
         for k in range(order + 1)]
    return b, a


def freq_response_db(b, a, freq_hz, fs):
    """Magnitude response 20*log10(|H|) in dB at freq_hz.

    H is evaluated by Horner on z^-1 = exp(-1j*2*pi*freq_hz/fs).
    """
    _check_fs_cutoff(fs, freq_hz)
    if len(b) == 0 or len(a) == 0:
        raise ValueError("coefficient vectors must be non-empty")
    zinv = cmath.exp(-1j * 2.0 * PI * freq_hz / fs)
    num = 0.0 + 0.0j
    for coef in reversed(b):
        num = num * zinv + coef
    den = 0.0 + 0.0j
    for coef in reversed(a):
        den = den * zinv + coef
    magnitude = abs(num / den)
    if magnitude <= 0.0:
        raise ValueError("zero magnitude at the requested frequency")
    return 20.0 * math.log10(magnitude)


def apply_filter(b, a, x):
    """Filter x with the direct-form difference equation, zero initial state.

    y[n] = b[0]*x[n] + sum_{k>=1} (b[k]*x[n-k] - a[k]*y[n-k]) with
    a[0] normalized to 1 and past samples treated as zero.
    """
    _check_signal(x)
    if len(b) == 0 or len(a) == 0:
        raise ValueError("coefficient vectors must be non-empty")
    if abs(a[0]) < 1e-12:
        raise ValueError("a[0] must be non-zero")
    samples = [float(v) for v in x]
    n_out = len(samples)
    nb = len(b)
    na = len(a)
    y = [0.0] * n_out
    for n in range(n_out):
        acc = b[0] * samples[n]
        for k in range(1, nb):
            if n - k >= 0:
                acc += b[k] * samples[n - k]
        for k in range(1, na):
            if n - k >= 0:
                acc -= a[k] * y[n - k]
        y[n] = acc / a[0]
    return y


def _schur_jury_stable(a):
    """Schur-Jury stability table for orders 1..4, returns bool.

    A(z) = a[0] + a[1]*z^-1 + ... + a[n]*z^-n maps to the z polynomial
    F(z) = z^n*A(1/z) with descending coefficients [a[0], ..., a[n]].
    All roots lie strictly inside the unit circle iff F(1) > 0,
    (-1)^n*F(-1) > 0, and |row[0]| > |row[-1]| for each reduced row
    down to three entries.
    """
    n = len(a) - 1
    if n < 1:
        return False
    row = [float(c) for c in a]
    f1 = sum(row)
    if f1 <= 0.0:
        return False
    fneg = 0.0
    for k in range(n + 1):
        fneg += row[k] * ((-1.0) ** (n - k))
    if ((-1.0) ** n) * fneg <= 0.0:
        return False
    while len(row) >= 3:
        if abs(row[0]) <= abs(row[-1]):
            return False
        m = len(row) - 1
        nxt = [0.0] * m
        for k in range(m):
            nxt[k] = row[0] * row[k] - row[-1] * row[m - k]
        row = nxt
    return True


def _verdict(passband_ok, stable, cutoff_gain_db):
    """Assemble the design-verdict string from the check results."""
    if stable is False:
        return "FAIL: denominator poles outside the unit circle (Schur-Jury table); lower the order or move the cutoff"
    if not passband_ok:
        return ("FAIL: cutoff gain %.3f dB deviates from -%.4f dB by more "
                "than %.2f dB" % (cutoff_gain_db, CUTOFF_DB, TOL_3DB))
    if stable is None:
        return ("PASS: cutoff gain %.3f dB within %.2f dB of -%.4f dB; "
                "stability not checked above order %d"
                % (cutoff_gain_db, TOL_3DB, CUTOFF_DB, _MAX_JURY_ORDER))
    return ("PASS: cutoff gain %.3f dB within %.2f dB of -%.4f dB; "
            "denominator poles stable" % (cutoff_gain_db, TOL_3DB, CUTOFF_DB))


def filter_design_checks(b, a, fs, cutoff_hz, ftype):
    """Verify a design: cutoff gain, reference gain, stability, verdict.

    ftype is 'lowpass' or 'highpass'. The lowpass reference gain probes
    DC at 1 Hz; the highpass reference gain probes Nyquist at fs/2 - 1
    Hz, so fs must exceed 2 Hz for the probe to be meaningful.
    Stability uses the Schur-Jury table for orders 1..4 and returns
    None (not checked) above order 4.
    """
    _check_fs_cutoff(fs, cutoff_hz)
    if fs <= 2:
        raise ValueError("fs must exceed 2 Hz for the reference-gain probe")
    if ftype not in ("lowpass", "highpass"):
        raise ValueError("ftype must be 'lowpass' or 'highpass'")
    if len(b) == 0 or len(a) != len(b):
        raise ValueError("b and a must be non-empty vectors of equal length")
    order = len(a) - 1
    if order < 1:
        raise ValueError("a must describe at least a first-order filter")
    cutoff_gain_db = freq_response_db(b, a, cutoff_hz, fs)
    if ftype == "lowpass":
        reference_gain_db = freq_response_db(b, a, 1.0, fs)
    else:
        reference_gain_db = freq_response_db(b, a, fs / 2.0 - 1.0, fs)
    passband_ok = abs(cutoff_gain_db + CUTOFF_DB) <= TOL_3DB
    if order <= _MAX_JURY_ORDER:
        stable = _schur_jury_stable(a)
    else:
        stable = None
    verdict = _verdict(passband_ok, stable, cutoff_gain_db)
    return {
        "cutoff_gain_db": cutoff_gain_db,
        "reference_gain_db": reference_gain_db,
        "passband_ok": passband_ok,
        "stable": stable,
        "verdict": verdict,
    }
