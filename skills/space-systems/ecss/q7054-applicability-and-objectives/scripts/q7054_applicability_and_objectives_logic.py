#!/usr/bin/env python3
"""Applicability and objectives of ultracleaning for flight hardware.

Anchor: ECSS-Q-ST-70-54C framework clause. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Ultracleaning is not "cleaning harder". It is the separate discipline that
applies once a hardware item has to reach a cleanliness state beyond what
the standard cleaning route delivers, and the first decision is whether an
item is in that population at all.

Two independent ladders describe the state:

    particulate    a surface cleanliness level, quoted as the size in
                   micrometre of the largest permitted particle. The
                   permitted count at every smaller size follows from the
                   level through the log-square distribution used across
                   precision-cleaning practice, so a level is a whole
                   distribution and not a single number.

    molecular      a non-volatile residue allowance in milligram per
                   0.1 square metre, quoted as a lettered class.

An item owes ultracleaning when either ladder puts it beyond the standard
baseline. Which ladder drives it decides the objective, and the objective
decides what the verification has to measure: a particulate-driven item is
verified by particle count or obscuration, a molecular-driven item by a
solvent rinse and residue weighing. Getting that backwards produces a clean
report about the wrong quantity.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Surface cleanliness ladder, largest permitted particle size in micrometre.
PARTICULATE_LADDER = (25.0, 50.0, 100.0, 200.0, 300.0, 500.0, 750.0, 1000.0)

# The routine cleaning route is taken to deliver this level; anything tighter
# is the ultracleaning population.
STANDARD_PARTICULATE_LEVEL = 500.0

# Slope of the log-square particle size distribution the ladder is built on.
_DISTRIBUTION_SLOPE = 0.926

# Non-volatile residue ladder, milligram per 0.1 square metre.
NVR_LADDER = (
    ("A/100", 0.01),
    ("A/50", 0.02),
    ("A/20", 0.05),
    ("A/10", 0.10),
    ("A/5", 0.20),
    ("A/2", 0.50),
    ("A", 1.00),
    ("B", 2.00),
    ("C", 3.00),
    ("D", 4.00),
    ("E", 5.00),
)
STANDARD_NVR_MG_PER_01M2 = 2.00  # ladder entry "B"

FUNCTION_CATEGORIES = (
    "cryogenic-optics",
    "ambient-optics",
    "oxygen-propulsion",
    "precision-mechanism",
    "thermal-control-surface",
    "structure",
)

EXPOSURE_ENVIRONMENTS = ("on-orbit-exposed", "vented-enclosure", "sealed-enclosure")

# Default allowances the function implies when the project has not stated one.
FUNCTION_ALLOWANCES = {
    "cryogenic-optics": {
        "reference_particle_um": 5.0,
        "max_particles_per_01m2": 60.0,
        "max_nvr_mg_per_01m2": 0.02,
    },
    "ambient-optics": {
        "reference_particle_um": 5.0,
        "max_particles_per_01m2": 900.0,
        "max_nvr_mg_per_01m2": 0.10,
    },
    "oxygen-propulsion": {
        "reference_particle_um": 25.0,
        "max_particles_per_01m2": 60.0,
        "max_nvr_mg_per_01m2": 0.20,
    },
    "precision-mechanism": {
        "reference_particle_um": 25.0,
        "max_particles_per_01m2": 900.0,
        "max_nvr_mg_per_01m2": 1.00,
    },
    "thermal-control-surface": {
        "reference_particle_um": 25.0,
        "max_particles_per_01m2": 9000.0,
        "max_nvr_mg_per_01m2": 2.00,
    },
    "structure": {
        "reference_particle_um": 100.0,
        "max_particles_per_01m2": 9000.0,
        "max_nvr_mg_per_01m2": 5.00,
    },
}

# An enclosure that cannot deliver released contaminant to the sensitive
# surface relaxes the allowance the item itself has to meet.
ENVIRONMENT_RELAXATION = {
    "on-orbit-exposed": 1.0,
    "vented-enclosure": 2.0,
    "sealed-enclosure": 5.0,
}

PARTICULATE_DRIVEN = "particulate-driven"
MOLECULAR_DRIVEN = "molecular-driven"
BOTH_DRIVEN = "particulate-and-molecular-driven"
STANDARD_SUFFICIENT = "standard-cleaning-sufficient"

VERIFICATION_BY_OBJECTIVE = {
    PARTICULATE_DRIVEN: ("particle-count-or-obscuration",),
    MOLECULAR_DRIVEN: ("solvent-rinse-residue-weighing",),
    BOTH_DRIVEN: ("particle-count-or-obscuration", "solvent-rinse-residue-weighing"),
    STANDARD_SUFFICIENT: (),
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _strictly_below(value, limit):
    """value < limit, with an exact landing on the limit read as equal."""
    if math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return False
    return value < limit


def particles_per_01m2(level_um, size_um):
    """Permitted count above size_um on a surface held at level_um.

    The ladder is a distribution, not a single permitted particle: the count
    above any size follows from the level through the log-square law used
    across precision-cleaning practice.
    """
    level = _require_positive("level_um", level_um)
    size = _require_positive("size_um", size_um)
    if size > level:
        raise ValueError(
            "size %g um is above the level %g um; the ladder permits no "
            "particle larger than the level" % (size, level)
        )
    exponent = _DISTRIBUTION_SLOPE * (
        math.log10(level) ** 2 - math.log10(size) ** 2
    )
    return 10.0**exponent


def required_particulate_level(size_um, max_particles_per_01m2):
    """Cleanliness level that permits no more than the stated count."""
    size = _require_positive("size_um", size_um)
    count = _require_positive("max_particles_per_01m2", max_particles_per_01m2)
    if count < 1.0:
        raise ValueError(
            "an allowance below one particle per 0.1 m2 is outside the ladder; "
            "state the allowance at a larger reference size"
        )
    squared = math.log10(count) / _DISTRIBUTION_SLOPE + math.log10(size) ** 2
    if squared < 0.0:
        raise ValueError(
            "allowance of %g particles above %g um cannot be expressed on the "
            "ladder" % (count, size)
        )
    return 10.0 ** math.sqrt(squared)


def nearest_ladder_level(level_um):
    """Tabulated ladder rung at or below a computed level."""
    level = _require_positive("level_um", level_um)
    rungs = [r for r in PARTICULATE_LADDER if r <= level or math.isclose(
        r, level, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )]
    if not rungs:
        raise ValueError(
            "level %g um is below the tightest tabulated rung %g um"
            % (level, PARTICULATE_LADDER[0])
        )
    return max(rungs)


def required_nvr_class(mg_per_01m2):
    """Tightest lettered residue class that meets an allowance."""
    allowance = _require_positive("mg_per_01m2", mg_per_01m2)
    candidates = [
        (name, value)
        for name, value in NVR_LADDER
        if value <= allowance
        or math.isclose(value, allowance, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)
    ]
    if not candidates:
        raise ValueError(
            "allowance %g mg per 0.1 m2 is below the tightest tabulated class %s"
            % (allowance, NVR_LADDER[0][0])
        )
    return max(candidates, key=lambda pair: pair[1])[0]


def resolve_allowances(case):
    """Allowances the item must meet, from the case or from its function."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    function = _require_choice(
        "function_category", case.get("function_category"), FUNCTION_CATEGORIES
    )
    environment = _require_choice(
        "exposure_environment", case.get("exposure_environment"), EXPOSURE_ENVIRONMENTS
    )
    defaults = FUNCTION_ALLOWANCES[function]
    size = case.get("reference_particle_um", defaults["reference_particle_um"])
    count = case.get("max_particles_per_01m2", defaults["max_particles_per_01m2"])
    nvr = case.get("max_nvr_mg_per_01m2", defaults["max_nvr_mg_per_01m2"])
    size = _require_positive("reference_particle_um", size)
    count = _require_positive("max_particles_per_01m2", count)
    nvr = _require_positive("max_nvr_mg_per_01m2", nvr)
    relaxation = ENVIRONMENT_RELAXATION[environment]
    stated = any(
        key in case
        for key in (
            "reference_particle_um",
            "max_particles_per_01m2",
            "max_nvr_mg_per_01m2",
        )
    )
    return {
        "function_category": function,
        "exposure_environment": environment,
        "reference_particle_um": size,
        "max_particles_per_01m2": count * relaxation,
        "max_nvr_mg_per_01m2": nvr * relaxation,
        "relaxation_applied": relaxation,
        "allowance_source": "case-stated" if stated else "function-default",
    }


