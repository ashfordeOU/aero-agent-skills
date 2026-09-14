#!/usr/bin/env python3
"""High voltage applications of parts bought at the intermediate class.

Anchor: ECSS-Q-ST-60-13C clause 5.6.7. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause constrains how a commercial part may be used where the
voltage across it is high. A high voltage application is not a hotter
version of an ordinary one: the failure arrives through the gas and the
surface around the part rather than through the die inside it, and it
arrives during the ascent rather than on orbit.

Four things are computed rather than asserted. The voltage derating is
the applied voltage as a fraction of the part rating, and it is the only
one of the four that concerns the part itself. The required creepage and
clearance follow from the applied voltage and the field limits the
programme works to, and they are compared against the distances the
layout actually provides. The gas breakdown voltage follows a Townsend
form of the Paschen relation at the pressure-times-gap the assembly sees,
and the margin is that breakdown voltage over the applied voltage.

The ascent is the case that decides it. An assembly energised while the
pressure falls sweeps the whole Paschen curve, including its minimum,
so the governing breakdown voltage for a powered ascent is the minimum
of the curve rather than the value at the operating pressure. An assembly
that stays unpowered until the pressure has fallen never visits the
minimum, and is judged at the pressure it actually operates at. That one
declaration moves the verdict more than any distance on the layout.

Below the Paschen minimum there is no gas breakdown to sustain: too few
molecules sit in the gap to build an avalanche. The relation is reported
as unbounded there rather than extrapolated, because an extrapolated
Townsend expression on the vacuum side of the minimum returns a number
that looks like an answer and is not one.

The evidence list is scored rather than ticked. A subject may be carried
by analysis rather than by measurement at this class, which the class
above does not allow, and analysis is credited below a measured record so
that an application argued entirely on paper cannot read as a measured
one.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

HIGH_VOLTAGE_DESIGN_REVIEW_RECORD = "high-voltage-design-review-record"
PARTIAL_DISCHARGE_INCEPTION_MEASUREMENT = "partial-discharge-inception-measurement"
INSULATION_MATERIAL_OUTGASSING_DATA = "insulation-material-outgassing-data"
VENTING_AND_DEPRESSURISATION_ANALYSIS = "venting-and-depressurisation-analysis"
HIGH_VOLTAGE_PART_DERATING_RECORD = "high-voltage-part-derating-record"
CREEPAGE_AND_CLEARANCE_SURVEY = "creepage-and-clearance-survey"

REQUIRED_EVIDENCE = (
    HIGH_VOLTAGE_DESIGN_REVIEW_RECORD,
    PARTIAL_DISCHARGE_INCEPTION_MEASUREMENT,
    INSULATION_MATERIAL_OUTGASSING_DATA,
    VENTING_AND_DEPRESSURISATION_ANALYSIS,
    HIGH_VOLTAGE_PART_DERATING_RECORD,
    CREEPAGE_AND_CLEARANCE_SURVEY,
)

HELD_AS_MEASURED = "held-as-a-measured-record"
HELD_AS_ANALYSIS = "held-as-an-analysis-without-measurement"
DECLARED_WITHOUT_RECORD = "declared-without-a-record"
ABSENT = "absent"

HELD_STATES = (HELD_AS_MEASURED, HELD_AS_ANALYSIS)

HV_APPLICATION_NOT_DECLARED = "high-voltage-application-not-declared"
HV_BELOW_THRESHOLD = "application-below-the-high-voltage-threshold"
HV_VOLTAGE_DERATING_EXCEEDED = "high-voltage-part-voltage-derating-exceeded"
HV_CREEPAGE_OR_CLEARANCE_SHORT = "high-voltage-creepage-or-clearance-short"
HV_PASCHEN_MARGIN_SHORT = "high-voltage-paschen-margin-short"
HV_EVIDENCE_SHORT = "high-voltage-evidence-short"
HV_MEETS_CLASS_TWO_SCOPE = "high-voltage-application-meets-class-two-scope"

DEFAULT_HV_POLICY = {
    "high_voltage_threshold_v": 100.0,
    "max_voltage_derating_fraction": 0.5,
    "creepage_field_limit_v_per_mm": 200.0,
    "clearance_field_limit_v_per_mm": 500.0,
    "min_paschen_margin_factor": 2.0,
    "min_evidence_share": 1.0,
    "min_weighted_evidence": 0.6,
    "analysis_credit": 0.7,
    "marginal_derating_band": 0.05,
    "allow_encapsulation_to_waive_paschen": True,
}

DEFAULT_GAS_MODEL = {
    "townsend_a_per_pa_m": 112.5,
    "townsend_b_v_per_pa_m": 2737.5,
    "secondary_emission_coefficient": 0.01,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
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


def validate_hv_policy(policy):
    """Check the high voltage policy is complete and usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "high_voltage_threshold_v", policy.get("high_voltage_threshold_v")
    )
    derating = _require_fraction(
        "max_voltage_derating_fraction", policy.get("max_voltage_derating_fraction")
    )
    if derating <= 0.0:
        raise ValueError(
            "max_voltage_derating_fraction must be greater than zero, got %r"
            % (derating,)
        )
    creepage_limit = _require_positive(
        "creepage_field_limit_v_per_mm", policy.get("creepage_field_limit_v_per_mm")
    )
    clearance_limit = _require_positive(
        "clearance_field_limit_v_per_mm", policy.get("clearance_field_limit_v_per_mm")
    )
    if creepage_limit > clearance_limit:
        raise ValueError(
            "creepage_field_limit_v_per_mm %g is above the clearance limit %g; a "
            "surface path withstands less field than an open gap, never more"
            % (creepage_limit, clearance_limit)
        )
    margin = _require_number(
        "min_paschen_margin_factor", policy.get("min_paschen_margin_factor")
    )
    if margin < 1.0:
        raise ValueError(
            "min_paschen_margin_factor %g would accept an applied voltage at or "
            "above the breakdown voltage" % (margin,)
        )
    share = _require_fraction("min_evidence_share", policy.get("min_evidence_share"))
    weighted = _require_fraction(
        "min_weighted_evidence", policy.get("min_weighted_evidence")
    )
    if weighted > share:
        raise ValueError(
            "min_weighted_evidence %g is above min_evidence_share %g; a credited "
            "figure can never exceed the plain one" % (weighted, share)
        )
    credit = _require_fraction("analysis_credit", policy.get("analysis_credit"))
    if credit <= 0.0:
        raise ValueError(
            "analysis_credit must be greater than zero, got %r" % (credit,)
        )
    _require_fraction("marginal_derating_band", policy.get("marginal_derating_band"))
    _require_flag(
        "allow_encapsulation_to_waive_paschen",
        policy.get("allow_encapsulation_to_waive_paschen"),
    )
    return policy


