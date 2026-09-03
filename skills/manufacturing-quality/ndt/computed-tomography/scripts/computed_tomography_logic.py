"""Computed tomography (CT) inspection planning and interpretation logic.

Pure Python stdlib module for volumetric X-ray CT of aerospace parts:
geometry (magnification, voxel size), spatial resolution check against a
required flaw size, cone beam projection count, tube energy rule of
thumb, scan time, CT number (Hounsfield) conversion, material class from
CT number, and porosity volume fraction with equivalent spherical void
diameter from a segmented region of interest.

All values are SI unless stated otherwise: distances in m, pixel pitch
in m, voxel size in m, thickness input in mm for the tube energy rule,
time in s, porosity as percent.

Standard forms are paraphrased reference-only guidance (see SKILL.md);
nothing here reproduces proprietary standard text.

Functions
---------
magnification(sod, odd) -> float
voxel_size(pixel_pitch, sod, odd) -> float
resolution_check(voxel_size_m, required_flaw_m) -> str
projection_count(columns_span) -> int
tube_energy_kv(material, thickness_mm) -> float
scan_time(num_projections, exposure_s_per_proj) -> float
ct_number(mu, mu_water) -> float
material_class_from_ct_number(hu) -> str
porosity_fraction(void_voxels, total_voxels) -> float
void_diameter(void_voxels, voxel_size_m) -> float
ct_inspection_verdict(...) -> dict

ValueError is raised for non-physical inputs: negative distances, pixel
pitch <= 0, SOD <= 0, required flaw <= 0, void_voxels > total_voxels,
and unknown material.
"""

import math

# Geometric magnification: M = (SOD + ODD) / SOD.
# Voxel size: v = p_det / M (approximate isotropic voxel).
MU_WATER_DEFAULT = 20.0  # 1/m, representative linear attenuation of water at CT energies

# Smallest reliably detected feature spans this many voxels
# (2 to 3 voxels rule; module constant, reference-only guidance).
DETECT_FACTOR = 3

# Cone beam projection count rule of thumb (Nyquist-ish):
# N_proj ~= pi / 2 * N_col, where N_col is the number of detector
# columns spanned by the object projection.
PROJECTION_K = math.pi / 2.0

# Tube energy rule of thumb, representative kV per mm of material
# thickness at moderate density (paraphrased reference-only guidance).
# Aluminum band 60 to 80 kV per 10 mm maps to 6.0 to 8.0 kV/mm; the
# table uses a representative midband value per material, steel roughly
# twice aluminum.
KV_PER_MM = {
    "aluminum": 7.0,
    "titanium": 9.0,
    "steel": 14.0,
    "nickel": 16.0,
}

# CT number (Hounsfield) material class bands, reference-only
# classification at a typical effective CT spectrum. Bands are defined
# on measured HU and are not a substitute for a calibrated acceptance.
HU_AIR = -1000.0
HU_AIR_BAND = -950.0
HU_FOAM_BAND = -100.0
HU_WATER_BAND = 100.0
HU_LIGHT_ALLOY_BAND = 1000.0


def magnification(sod, odd):
    """Geometric magnification M = (SOD + ODD) / SOD.

    sod: source to object distance in m (> 0).
    odd: object to detector distance in m (>= 0).
    """
    if sod <= 0:
        raise ValueError("SOD must be positive")
    if odd < 0:
        raise ValueError("ODD must be non-negative")
    return (sod + odd) / sod


def voxel_size(pixel_pitch, sod, odd):
    """Approximate isotropic voxel size v = pixel_pitch / M in m."""
    if pixel_pitch <= 0:
        raise ValueError("detector pixel pitch must be positive")
    return pixel_pitch / magnification(sod, odd)


def resolution_check(voxel_size_m, required_flaw_m):
    """Check that the smallest detectable feature meets the requirement.

    Smallest detectable feature is DETECT_FACTOR voxels wide. Returns a
    pass/fail verdict string with the values embedded.
    """
    if voxel_size_m <= 0:
        raise ValueError("voxel size must be positive")
    if required_flaw_m <= 0:
        raise ValueError("required flaw size must be positive")
    smallest = voxel_size_m * DETECT_FACTOR
    if smallest <= required_flaw_m * (1.0 + 1e-9):
        return (
            "PASS: smallest detectable feature "
            + f"{smallest:.3e} m (3 voxels) is at or below the required "
            + f"{required_flaw_m:.3e} m flaw size"
        )
    return (
        "FAIL: smallest detectable feature "
        + f"{smallest:.3e} m (3 voxels) exceeds the required "
        + f"{required_flaw_m:.3e} m flaw size"
    )


def projection_count(columns_span):
    """Number of cone beam projections: N_proj ~= (pi / 2) * N_col."""
    if columns_span <= 0:
        raise ValueError("detector column span must be positive")
    return int(math.ceil(PROJECTION_K * columns_span))


