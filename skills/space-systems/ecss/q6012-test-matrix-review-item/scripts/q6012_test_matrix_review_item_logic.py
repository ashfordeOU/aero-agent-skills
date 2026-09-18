"""Test matrix review item of a device design review.

Anchor: ECSS-Q-ST-60-12C clause 7.3.8 (design review -- the planned
measurement matrix review item). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the requirement list and the planned verification activities,
   refusing repeated identifiers on either side.
2. Trace forwards: every requirement to at least one activity that is
   admissible for it, carries measurable pass criteria, and between them
   cover every condition the requirement is specified over.
3. Trace backwards: every activity to at least one requirement that exists,
   so an activity covering nothing and an activity citing an unknown
   requirement are separated.
4. Report the coverage reached, overall and over the requirements grouped as
   critical, and close the item only when nothing is open.
"""

__all__ = [
    "METHODS",
    "validate_requirement",
    "validate_activity",
    "normalise_matrix",
    "activities_for_requirement",
    "admissible_activities",
    "condition_gaps",
    "unverified_requirements",
    "orphan_activities",
    "unknown_requirement_references",
    "coverage_fraction",
    "assess_test_matrix_review",
]

# The verification methods a planned activity may declare.
METHODS = ("test", "analysis", "inspection", "review-of-design")