def validate_gas_model(model):
    """Check the Townsend constants the breakdown relation is built on."""
    if not isinstance(model, dict):
        raise ValueError("gas model must be a mapping, got %r" % (model,))
    _require_positive("townsend_a_per_pa_m", model.get("townsend_a_per_pa_m"))
    _require_positive("townsend_b_v_per_pa_m", model.get("townsend_b_v_per_pa_m"))
    gamma = _require_positive(
        "secondary_emission_coefficient",
        model.get("secondary_emission_coefficient"),
    )
    if gamma >= 1.0:
        raise ValueError(
            "secondary_emission_coefficient %g is not below one; every ion would "
            "release more than one electron" % (gamma,)
        )
    return model


def validate_hv_application(case):
    """Read the application identity, its voltages and its geometry."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    application = _require_label(
        "application_reference", case.get("application_reference", "")
    )
    part = _require_label("part_reference", case.get("part_reference", ""))
    applied = _require_positive("applied_voltage_v", case.get("applied_voltage_v"))
    rated = _require_positive("rated_voltage_v", case.get("rated_voltage_v"))
    creepage = _require_non_negative(
        "creepage_distance_mm", case.get("creepage_distance_mm")
    )
    clearance = _require_non_negative(
        "clearance_distance_mm", case.get("clearance_distance_mm")
    )
    if creepage < clearance:
        raise ValueError(
            "creepage_distance_mm %g is shorter than the clearance %g; the path "
            "over a surface cannot be shorter than the straight line"
            % (creepage, clearance)
        )
    pressure = _require_positive("gap_pressure_pa", case.get("gap_pressure_pa"))
    powered = _require_flag(
        "powered_during_depressurisation",
        case.get("powered_during_depressurisation", False),
    )
    encapsulated = _require_flag(
        "fully_encapsulated", case.get("fully_encapsulated", False)
    )
    return {
        "application_reference": application,
        "part_reference": part,
        "applied_voltage_v": applied,
        "rated_voltage_v": rated,
        "creepage_distance_mm": creepage,
        "clearance_distance_mm": clearance,
        "gap_pressure_pa": pressure,
        "powered_during_depressurisation": powered,
        "fully_encapsulated": encapsulated,
    }


def voltage_derating_fraction(case):
    """Applied voltage as a fraction of the part rating."""
    application = validate_hv_application(case)
    return application["applied_voltage_v"] / application["rated_voltage_v"]


def required_creepage_mm(case, policy=DEFAULT_HV_POLICY):
    """Surface path the applied voltage needs at the programme field limit."""
    validate_hv_policy(policy)
    application = validate_hv_application(case)
    return application["applied_voltage_v"] / float(
        policy["creepage_field_limit_v_per_mm"]
    )


def required_clearance_mm(case, policy=DEFAULT_HV_POLICY):
    """Open gap the applied voltage needs at the programme field limit."""
    validate_hv_policy(policy)
    application = validate_hv_application(case)
    return application["applied_voltage_v"] / float(
        policy["clearance_field_limit_v_per_mm"]
    )


def _log_gamma_term(model):
    gamma = float(model["secondary_emission_coefficient"])
    return math.log(math.log(1.0 + 1.0 / gamma))


def paschen_minimum_pressure_gap_pa_m(model=DEFAULT_GAS_MODEL):
    """Pressure-times-gap at which the breakdown voltage is least."""
    validate_gas_model(model)
    gamma = float(model["secondary_emission_coefficient"])
    return math.e * math.log(1.0 + 1.0 / gamma) / float(model["townsend_a_per_pa_m"])


def paschen_minimum_voltage_v(model=DEFAULT_GAS_MODEL):
    """Least breakdown voltage the gas sustains anywhere on the curve."""
    validate_gas_model(model)
    gamma = float(model["secondary_emission_coefficient"])
    ratio = float(model["townsend_b_v_per_pa_m"]) / float(
        model["townsend_a_per_pa_m"]
    )
    return math.e * ratio * math.log(1.0 + 1.0 / gamma)


def is_vacuum_regime(pressure_pa, gap_m, model=DEFAULT_GAS_MODEL):
    """True where too little gas sits in the gap to sustain an avalanche."""
    validate_gas_model(model)
    pressure = _require_positive("pressure_pa", pressure_pa)
    gap = _require_positive("gap_m", gap_m)
    product = float(model["townsend_a_per_pa_m"]) * pressure * gap
    return not _at_least(math.log(product), _log_gamma_term(model))


def paschen_breakdown_voltage_v(pressure_pa, gap_m, model=DEFAULT_GAS_MODEL):
    """Gas breakdown voltage at one pressure and gap.

    Returns positive infinity on the vacuum side of the Paschen minimum,
    where no gas breakdown is sustained, rather than extrapolating the
    Townsend expression into a number that looks like an answer.
    """
    validate_gas_model(model)
    pressure = _require_positive("pressure_pa", pressure_pa)
    gap = _require_positive("gap_m", gap_m)
    if is_vacuum_regime(pressure, gap, model):
        return math.inf
    product = pressure * gap
    denominator = (
        math.log(float(model["townsend_a_per_pa_m"]) * product)
        - _log_gamma_term(model)
    )
    if denominator <= 0.0:
        return math.inf
    return float(model["townsend_b_v_per_pa_m"]) * product / denominator


def governing_breakdown_voltage_v(case, model=DEFAULT_GAS_MODEL):
    """The breakdown voltage the application actually has to survive.

    A powered depressurisation sweeps the whole curve, so the minimum of
    the curve governs; an application that stays unpowered until the
    pressure has fallen is judged at the pressure it operates at.
    """
    validate_gas_model(model)
    application = validate_hv_application(case)
    if application["powered_during_depressurisation"]:
        return paschen_minimum_voltage_v(model)
    gap_m = application["clearance_distance_mm"] / 1000.0
    if gap_m <= 0.0:
        raise ValueError(
            "a gas gap of zero cannot be assessed against the Paschen relation; "
            "declare the clearance the layout provides"
        )
    return paschen_breakdown_voltage_v(
        application["gap_pressure_pa"], gap_m, model
    )


def paschen_margin_factor(case, model=DEFAULT_GAS_MODEL):
    """Governing breakdown voltage over the applied voltage."""
    application = validate_hv_application(case)
    return (
        governing_breakdown_voltage_v(case, model)
        / application["applied_voltage_v"]
    )


def validate_evidence_record(entry):
    """Read one declared high voltage evidence item."""
    if not isinstance(entry, dict):
        raise ValueError("evidence entry must be a mapping, got %r" % (entry,))
    subject = _require_label("subject", entry.get("subject"))
    if subject not in REQUIRED_EVIDENCE:
        raise ValueError(
            "unrecognised evidence subject %r; the subject names are fixed"
            % (subject,)
        )
    by_analysis = _require_flag(
        "held_by_analysis on %s" % subject, entry.get("held_by_analysis", False)
    )
    record = _require_label(
        "record_reference on %s" % subject, entry.get("record_reference", "")
    )
    analysis = _require_label(
        "analysis_reference on %s" % subject, entry.get("analysis_reference", "")
    )
    if by_analysis and record:
        raise ValueError(
            "%s is declared both as a measured record and as an analysis; it is "
            "one or the other" % subject
        )
    return {
        "subject": subject,
        "held_by_analysis": by_analysis,
        "record_reference": record,
        "analysis_reference": analysis,
    }


def validate_evidence(records):
    """Read every declared evidence item, refusing an empty or repeated set."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("evidence must be a sequence of evidence records")
    if not records:
        raise ValueError("no high voltage evidence is declared")
    checked = []
    seen = set()
    for entry in records:
        item = validate_evidence_record(entry)
        if item["subject"] in seen:
            raise ValueError("evidence subject %r is declared twice" % item["subject"])
        seen.add(item["subject"])
        checked.append(item)
    return tuple(checked)


