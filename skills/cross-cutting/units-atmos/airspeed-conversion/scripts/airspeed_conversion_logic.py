#!/usr/bin/env python3
"""Airspeed conversion logic through the compressibility-corrected chain.

Paraphrase of common-knowledge air-data methodology (standards-map.yaml,
naca-tr-824 reference-only): the airspeed indicator reads impact pressure
qc = p_total - p_static. The standard compressible calibration (NACA TR-824
style airspeed-indicator correction) converts qc into calibrated airspeed
using sea-level ISA conditions, and converts true airspeed at altitude into
CAS through the local Mach number and static pressure. This module owns the
full subsonic chain qc <-> CAS, CAS <-> M <-> TAS, TAS <-> EAS in both
directions, with the ISA state leg computed internally.

All functions are pure, deterministic, stdlib-only and scalar. Speeds are in
m/s unless a name says kt; pressures in Pa; altitude in m; density in kg/m3.
"""

import math

# Module constants (SI)
GAMMA = 1.4  # ratio of specific heats for air
R_GAS = 287.05287  # J/(kg K), air gas constant
T0_ISA = 288.15  # K, ISA sea-level temperature
P0_ISA = 101325.0  # Pa, ISA sea-level pressure
RHO0_ISA = 1.225  # kg/m3, ISA sea-level density
A0_ISA = math.sqrt(GAMMA * R_GAS * T0_ISA)  # 340.294 m/s, sea-level speed of sound
G0 = 9.80665  # m/s2, standard gravity
LAPSE = 0.0065  # K/m, troposphere lapse rate
TROPOPAUSE = 11000.0  # m
T_TROPOPAUSE = T0_ISA - LAPSE * TROPOPAUSE  # 216.65 K
KT_TO_MS = 0.514444  # m/s per knot
# qc/p at M = 1: (1 + 0.2)^3.5 - 1; the inversion is non-unique past it.
QC_SONIC_RATIO = (1.0 + 0.2) ** 3.5 - 1.0  # 0.8929... subsonic limit


def _check_altitude(altitude_m):
    """Reject negative altitude; return None."""
    if altitude_m < 0:
        raise ValueError("altitude must be >= 0 m, got %r" % (altitude_m,))


def isa_state(altitude_m):
    """Return dict {T, p, rho, a} of the ISA atmosphere at altitude_m.

    Troposphere below 11000 m uses the 6.5 K/km lapse; above the
    tropopause the temperature is constant at 216.65 K and pressure
    decays exponentially. ValueError for altitude < 0.
    """
    _check_altitude(altitude_m)
    if altitude_m <= TROPOPAUSE:
        t = T0_ISA - LAPSE * altitude_m
        p = P0_ISA * (t / T0_ISA) ** (G0 / (LAPSE * R_GAS))
    else:
        t = T_TROPOPAUSE
        p_tropo = P0_ISA * (T_TROPOPAUSE / T0_ISA) ** (G0 / (LAPSE * R_GAS))
        p = p_tropo * math.exp(-G0 * (altitude_m - TROPOPAUSE) / (R_GAS * t))
    rho = p / (R_GAS * t)
    a = math.sqrt(GAMMA * R_GAS * t)
    return {"T": t, "p": p, "rho": rho, "a": a}


def impact_pressure_from_mach(mach, pressure):
    """Impact pressure qc (Pa) from Mach number and static pressure p.

    qc = p * ((1 + 0.2*M^2)^3.5 - 1), the isentropic Rayleigh pitot
    relation for subsonic flow. ValueError if M < 0, M >= 1 or p <= 0.
    """
    if mach < 0:
        raise ValueError("Mach must be >= 0, got %r" % (mach,))
    if mach >= 1:
        raise ValueError("subsonic domain only: Mach must be < 1, got %r" % (mach,))
    if pressure <= 0:
        raise ValueError("static pressure must be > 0, got %r" % (pressure,))
    return pressure * ((1.0 + 0.2 * mach * mach) ** 3.5 - 1.0)


def mach_from_impact_pressure(qc, pressure):
    """Mach number from impact pressure qc and static pressure p.

    Inversion M = sqrt(5 * ((qc/p + 1)^(1/3.5) - 1)), subsonic branch
    only. ValueError if qc < 0, p <= 0, or qc/p >= the sonic ratio
    0.8929 where the inversion is non-unique.
    """
    if qc < 0:
        raise ValueError("impact pressure must be >= 0, got %r" % (qc,))
    if pressure <= 0:
        raise ValueError("static pressure must be > 0, got %r" % (pressure,))
    ratio = qc / pressure
    if ratio >= QC_SONIC_RATIO:
        raise ValueError(
            "subsonic branch only: qc/p %r implies M >= 1" % (ratio,)
        )
    return math.sqrt(5.0 * ((ratio + 1.0) ** (1.0 / 3.5) - 1.0))


def calibrated_from_impact_pressure(qc):
    """Calibrated airspeed (m/s) from impact pressure qc at sea level.

    CAS = A0 * sqrt(5 * ((qc/P0 + 1)^(2/7) - 1)), the airspeed-indicator
    compressibility calibration evaluated at ISA sea level. ValueError
    if qc < 0.
    """
    if qc < 0:
        raise ValueError("impact pressure must be >= 0, got %r" % (qc,))
    return A0_ISA * math.sqrt(5.0 * ((qc / P0_ISA + 1.0) ** (2.0 / 7.0) - 1.0))


def _impact_pressure_from_calibrated(cas_ms):
    """Exact algebraic inverse of calibrated_from_impact_pressure.

    qc = P0 * ((1 + (cas/A0)^2/5)^3.5 - 1). ValueError if cas < 0.
    """
    if cas_ms < 0:
        raise ValueError("calibrated airspeed must be >= 0, got %r" % (cas_ms,))
    return P0_ISA * ((1.0 + (cas_ms / A0_ISA) ** 2 / 5.0) ** 3.5 - 1.0)


