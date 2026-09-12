"""
ECSS-E-ST-32C §4.5.14–4.5.15: MMOD collision design and venting provisions.
Paraphrased engineering screening procedures; cite ECSS-E-ST-32C §4.5.14–4.5.15.
Stdlib only. Deterministic, offline.
"""
import math
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Threat category constants
# ---------------------------------------------------------------------------

METEOROID = "meteoroid"
ORBITAL_DEBRIS = "orbital_debris"
VALID_THREAT_CATEGORIES = {METEOROID, ORBITAL_DEBRIS}

# ---------------------------------------------------------------------------
# Shield type constants
# ---------------------------------------------------------------------------

SHIELD_SINGLE_WALL = "single_wall"
SHIELD_WHIPPLE = "whipple"
SHIELD_STUFFED_WHIPPLE = "stuffed_whipple"
SHIELD_MULTI_SHOCK = "multi_shock"
VALID_SHIELD_TYPES = {
    SHIELD_SINGLE_WALL,
    SHIELD_WHIPPLE,
    SHIELD_STUFFED_WHIPPLE,
    SHIELD_MULTI_SHOCK,
}

# Mapping from recognizable source-type strings to threat categories.
_SOURCE_CATEGORY_MAP: Dict[str, str] = {
    "sporadic_meteoroid": METEOROID,
    "meteor_stream": METEOROID,
    "cometary_particle": METEOROID,
    "rocket_body_fragment": ORBITAL_DEBRIS,
    "satellite_fragment": ORBITAL_DEBRIS,
    "paint_flake": ORBITAL_DEBRIS,
    "slag": ORBITAL_DEBRIS,
    "coolant_droplet": ORBITAL_DEBRIS,
}


# ---------------------------------------------------------------------------
# Step 1: Categorize threat source
# ---------------------------------------------------------------------------

def categorize_threat_source(source_type: str) -> str:
    """
    Return the threat category (METEOROID or ORBITAL_DEBRIS) for the given
    source type string. ECSS-E-ST-32C §4.5.14 anchor.

    Raises ValueError for source types not in the recognized map.
    """
    key = source_type.strip().lower().replace(" ", "_")
    if key not in _SOURCE_CATEGORY_MAP:
        raise ValueError(
            f"Unrecognized threat source type {source_type!r}. "
            f"Valid types: {sorted(_SOURCE_CATEGORY_MAP)}"
        )
    return _SOURCE_CATEGORY_MAP[key]


# ---------------------------------------------------------------------------
# Step 2: Flux estimation
# ---------------------------------------------------------------------------

def estimate_flux(
    diameter_mm: float,
    altitude_km: float,
    category: str,
) -> float:
    """
    Return cumulative MMOD flux [impacts m⁻² yr⁻¹] for particles >= diameter_mm
    at altitude_km for the given threat category.

    Simplified power-law model for engineering screening; for high-fidelity work,
    use NASA ORDEM or ESA MASTER. ECSS-E-ST-32C §4.5.14 anchor.
    """
    if diameter_mm <= 0:
        raise ValueError(f"diameter_mm must be > 0; got {diameter_mm}")
    if altitude_km < 0:
        raise ValueError(f"altitude_km must be >= 0; got {altitude_km}")
    if category not in VALID_THREAT_CATEGORIES:
        raise ValueError(
            f"category must be one of {VALID_THREAT_CATEGORIES}; got {category!r}"
        )

    d_ref_mm = 1.0  # reference diameter [mm]

    if category == METEOROID:
        # Sporadic meteoroid background; roughly altitude-independent below GEO.
        base_flux = 9.7e-4   # impacts m⁻² yr⁻¹ at d_ref = 1 mm
        exponent = -2.5
        altitude_factor = 1.0
    else:  # ORBITAL_DEBRIS
        base_flux = 1.2e-3   # impacts m⁻² yr⁻¹ at d_ref = 1 mm, 400 km
        exponent = -3.0
        # Simplified altitude scaling: debris density peaks near 800 km.
        if altitude_km < 200:
            altitude_factor = 0.05
        elif altitude_km <= 600:
            altitude_factor = 1.0
        elif altitude_km <= 1000:
            altitude_factor = 1.5
        elif altitude_km <= 2000:
            altitude_factor = 0.8
        else:
            altitude_factor = 0.3  # GEO and above

    flux = base_flux * ((diameter_mm / d_ref_mm) ** exponent) * altitude_factor
    return max(flux, 0.0)


