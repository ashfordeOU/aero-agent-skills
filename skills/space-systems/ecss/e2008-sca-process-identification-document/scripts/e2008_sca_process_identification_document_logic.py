#!/usr/bin/env python3
"""Process identification document for a solar cell assembly campaign.

Anchor: ECSS-E-ST-20-08C clause 6.2. The supplier prepares a production
control document that identifies the cell assembly processes to be qualified.
The procedure below is a paraphrase into implementable steps; no standard text
is reproduced.

What the document has to do
---------------------------
    coverage    every process the assembly is actually built with appears in
                the document -- a process nobody wrote down is a process
                nobody qualified
    control     each declared process names the production document that
                controls it and the parameters that production document
                holds, each parameter carrying a tolerance band that
                brackets its nominal
    tightness   a band drawn so wide that any build sits inside it controls
                nothing, so the band is measured against the nominal and not
                merely checked for existence
    evidence    a process the assembly depends on carries a reference to the
                qualification evidence that closes it
    timing      the document is issued no later than the start of the
                qualification campaign, so it defines what was to be built
                rather than recording what was built

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime
import math

__all__ = [
    "REQUIRED_SCA_PROCESSES",
    "CRITICALITY_KINDS",
    "DEFAULT_PID_POLICY",
    "BAND_TOLERANCE_REL",
    "PARAMETER_CONTROLLED",
    "PARAMETER_BAND_EXCLUDES_NOMINAL",
    "PARAMETER_BAND_TOO_WIDE",
    "PROCESS_ENTRY_ACCEPTED",
    "PROCESS_DOCUMENT_MISSING",
    "PROCESS_PARAMETERS_MISSING",
    "PROCESS_PARAMETER_DEFECT",
    "PROCESS_EVIDENCE_MISSING",
    "DOCUMENT_ACCEPTED",
    "DOCUMENT_INCOMPLETE",
    "validate_identifier",
    "validate_real",
    "validate_iso_date",
    "validate_control_parameter",
    "assess_control_parameter",
    "assess_process_entry",
    "process_coverage",
    "document_precedes_campaign",
    "assess_process_identification_document",
]

# The processes a solar cell assembly is built with, and whether the assembly
# depends on the process holding (qualification-critical) or the process is
# held by production control alone.
REQUIRED_SCA_PROCESSES = {
    "sca-surface-preparation": "control-only",
    "sca-cell-interconnector-welding": "qualification-critical",
    "sca-coverglass-bonding": "qualification-critical",
    "sca-cell-to-substrate-bonding": "qualification-critical",
    "sca-bypass-diode-attachment": "qualification-critical",
    "sca-bus-bar-attachment": "control-only",
    "sca-cleaning-and-handling": "control-only",
}

CRITICALITY_KINDS = ("qualification-critical", "control-only")

# Per-parameter outcomes.
PARAMETER_CONTROLLED = "parameter-controlled"
PARAMETER_BAND_EXCLUDES_NOMINAL = "parameter-band-excludes-nominal"
PARAMETER_BAND_TOO_WIDE = "parameter-band-too-wide"

# Per-process outcomes, ranked worst first by _PROCESS_RANK below.
PROCESS_ENTRY_ACCEPTED = "process-entry-accepted"
PROCESS_DOCUMENT_MISSING = "process-controlling-document-missing"
PROCESS_PARAMETERS_MISSING = "process-control-parameters-missing"
PROCESS_PARAMETER_DEFECT = "process-control-parameter-defect"
PROCESS_EVIDENCE_MISSING = "process-qualification-evidence-missing"

# Document outcomes.
DOCUMENT_ACCEPTED = "process-identification-document-accepted"
DOCUMENT_INCOMPLETE = "process-identification-document-incomplete"

# A controlling document reference is worth nothing if the parameters it is
# supposed to hold were never written down, and parameters are worth nothing
# if nobody can say which document holds them; the missing reference is
# reported first because it is the one that has to be raised with the
# supplier before anything else can be graded.
_PROCESS_RANK = {
    PROCESS_DOCUMENT_MISSING: 0,
    PROCESS_PARAMETERS_MISSING: 1,
    PROCESS_PARAMETER_DEFECT: 2,
    PROCESS_EVIDENCE_MISSING: 3,
    PROCESS_ENTRY_ACCEPTED: 4,
}

DEFAULT_PID_POLICY = {
    # Widest tolerance band, as a fraction of the nominal, that still counts
    # as control of the parameter.
    "max_relative_band": 0.20,
    # Share of the required process set the document has to declare.
    "min_process_coverage": 1.0,
    # A control-only process may close without qualification evidence.
    "require_evidence_for_control_only": False,
}

# Band edges and coverage shares are float arithmetic. A value that physically
# equals its limit can land a few units in the last place either side of it,
# so the comparisons absorb that representation error rather than moving the
# limit itself.
BAND_TOLERANCE_REL = 1e-9


def validate_identifier(value, label):
    """Return value as a trimmed, non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty identifier string" % label)
    return value.strip()


