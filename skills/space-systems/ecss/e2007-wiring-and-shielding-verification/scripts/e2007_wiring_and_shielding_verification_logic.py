"""Verification of harness categories and shield treatment.

Anchor: ECSS-E-ST-20-07C clause 5.3.11 (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Treat the verification as two stages that do different jobs. The
   design review reads the wiring documentation and confirms that every
   run has been given a category and a shield treatment on paper. The
   physical inspection looks at the built harness and records what was
   actually fitted. Neither stage substitutes for the other: paper
   without hardware verifies an intention, hardware without paper
   verifies nothing against a requirement.
2. Compare the two stages run by run. A category recorded on the
   drawing and a different category found on the harness is a finding,
   and so is a shield termination that changed between the two.
3. Grade the shield treatment itself against what the run's category
   needs: a sensitive or interfering run needs a full-circumference
   termination, a signal or power run may use a pigtail but only under
   its length limit, and a shielded run terminated nowhere is a finding
   whatever its category.
4. Check inspection coverage per category. A sensitive or interfering
   run is inspected individually; a signal or power run may be covered
   by a sample, but the sample has a floor.

Stdlib only, offline, deterministic.
"""

CATEGORY_SENSITIVE = "sensitive"
CATEGORY_SIGNAL = "signal"
CATEGORY_POWER = "power"
CATEGORY_INTERFERING = "interfering"
VALID_CATEGORIES = (
    CATEGORY_SENSITIVE,
    CATEGORY_SIGNAL,
    CATEGORY_POWER,
    CATEGORY_INTERFERING,
)

# Categories whose runs are inspected one by one rather than sampled.
FULL_INSPECTION_CATEGORIES = (CATEGORY_SENSITIVE, CATEGORY_INTERFERING)

TERMINATION_CIRCUMFERENTIAL = "full-circumference"
TERMINATION_PIGTAIL = "pigtail"
TERMINATION_NONE = "none"
VALID_TERMINATIONS = (
    TERMINATION_CIRCUMFERENTIAL,
    TERMINATION_PIGTAIL,
    TERMINATION_NONE,
)

# A pigtail is an unshielded stub in series with the shield, so its
# length is the part of the run the shield does not cover.
MAX_PIGTAIL_LENGTH_MM = 25.0

# Inspection sample floor for a category that may be sampled.
SAMPLED_INSPECTION_FRACTION = 0.20
FULL_INSPECTION_FRACTION = 1.0

# Coverage is a ratio of two small integers, so a sample sitting exactly
# on its floor can land a few units in the last place below it. This
# tolerance absorbs that without lowering the floor itself.
FRACTION_TOLERANCE = 1.0e-12

STAGE_DESIGN_REVIEW = "design-review"
STAGE_PHYSICAL_INSPECTION = "physical-inspection"


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _category(label, value, allow_none=False):
    if value is None and allow_none:
        return None
    if value not in VALID_CATEGORIES:
        raise ValueError(
            "%s must be one of %s, got %r" % (label, ", ".join(VALID_CATEGORIES), value)
        )
    return value


def _termination(label, value, allow_none=False):
    if value is None and allow_none:
        return None
    if value not in VALID_TERMINATIONS:
        raise ValueError(
            "%s must be one of %s, got %r"
            % (label, ", ".join(VALID_TERMINATIONS), value)
        )
    return value


def validate_run(run):
    """Validate one harness-run record and return a normalized copy."""
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping")
    run_id = run.get("id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run needs a non-empty string id")
    declared_category = _category(
        "run %s declared_category" % run_id, run.get("declared_category")
    )
    inspected_category = _category(
        "run %s inspected_category" % run_id,
        run.get("inspected_category"),
        allow_none=True,
    )
    declared_termination = _termination(
        "run %s declared_termination" % run_id, run.get("declared_termination")
    )
    inspected_termination = _termination(
        "run %s inspected_termination" % run_id,
        run.get("inspected_termination"),
        allow_none=True,
    )
    declared_pigtail = run.get("declared_pigtail_length_mm")
    if declared_pigtail is not None:
        declared_pigtail = _numeric(
            "run %s declared_pigtail_length_mm" % run_id, declared_pigtail, 0.0
        )
    inspected_pigtail = run.get("inspected_pigtail_length_mm")
    if inspected_pigtail is not None:
        inspected_pigtail = _numeric(
            "run %s inspected_pigtail_length_mm" % run_id, inspected_pigtail, 0.0
        )
    review_evidence = run.get("design_review_evidence")
    if review_evidence is not None and not isinstance(review_evidence, str):
        raise ValueError("run %s design_review_evidence must be a string" % run_id)
    inspection_evidence = run.get("inspection_evidence")
    if inspection_evidence is not None and not isinstance(inspection_evidence, str):
        raise ValueError("run %s inspection_evidence must be a string" % run_id)
    return {
        "id": run_id,
        "declared_category": declared_category,
        "inspected_category": inspected_category,
        "declared_termination": declared_termination,
        "inspected_termination": inspected_termination,
        "declared_pigtail_length_mm": declared_pigtail,
        "inspected_pigtail_length_mm": inspected_pigtail,
        "shielded": _boolean("run %s shielded" % run_id, run.get("shielded", True)),
        "design_review_done": _boolean(
            "run %s design_review_done" % run_id, run.get("design_review_done", False)
        ),
        "physical_inspection_done": _boolean(
            "run %s physical_inspection_done" % run_id,
            run.get("physical_inspection_done", False),
        ),
        "design_review_evidence": review_evidence,
        "inspection_evidence": inspection_evidence,
    }


