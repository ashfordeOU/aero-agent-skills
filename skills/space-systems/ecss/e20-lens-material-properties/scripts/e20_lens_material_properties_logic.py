#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 7.2.2.3.3 lens material properties
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard expects the reflective and the
transmissive behaviour of lens materials, and the impact of that
behaviour on antenna performance, to be quantified as part of the
antenna design. This module implements the checkable part of that
clause: categorization of a lens material into a dielectric family,
the refractive index and interface reflectance its relative
permittivity implies, the transmission loss of the illuminated and the
exit face, the quarter-wave matching layer that cancels a face
reflection, the absorption a loss tangent costs along the ray path,
the aperture phase error a permittivity tolerance produces, the gain
that phase error costs, the wave returned toward the feed, and the
comparison of the summed lens loss against its allocation. It does not
trace rays through a lens profile, does not synthesise a lens shape,
and does not qualify a moulding process.
"""

import math

# Relative tolerance that absorbs floating-point representation error
# when a quantity sits exactly on a limit. It widens no engineering
# limit: it only stops a value that is mathematically equal to the
# limit from reading as a violation a few ULPs out.
LIMIT_REL_TOL = 1e-9

SPEED_OF_LIGHT_M_PER_S = 299792458.0

# Relative permittivity of the medium the lens radiates into.
FREE_SPACE_RELATIVE_PERMITTIVITY = 1.0

# Loss tangent above which the low-loss attenuation form stops being
# the right physics for a lens material.
MAX_MODELLED_LOSS_TANGENT = 0.1

# Aperture phase error above which the square-law gain penalty is no
# longer a small-error approximation.
MAX_MODELLED_PHASE_ERROR_DEG = 90.0

# Reported when a face reflects nothing measurable, so the return
# toward the feed is bounded only by the model.
UNBOUNDED_RETURN_LOSS_DB = 200.0

LENS_MATERIALS = {
    "polytetrafluoroethylene": {
        "family": "low_loss_thermoplastic",
        "relative_permittivity": 2.05,
        "loss_tangent": 2.0e-4,
    },
    "cross_linked_polystyrene": {
        "family": "low_loss_thermoplastic",
        "relative_permittivity": 2.53,
        "loss_tangent": 6.0e-4,
    },
    "polypropylene": {
        "family": "low_loss_thermoplastic",
        "relative_permittivity": 2.25,
        "loss_tangent": 3.0e-4,
    },
    "expanded_polystyrene_foam": {
        "family": "dielectric_foam",
        "relative_permittivity": 1.05,
        "loss_tangent": 2.0e-4,
    },
    "polymethacrylimide_foam": {
        "family": "dielectric_foam",
        "relative_permittivity": 1.10,
        "loss_tangent": 5.0e-4,
    },
    "alumina_ceramic": {
        "family": "ceramic_dielectric",
        "relative_permittivity": 9.80,
        "loss_tangent": 1.0e-4,
    },
    "fused_quartz": {
        "family": "ceramic_dielectric",
        "relative_permittivity": 3.78,
        "loss_tangent": 1.0e-4,
    },
    "parallel_plate_metal_lens": {
        "family": "artificial_dielectric",
        "relative_permittivity": 0.60,
        "loss_tangent": 1.0e-4,
    },
    "dielectric_loaded_lattice": {
        "family": "artificial_dielectric",
        "relative_permittivity": 1.60,
        "loss_tangent": 8.0e-4,
    },
}


def _within_upper_limit(value, limit):
    """True when value is at or below limit, treating a value equal to
    the limit within LIMIT_REL_TOL as within it."""
    return value <= limit or math.isclose(value, limit, rel_tol=LIMIT_REL_TOL)


def _meets_lower_limit(value, limit):
    """True when value is at or above limit, treating a value equal to
    the limit within LIMIT_REL_TOL as meeting it."""
    return value >= limit or math.isclose(value, limit, rel_tol=LIMIT_REL_TOL)


def categorize_lens_material(material):
    """Dielectric family of a lens material:
    "low_loss_thermoplastic", "dielectric_foam", "ceramic_dielectric"
    or "artificial_dielectric". Raises ValueError for a material
    outside the clause 7.2.2.3.3 set."""
    entry = LENS_MATERIALS.get(material)
    if entry is None:
        raise ValueError("uncategorized lens material: %r" % (material,))
    return entry["family"]


def lens_relative_permittivity(material):
    """Relative permittivity of a known lens material. Raises
    ValueError for an unknown material."""
    categorize_lens_material(material)
    return LENS_MATERIALS[material]["relative_permittivity"]


def lens_loss_tangent(material):
    """Loss tangent of a known lens material. Raises ValueError for an
    unknown material."""
    categorize_lens_material(material)
    return LENS_MATERIALS[material]["loss_tangent"]


def wavelength_m(frequency_hz):
    """Free-space wavelength in metres. Raises ValueError for a
    non-positive frequency."""
    if frequency_hz <= 0.0:
        raise ValueError("frequency must be positive, got %r" % (frequency_hz,))
    return SPEED_OF_LIGHT_M_PER_S / float(frequency_hz)


def refractive_index(relative_permittivity):
    """Refractive index of a non-magnetic dielectric. Raises ValueError
    for a non-positive relative permittivity."""
    if relative_permittivity <= 0.0:
        raise ValueError(
            "relative permittivity must be positive, got %r" % (relative_permittivity,)
        )
    return math.sqrt(relative_permittivity)


def interface_power_reflectance(permittivity_in, permittivity_out):
    """Fraction of normally incident power reflected at the boundary
    between two dielectrics. Raises ValueError through
    refractive_index for a non-positive permittivity."""
    n_in = refractive_index(permittivity_in)
    n_out = refractive_index(permittivity_out)
    gamma = (n_in - n_out) / (n_in + n_out)
    return gamma * gamma


def matched_face_power_reflectance(lens_permittivity, layer_permittivity):
    """Fraction of power reflected at a lens face carrying a
    quarter-wave layer of the given permittivity, at the design
    frequency. Reduces to zero when the layer permittivity is the
    geometric mean of the two media. Raises ValueError for a
    non-positive permittivity."""
    n_lens = refractive_index(lens_permittivity)
    n_layer = refractive_index(layer_permittivity)
    n_air = refractive_index(FREE_SPACE_RELATIVE_PERMITTIVITY)
    numerator = n_air * n_lens - n_layer * n_layer
    denominator = n_air * n_lens + n_layer * n_layer
    gamma = numerator / denominator
    return gamma * gamma


def quarter_wave_matching_layer(lens_permittivity, frequency_hz):
    """Permittivity and physical thickness of the quarter-wave layer
    that cancels the reflection of one lens face. Raises ValueError for
    a non-positive permittivity, and for a lens whose required layer
    permittivity falls below free space, which no natural dielectric
    provides."""
    n_lens = refractive_index(lens_permittivity)
    layer_permittivity = math.sqrt(
        FREE_SPACE_RELATIVE_PERMITTIVITY * n_lens * n_lens
    )
    if not _meets_lower_limit(layer_permittivity, FREE_SPACE_RELATIVE_PERMITTIVITY):
        raise ValueError(
            "required matching-layer permittivity %r is below free space"
            % (layer_permittivity,)
        )
    lam = wavelength_m(frequency_hz)
    thickness = lam / (4.0 * math.sqrt(layer_permittivity))
    return {
        "layer_relative_permittivity": layer_permittivity,
        "layer_thickness_m": thickness,
    }


def face_transmission_loss_db(face_reflectance, face_count=2):
    """Transmission loss, in decibels, of the lens faces, each
    reflecting the given fraction of power. Raises ValueError for a
    reflectance outside zero to one, or a face count below one."""
    if not 0.0 <= face_reflectance < 1.0:
        raise ValueError(
            "face reflectance must be in [0, 1), got %r" % (face_reflectance,)
        )
    if face_count < 1:
        raise ValueError("face count must be at least 1, got %r" % (face_count,))
    return -10.0 * face_count * math.log10(1.0 - face_reflectance)


def dielectric_absorption_loss_db(
    relative_permittivity, loss_tangent, ray_path_length_m, frequency_hz
):
    """Loss the material absorbs along the ray path, in decibels.
    Raises ValueError for a negative loss tangent, a loss tangent
    outside the low-loss form, or a non-positive path length."""
    if loss_tangent < 0.0:
        raise ValueError("loss tangent must not be negative, got %r" % (loss_tangent,))
    if not _within_upper_limit(loss_tangent, MAX_MODELLED_LOSS_TANGENT):
        raise ValueError(
            "loss tangent %r is outside the low-loss attenuation form" % (loss_tangent,)
        )
    if ray_path_length_m <= 0.0:
        raise ValueError(
            "ray path length must be positive, got %r" % (ray_path_length_m,)
        )
    lam = wavelength_m(frequency_hz)
    n = refractive_index(relative_permittivity)
    attenuation_np_per_m = math.pi * n * loss_tangent / lam
    return 20.0 * math.log10(math.e) * attenuation_np_per_m * ray_path_length_m


def permittivity_tolerance_phase_error_deg(
    relative_permittivity, permittivity_tolerance, lens_thickness_m, frequency_hz
):
    """Aperture phase error, in degrees, a spread on the relative
    permittivity produces across the lens thickness. Raises ValueError
    for a non-positive thickness or a tolerance that drives the
    permittivity to zero or below."""
    if lens_thickness_m <= 0.0:
        raise ValueError("lens thickness must be positive, got %r" % (lens_thickness_m,))
    nominal = refractive_index(relative_permittivity)
    perturbed_permittivity = relative_permittivity + abs(permittivity_tolerance)
    lower_permittivity = relative_permittivity - abs(permittivity_tolerance)
    if lower_permittivity <= 0.0:
        raise ValueError(
            "permittivity tolerance %r drives the permittivity to zero or below"
            % (permittivity_tolerance,)
        )
    perturbed = refractive_index(perturbed_permittivity)
    lam = wavelength_m(frequency_hz)
    return 360.0 * abs(perturbed - nominal) * lens_thickness_m / lam


def phase_error_gain_loss_db(phase_error_deg):
    """Gain a lens aperture phase error costs, in decibels. Raises
    ValueError for a negative error or an error outside the
    small-error square-law form."""
    if phase_error_deg < 0.0:
        raise ValueError("phase error must not be negative, got %r" % (phase_error_deg,))
    if not _within_upper_limit(phase_error_deg, MAX_MODELLED_PHASE_ERROR_DEG):
        raise ValueError(
            "phase error %r is outside the small-error gain form" % (phase_error_deg,)
        )
    phase_rad = math.radians(phase_error_deg)
    return 10.0 * math.log10(math.e) * phase_rad * phase_rad


def feed_return_loss_db(face_reflectance, feed_capture_fraction=1.0):
    """Return loss seen at the feed, in decibels, from the wave the
    illuminated face sends back along the axis. Raises ValueError for a
    reflectance outside zero to one or a capture fraction outside the
    open interval zero to one inclusive."""
    if not 0.0 <= face_reflectance <= 1.0:
        raise ValueError(
            "face reflectance must be in [0, 1], got %r" % (face_reflectance,)
        )
    if not 0.0 < feed_capture_fraction <= 1.0:
        raise ValueError(
            "feed capture fraction must be in (0, 1], got %r" % (feed_capture_fraction,)
        )
    returned = face_reflectance * feed_capture_fraction
    if returned <= 0.0:
        return UNBOUNDED_RETURN_LOSS_DB
    return min(UNBOUNDED_RETURN_LOSS_DB, -10.0 * math.log10(returned))


def total_lens_loss_db(loss_terms):
    """Sum of the named lens loss terms, in decibels. Raises ValueError
    for an empty set of terms or a negative term."""
    if not loss_terms:
        raise ValueError("at least one loss term is required")
    total = 0.0
    for name, value in sorted(loss_terms.items()):
        if value < 0.0:
            raise ValueError("loss term %r must not be negative, got %r" % (name, value))
        total += value
    return total


def _require(record, key):
    if key not in record:
        raise ValueError("lens record missing key %r" % (key,))
    return record[key]


def assess_lens_material(record):
    """Assess one lens material against clause 7.2.2.3.3 and return the
    aggregated result.

    Required keys: material, frequency_hz, ray_path_length_m,
    lens_thickness_m, permittivity_tolerance, max_phase_error_deg,
    required_feed_return_loss_db, allocated_loss_db. Optional key
    matching_layer_permittivity applies a quarter-wave layer to both
    faces; optional key feed_capture_fraction scales the wave the feed
    actually recaptures.
    """
    if not isinstance(record, dict):
        raise ValueError("lens record must be a mapping")
    material = _require(record, "material")
    family = categorize_lens_material(material)
    permittivity = lens_relative_permittivity(material)
    loss_tangent = lens_loss_tangent(material)
    frequency_hz = _require(record, "frequency_hz")
    findings = []

    layer_permittivity = record.get("matching_layer_permittivity")
    if layer_permittivity is None:
        face_reflectance = interface_power_reflectance(
            FREE_SPACE_RELATIVE_PERMITTIVITY, permittivity
        )
    else:
        face_reflectance = matched_face_power_reflectance(
            permittivity, layer_permittivity
        )

    face_loss = face_transmission_loss_db(face_reflectance, face_count=2)
    absorption_loss = dielectric_absorption_loss_db(
        permittivity,
        loss_tangent,
        _require(record, "ray_path_length_m"),
        frequency_hz,
    )
    phase_error = permittivity_tolerance_phase_error_deg(
        permittivity,
        _require(record, "permittivity_tolerance"),
        _require(record, "lens_thickness_m"),
        frequency_hz,
    )
    max_phase_error = _require(record, "max_phase_error_deg")
    if not _within_upper_limit(phase_error, max_phase_error):
        findings.append("lens_aperture_phase_error_above_limit")
    phase_loss = phase_error_gain_loss_db(phase_error)

    return_loss = feed_return_loss_db(
        face_reflectance, record.get("feed_capture_fraction", 1.0)
    )
    if not _meets_lower_limit(
        return_loss, _require(record, "required_feed_return_loss_db")
    ):
        findings.append("feed_return_loss_below_requirement")

    total_loss = total_lens_loss_db(
        {
            "face_reflection": face_loss,
            "absorption": absorption_loss,
            "phase_error": phase_loss,
        }
    )
    if not _within_upper_limit(total_loss, _require(record, "allocated_loss_db")):
        findings.append("lens_loss_above_allocation")

    return {
        "material_family": family,
        "relative_permittivity": permittivity,
        "loss_tangent": loss_tangent,
        "face_power_reflectance": face_reflectance,
        "face_transmission_loss_db": face_loss,
        "absorption_loss_db": absorption_loss,
        "lens_aperture_phase_error_deg": phase_error,
        "phase_error_loss_db": phase_loss,
        "feed_return_loss_db": return_loss,
        "total_loss_db": total_loss,
        "findings": findings,
        "lens_material_acceptable": not findings,
    }
