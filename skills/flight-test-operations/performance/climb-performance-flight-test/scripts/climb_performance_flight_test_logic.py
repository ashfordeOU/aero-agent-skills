#!/usr/bin/env python3
"""Climb performance flight test logic (paraphrase, common flight-test methodology).

Simplified steady-climb model in the FAR-25 / CS-25 general performance
context (standards-map.yaml, far-25 and cs-25: reference-only). The leaf
covers the flight test side of climb performance: measuring the rate of
climb from pressure altitude change over a timed steady climb segment,
correcting the measured rate to the reference weight and the standard
day, converting the pressure altitude rate to the geometric rate, and
reducing the excess power model to the best rate of climb, the service
ceiling and absolute ceiling, the time to climb, and the climb gradient
checks against the certification requirement.

Units: speed in ft/s, rate of climb in ft/min, weight in lbf, wing area
in ft^2, density ratio sigma = rho/rho0 (rho0 = 0.0023769 slug/ft^3),
thrust in lbf, gradient in percent. Stdlib only.
"""

import math

RHO0 = 0.0023769          # sea level density, slug/ft^3
T_ISA0 = 288.15           # sea level ISA temperature, K
LAPSE_K_PER_M = 0.0065    # troposphere lapse rate, K/m
G0 = 9.80665              # standard gravity, m/s^2
R_GAS = 287.05287         # specific gas constant air, J/(kg K)
H_TROPO_M = 11000.0       # tropopause, m
MAX_H_FT = 65617.0        # model ceiling (20 km), ft
T_TROPO_K = 216.65        # tropopause temperature, K
ISA_EXP = G0 / (R_GAS * LAPSE_K_PER_M) - 1.0          # 4.25588
ISA_P_EXP = G0 / (R_GAS * LAPSE_K_PER_M)              # 5.25588
H_ISO_M = R_GAS * T_TROPO_K / G0                      # 6341.6 m

FT_PER_M = 1.0 / 0.3048


def _check_positive(name, value):
    if value <= 0:
        raise ValueError("%s must be > 0, got %r" % (name, value))


def isa_temperature_k(h_ft):
    """ISA temperature in K at geopotential altitude h_ft (0 to 65617 ft)."""
    if h_ft < 0 or h_ft > MAX_H_FT:
        raise ValueError("altitude must be within 0 to 65617 ft, got %r" % (h_ft,))
    h_m = h_ft * 0.3048
    if h_m <= H_TROPO_M:
        return T_ISA0 - LAPSE_K_PER_M * h_m
    return T_TROPO_K


def isa_pressure_ratio(h_ft):
    """ISA pressure ratio delta = P/P0 at geopotential altitude h_ft."""
    if h_ft < 0 or h_ft > MAX_H_FT:
        raise ValueError("altitude must be within 0 to 65617 ft, got %r" % (h_ft,))
    h_m = h_ft * 0.3048
    if h_m <= H_TROPO_M:
        return (1.0 - LAPSE_K_PER_M * h_m / T_ISA0) ** ISA_P_EXP
    delta_t = (1.0 - LAPSE_K_PER_M * H_TROPO_M / T_ISA0) ** ISA_P_EXP
    return delta_t * math.exp(-(h_m - H_TROPO_M) / H_ISO_M)


def isa_density_ratio(h_ft):
    """ISA density ratio sigma = rho/rho0 at geopotential altitude h_ft.

    Worked: 0 ft gives 1.0, 10000 ft gives about 0.73846, and the
    tropopause at 36089.24 ft gives about 0.29707.
    """
    if h_ft < 0 or h_ft > MAX_H_FT:
        raise ValueError("altitude must be within 0 to 65617 ft, got %r" % (h_ft,))
    h_m = h_ft * 0.3048
    if h_m <= H_TROPO_M:
        return (1.0 - LAPSE_K_PER_M * h_m / T_ISA0) ** ISA_EXP
    sigma_t = (1.0 - LAPSE_K_PER_M * H_TROPO_M / T_ISA0) ** ISA_EXP
    return sigma_t * math.exp(-(h_m - H_TROPO_M) / H_ISO_M)


