"""Legacy evaluation test-list assessment for highest-assurance active parts.

Anchor: ECSS-Q-ST-60-13C Table 8-9 (the evaluation test list applied to
active commercial parts procured under the highest assurance class, where
the part has legacy standing: evaluation data already exists from an earlier
procurement of the same part). Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the evaluation context: the assurance class the part is being
   bought to, the manufacturing site and technology it now comes from, and
   the number of devices the evaluation lot can give up. Evaluation consumes
   devices, so the allocation has to fit the lot.
2. Check the declared evaluation list covers every required group for an
   active part, and that no group appears twice.
3. Decide, group by group, whether legacy evidence may be credited. Credit
   is allowed only when the evidence names the same manufacturer, the same
   manufacturing site and the same technology, was raised against an
   assurance class at least as demanding as the one now being bought to, and
   is no older than the validity window. Some groups are never creditable:
   they read the part in front of you, not the part that was evaluated.
4. Reduce the declared list to the residual programme -- the groups that
   still have to be run -- and allocate devices to them, refusing an
   allocation that exceeds the devices the evaluation lot can give up.
5. Judge each residual group on failures against its accept number.
   Evaluation is an accept-on-zero exercise for the groups that carry no
   accept number, and a group that took a failure sends the part type back
   to a repeated evaluation rather than reducing its sample.
6. Release the part type for use only when coverage is complete, every
   credit is sound, the allocation fits and no residual group failed.
"""

__all__ = [
    "REQUIRED_EVALUATION_GROUPS",
    "NEVER_CREDITABLE_GROUPS",
    "ASSURANCE_CLASSES",
    "HIGHEST_ASSURANCE_CLASS",
    "DEFAULT_VALIDITY_MONTHS",
    "validate_context",
    "validate_evidence",
    "credit_decision",
    "evaluation_coverage",
    "residual_programme",
    "allocate_devices",
    "group_verdict",
    "assess_legacy_evaluation_table",
]

# The evaluation groups an active part's legacy evaluation list has to cover
# before any credit or verdict means anything.
REQUIRED_EVALUATION_GROUPS = (
    "construction-analysis",
    "electrical-characterization",
    "temperature-extreme-electrical",
    "extended-burn-in",
    "operating-life-evaluation",
    "mechanical-sequence",
    "moisture-and-seal",
    "solderability-and-terminals",
    "radiation-capability",
    "destructive-physical-analysis",
)

# Groups that read the material in front of you rather than the design.
# Legacy evidence never stands in for these, however recent it is.
NEVER_CREDITABLE_GROUPS = (
    "construction-analysis",
    "destructive-physical-analysis",
)

# Assurance classes, most demanding first. Evidence raised against a less
# demanding class cannot be credited upwards.
ASSURANCE_CLASSES = (1, 2, 3)
HIGHEST_ASSURANCE_CLASS = 1

# How old legacy evidence may be before it stops standing for the part now
# being procured.
DEFAULT_VALIDITY_MONTHS = 60


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _name(label, value):
    """Return value as a stripped non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty name, got %r" % (label, value))
    return value.strip()


def _assurance_class(label, value):
    """Return value as a known assurance class."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer assurance class, got %r" % (label, value))
    if value not in ASSURANCE_CLASSES:
        raise ValueError(
            "%s must be one of %r, got %d" % (label, ASSURANCE_CLASSES, value)
        )
    return value


def validate_context(context):
    """Return the validated procurement context the evaluation is run against.

    context keys: manufacturer, site, technology, assurance_class,
    devices_available and an optional validity_months.
    """
    if not isinstance(context, dict):
        raise ValueError("context must be a mapping, got %r" % (context,))
    for key in ("manufacturer", "site", "technology", "assurance_class", "devices_available"):
        if key not in context:
            raise ValueError("context missing required key '%s'" % key)
    devices = _count("devices_available", context["devices_available"])
    if devices < 1:
        raise ValueError("an evaluation needs at least one device, got %d" % devices)
    validity = context.get("validity_months", DEFAULT_VALIDITY_MONTHS)
    validity = _count("validity_months", validity)
    if validity < 1:
        raise ValueError("the validity window must be at least one month")
    return {
        "manufacturer": _name("manufacturer", context["manufacturer"]),
        "site": _name("site", context["site"]),
        "technology": _name("technology", context["technology"]),
        "assurance_class": _assurance_class("assurance_class", context["assurance_class"]),
        "devices_available": devices,
        "validity_months": validity,
    }