def validate_real(value, label):
    """Return value as a finite real number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def validate_iso_date(value, label):
    """Return an ISO-8601 calendar date parsed from value."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO-8601 date string (YYYY-MM-DD)" % label)
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError("%s is not a valid ISO-8601 date: %r" % (label, value))


def validate_control_parameter(parameter, index=0):
    """Return one validated control parameter of a declared process."""
    if not isinstance(parameter, dict):
        raise ValueError("control parameter %d must be a mapping" % index)
    name = validate_identifier(
        parameter.get("parameter"), "control parameter %d name" % index
    )
    for key in ("nominal", "lower", "upper"):
        if key not in parameter:
            raise ValueError("control parameter %r is missing '%s'" % (name, key))
    nominal = validate_real(parameter["nominal"], "nominal of %r" % name)
    lower = validate_real(parameter["lower"], "lower of %r" % name)
    upper = validate_real(parameter["upper"], "upper of %r" % name)
    if lower > upper:
        raise ValueError(
            "tolerance band of %r is inverted: lower %g above upper %g"
            % (name, lower, upper)
        )
    units = parameter.get("units")
    if units is not None:
        units = validate_identifier(units, "units of %r" % name)
    return {
        "parameter": name,
        "nominal": nominal,
        "lower": lower,
        "upper": upper,
        "units": units,
    }


def assess_control_parameter(parameter, policy=None):
    """Grade one control parameter against the band policy."""
    settings = _policy(policy)
    row = validate_control_parameter(parameter)
    width = row["upper"] - row["lower"]
    magnitude = abs(row["nominal"])
    if magnitude > 0.0:
        relative_band = width / magnitude
    else:
        relative_band = None

    lower_ok = row["lower"] < row["nominal"] or math.isclose(
        row["lower"], row["nominal"], rel_tol=BAND_TOLERANCE_REL, abs_tol=0.0
    )
    upper_ok = row["nominal"] < row["upper"] or math.isclose(
        row["nominal"], row["upper"], rel_tol=BAND_TOLERANCE_REL, abs_tol=0.0
    )
    brackets_nominal = bool(lower_ok and upper_ok)

    limit = settings["max_relative_band"]
    if relative_band is None:
        too_wide = False
    else:
        too_wide = relative_band > limit and not math.isclose(
            relative_band, limit, rel_tol=BAND_TOLERANCE_REL, abs_tol=0.0
        )

    if not brackets_nominal:
        verdict = PARAMETER_BAND_EXCLUDES_NOMINAL
    elif too_wide:
        verdict = PARAMETER_BAND_TOO_WIDE
    else:
        verdict = PARAMETER_CONTROLLED

    row.update(
        {
            "band_width": width,
            "relative_band": relative_band,
            "brackets_nominal": brackets_nominal,
            "verdict": verdict,
        }
    )
    return row


def _policy(policy):
    """Return the effective policy, defaults filled in and validated."""
    settings = dict(DEFAULT_PID_POLICY)
    if policy is None:
        return settings
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    for key, value in policy.items():
        if key not in DEFAULT_PID_POLICY:
            raise ValueError("policy carries unknown key '%s'" % key)
        settings[key] = value
    band = validate_real(settings["max_relative_band"], "max_relative_band")
    if band <= 0.0:
        raise ValueError("max_relative_band must be positive, got %g" % band)
    settings["max_relative_band"] = band
    coverage = validate_real(settings["min_process_coverage"], "min_process_coverage")
    if coverage < 0.0 or coverage > 1.0:
        raise ValueError("min_process_coverage must lie in [0, 1], got %g" % coverage)
    settings["min_process_coverage"] = coverage
    flag = settings["require_evidence_for_control_only"]
    if not isinstance(flag, bool):
        raise ValueError("require_evidence_for_control_only must be a boolean")
    return settings


def assess_process_entry(entry, policy=None):
    """Grade one declared process entry of the identification document."""
    settings = _policy(policy)
    if not isinstance(entry, dict):
        raise ValueError("process entry must be a mapping")
    name = validate_identifier(entry.get("process"), "process name")
    if name not in REQUIRED_SCA_PROCESSES:
        raise ValueError(
            "process %r is not one of the cell assembly processes this document "
            "covers" % name
        )
    criticality = REQUIRED_SCA_PROCESSES[name]

    document_ref = entry.get("controlling_document")
    if document_ref is not None:
        document_ref = validate_identifier(
            document_ref, "controlling_document of %r" % name
        )

    raw_parameters = entry.get("control_parameters", [])
    if not isinstance(raw_parameters, (list, tuple)):
        raise ValueError("control_parameters of %r must be a sequence" % name)
    graded = [assess_control_parameter(p, settings) for p in raw_parameters]
    seen = [p["parameter"] for p in graded]
    if len(set(seen)) != len(seen):
        raise ValueError("control parameter names of %r must be unique" % name)

    evidence_ref = entry.get("qualification_evidence")
    if evidence_ref is not None:
        evidence_ref = validate_identifier(
            evidence_ref, "qualification_evidence of %r" % name
        )
    evidence_needed = criticality == "qualification-critical" or settings[
        "require_evidence_for_control_only"
    ]

    defective = [p for p in graded if p["verdict"] != PARAMETER_CONTROLLED]

    if document_ref is None:
        verdict = PROCESS_DOCUMENT_MISSING
    elif not graded:
        verdict = PROCESS_PARAMETERS_MISSING
    elif defective:
        verdict = PROCESS_PARAMETER_DEFECT
    elif evidence_needed and evidence_ref is None:
        verdict = PROCESS_EVIDENCE_MISSING
    else:
        verdict = PROCESS_ENTRY_ACCEPTED

    return {
        "process": name,
        "criticality": criticality,
        "controlling_document": document_ref,
        "qualification_evidence": evidence_ref,
        "evidence_required": evidence_needed,
        "parameters": graded,
        "defective_parameters": [p["parameter"] for p in defective],
        "verdict": verdict,
        "rank": _PROCESS_RANK[verdict],
    }


