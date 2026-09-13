#!/usr/bin/env python3
"""Plume particle deposition logic for ECSS-E-ST-20-06C clause 11.2.3.

Offline, deterministic, standard-library only. The module carries an
electric-propulsion efflux source through the chain the clause is argued
on: the species is categorized as neutral or charged, its transport path
to a surface is resolved as direct plume-cone impingement or backflow,
the source rate is propagated through cone solid angle, inverse-square
distance and incidence cosine into an areal flux, the flux is accumulated
over the firing duration with a sticking coefficient into a deposited
film, and the film thickness is compared against the deposition limit the
customer agreed.

No standard text is reproduced; the clause is cited as the anchor only.
"""

import math

__all__ = [
    "categorize_efflux_species",
    "plume_transport_path",
    "surface_particle_flux",
    "accumulate_deposition",
    "deposition_thickness_nm",
    "check_deposition_allowance",
    "assess_surface_deposition",
    "assess_deposition_campaign",
]

# Representation tolerance for at-the-limit comparisons. It absorbs the
# few ULPs a product or a quotient can land above an exact limit; the
# agreed engineering limit itself is never widened.
_REL_TOL = 1e-9
_ABS_TOL = 1e-15

NEUTRAL_FAMILY = "neutral-efflux"
CHARGED_FAMILY = "charged-efflux"

SPECIES_FAMILY = {
    "unionized-propellant": NEUTRAL_FAMILY,
    "neutral-propellant": NEUTRAL_FAMILY,
    "cathode-neutral-flow": NEUTRAL_FAMILY,
    "sputtered-neutral": NEUTRAL_FAMILY,
    "thermal-vapour": NEUTRAL_FAMILY,
    "beam-ion": CHARGED_FAMILY,
    "charge-exchange-ion": CHARGED_FAMILY,
    "doubly-charged-ion": CHARGED_FAMILY,
    "sputtered-ion": CHARGED_FAMILY,
}

DIRECT_PATH = "direct-plume-impingement"
CHARGE_EXCHANGE_PATH = "charge-exchange-backflow"
NEUTRAL_SCATTER_PATH = "neutral-scatter-backflow"
NO_TRANSPORT_PATH = "no-transport-path"

BACKFLOW_PATHS = frozenset((CHARGE_EXCHANGE_PATH, NEUTRAL_SCATTER_PATH))
TRANSPORT_PATHS = frozenset(
    (DIRECT_PATH, CHARGE_EXCHANGE_PATH, NEUTRAL_SCATTER_PATH, NO_TRANSPORT_PATH)
)

# Worst-case sticking assumed when a source records no measured value.
DEFAULT_STICKING_COEFFICIENT = 1.0

# Findings that record an assessment weakness rather than a clause breach.
ADVISORY_FINDINGS = frozenset(("sticking-coefficient-defaulted-to-unity",))


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


def _fraction(name, value):
    out = _number(name, value)
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %r" % (name, value))
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


def categorize_efflux_species(species):
    """Categorize an efflux species as neutral-efflux or charged-efflux."""
    if not isinstance(species, str):
        raise ValueError("species must be a string, got %r" % (species,))
    key = species.strip().lower().replace("_", "-").replace(" ", "-")
    if not key:
        raise ValueError("species must not be empty")
    if key not in SPECIES_FAMILY:
        raise ValueError(
            "uncategorized efflux species %r; expected one of %s"
            % (species, ", ".join(sorted(SPECIES_FAMILY)))
        )
    return SPECIES_FAMILY[key]


def plume_transport_path(species, surface_angle_deg, plume_half_angle_deg,
                         line_of_sight=True):
    """Resolve how a species reaches a surface off the thrust axis.

    A surface inside the plume cone with an unobstructed view takes direct
    impingement. Outside the cone, charged species arrive by
    charge-exchange backflow and neutral species by scatter backflow. No
    line of sight means no transport path at all.
    """
    family = categorize_efflux_species(species)
    angle = _angle("surface_angle_deg", surface_angle_deg, 0.0, 180.0)
    half_angle = _angle("plume_half_angle_deg", plume_half_angle_deg, 0.0, 90.0)
    if half_angle <= 0.0:
        raise ValueError(
            "plume_half_angle_deg must be > 0, got %r" % (plume_half_angle_deg,)
        )
    if not isinstance(line_of_sight, bool):
        raise ValueError("line_of_sight must be a boolean, got %r" % (line_of_sight,))
    if not line_of_sight:
        path = NO_TRANSPORT_PATH
    elif _at_or_below(angle, half_angle):
        path = DIRECT_PATH
    elif family == CHARGED_FAMILY:
        path = CHARGE_EXCHANGE_PATH
    else:
        path = NEUTRAL_SCATTER_PATH
    return {
        "species_family": family,
        "surface_angle_deg": angle,
        "plume_half_angle_deg": half_angle,
        "path": path,
        "inside_cone": path == DIRECT_PATH,
    }


