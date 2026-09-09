#!/usr/bin/env python3
"""Reciprocating high-speed compression-ignition aircraft powerplant
single-point dual (Sabathe / limited-pressure / mixed heat-addition) cycle.

Pure Python 3, stdlib only, SI units throughout. Implements the standard
air-standard dual cycle (constant-volume then constant-pressure heat
addition) and the four-stroke brake-power bookkeeping used for high-speed
direct-injection compression-ignition aircraft reciprocating engine
performance:

  - air-standard dual thermal efficiency:
    eta = 1 - (1/r^(gamma-1)) * ((alpha*rho^gamma - 1)/((alpha - 1) +
    gamma*alpha*(rho - 1)))
  - isentropic compression temperature ratio: T2/T1 = r^(gamma-1)
  - five-state temperature bookkeeping: T2 = T1*r^(gamma-1), T3 = T2*alpha,
    T4 = T3*rho, T5 = T1*alpha*rho^gamma
  - mixed heat addition: q23 = (cp/gamma)*T2*(alpha-1) (constant volume),
    q34 = cp*T2*alpha*(rho-1) (constant pressure), q_in = q23 + q34
  - constant-volume heat rejection: q_out = (cp/gamma)*(T5-T1)
  - ideal-cycle mean effective pressure: MEP = eta*q_in/(v1 - v2)
  - four-stroke indicated power: P_i = IMEP * V_d * (rpm/60)/2
  - brake power: P_b = P_i * eta_m
  - brake specific fuel consumption: BSFC = m_dot_fuel * 3600 * 1000 / P_b
  - indicated and brake thermal efficiencies on the Jet-A lower heating value
  - volumetric fuel flow from mass flow and fuel density
  - a reference-only compression-ignition band verdict that reports the
    point's position and never enforces it

The alpha -> 1 limit recovers the air-standard Diesel closed form owned by
propulsion/reciprocating/diesel-cycle and the rho -> 1 limit recovers the
air-standard Otto closed form owned by propulsion/reciprocating/
piston-engine-cycle; both limits appear in this module's contract test only
as bounds, never as a computed operating mode this leaf claims.

All functions validate their inputs and raise ValueError on non-finite or
physically invalid values.
"""

import math

# Module constants (SI unless noted).
GAMMA_AIR = 1.4
CP_AIR = 1005.0
T1_REF_K = 288.15
P1_REF_PA = 150000.0
R_AIR_J_PER_KG_K = 287.0
HOUR_S = 3600.0
KG_PER_LB = 0.45359237
W_PER_HP = 745.6998715822702
M3_PER_L = 1.0e-3
L_PER_M3 = 1.0e3
US_GAL_PER_M3 = 264.17205235814845
KG_PER_KWH_PER_LB_PER_HP_HR = KG_PER_LB / (W_PER_HP * 1.0e-3)
JET_A_LHV_J_PER_KG = 43.2e6
JET_A_DENSITY_KG_PER_M3 = 800.0

# Reference-only compression-ignition bands, never enforced (the same
# published band class as the diesel sibling's worked example).
BSFC_BAND_LB_PER_HP_HR = (0.35, 0.42)
BSFC_BAND_KG_PER_KWH = (
    BSFC_BAND_LB_PER_HP_HR[0] * KG_PER_KWH_PER_LB_PER_HP_HR,
    BSFC_BAND_LB_PER_HP_HR[1] * KG_PER_KWH_PER_LB_PER_HP_HR,
)
ETA_B_BAND = (
    3.6e6 / (0.42 * KG_PER_KWH_PER_LB_PER_HP_HR * JET_A_LHV_J_PER_KG),
    3.6e6 / (0.36 * KG_PER_KWH_PER_LB_PER_HP_HR * JET_A_LHV_J_PER_KG),
)


def _require_finite(value, name):
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))


def _require_positive(value, name):
    _require_finite(value, name)
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (name, value))


def _require_mechanical_efficiency(value):
    _require_finite(value, "mechanical_efficiency")
    if not (0.0 < value <= 1.0):
        raise ValueError(
            "mechanical_efficiency must be in (0, 1], got %r" % (value,))


def _require_compression_ratio(compression_ratio):
    _require_finite(compression_ratio, "compression_ratio")
    if compression_ratio <= 1.0:
        raise ValueError(
            "compression_ratio must be > 1, got %r" % (compression_ratio,))


