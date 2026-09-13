#!/usr/bin/env python3
"""Charge-exchange ion erosion logic for ECSS-E-ST-20-06C clause 11.2.4.

Offline, deterministic, standard-library only. The module carries a
surface exposed to the charge-exchange plasma of an electric thruster
through the chain the clause is verified on: the exposure is categorized
as direct-beam impingement, charge-exchange backflow or no exposure; the
collected ion current density is converted into an ion number flux; the
near-threshold sputter yield of the surface material at the arrival
energy is evaluated; yield and flux give an erosion rate, the rate over
the exposure time gives an erosion depth, and that depth is compared
against the agreed erosion allowance and the coating reserve.

The sputter yield uses a documented near-threshold fit of the form
k * (sqrt(E) - sqrt(E_threshold))^2, saturating at a tabulated maximum.
The constants are engineering fit values carried with the module, not
reproduced standard text; the clause is cited as the anchor only.
"""

import math

__all__ = [
    "material_properties",
    "sputter_yield",
    "categorize_ion_exposure",
    "ion_number_flux",
    "erosion_rate_m_per_s",
    "erosion_depth_um",
    "check_erosion_allowance",
    "check_coating_reserve",
    "assess_surface_erosion",
    "assess_erosion_campaign",
]

# Representation tolerance for at-the-limit comparisons. It absorbs the
# few ULPs a product of powers can land above an exact limit; the agreed
# erosion allowance itself is never widened.
_REL_TOL = 1e-9
_ABS_TOL = 1e-15

ELEMENTARY_CHARGE_C = 1.602176634e-19

# material -> sputter-threshold energy (eV), near-threshold coefficient
# (atoms per ion per eV), saturation yield (atoms per ion), atomic number
# density (atoms per m^3).
MATERIAL_PROPERTIES = {
    "aluminium-alloy": {
        "threshold_ev": 20.0,
        "yield_coefficient": 0.012,
        "yield_max": 3.0,
        "number_density_m3": 6.03e28,
    },
    "silver-coating": {
        "threshold_ev": 15.0,
        "yield_coefficient": 0.020,
        "yield_max": 4.0,
        "number_density_m3": 5.86e28,
    },
    "molybdenum-grid": {
        "threshold_ev": 28.0,
        "yield_coefficient": 0.006,
        "yield_max": 2.0,
        "number_density_m3": 6.40e28,
    },
    "quartz-osr": {
        "threshold_ev": 30.0,
        "yield_coefficient": 0.004,
        "yield_max": 1.5,
        "number_density_m3": 6.60e28,
    },
    "solar-cell-coverglass": {
        "threshold_ev": 30.0,
        "yield_coefficient": 0.004,
        "yield_max": 1.5,
        "number_density_m3": 6.60e28,
    },
    "polyimide-blanket": {
        "threshold_ev": 15.0,
        "yield_coefficient": 0.010,
        "yield_max": 2.0,
        "number_density_m3": 5.00e28,
    },
}

DIRECT_BEAM_EXPOSURE = "direct-beam-impingement"
BACKFLOW_EXPOSURE = "charge-exchange-backflow"
NO_EXPOSURE = "no-ion-exposure"

# Findings that record an assessment weakness rather than a clause breach.
ADVISORY_FINDINGS = frozenset(
    ("sputtered-material-redeposition-not-assessed",)
)


def _number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _positive(name, value):
    out = _number(name, value)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (name, value))
    return out


def _non_negative(name, value):
    out = _number(name, value)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (name, value))
    return out


def _angle(name, value, lower, upper):
    out = _number(name, value)
    if not lower <= out <= upper:
        raise ValueError(
            "%s must lie in [%g, %g] degrees, got %r" % (name, lower, upper, value)
        )
    return out


