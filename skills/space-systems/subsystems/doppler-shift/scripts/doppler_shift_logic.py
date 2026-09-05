"""Doppler shift on a spacecraft-to-ground link (pure stdlib).

Straight-line overflight model in the orbital plane: a satellite in a
circular orbit at altitude h (m) passes a ground station; at the moment
the station sees the satellite at elevation elev (deg) the line-of-sight
range rate is rho_dot = -v * cos(elev) (negative while closing) with v
the circular speed sqrt(MU / (R_EARTH + h)). The horizontal distance to
the sub-satellite point is x = h / tan(elev) and the slant range is
rho = sqrt(h^2 + x^2). The received carrier follows
f_rx = f_tx * (1 - rho_dot / C).

Module constants (SI): R_EARTH = 6371.0e3 m, MU = 3.986004418e14 m^3/s^2,
C = 299792458.0 m/s. F_TX_REF = 2.25e9 Hz is the S-band reference carrier
of the leaf worked example, used as the default frequency scale for the
doppler-rate output (Hz/s is a carrier-dependent quantity; pass f_tx
explicitly for any other link).

Conventions: elevation is measured from the local horizontal plane, valid
domain [0, 90] deg. The zenith point (90 deg) is the degenerate overhead
case with zero range rate and is admitted; any elevation above 90 deg is
non-physical and raises ValueError. All functions raise ValueError on
non-physical inputs and are fully deterministic.
"""

import math

# Physical constants (SI) and the leaf reference carrier.
R_EARTH = 6371.0e3      # Earth mean radius, m
MU = 3.986004418e14     # Earth gravitational parameter, m^3/s^2
C = 299792458.0         # Speed of light, m/s
F_TX_REF = 2.25e9       # Reference S-band carrier of the worked example, Hz

MAX_ELEV = 90.0         # zenith, deg (overhead, zero range rate)


def circular_velocity(h):
    """Return the circular-orbit speed (m/s) at altitude h (m)."""
    if h < 0.0:
        raise ValueError("altitude h must be non-negative, got %r" % (h,))
    return math.sqrt(MU / (R_EARTH + h))


def _check_elevation(elev_deg):
    """Raise ValueError unless elev_deg lies in the physical domain."""
    if not math.isfinite(elev_deg):
        raise ValueError("elevation must be finite, got %r" % (elev_deg,))
    if elev_deg < 0.0 or elev_deg > MAX_ELEV:
        raise ValueError(
            "elevation must be within [0, 90] deg, got %r" % (elev_deg,))


def range_rate(h, elev_deg):
    """Return the line-of-sight range rate (m/s) at altitude and elevation.

    Negative while the satellite approaches (closing). Overhead (90 deg)
    the range rate is zero.
    """
    v = circular_velocity(h)
    _check_elevation(elev_deg)
    return -v * math.cos(math.radians(elev_deg))


def doppler_shift(f_tx, h, elev_deg):
    """Return dict with range_rate, received_freq and delta_f for the link.

    f_rx = f_tx * (1 - rho_dot / C); delta_f = f_rx - f_tx. A closing
    satellite (negative range rate) raises the received frequency, so
    delta_f is positive while approaching.
    """
    if f_tx <= 0.0:
        raise ValueError("carrier f_tx must be positive, got %r" % (f_tx,))
    rho_dot = range_rate(h, elev_deg)
    received_freq = f_tx * (1.0 - rho_dot / C)
    return {
        "range_rate": rho_dot,
        "received_freq": received_freq,
        "delta_f": received_freq - f_tx,
    }


def max_doppler(f_tx, h):
    """Return the worst-case Doppler shift (Hz), the value at the horizon.

    At elevation 0 deg the range rate is -v and the shift is f_tx * v / C.
    """
    if f_tx <= 0.0:
        raise ValueError("carrier f_tx must be positive, got %r" % (f_tx,))
    v = circular_velocity(h)
    return f_tx * v / C


def slant_range_and_rate(h, elev_deg, f_tx=F_TX_REF):
    """Return dict with x, rho, rho_dot and doppler_rate at the geometry.

    x (m) is the horizontal distance to the sub-satellite point,
    rho (m) the slant range, rho_dot (m/s) the range rate and doppler_rate
    (Hz/s) the time derivative of the shift magnitude,
    f_tx / C * |rho_dot_dot| with rho_dot_dot = v^2 * h^2 / rho^3.
    """
    _check_elevation(elev_deg)
    if h < 0.0:
        raise ValueError("altitude h must be non-negative, got %r" % (h,))
    if f_tx <= 0.0:
        raise ValueError("carrier f_tx must be positive, got %r" % (f_tx,))
    if elev_deg == 0.0:
        raise ValueError(
            "slant geometry is singular at the horizon; use max_doppler "
            "for the elevation-0 shift")
    v = circular_velocity(h)
    x = h / math.tan(math.radians(elev_deg))
    rho = math.sqrt(h * h + x * x)
    rho_dot = range_rate(h, elev_deg)
    rho_dot_dot = v * v * h * h / (rho ** 3)
    return {
        "x": x,
        "rho": rho,
        "rho_dot": rho_dot,
        "doppler_rate": f_tx / C * abs(rho_dot_dot),
    }
