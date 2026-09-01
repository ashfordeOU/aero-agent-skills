#!/usr/bin/env python3
"""Specific air range cruise fuel economy logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): the specific air range SAR is the distance flown
per unit fuel mass, SAR = V / mdot for true airspeed V and fuel flow
mdot. Fuel flow follows from the thrust specific fuel consumption
and the required thrust, mdot = TSFC * T. In steady cruise the
instantaneous range from aerodynamic inputs is SAR = V * (L/D) /
(TSFC * W), with the weight in newtons. The fuel burn for a block
distance d is m_fuel = d / SAR. Units: speed in m/s, fuel flow in
kg/s, TSFC in kg/(N s), weight in newtons, SAR in meters per
kilogram, distance in meters, fuel burn in kilograms.
"""


def specific_air_range(v_tas, fuel_flow):
    """Specific air range in meters per kilogram: V / mdot.

    Raises ValueError on non-positive true airspeed or fuel flow.
    """
    if v_tas <= 0:
        raise ValueError("true airspeed must be > 0 m/s, got %r" % (v_tas,))
    if fuel_flow <= 0:
        raise ValueError("fuel flow must be > 0 kg/s, got %r" % (fuel_flow,))
    return v_tas / fuel_flow


def fuel_flow_from_thrust(tsfc, thrust):
    """Fuel flow in kg/s from thrust specific fuel consumption and thrust."""
    if tsfc <= 0:
        raise ValueError("TSFC must be > 0 kg/(N s), got %r" % (tsfc,))
    if thrust <= 0:
        raise ValueError("thrust must be > 0 N, got %r" % (thrust,))
    return tsfc * thrust


def instantaneous_range(v_tas, tsfc, weight_n, ld):
    """Instantaneous specific air range in m/kg: V * (L/D) / (TSFC * W).

    Weight is in newtons; raises ValueError on non-positive inputs.
    """
    if v_tas <= 0:
        raise ValueError("true airspeed must be > 0 m/s, got %r" % (v_tas,))
    if tsfc <= 0:
        raise ValueError("TSFC must be > 0 kg/(N s), got %r" % (tsfc,))
    if weight_n <= 0:
        raise ValueError("weight must be > 0 N, got %r" % (weight_n,))
    if ld <= 0:
        raise ValueError("lift to drag ratio must be > 0, got %r" % (ld,))
    return v_tas * ld / (tsfc * weight_n)


def sector_fuel_burn(sar, distance):
    """Fuel burn in kg for a block distance at a given specific air range.

    Raises ValueError on non-positive SAR or negative distance.
    """
    if sar <= 0:
        raise ValueError("specific air range must be > 0 m/kg, got %r" % (sar,))
    if distance < 0:
        raise ValueError("distance must be >= 0 m, got %r" % (distance,))
    return distance / sar
