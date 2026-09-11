"""
Simplified shielding analysis for spacecraft radiation environments.
Implements planar slab, spherical shell, and solid-angle sectoring approaches
per ECSS-E-ST-10-12C §6.2.2. Stdlib only — offline, deterministic.
"""

import math


class ShieldingError(ValueError):
    """Raised for invalid shielding inputs or configurations."""


# ---------------------------------------------------------------------------
# Planar (slab) geometry
# ---------------------------------------------------------------------------

def planar_areal_density(thickness_cm: float, density_g_cm3: float) -> float:
    """
    Areal density of a planar slab shield.
    areal_density (g/cm²) = thickness (cm) × material_density (g/cm³)
    """
    if thickness_cm < 0:
        raise ShieldingError("thickness_cm must be non-negative")
    if density_g_cm3 <= 0:
        raise ShieldingError("density_g_cm3 must be positive")
    return thickness_cm * density_g_cm3


def planar_thickness_from_areal_density(areal_density_g_cm2: float, density_g_cm3: float) -> float:
    """
    Invert planar_areal_density: derive thickness given areal density and material density.
    """
    if areal_density_g_cm2 < 0:
        raise ShieldingError("areal_density_g_cm2 must be non-negative")
    if density_g_cm3 <= 0:
        raise ShieldingError("density_g_cm3 must be positive")
    return areal_density_g_cm2 / density_g_cm3


# ---------------------------------------------------------------------------
# Spherical geometry
# ---------------------------------------------------------------------------

def spherical_shell_areal_density(
    outer_radius_cm: float,
    inner_radius_cm: float,
    density_g_cm3: float,
) -> float:
    """
    Areal density of a spherical shell shield (radial ray from inner to outer surface).
    areal_density = shell_thickness × density
    """
    if inner_radius_cm < 0:
        raise ShieldingError("inner_radius_cm must be non-negative")
    if outer_radius_cm <= inner_radius_cm:
        raise ShieldingError("outer_radius_cm must exceed inner_radius_cm")
    if density_g_cm3 <= 0:
        raise ShieldingError("density_g_cm3 must be positive")
    return (outer_radius_cm - inner_radius_cm) * density_g_cm3


def solid_sphere_areal_density(radius_cm: float, density_g_cm3: float) -> float:
    """
    Areal density for a solid sphere along a radial ray (centre to surface).
    areal_density = radius × density
    """
    if radius_cm <= 0:
        raise ShieldingError("radius_cm must be positive")
    if density_g_cm3 <= 0:
        raise ShieldingError("density_g_cm3 must be positive")
    return radius_cm * density_g_cm3


# ---------------------------------------------------------------------------
# Solid-angle sectoring
# ---------------------------------------------------------------------------

def _validate_sector(sector: dict, index: int) -> tuple:
    """Return (solid_angle_sr, areal_density_g_cm2) after validating a sector dict."""
    omega = sector.get("solid_angle_sr")
    ad = sector.get("areal_density_g_cm2")
    if omega is None or ad is None:
        raise ShieldingError(
            f"sector {index} must contain 'solid_angle_sr' and 'areal_density_g_cm2'"
        )
    if omega <= 0:
        raise ShieldingError(f"sector {index}: solid_angle_sr must be positive")
    if ad < 0:
        raise ShieldingError(f"sector {index}: areal_density_g_cm2 must be non-negative")
    return float(omega), float(ad)


def solid_angle_weighted_areal_density(sectors: list) -> float:
    """
    Flux-weighted mean areal density across all sectors.
    Weighted mean = Σ(ωᵢ × ADᵢ) / Σωᵢ
    """
    if not sectors:
        raise ShieldingError("sectors list must not be empty")
    total_omega = 0.0
    weighted_sum = 0.0
    for i, s in enumerate(sectors):
        omega, ad = _validate_sector(s, i)
        weighted_sum += omega * ad
        total_omega += omega
    return weighted_sum / total_omega


def total_solid_angle_check(sectors: list, tolerance: float = 0.01) -> bool:
    """
    Verify the sector set covers the full sphere (4π sr) within a fractional tolerance.
    Returns True if |Σωᵢ − 4π| / 4π ≤ tolerance.
    """
    full_sphere = 4.0 * math.pi
    total = sum(float(s.get("solid_angle_sr", 0.0)) for s in sectors)
    return abs(total - full_sphere) / full_sphere <= tolerance


def build_uniform_sectoring(
    n_sectors: int,
    density_g_cm3: float,
    thickness_cm: float,
) -> list:
    """
    Build a uniform N-sector decomposition of the sphere.
    Each sector carries equal solid angle (4π/N sr) and identical areal density.
    """
    if n_sectors <= 0:
        raise ShieldingError("n_sectors must be a positive integer")
    if density_g_cm3 <= 0:
        raise ShieldingError("density_g_cm3 must be positive")
    if thickness_cm < 0:
        raise ShieldingError("thickness_cm must be non-negative")
    omega_each = 4.0 * math.pi / n_sectors
    ad_each = planar_areal_density(thickness_cm, density_g_cm3)
    return [{"solid_angle_sr": omega_each, "areal_density_g_cm2": ad_each}
            for _ in range(n_sectors)]


def minimum_sector_areal_density(sectors: list) -> float:
    """
    Minimum areal density across all sectors — worst-case shielding direction.
    """
    if not sectors:
        raise ShieldingError("sectors list must not be empty")
    for i, s in enumerate(sectors):
        _validate_sector(s, i)
    return min(s["areal_density_g_cm2"] for s in sectors)


def maximum_sector_areal_density(sectors: list) -> float:
    """
    Maximum areal density across all sectors — best-shielded direction.
    """
    if not sectors:
        raise ShieldingError("sectors list must not be empty")
    for i, s in enumerate(sectors):
        _validate_sector(s, i)
    return max(s["areal_density_g_cm2"] for s in sectors)


def shielding_summary(sectors: list) -> dict:
    """
    Aggregate summary of a sectored shielding configuration.
    Returns min, max, and flux-weighted mean areal density, full-sphere coverage flag,
    and sector count.
    """
    if not sectors:
        raise ShieldingError("sectors list must not be empty")
    return {
        "n_sectors": len(sectors),
        "min_areal_density_g_cm2": minimum_sector_areal_density(sectors),
        "max_areal_density_g_cm2": maximum_sector_areal_density(sectors),
        "weighted_mean_areal_density_g_cm2": solid_angle_weighted_areal_density(sectors),
        "full_sphere_coverage": total_solid_angle_check(sectors),
    }
