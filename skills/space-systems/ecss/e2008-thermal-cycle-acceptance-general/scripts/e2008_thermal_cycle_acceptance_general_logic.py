#!/usr/bin/env python3
"""Vacuum preferred over ambient atmosphere for acceptance cycling.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.7.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Acceptance thermal cycling of a photovoltaic assembly is preferably run
under vacuum. In orbit the assembly exchanges heat by radiation alone
and sits in a dry, non-oxidising environment; a chamber full of gas
gives it none of those conditions. The preference is therefore not a
convenience: cycling in atmosphere changes the stress that reaches the
article and adds failure modes the flight article will never meet.

Three things change when gas is present.

Heat leaves the assembly by conduction through the gas as well as by
radiation, so the assembly follows the chamber faster and more evenly
than it would in flight. Whether that matters is a Knudsen question --
the molecular mean free path against the gap the heat crosses -- and it
matters most in the continuum regime, where the gas behaves as a fluid.

Water in the gas condenses or frosts on cold surfaces at the cold
dwell. A coverglass or an adhesive bond line that ices at 173 K is
being tested against a mechanism that does not exist on orbit, and the
damage it causes is indistinguishable afterwards from a workmanship
escape.

Oxygen attacks exposed metallisation at the hot dwell. Silver
interconnects tarnish in air at elevated temperature, so an acceptance
run in air can degrade the very joints it was meant to screen.

Departing from vacuum is therefore allowed only against a recorded
justification, with each of those deviations sized rather than
asserted to be small.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ENVIRONMENT_VACUUM = "vacuum"
ENVIRONMENT_RAREFIED = "rarefied-gas"
ENVIRONMENT_ATMOSPHERIC = "ambient-atmosphere"

CHAMBER_ENVIRONMENTS = (
    ENVIRONMENT_VACUUM,
    ENVIRONMENT_RAREFIED,
    ENVIRONMENT_ATMOSPHERIC,
)

CONDUCTION_REGIMES = (
    "continuum",
    "transitional",
    "free-molecular",
)

VACUUM_CEILING_PA = 1.0e-3
RAREFIED_CEILING_PA = 1.0e2
STANDARD_ATMOSPHERE_PA = 101325.0

BOLTZMANN_J_PER_K = 1.380649e-23
DEFAULT_MOLECULE_DIAMETER_M = 3.7e-10

CONTINUUM_KNUDSEN = 0.01
FREE_MOLECULAR_KNUDSEN = 10.0

MIN_FROST_POINT_MARGIN_K = 10.0
OXIDATION_ONSET_K = 333.15
MAX_OXYGEN_VOLUME_FRACTION = 1.0e-3

GAS_EVIDENCE_FIELDS = (
    "gas_frost_point_k",
    "oxygen_volume_fraction",
)

VACUUM_PREFERENCE_MET = "vacuum-cycling-preference-met"
AMBIENT_JUSTIFIED = "ambient-cycling-justified"
AMBIENT_NOT_JUSTIFIED = "ambient-cycling-not-justified"

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _require_fraction(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must be a fraction between zero and one, got %r" % (name, value))
    return float(value)


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A Knudsen number is a quotient of two derived floats and can land a
    few units in the last place either side of a regime boundary, so
    the comparison tolerates that error while the boundary itself is
    never moved.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_pressure_pa(value):
    """Normalise a chamber pressure, refusing an unphysical one."""
    return _require_positive("chamber_pressure_pa", value)


def chamber_environment(pressure_pa):
    """Name the environment a chamber pressure actually puts the article in."""
    pressure = validate_pressure_pa(pressure_pa)
    if _at_most(pressure, VACUUM_CEILING_PA):
        return ENVIRONMENT_VACUUM
    if _at_most(pressure, RAREFIED_CEILING_PA):
        return ENVIRONMENT_RAREFIED
    return ENVIRONMENT_ATMOSPHERIC


def is_preferred_environment(pressure_pa):
    """Whether the run sits in the environment the clause prefers."""
    return chamber_environment(pressure_pa) == ENVIRONMENT_VACUUM


def molecular_mean_free_path_m(
    pressure_pa, temperature_k, molecule_diameter_m=DEFAULT_MOLECULE_DIAMETER_M
):
    """Distance a gas molecule travels between collisions, in metres."""
    pressure = validate_pressure_pa(pressure_pa)
    temperature = _require_positive("temperature_k", temperature_k)
    diameter = _require_positive("molecule_diameter_m", molecule_diameter_m)
    return (BOLTZMANN_J_PER_K * temperature) / (
        math.sqrt(2.0) * math.pi * diameter * diameter * pressure
    )


def knudsen_number(mean_free_path_m, characteristic_gap_m):
    """Mean free path against the gap the heat has to cross."""
    path = _require_positive("mean_free_path_m", mean_free_path_m)
    gap = _require_positive("characteristic_gap_m", characteristic_gap_m)
    return path / gap


def gas_conduction_regime(knudsen):
    """Group a Knudsen number into the regime the gas conducts in."""
    value = _require_positive("knudsen", knudsen)
    if _at_most(value, CONTINUUM_KNUDSEN):
        return "continuum"
    if _at_least(value, FREE_MOLECULAR_KNUDSEN):
        return "free-molecular"
    return "transitional"


def gas_conduction_is_negligible(regime):
    """Whether the gas path can be left out of the thermal profile."""
    if regime not in CONDUCTION_REGIMES:
        raise ValueError(
            "unknown conduction regime %r; expected one of %s"
            % (regime, ", ".join(CONDUCTION_REGIMES))
        )
    return regime == "free-molecular"


def frost_point_margin_k(cold_dwell_k, gas_frost_point_k):
    """Kelvin between the cold dwell and the frost point of the gas.

    A negative margin means the assembly is colder than the point at
    which the chamber gas deposits on it, so the cold dwell is icing
    the article rather than cycling it.
    """
    cold = _require_positive("cold_dwell_k", cold_dwell_k)
    frost = _require_positive("gas_frost_point_k", gas_frost_point_k)
    return cold - frost


def frost_margin_adequate(cold_dwell_k, gas_frost_point_k):
    """Whether the cold dwell stays clear of the frost point."""
    return _at_least(
        frost_point_margin_k(cold_dwell_k, gas_frost_point_k),
        MIN_FROST_POINT_MARGIN_K,
    )


def oxidation_exposure(hot_dwell_k, oxygen_volume_fraction):
    """Whether the hot dwell will tarnish exposed metallisation."""
    hot = _require_positive("hot_dwell_k", hot_dwell_k)
    oxygen = _require_fraction("oxygen_volume_fraction", oxygen_volume_fraction)
    hot_enough = _at_least(hot, OXIDATION_ONSET_K)
    rich_enough = not _at_most(oxygen, MAX_OXYGEN_VOLUME_FRACTION)
    return {
        "hot_dwell_k": hot,
        "oxygen_volume_fraction": oxygen,
        "above_oxidation_onset": hot_enough,
        "oxygen_above_ceiling": rich_enough,
        "at_risk": hot_enough and rich_enough,
    }


def requires_justification(pressure_pa):
    """Whether departing from the preferred environment has to be argued."""
    return not is_preferred_environment(pressure_pa)


def missing_gas_evidence(case):
    """Gas-side inputs a non-vacuum run has not brought."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    return tuple(
        field for field in GAS_EVIDENCE_FIELDS if case.get(field) is None
    )