def _require_gamma(gamma):
    _require_finite(gamma, "gamma")
    if gamma <= 1.0:
        raise ValueError("gamma must be > 1, got %r" % (gamma,))


def _require_pressure_ratio(pressure_ratio):
    _require_finite(pressure_ratio, "pressure_ratio")
    if pressure_ratio < 1.0:
        raise ValueError(
            "pressure_ratio must be >= 1, got %r" % (pressure_ratio,))


def _require_cutoff_ratio(cutoff_ratio):
    _require_finite(cutoff_ratio, "cutoff_ratio")
    if cutoff_ratio <= 1.0:
        raise ValueError("cutoff_ratio must be > 1, got %r" % (cutoff_ratio,))


def dual_efficiency(compression_ratio, pressure_ratio, cutoff_ratio,
                     gamma=GAMMA_AIR):
    """Air-standard dual (Sabathe / limited-pressure) cycle thermal
    efficiency, mixed constant-volume-then-constant-pressure heat addition:

    eta = 1 - (1/r^(gamma-1)) * ((alpha*rho^gamma - 1)/((alpha - 1) +
    gamma*alpha*(rho - 1)))

    compression_ratio: r, the volumetric compression ratio (r > 1).
    pressure_ratio: alpha = P3/P2, the pressure ratio of the
    constant-volume heat-addition phase (alpha >= 1).
    cutoff_ratio: rho = V4/V3 = T4/T3, the cutoff ratio of the
    constant-pressure heat-addition phase (1 < rho <= r; heat addition
    must end before bottom dead center).
    gamma: specific-heat ratio (gamma > 1), defaults to air-standard 1.4.
    """
    _require_compression_ratio(compression_ratio)
    _require_gamma(gamma)
    _require_pressure_ratio(pressure_ratio)
    _require_cutoff_ratio(cutoff_ratio)
    if cutoff_ratio > compression_ratio:
        raise ValueError(
            "cutoff_ratio must be <= compression_ratio, got rho=%r > r=%r" % (
                cutoff_ratio, compression_ratio))
    temperature_ratio = compression_ratio ** (gamma - 1.0)
    numerator = pressure_ratio * cutoff_ratio ** gamma - 1.0
    denominator = (pressure_ratio - 1.0) + gamma * pressure_ratio * (
        cutoff_ratio - 1.0)
    return 1.0 - (1.0 / temperature_ratio) * (numerator / denominator)


def isentropic_temperature_ratio(compression_ratio, gamma=GAMMA_AIR):
    """Isentropic compression temperature ratio, T2/T1 = r^(gamma-1)."""
    _require_compression_ratio(compression_ratio)
    _require_gamma(gamma)
    return compression_ratio ** (gamma - 1.0)


def compression_temperature(t1_k, compression_ratio, gamma=GAMMA_AIR):
    """Compression temperature T2 (K) = T1 * r^(gamma-1)."""
    _require_positive(t1_k, "t1_k")
    ratio = isentropic_temperature_ratio(compression_ratio, gamma)
    return t1_k * ratio


def cv_phase_temperature(t2_k, pressure_ratio):
    """Constant-volume phase temperature T3 (K) = T2 * alpha (heat
    addition 2 to 3)."""
    _require_positive(t2_k, "t2_k")
    _require_pressure_ratio(pressure_ratio)
    return t2_k * pressure_ratio


def cp_phase_temperature(t3_k, cutoff_ratio):
    """Constant-pressure phase temperature T4 (K) = T3 * rho (heat
    addition 3 to 4)."""
    _require_positive(t3_k, "t3_k")
    _require_cutoff_ratio(cutoff_ratio)
    return t3_k * cutoff_ratio


def expansion_temperature(t1_k, pressure_ratio, cutoff_ratio,
                           gamma=GAMMA_AIR):
    """Expansion temperature T5 (K) = T1 * alpha * rho^gamma (isentropic
    expansion 4 to 5 to V5 = V1, closed form)."""
    _require_positive(t1_k, "t1_k")
    _require_pressure_ratio(pressure_ratio)
    _require_cutoff_ratio(cutoff_ratio)
    _require_gamma(gamma)
    return t1_k * pressure_ratio * cutoff_ratio ** gamma