def _at_or_below(value, limit):
    """True when value is below limit or equal to it within representation."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def material_properties(material):
    """Return the sputter fit constants tabulated for a surface material."""
    if not isinstance(material, str):
        raise ValueError("material must be a string, got %r" % (material,))
    key = material.strip().lower().replace("_", "-").replace(" ", "-")
    if not key:
        raise ValueError("material must not be empty")
    if key not in MATERIAL_PROPERTIES:
        raise ValueError(
            "uncategorized surface material %r; expected one of %s"
            % (material, ", ".join(sorted(MATERIAL_PROPERTIES)))
        )
    properties = dict(MATERIAL_PROPERTIES[key])
    properties["material"] = key
    return properties


def sputter_yield(material, ion_energy_ev):
    """Atoms removed per arriving ion at the given impact energy.

    Below (or at) the material threshold the surface does not sputter.
    Above it the near-threshold fit applies, saturating at yield_max.
    """
    properties = material_properties(material)
    energy = _non_negative("ion_energy_ev", ion_energy_ev)
    threshold = properties["threshold_ev"]
    if _at_or_below(energy, threshold):
        return 0.0
    excess = math.sqrt(energy) - math.sqrt(threshold)
    raw = properties["yield_coefficient"] * excess * excess
    return min(raw, properties["yield_max"])


def categorize_ion_exposure(surface_angle_deg, plume_half_angle_deg,
                            line_of_sight=True):
    """Categorize how thruster ions reach a surface.

    Inside the beam cone with a clear view the surface takes direct beam
    impingement -- a condition clause 11.2.4 does not cover with a
    charge-exchange allowance and which the caller has to treat as a
    design finding. Outside the cone the surface sees charge-exchange
    backflow. A shadowed surface sees no ions at all.
    """
    angle = _angle("surface_angle_deg", surface_angle_deg, 0.0, 180.0)
    half_angle = _angle("plume_half_angle_deg", plume_half_angle_deg, 0.0, 90.0)
    if half_angle <= 0.0:
        raise ValueError(
            "plume_half_angle_deg must be > 0, got %r" % (plume_half_angle_deg,)
        )
    if not isinstance(line_of_sight, bool):
        raise ValueError("line_of_sight must be a boolean, got %r" % (line_of_sight,))
    if not line_of_sight:
        return NO_EXPOSURE
    if _at_or_below(angle, half_angle):
        return DIRECT_BEAM_EXPOSURE
    return BACKFLOW_EXPOSURE


def ion_number_flux(current_density_a_m2, charge_state=1):
    """Ion number flux (ions/m^2/s) behind a collected current density."""
    current_density = _non_negative("current_density_a_m2", current_density_a_m2)
    if isinstance(charge_state, bool) or not isinstance(charge_state, int):
        raise ValueError("charge_state must be an integer, got %r" % (charge_state,))
    if charge_state < 1:
        raise ValueError("charge_state must be >= 1, got %r" % (charge_state,))
    return current_density / (charge_state * ELEMENTARY_CHARGE_C)


def erosion_rate_m_per_s(ion_flux_m2_s, yield_atoms_per_ion, number_density_m3):
    """Recession rate of a surface under a sputtering ion flux."""
    flux = _non_negative("ion_flux_m2_s", ion_flux_m2_s)
    sputtering = _non_negative("yield_atoms_per_ion", yield_atoms_per_ion)
    density = _positive("number_density_m3", number_density_m3)
    return flux * sputtering / density


def erosion_depth_um(rate_m_per_s, exposure_time_s):
    """Eroded depth in micrometres over an exposure time."""
    rate = _non_negative("rate_m_per_s", rate_m_per_s)
    duration = _positive("exposure_time_s", exposure_time_s)
    return rate * duration * 1.0e6


def check_erosion_allowance(depth_um, allowable_depth_um):
    """Compare an eroded depth against the agreed erosion allowance."""
    depth = _non_negative("depth_um", depth_um)
    allowance = _positive("allowable_depth_um", allowable_depth_um)
    return {
        "depth_um": depth,
        "allowable_depth_um": allowance,
        "margin_um": allowance - depth,
        "utilisation": depth / allowance,
        "compliant": _at_or_below(depth, allowance),
    }


def check_coating_reserve(depth_um, coating_thickness_um):
    """Check the eroded depth stays inside the coating that protects it."""
    depth = _non_negative("depth_um", depth_um)
    thickness = _positive("coating_thickness_um", coating_thickness_um)
    return {
        "depth_um": depth,
        "coating_thickness_um": thickness,
        "remaining_um": thickness - depth,
        "coating_intact": _at_or_below(depth, thickness),
    }


def assess_surface_erosion(surface):
    """Assess one surface against the clause 11.2.4 erosion allowance."""
    if not isinstance(surface, dict):
        raise ValueError("surface must be a mapping, got %r" % (type(surface),))
    required = (
        "id",
        "material",
        "ion_energy_ev",
        "current_density_a_m2",
        "exposure_time_s",
        "surface_angle_deg",
        "plume_half_angle_deg",
    )
    missing = [key for key in required if key not in surface]
    if missing:
        raise ValueError(
            "surface record is missing required key(s): %s" % ", ".join(missing)
        )
    identifier = surface["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("surface id must be a non-empty string, got %r" % (identifier,))
    properties = material_properties(surface["material"])
    exposure = categorize_ion_exposure(
        surface["surface_angle_deg"],
        surface["plume_half_angle_deg"],
        surface.get("line_of_sight", True),
    )
    findings = []
    observations = []
    if exposure == DIRECT_BEAM_EXPOSURE:
        findings.append("surface-inside-direct-beam-cone")
    yield_atoms = sputter_yield(surface["material"], surface["ion_energy_ev"])
    if yield_atoms <= 0.0:
        observations.append("ion-energy-below-sputter-threshold")
    if exposure == NO_EXPOSURE:
        flux = 0.0
    else:
        flux = ion_number_flux(
            surface["current_density_a_m2"], surface.get("charge_state", 1)
        )
    rate = erosion_rate_m_per_s(flux, yield_atoms, properties["number_density_m3"])
    depth = erosion_depth_um(rate, surface["exposure_time_s"])

    allowance = surface.get("allowable_depth_um")
    allowance_check = None
    if allowance is None:
        findings.append("agreed-erosion-limit-not-recorded")
    else:
        allowance_check = check_erosion_allowance(depth, allowance)
        if not allowance_check["compliant"]:
            findings.append("erosion-depth-exceeds-agreed-limit")

    coating = surface.get("coating_thickness_um")
    coating_check = None
    if coating is not None:
        coating_check = check_coating_reserve(depth, coating)
        if not coating_check["coating_intact"]:
            findings.append("erosion-breaches-coating-thickness")

    if depth > 0.0 and not surface.get("redeposition_assessed", False):
        observations.append("sputtered-material-redeposition-not-assessed")

    blocking = [item for item in findings if item not in ADVISORY_FINDINGS]
    return {
        "id": identifier,
        "material": properties["material"],
        "exposure": exposure,
        "sputter_yield_atoms_per_ion": yield_atoms,
        "ion_flux_m2_s": flux,
        "erosion_rate_m_per_s": rate,
        "erosion_depth_um": depth,
        "allowance_check": allowance_check,
        "coating_check": coating_check,
        "findings": blocking,
        "observations": observations,
        "compliant": not blocking,
    }


def assess_erosion_campaign(surfaces):
    """Aggregate the clause 11.2.4 verdict across exposed surfaces."""
    if isinstance(surfaces, (str, bytes, dict)) or not isinstance(
        surfaces, (list, tuple)
    ):
        raise ValueError("surfaces must be a list of mappings")
    if not surfaces:
        raise ValueError("surfaces must not be empty")
    results = []
    seen = set()
    for surface in surfaces:
        result = assess_surface_erosion(surface)
        if result["id"] in seen:
            raise ValueError("duplicate surface id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    noncompliant = [item["id"] for item in results if not item["compliant"]]
    worst = max(results, key=lambda item: item["erosion_depth_um"])
    return {
        "surface_count": len(results),
        "compliant_count": len(results) - len(noncompliant),
        "noncompliant_ids": noncompliant,
        "worst_surface_id": worst["id"],
        "worst_depth_um": worst["erosion_depth_um"],
        "results": results,
        "findings_by_surface": {
            item["id"]: list(item["findings"]) for item in results
        },
        "compliant": not noncompliant,
    }