def density_altitude_ft(pressure_alt_ft, oat_deg_c):
    """Density altitude in ft for a measured pressure altitude and OAT.

    sigma = (P/P0) * (T0/T) with P/P0 the ISA pressure ratio at the
    pressure altitude; the density altitude is the altitude where the
    ISA density ratio equals sigma. Worked: at 10000 ft pressure
    altitude with OAT 15 C (ISA day) the density altitude equals the
    pressure altitude.
    """
    if pressure_alt_ft < 0 or pressure_alt_ft > MAX_H_FT:
        raise ValueError(
            "pressure altitude must be within 0 to 65617 ft, got %r" % (pressure_alt_ft,)
        )
    t_amb = oat_deg_c + 273.15
    if t_amb <= 0:
        raise ValueError("outside air temperature must be above absolute zero")
    sigma = isa_pressure_ratio(pressure_alt_ft) * (T_ISA0 / t_amb)
    lo, hi = 0.0, MAX_H_FT
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if isa_density_ratio(mid) > sigma:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def rate_of_climb_from_pressure_altitude(h1_ft, h2_ft, t_s):
    """Measured rate of climb in ft/min from a timed climb segment.

    ROC = (h2 - h1) / t * 60, pressure altitude change over the
    segment time. Raises ValueError on a non-positive time or a
    non-climbing segment.
    """
    _check_positive("segment time", t_s)
    if h2_ft <= h1_ft:
        raise ValueError(
            "climb segment must gain altitude, h2 %r must exceed h1 %r" % (h2_ft, h1_ft)
        )
    return (h2_ft - h1_ft) / t_s * 60.0


def geometric_roc_from_pressure_roc(roc_p_fpm, oat_deg_c, pressure_alt_ft):
    """Geometric rate of climb from the pressure altitude rate.

    h_geo_dot = h_p_dot * T_amb / T_ISA(pressure altitude): at the same
    pressure, the geometric altitude increment exceeds the pressure
    altitude increment by the ambient over ISA temperature ratio. Raises
    ValueError on a non-positive rate or an out of range altitude.
    """
    _check_positive("pressure rate of climb", roc_p_fpm)
    if pressure_alt_ft < 0 or pressure_alt_ft > MAX_H_FT:
        raise ValueError(
            "pressure altitude must be within 0 to 65617 ft, got %r" % (pressure_alt_ft,)
        )
    t_amb = oat_deg_c + 273.15
    if t_amb <= 0:
        raise ValueError("outside air temperature must be above absolute zero")
    return roc_p_fpm * (t_amb / isa_temperature_k(pressure_alt_ft))


def lift_coefficient(w_lb, v_ftps, s_ft2, sigma):
    """Lift coefficient CL = W / (0.5 * rho0 * sigma * V^2 * S)."""
    for name, value in (("weight", w_lb), ("airspeed", v_ftps),
                        ("wing area", s_ft2), ("density ratio", sigma)):
        _check_positive(name, value)
    return w_lb / (0.5 * RHO0 * sigma * v_ftps * v_ftps * s_ft2)


def drag_coefficient(cd0, k, cl):
    """Drag coefficient CD = cd0 + k * CL^2 (parabolic drag polar)."""
    if cd0 < 0 or k < 0:
        raise ValueError("drag polar coefficients must be >= 0, got cd0 %r k %r" % (cd0, k))
    if cl < 0:
        raise ValueError("lift coefficient must be >= 0, got %r" % (cl,))
    return cd0 + k * cl * cl


def drag_force(w_lb, v_ftps, s_ft2, sigma, cd0, k):
    """Drag force in lbf from the parabolic polar at the test density."""
    _check_positive("weight", w_lb)
    _check_positive("airspeed", v_ftps)
    _check_positive("wing area", s_ft2)
    _check_positive("density ratio", sigma)
    if cd0 < 0 or k < 0:
        raise ValueError("drag polar coefficients must be >= 0, got cd0 %r k %r" % (cd0, k))
    qs = 0.5 * RHO0 * sigma * v_ftps * v_ftps * s_ft2
    cl = w_lb / qs
    return qs * (cd0 + k * cl * cl)


def thrust_available(t0_lbf, sigma, lapse_exp=0.7):
    """Installed thrust in lbf at density ratio sigma.

    T = T0 * sigma^lapse_exp, the common jet thrust lapse model with a
    default exponent of 0.7.
    """
    _check_positive("sea level static thrust", t0_lbf)
    _check_positive("density ratio", sigma)
    if not 0.0 < lapse_exp <= 1.0:
        raise ValueError("thrust lapse exponent must be in (0, 1], got %r" % (lapse_exp,))
    return t0_lbf * sigma ** lapse_exp


def excess_thrust(t_lbf, d_lbf):
    """Excess thrust in lbf, T - D."""
    if d_lbf < 0:
        raise ValueError("drag must be >= 0, got %r" % (d_lbf,))
    if t_lbf < 0:
        raise ValueError("thrust must be >= 0, got %r" % (t_lbf,))
    return t_lbf - d_lbf


def rate_of_climb_fpm(t_lbf, d_lbf, v_ftps, w_lb):
    """Rate of climb in ft/min from excess power.

    ROC = (T - D) * V / W, converted to ft/min. Raises ValueError on a
    negative excess thrust (no climb capability at that condition).
    """
    if t_lbf - d_lbf < 0:
        raise ValueError("no climb capability: thrust %r below drag %r" % (t_lbf, d_lbf))
    _check_positive("airspeed", v_ftps)
    _check_positive("weight", w_lb)
    return (t_lbf - d_lbf) * v_ftps / w_lb * 60.0