# ---------------------------------------------------------------------------
# Step 3: Critical diameter via ballistic limit equations (BLE)
# ---------------------------------------------------------------------------

def compute_critical_diameter_single_wall(
    wall_thickness_mm: float,
    projectile_density_gcc: float,
    impact_velocity_kms: float,
) -> float:
    """
    Return the critical (maximum non-penetrating) projectile diameter [mm]
    for a single aluminium wall using a simplified Cour-Palais-style BLE.
    ECSS-E-ST-32C §4.5.14 anchor. Screening use only.
    """
    if wall_thickness_mm <= 0:
        raise ValueError(f"wall_thickness_mm must be > 0; got {wall_thickness_mm}")
    if projectile_density_gcc <= 0:
        raise ValueError(f"projectile_density_gcc must be > 0; got {projectile_density_gcc}")
    if impact_velocity_kms <= 0:
        raise ValueError(f"impact_velocity_kms must be > 0; got {impact_velocity_kms}")

    # Simplified BLE: d_c [mm] = 1.8 * t_w^0.5 / (rho_p^0.5 * v^(2/3))
    d_c = (
        1.8
        * (wall_thickness_mm ** 0.5)
        / ((projectile_density_gcc ** 0.5) * (impact_velocity_kms ** (2.0 / 3.0)))
    )
    return d_c


def compute_critical_diameter_whipple(
    bumper_thickness_mm: float,
    standoff_mm: float,
    rear_wall_thickness_mm: float,
    projectile_density_gcc: float,
    impact_velocity_kms: float,
) -> float:
    """
    Return the critical diameter [mm] for a Whipple dual-wall shield.
    Simplified BLE (paraphrased, screening use only); applies hypervelocity
    formula for v >= 7 km/s and interpolates toward single-wall for v < 7 km/s.
    ECSS-E-ST-32C §4.5.14 anchor.
    """
    for name, val in [
        ("bumper_thickness_mm", bumper_thickness_mm),
        ("standoff_mm", standoff_mm),
        ("rear_wall_thickness_mm", rear_wall_thickness_mm),
        ("projectile_density_gcc", projectile_density_gcc),
        ("impact_velocity_kms", impact_velocity_kms),
    ]:
        if val <= 0:
            raise ValueError(f"{name} must be > 0; got {val}")

    C_wh = 0.6       # calibration constant
    rho_b = 2.7      # bumper Al density [g/cc]

    def _hypervelocity_dc(v_kms: float) -> float:
        return (
            (bumper_thickness_mm ** (2.0 / 3.0)) * (standoff_mm ** (1.0 / 3.0))
            + 0.37 * rear_wall_thickness_mm
        ) / (
            C_wh
            * (projectile_density_gcc ** (1.0 / 3.0))
            * (v_kms ** (2.0 / 3.0))
            * (rho_b ** (1.0 / 9.0))
        )

    if impact_velocity_kms >= 7.0:
        d_c = _hypervelocity_dc(impact_velocity_kms)
    else:
        # Interpolate between single-wall (at v) and hypervelocity Whipple (at 7).
        d_c_sw = compute_critical_diameter_single_wall(
            bumper_thickness_mm + rear_wall_thickness_mm,
            projectile_density_gcc,
            impact_velocity_kms,
        )
        d_c_hv = _hypervelocity_dc(7.0)
        alpha = max(0.0, (impact_velocity_kms - 3.0) / (7.0 - 3.0))
        d_c = d_c_sw + alpha * (d_c_hv - d_c_sw)

    return max(d_c, 0.0)