def evidence_disposition(records, policy=DEFAULT_HV_POLICY):
    """How each required evidence subject is held, with its credit."""
    validate_hv_policy(policy)
    checked = validate_evidence(records)
    credit = float(policy["analysis_credit"])
    declared = {item["subject"]: item for item in checked}
    disposition = {}
    for subject in REQUIRED_EVIDENCE:
        item = declared.get(subject)
        if item is None:
            disposition[subject] = {"state": ABSENT, "credit": 0.0}
            continue
        if item["held_by_analysis"]:
            if item["analysis_reference"]:
                disposition[subject] = {"state": HELD_AS_ANALYSIS, "credit": credit}
            else:
                disposition[subject] = {"state": DECLARED_WITHOUT_RECORD, "credit": 0.0}
            continue
        if item["record_reference"]:
            disposition[subject] = {"state": HELD_AS_MEASURED, "credit": 1.0}
        else:
            disposition[subject] = {"state": DECLARED_WITHOUT_RECORD, "credit": 0.0}
    return disposition


def _evidence_in_state(records, states, policy):
    disposition = evidence_disposition(records, policy)
    return tuple(
        subject
        for subject in REQUIRED_EVIDENCE
        if disposition[subject]["state"] in states
    )


def held_evidence(records, policy=DEFAULT_HV_POLICY):
    """Required subjects the application actually holds."""
    return _evidence_in_state(records, HELD_STATES, policy)


