"""Legacy lot acceptance test-list assessment for highest-assurance parts.

Anchor: ECSS-Q-ST-60-13C Table 8-11 (the lot acceptance test list applied to
active commercial parts procured under the highest assurance class, where
the part has legacy standing). Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the screened quantity the acceptance sample is drawn from. Lot
   acceptance follows screening, so the population here is what screening
   delivered, not the quantity originally procured.
2. Check the declared list covers every required acceptance subgroup once.
3. Resolve each subgroup's sample from the sampling plan the screened
   quantity falls into. The plan is a band table, not a percentage: a lot of
   sixty and a lot of a hundred and forty draw the same sample, which is why
   reading the sample off a proportion quietly under-draws a large lot and
   over-draws a small one. A list may declare a larger sample than its band
   asks for; it may never declare a smaller one.
4. Take each subgroup's failures against the accept number of its plan.
5. Allow at most one retest, on a doubled sample, and only for the subgroups
   the list permits one for. A second retest is refused rather than run: a
   subgroup that failed twice has answered the question.
6. Hold back what the destructive subgroups consume. A device that went
   through die shear or a sealed-package moisture reading is not deliverable
   afterwards, so the deliverable quantity is the screened quantity less
   every destructive sample actually drawn, retests included.
7. Accept the lot only when coverage is complete and every subgroup ended
   accepted; report the deliverable quantity either way.
"""

__all__ = [
    "REQUIRED_SUBGROUPS",
    "DESTRUCTIVE_SUBGROUPS",
    "RETESTABLE_SUBGROUPS",
    "SAMPLING_BANDS",
    "MAX_RETESTS",
    "validate_screened_quantity",
    "sampling_plan",
    "resolve_subgroup_sample",
    "acceptance_coverage",
    "subgroup_verdict",
    "destructive_consumption",
    "deliverable_quantity",
    "assess_legacy_acceptance_table",
]

# The acceptance subgroups an active part's lot acceptance list has to cover.
REQUIRED_SUBGROUPS = (
    "electrical-end-points",
    "seal-fine-and-gross",
    "solderability",
    "bond-strength",
    "die-shear",
    "internal-water-vapour",
    "steady-state-life-sample",
    "external-visual-sample",
    "destructive-physical-analysis",
)

# Subgroups whose sample cannot be delivered afterwards.
DESTRUCTIVE_SUBGROUPS = (
    "bond-strength",
    "die-shear",
    "internal-water-vapour",
    "steady-state-life-sample",
    "destructive-physical-analysis",
    "solderability",
)

# Subgroups the list allows a single doubled-sample retest for. The
# destructive analyses that read construction are not among them: a second
# sample answers the same question about a different device.
RETESTABLE_SUBGROUPS = (
    "electrical-end-points",
    "seal-fine-and-gross",
    "solderability",
    "external-visual-sample",
)

# Sampling plan bands: (lowest quantity, highest quantity or None, sample
# size, accept number). A band table, not a proportion.
SAMPLING_BANDS = (
    (1, 25, 3, 0),
    (26, 50, 5, 0),
    (51, 150, 8, 0),
    (151, 500, 13, 0),
    (501, 1200, 20, 1),
    (1201, None, 32, 1),
)

# A subgroup gets one retest on a doubled sample, never a second.
MAX_RETESTS = 1


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


def validate_screened_quantity(quantity):
    """Return the validated population the acceptance samples are drawn from."""
    value = _count("screened_quantity", quantity)
    if value < 1:
        raise ValueError("the screened quantity must be at least one part, got %d" % value)
    return value


def sampling_plan(quantity):
    """Return the (sample size, accept number) band a screened quantity falls in."""
    value = validate_screened_quantity(quantity)
    for low, high, sample, accept in SAMPLING_BANDS:
        if value >= low and (high is None or value <= high):
            return {"sample_size": sample, "accept_number": accept, "band": (low, high)}
    raise ValueError("no sampling band covers a screened quantity of %d" % value)


