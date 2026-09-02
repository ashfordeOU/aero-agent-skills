#!/usr/bin/env python3
"""Nacelle geometric sizing logic (deterministic, stdlib only, offline).

Common-knowledge summary (standards-map.yaml: far-25, cs-25 reference-only):
the engine nacelle is sized geometrically around the fan or compressor
face. The fan face area follows from mass flow continuity
A1 = mdot / (rho * V) with the face velocity set by the Mach number and
the local speed of sound. The inlet highlight (lip) area is the fan face
area enlarged by a lip area ratio that the inlet designer chooses to
trade capture efficiency against spillage drag. The capture area A0 is
the free stream tube area that the same mass flow would occupy at the
flight Mach number, and A0/A1 expresses how strongly the inlet diffuses
the flow. The nacelle length scales with the fan diameter through a
length to diameter ratio, the cowl maximum thickness follows from a
thickness to chord ratio on the cowl chord, and the wetted area is the
axisymmetric outer surface of the cowl approximated from the maximum
diameter, length, and a shape factor. Nacelle drag is bookkept from the
wetted area and skin friction coefficient at the dynamic pressure,
split into friction, form (pressure) and interference components. All
formulas are conceptual sizing practice; FAR-25 and CS-25 are referenced
for the certification context only, never reproduced.
"""

import math

GAMMA_AIR = 1.4
R_AIR = 287.0  # J/(kg*K) specific gas constant for air


def area_from_mass_flow(mass_flow, density, velocity):
    """Cross section area from mass flow continuity: A = mdot / (rho * V).

    All inputs must be strictly positive; otherwise ValueError.
    """
    if mass_flow <= 0.0:
        raise ValueError("mass_flow must be positive: %r" % (mass_flow,))
    if density <= 0.0:
        raise ValueError("density must be positive: %r" % (density,))
    if velocity <= 0.0:
        raise ValueError("velocity must be positive: %r" % (velocity,))
    return mass_flow / (density * velocity)


def speed_of_sound(temperature, gamma=GAMMA_AIR, gas_constant=R_AIR):
    """Local speed of sound a = sqrt(gamma * R * T).

    Temperature must be strictly positive.
    """
    if temperature <= 0.0:
        raise ValueError("temperature must be positive: %r" % (temperature,))
    if gamma <= 0.0:
        raise ValueError("gamma must be positive: %r" % (gamma,))
    if gas_constant <= 0.0:
        raise ValueError("gas_constant must be positive: %r" % (gas_constant,))
    return math.sqrt(gamma * gas_constant * temperature)


def fan_face_area(mass_flow, density, mach, temperature,
                  gamma=GAMMA_AIR, gas_constant=R_AIR):
    """Fan (compressor) face area A1 from mass flow, density, Mach, T.

    Face velocity V1 = M * a with a the local speed of sound, then
    A1 = mdot / (rho * V1). Mach must be strictly positive; a zero or
    negative Mach (no flow) raises ValueError.
    """
    if mach <= 0.0:
        raise ValueError("mach must be positive: %r" % (mach,))
    velocity = mach * speed_of_sound(temperature, gamma, gas_constant)
    return area_from_mass_flow(mass_flow, density, velocity)


def diameter_from_area(area):
    """Diameter of a circular cross section: D = sqrt(4 * A / pi)."""
    if area <= 0.0:
        raise ValueError("area must be positive: %r" % (area,))
    return math.sqrt(4.0 * area / math.pi)


def fan_face_diameter(mass_flow, density, mach, temperature,
                      gamma=GAMMA_AIR, gas_constant=R_AIR):
    """Fan face diameter from mass flow, density, Mach and temperature."""
    return diameter_from_area(
        fan_face_area(mass_flow, density, mach, temperature,
                      gamma, gas_constant)
    )


def highlight_area_from_massflow(mass_flow, density, mach, temperature,
                                 lip_area_ratio=0.15,
                                 gamma=GAMMA_AIR, gas_constant=R_AIR):
    """Inlet highlight (lip) area from fan face mass flow and Mach.

    A_hi = A1 * (1 + lip_area_ratio). The lip area ratio is the
    fractional enlargement of the fan face area at the highlight,
    typically 0.10 to 0.20 for a high bypass turbofan; it must be
    non-negative (a zero ratio gives a flush lip).
    """
    if lip_area_ratio < 0.0:
        raise ValueError(
            "lip_area_ratio must be >= 0: %r" % (lip_area_ratio,)
        )
    a1 = fan_face_area(mass_flow, density, mach, temperature,
                       gamma, gas_constant)
    return a1 * (1.0 + lip_area_ratio)


def highlight_diameter_from_massflow(mass_flow, density, mach, temperature,
                                     lip_area_ratio=0.15,
                                     gamma=GAMMA_AIR, gas_constant=R_AIR):
    """Highlight diameter from fan face mass flow, Mach and lip ratio."""
    return diameter_from_area(
        highlight_area_from_massflow(mass_flow, density, mach, temperature,
                                     lip_area_ratio, gamma, gas_constant)
    )


def lip_area_ratio(highlight_area, fan_area):
    """Fractional lip enlargement: A_hi / A1 - 1.

    The highlight area must exceed the fan face area, both positive.
    """
    if highlight_area <= 0.0:
        raise ValueError("highlight_area must be positive: %r" % (highlight_area,))
    if fan_area <= 0.0:
        raise ValueError("fan_area must be positive: %r" % (fan_area,))
    if highlight_area <= fan_area:
        raise ValueError(
            "highlight_area must exceed fan_area: %r <= %r"
            % (highlight_area, fan_area)
        )
    return highlight_area / fan_area - 1.0


