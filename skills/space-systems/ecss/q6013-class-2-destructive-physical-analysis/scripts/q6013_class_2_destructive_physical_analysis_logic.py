"""Destructive physical sampling of commercial EEE lots at the middle class.

Anchor: ECSS-Q-ST-60-13C clause 5.3.9 (intermediate assurance class use of
commercial EEE components -- destructive physical sampling that verifies the
construction actually delivered). Paraphrased into an implementable
procedure; no standard text is reproduced.

What this class changes relative to the class above
---------------------------------------------------
Two relaxations define the intermediate class and both are implemented here.
A manufacturer teardown report may be credited in place of part of the
receiving activity's own sampling, provided the report names the same
date-code group, is signed, is young enough to describe the same build, and
covers every construction criterion the group is judged on. And a single
major construction defect calls for a second sample rather than disposing of
the group outright, so a one-off assembly escape is separated from a process
that is producing them.

Procedure implemented here
--------------------------
1. Validate the sampling policy: the proportional fraction, the sample floor,
   the reduced confirmation sample a credited group still owes, the age limit
   on a credited report and the major-defect count that calls for a resample.
2. Resolve the delivery into date-code groups. A date code is one build, and
   a group with neither a teardown nor a credited report has not been sampled
   at all.
3. Decide credit for each group from the manufacturer report offered against
   it, then size the sample: the proportional fraction rounded up against the
   floor for an uncredited group, the confirmation sample for a credited one,
   never more than the group holds.
4. Categorize every observed construction defect against a named register.
   An unregistered code is refused rather than quietly treated as cosmetic.
5. Evaluate the numeric construction criteria the teardown produces:
   die-attach voiding, on the total voided area and on the largest single
   void, and wire bond pull strength, on the sample minimum and the mean.
6. Fold the numeric failures back into the defect record and dispose each
   group: accepted, accepted with a recorded observation, second sample
   required, or rejected.
7. Close the delivery on one verdict with the findings that produced it.
"""

import math

__all__ = [
    "FRACTION_TOLERANCE",
    "DEFAULT_DPA_POLICY",
    "REQUIRED_CRITERIA",
    "MAJOR_DEFECTS",
    "MINOR_DEFECTS",
    "GROUP_ACCEPTED",
    "GROUP_ACCEPTED_WITH_RECORD",
    "GROUP_RESAMPLE_REQUIRED",
    "GROUP_REJECTED",
    "GROUP_NOT_SAMPLED",
    "DPA_NOT_PERFORMED",
    "DPA_SAMPLE_NOT_FEASIBLE",
    "DPA_CONSTRUCTION_REJECTED",
    "DPA_RESAMPLE_REQUIRED",
    "DPA_MEETS_CLASS_TWO_SCOPE",
    "validate_fraction",
    "validate_dpa_policy",
    "categorize_defect",
    "categorize_defects",
    "manufacturer_credit_decision",
    "dpa_sample_size",
    "group_sample_plan",
    "void_assessment",
    "bond_pull_assessment",
    "group_disposition",
    "assess_destructive_physical_sampling",
]

# Area fractions, strengths and means are compared against declared limits. A
# value sitting exactly on a limit can land a few ULP either side of it once
# it has been divided or averaged, and the two sides round differently on
# different platforms, so the representation error is absorbed here rather
# than being allowed to flip a disposition.
FRACTION_TOLERANCE = 1e-12

DEFAULT_DPA_POLICY = {
    # Proportional sample taken from a date-code group the receiving activity
    # tears down itself.
    "sample_fraction": 0.005,
    # Floor under that proportional sample.
    "min_sample": 2,
    # Reduced sample a group still owes when a manufacturer report is
    # credited. Credit thins the sampling; it never removes it, because the
    # units in the box are not the units the report describes.
    "confirmation_sample": 1,
    # A teardown report older than this describes a build that has had time
    # to drift away from the one in the box.
    "max_report_age_months": 24,
    "allow_manufacturer_credit": True,
    # One major defect calls for a second sample at this class. More than one
    # is a process finding and disposes of the group.
    "major_defects_triggering_resample": 1,
    "allow_resample": True,
}

# The construction criteria a credited report has to have covered before it
# can stand in for part of the receiving activity's own sampling.
REQUIRED_CRITERIA = frozenset(
    {
        "internal-visual",
        "die-attach-integrity",
        "wire-bond-strength",
        "package-seal",
    }
)