def resolve_subgroup_sample(entry, quantity):
    """Return the sample a subgroup draws, honouring a declared enlargement.

    entry keys: subgroup and an optional sample_size. A declared sample at or
    above the band's is taken as written; one below it is refused rather than
    raised silently, because a list that under-draws has to be corrected in
    the list.
    """
    if not isinstance(entry, dict):
        raise ValueError("an acceptance subgroup must be a mapping, got %r" % (entry,))
    subgroup = _name("subgroup", entry.get("subgroup"))
    plan = sampling_plan(quantity)
    sample = plan["sample_size"]
    if "sample_size" in entry:
        declared = _count("sample_size", entry["sample_size"])
        if declared < sample:
            raise ValueError(
                "subgroup '%s' declares a sample of %d against a plan sample of %d"
                % (subgroup, declared, sample)
            )
        sample = declared
    if sample > quantity:
        raise ValueError(
            "subgroup '%s' draws %d parts from a screened quantity of %d"
            % (subgroup, sample, quantity)
        )
    accept_number = plan["accept_number"]
    if "accept_number" in entry:
        declared_accept = _count("accept_number", entry["accept_number"])
        if declared_accept > plan["accept_number"]:
            raise ValueError(
                "subgroup '%s' declares an accept number of %d against a plan of %d"
                % (subgroup, declared_accept, plan["accept_number"])
            )
        accept_number = declared_accept
    return {
        "subgroup": subgroup,
        "sample_size": sample,
        "accept_number": accept_number,
        "plan_sample_size": plan["sample_size"],
        "plan_accept_number": plan["accept_number"],
        "band": plan["band"],
        "enlarged": sample > plan["sample_size"],
    }


def acceptance_coverage(entries):
    """Return the coverage record of a declared acceptance list."""
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("entries must be a non-empty sequence of acceptance subgroups")
    seen = []
    duplicates = []
    unknown = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("entries[%d] must be a mapping" % index)
        subgroup = entry.get("subgroup")
        if not isinstance(subgroup, str) or not subgroup.strip():
            raise ValueError("entries[%d] needs a non-empty 'subgroup'" % index)
        subgroup = subgroup.strip()
        if subgroup in seen and subgroup not in duplicates:
            duplicates.append(subgroup)
        if subgroup not in seen:
            seen.append(subgroup)
        if subgroup not in REQUIRED_SUBGROUPS and subgroup not in unknown:
            unknown.append(subgroup)
    missing = [s for s in REQUIRED_SUBGROUPS if s not in seen]
    return {
        "declared": seen,
        "missing": missing,
        "duplicated": duplicates,
        "unrecognized": unknown,
        "complete": not missing and not duplicates,
    }


def subgroup_verdict(entry, quantity):
    """Return the verdict record for one acceptance subgroup.

    entry keys: subgroup, failures and optional sample_size, accept_number,
    retest (a mapping with its own failures). A retest doubles the sample and
    is permitted once, for the subgroups the list allows it for.
    """
    resolved = resolve_subgroup_sample(entry, quantity)
    subgroup = resolved["subgroup"]
    if "failures" not in entry:
        raise ValueError("subgroup '%s' does not declare its failure count" % subgroup)
    failures = _count("failures", entry["failures"])
    if failures > resolved["sample_size"]:
        raise ValueError(
            "subgroup '%s' reports %d failures in a sample of %d"
            % (subgroup, failures, resolved["sample_size"])
        )
    accepted = failures <= resolved["accept_number"]
    drawn = resolved["sample_size"]
    retest = entry.get("retest")
    retest_record = None
    findings = []
    if retest is not None:
        if not isinstance(retest, dict):
            raise ValueError("a retest must be a mapping, got %r" % (retest,))
        if accepted:
            raise ValueError(
                "subgroup '%s' accepted on the first sample and has no retest to run"
                % subgroup
            )
        if subgroup not in RETESTABLE_SUBGROUPS:
            raise ValueError("subgroup '%s' takes no retest" % subgroup)
        attempts = _count("retest attempts", retest.get("attempt", 1))
        if attempts > MAX_RETESTS:
            raise ValueError(
                "subgroup '%s' may be retested %d time(s), not %d"
                % (subgroup, MAX_RETESTS, attempts)
            )
        retest_sample = 2 * resolved["sample_size"]
        if retest_sample > quantity:
            raise ValueError(
                "subgroup '%s' needs %d parts for a doubled sample, from %d"
                % (subgroup, retest_sample, quantity)
            )
        if "failures" not in retest:
            raise ValueError("the retest of '%s' does not declare its failures" % subgroup)
        retest_failures = _count("retest failures", retest["failures"])
        if retest_failures > retest_sample:
            raise ValueError(
                "the retest of '%s' reports %d failures in a sample of %d"
                % (subgroup, retest_failures, retest_sample)
            )
        retest_accepted = retest_failures <= resolved["accept_number"]
        retest_record = {
            "sample_size": retest_sample,
            "failures": retest_failures,
            "accepted": retest_accepted,
        }
        drawn = resolved["sample_size"] + retest_sample
        accepted = retest_accepted
        if not retest_accepted:
            findings.append(
                "subgroup '%s' failed its first sample and its doubled retest" % subgroup
            )
    elif not accepted:
        findings.append(
            "subgroup '%s' took %d failures against an accept number of %d"
            % (subgroup, failures, resolved["accept_number"])
        )
    record = dict(resolved)
    record.update(
        {
            "failures": failures,
            "retest": retest_record,
            "parts_drawn": drawn,
            "destructive": subgroup in DESTRUCTIVE_SUBGROUPS,
            "accepted": accepted,
            "findings": findings,
        }
    )
    return record


