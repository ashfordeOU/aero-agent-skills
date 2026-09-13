#!/usr/bin/env python3
"""Electric-propulsion description and charging-interaction survey.

Anchor: ECSS-E-ST-20-06C clause 11.1.1 (paraphrased, not quoted).

Clause 11.1.1 introduces the range of electric thrusters flown on
spacecraft and the charging interactions their operation produces.
This module turns that introduction into a deterministic, checkable
procedure:

* sort a thruster designation into its acceleration family
  (electrostatic, electromagnetic, electrothermal);
* derive exhaust velocity, propellant mass-flow and the extracted
  beam current from thrust, specific impulse and propellant ion mass;
* decide whether the unit ejects a net charged beam and therefore
  needs an electron-emitting neutralizer;
* enumerate the charging interactions the unit drives on the host
  spacecraft;
* aggregate a propulsion set into one survey with explicit findings.

Standard library only, offline, deterministic.
"""

import math

# Physical constants (CODATA, exact where defined).
STANDARD_GRAVITY_M_S2 = 9.80665
ELEMENTARY_CHARGE_C = 1.602176634e-19
ATOMIC_MASS_UNIT_KG = 1.66053906660e-27

# Tolerance used only to absorb binary-floating-point representation
# error on an exact-boundary comparison. It never widens an
# engineering limit.
REPRESENTATION_TOLERANCE = 1e-9

# Acceleration family per thruster designation. The family fixes how
# momentum is imparted and therefore which charging interactions the
# unit can drive.
THRUSTER_FAMILY = {
    "gridded-ion": "electrostatic",
    "hall-effect": "electromagnetic",
    "field-emission-electric-propulsion": "electrostatic",
    "colloid": "electrostatic",
    "pulsed-plasma": "electromagnetic",
    "magnetoplasmadynamic": "electromagnetic",
    "arcjet": "electrothermal",
    "resistojet": "electrothermal",
}

# Short paraphrase of the acceleration mechanism, used in the survey
# record so a reviewer can see why a family was assigned.
ACCELERATION_MECHANISM = {
    "gridded-ion": "ions extracted and accelerated by a biased grid set",
    "hall-effect": "ions accelerated in a crossed-field discharge channel",
    "field-emission-electric-propulsion": (
        "ions field-extracted from a liquid-metal emitter"
    ),
    "colloid": "charged droplets extracted from a conductive liquid",
    "pulsed-plasma": "ablated plasma driven by a pulsed Lorentz force",
    "magnetoplasmadynamic": "plasma driven by a self-induced Lorentz force",
    "arcjet": "propellant heated by an electric arc, expanded in a nozzle",
    "resistojet": "propellant heated by a resistive element, expanded in a nozzle",
}

# Ion mass of the qualified propellants, in atomic mass units.
PROPELLANT_ION_MASS_AMU = {
    "xenon": 131.293,
    "krypton": 83.798,
    "argon": 39.948,
    "iodine": 126.904,
    "ptfe": 100.016,
}

# Net charge ejection per designation. A quasi-neutral plasma exhaust
# (ablation-fed or self-field accelerated) leaves the unit already
# current-balanced and drives no separate neutralizer requirement;
# a net ion beam does.
EJECTS_NET_CHARGE = {
    "gridded-ion": True,
    "hall-effect": True,
    "field-emission-electric-propulsion": True,
    "colloid": True,
    "pulsed-plasma": False,
    "magnetoplasmadynamic": False,
    "arcjet": False,
    "resistojet": False,
}

# Plume-driven charging interactions common to every plasma-producing
# family. Ordered tuples keep the survey output deterministic.
PLASMA_PLUME_INTERACTIONS = (
    "charge-exchange-plasma-backflow",
    "floating-potential-shift",
    "plume-sputter-deposition",
)
ELECTROTHERMAL_INTERACTIONS = ("neutral-gas-pressure-rise",)


def thruster_family(kind):
    """Return the acceleration family of a thruster designation."""
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("thruster designation must be a non-empty string")
    key = kind.strip().lower()
    if key not in THRUSTER_FAMILY:
        raise ValueError("uncategorized thruster designation: %r" % (kind,))
    return THRUSTER_FAMILY[key]


