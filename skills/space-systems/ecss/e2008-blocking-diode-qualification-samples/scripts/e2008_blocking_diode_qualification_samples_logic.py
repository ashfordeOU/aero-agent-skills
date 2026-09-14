#!/usr/bin/env python3
"""Conformance of blocking diode qualification samples to the declared process.

Anchor: ECSS-E-ST-20-08C clause 12.5.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The requirement is one sentence and the whole difficulty is in taking it
literally: the diodes submitted to qualification are built by the process
the supplier has written down, at the issue of that document which was in
force, and a qualification run on anything else has qualified something
the delivered lot will not be.

Three things follow, and each is a way a campaign quietly invalidates
itself.

The document has to exist as an identified thing. A process description
with no reference and no issue cannot be the baseline of anything,
because nobody can say later which text the samples were built to. An
unreferenced or unissued document therefore closes the assessment rather
than passing it.

The issue matters as much as the reference. A sample built to issue B of
a document whose issue C is what the qualification is being claimed
against was built by a different process, whatever the reference on its
traveller says. The same argument runs in time: a sample whose build
predates the effective day of the issue it cites cannot have been built
by that issue, and that is a record defect worth catching before the
data is presented rather than after.

The build parameters are judged against the bands the document declares,
not against what the shop can hold. Each declared parameter carries a
nominal and a tolerance; a sample sits inside the band or does not, a
value exactly on a limit is inside, and the utilisation -- how much of
the allowed band the sample has spent -- is worth reporting beside the
verdict, because a sample conforming at ninety-eight per cent of band
and one conforming at five per cent say very different things about
whether the next lot will conform too.

A declared parameter with no value recorded on the sample is not a pass.
It is an unestablished parameter, and it is held apart from a measured
value that drifted.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PROCESS_ISSUE_MISMATCH = "process-issue-mismatch"
PROCESS_REFERENCE_MISMATCH = "process-reference-mismatch"
BUILT_BEFORE_ISSUE_EFFECTIVE = "built-before-issue-effective"
CONSTRUCTION_OUTSIDE_SCOPE = "construction-outside-document-scope"
BUILD_PARAMETER_OUT_OF_BAND = "build-parameter-out-of-band"
BUILD_PARAMETER_NOT_RECORDED = "build-parameter-not-recorded"

PROCESS_IDENTIFICATION_NOT_ESTABLISHED = "process-identification-not-established"
SAMPLES_DO_NOT_CONFORM = "samples-do-not-conform-to-process-identification"
SAMPLES_CONFORM = "samples-conform-to-process-identification"

DEFAULT_CONFORMANCE_POLICY = {
    "max_nonconforming_fraction": 0.0,
    "marginal_band_utilisation": 0.9,
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


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_conformance_policy(policy):
    """Check the sample conformance policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    allowance = _require_non_negative(
        "max_nonconforming_fraction", policy.get("max_nonconforming_fraction")
    )
    if allowance > 1.0:
        raise ValueError(
            "max_nonconforming_fraction %g is above one; an allowance that "
            "admits a sample set with nothing conforming is not a policy"
            % allowance
        )
    marginal = _require_positive(
        "marginal_band_utilisation", policy.get("marginal_band_utilisation")
    )
    if marginal > 1.0:
        raise ValueError(
            "marginal_band_utilisation %g is above one; no conforming sample "
            "could ever reach it" % marginal
        )
    return policy


def validate_declared_parameter(parameter):
    """Read one build parameter band the process document declares."""
    if not isinstance(parameter, dict):
        raise ValueError("parameter must be a mapping, got %r" % (parameter,))
    name = _require_label("parameter name", parameter.get("name"))
    if not name:
        raise ValueError("parameter name must not be blank")
    nominal = _require_number("nominal on %s" % name, parameter.get("nominal"))
    tolerance = _require_positive(
        "tolerance on %s" % name, parameter.get("tolerance")
    )
    return {"name": name, "nominal": nominal, "tolerance": tolerance}


def validate_process_identification(document):
    """Check the process identification document can serve as a baseline."""
    if not isinstance(document, dict):
        raise ValueError("document must be a mapping, got %r" % (document,))
    reference = _require_label("reference", document.get("reference"))
    issue = _require_label("issue", document.get("issue"))
    effective_day = _require_non_negative(
        "effective_day", document.get("effective_day")
    )
    construction = _require_label("construction", document.get("construction"))
    raw = document.get("parameters")
    if not isinstance(raw, (list, tuple)):
        raise ValueError("parameters must be a sequence of declared bands")
    parameters = []
    seen = set()
    for parameter in raw:
        checked = validate_declared_parameter(parameter)
        if checked["name"] in seen:
            raise ValueError(
                "parameter %r is declared twice in the document"
                % checked["name"]
            )
        seen.add(checked["name"])
        parameters.append(checked)
    return {
        "reference": reference,
        "issue": issue,
        "effective_day": effective_day,
        "construction": construction,
        "parameters": tuple(parameters),
    }


