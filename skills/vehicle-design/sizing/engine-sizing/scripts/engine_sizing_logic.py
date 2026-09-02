"""Engine sizing math for vehicle design propulsion selection.

Deterministic, offline, stdlib-only helpers for sizing the propulsion
system of a transport aircraft: sea level static thrust from the design
thrust to weight ratio and the takeoff gross weight; thrust lapse with
altitude through the ISA density ratio; installed thrust loss at
takeoff; cruise and top of climb thrust margin against the drag;
specific fuel consumption to fuel flow; engine weight from the engine
thrust to weight ratio; and the thrust split across the number of
engines. All units are SI: thrust and weight in newtons, altitude in
meters, fuel flow in kg/s, SFC in kg/(N*s).

Contract exercised by scripts/test_engine_sizing.py.
"""

import math

G0 = 9.80665  # standard gravity, m/s^2
RHO0 = 1.225  # sea level ISA air density, kg/m^3
T0 = 288.15  # sea level ISA temperature, K
LAPSE = 0.0065  # ISA troposphere temperature lapse rate, K/m
DENSITY_EXPONENT = 4.255879  # g0 / (R * L) - 1 for the density ratio
TROPOPAUSE = 11000.0  # troposphere top, m
LB_PER_LBF_HR_TO_KG_PER_N_S = 0.45359237 / (4.4482216 * 3600.0)


def sea_level_static_thrust(weight, thrust_weight_ratio):
    """Return the sea level static thrust in newtons.

    T_SL = (T/W) * W, the design point that the engine selection must
    meet at takeoff gross weight. A transport aircraft at 500000 N with
    a design thrust to weight ratio of 0.25 needs 125000 N of sea level
    static thrust.

    Raises ValueError for a non-positive weight or thrust to weight
    ratio.
    """
    if weight <= 0:
        raise ValueError("weight must be > 0, got %r" % (weight,))
    if thrust_weight_ratio <= 0:
        raise ValueError(
            "thrust to weight ratio must be > 0, got %r" % (thrust_weight_ratio,)
        )
    return thrust_weight_ratio * weight


def isa_density_ratio(altitude):
    """Return the ISA air density ratio sigma = rho / rho0 at altitude.

    In the troposphere (0 to 11000 m) the temperature falls at
    0.0065 K/m and the density ratio is
    sigma = (1 - L * h / T0) ** (g0 / (R * L) - 1).
    At sea level sigma is 1.0; at 11000 m it is about 0.297.

    Raises ValueError for an altitude outside the troposphere.
    """
    if altitude < 0:
        raise ValueError("altitude must be >= 0, got %r" % (altitude,))
    if altitude > TROPOPAUSE:
        raise ValueError(
            "altitude must be <= %g m (tropopause), got %r" % (TROPOPAUSE, altitude)
        )
    temp_ratio = 1.0 - LAPSE * altitude / T0
    return temp_ratio ** DENSITY_EXPONENT


def thrust_at_altitude(thrust_sl, altitude, lapse_exponent=0.7):
    """Return the available thrust in newtons at altitude.

    T(h) = T_SL * sigma ** m, with sigma the ISA density ratio and m
    the thrust lapse exponent. High bypass turbofans retain thrust
    better at altitude (m near 0.7); a turbojet lapses closer to the
    density ratio itself (m near 1.0).

    Raises ValueError for a non-positive thrust, an altitude outside
    the troposphere, or a non-positive lapse exponent.
    """
    if thrust_sl <= 0:
        raise ValueError("sea level thrust must be > 0, got %r" % (thrust_sl,))
    if lapse_exponent <= 0:
        raise ValueError(
            "lapse exponent must be > 0, got %r" % (lapse_exponent,)
        )
    sigma = isa_density_ratio(altitude)
    return thrust_sl * sigma ** lapse_exponent


def takeoff_thrust(thrust_sl, installation_loss=0.02):
    """Return the installed takeoff thrust in newtons.

    T_TO = T_SL * (1 - loss), with the installation loss covering the
    intake, nacelle, and auxiliary power bleed. Losses of 0.02 to 0.04
    are typical for a padded turbofan installation.

    Raises ValueError for a non-positive thrust or a loss outside
    [0, 1).
    """
    if thrust_sl <= 0:
        raise ValueError("sea level thrust must be > 0, got %r" % (thrust_sl,))
    if installation_loss < 0 or installation_loss >= 1.0:
        raise ValueError(
            "installation loss must be in [0, 1), got %r" % (installation_loss,)
        )
    return thrust_sl * (1.0 - installation_loss)


def cruise_thrust_required(weight, lift_drag_ratio):
    """Return the thrust required in newtons in level cruise.

    T_req = W / (L/D), the drag the engine must overcome at cruise
    weight. A 500000 N aircraft with an 18 to 1 lift to drag ratio
    needs about 27778 N.

    Raises ValueError for a non-positive weight or lift to drag ratio.
    """
    if weight <= 0:
        raise ValueError("weight must be > 0, got %r" % (weight,))
    if lift_drag_ratio <= 0:
        raise ValueError(
            "lift to drag ratio must be > 0, got %r" % (lift_drag_ratio,)
        )
    return weight / lift_drag_ratio