def acceleration_mechanism(kind):
    """Return the paraphrased acceleration mechanism of a thruster."""
    family = thruster_family(kind)  # validates the designation
    del family
    return ACCELERATION_MECHANISM[kind.strip().lower()]


def emits_charged_beam(kind):
    """True when the unit ejects a net charged beam.

    An electrothermal unit heats a neutral gas, and an ablation-fed or
    self-field plasma unit ejects a quasi-neutral exhaust; neither
    leaves the spacecraft with a net current to return.
    """
    thruster_family(kind)  # validates the designation
    return EJECTS_NET_CHARGE[kind.strip().lower()]


def neutralizer_required(kind):
    """True when an electron-emitting neutralizer is required."""
    return emits_charged_beam(kind)


def exhaust_velocity(specific_impulse_s):
    """Effective exhaust velocity [m/s] from specific impulse [s]."""
    if specific_impulse_s <= 0:
        raise ValueError("specific impulse must be > 0 s")
    return specific_impulse_s * STANDARD_GRAVITY_M_S2


def mass_flow_rate(thrust_n, specific_impulse_s):
    """Propellant mass-flow [kg/s] from thrust [N] and impulse [s]."""
    if thrust_n <= 0:
        raise ValueError("thrust must be > 0 N")
    return thrust_n / exhaust_velocity(specific_impulse_s)


def specific_charge(propellant, charge_state=1):
    """Charge-to-mass ratio [C/kg] of the accelerated ion."""
    if not isinstance(propellant, str) or not propellant.strip():
        raise ValueError("propellant must be a non-empty string")
    key = propellant.strip().lower()
    if key not in PROPELLANT_ION_MASS_AMU:
        raise ValueError("undeclared propellant: %r" % (propellant,))
    if not isinstance(charge_state, int) or isinstance(charge_state, bool):
        raise ValueError("charge state must be an integer")
    if charge_state < 1:
        raise ValueError("charge state must be >= 1")
    ion_mass_kg = PROPELLANT_ION_MASS_AMU[key] * ATOMIC_MASS_UNIT_KG
    return charge_state * ELEMENTARY_CHARGE_C / ion_mass_kg


def beam_current(thrust_n, specific_impulse_s, propellant,
                 charge_state=1, beam_fraction=1.0):
    """Extracted beam current [A] of a charged-beam thruster.

    The current is the charged mass-flow times the ion charge-to-mass
    ratio; ``beam_fraction`` is the share of the mass-flow that leaves
    the unit ionised (the remainder escapes as neutral gas).
    """
    if beam_fraction <= 0:
        raise ValueError("beam fraction must be > 0")
    if beam_fraction > 1.0 + REPRESENTATION_TOLERANCE:
        raise ValueError("beam fraction must be <= 1")
    flow = mass_flow_rate(thrust_n, specific_impulse_s)
    return flow * min(beam_fraction, 1.0) * specific_charge(propellant, charge_state)


def validate_power_split(fractions):
    """Validate a declared input-power split of an electric thruster.

    ``fractions`` maps a loss/consumer label to its share of the input
    power. Shares must be positive and their sum must not exceed unity;
    the balance is the residual thermal loss, returned to the caller.
    An exact-unity split expressed as a sum of binary floats is
    compliant, so the sum test absorbs representation error rather than
    relaxing the engineering limit.
    """
    if not isinstance(fractions, dict) or not fractions:
        raise ValueError("power split must be a non-empty mapping")
    total = 0.0
    for label, share in sorted(fractions.items()):
        if not isinstance(label, str) or not label.strip():
            raise ValueError("power split label must be a non-empty string")
        if share <= 0:
            raise ValueError("power share %r must be > 0" % (label,))
        total += share
    if total > 1.0 and not math.isclose(total, 1.0,
                                        rel_tol=0.0,
                                        abs_tol=REPRESENTATION_TOLERANCE):
        raise ValueError("declared power shares sum to %.6f, must not exceed 1" % total)
    residual = 1.0 - total
    if residual < 0.0:
        residual = 0.0
    return residual