def validate_sample_record(sample):
    """Read one qualification sample's build record."""
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping, got %r" % (sample,))
    identifier = _require_label("sample id", sample.get("id"))
    if not identifier:
        raise ValueError("sample id must not be blank")
    reference = _require_label(
        "process_reference on %s" % identifier, sample.get("process_reference")
    )
    issue = _require_label(
        "process_issue on %s" % identifier, sample.get("process_issue")
    )
    build_day = _require_non_negative(
        "build_day on %s" % identifier, sample.get("build_day")
    )
    construction = _require_label(
        "construction on %s" % identifier, sample.get("construction")
    )
    measured = sample.get("parameters")
    if not isinstance(measured, dict):
        raise ValueError(
            "parameters on %s must be a mapping of name to measured value"
            % identifier
        )
    return {
        "id": identifier,
        "process_reference": reference,
        "process_issue": issue,
        "build_day": build_day,
        "construction": construction,
        "parameters": dict(measured),
    }


def band_utilisation(measured, nominal, tolerance):
    """Share of the declared tolerance band a measured value has spent.

    Zero on nominal, one exactly on a limit, above one outside the band.
    """
    measured_value = _require_number("measured", measured)
    nominal_value = _require_number("nominal", nominal)
    tolerance_value = _require_positive("tolerance", tolerance)
    return abs(measured_value - nominal_value) / tolerance_value


def parameter_within_band(measured, nominal, tolerance):
    """True when a measured value sits inside the declared band, tie included."""
    return _at_most(band_utilisation(measured, nominal, tolerance), 1.0)


def sample_conformance(sample, document):
    """Judge one qualification sample against the process identification."""
    checked_document = validate_process_identification(document)
    record = validate_sample_record(sample)
    reasons = []
    parameter_findings = []
    utilisations = []

    if record["process_reference"] != checked_document["reference"]:
        reasons.append(PROCESS_REFERENCE_MISMATCH)
    if record["process_issue"] != checked_document["issue"]:
        reasons.append(PROCESS_ISSUE_MISMATCH)
    if record["construction"] != checked_document["construction"]:
        reasons.append(CONSTRUCTION_OUTSIDE_SCOPE)
    if record["build_day"] < checked_document["effective_day"] and not math.isclose(
        record["build_day"],
        checked_document["effective_day"],
        rel_tol=_REL_TOL,
        abs_tol=_ABS_TOL,
    ):
        reasons.append(BUILT_BEFORE_ISSUE_EFFECTIVE)

    for declared in checked_document["parameters"]:
        name = declared["name"]
        if name not in record["parameters"]:
            if BUILD_PARAMETER_NOT_RECORDED not in reasons:
                reasons.append(BUILD_PARAMETER_NOT_RECORDED)
            parameter_findings.append(
                "sample %s records no value for declared parameter %s, so that "
                "parameter is unestablished rather than met"
                % (record["id"], name)
            )
            continue
        utilisation = band_utilisation(
            record["parameters"][name], declared["nominal"], declared["tolerance"]
        )
        utilisations.append((name, utilisation))
        if not _at_most(utilisation, 1.0):
            if BUILD_PARAMETER_OUT_OF_BAND not in reasons:
                reasons.append(BUILD_PARAMETER_OUT_OF_BAND)
            parameter_findings.append(
                "sample %s holds parameter %s at %.4g per cent of the declared "
                "band, outside the document limit"
                % (record["id"], name, utilisation * 100.0)
            )

    worst_name = None
    worst_utilisation = 0.0
    for name, utilisation in utilisations:
        if utilisation > worst_utilisation:
            worst_name = name
            worst_utilisation = utilisation
    if worst_name is None and utilisations:
        worst_name = utilisations[0][0]

    return {
        "id": record["id"],
        "reasons": tuple(reasons),
        "parameter_findings": tuple(parameter_findings),
        "worst_parameter": worst_name,
        "worst_band_utilisation": worst_utilisation,
        "conforming": not reasons,
    }


def sample_conformances(samples, document):
    """Judge every submitted sample, in record order."""
    if not isinstance(samples, (list, tuple)):
        raise ValueError("samples must be a sequence of build records")
    if not samples:
        raise ValueError(
            "no sample was submitted, so there is nothing to hold against the "
            "process identification document"
        )
    results = []
    seen = set()
    for sample in samples:
        result = sample_conformance(sample, document)
        if result["id"] in seen:
            raise ValueError("duplicate sample id %r in the record" % result["id"])
        seen.add(result["id"])
        results.append(result)
    return tuple(results)


def nonconforming_fraction(results):
    """Share of the judged samples that failed at least one conformance test."""
    if not isinstance(results, (list, tuple)) or not results:
        raise ValueError("results must be a non-empty sequence")
    failed = sum(1 for result in results if not result["conforming"])
    return failed / len(results)


