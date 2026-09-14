#!/usr/bin/env python3
"""Why contact attachment on a planar blocking diode is verified, and only
where contacts are actually there to verify.

Anchor: ECSS-E-ST-20-08C clause 12.6.4.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause carries a condition before it carries a requirement. A planar
blocking diode reaches a panel in more than one build state: some parts
arrive with leads already attached to the metallisation, ready to be
welded into the harness run, and some arrive with bare metallisation and
nothing attached to it at all. Only the first kind has an attachment
whose strength a pull can describe, and pulling the second kind returns
a number about the grip of the tooling written into the record as though
it were about the part. A mesa or integrated build is a different
construction again and is outside this clause rather than failing it.

Where contacts are present, two independent things decide whether the
verification earns its place:

    what it costs     a blocking diode sits in series with a string, so
                      an attachment that opens takes the whole string
                      off the array. The share of array power that
                      represents is the consequence half of the argument
    what it faces     the series weld of the lead, the conduction
                      heating the string current puts through the joint,
                      the routing strain of harness integration, the
                      broadband loading of launch, and the coefficient
                      mismatch a mission of thermal cycles drives
                      through the attachment

The exposure weights sum to one, which makes the exposure index a share
of the downstream life rather than a score, and the criticality is the
product of the two halves: a big consequence faced by almost nothing,
or a full downstream life on a string worth almost nothing, both come
out small. A parallel diode carrying the string when this one opens
relieves the consequence by a declared factor rather than removing it.

An exposure is only worth declaring if something is recorded against it,
so each maps onto an evidence parameter and the coverage of those
parameters is checked in its own right.

The weights, relief factor and floors below are a declared policy, not
physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PLANAR_CONSTRUCTION = "planar"

ATTACHED_CONTACTS_PRESENT = "planar-attached-contacts-present"
NO_ATTACHED_CONTACTS = "planar-no-attached-contacts"
NON_PLANAR_CONSTRUCTION = "non-planar-blocking-diode-construction"

CONTACT_CONFIGURATIONS = (
    ATTACHED_CONTACTS_PRESENT,
    NO_ATTACHED_CONTACTS,
    NON_PLANAR_CONSTRUCTION,
)

# Service exposure -> the evidence parameter it is watched through.
SERVICE_EXPOSURES = {
    "diode-lead-series-weld": "lead-weld-pull-strength",
    "string-current-conduction-heating": "attachment-thermal-resistance-drift",
    "panel-harness-routing-strain": "lead-bend-strain-record",
    "launch-random-vibration": "lead-attachment-fatigue-margin",
    "orbital-thermal-cycling": "attachment-shear-degradation",
}

RECOGNISED_EXPOSURES = tuple(sorted(SERVICE_EXPOSURES))

# Share of the downstream life each exposure accounts for. Sums to one.
EXPOSURE_WEIGHTS = {
    "diode-lead-series-weld": 0.25,
    "string-current-conduction-heating": 0.20,
    "panel-harness-routing-strain": 0.15,
    "launch-random-vibration": 0.20,
    "orbital-thermal-cycling": 0.20,
}

OUT_OF_CLAUSE_SCOPE = "blocking-diode-adherence-out-of-clause-scope"
ADHERENCE_NOT_APPLICABLE = "blocking-diode-adherence-not-applicable"
EXPOSURES_NOT_DECLARED = "blocking-diode-exposures-not-declared"
CRITICALITY_BELOW_THRESHOLD = "blocking-diode-attachment-criticality-below-threshold"
EVIDENCE_COVERAGE_INCOMPLETE = "blocking-diode-attachment-evidence-incomplete"
ADHERENCE_JUSTIFIED = "blocking-diode-adherence-verification-justified"

PURPOSE_VERDICTS = (
    OUT_OF_CLAUSE_SCOPE,
    ADHERENCE_NOT_APPLICABLE,
    EXPOSURES_NOT_DECLARED,
    CRITICALITY_BELOW_THRESHOLD,
    EVIDENCE_COVERAGE_INCOMPLETE,
    ADHERENCE_JUSTIFIED,
)

DEFAULT_BLOCKING_DIODE_PURPOSE_POLICY = {
    "min_attachment_criticality": 0.02,
    "min_evidence_coverage": 1.0,
    "redundancy_relief_factor": 0.5,
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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number <= 1.0:
        raise ValueError(
            "%s must be a fraction above zero and at most one, got %r"
            % (name, value)
        )
    return number


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if isinstance(value, (str, bytes)) or not hasattr(value, "__iter__"):
        raise ValueError("%s must be a sequence, got %r" % (name, value))
    return list(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_blocking_diode_purpose_policy(policy):
    """Check a planar blocking diode adherence purpose policy is usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction(
        "min_attachment_criticality", policy.get("min_attachment_criticality")
    )
    _require_fraction("min_evidence_coverage", policy.get("min_evidence_coverage"))
    _require_fraction(
        "redundancy_relief_factor", policy.get("redundancy_relief_factor")
    )
    return policy


