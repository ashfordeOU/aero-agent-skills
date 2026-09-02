#!/usr/bin/env python3
"""Level acceleration (total energy method) flight test logic.

Paraphrase of common flight-test methodology in the FAR-25 / CS-25
general performance context (standards-map.yaml, far-25 and cs-25:
reference-only). This leaf covers the flight test side of acceleration
capability at constant altitude: converting the recorded airspeed
samples to true airspeed with the ISA density at the test altitude,
smoothing the airspeed versus time trace, differentiating the smoothed
trace to the acceleration, evaluating the specific excess power
P_s = dh/dt + V * a / g with the total energy method, estimating the
excess thrust (the drag gap, thrust available minus drag) at the test
weight from P_s, adding the drag from the aircraft polar to estimate
the thrust available and the thrust required when the polar is
provided, and correcting the measured specific excess power to the
reference weight and the standard density with a documented simplified
correction.

Units: SI. Forces and weight in N, speeds in m/s, accelerations in
m/s^2, density in kg/m^3, time in s. P_s is specific power, power per
unit weight, in m/s (= W per N of weight). Stdlib only, deterministic.

ISA model: sea level density RHO0 = 1.225 kg/m^3, sea level
temperature 288.15 K, sea level pressure 101325 Pa, troposphere lapse
0.0065 K/m to the 11000 m tropopause (isothermal 216.65 K above), valid
0 to 20000 m. A0 = 340.294 m/s is the reference sea level speed of
sound.
"""

import math

RHO0 = 1.225             # standard sea level density, kg/m^3
P0_PA = 101325.0         # standard sea level pressure, Pa
T0_K = 288.15            # standard sea level temperature, K
LAPSE_K_PER_M = 0.0065   # troposphere lapse rate, K/m
G0 = 9.80665             # standard gravity, m/s^2
R_GAS = 287.05287        # specific gas constant of air, J/(kg K)
A0_MS = 340.294          # reference sea level speed of sound, m/s
H_TROPO_M = 11000.0      # tropopause geopotential altitude, m
T_TROPO_K = 216.65       # tropopause temperature, K
MAX_H_M = 20000.0        # model ceiling, m
H_ISO_M = R_GAS * T_TROPO_K / G0                 # isothermal scale height, m
ISA_DENSITY_EXP = G0 / (R_GAS * LAPSE_K_PER_M) - 1.0    # 4.25588
ISA_PRESSURE_EXP = G0 / (R_GAS * LAPSE_K_PER_M)          # 5.25588


def _check_positive(name, value):
    if value <= 0:
        raise ValueError("%s must be > 0, got %r" % (name, value))


def _check_nonnegative(name, value):
    if value < 0:
        raise ValueError("%s must be >= 0, got %r" % (name, value))


def isa_conditions(altitude_m):
    """ISA (T in K, P in Pa, rho in kg/m^3) at geopotential altitude.

    Troposphere lapse 0.0065 K/m to 11000 m, isothermal 216.65 K above,
    pressure integrated from the hydrostatic balance, rho = P / (R * T).
    Worked anchors: at 0 m (288.15, 101325.0, 1.225); at 8000 m
    (236.15, 35599.8, 0.52517); at the tropopause 11000 m the
    temperature is 216.65 K and the density ratio is 0.29707.
    """
    if altitude_m < 0 or altitude_m > MAX_H_M:
        raise ValueError(
            "altitude must be within 0 to 20000 m, got %r" % (altitude_m,))
    if altitude_m <= H_TROPO_M:
        t = T0_K - LAPSE_K_PER_M * altitude_m
        p = P0_PA * (1.0 - LAPSE_K_PER_M * altitude_m / T0_K) ** ISA_PRESSURE_EXP
    else:
        t = T_TROPO_K
        p_t = P0_PA * (1.0 - LAPSE_K_PER_M * H_TROPO_M / T0_K) ** ISA_PRESSURE_EXP
        p = p_t * math.exp(-(altitude_m - H_TROPO_M) / H_ISO_M)
    return (t, p, p / (R_GAS * t))


def true_airspeed_from_eas(v_eas, rho, rho0=RHO0):
    """True airspeed in m/s from equivalent airspeed and air density.

    V_tas = V_eas * sqrt(rho0 / rho), the equal dynamic pressure form
    q = 0.5 * rho0 * V_eas^2 = 0.5 * rho * V_tas^2. At sea level on the
    standard day rho = rho0 and the two speeds coincide; at altitude
    the true airspeed exceeds the equivalent airspeed. Worked: 110 m/s
    equivalent airspeed at the 8000 m ISA density 0.52517 kg/m^3 gives
    168.0 m/s true airspeed.
    """
    _check_positive("equivalent airspeed", v_eas)
    _check_positive("air density", rho)
    _check_positive("sea level density", rho0)
    return v_eas * math.sqrt(rho0 / rho)


