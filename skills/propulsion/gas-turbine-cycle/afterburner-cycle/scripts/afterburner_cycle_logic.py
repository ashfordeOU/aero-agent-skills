#!/usr/bin/env python3
"""Afterburner (reheat) cycle calculations for a gas turbine (stdlib only).

Given the turbine exit total temperature and the afterburner exit total
temperature, this module computes the reheat topping block that sits
between the turbine exit and the nozzle:
  - afterburner_far      : reheat fuel-air ratio from the duct energy balance
  - afterburner_fuel_flow: reheat fuel flow for the core mass flow
  - nozzle_exit_velocity : fully expanded ideal nozzle exit velocity
  - thrust_dry           : gross thrust with the afterburner off
  - thrust_reheat        : gross thrust with the afterburner lit
  - augmentation_ratio   : reheat thrust over dry thrust
  - sfc                  : specific fuel consumption in kg/(N s)
  - analyze              : complete afterburner cycle summary dict

The core flow is the topping-cycle input: the turbine exit state (t04, p04)
comes from the gas-turbine-cycle / real-cycle-effects core leaves. Reheat
fuel is added between the turbine exit and the nozzle entry; the nozzle is
modeled as fully expanded and ideal (real nozzles add a thrust
coefficient). All functions validate inputs and raise ValueError on
non-physical values. No network, no third-party imports; deterministic.

Worked example (t04 = 900 K, f_core = 0.02, mdot = 100 kg/s, t05 = 1700 K,
p04 = 3.0e5 Pa, p_amb = 1.01325e5 Pa):
  f_ab          = 1.02 * 1150 * 800 / (0.97 * 43e6) = 0.0225
  mdot_f_ab     = 2.2498 kg/s
  v_dry         = 699.1 m/s      (Te_dry = 687.6 K)
  v_reheat      = 960.8 m/s      (Te_rh   = 1298.7 K)
  F_dry         = 102 * 699.1    = 71307 N
  F_reheat      = 104.25 * 960.8 = 100162 N
  augmentation  = 1.405
  sfc_dry       = 28.05 mg/(N s), sfc_reheat = 42.42 mg/(N s)
"""

CP = 1150.0        # J/(kg K), constant specific heat in the reheat duct
LHV = 43.0e6       # J/kg, kerosene lower heating value
ETA_AB = 0.97      # afterburner combustion efficiency
GAMMA = 1.33       # specific heat ratio for the isentropic nozzle expansion
R = 287.0          # J/(kg K), gas constant (documented; velocity uses CP only)


def _require_positive(name, value):
    """Return float(value) or raise ValueError when value is not > 0."""
    if not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return value


def _require_nonnegative(name, value):
    """Return float(value) or raise ValueError when value is < 0."""
    if not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if value < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (name, value))
    return value


def afterburner_far(t04_k, t05_k, f_core):
    """Afterburner fuel-air ratio from the reheat duct energy balance.

    f_ab = (1 + f_core) * CP * (t05 - t04) / (ETA_AB * LHV): the heat needed
    to raise the (fuel + air) core products from the turbine exit temperature
    t04 to the afterburner exit temperature t05, divided by the useful heat
    released per kg of reheat fuel.

    Args:
        t04_k: turbine exit total temperature in K, > 0.
        t05_k: afterburner exit (nozzle entry) total temperature in K, > t04.
        f_core: core fuel-air ratio (kg fuel per kg air), >= 0.

    Returns:
        Reheat fuel-air ratio (kg reheat fuel per kg core air), dimensionless.

    Raises:
        ValueError: for t05 <= t04, t04 <= 0, or f_core < 0.

    Worked anchor: t04 = 900 K, t05 = 1700 K, f_core = 0.02 ->
        1.02 * 1150 * 800 / (0.97 * 43e6) = 0.022498.
    """
    t04 = _require_positive("t04_k", t04_k)
    f = _require_nonnegative("f_core", f_core)
    t05 = _require_positive("t05_k", t05_k)
    if t05 <= t04:
        raise ValueError(
            "afterburner exit temperature t05 (%.1f K) must exceed the "
            "turbine exit temperature t04 (%.1f K)" % (t05, t04)
        )
    return (1.0 + f) * CP * (t05 - t04) / (ETA_AB * LHV)


