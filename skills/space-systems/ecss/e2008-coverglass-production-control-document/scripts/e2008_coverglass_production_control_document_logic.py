#!/usr/bin/env python3
"""Supplier process identification document for coverglass production.

Anchor: ECSS-E-ST-20-08C clause 8.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Before coverglass production is qualified the supplier writes a
production control document that identifies the processes to be
qualified. Somebody then has to decide whether that document actually
identifies them. The document is a gate, not a catalogue: its job is to
fix, before the campaign, which processes the glass depends on, so a
process qualified later can be traced back to a commitment made earlier.

Production processes a coverglass depends on
    substrate-glass-forming        qualification-critical
    cutting-and-sizing             qualification-critical
    edge-finishing                 control-only
    cleaning                       qualification-critical
    ar-coating-deposition          qualification-critical
    uv-filter-deposition           qualification-critical
    conductive-coating-deposition  control-only
    marking-and-packaging          control-only

A declared process entry has four parts and each fails on its own:
the production document that controls it, the control parameters with
their nominal and their band, the qualification evidence, and the date
that evidence carries.

A control parameter is graded three ways, and the third is the one that
is normally skipped. The band has to bracket its nominal, or it
describes some other setting. The band has to be tight enough to control
anything, or it is a range and not a tolerance. And the band has to be
wider than the measurement behind it can resolve: a deposition rate held
to plus or minus one part in a thousand by an instrument whose
uncertainty is one part in five hundred is not controlled, it is
recorded. That last reading is a test uncertainty ratio.

Evidence dated before the document that committed to it discharges
nothing. It was generated under some other commitment, and using it here
inverts the gate the document exists to be.

The required process set, the band width cap, the uncertainty ratio and
the criticality grades below are declared project policy, not physical
constants; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime
import math

CRITICALITY_KINDS = ("qualification-critical", "control-only")

REQUIRED_COVERGLASS_PROCESSES = {
    "substrate-glass-forming": "qualification-critical",
    "cutting-and-sizing": "qualification-critical",
    "edge-finishing": "control-only",
    "cleaning": "qualification-critical",
    "ar-coating-deposition": "qualification-critical",
    "uv-filter-deposition": "qualification-critical",
    "conductive-coating-deposition": "control-only",
    "marking-and-packaging": "control-only",
}

PARAMETER_CONTROLLED = "parameter-controlled"
PARAMETER_BAND_EXCLUDES_NOMINAL = "parameter-band-excludes-nominal"
PARAMETER_BAND_TOO_WIDE = "parameter-band-too-wide"
PARAMETER_BAND_BELOW_RESOLUTION = "parameter-band-below-measurement-resolution"

ENTRY_ACCEPTED = "process-entry-accepted"
ENTRY_DOCUMENT_MISSING = "process-controlling-document-missing"
ENTRY_PARAMETERS_MISSING = "process-control-parameters-missing"
ENTRY_PARAMETER_DEFECT = "process-control-parameter-defect"
ENTRY_EVIDENCE_MISSING = "process-qualification-evidence-missing"
ENTRY_EVIDENCE_PREDATES_DOCUMENT = "process-qualification-evidence-predates-document"

_ENTRY_RANK = {
    ENTRY_DOCUMENT_MISSING: 0,
    ENTRY_EVIDENCE_MISSING: 1,
    ENTRY_EVIDENCE_PREDATES_DOCUMENT: 2,
    ENTRY_PARAMETERS_MISSING: 3,
    ENTRY_PARAMETER_DEFECT: 4,
    ENTRY_ACCEPTED: 5,
}

DOCUMENT_ACCEPTED = "coverglass-production-control-document-accepted"
DOCUMENT_INCOMPLETE = "coverglass-production-control-document-incomplete"

DEFAULT_PCD_POLICY = {
    "max_relative_half_width": 0.25,
    "min_uncertainty_ratio": 4.0,
    "required_processes": dict(REQUIRED_COVERGLASS_PROCESSES),
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def validate_identifier(value, label):
    """A non-empty printable identifier, trimmed."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def validate_real(value, label):
    """A finite real number."""
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (label, value))
    return float(value)


