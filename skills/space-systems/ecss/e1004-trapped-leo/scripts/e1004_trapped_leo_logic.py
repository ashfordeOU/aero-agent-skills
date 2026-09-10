"""Trapped LEO electron environment logic (ECSS-E-ST-10-04C 9.2.1.2).

Computes AE-8/AE-9-class omnidirectional electron flux for a LEO ground
track using McIlwain L-shell and B-L (B/B0) coordinates, and produces an
orbit-averaged flux/fluence estimate that captures the South Atlantic
Anomaly (SAA) contribution.

Data provenance: AE_ELECTRON_TABLE below is a representative,
order-of-magnitude placeholder calibrated to the published *shape* of
AE-8 MIN/MAX omnidirectional electron flux vs. L-shell and energy. It is
NOT a transcription of the original NASA AE-8/AE-9 coefficient files.
Replace this table with vetted SPENVIS/OMERE/AE9-AP9 (IRENE) output for
mission-grade, traceable analysis; the lookup/interpolation and orbit
geometry below are model-independent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

EARTH_RADIUS_KM = 6371.2
DIPOLE_MOMENT_GAUSS_RE3 = 0.311  # equatorial surface field, centered-dipole approx

# Representative AE-8/AE-9-class electron table.
# Keyed by L-shell grid point -> (J0 [cm^-2 s^-1], E0 [MeV]) for an
# exponential differential-flux spectrum J(E) = J0/E0 * exp(-E/E0).
# Values rise from the inner belt (~L=1.5, weaker, harder-edged by SAA
# geometry) to the outer-belt peak (~L=4) then fall off toward L=7.
AE_ELECTRON_TABLE: dict[float, tuple[float, float]] = {
    1.2: (5.0e6, 0.10),
    1.5: (2.0e7, 0.15),
    2.0: (8.0e7, 0.25),
    2.5: (3.0e8, 0.35),
    3.0: (8.0e8, 0.45),
    3.5: (1.2e9, 0.55),
    4.0: (1.0e9, 0.60),
    4.5: (6.0e8, 0.55),
    5.0: (3.0e8, 0.45),
    6.0: (8.0e7, 0.35),
    7.0: (2.0e7, 0.25),
}

MIN_ENERGY_MEV = 0.04
MAX_ENERGY_MEV = 7.0
MIN_L = min(AE_ELECTRON_TABLE)
MAX_L = max(AE_ELECTRON_TABLE)


@dataclass(frozen=True)
class OrbitDefinition:
    altitude_km: float
    inclination_deg: float
    n_samples: int = 360


@dataclass(frozen=True)
class BLCoordinate:
    b_gauss: float
    b_over_b0: float
    l_shell: float


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def geodetic_to_bl(altitude_km: float, geomagnetic_latitude_deg: float) -> BLCoordinate:
    """Centered-dipole approximation of (B, L) from altitude and geomagnetic latitude.

    This is the standard first-order dipole relation used for
    environment-categorization work (not precision field modelling):
        r = 1 + altitude/Re          (radial distance in Earth radii)
        L = r / cos^2(lambda_m)      (McIlwain L, dipole form)
        B = (M/r^3) * sqrt(1 + 3*sin^2(lambda_m))
        B0 = M / L^3                 (equatorial field at that L)
    """
    if altitude_km < 0:
        raise ValueError("altitude_km must be non-negative")

    lat_rad = math.radians(geomagnetic_latitude_deg)
    r_re = 1.0 + altitude_km / EARTH_RADIUS_KM
    cos2_lat = math.cos(lat_rad) ** 2
    if cos2_lat < 1e-6:
        cos2_lat = 1e-6  # avoid singularity exactly at the magnetic pole

    l_shell = r_re / cos2_lat
    b_gauss = (DIPOLE_MOMENT_GAUSS_RE3 / r_re**3) * math.sqrt(1 + 3 * math.sin(lat_rad) ** 2)
    b0_gauss = DIPOLE_MOMENT_GAUSS_RE3 / l_shell**3
    b_over_b0 = b_gauss / b0_gauss if b0_gauss > 0 else 1.0

    return BLCoordinate(b_gauss=b_gauss, b_over_b0=b_over_b0, l_shell=l_shell)


def _interpolate_j0_e0(l_shell: float) -> tuple[float, float]:
    """Linear interpolation of (J0, E0) across the L-shell grid, clamped at the edges."""
    l_clamped = _clamp(l_shell, MIN_L, MAX_L)
    grid = sorted(AE_ELECTRON_TABLE)

    if l_clamped <= grid[0]:
        return AE_ELECTRON_TABLE[grid[0]]
    if l_clamped >= grid[-1]:
        return AE_ELECTRON_TABLE[grid[-1]]

    for lower, upper in zip(grid, grid[1:]):
        if lower <= l_clamped <= upper:
            frac = (l_clamped - lower) / (upper - lower)
            j0_lo, e0_lo = AE_ELECTRON_TABLE[lower]
            j0_hi, e0_hi = AE_ELECTRON_TABLE[upper]
            j0 = j0_lo + frac * (j0_hi - j0_lo)
            e0 = e0_lo + frac * (e0_hi - e0_lo)
            return j0, e0

    raise AssertionError("unreachable: l_clamped must fall within grid bounds")


def _b_attenuation(b_over_b0: float) -> float:
    """Off-equator flux attenuation as a function of B/B0 (mirror-point loss cone falloff)."""
    b_over_b0 = max(1.0, b_over_b0)
    return math.exp(-(b_over_b0 - 1.0))


def flux_differential(energy_mev: float, l_shell: float, b_over_b0: float = 1.0) -> float:
    """Differential omnidirectional electron flux [cm^-2 s^-1 MeV^-1] at (E, L, B/B0)."""
    if energy_mev <= 0:
        raise ValueError("energy_mev must be positive")

    j0, e0 = _interpolate_j0_e0(l_shell)
    spectral_shape = math.exp(-energy_mev / e0) / e0
    return j0 * spectral_shape * _b_attenuation(b_over_b0)


def flux_integral(energy_mev: float, l_shell: float, b_over_b0: float = 1.0) -> float:
    """Integral omnidirectional electron flux J(>E) [cm^-2 s^-1] at (E, L, B/B0).

    Closed form of the exponential spectrum's integral from energy_mev to infinity.
    """
    if energy_mev <= 0:
        raise ValueError("energy_mev must be positive")

    j0, e0 = _interpolate_j0_e0(l_shell)
    return j0 * math.exp(-energy_mev / e0) * _b_attenuation(b_over_b0)


def _ground_track_geomagnetic_latitude(inclination_deg: float, fraction: float) -> float:
    """Approximate geomagnetic latitude along a circular orbit as a function of orbit fraction.

    Treats the geomagnetic pole offset implicitly via the caller supplying
    an inclination already referenced to the geomagnetic pole; this keeps
    the SAA's below-average L-shell dip representable without requiring
    a full IGRF/offset-dipole implementation for a categorization-level estimate.
    """
    inc_rad = math.radians(inclination_deg)
    orbit_angle = 2 * math.pi * fraction
    return math.degrees(math.asin(math.sin(inc_rad) * math.sin(orbit_angle)))


def orbit_average_flux(
    orbit: OrbitDefinition, energy_mev: float, saa_l_threshold: float = 2.0
) -> dict[str, float]:
    """Time-weighted average electron flux over one orbit, with SAA-dominant fraction flagged.

    Samples are equally spaced in orbit fraction (equal time, for a
    circular orbit), so a simple arithmetic mean over samples is the
    correct time-weighted average.
    """
    if orbit.n_samples < 1:
        raise ValueError("n_samples must be >= 1")

    fluxes: list[float] = []
    saa_fluxes: list[float] = []

    for i in range(orbit.n_samples):
        fraction = i / orbit.n_samples
        geomag_lat = _ground_track_geomagnetic_latitude(orbit.inclination_deg, fraction)
        bl = geodetic_to_bl(orbit.altitude_km, geomag_lat)
        flux = flux_integral(energy_mev, bl.l_shell, bl.b_over_b0)
        fluxes.append(flux)
        if bl.l_shell < saa_l_threshold:
            saa_fluxes.append(flux)

    mean_flux = sum(fluxes) / len(fluxes)
    saa_mean_flux = sum(saa_fluxes) / len(saa_fluxes) if saa_fluxes else 0.0
    saa_fraction = len(saa_fluxes) / len(fluxes)

    return {
        "mean_flux_cm2_s": mean_flux,
        "saa_mean_flux_cm2_s": saa_mean_flux,
        "saa_time_fraction": saa_fraction,
        "n_samples": float(orbit.n_samples),
    }