def climb_gradient_pct(t_lbf, d_lbf, w_lb):
    """Climb gradient in percent, 100 * (T - D) / W (small angle)."""
    if t_lbf - d_lbf < 0:
        raise ValueError("no climb capability: thrust %r below drag %r" % (t_lbf, d_lbf))
    _check_positive("weight", w_lb)
    return (t_lbf - d_lbf) / w_lb * 100.0


def gradient_from_roc(roc_fpm, v_ftps):
    """Climb gradient in percent from the rate of climb and true airspeed.

    G = (ROC / 60) / V * 100, the small angle form sin(gamma) ~= ROC / V.
    """
    _check_positive("rate of climb", roc_fpm)
    _check_positive("true airspeed", v_ftps)
    return roc_fpm / 60.0 / v_ftps * 100.0


def gradient_margin_pct(gradient_pct, required_pct):
    """Gradient margin in percent, measured minus required."""
    if required_pct < 0:
        raise ValueError("required gradient must be >= 0, got %r" % (required_pct,))
    return gradient_pct - required_pct


def _raw_best_roc(w_lb, s_ft2, sigma, cd0, k, t_lbf, v_min_ftps, v_max_ftps, n_pts):
    """Maximum rate of climb over the speed band, ft/min (may be negative).

    Private helper for the ceiling search: at altitudes above the
    capability limit every speed gives a negative rate of climb, and the
    bisection needs that signed value.
    """
    best_roc, best_v = None, None
    for i in range(n_pts):
        v = v_min_ftps + (v_max_ftps - v_min_ftps) * i / (n_pts - 1)
        d = drag_force(w_lb, v, s_ft2, sigma, cd0, k)
        roc = (t_lbf - d) * v / w_lb * 60.0
        if best_roc is None or roc > best_roc:
            best_roc, best_v = roc, v
    return best_roc, best_v


def best_rate_of_climb_fpm(w_lb, s_ft2, sigma, cd0, k, t_lbf,
                           v_min_ftps=200.0, v_max_ftps=1000.0, n_pts=400):
    """Best rate of climb in ft/min and the speed that achieves it.

    Scans the true airspeed band at the given density ratio and returns
    (roc_max_fpm, v_best_ftps). Raises ValueError when no speed in the
    band gives a positive rate of climb.
    """
    _check_positive("weight", w_lb)
    _check_positive("wing area", s_ft2)
    _check_positive("density ratio", sigma)
    _check_positive("thrust", t_lbf)
    if cd0 < 0 or k < 0:
        raise ValueError("drag polar coefficients must be >= 0, got cd0 %r k %r" % (cd0, k))
    if v_min_ftps <= 0 or v_max_ftps <= v_min_ftps or n_pts < 2:
        raise ValueError(
            "speed band invalid: v_min %r v_max %r n_pts %r" % (v_min_ftps, v_max_ftps, n_pts)
        )
    best_roc, best_v = _raw_best_roc(w_lb, s_ft2, sigma, cd0, k, t_lbf,
                                     v_min_ftps, v_max_ftps, n_pts)
    if best_roc is None or best_roc <= 0:
        raise ValueError("no positive rate of climb in the speed band at sigma %r" % (sigma,))
    return best_roc, best_v


def _best_roc_at(w_lb, s_ft2, cd0, k, t0_lbf, lapse_exp, h_ft, v_min, v_max, n_pts):
    sigma = isa_density_ratio(h_ft)
    t = thrust_available(t0_lbf, sigma, lapse_exp)
    return _raw_best_roc(w_lb, s_ft2, sigma, cd0, k, t, v_min, v_max, n_pts)[0]