def design_review_findings(run):
    """Findings about the documentation stage of one run."""
    norm = validate_run(run)
    findings = []
    if not norm["design_review_done"]:
        findings.append("design-review-not-performed")
        return findings
    if not norm["design_review_evidence"]:
        findings.append("design-review-without-an-evidence-reference")
    if (
        norm["declared_termination"] == TERMINATION_PIGTAIL
        and norm["declared_pigtail_length_mm"] is None
    ):
        findings.append("declared-pigtail-length-not-documented")
    return findings


def physical_inspection_findings(run):
    """Findings about the hardware stage of one run."""
    norm = validate_run(run)
    findings = []
    if not norm["physical_inspection_done"]:
        findings.append("physical-inspection-not-performed")
        return findings
    if not norm["inspection_evidence"]:
        findings.append("physical-inspection-without-an-evidence-reference")
    if norm["inspected_category"] is None:
        findings.append("inspected-category-not-recorded")
    if norm["inspected_termination"] is None:
        findings.append("inspected-termination-not-recorded")
    elif (
        norm["inspected_termination"] == TERMINATION_PIGTAIL
        and norm["inspected_pigtail_length_mm"] is None
    ):
        findings.append("inspected-pigtail-length-not-recorded")
    return findings


def category_agreement_findings(run):
    """Findings where the built category differs from the documented one."""
    norm = validate_run(run)
    if not norm["physical_inspection_done"] or norm["inspected_category"] is None:
        return []
    if norm["inspected_category"] != norm["declared_category"]:
        return ["as-built-category-differs-from-the-documented-category"]
    return []


def required_termination(category):
    """Shield termination a run of this category needs."""
    cat = _category("category", category)
    if cat in FULL_INSPECTION_CATEGORIES:
        return TERMINATION_CIRCUMFERENTIAL
    return TERMINATION_PIGTAIL


def shield_treatment_findings(run):
    """Findings about the shield treatment of one run."""
    norm = validate_run(run)
    if not norm["shielded"]:
        if norm["declared_termination"] != TERMINATION_NONE:
            return ["unshielded-run-declares-a-shield-termination"]
        return []
    findings = []
    effective = norm["inspected_termination"]
    effective_pigtail = norm["inspected_pigtail_length_mm"]
    if effective is None:
        effective = norm["declared_termination"]
        effective_pigtail = norm["declared_pigtail_length_mm"]
    if effective == TERMINATION_NONE:
        findings.append("shielded-run-with-no-shield-termination")
        return findings
    needed = required_termination(norm["declared_category"])
    if needed == TERMINATION_CIRCUMFERENTIAL and effective != TERMINATION_CIRCUMFERENTIAL:
        findings.append("category-needs-a-full-circumference-termination")
    if effective == TERMINATION_PIGTAIL and effective_pigtail is not None:
        if effective_pigtail > MAX_PIGTAIL_LENGTH_MM:
            findings.append("pigtail-longer-than-its-limit")
    if (
        norm["inspected_termination"] is not None
        and norm["inspected_termination"] != norm["declared_termination"]
    ):
        findings.append("as-built-termination-differs-from-the-documented-one")
    return findings


def required_inspection_fraction(category):
    """Fraction of a category's runs that has to be inspected."""
    cat = _category("category", category)
    if cat in FULL_INSPECTION_CATEGORIES:
        return FULL_INSPECTION_FRACTION
    return SAMPLED_INSPECTION_FRACTION


def inspection_coverage(runs):
    """Inspected-run counts and fractions, grouped by declared category."""
    if not isinstance(runs, list) or not runs:
        raise ValueError("runs must be a non-empty list")
    coverage = {}
    for run in runs:
        norm = validate_run(run)
        cat = norm["declared_category"]
        entry = coverage.setdefault(cat, {"total": 0, "inspected": 0})
        entry["total"] += 1
        if norm["physical_inspection_done"]:
            entry["inspected"] += 1
    for cat, entry in coverage.items():
        entry["fraction"] = entry["inspected"] / entry["total"]
        entry["required_fraction"] = required_inspection_fraction(cat)
    return coverage


def coverage_findings(runs):
    """Categories whose inspected share falls under its floor."""
    coverage = inspection_coverage(runs)
    findings = []
    for cat in sorted(coverage):
        entry = coverage[cat]
        if entry["fraction"] < entry["required_fraction"] - FRACTION_TOLERANCE:
            findings.append("%s-inspection-coverage-below-floor" % cat)
    return findings


def assess_run(run):
    """Assess one harness run against clause 5.3.11."""
    norm = validate_run(run)
    findings = []
    findings.extend(design_review_findings(norm))
    findings.extend(physical_inspection_findings(norm))
    findings.extend(category_agreement_findings(norm))
    findings.extend(shield_treatment_findings(norm))
    return {
        "id": norm["id"],
        "declared_category": norm["declared_category"],
        "inspected_category": norm["inspected_category"],
        "stages_complete": norm["design_review_done"]
        and norm["physical_inspection_done"],
        "required_termination": required_termination(norm["declared_category"]),
        "findings": findings,
        "compliant": not findings,
    }


def assess_wiring_and_shielding_verification(runs):
    """Run the full clause 5.3.11 verification over a harness run list."""
    if not isinstance(runs, list) or not runs:
        raise ValueError("runs must be a non-empty list")
    results = []
    seen = set()
    for run in runs:
        result = assess_run(run)
        if result["id"] in seen:
            raise ValueError("duplicate run id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    non_compliant = [r["id"] for r in results if not r["compliant"]]
    coverage = inspection_coverage(runs)
    cov_findings = coverage_findings(runs)
    return {
        "runs": results,
        "coverage": coverage,
        "coverage_findings": cov_findings,
        "non_compliant_ids": non_compliant,
        "compliant": not non_compliant and not cov_findings,
    }
