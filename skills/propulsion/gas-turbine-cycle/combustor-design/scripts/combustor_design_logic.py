#!/usr/bin/env python3
"""Combustor design calculations for a gas turbine (stdlib only, deterministic).

Covers the combustor sizing block of the gas-turbine cycle:
  - stoichiometric_far         : fuel-air ratio at complete combustion from fuel mass
                                 composition (C, H mass fractions)
  - operating_far              : actual fuel-air ratio from fuel and air flows
  - equivalence_ratio          : operating / stoichiometric fuel-air ratio
  - combustion_efficiency      : actual vs ideal temperature rise across the burner
  - heat_release               : eta * m_f * LHV, the thermal power added by the fuel
  - temperature_rise           : combustor temperature rise from heat release and air flow
  - adiabatic_flame_temperature: simple constant-specific-heat energy balance estimate

All functions validate their inputs and raise ValueError with a clear message on
non-physical values. No network, no third-party imports; every result is
deterministic and reproducible to machine precision.

Worked anchors (kerosene-class fuel, c = 0.86, h = 0.14, LHV = 43.2 MJ/kg):
  far_st       = 0.232 / (2.6667 * 0.86 + 8.0 * 0.14)        = 0.0680
  far_op       = 2.0 / 100.0                                 = 0.0200
  phi          = 0.0200 / 0.0680                             = 0.2942
  eta_b        = 706.563 / 713.7                             = 0.9900
  Q            = 0.99 * 2.0 * 43.2e6                         = 85.536e6 W
  delta_T      = 85.536e6 / (100.0 * 1150.0)                 = 743.79 K
  T_ad (lean)  = 700 + 0.99 * 43.2e6 * 0.02 / (1300 * 1.02)  = 1345.1 K
  T_ad (stoich)= 700 + 0.99 * 43.2e6 * 0.0680 / (1300 * 1.0680) = 2793.9 K
"""

O2_PER_KG_CARBON = 32.0 / 12.0          # kg O2 per kg C burned to CO2
O2_PER_KG_HYDROGEN = 16.0 / 2.0         # kg O2 per kg H2 burned to H2O
DEFAULT_O2_AIR_FRAC = 0.232             # mass fraction of O2 in dry air


def _require_positive(name, value):
    if not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return float(value)


def stoichiometric_far(c_mass_frac, h_mass_frac, o2_mass_frac_in_air=DEFAULT_O2_AIR_FRAC):
    """Stoichiometric fuel-air ratio from fuel mass composition.

    Oxygen demand per kg of fuel is 32/12 kg per kg of carbon (to CO2) plus
    8 kg per kg of hydrogen (to H2O); the fuel-air ratio is the oxygen demand
    divided by the oxygen mass fraction of air.

    Args:
        c_mass_frac: mass fraction of carbon in the fuel, 0 < c < 1.
        h_mass_frac: mass fraction of hydrogen in the fuel, 0 < h < 1.
        o2_mass_frac_in_air: oxygen mass fraction of the oxidizer, default 0.232.

    Returns:
        Stoichiometric fuel-air ratio (kg fuel per kg air), dimensionless.

    Raises:
        ValueError: for non-physical compositions (c + h must be about 1).

    Worked anchor (kerosene, C12H26-like): c = 0.86, h = 0.14 ->
        0.232 / (2.6667 * 0.86 + 8.0 * 0.14) = 0.0680.
    """
    c = _require_positive("c_mass_frac", c_mass_frac)
    h = _require_positive("h_mass_frac", h_mass_frac)
    o2a = _require_positive("o2_mass_frac_in_air", o2_mass_frac_in_air)
    if o2a > 1.0:
        raise ValueError("o2_mass_frac_in_air must be at most 1.0, got %r" % (o2a,))
    if c >= 1.0 or h >= 1.0:
        raise ValueError("mass fractions must be below 1.0, got c=%r h=%r" % (c, h))
    if abs(c + h - 1.0) > 1e-3:
        raise ValueError(
            "fuel composition c + h must sum to about 1 (got %.4f); "
            "trace elements not supported" % (c + h,)
        )
    o2_per_kg_fuel = O2_PER_KG_CARBON * c + O2_PER_KG_HYDROGEN * h
    return o2a / o2_per_kg_fuel


def operating_far(fuel_flow, air_flow):
    """Operating (actual) fuel-air ratio from the burner fuel and air flows.

    Args:
        fuel_flow: fuel mass flow in kg/s.
        air_flow: combustor air mass flow in kg/s.

    Returns:
        Operating fuel-air ratio, dimensionless.

    Raises:
        ValueError: for non-positive flows.

    Worked anchor: fuel_flow = 2.0 kg/s, air_flow = 100.0 kg/s -> 0.0200.
    """
    mf = _require_positive("fuel_flow", fuel_flow)
    ma = _require_positive("air_flow", air_flow)
    return mf / ma


def equivalence_ratio(far_operating, far_stoichiometric):
    """Equivalence ratio phi = operating FAR / stoichiometric FAR.

    phi < 1 is fuel-lean, phi = 1 is stoichiometric, phi > 1 is fuel-rich.

    Args:
        far_operating: operating fuel-air ratio, dimensionless.
        far_stoichiometric: stoichiometric fuel-air ratio, dimensionless.

    Returns:
        Equivalence ratio, dimensionless.

    Raises:
        ValueError: for non-positive inputs.

    Worked anchor: far_op = 0.0200, far_st = 0.0680 -> 0.2942.
    """
    fop = _require_positive("far_operating", far_operating)
    fst = _require_positive("far_stoichiometric", far_stoichiometric)
    return fop / fst