# Construction defects that bear on function or on reliability over life.
MAJOR_DEFECTS = frozenset(
    {
        "wire-bond-lift",
        "wire-bond-neck-break",
        "bond-pull-below-limit",
        "die-attach-void-excess",
        "die-attach-delamination",
        "die-crack",
        "metallization-corrosion",
        "metallization-void",
        "package-seal-leak",
        "conductive-foreign-particle",
        "glassivation-crack-over-metal",
        "wrong-die-in-package",
    }
)

# Observations recorded against the group without disposing of it.
MINOR_DEFECTS = frozenset(
    {
        "external-marking-blemish",
        "lead-finish-blemish",
        "glassivation-crack-over-oxide",
        "non-conductive-foreign-particle",
        "minor-die-attach-void",
        "bond-placement-off-centre",
        "tool-mark-on-package",
    }
)

GROUP_ACCEPTED = "group-accepted"
GROUP_ACCEPTED_WITH_RECORD = "group-accepted-with-record"
GROUP_RESAMPLE_REQUIRED = "group-second-sample-required"
GROUP_REJECTED = "group-rejected"
GROUP_NOT_SAMPLED = "group-not-sampled"

DPA_NOT_PERFORMED = "destructive-sampling-not-performed"
DPA_SAMPLE_NOT_FEASIBLE = "destructive-sample-not-feasible"
DPA_CONSTRUCTION_REJECTED = "construction-rejected"
DPA_RESAMPLE_REQUIRED = "second-sample-required"
DPA_MEETS_CLASS_TWO_SCOPE = "sampling-meets-class-two-scope"


def _at_or_below(value, limit):
    """True when value is at or below limit, absorbing representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=FRACTION_TOLERANCE, abs_tol=0.0
    )


def _at_or_above(value, limit):
    """True when value is at or above limit, absorbing representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=FRACTION_TOLERANCE, abs_tol=0.0
    )


