#!/usr/bin/env python3
"""Material selection screen for an explosive device and its housing.

Anchor: ECSS-E-ST-33-11C clause 4.9. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A material next to an explosive charge has to survive two things that
are usually treated separately: the space environment, and the charge
itself. The clause puts them in one screen because the failure that
matters is the combination -- a polymer that outgasses acceptably and a
charge that is stable on its own can still produce a device whose
composition has been slowly attacked by what the polymer released.

The screen therefore runs five independent gates over every candidate
material and groups the outcome:

    outgassing      mass loss and condensable volatile fraction, from
                    the vacuum screening test
    compatibility   gas evolution and the shift in decomposition onset
                    measured with the material in contact with the
                    explosive
    corrosion       stress-corrosion susceptibility category, which is
                    a property of the alloy and its temper
    service         the material's own temperature rating against the
                    predicted hot case plus margin
    galvanic        the potential difference across each declared
                    contact pair, against the allowance the assembly's
                    environment carries

Limits are declared policy, not physical constants: the defaults below
are a starting point and a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SUSCEPTIBILITY_LEVELS = ("low", "moderate", "high")

ENVIRONMENTS = ("controlled-benign", "uncontrolled-humid", "marine-coastal")

GATES = ("outgassing", "compatibility", "corrosion", "service", "galvanic")

ACCEPTED = "accepted"
ACCEPTED_WITH_RESTRICTION = "accepted-with-restriction"
REJECTED = "rejected"

VERDICT_MET = "material-selection-met"
VERDICT_NOT_MET = "material-selection-not-met"

DEFAULT_MATERIAL_POLICY = {
    "max_total_mass_loss_percent": 1.0,
    "max_condensable_volatile_percent": 0.10,
    "max_gas_evolution_cc_per_g": 2.0,
    "max_onset_depression_k": 4.0,
    "allowed_susceptibility": ("low",),
    "service_temperature_margin_k": 10.0,
    "galvanic_allowance_v": {
        "controlled-benign": 0.50,
        "uncontrolled-humid": 0.25,
        "marine-coastal": 0.15,
    },
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    Screening limits are compared against measured percentages and
    differences of potentials, so a material sitting exactly on a limit
    can land a few units in the last place above it. The limit is never
    relaxed; only the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_material_policy(policy):
    """Check a selection policy carries every limit the gates need."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "max_total_mass_loss_percent",
        "max_condensable_volatile_percent",
        "max_gas_evolution_cc_per_g",
        "max_onset_depression_k",
    ):
        _require_positive("policy %s" % key, policy.get(key))
    _require_non_negative(
        "policy service_temperature_margin_k", policy.get("service_temperature_margin_k")
    )
    allowed = policy.get("allowed_susceptibility")
    if not isinstance(allowed, (list, tuple)) or not allowed:
        raise ValueError("policy allowed_susceptibility must be a non-empty sequence")
    for level in allowed:
        _require_choice("allowed susceptibility level", level, SUSCEPTIBILITY_LEVELS)
    table = policy.get("galvanic_allowance_v")
    if not isinstance(table, dict):
        raise ValueError("policy galvanic_allowance_v must be a mapping")
    missing = set(ENVIRONMENTS) - set(table)
    if missing:
        raise ValueError(
            "policy galvanic_allowance_v is missing environments: %s"
            % ", ".join(sorted(missing))
        )
    for environment in ENVIRONMENTS:
        _require_positive("galvanic allowance %s" % environment, table[environment])
    return policy


def validate_material(record):
    """Normalize one candidate material into a checked record."""
    if not isinstance(record, dict):
        raise ValueError("material must be a mapping, got %r" % (record,))
    material_id = record.get("id")
    if not isinstance(material_id, str) or not material_id.strip():
        raise ValueError("material id must be a non-empty string, got %r" % (material_id,))
    material_id = material_id.strip()
    contacts = record.get("contacts", [])
    if not isinstance(contacts, (list, tuple)):
        raise ValueError("material %s contacts must be a list" % material_id)
    cleaned_contacts = []
    for contact in contacts:
        if not isinstance(contact, str) or not contact.strip():
            raise ValueError("material %s has an empty contact id" % material_id)
        cleaned_contacts.append(contact.strip())
    return {
        "id": material_id,
        "total_mass_loss_percent": _require_non_negative(
            "material %s total_mass_loss_percent" % material_id,
            record.get("total_mass_loss_percent"),
        ),
        "condensable_volatile_percent": _require_non_negative(
            "material %s condensable_volatile_percent" % material_id,
            record.get("condensable_volatile_percent"),
        ),
        "gas_evolution_cc_per_g": _require_non_negative(
            "material %s gas_evolution_cc_per_g" % material_id,
            record.get("gas_evolution_cc_per_g"),
        ),
        "onset_depression_k": _require_non_negative(
            "material %s onset_depression_k" % material_id,
            record.get("onset_depression_k", 0.0),
        ),
        "susceptibility": _require_choice(
            "material %s susceptibility" % material_id,
            record.get("susceptibility"),
            SUSCEPTIBILITY_LEVELS,
        ),
        "susceptibility_justified": _require_bool(
            "material %s susceptibility_justified" % material_id,
            record.get("susceptibility_justified", False),
        ),
        "max_service_temperature_k": _require_positive(
            "material %s max_service_temperature_k" % material_id,
            record.get("max_service_temperature_k"),
        ),
        "galvanic_potential_v": _require_number(
            "material %s galvanic_potential_v" % material_id,
            record.get("galvanic_potential_v"),
        ),
        "contacts": cleaned_contacts,
    }