def tube_energy_kv(material, thickness_mm):
    """Tube peak energy kV for a material and thickness (rule of thumb).

    kV = KV_PER_MM[material] * thickness_mm. Reference-only first-pass
    guidance for planning; validate against the actual beam quality
    curve and the required contrast before the scan.
    """
    key = material.strip().lower()
    if key not in KV_PER_MM:
        raise ValueError(
            "unknown material " + str(material)
            + "; supported: " + ", ".join(sorted(KV_PER_MM))
        )
    if thickness_mm <= 0:
        raise ValueError("material thickness must be positive")
    return KV_PER_MM[key] * thickness_mm


def scan_time(num_projections, exposure_s_per_proj):
    """Total scan time t_scan = N_proj * t_per_proj in s."""
    if num_projections <= 0:
        raise ValueError("number of projections must be positive")
    if exposure_s_per_proj <= 0:
        raise ValueError("exposure time per projection must be positive")
    return num_projections * exposure_s_per_proj


def ct_number(mu, mu_water):
    """CT number in Hounsfield units: 1000 * (mu - mu_water) / mu_water."""
    if mu < 0:
        raise ValueError("measured linear attenuation must be non-negative")
    if mu_water <= 0:
        raise ValueError("water linear attenuation must be positive")
    return 1000.0 * (mu - mu_water) / mu_water


def material_class_from_ct_number(hu):
    """Material class from the CT number band (reference-only)."""
    if hu <= HU_AIR_BAND:
        return "air-or-gas"
    if hu < HU_FOAM_BAND:
        return "low-density-void"
    if hu < HU_WATER_BAND:
        return "polymer-composite"
    if hu < HU_LIGHT_ALLOY_BAND:
        return "light-alloy"
    return "high-density-metal"


def porosity_fraction(void_voxels, total_voxels):
    """Porosity volume fraction in percent = 100 * V_voids / V_total."""
    if void_voxels < 0:
        raise ValueError("void voxel count must be non-negative")
    if total_voxels <= 0:
        raise ValueError("total voxel count must be positive")
    if void_voxels > total_voxels:
        raise ValueError("void voxel count cannot exceed total voxel count")
    return 100.0 * void_voxels / total_voxels


def void_diameter(void_voxels, voxel_size_m):
    """Equivalent spherical void diameter in m from the void voxel count.

    Assumes cubic voxels of side voxel_size_m; the equivalent sphere
    conserves the segmented void volume.
    """
    if void_voxels < 0:
        raise ValueError("void voxel count must be non-negative")
    if voxel_size_m <= 0:
        raise ValueError("voxel size must be positive")
    if void_voxels == 0:
        return 0.0
    volume = void_voxels * voxel_size_m ** 3
    return 2.0 * (3.0 * volume / (4.0 * math.pi)) ** (1.0 / 3.0)


def ct_inspection_verdict(pixel_pitch, sod, odd, required_flaw_m,
                          columns_span, material, thickness_mm,
                          num_projections=None, exposure_s_per_proj=None,
                          void_voxels=None, total_voxels=None,
                          mu=None, mu_water=None):
    """Compose the full CT inspection planning verdict dict.

    Returns magnification, voxel size, resolution verdict, projection
    count, tube energy, and, when provided, scan time, porosity percent
    and void diameter plus the CT number material class.
    """
    mag = magnification(sod, odd)
    vsize = voxel_size(pixel_pitch, sod, odd)
    verdict = {
        "magnification": mag,
        "voxel_size_m": vsize,
        "resolution": resolution_check(vsize, required_flaw_m),
        "projection_count": projection_count(columns_span),
        "tube_energy_kv": tube_energy_kv(material, thickness_mm),
    }
    if num_projections is not None and exposure_s_per_proj is not None:
        verdict["scan_time_s"] = scan_time(
            num_projections, exposure_s_per_proj)
    if void_voxels is not None and total_voxels is not None:
        frac = porosity_fraction(void_voxels, total_voxels)
        verdict["porosity_percent"] = frac
        verdict["void_diameter_m"] = void_diameter(void_voxels, vsize)
    if mu is not None and mu_water is not None:
        hu = ct_number(mu, mu_water)
        verdict["ct_number_hu"] = hu
        verdict["material_class"] = material_class_from_ct_number(hu)
    return verdict


if __name__ == "__main__":
    # Self check on the SKILL worked example values.
    import sys
    out = ct_inspection_verdict(
        pixel_pitch=200e-6, sod=0.300, odd=0.300, required_flaw_m=0.5e-3,
        columns_span=1024, material="aluminum", thickness_mm=50.0,
        num_projections=1609, exposure_s_per_proj=0.1,
        void_voxels=64000, total_voxels=8000000)
    for key, value in out.items():
        print(f"{key} = {value}")
    sys.exit(0)