def charging_interactions(kind, neutralizer_present=True):
    """Charging interactions the unit drives on the host spacecraft.

    A net-charge unit flown without an electron-emitting neutralizer
    replaces the neutralizer-coupling-voltage interaction with an
    unneutralized-beam-charging interaction, because the host body must
    then supply the return current through its own surfaces.
    """
    family = thruster_family(kind)
    if not isinstance(neutralizer_present, bool):
        raise ValueError("neutralizer presence must be a boolean")
    if family == "electrothermal":
        return tuple(sorted(ELECTROTHERMAL_INTERACTIONS))
    interactions = list(PLASMA_PLUME_INTERACTIONS)
    if family == "electromagnetic":
        interactions.append("pulsed-electromagnetic-emission")
    if EJECTS_NET_CHARGE[kind.strip().lower()]:
        interactions.append("beam-space-charge")
        if neutralizer_present:
            interactions.append("neutralizer-coupling-voltage")
        else:
            interactions.append("unneutralized-beam-charging")
    return tuple(sorted(interactions))


def describe_thruster(record):
    """Build the clause 11.1.1 description record for one unit.

    Required keys: ``id``, ``kind``, ``thrust_n``, ``specific_impulse_s``.
    Optional: ``propellant``, ``charge_state``, ``beam_fraction``,
    ``neutralizer_present``, ``power_split``.
    """
    if not isinstance(record, dict):
        raise ValueError("thruster record must be a mapping")
    for key in ("id", "kind", "thrust_n", "specific_impulse_s"):
        if key not in record:
            raise ValueError("thruster record missing required key %r" % (key,))
    unit_id = record["id"]
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("thruster id must be a non-empty string")
    kind = record["kind"]
    family = thruster_family(kind)
    charged = emits_charged_beam(kind)
    neutralizer_present = record.get("neutralizer_present", charged)
    out = {
        "id": unit_id,
        "kind": kind.strip().lower(),
        "family": family,
        "mechanism": acceleration_mechanism(kind),
        "exhaust_velocity_m_s": exhaust_velocity(record["specific_impulse_s"]),
        "mass_flow_kg_s": mass_flow_rate(record["thrust_n"],
                                         record["specific_impulse_s"]),
        "emits_charged_beam": charged,
        "neutralizer_required": charged,
        "neutralizer_present": bool(neutralizer_present),
        "findings": [],
    }
    if charged:
        propellant = record.get("propellant")
        if propellant is None:
            raise ValueError("charged-beam thruster %r needs a propellant" % (unit_id,))
        out["beam_current_a"] = beam_current(
            record["thrust_n"],
            record["specific_impulse_s"],
            propellant,
            record.get("charge_state", 1),
            record.get("beam_fraction", 1.0),
        )
        out["propellant"] = propellant.strip().lower()
    else:
        out["beam_current_a"] = 0.0
        out["propellant"] = record.get("propellant", "none")
    if "power_split" in record:
        out["residual_thermal_fraction"] = validate_power_split(record["power_split"])
    out["interactions"] = charging_interactions(kind, bool(neutralizer_present))
    if charged and not neutralizer_present:
        out["findings"].append("unneutralized-beam: %s" % unit_id)
    if not charged and record.get("neutralizer_present"):
        out["findings"].append(
            "neutralizer-declared-on-current-balanced-unit: %s" % unit_id)
    return out


def survey_propulsion_set(records):
    """Survey a whole electric-propulsion set for clause 11.1.1.

    Returns per-unit descriptions, the union of charging interactions,
    the summed beam current and the aggregated findings. The set is
    description-complete when no finding is raised.
    """
    if not isinstance(records, (list, tuple)):
        raise ValueError("propulsion set must be a list of records")
    if not records:
        raise ValueError("propulsion set must contain at least one unit")
    units = []
    seen = set()
    findings = []
    interactions = set()
    total_beam_current = 0.0
    for record in records:
        described = describe_thruster(record)
        if described["id"] in seen:
            raise ValueError("duplicate thruster id %r" % (described["id"],))
        seen.add(described["id"])
        units.append(described)
        findings.extend(described["findings"])
        interactions.update(described["interactions"])
        total_beam_current += described["beam_current_a"]
    families = sorted({u["family"] for u in units})
    return {
        "units": units,
        "families": families,
        "interactions": tuple(sorted(interactions)),
        "total_beam_current_a": total_beam_current,
        "findings": findings,
        "description_complete": not findings,
    }