def validate_materials(materials):
    """Normalize a candidate list and reject duplicate identifiers."""
    if not isinstance(materials, (list, tuple)):
        raise ValueError("materials must be a list, got %r" % (materials,))
    if not materials:
        raise ValueError("materials must contain at least one candidate")
    normalized = []
    seen = set()
    for raw in materials:
        record = validate_material(raw)
        if record["id"] in seen:
            raise ValueError("duplicate material id %r" % record["id"])
        seen.add(record["id"])
        normalized.append(record)
    known = {record["id"] for record in normalized}
    for record in normalized:
        for contact in record["contacts"]:
            if contact not in known:
                raise ValueError(
                    "material %s declares a contact with unknown material %r"
                    % (record["id"], contact)
                )
            if contact == record["id"]:
                raise ValueError(
                    "material %s declares a contact with itself" % record["id"]
                )
    return normalized


def outgassing_verdict(record, policy=DEFAULT_MATERIAL_POLICY):
    """Grade the vacuum screening figures against the policy limits."""
    validate_material_policy(policy)
    material = validate_material(record)
    findings = []
    mass_ok = _at_most(
        material["total_mass_loss_percent"], policy["max_total_mass_loss_percent"]
    )
    volatile_ok = _at_most(
        material["condensable_volatile_percent"],
        policy["max_condensable_volatile_percent"],
    )
    if not mass_ok:
        findings.append(
            "%s loses %.3f%% of its mass, above the allowed %.3f%%"
            % (
                material["id"],
                material["total_mass_loss_percent"],
                policy["max_total_mass_loss_percent"],
            )
        )
    if not volatile_ok:
        findings.append(
            "%s deposits %.3f%% condensable volatiles, above the allowed %.3f%%"
            % (
                material["id"],
                material["condensable_volatile_percent"],
                policy["max_condensable_volatile_percent"],
            )
        )
    return {"gate": "outgassing", "compliant": not findings, "findings": findings}


def compatibility_verdict(record, policy=DEFAULT_MATERIAL_POLICY):
    """Grade contact-with-explosive behaviour: gas evolution and onset."""
    validate_material_policy(policy)
    material = validate_material(record)
    findings = []
    gas_ok = _at_most(
        material["gas_evolution_cc_per_g"], policy["max_gas_evolution_cc_per_g"]
    )
    onset_ok = _at_most(material["onset_depression_k"], policy["max_onset_depression_k"])
    if not gas_ok:
        findings.append(
            "%s evolves %.3f cc/g in contact with the charge, above the allowed "
            "%.3f cc/g"
            % (
                material["id"],
                material["gas_evolution_cc_per_g"],
                policy["max_gas_evolution_cc_per_g"],
            )
        )
    if not onset_ok:
        findings.append(
            "%s depresses the decomposition onset by %.2f K, above the allowed "
            "%.2f K"
            % (
                material["id"],
                material["onset_depression_k"],
                policy["max_onset_depression_k"],
            )
        )
    return {"gate": "compatibility", "compliant": not findings, "findings": findings}


def corrosion_verdict(record, policy=DEFAULT_MATERIAL_POLICY):
    """Grade stress-corrosion susceptibility, allowing a justified case."""
    validate_material_policy(policy)
    material = validate_material(record)
    level = material["susceptibility"]
    findings = []
    restricted = False
    if level not in policy["allowed_susceptibility"]:
        if material["susceptibility_justified"]:
            restricted = True
            findings.append(
                "%s carries %s stress-corrosion susceptibility and is retained "
                "only on its declared justification" % (material["id"], level)
            )
        else:
            findings.append(
                "%s carries %s stress-corrosion susceptibility with no "
                "justification on record" % (material["id"], level)
            )
    return {
        "gate": "corrosion",
        "susceptibility": level,
        "restricted": restricted,
        "compliant": restricted or not findings,
        "findings": findings,
    }


