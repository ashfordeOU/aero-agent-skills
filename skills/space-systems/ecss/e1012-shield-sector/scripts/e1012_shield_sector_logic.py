"""
e1012_shield_sector_logic.py

Sector shielding analysis: mass model -> ray-tracing -> dose.
Reference: ECSS-E-ST-10-12C §6.2.3.

Implements deterministic, offline engineering logic — stdlib only.
"""

import math


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class ShieldingError(ValueError):
    """Raised on invalid inputs to shielding functions."""


class Material:
    """A single shielding material layer."""

    def __init__(self, name: str, thickness_mm: float, density_g_cm3: float):
        if thickness_mm < 0:
            raise ShieldingError(
                f"thickness_mm must be non-negative, got {thickness_mm!r}"
            )
        if density_g_cm3 <= 0:
            raise ShieldingError(
                f"density_g_cm3 must be positive, got {density_g_cm3!r}"
            )
        self.name = name
        self.thickness_mm = thickness_mm
        self.density_g_cm3 = density_g_cm3

    def areal_density_g_cm2(self) -> float:
        """Return normal-incidence areal density (g/cm²)."""
        return self.density_g_cm3 * (self.thickness_mm / 10.0)


class Ray:
    """
    A sector direction expressed as a polar angle (theta, degrees from +Z),
    an azimuth angle (phi, degrees), and the solid angle (sr) of the sector.
    """

    def __init__(self, theta_deg: float, phi_deg: float, solid_angle_sr: float):
        self.theta_deg = theta_deg
        self.phi_deg = phi_deg
        self.solid_angle_sr = solid_angle_sr


class SectorResult:
    """Outcome for one sector: accumulated shield thickness and dose contribution."""

    def __init__(
        self,
        ray: Ray,
        shield_thickness_g_cm2: float,
        dose_contribution_krad: float,
    ):
        self.ray = ray
        self.shield_thickness_g_cm2 = shield_thickness_g_cm2
        self.dose_contribution_krad = dose_contribution_krad


class BudgetCheck:
    """Result of an RDM-adjusted dose vs qualified-dose comparison."""

    def __init__(
        self,
        total_dose_krad: float,
        qualified_dose_krad: float,
        rdm: float,
    ):
        if qualified_dose_krad <= 0:
            raise ShieldingError(
                f"qualified_dose_krad must be positive, got {qualified_dose_krad!r}"
            )
        if rdm < 1.0:
            raise ShieldingError(
                f"rdm must be >= 1.0, got {rdm!r}"
            )
        if total_dose_krad < 0:
            raise ShieldingError(
                f"total_dose_krad must be non-negative, got {total_dose_krad!r}"
            )
        self.total_dose_krad = total_dose_krad
        self.qualified_dose_krad = qualified_dose_krad
        self.rdm = rdm
        self.design_dose_krad = total_dose_krad * rdm
        self.passes = self.design_dose_krad <= qualified_dose_krad

    def margin_db(self) -> float:
        """
        Radiation design margin in dB.  Positive value means the design passes
        (qualified dose exceeds design dose); negative means it fails.
        """
        if self.design_dose_krad <= 0:
            return float("inf")
        return 10.0 * math.log10(self.qualified_dose_krad / self.design_dose_krad)


# ---------------------------------------------------------------------------
# Sector grid generation
# ---------------------------------------------------------------------------

def generate_sectors_uniform(n_theta: int, n_phi: int) -> list:
    """
    Divide the sphere into n_theta × n_phi sectors with approximately equal
    solid angles and return the list of Ray objects.

    n_theta : number of elevation bands (polar divisions)
    n_phi   : number of azimuth divisions per band

    The total solid angle of the returned set equals 4π sr exactly (within
    floating-point rounding).
    """
    if n_theta < 1:
        raise ShieldingError(f"n_theta must be >= 1, got {n_theta!r}")
    if n_phi < 1:
        raise ShieldingError(f"n_phi must be >= 1, got {n_phi!r}")

    rays = []
    for i in range(n_theta):
        theta_lo = math.pi * i / n_theta
        theta_hi = math.pi * (i + 1) / n_theta
        theta_mid = (theta_lo + theta_hi) / 2.0
        band_solid_angle = 2.0 * math.pi * (math.cos(theta_lo) - math.cos(theta_hi))
        sector_solid_angle = band_solid_angle / n_phi
        for j in range(n_phi):
            phi_mid = 2.0 * math.pi * (j + 0.5) / n_phi
            rays.append(
                Ray(
                    theta_deg=math.degrees(theta_mid),
                    phi_deg=math.degrees(phi_mid),
                    solid_angle_sr=sector_solid_angle,
                )
            )
    return rays


def total_solid_angle(rays: list) -> float:
    """Return the sum of solid angles for a list of Ray objects."""
    return sum(r.solid_angle_sr for r in rays)


# ---------------------------------------------------------------------------
# Ray-tracing (flat-slab geometry)
# ---------------------------------------------------------------------------

_MAX_INCIDENCE_DEG = 85.0  # cap to avoid cos-theta -> 0


def incidence_angle_deg(theta_deg: float) -> float:
    """
    Compute the incidence angle on a flat slab (normal along +Z) for a ray
    at polar angle theta_deg (measured from the +Z axis, 0-180°).

    Rays at theta=0 (from +Z) or theta=180 (from -Z) are at normal incidence
    (0°).  Rays near theta=90 are grazing; they are capped at 85° to prevent
    numerical divergence.
    """
    raw = min(theta_deg, 180.0 - theta_deg)
    return min(raw, _MAX_INCIDENCE_DEG)


