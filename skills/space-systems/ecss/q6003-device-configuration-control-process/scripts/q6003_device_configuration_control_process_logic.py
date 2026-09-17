"""Change control of device baselines, aligned with ECSS project management.

Anchor: ECSS-Q-ST-60-03C clause 8.3 (control of changes to a device baseline,
using the change categories and approval route of the ECSS project-management
change practice). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Establish the baseline the change is raised against: its stage and its
   version. A change against a baseline that was never established is a
   design decision, not a change, and is refused as such.
2. Categorise the change from its declared impacts. Any impact that reaches
   outside the supplier -- form, fit, function, an external interface,
   qualification evidence, the delivered documentation baseline, the
   criticality category, or a committed cost or schedule -- makes it a
   first-category change; otherwise it stays second category.
3. Route it: a first-category change goes to the customer change board, a
   second-category change stays with the supplier configuration board.
4. Demand the supporting evidence the category requires and report what is
   absent.
5. Check the process order: a change may not be implemented before it has
   been dispositioned, and implementation follows approval, not submission.
6. Compute the baseline version the approved change moves the device to.
"""

__all__ = [
    "BASELINE_STAGES",
    "CHANGE_CATEGORIES",
    "EXTERNAL_IMPACTS",
    "INTERNAL_IMPACTS",
    "ALL_IMPACTS",
    "DISPOSITIONS",
    "EVIDENCE_BY_CATEGORY",
    "APPROVAL_AUTHORITIES",
    "normalize_token",
    "normalize_stage",
    "parse_baseline_version",
    "format_baseline_version",
    "validate_baseline",
    "normalize_impacts",
    "categorize_change",
    "approval_authority",
    "required_evidence",
    "absent_evidence",
    "parse_iso_date",
    "sequence_findings",
    "implementation_allowed",
    "next_baseline_version",
    "assess_change",
]

BASELINE_STAGES = ("functional", "design", "product")

CHANGE_CATEGORIES = ("first-category", "second-category")

# Impacts that reach past the supplier and therefore pull a change into the
# first category.
EXTERNAL_IMPACTS = (
    "form-fit-or-function",
    "external-interface",
    "qualification-evidence",
    "delivered-documentation-baseline",
    "criticality-category",
    "committed-cost-or-schedule",
)

# Impacts that stay inside the supplier's own design and process control.
INTERNAL_IMPACTS = (
    "internal-implementation-detail",
    "supplier-internal-process",
    "non-delivered-analysis-file",
    "internal-naming-or-layout",
)

ALL_IMPACTS = EXTERNAL_IMPACTS + INTERNAL_IMPACTS

DISPOSITIONS = ("approved", "rejected", "deferred", "not-dispositioned")

EVIDENCE_BY_CATEGORY = {
    "first-category": (
        "impact-assessment",
        "re-verification-plan",
        "updated-item-data-list",
        "affected-deliverable-list",
        "customer-notification-record",
    ),
    "second-category": (
        "impact-assessment",
        "updated-item-data-list",
    ),
}

APPROVAL_AUTHORITIES = {
    "first-category": "customer-change-board",
    "second-category": "supplier-configuration-board",
}


