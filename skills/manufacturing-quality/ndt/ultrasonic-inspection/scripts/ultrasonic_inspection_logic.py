"""Ultrasonic inspection (UT) math for aerospace NDT.

Deterministic, offline, stdlib-only helpers for pulse-echo ultrasonic
inspection: discontinuity depth from time of flight, wavelength and
near-field length for transducer and frequency selection, decibel to
amplitude ratio conversion, Snell's law for angle-beam probes, and
beam-spread half-angle. All units are SI: time in seconds, velocity in
m/s, frequency in Hz, length in meters.

Contract exercised by scripts/test_ultrasonic_inspection.py.
"""

import math

DEFAULT_STEEL_LONGITUDINAL = 5920.0  # m/s
DEFAULT_STEEL_SHEAR = 3230.0  # m/s


def time_of_flight_to_depth(tof, velocity):
    """Return the one-way depth of a reflector in meters.

    The pulse travels to the reflector and back, so depth is half the
    product of the round-trip time of flight and the wave velocity:
    depth = tof * velocity / 2.

    Raises ValueError for a negative time of flight or a non-positive
    velocity.
    """
    if tof < 0:
        raise ValueError("time of flight must be >= 0, got %r" % (tof,))
    if velocity <= 0:
        raise ValueError("velocity must be > 0, got %r" % (velocity,))
    return tof * velocity / 2.0


def wavelength(frequency, velocity):
    """Return the wavelength in meters: lambda = velocity / frequency.

    Raises ValueError for a non-positive frequency or velocity.
    """
    if frequency <= 0:
        raise ValueError("frequency must be > 0, got %r" % (frequency,))
    if velocity <= 0:
        raise ValueError("velocity must be > 0, got %r" % (velocity,))
    return velocity / frequency


def near_field_length(transducer_diameter, wavelength_value):
    """Return the near-field length N in meters for a circular piston.

    N = D^2 / (4 * lambda). Inside the near field the beam has
    amplitude maxima and minima, so amplitude-based sizing there is
    unreliable.

    Raises ValueError for a non-positive diameter or wavelength.
    """
    if transducer_diameter <= 0:
        raise ValueError(
            "transducer diameter must be > 0, got %r" % (transducer_diameter,)
        )
    if wavelength_value <= 0:
        raise ValueError("wavelength must be > 0, got %r" % (wavelength_value,))
    return transducer_diameter ** 2 / (4.0 * wavelength_value)


def db_to_amplitude_ratio(db):
    """Return the amplitude ratio for a decibel difference.

    Amplitude (voltage) ratio = 10^(db / 20). A 6 dB difference is a
    2x amplitude ratio, 20 dB is 10x, and -6 dB is half.

    Raises ValueError for a non-finite decibel value.
    """
    if not math.isfinite(db):
        raise ValueError("db must be finite, got %r" % (db,))
    return 10.0 ** (db / 20.0)


def snell_refraction_angle(incident_angle_deg, velocity_medium1, velocity_medium2):
    """Return the refracted angle in degrees via Snell's law.

    sin(theta2) = velocity_medium2 * sin(theta1) / velocity_medium1.
    Used for angle-beam probes, e.g. a Plexiglas wedge (longitudinal)
    generating a shear wave in steel.

    Raises ValueError for an incident angle outside 0-90 degrees, a
    non-positive velocity, or a refracted sine above 1 (total internal
    reflection, no transmitted wave).
    """
    if not 0.0 <= incident_angle_deg <= 90.0:
        raise ValueError(
            "incident angle must be in 0-90 degrees, got %r" % (incident_angle_deg,)
        )
    if velocity_medium1 <= 0:
        raise ValueError(
            "velocity of medium 1 must be > 0, got %r" % (velocity_medium1,)
        )
    if velocity_medium2 <= 0:
        raise ValueError(
            "velocity of medium 2 must be > 0, got %r" % (velocity_medium2,)
        )
    sin_theta2 = (
        velocity_medium2 * math.sin(math.radians(incident_angle_deg))
    ) / velocity_medium1
    if sin_theta2 > 1.0:
        raise ValueError(
            "no refracted wave: sin(theta2) = %.3f exceeds 1 (total internal "
            "reflection)" % sin_theta2
        )
    return math.degrees(math.asin(sin_theta2))


def beam_spread_half_angle(transducer_diameter, wavelength_value):
    """Return the far-field beam half-angle gamma in degrees.

    sin(gamma) = 1.22 * lambda / D for a circular piston transducer.
    The beam is considered spread beyond the near-field length.

    Raises ValueError for a non-positive diameter or wavelength, or
    when 1.22 * lambda / D exceeds 1 (no directive beam, unphysical).
    """
    if transducer_diameter <= 0:
        raise ValueError(
            "transducer diameter must be > 0, got %r" % (transducer_diameter,)
        )
    if wavelength_value <= 0:
        raise ValueError("wavelength must be > 0, got %r" % (wavelength_value,))
    sine = 1.22 * wavelength_value / transducer_diameter
    if sine > 1.0:
        raise ValueError(
            "beam not directive: 1.22 * lambda / D = %.3f exceeds 1" % sine
        )
    return math.degrees(math.asin(sine))
