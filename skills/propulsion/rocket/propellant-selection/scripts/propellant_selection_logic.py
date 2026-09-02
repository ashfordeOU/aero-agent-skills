#!/usr/bin/env python3
"""Propellant selection logic: propellant families, density impulse,
mixture bulk density, O/F ratio verdict, rocket-equation propellant
mass fraction, and a mission suitability verdict (common propulsion
methodology).

Common-knowledge summary (standards-map.yaml, ecss: free ESA download,
reference-only): ECSS space-systems standards frame launch-vehicle
propulsion context. Propellant performance and selection trade-offs
(density impulse, mixture ratio, storability) are standard propulsion
methodology. Units: specific impulse in seconds, densities in kg/m^3,
delta-v in m/s, g0 = 9.80665 m/s^2.
"""

import math

G0 = 9.80665

FAMILIES = ("cryogenic", "storable", "hypergolic", "solid")

MISSIONS = (
    "booster",
    "upper-stage",
    "orbit",
    "deep-space",
    "long-duration",
    "quick-response",
)

_FAMILY_BY_NAME = {
    # cryogenic: liquefied gases that boil off unless kept near their
    # boiling point
    "lox": "cryogenic",
    "liquid oxygen": "cryogenic",
    "lh2": "cryogenic",
    "liquid hydrogen": "cryogenic",
    "lch4": "cryogenic",
    "liquid methane": "cryogenic",
    "methane": "cryogenic",
    # storable: dense liquids that hold at ambient temperature without
    # spontaneous ignition
    "rp-1": "storable",
    "rp1": "storable",
    "kerosene": "storable",
    "h2o2": "storable",
    "hydrogen peroxide": "storable",
    "ethanol": "storable",
    # hypergolic: storable liquids that ignite on contact with each
    # other, no ignition system needed
    "mmh": "hypergolic",
    "monomethylhydrazine": "hypergolic",
    "udmh": "hypergolic",
    "hydrazine": "hypergolic",
    "nto": "hypergolic",
    "nitrogen tetroxide": "hypergolic",
    "n2o4": "hypergolic",
    "irfna": "hypergolic",
    "aerozine 50": "hypergolic",
    # solid: cured grain cast in the motor case, burns on demand,
    # cannot throttle or restart
    "htpb": "solid",
    "apcp": "solid",
    "ammonium perchlorate": "solid",
    "double-base": "solid",
    "solid": "solid",
}

# Verdict heuristics: suitable, caveat, or unsuitable for each family
# on each mission class. Deterministic screening guidance, not a
# substitute for a full trade study.
_VERDICT_BY_CLASS_MISSION = {
    "cryogenic": {
        "booster": "suitable",
        "upper-stage": "suitable",
        "orbit": "suitable",
        "deep-space": "caveat",
        "long-duration": "caveat",
        "quick-response": "unsuitable",
    },
    "storable": {
        "booster": "suitable",
        "upper-stage": "caveat",
        "orbit": "caveat",
        "deep-space": "caveat",
        "long-duration": "suitable",
        "quick-response": "suitable",
    },
    "hypergolic": {
        "booster": "caveat",
        "upper-stage": "suitable",
        "orbit": "suitable",
        "deep-space": "suitable",
        "long-duration": "suitable",
        "quick-response": "suitable",
    },
    "solid": {
        "booster": "suitable",
        "upper-stage": "caveat",
        "orbit": "caveat",
        "deep-space": "unsuitable",
        "long-duration": "unsuitable",
        "quick-response": "suitable",
    },
}


def density_impulse(isp_s, bulk_density_kg_m3):
    """Density impulse, Isp * bulk density, in kg s/m^3.

    Ranks propellants per unit tank volume, which is what drives tank
    and vehicle size, not Isp alone. Raises ValueError when Isp or the
    bulk density is not positive.
    """
    if isp_s <= 0:
        raise ValueError("specific impulse must be > 0, got %r" % (isp_s,))
    if bulk_density_kg_m3 <= 0:
        raise ValueError(
            "bulk density must be > 0, got %r" % (bulk_density_kg_m3,)
        )
    return isp_s * bulk_density_kg_m3