def afterburner_fuel_flow(f_ab, mdot_core_kg_s):
    """Reheat fuel mass flow for the core air mass flow.

    mdot_f_ab = f_ab * mdot_core, the fuel added in the afterburner duct.

    Args:
        f_ab: afterburner fuel-air ratio, >= 0.
        mdot_core_kg_s: core air mass flow in kg/s, > 0.

    Returns:
        Reheat fuel mass flow in kg/s.

    Raises:
        ValueError: for f_ab < 0 or non-positive core mass flow.

    Worked anchor: f_ab = 0.022498, mdot = 100 kg/s -> 2.2498 kg/s.
    """
    fab = _require_nonnegative("f_ab", f_ab)
    mdot = _require_positive("mdot_core_kg_s", mdot_core_kg_s)
    return fab * mdot


def nozzle_exit_velocity(t_total_k, p_total_pa, p_amb_pa):
    """Fully expanded ideal nozzle exit velocity from isentropic expansion.

    Te = Tt * (p_amb / p_total)^((GAMMA-1)/GAMMA), then the steady flow
    energy balance v = sqrt(2 * CP * (Tt - Te)); the fully expanded pressure
    term is zero, so CP and the temperature drop alone give the velocity.

    Args:
        t_total_k: nozzle entry total temperature in K, > 0.
        p_total_pa: nozzle entry total pressure in Pa, > p_amb.
        p_amb_pa: ambient (nozzle exit) pressure in Pa, > 0.

    Returns:
        Nozzle exit velocity in m/s.

    Raises:
        ValueError: for p_total <= p_amb (underexpansion is not modeled,
            a fully expanded nozzle requires p_total > p_amb) or t_total <= 0.

    Worked anchors: t = 900 K -> 699.1 m/s; t = 1700 K -> 960.8 m/s at
        p04 = 3.0e5 Pa, p_amb = 1.01325e5 Pa.
    """
    tt = _require_positive("t_total_k", t_total_k)
    pt = _require_positive("p_total_pa", p_total_pa)
    pa = _require_positive("p_amb_pa", p_amb_pa)
    if pt <= pa:
        raise ValueError(
            "p_total (%.4g Pa) must exceed p_amb (%.4g Pa) for a fully "
            "expanded nozzle; underexpansion is not modeled" % (pt, pa)
        )
    te = tt * (pa / pt) ** ((GAMMA - 1.0) / GAMMA)
    return (max(0.0, 2.0 * CP * (tt - te))) ** 0.5


def thrust_dry(t04_k, p04_pa, p_amb_pa, mdot_core_kg_s, f_core):
    """Gross thrust with the afterburner off (dry nozzle).

    mdot_gas = mdot_core * (1 + f_core) and F = mdot_gas * v_dry with the
    nozzle fully expanded, so the pressure thrust term is zero.

    Args:
        t04_k: turbine exit (nozzle entry) total temperature in K.
        p04_pa: nozzle entry total pressure in Pa, > p_amb.
        p_amb_pa: ambient pressure in Pa.
        mdot_core_kg_s: core air mass flow in kg/s, > 0.
        f_core: core fuel-air ratio, >= 0.

    Returns:
        Dry gross thrust in N.

    Raises:
        ValueError: for non-positive mass flow, p04 <= p_amb, t04 <= 0.

    Worked anchor: 102 kg/s * 699.1 m/s = 71307 N.
    """
    mdot = _require_positive("mdot_core_kg_s", mdot_core_kg_s)
    f = _require_nonnegative("f_core", f_core)
    v = nozzle_exit_velocity(t04_k, p04_pa, p_amb_pa)
    return mdot * (1.0 + f) * v


def thrust_reheat(t05_k, p04_pa, p_amb_pa, mdot_core_kg_s, f_core, f_ab):
    """Gross thrust with the afterburner lit (reheat nozzle).

    mdot_gas = mdot_core * (1 + f_core + f_ab) and F = mdot_gas * v_reheat
    with the nozzle fully expanded at the afterburner exit temperature t05.

    Args:
        t05_k: afterburner exit (nozzle entry) total temperature in K.
        p04_pa: nozzle entry total pressure in Pa, > p_amb.
        p_amb_pa: ambient pressure in Pa.
        mdot_core_kg_s: core air mass flow in kg/s, > 0.
        f_core: core fuel-air ratio, >= 0.
        f_ab: afterburner fuel-air ratio, >= 0 (from afterburner_far).

    Returns:
        Reheat gross thrust in N.

    Raises:
        ValueError: for non-positive mass flow, p04 <= p_amb, t05 <= 0,
            or negative fuel-air ratios.

    Worked anchor: 104.25 kg/s * 960.8 m/s = 100162 N.
    """
    mdot = _require_positive("mdot_core_kg_s", mdot_core_kg_s)
    f = _require_nonnegative("f_core", f_core)
    fab = _require_nonnegative("f_ab", f_ab)
    v = nozzle_exit_velocity(t05_k, p04_pa, p_amb_pa)
    return mdot * (1.0 + f + fab) * v