# ---------------------------------------------------------------------------
# Step 4: Probability of No Penetration
# ---------------------------------------------------------------------------

def compute_pnp(
    flux_per_m2_yr: float,
    exposed_area_m2: float,
    mission_duration_yr: float,
) -> float:
    """
    Return Probability of No Penetration (PNP) using Poisson statistics.
    PNP = exp(−λ) where λ = flux × area × duration.
    ECSS-E-ST-32C §4.5.14 anchor.
    """
    if flux_per_m2_yr < 0:
        raise ValueError(f"flux_per_m2_yr must be >= 0; got {flux_per_m2_yr}")
    if exposed_area_m2 <= 0:
        raise ValueError(f"exposed_area_m2 must be > 0; got {exposed_area_m2}")
    if mission_duration_yr <= 0:
        raise ValueError(f"mission_duration_yr must be > 0; got {mission_duration_yr}")

    lam = flux_per_m2_yr * exposed_area_m2 * mission_duration_yr
    return math.exp(-lam)


def check_pnp_compliance(pnp: float, required_pnp: float) -> dict:
    """
    Compare PNP against the required threshold. Returns a findings dict.
    """
    if not (0.0 <= pnp <= 1.0):
        raise ValueError(f"pnp must be in [0, 1]; got {pnp}")
    if not (0.0 <= required_pnp <= 1.0):
        raise ValueError(f"required_pnp must be in [0, 1]; got {required_pnp}")

    compliant = pnp >= required_pnp
    findings: List[str] = []
    if not compliant:
        findings.append(
            f"PNP {pnp:.4f} is below the required threshold {required_pnp:.4f}; "
            "shielding upgrade or mission shortening required."
        )
    return {
        "pnp": pnp,
        "required_pnp": required_pnp,
        "compliant": compliant,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# Step 5: Venting provisions
# ---------------------------------------------------------------------------

def check_venting_provision(
    enclosed_volume_m3: float,
    vent_area_m2: float,
    min_area_to_volume_ratio: float = 1.0e-4,
) -> dict:
    """
    Verify that an enclosed structural volume has adequate venting.
    Compares the vent-area-to-volume ratio against min_area_to_volume_ratio
    (default 1e-4 m⁻¹, i.e. ~1 cm² per 1 m³ enclosed).
    ECSS-E-ST-32C §4.5.15 anchor.
    """
    if enclosed_volume_m3 <= 0:
        raise ValueError(f"enclosed_volume_m3 must be > 0; got {enclosed_volume_m3}")
    if vent_area_m2 < 0:
        raise ValueError(f"vent_area_m2 must be >= 0; got {vent_area_m2}")
    if min_area_to_volume_ratio <= 0:
        raise ValueError(
            f"min_area_to_volume_ratio must be > 0; got {min_area_to_volume_ratio}"
        )

    ratio = vent_area_m2 / enclosed_volume_m3
    required_vent_area = enclosed_volume_m3 * min_area_to_volume_ratio
    compliant = ratio >= min_area_to_volume_ratio

    findings: List[str] = []
    if vent_area_m2 == 0.0:
        findings.append(
            "No venting provision found for enclosed volume; "
            "non-compliance per ECSS-E-ST-32C §4.5.15."
        )
    elif not compliant:
        shortfall = required_vent_area - vent_area_m2
        findings.append(
            f"Vent area {vent_area_m2:.6f} m² is below the required "
            f"{required_vent_area:.6f} m² (shortfall {shortfall:.6f} m²) "
            f"for enclosed volume {enclosed_volume_m3:.4f} m³."
        )

    return {
        "enclosed_volume_m3": enclosed_volume_m3,
        "vent_area_m2": vent_area_m2,
        "area_to_volume_ratio": ratio,
        "required_ratio": min_area_to_volume_ratio,
        "required_vent_area_m2": required_vent_area,
        "compliant": compliant,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# Step 6: Full component assessment
# ---------------------------------------------------------------------------

def assess_mmod_component(
    component_id: str,
    exposed_area_m2: float,
    altitude_km: float,
    mission_duration_yr: float,
    shield_type: str,
    shield_params: dict,
    required_pnp: float,
    enclosed_volumes: Optional[List[dict]] = None,
    threat_categories: Optional[List[str]] = None,
) -> dict:
    """
    Full MMOD assessment for one structural component.

    shield_params keys depend on shield_type:
      single_wall:
        wall_thickness_mm, projectile_density_gcc, impact_velocity_kms
      whipple / stuffed_whipple / multi_shock:
        bumper_thickness_mm, standoff_mm, rear_wall_thickness_mm,
        projectile_density_gcc, impact_velocity_kms

    enclosed_volumes: list of dicts with keys volume_m3, vent_area_m2
    threat_categories: list of category strings (default: both categories)

    Returns a findings dict; overall_compliant is True only when all findings
    lists are empty.
    """
    if shield_type not in VALID_SHIELD_TYPES:
        raise ValueError(
            f"shield_type must be one of {VALID_SHIELD_TYPES}; got {shield_type!r}"
        )

    if threat_categories is None:
        threat_categories = [METEOROID, ORBITAL_DEBRIS]
    for cat in threat_categories:
        if cat not in VALID_THREAT_CATEGORIES:
            raise ValueError(f"Invalid threat category {cat!r}")

    # Derive critical diameter
    if shield_type == SHIELD_SINGLE_WALL:
        d_c = compute_critical_diameter_single_wall(
            shield_params["wall_thickness_mm"],
            shield_params["projectile_density_gcc"],
            shield_params["impact_velocity_kms"],
        )
    elif shield_type == SHIELD_WHIPPLE:
        d_c = compute_critical_diameter_whipple(
            shield_params["bumper_thickness_mm"],
            shield_params["standoff_mm"],
            shield_params["rear_wall_thickness_mm"],
            shield_params["projectile_density_gcc"],
            shield_params["impact_velocity_kms"],
        )
    else:
        # Stuffed Whipple and multi-shock: use Whipple BLE as conservative proxy.
        d_c = compute_critical_diameter_whipple(
            shield_params.get("bumper_thickness_mm", 2.0),
            shield_params.get("standoff_mm", 100.0),
            shield_params.get("rear_wall_thickness_mm", 3.0),
            shield_params.get("projectile_density_gcc", 2.8),
            shield_params.get("impact_velocity_kms", 10.0),
        )

    # Sum penetrating flux across all applicable threat categories
    total_flux = sum(
        estimate_flux(d_c, altitude_km, cat) for cat in threat_categories
    )

    # PNP
    pnp = compute_pnp(total_flux, exposed_area_m2, mission_duration_yr)
    pnp_result = check_pnp_compliance(pnp, required_pnp)

    # Venting
    vent_results: List[dict] = []
    if enclosed_volumes:
        for i, vol_spec in enumerate(enclosed_volumes):
            vr = check_venting_provision(
                vol_spec["volume_m3"],
                vol_spec.get("vent_area_m2", 0.0),
            )
            vr["volume_index"] = i
            vent_results.append(vr)

    all_findings: List[str] = list(pnp_result["findings"])
    for vr in vent_results:
        all_findings.extend(vr["findings"])

    return {
        "component_id": component_id,
        "critical_diameter_mm": d_c,
        "penetrating_flux_per_m2_yr": total_flux,
        "pnp": pnp,
        "pnp_compliant": pnp_result["compliant"],
        "vent_results": vent_results,
        "findings": all_findings,
        "overall_compliant": len(all_findings) == 0,
    }