def smooth_trace(trace, window):
    """Moving average of the trace over an odd centered window.

    Same-length output. At points within (window - 1) / 2 samples of
    either end the window is clipped to the available samples. The
    window must be a positive odd integer; even windows raise
    ValueError because a centered stencil needs a midpoint. A linear
    ramp is preserved exactly at every interior point where the full
    window fits.
    """
    if not isinstance(window, int):
        raise ValueError("smoothing window must be an integer, got %r" % (window,))
    if window < 1:
        raise ValueError("smoothing window must be >= 1, got %r" % (window,))
    if window % 2 == 0:
        raise ValueError("smoothing window must be odd, got %r" % (window,))
    if len(trace) == 0:
        raise ValueError("trace must not be empty")
    half = (window - 1) // 2
    out = []
    for i in range(len(trace)):
        lo = max(0, i - half)
        hi = min(len(trace) - 1, i + half)
        out.append(sum(trace[lo:hi + 1]) / (hi - lo + 1.0))
    return out


def acceleration_from_trace(v_list, t_list):
    """Acceleration in m/s^2 from the airspeed and time samples.

    Central differences on the interior, one-sided differences at the
    two ends: a[0] from the first two samples, a[i] = (V[i+1] -
    V[i-1]) / (t[i+1] - t[i-1]) for 1 <= i <= n - 2, and a[n-1] from the
    last two samples. The times must be strictly increasing and the two
    lists equal in length (at least two samples). A constant airspeed
    trace gives exactly zero acceleration.
    """
    if len(v_list) != len(t_list):
        raise ValueError(
            "airspeed and time lists must match in length, got %r and %r"
            % (len(v_list), len(t_list)))
    n = len(v_list)
    if n < 2:
        raise ValueError("at least two samples are required, got %r" % (n,))
    for i in range(n):
        _check_positive("airspeed sample %d" % i, v_list[i])
    for i in range(1, n):
        if t_list[i] <= t_list[i - 1]:
            raise ValueError(
                "time must be strictly increasing, sample %d time %r not above %r"
                % (i, t_list[i], t_list[i - 1]))
    out = [0.0] * n
    out[0] = (v_list[1] - v_list[0]) / (t_list[1] - t_list[0])
    for i in range(1, n - 1):
        out[i] = (v_list[i + 1] - v_list[i - 1]) / (t_list[i + 1] - t_list[i - 1])
    out[n - 1] = (v_list[n - 1] - v_list[n - 2]) / (t_list[n - 1] - t_list[n - 2])
    return out


def specific_excess_power(v, a, g=G0, dh_dt=0.0):
    """Specific excess power P_s in m/s from the total energy method.

    P_s = dh/dt + V * a / g, the time rate of change of the total
    energy per unit weight (energy height rate). For a level run
    dh/dt = 0 and P_s = V * a / g. The dh_dt term keeps the form valid
    for slightly non-level runs. A decelerating run gives a negative
    P_s. Worked: 160 m/s at 1 m/s^2 gives 16.3155 m/s; with a 1.5 m/s
    climb rate added, 17.8155 m/s.
    """
    _check_positive("true airspeed", v)
    _check_positive("gravity", g)
    return dh_dt + v * a / g


def excess_thrust_from_ps(ps, v, w):
    """Excess thrust in N (drag gap, thrust available minus drag).

    delta_T = W * P_s / V, from the power balance delta_T * V = W * P_s.
    For a level run delta_T equals (W / g) * a, Newton's second law
    along the flight path. A negative P_s gives a negative excess
    thrust, meaning no sustained acceleration at that speed. Worked:
    250000 N at 160 m/s with P_s 16.3155 m/s gives 25492.9 N.
    """
    _check_positive("true airspeed", v)
    _check_positive("weight", w)
    return w * ps / v


def lift_coefficient(w, v, rho, s):
    """Lift coefficient CL = W / (0.5 * rho * V^2 * S)."""
    _check_positive("weight", w)
    _check_positive("true airspeed", v)
    _check_positive("air density", rho)
    _check_positive("wing area", s)
    return w / (0.5 * rho * v * v * s)


def drag_coefficient(cd0, k, cl):
    """Drag coefficient CD = cd0 + k * CL^2 (parabolic drag polar)."""
    _check_nonnegative("zero lift drag coefficient", cd0)
    _check_nonnegative("induced drag factor", k)
    _check_nonnegative("lift coefficient", cl)
    return cd0 + k * cl * cl


