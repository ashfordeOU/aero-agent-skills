"""
Radiation transport logic for spacecraft shielding analysis.
Ref: ECSS-E-ST-10-12C §6.2.4

Implements deterministic 1-D slab transport for photon and proton radiation.
For 2-D/3-D geometry requests the module applies the 1-D bound and flags
that a full multi-dimensional external code is required.
Stdlib only — no third-party dependencies.
"""

import math

# ---------------------------------------------------------------------------
# Material database
# ---------------------------------------------------------------------------
# Each entry holds:
#   density_g_cm3       : bulk density [g/cm³]
#   mu_photon_cm2_g     : mass attenuation coefficient at ~1 MeV [cm²/g]
#   proton_range_a      : power-law prefactor R = a * E^b  [g/cm², E in MeV]
#   proton_range_b      : power-law exponent
# Values are representative engineering reference data (not verbatim ECSS tables).
MATERIALS = {
    'aluminum': {
        'density_g_cm3': 2.700,
        'mu_photon_cm2_g': 0.0843,
        'proton_range_a': 0.00222,
        'proton_range_b': 1.770,
    },
    'tantalum': {
        'density_g_cm3': 16.654,
        'mu_photon_cm2_g': 0.0525,
        'proton_range_a': 0.00175,
        'proton_range_b': 1.720,
    },
    'polyethylene': {
        'density_g_cm3': 0.940,
        'mu_photon_cm2_g': 0.0959,
        'proton_range_a': 0.00198,
        'proton_range_b': 1.780,
    },
    'titanium': {
        'density_g_cm3': 4.506,
        'mu_photon_cm2_g': 0.0680,
        'proton_range_a': 0.00195,
        'proton_range_b': 1.760,
    },
}

VALID_METHODS = frozenset({'monte_carlo', 'deterministic_sn', 'deterministic_pn'})
VALID_GEOMETRY_DIMS = frozenset({1, 2, 3})
VALID_PARTICLE_TYPES = frozenset({'photon', 'proton', 'electron'})


class TransportError(Exception):
    """Raised for invalid transport inputs or unsupported configurations."""


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def validate_transport_setup(geometry_dim, method, material_name, thickness_cm,
                              source_rate_Gy_s, exposure_s, dose_limit_Gy):
    """
    Validate all parameters for a transport run.
    Raises TransportError with a descriptive message on any invalid input.
    """
    if geometry_dim not in VALID_GEOMETRY_DIMS:
        raise TransportError(
            f"Invalid geometry dimension {geometry_dim!r}; must be 1, 2, or 3."
        )
    if method not in VALID_METHODS:
        raise TransportError(
            f"Unknown transport method {method!r}; supported: {sorted(VALID_METHODS)}."
        )
    if material_name not in MATERIALS:
        raise TransportError(
            f"Unknown material {material_name!r}; available: {sorted(MATERIALS)}."
        )
    if thickness_cm <= 0:
        raise TransportError(
            f"Thickness must be positive, got {thickness_cm} cm."
        )
    if source_rate_Gy_s < 0:
        raise TransportError(
            f"Source dose rate must be non-negative, got {source_rate_Gy_s} Gy/s."
        )
    if exposure_s <= 0:
        raise TransportError(
            f"Exposure duration must be positive, got {exposure_s} s."
        )
    if dose_limit_Gy <= 0:
        raise TransportError(
            f"Dose limit must be positive, got {dose_limit_Gy} Gy."
        )


# ---------------------------------------------------------------------------
# Method and geometry categorization
# ---------------------------------------------------------------------------

def categorize_transport_method(method):
    """
    Return the category of the transport method: 'stochastic' or 'deterministic'.
    Raises TransportError for an unrecognised method.
    """
    if method == 'monte_carlo':
        return 'stochastic'
    if method in ('deterministic_sn', 'deterministic_pn'):
        return 'deterministic'
    raise TransportError(
        f"Cannot categorize unknown transport method {method!r}."
    )


def categorize_geometry(geometry_dim):
    """
    Return the dimension label ('1-D', '2-D', or '3-D') for the geometry.
    Raises TransportError for an unsupported dimension.
    """
    labels = {1: '1-D', 2: '2-D', 3: '3-D'}
    if geometry_dim not in labels:
        raise TransportError(
            f"Invalid geometry dimension {geometry_dim!r}; must be 1, 2, or 3."
        )
    return labels[geometry_dim]


