#!/usr/bin/env python3
"""Thrust vector control (TVC) logic for a rocket: deflection geometry.

Common-knowledge summary (standards-map.yaml, ecss: free ESA download,
reference-only): ECSS space-systems standards frame rocket propulsion
engineering context. TVC force and torque geometry is standard
mechanics: a thrust vector deflected by an angle delta produces a side
force T * sin(delta), a control torque about the vehicle center of
gravity of T * sin(delta) * L where L is the moment arm from the gimbal
point to the center of gravity, and an axial thrust loss
T * (1 - cos(delta)) from the cosine projection.

Units (ONE convention, all SI base): thrust in N, deflection angle in
radians, moment arm in m, side force in N, torque in N*m.
"""

import math

MAX_DEFLECTION_RAD = math.pi / 2.0  # +/-90 deg hard domain limit


def _check_thrust(thrust):
    if thrust < 0:
        raise ValueError("thrust must be >= 0, got %r" % (thrust,))


def _check_deflection(deflection_rad):
    if not (-MAX_DEFLECTION_RAD <= deflection_rad <= MAX_DEFLECTION_RAD):
        raise ValueError(
            "deflection angle must be within +/-90 deg, got %r rad"
            % (deflection_rad,)
        )


def side_force(thrust, deflection_rad):
    """Lateral control force from a deflected thrust vector, in N.

    F_side = T * sin(delta). A positive deflection (nozzle pitched
    toward the +y direction) gives a positive side force along +y.

    Raises ValueError when thrust is negative or the deflection angle
    lies outside +/-90 deg.
    """
    _check_thrust(thrust)
    _check_deflection(deflection_rad)
    return thrust * math.sin(deflection_rad)


def control_torque(thrust, deflection_rad, moment_arm):
    """Control torque about the vehicle center of gravity, in N*m.

    M = T * sin(delta) * L, where L is the moment arm from the gimbal
    point to the center of gravity.

    Raises ValueError when thrust is negative, the deflection angle
    lies outside +/-90 deg, or the moment arm is negative.
    """
    _check_thrust(thrust)
    _check_deflection(deflection_rad)
    if moment_arm < 0:
        raise ValueError("moment arm must be >= 0, got %r" % (moment_arm,))
    return thrust * math.sin(deflection_rad) * moment_arm


def axial_thrust_ratio(deflection_rad):
    """Fraction of the thrust retained along the vehicle axis, cos(delta).

    Raises ValueError when the deflection angle lies outside +/-90 deg.
    """
    _check_deflection(deflection_rad)
    return math.cos(deflection_rad)


def axial_thrust_loss(thrust, deflection_rad):
    """Axial thrust lost to the deflection, in N: T * (1 - cos(delta)).

    Raises ValueError when thrust is negative or the deflection angle
    lies outside +/-90 deg.
    """
    _check_thrust(thrust)
    _check_deflection(deflection_rad)
    return thrust * (1.0 - math.cos(deflection_rad))


def deflection_angle_for_side_force(side_force_required, thrust):
    """Gimbal deflection angle (rad) that produces the required side force.

    delta = arcsin(F / T). Raises ValueError when the requirement
    cannot be met by pure deflection (|F| > T) or when thrust is not
    positive.
    """
    if thrust <= 0:
        raise ValueError("thrust must be > 0 to deflect, got %r" % (thrust,))
    ratio = side_force_required / thrust
    if abs(ratio) > 1.0:
        raise ValueError(
            "side force %r exceeds the thrust %r; cannot be met by deflection"
            % (side_force_required, thrust)
        )
    return math.asin(ratio)


def actuator_authority_required(required_torque, moment_arm):
    """Side force the TVC actuator must deliver, in N: F = M / L.

    The actuator authority requirement is the control force at the
    gimbal point that produces the demanded control torque about the
    center of gravity with the given moment arm.

    Raises ValueError when the required torque is negative or the
    moment arm is not positive.
    """
    if required_torque < 0:
        raise ValueError("required torque must be >= 0, got %r" % (required_torque,))
    if moment_arm <= 0:
        raise ValueError("moment arm must be > 0, got %r" % (moment_arm,))
    return required_torque / moment_arm