def surface_particle_flux(source_rate_kg_s, distance_m, incidence_deg, path,
                          plume_half_angle_deg, backflow_fraction=0.0):
    """Areal mass flux (kg/m^2/s) arriving on a surface by one path.

    Direct impingement spreads the source rate over the plume cone solid
    angle; backflow spreads the backflowing part over the full sphere.
    Both fall off with inverse-square distance and the incidence cosine.
    """
    if path not in TRANSPORT_PATHS:
        raise ValueError(
            "unrecognized transport path %r; expected one of %s"
            % (path, ", ".join(sorted(TRANSPORT_PATHS)))
        )
    rate = _positive("source_rate_kg_s", source_rate_kg_s)
    distance = _positive("distance_m", distance_m)
    incidence = _angle("incidence_deg", incidence_deg, 0.0, 90.0)
    if path == NO_TRANSPORT_PATH:
        return 0.0
    cos_incidence = math.cos(math.radians(incidence))
    if path == DIRECT_PATH:
        half_angle = _angle("plume_half_angle_deg", plume_half_angle_deg, 0.0, 90.0)
        if half_angle <= 0.0:
            raise ValueError(
                "plume_half_angle_deg must be > 0, got %r" % (plume_half_angle_deg,)
            )
        solid_angle_sr = 2.0 * math.pi * (1.0 - math.cos(math.radians(half_angle)))
        return rate * cos_incidence / (solid_angle_sr * distance * distance)
    fraction = _fraction("backflow_fraction", backflow_fraction)
    return rate * fraction * cos_incidence / (4.0 * math.pi * distance * distance)


def accumulate_deposition(flux_kg_m2_s, firing_duration_s,
                          sticking_coefficient=DEFAULT_STICKING_COEFFICIENT):
    """Areal deposited mass (kg/m^2) from a flux held over a firing."""
    flux = _non_negative("flux_kg_m2_s", flux_kg_m2_s)
    duration = _positive("firing_duration_s", firing_duration_s)
    sticking = _fraction("sticking_coefficient", sticking_coefficient)
    return flux * duration * sticking


def deposition_thickness_nm(areal_mass_kg_m2, film_density_kg_m3):
    """Convert an areal deposited mass into a film thickness in nanometres."""
    areal_mass = _non_negative("areal_mass_kg_m2", areal_mass_kg_m2)
    density = _positive("film_density_kg_m3", film_density_kg_m3)
    return areal_mass / density * 1.0e9


def check_deposition_allowance(thickness_nm, allowable_thickness_nm):
    """Compare a deposited film thickness against the agreed allowance."""
    thickness = _non_negative("thickness_nm", thickness_nm)
    allowance = _positive("allowable_thickness_nm", allowable_thickness_nm)
    return {
        "thickness_nm": thickness,
        "allowable_thickness_nm": allowance,
        "margin_nm": allowance - thickness,
        "utilisation": thickness / allowance,
        "compliant": _at_or_below(thickness, allowance),
    }


