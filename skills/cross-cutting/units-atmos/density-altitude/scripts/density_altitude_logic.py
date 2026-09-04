#!/usr/bin/env python3
"""Density altitude logic (pure stdlib, deterministic).

Computes the density altitude on a non-standard day from the pressure
altitude and the outside air temperature: the ISA deviation, the
density ratio sigma = delta(hp) * T0 / T_oat from the ISA pressure
ratio and the temperature ratio, and the density altitude via the
troposphere closed-form inverse with the stratosphere branch.

Model (standard engineering method, constants documented):
  T0 = 288.15 K standard sea-level temperature
  L  = 0.0065 K/m troposphere temperature lapse (geopotential)
  g  = 9.80665 m/s2
  R  = 287.0 J/(kg K)
  p0 = 101325 Pa standard sea-level pressure
  tropopause at 11000 m, isothermal stratosphere at 216.65 K
Forward ISA troposphere density ratio:
  sigma_ISA(h) = (1 - L h / T0)^(g/(R L) - 1)
Inverse (troposphere closed form):
  h_rho = (T0 / L) (1 - sigma^e),  e = 1 / (g/(R L) - 1)
The exponent e equals the exact inverse of the density power law;
written with the module constants it is R L / (g - R L). The
classical notation R L / g inverts the pressure law instead and would
break the ISA identity, so the exact inverse exponent is used here.
Stratosphere branch (sigma below the tropopause density ratio):
  h_rho = 11000 - (R T_strat / g) ln(sigma / sigma_trop)
"""

import math

T0 = 288.15  # K, standard sea-level temperature
L = 0.0065  # K/m, troposphere temperature lapse
G = 9.80665  # m/s2, standard gravity
R = 287.0  # J/(kg K), specific gas constant of air
P0 = 101325.0  # Pa, standard sea-level pressure
TROPOPAUSE = 11000.0  # m, ISA tropopause
T_STRAT = 216.65  # K, isothermal lower stratosphere (T0 - L * TROPOPAUSE)
MIN_HP_M = -1000.0  # m, lowest allowed geopotential altitude

PRESSURE_EXP = G / (R * L)  # 5.2569, troposphere pressure power law
DENSITY_EXP = PRESSURE_EXP - 1.0  # 4.2569, troposphere density power law
INV_EXP = 1.0 / DENSITY_EXP  # exact inverse of the density power law
DELTA_TROP = (1.0 - L * TROPOPAUSE / T0) ** PRESSURE_EXP  # p/p0 at tropopause
SIGMA_TROP = DELTA_TROP * T0 / T_STRAT  # density ratio at tropopause
STRAT_SCALE = R * T_STRAT / G  # m, stratosphere density scale height


def _check_altitude(hp_m):
    """Reject pressure altitudes below the small-negative bound."""
    if hp_m < MIN_HP_M:
        raise ValueError(
            "pressure altitude must be >= %r m, got %r" % (MIN_HP_M, hp_m)
        )


def _check_temperature(oat_k):
    """Reject outside-air temperatures at or below absolute zero."""
    if oat_k <= 0:
        raise ValueError(
            "outside air temperature must be above absolute zero, got %r K" % (oat_k,)
        )


def isa_temperature_k(hp_m):
    """ISA temperature (K) at pressure altitude hp_m (m).

    Troposphere linear lapse from T0; isothermal 216.65 K from the
    tropopause up. Allows the small negative geopotential bound.
    """
    _check_altitude(hp_m)
    if hp_m <= TROPOPAUSE:
        return T0 - L * hp_m
    return T_STRAT


def isa_pressure_ratio(hp_m):
    """ISA pressure ratio delta = p/p0 at pressure altitude hp_m.

    Troposphere power law (1 - L h / T0)^(g/(R L)); stratosphere
    exponential decay from the tropopause state.
    """
    _check_altitude(hp_m)
    if hp_m <= TROPOPAUSE:
        return (1.0 - L * hp_m / T0) ** PRESSURE_EXP
    return DELTA_TROP * math.exp(-(hp_m - TROPOPAUSE) / STRAT_SCALE)


def isa_deviation_k(hp_m, oat_k):
    """ISA temperature deviation (K): oat_k minus isa_temperature_k."""
    _check_altitude(hp_m)
    _check_temperature(oat_k)
    return oat_k - isa_temperature_k(hp_m)


def density_ratio_from_pressure_temperature(p_pa, t_k):
    """Density ratio sigma = (p/p0) * (T0/t_k) for a static pressure.

    Perfect-gas density ratio of the actual state to the standard
    sea-level state. Raises ValueError on non-physical inputs.
    """
    if p_pa <= 0:
        raise ValueError("static pressure must be positive, got %r Pa" % (p_pa,))
    _check_temperature(t_k)
    return (p_pa / P0) * (T0 / t_k)


def density_altitude_m(hp_m, oat_k):
    """Density altitude (m) at pressure altitude hp_m, OAT oat_k (K).

    sigma = isa_pressure_ratio(hp_m) * T0 / oat_k. In the troposphere
    (sigma >= SIGMA_TROP) the closed form h = (T0/L)(1 - sigma^e)
    with e = 1/(g/(R L) - 1); below that the stratosphere closed form
    h = 11000 - (R T_strat / g) ln(sigma / SIGMA_TROP).
    """
    _check_altitude(hp_m)
    _check_temperature(oat_k)
    sigma = isa_pressure_ratio(hp_m) * T0 / oat_k
    if sigma >= SIGMA_TROP:
        return (T0 / L) * (1.0 - sigma ** INV_EXP)
    return TROPOPAUSE - STRAT_SCALE * math.log(sigma / SIGMA_TROP)


def density_altitude_ft(hp_ft, oat_deg_c):
    """Density altitude (ft) at pressure altitude hp_ft, OAT oat_deg_c.

    Wrapper: hp_m = hp_ft * 0.3048, oat_k = oat_deg_c + 273.15,
    returns the density altitude in ft.
    """
    return density_altitude_m(hp_ft * 0.3048, oat_deg_c + 273.15) / 0.3048


def density_altitude_summary(hp_m, oat_k):
    """Summary dict for the density altitude problem at (hp_m, oat_k).

    Keys: hp_m, oat_k, isa_temp_k, deviation_k, density_ratio,
    density_altitude_m, density_altitude_ft.
    """
    isa_temp_k = isa_temperature_k(hp_m)
    sigma = isa_pressure_ratio(hp_m) * T0 / oat_k
    h_rho_m = density_altitude_m(hp_m, oat_k)
    return {
        "hp_m": hp_m,
        "oat_k": oat_k,
        "isa_temp_k": isa_temp_k,
        "deviation_k": oat_k - isa_temp_k,
        "density_ratio": sigma,
        "density_altitude_m": h_rho_m,
        "density_altitude_ft": h_rho_m / 0.3048,
    }


if __name__ == "__main__":
    # Quick smoke: print the worked anchors.
    print("da(0, 288.15) =", density_altitude_m(0.0, 288.15), "m")
    print("da(3048, T_isa) =", density_altitude_m(3048.0, isa_temperature_k(3048.0)), "m")
    print("SL +15 C =", density_altitude_ft(0.0, 15.0), "ft")
    print("10000 ft, ISA+10 K =", density_altitude_ft(10000.0, isa_temperature_k(3048.0) - 273.15 + 10.0), "ft")
    print("10000 ft, ISA-10 K =", density_altitude_ft(10000.0, isa_temperature_k(3048.0) - 273.15 - 10.0), "ft")
    print("10000 ft, +15 C absolute =", density_altitude_ft(10000.0, 15.0), "ft")
