"""Per-batch acceptance scheme for an approved hybrid production line.

Anchor: ECSS-Q-ST-60-05C clause 12.2.1 (the acceptance option built around
testing samples drawn from each individual production batch). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the production lot and the test groups it has to feed. Every
   group names its own sample size, its own acceptance number and whether it
   consumes what it measures.
2. Allocate units from the lot to the groups. Samples from different groups
   do not share units, so the commitment is the sum, and a lot that cannot
   cover the sum cannot be accepted under this option at all.
3. Separate the units destroyed from the units merely committed. Only the
   destroyed ones come off the deliverable quantity; a lot sized to the order
   ships short by exactly the destructive sample.
4. Disposition each group against its own acceptance number, then the lot
   against its groups: one failing group refuses the lot, and the report
   names which.
5. Track the line across lots. A rejected lot may be reworked and resubmitted
   a limited number of times, and a run of consecutive rejected lots
   suspends the entitlement to operate this option rather than merely
   refusing another batch.
"""

__all__ = [
    "DEFAULT_TEST_GROUPS",
    "CONSECUTIVE_REJECT_LIMIT",
    "MAX_RESUBMISSIONS",
    "validate_lot_size",
    "validate_test_groups",
    "allocate_lot_samples",
    "units_destroyed",
    "deliverable_after_acceptance",
    "lot_sampling_fraction",
    "group_disposition",
    "lot_disposition",
    "resubmission_allowed",
    "campaign_status",
    "plan_production_lot_control",
]

# Acceptance groups a production lot feeds. A project substitutes its own set
# through the `groups` argument; the allocation, the destructive accounting
# and the disposition are the part that does not change.
DEFAULT_TEST_GROUPS = (
    {"name": "electrical-acceptance", "sample_size": 22, "acceptance_number": 0, "destructive": False},
    {"name": "environmental-acceptance", "sample_size": 8, "acceptance_number": 0, "destructive": False},
    {"name": "destructive-physical-analysis", "sample_size": 2, "acceptance_number": 0, "destructive": True},
)

# Consecutive rejected lots at which the line loses this option.
CONSECUTIVE_REJECT_LIMIT = 2

# Times one lot may come back after rework before it is scrapped.
MAX_RESUBMISSIONS = 1


def _require_positive_int(value, label):
    """Return value as a positive int, raising on anything that is not one."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _require_non_negative_int(value, label):
    """Return value as a non-negative int, raising on anything that is not one."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def validate_lot_size(lot_size):
    """Return the production lot size as a positive integer count of units."""
    return _require_positive_int(lot_size, "lot_size")


def validate_test_groups(groups=DEFAULT_TEST_GROUPS):
    """Return the acceptance groups normalised, raising on an unusable set.

    Group names are unique because the allocation and the results are matched
    by name; a duplicate name silently takes one group's result for another's.
    """
    if isinstance(groups, dict) or not isinstance(groups, (list, tuple)):
        raise ValueError("groups must be a sequence of group records")
    if not groups:
        raise ValueError("no acceptance test groups were given")
    seen = set()
    normalised = []
    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            raise ValueError("groups[%d] must be a mapping" % index)
        name = group.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("groups[%d] needs a non-empty 'name'" % index)
        key = name.strip().lower().replace("_", "-").replace(" ", "-")
        if key in seen:
            raise ValueError("duplicate acceptance group name %r" % key)
        seen.add(key)
        sample_size = _require_positive_int(group.get("sample_size"), "groups[%d] sample_size" % index)
        acceptance_number = _require_non_negative_int(
            group.get("acceptance_number", 0), "groups[%d] acceptance_number" % index
        )
        if acceptance_number >= sample_size:
            raise ValueError(
                "groups[%d] accepts %d nonconforming units out of a sample of %d"
                % (index, acceptance_number, sample_size)
            )
        destructive = group.get("destructive", False)
        if not isinstance(destructive, bool):
            raise ValueError("groups[%d] destructive must be a boolean" % index)
        normalised.append(
            {
                "name": key,
                "sample_size": sample_size,
                "acceptance_number": acceptance_number,
                "destructive": destructive,
            }
        )
    return normalised


