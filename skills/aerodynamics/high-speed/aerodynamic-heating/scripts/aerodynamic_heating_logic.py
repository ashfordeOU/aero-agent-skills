"""Aerodynamic heating logic: stagnation-point convective heating.

Correlation-level stagnation-point aerodynamic heating for hypersonic
vehicles. Pure Python stdlib, deterministic, offline. Uses the Sutton-Graves
correlation to estimate the stagnation-point convective heat flux from
freestream density, flight velocity and nose radius, the Stefan-Boltzmann
balance to convert that flux to a radiation-equilibrium wall temperature at a
chosen surface emissivity, and the sqrt(1/R_n) flux scaling to trade nose
bluntness.

SI units throughout: rho in kg/m3, velocity in m/s, nose radius in m,
heat flux in W/m2, temperature in K.
"""

import math

# Sutton-Graves correlation constant for air, SI units arranged so that
# q_s = C_SG * sqrt(rho / R_n) * V**3 gives W/m2.
C_SG = 1.83e-4
# Stefan-Boltzmann constant, W/m2/K4.
SIGMA_SB = 5.670374419e-8
# Typical thermal protection surface emissivity.
EPSILON_DEFAULT = 0.85


def stagnation_heat_flux(rho, velocity, nose_radius, c_sg=C_SG):
    """Stagnation-point convective heat flux from the Sutton-Graves model.

    q_s = c_sg * sqrt(rho / nose_radius) * velocity**3 (W/m2).

    Raises ValueError if rho, velocity or nose_radius is not positive.
    """
    if rho <= 0:
        raise ValueError("freestream density must be positive, got %r" % (rho,))
    if velocity <= 0:
        raise ValueError("flight velocity must be positive, got %r" % (velocity,))
    if nose_radius <= 0:
        raise ValueError("nose radius must be positive, got %r" % (nose_radius,))
    if c_sg <= 0:
        raise ValueError("correlation constant must be positive, got %r" % (c_sg,))
    return c_sg * math.sqrt(rho / nose_radius) * velocity**3


def radiation_equilibrium_temp(heat_flux, emissivity=EPSILON_DEFAULT,
                               sigma=SIGMA_SB):
    """Radiation-equilibrium wall temperature for a given heat flux.

    T_w = (heat_flux / (emissivity * sigma))**0.25 (K), from the balance
    q = emissivity * sigma * T_w**4 at steady state with no conduction.

    Raises ValueError if heat_flux is negative or emissivity is not in (0, 1].
    """
    if heat_flux < 0:
        raise ValueError("heat flux must be non-negative, got %r" % (heat_flux,))
    if emissivity <= 0 or emissivity > 1:
        raise ValueError(
            "surface emissivity must be in (0, 1], got %r" % (emissivity,))
    if sigma <= 0:
        raise ValueError("Stefan-Boltzmann constant must be positive, got %r"
                         % (sigma,))
    return (heat_flux / (emissivity * sigma))**0.25


def radius_scaling(heat_flux_reference, radius_reference, radius_new):
    """Scale a stagnation heat flux to a new nose radius.

    q_new = heat_flux_reference * sqrt(radius_reference / radius_new),
    the sqrt(1/R_n) scaling of the Sutton-Graves correlation.

    Raises ValueError if any argument is not positive.
    """
    if heat_flux_reference <= 0:
        raise ValueError(
            "reference heat flux must be positive, got %r"
            % (heat_flux_reference,))
    if radius_reference <= 0:
        raise ValueError(
            "reference radius must be positive, got %r" % (radius_reference,))
    if radius_new <= 0:
        raise ValueError(
            "new radius must be positive, got %r" % (radius_new,))
    return heat_flux_reference * math.sqrt(radius_reference / radius_new)


def heating_assessment(rho, velocity, nose_radius,
                       emissivity=EPSILON_DEFAULT):
    """Full stagnation heating assessment at one flight point.

    Returns a dict with heat_flux_W_m2 (Sutton-Graves stagnation flux),
    radiation_temp_K (radiation-equilibrium wall temperature), and the flux
    at doubled and halved nose radius at the same rho and velocity. ValueErrors
    propagate from the underlying checks.
    """
    flux = stagnation_heat_flux(rho, velocity, nose_radius)
    temp = radiation_equilibrium_temp(flux, emissivity=emissivity)
    flux_doubled = radius_scaling(flux, nose_radius, 2.0 * nose_radius)
    flux_halved = radius_scaling(flux, nose_radius, 0.5 * nose_radius)
    return {
        "heat_flux_W_m2": flux,
        "radiation_temp_K": temp,
        "flux_doubled_nose_radius": flux_doubled,
        "flux_halved_nose_radius": flux_halved,
    }