def trace_ray_areal_density(materials: list, theta_deg: float) -> float:
    """
    Compute the total areal density (g/cm²) for a ray at polar angle theta_deg
    through a stack of flat-slab Material layers.

    The path length through each slab is increased by 1/cos(ι), where ι is
    the incidence angle derived from theta_deg.  Both normal and oblique
    incidence are handled; grazing angles are capped at 85°.

    materials : list of Material instances (may be empty → returns 0.0)
    theta_deg : polar angle of the ray direction (degrees, 0-180)
    """
    if not isinstance(materials, list):
        raise ShieldingError("materials must be a list")
    if theta_deg < 0.0 or theta_deg > 180.0:
        raise ShieldingError(
            f"theta_deg must be in [0, 180], got {theta_deg!r}"
        )

    ι = incidence_angle_deg(theta_deg)
    cos_i = math.cos(math.radians(ι))
    # cos_i is always > 0 because ι <= 85°
    base = sum(m.areal_density_g_cm2() for m in materials)
    return base / cos_i


# ---------------------------------------------------------------------------
# Dose-depth attenuation
# ---------------------------------------------------------------------------

# Simplified power-law dose-depth parameters:
#   D(t) = D0 * (1 + t / lambda) ** (-alpha)
# λ and α are engineering approximations derived from published dose-depth
# tables for aluminium shielding in standard orbit environments.

_ENV_PARAMS = {
    "LEO": {"lambda_g_cm2": 1.0, "alpha": 0.70},
    "GEO": {"lambda_g_cm2": 2.5, "alpha": 0.60},
    "MEO": {"lambda_g_cm2": 1.5, "alpha": 0.65},
}


def dose_behind_shield_krad(
    unshielded_dose_krad: float,
    shield_thickness_g_cm2: float,
    environment: str = "LEO",
) -> float:
    """
    Estimate TID (krad Si) behind shielding using a simplified power-law
    dose-depth approximation.

    unshielded_dose_krad  : total TID with no shielding present (krad Si)
    shield_thickness_g_cm2: areal density of the shielding (g/cm²)
    environment           : orbit environment key — "LEO", "GEO", or "MEO"

    Returns the estimated TID at the shielded location.
    """
    if unshielded_dose_krad < 0:
        raise ShieldingError(
            f"unshielded_dose_krad must be non-negative, got {unshielded_dose_krad!r}"
        )
    if shield_thickness_g_cm2 < 0:
        raise ShieldingError(
            f"shield_thickness_g_cm2 must be non-negative, got {shield_thickness_g_cm2!r}"
        )
    if environment not in _ENV_PARAMS:
        raise ShieldingError(
            f"Unknown environment {environment!r}. "
            f"Choose from {sorted(_ENV_PARAMS)}"
        )

    p = _ENV_PARAMS[environment]
    attenuation = (1.0 + shield_thickness_g_cm2 / p["lambda_g_cm2"]) ** (-p["alpha"])
    return unshielded_dose_krad * attenuation


# ---------------------------------------------------------------------------
# Sector analysis
# ---------------------------------------------------------------------------

def run_sector_analysis(
    rays: list,
    materials: list,
    unshielded_dose_krad: float,
    environment: str = "LEO",
) -> list:
    """
    Execute the sector shielding analysis.

    For each ray (sector direction):
      1. Ray-trace through the material stack to obtain areal density.
      2. Apply dose-depth attenuation to obtain local dose estimate.
      3. Weight by fractional solid angle (sector / 4π).

    Returns a list of SectorResult objects, one per ray.

    rays                 : list of Ray objects from generate_sectors_uniform
    materials            : list of Material layers for the shielding stack
    unshielded_dose_krad : TID with no shielding (krad Si)
    environment          : orbit environment key for dose-depth parameters
    """
    if not rays:
        raise ShieldingError("rays list must not be empty")
    if unshielded_dose_krad < 0:
        raise ShieldingError(
            f"unshielded_dose_krad must be non-negative, got {unshielded_dose_krad!r}"
        )

    sphere_sr = total_solid_angle(rays)
    if sphere_sr <= 0:
        raise ShieldingError("Total solid angle of ray set must be positive")

    results = []
    for ray in rays:
        t = trace_ray_areal_density(materials, ray.theta_deg)
        local_dose = dose_behind_shield_krad(unshielded_dose_krad, t, environment)
        contribution = local_dose * (ray.solid_angle_sr / sphere_sr)
        results.append(SectorResult(ray, t, contribution))
    return results


def aggregate_dose(results: list) -> float:
    """Sum the dose contributions from all sectors to give total TID (krad Si)."""
    if not results:
        raise ShieldingError("results list must not be empty")
    return sum(r.dose_contribution_krad for r in results)


def worst_case_sector(results: list) -> "SectorResult":
    """Return the SectorResult with the highest dose contribution per unit solid angle."""
    if not results:
        raise ShieldingError("results list must not be empty")
    return max(
        results,
        key=lambda r: (
            r.dose_contribution_krad / r.ray.solid_angle_sr
            if r.ray.solid_angle_sr > 0
            else 0.0
        ),
    )


# ---------------------------------------------------------------------------
# Budget check
# ---------------------------------------------------------------------------

def check_dose_budget(
    total_dose_krad: float,
    qualified_dose_krad: float,
    rdm: float = 2.0,
) -> BudgetCheck:
    """
    Apply the radiation design margin and compare against the qualified dose.

    ECSS-E-ST-10-12C §6.2.3 requires design_dose = total_dose × RDM ≤ qualified.
    The default RDM of 2.0 is used unless the project has established and
    approved a different value.

    total_dose_krad     : aggregated TID from sector analysis (krad Si)
    qualified_dose_krad : part's qualified (or required) dose level (krad Si)
    rdm                 : radiation design margin factor (≥ 1.0)
    """
    return BudgetCheck(total_dose_krad, qualified_dose_krad, rdm)