def validate_fraction(value, label, allow_zero=True):
    """Return a validated area or sampling fraction in the unit interval."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    fraction = float(value)
    if not math.isfinite(fraction):
        raise ValueError("%s must be finite" % label)
    if fraction < 0.0 or (fraction == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %r" % (label, value))
    if fraction > 1.0:
        raise ValueError("%s is a fraction and cannot exceed unity, got %r" % (label, value))
    return fraction


def _validate_count(value, label, minimum=1):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer" % label)
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (label, minimum, value))
    return value


def _validate_flag(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean" % label)
    return value


def _validate_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def _validate_strength(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    strength = float(value)
    if not math.isfinite(strength) or strength <= 0.0:
        raise ValueError("%s must be positive and finite, got %r" % (label, value))
    return strength


def validate_dpa_policy(policy):
    """Validate a sampling policy and return it unchanged.

    A policy that cannot produce a defensible sample is refused here rather
    than being allowed to produce a comfortable answer downstream.
    """
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    for key in DEFAULT_DPA_POLICY:
        if key not in policy:
            raise ValueError("policy missing required key '%s'" % key)
    validate_fraction(policy["sample_fraction"], "sample_fraction", allow_zero=False)
    minimum = _validate_count(policy["min_sample"], "min_sample")
    confirmation = _validate_count(policy["confirmation_sample"], "confirmation_sample")
    _validate_count(policy["max_report_age_months"], "max_report_age_months")
    _validate_flag(policy["allow_manufacturer_credit"], "allow_manufacturer_credit")
    _validate_flag(policy["allow_resample"], "allow_resample")
    _validate_count(
        policy["major_defects_triggering_resample"],
        "major_defects_triggering_resample",
        minimum=0,
    )
    if confirmation > minimum:
        raise ValueError(
            "confirmation_sample %d exceeds min_sample %d; a credited group would "
            "then be sampled harder than an uncredited one" % (confirmation, minimum)
        )
    return policy


def categorize_defect(code):
    """Return 'major' or 'minor' for a registered construction defect code."""
    key = _validate_text(code, "defect code").lower()
    if key in MAJOR_DEFECTS:
        return "major"
    if key in MINOR_DEFECTS:
        return "minor"
    raise ValueError(
        "defect code '%s' is not in the register; add it to the register with a "
        "category rather than letting it pass uncategorized" % key
    )


def categorize_defects(codes):
    """Group a sequence of defect codes into major and minor buckets."""
    if not isinstance(codes, (list, tuple)):
        raise ValueError("codes must be a sequence of defect codes")
    grouped = {"major": [], "minor": []}
    for code in codes:
        grouped[categorize_defect(code)].append(_validate_text(code, "defect code").lower())
    return {"major": sorted(set(grouped["major"])), "minor": sorted(set(grouped["minor"]))}


def manufacturer_credit_decision(report, date_code, policy=None):
    """Decide whether a manufacturer teardown report may be credited.

    report keys: date_code, signed, age_months, criteria_covered.
    A report is credited only when the policy permits credit at all, the
    report names the same date-code group, it is signed, it is inside the age
    limit, and it covers every construction criterion the group is judged on.
    """
    policy = validate_dpa_policy(DEFAULT_DPA_POLICY if policy is None else policy)
    date_code = _validate_text(date_code, "date_code")
    if report is None:
        return {"credited": False, "reason": "no manufacturer report offered"}
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping or None")
    for key in ("date_code", "signed", "age_months", "criteria_covered"):
        if key not in report:
            raise ValueError("report missing required key '%s'" % key)
    report_code = _validate_text(report["date_code"], "report date_code")
    signed = _validate_flag(report["signed"], "report signed")
    age = _validate_count(report["age_months"], "report age_months", minimum=0)
    covered = report["criteria_covered"]
    if not isinstance(covered, (list, tuple, set, frozenset)):
        raise ValueError("report criteria_covered must be a sequence")
    covered = {_validate_text(c, "criterion").lower() for c in covered}
    unknown = sorted(covered - REQUIRED_CRITERIA)
    if unknown:
        raise ValueError(
            "report names criteria outside the register: %s" % ", ".join(unknown)
        )
    if not policy["allow_manufacturer_credit"]:
        return {"credited": False, "reason": "policy does not permit manufacturer credit"}
    if report_code.lower() != date_code.lower():
        return {
            "credited": False,
            "reason": "report covers date code '%s', group is '%s'" % (report_code, date_code),
        }
    if not signed:
        return {"credited": False, "reason": "report is not signed by the manufacturer"}
    if age > policy["max_report_age_months"]:
        return {
            "credited": False,
            "reason": "report is %d months old, limit is %d"
            % (age, policy["max_report_age_months"]),
        }
    missing = sorted(REQUIRED_CRITERIA - covered)
    if missing:
        return {
            "credited": False,
            "reason": "report does not cover %s" % ", ".join(missing),
        }
    return {"credited": True, "reason": "report covers the group and every criterion"}


def dpa_sample_size(group_size, credited, policy=None):
    """Return the destructive sample size owed by one date-code group."""
    policy = validate_dpa_policy(DEFAULT_DPA_POLICY if policy is None else policy)
    group_size = _validate_count(group_size, "group_size")
    credited = _validate_flag(credited, "credited")
    if credited:
        return min(group_size, policy["confirmation_sample"])
    proportional = int(
        math.ceil(group_size * float(policy["sample_fraction"]) - FRACTION_TOLERANCE)
    )
    return min(group_size, max(policy["min_sample"], proportional))


def group_sample_plan(group_size, credited, policy=None):
    """Return the sample plan for one group with any feasibility finding."""
    policy = validate_dpa_policy(DEFAULT_DPA_POLICY if policy is None else policy)
    size = dpa_sample_size(group_size, credited, policy)
    findings = []
    if size >= group_size:
        findings.append(
            "date-code group holds %d unit(s) and owes a sample of %d, which consumes "
            "the group; buy a larger group rather than skipping the sampling"
            % (group_size, size)
        )
    return {
        "group_size": group_size,
        "sample_size": size,
        "credited": credited,
        "feasible": size < group_size,
        "findings": findings,
    }


def void_assessment(total_void_fraction, largest_void_fraction, limits):
    """Assess die-attach voiding against the declared area-fraction limits.

    limits keys: total_limit, largest_limit, both area fractions. Both
    criteria are evaluated: a die attach can meet the total and still fail on
    one void sitting under the hottest junction.
    """
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping")
    for key in ("total_limit", "largest_limit"):
        if key not in limits:
            raise ValueError("limits missing required key '%s'" % key)
    total_limit = validate_fraction(limits["total_limit"], "total_limit", allow_zero=False)
    largest_limit = validate_fraction(limits["largest_limit"], "largest_limit", allow_zero=False)
    total = validate_fraction(total_void_fraction, "total_void_fraction")
    largest = validate_fraction(largest_void_fraction, "largest_void_fraction")
    if not _at_or_below(largest, total):
        raise ValueError(
            "largest single void %g cannot exceed the total voided fraction %g"
            % (largest, total)
        )
    if not _at_or_below(largest_limit, total_limit):
        raise ValueError("largest_limit cannot exceed total_limit")
    defects = []
    if not _at_or_below(total, total_limit):
        defects.append("die-attach-void-excess")
    if not _at_or_below(largest, largest_limit):
        defects.append("die-attach-void-excess")
    return {
        "total_void_fraction": total,
        "largest_void_fraction": largest,
        "total_limit": total_limit,
        "largest_limit": largest_limit,
        "within_limits": not defects,
        "defects": sorted(set(defects)),
    }


def bond_pull_assessment(pull_values_g, minimum_g, mean_minimum_g):
    """Assess wire bond pull strengths against a floor and a mean floor.

    The two criteria catch different failures: one bad bond, and a whole
    sample drifting down while every individual bond still clears.
    """
    if not isinstance(pull_values_g, (list, tuple)) or not pull_values_g:
        raise ValueError("pull_values_g must be a non-empty sequence")
    values = []
    for index, value in enumerate(pull_values_g):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("pull_values_g[%d] must be a real number" % index)
        value = float(value)
        if not math.isfinite(value) or value < 0.0:
            raise ValueError("pull_values_g[%d] must be non-negative and finite" % index)
        values.append(value)
    floor = _validate_strength(minimum_g, "minimum_g")
    mean_floor = _validate_strength(mean_minimum_g, "mean_minimum_g")
    if not _at_or_below(floor, mean_floor):
        raise ValueError("minimum_g cannot exceed mean_minimum_g")
    observed_min = min(values)
    observed_mean = math.fsum(values) / len(values)
    defects = []
    if not _at_or_above(observed_min, floor):
        defects.append("bond-pull-below-limit")
    if not _at_or_above(observed_mean, mean_floor):
        defects.append("bond-pull-below-limit")
    return {
        "count": len(values),
        "minimum_observed_g": observed_min,
        "mean_observed_g": observed_mean,
        "minimum_limit_g": floor,
        "mean_limit_g": mean_floor,
        "within_limits": not defects,
        "defects": sorted(set(defects)),
    }


def group_disposition(grouped, resample_performed, policy=None):
    """Return the disposition one date-code group's defect record implies."""
    policy = validate_dpa_policy(DEFAULT_DPA_POLICY if policy is None else policy)
    if not isinstance(grouped, dict):
        raise ValueError("grouped must be a mapping with 'major' and 'minor' keys")
    for key in ("major", "minor"):
        if key not in grouped or not isinstance(grouped[key], (list, tuple)):
            raise ValueError("grouped['%s'] must be a sequence" % key)
    resample_performed = _validate_flag(resample_performed, "resample_performed")
    majors = len(grouped["major"])
    if majors == 0:
        return GROUP_ACCEPTED_WITH_RECORD if grouped["minor"] else GROUP_ACCEPTED
    if (
        policy["allow_resample"]
        and not resample_performed
        and majors <= policy["major_defects_triggering_resample"]
    ):
        return GROUP_RESAMPLE_REQUIRED
    return GROUP_REJECTED


