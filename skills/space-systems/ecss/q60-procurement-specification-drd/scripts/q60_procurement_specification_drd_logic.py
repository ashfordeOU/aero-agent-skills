"""Part purchasing specification data item: content, screening, lot acceptance.

Anchor: ECSS-Q-ST-60C Annex C (procurement specification DRD). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the specification header, because an uncontrolled document cannot
   be the baseline an order is placed against.
2. Weight the required content sections by how much of the purchasing decision
   rests on them, and report coverage as a weighted share rather than as a
   count of headings present.
3. Grade every screening step on the fields that make it executable — what is
   done, under what condition, and what result rejects the part. A step with
   no reject criterion is a description, not a screen.
4. Check the screening sequence itself: positions have to be unique, because a
   sequence with two step fours does not say which one runs first.
5. Check the screening families the flow has to cover, so a long sequence of
   electrical measurements cannot stand in for a burn-in that is absent.
6. Check the lot acceptance plan is arithmetically able to reject: a sample
   larger than the lot is not a sample, and an accept number at or above the
   sample size accepts every lot that can be drawn.
7. Compute the acceptance probability of the stated plan against an assumed
   defective population, exactly, so a reviewer can see what the plan actually
   screens out before the order is placed.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "HEADER_FIELDS",
    "LOT_ACCEPTANCE_FIELDS",
    "MANDATED_SCREENING_FAMILIES",
    "REQUIRED_SECTIONS",
    "SCREENING_STEP_FIELDS",
    "validate_specification_header",
    "section_coverage",
    "screening_step_completeness",
    "screening_sequence_findings",
    "screening_family_coverage",
    "lot_acceptance_findings",
    "probability_of_acceptance",
    "assess_procurement_specification_drd",
]

# Coverage is a ratio of summed weights. An exactly-met requirement can land a
# few ULPs low; absorb the representation error here rather than lowering the
# level the project agreed.
COVERAGE_TOLERANCE = 1e-9

# Header fields without which the specification is not a controlled document.
HEADER_FIELDS = (
    "specification_id",
    "issue",
    "part_type",
    "issue_date",
    "approving_authority",
)

# Required content section -> weight. The weights say how much of a purchasing
# decision rests on the section, which is why coverage is not a heading count.
REQUIRED_SECTIONS = {
    "identification": 2,
    "applicable-documents": 1,
    "part-description": 2,
    "electrical-and-functional-requirements": 3,
    "screening-sequence": 3,
    "lot-acceptance-testing": 3,
    "marking-and-traceability": 2,
    "packaging-and-handling": 1,
    "quality-assurance-clauses": 2,
}

# Fields that make one screening step executable rather than merely described.
SCREENING_STEP_FIELDS = (
    "step_id",
    "sequence",
    "family",
    "test_name",
    "condition",
    "reject_criterion",
)

# Families the screening flow has to cover; a deep sequence inside one family
# does not substitute for a family that is missing entirely.
MANDATED_SCREENING_FAMILIES = (
    "visual-inspection",
    "electrical-measurement",
    "environmental-stress",
    "burn-in",
    "final-electrical",
)

# Fields the lot acceptance plan cannot be evaluated without.
LOT_ACCEPTANCE_FIELDS = ("test_name", "lot_size", "sample_size", "accept_number")

# Disposition -> severity used to rank findings. Lower sorts first.
_SEVERITY = {
    "section-absent": 0,
    "step-incomplete": 1,
    "sequence-position-repeated": 2,
    "screening-family-absent": 3,
    "sample-exceeds-lot": 4,
    "accept-number-not-discriminating": 5,
    "lot-plan-incomplete": 6,
}


def _require_text(value, label):
    """Return a non-blank stripped string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_non_negative_int(value, label):
    """Return a non-negative integer, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _require_positive_int(value, label):
    """Return a strictly positive integer, or raise."""
    value = _require_non_negative_int(value, label)
    if value == 0:
        raise ValueError("%s must be strictly positive" % label)
    return value


def validate_specification_header(header):
    """Return the validated header of one part purchasing specification."""
    if not isinstance(header, dict):
        raise ValueError("header must be a mapping")
    validated = {}
    for field in HEADER_FIELDS:
        validated[field] = _require_text(header.get(field), field)
    return validated


def section_coverage(sections):
    """Return (absent_sections, weighted_coverage) for the content sections."""
    if not isinstance(sections, dict):
        raise ValueError("sections must be a mapping of section name -> content")
    absent = []
    present_weight = 0
    total_weight = 0
    for name, weight in REQUIRED_SECTIONS.items():
        total_weight += weight
        body = sections.get(name)
        if body is None or (isinstance(body, str) and not body.strip()):
            absent.append(name)
            continue
        if not isinstance(body, str):
            raise ValueError("section %s must hold text, got %r" % (name, body))
        present_weight += weight
    if total_weight <= 0:
        raise ValueError("the required section table carries no weight")
    return (tuple(sorted(absent)), present_weight / total_weight)


def screening_step_completeness(step):
    """Return (missing_fields, completeness_fraction) for one screening step."""
    if not isinstance(step, dict):
        raise ValueError(
            "each screening step must be a mapping, got %r" % (type(step).__name__,)
        )
    missing = []
    for field in SCREENING_STEP_FIELDS:
        if field not in step:
            missing.append(field)
            continue
        value = step[field]
        if value is None:
            missing.append(field)
        elif isinstance(value, str) and not value.strip():
            missing.append(field)
    total = len(SCREENING_STEP_FIELDS)
    return (tuple(missing), (total - len(missing)) / total)


def screening_sequence_findings(steps):
    """Return findings on the screening sequence's completeness and ordering."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("screening_steps must be a non-empty sequence")
    findings = []
    positions = {}
    for step in steps:
        missing, _ = screening_step_completeness(step)
        raw_label = step.get("step_id") if isinstance(step, dict) else None
        label = (
            raw_label.strip()
            if isinstance(raw_label, str) and raw_label.strip()
            else "<unnumbered>"
        )
        if missing:
            findings.append(
                {
                    "severity": _SEVERITY["step-incomplete"],
                    "reference": label,
                    "disposition": "step-incomplete",
                    "detail": "screening step lacks %s; it cannot be executed or "
                    "adjudicated as written" % ", ".join(missing),
                }
            )
            continue
        position = _require_positive_int(step["sequence"], "sequence")
        if position in positions:
            findings.append(
                {
                    "severity": _SEVERITY["sequence-position-repeated"],
                    "reference": label,
                    "disposition": "sequence-position-repeated",
                    "detail": "sequence position %d is already held by step %s"
                    % (position, positions[position]),
                }
            )
            continue
        positions[position] = label
    return findings