def cycle_state_temperatures(t1_k, compression_ratio, pressure_ratio,
                              cutoff_ratio, gamma=GAMMA_AIR):
    """Five-state temperature bookkeeping dict {t1_k, t2_k, t3_k, t4_k,
    t5_k}."""
    _require_positive(t1_k, "t1_k")
    _require_compression_ratio(compression_ratio)
    _require_gamma(gamma)
    _require_pressure_ratio(pressure_ratio)
    _require_cutoff_ratio(cutoff_ratio)
    if cutoff_ratio > compression_ratio:
        raise ValueError(
            "cutoff_ratio must be <= compression_ratio, got rho=%r > r=%r" % (
                cutoff_ratio, compression_ratio))
    t2_k = compression_temperature(t1_k, compression_ratio, gamma)
    t3_k = cv_phase_temperature(t2_k, pressure_ratio)
    t4_k = cp_phase_temperature(t3_k, cutoff_ratio)
    t5_k = expansion_temperature(t1_k, pressure_ratio, cutoff_ratio, gamma)
    return {"t1_k": t1_k, "t2_k": t2_k, "t3_k": t3_k, "t4_k": t4_k,
            "t5_k": t5_k}


def cv_heat_addition_j_per_kg(t2_k, pressure_ratio, gamma=GAMMA_AIR,
                               cp_j_per_kg_k=CP_AIR):
    """Constant-volume phase heat addition per kg of air,
    q23 = (cp/gamma) * T2 * (alpha - 1)."""
    _require_positive(t2_k, "t2_k")
    _require_pressure_ratio(pressure_ratio)
    _require_gamma(gamma)
    _require_positive(cp_j_per_kg_k, "cp_j_per_kg_k")
    return (cp_j_per_kg_k / gamma) * t2_k * (pressure_ratio - 1.0)


def cp_heat_addition_j_per_kg(t2_k, pressure_ratio, cutoff_ratio,
                               cp_j_per_kg_k=CP_AIR):
    """Constant-pressure phase heat addition per kg of air,
    q34 = cp * T2 * alpha * (rho - 1)."""
    _require_positive(t2_k, "t2_k")
    _require_pressure_ratio(pressure_ratio)
    _require_cutoff_ratio(cutoff_ratio)
    _require_positive(cp_j_per_kg_k, "cp_j_per_kg_k")
    return cp_j_per_kg_k * t2_k * pressure_ratio * (cutoff_ratio - 1.0)


def heat_addition_j_per_kg(t2_k, pressure_ratio, cutoff_ratio,
                            gamma=GAMMA_AIR, cp_j_per_kg_k=CP_AIR):
    """Total mixed heat addition per kg of air, q_in = q23 + q34."""
    q23 = cv_heat_addition_j_per_kg(t2_k, pressure_ratio, gamma,
                                     cp_j_per_kg_k)
    q34 = cp_heat_addition_j_per_kg(t2_k, pressure_ratio, cutoff_ratio,
                                     cp_j_per_kg_k)
    return q23 + q34


def heat_rejection_j_per_kg(t1_k, t5_k, gamma=GAMMA_AIR,
                             cp_j_per_kg_k=CP_AIR):
    """Constant-volume heat rejection 5 to 1 per kg of air,
    q_out = (cp/gamma) * (T5 - T1)."""
    _require_positive(t1_k, "t1_k")
    _require_positive(t5_k, "t5_k")
    _require_gamma(gamma)
    _require_positive(cp_j_per_kg_k, "cp_j_per_kg_k")
    if t5_k <= t1_k:
        raise ValueError(
            "t5_k must be > t1_k, got t5_k=%r <= t1_k=%r" % (t5_k, t1_k))
    return (cp_j_per_kg_k / gamma) * (t5_k - t1_k)


def mean_effective_pressure(t1_k, p1_pa, compression_ratio, pressure_ratio,
                             cutoff_ratio, gamma=GAMMA_AIR,
                             cp_j_per_kg_k=CP_AIR,
                             r_air_j_per_kg_k=R_AIR_J_PER_KG_K):
    """Ideal-cycle mean effective pressure, MEP = eta * q_in/(v1 - v2), in
    Pa. Exactly linear in the state-1 pressure p1_pa."""
    _require_positive(t1_k, "t1_k")
    _require_positive(p1_pa, "p1_pa")
    _require_positive(cp_j_per_kg_k, "cp_j_per_kg_k")
    _require_positive(r_air_j_per_kg_k, "r_air_j_per_kg_k")
    eta = dual_efficiency(compression_ratio, pressure_ratio, cutoff_ratio,
                           gamma)
    t2_k = compression_temperature(t1_k, compression_ratio, gamma)
    q_in = heat_addition_j_per_kg(t2_k, pressure_ratio, cutoff_ratio, gamma,
                                   cp_j_per_kg_k)
    v1 = r_air_j_per_kg_k * t1_k / p1_pa
    v2 = v1 / compression_ratio
    return eta * q_in / (v1 - v2)


