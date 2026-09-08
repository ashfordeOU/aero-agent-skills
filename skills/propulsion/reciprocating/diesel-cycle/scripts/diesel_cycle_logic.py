#!/usr/bin/env python3
"""Reciprocating compression-ignition aircraft powerplant single-point cycle.

Pure Python 3, stdlib only, SI units throughout. Implements the standard
air-standard Diesel cycle (constant-pressure heat addition) and the
four-stroke brake-power bookkeeping used for compression-ignition aircraft
reciprocating engine performance:

  - air-standard Diesel thermal efficiency:
    eta = 1 - (1/r^(gamma-1)) * ((rc^gamma - 1)/(gamma * (rc - 1)))
  - isentropic compression temperature ratio: T2/T1 = r^(gamma-1)
  - four-state temperature bookkeeping: T2 = T1*r^(gamma-1), T3 = T2*rc,
    T4 = T1*rc^gamma
  - constant-pressure heat addition: q_in = cp * T2 * (rc - 1), with the
    closed-form cutoff-ratio identity rc = 1 + q_in/(cp * T2)
  - four-stroke indicated power: P_i = IMEP * V_d * (rpm/60)/2
  - brake power: P_b = P_i * eta_m
  - brake specific fuel consumption: BSFC = m_dot_fuel * 3600 * 1000 / P_b
  - indicated and brake thermal efficiencies on the Jet-A lower heating value
  - volumetric fuel flow from mass flow and fuel density
  - a reference-only compression-ignition band verdict that reports the
    point's position and never enforces it

All functions validate their inputs and raise ValueError on non-finite or
physically invalid values.
"""

import math

# Module constants (SI unless noted).
GAMMA_AIR = 1.4
CP_AIR = 1005.0
T1_REF_K = 288.15
HOUR_S = 3600.0
KG_PER_LB = 0.45359237
W_PER_HP = 745.6998715822702
M3_PER_L = 1.0e-3
L_PER_M3 = 1.0e3
US_GAL_PER_M3 = 264.17205235814845
KG_PER_KWH_PER_LB_PER_HP_HR = KG_PER_LB / (W_PER_HP * 1.0e-3)
JET_A_LHV_J_PER_KG = 43.2e6
JET_A_DENSITY_KG_PER_M3 = 800.0

# Reference-only compression-ignition bands, never enforced.
BSFC_BAND_LB_PER_HP_HR = (0.35, 0.42)
BSFC_BAND_KG_PER_KWH = (
    BSFC_BAND_LB_PER_HP_HR[0] * KG_PER_KWH_PER_LB_PER_HP_HR,
    BSFC_BAND_LB_PER_HP_HR[1] * KG_PER_KWH_PER_LB_PER_HP_HR,
)
# The receipt's own band-endpoint formula eta_b = 3.6e6/(b * LHV) evaluated
# at b = 0.42 and b = 0.36 lb/(hp h) (its own tighter sub-range inside the
# BSFC band, not the 0.35 BSFC lower bound) is the exact derivation of the
# pinned ETA_B_BAND window.
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


def _require_cutoff_ratio(cutoff_ratio):
    _require_finite(cutoff_ratio, "cutoff_ratio")
    if cutoff_ratio <= 1.0:
        raise ValueError("cutoff_ratio must be > 1, got %r" % (cutoff_ratio,))


def diesel_efficiency(compression_ratio, cutoff_ratio, gamma=GAMMA_AIR):
    """Air-standard Diesel cycle thermal efficiency (constant-pressure heat
    addition):

    eta = 1 - (1/r^(gamma-1)) * ((rc^gamma - 1)/(gamma * (rc - 1)))

    compression_ratio: r, the volumetric compression ratio (r > 1).
    cutoff_ratio: rc = V3/V2 = T3/T2 (1 < rc <= r; heat addition must end
    before bottom dead center).
    gamma: specific-heat ratio (gamma > 1), defaults to air-standard 1.4.
    """
    _require_compression_ratio(compression_ratio)
    _require_gamma(gamma)
    _require_cutoff_ratio(cutoff_ratio)
    if cutoff_ratio > compression_ratio:
        raise ValueError(
            "cutoff_ratio must be <= compression_ratio, got rc=%r > r=%r" % (
                cutoff_ratio, compression_ratio))
    temperature_ratio = compression_ratio ** (gamma - 1.0)
    cutoff_term = (cutoff_ratio ** gamma - 1.0) / (gamma * (cutoff_ratio - 1.0))
    return 1.0 - (1.0 / temperature_ratio) * cutoff_term


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


def cutoff_temperature(t2_k, cutoff_ratio):
    """Cutoff temperature T3 (K) = T2 * rc (constant-pressure heat addition
    2 to 3)."""
    _require_positive(t2_k, "t2_k")
    _require_cutoff_ratio(cutoff_ratio)
    return t2_k * cutoff_ratio


def expansion_temperature(t1_k, cutoff_ratio, gamma=GAMMA_AIR):
    """Expansion temperature T4 (K) = T1 * rc^gamma (isentropic expansion
    3 to 4 to V4 = V1, closed form)."""
    _require_positive(t1_k, "t1_k")
    _require_cutoff_ratio(cutoff_ratio)
    _require_gamma(gamma)
    return t1_k * cutoff_ratio ** gamma