def planar_contact_configuration(diode):
    """Which build state this device is in, before any pull is planned."""
    if not isinstance(diode, dict):
        raise ValueError("diode must be a mapping, got %r" % (diode,))
    construction = diode.get("construction")
    if not isinstance(construction, str) or not construction.strip():
        raise ValueError(
            "diode is missing a construction label, got %r" % (construction,)
        )
    count = diode.get("attached_contact_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError(
            "diode attached_contact_count must be a whole number of zero or "
            "more, got %r" % (count,)
        )
    if construction.strip().lower() != PLANAR_CONSTRUCTION:
        return NON_PLANAR_CONSTRUCTION
    if count == 0:
        return NO_ATTACHED_CONTACTS
    return ATTACHED_CONTACTS_PRESENT


def string_loss_fraction(string_power_w, array_power_w):
    """Share of array power one opened series attachment takes with it."""
    string = _require_positive("string_power_w", string_power_w)
    array = _require_positive("array_power_w", array_power_w)
    if string > array and not math.isclose(
        string, array, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "a %g W string cannot sit inside a %g W array" % (string, array)
        )
    return string / array


def service_exposure_index(exposures):
    """Share of the downstream life the declared exposures account for."""
    declared = _require_sequence("exposures", exposures)
    seen = set()
    total = 0.0
    for exposure in declared:
        if exposure not in EXPOSURE_WEIGHTS:
            raise ValueError(
                "unrecognised service exposure %r; known exposures are %s"
                % (exposure, ", ".join(RECOGNISED_EXPOSURES))
            )
        if exposure in seen:
            continue
        seen.add(exposure)
        total += EXPOSURE_WEIGHTS[exposure]
    # The weights sum to one exactly in decimal but not in binary, so a full
    # set can land a unit in the last place above one on some hosts. Clamp
    # that representation error rather than letting it read as an index
    # larger than the whole downstream life.
    if total > 1.0 and math.isclose(total, 1.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        total = 1.0
    return total


def exposure_evidence_map(exposures):
    """Map each declared exposure onto the parameter recording it."""
    declared = _require_sequence("exposures", exposures)
    mapped = {}
    for exposure in declared:
        if exposure not in SERVICE_EXPOSURES:
            raise ValueError(
                "unrecognised service exposure %r; known exposures are %s"
                % (exposure, ", ".join(RECOGNISED_EXPOSURES))
            )
        mapped[exposure] = SERVICE_EXPOSURES[exposure]
    return mapped


def evidence_coverage(exposures, recorded_parameters):
    """Share of the declared exposures that something is recorded against."""
    mapped = exposure_evidence_map(exposures)
    if not mapped:
        raise ValueError("no service exposure is declared, so nothing to cover")
    recorded = set(_require_sequence("recorded_parameters", recorded_parameters))
    covered = sum(1 for parameter in mapped.values() if parameter in recorded)
    return covered / len(mapped)


def attachment_criticality(
    loss_fraction,
    exposure_index,
    redundant_diode,
    policy=DEFAULT_BLOCKING_DIODE_PURPOSE_POLICY,
):
    """Consequence of an open attachment weighted by what it has to survive."""
    validate_blocking_diode_purpose_policy(policy)
    loss = _require_fraction("loss_fraction", loss_fraction)
    index = _require_fraction("exposure_index", exposure_index)
    redundant = _require_flag("redundant_diode", redundant_diode)
    criticality = loss * index
    if redundant:
        criticality *= float(policy["redundancy_relief_factor"])
    return criticality


def assess_blocking_diode_adherence_purpose(
    case, policy=DEFAULT_BLOCKING_DIODE_PURPOSE_POLICY
):
    """Full clause 12.6.4.2.1 judgement for one adherence verification case."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_blocking_diode_purpose_policy(policy)
    diode = case.get("diode")
    if diode is None:
        raise ValueError("case is missing a diode block")

    configuration = planar_contact_configuration(diode)
    findings = []
    result = {
        "contact_configuration": configuration,
        "exposure_index": 0.0,
        "attachment_criticality": 0.0,
        "evidence_map": {},
        "findings": findings,
    }

    if configuration == NON_PLANAR_CONSTRUCTION:
        result["verdict"] = OUT_OF_CLAUSE_SCOPE
        result["rationale"] = (
            "the device is not a planar build, so this clause is not the one "
            "that governs its attachment"
        )
        return result

    if configuration == NO_ATTACHED_CONTACTS:
        result["verdict"] = ADHERENCE_NOT_APPLICABLE
        result["rationale"] = (
            "the planar device carries bare metallisation with nothing "
            "attached, so there is no attachment for a pull to describe"
        )
        return result

    exposures = case.get("exposures")
    if exposures is None:
        raise ValueError("case is missing an exposures list")
    index = service_exposure_index(exposures)
    mapped = exposure_evidence_map(exposures)
    result["exposure_index"] = index
    result["evidence_map"] = mapped

    if not mapped:
        findings.append(
            "the case declares no service exposure against the attachment"
        )
        result["verdict"] = EXPOSURES_NOT_DECLARED
        result["rationale"] = (
            "nothing states what the lead attachment is being asked to "
            "outlast, so a destructive pull has no argument behind it"
        )
        return result

    consequence = case.get("consequence")
    if not isinstance(consequence, dict):
        raise ValueError("case is missing a consequence block")
    loss = string_loss_fraction(
        consequence.get("string_power_w"), consequence.get("array_power_w")
    )
    redundant = _require_flag(
        "consequence redundant_diode", consequence.get("redundant_diode")
    )
    criticality = attachment_criticality(loss, index, redundant, policy)
    result["string_loss_fraction"] = loss
    result["redundant_diode"] = redundant
    result["attachment_criticality"] = criticality

    recorded = case.get("recorded_parameters")
    if recorded is None:
        raise ValueError("case is missing a recorded_parameters list")
    coverage = evidence_coverage(exposures, recorded)
    result["evidence_coverage"] = coverage

    criticality_low = not _at_least(
        criticality, float(policy["min_attachment_criticality"])
    )
    if criticality_low:
        findings.append(
            "an opened attachment costs %.5f of the array weighted by a %.4f "
            "exposure index, a criticality of %.5f against the %.5f that earns "
            "a destructive pull"
            % (
                loss,
                index,
                criticality,
                float(policy["min_attachment_criticality"]),
            )
        )

    coverage_low = not _at_least(
        coverage, float(policy["min_evidence_coverage"])
    )
    if coverage_low:
        uncovered = sorted(
            exposure
            for exposure, parameter in mapped.items()
            if parameter not in set(recorded)
        )
        findings.append(
            "%.4f of the declared exposures are recorded against, below the "
            "%.4f required; nothing is recorded for %s"
            % (
                coverage,
                float(policy["min_evidence_coverage"]),
                ", ".join(uncovered),
            )
        )

    if criticality_low:
        result["verdict"] = CRITICALITY_BELOW_THRESHOLD
    elif coverage_low:
        result["verdict"] = EVIDENCE_COVERAGE_INCOMPLETE
    else:
        result["verdict"] = ADHERENCE_JUSTIFIED
    result["rationale"] = (
        "a planar device with attached contacts, %d service exposures declared "
        "and a criticality of %.5f" % (len(mapped), criticality)
    )
    return result