def _assess_group(group, void_limits, bond_floor, bond_mean_floor, policy):
    if not isinstance(group, dict):
        raise ValueError("each group must be a mapping")
    for key in ("date_code", "unit_count", "teardown_performed"):
        if key not in group:
            raise ValueError("group missing required key '%s'" % key)
    date_code = _validate_text(group["date_code"], "date_code")
    unit_count = _validate_count(group["unit_count"], "unit_count")
    teardown = _validate_flag(group["teardown_performed"], "teardown_performed")
    credit = manufacturer_credit_decision(group.get("manufacturer_report"), date_code, policy)
    plan = group_sample_plan(unit_count, credit["credited"], policy)
    record = {
        "date_code": date_code,
        "unit_count": unit_count,
        "credit": credit,
        "sample_plan": plan,
        "teardown_performed": teardown,
        "findings": list(plan["findings"]),
    }
    if not teardown and not credit["credited"]:
        record["disposition"] = GROUP_NOT_SAMPLED
        record["defects"] = {"major": [], "minor": []}
        record["void_assessment"] = None
        record["bond_pull_assessment"] = None
        record["findings"].append(
            "date-code group '%s' has neither a teardown nor a credited report" % date_code
        )
        return record
    voids = void_assessment(
        group.get("total_void_fraction", 0.0),
        group.get("largest_void_fraction", 0.0),
        void_limits,
    )
    bonds = bond_pull_assessment(
        group.get("pull_values_g", [bond_mean_floor]), bond_floor, bond_mean_floor
    )
    observed = group.get("observed_defects", [])
    if not isinstance(observed, (list, tuple)):
        raise ValueError("observed_defects must be a sequence")
    defects = categorize_defects(list(observed) + voids["defects"] + bonds["defects"])
    resampled = _validate_flag(
        group.get("resample_performed", False), "resample_performed"
    )
    record["void_assessment"] = voids
    record["bond_pull_assessment"] = bonds
    record["defects"] = defects
    record["disposition"] = group_disposition(defects, resampled, policy)
    for code in defects["major"]:
        record["findings"].append(
            "major construction defect '%s' in date-code group '%s'" % (code, date_code)
        )
    for code in defects["minor"]:
        record["findings"].append(
            "minor observation '%s' recorded against date-code group '%s'"
            % (code, date_code)
        )
    return record