def indicated_power(imep_pa, displacement_m3, rpm):
    """Four-stroke indicated power, P_i = IMEP * V_d * (rpm/60)/2.

    One power stroke occurs per two crankshaft revolutions, so the
    revolution rate halves in the bookkeeping.
    """
    _require_positive(imep_pa, "imep_pa")
    _require_positive(displacement_m3, "displacement_m3")
    _require_positive(rpm, "rpm")
    return imep_pa * displacement_m3 * (rpm / 60.0) / 2.0


def brake_power(indicated_power_w, mechanical_efficiency):
    """Brake power, P_b = P_i * eta_m; eta_m = 1.0 returns P_i exactly."""
    _require_positive(indicated_power_w, "indicated_power_w")
    _require_mechanical_efficiency(mechanical_efficiency)
    return indicated_power_w * mechanical_efficiency


def brake_specific_fuel_consumption(fuel_flow_kg_per_s, brake_power_w):
    """Brake specific fuel consumption, BSFC = m_dot_fuel*3600*1000/P_b, in
    kg/(kW h) (family shaft-power convention)."""
    _require_positive(fuel_flow_kg_per_s, "fuel_flow_kg_per_s")
    _require_positive(brake_power_w, "brake_power_w")
    return fuel_flow_kg_per_s * HOUR_S * 1000.0 / brake_power_w


def bsfc_lb_per_hp_hr(bsfc_kg_per_kwh):
    """Convert BSFC from kg/(kW h) to lb/(hp h) through the exact unit
    bridge KG_PER_KWH_PER_LB_PER_HP_HR."""
    _require_positive(bsfc_kg_per_kwh, "bsfc_kg_per_kwh")
    return bsfc_kg_per_kwh / KG_PER_KWH_PER_LB_PER_HP_HR


def fuel_flow_from_bsfc(bsfc_kg_per_kwh, brake_power_w):
    """Fuel mass flow from BSFC and brake power, the exact inverse of
    brake_specific_fuel_consumption."""
    _require_positive(bsfc_kg_per_kwh, "bsfc_kg_per_kwh")
    _require_positive(brake_power_w, "brake_power_w")
    return bsfc_kg_per_kwh * brake_power_w / (HOUR_S * 1000.0)


def indicated_thermal_efficiency(indicated_power_w, fuel_flow_kg_per_s,
                                  lhv_j_per_kg=JET_A_LHV_J_PER_KG):
    """Indicated thermal efficiency on the Jet-A lower heating value,
    eta_i = P_i / (m_dot_fuel * LHV)."""
    _require_positive(indicated_power_w, "indicated_power_w")
    _require_positive(fuel_flow_kg_per_s, "fuel_flow_kg_per_s")
    _require_positive(lhv_j_per_kg, "lhv_j_per_kg")
    return indicated_power_w / (fuel_flow_kg_per_s * lhv_j_per_kg)


def brake_thermal_efficiency(brake_power_w, fuel_flow_kg_per_s,
                              lhv_j_per_kg=JET_A_LHV_J_PER_KG):
    """Brake thermal efficiency on the Jet-A lower heating value,
    eta_b = P_b / (m_dot_fuel * LHV) = eta_m * eta_i."""
    _require_positive(brake_power_w, "brake_power_w")
    _require_positive(fuel_flow_kg_per_s, "fuel_flow_kg_per_s")
    _require_positive(lhv_j_per_kg, "lhv_j_per_kg")
    return brake_power_w / (fuel_flow_kg_per_s * lhv_j_per_kg)