def validate_positive(value, label):
    """A finite real number greater than zero."""
    number = validate_real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def validate_iso_date(value, label):
    """A calendar date written as YYYY-MM-DD."""
    text = validate_identifier(value, label)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError(
            "%s must be an ISO calendar date (YYYY-MM-DD), got %r" % (label, value)
        ) from None


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A relative band width and an uncertainty ratio are both quotients of
    measured quantities and their limits are round numbers, so a band
    drawn exactly at the limit can evaluate a unit in the last place on
    the wrong side of it. The comparison absorbs that; the limit stays as
    declared.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _policy(policy):
    settings = dict(DEFAULT_PCD_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    return settings


def validate_control_parameter(parameter, index=0):
    """Read one control parameter into its four numbers."""
    _require_mapping("control parameter %d" % index, parameter)
    name = validate_identifier(
        parameter.get("name"), "control parameter %d name" % index
    )
    nominal = validate_positive(parameter.get("nominal"), "%s nominal" % name)
    lower = validate_real(parameter.get("lower"), "%s lower limit" % name)
    upper = validate_real(parameter.get("upper"), "%s upper limit" % name)
    if upper <= lower:
        raise ValueError(
            "%s upper limit %r must exceed its lower limit %r"
            % (name, parameter.get("upper"), parameter.get("lower"))
        )
    uncertainty = validate_positive(
        parameter.get("measurement_uncertainty"), "%s measurement uncertainty" % name
    )
    return {
        "name": name,
        "nominal": nominal,
        "lower": lower,
        "upper": upper,
        "measurement_uncertainty": uncertainty,
    }


def assess_control_parameter(parameter, policy=None, index=0):
    """Grade one control parameter three ways.

    Bracketing, width and resolution are independent readings. A band
    can bracket its nominal, be tight enough to mean something, and
    still be narrower than the instrument behind it can see.
    """
    settings = _policy(policy)
    cap = validate_positive(
        settings.get("max_relative_half_width"), "max_relative_half_width"
    )
    min_ratio = validate_positive(
        settings.get("min_uncertainty_ratio"), "min_uncertainty_ratio"
    )
    read = validate_control_parameter(parameter, index)

    half_width = (read["upper"] - read["lower"]) / 2.0
    relative_half_width = half_width / read["nominal"]
    uncertainty_ratio = half_width / read["measurement_uncertainty"]

    findings = []
    brackets = read["lower"] <= read["nominal"] <= read["upper"]
    within_cap = _at_most(relative_half_width, cap)
    resolvable = _at_least(uncertainty_ratio, min_ratio)

    if not brackets:
        status = PARAMETER_BAND_EXCLUDES_NOMINAL
        findings.append(
            "%s: the band %r to %r does not contain its own nominal %r, so it "
            "describes some other setting"
            % (read["name"], read["lower"], read["upper"], read["nominal"])
        )
    elif not within_cap:
        status = PARAMETER_BAND_TOO_WIDE
        findings.append(
            "%s: the band is %.4g of nominal either side against a %.4g cap; a "
            "band that wide is a range, not a tolerance"
            % (read["name"], relative_half_width, cap)
        )
    elif not resolvable:
        status = PARAMETER_BAND_BELOW_RESOLUTION
        findings.append(
            "%s: the band half-width is %.4g times the measurement uncertainty "
            "against a %.4g ratio; the parameter is recorded, not controlled"
            % (read["name"], uncertainty_ratio, min_ratio)
        )
    else:
        status = PARAMETER_CONTROLLED

    result = dict(read)
    result.update(
        {
            "half_width": half_width,
            "relative_half_width": relative_half_width,
            "uncertainty_ratio": uncertainty_ratio,
            "brackets_nominal": brackets,
            "within_width_cap": within_cap,
            "resolvable": resolvable,
            "status": status,
            "findings": findings,
        }
    )
    return result


def evidence_standing(evidence_reference, evidence_date, document_issue_date):
    """Decide whether the qualification evidence discharges the commitment.

    Evidence dated before the document that committed to the process was
    generated under some other commitment. Accepting it inverts the gate
    the document exists to be.
    """
    issued = validate_iso_date(document_issue_date, "document issue date")
    if evidence_reference is None:
        return {
            "reference": None,
            "date": None,
            "present": False,
            "postdates_document": False,
            "findings": [
                "the entry cites no qualification evidence, so the process was "
                "declared and never put forward"
            ],
        }
    reference = validate_identifier(evidence_reference, "evidence reference")
    dated = validate_iso_date(evidence_date, "evidence date")
    postdates = dated >= issued
    findings = []
    if not postdates:
        findings.append(
            "evidence %s is dated %s, before the document was issued on %s; it "
            "was generated under some other commitment"
            % (reference, dated.isoformat(), issued.isoformat())
        )
    return {
        "reference": reference,
        "date": dated.isoformat(),
        "present": True,
        "postdates_document": postdates,
        "findings": findings,
    }


def assess_process_entry(entry, document_issue_date, policy=None):
    """Grade one declared process entry in the production control document."""
    _require_mapping("process entry", entry)
    settings = _policy(policy)
    required = _require_mapping(
        "required_processes", settings.get("required_processes")
    )

    process = validate_identifier(entry.get("process"), "process name")
    criticality = entry.get("criticality") or required.get(process)
    if criticality not in CRITICALITY_KINDS:
        raise ValueError(
            "criticality for %s must be one of %s, got %r"
            % (process, ", ".join(CRITICALITY_KINDS), criticality)
        )

    findings = []
    controlling = entry.get("controlling_document")
    has_document = bool(
        isinstance(controlling, str) and controlling.strip()
    )
    if not has_document:
        findings.append(
            "%s: the entry names the process and no production document that "
            "controls it; naming a process is half a declaration" % process
        )

    parameters = entry.get("control_parameters")
    if parameters is None:
        parameters = []
    if not isinstance(parameters, (list, tuple)):
        raise ValueError(
            "control_parameters for %s must be a sequence" % process
        )
    graded = [
        assess_control_parameter(p, settings, i) for i, p in enumerate(parameters)
    ]
    seen = []
    for parameter in graded:
        if parameter["name"] in seen:
            raise ValueError(
                "control parameter %r is declared twice under %s"
                % (parameter["name"], process)
            )
        seen.append(parameter["name"])
        findings.extend("%s: %s" % (process, f) for f in parameter["findings"])

    evidence = evidence_standing(
        entry.get("evidence_reference"),
        entry.get("evidence_date"),
        document_issue_date,
    )
    findings.extend("%s: %s" % (process, f) for f in evidence["findings"])

    defective = [p for p in graded if p["status"] != PARAMETER_CONTROLLED]

    if not has_document:
        status = ENTRY_DOCUMENT_MISSING
    elif not graded:
        status = ENTRY_PARAMETERS_MISSING
        findings.append(
            "%s: the controlling document is named and no control parameter is "
            "declared, so nothing about the process is held anywhere" % process
        )
    elif defective:
        status = ENTRY_PARAMETER_DEFECT
    elif not evidence["present"]:
        status = ENTRY_EVIDENCE_MISSING
    elif not evidence["postdates_document"]:
        status = ENTRY_EVIDENCE_PREDATES_DOCUMENT
    else:
        status = ENTRY_ACCEPTED

    return {
        "process": process,
        "criticality": criticality,
        "controlling_document": controlling.strip() if has_document else None,
        "control_parameters": graded,
        "defective_parameters": [p["name"] for p in defective],
        "evidence": evidence,
        "status": status,
        "accepted": status == ENTRY_ACCEPTED,
        "findings": findings,
    }


def process_coverage(entries, policy=None):
    """Compare the declared process set against the set the glass needs.

    Coverage is measured against the processes a coverglass is genuinely
    made by, not against the list the supplier happened to submit. A
    process that never reaches the document is never put forward for
    qualification.
    """
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence of process entries")
    settings = _policy(policy)
    required = _require_mapping(
        "required_processes", settings.get("required_processes")
    )

    declared = []
    for entry in entries:
        _require_mapping("process entry", entry)
        name = validate_identifier(entry.get("process"), "process name")
        if name in declared:
            raise ValueError("process %r is declared twice" % name)
        declared.append(name)

    missing = sorted(name for name in required if name not in declared)
    missing_critical = [
        name for name in missing if required[name] == "qualification-critical"
    ]
    extra = sorted(name for name in declared if name not in required)

    findings = []
    for name in missing_critical:
        findings.append(
            "%s is a process the coverglass depends on and the document never "
            "declares it, so it is never put forward for qualification" % name
        )
    for name in missing:
        if name not in missing_critical:
            findings.append(
                "%s is undeclared; it is control-only, so this is a gap in the "
                "baseline rather than a missing qualification" % name
            )
    for name in extra:
        findings.append(
            "%s is declared and is not in the required set; it is carried as "
            "extra baseline and nothing depends on it" % name
        )
    return {
        "declared": sorted(declared),
        "missing": missing,
        "missing_critical": sorted(missing_critical),
        "extra": extra,
        "covers_required_set": not missing,
        "covers_critical_set": not missing_critical,
        "findings": findings,
    }


def assess_production_control_document(spec):
    """Full clause 8.4 review of a coverglass production control document."""
    _require_mapping("spec", spec)
    document_id = validate_identifier(spec.get("document_id"), "document_id")
    issue_date = validate_iso_date(spec.get("issue_date"), "issue_date")
    campaign_start = validate_iso_date(
        spec.get("campaign_start_date"), "campaign_start_date"
    )
    entries = spec.get("entries")
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("spec must carry a non-empty entries sequence")
    policy = spec.get("policy")
    settings = _policy(policy)

    coverage = process_coverage(entries, settings)
    assessments = [
        assess_process_entry(entry, issue_date.isoformat(), settings)
        for entry in entries
    ]

    findings = list(coverage["findings"])
    for assessment in assessments:
        findings.extend(assessment["findings"])

    precedes_campaign = issue_date <= campaign_start
    if not precedes_campaign:
        findings.append(
            "the document is issued %s and the campaign started %s; a gate "
            "written after the work is a record, not a gate"
            % (issue_date.isoformat(), campaign_start.isoformat())
        )

    accepted = [a for a in assessments if a["accepted"]]
    rejected = sorted(a["process"] for a in assessments if not a["accepted"])
    accepted_share = len(accepted) / len(assessments)

    if (
        coverage["covers_required_set"]
        and precedes_campaign
        and not rejected
    ):
        verdict = DOCUMENT_ACCEPTED
    else:
        verdict = DOCUMENT_INCOMPLETE

    weakest = min(
        assessments,
        key=lambda a: (
            _ENTRY_RANK[a["status"]],
            0 if a["criticality"] == "qualification-critical" else 1,
            a["process"],
        ),
    )
    return {
        "document_id": document_id,
        "issue_date": issue_date.isoformat(),
        "campaign_start_date": campaign_start.isoformat(),
        "precedes_campaign": precedes_campaign,
        "coverage": coverage,
        "entries": assessments,
        "rejected_entries": rejected,
        "accepted_share": accepted_share,
        "weakest_entry": weakest["process"],
        "verdict": verdict,
        "fully_accepted": verdict == DOCUMENT_ACCEPTED
        and _at_least(accepted_share, 1.0),
        "findings": findings,
    }