def assess_destructive_physical_sampling(case, policy=None):
    """Run the clause 5.3.9 assessment for one delivered commercial lot.

    case keys: groups (a non-empty sequence of date-code group records),
    void_limits, bond_minimum_g, bond_mean_minimum_g.
    """
    policy = validate_dpa_policy(DEFAULT_DPA_POLICY if policy is None else policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("groups", "void_limits", "bond_minimum_g", "bond_mean_minimum_g"):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)
    groups = case["groups"]
    if not isinstance(groups, (list, tuple)) or not groups:
        raise ValueError("groups must be a non-empty sequence of date-code groups")
    bond_floor = _validate_strength(case["bond_minimum_g"], "bond_minimum_g")
    bond_mean_floor = _validate_strength(case["bond_mean_minimum_g"], "bond_mean_minimum_g")
    seen = set()
    records = []
    findings = []
    total_units = 0
    total_sample = 0
    for group in groups:
        record = _assess_group(
            group, case["void_limits"], bond_floor, bond_mean_floor, policy
        )
        key = record["date_code"].lower()
        if key in seen:
            raise ValueError("date code '%s' appears twice" % record["date_code"])
        seen.add(key)
        records.append(record)
        findings.extend(record["findings"])
        total_units += record["unit_count"]
        total_sample += record["sample_plan"]["sample_size"]
    if len(records) > 1:
        findings.append(
            "delivery spans %d date codes; each is a separate build and is sampled "
            "in its own right" % len(records)
        )
    dispositions = [record["disposition"] for record in records]
    credited = [r["date_code"] for r in records if r["credit"]["credited"]]
    infeasible = [r["date_code"] for r in records if not r["sample_plan"]["feasible"]]
    if GROUP_NOT_SAMPLED in dispositions:
        verdict = DPA_NOT_PERFORMED
    elif infeasible:
        verdict = DPA_SAMPLE_NOT_FEASIBLE
    elif GROUP_REJECTED in dispositions:
        verdict = DPA_CONSTRUCTION_REJECTED
    elif GROUP_RESAMPLE_REQUIRED in dispositions:
        verdict = DPA_RESAMPLE_REQUIRED
    else:
        verdict = DPA_MEETS_CLASS_TWO_SCOPE
    return {
        "groups": records,
        "total_units": total_units,
        "total_sample": total_sample,
        "credited_date_codes": credited,
        "infeasible_date_codes": infeasible,
        "verdict": verdict,
        "accepted": verdict == DPA_MEETS_CLASS_TWO_SCOPE,
        "findings": findings,
    }