def service_ceiling_ft(w_lb, s_ft2, cd0, k, t0_lbf, lapse_exp=0.7,
                       roc_target_fpm=100.0, v_min=200.0, v_max=1000.0, n_pts=400):
    """Service ceiling in ft: altitude where the best rate of climb
    decays to roc_target_fpm (100 ft/min is the common jet threshold).

    Raises ValueError when the aircraft cannot climb at sea level or
    still climbs at the 65617 ft ISA model limit.
    """
    _check_positive("weight", w_lb)
    _check_positive("wing area", s_ft2)
    _check_positive("sea level static thrust", t0_lbf)
    if roc_target_fpm < 0:
        raise ValueError("target rate of climb must be >= 0, got %r" % (roc_target_fpm,))
    roc0 = _best_roc_at(w_lb, s_ft2, cd0, k, t0_lbf, lapse_exp, 0.0, v_min, v_max, n_pts)
    if roc0 <= roc_target_fpm:
        raise ValueError("aircraft does not climb above the target at sea level: %r" % (roc0,))
    roc_hi = _best_roc_at(w_lb, s_ft2, cd0, k, t0_lbf, lapse_exp, MAX_H_FT, v_min, v_max, n_pts)
    if roc_hi > roc_target_fpm:
        raise ValueError("aircraft still climbs above the target at the model limit: %r" % (roc_hi,))
    lo, hi = 0.0, MAX_H_FT
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if _best_roc_at(w_lb, s_ft2, cd0, k, t0_lbf, lapse_exp, mid, v_min, v_max, n_pts) > roc_target_fpm:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def absolute_ceiling_ft(w_lb, s_ft2, cd0, k, t0_lbf, lapse_exp=0.7,
                        v_min=200.0, v_max=1000.0, n_pts=400):
    """Absolute ceiling in ft: altitude where the best rate of climb
    decays to zero. The service ceiling is below the absolute ceiling.
    """
    return service_ceiling_ft(w_lb, s_ft2, cd0, k, t0_lbf, lapse_exp,
                              0.0, v_min, v_max, n_pts)


def time_to_climb_min(h0_ft, h1_ft, w_lb, s_ft2, cd0, k, t0_lbf,
                      lapse_exp=0.7, step_ft=500.0, v_min=200.0, v_max=1000.0, n_pts=400):
    """Time to climb in minutes from h0 to h1 at the best rate schedule.

    Trapezoid integration of dt = dh / ROC(h). Raises ValueError when
    the band has no climb capability or the segment is degenerate.
    """
    if h0_ft < 0 or h1_ft < 0:
        raise ValueError("altitudes must be >= 0, got h0 %r h1 %r" % (h0_ft, h1_ft))
    if h1_ft <= h0_ft:
        raise ValueError("climb segment must gain altitude, h1 %r must exceed h0 %r" % (h1_ft, h0_ft))
    if h1_ft > MAX_H_FT:
        raise ValueError("climb segment above the ISA model limit: %r" % (h1_ft,))
    if step_ft <= 0:
        raise ValueError("integration step must be > 0, got %r" % (step_ft,))
    total_min = 0.0
    h = h0_ft
    while h < h1_ft:
        h_next = min(h + step_ft, h1_ft)
        roc0 = _best_roc_at(w_lb, s_ft2, cd0, k, t0_lbf, lapse_exp, h, v_min, v_max, n_pts)
        roc1 = _best_roc_at(w_lb, s_ft2, cd0, k, t0_lbf, lapse_exp, h_next, v_min, v_max, n_pts)
        if roc0 <= 0.0 or roc1 <= 0.0:
            raise ValueError("no climb capability between %r and %r ft" % (h, h_next))
        total_min += 2.0 * (h_next - h) / (roc0 + roc1)
        h = h_next
    return total_min


def weight_corrected_roc(roc_meas_fpm, w_test_lb, w_ref_lb):
    """Rate of climb corrected to the reference weight, ft/min.

    ROC_ref = ROC_meas * w_test / w_ref: the specific excess power
    scaling at constant true airspeed, the first order form valid when
    the drag is a small fraction of the thrust (typical climb).
    """
    _check_positive("measured rate of climb", roc_meas_fpm)
    _check_positive("test weight", w_test_lb)
    _check_positive("reference weight", w_ref_lb)
    return roc_meas_fpm * w_test_lb / w_ref_lb


def density_corrected_roc(roc_meas_fpm, sigma_test, sigma_std=1.0, lapse_exp=0.7):
    """Rate of climb corrected to the standard density day, ft/min.

    ROC_std = ROC_meas * (sigma_test / sigma_std)^(lapse_exp - 0.5):
    at constant indicated airspeed the thrust scales with sigma^lapse_exp
    and the true airspeed with sigma^-0.5, so the excess-power rate
    scales with sigma^(lapse_exp - 0.5) in the thrust dominated limit.
    """
    _check_positive("measured rate of climb", roc_meas_fpm)
    _check_positive("test density ratio", sigma_test)
    _check_positive("standard density ratio", sigma_std)
    if not 0.0 < lapse_exp <= 1.0:
        raise ValueError("thrust lapse exponent must be in (0, 1], got %r" % (lapse_exp,))
    return roc_meas_fpm * (sigma_test / sigma_std) ** (lapse_exp - 0.5)


def corrected_rate_of_climb(roc_meas_fpm, w_test_lb, w_ref_lb,
                            sigma_test, sigma_std=1.0, lapse_exp=0.7):
    """Rate of climb corrected to the reference weight and the standard
    day, ft/min: the weight factor times the density factor.
    """
    return weight_corrected_roc(roc_meas_fpm, w_test_lb, w_ref_lb) * (
        sigma_test / sigma_std) ** (lapse_exp - 0.5)
