"""Destructive sampling arrangement for a finished hybrid batch.

Anchor: ECSS-Q-ST-60-05C clause 12.1 (the purpose and the overall arrangement
of the destructive sampling performed on each finished batch of hybrids).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the lot and the sampling groups it will be put through. A group
   names how its sample size is arrived at -- a fixed number, or a
   proportion of the lot with a floor and a ceiling -- whether it consumes
   the units it takes, and how many failures it tolerates.
2. Size every group against the lot. Proportional sizes are rounded up using
   integer arithmetic, because a percentage taken in floating point lands
   just above a whole number often enough to add a unit that was never
   required.
3. Add up what the destructive groups consume, subtract it from the lot and
   compare what is left with the quantity the contract expects. A sampling
   arrangement that cannot leave the deliverables behind is not a plan.
4. Where results have been entered, grade each group: a sample smaller than
   the one required does not speak for the lot, and failures beyond the
   accept number reject it.
5. Return the arrangement, the destructive burden as a fraction of the lot,
   and one disposition for the batch.

The burden fraction is a quotient of counts that lands exactly on simple
values, so callers comparing it should do so with a tolerance.
"""

__all__ = [
    "RATIO_TOLERANCE",
    "SAMPLE_RULE_KINDS",
    "validate_rule",
    "required_sample_size",
    "validate_group",
    "validate_lot",
    "size_groups",
    "destructive_demand",
    "deliverable_after_sampling",
    "destructive_burden_ratio",
    "grade_group",
    "assess_lot_acceptance_arrangement",
]

# Sampling fractions land exactly on values like one tenth, so equality
# against a burden target is a tolerance comparison, never a strict one.
RATIO_TOLERANCE = 1e-9

SAMPLE_RULE_KINDS = ("fixed", "proportional")


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


def _require_identity(value, label):
    """Return a stripped, non-empty identity string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def validate_rule(rule, label="sample_rule"):
    """Return the normalised sample-size rule for one group.

    A fixed rule names the number of units outright. A proportional rule
    names a share of the lot in parts per thousand, with a floor and a
    ceiling, so that small lots are not under-sampled and large ones are not
    consumed wholesale.
    """
    if not isinstance(rule, dict):
        raise ValueError("%s must be a mapping" % label)
    if "kind" not in rule:
        raise ValueError("%s missing 'kind'" % label)
    kind = _require_identity(rule["kind"], "%s['kind']" % label).lower()
    if kind not in SAMPLE_RULE_KINDS:
        raise ValueError(
            "%s['kind'] must be one of %s, got %r" % (label, ", ".join(SAMPLE_RULE_KINDS), kind)
        )
    if kind == "fixed":
        return {"kind": "fixed", "units": _require_positive_int(rule.get("units"), "%s['units']" % label)}
    permille = _require_positive_int(rule.get("permille"), "%s['permille']" % label)
    if permille > 1000:
        raise ValueError("%s['permille'] must not exceed 1000, got %d" % (label, permille))
    minimum = _require_positive_int(rule.get("minimum", 1), "%s['minimum']" % label)
    maximum = _require_positive_int(rule.get("maximum", minimum), "%s['maximum']" % label)
    if maximum < minimum:
        raise ValueError("%s['maximum'] must not be below its minimum" % label)
    return {
        "kind": "proportional",
        "permille": permille,
        "minimum": minimum,
        "maximum": maximum,
    }


def required_sample_size(rule, lot_size):
    """Return the units this rule demands from a lot of this size.

    The proportional case rounds up with integer arithmetic. Taking the same
    share as a float and rounding the product up adds a unit whenever the
    product lands a hair above a whole number, which it does for ordinary
    shares of ordinary lot sizes.
    """
    normalised = validate_rule(rule)
    units = _require_positive_int(lot_size, "lot_size")
    if normalised["kind"] == "fixed":
        return normalised["units"]
    exact = -((-normalised["permille"] * units) // 1000)
    if exact < normalised["minimum"]:
        return normalised["minimum"]
    if exact > normalised["maximum"]:
        return normalised["maximum"]
    return exact


def validate_group(group, index=0):
    """Return the normalised record of one sampling group."""
    label = "groups[%d]" % index
    if not isinstance(group, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("group_id", "sample_rule"):
        if key not in group:
            raise ValueError("%s missing required key '%s'" % (label, key))
    destructive = group.get("destructive", True)
    if not isinstance(destructive, bool):
        raise ValueError("%s['destructive'] must be a boolean" % label)
    drawn = group.get("units_drawn")
    if drawn is not None:
        drawn = _require_non_negative_int(drawn, "%s['units_drawn']" % label)
    failed = group.get("units_failed")
    if failed is not None:
        failed = _require_non_negative_int(failed, "%s['units_failed']" % label)
    if failed is not None and drawn is not None and failed > drawn:
        raise ValueError("%s reports more failures than units drawn" % label)
    return {
        "group_id": _require_identity(group["group_id"], "%s['group_id']" % label),
        "sample_rule": validate_rule(group["sample_rule"], "%s['sample_rule']" % label),
        "destructive": destructive,
        "accept_number": _require_non_negative_int(
            group.get("accept_number", 0), "%s['accept_number']" % label
        ),
        "units_drawn": drawn,
        "units_failed": failed,
    }


def validate_lot(spec):
    """Return the normalised lot header: batch size and contract quantity."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_size", "groups"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    groups = spec["groups"]
    if isinstance(groups, dict) or not isinstance(groups, (list, tuple)):
        raise ValueError("spec['groups'] must be a sequence of group records")
    if not groups:
        raise ValueError("a lot acceptance arrangement needs at least one group")
    delivery = spec.get("contract_delivery_quantity", 0)
    return {
        "lot_size": _require_positive_int(spec["lot_size"], "lot_size"),
        "contract_delivery_quantity": _require_non_negative_int(
            delivery, "contract_delivery_quantity"
        ),
    }


