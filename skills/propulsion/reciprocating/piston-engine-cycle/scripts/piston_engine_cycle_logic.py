#!/usr/bin/env python3
"""Reciprocating four-stroke aircraft powerplant single-point cycle.

Pure Python 3, stdlib only, SI units throughout. Implements the standard
air-standard Otto cycle and four-stroke brake-power bookkeeping used for
general-aviation reciprocating engine performance:

  - air-standard Otto thermal efficiency: eta = 1 - 1/r^(gamma-1)
  - isentropic compression temperature ratio: T2/T1 = r^(gamma-1)
  - four-stroke indicated power: P_i = IMEP * V_d * (rpm/60)/2
  - brake power: P_b = P_i * eta_m
  - brake specific fuel consumption: BSFC = m_dot_fuel * 3600 * 1000 / P_b
  - indicated and brake thermal efficiencies on the fuel lower heating value
  - volumetric fuel flow from mass flow and fuel density
  - a reference-only general-aviation band verdict that reports the point's
    position and never enforces it

All functions validate their inputs and raise ValueError on non-finite or
physically invalid values.
"""

import math

# Module constants (SI unless noted).
GAMMA_AIR = 1.4
HOUR_S = 3600.0
KG_PER_LB = 0.45359237
W_PER_HP = 745.6998715822702
M3_PER_L = 1.0e-3
L_PER_M3 = 1.0e3
US_GAL_PER_M3 = 264.17205235814845
KG_PER_KWH_PER_LB_PER_HP_HR = KG_PER_LB / (W_PER_HP * 1.0e-3)
AVGAS_DENSITY_KG_PER_M3 = 720.0
AVGAS_LHV_J_PER_KG = 43.5e6

