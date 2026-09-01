#!/usr/bin/env python3
"""Thrust required and power required curve logic for level unaccelerated
flight (paraphrase, summary only).

For level unaccelerated flight the lift equals the weight and the thrust
required equals the drag. With a parabolic drag polar,
CD = cd0 + k CL^2, and CL = 2 W / (rho V^2 S), the thrust required is

  T_req = 0.5 rho V^2 S cd0 + 2 k W^2 / (rho V^2 S)

with weight W in newtons, wing area S in m^2, air density rho in kg/m^3,
and speed V in m/s equivalent airspeed (EAS). The power required is
P_req = T_req V. Compressibility is ignored, the usual low speed
assumption.

Characteristic points (level flight, parabolic polar):
- minimum drag speed V_md = sqrt((2 W / (rho S)) sqrt(k / cd0)), where
  the parasite drag equals the induced drag;
- minimum power speed V_mp = sqrt((2 W / (rho S)) sqrt(k / (3 cd0))),
  where the induced drag is three times the parasite drag;
- maximum lift to drag ratio (L/D)_max = 1 / (2 sqrt(cd0 k));
- minimum thrust T_min = W / (L/D)_max = 2 W sqrt(cd0 k).

Worked example (pinned by the contract test): weight 650000 N, wing
area 122 m^2, rho 1.225 kg/m^3 at sea level, cd0 0.02, k 0.042 gives
V_md about 112.3 m/s EAS, V_mp about 85.3 m/s EAS, (L/D)_max about
17.25, and T_min about 37.7 kN, equal to the thrust required at the
minimum drag speed.

FAR-25 and CS-25 performance requirements frame the level flight
performance analysis (summary reference only, standards-map.yaml).

Functions:
- lift_coefficient(v_eas, weight, wing_area, rho)
- drag_coefficient(v_eas, weight, wing_area, rho, cd0, k)
- thrust_required(v_eas, weight, wing_area, rho, cd0, k)
- power_required(v_eas, weight, wing_area, rho, cd0, k)
- minimum_drag_speed(weight, wing_area, rho, cd0, k)
- minimum_power_speed(weight, wing_area, rho, cd0, k)
- maximum_lift_to_drag(cd0, k)
- minimum_thrust(weight, cd0, k)
"""

import math


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    return float(value)


def _positive(value, name):
    v = _number(value, name)
    if v <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return v


def lift_coefficient(v_eas, weight, wing_area, rho):
    """Lift coefficient for level flight: CL = 2 W / (rho V^2 S).

    Worked: (112.27, 650000, 122, 1.225) returns 0.6901, the lift
    coefficient at the minimum drag speed, equal to sqrt(cd0 / k) for
    cd0 0.02 and k 0.042. Raises ValueError on non-positive speed,
    weight, wing area, or density.
    """
    v = _positive(v_eas, "v_eas")
    w = _positive(weight, "weight")
    s = _positive(wing_area, "wing_area")
    r = _positive(rho, "rho")
    return 2.0 * w / (r * v * v * s)


def drag_coefficient(v_eas, weight, wing_area, rho, cd0, k):
    """Total drag coefficient from the parabolic polar: CD = cd0 + k CL^2.

    Worked: (112.27, 650000, 122, 1.225, 0.02, 0.042) returns 0.0400,
    twice cd0 at the minimum drag speed where parasite equals induced.
    Raises ValueError on non-positive inputs.
    """
    v = _positive(v_eas, "v_eas")
    w = _positive(weight, "weight")
    s = _positive(wing_area, "wing_area")
    r = _positive(rho, "rho")
    c0 = _positive(cd0, "cd0")
    kk = _positive(k, "k")
    cl = 2.0 * w / (r * v * v * s)
    return c0 + kk * cl * cl


def thrust_required(v_eas, weight, wing_area, rho, cd0, k):
    """Thrust required for level unaccelerated flight in newtons.

    T_req = 0.5 rho V^2 S cd0 + 2 k W^2 / (rho V^2 S). Worked:
    (112.27, 650000, 122, 1.225, 0.02, 0.042) returns about 37678 N,
    the curve minimum; (85.31, ...) returns about 43506 N, and
    (60.0, ...) returns about 71344 N. Raises ValueError on
    non-positive inputs.
    """
    v = _positive(v_eas, "v_eas")
    w = _positive(weight, "weight")
    s = _positive(wing_area, "wing_area")
    r = _positive(rho, "rho")
    c0 = _positive(cd0, "cd0")
    kk = _positive(k, "k")
    parasite = 0.5 * r * v * v * s * c0
    induced = 2.0 * kk * w * w / (r * v * v * s)
    return parasite + induced