def destructive_consumption(verdicts):
    """Return the number of parts the destructive subgroups consumed."""
    if not isinstance(verdicts, (list, tuple)):
        raise ValueError("verdicts must be a sequence of subgroup records")
    total = 0
    for verdict in verdicts:
        if not isinstance(verdict, dict):
            raise ValueError("each verdict must be a mapping")
        if verdict.get("destructive"):
            total += _count("parts_drawn", verdict.get("parts_drawn", 0))
    return total


def deliverable_quantity(screened, consumed):
    """Return what is left to deliver once the destructive samples are held back."""
    available = validate_screened_quantity(screened)
    taken = _count("consumed", consumed)
    if taken > available:
        raise ValueError(
            "the destructive subgroups consumed %d parts from %d" % (taken, available)
        )
    return available - taken


def assess_legacy_acceptance_table(spec):
    """Run the full Table 8-11 legacy lot acceptance assessment.

    spec keys: screened_quantity and entries (the declared acceptance
    subgroups, each with a failure count and optional sample_size,
    accept_number and retest).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("screened_quantity", "entries"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    quantity = validate_screened_quantity(spec["screened_quantity"])
    coverage = acceptance_coverage(spec["entries"])
    verdicts = [subgroup_verdict(entry, quantity) for entry in spec["entries"]]
    consumed = destructive_consumption(verdicts)
    deliverable = deliverable_quantity(quantity, consumed)
    findings = []
    for subgroup in coverage["missing"]:
        findings.append("required acceptance subgroup '%s' is absent from the list" % subgroup)
    for subgroup in coverage["duplicated"]:
        findings.append("acceptance subgroup '%s' is declared more than once" % subgroup)
    for verdict in verdicts:
        findings.extend(verdict["findings"])
    accepted = not findings
    advisories = []
    for verdict in verdicts:
        if verdict["enlarged"]:
            advisories.append(
                "subgroup '%s' draws %d against a plan sample of %d"
                % (verdict["subgroup"], verdict["sample_size"], verdict["plan_sample_size"])
            )
        if verdict["retest"] is not None and verdict["accepted"]:
            advisories.append(
                "subgroup '%s' was accepted on its doubled retest" % verdict["subgroup"]
            )
    if deliverable == 0:
        advisories.append("the acceptance programme consumed the whole screened quantity")
    return {
        "screened_quantity": quantity,
        "coverage": coverage,
        "verdicts": verdicts,
        "failing_subgroups": [v["subgroup"] for v in verdicts if not v["accepted"]],
        "parts_consumed": consumed,
        "deliverable_quantity": deliverable,
        "accepted": accepted,
        "disposition": "accept-lot" if accepted else "reject-lot",
        "findings": findings,
        "advisories": advisories,
    }
