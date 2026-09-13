#!/usr/bin/env python3
"""Electromagnetic-effects verification report content check.

Anchor: ECSS-E-ST-20C Annex C (data-requirement for the report that states
the demonstrated margins, the results and the deviations of every
electromagnetic-effects verification activity). Paraphrased into an
implementable procedure; no verbatim standard text.

Stdlib only, offline, deterministic.

Procedure implemented here:

1. check that the mandated report sections are present;
2. categorize each verification activity into its electromagnetic family;
3. recompute the demonstrated margin from the applicable limit and the
   measured level using the sense that the family imposes;
4. grade the recomputed margin against the required margin in three bands;
5. check activity coverage against the mandated method list;
6. validate the deviation register (recognized disposition, waiver
   reference where a waiver is claimed, activity that actually exists);
7. aggregate into a report-level verdict.
"""

import math

# Equality on a margin boundary is physically compliant; the comparison
# absorbs floating-point representation error instead of widening the
# engineering limit.
MARGIN_REL_TOL = 1e-9
MARGIN_ABS_TOL = 1e-9

REQUIRED_SECTIONS = (
    "identification",
    "verification-matrix",
    "results",
    "deviation-register",
    "conclusion",
)

# method -> electromagnetic family
METHOD_FAMILY = {
    "conducted-emission-power-lead": "emission",
    "conducted-emission-signal-lead": "emission",
    "radiated-emission-electric-field": "emission",
    "radiated-emission-magnetic-field": "emission",
    "conducted-susceptibility-power-lead": "susceptibility",
    "conducted-susceptibility-bulk-current-injection": "susceptibility",
    "radiated-susceptibility-electric-field": "susceptibility",
    "radiated-susceptibility-magnetic-field": "susceptibility",
    "electrostatic-discharge-immunity": "electrostatic",
    "magnetic-moment-characterisation": "magnetic",
    "bonding-resistance-measurement": "grounding",
    "isolation-resistance-measurement": "grounding",
}

# family -> sense of a good result
FAMILY_SENSE = {
    "emission": "lower-is-better",
    "magnetic": "lower-is-better",
    "grounding": "lower-is-better",
    "susceptibility": "higher-is-better",
    "electrostatic": "higher-is-better",
}

VALID_DISPOSITIONS = (
    "accepted-as-is",
    "waiver",
    "corrective-action",
    "retest",
)

GRADE_COMPLIANT = "compliant"
GRADE_MARGINAL = "marginal"
GRADE_NON_COMPLIANT = "non-compliant"