def power_required(v_eas, weight, wing_area, rho, cd0, k):
    """Power required in watts: P_req = T_req V.

    Worked: (112.27, 650000, 122, 1.225, 0.02, 0.042) returns about
    4.23e6 W; (85.31, ...) returns about 3.71e6 W, the curve minimum.
    Raises ValueError on non-positive inputs.
    """
    v = _positive(v_eas, "v_eas")
    t = thrust_required(v, weight, wing_area, rho, cd0, k)
    return t * v


def minimum_drag_speed(weight, wing_area, rho, cd0, k):
    """Minimum drag speed in m/s EAS.

    V_md = sqrt((2 W / (rho S)) sqrt(k / cd0)). Worked:
    (650000, 122, 1.225, 0.02, 0.042) returns about 112.27 m/s.
    Raises ValueError on non-positive inputs.
    """
    w = _positive(weight, "weight")
    s = _positive(wing_area, "wing_area")
    r = _positive(rho, "rho")
    c0 = _positive(cd0, "cd0")
    kk = _positive(k, "k")
    return math.sqrt((2.0 * w / (r * s)) * math.sqrt(kk / c0))


def minimum_power_speed(weight, wing_area, rho, cd0, k):
    """Minimum power speed in m/s EAS.

    V_mp = sqrt((2 W / (rho S)) sqrt(k / (3 cd0))). Worked:
    (650000, 122, 1.225, 0.02, 0.042) returns about 85.31 m/s, equal
    to the minimum drag speed divided by 3^(1/4). Raises ValueError on
    non-positive inputs.
    """
    w = _positive(weight, "weight")
    s = _positive(wing_area, "wing_area")
    r = _positive(rho, "rho")
    c0 = _positive(cd0, "cd0")
    kk = _positive(k, "k")
    return math.sqrt((2.0 * w / (r * s)) * math.sqrt(kk / (3.0 * c0)))


def maximum_lift_to_drag(cd0, k):
    """Maximum lift to drag ratio of the parabolic polar.

    (L/D)_max = 1 / (2 sqrt(cd0 k)). Worked: (0.02, 0.042) returns
    about 17.25. Raises ValueError on non-positive inputs.
    """
    c0 = _positive(cd0, "cd0")
    kk = _positive(k, "k")
    return 1.0 / (2.0 * math.sqrt(c0 * kk))


def minimum_thrust(weight, cd0, k):
    """Minimum thrust in newtons at the maximum lift to drag ratio.

    T_min = 2 W sqrt(cd0 k). Worked: (650000, 0.02, 0.042) returns
    about 37677 N, equal to the thrust required at the minimum drag
    speed. Raises ValueError on non-positive inputs.
    """
    w = _positive(weight, "weight")
    c0 = _positive(cd0, "cd0")
    kk = _positive(k, "k")
    return 2.0 * w * math.sqrt(c0 * kk)


def demonstrate():
    """Print a demonstration of the thrust required analysis."""
    w, s, rho, cd0, k = 650000.0, 122.0, 1.225, 0.02, 0.042
    v_md = minimum_drag_speed(w, s, rho, cd0, k)
    v_mp = minimum_power_speed(w, s, rho, cd0, k)
    print("minimum_drag_speed -> %.2f m/s EAS" % v_md)
    print("minimum_power_speed -> %.2f m/s EAS" % v_mp)
    print("maximum_lift_to_drag -> %.3f" % maximum_lift_to_drag(cd0, k))
    print("minimum_thrust -> %.1f N" % minimum_thrust(w, cd0, k))
    for v in (60.0, v_mp, v_md, 140.0):
        print("thrust_required(%.1f) -> %.1f N, power_required -> %.3e W"
              % (v, thrust_required(v, w, s, rho, cd0, k),
                 power_required(v, w, s, rho, cd0, k)))


if __name__ == "__main__":
    demonstrate()