def allocate_lot_samples(lot_size, groups=DEFAULT_TEST_GROUPS):
    """Return the per-group allocation of units out of one production lot.

    Raises when the lot cannot cover the total commitment: under this option
    the lot feeds its own acceptance tests, so an undersized lot has no plan.
    """
    size = validate_lot_size(lot_size)
    normalised = validate_test_groups(groups)
    committed = sum(group["sample_size"] for group in normalised)
    if committed > size:
        raise ValueError(
            "acceptance groups commit %d units from a lot of %d" % (committed, size)
        )
    destroyed = sum(g["sample_size"] for g in normalised if g["destructive"])
    return {
        "lot_size": size,
        "groups": normalised,
        "units_committed": committed,
        "units_destroyed": destroyed,
        "units_returned_to_stock": committed - destroyed,
        "deliverable_after_acceptance": size - destroyed,
    }


def units_destroyed(lot_size, groups=DEFAULT_TEST_GROUPS):
    """Return the units this lot loses to destructive acceptance groups."""
    return allocate_lot_samples(lot_size, groups)["units_destroyed"]


def deliverable_after_acceptance(lot_size, groups=DEFAULT_TEST_GROUPS):
    """Return the units still shippable once the destructive groups are run."""
    return allocate_lot_samples(lot_size, groups)["deliverable_after_acceptance"]


def lot_sampling_fraction(lot_size, groups=DEFAULT_TEST_GROUPS):
    """Return the committed sample as a fraction of the production lot."""
    allocation = allocate_lot_samples(lot_size, groups)
    return allocation["units_committed"] / float(allocation["lot_size"])


def group_disposition(group, nonconforming_found):
    """Return accept or reject for one acceptance group's result."""
    normalised = validate_test_groups([group])[0]
    found = _require_non_negative_int(nonconforming_found, "nonconforming_found")
    if found > normalised["sample_size"]:
        raise ValueError(
            "group %s sampled %d units and cannot yield %d nonconforming"
            % (normalised["name"], normalised["sample_size"], found)
        )
    accepted = found <= normalised["acceptance_number"]
    return {
        "group": normalised["name"],
        "sample_size": normalised["sample_size"],
        "acceptance_number": normalised["acceptance_number"],
        "nonconforming_found": found,
        "accepted": accepted,
        "disposition": "accept" if accepted else "reject",
    }


def lot_disposition(lot_size, results, groups=DEFAULT_TEST_GROUPS):
    """Return the lot's disposition from its per-group results.

    Every group has to report. A group with no result is unverified, and
    unverified is not accepted.
    """
    allocation = allocate_lot_samples(lot_size, groups)
    if not isinstance(results, dict):
        raise ValueError("results must be a mapping of group name to nonconforming count")
    normalised_results = {}
    for name, found in results.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("result keys must be non-empty group names")
        normalised_results[name.strip().lower().replace("_", "-").replace(" ", "-")] = found
    per_group = []
    failing = []
    unreported = []
    for group in allocation["groups"]:
        if group["name"] not in normalised_results:
            unreported.append(group["name"])
            continue
        outcome = group_disposition(group, normalised_results[group["name"]])
        per_group.append(outcome)
        if not outcome["accepted"]:
            failing.append(group["name"])
    extra = [name for name in normalised_results if name not in {g["name"] for g in allocation["groups"]}]
    if extra:
        raise ValueError("results name groups that are not in the plan: %s" % ", ".join(sorted(extra)))
    accepted = not failing and not unreported
    return {
        "lot_size": allocation["lot_size"],
        "per_group": per_group,
        "failing_groups": failing,
        "unreported_groups": unreported,
        "accepted": accepted,
        "disposition": "accept" if accepted else "reject",
        "deliverable_after_acceptance": allocation["deliverable_after_acceptance"] if accepted else 0,
    }