# Reference-only general-aviation bands, never enforced.
ETA_B_BAND = (0.25, 0.30)
BSFC_BAND_LB_PER_HP_HR = (0.40, 0.55)
BSFC_BAND_KG_PER_KWH = (
    BSFC_BAND_LB_PER_HP_HR[0] * KG_PER_KWH_PER_LB_PER_HP_HR,
    BSFC_BAND_LB_PER_HP_HR[1] * KG_PER_KWH_PER_LB_PER_HP_HR,
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


def otto_efficiency(compression_ratio, gamma=GAMMA_AIR):
    """Air-standard Otto cycle thermal efficiency, eta = 1 - 1/r^(gamma-1).

    compression_ratio: r, the volumetric compression ratio (r > 1).
    gamma: specific-heat ratio (gamma > 1), defaults to air-standard 1.4.
    """
    _require_finite(compression_ratio, "compression_ratio")
    _require_finite(gamma, "gamma")
    if compression_ratio <= 1.0:
        raise ValueError(
            "compression_ratio must be > 1, got %r" % (compression_ratio,))
    if gamma <= 1.0:
        raise ValueError("gamma must be > 1, got %r" % (gamma,))
    return 1.0 - 1.0 / compression_ratio ** (gamma - 1.0)


def isentropic_temperature_ratio(compression_ratio, gamma=GAMMA_AIR):
    """Isentropic compression temperature ratio, T2/T1 = r^(gamma-1).

    Same validity range as otto_efficiency; the efficiency identity
    eta = 1 - 1/(T2/T1) holds against this value.
    """
    _require_finite(compression_ratio, "compression_ratio")
    _require_finite(gamma, "gamma")
    if compression_ratio <= 1.0:
        raise ValueError(
            "compression_ratio must be > 1, got %r" % (compression_ratio,))
    if gamma <= 1.0:
        raise ValueError("gamma must be > 1, got %r" % (gamma,))
    return compression_ratio ** (gamma - 1.0)


def indicated_power(imep_pa, displacement_m3, rpm):
    """Four-stroke indicated power, P_i = IMEP * V_d * (rpm/60)/2.

    imep_pa: indicated mean effective pressure, Pa. displacement_m3: swept
    displacement per cycle, m3. rpm: crankshaft speed, rev/min. One power
    stroke occurs per two crankshaft revolutions, so the revolution rate
    halves in the bookkeeping.
    """
    _require_positive(imep_pa, "imep_pa")
    _require_positive(displacement_m3, "displacement_m3")
    _require_positive(rpm, "rpm")
    return imep_pa * displacement_m3 * (rpm / 60.0) / 2.0


def brake_power(indicated_power_w, mechanical_efficiency):
    """Brake power, P_b = P_i * eta_m.

    mechanical_efficiency in (0, 1]; eta_m = 1.0 returns P_i exactly.
    """
    _require_positive(indicated_power_w, "indicated_power_w")
    _require_mechanical_efficiency(mechanical_efficiency)
    return indicated_power_w * mechanical_efficiency


def brake_specific_fuel_consumption(fuel_flow_kg_per_s, brake_power_w):
    """Brake specific fuel consumption, BSFC = m_dot_fuel*3600*1000/P_b.

    Reported in kg/(kW h), the family shaft-power convention.
    """
    _require_positive(fuel_flow_kg_per_s, "fuel_flow_kg_per_s")
    _require_positive(brake_power_w, "brake_power_w")
    return fuel_flow_kg_per_s * HOUR_S * 1000.0 / brake_power_w


def bsfc_lb_per_hp_hr(bsfc_kg_per_kwh):
    """Convert BSFC from kg/(kW h) to lb/(hp h) with the exact unit bridge."""
    _require_positive(bsfc_kg_per_kwh, "bsfc_kg_per_kwh")
    return bsfc_kg_per_kwh / KG_PER_KWH_PER_LB_PER_HP_HR


def fuel_flow_from_bsfc(bsfc_kg_per_kwh, brake_power_w):
    """Fuel mass flow from BSFC and brake power, the exact inverse of
    brake_specific_fuel_consumption."""
    _require_positive(bsfc_kg_per_kwh, "bsfc_kg_per_kwh")
    _require_positive(brake_power_w, "brake_power_w")
    return bsfc_kg_per_kwh * brake_power_w / (HOUR_S * 1000.0)


def indicated_thermal_efficiency(indicated_power_w, fuel_flow_kg_per_s,
                                  lhv_j_per_kg=AVGAS_LHV_J_PER_KG):
    """Indicated thermal efficiency on the fuel lower heating value,
    eta_i = P_i / (m_dot_fuel * LHV)."""
    _require_positive(indicated_power_w, "indicated_power_w")
    _require_positive(fuel_flow_kg_per_s, "fuel_flow_kg_per_s")
    _require_positive(lhv_j_per_kg, "lhv_j_per_kg")
    return indicated_power_w / (fuel_flow_kg_per_s * lhv_j_per_kg)


def brake_thermal_efficiency(brake_power_w, fuel_flow_kg_per_s,
                              lhv_j_per_kg=AVGAS_LHV_J_PER_KG):
    """Brake thermal efficiency on the fuel lower heating value,
    eta_b = P_b / (m_dot_fuel * LHV) = eta_m * eta_i."""
    _require_positive(brake_power_w, "brake_power_w")
    _require_positive(fuel_flow_kg_per_s, "fuel_flow_kg_per_s")
    _require_positive(lhv_j_per_kg, "lhv_j_per_kg")
    return brake_power_w / (fuel_flow_kg_per_s * lhv_j_per_kg)


def volumetric_fuel_flow(fuel_flow_kg_per_s,
                          fuel_density_kg_per_m3=AVGAS_DENSITY_KG_PER_M3):
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


def ga_band_verdict(brake_thermal_eff, bsfc_lb_per_hp_hr_value):
    """Reference-only general-aviation band verdict.

    Reports where the point's brake thermal efficiency and BSFC (lb/(hp h))
    sit against the published GA bands (ETA_B_BAND, BSFC_BAND_LB_PER_HP_HR).
    enforced is always False: an out-of-band point is not an error and this
    function never raises for one, only for non-finite or non-positive
    inputs.
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


def piston_engine_cycle(compression_ratio, imep_pa, displacement_m3, rpm,
                         mechanical_efficiency, fuel_flow_kg_per_s,
                         gamma=GAMMA_AIR, lhv_j_per_kg=AVGAS_LHV_J_PER_KG,
                         fuel_density_kg_per_m3=AVGAS_DENSITY_KG_PER_M3):
    """Single operating point of a reciprocating four-stroke aircraft
    powerplant: ideal cycle efficiency, indicated and brake power, BSFC in
    both reporting units, thermal efficiencies, volumetric fuel flow and
    the reference-only GA band verdict, in one call. ValueErrors propagate
    from the chained functions below.
    """
    eta_otto = otto_efficiency(compression_ratio, gamma)
    temperature_ratio = isentropic_temperature_ratio(compression_ratio, gamma)
    p_i = indicated_power(imep_pa, displacement_m3, rpm)
    p_b = brake_power(p_i, mechanical_efficiency)
    bsfc_kg_per_kwh = brake_specific_fuel_consumption(fuel_flow_kg_per_s, p_b)
    bsfc_lb_hp_hr = bsfc_lb_per_hp_hr(bsfc_kg_per_kwh)
    eta_i = indicated_thermal_efficiency(p_i, fuel_flow_kg_per_s, lhv_j_per_kg)
    eta_b = brake_thermal_efficiency(p_b, fuel_flow_kg_per_s, lhv_j_per_kg)
    v_dot_m3_s = volumetric_fuel_flow(fuel_flow_kg_per_s, fuel_density_kg_per_m3)
    band_verdict = ga_band_verdict(eta_b, bsfc_lb_hp_hr)
    return {
        "compression_ratio": compression_ratio,
        "gamma": gamma,
        "eta_otto": eta_otto,
        "temperature_ratio": temperature_ratio,
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
    # Lycoming O-320 class cruise point (matches the contract test).
    result = piston_engine_cycle(
        compression_ratio=8.5, imep_pa=9.5e5, displacement_m3=5.4e-3,
        rpm=2700.0, mechanical_efficiency=0.85, fuel_flow_kg_per_s=7.6e-3)
    print("eta_otto = %.10f" % result["eta_otto"])
    print("P_i = %.3f W (%.3f hp)" % (
        result["indicated_power_w"], result["indicated_power_hp"]))
    print("P_b = %.3f W (%.3f hp)" % (
        result["brake_power_w"], result["brake_power_hp"]))
    print("BSFC = %.10f kg/(kW h) = %.10f lb/(hp h)" % (
        result["bsfc_kg_per_kwh"], result["bsfc_lb_per_hp_hr"]))
    print("eta_i = %.10f, eta_b = %.10f" % (
        result["indicated_thermal_efficiency"],
        result["brake_thermal_efficiency"]))
    print("V_dot = %.10e m3/s, %.3f L/h, %.5f US gal/h" % (
        result["volumetric_fuel_flow_m3_per_s"],
        result["volumetric_fuel_flow_l_per_h"],
        result["volumetric_fuel_flow_us_gal_per_h"]))
    print("band_verdict = %r" % (result["band_verdict"],))