def absent_evidence(records, policy=DEFAULT_HV_POLICY):
    """Required subjects the application does not declare at all."""
    return _evidence_in_state(records, (ABSENT,), policy)


def unrecorded_evidence(records, policy=DEFAULT_HV_POLICY):
    """Subjects declared with neither a measurement nor a named analysis."""
    return _evidence_in_state(records, (DECLARED_WITHOUT_RECORD,), policy)


def analysis_evidence(records, policy=DEFAULT_HV_POLICY):
    """Subjects carried by analysis rather than by measurement."""
    return _evidence_in_state(records, (HELD_AS_ANALYSIS,), policy)


def evidence_share(records, policy=DEFAULT_HV_POLICY):
    """Share of the required subjects the application holds."""
    return len(held_evidence(records, policy)) / len(REQUIRED_EVIDENCE)


def weighted_evidence(records, policy=DEFAULT_HV_POLICY):
    """Credited evidence over the full required subject list."""
    disposition = evidence_disposition(records, policy)
    total = 0.0
    for subject in REQUIRED_EVIDENCE:
        total += disposition[subject]["credit"]
    return total / len(REQUIRED_EVIDENCE)


def derating_advisories(case, policy=DEFAULT_HV_POLICY):
    """Name a voltage derating sitting just under the cap.

    These do not move the verdict -- a derating under the cap is under the
    cap -- but an application a hair under and one at half the cap carry
    the same word, and nobody recovers the difference later from the word
    alone.
    """
    validate_hv_policy(policy)
    fraction = voltage_derating_fraction(case)
    cap = float(policy["max_voltage_derating_fraction"])
    band = float(policy["marginal_derating_band"])
    advisories = []
    if _at_most(fraction, cap) and _at_most(cap - fraction, band):
        advisories.append(
            "the applied voltage sits at %.4g of the part rating, inside the "
            "%.4g marginal band under the %.4g cap; the application holds today "
            "and is the one a bus transient would take out first"
            % (fraction, band, cap)
        )
    return tuple(advisories)