def resubmission_allowed(prior_submissions, limit=MAX_RESUBMISSIONS):
    """Return whether a rejected lot may come back after rework."""
    prior = _require_non_negative_int(prior_submissions, "prior_submissions")
    return prior <= _require_non_negative_int(limit, "limit")


def campaign_status(dispositions, limit=CONSECUTIVE_REJECT_LIMIT):
    """Return the line's standing across a run of lots, oldest first.

    A run of consecutive rejected lots suspends the entitlement to operate
    this option; the line goes back for review rather than simply offering
    another batch.
    """
    if isinstance(dispositions, str) or not isinstance(dispositions, (list, tuple)):
        raise ValueError("dispositions must be a sequence of 'accept'/'reject' values")
    reject_limit = _require_positive_int(limit, "limit")
    trailing = 0
    rejects = 0
    for index, value in enumerate(dispositions):
        if value not in ("accept", "reject"):
            raise ValueError("dispositions[%d] must be 'accept' or 'reject', got %r" % (index, value))
        if value == "reject":
            rejects += 1
            trailing += 1
        else:
            trailing = 0
    suspended = trailing >= reject_limit
    return {
        "lots_reviewed": len(dispositions),
        "lots_rejected": rejects,
        "consecutive_rejects": trailing,
        "entitlement": "suspended" if suspended else "retained",
        "may_submit_next_lot": not suspended,
    }


def plan_production_lot_control(spec):
    """Run the full clause 12.2.1 per-lot acceptance plan and disposition.

    spec keys: lot_size, optional groups, optional deliverable_quantity,
    optional results (group name to nonconforming count), optional
    lot_history (previous dispositions, oldest first), optional
    prior_submissions.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "lot_size" not in spec:
        raise ValueError("spec missing required key 'lot_size'")
    groups = spec.get("groups", DEFAULT_TEST_GROUPS)
    allocation = allocate_lot_samples(spec["lot_size"], groups)
    findings = []

    shortfall = 0
    if spec.get("deliverable_quantity") is not None:
        wanted = _require_positive_int(spec["deliverable_quantity"], "deliverable_quantity")
        shortfall = max(0, wanted - allocation["deliverable_after_acceptance"])
        if shortfall:
            findings.append(
                "destructive groups leave %d units short of the deliverable quantity"
                % shortfall
            )

    disposition = None
    if spec.get("results") is not None:
        outcome = lot_disposition(spec["lot_size"], spec["results"], groups)
        disposition = outcome["disposition"]
        for name in outcome["failing_groups"]:
            findings.append("acceptance group %s rejected the lot" % name)
        for name in outcome["unreported_groups"]:
            findings.append("acceptance group %s reported no result" % name)

    history = campaign_status(spec.get("lot_history", []))
    if history["entitlement"] == "suspended":
        findings.append(
            "%d consecutive rejected lots; the per-lot option is suspended pending review"
            % history["consecutive_rejects"]
        )

    may_resubmit = resubmission_allowed(spec.get("prior_submissions", 0))
    if disposition == "reject" and not may_resubmit:
        findings.append("this lot has used its resubmissions and cannot come back after rework")

    return {
        "lot_size": allocation["lot_size"],
        "units_committed": allocation["units_committed"],
        "units_destroyed": allocation["units_destroyed"],
        "units_returned_to_stock": allocation["units_returned_to_stock"],
        "deliverable_after_acceptance": allocation["deliverable_after_acceptance"],
        "sampling_fraction": allocation["units_committed"] / float(allocation["lot_size"]),
        "deliverable_shortfall": shortfall,
        "lot_disposition": disposition,
        "campaign": history,
        "may_resubmit": may_resubmit,
        "plan_is_workable": not findings,
        "findings": findings,
    }
