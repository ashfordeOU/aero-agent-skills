"""Completion assessment for the device Validation Plan at end of implementation.

Anchor: ECSS-E-ST-20-40C clause 5.7.4 (implementation phase -- closing out the
Validation Plan so device validation activities can formally begin).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the plan record, the requirement register and the validation-case
   register; a malformed record is an input error, not a zero score.
2. Trace every requirement that owes validation to at least one validation
   case, and every case back to a live requirement.
3. Assess each case for the two things that make it runnable: a declared
   environment and a stated pass criterion.
4. Compare the configuration each case was written against with the plan
   baseline, because the implementation phase has just produced the final
   build and a case still pointing at a layout-phase build cannot be run.
5. Assess the maturity of each mandated plan section; the plan is closed out
   only when every mandated section reaches final maturity.
6. Combine the three measures into a completion index and decide whether
   validation may formally begin.
"""

import math

__all__ = [
    "COMPLETION_TOLERANCE",
    "FINAL_MATURITY",
    "MANDATED_SECTIONS",
    "MATURITY_ORDER",
    "VALIDATION_METHODS",
    "WEIGHT_COVERAGE",
    "WEIGHT_CRITERIA",
    "WEIGHT_SECTIONS",
    "validate_requirement",
    "validate_case",
    "validate_plan",
    "requirement_coverage",
    "case_readiness",
    "stale_configuration_cases",
    "section_completion",
    "completion_index",
    "assess_validation_plan_completion",
]

# A completion index is a ratio of small integers combined with float weights;
# an exact unity can land a few ULP either side. Absorb the representation
# error here rather than relaxing what "closed out" means.
COMPLETION_TOLERANCE = 1e-9

# Verification and validation methods a case may claim.
VALIDATION_METHODS = ("test", "analysis", "inspection", "review-of-design")

# Section maturity ladder. A plan section is closed out only at the top rung.
MATURITY_ORDER = {
    "draft": 0,
    "preliminary": 1,
    "consolidated": 2,
    "final": 3,
}
FINAL_MATURITY = "final"

# The sections the validation plan has to carry before validation may begin.
MANDATED_SECTIONS = (
    "validation-approach",
    "validation-cases",
    "pass-criteria",
    "validation-environment",
    "model-representativeness",
    "anomaly-handling",
)

WEIGHT_COVERAGE = 0.5
WEIGHT_CRITERIA = 0.3
WEIGHT_SECTIONS = 0.2