def process_coverage(entries):
    """Return the share of the required process set the document declares."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence of graded process entries")
    declared = set()
    for entry in entries:
        if not isinstance(entry, dict) or "process" not in entry:
            raise ValueError("each entry must be a mapping carrying 'process'")
        declared.add(entry["process"])
    total = len(REQUIRED_SCA_PROCESSES)
    undeclared = sorted(set(REQUIRED_SCA_PROCESSES) - declared)
    return {
        "declared_count": len(declared),
        "required_count": total,
        "undeclared_processes": undeclared,
        "coverage_share": len(declared) / total,
    }


def document_precedes_campaign(issue_date, campaign_start_date):
    """Return True when the document was issued no later than campaign start."""
    issued = validate_iso_date(issue_date, "issue_date")
    start = validate_iso_date(campaign_start_date, "campaign_start_date")
    return issued <= start


def assess_process_identification_document(spec):
    """Run the full clause 6.2 assessment of a process identification document.

    spec keys: document_id, issue_date, campaign_start_date, processes, and
    an optional policy mapping.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("document_id", "issue_date", "campaign_start_date", "processes"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    document_id = validate_identifier(spec["document_id"], "document_id")
    settings = _policy(spec.get("policy"))

    raw = spec["processes"]
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError("processes must be a non-empty sequence of entries")
    entries = [assess_process_entry(e, settings) for e in raw]
    names = [e["process"] for e in entries]
    if len(set(names)) != len(names):
        raise ValueError("process entries must be unique, got %r" % (names,))

    coverage = process_coverage(entries)
    issued_in_time = document_precedes_campaign(
        spec["issue_date"], spec["campaign_start_date"]
    )

    limit = settings["min_process_coverage"]
    coverage_met = coverage["coverage_share"] > limit or math.isclose(
        coverage["coverage_share"], limit, rel_tol=BAND_TOLERANCE_REL, abs_tol=0.0
    )

    findings = []
    for name in coverage["undeclared_processes"]:
        findings.append(
            "document %s does not identify the %s process, so it was never "
            "put forward for qualification" % (document_id, name)
        )
    for entry in sorted(entries, key=lambda e: (e["rank"], e["process"])):
        if entry["verdict"] == PROCESS_DOCUMENT_MISSING:
            findings.append(
                "process %s names no controlling production document"
                % entry["process"]
            )
        elif entry["verdict"] == PROCESS_PARAMETERS_MISSING:
            findings.append(
                "process %s declares no control parameter, so document %s holds "
                "nothing" % (entry["process"], entry["controlling_document"])
            )
        elif entry["verdict"] == PROCESS_PARAMETER_DEFECT:
            findings.append(
                "process %s carries an uncontrolled parameter: %s"
                % (entry["process"], ", ".join(entry["defective_parameters"]))
            )
        elif entry["verdict"] == PROCESS_EVIDENCE_MISSING:
            findings.append(
                "process %s is depended on by the assembly but references no "
                "qualification evidence" % entry["process"]
            )
    if not coverage_met:
        findings.append(
            "declared process coverage %.3f is below the required share %.3f"
            % (coverage["coverage_share"], limit)
        )
    if not issued_in_time:
        findings.append(
            "document %s was issued after the qualification campaign started, so "
            "it records the build instead of defining it" % document_id
        )

    grouped = {}
    for entry in entries:
        grouped.setdefault(entry["verdict"], []).append(entry["process"])
    for key in grouped:
        grouped[key].sort()

    accepted = [e for e in entries if e["verdict"] == PROCESS_ENTRY_ACCEPTED]
    return {
        "document_id": document_id,
        "entries": entries,
        "entries_by_verdict": grouped,
        "coverage": coverage,
        "coverage_met": coverage_met,
        "accepted_share": len(accepted) / len(entries),
        "issued_before_campaign": issued_in_time,
        "findings": findings,
        "verdict": DOCUMENT_ACCEPTED if not findings else DOCUMENT_INCOMPLETE,
    }
