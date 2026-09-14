#!/usr/bin/env python3
"""High voltage and high power usage at the lowest assurance class.

Anchor: ECSS-Q-ST-60-13C clause 6.6.7. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause covers a commercial part put somewhere the voltage across it
is high, somewhere the power through it is high, or both. The two axes
are separate and they fail differently. The voltage axis fails in the
insulation around the part: a surface tracks, a gap breaks down, a void
in a coating starts discharging long before anything conducts. The power
axis fails inside the part: the die runs hotter than the package can
carry it away, and the case temperature everyone quotes is the number
furthest from the one that matters.

Nothing here is asserted. Five quantities are computed. The voltage
utilization is the applied voltage over the part rating. The required
insulation spacing follows from the applied voltage and a field limit,
and is compared with the path the layout actually gives. The discharge
margin is the inception voltage over the peak working voltage, peak
rather than mean because discharge does not average. The allowed
dissipation is the part rating derated for the class and derated again
along the package's own temperature curve, because a part at its onset
temperature and a part near its maximum case temperature are not the
same part. The junction temperature is the case temperature plus the
dissipation through the thermal resistance, and it is checked against
the junction rating less a declared margin rather than against the
rating itself.

Which checks run is decided by the thresholds rather than by habit. An
application under both thresholds is not partly assessed, it is outside
this clause, and saying so is a result rather than a gap. An application
over the power threshold but under the voltage threshold is not asked
for a creepage path it has no need of.

The evidence list is scored rather than ticked, and at this class it has
three tiers instead of two. A subject may be carried by a measurement,
by an analysis, or by a supplier's own declaration, and each is credited
below the one before it so that an application argued entirely on what a
datasheet claims cannot read as a measured one.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

HIGH_VOLTAGE_AXIS = "high-voltage-axis"
HIGH_POWER_AXIS = "high-power-axis"

HIGH_VOLTAGE_DIELECTRIC_WITHSTAND_RECORD = "high-voltage-dielectric-withstand-record"
PARTIAL_DISCHARGE_INCEPTION_RECORD = "partial-discharge-inception-record"
HIGH_POWER_THERMAL_SURVEY_RECORD = "high-power-thermal-survey-record"
INSULATION_SPACING_LAYOUT_RECORD = "insulation-spacing-layout-record"
VOLTAGE_AND_POWER_DERATING_ANALYSIS = "voltage-and-power-derating-analysis"
CONFORMAL_COATING_AND_VENTING_RECORD = "conformal-coating-and-venting-record"

REQUIRED_APPLICATION_EVIDENCE = (
    HIGH_VOLTAGE_DIELECTRIC_WITHSTAND_RECORD,
    PARTIAL_DISCHARGE_INCEPTION_RECORD,
    HIGH_POWER_THERMAL_SURVEY_RECORD,
    INSULATION_SPACING_LAYOUT_RECORD,
    VOLTAGE_AND_POWER_DERATING_ANALYSIS,
    CONFORMAL_COATING_AND_VENTING_RECORD,
)

HELD_AS_A_MEASUREMENT = "held-as-a-measurement"
HELD_AS_AN_ANALYSIS = "held-as-an-analysis"
HELD_AS_A_SUPPLIER_DECLARATION = "held-as-a-supplier-declaration"
DECLARED_WITHOUT_A_RECORD = "declared-without-a-record"
ABSENT = "absent"

HELD_STATES = (
    HELD_AS_A_MEASUREMENT,
    HELD_AS_AN_ANALYSIS,
    HELD_AS_A_SUPPLIER_DECLARATION,
)

APPLICATION_NOT_DECLARED = "high-voltage-application-not-declared"
BELOW_BOTH_THRESHOLDS = "below-the-high-voltage-and-high-power-thresholds"
VOLTAGE_DERATING_EXCEEDED = "high-voltage-part-voltage-derating-exceeded"
INSULATION_SPACING_SHORT = "high-voltage-insulation-spacing-short"
DISCHARGE_MARGIN_SHORT = "partial-discharge-inception-margin-short"
POWER_DERATING_EXCEEDED = "high-power-part-power-derating-exceeded"
JUNCTION_TEMPERATURE_EXCEEDED = "high-power-part-junction-temperature-exceeded"
APPLICATION_EVIDENCE_SHORT = "high-voltage-application-evidence-short"
MEETS_CLASS_THREE_SCOPE = "high-voltage-application-meets-class-three-scope"

DEFAULT_APPLICATION_POLICY = {
    "high_voltage_threshold_v": 50.0,
    "high_power_threshold_w": 5.0,
    "max_voltage_utilization": 0.75,
    "power_derating_factor": 0.7,
    "creepage_field_limit_v_per_mm": 200.0,
    "min_discharge_margin": 1.3,
    "junction_temperature_margin_c": 10.0,
    "analysis_credit": 0.6,
    "supplier_declaration_credit": 0.35,
    "min_evidence_share": 0.8,
    "min_weighted_evidence": 0.5,
    "marginal_utilization_band": 0.05,
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


def validate_application_policy(policy):
    """Check the high voltage and high power policy is complete and usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "high_voltage_threshold_v", policy.get("high_voltage_threshold_v")
    )
    _require_positive("high_power_threshold_w", policy.get("high_power_threshold_w"))
    utilization = _require_fraction(
        "max_voltage_utilization", policy.get("max_voltage_utilization")
    )
    if utilization <= 0.0:
        raise ValueError(
            "max_voltage_utilization must be greater than zero, got %r"
            % (utilization,)
        )
    power = _require_fraction(
        "power_derating_factor", policy.get("power_derating_factor")
    )
    if power <= 0.0:
        raise ValueError(
            "power_derating_factor must be greater than zero, got %r" % (power,)
        )
    _require_positive(
        "creepage_field_limit_v_per_mm",
        policy.get("creepage_field_limit_v_per_mm"),
    )
    margin = _require_number(
        "min_discharge_margin", policy.get("min_discharge_margin")
    )
    if margin < 1.0:
        raise ValueError(
            "min_discharge_margin %g is below one; a discharge starting at the "
            "working voltage is not a margin" % (margin,)
        )
    _require_non_negative(
        "junction_temperature_margin_c",
        policy.get("junction_temperature_margin_c"),
    )
    analysis = _require_fraction("analysis_credit", policy.get("analysis_credit"))
    if analysis <= 0.0:
        raise ValueError(
            "analysis_credit must be greater than zero, got %r" % (analysis,)
        )
    if analysis >= 1.0:
        raise ValueError(
            "analysis_credit %g would make an analysis the equal of a measurement"
            % (analysis,)
        )
    declaration = _require_fraction(
        "supplier_declaration_credit", policy.get("supplier_declaration_credit")
    )
    if declaration <= 0.0:
        raise ValueError(
            "supplier_declaration_credit must be greater than zero, got %r"
            % (declaration,)
        )
    if declaration >= analysis:
        raise ValueError(
            "supplier_declaration_credit %g is at or above analysis_credit %g; a "
            "declaration can never be worth more than an analysis of this build"
            % (declaration, analysis)
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
    _require_fraction(
        "marginal_utilization_band", policy.get("marginal_utilization_band")
    )
    return policy


def validate_application(case):
    """Read the declared application, its ratings and its layout."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    reference = _require_label(
        "application_reference", case.get("application_reference", "")
    )
    part = _require_label("part_reference", case.get("part_reference", ""))
    applied = _require_positive("applied_voltage_v", case.get("applied_voltage_v"))
    rated_voltage = _require_positive(
        "rated_voltage_v", case.get("rated_voltage_v")
    )
    peak_factor = _require_number("peak_factor", case.get("peak_factor"))
    if peak_factor < 1.0:
        raise ValueError(
            "peak_factor %g is below one; the peak of a working waveform is never "
            "under its own working value" % (peak_factor,)
        )
    inception = _require_positive(
        "discharge_inception_voltage_v", case.get("discharge_inception_voltage_v")
    )
    creepage = _require_positive("creepage_path_mm", case.get("creepage_path_mm"))
    dissipated = _require_non_negative(
        "dissipated_power_w", case.get("dissipated_power_w")
    )
    rated_power = _require_positive("rated_power_w", case.get("rated_power_w"))
    onset = _require_number(
        "derating_onset_temperature_c", case.get("derating_onset_temperature_c")
    )
    max_case = _require_number(
        "max_case_temperature_c", case.get("max_case_temperature_c")
    )
    if max_case <= onset:
        raise ValueError(
            "max_case_temperature_c %g is at or below derating_onset_temperature_c "
            "%g; the derating curve would have no run" % (max_case, onset)
        )
    case_temperature = _require_number(
        "case_temperature_c", case.get("case_temperature_c")
    )
    resistance = _require_positive(
        "thermal_resistance_c_per_w", case.get("thermal_resistance_c_per_w")
    )
    max_junction = _require_number(
        "max_junction_temperature_c", case.get("max_junction_temperature_c")
    )
    if max_junction < max_case:
        raise ValueError(
            "max_junction_temperature_c %g is below max_case_temperature_c %g; the "
            "die cannot be rated cooler than the package around it"
            % (max_junction, max_case)
        )
    return {
        "application_reference": reference,
        "part_reference": part,
        "applied_voltage_v": applied,
        "rated_voltage_v": rated_voltage,
        "peak_factor": peak_factor,
        "discharge_inception_voltage_v": inception,
        "creepage_path_mm": creepage,
        "dissipated_power_w": dissipated,
        "rated_power_w": rated_power,
        "derating_onset_temperature_c": onset,
        "max_case_temperature_c": max_case,
        "case_temperature_c": case_temperature,
        "thermal_resistance_c_per_w": resistance,
        "max_junction_temperature_c": max_junction,
    }


def engaged_axes(case, policy=DEFAULT_APPLICATION_POLICY):
    """Which of the two axes the application actually crosses into."""
    validate_application_policy(policy)
    declared = validate_application(case)
    axes = []
    if _at_least(
        declared["applied_voltage_v"], float(policy["high_voltage_threshold_v"])
    ):
        axes.append(HIGH_VOLTAGE_AXIS)
    if _at_least(
        declared["dissipated_power_w"], float(policy["high_power_threshold_w"])
    ):
        axes.append(HIGH_POWER_AXIS)
    return tuple(axes)


def voltage_utilization(case):
    """Applied voltage as a share of the part's own voltage rating."""
    declared = validate_application(case)
    return declared["applied_voltage_v"] / declared["rated_voltage_v"]


def peak_working_voltage_v(case):
    """The peak the insulation actually sees, not the mean it is quoted at."""
    declared = validate_application(case)
    return declared["applied_voltage_v"] * declared["peak_factor"]


def required_creepage_mm(case, policy=DEFAULT_APPLICATION_POLICY):
    """Surface path the applied voltage demands at the declared field limit."""
    validate_application_policy(policy)
    declared = validate_application(case)
    return declared["applied_voltage_v"] / float(
        policy["creepage_field_limit_v_per_mm"]
    )


def discharge_margin(case):
    """Inception voltage over the peak the part works at."""
    declared = validate_application(case)
    return declared["discharge_inception_voltage_v"] / peak_working_voltage_v(case)


def thermal_derating_factor(case):
    """Where the case temperature sits on the package's own derating run.

    Full rating up to the onset temperature, falling linearly to nothing at
    the maximum case temperature, and clamped at both ends so a cold part is
    never credited above its rating and a hot one is never credited below
    zero.
    """
    declared = validate_application(case)
    onset = declared["derating_onset_temperature_c"]
    ceiling = declared["max_case_temperature_c"]
    case_temperature = declared["case_temperature_c"]
    if case_temperature <= onset:
        return 1.0
    if case_temperature >= ceiling:
        return 0.0
    return (ceiling - case_temperature) / (ceiling - onset)


def allowed_dissipation_w(case, policy=DEFAULT_APPLICATION_POLICY):
    """Dissipation the part may carry, derated for the class and the case."""
    validate_application_policy(policy)
    declared = validate_application(case)
    return (
        declared["rated_power_w"]
        * float(policy["power_derating_factor"])
        * thermal_derating_factor(case)
    )


def junction_temperature_c(case):
    """Case temperature plus the rise the dissipation drives through the package."""
    declared = validate_application(case)
    return (
        declared["case_temperature_c"]
        + declared["dissipated_power_w"] * declared["thermal_resistance_c_per_w"]
    )


def allowed_junction_temperature_c(case, policy=DEFAULT_APPLICATION_POLICY):
    """The junction rating less the margin the class holds back."""
    validate_application_policy(policy)
    declared = validate_application(case)
    return declared["max_junction_temperature_c"] - float(
        policy["junction_temperature_margin_c"]
    )


def validate_evidence_record(entry):
    """Read one declared application evidence item."""
    if not isinstance(entry, dict):
        raise ValueError("evidence entry must be a mapping, got %r" % (entry,))
    subject = _require_label("subject", entry.get("subject"))
    if subject not in REQUIRED_APPLICATION_EVIDENCE:
        raise ValueError(
            "unrecognised evidence subject %r; the subject names are fixed"
            % (subject,)
        )
    by_analysis = _require_flag(
        "held_as_analysis on %s" % subject, entry.get("held_as_analysis", False)
    )
    by_declaration = _require_flag(
        "held_as_supplier_declaration on %s" % subject,
        entry.get("held_as_supplier_declaration", False),
    )
    if by_analysis and by_declaration:
        raise ValueError(
            "%s is declared both as an analysis and as a supplier declaration; it "
            "is one or the other" % subject
        )
    record = _require_label(
        "record_reference on %s" % subject, entry.get("record_reference", "")
    )
    return {
        "subject": subject,
        "held_as_analysis": by_analysis,
        "held_as_supplier_declaration": by_declaration,
        "record_reference": record,
    }


def validate_evidence(records):
    """Read every declared evidence item, refusing an empty or repeated set."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("evidence must be a sequence of evidence records")
    if not records:
        raise ValueError("no application evidence is declared")
    checked = []
    seen = set()
    for entry in records:
        item = validate_evidence_record(entry)
        if item["subject"] in seen:
            raise ValueError("evidence subject %r is declared twice" % item["subject"])
        seen.add(item["subject"])
        checked.append(item)
    return tuple(checked)


def evidence_disposition(records, policy=DEFAULT_APPLICATION_POLICY):
    """How each required evidence subject is held, with its credit."""
    validate_application_policy(policy)
    checked = validate_evidence(records)
    analysis = float(policy["analysis_credit"])
    declaration = float(policy["supplier_declaration_credit"])
    declared = {item["subject"]: item for item in checked}
    disposition = {}
    for subject in REQUIRED_APPLICATION_EVIDENCE:
        item = declared.get(subject)
        if item is None:
            disposition[subject] = {"state": ABSENT, "credit": 0.0}
            continue
        if not item["record_reference"]:
            disposition[subject] = {"state": DECLARED_WITHOUT_A_RECORD, "credit": 0.0}
            continue
        if item["held_as_supplier_declaration"]:
            disposition[subject] = {
                "state": HELD_AS_A_SUPPLIER_DECLARATION,
                "credit": declaration,
            }
        elif item["held_as_analysis"]:
            disposition[subject] = {"state": HELD_AS_AN_ANALYSIS, "credit": analysis}
        else:
            disposition[subject] = {"state": HELD_AS_A_MEASUREMENT, "credit": 1.0}
    return disposition


def _evidence_in_state(records, states, policy):
    disposition = evidence_disposition(records, policy)
    return tuple(
        subject
        for subject in REQUIRED_APPLICATION_EVIDENCE
        if disposition[subject]["state"] in states
    )


def held_evidence(records, policy=DEFAULT_APPLICATION_POLICY):
    """Required subjects the application actually holds."""
    return _evidence_in_state(records, HELD_STATES, policy)


def measured_evidence(records, policy=DEFAULT_APPLICATION_POLICY):
    """Subjects carried by a measurement on this build."""
    return _evidence_in_state(records, (HELD_AS_A_MEASUREMENT,), policy)


def analysis_evidence(records, policy=DEFAULT_APPLICATION_POLICY):
    """Subjects carried by an analysis rather than a measurement."""
    return _evidence_in_state(records, (HELD_AS_AN_ANALYSIS,), policy)


def declaration_evidence(records, policy=DEFAULT_APPLICATION_POLICY):
    """Subjects carried on a supplier's own declaration."""
    return _evidence_in_state(records, (HELD_AS_A_SUPPLIER_DECLARATION,), policy)


def unrecorded_evidence(records, policy=DEFAULT_APPLICATION_POLICY):
    """Subjects declared with no reference behind them at all."""
    return _evidence_in_state(records, (DECLARED_WITHOUT_A_RECORD,), policy)


def absent_evidence(records, policy=DEFAULT_APPLICATION_POLICY):
    """Required subjects the application does not declare at all."""
    return _evidence_in_state(records, (ABSENT,), policy)


def evidence_share(records, policy=DEFAULT_APPLICATION_POLICY):
    """Share of the required subjects the application holds."""
    return len(held_evidence(records, policy)) / len(REQUIRED_APPLICATION_EVIDENCE)


def weighted_evidence(records, policy=DEFAULT_APPLICATION_POLICY):
    """Credited evidence over the full required subject list."""
    disposition = evidence_disposition(records, policy)
    total = 0.0
    for subject in REQUIRED_APPLICATION_EVIDENCE:
        total += disposition[subject]["credit"]
    return total / len(REQUIRED_APPLICATION_EVIDENCE)


def utilization_advisories(case, policy=DEFAULT_APPLICATION_POLICY):
    """Name an axis sitting just inside its limit rather than comfortably under.

    These do not move the verdict, but a part at nine tenths of its cap and
    one at half carry the same word, and nobody recovers the difference later
    from the word alone.
    """
    validate_application_policy(policy)
    axes = engaged_axes(case, policy)
    band = float(policy["marginal_utilization_band"])
    advisories = []
    if HIGH_VOLTAGE_AXIS in axes:
        cap = float(policy["max_voltage_utilization"])
        used = voltage_utilization(case)
        if _at_most(used, cap) and _at_most(cap - used, band * cap):
            advisories.append(
                "the part works at %.4g of its voltage rating against a %.4g cap, "
                "inside the marginal band; it is within the cap today and is the "
                "first thing a bus voltage increase would take out" % (used, cap)
            )
    if HIGH_POWER_AXIS in axes:
        allowed = allowed_dissipation_w(case, policy)
        used = validate_application(case)["dissipated_power_w"]
        if allowed > 0.0 and _at_most(used, allowed) and _at_most(
            allowed - used, band * allowed
        ):
            advisories.append(
                "the part dissipates %.4g W against a %.4g W allowance, inside the "
                "marginal band; it is within the allowance today and has nothing "
                "left for a hotter mounting" % (used, allowed)
            )
    return tuple(advisories)


def assess_high_voltage_application(case, policy=DEFAULT_APPLICATION_POLICY):
    """Full clause 6.6.7 application decision for one commercial part."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_application_policy(policy)

    findings = []
    advisories = []
    result = {
        "application_reference": None,
        "part_reference": None,
        "engaged_axes": (),
        "voltage_utilization": None,
        "peak_working_voltage_v": None,
        "required_creepage_mm": None,
        "discharge_margin": None,
        "thermal_derating_factor": None,
        "allowed_dissipation_w": None,
        "junction_temperature_c": None,
        "allowed_junction_temperature_c": None,
        "evidence_share": None,
        "weighted_evidence": None,
        "measured_evidence": (),
        "analysis_evidence": (),
        "declaration_evidence": (),
        "unrecorded_evidence": (),
        "absent_evidence": (),
        "findings": findings,
        "advisories": advisories,
    }

    declared = validate_application(case)
    result["application_reference"] = declared["application_reference"]
    result["part_reference"] = declared["part_reference"]
    if not declared["application_reference"] or not declared["part_reference"]:
        findings.append(
            "the application carries no reference or names no part, so no verdict "
            "taken here can be traced to the thing it was taken about"
        )
        result["verdict"] = APPLICATION_NOT_DECLARED
        return result

    axes = engaged_axes(case, policy)
    result["engaged_axes"] = axes
    if not axes:
        findings.append(
            "the application sits under both the high voltage and the high power "
            "threshold, so this clause does not constrain it; the ordinary "
            "derating rules still apply and this is not the assessment to run"
        )
        result["verdict"] = BELOW_BOTH_THRESHOLDS
        return result

    advisories.extend(utilization_advisories(case, policy))

    if HIGH_VOLTAGE_AXIS in axes:
        used = voltage_utilization(case)
        peak = peak_working_voltage_v(case)
        required = required_creepage_mm(case, policy)
        margin = discharge_margin(case)
        result["voltage_utilization"] = used
        result["peak_working_voltage_v"] = peak
        result["required_creepage_mm"] = required
        result["discharge_margin"] = margin

        if not _at_most(used, float(policy["max_voltage_utilization"])):
            findings.append(
                "the part works at %.4g of its voltage rating against the %.4g the "
                "class allows" % (used, float(policy["max_voltage_utilization"]))
            )
            result["verdict"] = VOLTAGE_DERATING_EXCEEDED
            return result

        if not _at_least(declared["creepage_path_mm"], required):
            findings.append(
                "the layout gives a %.4g mm surface path against the %.4g mm the "
                "applied voltage demands at the declared field limit, so the "
                "surface tracks before anything in the part conducts"
                % (declared["creepage_path_mm"], required)
            )
            result["verdict"] = INSULATION_SPACING_SHORT
            return result

        if not _at_least(margin, float(policy["min_discharge_margin"])):
            findings.append(
                "discharge starts at %.4g times the peak working voltage against "
                "the %.4g the class asks for, so the voids in the insulation are "
                "discharging inside the mission rather than outside it"
                % (margin, float(policy["min_discharge_margin"]))
            )
            result["verdict"] = DISCHARGE_MARGIN_SHORT
            return result

    if HIGH_POWER_AXIS in axes:
        factor = thermal_derating_factor(case)
        allowed = allowed_dissipation_w(case, policy)
        junction = junction_temperature_c(case)
        junction_cap = allowed_junction_temperature_c(case, policy)
        result["thermal_derating_factor"] = factor
        result["allowed_dissipation_w"] = allowed
        result["junction_temperature_c"] = junction
        result["allowed_junction_temperature_c"] = junction_cap

        if _at_least(
            declared["case_temperature_c"], declared["max_case_temperature_c"]
        ):
            findings.append(
                "the case runs at %.4g C against a %.4g C maximum, so the package "
                "is off the end of its own derating curve and carries no rated "
                "dissipation at all"
                % (
                    declared["case_temperature_c"],
                    declared["max_case_temperature_c"],
                )
            )
            result["verdict"] = POWER_DERATING_EXCEEDED
            return result

        if not _at_most(declared["dissipated_power_w"], allowed):
            findings.append(
                "the part dissipates %.4g W against the %.4g W it may carry once "
                "the class derating and the %.4g case derating are applied"
                % (declared["dissipated_power_w"], allowed, factor)
            )
            result["verdict"] = POWER_DERATING_EXCEEDED
            return result

        if not _at_most(junction, junction_cap):
            findings.append(
                "the junction reaches %.4g C against the %.4g C left once the "
                "class margin is held back from the junction rating"
                % (junction, junction_cap)
            )
            result["verdict"] = JUNCTION_TEMPERATURE_EXCEEDED
            return result

    records = case.get("evidence")
    if records is None:
        findings.append(
            "no application evidence is declared, so neither the insulation nor "
            "the thermal path has been shown to behave as the assessment assumed"
        )
        result["verdict"] = APPLICATION_EVIDENCE_SHORT
        return result

    evidence = validate_evidence(records)
    result["evidence_share"] = evidence_share(evidence, policy)
    result["weighted_evidence"] = weighted_evidence(evidence, policy)
    result["measured_evidence"] = measured_evidence(evidence, policy)
    result["analysis_evidence"] = analysis_evidence(evidence, policy)
    result["declaration_evidence"] = declaration_evidence(evidence, policy)
    result["unrecorded_evidence"] = unrecorded_evidence(evidence, policy)
    result["absent_evidence"] = absent_evidence(evidence, policy)

    for subject in result["absent_evidence"]:
        findings.append("the application does not declare %s at all" % subject)
    for subject in result["unrecorded_evidence"]:
        findings.append(
            "%s is declared with no reference behind it, measured, analysed or "
            "otherwise" % subject
        )

    share_short = not _at_least(
        result["evidence_share"], float(policy["min_evidence_share"])
    )
    weighted_short = not _at_least(
        result["weighted_evidence"], float(policy["min_weighted_evidence"])
    )
    if share_short or weighted_short:
        findings.append(
            "the application holds %.4g of the required subjects against %.4g, at "
            "a credited %.4g against %.4g"
            % (
                result["evidence_share"],
                float(policy["min_evidence_share"]),
                result["weighted_evidence"],
                float(policy["min_weighted_evidence"]),
            )
        )
        result["verdict"] = APPLICATION_EVIDENCE_SHORT
        return result

    result["verdict"] = MEETS_CLASS_THREE_SCOPE
    return result