def _text(value, label):
    """Return a non-empty stripped string or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    stripped = value.strip()
    if not stripped:
        raise ValueError("%s must not be empty" % label)
    return stripped


def _flag(value, label, default=None):
    """Return a boolean, applying a default when the key is absent."""
    if value is None:
        if default is None:
            raise ValueError("%s must be given" % label)
        return default
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_requirement(record):
    """Return a normalised device-requirement record."""
    if not isinstance(record, dict):
        raise ValueError("requirement record must be a mapping, got %r" % (record,))
    rid = _text(record.get("id"), "requirement id")
    owes = _flag(record.get("validation_required"), "validation_required", default=True)
    category = record.get("category", "A")
    if not isinstance(category, str) or category.strip().upper() not in ("A", "B", "C", "D"):
        raise ValueError("requirement %s has an unknown criticality category %r" % (rid, category))
    return {
        "id": rid,
        "validation_required": owes,
        "category": category.strip().upper(),
    }


def validate_case(record):
    """Return a normalised validation-case record."""
    if not isinstance(record, dict):
        raise ValueError("validation case must be a mapping, got %r" % (record,))
    cid = _text(record.get("id"), "case id")
    method = _text(record.get("method"), "case %s method" % cid).lower()
    if method not in VALIDATION_METHODS:
        raise ValueError(
            "case %s declares an unknown method %r; expected one of %s"
            % (cid, method, ", ".join(VALIDATION_METHODS))
        )
    covers = record.get("requirement_ids", [])
    if isinstance(covers, str) or not isinstance(covers, (list, tuple)):
        raise ValueError("case %s requirement_ids must be a list of ids" % cid)
    traced = [_text(item, "case %s requirement id" % cid) for item in covers]
    if len(set(traced)) != len(traced):
        raise ValueError("case %s traces the same requirement twice" % cid)
    environment = record.get("environment")
    if environment is not None:
        environment = _text(environment, "case %s environment" % cid)
    criterion = record.get("pass_criterion")
    if criterion is not None:
        criterion = _text(criterion, "case %s pass_criterion" % cid)
    configuration = _text(record.get("configuration_id"), "case %s configuration_id" % cid)
    return {
        "id": cid,
        "method": method,
        "requirement_ids": traced,
        "environment": environment,
        "pass_criterion": criterion,
        "configuration_id": configuration,
    }


def validate_plan(record):
    """Return a normalised validation-plan record."""
    if not isinstance(record, dict):
        raise ValueError("plan record must be a mapping, got %r" % (record,))
    baseline = _text(record.get("baseline_configuration_id"), "baseline_configuration_id")
    issue = _text(record.get("issue"), "plan issue").lower()
    if issue not in MATURITY_ORDER:
        raise ValueError(
            "plan issue %r is not on the maturity ladder %s"
            % (issue, ", ".join(sorted(MATURITY_ORDER, key=MATURITY_ORDER.get)))
        )
    sections = record.get("sections")
    if not isinstance(sections, dict) or not sections:
        raise ValueError("plan sections must be a non-empty mapping of section to maturity")
    normalised = {}
    for name, maturity in sections.items():
        key = _text(name, "section name").lower()
        level = _text(maturity, "section %s maturity" % key).lower()
        if level not in MATURITY_ORDER:
            raise ValueError("section %s has an unknown maturity %r" % (key, maturity))
        normalised[key] = level
    unknown = sorted(set(normalised) - set(MANDATED_SECTIONS))
    if unknown:
        raise ValueError("plan carries sections outside the mandated set: %s" % ", ".join(unknown))
    return {
        "baseline_configuration_id": baseline,
        "issue": issue,
        "sections": normalised,
    }


def requirement_coverage(requirements, cases):
    """Return the traceability picture between requirements and cases."""
    if not isinstance(requirements, (list, tuple)) or not requirements:
        raise ValueError("requirements must be a non-empty sequence")
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("cases must be a non-empty sequence")
    reqs = [validate_requirement(item) for item in requirements]
    ids = [r["id"] for r in reqs]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate requirement id in the register")
    known = {r["id"]: r for r in reqs}
    checked = [validate_case(item) for item in cases]
    cids = [c["id"] for c in checked]
    if len(set(cids)) != len(cids):
        raise ValueError("duplicate validation-case id in the register")
    covered = set()
    orphans = []
    for case in checked:
        if not case["requirement_ids"]:
            orphans.append(case["id"])
            continue
        for rid in case["requirement_ids"]:
            if rid not in known:
                raise ValueError(
                    "case %s traces requirement %s, which is not in the register"
                    % (case["id"], rid)
                )
            covered.add(rid)
    owing = [r["id"] for r in reqs if r["validation_required"]]
    if not owing:
        raise ValueError("no requirement in the register owes validation")
    uncovered = sorted(r for r in owing if r not in covered)
    over_traced = sorted(
        rid for rid in covered if rid in known and not known[rid]["validation_required"]
    )
    fraction = (len(owing) - len(uncovered)) / float(len(owing))
    return {
        "cases": checked,
        "requirements": reqs,
        "owing_count": len(owing),
        "uncovered_requirement_ids": uncovered,
        "orphan_case_ids": sorted(orphans),
        "over_traced_requirement_ids": over_traced,
        "coverage_fraction": fraction,
    }


def case_readiness(cases):
    """Return which validated cases are runnable as written."""
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("cases must be a non-empty sequence")
    checked = [c if "pass_criterion" in c and "method" in c else validate_case(c) for c in cases]
    no_criterion = sorted(c["id"] for c in checked if not c["pass_criterion"])
    no_environment = sorted(
        c["id"] for c in checked if c["method"] == "test" and not c["environment"]
    )
    blocked = sorted(set(no_criterion) | set(no_environment))
    fraction = (len(checked) - len(blocked)) / float(len(checked))
    return {
        "cases_without_pass_criterion": no_criterion,
        "test_cases_without_environment": no_environment,
        "runnable_fraction": fraction,
    }


def stale_configuration_cases(cases, baseline_configuration_id):
    """Return the ids of cases still written against a superseded build."""
    baseline = _text(baseline_configuration_id, "baseline_configuration_id")
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("cases must be a non-empty sequence")
    checked = [c if "configuration_id" in c and "method" in c else validate_case(c) for c in cases]
    return sorted(c["id"] for c in checked if c["configuration_id"] != baseline)


def section_completion(plan):
    """Return the mandated-section maturity picture for the plan."""
    checked = plan if "sections" in plan and "issue" in plan else validate_plan(plan)
    sections = checked["sections"]
    missing = sorted(name for name in MANDATED_SECTIONS if name not in sections)
    immature = sorted(
        name
        for name in MANDATED_SECTIONS
        if name in sections and MATURITY_ORDER[sections[name]] < MATURITY_ORDER[FINAL_MATURITY]
    )
    done = len(MANDATED_SECTIONS) - len(missing) - len(immature)
    return {
        "missing_sections": missing,
        "immature_sections": immature,
        "section_fraction": done / float(len(MANDATED_SECTIONS)),
    }


def completion_index(coverage_fraction, runnable_fraction, section_fraction):
    """Combine the three measures into a single closure index in [0, 1]."""
    for label, value in (
        ("coverage_fraction", coverage_fraction),
        ("runnable_fraction", runnable_fraction),
        ("section_fraction", section_fraction),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        v = float(value)
        if not math.isfinite(v) or v < 0.0 or v > 1.0:
            raise ValueError("%s must lie in [0, 1], got %r" % (label, value))
    return (
        WEIGHT_COVERAGE * float(coverage_fraction)
        + WEIGHT_CRITERIA * float(runnable_fraction)
        + WEIGHT_SECTIONS * float(section_fraction)
    )


def assess_validation_plan_completion(spec):
    """Run the full clause 5.7.4 validation-plan completion assessment.

    spec keys: plan (mapping), requirements (sequence), cases (sequence).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("plan", "requirements", "cases"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    plan = validate_plan(spec["plan"])
    trace = requirement_coverage(spec["requirements"], spec["cases"])
    readiness = case_readiness(trace["cases"])
    stale = stale_configuration_cases(trace["cases"], plan["baseline_configuration_id"])
    sections = section_completion(plan)
    index = completion_index(
        trace["coverage_fraction"],
        readiness["runnable_fraction"],
        sections["section_fraction"],
    )

    findings = []
    if trace["uncovered_requirement_ids"]:
        findings.append(
            "%d requirement(s) owe validation but no case traces them: %s"
            % (
                len(trace["uncovered_requirement_ids"]),
                ", ".join(trace["uncovered_requirement_ids"]),
            )
        )
    if trace["orphan_case_ids"]:
        findings.append(
            "case(s) trace no requirement: %s" % ", ".join(trace["orphan_case_ids"])
        )
    if readiness["cases_without_pass_criterion"]:
        findings.append(
            "case(s) carry no pass criterion: %s"
            % ", ".join(readiness["cases_without_pass_criterion"])
        )
    if readiness["test_cases_without_environment"]:
        findings.append(
            "test case(s) name no validation environment: %s"
            % ", ".join(readiness["test_cases_without_environment"])
        )
    if stale:
        findings.append(
            "case(s) written against a superseded build rather than baseline %s: %s"
            % (plan["baseline_configuration_id"], ", ".join(stale))
        )
    if sections["missing_sections"]:
        findings.append("mandated section(s) absent: %s" % ", ".join(sections["missing_sections"]))
    if sections["immature_sections"]:
        findings.append(
            "mandated section(s) below final maturity: %s"
            % ", ".join(sections["immature_sections"])
        )
    if plan["issue"] != FINAL_MATURITY:
        findings.append("plan is issued as %s, not final" % plan["issue"])

    complete = math.isclose(index, 1.0, rel_tol=0.0, abs_tol=COMPLETION_TOLERANCE)
    return {
        "coverage_fraction": trace["coverage_fraction"],
        "runnable_fraction": readiness["runnable_fraction"],
        "section_fraction": sections["section_fraction"],
        "completion_index": index,
        "uncovered_requirement_ids": trace["uncovered_requirement_ids"],
        "orphan_case_ids": trace["orphan_case_ids"],
        "stale_configuration_case_ids": stale,
        "findings": findings,
        "validation_may_begin": complete and not findings,
    }
