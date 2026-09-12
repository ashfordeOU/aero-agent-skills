#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 4.3.2 electrical design documentation set
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical and electronic engineering standard requires the design to
be captured in a design report backed by supporting analyses. Worst
case and reliability are always owed; thermal, radiation and
electromagnetic analyses are owed when the item respectively
dissipates power, accumulates mission dose, or carries an external
electrical interface. A worst-case parameter excursion stacks initial
tolerance, temperature drift and end-of-life ageing on the nominal
value, arithmetically (extreme value) or in quadrature (root sum
square) when independence is argued. Part derating compares the
applied stress with the rated stress reduced by a derating factor;
radiation design margin is the ratio of the part's rated dose to the
predicted mission dose. Report maturity is read against the project
review: draft is acceptable at PDR, issued is required from CDR
onwards, and a report built against a superseded design revision is
stale.

This module implements the owed-analysis derivation, the worst-case
stacking, the derating and radiation margins, the report maturity and
staleness checks, and the aggregate review. It does not model the
internal content of any analysis, the reliability prediction method,
or the derating tables themselves.
"""

import math

UNCONDITIONAL_ANALYSES = ("worst_case", "reliability")
CONDITIONAL_ANALYSES = ("thermal", "radiation", "electromagnetic")
ANALYSIS_KINDS = frozenset(UNCONDITIONAL_ANALYSES + CONDITIONAL_ANALYSES)

# Canonical ordering used for the owed-analysis checklist.
ANALYSIS_ORDER = UNCONDITIONAL_ANALYSES + CONDITIONAL_ANALYSES

REPORT_STATES = frozenset({"absent", "draft", "issued"})

# Project reviews in chronological order and the report maturity each
# one demands of an owed analysis.
MILESTONE_SEQUENCE = ("pdr", "cdr", "qr", "ar")
REQUIRED_STATE_AT_MILESTONE = {
    "pdr": "draft",
    "cdr": "issued",
    "qr": "issued",
    "ar": "issued",
}

WORST_CASE_METHODS = frozenset({"extreme_value", "root_sum_square"})
ADVERSE_DIRECTIONS = frozenset({"high", "low"})

# House minimum ratio of rated dose to predicted mission dose.
MINIMUM_RADIATION_DESIGN_MARGIN = 2.0


def normalize_analysis_kind(kind):
    """Canonical supporting-analysis name. Raises ValueError for a kind
    outside the five recognized by clause 4.3.2."""
    if not isinstance(kind, str):
        raise ValueError("analysis kind must be a string, got %r" % (kind,))
    candidate = kind.strip().lower().replace("-", "_").replace(" ", "_")
    if candidate not in ANALYSIS_KINDS:
        raise ValueError(
            "unrecognized supporting analysis %r under E-ST-20C clause 4.3.2"
            % (kind,)
        )
    return candidate


def required_analyses(item):
    """Owed supporting analyses for one electrical item, in canonical
    order. Worst case and reliability are unconditional; thermal is
    owed once power_dissipation_w is positive, radiation once
    mission_dose_krad is positive, electromagnetic once
    has_external_interfaces is true. Raises ValueError for a negative
    dissipation or dose."""
    dissipation = float(item.get("power_dissipation_w", 0.0))
    dose = float(item.get("mission_dose_krad", 0.0))
    if dissipation < 0:
        raise ValueError("power_dissipation_w must be >= 0")
    if dose < 0:
        raise ValueError("mission_dose_krad must be >= 0")
    owed = set(UNCONDITIONAL_ANALYSES)
    if dissipation > 0:
        owed.add("thermal")
    if dose > 0:
        owed.add("radiation")
    if item.get("has_external_interfaces"):
        owed.add("electromagnetic")
    return tuple(kind for kind in ANALYSIS_ORDER if kind in owed)


def worst_case_value(
    nominal,
    tolerance_fraction,
    temperature_coefficient_per_k,
    delta_temperature_k,
    ageing_fraction,
    direction,
    method="extreme_value",
):
    """Worst-case excursion of one parameter.

    Stacks the initial tolerance, the temperature drift (magnitude of
    the temperature coefficient times the temperature excursion) and
    the end-of-life ageing fraction, then applies the stacked deviation
    to the nominal value in the adverse direction ("high" for a stress,
    "low" for a supply or drive capability). Extreme-value stacking is
    arithmetic; root-sum-square stacking is in quadrature. Raises
    ValueError for a non-positive nominal, a negative fraction or
    temperature excursion, an unrecognized direction, or an
    unrecognized stacking method."""
    if nominal <= 0:
        raise ValueError("nominal must be > 0")
    if tolerance_fraction < 0:
        raise ValueError("tolerance_fraction must be >= 0")
    if ageing_fraction < 0:
        raise ValueError("ageing_fraction must be >= 0")
    if delta_temperature_k < 0:
        raise ValueError("delta_temperature_k must be >= 0 (magnitude)")
    if direction not in ADVERSE_DIRECTIONS:
        raise ValueError("unrecognized adverse direction %r" % (direction,))
    if method not in WORST_CASE_METHODS:
        raise ValueError("unrecognized worst-case stacking method %r" % (method,))
    thermal_fraction = abs(temperature_coefficient_per_k) * delta_temperature_k
    contributions = (tolerance_fraction, thermal_fraction, ageing_fraction)
    if method == "extreme_value":
        deviation = sum(contributions)
    else:
        deviation = math.sqrt(sum(c * c for c in contributions))
    if direction == "high":
        return nominal * (1.0 + deviation)
    return nominal * (1.0 - deviation)


def derating_margin(applied_stress, rated_stress, derating_factor):
    """Margin of one stressed part as a fraction of its derated limit:
    (rated_stress * derating_factor - applied_stress) / derated limit.
    Negative means the part runs beyond the derated limit even when it
    sits under the datasheet rating. Raises ValueError for a
    non-positive rating, a negative applied stress, or a derating
    factor outside (0, 1]."""
    if rated_stress <= 0:
        raise ValueError("rated_stress must be > 0")
    if applied_stress < 0:
        raise ValueError("applied_stress must be >= 0")
    if not 0 < derating_factor <= 1:
        raise ValueError("derating_factor must be in (0, 1]")
    derated_limit = rated_stress * derating_factor
    return (derated_limit - applied_stress) / derated_limit


def radiation_design_margin(rated_dose_krad, mission_dose_krad):
    """Ratio of a part's rated total dose to the predicted mission dose
    at its location. Raises ValueError for a negative rating or a
    non-positive mission dose (no radiation case to margin against)."""
    if rated_dose_krad < 0:
        raise ValueError("rated_dose_krad must be >= 0")
    if mission_dose_krad <= 0:
        raise ValueError("mission_dose_krad must be > 0 for a radiation case")
    return rated_dose_krad / mission_dose_krad


def report_maturity_findings(item_id, owed, reports, milestone, design_revision):
    """Finding list (empty if acceptable) for the report set of one
    item at one project review.

    reports: {analysis kind: {"state", "design_revision"}}. Flags an
    absent report, a draft report at CDR or later, and a report built
    against a design revision other than the item's current one. Raises
    ValueError for an unrecognized milestone, analysis kind or report
    state."""
    if not isinstance(milestone, str) or milestone.strip().lower() not in (
        REQUIRED_STATE_AT_MILESTONE
    ):
        raise ValueError("unrecognized project review milestone %r" % (milestone,))
    review = milestone.strip().lower()
    required_state = REQUIRED_STATE_AT_MILESTONE[review]
    for kind in reports:
        normalize_analysis_kind(kind)
    findings = []
    for kind in owed:
        report = reports.get(kind)
        state = "absent" if report is None else report.get("state", "absent")
        if state not in REPORT_STATES:
            raise ValueError("unrecognized report state %r" % (state,))
        if state == "absent":
            findings.append(
                {
                    "issue": "missing_design_analysis_report",
                    "item": item_id,
                    "analysis": kind,
                }
            )
            continue
        if required_state == "issued" and state != "issued":
            findings.append(
                {
                    "issue": "design_analysis_report_not_issued",
                    "item": item_id,
                    "analysis": kind,
                    "milestone": review,
                }
            )
        if report.get("design_revision") != design_revision:
            findings.append(
                {
                    "issue": "design_analysis_report_stale",
                    "item": item_id,
                    "analysis": kind,
                    "report_revision": report.get("design_revision"),
                    "design_revision": design_revision,
                }
            )
    return findings


def margin_findings(item_id, derating_cases, radiation_case):
    """Finding list (empty if acceptable) for the margin calculations
    the design report turns on. derating_cases: iterable of dicts with
    "part", "applied_stress", "rated_stress", "derating_factor".
    radiation_case: dict with "part", "rated_dose_krad",
    "mission_dose_krad", or None when the item has no radiation case."""
    findings = []
    for case in derating_cases:
        margin = derating_margin(
            case["applied_stress"], case["rated_stress"], case["derating_factor"]
        )
        if margin < 0:
            findings.append(
                {
                    "issue": "part_derating_limit_exceeded",
                    "item": item_id,
                    "part": case.get("part"),
                    "margin": margin,
                }
            )
    if radiation_case is not None:
        ratio = radiation_design_margin(
            radiation_case["rated_dose_krad"], radiation_case["mission_dose_krad"]
        )
        if ratio < MINIMUM_RADIATION_DESIGN_MARGIN:
            findings.append(
                {
                    "issue": "radiation_design_margin_below_minimum",
                    "item": item_id,
                    "part": radiation_case.get("part"),
                    "margin": ratio,
                    "minimum": MINIMUM_RADIATION_DESIGN_MARGIN,
                }
            )
    return findings


def design_documentation_review(item, reports, milestone):
    """Full clause 4.3.2 documentation review for one item.

    item: {"item_id", "power_dissipation_w", "mission_dose_krad",
    "has_external_interfaces", "design_revision", optional
    "derating_cases", optional "radiation_case"}. Returns
    {"owed": (...), "completeness": [...], "maturity": [...],
    "margin": [...]}, where completeness holds the missing reports,
    maturity the not-issued and stale reports, and margin the derating
    and radiation findings."""
    item_id = item["item_id"]
    owed = required_analyses(item)
    report_issues = report_maturity_findings(
        item_id, owed, reports, milestone, item.get("design_revision")
    )
    completeness = [
        finding
        for finding in report_issues
        if finding["issue"] == "missing_design_analysis_report"
    ]
    maturity = [
        finding
        for finding in report_issues
        if finding["issue"] != "missing_design_analysis_report"
    ]
    return {
        "owed": owed,
        "completeness": completeness,
        "maturity": maturity,
        "margin": margin_findings(
            item_id,
            item.get("derating_cases", ()),
            item.get("radiation_case"),
        ),
    }


FINDING_KEYS = ("completeness", "maturity", "margin")


def is_documentation_set_complete(review):
    """True when the completeness, maturity and margin finding lists of
    a design_documentation_review result are all empty -- the item
    satisfies clause 4.3.2 for this audit."""
    return all(len(review[key]) == 0 for key in FINDING_KEYS)