def drag_from_polar(v, rho, s, w, cd0, k):
    """Drag force in N from the parabolic polar at the test density.

    CL from the test weight, CD = cd0 + k * CL^2, D = 0.5 * rho * V^2 *
    S * CD. At steady level flight this drag equals the thrust
    required. Worked at 8000 m ISA density (0.52517 kg/m^3), V 160 m/s,
    W 250000 N, S 122.6 m^2, cd0 0.02, k 0.042: CL 0.30335, CD
    0.023865, D 19667.8 N.
    """
    _check_positive("true airspeed", v)
    _check_positive("air density", rho)
    _check_positive("wing area", s)
    _check_positive("weight", w)
    qs = 0.5 * rho * v * v * s
    cl = lift_coefficient(w, v, rho, s)
    return qs * drag_coefficient(cd0, k, cl)


def thrust_available_estimate(delta_t, drag):
    """Thrust available estimate in N: T = delta_T + D.

    The measured excess thrust (drag gap) plus the drag from the polar
    closes to the thrust the propulsion system must deliver at that
    speed. A negative result is unphysical (it would imply negative
    thrust) and raises ValueError. Worked: delta_T 25492.9 N plus D
    19667.8 N at 160 m/s gives 45160.8 N.
    """
    _check_nonnegative("drag", drag)
    total = delta_t + drag
    if total < 0:
        raise ValueError(
            "negative thrust available: delta_T %r below drag %r" % (delta_t, drag))
    return total


def weight_corrected_ps(ps, w_test, w_ref):
    """Specific excess power corrected to the reference weight, m/s.

    P_s_ref = P_s * W_test / W_ref at constant excess thrust: the
    weight-specific power of the lighter reference weight aircraft is
    higher than the measured value. First order form, valid while the
    induced drag change over the weight difference is small relative to
    the excess thrust. Worked: P_s 16.3155 m/s at W_test 250000 N
    corrects to 16.9953 m/s at W_ref 240000 N.
    """
    _check_positive("test weight", w_test)
    _check_positive("reference weight", w_ref)
    return ps * w_test / w_ref


def density_corrected_ps(ps, rho_test, rho_std=RHO0, lapse_exp=0.7):
    """Specific excess power corrected to the reference density, m/s.

    P_s_std = P_s * (rho_test / rho_std)^(lapse_exp - 0.5), the same
    simplified thrust lapse model the climb leaf applies at constant
    indicated airspeed: the thrust scales with sigma^lapse_exp and the
    true airspeed with sigma^-0.5. Documented simplification: the same
    throttle setting at test and reference, engine lapse only, drag
    polar unchanged. Worked: P_s 16.3155 m/s at rho_test / rho_std 0.9
    with the 0.7 lapse exponent gives 15.9753 m/s.
    """
    _check_positive("test density", rho_test)
    _check_positive("reference density", rho_std)
    if not 0.0 < lapse_exp <= 1.0:
        raise ValueError("thrust lapse exponent must be in (0, 1], got %r" % (lapse_exp,))
    return ps * (rho_test / rho_std) ** (lapse_exp - 0.5)


def ps_at_reference_conditions(ps, w_test, w_ref, rho_test,
                               rho_std=RHO0, lapse_exp=0.7):
    """Specific excess power corrected to reference weight and density.

    The weight factor times the density factor of weight_corrected_ps
    and density_corrected_ps. Worked: P_s 16.3155 m/s from W_test
    250000 N to W_ref 240000 N and rho_test / rho_std 0.9 gives
    16.6409 m/s.
    """
    wc = weight_corrected_ps(ps, w_test, w_ref)
    return density_corrected_ps(wc, rho_test, rho_std, lapse_exp)


def _assessment_region(n, window):
    """Interior sample range where the differentiated trace is clean.

    The acceleration at sample i uses the smoothed neighbours i - 1 and
    i + 1; both carry full windows when i - 1 and i + 1 lie between
    (window - 1) / 2 and n - 1 - (window - 1) / 2, that is i in
    [(window + 1) / 2, n - (window + 1) / 2). Returns (start, end) with
    end exclusive.
    """
    margin = (window + 1) // 2
    return margin, n - margin


