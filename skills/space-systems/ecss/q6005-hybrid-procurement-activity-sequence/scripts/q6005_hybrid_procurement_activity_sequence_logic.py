"""Procurement activity ordering for hybrid microcircuits.

Anchor: ECSS-Q-ST-60-05 clause 4 (the sequence of procurement activities and
the point in that sequence at which each manufacturer category joins it).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise the manufacturer category: a maker whose production line already
   carries an approval, or a maker whose line does not.
2. Derive the ordered set of activities that category owes. The requirement
   definition and the manufacturer selection are common to both; the line
   evaluation and the line approval belong to the non-approved category only,
   and an approved-line maker joins the sequence at the specification
   agreement instead.
3. Derive each activity's prerequisites inside that ordered set, so an audit
   of an executed step list can say which step ran before its predecessor
   rather than only that the list is out of order somewhere.
4. Grade an executed step list: unknown or repeated names are input errors,
   a step outside the category's set is a not-applicable finding, a step whose
   prerequisite is still outstanding is an ordering finding.
5. Report the entry point, the outstanding activities, the next activity due
   and the fraction of the category's sequence completed.
"""

__all__ = [
    "CATEGORY_APPROVED_LINE",
    "CATEGORY_NO_APPROVED_LINE",
    "CATEGORIES",
    "PROCUREMENT_SEQUENCE",
    "COMMON_OPENING_STEPS",
    "LINE_APPROVAL_STEPS",
    "normalize_category",
    "normalize_step",
    "applicable_steps",
    "skipped_steps",
    "entry_step",
    "prerequisites",
    "step_position",
    "validate_executed",
    "ordering_findings",
    "not_applicable_findings",
    "remaining_steps",
    "next_step",
    "completion_fraction",
    "assess_procurement_sequence",
]

CATEGORY_APPROVED_LINE = "approved-line"
CATEGORY_NO_APPROVED_LINE = "no-approved-line"
CATEGORIES = (CATEGORY_APPROVED_LINE, CATEGORY_NO_APPROVED_LINE)

# Spellings an ordering paperwork trail tends to carry for the same category.
_CATEGORY_ALIASES = {
    "approved-line": CATEGORY_APPROVED_LINE,
    "approved_line": CATEGORY_APPROVED_LINE,
    "approved line": CATEGORY_APPROVED_LINE,
    "line-approved": CATEGORY_APPROVED_LINE,
    "category-1": CATEGORY_APPROVED_LINE,
    "no-approved-line": CATEGORY_NO_APPROVED_LINE,
    "no_approved_line": CATEGORY_NO_APPROVED_LINE,
    "no approved line": CATEGORY_NO_APPROVED_LINE,
    "non-approved-line": CATEGORY_NO_APPROVED_LINE,
    "unapproved-line": CATEGORY_NO_APPROVED_LINE,
    "category-2": CATEGORY_NO_APPROVED_LINE,
}

# The whole activity chain, in the order the standard runs it.
PROCUREMENT_SEQUENCE = (
    "define-procurement-requirements",
    "select-manufacturer",
    "evaluate-production-line",
    "approve-production-line",
    "agree-procurement-specification",
    "qualify-part-type",
    "manufacture-under-inline-control",
    "lot-acceptance-testing",
    "accept-and-deliver-lot",
)

# Owed by both categories before the routes diverge.
COMMON_OPENING_STEPS = (
    "define-procurement-requirements",
    "select-manufacturer",
)

# Owed only by a maker whose production line is not already approved.
LINE_APPROVAL_STEPS = (
    "evaluate-production-line",
    "approve-production-line",
)

# Where each category joins the sequence once the manufacturer is chosen.
_ENTRY_STEP = {
    CATEGORY_APPROVED_LINE: "agree-procurement-specification",
    CATEGORY_NO_APPROVED_LINE: "evaluate-production-line",
}


def _check_sequence_invariants():
    """Fail loudly at import if the tables disagree with the sequence."""
    for step in COMMON_OPENING_STEPS + LINE_APPROVAL_STEPS:
        if step not in PROCUREMENT_SEQUENCE:
            raise ValueError("table names a step outside the sequence: %s" % step)
    if len(set(PROCUREMENT_SEQUENCE)) != len(PROCUREMENT_SEQUENCE):
        raise ValueError("the procurement sequence repeats a step name")
    for category, step in _ENTRY_STEP.items():
        if category not in CATEGORIES:
            raise ValueError("entry table names an unknown category: %s" % category)
        if step not in PROCUREMENT_SEQUENCE:
            raise ValueError("entry step is outside the sequence: %s" % step)


_check_sequence_invariants()


def normalize_category(category):
    """Return the canonical manufacturer category name."""
    if not isinstance(category, str):
        raise ValueError("category must be a string, got %r" % (category,))
    key = category.strip().lower()
    if not key:
        raise ValueError("category must not be empty")
    if key in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[key]
    raise ValueError(
        "unknown manufacturer category %r; expected one of %s"
        % (category, ", ".join(CATEGORIES))
    )


