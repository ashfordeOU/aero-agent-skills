#!/usr/bin/env python3
"""Material selection indices logic (paraphrase, not copy).

Selection indices (Ashby, Materials Selection in Mechanical Design;
common engineering knowledge, summary-only):
  tension stiffness per weight:   E / rho
  beam bending stiffness/weight:  E**(1/2) / rho
  panel bending stiffness/weight: E**(1/3) / rho
  tension strength per weight:    sigma / rho
  beam bending strength/weight:   sigma**(2/3) / rho
  panel bending strength/weight:  sigma**(1/2) / rho

Unit convention (single, consistent): rho in g/cm3, E in GPa,
sigma in MPa. Indices are ranking metrics in mixed units, not
design allowables.

Material table: representative common-knowledge band values for
selection screening (aluminum 2xxx/7xxx, titanium 6Al-4V, 4340
steel, carbon-epoxy laminate). Verify every value against MMPDS,
AMS, or CMH-17 before design use; MMPDS is proprietary (SAE) and
its design-value tables are never reproduced here.
"""

MATERIALS = {
    "al-2024-t3": {
        "family": "aluminum",
        "rho": 2.78,   # g/cm3
        "e_mod": 71.7,  # GPa
        "fty": 345.0,   # MPa, yield
        "uts": 485.0,   # MPa
        "temp_max": 150.0,   # C
        "corrosion": 2,      # 0 (poor) to 5 (excellent)
        "cost": 1.0,         # per kg, relative to 2024-T3
        "availability": 5,   # 1 (scarce) to 5 (standard stock)
    },
    "al-7075-t6": {
        "family": "aluminum",
        "rho": 2.80,
        "e_mod": 71.7,
        "fty": 503.0,
        "uts": 572.0,
        "temp_max": 130.0,
        "corrosion": 2,
        "cost": 1.1,
        "availability": 5,
    },
    "ti-6al-4v": {
        "family": "titanium",
        "rho": 4.43,
        "e_mod": 113.8,
        "fty": 880.0,
        "uts": 950.0,
        "temp_max": 315.0,
        "corrosion": 5,
        "cost": 7.0,
        "availability": 4,
    },
    "steel-4340": {
        "family": "steel",
        "rho": 7.85,
        "e_mod": 200.0,
        "fty": 1240.0,
        "uts": 1480.0,
        "temp_max": 370.0,
        "corrosion": 3,
        "cost": 0.4,
        "availability": 5,
    },
    "cfrp-epoxy-laminate": {
        "family": "composite",
        "rho": 1.60,
        "e_mod": 140.0,
        "fty": 800.0,   # laminate tension allowable
        "uts": 800.0,
        "temp_max": 120.0,
        "corrosion": 4,
        "cost": 15.0,
        "availability": 3,
    },
}

MODES = {
    "stiffness-tie": lambda m: m["e_mod"] / m["rho"],
    "stiffness-beam": lambda m: m["e_mod"] ** 0.5 / m["rho"],
    "stiffness-panel": lambda m: m["e_mod"] ** (1.0 / 3.0) / m["rho"],
    "strength-tie": lambda m: m["fty"] / m["rho"],
    "strength-beam": lambda m: m["fty"] ** (2.0 / 3.0) / m["rho"],
    "strength-panel": lambda m: m["fty"] ** 0.5 / m["rho"],
}


def _material(material):
    if material not in MATERIALS:
        raise ValueError("unknown material: %r" % (material,))
    return MATERIALS[material]


def selection_index(material, mode):
    """Selection index for one material and mode (ranking metric)."""
    m = _material(material)
    if mode not in MODES:
        raise ValueError(
            "mode must be one of %s: %r" % (sorted(MODES), mode)
        )
    return MODES[mode](m)


def rank_materials(materials, mode):
    """Rank candidate materials by the index, best first.

    Returns a list of (material_id, index) pairs sorted by index
    descending. Deterministic: ties break on material id ascending.
    """
    if not materials:
        raise ValueError("materials list is empty")
    scored = [(selection_index(mat, mode), mat) for mat in materials]
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [(mat, index) for index, mat in scored]


def material_family(material):
    """Material family: aluminum, titanium, steel, or composite."""
    return _material(material)["family"]


def temperature_ok(material, temp_c):
    """True if the temperature is at or below the material limit."""
    return temp_c <= _material(material)["temp_max"]


def temperature_limit(material):
    """Maximum service temperature in C (representative band value)."""
    return _material(material)["temp_max"]


def corrosion_rating(material):
    """Corrosion resistance rating, 0 (poor) to 5 (excellent)."""
    return _material(material)["corrosion"]


def relative_cost(material):
    """Cost per kg relative to 2024-T3 (1.0)."""
    return _material(material)["cost"]