def _name(value, label):
    """Return a non-empty stripped identifier string."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _name_list(values, label, allow_empty=False):
    """Return a de-duplicated, order-preserving list of identifier strings."""
    if not isinstance(values, (list, tuple)):
        raise ValueError("%s must be a sequence, got %r" % (label, values))
    if not values and not allow_empty:
        raise ValueError("%s must not be empty" % label)
    out = []
    for item in values:
        text = _name(item, "%s entry" % label).lower()
        if text not in out:
            out.append(text)
    return out


def validate_requirement(requirement):
    """Return one validated requirement record.

    Keys: id, conditions (the corners it is specified over), methods_allowed
    (the verification methods that may discharge it), optional critical flag.
    """
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping, got %r" % (requirement,))
    for key in ("id", "conditions", "methods_allowed"):
        if key not in requirement:
            raise ValueError("requirement missing required key '%s'" % key)
    identifier = _name(requirement["id"], "requirement id").lower()
    conditions = _name_list(requirement["conditions"], "requirement conditions")
    methods = _name_list(requirement["methods_allowed"], "requirement methods_allowed")
    for method in methods:
        if method not in METHODS:
            raise ValueError(
                "requirement %s allows unknown method %r; methods are %s"
                % (identifier, method, METHODS)
            )
    critical = requirement.get("critical", False)
    if not isinstance(critical, bool):
        raise ValueError("requirement critical flag must be a boolean")
    return {
        "id": identifier,
        "conditions": conditions,
        "methods_allowed": methods,
        "critical": critical,
    }


def validate_activity(activity):
    """Return one validated verification activity record.

    Keys: id, method, covers (requirement ids), conditions (the corners the
    activity is run at), pass_criteria (whether measurable criteria exist).
    """
    if not isinstance(activity, dict):
        raise ValueError("activity must be a mapping, got %r" % (activity,))
    for key in ("id", "method", "covers", "conditions", "pass_criteria"):
        if key not in activity:
            raise ValueError("activity missing required key '%s'" % key)
    identifier = _name(activity["id"], "activity id").lower()
    method = _name(activity["method"], "activity method").lower()
    if method not in METHODS:
        raise ValueError(
            "activity %s declares unknown method %r; methods are %s"
            % (identifier, method, METHODS)
        )
    covers = _name_list(activity["covers"], "activity covers", allow_empty=True)
    conditions = _name_list(activity["conditions"], "activity conditions", allow_empty=True)
    criteria = activity["pass_criteria"]
    if not isinstance(criteria, bool):
        raise ValueError("activity pass_criteria flag must be a boolean")
    return {
        "id": identifier,
        "method": method,
        "covers": covers,
        "conditions": conditions,
        "pass_criteria": criteria,
    }


def normalise_matrix(requirements, activities):
    """Return the validated (requirements, activities) pair of the matrix."""
    if not isinstance(requirements, (list, tuple)) or not requirements:
        raise ValueError("requirements must be a non-empty sequence")
    if not isinstance(activities, (list, tuple)):
        raise ValueError("activities must be a sequence")
    reqs = []
    seen = set()
    for requirement in requirements:
        record = validate_requirement(requirement)
        if record["id"] in seen:
            raise ValueError("requirement %s is listed more than once" % record["id"])
        seen.add(record["id"])
        reqs.append(record)
    acts = []
    seen_acts = set()
    for activity in activities:
        record = validate_activity(activity)
        if record["id"] in seen_acts:
            raise ValueError("activity %s is listed more than once" % record["id"])
        seen_acts.add(record["id"])
        acts.append(record)
    return (reqs, acts)


def activities_for_requirement(requirement, activities):
    """Return every activity that names this requirement, admissible or not."""
    return [a for a in activities if requirement["id"] in a["covers"]]


def admissible_activities(requirement, activities):
    """Return the activities that may actually discharge this requirement.

    An activity is admissible when its method is one the requirement permits
    and it carries measurable pass criteria; anything else is planned work
    that cannot close the requirement.
    """
    admissible = []
    for activity in activities_for_requirement(requirement, activities):
        if activity["method"] not in requirement["methods_allowed"]:
            continue
        if not activity["pass_criteria"]:
            continue
        admissible.append(activity)
    return admissible


def condition_gaps(requirement, activities):
    """Return the conditions no admissible activity covers for this requirement."""
    covered = set()
    for activity in admissible_activities(requirement, activities):
        covered.update(activity["conditions"])
    return [c for c in requirement["conditions"] if c not in covered]


def unverified_requirements(requirements, activities):
    """Return the requirements the matrix does not close, each with its reason."""
    open_items = []
    for requirement in requirements:
        named = activities_for_requirement(requirement, activities)
        admissible = admissible_activities(requirement, activities)
        if not named:
            reason = "no verification activity names this requirement"
        elif not admissible:
            reason = (
                "every activity naming it is inadmissible: wrong method for the "
                "requirement, or no measurable pass criteria"
            )
        else:
            gaps = condition_gaps(requirement, activities)
            if gaps:
                reason = "conditions not covered: %s" % ", ".join(gaps)
            else:
                continue
        open_items.append({"id": requirement["id"], "reason": reason})
    return open_items


def orphan_activities(requirements, activities):
    """Return activities that close no requirement in the matrix."""
    known = {r["id"] for r in requirements}
    orphans = []
    for activity in activities:
        if not activity["covers"]:
            orphans.append(activity["id"])
            continue
        if not any(c in known for c in activity["covers"]):
            orphans.append(activity["id"])
    return orphans


def unknown_requirement_references(requirements, activities):
    """Return (activity id, requirement id) pairs citing a requirement not listed."""
    known = {r["id"] for r in requirements}
    dangling = []
    for activity in activities:
        for reference in activity["covers"]:
            if reference not in known:
                dangling.append((activity["id"], reference))
    return dangling


def coverage_fraction(total, closed):
    """Return the fraction of requirements the matrix closes."""
    for label, value in (("total", total), ("closed", closed)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (label, value))
        if value < 0:
            raise ValueError("%s must not be negative, got %d" % (label, value))
    if total == 0:
        raise ValueError("coverage of an empty requirement set is undefined")
    if closed > total:
        raise ValueError("closed %d exceeds the total %d requirements" % (closed, total))
    return closed / total


def assess_test_matrix_review(spec):
    """Run the clause 7.3.8 test matrix review item end to end.

    spec keys: requirements, activities.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("requirements", "activities"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    requirements, activities = normalise_matrix(spec["requirements"], spec["activities"])
    open_items = unverified_requirements(requirements, activities)
    open_ids = {item["id"] for item in open_items}
    orphans = orphan_activities(requirements, activities)
    dangling = unknown_requirement_references(requirements, activities)
    without_criteria = [a["id"] for a in activities if not a["pass_criteria"]]
    total = len(requirements)
    closed = total - len(open_ids)
    critical = [r for r in requirements if r["critical"]]
    critical_closed = len([r for r in critical if r["id"] not in open_ids])
    findings = []
    for item in open_items:
        findings.append("requirement %s is not closed: %s" % (item["id"], item["reason"]))
    for activity_id in orphans:
        findings.append(
            "activity %s closes no requirement in the matrix" % activity_id
        )
    for activity_id, reference in dangling:
        findings.append(
            "activity %s cites requirement %s, which the matrix does not list"
            % (activity_id, reference)
        )
    for activity_id in without_criteria:
        findings.append(
            "activity %s is planned without measurable pass criteria" % activity_id
        )
    return {
        "requirements": requirements,
        "activities": activities,
        "unverified": open_items,
        "orphan_activities": orphans,
        "unknown_references": dangling,
        "activities_without_criteria": without_criteria,
        "coverage": coverage_fraction(total, closed),
        "critical_coverage": (
            coverage_fraction(len(critical), critical_closed) if critical else None
        ),
        "findings": findings,
        "disposition": "closed" if not findings else "open",
    }