def normalize_token(value, label):
    """Return a trimmed, lower-cased token, or raise for an unusable value."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = " ".join(value.split()).lower()
    if not key:
        raise ValueError("%s must not be empty" % label)
    return key


def normalize_stage(value):
    """Return the canonical baseline stage, or raise for an unknown one."""
    key = normalize_token(value, "baseline stage")
    if key not in BASELINE_STAGES:
        raise ValueError("unknown baseline stage '%s'" % key)
    return key


def parse_baseline_version(value):
    """Return (major, minor) from a 'M.N' baseline version string, or raise."""
    if not isinstance(value, str):
        raise ValueError("baseline version must be a string, got %r" % (value,))
    text = value.strip()
    parts = text.split(".")
    if len(parts) != 2:
        raise ValueError("baseline version '%s' is not in M.N form" % text)
    numbers = []
    for part in parts:
        if not part.isdigit():
            raise ValueError("baseline version '%s' has a non-numeric field" % text)
        numbers.append(int(part))
    if numbers[0] < 1:
        raise ValueError("a baseline major version starts at 1, got '%s'" % text)
    return (numbers[0], numbers[1])


def format_baseline_version(version):
    """Return the 'M.N' string for a (major, minor) baseline version."""
    if not isinstance(version, (tuple, list)) or len(version) != 2:
        raise ValueError("version must be a (major, minor) pair")
    major, minor = version
    for name, number in (("major", major), ("minor", minor)):
        if not isinstance(number, int) or isinstance(number, bool):
            raise ValueError("%s version must be an integer, got %r" % (name, number))
        if number < 0:
            raise ValueError("%s version must not be negative" % name)
    if major < 1:
        raise ValueError("a baseline major version starts at 1")
    return "%d.%d" % (major, minor)


def validate_baseline(baseline):
    """Return the normalized baseline, refusing one that was never established."""
    if not isinstance(baseline, dict):
        raise ValueError("baseline must be a mapping")
    for key in ("stage", "version", "established"):
        if key not in baseline:
            raise ValueError("baseline is missing '%s'" % key)
    if not isinstance(baseline["established"], bool):
        raise ValueError("baseline 'established' must be a boolean")
    if not baseline["established"]:
        raise ValueError(
            "a change cannot be raised against a baseline that was never established"
        )
    return {
        "stage": normalize_stage(baseline["stage"]),
        "version": parse_baseline_version(baseline["version"]),
        "established": True,
    }


def normalize_impacts(impacts):
    """Return the sorted, de-duplicated impact set, or raise on an unknown one."""
    if impacts is None:
        impacts = []
    if not isinstance(impacts, (list, tuple, set, frozenset)):
        raise ValueError("impacts must be a sequence")
    seen = []
    for item in impacts:
        key = normalize_token(item, "impact")
        if key not in ALL_IMPACTS:
            raise ValueError("unknown impact '%s'" % key)
        if key not in seen:
            seen.append(key)
    return sorted(seen)


def categorize_change(impacts):
    """Return (category, triggering-impacts) for the declared impact set."""
    declared = normalize_impacts(impacts)
    if not declared:
        raise ValueError("a change declares at least one impact")
    triggers = [item for item in declared if item in EXTERNAL_IMPACTS]
    category = "first-category" if triggers else "second-category"
    return (category, triggers)


def approval_authority(category):
    """Return the board that dispositions a change of this category."""
    key = normalize_token(category, "change category")
    if key not in APPROVAL_AUTHORITIES:
        raise ValueError("unknown change category '%s'" % key)
    return APPROVAL_AUTHORITIES[key]


def required_evidence(category, baseline_stage):
    """Return the supporting evidence this category demands at this stage."""
    key = normalize_token(category, "change category")
    if key not in EVIDENCE_BY_CATEGORY:
        raise ValueError("unknown change category '%s'" % key)
    stage = normalize_stage(baseline_stage)
    items = list(EVIDENCE_BY_CATEGORY[key])
    # Once hardware exists against the baseline, the change has to say what
    # happens to the units already built.
    if stage == "product" and "as-built-recall-assessment" not in items:
        items.append("as-built-recall-assessment")
    return tuple(sorted(items))


def absent_evidence(category, baseline_stage, declared):
    """Return the demanded evidence items the change package does not carry."""
    demanded = required_evidence(category, baseline_stage)
    if declared is None:
        declared = []
    if not isinstance(declared, (list, tuple, set, frozenset)):
        raise ValueError("declared evidence must be a sequence")
    present = []
    for item in declared:
        key = normalize_token(item, "evidence item")
        present.append(key)
    return [item for item in demanded if item not in present]


def parse_iso_date(value):
    """Return (year, month, day) from a YYYY-MM-DD string, or raise."""
    if not isinstance(value, str):
        raise ValueError("date must be a string, got %r" % (value,))
    text = value.strip()
    parts = text.split("-")
    if len(parts) != 3 or len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
        raise ValueError("date '%s' is not in YYYY-MM-DD form" % text)
    if not all(p.isdigit() for p in parts):
        raise ValueError("date '%s' has non-numeric fields" % text)
    year, month, day = (int(p) for p in parts)
    if not 1 <= month <= 12:
        raise ValueError("date '%s' has an out-of-range month" % text)
    if not 1 <= day <= 31:
        raise ValueError("date '%s' has an out-of-range day" % text)
    return (year, month, day)


def sequence_findings(record):
    """Return the process-order findings for the dates on a change record."""
    if not isinstance(record, dict):
        raise ValueError("change record must be a mapping")
    if "raised_on" not in record:
        raise ValueError("change record is missing 'raised_on'")
    raised = parse_iso_date(record["raised_on"])
    dispositioned = record.get("dispositioned_on")
    implemented = record.get("implemented_on")
    findings = []
    disposition_date = None
    if dispositioned is not None:
        disposition_date = parse_iso_date(dispositioned)
        if disposition_date < raised:
            findings.append("the change was dispositioned before it was raised")
    if implemented is not None:
        implementation_date = parse_iso_date(implemented)
        if implementation_date < raised:
            findings.append("the change was implemented before it was raised")
        if disposition_date is None:
            findings.append("the change was implemented with no disposition on record")
        elif implementation_date < disposition_date:
            findings.append("the change was implemented before it was dispositioned")
    return findings


def implementation_allowed(disposition, evidence_complete, order_clean):
    """Return True when the change may be implemented against the baseline."""
    key = normalize_token(disposition, "disposition")
    if key not in DISPOSITIONS:
        raise ValueError("unknown disposition '%s'" % key)
    if not isinstance(evidence_complete, bool):
        raise ValueError("evidence_complete must be a boolean")
    if not isinstance(order_clean, bool):
        raise ValueError("order_clean must be a boolean")
    return key == "approved" and evidence_complete and order_clean


def next_baseline_version(current, category):
    """Return the baseline version an approved change of this category yields."""
    if isinstance(current, str):
        major, minor = parse_baseline_version(current)
    elif isinstance(current, (tuple, list)) and len(current) == 2:
        format_baseline_version(current)
        major, minor = current
    else:
        raise ValueError("current baseline version must be 'M.N' or a pair")
    key = normalize_token(category, "change category")
    if key not in CHANGE_CATEGORIES:
        raise ValueError("unknown change category '%s'" % key)
    if key == "first-category":
        return (major + 1, 0)
    return (major, minor + 1)


def assess_change(spec):
    """Run the full clause 8.3 device change-control assessment.

    spec keys: baseline (stage, version, established), impacts, record
    (raised_on and optionally dispositioned_on / implemented_on), disposition,
    and optionally declared_evidence.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("baseline", "impacts", "record", "disposition"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    baseline = validate_baseline(spec["baseline"])
    category, triggers = categorize_change(spec["impacts"])
    authority = approval_authority(category)
    demanded = required_evidence(category, baseline["stage"])
    absent = absent_evidence(
        category, baseline["stage"], spec.get("declared_evidence")
    )
    order = sequence_findings(spec["record"])
    disposition = normalize_token(spec["disposition"], "disposition")
    if disposition not in DISPOSITIONS:
        raise ValueError("unknown disposition '%s'" % disposition)
    allowed = implementation_allowed(disposition, not absent, not order)
    resulting = (
        next_baseline_version(baseline["version"], category)
        if allowed
        else baseline["version"]
    )

    findings = list(order)
    for item in absent:
        findings.append("the change package is missing '%s'" % item)
    if disposition == "not-dispositioned":
        findings.append(
            "the change is still open at the %s and cannot be implemented" % authority
        )
    elif disposition == "deferred":
        findings.append("the change was deferred; the baseline is unchanged")
    elif disposition == "rejected":
        findings.append("the change was rejected; the baseline is unchanged")
    return {
        "baseline_stage": baseline["stage"],
        "baseline_version": format_baseline_version(baseline["version"]),
        "category": category,
        "triggering_impacts": triggers,
        "approval_authority": authority,
        "required_evidence": list(demanded),
        "absent_evidence": absent,
        "order_findings": order,
        "disposition": disposition,
        "implementation_allowed": allowed,
        "resulting_baseline_version": format_baseline_version(resulting),
        "findings": findings,
        "under_control": allowed and not findings,
    }
