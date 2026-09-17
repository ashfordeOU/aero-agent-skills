#!/usr/bin/env python3
"""Routing a class 2 application specific integrated circuit to its dedicated standard.

Anchor: ECSS-Q-ST-60C clause 5.6.2 (a class 2 application specific integrated
circuit is developed and reused under the dedicated ASIC and FPGA development
standard rather than under the general component rules). Paraphrased into an
implementable procedure; no standard text is reproduced.

The general component rules stop at the package. Everything inside it — the
design, the silicon it is cut into, the verification behind it — belongs to
the dedicated standard, and clause 5.6.2 is the referral: which flow of that
standard the device enters, which activities that flow carries, and, for a
class 2 device leaning on heritage, which of those activities may rest on the
referenced qualification instead of being run again.

Procedure implemented here
--------------------------
1. Validate the referral case: the device category, the declared procurement
   origin, the heritage records a reuse claim leans on, and the evidence
   references behind it.
2. Compare the candidate build against the referenced build axis by axis and
   group the differences into silicon, design and assembly movements.
3. Build the activity plan the category carries inside the dedicated standard.
4. Split that plan into activities the heritage still covers and activities
   the movements invalidate, and count the residual workload.
5. Route the device into the dedicated standard: a full development flow, a
   delta development flow, a reviewed reuse flow, or no referral at all while
   the reuse evidence is short.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

__all__ = [
    "ASIC_CATEGORIES",
    "PROCUREMENT_ORIGINS",
    "SILICON_AXES",
    "DESIGN_AXES",
    "ASSEMBLY_AXES",
    "HERITAGE_AXES",
    "AXIS_GROUPS",
    "BASE_ACTIVITIES",
    "CATEGORY_EXTRA_ACTIVITIES",
    "ACTIVITY_INVALIDATORS",
    "ALWAYS_REPERFORMED",
    "REQUIRED_REUSE_EVIDENCE",
    "DEFAULT_REFERRAL_POLICY",
    "FULL_DEVELOPMENT",
    "DELTA_DEVELOPMENT",
    "REVIEWED_REUSE",
    "REFERRAL_BLOCKED",
    "QUALIFICATION_LAPSED",
    "validate_referral_policy",
    "validate_build_record",
    "validate_case",
    "changed_axes",
    "group_changed_axes",
    "activity_plan",
    "inheritance_split",
    "reperform_ratio",
    "missing_reuse_evidence",
    "qualification_is_current",
    "route_asic_referral",
    "assess_asic_referral",
]

ASIC_CATEGORIES = (
    "full-custom",
    "standard-cell",
    "structured-array",
    "gate-array",
    "analogue-mixed-signal",
)

PROCUREMENT_ORIGINS = ("new-development", "re-target", "catalogue-reuse")

# The three ways a candidate build can differ from the one that was qualified.
SILICON_AXES = ("foundry", "technology_node_nm", "mask_set_revision", "process_option")
DESIGN_AXES = ("design_database_revision", "cell_library_revision", "functional_scope")
ASSEMBLY_AXES = ("package_type", "die_attach_process", "lid_seal_process")
HERITAGE_AXES = SILICON_AXES + DESIGN_AXES + ASSEMBLY_AXES

AXIS_GROUPS = {
    "silicon": SILICON_AXES,
    "design": DESIGN_AXES,
    "assembly": ASSEMBLY_AXES,
}

# The activity set the dedicated standard carries for every category.
BASE_ACTIVITIES = (
    "design-requirements-review",
    "design-rule-compliance-check",
    "functional-verification-campaign",
    "timing-and-signal-integrity-analysis",
    "radiation-hardness-evaluation",
    "prototype-wafer-lot-manufacture",
    "electrical-characterisation-over-temperature",
    "package-qualification-testing",
    "lot-acceptance-test-definition",
    "reliability-and-life-testing",
)

# What a category adds on top of the base set.
CATEGORY_EXTRA_ACTIVITIES = {
    "full-custom": ("full-custom-layout-verification",),
    "standard-cell": (),
    "structured-array": ("array-configuration-verification",),
    "gate-array": ("array-configuration-verification",),
    "analogue-mixed-signal": (
        "analogue-block-characterisation",
        "mixed-signal-isolation-analysis",
    ),
}

# Which movement groups invalidate the heritage behind each activity. An
# activity whose invalidator groups all stayed still may rest on the reference.
ACTIVITY_INVALIDATORS = {
    "design-requirements-review": ("silicon", "design", "assembly"),
    "design-rule-compliance-check": ("silicon",),
    "functional-verification-campaign": ("design",),
    "timing-and-signal-integrity-analysis": ("silicon", "design"),
    "radiation-hardness-evaluation": ("silicon",),
    "prototype-wafer-lot-manufacture": ("silicon",),
    "electrical-characterisation-over-temperature": ("silicon", "design"),
    "package-qualification-testing": ("assembly",),
    "lot-acceptance-test-definition": ("silicon", "assembly"),
    "reliability-and-life-testing": ("silicon", "assembly"),
    "full-custom-layout-verification": ("silicon", "design"),
    "array-configuration-verification": ("design",),
    "analogue-block-characterisation": ("silicon", "design"),
    "mixed-signal-isolation-analysis": ("silicon", "design"),
}

# Activities that belong to this order and never rest on an earlier one.
ALWAYS_REPERFORMED = ("design-requirements-review", "lot-acceptance-test-definition")

REQUIRED_REUSE_EVIDENCE = (
    "referenced-qualification-report",
    "heritage-usage-record",
    "delta-analysis-note",
    "foundry-process-change-notice-review",
)

DEFAULT_REFERRAL_POLICY = {
    # Class 2 accepts a longer currency window than a class 1 referral.
    "qualification_validity_months": 84,
    # Two or more silicon movements put the device back through development.
    "silicon_movements_forcing_full_development": 2,
}

FULL_DEVELOPMENT = "dedicated-standard-full-development"
DELTA_DEVELOPMENT = "dedicated-standard-delta-development"
REVIEWED_REUSE = "dedicated-standard-reviewed-reuse"
REFERRAL_BLOCKED = "dedicated-standard-referral-blocked"
QUALIFICATION_LAPSED = "referenced-qualification-currency-lapsed"


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def validate_referral_policy(policy=None):
    """Validate the referral policy, returning the default when omitted."""
    if policy is None:
        return dict(DEFAULT_REFERRAL_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (type(policy).__name__,))
    merged = dict(DEFAULT_REFERRAL_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_REFERRAL_POLICY:
            raise ValueError("unknown policy key %r" % (key,))
        merged[key] = value
    months = merged["qualification_validity_months"]
    if not _is_int(months) or months < 1:
        raise ValueError(
            "qualification_validity_months must be a positive integer, got %r"
            % (months,)
        )
    threshold = merged["silicon_movements_forcing_full_development"]
    if not _is_int(threshold) or threshold < 1:
        raise ValueError(
            "silicon_movements_forcing_full_development must be a positive integer,"
            " got %r" % (threshold,)
        )
    return merged


def validate_build_record(label, record):
    """Validate one build record: every heritage axis carries a value."""
    if not isinstance(record, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, type(record).__name__))
    validated = {}
    for axis in HERITAGE_AXES:
        if axis not in record:
            raise ValueError("%s has no %r" % (label, axis))
        value = record[axis]
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise ValueError(
                "%s %s must be a string or an integer, got %r" % (label, axis, value)
            )
        if isinstance(value, str) and not value.strip():
            raise ValueError("%s %s must not be blank" % (label, axis))
        validated[axis] = value
    return validated


def validate_case(case):
    """Validate a whole referral case and fill in its defaults."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (type(case).__name__,))
    part_number = case.get("part_number")
    if not isinstance(part_number, str) or not part_number.strip():
        raise ValueError("case needs a non-empty part_number, got %r" % (part_number,))
    category = case.get("category")
    if category not in ASIC_CATEGORIES:
        raise ValueError(
            "category must be one of %s, got %r" % (", ".join(ASIC_CATEGORIES), category)
        )
    origin = case.get("origin")
    if origin not in PROCUREMENT_ORIGINS:
        raise ValueError(
            "origin must be one of %s, got %r" % (", ".join(PROCUREMENT_ORIGINS), origin)
        )
    validated = {
        "part_number": part_number,
        "category": category,
        "origin": origin,
    }
    if origin == "new-development":
        validated["candidate"] = None
        validated["referenced"] = None
        validated["evidence"] = ()
        validated["qualification_age_months"] = None
        return validated
    validated["candidate"] = validate_build_record("candidate", case.get("candidate"))
    validated["referenced"] = validate_build_record("referenced", case.get("referenced"))
    evidence = case.get("evidence", ())
    if not isinstance(evidence, (list, tuple)):
        raise ValueError("evidence must be a list or tuple, got %r" % (evidence,))
    for item in evidence:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("evidence entries must be non-empty strings, got %r" % (item,))
    validated["evidence"] = tuple(evidence)
    age = case.get("qualification_age_months")
    if not _is_int(age) or age < 0:
        raise ValueError(
            "qualification_age_months must be a non-negative integer, got %r" % (age,)
        )
    validated["qualification_age_months"] = age
    return validated