def assess_cycling_environment(case):
    """Full clause 5.5.3.7.2 judgement of the cycling environment."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    pressure = validate_pressure_pa(case.get("chamber_pressure_pa"))
    environment = chamber_environment(pressure)
    cold = _require_positive("cold_dwell_k", case.get("cold_dwell_k"))
    hot = _require_positive("hot_dwell_k", case.get("hot_dwell_k"))
    if not hot > cold:
        raise ValueError(
            "hot_dwell_k %g must be above cold_dwell_k %g" % (hot, cold)
        )
    gap = _require_positive("characteristic_gap_m", case.get("characteristic_gap_m"))
    diameter = _require_positive(
        "molecule_diameter_m",
        case.get("molecule_diameter_m", DEFAULT_MOLECULE_DIAMETER_M),
    )

    mean_free_path = molecular_mean_free_path_m(pressure, cold, diameter)
    knudsen = knudsen_number(mean_free_path, gap)
    regime = gas_conduction_regime(knudsen)
    negligible = gas_conduction_is_negligible(regime)

    result = {
        "chamber_pressure_pa": pressure,
        "environment": environment,
        "preferred_environment": is_preferred_environment(pressure),
        "mean_free_path_m": mean_free_path,
        "knudsen_number": knudsen,
        "conduction_regime": regime,
        "gas_conduction_negligible": negligible,
        "justification_required": requires_justification(pressure),
        "frost_point_margin_k": None,
        "frost_margin_adequate": None,
        "oxidation_exposure": None,
        "findings": [],
    }

    if not result["justification_required"]:
        if not negligible:
            result["findings"].append(
                "chamber is at vacuum but the %s regime still conducts across the %.3g m gap; check the pressure reading before trusting a radiation-limited profile"
                % (regime, gap)
            )
        result["verdict"] = (
            VACUUM_PREFERENCE_MET if not result["findings"] else AMBIENT_NOT_JUSTIFIED
        )
        result["acceptable"] = result["verdict"] == VACUUM_PREFERENCE_MET
        return result

    absent = missing_gas_evidence(case)
    if absent:
        raise ValueError(
            "a %s run must bring %s before it can be judged"
            % (environment, ", ".join(absent))
        )

    justified = _require_flag(
        "justification_recorded", case.get("justification_recorded", False)
    )
    compensated = _require_flag(
        "profile_compensated_for_gas_conduction",
        case.get("profile_compensated_for_gas_conduction", False),
    )

    margin = frost_point_margin_k(cold, case.get("gas_frost_point_k"))
    margin_ok = frost_margin_adequate(cold, case.get("gas_frost_point_k"))
    oxidation = oxidation_exposure(hot, case.get("oxygen_volume_fraction"))
    result["frost_point_margin_k"] = margin
    result["frost_margin_adequate"] = margin_ok
    result["oxidation_exposure"] = oxidation

    if not justified:
        result["findings"].append(
            "no recorded justification for cycling at %.3g Pa instead of the preferred vacuum"
            % pressure
        )
    if not negligible and not compensated:
        result["findings"].append(
            "gas conduction is in the %s regime and the profile was not compensated for it; the assembly follows the chamber faster than radiation alone would carry it"
            % regime
        )
    if not margin_ok:
        result["findings"].append(
            "cold dwell sits %.1f K from the frost point, inside the %.0f K margin; the cold dwell will deposit on the assembly"
            % (margin, MIN_FROST_POINT_MARGIN_K)
        )
    if oxidation["at_risk"]:
        result["findings"].append(
            "hot dwell at %.1f K in %.2f%% oxygen will tarnish exposed metallisation, degrading the joints the screen is meant to judge"
            % (oxidation["hot_dwell_k"], oxidation["oxygen_volume_fraction"] * 100.0)
        )

    acceptable = not result["findings"]
    result["verdict"] = AMBIENT_JUSTIFIED if acceptable else AMBIENT_NOT_JUSTIFIED
    result["acceptable"] = acceptable
    return result
