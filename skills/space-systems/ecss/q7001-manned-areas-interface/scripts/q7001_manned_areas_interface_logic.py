"""Crewed-area molecular and particulate constraints at the cleanliness interface.

Anchor: ECSS-Q-ST-70-01C sensitive-hardware provisions where the hardware is
installed in a crewed compartment, and the offgassing determination of
ECSS-Q-ST-70-29C that the compartment atmosphere is judged against.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Turn each material or assembled article into an offgassing rate: a
   specific rate per unit mass multiplied by the installed mass, or a
   directly measured article rate.
2. Convert the rate into a steady-state cabin concentration through the air
   revitalisation flow and its removal efficiency, not through the cabin
   volume alone: at steady state the removal path, not the volume, sets the
   concentration the crew actually breathes.
3. Divide each concentration by that species' maximum allowable
   concentration to get its hazard index, and sum the indices into the total
   hazard index for the atmosphere. Species acting on the same organ add;
   one species at a tenth of its own limit is not automatically acceptable.
4. Compare the total with the allowable total, name the driving species, and
   check the airborne particulate loading against its own separate limit.
"""

import math

__all__ = [
    "DEFAULT_ALLOWABLE_TOTAL_INDEX",
    "INDEX_TOLERANCE",
    "assess_crewed_area_interface",
    "driving_species",
    "hazard_index",
    "particulate_margin_mg_m3",
    "species_rate_mg_per_day",
    "steady_state_concentration_mg_m3",
    "total_hazard_index",
    "validate_compartment",
    "validate_species",
]

# The crewed-compartment atmosphere is accepted on a total index well below
# unity so that the article leaves room for everything else in the volume.
DEFAULT_ALLOWABLE_TOTAL_INDEX = 0.5

# The index is a sum of quotients; an exactly on-limit case can land a few
# ULP either side of the allowable total.
INDEX_TOLERANCE = 1e-12