def _as_float(value, label):
    """Return value as a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def normalize_method(method):
    """Normalize a free-form method label to its canonical hyphenated token."""
    if not isinstance(method, str) or not method.strip():
        raise ValueError("method must be a non-empty string, got %r" % (method,))
    token = "-".join(method.strip().lower().replace("_", " ").replace("-", " ").split())
    return token


def categorize_verification_activity(method):
    """Return the electromagnetic family of a verification method.

    Raises ValueError for a method outside the recognized set: an
    uncategorized method has no margin sense and cannot be graded.
    """
    token = normalize_method(method)
    family = METHOD_FAMILY.get(token)
    if family is None:
        raise ValueError("uncategorized verification method %r" % (method,))
    return family


def margin_sense(family):
    """Return 'lower-is-better' or 'higher-is-better' for an electromagnetic family."""
    if family not in FAMILY_SENSE:
        raise ValueError("unknown electromagnetic family %r" % (family,))
    return FAMILY_SENSE[family]


def compute_demonstrated_margin(applicable_limit, measured_level, family):
    """Recompute the demonstrated margin in the unit of its two inputs.

    lower-is-better families: limit - measured.
    higher-is-better families: measured (level survived) - limit (level required).
    """
    limit = _as_float(applicable_limit, "applicable_limit")
    measured = _as_float(measured_level, "measured_level")
    sense = margin_sense(family)
    if sense == "lower-is-better":
        return limit - measured
    return measured - limit


def grade_margin(demonstrated_margin, required_margin):
    """Grade a recomputed margin into compliant / marginal / non-compliant."""
    margin = _as_float(demonstrated_margin, "demonstrated_margin")
    required = _as_float(required_margin, "required_margin")
    if required < 0.0:
        raise ValueError("required_margin must be non-negative, got %r" % (required_margin,))
    if margin > required or math.isclose(
        margin, required, rel_tol=MARGIN_REL_TOL, abs_tol=MARGIN_ABS_TOL
    ):
        return GRADE_COMPLIANT
    if margin > 0.0 or math.isclose(margin, 0.0, abs_tol=MARGIN_ABS_TOL):
        return GRADE_MARGINAL
    return GRADE_NON_COMPLIANT


def evaluate_activity(activity, default_required_margin=0.0):
    """Evaluate one verification activity record.

    Required keys: method, applicable_limit, measured_level, unit.
    Optional: required_margin (falls back to the report default), requirement.
    """
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping, got %r" % (type(activity).__name__,))
    for key in ("method", "applicable_limit", "measured_level", "unit"):
        if key not in activity:
            raise ValueError("activity is missing required key %r" % (key,))
    unit = activity["unit"]
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("activity unit must be a non-empty string, got %r" % (unit,))
    family = categorize_verification_activity(activity["method"])
    margin = compute_demonstrated_margin(
        activity["applicable_limit"], activity["measured_level"], family
    )
    required = activity.get("required_margin", default_required_margin)
    grade = grade_margin(margin, required)
    return {
        "method": normalize_method(activity["method"]),
        "family": family,
        "sense": margin_sense(family),
        "unit": unit.strip(),
        "demonstrated_margin": margin,
        "required_margin": _as_float(required, "required_margin"),
        "grade": grade,
        "requirement": activity.get("requirement"),
    }


def check_activity_coverage(activities, mandated_methods):
    """Return the sorted mandated methods that no activity discharges."""
    if not isinstance(activities, (list, tuple)):
        raise ValueError("activities must be a list")
    if not isinstance(mandated_methods, (list, tuple)):
        raise ValueError("mandated_methods must be a list")
    present = set()
    for activity in activities:
        if not isinstance(activity, dict) or "method" not in activity:
            raise ValueError("every activity must be a mapping carrying 'method'")
        present.add(normalize_method(activity["method"]))
    missing = []
    for method in mandated_methods:
        token = normalize_method(method)
        if token not in METHOD_FAMILY:
            raise ValueError("uncategorized mandated method %r" % (method,))
        if token not in present:
            missing.append(token)
    return sorted(set(missing))


def validate_deviation(deviation, known_methods=None):
    """Validate one deviation-register entry and return it normalized."""
    if not isinstance(deviation, dict):
        raise ValueError("deviation must be a mapping")
    for key in ("activity", "description", "disposition"):
        if key not in deviation:
            raise ValueError("deviation is missing required key %r" % (key,))
    method = normalize_method(deviation["activity"])
    if known_methods is not None and method not in known_methods:
        raise ValueError("deviation names activity %r absent from the report" % (method,))
    description = deviation["description"]
    if not isinstance(description, str) or not description.strip():
        raise ValueError("deviation description must be a non-empty string")
    disposition = deviation["disposition"]
    if disposition not in VALID_DISPOSITIONS:
        raise ValueError("unrecognized deviation disposition %r" % (disposition,))
    reference = deviation.get("waiver_reference")
    if disposition == "waiver":
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError("a waiver disposition needs a non-empty waiver_reference")
        reference = reference.strip()
    else:
        reference = reference.strip() if isinstance(reference, str) else None
    return {
        "activity": method,
        "description": description.strip(),
        "disposition": disposition,
        "waiver_reference": reference,
        "closes_campaign": disposition in ("accepted-as-is", "waiver"),
    }


def register_deviations(deviations, known_methods=None):
    """Validate every deviation-register entry; return the normalized list."""
    if not isinstance(deviations, (list, tuple)):
        raise ValueError("deviations must be a list")
    return [validate_deviation(entry, known_methods) for entry in deviations]


def check_sections(sections):
    """Return the sorted mandated report sections that are absent."""
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be a list")
    present = set()
    for section in sections:
        if not isinstance(section, str) or not section.strip():
            raise ValueError("every section name must be a non-empty string")
        present.add("-".join(section.strip().lower().replace("_", " ").replace("-", " ").split()))
    return sorted(s for s in REQUIRED_SECTIONS if s not in present)


def summarize_margins(evaluations):
    """Summarize graded activities: counts per band and the worst margin."""
    if not isinstance(evaluations, (list, tuple)) or not evaluations:
        raise ValueError("evaluations must be a non-empty list")
    counts = {GRADE_COMPLIANT: 0, GRADE_MARGINAL: 0, GRADE_NON_COMPLIANT: 0}
    worst = None
    for item in evaluations:
        counts[item["grade"]] += 1
        shortfall = item["demonstrated_margin"] - item["required_margin"]
        if worst is None or shortfall < worst["shortfall"]:
            worst = {
                "method": item["method"],
                "shortfall": shortfall,
                "unit": item["unit"],
                "grade": item["grade"],
            }
    return {"counts": counts, "worst": worst, "activity_count": len(evaluations)}


def assess_report(report):
    """Assess a whole electromagnetic-effects verification report.

    Keys: sections, activities, deviations (optional), mandated_methods
    (optional), default_required_margin (optional).
    """
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    for key in ("sections", "activities"):
        if key not in report:
            raise ValueError("report is missing required key %r" % (key,))
    activities = report["activities"]
    if not isinstance(activities, (list, tuple)) or not activities:
        raise ValueError("report must carry at least one verification activity")
    missing_sections = check_sections(report["sections"])
    default_margin = report.get("default_required_margin", 0.0)
    evaluations = [evaluate_activity(a, default_margin) for a in activities]
    known = {item["method"] for item in evaluations}
    coverage_gaps = check_activity_coverage(activities, report.get("mandated_methods", []))
    deviations = register_deviations(report.get("deviations", []), known)
    summary = summarize_margins(evaluations)
    non_compliant = [e["method"] for e in evaluations if e["grade"] == GRADE_NON_COMPLIANT]
    marginal = [e["method"] for e in evaluations if e["grade"] == GRADE_MARGINAL]
    covered_by_deviation = {d["activity"] for d in deviations}
    uncarried_marginal = sorted(m for m in marginal if m not in covered_by_deviation)
    findings = []
    if missing_sections:
        findings.append("missing-sections: " + ", ".join(missing_sections))
    if coverage_gaps:
        findings.append("coverage-gaps: " + ", ".join(coverage_gaps))
    if non_compliant:
        findings.append("non-compliant-activities: " + ", ".join(sorted(non_compliant)))
    if uncarried_marginal:
        findings.append("marginal-not-in-register: " + ", ".join(uncarried_marginal))
    return {
        "missing_sections": missing_sections,
        "coverage_gaps": coverage_gaps,
        "evaluations": evaluations,
        "deviations": deviations,
        "summary": summary,
        "findings": findings,
        "acceptable": not findings,
    }
