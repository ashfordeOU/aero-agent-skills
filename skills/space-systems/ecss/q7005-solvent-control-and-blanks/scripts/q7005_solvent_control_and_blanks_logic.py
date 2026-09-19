#!/usr/bin/env python3
"""Solvent purity, blank control and blank correction for the indirect method.

Anchor: ECSS-Q-ST-70-05C, the indirect-method clauses covering solvent
purity, control blanks and the avoidance of contamination introduced by
the measurement itself. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

An indirect measurement weighs whatever the solvent brought to the cell.
Some of that came off the hardware; the rest came out of the bottle, off
the glassware, off the gloves and out of the air of the room. Separating
the two is not an optional refinement, it is the measurement.

The solvent's own contribution is predictable from its non-volatile
residue specification and the volume used, and it concentrates with the
sample when the extract is reduced. That expected mass is compared with
what the sample actually delivered: a blank that is a large fraction of
the gross signal means the result is a property of the solvent, not of
the surface.

What the blanks cannot predict is their own scatter, and that scatter is
what sets the limits. Three standard deviations of the blank is the
smallest net mass distinguishable from nothing; ten is the smallest that
can be quoted as a number. Between the two the honest answer is that
something is there and it cannot be quantified.

A run with no blank at all is not a run with a zero blank.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

QUANTIFIABLE = "quantifiable"
DETECTED_NOT_QUANTIFIABLE = "detected-not-quantifiable"
NOT_DETECTED = "not-detected"
GRADES = (QUANTIFIABLE, DETECTED_NOT_QUANTIFIABLE, NOT_DETECTED)

SOLVENT_BLANK = "solvent-blank"
HANDLING_BLANK = "handling-blank"
BLANK_KINDS = (SOLVENT_BLANK, HANDLING_BLANK)

DEFAULT_BLANK_POLICY = {
    "min_blank_replicates": 3,
    "max_blank_fraction": 0.25,
    "detection_sigma": 3.0,
    "quantitation_sigma": 10.0,
    "max_solvent_nvr_mg_per_l": 1.0,
    "require_handling_blank": True,
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


def validate_blank_policy(policy):
    """Check a blank-control policy carries usable replicates and sigmas."""
    _require_mapping("policy", policy)
    replicates = _require_count(
        "min_blank_replicates", policy.get("min_blank_replicates")
    )
    if replicates < 2:
        raise ValueError(
            "min_blank_replicates must be at least 2; a single blank has no "
            "scatter and therefore sets no limit, got %r" % (replicates,)
        )
    fraction = _require_number(
        "max_blank_fraction", policy.get("max_blank_fraction")
    )
    if not 0.0 < fraction < 1.0:
        raise ValueError(
            "max_blank_fraction must sit strictly inside (0, 1), got %r"
            % policy.get("max_blank_fraction")
        )
    detection = _require_positive(
        "detection_sigma", policy.get("detection_sigma")
    )
    quantitation = _require_positive(
        "quantitation_sigma", policy.get("quantitation_sigma")
    )
    if quantitation <= detection:
        raise ValueError(
            "quantitation_sigma %g must sit above detection_sigma %g"
            % (quantitation, detection)
        )
    _require_positive(
        "max_solvent_nvr_mg_per_l", policy.get("max_solvent_nvr_mg_per_l")
    )
    if not isinstance(policy.get("require_handling_blank"), bool):
        raise ValueError("require_handling_blank must be true or false")
    return policy


def expected_blank_mass_ug(volume_ml, nvr_mg_per_l):
    """Residue the solvent alone contributes, from its purity specification.

    A non-volatile residue in milligrams per litre, times a volume in
    millilitres, is a mass in micrograms: the two unit conversions cancel.
    """
    volume = _require_positive("volume_ml", volume_ml)
    nvr = _require_non_negative("nvr_mg_per_l", nvr_mg_per_l)
    return nvr * volume


def solvent_purity_check(nvr_mg_per_l, policy=DEFAULT_BLANK_POLICY):
    """Whether the solvent grade is clean enough to be used at all."""
    validate_blank_policy(policy)
    nvr = _require_non_negative("nvr_mg_per_l", nvr_mg_per_l)
    acceptable = _at_most(nvr, policy["max_solvent_nvr_mg_per_l"])
    return {
        "nvr_mg_per_l": nvr,
        "acceptable": acceptable,
        "reason": None
        if acceptable
        else "solvent residue %.4g mg/l exceeds the grade ceiling %.4g mg/l"
        % (nvr, policy["max_solvent_nvr_mg_per_l"]),
    }


def blank_fraction(blank_mass_ug, gross_mass_ug):
    """Share of the gross signal the blank accounts for."""
    blank = _require_non_negative("blank_mass_ug", blank_mass_ug)
    gross = _require_positive("gross_mass_ug", gross_mass_ug)
    return blank / gross


def net_residue_ug(gross_mass_ug, blank_mass_ug):
    """Blank-corrected residue, with the raw difference kept alongside."""
    gross = _require_positive("gross_mass_ug", gross_mass_ug)
    blank = _require_non_negative("blank_mass_ug", blank_mass_ug)
    raw = gross - blank
    return {
        "gross_mass_ug": gross,
        "blank_mass_ug": blank,
        "raw_net_ug": raw,
        "net_mass_ug": max(raw, 0.0),
        "blank_exceeded_sample": raw < 0.0,
    }


def detection_limit_ug(blank_sd_ug, policy=DEFAULT_BLANK_POLICY):
    """Smallest net mass distinguishable from the blank's own scatter."""
    validate_blank_policy(policy)
    sd = _require_positive("blank_sd_ug", blank_sd_ug)
    return policy["detection_sigma"] * sd