def _positive(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _non_negative(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _fraction(value, label):
    number = _non_negative(value, label)
    if number > 1.0:
        raise ValueError("%s must not exceed 1, got %r" % (label, value))
    return number


def species_rate_mg_per_day(species):
    """Return the offgassing rate of one species in milligrams per day.

    Either a measured article rate, or a specific rate per kilogram of
    installed material multiplied by that mass. Declaring both is an input
    error, because the two cannot be reconciled after the fact.
    """
    if not isinstance(species, dict):
        raise ValueError("each species must be a mapping")
    measured = species.get("rate_mg_per_day")
    specific = species.get("specific_rate_mg_per_kg_day")
    mass = species.get("installed_mass_kg")
    if measured is not None and specific is not None:
        raise ValueError(
            "declare either rate_mg_per_day or specific_rate_mg_per_kg_day with "
            "installed_mass_kg, not both"
        )
    if measured is not None:
        return _non_negative(measured, "rate_mg_per_day")
    if specific is None or mass is None:
        raise ValueError(
            "species needs rate_mg_per_day, or specific_rate_mg_per_kg_day plus "
            "installed_mass_kg"
        )
    return _non_negative(
        specific, "specific_rate_mg_per_kg_day"
    ) * _positive(mass, "installed_mass_kg")


def validate_species(species):
    """Return a normalised offgassing-species record."""
    if not isinstance(species, dict):
        raise ValueError("each species must be a mapping")
    name = species.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("species name must be a non-empty string")
    if "max_allowable_concentration_mg_m3" not in species:
        raise ValueError(
            "species '%s' missing max_allowable_concentration_mg_m3" % name
        )
    return {
        "name": name,
        "rate_mg_per_day": species_rate_mg_per_day(species),
        "max_allowable_concentration_mg_m3": _positive(
            species["max_allowable_concentration_mg_m3"],
            "max_allowable_concentration_mg_m3",
        ),
    }


def steady_state_concentration_mg_m3(
    rate_mg_per_day, scrubbing_flow_m3_per_day, removal_efficiency
):
    """Return the steady-state cabin concentration of one species."""
    rate = _non_negative(rate_mg_per_day, "rate_mg_per_day")
    flow = _positive(scrubbing_flow_m3_per_day, "scrubbing_flow_m3_per_day")
    efficiency = _fraction(removal_efficiency, "removal_efficiency")
    if efficiency <= 0.0:
        raise ValueError(
            "removal_efficiency must be greater than zero; with no removal path "
            "the concentration does not reach a steady state"
        )
    return rate / (flow * efficiency)


def hazard_index(concentration_mg_m3, max_allowable_concentration_mg_m3):
    """Return one species' share of the allowable atmosphere."""
    concentration = _non_negative(concentration_mg_m3, "concentration_mg_m3")
    limit = _positive(
        max_allowable_concentration_mg_m3, "max_allowable_concentration_mg_m3"
    )
    return concentration / limit


def total_hazard_index(indices):
    """Sum the per-species hazard indices into the atmosphere total."""
    if not isinstance(indices, (list, tuple)) or not indices:
        raise ValueError("indices must be a non-empty sequence")
    values = [_non_negative(item, "hazard index") for item in indices]
    return math.fsum(values)


def driving_species(records):
    """Return the record carrying the largest hazard index."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    leader = None
    for record in records:
        if not isinstance(record, dict) or "hazard_index" not in record:
            raise ValueError("each record must be a mapping carrying 'hazard_index'")
        if leader is None or record["hazard_index"] > leader["hazard_index"]:
            leader = record
    return leader


def particulate_margin_mg_m3(measured_mg_m3, limit_mg_m3):
    """Return the airborne particulate headroom left in the compartment."""
    measured = _non_negative(measured_mg_m3, "measured_mg_m3")
    limit = _positive(limit_mg_m3, "limit_mg_m3")
    return limit - measured


def validate_compartment(compartment):
    """Return a normalised crewed-compartment record."""
    if not isinstance(compartment, dict):
        raise ValueError("compartment must be a mapping")
    for key in ("volume_m3", "scrubbing_flow_m3_per_day"):
        if key not in compartment:
            raise ValueError("compartment missing required key '%s'" % key)
    record = {
        "volume_m3": _positive(compartment["volume_m3"], "volume_m3"),
        "scrubbing_flow_m3_per_day": _positive(
            compartment["scrubbing_flow_m3_per_day"], "scrubbing_flow_m3_per_day"
        ),
        "removal_efficiency": _fraction(
            compartment.get("removal_efficiency", 1.0), "removal_efficiency"
        ),
        "allowable_total_index": _positive(
            compartment.get("allowable_total_index", DEFAULT_ALLOWABLE_TOTAL_INDEX),
            "allowable_total_index",
        ),
        "particulate_mg_m3": _non_negative(
            compartment.get("particulate_mg_m3", 0.0), "particulate_mg_m3"
        ),
        "particulate_limit_mg_m3": _positive(
            compartment.get("particulate_limit_mg_m3", 0.2),
            "particulate_limit_mg_m3",
        ),
    }
    if record["removal_efficiency"] <= 0.0:
        raise ValueError("removal_efficiency must be greater than zero")
    if record["scrubbing_flow_m3_per_day"] > record["volume_m3"] * 1.0e4:
        raise ValueError(
            "scrubbing_flow_m3_per_day is implausible against the declared volume; "
            "check the units before trusting the concentration"
        )
    return record


def assess_crewed_area_interface(spec):
    """Run the full crewed-area molecular and particulate assessment.

    spec keys: compartment (mapping), species (non-empty sequence of mappings).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("compartment", "species"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    compartment = validate_compartment(spec["compartment"])
    entries = spec["species"]
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("species must be a non-empty sequence")
    records = []
    for entry in entries:
        species = validate_species(entry)
        concentration = steady_state_concentration_mg_m3(
            species["rate_mg_per_day"],
            compartment["scrubbing_flow_m3_per_day"],
            compartment["removal_efficiency"],
        )
        records.append(
            {
                "name": species["name"],
                "rate_mg_per_day": species["rate_mg_per_day"],
                "concentration_mg_m3": concentration,
                "max_allowable_concentration_mg_m3": species[
                    "max_allowable_concentration_mg_m3"
                ],
                "hazard_index": hazard_index(
                    concentration, species["max_allowable_concentration_mg_m3"]
                ),
            }
        )
    names = [record["name"] for record in records]
    if len(set(names)) != len(names):
        raise ValueError("species names must be unique for a traceable total")
    total = total_hazard_index([record["hazard_index"] for record in records])
    leader = driving_species(records)
    particulate_headroom = particulate_margin_mg_m3(
        compartment["particulate_mg_m3"], compartment["particulate_limit_mg_m3"]
    )
    findings = []
    molecular_ok = total < compartment["allowable_total_index"] or math.isclose(
        total,
        compartment["allowable_total_index"],
        rel_tol=0.0,
        abs_tol=INDEX_TOLERANCE,
    )
    if not molecular_ok:
        findings.append(
            "total hazard index %.6f exceeds the allowable %.6f, driven by '%s'"
            % (total, compartment["allowable_total_index"], leader["name"])
        )
    over_limit = [
        record["name"] for record in records if record["hazard_index"] > 1.0
    ]
    for name in over_limit:
        findings.append(
            "species '%s' alone exceeds its own maximum allowable concentration"
            % name
        )
    particulate_ok = particulate_headroom > 0.0 or math.isclose(
        particulate_headroom, 0.0, rel_tol=0.0, abs_tol=INDEX_TOLERANCE
    )
    if not particulate_ok:
        findings.append(
            "airborne particulate %.4f mg/m3 exceeds the allowable %.4f mg/m3"
            % (
                compartment["particulate_mg_m3"],
                compartment["particulate_limit_mg_m3"],
            )
        )
    return {
        "species": records,
        "total_hazard_index": total,
        "allowable_total_index": compartment["allowable_total_index"],
        "driving_species": leader["name"],
        "species_over_own_limit": over_limit,
        "particulate_mg_m3": compartment["particulate_mg_m3"],
        "particulate_headroom_mg_m3": particulate_headroom,
        "compliant": molecular_ok and not over_limit and particulate_ok,
        "findings": findings,
    }