# ---------------------------------------------------------------------------
# Photon transport
# ---------------------------------------------------------------------------

def compute_buildup_factor(mu_cm2_g, density_g_cm3, thickness_cm):
    """
    Estimate the photon buildup factor using Berger's linear approximation:
        B = 1 + mu_lin * t
    where mu_lin = mu_cm2_g * density_g_cm3 [cm⁻¹] and t is thickness [cm].
    Valid for thin shields; provides a conservative upper bound at higher
    optical depths.
    Raises TransportError if inputs are non-positive.
    """
    if mu_cm2_g <= 0:
        raise TransportError("Mass attenuation coefficient must be positive.")
    if density_g_cm3 <= 0:
        raise TransportError("Density must be positive.")
    if thickness_cm <= 0:
        raise TransportError("Thickness must be positive.")
    mu_lin = mu_cm2_g * density_g_cm3  # [cm⁻¹]
    return 1.0 + mu_lin * thickness_cm


def compute_photon_attenuation(source_rate_Gy_s, mu_cm2_g, density_g_cm3,
                               thickness_cm, buildup_factor=1.0):
    """
    Compute the transmitted photon dose rate [Gy/s] through a homogeneous slab:
        D_trans = D0 * B * exp(-mu_lin * t)
    Raises TransportError if buildup_factor < 1.0 (physically impossible).
    """
    if buildup_factor < 1.0:
        raise TransportError(
            f"Buildup factor must be >= 1.0, got {buildup_factor}."
        )
    mu_lin = mu_cm2_g * density_g_cm3  # [cm⁻¹]
    return source_rate_Gy_s * buildup_factor * math.exp(-mu_lin * thickness_cm)


# ---------------------------------------------------------------------------
# Proton transport
# ---------------------------------------------------------------------------

def compute_proton_range_g_cm2(material_name, energy_MeV):
    """
    Estimate proton range in a material [g/cm²] using the power-law fit:
        R = a * E^b
    where a and b are material-specific Bragg–Kleeman parameters.
    Raises TransportError for unknown material or non-positive energy.
    """
    if energy_MeV <= 0:
        raise TransportError(
            f"Proton energy must be positive, got {energy_MeV} MeV."
        )
    mat = MATERIALS.get(material_name)
    if mat is None:
        raise TransportError(
            f"Unknown material {material_name!r}; available: {sorted(MATERIALS)}."
        )
    return mat['proton_range_a'] * (energy_MeV ** mat['proton_range_b'])


def compute_proton_transmission(material_name, thickness_cm, energy_MeV):
    """
    Determine whether a proton of given energy penetrates a slab.
    Returns (penetrates: bool, residual_range_g_cm2: float).
    A negative residual_range means the proton is stopped inside the slab.
    """
    mat = MATERIALS.get(material_name)
    if mat is None:
        raise TransportError(
            f"Unknown material {material_name!r}; available: {sorted(MATERIALS)}."
        )
    areal_thickness = thickness_cm * mat['density_g_cm3']  # [g/cm²]
    proton_range = compute_proton_range_g_cm2(material_name, energy_MeV)
    residual = proton_range - areal_thickness
    return (residual > 0.0, residual)


# ---------------------------------------------------------------------------
# Combined transmitted dose (1-D slab)
# ---------------------------------------------------------------------------