def normalize_step(step):
    """Return the canonical activity name for a step of the sequence."""
    if not isinstance(step, str):
        raise ValueError("step must be a string, got %r" % (step,))
    key = step.strip().lower().replace("_", "-").replace(" ", "-")
    if not key:
        raise ValueError("step must not be empty")
    if key not in PROCUREMENT_SEQUENCE:
        raise ValueError("unknown procurement activity %r" % (step,))
    return key


def applicable_steps(category):
    """Return the ordered activities the given category has to run."""
    canonical = normalize_category(category)
    if canonical == CATEGORY_NO_APPROVED_LINE:
        return tuple(PROCUREMENT_SEQUENCE)
    return tuple(s for s in PROCUREMENT_SEQUENCE if s not in LINE_APPROVAL_STEPS)


def skipped_steps(category):
    """Return the activities the given category does not run."""
    applicable = set(applicable_steps(category))
    return tuple(s for s in PROCUREMENT_SEQUENCE if s not in applicable)


def entry_step(category):
    """Return the activity at which the category joins after manufacturer selection."""
    return _ENTRY_STEP[normalize_category(category)]


def step_position(step, category):
    """Return the zero-based position of a step inside the category's sequence."""
    canonical = normalize_step(step)
    applicable = applicable_steps(category)
    if canonical not in applicable:
        raise ValueError(
            "activity %s is not run by a %s manufacturer"
            % (canonical, normalize_category(category))
        )
    return applicable.index(canonical)


def prerequisites(step, category):
    """Return the activities that must be complete before the given step."""
    applicable = applicable_steps(category)
    index = step_position(step, category)
    return applicable[:index]


def validate_executed(executed):
    """Return the executed step list, canonicalised; raise on repeats or junk."""
    if not isinstance(executed, (list, tuple)):
        raise ValueError("executed steps must be a list or tuple")
    canonical = []
    for item in executed:
        name = normalize_step(item)
        if name in canonical:
            raise ValueError("activity %s is recorded more than once" % name)
        canonical.append(name)
    return canonical


def not_applicable_findings(category, executed):
    """Return executed activities the category is not required to run."""
    canonical = validate_executed(executed)
    applicable = set(applicable_steps(category))
    return [s for s in canonical if s not in applicable]


def ordering_findings(category, executed):
    """Return (step, prerequisite) pairs for activities run out of turn.

    The executed list is read as the order the activities actually ran in, so a
    pair is reported both when a prerequisite is missing altogether and when it
    is present but ran after the activity that depends on it.
    """
    canonical = validate_executed(executed)
    applicable = applicable_steps(category)
    rank = dict((name, i) for i, name in enumerate(canonical))
    findings = []
    for step in canonical:
        if step not in applicable:
            continue
        for earlier in prerequisites(step, category):
            if earlier not in rank or rank[earlier] > rank[step]:
                findings.append((step, earlier))
    return findings


def remaining_steps(category, executed):
    """Return the category's activities that are still outstanding, in order."""
    canonical = set(validate_executed(executed))
    return tuple(s for s in applicable_steps(category) if s not in canonical)


def next_step(category, executed):
    """Return the next activity due, or None when the sequence is complete."""
    outstanding = remaining_steps(category, executed)
    if not outstanding:
        return None
    return outstanding[0]


def completion_fraction(category, executed):
    """Return the fraction of the category's sequence already executed."""
    applicable = applicable_steps(category)
    done = [s for s in validate_executed(executed) if s in applicable]
    return len(done) / float(len(applicable))


def assess_procurement_sequence(spec):
    """Grade an executed hybrid procurement step list against its category.

    spec keys: category (required), executed_steps (required), optional
    target_step naming the milestone the buy is meant to have reached.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("category", "executed_steps"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    category = normalize_category(spec["category"])
    executed = validate_executed(spec["executed_steps"])
    applicable = applicable_steps(category)
    not_applicable = not_applicable_findings(category, executed)
    out_of_order = ordering_findings(category, executed)
    outstanding = remaining_steps(category, executed)
    findings = []
    for step in not_applicable:
        findings.append(
            "activity %s is not part of the %s route and was run anyway" % (step, category)
        )
    for step, earlier in out_of_order:
        findings.append("activity %s was run before its prerequisite %s" % (step, earlier))
    target = None
    if spec.get("target_step") is not None:
        target = normalize_step(spec["target_step"])
        if target not in applicable:
            raise ValueError(
                "target activity %s is not run by a %s manufacturer" % (target, category)
            )
        cut = applicable.index(target) + 1
        shortfall = [s for s in applicable[:cut] if s not in executed]
        for step in shortfall:
            findings.append(
                "activity %s is outstanding but the buy claims to have reached %s"
                % (step, target)
            )
    return {
        "category": category,
        "entry_step": entry_step(category),
        "applicable_steps": applicable,
        "skipped_steps": skipped_steps(category),
        "executed_steps": tuple(executed),
        "not_applicable": tuple(not_applicable),
        "out_of_order": tuple(out_of_order),
        "remaining_steps": outstanding,
        "next_step": next_step(category, executed),
        "target_step": target,
        "completion_fraction": completion_fraction(category, executed),
        "compliant": not findings,
        "findings": findings,
    }