def level_acceleration_summary(t_s, v_tas_ms, w_test_n, altitude_m=None,
                               rho=None, w_ref_n=None, rho_std=None,
                               s_m2=None, cd0=None, k=None, dh_dt=0.0,
                               window=5, g=G0):
    """One-pass reduction of an accelerated level flight run.

    Inputs: t_s the recorded sample times in s, v_tas_ms the true
    airspeed samples in m/s (convert equivalent airspeed with
    true_airspeed_from_eas first), w_test_n the test weight in N, and
    either rho (test day density, kg/m^3) or altitude_m (ISA density at
    that altitude). The drag polar is used when s_m2, cd0 and k are all
    given; w_ref_n and rho_std enable the reference condition
    corrections. dh_dt is the climb rate in m/s, a scalar broadcast to
    every sample or a list matching the trace (0 for a level run).

    Returns a dict with the smoothed trace, the acceleration, the
    specific excess power, the excess thrust, the per-sample
    acceleration verdict, the sustained_over_band verdict, the mean
    values over the assessment region where the smoothing window and
    the central difference stencil are both full, and, when requested,
    the drag, the thrust available estimate and the corrected mean
    specific excess power.

    Worked (contract test): t 0 to 20 s at 1 s steps, linear true
    airspeed 150 to 170 m/s, W 250000 N, S 122.6 m^2, cd0 0.02, k
    0.042, ISA density at 8000 m, window 5: mean acceleration
    1.0 m/s^2, mean P_s 16.3155 m/s, mean excess thrust 25492.9 N,
    sustained_over_band True, mean drag 19686.85 N, mean thrust
    available 45179.75 N.
    """
    _check_positive("test weight", w_test_n)
    if len(v_tas_ms) != len(t_s):
        raise ValueError(
            "airspeed and time lists must match in length, got %r and %r"
            % (len(v_tas_ms), len(t_s)))
    n = len(v_tas_ms)
    if n < 3:
        raise ValueError("at least three samples are required, got %r" % (n,))
    for i in range(n):
        _check_positive("true airspeed sample %d" % i, v_tas_ms[i])
    if rho is None:
        if altitude_m is None:
            raise ValueError(
                "test density required: give rho or altitude_m, got neither")
        rho = isa_conditions(altitude_m)[2]
    _check_positive("air density", rho)
    if isinstance(dh_dt, (int, float)):
        dh_dt_list = [float(dh_dt)] * n
    else:
        if len(dh_dt) != n:
            raise ValueError(
                "dh_dt list must match the trace length, got %r and %r"
                % (len(dh_dt), n))
        dh_dt_list = list(dh_dt)
    polar_args = (s_m2, cd0, k)
    if any(arg is None for arg in polar_args) and not all(arg is None for arg in polar_args):
        raise ValueError("polar requires all of s_m2, cd0 and k, or none")
    use_polar = s_m2 is not None
    if w_ref_n is not None:
        _check_positive("reference weight", w_ref_n)
    if rho_std is not None:
        _check_positive("reference density", rho_std)

    v_s = smooth_trace(v_tas_ms, window)
    acc = acceleration_from_trace(v_s, t_s)
    ps = [specific_excess_power(v_s[i], acc[i], g, dh_dt_list[i])
          for i in range(n)]
    delta_t = [excess_thrust_from_ps(ps[i], v_s[i], w_test_n) for i in range(n)]
    start, end = _assessment_region(n, window)
    if end <= start:
        raise ValueError(
            "trace too short for window %r: need more than %r samples"
            % (window, window + 1))
    mean_acc = sum(acc[start:end]) / (end - start)
    mean_ps = sum(ps[start:end]) / (end - start)
    mean_dt = sum(delta_t[start:end]) / (end - start)
    result = {
        "density_kgm3": rho,
        "window": window,
        "assessment_start": start,
        "assessment_end": end,
        "v_smoothed": v_s,
        "acceleration": acc,
        "specific_excess_power": ps,
        "excess_thrust": delta_t,
        "accelerating": [delta_t[i] > 0 for i in range(n)],
        "sustained_over_band": all(delta_t[i] > 0 for i in range(start, end)),
        "mean_acceleration": mean_acc,
        "mean_specific_excess_power": mean_ps,
        "mean_excess_thrust": mean_dt,
        "mean_ps_reference_weight": None,
        "mean_ps_reference_conditions": None,
    }
    if use_polar:
        drag = [drag_from_polar(v_s[i], rho, s_m2, w_test_n, cd0, k)
                for i in range(n)]
        t_avail = [thrust_available_estimate(delta_t[i], drag[i])
                   for i in range(n)]
        result["drag"] = drag
        result["thrust_available"] = t_avail
        result["mean_drag"] = sum(drag[start:end]) / (end - start)
        result["mean_thrust_available"] = sum(t_avail[start:end]) / (end - start)
    if w_ref_n is not None:
        result["mean_ps_reference_weight"] = (
            mean_ps * w_test_n / w_ref_n)
        if rho_std is not None:
            result["mean_ps_reference_conditions"] = (
                ps_at_reference_conditions(mean_ps, w_test_n, w_ref_n,
                                           rho, rho_std))
    return result