def validate_evidence(evidence):
    """Return the validated record of one piece of legacy evaluation evidence.

    evidence keys: group, manufacturer, site, technology, assurance_class,
    age_months, report.
    """
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a mapping, got %r" % (evidence,))
    required = (
        "group",
        "manufacturer",
        "site",
        "technology",
        "assurance_class",
        "age_months",
        "report",
    )
    for key in required:
        if key not in evidence:
            raise ValueError("evidence missing required key '%s'" % key)
    return {
        "group": _name("evidence group", evidence["group"]),
        "manufacturer": _name("evidence manufacturer", evidence["manufacturer"]),
        "site": _name("evidence site", evidence["site"]),
        "technology": _name("evidence technology", evidence["technology"]),
        "assurance_class": _assurance_class(
            "evidence assurance_class", evidence["assurance_class"]
        ),
        "age_months": _count("evidence age_months", evidence["age_months"]),
        "report": _name("evidence report", evidence["report"]),
    }


def credit_decision(evidence, context):
    """Return whether one piece of legacy evidence may be credited, and why not.

    A credit is sound only when the evidence describes the same part from the
    same source, was raised to an assurance class at least as demanding as
    the one now being bought to, is inside the validity window, and is for a
    group that legacy evidence is allowed to stand for at all.
    """
    record = validate_evidence(evidence)
    ctx = validate_context(context)
    reasons = []
    if record["group"] in NEVER_CREDITABLE_GROUPS:
        reasons.append(
            "group '%s' is read on the delivered material and takes no legacy credit"
            % record["group"]
        )
    if record["manufacturer"] != ctx["manufacturer"]:
        reasons.append(
            "evidence names manufacturer '%s' against a procurement from '%s'"
            % (record["manufacturer"], ctx["manufacturer"])
        )
    if record["site"] != ctx["site"]:
        reasons.append(
            "evidence names site '%s' against a procurement from '%s'"
            % (record["site"], ctx["site"])
        )
    if record["technology"] != ctx["technology"]:
        reasons.append(
            "evidence names technology '%s' against a procurement of '%s'"
            % (record["technology"], ctx["technology"])
        )
    if record["assurance_class"] > ctx["assurance_class"]:
        reasons.append(
            "evidence was raised to assurance class %d and cannot be credited to class %d"
            % (record["assurance_class"], ctx["assurance_class"])
        )
    if record["age_months"] > ctx["validity_months"]:
        reasons.append(
            "evidence is %d months old against a %d month validity window"
            % (record["age_months"], ctx["validity_months"])
        )
    return {
        "group": record["group"],
        "report": record["report"],
        "credited": not reasons,
        "reasons": reasons,
    }


def evaluation_coverage(entries):
    """Return the coverage record of a declared evaluation list."""
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("entries must be a non-empty sequence of evaluation groups")
    seen = []
    duplicates = []
    unknown = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("entries[%d] must be a mapping" % index)
        group = entry.get("group")
        if not isinstance(group, str) or not group.strip():
            raise ValueError("entries[%d] needs a non-empty 'group'" % index)
        group = group.strip()
        if group in seen and group not in duplicates:
            duplicates.append(group)
        if group not in seen:
            seen.append(group)
        if group not in REQUIRED_EVALUATION_GROUPS and group not in unknown:
            unknown.append(group)
    missing = [g for g in REQUIRED_EVALUATION_GROUPS if g not in seen]
    return {
        "declared": seen,
        "missing": missing,
        "duplicated": duplicates,
        "unrecognized": unknown,
        "complete": not missing and not duplicates,
    }


def residual_programme(entries, evidence_records, context):
    """Return the groups that still have to be run once credit is applied.

    entries are the declared evaluation groups; evidence_records are the
    legacy reports offered against them.
    """
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("entries must be a non-empty sequence of evaluation groups")
    if evidence_records is None:
        evidence_records = []
    if not isinstance(evidence_records, (list, tuple)):
        raise ValueError("evidence must be a sequence of records")
    ctx = validate_context(context)
    decisions = [credit_decision(item, ctx) for item in evidence_records]
    credited = []
    refused = []
    for decision in decisions:
        if decision["credited"]:
            if decision["group"] not in credited:
                credited.append(decision["group"])
        elif decision["group"] not in refused:
            refused.append(decision["group"])
    declared = []
    for entry in entries:
        group = _name("evaluation group", entry.get("group"))
        if group not in declared:
            declared.append(group)
    offered = [d["group"] for d in decisions]
    orphan = [g for g in offered if g not in declared]
    residual = [g for g in declared if g not in credited]
    return {
        "declared": declared,
        "credited": credited,
        "credit_refused": [g for g in refused if g not in credited],
        "orphan_evidence": orphan,
        "residual": residual,
        "decisions": decisions,
    }