def _source_thickness(source):
    """Thickness (nm) one efflux source deposits, plus its bookkeeping."""
    if not isinstance(source, dict):
        raise ValueError("efflux source must be a mapping, got %r" % (type(source),))
    required = (
        "species",
        "source_rate_kg_s",
        "distance_m",
        "incidence_deg",
        "plume_half_angle_deg",
        "surface_angle_deg",
        "firing_duration_s",
        "film_density_kg_m3",
    )
    missing = [key for key in required if key not in source]
    if missing:
        raise ValueError(
            "efflux source is missing required key(s): %s" % ", ".join(missing)
        )
    transport = plume_transport_path(
        source["species"],
        source["surface_angle_deg"],
        source["plume_half_angle_deg"],
        source.get("line_of_sight", True),
    )
    findings = []
    observations = []
    backflow_fraction = source.get("backflow_fraction")
    if transport["path"] in BACKFLOW_PATHS and backflow_fraction is None:
        findings.append("backflow-fraction-not-recorded")
        backflow_fraction = 0.0
    elif backflow_fraction is None:
        backflow_fraction = 0.0
    sticking = source.get("sticking_coefficient")
    if sticking is None:
        observations.append("sticking-coefficient-defaulted-to-unity")
        sticking = DEFAULT_STICKING_COEFFICIENT
    flux = surface_particle_flux(
        source["source_rate_kg_s"],
        source["distance_m"],
        source["incidence_deg"],
        transport["path"],
        source["plume_half_angle_deg"],
        backflow_fraction,
    )
    areal_mass = accumulate_deposition(flux, source["firing_duration_s"], sticking)
    thickness = deposition_thickness_nm(areal_mass, source["film_density_kg_m3"])
    return {
        "species": source["species"],
        "species_family": transport["species_family"],
        "path": transport["path"],
        "flux_kg_m2_s": flux,
        "areal_mass_kg_m2": areal_mass,
        "thickness_nm": thickness,
        "findings": findings,
        "observations": observations,
    }


def assess_surface_deposition(surface):
    """Assess one surface against the clause 11.2.3 deposition allowance."""
    if not isinstance(surface, dict):
        raise ValueError("surface must be a mapping, got %r" % (type(surface),))
    for key in ("id", "sources"):
        if key not in surface:
            raise ValueError("surface record is missing required key %r" % (key,))
    identifier = surface["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("surface id must be a non-empty string, got %r" % (identifier,))
    sources = surface["sources"]
    if isinstance(sources, (str, bytes, dict)) or not isinstance(
        sources, (list, tuple)
    ):
        raise ValueError("surface sources must be a list of mappings")
    if not sources:
        raise ValueError("surface %r declares no efflux source" % (identifier,))
    contributions = [_source_thickness(source) for source in sources]
    findings = []
    observations = []
    for item in contributions:
        findings.extend(item["findings"])
        observations.extend(item["observations"])
    neutral_nm = sum(
        item["thickness_nm"]
        for item in contributions
        if item["species_family"] == NEUTRAL_FAMILY
    )
    charged_nm = sum(
        item["thickness_nm"]
        for item in contributions
        if item["species_family"] == CHARGED_FAMILY
    )
    total_nm = neutral_nm + charged_nm
    families = {item["species_family"] for item in contributions}
    if CHARGED_FAMILY not in families:
        findings.append("charged-efflux-source-not-declared")
    if NEUTRAL_FAMILY not in families:
        findings.append("neutral-efflux-source-not-declared")
    allowance = surface.get("allowable_thickness_nm")
    allowance_check = None
    if allowance is None:
        findings.append("agreed-deposition-limit-not-recorded")
    else:
        allowance_check = check_deposition_allowance(total_nm, allowance)
        if not allowance_check["compliant"]:
            findings.append("plume-deposition-exceeds-agreed-limit")
    blocking = [item for item in findings if item not in ADVISORY_FINDINGS]
    return {
        "id": identifier,
        "contributions": contributions,
        "neutral_thickness_nm": neutral_nm,
        "charged_thickness_nm": charged_nm,
        "total_thickness_nm": total_nm,
        "allowance_check": allowance_check,
        "findings": blocking,
        "observations": observations,
        "compliant": not blocking,
    }


def assess_deposition_campaign(surfaces):
    """Aggregate the clause 11.2.3 verdict across sensitive surfaces."""
    if isinstance(surfaces, (str, bytes, dict)) or not isinstance(
        surfaces, (list, tuple)
    ):
        raise ValueError("surfaces must be a list of mappings")
    if not surfaces:
        raise ValueError("surfaces must not be empty")
    results = []
    seen = set()
    for surface in surfaces:
        result = assess_surface_deposition(surface)
        if result["id"] in seen:
            raise ValueError("duplicate surface id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    noncompliant = [item["id"] for item in results if not item["compliant"]]
    worst = max(results, key=lambda item: item["total_thickness_nm"])
    return {
        "surface_count": len(results),
        "compliant_count": len(results) - len(noncompliant),
        "noncompliant_ids": noncompliant,
        "worst_surface_id": worst["id"],
        "worst_thickness_nm": worst["total_thickness_nm"],
        "results": results,
        "findings_by_surface": {
            item["id"]: list(item["findings"]) for item in results
        },
        "compliant": not noncompliant,
    }
