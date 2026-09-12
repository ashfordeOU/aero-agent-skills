#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.11.1 electrical power engineering
verification provisions (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard requires the electrical power
engineering requirements to carry verification provisions -- a
verification method and the review point at which the evidence is
presented -- and requires the evidence to represent the worst case of
the power system rather than a nominal operating point. This module
implements the checkable part of that clause: categorization of a
power verification item into its engineering family, the admissible
method set that follows from the item, the earliest review at which a
given method can hand over mature evidence, the mandatory worst-case
power condition set each item's evidence must cover (end-of-life
degradation, maximum eclipse, worst-case solar aspect, thermal
corners, fault current), the demonstrated power margin computed from
available against demanded power, and the coverage of the required
item set by the declared provisions. It does not size an array, does
not run a load-flow, and does not write the verification control
document.
"""

import math

# Programme review points in chronological order.
REVIEW_POINTS = ("PDR", "CDR", "QR", "AR")

# Verification methods recognised by the electrical engineering chain.
VERIFICATION_METHODS = frozenset(
    {"analysis", "test", "review_of_design", "inspection", "similarity"}
)

# Earliest review at which a method can present mature closure evidence.
# Review-of-design and similarity rest on documentation that already
# exists at the preliminary baseline; an analysis closes against the
# detailed design baseline; an inspection needs manufactured hardware;
# a test needs a qualification-configuration model.
METHOD_EARLIEST_REVIEW = {
    "review_of_design": "PDR",
    "similarity": "PDR",
    "analysis": "CDR",
    "inspection": "CDR",
    "test": "QR",
}

# Power engineering verification items: family, admissible methods, the
# worst-case conditions the evidence must represent, and whether the
# item closes against a numeric power margin.
POWER_VERIFICATION_ITEMS = {
    "power_budget": {
        "family": "budget",
        "methods": frozenset({"analysis", "review_of_design"}),
        "conditions": frozenset(
            {"end_of_life", "worst_case_load_case", "maximum_eclipse"}
        ),
        "margin_required": True,
    },
    "energy_balance": {
        "family": "budget",
        "methods": frozenset({"analysis"}),
        "conditions": frozenset(
            {"end_of_life", "maximum_eclipse", "worst_case_solar_aspect"}
        ),
        "margin_required": True,
    },
    "solar_array_sizing": {
        "family": "sizing",
        "methods": frozenset({"analysis", "test", "similarity"}),
        "conditions": frozenset(
            {"end_of_life", "worst_case_solar_aspect", "hot_case_temperature"}
        ),
        "margin_required": True,
    },
    "battery_capacity": {
        "family": "sizing",
        "methods": frozenset({"analysis", "test"}),
        "conditions": frozenset(
            {"end_of_life", "maximum_eclipse", "cold_case_temperature"}
        ),
        "margin_required": True,
    },
    "bus_voltage_stability": {
        "family": "dynamic",
        "methods": frozenset({"analysis", "test"}),
        "conditions": frozenset(
            {"worst_case_load_step", "maximum_source_impedance_case"}
        ),
        "margin_required": False,
    },
    "power_protection_coordination": {
        "family": "protection",
        "methods": frozenset({"analysis", "test"}),
        "conditions": frozenset({"worst_case_fault_current", "cold_case_temperature"}),
        "margin_required": False,
    },
    "harness_voltage_drop": {
        "family": "budget",
        "methods": frozenset({"analysis", "test", "inspection"}),
        "conditions": frozenset({"worst_case_load_case", "hot_case_temperature"}),
        "margin_required": False,
    },
}

# A margin computed from a difference of floats can land a few units in
# the last place under an exactly-satisfied requirement. The tolerance
# absorbs that representation error; it does not relax the requirement.
MARGIN_REL_TOL = 1e-9
MARGIN_ABS_TOL = 1e-12


def categorize_verification_item(item_kind):
    """Engineering family of a power verification item: "budget",
    "sizing", "dynamic" or "protection". Raises ValueError for an item
    that is not an E-ST-20C clause 5.11.1 power engineering item."""
    spec = POWER_VERIFICATION_ITEMS.get(item_kind)
    if spec is None:
        raise ValueError(
            "unrecognized power verification item %r under "
            "E-ST-20C clause 5.11.1" % (item_kind,)
        )
    return spec["family"]


def admissible_methods(item_kind):
    """Set of verification methods that can produce closure evidence for
    a power verification item. Raises ValueError for an unknown item."""
    categorize_verification_item(item_kind)
    return POWER_VERIFICATION_ITEMS[item_kind]["methods"]


def mandatory_conditions(item_kind):
    """Worst-case power conditions the evidence for an item must
    represent. Raises ValueError for an unknown item."""
    categorize_verification_item(item_kind)
    return POWER_VERIFICATION_ITEMS[item_kind]["conditions"]


def earliest_closure_review(method):
    """Earliest review point at which a method can hand over mature
    evidence. Raises ValueError for an unrecognized method."""
    review = METHOD_EARLIEST_REVIEW.get(method)
    if review is None:
        raise ValueError(
            "unrecognized verification method %r for power engineering" % (method,)
        )
    return review


def review_index(review_point):
    """Chronological index of a programme review point. Raises
    ValueError for a review point outside the programme sequence."""
    try:
        return REVIEW_POINTS.index(review_point)
    except ValueError:
        raise ValueError(
            "unrecognized review point %r (expected one of %s)"
            % (review_point, ", ".join(REVIEW_POINTS))
        ) from None


def power_margin_fraction(available_w, demanded_w):
    """Demonstrated power margin as a fraction of the demand:
    (available - demanded) / demanded. Raises ValueError for a
    non-positive demand or a negative availability."""
    for label, value in (("available_w", available_w), ("demanded_w", demanded_w)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number, got %r" % (label, value))
    if demanded_w <= 0.0:
        raise ValueError("demanded_w must be positive, got %r" % (demanded_w,))
    if available_w < 0.0:
        raise ValueError("available_w must not be negative, got %r" % (available_w,))
    return (float(available_w) - float(demanded_w)) / float(demanded_w)


def margin_meets_requirement(margin, required_margin):
    """True when a demonstrated margin satisfies the required margin.
    An exactly-satisfied requirement that lands a few units in the last
    place low through floating-point subtraction still passes; a real
    shortfall does not. Raises ValueError for a negative requirement."""
    if not isinstance(required_margin, (int, float)) or isinstance(
        required_margin, bool
    ):
        raise ValueError(
            "required_margin must be a real number, got %r" % (required_margin,)
        )
    if required_margin < 0.0:
        raise ValueError(
            "required_margin must not be negative, got %r" % (required_margin,)
        )
    if margin >= required_margin:
        return True
    return math.isclose(
        margin, required_margin, rel_tol=MARGIN_REL_TOL, abs_tol=MARGIN_ABS_TOL
    )


def missing_conditions(item_kind, covered_conditions):
    """Sorted list of mandatory worst-case conditions the declared
    evidence does not cover. Raises ValueError for an unknown item or a
    condition set that is not an iterable of strings."""
    required = mandatory_conditions(item_kind)
    if isinstance(covered_conditions, str) or covered_conditions is None:
        raise ValueError(
            "covered_conditions must be an iterable of condition names, got %r"
            % (covered_conditions,)
        )
    covered = set(covered_conditions)
    return sorted(required - covered)


def check_verification_provision(provision):
    """Sorted findings against one power verification provision.

    provision keys: item_kind, method, review_point, evidence_artefact,
    covered_conditions, and for a margin item available_power_w,
    demanded_power_w and required_margin. Raises ValueError for an
    unknown item, method or review point -- those are inputs the
    provision cannot legally carry, not findings."""
    item_kind = provision.get("item_kind")
    family = categorize_verification_item(item_kind)
    method = provision.get("method")
    earliest = earliest_closure_review(method)
    review_point = provision.get("review_point")
    planned_index = review_index(review_point)
    findings = []
    if method not in admissible_methods(item_kind):
        findings.append(
            "method %r cannot produce closure evidence for %s item %r"
            % (method, family, item_kind)
        )
    if planned_index < review_index(earliest):
        findings.append(
            "review point %r is earlier than %r, the first review at which "
            "method %r can present mature evidence"
            % (review_point, earliest, method)
        )
    artefact = provision.get("evidence_artefact")
    if not isinstance(artefact, str) or not artefact.strip():
        findings.append("no evidence artefact named for item %r" % (item_kind,))
    for condition in missing_conditions(item_kind, provision.get("covered_conditions", ())):
        findings.append(
            "worst-case condition %r not represented in the evidence for %r"
            % (condition, item_kind)
        )
    if POWER_VERIFICATION_ITEMS[item_kind]["margin_required"]:
        available = provision.get("available_power_w")
        demanded = provision.get("demanded_power_w")
        required = provision.get("required_margin")
        if available is None or demanded is None or required is None:
            findings.append(
                "item %r closes against a power margin but the provision "
                "carries no available/demanded/required margin data" % (item_kind,)
            )
        else:
            margin = power_margin_fraction(available, demanded)
            if not margin_meets_requirement(margin, required):
                findings.append(
                    "demonstrated power margin %.6f is below the required %.6f "
                    "for item %r" % (margin, float(required), item_kind)
                )
    return sorted(findings)


def verification_coverage(provisions, required_items):
    """Fraction of the required power verification items that carry at
    least one provision, rounded to six decimals. Raises ValueError for
    an empty required set."""
    required = set(required_items)
    if not required:
        raise ValueError("required_items must name at least one verification item")
    for item_kind in required:
        categorize_verification_item(item_kind)
    declared = {p.get("item_kind") for p in provisions}
    covered = required & declared
    return round(len(covered) / float(len(required)), 6)


def aggregate_power_verification(provisions, required_items):
    """Full clause 5.11.1 review of a set of power verification
    provisions.

    Returns a mapping with per-item findings, the required items with no
    provision, the declared provisions pointing at items outside the
    required set, the coverage fraction and the overall compliance flag.
    The provision set is compliant only when every list is empty and the
    coverage is complete."""
    required = set(required_items)
    coverage = verification_coverage(provisions, required)
    item_findings = {}
    orphan_items = []
    for provision in provisions:
        item_kind = provision.get("item_kind")
        findings = check_verification_provision(provision)
        if item_kind not in required:
            orphan_items.append(item_kind)
        if findings:
            item_findings.setdefault(item_kind, []).extend(findings)
    uncovered = sorted(required - {p.get("item_kind") for p in provisions})
    compliant = (
        not item_findings
        and not uncovered
        and not orphan_items
        and math.isclose(coverage, 1.0, rel_tol=MARGIN_REL_TOL, abs_tol=MARGIN_ABS_TOL)
    )
    return {
        "coverage": coverage,
        "item_findings": {k: sorted(v) for k, v in item_findings.items()},
        "uncovered_items": uncovered,
        "orphan_items": sorted(set(orphan_items)),
        "compliant": compliant,
    }
