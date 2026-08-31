#!/usr/bin/env python3
"""ISA standard atmosphere logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, ecss: free download):
ECSS space environment practice and the ICAO standard atmosphere
agree on the reference model: sea level 288.15 K, 101325 Pa,
1.225 kg/m3; troposphere lapse 6.5 K/km up to 11 km; isothermal
lower stratosphere at 216.65 K. Pressure integrates the hydrostatic
balance with the lapse rate. Model range here is 0-20 km.
"""

G = 9.80665  # m/s2
R_AIR = 287.05  # J/(kg K)
LAPSE = 0.0065  # K/m
T0 = 288.15  # K
P0 = 101325.0  # Pa
TROPOPAUSE = 11000.0
T_TROPOPAUSE = T0 - LAPSE * TROPOPAUSE  # 216.65 K
TOP = 20000.0

import math


def _check_altitude(h):
    if h < 0:
        raise ValueError("altitude must be >= 0, got %r" % (h,))
    if h > TOP:
        raise ValueError("altitude above model top 20 km, got %r" % (h,))


def isa_temperature_k(h):
    """ISA temperature (K) at altitude h (m), 0-20 km."""
    _check_altitude(h)
    if h <= TROPOPAUSE:
        return T0 - LAPSE * h
    return T_TROPOPAUSE


def isa_pressure_pa(h):
    """ISA pressure (Pa) at altitude h (m), 0-20 km."""
    _check_altitude(h)
    if h <= TROPOPAUSE:
        t = T0 - LAPSE * h
        return P0 * (t / T0) ** (G / (R_AIR * LAPSE))
    p_trop = isa_pressure_pa(TROPOPAUSE)
    return p_trop * math.exp(-G * (h - TROPOPAUSE) / (R_AIR * T_TROPOPAUSE))


def isa_density_kgm3(h):
    """ISA density (kg/m3) at altitude h (m), 0-20 km."""
    return isa_pressure_pa(h) / (R_AIR * isa_temperature_k(h))


def isa_sea_level():
    """(temperature K, pressure Pa, density kg/m3) at sea level."""
    return (T0, P0, P0 / (R_AIR * T0))