def ultracleaning_objective(particulate_level_um, nvr_mg_per_01m2):
    """Which ladder drives the item beyond the standard baseline."""
    level = _require_positive("particulate_level_um", particulate_level_um)
    nvr = _require_positive("nvr_mg_per_01m2", nvr_mg_per_01m2)
    particulate = _strictly_below(level, STANDARD_PARTICULATE_LEVEL)
    molecular = _strictly_below(nvr, STANDARD_NVR_MG_PER_01M2)
    if particulate and molecular:
        return BOTH_DRIVEN
    if particulate:
        return PARTICULATE_DRIVEN
    if molecular:
        return MOLECULAR_DRIVEN
    return STANDARD_SUFFICIENT


def assess_ultracleaning_applicability(case):
    """Full framework decision: owed or not, why, and what to verify."""
    allowances = resolve_allowances(case)
    level = required_particulate_level(
        allowances["reference_particle_um"], allowances["max_particles_per_01m2"]
    )
    nvr_class = required_nvr_class(allowances["max_nvr_mg_per_01m2"])
    objective = ultracleaning_objective(level, allowances["max_nvr_mg_per_01m2"])
    required = objective != STANDARD_SUFFICIENT
    findings = []
    if allowances["allowance_source"] == "function-default":
        findings.append(
            "no allowance stated; the %s function default was used and owes "
            "confirmation against the contamination budget"
            % allowances["function_category"]
        )
    if allowances["relaxation_applied"] > 1.0:
        findings.append(
            "allowance relaxed by %.1fx for a %s; the relaxation fails if the "
            "enclosure is opened with the sensitive surface in view"
            % (allowances["relaxation_applied"], allowances["exposure_environment"])
        )
    if required and objective == MOLECULAR_DRIVEN:
        findings.append(
            "particulate allowance is met by the standard route; verification "
            "by particle count alone would grade the wrong quantity"
        )
    return {
        "ultracleaning_required": required,
        "objective": objective,
        "required_particulate_level_um": level,
        "ladder_particulate_level_um": nearest_ladder_level(level),
        "required_nvr_class": nvr_class,
        "required_nvr_mg_per_01m2": allowances["max_nvr_mg_per_01m2"],
        "verification_methods": list(VERIFICATION_BY_OBJECTIVE[objective]),
        "allowances": allowances,
        "findings": findings,
    }
