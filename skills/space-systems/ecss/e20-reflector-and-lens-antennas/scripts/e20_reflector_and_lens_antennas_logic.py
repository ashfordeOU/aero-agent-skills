#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 7.2.2.2.2 -- reflector and lens antenna surfaces.

Deterministic, offline, stdlib-only implementation of the surface-quality
assessment: categorize a radiating-path surface as reflecting or
transmitting, quantify its dissipative loss, its diffusivity (the power
scattered out of the specular direction by rms surface roughness) and its
depolarisation, then compare the rolled-up budget against the antenna
requirement.

Paraphrased procedure only -- no standard text is reproduced.
"""

import math

SPEED_OF_LIGHT_M_S = 299792458.0
VACUUM_PERMEABILITY_H_M = 4.0e-7 * math.pi
FREE_SPACE_IMPEDANCE_OHM = 376.730313668
NEPER_TO_DB = 8.685889638065035

# Representation tolerance used only to absorb float round-off at an exact
# limit. It never widens an engineering limit.
LIMIT_TOL_DB = 1e-9
LIMIT_TOL_FRACTION = 1e-12

REFLECTING_SURFACES = {
    "metal-reflector",
    "mesh-reflector",
    "grid-polariser",
    "sub-reflector",
    "shaped-reflector",
}
TRANSMITTING_SURFACES = {
    "dielectric-lens",
    "radome-wall",
    "dichroic-panel",
    "matching-layer",
    "transmit-window",
}


def _le(value, limit, tol=LIMIT_TOL_DB):
    """value <= limit, absorbing representation error at the exact limit."""
    return value <= limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=tol)


def _ge(value, limit, tol=LIMIT_TOL_DB):
    """value >= limit, absorbing representation error at the exact limit."""
    return value >= limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=tol)


def categorize_surface(family):
    """Return 'reflecting' or 'transmitting' for a surface family token."""
    if not isinstance(family, str) or not family.strip():
        raise ValueError("surface family must be a non-empty string")
    key = family.strip().lower()
    if key in REFLECTING_SURFACES:
        return "reflecting"
    if key in TRANSMITTING_SURFACES:
        return "transmitting"
    raise ValueError("uncategorized surface family: %r" % (family,))


def wavelength_m(frequency_hz):
    """Free-space wavelength at an operating frequency."""
    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be > 0")
    return SPEED_OF_LIGHT_M_S / float(frequency_hz)


def surface_resistance_ohm(frequency_hz, conductivity_s_per_m):
    """Skin-effect surface resistance Rs = sqrt(pi f mu0 / sigma)."""
    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be > 0")
    if conductivity_s_per_m <= 0:
        raise ValueError("conductivity_s_per_m must be > 0")
    return math.sqrt(
        math.pi * float(frequency_hz) * VACUUM_PERMEABILITY_H_M
        / float(conductivity_s_per_m)
    )


def _incidence_cosine(incidence_deg):
    if not (0.0 <= incidence_deg < 90.0):
        raise ValueError("incidence_deg must be in [0, 90)")
    return math.cos(math.radians(incidence_deg))


def conductor_absorptivity(frequency_hz, conductivity_s_per_m, incidence_deg=0.0):
    """Fraction of incident power absorbed per bounce on a good conductor.

    Worst-case (parallel-polarised) form A = 4 Rs / (eta0 cos theta).
    """
    r_s = surface_resistance_ohm(frequency_hz, conductivity_s_per_m)
    cos_i = _incidence_cosine(incidence_deg)
    absorptivity = 4.0 * r_s / (FREE_SPACE_IMPEDANCE_OHM * cos_i)
    if absorptivity >= 1.0:
        raise ValueError(
            "absorptivity %.3f >= 1: surface is not a good conductor at "
            "this frequency and incidence" % absorptivity
        )
    return absorptivity


def conductor_loss_db(frequency_hz, conductivity_s_per_m, incidence_deg=0.0,
                      bounces=1):
    """Dissipative loss of a reflecting-surface chain, in dB (positive)."""
    if not isinstance(bounces, int) or bounces < 1:
        raise ValueError("bounces must be an integer >= 1")
    absorptivity = conductor_absorptivity(
        frequency_hz, conductivity_s_per_m, incidence_deg
    )
    return -10.0 * math.log10(1.0 - absorptivity) * bounces


def refracted_path_m(thickness_m, relative_permittivity, incidence_deg=0.0):
    """Geometric path length of the ray inside a transmitting wall."""
    if thickness_m <= 0:
        raise ValueError("thickness_m must be > 0")
    if relative_permittivity < 1.0:
        raise ValueError("relative_permittivity must be >= 1.0")
    cos_i = _incidence_cosine(incidence_deg)
    sin_i = math.sqrt(max(0.0, 1.0 - cos_i * cos_i))
    index = math.sqrt(relative_permittivity)
    sin_t = sin_i / index
    cos_t = math.sqrt(max(0.0, 1.0 - sin_t * sin_t))
    return thickness_m / cos_t


def dielectric_loss_db(frequency_hz, thickness_m, relative_permittivity,
                       loss_tangent, incidence_deg=0.0):
    """Dissipative loss of a transmitting-surface wall, in dB (positive)."""
    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be > 0")
    if loss_tangent < 0:
        raise ValueError("loss_tangent must be >= 0")
    if loss_tangent > 1.0:
        raise ValueError("loss_tangent > 1 is outside the low-loss model")
    path = refracted_path_m(thickness_m, relative_permittivity, incidence_deg)
    beta = 2.0 * math.pi * float(frequency_hz) * math.sqrt(relative_permittivity) \
        / SPEED_OF_LIGHT_M_S
    alpha_np_m = 0.5 * beta * loss_tangent
    return NEPER_TO_DB * alpha_np_m * path


def diffusivity(rms_roughness_m, wavelength, surface_class,
                incidence_deg=0.0, relative_permittivity=None):
    """Specular efficiency and diffuse-scattered fraction from roughness."""
    if rms_roughness_m < 0:
        raise ValueError("rms_roughness_m must be >= 0")
    if wavelength <= 0:
        raise ValueError("wavelength must be > 0")
    if surface_class == "reflecting":
        cos_i = _incidence_cosine(incidence_deg)
        phase_err = 4.0 * math.pi * rms_roughness_m * cos_i / wavelength
    elif surface_class == "transmitting":
        if relative_permittivity is None:
            raise ValueError(
                "relative_permittivity is required for a transmitting surface"
            )
        if relative_permittivity < 1.0:
            raise ValueError("relative_permittivity must be >= 1.0")
        index_excess = math.sqrt(relative_permittivity) - 1.0
        phase_err = 2.0 * math.pi * index_excess * rms_roughness_m / wavelength
    else:
        raise ValueError("uncategorized surface class: %r" % (surface_class,))
    specular = math.exp(-(phase_err ** 2))
    diffuse = 1.0 - specular
    scatter_loss_db = -10.0 * math.log10(specular) if specular > 0 else float("inf")
    return {
        "phase_error_rad": phase_err,
        "specular_efficiency": specular,
        "diffuse_fraction": diffuse,
        "scatter_loss_db": scatter_loss_db,
    }


def combine_depolarisation_db(contributions_db):
    """Combine cross-polar contributions in power into one discrimination."""
    if not contributions_db:
        raise ValueError("contributions_db must contain at least one term")
    total_ratio = 0.0
    for term in contributions_db:
        if term <= 0:
            raise ValueError(
                "each depolarisation term must be a positive dB "
                "discrimination, got %r" % (term,)
            )
        total_ratio += 10.0 ** (-term / 10.0)
    if total_ratio >= 1.0:
        raise ValueError(
            "combined cross-polar power exceeds the co-polar power; "
            "inputs are not a physical discrimination set"
        )
    return -10.0 * math.log10(total_ratio)


def axial_ratio_db(cross_polar_discrimination_db):
    """Equivalent axial ratio for a given cross-polar discrimination."""
    if cross_polar_discrimination_db <= 0:
        raise ValueError("cross_polar_discrimination_db must be > 0")
    ratio = 10.0 ** (-cross_polar_discrimination_db / 20.0)
    return 20.0 * math.log10((1.0 + ratio) / (1.0 - ratio))


def evaluate_surface(spec):
    """Evaluate one surface spec into loss, diffusivity and depolarisation."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for field in ("id", "family", "frequency_hz"):
        if field not in spec:
            raise ValueError("spec missing required field %r" % (field,))
    surface_class = categorize_surface(spec["family"])
    frequency_hz = spec["frequency_hz"]
    lam = wavelength_m(frequency_hz)
    incidence_deg = spec.get("incidence_deg", 0.0)
    if surface_class == "reflecting":
        if "conductivity_s_per_m" not in spec:
            raise ValueError("spec missing required field 'conductivity_s_per_m'")
        dissipative_db = conductor_loss_db(
            frequency_hz,
            spec["conductivity_s_per_m"],
            incidence_deg,
            spec.get("bounces", 1),
        )
        permittivity = None
    else:
        for field in ("thickness_m", "relative_permittivity", "loss_tangent"):
            if field not in spec:
                raise ValueError("spec missing required field %r" % (field,))
        permittivity = spec["relative_permittivity"]
        dissipative_db = dielectric_loss_db(
            frequency_hz,
            spec["thickness_m"],
            permittivity,
            spec["loss_tangent"],
            incidence_deg,
        )
    scatter = diffusivity(
        spec.get("rms_roughness_m", 0.0), lam, surface_class,
        incidence_deg, permittivity,
    )
    xpd_db = combine_depolarisation_db(spec["depolarisation_terms_db"]) \
        if spec.get("depolarisation_terms_db") else None
    total_loss_db = dissipative_db + scatter["scatter_loss_db"]
    return {
        "id": spec["id"],
        "surface_class": surface_class,
        "wavelength_m": lam,
        "dissipative_loss_db": dissipative_db,
        "scatter_loss_db": scatter["scatter_loss_db"],
        "specular_efficiency": scatter["specular_efficiency"],
        "diffuse_fraction": scatter["diffuse_fraction"],
        "total_loss_db": total_loss_db,
        "cross_polar_discrimination_db": xpd_db,
        "axial_ratio_db": axial_ratio_db(xpd_db) if xpd_db is not None else None,
    }