def thrust_margin(available_thrust, required_thrust):
    """Return the thrust margin ratio available / required.

    A margin of 1.0 means the thrust exactly meets the demand; above
    1.0 there is excess thrust for climb or acceleration. The top of
    climb check keeps the margin above 1.0 with the required climb
    gradient.

    Raises ValueError for a non-positive required thrust.
    """
    if required_thrust <= 0:
        raise ValueError(
            "required thrust must be > 0, got %r" % (required_thrust,)
        )
    return available_thrust / required_thrust


def top_of_climb_margin(
    thrust_sl,
    altitude,
    weight,
    lift_drag_ratio,
    lapse_exponent=0.7,
):
    """Return the thrust margin at the top of climb altitude.

    The thrust available at altitude from thrust_at_altitude is divided
    by the cruise thrust required at the top of climb weight and lift
    to drag ratio. A margin below 1.0 means the engine cannot hold the
    top of climb condition and the sea level thrust must grow.

    Raises ValueError for a non-positive sea level thrust, weight, or
    lift to drag ratio, an altitude outside the troposphere, or a
    non-positive lapse exponent.
    """
    if weight <= 0:
        raise ValueError("weight must be > 0, got %r" % (weight,))
    if lift_drag_ratio <= 0:
        raise ValueError(
            "lift to drag ratio must be > 0, got %r" % (lift_drag_ratio,)
        )
    available = thrust_at_altitude(thrust_sl, altitude, lapse_exponent)
    required = cruise_thrust_required(weight, lift_drag_ratio)
    return thrust_margin(available, required)


def sfc_from_lb_per_lbf_hr(lb_per_lbf_hr):
    """Return the thrust specific fuel consumption in kg/(N*s).

    Converts the English unit convention (pounds of fuel per pound of
    thrust per hour) to SI. A modern high bypass turbofan at 0.5
    lb/(lbf*h) is about 1.4163e-5 kg/(N*s).

    Raises ValueError for a non-positive SFC value.
    """
    if lb_per_lbf_hr <= 0:
        raise ValueError(
            "SFC must be > 0, got %r" % (lb_per_lbf_hr,)
        )
    return lb_per_lbf_hr * LB_PER_LBF_HR_TO_KG_PER_N_S


def fuel_flow(sfc, thrust):
    """Return the fuel flow in kg/s for an SFC in kg/(N*s) and a thrust
    in newtons.

    mdot = SFC * T. At 1.4163e-5 kg/(N*s) and 27778 N the flow is
    about 0.3934 kg/s, roughly 1416 kg/h.

    Raises ValueError for a non-positive SFC or thrust.
    """
    if sfc <= 0:
        raise ValueError("SFC must be > 0, got %r" % (sfc,))
    if thrust <= 0:
        raise ValueError("thrust must be > 0, got %r" % (thrust,))
    return sfc * thrust


def engine_weight(thrust_sl, engine_thrust_weight_ratio=5.0):
    """Return the installed engine weight in newtons.

    W_eng = T_SL / (T/W)_eng, with the engine thrust to weight ratio
    near 5 for a modern turbofan (4 to 6 is the typical band). The
    weight is a force in newtons; divide by g0 for kilograms.

    Raises ValueError for a non-positive thrust or engine ratio.
    """
    if thrust_sl <= 0:
        raise ValueError("sea level thrust must be > 0, got %r" % (thrust_sl,))
    if engine_thrust_weight_ratio <= 0:
        raise ValueError(
            "engine thrust to weight ratio must be > 0, got %r"
            % (engine_thrust_weight_ratio,)
        )
    return thrust_sl / engine_thrust_weight_ratio


def thrust_per_engine(total_thrust, number_of_engines):
    """Return the thrust per engine in newtons.

    Splitting the total sea level static thrust across the propulsion
    units, for example 125000 N over two engines is 62500 N per engine.
    The split is the entry to the engine catalogue lookup.

    Raises ValueError for a non-positive total thrust or a number of
    engines below one.
    """
    if total_thrust <= 0:
        raise ValueError("total thrust must be > 0, got %r" % (total_thrust,))
    if number_of_engines < 1:
        raise ValueError(
            "number of engines must be >= 1, got %r" % (number_of_engines,)
        )
    return total_thrust / number_of_engines


def matched_engine_count(required_thrust, thrust_per_engine):
    """Return the smallest whole number of engines that covers the
    required thrust.

    ceil(required / per_engine), the count that closes the sizing loop
    when the catalogue engine is smaller than the total demand. A
    required thrust of 125000 N with 60000 N per engine needs 3 units.

    Raises ValueError for a non-positive required thrust or per engine
    thrust.
    """
    if required_thrust <= 0:
        raise ValueError(
            "required thrust must be > 0, got %r" % (required_thrust,)
        )
    if thrust_per_engine <= 0:
        raise ValueError(
            "thrust per engine must be > 0, got %r" % (thrust_per_engine,)
        )
    return int(math.ceil(required_thrust / thrust_per_engine))