def quantitation_limit_ug(blank_sd_ug, policy=DEFAULT_BLANK_POLICY):
    """Smallest net mass that can be quoted as a number."""
    validate_blank_policy(policy)
    sd = _require_positive("blank_sd_ug", blank_sd_ug)
    return policy["quantitation_sigma"] * sd


def combined_uncertainty_ug(gross_sd_ug, blank_sd_ug):
    """Uncertainty on the net, with the two scatters added in quadrature."""
    gross_sd = _require_non_negative("gross_sd_ug", gross_sd_ug)
    blank_sd = _require_non_negative("blank_sd_ug", blank_sd_ug)
    return math.sqrt(gross_sd * gross_sd + blank_sd * blank_sd)


def grade_net_result(net_mass_ug, blank_sd_ug, policy=DEFAULT_BLANK_POLICY):
    """Whether the net residue is quantifiable, merely detected, or not."""
    validate_blank_policy(policy)
    net = _require_non_negative("net_mass_ug", net_mass_ug)
    lod = detection_limit_ug(blank_sd_ug, policy)
    loq = quantitation_limit_ug(blank_sd_ug, policy)
    if _at_least(net, loq):
        grade = QUANTIFIABLE
    elif _at_least(net, lod):
        grade = DETECTED_NOT_QUANTIFIABLE
    else:
        grade = NOT_DETECTED
    return {
        "net_mass_ug": net,
        "detection_limit_ug": lod,
        "quantitation_limit_ug": loq,
        "grade": grade,
    }


def assess_blank_control(case, policy=DEFAULT_BLANK_POLICY):
    """Full blank-control assessment for one indirect measurement."""
    validate_blank_policy(policy)
    _require_mapping("case", case)
    replicates = _require_count(
        "blank_replicates", case.get("blank_replicates")
    )
    if replicates == 0:
        raise ValueError(
            "the run carries no blank; an absent blank is not a zero blank and "
            "the measurement cannot be corrected or graded"
        )
    kinds = case.get("blank_kinds", ())
    if not isinstance(kinds, (tuple, list)):
        raise ValueError("blank_kinds must be a sequence of blank kinds")
    unknown = [kind for kind in kinds if kind not in BLANK_KINDS]
    if unknown:
        raise ValueError(
            "unknown blank kind(s): %s" % ", ".join(sorted(unknown))
        )
    if SOLVENT_BLANK not in kinds:
        raise ValueError(
            "a solvent blank is required before any correction can be applied"
        )

    purity = solvent_purity_check(case.get("solvent_nvr_mg_per_l"), policy)
    expected_blank = expected_blank_mass_ug(
        case.get("solvent_volume_ml"), case.get("solvent_nvr_mg_per_l")
    )
    measured_blank = _require_non_negative(
        "measured_blank_ug", case.get("measured_blank_ug")
    )
    gross = _require_positive("gross_residue_ug", case.get("gross_residue_ug"))
    fraction = blank_fraction(measured_blank, gross)
    net = net_residue_ug(gross, measured_blank)
    grading = grade_net_result(
        net["net_mass_ug"], case.get("blank_sd_ug"), policy
    )
    uncertainty = combined_uncertainty_ug(
        case.get("gross_sd_ug", 0.0), case.get("blank_sd_ug")
    )

    findings = []
    duties = []
    if replicates < policy["min_blank_replicates"]:
        findings.append(
            "%d blank replicates were run against a required %d; the scatter "
            "that sets the detection limit is not established"
            % (replicates, policy["min_blank_replicates"])
        )
    if policy["require_handling_blank"] and HANDLING_BLANK not in kinds:
        findings.append(
            "no handling blank was run, so contamination picked up from the "
            "glassware, the gloves and the room is attributed to the surface"
        )
    if not purity["acceptable"]:
        findings.append("the solvent grade is not clean enough: %s" % purity["reason"])
    if not _at_most(fraction, policy["max_blank_fraction"]):
        findings.append(
            "the blank accounts for %.3f of the gross residue against a ceiling "
            "of %.3f; the result is blank-limited and describes the solvent "
            "rather than the surface"
            % (fraction, policy["max_blank_fraction"])
        )
    if net["blank_exceeded_sample"]:
        findings.append(
            "the blank exceeded the gross residue, so the sample carried no "
            "measurable contamination above the solvent it was taken up in"
        )
    if grading["grade"] == DETECTED_NOT_QUANTIFIABLE:
        findings.append(
            "the net residue %.2f ug sits between the detection limit %.2f ug "
            "and the quantitation limit %.2f ug; report it as present and "
            "bounded, never as a figure"
            % (
                grading["net_mass_ug"],
                grading["detection_limit_ug"],
                grading["quantitation_limit_ug"],
            )
        )
    if not math.isclose(
        expected_blank, measured_blank, rel_tol=0.5, abs_tol=_ABS_TOL
    ):
        findings.append(
            "the measured blank %.2f ug departs from the %.2f ug the solvent "
            "specification predicts, so something other than the solvent grade "
            "is contributing" % (measured_blank, expected_blank)
        )
    duties.append(
        "carry the blank-corrected net of %.2f ug and its combined uncertainty "
        "of %.2f ug into the areal level, not the gross residue"
        % (net["net_mass_ug"], uncertainty)
    )
    duties.append(
        "record the solvent lot and its residue specification beside the "
        "result, since the blank is a property of the lot and not of the method"
    )
    return {
        "purity": purity,
        "expected_blank_ug": expected_blank,
        "measured_blank_ug": measured_blank,
        "blank_fraction": fraction,
        "net": net,
        "grading": grading,
        "combined_uncertainty_ug": uncertainty,
        "duties": duties,
        "findings": findings,
        "blank_control_sound": not findings,
    }