def capture_area(mass_flow, density, velocity):
    """Free stream capture area A0: area of the stream tube ingested.

    A0 = mdot / (rho_inf * V_inf) at the flight condition.
    """
    return area_from_mass_flow(mass_flow, density, velocity)


def capture_area_ratio(mass_flow, density, velocity, fan_area):
    """Capture area ratio A0/A1 at the flight condition.

    A0 from the free stream density and velocity, divided by the fan
    face area. Ratios above 1 mean the stream tube contracts into the
    inlet; ratios below 1 mean the inlet spills flow. The fan face area
    must be strictly positive.
    """
    if fan_area <= 0.0:
        raise ValueError("fan_area must be positive: %r" % (fan_area,))
    a0 = capture_area(mass_flow, density, velocity)
    return a0 / fan_area


def nacelle_length(fan_diameter, length_to_diameter_ratio=1.8):
    """Nacelle overall length: L = (L/D) * D_fan.

    High bypass turbofan nacelles typically run 1.5 to 2.2 fan
    diameters long; both inputs must be strictly positive.
    """
    if fan_diameter <= 0.0:
        raise ValueError("fan_diameter must be positive: %r" % (fan_diameter,))
    if length_to_diameter_ratio <= 0.0:
        raise ValueError(
            "length_to_diameter_ratio must be positive: %r"
            % (length_to_diameter_ratio,)
        )
    return length_to_diameter_ratio * fan_diameter


def cowl_thickness(cowl_chord, thickness_to_chord_ratio=0.10):
    """Cowl maximum thickness: t = (t/c) * chord.

    High bypass turbofan cowls are typically 0.08 to 0.12 of the cowl
    chord; the ratio must lie in (0, 0.5].
    """
    if cowl_chord <= 0.0:
        raise ValueError("cowl_chord must be positive: %r" % (cowl_chord,))
    if not (0.0 < thickness_to_chord_ratio <= 0.5):
        raise ValueError(
            "thickness_to_chord_ratio must be in (0, 0.5]: %r"
            % (thickness_to_chord_ratio,)
        )
    return thickness_to_chord_ratio * cowl_chord


def wetted_area(max_diameter, length, shape_factor=0.85):
    """Cowl wetted area: S_wet = pi * D_max * L * k.

    The axisymmetric outer surface is approximated as the product of
    the maximum circumference, the length, and a shape factor k in
    (0, 1] that accounts for the fore and aft taper (0.80 to 0.90 is
    the typical band for a high bypass turbofan cowl; 1.0 is a plain
    cylinder).
    """
    if max_diameter <= 0.0:
        raise ValueError("max_diameter must be positive: %r" % (max_diameter,))
    if length <= 0.0:
        raise ValueError("length must be positive: %r" % (length,))
    if not (0.0 < shape_factor <= 1.0):
        raise ValueError("shape_factor must be in (0, 1]: %r" % (shape_factor,))
    return math.pi * max_diameter * length * shape_factor


def nacelle_drag_bookkeeping(dynamic_pressure, wetted_area_value,
                             skin_friction_coefficient, form_factor=1.20,
                             interference_factor=0.05):
    """Nacelle drag split into friction, form and interference parts.

    friction_drag = q * S_wet * Cf; form_drag = friction * (FF - 1)
    captures the pressure drag of the finite thickness cowl; the
    interference_drag = friction * k_int captures pylon and installation
    interference. All inputs must be positive except the factors which
    must satisfy FF >= 1 and k_int >= 0. Returns a dict with the three
    components and the total.
    """
    if dynamic_pressure <= 0.0:
        raise ValueError(
            "dynamic_pressure must be positive: %r" % (dynamic_pressure,)
        )
    if wetted_area_value <= 0.0:
        raise ValueError(
            "wetted_area must be positive: %r" % (wetted_area_value,)
        )
    if skin_friction_coefficient <= 0.0:
        raise ValueError(
            "skin_friction_coefficient must be positive: %r"
            % (skin_friction_coefficient,)
        )
    if form_factor < 1.0:
        raise ValueError("form_factor must be >= 1: %r" % (form_factor,))
    if interference_factor < 0.0:
        raise ValueError(
            "interference_factor must be >= 0: %r" % (interference_factor,)
        )
    friction = (dynamic_pressure * wetted_area_value
                * skin_friction_coefficient)
    form = friction * (form_factor - 1.0)
    interference = friction * interference_factor
    return {
        "friction_drag": friction,
        "form_drag": form,
        "interference_drag": interference,
        "total_drag": friction + form + interference,
    }


def drag_coefficient(drag, dynamic_pressure, reference_area):
    """Non-dimensional nacelle drag: CD = D / (q * Sref).

    reference_area is the aircraft reference area (wing area) when the
    nacelle drag is being bookkept against aircraft level drag.
    """
    if drag < 0.0:
        raise ValueError("drag must be non-negative: %r" % (drag,))
    if dynamic_pressure <= 0.0:
        raise ValueError(
            "dynamic_pressure must be positive: %r" % (dynamic_pressure,)
        )
    if reference_area <= 0.0:
        raise ValueError(
            "reference_area must be positive: %r" % (reference_area,)
        )
    return drag / (dynamic_pressure * reference_area)
