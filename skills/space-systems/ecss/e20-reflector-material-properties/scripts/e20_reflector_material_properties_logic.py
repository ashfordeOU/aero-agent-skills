#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 7.2.2.3.2 reflector material properties
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard expects the reflective behaviour of
reflector materials and composites, and the impact of that behaviour on
antenna performance, to be quantified as part of the antenna design.
This module implements the checkable part of that clause:
categorization of a reflecting surface into a material family, the
skin depth that sets the required metallisation thickness, the radio
frequency surface resistance a conductivity implies, the ohmic
reflection loss per bounce, the leakage of a knitted metal mesh from
its cell opening and wire radius, the thermoelastic surface error a
material expansion produces, the Ruze gain loss that error costs, and
the comparison of the summed reflector loss against its allocation. It
does not run a physical-optics scattering solve, does not synthesise a
reflector shape, and does not qualify a coating process.
"""

import math

# Relative tolerance that absorbs floating-point representation error
# when a quantity sits exactly on a limit. It widens no engineering
# limit: it only stops a value that is mathematically equal to the
# limit from reading as a violation a few ULPs out.
LIMIT_REL_TOL = 1e-9

SPEED_OF_LIGHT_M_PER_S = 299792458.0
VACUUM_PERMEABILITY_H_PER_M = 4.0e-7 * math.pi
FREE_SPACE_WAVE_IMPEDANCE_OHM = 376.730313668

# A deposited metallisation stops the substrate participating once it
# is this many skin depths thick at the lowest frequency of the band.
MIN_METALLISATION_SKIN_DEPTHS = 5.0

# Good-conductor reflection model validity: the absorbed fraction must
# stay well below unity for the surface to be a reflector at all.
MAX_MODELLED_ABSORBED_FRACTION = 1.0

# A woven grid behaves as an inductive sheet only while its opening is
# electrically small; above this the grating regime takes over.
MESH_MAX_CELL_WAVELENGTHS = 0.5

# The Ruze relation is the small-error form; above this surface error
# in wavelengths the scattered power is no longer a small perturbation.
RUZE_MAX_RMS_WAVELENGTHS = 0.1

# Ohmic loss above this, for a laminate carrying no metallisation, is
# reported so the bare surface is a decision and not an oversight.
BARE_COMPOSITE_OHMIC_LOSS_LIMIT_DB = 0.05

REFLECTOR_MATERIALS = {
    "aluminium_alloy_sheet": {
        "family": "metallic_sheet",
        "conductivity_s_per_m": 2.2e7,
        "expansion_per_k": 23.0e-6,
    },
    "copper_clad_sheet": {
        "family": "metallic_sheet",
        "conductivity_s_per_m": 5.8e7,
        "expansion_per_k": 17.0e-6,
    },
    "cfrp_with_vapour_deposited_aluminium": {
        "family": "metallised_composite",
        "conductivity_s_per_m": 3.5e7,
        "expansion_per_k": 1.0e-6,
    },
    "cfrp_with_electroplated_copper": {
        "family": "metallised_composite",
        "conductivity_s_per_m": 5.0e7,
        "expansion_per_k": 1.2e-6,
    },
    "polyimide_membrane_with_vapour_deposited_aluminium": {
        "family": "metallised_membrane",
        "conductivity_s_per_m": 3.5e7,
        "expansion_per_k": 20.0e-6,
    },
    "bare_carbon_fibre_laminate": {
        "family": "bare_composite",
        "conductivity_s_per_m": 1.0e4,
        "expansion_per_k": 0.5e-6,
    },
    "gold_plated_molybdenum_mesh": {
        "family": "knitted_metal_mesh",
        "conductivity_s_per_m": 4.1e7,
        "expansion_per_k": 5.0e-6,
    },
    "silver_plated_tungsten_mesh": {
        "family": "knitted_metal_mesh",
        "conductivity_s_per_m": 6.1e7,
        "expansion_per_k": 4.5e-6,
    },
}

METALLISED_FAMILIES = frozenset({"metallised_composite", "metallised_membrane"})


def _within_upper_limit(value, limit):
    """True when value is at or below limit, treating a value equal to
    the limit within LIMIT_REL_TOL as within it."""
    return value <= limit or math.isclose(value, limit, rel_tol=LIMIT_REL_TOL)


def _meets_lower_limit(value, limit):
    """True when value is at or above limit, treating a value equal to
    the limit within LIMIT_REL_TOL as meeting it."""
    return value >= limit or math.isclose(value, limit, rel_tol=LIMIT_REL_TOL)


def categorize_reflector_material(material):
    """Material family of a reflecting surface: "metallic_sheet",
    "metallised_composite", "metallised_membrane", "bare_composite" or
    "knitted_metal_mesh". Raises ValueError for a material outside the
    clause 7.2.2.3.2 set."""
    entry = REFLECTOR_MATERIALS.get(material)
    if entry is None:
        raise ValueError("uncategorized reflector material: %r" % (material,))
    return entry["family"]


def material_conductivity_s_per_m(material):
    """Bulk conductivity of the reflecting layer of a known material,
    in siemens per metre. Raises ValueError for an unknown material."""
    categorize_reflector_material(material)
    return REFLECTOR_MATERIALS[material]["conductivity_s_per_m"]


def material_expansion_per_k(material):
    """Coefficient of thermal expansion of a known material, per
    kelvin. Raises ValueError for an unknown material."""
    categorize_reflector_material(material)
    return REFLECTOR_MATERIALS[material]["expansion_per_k"]


def wavelength_m(frequency_hz):
    """Free-space wavelength in metres. Raises ValueError for a
    non-positive frequency."""
    if frequency_hz <= 0.0:
        raise ValueError("frequency must be positive, got %r" % (frequency_hz,))
    return SPEED_OF_LIGHT_M_PER_S / float(frequency_hz)


def skin_depth_m(conductivity_s_per_m, frequency_hz, relative_permeability=1.0):
    """Depth at which the conduction current has fallen to one over e,
    in metres. Raises ValueError for a non-positive conductivity,
    frequency or relative permeability."""
    if conductivity_s_per_m <= 0.0:
        raise ValueError(
            "conductivity must be positive, got %r" % (conductivity_s_per_m,)
        )
    if relative_permeability <= 0.0:
        raise ValueError(
            "relative permeability must be positive, got %r" % (relative_permeability,)
        )
    if frequency_hz <= 0.0:
        raise ValueError("frequency must be positive, got %r" % (frequency_hz,))
    omega = 2.0 * math.pi * frequency_hz
    mu = VACUUM_PERMEABILITY_H_PER_M * relative_permeability
    return math.sqrt(2.0 / (omega * mu * conductivity_s_per_m))


def required_metallisation_thickness_m(
    conductivity_s_per_m, lowest_frequency_hz, skin_depths=MIN_METALLISATION_SKIN_DEPTHS
):
    """Deposited layer thickness a metallised surface needs at the
    lowest frequency of the band, in metres. Raises ValueError for a
    non-positive skin-depth count."""
    if skin_depths <= 0.0:
        raise ValueError("skin-depth count must be positive, got %r" % (skin_depths,))
    return skin_depths * skin_depth_m(conductivity_s_per_m, lowest_frequency_hz)


def conductor_surface_resistance_ohm(
    conductivity_s_per_m, frequency_hz, relative_permeability=1.0
):
    """Radio-frequency surface resistance of a conducting surface, in
    ohms per square. Raises ValueError through skin_depth_m for any
    non-positive input."""
    delta = skin_depth_m(conductivity_s_per_m, frequency_hz, relative_permeability)
    return 1.0 / (conductivity_s_per_m * delta)


def ohmic_reflection_loss_db(surface_resistance_ohm, incidence_angle_deg=0.0):
    """Loss of one reflection off a conducting surface, in decibels,
    from its surface resistance. Uses the good-conductor form for the
    perpendicular field orientation, which reduces to the normal
    incidence result at zero degrees. Raises ValueError for a
    non-positive surface resistance, an incidence angle outside zero to
    90 degrees, or a surface so resistive that the absorbed fraction
    reaches unity and the surface is no longer a reflector."""
    if surface_resistance_ohm <= 0.0:
        raise ValueError(
            "surface resistance must be positive, got %r" % (surface_resistance_ohm,)
        )
    if not 0.0 <= incidence_angle_deg < 90.0:
        raise ValueError(
            "incidence angle must be in [0, 90) degrees, got %r" % (incidence_angle_deg,)
        )
    absorbed = (
        4.0
        * surface_resistance_ohm
        * math.cos(math.radians(incidence_angle_deg))
        / FREE_SPACE_WAVE_IMPEDANCE_OHM
    )
    if absorbed >= MAX_MODELLED_ABSORBED_FRACTION:
        raise ValueError(
            "surface resistance %r is outside the good-conductor reflection model"
            % (surface_resistance_ohm,)
        )
    return -10.0 * math.log10(1.0 - absorbed)


def mesh_normalised_reactance(cell_size_m, wire_radius_m, frequency_hz):
    """Shunt reactance of a woven grid normalised to the free-space
    wave impedance. Raises ValueError for a non-positive dimension, a
    wire radius too large for the inductive-grid form, or a cell
    opening that is no longer electrically small."""
    if cell_size_m <= 0.0:
        raise ValueError("mesh cell size must be positive, got %r" % (cell_size_m,))
    if wire_radius_m <= 0.0:
        raise ValueError("wire radius must be positive, got %r" % (wire_radius_m,))
    if wire_radius_m >= cell_size_m / (2.0 * math.pi):
        raise ValueError(
            "wire radius %r is too large for the inductive-grid model at cell %r"
            % (wire_radius_m, cell_size_m)
        )
    lam = wavelength_m(frequency_hz)
    if cell_size_m >= MESH_MAX_CELL_WAVELENGTHS * lam:
        raise ValueError(
            "mesh cell %r is not electrically small at %r Hz" % (cell_size_m, frequency_hz)
        )
    return (cell_size_m / lam) * math.log(cell_size_m / (2.0 * math.pi * wire_radius_m))


def mesh_leakage_loss_db(cell_size_m, wire_radius_m, frequency_hz):
    """Reflection loss of a knitted metal mesh caused by leakage
    through its openings, in decibels. Raises ValueError through
    mesh_normalised_reactance for an invalid geometry."""
    x = mesh_normalised_reactance(cell_size_m, wire_radius_m, frequency_hz)
    return 10.0 * math.log10(1.0 + 4.0 * x * x)


def thermoelastic_surface_rms_m(
    expansion_per_k, temperature_excursion_k, characteristic_length_m, distortion_factor
):
    """Surface root-mean-square error a thermal excursion produces on a
    reflector of a given size, in metres. Raises ValueError for a
    negative expansion coefficient, a non-positive length, or a
    distortion factor outside the open interval zero to one
    inclusive."""
    if expansion_per_k < 0.0:
        raise ValueError(
            "expansion coefficient must not be negative, got %r" % (expansion_per_k,)
        )
    if characteristic_length_m <= 0.0:
        raise ValueError(
            "characteristic length must be positive, got %r" % (characteristic_length_m,)
        )
    if not 0.0 < distortion_factor <= 1.0:
        raise ValueError(
            "distortion factor must be in (0, 1], got %r" % (distortion_factor,)
        )
    return (
        distortion_factor
        * expansion_per_k
        * abs(temperature_excursion_k)
        * characteristic_length_m
    )


def ruze_gain_loss_db(surface_rms_m, frequency_hz):
    """Gain loss a surface error costs under the Ruze relation, in
    decibels. Raises ValueError for a negative error or an error too
    large in wavelengths for the small-error form."""
    if surface_rms_m < 0.0:
        raise ValueError("surface error must not be negative, got %r" % (surface_rms_m,))
    lam = wavelength_m(frequency_hz)
    if not _within_upper_limit(surface_rms_m, RUZE_MAX_RMS_WAVELENGTHS * lam):
        raise ValueError(
            "surface error %r is outside the small-error Ruze form at %r Hz"
            % (surface_rms_m, frequency_hz)
        )
    phase = 4.0 * math.pi * surface_rms_m / lam
    return 10.0 * math.log10(math.e) * phase * phase


def total_reflector_loss_db(loss_terms):
    """Sum of the named reflector loss terms, in decibels. Raises
    ValueError for an empty set of terms or a negative term."""
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
        raise ValueError("reflector record missing key %r" % (key,))
    return record[key]


def assess_reflector_material(record):
    """Assess one reflecting surface against clause 7.2.2.3.2 and
    return the aggregated result.

    Required keys: material, lowest_frequency_hz, highest_frequency_hz,
    incidence_angle_deg, temperature_excursion_k,
    characteristic_length_m, distortion_factor, allocated_loss_db. A
    metallised family also needs metallisation_thickness_m; a knitted
    metal mesh also needs cell_size_m and wire_radius_m.
    """
    if not isinstance(record, dict):
        raise ValueError("reflector record must be a mapping")
    material = _require(record, "material")
    family = categorize_reflector_material(material)
    low_hz = _require(record, "lowest_frequency_hz")
    high_hz = _require(record, "highest_frequency_hz")
    if high_hz < low_hz:
        raise ValueError(
            "highest frequency %r is below lowest frequency %r" % (high_hz, low_hz)
        )
    sigma = material_conductivity_s_per_m(material)
    findings = []

    skin_depth = skin_depth_m(sigma, low_hz)
    required_thickness = required_metallisation_thickness_m(sigma, low_hz)
    thickness = None
    if family in METALLISED_FAMILIES:
        thickness = _require(record, "metallisation_thickness_m")
        if thickness <= 0.0:
            raise ValueError(
                "metallisation thickness must be positive, got %r" % (thickness,)
            )
        if not _meets_lower_limit(thickness, required_thickness):
            findings.append("metallisation_thinner_than_required")

    surface_resistance = conductor_surface_resistance_ohm(sigma, high_hz)
    ohmic_loss = ohmic_reflection_loss_db(
        surface_resistance, _require(record, "incidence_angle_deg")
    )
    if family == "bare_composite" and not _within_upper_limit(
        ohmic_loss, BARE_COMPOSITE_OHMIC_LOSS_LIMIT_DB
    ):
        findings.append("unmetallised_composite_reflection_loss_significant")

    leakage_loss = 0.0
    if family == "knitted_metal_mesh":
        leakage_loss = mesh_leakage_loss_db(
            _require(record, "cell_size_m"),
            _require(record, "wire_radius_m"),
            high_hz,
        )

    surface_rms = thermoelastic_surface_rms_m(
        material_expansion_per_k(material),
        _require(record, "temperature_excursion_k"),
        _require(record, "characteristic_length_m"),
        _require(record, "distortion_factor"),
    )
    surface_loss = ruze_gain_loss_db(surface_rms, high_hz)

    total_loss = total_reflector_loss_db(
        {
            "ohmic": ohmic_loss,
            "mesh_leakage": leakage_loss,
            "surface_error": surface_loss,
        }
    )
    allocation = _require(record, "allocated_loss_db")
    if not _within_upper_limit(total_loss, allocation):
        findings.append("reflector_loss_above_allocation")

    return {
        "material_family": family,
        "skin_depth_m": skin_depth,
        "required_metallisation_thickness_m": required_thickness,
        "metallisation_thickness_m": thickness,
        "surface_resistance_ohm": surface_resistance,
        "ohmic_loss_db": ohmic_loss,
        "mesh_leakage_loss_db": leakage_loss,
        "surface_rms_m": surface_rms,
        "surface_error_loss_db": surface_loss,
        "total_loss_db": total_loss,
        "findings": findings,
        "reflecting_surface_acceptable": not findings,
    }