def changed_axes(referenced, candidate):
    """Heritage axes on which a candidate build departs from the reference."""
    left = validate_build_record("referenced", referenced)
    right = validate_build_record("candidate", candidate)
    return tuple(axis for axis in HERITAGE_AXES if left[axis] != right[axis])


def group_changed_axes(axes):
    """Group a set of moved axes into silicon, design and assembly movements."""
    if not isinstance(axes, (list, tuple)):
        raise ValueError("axes must be a list or tuple, got %r" % (axes,))
    grouped = {name: [] for name in AXIS_GROUPS}
    for axis in axes:
        placed = False
        for name, members in AXIS_GROUPS.items():
            if axis in members:
                grouped[name].append(axis)
                placed = True
                break
        if not placed:
            raise ValueError("unknown heritage axis %r" % (axis,))
    return {name: tuple(values) for name, values in grouped.items()}


def activity_plan(category):
    """Activity set the dedicated standard carries for a device category."""
    if category not in CATEGORY_EXTRA_ACTIVITIES:
        raise ValueError(
            "category must be one of %s, got %r" % (", ".join(ASIC_CATEGORIES), category)
        )
    return BASE_ACTIVITIES + CATEGORY_EXTRA_ACTIVITIES[category]


def inheritance_split(category, grouped):
    """Split the activity plan into inherited work and work to run again."""
    plan = activity_plan(category)
    if not isinstance(grouped, dict):
        raise ValueError("grouped must be a mapping, got %r" % (type(grouped).__name__,))
    for name in grouped:
        if name not in AXIS_GROUPS:
            raise ValueError("unknown movement group %r" % (name,))
    moved = {name for name in AXIS_GROUPS if grouped.get(name)}
    inherited = []
    reperformed = []
    for activity in plan:
        if activity in ALWAYS_REPERFORMED:
            reperformed.append(activity)
            continue
        invalidators = ACTIVITY_INVALIDATORS[activity]
        if moved.intersection(invalidators):
            reperformed.append(activity)
        else:
            inherited.append(activity)
    return {
        "plan": plan,
        "inherited": tuple(inherited),
        "reperformed": tuple(reperformed),
    }


