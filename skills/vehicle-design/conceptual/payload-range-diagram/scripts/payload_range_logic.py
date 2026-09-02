#!/usr/bin/env python3
"""Payload-range diagram logic for conceptual aircraft design
(paraphrase, common knowledge; no standard text reproduced).

Common-knowledge summary (standards-map.yaml: far-25 and cs-25 are
regulation context only, never quoted): the payload-range diagram
trades payload against range at three corner points. Point A carries
the maximum structural payload; its fuel is capped by the maximum
takeoff weight (MTOW) allowance and by tank capacity, whichever binds
first. Point B carries full fuel; its payload is capped by MTOW.
Point C is the ferry range: full fuel and zero payload. The Breguet
range equation turns fuel into range, and a reserve fuel policy holds
back a fraction of the loaded fuel that may never be burned. The fuel
fraction ties the diagram to weight sizing. The reserve fraction is a
project policy input; sanity thresholds are project-defined bands.
"""

import math

G0 = 9.80665  # standard gravity, m/s^2


def range_factor(speed, tsfc, l_over_d):
    """Breguet range factor K = V / (TSFC * g0) * L/D, in meters."""
    if speed <= 0 or tsfc <= 0 or l_over_d <= 0:
        raise ValueError("speed, tsfc, and l_over_d must be > 0")
    return speed / (tsfc * G0) * l_over_d


def breguet_range(K, w0, w1):
    """Still-air range (m) = K * ln(w0 / w1); requires w0 > w1 > 0."""
    if K <= 0:
        raise ValueError("range factor K must be > 0")
    if w0 <= w1 or w1 <= 0:
        raise ValueError("need w0 > w1 > 0")
    return K * math.log(w0 / w1)


def range_for_fuel(oew, payload, fuel, reserve_fraction, K):
    """Range (m) for a given payload and fuel mass on board.

    reserve_fraction is the fraction of the loaded fuel held in
    reserve and never burned. w0 is the takeoff weight (OEW + payload
    + fuel); w1 the landing weight (OEW + payload + reserve). Zero
    fuel gives zero range.
    """
    if oew <= 0:
        raise ValueError("oew must be > 0")
    if payload < 0:
        raise ValueError("payload must be >= 0")
    if fuel < 0:
        raise ValueError("fuel must be >= 0")
    if K <= 0:
        raise ValueError("range factor K must be > 0")
    if not (0.0 <= reserve_fraction < 1.0):
        raise ValueError("reserve_fraction must be in [0, 1)")
    if fuel == 0.0:
        return 0.0
    reserve = reserve_fraction * fuel
    burnable = fuel - reserve
    if burnable <= 0.0:
        return 0.0
    w0 = oew + payload + fuel
    w1 = oew + payload + reserve
    return K * math.log(w0 / w1)


def max_payload_point(oew, max_payload, mtow, fuel_capacity,
                      reserve_fraction, K):
    """Corner A: payload and range at the maximum structural payload.

    Fuel at A is the smaller of tank capacity and the MTOW allowance
    (MTOW - OEW - max payload). mtow_limited is True when MTOW, not
    tank capacity, caps the fuel.
    """
    if oew <= 0 or max_payload <= 0:
        raise ValueError("oew and max_payload must be > 0")
    if mtow < oew + max_payload:
        raise ValueError("MTOW cannot carry the max payload")
    if fuel_capacity < 0:
        raise ValueError("fuel_capacity must be >= 0")
    if K <= 0:
        raise ValueError("range factor K must be > 0")
    if not (0.0 <= reserve_fraction < 1.0):
        raise ValueError("reserve_fraction must be in [0, 1)")
    allowance = mtow - oew - max_payload
    fuel_a = min(fuel_capacity, allowance)
    rng = range_for_fuel(oew, max_payload, fuel_a, reserve_fraction, K)
    return {"payload": max_payload, "fuel": fuel_a, "range": rng,
            "mtow_limited": fuel_a < fuel_capacity}


