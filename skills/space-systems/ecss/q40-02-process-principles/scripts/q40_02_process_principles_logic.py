"""Hazard-analysis process: concept, implementation, documentation, reviews.

Anchor: the early clauses of ECSS-Q-HB/ST-40-02 on the hazard analysis concept
and its role in the safety programme -- process overview, implementation and
documentation rules, and the integration of the analysis with the safety
reviews. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. A hazard-analysis process is a definition, not an activity log. It has
   mandatory elements, and a definition missing one of them will still produce
   analyses -- it just will not produce the same analysis twice.
2. Each analysis level a programme declares has to carry a technique that suits
   that level. A fault tree is not a functional-level technique and a
   functional hazard analysis is not a subsystem one; pairing them the wrong
   way round produces work nobody can use.
3. The analysis is iterative and the iterations are tied to the safety reviews.
   A process whose iterations do not reach the mandatory reviews has an
   analysis that arrives after the decision it was supposed to inform.
4. The documentation set is what survives the programme. An analysis with no
   hazard log and no traceability to requirements is an opinion held once.
5. Update triggers are what keep the analysis alive between reviews: design
   change, anomaly, operational change. Without them the process is a one-off.
6. Grade the definition and say which elements are missing and why each one
   matters, rather than returning a single score.
"""

__all__ = [
    "PROCESS_ELEMENTS",
    "ANALYSIS_LEVELS",
    "TECHNIQUES_BY_LEVEL",
    "MANDATORY_REVIEWS",
    "REVIEW_MILESTONES",
    "DOCUMENTATION_ITEMS",
    "MANDATORY_DOCUMENTATION",
    "UPDATE_TRIGGERS",
    "MANDATORY_UPDATE_TRIGGERS",
    "SCORE_TOLERANCE",
    "validate_process",
    "missing_elements",
    "technique_findings",
    "review_integration_findings",
    "documentation_findings",
    "update_trigger_findings",
    "element_score",
    "assess_process_definition",
]

PROCESS_ELEMENTS = (
    "scope-and-objectives",
    "analysis-levels",
    "technique-selection",
    "input-data-set",
    "iteration-points",
    "documentation-set",
    "safety-review-integration",
    "update-triggers",
)

ANALYSIS_LEVELS = ("functional", "system", "subsystem", "operational")

# Which techniques suit which level of analysis.
TECHNIQUES_BY_LEVEL = {
    "functional": ("functional-hazard-analysis", "what-if-analysis"),
    "system": (
        "fault-tree-analysis",
        "failure-modes-effects-and-criticality-analysis",
        "hazard-and-operability-study",
    ),
    "subsystem": (
        "failure-modes-effects-and-criticality-analysis",
        "zonal-analysis",
        "common-cause-analysis",
    ),
    "operational": (
        "operating-and-support-hazard-analysis",
        "task-analysis",
    ),
}

# Programme reviews in order.
REVIEW_MILESTONES = ("prr", "pdr", "cdr", "qr", "ar")

# The reviews an iteration has to reach for the analysis to inform a decision.
MANDATORY_REVIEWS = ("pdr", "cdr")

DOCUMENTATION_ITEMS = (
    "hazard-analysis-report",
    "hazard-log",
    "technique-records",
    "traceability-to-requirements",
    "assumption-register",
)

MANDATORY_DOCUMENTATION = (
    "hazard-analysis-report",
    "hazard-log",
    "traceability-to-requirements",
)

UPDATE_TRIGGERS = (
    "design-change",
    "operational-change",
    "anomaly-or-incident",
    "periodic-review",
    "requirement-change",
)

MANDATORY_UPDATE_TRIGGERS = ("design-change", "anomaly-or-incident")

# The element score is an int/int division; compare it with this slack.
SCORE_TOLERANCE = 1e-9


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _token_set(values, label, allowed):
    if not isinstance(values, (list, tuple)):
        raise ValueError("%s must be a sequence, got %r" % (label, values))
    out = []
    for value in values:
        token = _text(value, "%s entry" % label).lower()
        if token not in allowed:
            raise ValueError(
                "%s entry must be one of %s, got %r" % (label, ", ".join(allowed), value)
            )
        if token in out:
            raise ValueError("%s repeats %r" % (label, token))
        out.append(token)
    return out


def validate_process(record):
    """Return a normalised hazard-analysis process definition."""
    if not isinstance(record, dict):
        raise ValueError("process definition must be a mapping")

    declared = _token_set(
        record.get("declared_elements", []), "declared_elements", PROCESS_ELEMENTS
    )
    levels = _token_set(record.get("analysis_levels", []), "analysis_levels", ANALYSIS_LEVELS)
    if not levels:
        raise ValueError("a hazard-analysis process must declare at least one level")

    raw_techniques = record.get("techniques_by_level", {})
    if not isinstance(raw_techniques, dict):
        raise ValueError("techniques_by_level must be a mapping")
    techniques = {}
    known = set()
    for names in TECHNIQUES_BY_LEVEL.values():
        known.update(names)
    for level, names in raw_techniques.items():
        level_token = _text(level, "technique level").lower()
        if level_token not in ANALYSIS_LEVELS:
            raise ValueError(
                "techniques_by_level names an unknown level %r" % level
            )
        techniques[level_token] = _token_set(
            names, "techniques for %s" % level_token, tuple(sorted(known))
        )

    return {
        "id": _text(record.get("id"), "id"),
        "declared_elements": declared,
        "analysis_levels": levels,
        "techniques_by_level": techniques,
        "iteration_reviews": _token_set(
            record.get("iteration_reviews", []), "iteration_reviews", REVIEW_MILESTONES
        ),
        "documentation_set": _token_set(
            record.get("documentation_set", []), "documentation_set", DOCUMENTATION_ITEMS
        ),
        "update_triggers": _token_set(
            record.get("update_triggers", []), "update_triggers", UPDATE_TRIGGERS
        ),
    }