def combustion_efficiency(actual_temp_rise, ideal_temp_rise):
    """Combustion efficiency from actual vs ideal temperature rise.

    eta_b = actual temperature rise / ideal temperature rise for the same
    fuel and air flows; 1.0 means complete combustion.

    Args:
        actual_temp_rise: measured combustor temperature rise in K.
        ideal_temp_rise: temperature rise for complete combustion in K.

    Returns:
        Combustion efficiency as a fraction in (0, 1].

    Raises:
        ValueError: if the actual rise is non-positive or exceeds the ideal.

    Worked anchor: actual = 706.563 K, ideal = 713.7 K -> 0.9900.
    """
    act = _require_positive("actual_temp_rise", actual_temp_rise)
    ide = _require_positive("ideal_temp_rise", ideal_temp_rise)
    if act > ide:
        raise ValueError(
            "actual_temp_rise (%.2f K) cannot exceed ideal_temp_rise (%.2f K)"
            % (act, ide)
        )
    return act / ide


def heat_release(fuel_flow, lhv, efficiency=1.0):
    """Heat release rate from the fuel flow, lower heating value, and efficiency.

    Q = eta_b * m_f * LHV in watts (J/s).

    Args:
        fuel_flow: fuel mass flow in kg/s.
        lhv: lower heating value of the fuel in J/kg.
        efficiency: combustion efficiency as a fraction in (0, 1].

    Returns:
        Heat release rate in W.

    Raises:
        ValueError: for non-positive flows/LHV or efficiency outside (0, 1].

    Worked anchor: m_f = 2.0 kg/s, LHV = 43.2e6 J/kg, eta = 0.99 -> 85.536e6 W.
    """
    mf = _require_positive("fuel_flow", fuel_flow)
    heat = _require_positive("lhv", lhv)
    eta = _require_positive("efficiency", efficiency)
    if eta > 1.0:
        raise ValueError("efficiency must be at most 1.0, got %r" % (eta,))
    return eta * mf * heat


def temperature_rise(heat_release_value, air_flow, cp_air):
    """Temperature rise across the combustor from the heat balance.

    delta_T = Q / (m_air * cp_air). The combustor is modeled as constant
    pressure heat addition; the heat release heats the air stream.

    Args:
        heat_release_value: heat release rate in W (from heat_release()).
        air_flow: combustor air mass flow in kg/s.
        cp_air: mean specific heat of the air at constant pressure in J/(kg K).

    Returns:
        Temperature rise in kelvin.

    Raises:
        ValueError: for non-positive inputs.

    Worked anchor: Q = 85.536e6 W, m_air = 100 kg/s, cp = 1150 J/(kg K) -> 743.79 K.
    """
    q = _require_positive("heat_release_value", heat_release_value)
    ma = _require_positive("air_flow", air_flow)
    cp = _require_positive("cp_air", cp_air)
    return q / (ma * cp)


def adiabatic_flame_temperature(
    inlet_temp, far, lhv, efficiency=1.0, cp_products=1300.0
):
    """Adiabatic flame temperature estimate from a constant-cp energy balance.

    Simple estimate: all heat release goes into raising the (fuel + air)
    products, T_ad = T_in + eta * LHV * far / (cp_products * (1 + far)).
    Constant specific heat, no dissociation; the stoichiometric value
    overestimates the real flame temperature (typical dissociation gives
    roughly 2300-2400 K for kerosene in air versus the simple estimate).

    Args:
        inlet_temp: combustor inlet (compressor exit) temperature in K.
        far: fuel-air ratio, dimensionless (operating or stoichiometric).
        lhv: lower heating value of the fuel in J/kg.
        efficiency: combustion efficiency as a fraction in (0, 1].
        cp_products: mean constant-pressure specific heat of the products
            in J/(kg K), default 1300.

    Returns:
        Adiabatic flame temperature estimate in kelvin.

    Raises:
        ValueError: for non-positive inputs or efficiency above 1.

    Worked anchors:
        lean:   T_in = 700 K, far = 0.0200, LHV = 43.2e6, eta = 0.99,
                cp = 1300 -> 1345.1 K.
        stoich: same but far = 0.0680 -> 2793.9 K.
    """
    tin = _require_positive("inlet_temp", inlet_temp)
    f = _require_positive("far", far)
    heat = _require_positive("lhv", lhv)
    eta = _require_positive("efficiency", efficiency)
    cp = _require_positive("cp_products", cp_products)
    if eta > 1.0:
        raise ValueError("efficiency must be at most 1.0, got %r" % (eta,))
    return tin + eta * heat * f / (cp * (1.0 + f))


if __name__ == "__main__":
    # Self-check against the worked anchors when run directly.
    far_st = stoichiometric_far(0.86, 0.14)
    far_op = operating_far(2.0, 100.0)
    q = heat_release(2.0, 43.2e6, 0.99)
    dt = temperature_rise(q, 100.0, 1150.0)
    t_ad = adiabatic_flame_temperature(700.0, far_op, 43.2e6, 0.99, 1300.0)
    t_st = adiabatic_flame_temperature(700.0, far_st, 43.2e6, 0.99, 1300.0)
    print("far_st=%.4f far_op=%.4f phi=%.4f eta=%.4f" % (
        far_st, far_op, equivalence_ratio(far_op, far_st), 0.99))
    print("Q=%.3e W  delta_T=%.2f K  T_ad_lean=%.1f K  T_ad_stoich=%.1f K" % (
        q, dt, t_ad, t_st))