def service_temperature_verdict(
    record, predicted_hot_k, policy=DEFAULT_MATERIAL_POLICY
):
    """Grade the material's temperature rating against the hot case."""
    validate_material_policy(policy)
    material = validate_material(record)
    hot = _require_positive("predicted_hot_k", predicted_hot_k)
    required = hot + policy["service_temperature_margin_k"]
    ok = _at_least(material["max_service_temperature_k"], required)
    findings = []
    if not ok:
        findings.append(
            "%s is rated to %.2f K, short of the %.2f K the hot case plus margin "
            "demands" % (material["id"], material["max_service_temperature_k"], required)
        )
    return {
        "gate": "service",
        "required_rating_k": required,
        "compliant": ok,
        "findings": findings,
    }


def galvanic_couple_difference_v(potential_a_v, potential_b_v):
    """Magnitude of the potential difference across a contact pair."""
    first = _require_number("potential_a_v", potential_a_v)
    second = _require_number("potential_b_v", potential_b_v)
    return abs(first - second)


def galvanic_verdict(
    material_a, material_b, environment, policy=DEFAULT_MATERIAL_POLICY
):
    """Grade one contact pair against the environment's allowance."""
    validate_material_policy(policy)
    _require_choice("environment", environment, ENVIRONMENTS)
    first = validate_material(material_a)
    second = validate_material(material_b)
    allowance = policy["galvanic_allowance_v"][environment]
    difference = galvanic_couple_difference_v(
        first["galvanic_potential_v"], second["galvanic_potential_v"]
    )
    ok = _at_most(difference, allowance)
    findings = []
    if not ok:
        findings.append(
            "%s against %s couples at %.3f V, above the %.3f V allowed in a %s "
            "environment"
            % (first["id"], second["id"], difference, allowance, environment)
        )
    return {
        "gate": "galvanic",
        "pair": tuple(sorted((first["id"], second["id"]))),
        "difference_v": difference,
        "allowance_v": allowance,
        "compliant": ok,
        "findings": findings,
    }


def couple_pairs(materials):
    """Distinct contact pairs declared across a material list."""
    records = validate_materials(materials)
    by_id = {record["id"]: record for record in records}
    pairs = set()
    for record in records:
        for contact in record["contacts"]:
            pairs.add(tuple(sorted((record["id"], contact))))
    return [(by_id[a], by_id[b]) for a, b in sorted(pairs)]


def assess_material(record, case, policy=DEFAULT_MATERIAL_POLICY):
    """Run the per-material gates and group the outcome."""
    validate_material_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    material = validate_material(record)
    gates = {
        "outgassing": outgassing_verdict(record, policy),
        "compatibility": compatibility_verdict(record, policy),
        "corrosion": corrosion_verdict(record, policy),
        "service": service_temperature_verdict(
            record, case.get("predicted_hot_k"), policy
        ),
    }
    findings = []
    failed = []
    for name in ("outgassing", "compatibility", "corrosion", "service"):
        gate = gates[name]
        findings.extend(gate["findings"])
        if not gate["compliant"]:
            failed.append(name)
    if failed:
        outcome = REJECTED
    elif gates["corrosion"]["restricted"]:
        outcome = ACCEPTED_WITH_RESTRICTION
    else:
        outcome = ACCEPTED
    return {
        "id": material["id"],
        "gates": gates,
        "failed_gates": failed,
        "outcome": outcome,
        "findings": findings,
    }


def select_materials(materials, case, policy=DEFAULT_MATERIAL_POLICY):
    """Full clause 4.9 selection screen with an assembly verdict."""
    validate_material_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    environment = _require_choice(
        "environment", case.get("environment"), ENVIRONMENTS
    )
    records = validate_materials(materials)
    per_material = [assess_material(record, case, policy) for record in records]
    couples = [
        galvanic_verdict(first, second, environment, policy)
        for first, second in couple_pairs(materials)
    ]
    findings = []
    for result in per_material:
        findings.extend(result["findings"])
    for couple in couples:
        findings.extend(couple["findings"])
    accepted = [r["id"] for r in per_material if r["outcome"] == ACCEPTED]
    restricted = [
        r["id"] for r in per_material if r["outcome"] == ACCEPTED_WITH_RESTRICTION
    ]
    rejected = [r["id"] for r in per_material if r["outcome"] == REJECTED]
    failed_couples = [couple["pair"] for couple in couples if not couple["compliant"]]
    compliant = not rejected and not failed_couples
    return {
        "environment": environment,
        "materials": per_material,
        "couples": couples,
        "accepted": accepted,
        "accepted_with_restriction": restricted,
        "rejected": rejected,
        "failed_couples": failed_couples,
        "compliant": compliant,
        "verdict": VERDICT_MET if compliant else VERDICT_NOT_MET,
        "findings": findings,
    }