def compute_transmitted_dose(source_rate_Gy_s, exposure_s, material_name,
                             thickness_cm, particle_type='photon',
                             proton_energy_MeV=None):
    """
    Compute total transmitted dose [Gy] for a 1-D slab scenario.

    particle_type='photon'   : exponential attenuation with Berger buildup.
    particle_type='proton'   : range-stopping — zero dose if stopped, full
                               incident dose (conservative) if penetrating.
    particle_type='electron' : simplified effective-attenuation approximation
                               using twice the photon mass-attenuation coefficient.

    Raises TransportError for unknown particle type or missing proton energy.
    """
    if particle_type not in VALID_PARTICLE_TYPES:
        raise TransportError(
            f"Unknown particle type {particle_type!r}; supported: {sorted(VALID_PARTICLE_TYPES)}."
        )

    mat = MATERIALS.get(material_name)
    if mat is None:
        raise TransportError(
            f"Unknown material {material_name!r}; available: {sorted(MATERIALS)}."
        )
    density = mat['density_g_cm3']

    if particle_type == 'photon':
        mu = mat['mu_photon_cm2_g']
        bf = compute_buildup_factor(mu, density, thickness_cm)
        rate = compute_photon_attenuation(source_rate_Gy_s, mu, density, thickness_cm, bf)
        return rate * exposure_s

    if particle_type == 'proton':
        if proton_energy_MeV is None:
            raise TransportError(
                "proton_energy_MeV is required for proton particle type."
            )
        penetrates, _ = compute_proton_transmission(material_name, thickness_cm,
                                                    proton_energy_MeV)
        return source_rate_Gy_s * exposure_s if penetrates else 0.0

    # electron
    mu_eff = mat['mu_photon_cm2_g'] * 2.0
    rate = source_rate_Gy_s * math.exp(-mu_eff * density * thickness_cm)
    return rate * exposure_s


# ---------------------------------------------------------------------------
# Dose margin
# ---------------------------------------------------------------------------

def compute_dose_margin(transmitted_dose_Gy, dose_limit_Gy):
    """
    Compute the shielding dose margin:
        margin = (dose_limit - transmitted_dose) / dose_limit

    A non-negative margin means the transmitted dose is within the limit.
    Raises TransportError if dose_limit_Gy is not positive.
    """
    if dose_limit_Gy <= 0:
        raise TransportError(
            f"Dose limit must be positive, got {dose_limit_Gy} Gy."
        )
    return (dose_limit_Gy - transmitted_dose_Gy) / dose_limit_Gy


# ---------------------------------------------------------------------------
# Full analysis pipeline
# ---------------------------------------------------------------------------

def run_transport_analysis(geometry_dim, method, material_name, thickness_cm,
                           source_rate_Gy_s, exposure_s, dose_limit_Gy,
                           particle_type='photon', proton_energy_MeV=None):
    """
    Run a complete 1-D shielding transport analysis per ECSS-E-ST-10-12C §6.2.4.

    Returns a result dict with keys:
      geometry_dim, geometry_label, method, method_category,
      material, thickness_cm, particle_type,
      source_rate_Gy_s, exposure_s, dose_limit_Gy,
      transmitted_dose_Gy, dose_margin, compliant, findings.

    The 'findings' list is empty when the shield is adequate.
    For geometry_dim > 1 a caveat finding is always added because only the
    1-D bound is computed here.
    """
    validate_transport_setup(geometry_dim, method, material_name, thickness_cm,
                             source_rate_Gy_s, exposure_s, dose_limit_Gy)

    geo_label = categorize_geometry(geometry_dim)
    method_cat = categorize_transport_method(method)

    transmitted = compute_transmitted_dose(
        source_rate_Gy_s, exposure_s, material_name, thickness_cm,
        particle_type, proton_energy_MeV,
    )
    margin = compute_dose_margin(transmitted, dose_limit_Gy)
    compliant = margin >= 0.0

    findings = []
    if not compliant:
        findings.append(
            f"Dose limit exceeded: {transmitted:.4e} Gy > {dose_limit_Gy:.4e} Gy "
            f"(margin {margin:.2%})."
        )
    if geometry_dim > 1:
        findings.append(
            f"{geo_label} geometry requested — this module applies a 1-D conservative "
            "bound; full multi-dimensional transport requires an external code (e.g. "
            "GEANT4, FASTRAD, NOVICE)."
        )

    return {
        'geometry_dim': geometry_dim,
        'geometry_label': geo_label,
        'method': method,
        'method_category': method_cat,
        'material': material_name,
        'thickness_cm': thickness_cm,
        'particle_type': particle_type,
        'source_rate_Gy_s': source_rate_Gy_s,
        'exposure_s': exposure_s,
        'dose_limit_Gy': dose_limit_Gy,
        'transmitted_dose_Gy': transmitted,
        'dose_margin': margin,
        'compliant': compliant,
        'findings': findings,
    }
