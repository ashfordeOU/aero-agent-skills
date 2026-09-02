"""Phase lead and lag compensator design math for aerospace GNC loops.

Deterministic, offline, stdlib-only helpers for classical compensator
design: plant transfer function evaluation, gain crossover frequency,
phase margin, phase lead compensator synthesis from the required phase
boost (lead ratio alpha, zero, pole, crossover frequency), phase lag
compensator synthesis (pole zero pair below crossover, steady state
error constant improvement), and the error constants that gate steady
state error. Transfer functions are numerator and denominator
coefficient lists in descending powers of s, e.g. G(s) = 1/(s(s + 1))
is num = [1], den = [1, 1, 0].

Contract exercised by scripts/test_lead_lag_compensation.py.
"""

import cmath
import math


def polmul(a, b):
    """Return the polynomial product of coefficient lists a and b."""
    out = [0.0] * (len(a) + len(b) - 1)
    for i, ca in enumerate(a):
        for j, cb in enumerate(b):
            out[i + j] += ca * cb
    return out


def tf_eval(num, den, omega):
    """Evaluate G(j*omega) = num(j*omega) / den(j*omega) as a complex value."""
    s = 1j * omega
    n = sum(c * s ** (len(num) - 1 - i) for i, c in enumerate(num))
    d = sum(c * s ** (len(den) - 1 - i) for i, c in enumerate(den))
    if d == 0j:
        raise ValueError("denominator is zero at omega=%r" % (omega,))
    return n / d


def magnitude_db(num, den, omega):
    """Return |G(j*omega)| in dB for a non-negative omega."""
    if omega < 0:
        raise ValueError("omega must be >= 0, got %r" % (omega,))
    return 20.0 * math.log10(abs(tf_eval(num, den, omega)))


def phase_deg(num, den, omega):
    """Return the phase of G(j*omega) in degrees, wrapped to (-180, 180]."""
    if omega < 0:
        raise ValueError("omega must be >= 0, got %r" % (omega,))
    return math.degrees(cmath.phase(tf_eval(num, den, omega)))


def gain_crossover_frequency(num, den, lo=1e-9, hi=1e12, tol=1e-10):
    """Return omega where |G(j*omega)| crosses 0 dB by bisection.

    Assumes the magnitude falls monotonically with omega, as it does
    for the proper plants used in compensator design. Returns the
    crossover frequency in rad/s.

    Raises ValueError when no crossover exists in [lo, hi].
    """
    f_lo = magnitude_db(num, den, lo)
    f_hi = magnitude_db(num, den, hi)
    if f_lo < 0.0:
        raise ValueError("magnitude is below 0 dB at the low end; no gain crossover")
    if f_hi > 0.0:
        raise ValueError("magnitude is above 0 dB at the high end; no gain crossover")
    mid = 0.0
    for _ in range(200):
        mid = math.sqrt(lo) * math.sqrt(hi)
        f_mid = magnitude_db(num, den, mid)
        if abs(f_mid) < tol:
            break
        if f_mid > 0.0:
            lo = mid
        else:
            hi = mid
    return mid


def phase_margin_degrees(num, den):
    """Return the phase margin in degrees of the open loop G.

    PM = 180 + phase(G(j*wc)) at the gain crossover frequency wc.
    A positive phase margin indicates a closed loop stable system.
    """
    wc = gain_crossover_frequency(num, den)
    return 180.0 + phase_deg(num, den, wc)


def series_tf(num1, den1, num2, den2):
    """Return the transfer function of two series blocks as (num, den)."""
    return polmul(num1, num2), polmul(den1, den2)


def compensated_phase_margin(num, den, cnum, cden):
    """Return the phase margin of the loop D(s) * G(s) in degrees."""
    pnum, pden = series_tf(num, den, cnum, cden)
    return phase_margin_degrees(pnum, pden)


def lead_alpha_from_phase_boost(boost_deg):
    """Return the lead ratio alpha for a required maximum phase boost.

    alpha = (1 - sin(phi_m)) / (1 + sin(phi_m)) with phi_m the maximum
    phase lead the network can add, in degrees. A smaller alpha gives a
    larger boost and a stronger gain rise at the peak frequency.

    Raises ValueError unless 0 < boost_deg < 90.
    """
    if not (0.0 < boost_deg < 90.0):
        raise ValueError("phase boost must be in (0, 90) degrees, got %r" % (boost_deg,))
    sin_m = math.sin(math.radians(boost_deg))
    return (1.0 - sin_m) / (1.0 + sin_m)


def lead_max_phase_deg(alpha):
    """Return the maximum phase lead in degrees of D = (1 + sT)/(1 + alpha sT)."""
    if not (0.0 < alpha < 1.0):
        raise ValueError("lead ratio alpha must be in (0, 1), got %r" % (alpha,))
    return math.degrees(math.asin((1.0 - alpha) / (1.0 + alpha)))