def missing_elements(record):
    """Return the mandatory process elements the definition does not declare."""
    norm = validate_process(record)
    return [item for item in PROCESS_ELEMENTS if item not in norm["declared_elements"]]


def technique_findings(record):
    """Return one finding per declared level whose techniques do not suit it."""
    norm = validate_process(record)
    findings = []
    for level in norm["analysis_levels"]:
        chosen = norm["techniques_by_level"].get(level, [])
        if not chosen:
            findings.append(
                "level %s is declared with no technique selected for it" % level
            )
            continue
        suited = TECHNIQUES_BY_LEVEL[level]
        unsuited = [name for name in chosen if name not in suited]
        if unsuited:
            findings.append(
                "level %s selects %s, which suit a different level of analysis"
                % (level, ", ".join(unsuited))
            )
    for level in norm["techniques_by_level"]:
        if level not in norm["analysis_levels"]:
            findings.append(
                "techniques are selected for level %s, which the process does not"
                " declare" % level
            )
    return findings


def review_integration_findings(record):
    """Return the findings on how the iterations meet the safety reviews."""
    norm = validate_process(record)
    findings = []
    missing = [name for name in MANDATORY_REVIEWS if name not in norm["iteration_reviews"]]
    for name in missing:
        findings.append(
            "no analysis iteration is tied to %s, so the decision taken there is"
            " not informed by it" % name
        )
    if "operational" in norm["analysis_levels"] and "ar" not in norm["iteration_reviews"]:
        findings.append(
            "operational analysis is declared with no iteration at ar, where the"
            " operational baseline is settled"
        )
    ordered = [
        name for name in REVIEW_MILESTONES if name in norm["iteration_reviews"]
    ]
    if len(ordered) < 2:
        findings.append(
            "fewer than two iterations are tied to reviews, so the analysis is a"
            " one-off rather than an iterative process"
        )
    return findings


def documentation_findings(record):
    """Return the findings on the documentation set the process commits to."""
    norm = validate_process(record)
    findings = []
    for item in MANDATORY_DOCUMENTATION:
        if item not in norm["documentation_set"]:
            findings.append("the documentation set omits the %s" % item.replace("-", " "))
    if (
        "hazard-log" in norm["documentation_set"]
        and "traceability-to-requirements" not in norm["documentation_set"]
    ):
        findings.append(
            "a hazard log without traceability to requirements cannot show which"
            " requirement each hazard is controlled by"
        )
    return findings


def update_trigger_findings(record):
    """Return the findings on what keeps the analysis alive between reviews."""
    norm = validate_process(record)
    findings = []
    for trigger in MANDATORY_UPDATE_TRIGGERS:
        if trigger not in norm["update_triggers"]:
            findings.append(
                "no update is triggered by %s, so the analysis will go stale on it"
                % trigger.replace("-", " ")
            )
    if "operational" in norm["analysis_levels"] and (
        "operational-change" not in norm["update_triggers"]
    ):
        findings.append(
            "operational analysis is declared but no update is triggered by an"
            " operational change"
        )
    return findings


def element_score(record):
    """Return the fraction of mandatory process elements the definition declares."""
    norm = validate_process(record)
    declared = len(
        [item for item in PROCESS_ELEMENTS if item in norm["declared_elements"]]
    )
    return declared / float(len(PROCESS_ELEMENTS))


def assess_process_definition(record):
    """Return the conformance grading of a hazard-analysis process definition."""
    norm = validate_process(record)
    missing = missing_elements(norm)
    techniques = technique_findings(norm)
    reviews = review_integration_findings(norm)
    documentation = documentation_findings(norm)
    triggers = update_trigger_findings(norm)

    findings = (
        ["the process definition omits the %s element" % item.replace("-", " ")
         for item in missing]
        + techniques
        + reviews
        + documentation
        + triggers
    )

    # A definition that cannot say what it analyses, how, or what it leaves
    # behind is not a process; the rest are gaps in one that is.
    structural = bool(missing) or bool(techniques) or bool(documentation)
    if structural:
        grade = "process-non-conformant"
    elif findings:
        grade = "process-conformant-with-gaps"
    else:
        grade = "process-conformant"

    return {
        "id": norm["id"],
        "missing_elements": missing,
        "technique_findings": techniques,
        "review_findings": reviews,
        "documentation_findings": documentation,
        "update_trigger_findings": triggers,
        "element_score": element_score(norm),
        "findings": findings,
        "conformant": grade == "process-conformant",
        "grade": grade,
    }