def screening_family_coverage(steps):
    """Return (absent_families, covered_fraction) over the mandated families."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("screening_steps must be a non-empty sequence")
    seen = set()
    for step in steps:
        missing, _ = screening_step_completeness(step)
        if missing:
            continue
        seen.add(_require_text(step["family"], "family").lower())
    absent = tuple(
        family for family in MANDATED_SCREENING_FAMILIES if family not in seen
    )
    covered = len(MANDATED_SCREENING_FAMILIES) - len(absent)
    return (absent, covered / len(MANDATED_SCREENING_FAMILIES))


def probability_of_acceptance(lot_size, sample_size, accept_number, defectives):
    """Return the exact probability a lot holding this many defectives passes.

    Sampling is without replacement, so the count of defectives drawn follows a
    hypergeometric law. The whole sum is built from exact integer binomials and
    divided once, which keeps the result identical on every platform.
    """
    lot = _require_positive_int(lot_size, "lot_size")
    sample = _require_positive_int(sample_size, "sample_size")
    accept = _require_non_negative_int(accept_number, "accept_number")
    bad = _require_non_negative_int(defectives, "defectives")
    if sample > lot:
        raise ValueError("sample_size %d exceeds lot_size %d" % (sample, lot))
    if bad > lot:
        raise ValueError("defectives %d exceeds lot_size %d" % (bad, lot))
    if bad <= accept:
        return 1.0
    good = lot - bad
    numerator = 0
    for drawn in range(0, accept + 1):
        if drawn > bad or sample - drawn > good or sample - drawn < 0:
            continue
        numerator += math.comb(bad, drawn) * math.comb(good, sample - drawn)
    return numerator / math.comb(lot, sample)


def lot_acceptance_findings(plan):
    """Return findings on whether the lot acceptance plan can reject a lot."""
    if not isinstance(plan, dict):
        raise ValueError("lot_acceptance must be a mapping")
    missing = []
    for field in LOT_ACCEPTANCE_FIELDS:
        if field not in plan:
            missing.append(field)
            continue
        value = plan[field]
        if value is None:
            missing.append(field)
        elif isinstance(value, str) and not value.strip():
            missing.append(field)
    if missing:
        return [
            {
                "severity": _SEVERITY["lot-plan-incomplete"],
                "reference": "lot-acceptance",
                "disposition": "lot-plan-incomplete",
                "detail": "lot acceptance plan lacks %s" % ", ".join(missing),
            }
        ]
    lot = _require_positive_int(plan["lot_size"], "lot_size")
    sample = _require_positive_int(plan["sample_size"], "sample_size")
    accept = _require_non_negative_int(plan["accept_number"], "accept_number")
    findings = []
    if sample > lot:
        findings.append(
            {
                "severity": _SEVERITY["sample-exceeds-lot"],
                "reference": "lot-acceptance",
                "disposition": "sample-exceeds-lot",
                "detail": "a sample of %d cannot be drawn from a lot of %d"
                % (sample, lot),
            }
        )
    if accept >= sample:
        findings.append(
            {
                "severity": _SEVERITY["accept-number-not-discriminating"],
                "reference": "lot-acceptance",
                "disposition": "accept-number-not-discriminating",
                "detail": "an accept number of %d against a sample of %d passes "
                "every lot that can be drawn" % (accept, sample),
            }
        )
    return findings


def assess_procurement_specification_drd(spec):
    """Run the full Annex C purchasing specification data item assessment.

    spec keys: header (mapping), sections (mapping of section name -> text),
    screening_steps (sequence), lot_acceptance (mapping), optional
    required_section_coverage (default 1.0), optional assumed_defectives
    (default 1) used to report what the stated plan lets through.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("header", "sections", "screening_steps", "lot_acceptance"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    header = validate_specification_header(spec["header"])

    required = spec.get("required_section_coverage", 1.0)
    if isinstance(required, bool) or not isinstance(required, (int, float)):
        raise ValueError("required_section_coverage must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError(
            "required_section_coverage must lie in [0, 1], got %r"
            % (spec["required_section_coverage"],)
        )

    absent_sections, coverage = section_coverage(spec["sections"])
    findings = [
        {
            "severity": _SEVERITY["section-absent"],
            "reference": name,
            "disposition": "section-absent",
            "detail": "the specification carries no content for this required "
            "section",
        }
        for name in absent_sections
    ]

    steps = spec["screening_steps"]
    findings.extend(screening_sequence_findings(steps))

    absent_families, family_coverage = screening_family_coverage(steps)
    findings.extend(
        {
            "severity": _SEVERITY["screening-family-absent"],
            "reference": family,
            "disposition": "screening-family-absent",
            "detail": "the screening flow covers no step of this mandated family",
        }
        for family in absent_families
    )

    plan = spec["lot_acceptance"]
    findings.extend(lot_acceptance_findings(plan))
    findings.sort(key=lambda entry: (entry["severity"], entry["reference"]))

    assumed = spec.get("assumed_defectives", 1)
    acceptance_probability = None
    plan_complete = not any(
        entry["disposition"] == "lot-plan-incomplete" for entry in findings
    )
    if plan_complete and not any(
        entry["disposition"] == "sample-exceeds-lot" for entry in findings
    ):
        acceptance_probability = probability_of_acceptance(
            plan["lot_size"], plan["sample_size"], plan["accept_number"], assumed
        )

    meets = coverage > required or math.isclose(
        coverage, required, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    orderable = meets and not findings
    return {
        "header": header,
        "section_coverage": coverage,
        "required_section_coverage": required,
        "absent_sections": absent_sections,
        "screening_family_coverage": family_coverage,
        "absent_screening_families": absent_families,
        "assumed_defectives": assumed,
        "acceptance_probability": acceptance_probability,
        "findings": findings,
        "orderable": orderable,
        "verdict": "issue" if orderable else "hold",
    }