def allocate_devices(entries, residual, devices_available):
    """Return the device allocation across the residual evaluation groups.

    Every residual group declares the devices it consumes; the allocation is
    refused when the groups together ask for more than the evaluation lot can
    give up.
    """
    available = _count("devices_available", devices_available)
    if available < 1:
        raise ValueError("an evaluation needs at least one device")
    by_group = {}
    for entry in entries:
        group = _name("evaluation group", entry.get("group"))
        if "devices" not in entry:
            raise ValueError("group '%s' does not declare its device count" % group)
        devices = _count("devices", entry["devices"])
        if group in residual and devices < 1:
            raise ValueError(
                "residual group '%s' has to consume at least one device" % group
            )
        by_group[group] = devices
    allocation = {group: by_group[group] for group in residual}
    consumed = sum(allocation.values())
    credited_saving = sum(
        by_group[g] for g in by_group if g not in residual
    )
    if consumed > available:
        raise ValueError(
            "the residual programme asks for %d devices from a lot of %d"
            % (consumed, available)
        )
    return {
        "allocation": allocation,
        "devices_consumed": consumed,
        "devices_remaining": available - consumed,
        "devices_saved_by_credit": credited_saving,
    }


def group_verdict(entry):
    """Return the verdict record for one residual evaluation group.

    entry keys: group, devices, failures and an optional accept_number
    (absent means accept on zero failures).
    """
    if not isinstance(entry, dict):
        raise ValueError("an evaluation group must be a mapping, got %r" % (entry,))
    for key in ("group", "devices", "failures"):
        if key not in entry:
            raise ValueError("evaluation group missing required key '%s'" % key)
    group = _name("evaluation group", entry["group"])
    devices = _count("devices", entry["devices"])
    failures = _count("failures", entry["failures"])
    accept_number = _count("accept_number", entry.get("accept_number", 0))
    if devices < 1:
        raise ValueError("group '%s' has to consume at least one device" % group)
    if failures > devices:
        raise ValueError(
            "group '%s' reports %d failures over %d devices" % (group, failures, devices)
        )
    if accept_number > devices:
        raise ValueError(
            "group '%s' has an accept number of %d over %d devices"
            % (group, accept_number, devices)
        )
    accepted = failures <= accept_number
    findings = []
    if not accepted:
        findings.append(
            "evaluation group '%s' took %d failures against an accept number of %d"
            % (group, failures, accept_number)
        )
    return {
        "group": group,
        "devices": devices,
        "failures": failures,
        "accept_number": accept_number,
        "accepted": accepted,
        "accept_on_zero": accept_number == 0,
        "findings": findings,
    }


def assess_legacy_evaluation_table(spec):
    """Run the full Table 8-9 legacy evaluation assessment.

    spec keys: context, entries (the declared evaluation groups, each with a
    device count, a failure count and an optional accept_number) and an
    optional evidence list of legacy reports.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("context", "entries"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    ctx = validate_context(spec["context"])
    coverage = evaluation_coverage(spec["entries"])
    programme = residual_programme(spec["entries"], spec.get("evidence"), ctx)
    allocation = allocate_devices(
        spec["entries"], programme["residual"], ctx["devices_available"]
    )
    verdicts = [
        group_verdict(entry)
        for entry in spec["entries"]
        if _name("evaluation group", entry.get("group")) in programme["residual"]
    ]
    findings = []
    for group in coverage["missing"]:
        findings.append("required evaluation group '%s' is absent from the list" % group)
    for group in coverage["duplicated"]:
        findings.append("evaluation group '%s' is declared more than once" % group)
    for decision in programme["decisions"]:
        for reason in decision["reasons"]:
            findings.append("credit refused for '%s': %s" % (decision["group"], reason))
    for group in programme["orphan_evidence"]:
        findings.append(
            "legacy evidence offered for '%s', which the list does not declare" % group
        )
    for verdict in verdicts:
        findings.extend(verdict["findings"])
    released = not findings
    advisories = []
    if ctx["assurance_class"] != HIGHEST_ASSURANCE_CLASS:
        advisories.append(
            "this list is written for assurance class %d; it is being applied to class %d"
            % (HIGHEST_ASSURANCE_CLASS, ctx["assurance_class"])
        )
    if allocation["devices_remaining"] == 0:
        advisories.append("the residual programme consumes the whole evaluation lot")
    return {
        "context": ctx,
        "coverage": coverage,
        "credited_groups": programme["credited"],
        "residual_groups": programme["residual"],
        "allocation": allocation,
        "verdicts": verdicts,
        "failing_groups": [v["group"] for v in verdicts if not v["accepted"]],
        "released": released,
        "disposition": "release" if released else "repeat-evaluation",
        "findings": findings,
        "advisories": advisories,
    }