def assess_surface(spec, requirement):
    """Evaluate a surface and return findings against its requirement."""
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping")
    result = evaluate_surface(spec)
    findings = []
    max_loss = requirement.get("max_total_loss_db")
    if max_loss is None:
        findings.append("%s: no surface-loss limit on record" % result["id"])
    elif not _le(result["total_loss_db"], max_loss):
        findings.append(
            "%s: surface-loss %.4f dB exceeds %.4f dB"
            % (result["id"], result["total_loss_db"], max_loss)
        )
    max_diffuse = requirement.get("max_diffuse_fraction")
    if max_diffuse is None:
        findings.append("%s: no diffusivity limit on record" % result["id"])
    elif not _le(result["diffuse_fraction"], max_diffuse, LIMIT_TOL_FRACTION):
        findings.append(
            "%s: diffuse fraction %.6f exceeds %.6f"
            % (result["id"], result["diffuse_fraction"], max_diffuse)
        )
    min_xpd = requirement.get("min_cross_polar_discrimination_db")
    if min_xpd is not None:
        if result["cross_polar_discrimination_db"] is None:
            findings.append(
                "%s: depolarisation required but no contributions on record"
                % result["id"]
            )
        elif not _ge(result["cross_polar_discrimination_db"], min_xpd):
            findings.append(
                "%s: cross-polar-discrimination %.4f dB below %.4f dB"
                % (result["id"], result["cross_polar_discrimination_db"], min_xpd)
            )
    result["findings"] = findings
    result["compliant"] = not findings
    return result


def assess_radiating_path(specs, requirements):
    """Assess every surface in a radiating path; roll up the loss budget."""
    if not specs:
        raise ValueError("specs must contain at least one surface")
    if not isinstance(requirements, dict):
        raise ValueError("requirements must be a mapping of id -> requirement")
    results = []
    findings = []
    total_loss_db = 0.0
    for spec in specs:
        surface_id = spec.get("id") if isinstance(spec, dict) else None
        if surface_id is None:
            raise ValueError("every surface spec needs an 'id'")
        if surface_id not in requirements:
            raise ValueError("no requirement on record for surface %r" % surface_id)
        result = assess_surface(spec, requirements[surface_id])
        results.append(result)
        findings.extend(result["findings"])
        total_loss_db += result["total_loss_db"]
    return {
        "surfaces": results,
        "path_total_loss_db": total_loss_db,
        "findings": findings,
        "compliant": not findings,
    }