def size_groups(spec):
    """Return each group with the sample size the lot demands of it."""
    header = validate_lot(spec)
    sized = []
    seen = set()
    for index, group in enumerate(spec["groups"]):
        record = validate_group(group, index)
        if record["group_id"] in seen:
            raise ValueError("duplicate group id %r in the arrangement" % record["group_id"])
        seen.add(record["group_id"])
        record["required_units"] = required_sample_size(
            record["sample_rule"], header["lot_size"]
        )
        sized.append(record)
    return sized


def destructive_demand(spec):
    """Return the units the destructive groups consume from the lot."""
    return sum(g["required_units"] for g in size_groups(spec) if g["destructive"])


def deliverable_after_sampling(spec):
    """Return what is left of the lot once the destructive groups have taken theirs."""
    header = validate_lot(spec)
    return header["lot_size"] - destructive_demand(spec)


def destructive_burden_ratio(spec):
    """Return the destructive demand as a fraction of the whole lot."""
    header = validate_lot(spec)
    return destructive_demand(spec) / float(header["lot_size"])


def grade_group(group):
    """Grade one sized group against its sample requirement and accept number."""
    if "required_units" not in group:
        raise ValueError("group has not been sized against a lot")
    drawn = group["units_drawn"]
    failed = group["units_failed"]
    if drawn is None:
        return {"group_id": group["group_id"], "status": "not-drawn", "reason": None}
    if drawn < group["required_units"]:
        return {
            "group_id": group["group_id"],
            "status": "short-sample",
            "reason": "%d unit(s) drawn against %d required" % (drawn, group["required_units"]),
        }
    if failed is None:
        return {"group_id": group["group_id"], "status": "not-graded", "reason": "no result entered"}
    if failed > group["accept_number"]:
        return {
            "group_id": group["group_id"],
            "status": "failed",
            "reason": "%d failure(s) against an accept number of %d"
            % (failed, group["accept_number"]),
        }
    return {"group_id": group["group_id"], "status": "passed", "reason": None}


def assess_lot_acceptance_arrangement(spec):
    """Run the full clause 12.1 lot acceptance arrangement assessment.

    spec keys: lot_size, groups; optional contract_delivery_quantity
    (default 0). Groups carry 'units_drawn' and 'units_failed' once the
    testing has been performed; without them the assessment reports the
    arrangement rather than a verdict on the batch.
    """
    header = validate_lot(spec)
    sized = size_groups(spec)
    demand = sum(g["required_units"] for g in sized if g["destructive"])
    remaining = header["lot_size"] - demand
    burden = demand / float(header["lot_size"])
    graded = [grade_group(g) for g in sized]

    blockers = []
    if demand > header["lot_size"]:
        blockers.append(
            "destructive sampling asks for %d unit(s) from a lot of %d"
            % (demand, header["lot_size"])
        )
    elif remaining < header["contract_delivery_quantity"]:
        blockers.append(
            "sampling leaves %d unit(s) against a contract quantity of %d"
            % (remaining, header["contract_delivery_quantity"])
        )

    short = [g["group_id"] for g in graded if g["status"] == "short-sample"]
    failed = [g["group_id"] for g in graded if g["status"] == "failed"]
    pending = [g["group_id"] for g in graded if g["status"] in ("not-drawn", "not-graded")]

    if blockers:
        disposition = "sampling-plan-not-feasible"
    elif short:
        disposition = "sampling-not-valid"
    elif pending:
        disposition = "sampling-not-complete"
    elif failed:
        disposition = "lot-rejected"
    else:
        disposition = "lot-accepted"
    return {
        "lot_size": header["lot_size"],
        "contract_delivery_quantity": header["contract_delivery_quantity"],
        "group_count": len(sized),
        "arrangement": [
            {
                "group_id": g["group_id"],
                "required_units": g["required_units"],
                "destructive": g["destructive"],
                "accept_number": g["accept_number"],
            }
            for g in sized
        ],
        "destructive_demand": demand,
        "deliverable_after_sampling": remaining,
        "destructive_burden_ratio": burden,
        "graded_groups": graded,
        "short_sampled_groups": short,
        "failed_groups": failed,
        "pending_groups": pending,
        "blockers": blockers,
        "disposition": disposition,
        "accepted": disposition == "lot-accepted",
    }