def reperform_ratio(split):
    """Share of the activity plan that has to be run again."""
    if not isinstance(split, dict) or "plan" not in split or "reperformed" not in split:
        raise ValueError("split must be an inheritance split mapping")
    plan = split["plan"]
    if len(plan) == 0:
        raise ValueError("activity plan must not be empty")
    return len(split["reperformed"]) / len(plan)


def missing_reuse_evidence(evidence):
    """Required reuse evidence references the case never named."""
    if not isinstance(evidence, (list, tuple)):
        raise ValueError("evidence must be a list or tuple, got %r" % (evidence,))
    present = set(evidence)
    return tuple(item for item in REQUIRED_REUSE_EVIDENCE if item not in present)


def qualification_is_current(age_months, policy=None):
    """True while the referenced qualification is inside its currency window."""
    merged = validate_referral_policy(policy)
    if not _is_int(age_months) or age_months < 0:
        raise ValueError(
            "age_months must be a non-negative integer, got %r" % (age_months,)
        )
    return age_months <= merged["qualification_validity_months"]


def route_asic_referral(case, policy=None):
    """Route one validated case into a flow of the dedicated standard."""
    validated = validate_case(case)
    merged = validate_referral_policy(policy)
    if validated["origin"] == "new-development":
        return {
            "route": FULL_DEVELOPMENT,
            "moved_axes": (),
            "movements": {name: () for name in AXIS_GROUPS},
            "missing_evidence": (),
            "qualification_current": None,
            "findings": (),
        }
    missing = missing_reuse_evidence(validated["evidence"])
    moved = changed_axes(validated["referenced"], validated["candidate"])
    movements = group_changed_axes(moved)
    current = qualification_is_current(
        validated["qualification_age_months"], merged
    )
    findings = []
    if not current:
        findings.append(QUALIFICATION_LAPSED)
    if missing:
        return {
            "route": REFERRAL_BLOCKED,
            "moved_axes": moved,
            "movements": movements,
            "missing_evidence": missing,
            "qualification_current": current,
            "findings": tuple(findings),
        }
    silicon_moves = len(movements["silicon"])
    if silicon_moves >= merged["silicon_movements_forcing_full_development"]:
        route = FULL_DEVELOPMENT
    elif moved:
        route = DELTA_DEVELOPMENT
    elif not current:
        route = DELTA_DEVELOPMENT
    else:
        route = REVIEWED_REUSE
    return {
        "route": route,
        "moved_axes": moved,
        "movements": movements,
        "missing_evidence": (),
        "qualification_current": current,
        "findings": tuple(findings),
    }


def assess_asic_referral(case, policy=None):
    """Route the device and report the activity split the route carries."""
    validated = validate_case(case)
    routing = route_asic_referral(case, policy)
    if routing["route"] == FULL_DEVELOPMENT:
        plan = activity_plan(validated["category"])
        split = {"plan": plan, "inherited": (), "reperformed": plan}
    elif routing["route"] == REFERRAL_BLOCKED:
        plan = activity_plan(validated["category"])
        split = {"plan": plan, "inherited": (), "reperformed": plan}
    else:
        split = inheritance_split(validated["category"], routing["movements"])
    return {
        "part_number": validated["part_number"],
        "category": validated["category"],
        "origin": validated["origin"],
        "route": routing["route"],
        "moved_axes": routing["moved_axes"],
        "movements": routing["movements"],
        "missing_evidence": routing["missing_evidence"],
        "qualification_current": routing["qualification_current"],
        "activity_plan": split["plan"],
        "inherited_activities": split["inherited"],
        "reperformed_activities": split["reperformed"],
        "reperform_ratio": reperform_ratio(split),
        "findings": routing["findings"],
        "referred": routing["route"] != REFERRAL_BLOCKED,
    }
