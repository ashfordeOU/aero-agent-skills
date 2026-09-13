#!/usr/bin/env python3
"""Shunt diode forward-voltage test on a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.3.7. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A shunt diode sits idle for the whole mission and then has to carry the
full string current the moment its section is shadowed or fails. There
is no way to see it working from the front: forward-biasing it means
driving the protected string backwards, pushing current in against the
cells so the diode -- not the cells -- takes the path.

What the drive produces is one number per diode:

    forward voltage   the drop across the diode while it carries the
                      forced current

and that number only means something with two things attached to it: the
current it was taken at, and the junction temperature it was taken at.

    drive current     has to reach the worst-case string current the
                      diode is there to carry; a gentle drive puts the
                      part at a knee it will never sit at in flight
    junction temp     a silicon forward drop falls as the junction warms,
                      so every reading is referred to a declared
                      reference temperature before it meets a window

Where the referred drop falls says what the part is:

    suspect-shorted    below the window; the junction is not developing a
                       drop, so the section it protects is being shunted
                       whenever it is lit
    conducting-nominal inside the window; the diode conducts as intended
    suspect-degraded   above the window; excess drop means added series
                       resistance, a damaged junction or the wrong part
    open-circuit       far above the window; the drive is being pushed
                       against a broken path and no diode is conducting

Summing the referred drops of a driven string and comparing that with the
voltage the supply actually had to develop catches a drop the diode
inventory does not explain -- a resisting interconnect in the reverse
path.

The window, the reference temperature, the coefficient and the
dissipation budget are declared project policy, not physical constants.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SHUNT_SHORTED = "suspect-shorted"
SHUNT_CONDUCTING = "conducting-nominal"
SHUNT_DEGRADED = "suspect-degraded"
SHUNT_OPEN = "open-circuit"

SHUNT_DIODE_CATEGORIES = (
    SHUNT_SHORTED,
    SHUNT_CONDUCTING,
    SHUNT_DEGRADED,
    SHUNT_OPEN,
)

SHUNT_DIODE_TEST_PASSED = "shunt-diode-test-passed"
SHUNT_DIODE_TEST_FAILED = "shunt-diode-test-failed"
SHUNT_DIODE_TEST_NOT_EVALUATED = "shunt-diode-test-not-evaluated"

# Declared acceptance policy: project numbers, not physical constants.
DEFAULT_SHUNT_DIODE_POLICY = {
    "min_forward_voltage_v": 0.45,
    "max_forward_voltage_v": 0.95,
    "open_circuit_threshold_v": 3.0,
    "reference_junction_temperature_c": 25.0,
    "forward_voltage_tempco_v_per_k": -0.002,
    "max_dissipation_w": 2.5,
    "max_unexplained_string_drop_v": 0.05,
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


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A referred drop is a difference of products and a window edge is a
    declared decimal, so a part meant to sit exactly on the edge can land
    a few units in the last place either side of it. The window is never
    widened; only the comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_shunt_diode_policy(policy):
    """Check an acceptance policy carries sane numbers before it is used."""
    _require_mapping("policy", policy)
    low = _require_positive("min_forward_voltage_v", policy.get("min_forward_voltage_v"))
    high = _require_positive(
        "max_forward_voltage_v", policy.get("max_forward_voltage_v")
    )
    if high <= low:
        raise ValueError("max_forward_voltage_v must exceed min_forward_voltage_v")
    open_threshold = _require_positive(
        "open_circuit_threshold_v", policy.get("open_circuit_threshold_v")
    )
    if open_threshold <= high:
        raise ValueError("open_circuit_threshold_v must exceed max_forward_voltage_v")
    _require_number(
        "reference_junction_temperature_c",
        policy.get("reference_junction_temperature_c"),
    )
    tempco = _require_number(
        "forward_voltage_tempco_v_per_k", policy.get("forward_voltage_tempco_v_per_k")
    )
    if tempco >= 0.0:
        raise ValueError(
            "forward_voltage_tempco_v_per_k must be negative, got %r" % (tempco,)
        )
    _require_positive("max_dissipation_w", policy.get("max_dissipation_w"))
    _require_non_negative(
        "max_unexplained_string_drop_v", policy.get("max_unexplained_string_drop_v")
    )
    return policy


def normalize_forward_voltage_v(
    measured_forward_voltage_v,
    measured_junction_temperature_c,
    reference_junction_temperature_c,
    tempco_v_per_k,
):
    """Refer a measured forward drop to the reference junction temperature.

    The drop falls as the junction warms, so a reading taken on a warm
    part is lifted back to the reference and a reading taken on a cold
    part is brought down. A non-negative coefficient is rejected rather
    than used, because it reverses the correction and turns a hot
    marginal part into an apparently healthy one.
    """
    measured = _require_positive(
        "measured_forward_voltage_v", measured_forward_voltage_v
    )
    t_meas = _require_number(
        "measured_junction_temperature_c", measured_junction_temperature_c
    )
    t_ref = _require_number(
        "reference_junction_temperature_c", reference_junction_temperature_c
    )
    tempco = _require_number("tempco_v_per_k", tempco_v_per_k)
    if tempco >= 0.0:
        raise ValueError("tempco_v_per_k must be negative, got %r" % (tempco,))
    return measured - tempco * (t_meas - t_ref)


def reverse_drive_adequacy(applied_drive_current_a, worst_case_string_current_a):
    """Did the drive reach the current the diode is there to carry?

    A drive below the worst-case string current parks the junction at a
    knee it will never occupy in flight, so the drop it produced is not
    evidence about the protected case and the campaign is reported as not
    evaluated rather than as a pass.
    """
    applied = _require_positive(
        "applied_drive_current_a", applied_drive_current_a
    )
    required = _require_positive(
        "worst_case_string_current_a", worst_case_string_current_a
    )
    adequate = _at_least(applied, required)
    findings = []
    if not adequate:
        findings.append(
            "reverse drive %.4f A is below the worst-case string current %.4f A, "
            "so the forward drops measured do not cover the protected case"
            % (applied, required)
        )
    return {
        "adequate": adequate,
        "applied_drive_current_a": applied,
        "worst_case_string_current_a": required,
        "shortfall_a": max(0.0, required - applied),
        "coverage_ratio": applied / required,
        "findings": findings,
    }


def categorize_shunt_diode(
    normalized_forward_voltage_v, policy=DEFAULT_SHUNT_DIODE_POLICY
):
    """Group one referred forward drop against the declared window."""
    validate_shunt_diode_policy(policy)
    value = _require_non_negative(
        "normalized_forward_voltage_v", normalized_forward_voltage_v
    )
    if not _at_least(value, float(policy["min_forward_voltage_v"])):
        return SHUNT_SHORTED
    if _at_most(value, float(policy["max_forward_voltage_v"])):
        return SHUNT_CONDUCTING
    if not _at_least(value, float(policy["open_circuit_threshold_v"])):
        return SHUNT_DEGRADED
    return SHUNT_OPEN


def diode_dissipation_w(forward_voltage_v, drive_current_a):
    """Power the diode carries while it conducts the forced current."""
    voltage = _require_positive("forward_voltage_v", forward_voltage_v)
    current = _require_positive("drive_current_a", drive_current_a)
    return voltage * current


def evaluate_shunt_diode(diode, drive_current_a, policy=DEFAULT_SHUNT_DIODE_POLICY):
    """Reduce one diode record to a referred drop, a grouping and a load."""
    validate_shunt_diode_policy(policy)
    _require_mapping("diode", diode)
    current = _require_positive("drive_current_a", drive_current_a)
    measured = _require_positive(
        "forward_voltage_v", diode.get("forward_voltage_v")
    )
    junction = _require_number(
        "junction_temperature_c", diode.get("junction_temperature_c")
    )
    normalized = normalize_forward_voltage_v(
        measured,
        junction,
        float(policy["reference_junction_temperature_c"]),
        float(policy["forward_voltage_tempco_v_per_k"]),
    )
    category = categorize_shunt_diode(normalized, policy)
    dissipation = diode_dissipation_w(measured, current)

    findings = []
    if category == SHUNT_SHORTED:
        findings.append(
            "diode %r drops only %.4f V referred; the junction is not developing "
            "a forward drop and the protected section is shunted while lit"
            % (diode.get("id"), normalized)
        )
    elif category == SHUNT_DEGRADED:
        findings.append(
            "diode %r drops %.4f V referred, above the window; added series "
            "resistance, a damaged junction or the wrong part"
            % (diode.get("id"), normalized)
        )
    elif category == SHUNT_OPEN:
        findings.append(
            "diode %r shows %.4f V referred; the reverse drive is being pushed "
            "against a broken path and no diode is conducting"
            % (diode.get("id"), normalized)
        )
    if not _at_most(dissipation, float(policy["max_dissipation_w"])):
        findings.append(
            "diode %r carries %.4f W at the drive current, above the allowed "
            "%.4f W" % (diode.get("id"), dissipation, float(policy["max_dissipation_w"]))
        )

    return {
        "id": diode.get("id"),
        "forward_voltage_v": measured,
        "junction_temperature_c": junction,
        "normalized_forward_voltage_v": normalized,
        "category": category,
        "dissipation_w": dissipation,
        "within_dissipation_budget": _at_most(
            dissipation, float(policy["max_dissipation_w"])
        ),
        "acceptable": category == SHUNT_CONDUCTING
        and _at_most(dissipation, float(policy["max_dissipation_w"])),
        "findings": findings,
    }


def unexplained_string_drop_v(measured_string_voltage_v, diode_voltages_v):
    """Drop the driven string developed that the diodes do not account for."""
    measured = _require_positive(
        "measured_string_voltage_v", measured_string_voltage_v
    )
    if not isinstance(diode_voltages_v, (list, tuple)) or not diode_voltages_v:
        raise ValueError(
            "diode_voltages_v must be a non-empty sequence, got %r"
            % (diode_voltages_v,)
        )
    total = sum(
        _require_positive("forward_voltage_v", value) for value in diode_voltages_v
    )
    return measured - total


def evaluate_shunt_diode_test(campaign, policy=DEFAULT_SHUNT_DIODE_POLICY):
    """Full clause 5.5.3.3.7 shunt diode assessment with a verdict."""
    validate_shunt_diode_policy(policy)
    _require_mapping("campaign", campaign)
    flight_case = _require_mapping("flight_case", campaign.get("flight_case"))
    diodes = campaign.get("diodes")
    if not isinstance(diodes, (list, tuple)) or not diodes:
        raise ValueError("campaign must carry a non-empty diodes sequence")

    adequacy = reverse_drive_adequacy(
        campaign.get("applied_drive_current_a"),
        flight_case.get("worst_case_string_current_a"),
    )
    evaluated = [
        evaluate_shunt_diode(diode, adequacy["applied_drive_current_a"], policy)
        for diode in diodes
    ]

    findings = list(adequacy["findings"])
    for record in evaluated:
        findings.extend(record["findings"])

    result = {
        "applied_drive_current_a": adequacy["applied_drive_current_a"],
        "worst_case_string_current_a": adequacy["worst_case_string_current_a"],
        "drive_adequate": adequacy["adequate"],
        "drive_shortfall_a": adequacy["shortfall_a"],
        "diodes": evaluated,
        "total_dissipation_w": sum(record["dissipation_w"] for record in evaluated),
        "unexplained_string_drop_v": None,
        "findings": findings,
    }

    if not adequacy["adequate"]:
        result.update(
            {
                "compliant": None,
                "verdict": SHUNT_DIODE_TEST_NOT_EVALUATED,
                "rejected_diode_ids": [],
            }
        )
        findings.append(
            "the drive never reached the protected case, so the string is driven "
            "again at the worst-case current before any diode is sentenced"
        )
        return result

    reasons = []
    rejected = [record["id"] for record in evaluated if not record["acceptable"]]
    if rejected:
        reasons.append(
            "%d shunt diode(s) outside the conducting window or the dissipation "
            "budget: %s" % (len(rejected), ", ".join(repr(item) for item in rejected))
        )

    measured_string = campaign.get("measured_string_reverse_voltage_v")
    if measured_string is not None:
        residual = unexplained_string_drop_v(
            measured_string, [record["forward_voltage_v"] for record in evaluated]
        )
        result["unexplained_string_drop_v"] = residual
        if not _at_most(
            abs(residual), float(policy["max_unexplained_string_drop_v"])
        ):
            reasons.append(
                "the driven string developed %.4f V that the diode drops do not "
                "explain; the reverse path carries a resisting joint" % (residual,)
            )

    compliant = not reasons
    findings.extend(reasons)
    result.update(
        {
            "compliant": compliant,
            "rejected_diode_ids": rejected,
            "verdict": SHUNT_DIODE_TEST_PASSED
            if compliant
            else SHUNT_DIODE_TEST_FAILED,
        }
    )
    return result
