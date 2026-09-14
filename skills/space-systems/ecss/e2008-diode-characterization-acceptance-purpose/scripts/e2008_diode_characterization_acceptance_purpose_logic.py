#!/usr/bin/env python3
"""Purpose of characterising a protection diode during acceptance.

Anchor: ECSS-E-ST-20-08C clause 9.4.5.2.1. The steps below are a
paraphrase into implementable form; no standard text is reproduced.

A protection diode on a photovoltaic assembly is fitted for a fault it
may never see. Nothing in an acceptance flow exercises that fault, so
the only evidence that the part will do its job on the day is its
electrical behaviour measured while the assembly is still on the
ground. That is what the acceptance characterisation is for.

Three separate consumers want the number, and each wants a different
part of it:

    forward behaviour   the drop the diode adds while it carries the
                        current of the section it protects, and the
                        heat that drop puts into the substrate
    reverse behaviour   the leakage it passes while it is supposed to
                        be blocking, which is array power spent on
                        nothing for the whole mission
    the record itself   a per-part electrical signature that a later
                        degradation claim can be measured against

A characterisation serves that purpose only if it reaches enough of
the population to sentence the lot. Measuring one diode out of four
hundred produces a number, not acceptance evidence, and the difference
between a characterisation nobody planned and one planned too thin is
a distinct outcome that has to be reported as such.

The sample floor, the dissipation budget and the parasitic-loss
allowance below are a declared policy, not a physical constant: a
project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Declared protection role -> the quantity the characterisation feeds.
PROTECTION_ROLES = {
    "cell-string-bypass-on-shadowing": "string-output-held-through-a-shadowed-section",
    "section-blocking-against-bus-drain": "reverse-drain-kept-off-the-regulated-bus",
    "shunt-path-around-a-failed-section": "current-carried-around-a-failed-section",
    "cell-reverse-bias-protection": "cell-reverse-bias-held-below-the-damage-point",
    "string-to-string-fault-isolation": "fault-propagation-contained-to-one-string",
}

RECOGNISED_ROLES = tuple(sorted(PROTECTION_ROLES))

COMMON_OBJECTIVE = "protection-diode-electrical-performance-record"

DIODE_CHARACTERISATION_NOT_REQUIRED = "diode-characterisation-not-required"
DIODE_CHARACTERISATION_NOT_PLANNED = "diode-characterisation-not-planned"
DIODE_CHARACTERISATION_UNDERSAMPLED = "diode-characterisation-undersampled"
DIODE_LOSS_BUDGET_EXCEEDED = "diode-loss-budget-exceeded"
DIODE_CHARACTERISATION_JUSTIFIED = "diode-characterisation-justified"

DEFAULT_PURPOSE_POLICY = {
    "min_sample_fraction": 0.10,
    "max_forward_dissipation_w": 2.0,
    "max_parasitic_loss_fraction": 0.01,
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
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return number


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_purpose_policy(policy):
    """Check an acceptance-characterisation policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    sample_floor = _require_fraction(
        "min_sample_fraction", policy.get("min_sample_fraction")
    )
    if sample_floor <= 0.0:
        raise ValueError(
            "min_sample_fraction must be above zero; a floor of nought accepts a "
            "lot nobody measured"
        )
    _require_positive(
        "max_forward_dissipation_w", policy.get("max_forward_dissipation_w")
    )
    loss_allowance = _require_fraction(
        "max_parasitic_loss_fraction", policy.get("max_parasitic_loss_fraction")
    )
    if loss_allowance >= 1.0:
        raise ValueError(
            "max_parasitic_loss_fraction %g would let leakage take the whole "
            "array output" % (loss_allowance,)
        )
    return policy


def forward_dissipation_w(forward_voltage_v, forward_current_a):
    """Heat the diode puts into the substrate while it conducts."""
    drop = _require_positive("forward_voltage_v", forward_voltage_v)
    current = _require_positive("forward_current_a", forward_current_a)
    return drop * current


def parasitic_reverse_loss_w(reverse_voltage_v, reverse_leakage_a, diode_count):
    """Array power the blocked diodes spend on leakage for the whole mission."""
    voltage = _require_positive("reverse_voltage_v", reverse_voltage_v)
    leakage = _require_non_negative("reverse_leakage_a", reverse_leakage_a)
    count = _require_count("diode_count", diode_count, minimum=1)
    return voltage * leakage * count


def parasitic_loss_fraction(loss_w, array_output_w):
    """The leakage loss taken as a share of what the array delivers."""
    loss = _require_non_negative("loss_w", loss_w)
    output = _require_positive("array_output_w", array_output_w)
    return loss / output


def sample_coverage_fraction(characterised_count, population_count):
    """Share of the fitted diode population the characterisation reaches."""
    population = _require_count("population_count", population_count, minimum=1)
    characterised = _require_count(
        "characterised_count", characterised_count, minimum=0
    )
    if characterised > population:
        raise ValueError(
            "characterised_count %d exceeds the population of %d; a sample "
            "cannot be larger than the lot it is drawn from"
            % (characterised, population)
        )
    return characterised / population


def dissipation_within_budget(dissipation_w, policy=DEFAULT_PURPOSE_POLICY):
    """True when the forward heat sits inside the declared substrate budget."""
    validate_purpose_policy(policy)
    value = _require_non_negative("dissipation_w", dissipation_w)
    return _at_most(value, float(policy["max_forward_dissipation_w"]))