def max_fuel_point(oew, max_payload, mtow, fuel_capacity,
                   reserve_fraction, K):
    """Corner B: payload and range with full fuel tanks.

    Payload at B is the smaller of max payload and the MTOW allowance
    (MTOW - OEW - full fuel).
    """
    if oew <= 0 or max_payload <= 0:
        raise ValueError("oew and max_payload must be > 0")
    if fuel_capacity < 0:
        raise ValueError("fuel_capacity must be >= 0")
    if K <= 0:
        raise ValueError("range factor K must be > 0")
    if not (0.0 <= reserve_fraction < 1.0):
        raise ValueError("reserve_fraction must be in [0, 1)")
    allowance = mtow - oew - fuel_capacity
    if allowance < 0:
        raise ValueError("full fuel exceeds MTOW with zero payload")
    payload_b = min(max_payload, allowance)
    rng = range_for_fuel(oew, payload_b, fuel_capacity, reserve_fraction, K)
    return {"payload": payload_b, "fuel": fuel_capacity, "range": rng}


def ferry_range(oew, mtow, fuel_capacity, reserve_fraction, K):
    """Corner C: range (m) with full fuel and zero payload."""
    if oew <= 0:
        raise ValueError("oew must be > 0")
    if fuel_capacity < 0:
        raise ValueError("fuel_capacity must be >= 0")
    if K <= 0:
        raise ValueError("range factor K must be > 0")
    if not (0.0 <= reserve_fraction < 1.0):
        raise ValueError("reserve_fraction must be in [0, 1)")
    if mtow < oew + fuel_capacity:
        raise ValueError("full fuel exceeds MTOW with zero payload")
    return range_for_fuel(oew, 0.0, fuel_capacity, reserve_fraction, K)


def payload_at_design_range(oew, max_payload, mtow, fuel_capacity,
                            reserve_fraction, K, design_range):
    """Payload (kg) available at the design range.

    Inside the max-payload segment (design range no larger than the
    range at max payload) the answer is max_payload. Beyond it the
    aircraft flies at MTOW and payload drops along the weight-limited
    line until the tanks are full, then along the fuel-volume line.
    Ranges past the ferry range are infeasible and raise ValueError.
    """
    if oew <= 0 or max_payload <= 0:
        raise ValueError("oew and max_payload must be > 0")
    if mtow < oew + max_payload:
        raise ValueError("MTOW cannot carry the max payload")
    if fuel_capacity < 0:
        raise ValueError("fuel_capacity must be >= 0")
    if K <= 0:
        raise ValueError("range factor K must be > 0")
    if design_range < 0:
        raise ValueError("design_range must be >= 0")
    if not (0.0 <= reserve_fraction < 1.0):
        raise ValueError("reserve_fraction must be in [0, 1)")
    r_a = max_payload_point(oew, max_payload, mtow, fuel_capacity,
                            reserve_fraction, K)["range"]
    if design_range <= r_a:
        return max_payload
    if mtow < oew + fuel_capacity:
        raise ValueError("full fuel exceeds MTOW with zero payload")
    r = math.exp(design_range / K)
    # MTOW-limited segment: weight fixed at MTOW, fuel F solves
    # K * ln(MTOW / (MTOW - F * (1 - reserve_fraction))) == design_range.
    fuel_mtow = mtow * (1.0 - 1.0 / r) / (1.0 - reserve_fraction)
    if fuel_mtow <= fuel_capacity:
        payload_mtow = mtow - oew - fuel_mtow
        if payload_mtow < 0.0:
            raise ValueError("design range exceeds the ferry range")
        return min(payload_mtow, max_payload)
    # Fuel-volume segment: full tanks, payload P solves
    # K * ln((OEW + P + F) / (OEW + P + reserve)) == design_range.
    reserve = reserve_fraction * fuel_capacity
    p = (fuel_capacity + oew - r * (oew + reserve)) / (r - 1.0)
    if p < 0.0 or not math.isfinite(p):
        raise ValueError("design range exceeds the ferry range")
    return p