def lead_gain_boost_db(alpha):
    """Return the lead network gain at the peak frequency in dB.

    At the peak frequency |D| = 1 / sqrt(alpha), so the gain boost is
    -10 * log10(alpha) dB. The plant must be short by exactly this
    amount at the new crossover.
    """
    if not (0.0 < alpha < 1.0):
        raise ValueError("lead ratio alpha must be in (0, 1), got %r" % (alpha,))
    return -10.0 * math.log10(alpha)


def lead_zero_pole(alpha, omega_m):
    """Return (T, zero, pole) for the lead network D = (1 + sT)/(1 + alpha sT).

    The maximum phase boost occurs at omega_m = 1 / (T * sqrt(alpha)),
    so T = 1 / (omega_m * sqrt(alpha)), the zero is 1 / T and the pole
    is 1 / (alpha * T). Zero and pole are in rad/s.

    Raises ValueError unless 0 < alpha < 1 and omega_m > 0.
    """
    if not (0.0 < alpha < 1.0):
        raise ValueError("lead ratio alpha must be in (0, 1), got %r" % (alpha,))
    if omega_m <= 0:
        raise ValueError("omega_m must be > 0, got %r" % (omega_m,))
    t = 1.0 / (omega_m * math.sqrt(alpha))
    return t, 1.0 / t, 1.0 / (alpha * t)


def lead_transfer_function(alpha, t):
    """Return (num, den) of the lead network (1 + sT)/(1 + alpha sT)."""
    if not (0.0 < alpha < 1.0):
        raise ValueError("lead ratio alpha must be in (0, 1), got %r" % (alpha,))
    if t <= 0:
        raise ValueError("T must be > 0, got %r" % (t,))
    return [t, 1.0], [alpha * t, 1.0]


def lead_phase_deg(alpha, t, omega):
    """Return the lead network phase in degrees at omega.

    phase = atan(omega * T) - atan(omega * alpha * T); at the peak
    frequency omega_m the phase equals the maximum boost phi_m.
    """
    if not (0.0 < alpha < 1.0):
        raise ValueError("lead ratio alpha must be in (0, 1), got %r" % (alpha,))
    if t <= 0:
        raise ValueError("T must be > 0, got %r" % (t,))
    if omega < 0:
        raise ValueError("omega must be >= 0, got %r" % (omega,))
    return math.degrees(
        math.atan(omega * t) - math.atan(omega * alpha * t)
    )


def design_lead_compensator(num, den, pm_desired, boost_margin=5.0):
    """Return the lead compensator parameters that meet a phase margin.

    Steps: measure the plant phase margin at gain crossover, compute
    the phase boost = pm_desired - pm_plant + boost_margin, derive
    alpha from the boost, then find the new crossover omega_m where
    |G(j*omega_m)| = sqrt(alpha) (the lead network adds 1/sqrt(alpha)
    there). Returns a dict with pm_plant, boost_deg, alpha, omega_m,
    t, zero, pole, and the compensator (num, den).

    Raises ValueError if the phase margin specification is already met
    (boost not positive) or no crossover satisfies the gain condition.
    """
    if pm_desired <= 0:
        raise ValueError("pm_desired must be > 0 degrees, got %r" % (pm_desired,))
    if boost_margin <= 0:
        raise ValueError("boost_margin must be > 0 degrees, got %r" % (boost_margin,))
    pm_plant = phase_margin_degrees(num, den)
    boost = pm_desired - pm_plant + boost_margin
    if boost <= 0:
        raise ValueError(
            "plant phase margin %.1f already meets the %g degree specification"
            % (pm_plant, pm_desired)
        )
    alpha = lead_alpha_from_phase_boost(boost)
    target_db = -lead_gain_boost_db(alpha)  # |G| must equal sqrt(alpha), below 0 dB
    lo, hi = 1e-9, 1e12
    f_lo = magnitude_db(num, den, lo) - target_db
    f_hi = magnitude_db(num, den, hi) - target_db
    if f_lo < 0.0:
        raise ValueError("plant magnitude is already below sqrt(alpha) at the low end")
    if f_hi > 0.0:
        raise ValueError("plant magnitude stays above sqrt(alpha); no valid crossover")
    mid = 0.0
    for _ in range(200):
        mid = math.sqrt(lo) * math.sqrt(hi)
        f_mid = magnitude_db(num, den, mid) - target_db
        if abs(f_mid) < 1e-9:
            break
        if f_mid > 0.0:
            lo = mid
        else:
            hi = mid
    omega_m = mid
    t, zero, pole = lead_zero_pole(alpha, omega_m)
    cnum, cden = lead_transfer_function(alpha, t)
    return {
        "pm_plant": pm_plant,
        "boost_deg": boost,
        "alpha": alpha,
        "omega_m": omega_m,
        "t": t,
        "zero": zero,
        "pole": pole,
        "num": cnum,
        "den": cden,
    }