def parasitic_loss_within_allowance(loss_fraction, policy=DEFAULT_PURPOSE_POLICY):
    """True when the leakage share sits inside the declared allowance."""
    validate_purpose_policy(policy)
    value = _require_non_negative("loss_fraction", loss_fraction)
    return _at_most(value, float(policy["max_parasitic_loss_fraction"]))


def role_inventory(roles):
    """Group the declared protection roles, rejecting an unrecognised one."""
    if not isinstance(roles, (list, tuple, set, frozenset)):
        raise ValueError("roles must be a collection of protection role names")
    grouped = []
    for role in roles:
        if role not in PROTECTION_ROLES:
            raise ValueError(
                "unknown protection role %r; recognised roles are %s"
                % (role, ", ".join(RECOGNISED_ROLES))
            )
        if role not in grouped:
            grouped.append(role)
    return tuple(sorted(grouped))


def characterisation_objectives(roles):
    """What the characterisation feeds, given the declared protection roles."""
    grouped = role_inventory(roles)
    if not grouped:
        return ()
    objectives = [PROTECTION_ROLES[role] for role in grouped]
    objectives.append(COMMON_OBJECTIVE)
    return tuple(objectives)


def assess_diode_characterisation_purpose(case, policy=DEFAULT_PURPOSE_POLICY):
    """Full clause 9.4.5.2.1 judgement for one acceptance characterisation."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_purpose_policy(policy)
    if "protection_roles" not in case:
        raise ValueError(
            "case is missing protection_roles; an absent inventory is not an "
            "empty one"
        )
    roles = role_inventory(case["protection_roles"])
    objectives = characterisation_objectives(case["protection_roles"])

    assembly = case.get("assembly")
    if not isinstance(assembly, dict):
        raise ValueError("case is missing an assembly block")
    population = _require_count(
        "assembly diode_population", assembly.get("diode_population"), minimum=1
    )
    forward_current = _require_positive(
        "assembly worst_case_forward_current_a",
        assembly.get("worst_case_forward_current_a"),
    )
    forward_voltage = _require_positive(
        "assembly expected_forward_voltage_v",
        assembly.get("expected_forward_voltage_v"),
    )
    reverse_voltage = _require_positive(
        "assembly string_reverse_voltage_v", assembly.get("string_reverse_voltage_v")
    )
    reverse_leakage = _require_non_negative(
        "assembly expected_reverse_leakage_a",
        assembly.get("expected_reverse_leakage_a"),
    )
    array_output = _require_positive(
        "assembly array_output_w", assembly.get("array_output_w")
    )

    dissipation = forward_dissipation_w(forward_voltage, forward_current)
    parasitic = parasitic_reverse_loss_w(reverse_voltage, reverse_leakage, population)
    loss_fraction = parasitic_loss_fraction(parasitic, array_output)
    heat_ok = dissipation_within_budget(dissipation, policy)
    loss_ok = parasitic_loss_within_allowance(loss_fraction, policy)

    findings = []
    result = {
        "protection_roles": roles,
        "objectives": objectives,
        "diode_population": population,
        "forward_dissipation_w": dissipation,
        "parasitic_reverse_loss_w": parasitic,
        "parasitic_loss_fraction": loss_fraction,
        "dissipation_within_budget": heat_ok,
        "parasitic_loss_within_allowance": loss_ok,
        "sample_coverage_fraction": None,
        "sample_coverage_met": None,
        "findings": findings,
    }

    if not roles:
        findings.append(
            "no protection role is declared, so nothing on the assembly depends "
            "on how this diode behaves electrically"
        )
        result["required"] = False
        result["verdict"] = DIODE_CHARACTERISATION_NOT_REQUIRED
        return result

    result["required"] = True
    characterisation = case.get("characterisation")
    if characterisation is None:
        findings.append(
            "a protection role is declared but no acceptance characterisation is "
            "planned; the purpose is stated and not yet served"
        )
        result["verdict"] = DIODE_CHARACTERISATION_NOT_PLANNED
        return result
    if not isinstance(characterisation, dict):
        raise ValueError(
            "characterisation must be a mapping, got %r" % (characterisation,)
        )

    characterised = _require_count(
        "characterisation characterised_count",
        characterisation.get("characterised_count"),
        minimum=0,
    )
    coverage = sample_coverage_fraction(characterised, population)
    sample_floor = float(policy["min_sample_fraction"])
    coverage_met = _at_least(coverage, sample_floor)
    result["characterised_count"] = characterised
    result["sample_coverage_fraction"] = coverage
    result["sample_coverage_met"] = coverage_met

    if not coverage_met:
        findings.append(
            "the characterisation reaches %d of %d fitted diodes, a coverage of "
            "%.4f against the %.4f floor, which sentences no lot"
            % (characterised, population, coverage, sample_floor)
        )
        result["verdict"] = DIODE_CHARACTERISATION_UNDERSAMPLED
        return result

    if not heat_ok:
        findings.append(
            "the diode drops %.4g V at %.4g A, putting %.4g W into the substrate "
            "against the %.4g W budget"
            % (
                forward_voltage,
                forward_current,
                dissipation,
                float(policy["max_forward_dissipation_w"]),
            )
        )
    if not loss_ok:
        findings.append(
            "the %d fitted diodes leak %.4g W at %.4g V, a share of %.6f of the "
            "%.4g W array output against the %.6f allowance"
            % (
                population,
                parasitic,
                reverse_voltage,
                loss_fraction,
                array_output,
                float(policy["max_parasitic_loss_fraction"]),
            )
        )
    if findings:
        result["verdict"] = DIODE_LOSS_BUDGET_EXCEEDED
        return result

    result["verdict"] = DIODE_CHARACTERISATION_JUSTIFIED
    return result