def calibrated_from_true_airspeed(tas_ms, altitude_m):
    """CAS (m/s) from true airspeed at altitude, two-step compressible chain.

    Local ISA state gives the speed of sound; M = TAS/a; qc follows from
    the impact pressure relation at the local static pressure; CAS is the
    sea-level calibration of that qc. ValueError if TAS < 0 or M >= 1.
    """
    if tas_ms < 0:
        raise ValueError("true airspeed must be >= 0, got %r" % (tas_ms,))
    state = isa_state(altitude_m)
    mach = tas_ms / state["a"]
    if mach >= 1:
        raise ValueError("subsonic domain only: Mach %r >= 1" % (mach,))
    qc = impact_pressure_from_mach(mach, state["p"])
    return calibrated_from_impact_pressure(qc)


def true_from_calibrated(cas_ms, altitude_m):
    """TAS (m/s) from calibrated airspeed at altitude, inverse chain.

    qc comes from the exact algebraic inverse of the CAS calibration;
    the local static pressure and the subsonic qc inversion give M; TAS
    = M * a. ValueError if CAS < 0. Round trip with
    calibrated_from_true_airspeed is exact to < 1e-9 m/s.
    """
    if cas_ms < 0:
        raise ValueError("calibrated airspeed must be >= 0, got %r" % (cas_ms,))
    qc = _impact_pressure_from_calibrated(cas_ms)
    state = isa_state(altitude_m)
    mach = mach_from_impact_pressure(qc, state["p"])
    return mach * state["a"]


def equivalent_from_true(tas_ms, rho):
    """EAS (m/s) from true airspeed and local density.

    EAS = TAS * sqrt(rho/rho0). ValueError if TAS < 0 or rho <= 0.
    """
    if tas_ms < 0:
        raise ValueError("true airspeed must be >= 0, got %r" % (tas_ms,))
    if rho <= 0:
        raise ValueError("density must be > 0, got %r" % (rho,))
    return tas_ms * math.sqrt(rho / RHO0_ISA)


def true_from_equivalent(eas_ms, rho):
    """TAS (m/s) from equivalent airspeed and local density.

    TAS = EAS / sqrt(rho/rho0). ValueError if EAS < 0 or rho <= 0.
    """
    if eas_ms < 0:
        raise ValueError("equivalent airspeed must be >= 0, got %r" % (eas_ms,))
    if rho <= 0:
        raise ValueError("density must be > 0, got %r" % (rho,))
    return eas_ms / math.sqrt(rho / RHO0_ISA)


def mach_from_true_airspeed(tas_ms, speed_of_sound):
    """Mach number from true airspeed and the local speed of sound.

    M = TAS / a. ValueError if TAS < 0 or speed of sound <= 0.
    """
    if tas_ms < 0:
        raise ValueError("true airspeed must be >= 0, got %r" % (tas_ms,))
    if speed_of_sound <= 0:
        raise ValueError("speed of sound must be > 0, got %r" % (speed_of_sound,))
    return tas_ms / speed_of_sound


def airspeed_chain(altitude_m, cas_kt=None, tas_ms=None, eas_kt=None, mach=None):
    """Full CAS/EAS/TAS/Mach set from exactly one speed input at altitude.

    Returns dict {altitude_m, p, rho, a, mach, cas_kt, eas_kt, tas_ms,
    qc_Pa} with every quantity filled by the appropriate chain leg:
    cas_kt and eas_kt are in knots, tas_ms in m/s, qc_Pa in Pa.
    ValueError if zero or more than one input is given, or any input is
    negative.
    """
    _check_altitude(altitude_m)
    inputs = [v for v in (cas_kt, tas_ms, eas_kt, mach) if v is not None]
    if len(inputs) != 1:
        raise ValueError(
            "exactly one speed input required, got %d" % len(inputs)
        )
    for v in inputs:
        if v < 0:
            raise ValueError("speed inputs must be >= 0, got %r" % (v,))
    state = isa_state(altitude_m)
    p = state["p"]
    rho = state["rho"]
    a = state["a"]
    if mach is not None:
        qc = impact_pressure_from_mach(mach, p)
        cas_ms = calibrated_from_impact_pressure(qc)
        tas_ms = mach * a
    elif cas_kt is not None:
        cas_ms = cas_kt * KT_TO_MS
        qc = _impact_pressure_from_calibrated(cas_ms)
        mach = mach_from_impact_pressure(qc, p)
        tas_ms = mach * a
    elif tas_ms is not None:
        mach = mach_from_true_airspeed(tas_ms, a)
        if mach >= 1:
            raise ValueError("subsonic domain only: Mach %r >= 1" % (mach,))
        qc = impact_pressure_from_mach(mach, p)
        cas_ms = calibrated_from_impact_pressure(qc)
    else:  # eas_kt is the single input
        eas_ms = eas_kt * KT_TO_MS
        tas_ms = true_from_equivalent(eas_ms, rho)
        mach = mach_from_true_airspeed(tas_ms, a)
        if mach >= 1:
            raise ValueError("subsonic domain only: Mach %r >= 1" % (mach,))
        qc = impact_pressure_from_mach(mach, p)
        cas_ms = calibrated_from_impact_pressure(qc)
    eas_ms = equivalent_from_true(tas_ms, rho)
    return {
        "altitude_m": altitude_m,
        "p": p,
        "rho": rho,
        "a": a,
        "mach": mach,
        "cas_kt": cas_ms / KT_TO_MS,
        "eas_kt": eas_ms / KT_TO_MS,
        "tas_ms": tas_ms,
        "qc_Pa": qc,
    }