def lag_zero_pole(omega_gc, ratio_beta, decades_below=1.0):
    """Return (zero, pole) in rad/s for a lag network.

    The zero sits decades_below decades below the gain crossover and
    the pole sits a factor ratio_beta below the zero, so the pair
    contributes a small phase lag (about 5 to 6 degrees) at crossover
    while lifting the low frequency gain by 20 * log10(ratio_beta) dB
    when the dc gain equals ratio_beta.

    Raises ValueError unless ratio_beta > 1, omega_gc > 0 and
    decades_below > 0.
    """
    if omega_gc <= 0:
        raise ValueError("omega_gc must be > 0, got %r" % (omega_gc,))
    if ratio_beta <= 1:
        raise ValueError("lag ratio beta must be > 1, got %r" % (ratio_beta,))
    if decades_below <= 0:
        raise ValueError("decades_below must be > 0, got %r" % (decades_below,))
    zero = omega_gc / (10.0 ** decades_below)
    pole = zero / ratio_beta
    return zero, pole


def lag_transfer_function(zero, pole, dc_gain):
    """Return (num, den) of the lag network D = dc_gain * (1 + s/zero)/(1 + s/pole)."""
    if zero <= 0:
        raise ValueError("zero must be > 0, got %r" % (zero,))
    if pole <= 0:
        raise ValueError("pole must be > 0, got %r" % (pole,))
    if dc_gain <= 0:
        raise ValueError("dc_gain must be > 0, got %r" % (dc_gain,))
    return [dc_gain / zero, dc_gain], [1.0 / pole, 1.0]


def lag_phase_deg(zero, pole, omega):
    """Return the lag network phase in degrees at omega (negative below crossover)."""
    if zero <= 0:
        raise ValueError("zero must be > 0, got %r" % (zero,))
    if pole <= 0:
        raise ValueError("pole must be > 0, got %r" % (pole,))
    if omega < 0:
        raise ValueError("omega must be >= 0, got %r" % (omega,))
    return math.degrees(math.atan(omega / zero) - math.atan(omega / pole))


def velocity_error_constant(num, den):
    """Return Kv = lim_{s->0} s * G(s) for a type-1 loop.

    For den with zero constant term, Kv = num(0) / a1 where a1 is the
    coefficient of s in the denominator. The ramp (velocity) error is
    1 / Kv.

    Raises ValueError when the loop is not type 1.
    """
    if den[-1] != 0:
        raise ValueError("loop is not type 1; denominator has a nonzero constant term")
    if len(den) < 2 or den[-2] == 0:
        raise ValueError("type-1 denominator needs a nonzero s coefficient")
    return num[-1] / den[-2]


def position_error_constant(num, den):
    """Return Kp = G(0) for a type-0 loop, or infinity for type 1 or higher."""
    if den[-1] == 0:
        return math.inf
    return num[-1] / den[-1]


def steady_state_error_step(kp):
    """Return the steady state error for a unit step, 1 / (1 + Kp)."""
    if kp == math.inf:
        return 0.0
    if kp < 0:
        raise ValueError("Kp must be >= 0, got %r" % (kp,))
    return 1.0 / (1.0 + kp)


def steady_state_error_ramp(kv):
    """Return the steady state error for a unit ramp, 1 / Kv."""
    if kv <= 0:
        raise ValueError("Kv must be > 0, got %r" % (kv,))
    return 1.0 / kv


def design_lag_compensator(num, den, ratio_beta, decades_below=1.0):
    """Return the lag compensator parameters that lift the error constant.

    The lag zero sits one decade below the plant gain crossover and
    the pole a factor ratio_beta below the zero; the dc gain is set to
    ratio_beta so the velocity error constant is multiplied by
    ratio_beta while the crossover moves little. Returns a dict with
    omega_gc, zero, pole, dc_gain, kv_before, kv_after, and the
    compensator (num, den).

    Raises ValueError when the plant is not type 1.
    """
    omega_gc = gain_crossover_frequency(num, den)
    zero, pole = lag_zero_pole(omega_gc, ratio_beta, decades_below)
    dc_gain = ratio_beta
    cnum, cden = lag_transfer_function(zero, pole, dc_gain)
    kv_before = velocity_error_constant(num, den)
    pnum, pden = series_tf(num, den, cnum, cden)
    kv_after = velocity_error_constant(pnum, pden)
    return {
        "omega_gc": omega_gc,
        "zero": zero,
        "pole": pole,
        "dc_gain": dc_gain,
        "kv_before": kv_before,
        "kv_after": kv_after,
        "num": cnum,
        "den": cden,
    }