def volumetric_fuel_flow(fuel_flow_kg_per_s,
                          fuel_density_kg_per_m3=JET_A_DENSITY_KG_PER_M3):
    """Volumetric fuel flow, V_dot = m_dot_fuel / rho_fuel, in m3/s."""
    _require_positive(fuel_flow_kg_per_s, "fuel_flow_kg_per_s")
    _require_positive(fuel_density_kg_per_m3, "fuel_density_kg_per_m3")
    return fuel_flow_kg_per_s / fuel_density_kg_per_m3


def _band_position(value, band):
    lo, hi = band
    if value < lo:
        return "below"
    if value > hi:
        return "above"
    return "inside"


def ci_band_verdict(brake_thermal_eff, bsfc_lb_per_hp_hr_value):
    """Reference-only compression-ignition band verdict.

    Reports where the point's brake thermal efficiency and BSFC (lb/(hp h))
    sit against the published compression-ignition bands (ETA_B_BAND,
    BSFC_BAND_LB_PER_HP_HR). enforced is always False: an out-of-band point
    is not an error and this function never raises for one, only for
    non-finite or non-positive inputs.
    """
    _require_positive(brake_thermal_eff, "brake_thermal_eff")
    _require_positive(bsfc_lb_per_hp_hr_value, "bsfc_lb_per_hp_hr_value")
    return {
        "eta_b_band": ETA_B_BAND,
        "eta_b_position": _band_position(brake_thermal_eff, ETA_B_BAND),
        "bsfc_band_lb_per_hp_hr": BSFC_BAND_LB_PER_HP_HR,
        "bsfc_position": _band_position(
            bsfc_lb_per_hp_hr_value, BSFC_BAND_LB_PER_HP_HR),
        "enforced": False,
    }


def dual_cycle(compression_ratio, pressure_ratio, cutoff_ratio, imep_pa,
               displacement_m3, rpm, mechanical_efficiency,
               fuel_flow_kg_per_s, t1_k=T1_REF_K, p1_pa=P1_REF_PA,
               gamma=GAMMA_AIR, cp_j_per_kg_k=CP_AIR,
               lhv_j_per_kg=JET_A_LHV_J_PER_KG,
               fuel_density_kg_per_m3=JET_A_DENSITY_KG_PER_M3,
               r_air_j_per_kg_k=R_AIR_J_PER_KG_K):
    """Single operating point of a high-speed compression-ignition
    reciprocating aircraft powerplant: ideal dual-cycle efficiency, state
    temperatures, both heat additions and the heat rejection, the
    ideal-cycle mean effective pressure, indicated and brake power, BSFC in
    both reporting units, thermal efficiencies, volumetric fuel flow and the
    reference-only compression-ignition band verdict, in one call.
    ValueErrors propagate from the chained functions below.
    """
    eta_dual = dual_efficiency(compression_ratio, pressure_ratio,
                                cutoff_ratio, gamma)
    temperature_ratio = isentropic_temperature_ratio(compression_ratio,
                                                       gamma)
    states = cycle_state_temperatures(t1_k, compression_ratio,
                                       pressure_ratio, cutoff_ratio, gamma)
    q23 = cv_heat_addition_j_per_kg(states["t2_k"], pressure_ratio, gamma,
                                     cp_j_per_kg_k)
    q34 = cp_heat_addition_j_per_kg(states["t2_k"], pressure_ratio,
                                     cutoff_ratio, cp_j_per_kg_k)
    q_in = q23 + q34
    q_out = heat_rejection_j_per_kg(t1_k, states["t5_k"], gamma,
                                     cp_j_per_kg_k)
    mep_pa = mean_effective_pressure(t1_k, p1_pa, compression_ratio,
                                      pressure_ratio, cutoff_ratio, gamma,
                                      cp_j_per_kg_k, r_air_j_per_kg_k)
    p_i = indicated_power(imep_pa, displacement_m3, rpm)
    p_b = brake_power(p_i, mechanical_efficiency)
    bsfc_kg_per_kwh = brake_specific_fuel_consumption(fuel_flow_kg_per_s, p_b)
    bsfc_lb_hp_hr = bsfc_lb_per_hp_hr(bsfc_kg_per_kwh)
    eta_i = indicated_thermal_efficiency(p_i, fuel_flow_kg_per_s,
                                          lhv_j_per_kg)
    eta_b = brake_thermal_efficiency(p_b, fuel_flow_kg_per_s, lhv_j_per_kg)
    v_dot_m3_s = volumetric_fuel_flow(fuel_flow_kg_per_s,
                                       fuel_density_kg_per_m3)
    band_verdict = ci_band_verdict(eta_b, bsfc_lb_hp_hr)
    return {
        "compression_ratio": compression_ratio,
        "pressure_ratio": pressure_ratio,
        "cutoff_ratio": cutoff_ratio,
        "gamma": gamma,
        "t1_k": t1_k,
        "p1_pa": p1_pa,
        "eta_dual": eta_dual,
        "temperature_ratio": temperature_ratio,
        "t2_k": states["t2_k"],
        "t3_k": states["t3_k"],
        "t4_k": states["t4_k"],
        "t5_k": states["t5_k"],
        "cv_heat_addition_j_per_kg": q23,
        "cp_heat_addition_j_per_kg": q34,
        "heat_addition_j_per_kg": q_in,
        "heat_rejection_j_per_kg": q_out,
        "mean_effective_pressure_pa": mep_pa,
        "imep_pa": imep_pa,
        "displacement_m3": displacement_m3,
        "rpm": rpm,
        "indicated_power_w": p_i,
        "indicated_power_hp": p_i / W_PER_HP,
        "mechanical_efficiency": mechanical_efficiency,
        "brake_power_w": p_b,
        "brake_power_hp": p_b / W_PER_HP,
        "fuel_flow_kg_per_s": fuel_flow_kg_per_s,
        "bsfc_kg_per_kwh": bsfc_kg_per_kwh,
        "bsfc_lb_per_hp_hr": bsfc_lb_hp_hr,
        "indicated_thermal_efficiency": eta_i,
        "brake_thermal_efficiency": eta_b,
        "volumetric_fuel_flow_m3_per_s": v_dot_m3_s,
        "volumetric_fuel_flow_l_per_h": v_dot_m3_s * L_PER_M3 * HOUR_S,
        "volumetric_fuel_flow_us_gal_per_h": (
            v_dot_m3_s * US_GAL_PER_M3 * HOUR_S),
        "band_verdict": band_verdict,
    }