def bulk_density(mixture_ratio, rho_fuel_kg_m3, rho_oxidizer_kg_m3):
    """Bulk density of the propellant mixture at an O/F mass ratio.

    For mass ratio r = m_oxidizer / m_fuel the bulk density is the
    mass-weighted harmonic mean:
      rho = (1 + r) / (1/rho_fuel + r/rho_oxidizer)
    A ratio of 0 gives the pure fuel density. Raises ValueError for a
    negative ratio or non-positive densities.
    """
    if mixture_ratio < 0:
        raise ValueError(
            "mixture ratio must be >= 0, got %r" % (mixture_ratio,)
        )
    if rho_fuel_kg_m3 <= 0:
        raise ValueError(
            "fuel density must be > 0, got %r" % (rho_fuel_kg_m3,)
        )
    if rho_oxidizer_kg_m3 <= 0:
        raise ValueError(
            "oxidizer density must be > 0, got %r" % (rho_oxidizer_kg_m3,)
        )
    return (
        (1.0 + mixture_ratio)
        * rho_fuel_kg_m3
        * rho_oxidizer_kg_m3
        / (rho_oxidizer_kg_m3 + mixture_ratio * rho_fuel_kg_m3)
    )


def required_mass_fraction(delta_v, isp_s, g0=G0):
    """Propellant mass fraction m_propellant / m_initial for a delta-v.

    Inverted rocket equation: 1 - exp(-delta_v / (g0 * Isp)). This is
    the fraction of the initial mass that must be propellant. Raises
    ValueError for a negative delta-v or a non-positive Isp.
    """
    if delta_v < 0:
        raise ValueError("delta-v must be >= 0, got %r" % (delta_v,))
    if isp_s <= 0:
        raise ValueError("specific impulse must be > 0, got %r" % (isp_s,))
    return 1.0 - math.exp(-delta_v / (g0 * isp_s))


def propellant_family(name):
    """Classify a propellant name as cryogenic, storable, hypergolic,
    or solid.

    Raises ValueError for an unknown name.
    """
    key = (name or "").strip().lower()
    if key not in _FAMILY_BY_NAME:
        raise ValueError(
            "unknown propellant %r, expected one of %s"
            % (name, ", ".join(sorted(_FAMILY_BY_NAME)))
        )
    return _FAMILY_BY_NAME[key]


def propellant_verdict(propellant_class, mission):
    """Suitability verdict for a propellant family on a mission class.

    Returns 'suitable', 'caveat', or 'unsuitable' from the screening
    table: cryogens suffer boil-off on long missions, solids cannot
    restart, hypergolics and storables hold indefinitely. Raises
    ValueError for an unknown family or mission.
    """
    if propellant_class not in _VERDICT_BY_CLASS_MISSION:
        raise ValueError(
            "unknown propellant class %r, expected one of %s"
            % (propellant_class, ", ".join(FAMILIES))
        )
    if mission not in MISSIONS:
        raise ValueError(
            "unknown mission %r, expected one of %s"
            % (mission, ", ".join(MISSIONS))
        )
    return _VERDICT_BY_CLASS_MISSION[propellant_class][mission]


def o_f_optimum_verdict(o_f_ratio, optimum_o_f, tolerance=0.05):
    """Verdict on an O/F ratio against the optimum.

    Within the relative tolerance of the optimum the verdict is
    'near-optimum'; below it 'fuel-rich' (too much fuel per oxidizer);
    above it 'oxidizer-rich'. Raises ValueError for a negative ratio,
    a non-positive optimum, or a non-positive tolerance.
    """
    if o_f_ratio < 0:
        raise ValueError("O/F ratio must be >= 0, got %r" % (o_f_ratio,))
    if optimum_o_f <= 0:
        raise ValueError(
            "optimum O/F must be > 0, got %r" % (optimum_o_f,)
        )
    if tolerance <= 0:
        raise ValueError("tolerance must be > 0, got %r" % (tolerance,))
    relative = abs(o_f_ratio - optimum_o_f) / optimum_o_f
    if relative <= tolerance:
        return "near-optimum"
    if o_f_ratio < optimum_o_f:
        return "fuel-rich"
    return "oxidizer-rich"