def augmentation_ratio(F_reheat, F_dry):
    """Thrust augmentation ratio of reheat thrust over dry thrust.

    Args:
        F_reheat: reheat gross thrust in N, > 0.
        F_dry: dry gross thrust in N, > 0.

    Returns:
        Augmentation ratio, dimensionless (about 1.4 for a typical reheat).

    Raises:
        ValueError: for non-positive thrust values.

    Worked anchor: 100162 N / 71307 N = 1.405.
    """
    fr = _require_positive("F_reheat", F_reheat)
    fd = _require_positive("F_dry", F_dry)
    return fr / fd


def sfc(fuel_flow_kg_s, thrust_N):
    """Specific fuel consumption in kg/(N s).

    Args:
        fuel_flow_kg_s: total fuel mass flow (core plus reheat) in kg/s, >= 0.
        thrust_N: gross thrust in N, > 0.

    Returns:
        SFC in kg/(N s); multiply by 1e6 for mg/(N s).

    Raises:
        ValueError: for negative fuel flow or non-positive thrust.

    Worked anchors: 2.0/71307 = 2.805e-5 kg/(N s) (dry);
        (2.0 + 2.2498)/100162 = 4.242e-5 kg/(N s) (reheat).
    """
    mf = _require_nonnegative("fuel_flow_kg_s", fuel_flow_kg_s)
    f = _require_positive("thrust_N", thrust_N)
    return mf / f


def analyze(t04_k, f_core, mdot_core_kg_s, t05_k, p04_pa, p_amb_pa):
    """Complete afterburner cycle summary for the given operating point.

    Computes the reheat fuel-air ratio and fuel flow, the dry and reheat
    nozzle exit velocities, the dry and reheat gross thrust, the thrust
    augmentation ratio, and the SFC with and without reheat, all in SI.

    Args:
        t04_k: turbine exit total temperature in K, > 0.
        f_core: core fuel-air ratio, >= 0.
        mdot_core_kg_s: core air mass flow in kg/s, > 0.
        t05_k: afterburner exit (nozzle entry) total temperature in K, > t04.
        p04_pa: nozzle entry total pressure in Pa, > p_amb.
        p_amb_pa: ambient pressure in Pa, > 0.

    Returns:
        Dict with keys f_ab, mdot_f_ab, v_dry, v_reheat, F_dry, F_reheat,
        augmentation_ratio, sfc_dry, sfc_reheat, all SI units.

    Raises:
        ValueError: for non-positive mass flow, t04 <= 0, t05 <= t04,
            p04 <= p_amb, p_amb <= 0, or f_core < 0.
    """
    _require_positive("mdot_core_kg_s", mdot_core_kg_s)
    _require_positive("p_amb_pa", p_amb_pa)
    fab = afterburner_far(t04_k, t05_k, f_core)
    mdot_f_ab = afterburner_fuel_flow(fab, mdot_core_kg_s)
    v_dry = nozzle_exit_velocity(t04_k, p04_pa, p_amb_pa)
    v_reheat = nozzle_exit_velocity(t05_k, p04_pa, p_amb_pa)
    f_dry = thrust_dry(t04_k, p04_pa, p_amb_pa, mdot_core_kg_s, f_core)
    f_reheat = thrust_reheat(
        t05_k, p04_pa, p_amb_pa, mdot_core_kg_s, f_core, fab
    )
    mdot_f_core = f_core * mdot_core_kg_s
    return {
        "f_ab": fab,
        "mdot_f_ab": mdot_f_ab,
        "v_dry": v_dry,
        "v_reheat": v_reheat,
        "F_dry": f_dry,
        "F_reheat": f_reheat,
        "augmentation_ratio": augmentation_ratio(f_reheat, f_dry),
        "sfc_dry": sfc(mdot_f_core, f_dry),
        "sfc_reheat": sfc(mdot_f_core + mdot_f_ab, f_reheat),
    }


if __name__ == "__main__":
    # Self-check against the worked example when run directly (smoke test).
    r = analyze(900.0, 0.02, 100.0, 1700.0, 3.0e5, 1.01325e5)
    print("f_ab=%.6f mdot_f_ab=%.4f v_dry=%.1f v_reheat=%.1f" % (
        r["f_ab"], r["mdot_f_ab"], r["v_dry"], r["v_reheat"]))
    print("F_dry=%.0f F_reheat=%.0f aug=%.3f" % (
        r["F_dry"], r["F_reheat"], r["augmentation_ratio"]))
    print("sfc_dry=%.4e sfc_reheat=%.4e kg/(N s)" % (
        r["sfc_dry"], r["sfc_reheat"]))