def assess_high_voltage_application(
    case, policy=DEFAULT_HV_POLICY, model=DEFAULT_GAS_MODEL
):
    """Full clause 5.6.7 application decision for one high voltage use."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_hv_policy(policy)
    validate_gas_model(model)

    findings = []
    advisories = []
    result = {
        "application_reference": None,
        "part_reference": None,
        "voltage_derating_fraction": None,
        "required_creepage_mm": None,
        "required_clearance_mm": None,
        "governing_breakdown_voltage_v": None,
        "paschen_margin_factor": None,
        "paschen_waived_by_encapsulation": False,
        "evidence_share": None,
        "weighted_evidence": None,
        "absent_evidence": (),
        "unrecorded_evidence": (),
        "analysis_evidence": (),
        "findings": findings,
        "advisories": advisories,
    }

    application = validate_hv_application(case)
    result["application_reference"] = application["application_reference"]
    result["part_reference"] = application["part_reference"]
    if not application["application_reference"] or not application["part_reference"]:
        findings.append(
            "the application carries no reference or names no part, so nothing "
            "about the voltage across it can be argued"
        )
        result["verdict"] = HV_APPLICATION_NOT_DECLARED
        return result

    threshold = float(policy["high_voltage_threshold_v"])
    if not _at_least(application["applied_voltage_v"], threshold):
        advisories.append(
            "the applied voltage of %.4g V sits under the %.4g V high voltage "
            "threshold, so this clause does not constrain the application; the "
            "ordinary derating rules still do"
            % (application["applied_voltage_v"], threshold)
        )
        result["verdict"] = HV_BELOW_THRESHOLD
        return result

    fraction = voltage_derating_fraction(case)
    creepage_needed = required_creepage_mm(case, policy)
    clearance_needed = required_clearance_mm(case, policy)
    result["voltage_derating_fraction"] = fraction
    result["required_creepage_mm"] = creepage_needed
    result["required_clearance_mm"] = clearance_needed
    advisories.extend(derating_advisories(case, policy))

    if not _at_most(fraction, float(policy["max_voltage_derating_fraction"])):
        findings.append(
            "the applied voltage sits at %.4g of the part rating against the "
            "%.4g the class allows in a high voltage application"
            % (fraction, float(policy["max_voltage_derating_fraction"]))
        )
        result["verdict"] = HV_VOLTAGE_DERATING_EXCEEDED
        return result

    creepage_short = not _at_least(
        application["creepage_distance_mm"], creepage_needed
    )
    clearance_short = not _at_least(
        application["clearance_distance_mm"], clearance_needed
    )
    if creepage_short:
        findings.append(
            "the layout provides %.4g mm of creepage against the %.4g mm the "
            "applied voltage needs at the programme field limit"
            % (application["creepage_distance_mm"], creepage_needed)
        )
    if clearance_short:
        findings.append(
            "the layout provides %.4g mm of clearance against the %.4g mm the "
            "applied voltage needs at the programme field limit"
            % (application["clearance_distance_mm"], clearance_needed)
        )
    if creepage_short or clearance_short:
        result["verdict"] = HV_CREEPAGE_OR_CLEARANCE_SHORT
        return result

    if (
        application["fully_encapsulated"]
        and policy["allow_encapsulation_to_waive_paschen"]
    ):
        result["paschen_waived_by_encapsulation"] = True
        advisories.append(
            "the high voltage path is declared fully encapsulated, so the gas "
            "breakdown check is waived and the partial discharge measurement "
            "carries the void risk in its place"
        )
    else:
        breakdown = governing_breakdown_voltage_v(case, model)
        margin = paschen_margin_factor(case, model)
        result["governing_breakdown_voltage_v"] = breakdown
        result["paschen_margin_factor"] = margin
        if not _at_least(margin, float(policy["min_paschen_margin_factor"])):
            findings.append(
                "the governing gas breakdown voltage is %.5g V against an "
                "applied %.5g V, a margin of %.4g against the %.4g the class "
                "asks for%s"
                % (
                    breakdown,
                    application["applied_voltage_v"],
                    margin,
                    float(policy["min_paschen_margin_factor"]),
                    "; the assembly is powered while the pressure falls, so the "
                    "minimum of the curve governs"
                    if application["powered_during_depressurisation"]
                    else "",
                )
            )
            result["verdict"] = HV_PASCHEN_MARGIN_SHORT
            return result

    records = case.get("evidence")
    if records is None:
        findings.append(
            "no high voltage evidence is declared, so neither the discharge "
            "behaviour nor the venting of this assembly has been shown"
        )
        result["verdict"] = HV_EVIDENCE_SHORT
        return result

    evidence = validate_evidence(records)
    share = evidence_share(evidence, policy)
    weighted = weighted_evidence(evidence, policy)
    absent = absent_evidence(evidence, policy)
    unrecorded = unrecorded_evidence(evidence, policy)
    analysed = analysis_evidence(evidence, policy)
    result["evidence_share"] = share
    result["weighted_evidence"] = weighted
    result["absent_evidence"] = absent
    result["unrecorded_evidence"] = unrecorded
    result["analysis_evidence"] = analysed

    for subject in absent:
        findings.append("the application does not declare %s at all" % subject)
    for subject in unrecorded:
        findings.append(
            "%s is declared with neither a measured record nor a named analysis "
            "behind it" % subject
        )

    share_short = not _at_least(share, float(policy["min_evidence_share"]))
    weighted_short = not _at_least(weighted, float(policy["min_weighted_evidence"]))
    if share_short or weighted_short:
        findings.append(
            "the application holds %.4g of the required subjects against %.4g, "
            "at a credited %.4g against %.4g"
            % (
                share,
                float(policy["min_evidence_share"]),
                weighted,
                float(policy["min_weighted_evidence"]),
            )
        )
        result["verdict"] = HV_EVIDENCE_SHORT
        return result

    result["verdict"] = HV_MEETS_CLASS_TWO_SCOPE
    return result
