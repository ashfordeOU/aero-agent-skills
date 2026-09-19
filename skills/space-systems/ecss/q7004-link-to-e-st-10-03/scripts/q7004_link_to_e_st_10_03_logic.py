#!/usr/bin/env python3
"""Interface between an ECSS thermal test and equipment-level testing.

Anchor: ECSS-Q-ST-70-04C, the interface clauses that point at the
equipment-level environmental test standard ECSS-E-ST-10-03C. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

One article can sit under two documents at once. The thermal testing
standard sets conditions from the material and process side; the
equipment-level standard sets them from the environmental verification
side. Where both speak to the same parameter the reconciliation is not a
negotiation, it is a comparison: the more severe value governs, and the
document it came from is named next to it.

Enveloping is the second question and it is not the same one. A set of
equipment-level conditions that is more severe on four parameters and
less severe on the fifth does not envelope anything; the fifth is a
coverage gap and stays in the material-level campaign.

Credit is the third. Cycles already run at equipment level can be
counted against the material-level requirement, but only at a declared
efficiency, because the two runs are not the same run, and only up to a
cap, because a campaign that credits itself away has verified nothing.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MATERIAL_STANDARD = "q-st-70-04"
EQUIPMENT_STANDARD = "e-st-10-03"

HIGHER_IS_SEVERE = "higher"
LOWER_IS_SEVERE = "lower"

PARAMETER_SENSE = {
    "hot_limit_k": HIGHER_IS_SEVERE,
    "cold_limit_k": LOWER_IS_SEVERE,
    "cycle_count": HIGHER_IS_SEVERE,
    "dwell_s": HIGHER_IS_SEVERE,
    "soak_s": HIGHER_IS_SEVERE,
    "chamber_pressure_pa": LOWER_IS_SEVERE,
}

DEFAULT_INTERFACE_POLICY = {
    "credit_efficiency": 0.5,
    "credit_cap_fraction": 0.5,
    "min_hot_margin_k": 5.0,
    "min_cold_margin_k": 5.0,
    "required_parameters": (
        "hot_limit_k",
        "cold_limit_k",
        "cycle_count",
        "dwell_s",
    ),
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


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(
            "%s must be a non-negative integer, got %r" % (name, value)
        )
    return value


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def validate_interface_policy(policy):
    """Check a reconciliation policy carries usable credit rules."""
    _require_mapping("policy", policy)
    efficiency = _require_number(
        "credit_efficiency", policy.get("credit_efficiency")
    )
    if not 0.0 < efficiency <= 1.0:
        raise ValueError(
            "credit_efficiency must sit in (0, 1], got %r"
            % policy.get("credit_efficiency")
        )
    cap = _require_number("credit_cap_fraction", policy.get("credit_cap_fraction"))
    if not 0.0 <= cap < 1.0:
        raise ValueError(
            "credit_cap_fraction must sit in [0, 1), or the campaign credits "
            "itself away entirely; got %r" % policy.get("credit_cap_fraction")
        )
    _require_non_negative("min_hot_margin_k", policy.get("min_hot_margin_k"))
    _require_non_negative("min_cold_margin_k", policy.get("min_cold_margin_k"))
    required = policy.get("required_parameters")
    if not isinstance(required, (tuple, list)) or not required:
        raise ValueError("policy required_parameters must be a non-empty sequence")
    unknown = [name for name in required if name not in PARAMETER_SENSE]
    if unknown:
        raise ValueError(
            "policy names parameters with no severity sense: %s"
            % ", ".join(sorted(unknown))
        )
    return policy


def severity_sense(parameter):
    """Which direction is the severe one for a named parameter."""
    if parameter not in PARAMETER_SENSE:
        raise ValueError(
            "no severity sense declared for parameter %r; add it rather than "
            "guessing a direction" % parameter
        )
    return PARAMETER_SENSE[parameter]


def more_severe(parameter, material_value, equipment_value):
    """Governing value of one parameter and the document it came from."""
    sense = severity_sense(parameter)
    material = _require_number("material %s" % parameter, material_value)
    equipment = _require_number("equipment %s" % parameter, equipment_value)
    if _close(material, equipment):
        return {
            "parameter": parameter,
            "material_value": material,
            "equipment_value": equipment,
            "governing_value": material,
            "governing_standard": "both",
        }
    if sense == HIGHER_IS_SEVERE:
        severe_is_equipment = equipment > material
    else:
        severe_is_equipment = equipment < material
    return {
        "parameter": parameter,
        "material_value": material,
        "equipment_value": equipment,
        "governing_value": equipment if severe_is_equipment else material,
        "governing_standard": (
            EQUIPMENT_STANDARD if severe_is_equipment else MATERIAL_STANDARD
        ),
    }


def reconcile_parameters(material, equipment, policy=DEFAULT_INTERFACE_POLICY):
    """Parameter-by-parameter reconciliation of the two requirement sets."""
    validate_interface_policy(policy)
    _require_mapping("material", material)
    _require_mapping("equipment", equipment)
    reconciled = {}
    for parameter in policy["required_parameters"]:
        if parameter not in material:
            raise ValueError(
                "material requirement set is missing %r" % parameter
            )
        if parameter not in equipment:
            raise ValueError(
                "equipment requirement set is missing %r" % parameter
            )
        reconciled[parameter] = more_severe(
            parameter, material[parameter], equipment[parameter]
        )
    return reconciled


def envelope_gaps(reconciled):
    """Parameters on which the equipment-level set fails to envelope."""
    _require_mapping("reconciled", reconciled)
    gaps = []
    for parameter, record in sorted(reconciled.items()):
        if record["governing_standard"] == MATERIAL_STANDARD:
            gaps.append(parameter)
    return tuple(gaps)


def envelopes_material(reconciled):
    """True when the equipment-level set covers every reconciled parameter."""
    return not envelope_gaps(reconciled)


def credited_cycles(
    equipment_cycles_run, required_cycles, policy=DEFAULT_INTERFACE_POLICY
):
    """Cycles the equipment-level run may be credited for, and what is left.

    A cycle run under the other standard is not the same cycle, so it is
    credited at a declared efficiency, and the total credit is capped at a
    fraction of the requirement so that a campaign cannot credit itself
    down to nothing.
    """
    validate_interface_policy(policy)
    run = _require_count("equipment_cycles_run", equipment_cycles_run)
    required = _require_count("required_cycles", required_cycles)
    if required < 1:
        raise ValueError("required_cycles must be at least 1, got %r" % required_cycles)
    earned = int(math.floor(run * policy["credit_efficiency"] + _ABS_TOL))
    cap = int(math.floor(required * policy["credit_cap_fraction"] + _ABS_TOL))
    credit = min(earned, cap)
    return {
        "equipment_cycles_run": run,
        "required_cycles": required,
        "earned_before_cap": earned,
        "cap": cap,
        "credited_cycles": credit,
        "remaining_cycles": required - credit,
        "capped": earned > cap,
    }


def qualification_margin_k(
    acceptance_limit_k, qualification_limit_k, sense=HIGHER_IS_SEVERE
):
    """Temperature margin the qualification limit holds over acceptance."""
    acceptance = _require_positive("acceptance_limit_k", acceptance_limit_k)
    qualification = _require_positive(
        "qualification_limit_k", qualification_limit_k
    )
    if sense == HIGHER_IS_SEVERE:
        return qualification - acceptance
    if sense == LOWER_IS_SEVERE:
        return acceptance - qualification
    raise ValueError("sense must be %r or %r, got %r" % (
        HIGHER_IS_SEVERE, LOWER_IS_SEVERE, sense
    ))


def coordinate_with_equipment_standard(case, policy=DEFAULT_INTERFACE_POLICY):
    """Full reconciliation of a thermal test with the equipment-level set."""
    validate_interface_policy(policy)
    _require_mapping("case", case)
    reconciled = reconcile_parameters(
        case.get("material_requirements"),
        case.get("equipment_requirements"),
        policy,
    )
    gaps = envelope_gaps(reconciled)
    governing_counts = reconciled["cycle_count"]["governing_value"]
    credit = credited_cycles(
        case.get("equipment_cycles_run", 0), int(governing_counts), policy
    )
    hot_margin = qualification_margin_k(
        reconciled["hot_limit_k"]["material_value"],
        reconciled["hot_limit_k"]["governing_value"],
        HIGHER_IS_SEVERE,
    )
    cold_margin = qualification_margin_k(
        reconciled["cold_limit_k"]["material_value"],
        reconciled["cold_limit_k"]["governing_value"],
        LOWER_IS_SEVERE,
    )

    findings = []
    duties = []
    if gaps:
        findings.append(
            "the equipment-level set does not envelope the material-level one on "
            "%s, so those parameters stay in the thermal test campaign rather "
            "than being covered by the equipment run" % ", ".join(gaps)
        )
    if credit["capped"]:
        findings.append(
            "the equipment-level run earned %d cycles of credit but the cap "
            "allows %d, so %d cycles still have to be run"
            % (credit["earned_before_cap"], credit["cap"], credit["remaining_cycles"])
        )
    if hot_margin < policy["min_hot_margin_k"] and not _close(
        hot_margin, policy["min_hot_margin_k"]
    ):
        findings.append(
            "the governing hot limit holds only %.2f K over the material-level "
            "value against a required %.2f K"
            % (hot_margin, policy["min_hot_margin_k"])
        )
    if cold_margin < policy["min_cold_margin_k"] and not _close(
        cold_margin, policy["min_cold_margin_k"]
    ):
        findings.append(
            "the governing cold limit holds only %.2f K below the material-level "
            "value against a required %.2f K"
            % (cold_margin, policy["min_cold_margin_k"])
        )
    duties.append(
        "name the governing document beside every reconciled parameter in the "
        "test specification, so a later change to either standard is traceable"
    )
    duties.append(
        "record the credit efficiency and the cap that produced the remaining "
        "cycle count, not just the remaining count"
    )
    return {
        "reconciled": reconciled,
        "envelope_gaps": gaps,
        "equipment_envelopes_material": not gaps,
        "credit": credit,
        "hot_margin_k": hot_margin,
        "cold_margin_k": cold_margin,
        "duties": duties,
        "findings": findings,
        "interface_clean": not findings,
    }