def cycle_state_temperatures(t1_k, compression_ratio, cutoff_ratio,
                              gamma=GAMMA_AIR):
    """Four-state temperature bookkeeping dict {t1_k, t2_k, t3_k, t4_k}."""
    _require_positive(t1_k, "t1_k")
    _require_compression_ratio(compression_ratio)
    _require_gamma(gamma)
    _require_cutoff_ratio(cutoff_ratio)
    if cutoff_ratio > compression_ratio:
        raise ValueError(
            "cutoff_ratio must be <= compression_ratio, got rc=%r > r=%r" % (
                cutoff_ratio, compression_ratio))
    t2_k = compression_temperature(t1_k, compression_ratio, gamma)
    t3_k = cutoff_temperature(t2_k, cutoff_ratio)
    t4_k = expansion_temperature(t1_k, cutoff_ratio, gamma)
    return {"t1_k": t1_k, "t2_k": t2_k, "t3_k": t3_k, "t4_k": t4_k}


def heat_addition_j_per_kg(t2_k, cutoff_ratio, cp_j_per_kg_k=CP_AIR):
    """Constant-pressure heat addition per kg of air,
    q_in = cp * T2 * (rc - 1)."""
    _require_positive(t2_k, "t2_k")
    _require_cutoff_ratio(cutoff_ratio)
    _require_positive(cp_j_per_kg_k, "cp_j_per_kg_k")
    return cp_j_per_kg_k * t2_k * (cutoff_ratio - 1.0)


def cutoff_ratio_from_heat_addition(q_in_j_per_kg, t2_k,
                                     cp_j_per_kg_k=CP_AIR):
    """Cutoff ratio recovered from heat addition, the exact inverse of
    heat_addition_j_per_kg: rc = 1 + q_in/(cp * T2)."""
    _require_positive(q_in_j_per_kg, "q_in_j_per_kg")
    _require_positive(t2_k, "t2_k")
    _require_positive(cp_j_per_kg_k, "cp_j_per_kg_k")
    return 1.0 + q_in_j_per_kg / (cp_j_per_kg_k * t2_k)


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


def diesel_cycle(compression_ratio, cutoff_ratio, imep_pa, displacement_m3,
                  rpm, mechanical_efficiency, fuel_flow_kg_per_s,
                  t1_k=T1_REF_K, gamma=GAMMA_AIR, cp_j_per_kg_k=CP_AIR,
                  lhv_j_per_kg=JET_A_LHV_J_PER_KG,
                  fuel_density_kg_per_m3=JET_A_DENSITY_KG_PER_M3):
    """Single operating point of a compression-ignition reciprocating
    aircraft powerplant: ideal Diesel cycle efficiency, state temperatures
    and heat addition, indicated and brake power, BSFC in both reporting
    units, thermal efficiencies, volumetric fuel flow and the
    reference-only compression-ignition band verdict, in one call.
    ValueErrors propagate from the chained functions below.
    """
    eta_diesel = diesel_efficiency(compression_ratio, cutoff_ratio, gamma)
    temperature_ratio = isentropic_temperature_ratio(compression_ratio, gamma)
    states = cycle_state_temperatures(t1_k, compression_ratio, cutoff_ratio,
                                       gamma)
    q_in = heat_addition_j_per_kg(states["t2_k"], cutoff_ratio, cp_j_per_kg_k)
    p_i = indicated_power(imep_pa, displacement_m3, rpm)
    p_b = brake_power(p_i, mechanical_efficiency)
    bsfc_kg_per_kwh = brake_specific_fuel_consumption(fuel_flow_kg_per_s, p_b)
    bsfc_lb_hp_hr = bsfc_lb_per_hp_hr(bsfc_kg_per_kwh)
    eta_i = indicated_thermal_efficiency(p_i, fuel_flow_kg_per_s, lhv_j_per_kg)
    eta_b = brake_thermal_efficiency(p_b, fuel_flow_kg_per_s, lhv_j_per_kg)
    v_dot_m3_s = volumetric_fuel_flow(fuel_flow_kg_per_s, fuel_density_kg_per_m3)
    band_verdict = ci_band_verdict(eta_b, bsfc_lb_hp_hr)
    return {
        "compression_ratio": compression_ratio,
        "cutoff_ratio": cutoff_ratio,
        "gamma": gamma,
        "t1_k": t1_k,
        "eta_diesel": eta_diesel,
        "temperature_ratio": temperature_ratio,
        "t2_k": states["t2_k"],
        "t3_k": states["t3_k"],
        "t4_k": states["t4_k"],
        "heat_addition_j_per_kg": q_in,
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
        "volumetric_fuel_flow_us_gal_per_h": v_dot_m3_s * US_GAL_PER_M3 * HOUR_S,
        "band_verdict": band_verdict,
    }


if __name__ == "__main__":
    # Centurion/AE300-class cruise point (matches the contract test).
    result = diesel_cycle(
        compression_ratio=17.0, cutoff_ratio=2.2, imep_pa=1.8e6,
        displacement_m3=2.0e-3, rpm=2300.0, mechanical_efficiency=0.86,
        fuel_flow_kg_per_s=3.9e-3)
    print("eta_diesel = %.16f" % result["eta_diesel"])
    print("temperature_ratio = %.16f" % result["temperature_ratio"])
    print("t2_k = %.16f" % result["t2_k"])
    print("t3_k = %.16f" % result["t3_k"])
    print("t4_k = %.16f" % result["t4_k"])
    print("heat_addition_j_per_kg = %.6f" % result["heat_addition_j_per_kg"])
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
