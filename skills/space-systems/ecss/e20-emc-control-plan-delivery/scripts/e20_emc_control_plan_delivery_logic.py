#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.2.2 electromagnetic compatibility control plan
delivery (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires the supplier to write an
electromagnetic compatibility control plan and to deliver it in time
for the preliminary design review, so the compatibility approach is on
the table while the architecture can still change. This module
implements the checkable part of that clause: the mandatory section set
of the plan and the group each section belongs to, the maturity a
declared section status represents, the completeness index of the plan
as the mean maturity over the mandatory set, the delivery lead time
between the planned issue date and the review date against the data
package deadline, the requirement-to-section traceability of the
compatibility requirement flow-down, and the aggregation that decides
whether the plan is deliverable. It does not write plan text, does not
predict coupling, and does not run the review.
"""

import datetime
import math

# Mandatory plan sections grouped by what the section governs.
PLAN_SECTION_GROUPS = {
    "scope_and_applicability": "management",
    "organisation_and_responsibilities": "management",
    "schedule_and_deliverables": "management",
    "nonconformance_and_waiver_route": "management",
    "requirement_and_limit_flowdown": "design",
    "grounding_and_bonding_concept": "design",
    "shielding_and_harness_rules": "design",
    "frequency_management_and_protected_bands": "design",
    "safety_margin_policy": "design",
    "predictive_analysis_approach": "verification",
    "verification_and_test_approach": "verification",
    "interference_critical_point_list": "verification",
}

MANDATORY_PLAN_SECTIONS = frozenset(PLAN_SECTION_GROUPS)

# Maturity a declared section status represents, on a zero to one scale.
SECTION_STATUS_MATURITY = {
    "not_started": 0.0,
    "draft": 0.4,
    "issued": 0.8,
    "approved": 1.0,
}

# Minimum status every mandatory section holds when the plan is handed
# over for the preliminary design review.
MINIMUM_STATUS_AT_REVIEW = "issued"

# Working days of lead time the review data package needs before the
# review itself; a plan handed over inside this window is late even if
# its date precedes the review.
DEFAULT_DATA_PACKAGE_LEAD_DAYS = 20

# Completeness index the plan holds at hand-over.
DEFAULT_COMPLETENESS_THRESHOLD = 0.8

# A mean of maturities is a sum of floats over a count, so an
# exactly-met threshold can land a few units in the last place low. The
# tolerance absorbs the representation error; the threshold is
# unchanged.
INDEX_REL_TOL = 1e-9
INDEX_ABS_TOL = 1e-12


def categorize_plan_section(section_name):
    """Group a mandatory plan section belongs to: "management",
    "design" or "verification". Raises ValueError for a section that is
    not part of the E-ST-20C clause 6.2.2 control plan."""
    group = PLAN_SECTION_GROUPS.get(section_name)
    if group is None:
        raise ValueError(
            "unrecognized control plan section %r under "
            "E-ST-20C clause 6.2.2" % (section_name,)
        )
    return group


def section_maturity(status):
    """Maturity value of a declared section status, between zero and
    one. Raises ValueError for a status outside the declared set."""
    maturity = SECTION_STATUS_MATURITY.get(status)
    if maturity is None:
        raise ValueError(
            "unrecognized section status %r (expected one of %s)"
            % (status, ", ".join(sorted(SECTION_STATUS_MATURITY)))
        )
    return maturity


def missing_plan_sections(declared_sections):
    """Sorted list of mandatory sections the plan does not declare.
    declared_sections: mapping of section name to status. Raises
    ValueError for a non-mapping declaration or an unrecognized
    section name."""
    if not isinstance(declared_sections, dict):
        raise ValueError(
            "declared_sections must be a mapping of section to status, got %r"
            % (declared_sections,)
        )
    for section_name in declared_sections:
        categorize_plan_section(section_name)
    return sorted(MANDATORY_PLAN_SECTIONS - set(declared_sections))


def immature_plan_sections(declared_sections, minimum_status=MINIMUM_STATUS_AT_REVIEW):
    """Sorted list of declared sections that sit below the minimum
    status required at hand-over. Raises ValueError for an unrecognized
    section, status or minimum status."""
    floor = section_maturity(minimum_status)
    if not isinstance(declared_sections, dict):
        raise ValueError(
            "declared_sections must be a mapping of section to status, got %r"
            % (declared_sections,)
        )
    immature = []
    for section_name, status in declared_sections.items():
        categorize_plan_section(section_name)
        if section_maturity(status) < floor:
            immature.append(section_name)
    return sorted(immature)


def plan_completeness_index(declared_sections):
    """Mean maturity over the mandatory section set. A section the plan
    does not declare contributes zero, so an incomplete plan cannot
    reach a complete index by declaring only its finished sections.
    Raises ValueError for an unrecognized section or status."""
    if not isinstance(declared_sections, dict):
        raise ValueError(
            "declared_sections must be a mapping of section to status, got %r"
            % (declared_sections,)
        )
    total = 0.0
    for section_name, status in declared_sections.items():
        categorize_plan_section(section_name)
        total += section_maturity(status)
    return total / float(len(MANDATORY_PLAN_SECTIONS))


def index_meets_threshold(index, threshold=DEFAULT_COMPLETENESS_THRESHOLD):
    """True when a completeness index satisfies the hand-over threshold.
    An exactly-met threshold that lands a few units in the last place
    low through the mean is not failed; a real shortfall is. Raises
    ValueError for a threshold outside the zero-to-one scale."""
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
        raise ValueError("threshold must be a real number, got %r" % (threshold,))
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must lie between 0 and 1, got %r" % (threshold,))
    if index >= threshold:
        return True
    return math.isclose(index, threshold, rel_tol=INDEX_REL_TOL, abs_tol=INDEX_ABS_TOL)


def parse_plan_date(value):
    """Calendar date from an ISO ``YYYY-MM-DD`` string or a date object.
    Raises ValueError for anything else."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str):
        raise ValueError("plan date must be an ISO date string or a date, got %r" % (value,))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("plan date %r is not an ISO YYYY-MM-DD date" % (value,)) from None


def delivery_lead_days(delivery_date, review_date):
    """Calendar days between the plan hand-over and the review. Positive
    when the plan arrives before the review, negative when it arrives
    after it. Raises ValueError for a malformed date."""
    delivered = parse_plan_date(delivery_date)
    review = parse_plan_date(review_date)
    return (review - delivered).days


def delivery_findings(
    delivery_date, review_date, required_lead_days=DEFAULT_DATA_PACKAGE_LEAD_DAYS
):
    """Sorted findings on the hand-over timing of the control plan.
    Raises ValueError for a malformed date or a negative lead
    requirement."""
    if not isinstance(required_lead_days, int) or isinstance(required_lead_days, bool):
        raise ValueError(
            "required_lead_days must be an integer number of days, got %r"
            % (required_lead_days,)
        )
    if required_lead_days < 0:
        raise ValueError(
            "required_lead_days must not be negative, got %r" % (required_lead_days,)
        )
    lead = delivery_lead_days(delivery_date, review_date)
    findings = []
    if lead < 0:
        findings.append(
            "control plan is handed over %d day(s) after the preliminary design "
            "review, so the compatibility approach is reviewed after the "
            "architecture is frozen" % (-lead,)
        )
    elif lead < required_lead_days:
        findings.append(
            "control plan is handed over %d day(s) before the review, inside the "
            "%d day data package deadline" % (lead, required_lead_days)
        )
    return sorted(findings)


def traceability_findings(requirement_map, declared_sections):
    """Sorted findings on the compatibility requirement flow-down into
    the plan. requirement_map: iterable of mappings with requirement_id
    and plan_section. A requirement with no section, or pointing at a
    section the plan does not declare, or pointing at a section that has
    not started, is a finding. Raises ValueError for a section name that
    is not part of the control plan."""
    if not isinstance(declared_sections, dict):
        raise ValueError(
            "declared_sections must be a mapping of section to status, got %r"
            % (declared_sections,)
        )
    findings = []
    for entry in requirement_map:
        requirement_id = entry.get("requirement_id")
        section_name = entry.get("plan_section")
        if section_name is None:
            findings.append(
                "requirement %r is not traced into any plan section"
                % (requirement_id,)
            )
            continue
        categorize_plan_section(section_name)
        status = declared_sections.get(section_name)
        if status is None:
            findings.append(
                "requirement %r is traced to section %r, which the plan does "
                "not declare" % (requirement_id, section_name)
            )
        elif section_maturity(status) <= 0.0:
            findings.append(
                "requirement %r is traced to section %r, which has not been "
                "started" % (requirement_id, section_name)
            )
    return sorted(findings)


def aggregate_control_plan_delivery(plan):
    """Full clause 6.2.2 review of a control plan hand-over.

    plan keys: declared_sections, delivery_date, review_date,
    requirement_map (optional), required_lead_days (optional),
    completeness_threshold (optional). Returns a mapping with the
    completeness index, the missing and immature sections, the timing
    and traceability findings, and the overall deliverable flag. The
    plan is deliverable only when every list is empty and the index
    holds the threshold."""
    declared = plan.get("declared_sections", {})
    index = plan_completeness_index(declared)
    threshold = plan.get("completeness_threshold", DEFAULT_COMPLETENESS_THRESHOLD)
    missing = missing_plan_sections(declared)
    immature = immature_plan_sections(declared)
    timing = delivery_findings(
        plan.get("delivery_date"),
        plan.get("review_date"),
        plan.get("required_lead_days", DEFAULT_DATA_PACKAGE_LEAD_DAYS),
    )
    traceability = traceability_findings(plan.get("requirement_map", []), declared)
    deliverable = (
        not missing
        and not immature
        and not timing
        and not traceability
        and index_meets_threshold(index, threshold)
    )
    return {
        "completeness_index": index,
        "missing_sections": missing,
        "immature_sections": immature,
        "delivery_findings": timing,
        "traceability_findings": traceability,
        "deliverable": deliverable,
    }