if __name__ == "__main__":
    # High-speed direct-injection CI aircraft diesel cruise point (matches
    # the contract test).
    result = dual_cycle(
        compression_ratio=16.0, pressure_ratio=1.35, cutoff_ratio=2.0,
        imep_pa=1.8e6, displacement_m3=2.0e-3, rpm=2300.0,
        mechanical_efficiency=0.86, fuel_flow_kg_per_s=3.9e-3)
    print("eta_dual = %.16f" % result["eta_dual"])
    print("temperature_ratio = %.16f" % result["temperature_ratio"])
    print("t2_k = %.16f" % result["t2_k"])
    print("t3_k = %.16f" % result["t3_k"])
    print("t4_k = %.16f" % result["t4_k"])
    print("t5_k = %.16f" % result["t5_k"])
    print("q23 = %.6f" % result["cv_heat_addition_j_per_kg"])
    print("q34 = %.6f" % result["cp_heat_addition_j_per_kg"])
    print("q_in = %.6f" % result["heat_addition_j_per_kg"])
    print("q_out = %.6f" % result["heat_rejection_j_per_kg"])
    print("MEP = %.6f Pa" % result["mean_effective_pressure_pa"])
    print("P_i = %.6f W (%.10f hp)" % (
        result["indicated_power_w"], result["indicated_power_hp"]))
    print("P_b = %.6f W (%.10f hp)" % (
        result["brake_power_w"], result["brake_power_hp"]))
    print("BSFC = %.16f kg/(kW h) = %.16f lb/(hp h)" % (
        result["bsfc_kg_per_kwh"], result["bsfc_lb_per_hp_hr"]))
    print("eta_i = %.16f, eta_b = %.16f" % (
        result["indicated_thermal_efficiency"],
        result["brake_thermal_efficiency"]))
    print("V_dot = %.16e m3/s, %.6f L/h, %.16f US gal/h" % (
        result["volumetric_fuel_flow_m3_per_s"],
        result["volumetric_fuel_flow_l_per_h"],
        result["volumetric_fuel_flow_us_gal_per_h"]))
    print("band_verdict = %r" % (result["band_verdict"],))
    print("ETA_B_BAND = %r" % (ETA_B_BAND,))
    print("BSFC_BAND_KG_PER_KWH = %r" % (BSFC_BAND_KG_PER_KWH,))