def within_nonconformance_allowance(results, policy=DEFAULT_CONFORMANCE_POLICY):
    """True when the nonconforming share is inside the declared allowance."""
    validate_conformance_policy(policy)
    return _at_most(
        nonconforming_fraction(results), float(policy["max_nonconforming_fraction"])
    )


def worst_sample(results):
    """The judged sample that has spent most of a declared tolerance band."""
    if not isinstance(results, (list, tuple)) or not results:
        raise ValueError("results must be a non-empty sequence")
    return max(results, key=lambda result: result["worst_band_utilisation"])


def marginal_sample_advisories(results, policy=DEFAULT_CONFORMANCE_POLICY):
    """Name conforming samples that have spent nearly all of a declared band.

    These do not move the verdict -- a conforming sample conforms -- but a
    qualification built on samples sitting against their process limits is
    qualifying the edge of the process, and that is worth saying here
    rather than rediscovering it on the first delivered lot.
    """
    validate_conformance_policy(policy)
    if not isinstance(results, (list, tuple)):
        raise ValueError("results must be a sequence")
    band = float(policy["marginal_band_utilisation"])
    advisories = []
    for result in results:
        if not result["conforming"]:
            continue
        if _at_least(result["worst_band_utilisation"], band):
            advisories.append(
                "sample %s conforms with parameter %s at %.4g per cent of the "
                "declared band, at or past the %.4g per cent marginal point; "
                "the qualification is being run on the edge of the process"
                % (
                    result["id"],
                    result["worst_parameter"],
                    result["worst_band_utilisation"] * 100.0,
                    band * 100.0,
                )
            )
    return tuple(advisories)


def assess_qualification_sample_conformance(
    case, policy=DEFAULT_CONFORMANCE_POLICY
):
    """Full clause 12.5.4 conformance decision for one submitted sample set."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_conformance_policy(policy)

    findings = []
    advisories = []
    result = {
        "process_reference": None,
        "process_issue": None,
        "effective_day": None,
        "construction": None,
        "sample_results": (),
        "conforming_samples": (),
        "nonconforming_samples": (),
        "nonconforming_fraction": None,
        "worst_sample_id": None,
        "worst_band_utilisation": None,
        "findings": findings,
        "advisories": advisories,
    }

    document = case.get("process_identification")
    if document is None:
        findings.append(
            "no process identification document is referenced, so there is no "
            "declared process these samples can be shown to match"
        )
        result["verdict"] = PROCESS_IDENTIFICATION_NOT_ESTABLISHED
        return result

    checked = validate_process_identification(document)
    result["process_reference"] = checked["reference"]
    result["process_issue"] = checked["issue"]
    result["effective_day"] = checked["effective_day"]
    result["construction"] = checked["construction"]

    if not checked["reference"] or not checked["issue"]:
        findings.append(
            "the process description carries no reference or no issue; a text "
            "nobody can name later is not a qualification baseline"
        )
        result["verdict"] = PROCESS_IDENTIFICATION_NOT_ESTABLISHED
        return result
    if not checked["parameters"]:
        findings.append(
            "the document declares no build parameter band, so sample "
            "conformance to it cannot be demonstrated on anything measurable"
        )
        result["verdict"] = PROCESS_IDENTIFICATION_NOT_ESTABLISHED
        return result

    results = sample_conformances(case.get("samples"), document)
    result["sample_results"] = results
    result["conforming_samples"] = tuple(
        item["id"] for item in results if item["conforming"]
    )
    result["nonconforming_samples"] = tuple(
        item["id"] for item in results if not item["conforming"]
    )
    result["nonconforming_fraction"] = nonconforming_fraction(results)

    worst = worst_sample(results)
    result["worst_sample_id"] = worst["id"]
    result["worst_band_utilisation"] = worst["worst_band_utilisation"]

    for item in results:
        if item["conforming"]:
            continue
        findings.append(
            "sample %s does not match the declared process (%s) of document %s "
            "issue %s"
            % (
                item["id"],
                ", ".join(item["reasons"]),
                checked["reference"],
                checked["issue"],
            )
        )
        findings.extend(item["parameter_findings"])

    advisories.extend(marginal_sample_advisories(results, policy))

    if not within_nonconformance_allowance(results, policy):
        findings.append(
            "%.4g per cent of the submitted samples do not match the declared "
            "process, above the %.4g per cent the policy allows; the "
            "qualification would be run on parts the delivered lot is not"
            % (
                result["nonconforming_fraction"] * 100.0,
                float(policy["max_nonconforming_fraction"]) * 100.0,
            )
        )
        result["verdict"] = SAMPLES_DO_NOT_CONFORM
        return result

    result["verdict"] = SAMPLES_CONFORM
    return result
