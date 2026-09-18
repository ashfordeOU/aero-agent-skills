"""Safety verification planning: method assignment, closure milestones, reports.

Anchor: ECSS-Q-ST-40C safety verification engineering and planning, and the
clause on verification methods and verification reports. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Each safety requirement carries a severity. Severity decides which
   verification methods are admissible for it at all: the weaker methods are
   withdrawn as severity rises, because a demonstration by similarity cannot
   underwrite a catastrophic consequence.
2. A method that is admissible on paper still has to be supportable. Analysis
   standing alone for a catastrophic requirement needs correlated test data
   behind it, and similarity needs a named baseline item to be similar TO.
3. Every requirement needs a planned verification report. A verification with
   no report is an activity, not a verification: nothing downstream can cite
   it, and the close-out has nothing to point at.
4. Closure has to be planned no later than the milestone the severity demands.
   A catastrophic requirement planned to close after the qualification review
   is planned to close too late, whatever its method.
5. Roll the per-requirement findings up into a plan with a coverage ratio, a
   method mix, and a plan-level disposition.
"""

__all__ = [
    "METHODS",
    "SEVERITIES",
    "MILESTONES",
    "ADMISSIBLE_METHODS",
    "LATEST_CLOSURE_MILESTONE",
    "RATIO_TOLERANCE",
    "validate_requirement",
    "admissible_methods",
    "latest_closure_milestone",
    "assess_requirement",
    "method_mix",
    "coverage_ratio",
    "build_verification_plan",
]

METHODS = ("test", "analysis", "inspection", "review-of-design", "similarity")

SEVERITIES = ("catastrophic", "critical", "major", "minor")

# Programme reviews in the order they occur; the index is the comparison.
MILESTONES = ("prr", "pdr", "cdr", "qr", "ar", "frr")

# Which methods a severity will carry. The list shortens as severity rises.
ADMISSIBLE_METHODS = {
    "catastrophic": ("test", "analysis"),
    "critical": ("test", "analysis", "inspection"),
    "major": ("test", "analysis", "inspection", "review-of-design"),
    "minor": METHODS,
}

# The last review by which the verification is allowed to be planned closed.
LATEST_CLOSURE_MILESTONE = {
    "catastrophic": "qr",
    "critical": "qr",
    "major": "ar",
    "minor": "frr",
}

# Coverage ratios are int/int divisions; compare them with this slack rather
# than with a bare equality, so the same numbers grade the same everywhere.
RATIO_TOLERANCE = 1e-9


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _member(value, label, allowed):
    token = _text(value, label).lower()
    if token not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (label, ", ".join(allowed), value)
        )
    return token


def _flag(record, key):
    value = record.get(key, False)
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (key, value))
    return value


def validate_requirement(record):
    """Return a normalised safety-requirement verification record."""
    if not isinstance(record, dict):
        raise ValueError("requirement must be a mapping")
    baseline = record.get("similarity_baseline")
    if baseline is not None:
        baseline = _text(baseline, "similarity_baseline")
    return {
        "id": _text(record.get("id"), "id"),
        "severity": _member(record.get("severity"), "severity", SEVERITIES),
        "method": _member(record.get("method"), "method", METHODS),
        "planned_closure_milestone": _member(
            record.get("planned_closure_milestone"),
            "planned_closure_milestone",
            MILESTONES,
        ),
        "analysis_correlated_by_test": _flag(record, "analysis_correlated_by_test"),
        "similarity_baseline": baseline,
        "report_planned": _flag(record, "report_planned"),
    }


def admissible_methods(severity):
    """Return the verification methods a severity will carry."""
    return ADMISSIBLE_METHODS[_member(severity, "severity", SEVERITIES)]


def latest_closure_milestone(severity):
    """Return the last review by which this severity must be planned closed."""
    return LATEST_CLOSURE_MILESTONE[_member(severity, "severity", SEVERITIES)]


def assess_requirement(record):
    """Return the planning findings for one safety requirement."""
    norm = validate_requirement(record)
    findings = []

    allowed = admissible_methods(norm["severity"])
    if norm["method"] not in allowed:
        findings.append(
            "method %s is not admissible for a %s requirement; admissible: %s"
            % (norm["method"], norm["severity"], ", ".join(allowed))
        )

    if (
        norm["method"] == "analysis"
        and norm["severity"] == "catastrophic"
        and not norm["analysis_correlated_by_test"]
    ):
        findings.append(
            "analysis of a catastrophic requirement needs correlated test data behind it"
        )

    if norm["method"] == "similarity" and norm["similarity_baseline"] is None:
        findings.append("similarity was chosen with no baseline item named")

    if not norm["report_planned"]:
        findings.append("no verification report is planned, so nothing can cite the result")

    latest = latest_closure_milestone(norm["severity"])
    if MILESTONES.index(norm["planned_closure_milestone"]) > MILESTONES.index(latest):
        findings.append(
            "closure planned at %s, later than the %s milestone a %s requirement allows"
            % (norm["planned_closure_milestone"], latest, norm["severity"])
        )

    return {
        "id": norm["id"],
        "severity": norm["severity"],
        "method": norm["method"],
        "admissible_methods": list(allowed),
        "latest_closure_milestone": latest,
        "planned_closure_milestone": norm["planned_closure_milestone"],
        "findings": findings,
        "planned": not findings,
    }


def method_mix(requirements):
    """Return how many requirements each verification method carries."""
    mix = dict((method, 0) for method in METHODS)
    for record in requirements:
        mix[validate_requirement(record)["method"]] += 1
    return mix


def coverage_ratio(requirements):
    """Return the fraction of requirements whose verification is soundly planned."""
    records = list(requirements)
    if not records:
        raise ValueError("at least one safety requirement is needed")
    planned = sum(1 for record in records if assess_requirement(record)["planned"])
    return planned / float(len(records))


def build_verification_plan(requirements):
    """Return the safety verification plan and its disposition."""
    records = list(requirements)
    if not records:
        raise ValueError("at least one safety requirement is needed")
    assessed = [assess_requirement(record) for record in records]
    seen = set()
    for item in assessed:
        if item["id"] in seen:
            raise ValueError("duplicate requirement id %r" % item["id"])
        seen.add(item["id"])

    open_items = [item for item in assessed if not item["planned"]]
    severe_open = [
        item for item in open_items if item["severity"] in ("catastrophic", "critical")
    ]
    ratio = coverage_ratio(records)

    if severe_open:
        disposition = "plan-rejected"
    elif open_items:
        disposition = "plan-acceptable-with-actions"
    else:
        disposition = "plan-acceptable"

    return {
        "requirements": assessed,
        "method_mix": method_mix(records),
        "coverage_ratio": ratio,
        "open_requirement_ids": [item["id"] for item in open_items],
        "severe_open_requirement_ids": [item["id"] for item in severe_open],
        "disposition": disposition,
        "acceptable": disposition != "plan-rejected",
    }
