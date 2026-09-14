#!/usr/bin/env python3
"""Supplier production control document for the bare cell design being qualified.

Anchor: ECSS-E-ST-20-08C clause 7.2. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Before a bare cell design is qualified the supplier writes the document
that says how the cell is made: which process steps the design depends
on, which floor instruction controls each one, what the controlled
parameters are and how wide their bands run, and on which line and at
which site the steps are run. The document is what a qualification
result is later attached to, so its job is to fix the build before the
campaign rather than to describe it afterwards.

Four things are graded, and they fail for different reasons.

    coverage     a step that never reaches the document was never put
                 forward for qualification, so coverage is measured
                 against the steps a cell is genuinely built with, not
                 against the list the supplier happened to submit
    control      naming a step is half a declaration; the other half is
                 the production document that controls it and the
                 parameters that document holds, each with a band that
                 brackets its nominal and is narrow enough to control
                 anything at all
    line binding a cell line is a site, not a recipe. A step declared on
                 a line other than the one being qualified makes the
                 qualification result belong to different hardware
    baseline     the document names the cell design it controls, and a
                 document naming a different design is qualifying
                 something else; the issue date has to precede the
                 campaign for the same reason

The required step set, the band width cap and the coverage minimum below
are declared project policy, not physical constants; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REQUIRED_PROCESS_STEPS = (
    "wafer-preparation",
    "epitaxial-growth",
    "junction-formation",
    "antireflective-coating",
    "front-metallisation",
    "rear-metallisation",
    "mesa-edge-isolation",
    "contact-anneal",
    "cell-electrical-sorting",
)

STEP_ACCEPTED = "step-accepted"
STEP_OFF_QUALIFIED_LINE = "step-off-qualified-line"
STEP_PARAMETER_UNCONTROLLED = "step-parameter-uncontrolled"
STEP_NO_PARAMETER = "step-declares-no-parameter"
STEP_NO_CONTROLLING_DOCUMENT = "step-no-controlling-document"

STEP_RANK = {
    STEP_NO_CONTROLLING_DOCUMENT: 0,
    STEP_NO_PARAMETER: 1,
    STEP_PARAMETER_UNCONTROLLED: 2,
    STEP_OFF_QUALIFIED_LINE: 3,
    STEP_ACCEPTED: 4,
}

DOCUMENT_ACCEPTED = "process-document-accepted"
DOCUMENT_REJECTED = "process-document-rejected"

DEFAULT_DOCUMENT_POLICY = {
    "max_band_width_fraction": 0.10,
    "min_coverage_share": 1.0,
    "required_process_steps": REQUIRED_PROCESS_STEPS,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_number(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A band width is a quotient of a span and a nominal while the cap is a
    round fraction, so a band drawn exactly to the cap can evaluate a
    unit in the last place above it. The comparison absorbs that; the cap
    stays as declared.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def parse_iso_date(value, name="date"):
    """Read a YYYY-MM-DD date into a comparable tuple."""
    text = _require_label(name, value)
    parts = text.split("-")
    if len(parts) != 3:
        raise ValueError("%s must be an ISO YYYY-MM-DD date, got %r" % (name, value))
    try:
        year, month, day = (int(part) for part in parts)
    except ValueError:
        raise ValueError(
            "%s must be an ISO YYYY-MM-DD date, got %r" % (name, value)
        )
    if not 1 <= month <= 12 or not 1 <= day <= 31 or year < 1:
        raise ValueError("%s is not a calendar date: %r" % (name, value))
    return (year, month, day)


def evaluate_control_parameter(parameter, max_band_width_fraction):
    """Grade one controlled parameter of a bare cell process step.

    A band has to bracket the nominal the line builds to, and it has to
    be narrow enough that leaving it means something. A band no realistic
    build can leave records the step instead of controlling it.
    """
    _require_mapping("parameter", parameter)
    cap = _require_positive("max_band_width_fraction", max_band_width_fraction)
    name = _require_label("parameter name", parameter.get("name"))
    nominal = _require_number("nominal", parameter.get("nominal"))
    if nominal == 0.0:
        raise ValueError(
            "parameter %r declares a zero nominal, so no band width can be "
            "expressed as a fraction of it" % name
        )
    low = _require_number("band_low", parameter.get("band_low"))
    high = _require_number("band_high", parameter.get("band_high"))
    if high < low:
        raise ValueError(
            "parameter %r declares an inverted band %r..%r" % (name, low, high)
        )

    brackets = low <= nominal <= high
    width_fraction = (high - low) / abs(nominal)
    narrow_enough = _at_most(width_fraction, cap)

    findings = []
    if not brackets:
        findings.append(
            "parameter %s declares a band %.6g..%.6g that does not contain its "
            "own nominal %.6g; production builds to the nominal and inspection "
            "reads the band" % (name, low, high, nominal)
        )
    if not narrow_enough:
        findings.append(
            "parameter %s declares a band %.4g wide as a fraction of nominal "
            "against a %.4g cap; a band no plausible build can leave records "
            "the step rather than controlling it" % (name, width_fraction, cap)
        )
    return {
        "name": name,
        "nominal": nominal,
        "band": (low, high),
        "brackets_nominal": brackets,
        "band_width_fraction": width_fraction,
        "controlled": brackets and narrow_enough,
        "findings": findings,
    }


def assess_process_step(step, qualified_line, policy=None):
    """Grade one declared process step of the bare cell production document."""
    _require_mapping("step", step)
    settings = dict(DEFAULT_DOCUMENT_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    required = tuple(settings.get("required_process_steps"))
    cap = _require_positive(
        "max_band_width_fraction", settings.get("max_band_width_fraction")
    )
    line = _require_label("qualified_line", qualified_line)

    name = _require_label("step name", step.get("name"))
    if name not in required:
        raise ValueError(
            "process step %r is not one the required bare cell process set "
            "names; declare it in the required set or correct the document"
            % name
        )

    controlling_document = step.get("controlling_document")
    parameters = step.get("control_parameters") or []
    if not isinstance(parameters, (list, tuple)):
        raise ValueError(
            "process step %r must carry a sequence of control parameters" % name
        )
    graded = [evaluate_control_parameter(p, cap) for p in parameters]
    uncontrolled = [p["name"] for p in graded if not p["controlled"]]

    findings = []
    for parameter in graded:
        findings.extend("%s: %s" % (name, f) for f in parameter["findings"])

    step_line = step.get("production_line")
    on_qualified_line = True
    if step_line is not None:
        on_qualified_line = _require_label("production_line", step_line) == line
        if not on_qualified_line:
            findings.append(
                "%s: the step is declared on line %s while the design is being "
                "qualified on line %s; a cell line is a site, so the result "
                "would belong to different hardware" % (name, step_line, line)
            )

    if controlling_document is None:
        findings.append(
            "%s: no production document is cited, so the step has a title and "
            "no floor instruction behind it" % name
        )
        verdict = STEP_NO_CONTROLLING_DOCUMENT
    elif not graded:
        _require_label("controlling_document", controlling_document)
        findings.append(
            "%s: a controlling document is cited and no parameter is declared, "
            "so nothing about the step is actually held" % name
        )
        verdict = STEP_NO_PARAMETER
    elif uncontrolled:
        _require_label("controlling_document", controlling_document)
        verdict = STEP_PARAMETER_UNCONTROLLED
    elif not on_qualified_line:
        _require_label("controlling_document", controlling_document)
        verdict = STEP_OFF_QUALIFIED_LINE
    else:
        _require_label("controlling_document", controlling_document)
        verdict = STEP_ACCEPTED

    return {
        "name": name,
        "controlling_document": controlling_document,
        "production_line": step_line,
        "on_qualified_line": on_qualified_line,
        "parameters": graded,
        "uncontrolled_parameters": sorted(uncontrolled),
        "verdict": verdict,
        "findings": findings,
    }


def process_coverage(declared_names, required_steps=REQUIRED_PROCESS_STEPS):
    """Measure the declared steps against the steps a bare cell is built with."""
    if not isinstance(declared_names, (list, tuple)):
        raise ValueError("declared_names must be a sequence of step names")
    required = tuple(required_steps)
    if not required:
        raise ValueError(
            "an empty required process set gives the document nothing to be "
            "measured against"
        )
    declared = set()
    for item in declared_names:
        declared.add(_require_label("declared step", item))
    covered = sorted(name for name in required if name in declared)
    missing = sorted(name for name in required if name not in declared)
    return {
        "required": len(required),
        "covered": len(covered),
        "covered_steps": covered,
        "missing_steps": missing,
        "coverage_share": len(covered) / len(required),
    }


def design_baseline_match(document_design_id, qualified_design_id):
    """Check the document names the cell design actually under qualification."""
    declared = _require_label("document_design_id", document_design_id)
    qualified = _require_label("qualified_design_id", qualified_design_id)
    matches = declared == qualified
    findings = []
    if not matches:
        findings.append(
            "the document controls design %s while design %s is being "
            "qualified; the campaign would attach to the wrong baseline"
            % (declared, qualified)
        )
    return {
        "document_design_id": declared,
        "qualified_design_id": qualified,
        "matches": matches,
        "findings": findings,
    }


def issue_precedes_campaign(issue_date, campaign_start_date):
    """Check the document was issued before the qualification campaign began."""
    issued = parse_iso_date(issue_date, "issue_date")
    started = parse_iso_date(campaign_start_date, "campaign_start_date")
    precedes = issued <= started
    findings = []
    if not precedes:
        findings.append(
            "the document was issued on %s and the campaign began on %s, so it "
            "records the build instead of defining it"
            % (issue_date, campaign_start_date)
        )
    return {
        "issue_date": issue_date,
        "campaign_start_date": campaign_start_date,
        "precedes_campaign": precedes,
        "findings": findings,
    }


def assess_bare_cell_process_document(case):
    """Full clause 7.2 assessment of the bare cell production control document."""
    _require_mapping("case", case)
    settings = dict(DEFAULT_DOCUMENT_POLICY)
    if case.get("policy") is not None:
        settings.update(_require_mapping("policy", case.get("policy")))
    required = tuple(settings.get("required_process_steps"))
    minimum = _require_number("min_coverage_share", settings.get("min_coverage_share"))

    qualified_line = _require_label("qualified_line", case.get("qualified_line"))
    steps = case.get("process_steps")
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("case must carry a non-empty process_steps sequence")

    assessments = [
        assess_process_step(step, qualified_line, settings) for step in steps
    ]
    seen = set()
    for assessment in assessments:
        if assessment["name"] in seen:
            raise ValueError(
                "process step %r is declared twice in one document"
                % assessment["name"]
            )
        seen.add(assessment["name"])

    findings = []
    for assessment in assessments:
        findings.extend(assessment["findings"])

    coverage = process_coverage([a["name"] for a in assessments], required)
    for missing in coverage["missing_steps"]:
        findings.append(
            "the cell depends on %s and the document never declares it, so it "
            "was never put forward for qualification" % missing
        )
    coverage_met = _at_least(coverage["coverage_share"], minimum)

    baseline = design_baseline_match(
        case.get("document_design_id"), case.get("qualified_design_id")
    )
    findings.extend(baseline["findings"])

    precedence = issue_precedes_campaign(
        case.get("issue_date"), case.get("campaign_start_date")
    )
    findings.extend(precedence["findings"])

    accepted = [a for a in assessments if a["verdict"] == STEP_ACCEPTED]
    accepted_share = len(accepted) / len(assessments)
    grouped = {}
    for assessment in assessments:
        grouped.setdefault(assessment["verdict"], []).append(assessment["name"])
    for names in grouped.values():
        names.sort()

    if (
        len(accepted) == len(assessments)
        and coverage_met
        and baseline["matches"]
        and precedence["precedes_campaign"]
    ):
        verdict = DOCUMENT_ACCEPTED
    else:
        verdict = DOCUMENT_REJECTED

    weakest = min(
        assessments, key=lambda a: (STEP_RANK[a["verdict"]], a["name"])
    )
    return {
        "qualified_design_id": baseline["qualified_design_id"],
        "qualified_line": qualified_line,
        "assessments": assessments,
        "grouped_steps": grouped,
        "coverage": coverage,
        "coverage_meets_minimum": coverage_met,
        "baseline": baseline,
        "precedence": precedence,
        "accepted_share": accepted_share,
        "weakest_step": weakest["name"],
        "verdict": verdict,
        "findings": findings,
    }
