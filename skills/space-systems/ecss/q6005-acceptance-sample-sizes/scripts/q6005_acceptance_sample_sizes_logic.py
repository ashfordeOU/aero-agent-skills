"""Acceptance sample sizes drawn from a hybrid production batch.

Anchor: ECSS-Q-ST-60-05C clause 12.1.2 (how many units are drawn for
acceptance testing relative to the size of the batch they come from).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the batch as a positive count of manufactured units, and validate
   the sampling schedule it will be read against: ascending, contiguous bands,
   each naming a sample size and the number of nonconforming units the band
   still accepts.
2. Read the band the batch falls in. Small batches collapse to full
   inspection: when the schedule's sample would be most of the batch anyway,
   drawing a sample buys nothing and every unit is tested.
3. Cap the sample at the batch. A schedule band is written for a range, and
   the low end of a band can name a sample larger than a batch sitting just
   inside it; the cap is what stops a plan asking for units that do not exist.
4. Report the sampling fraction, so a plan can be compared against a
   contractual minimum percentage rather than only against the schedule.
5. Where the acceptance tests consume the units they are drawn on, check the
   batch is large enough to yield both the sample and the deliverable
   quantity, and report the shortfall when it is not.
6. Disposition a batch from the nonconforming count found in its sample
   against the band's acceptance number.

The schedule shipped here is a default structure, not a transcription. A
project substitutes its own table through the `schedule` argument; the
validation, the band lookup, the cap, the fraction and the disposition are
the part that does not change.
"""

__all__ = [
    "DEFAULT_SAMPLE_SCHEDULE",
    "FULL_INSPECTION_THRESHOLD",
    "validate_batch_size",
    "validate_schedule",
    "schedule_band",
    "select_sample_plan",
    "sampling_fraction",
    "acceptance_number_for",
    "destructive_sample_shortfall",
    "batch_disposition",
    "assess_acceptance_sampling",
]

# (lowest batch size in band, highest batch size in band or None for open
# ended, sample size, acceptance number).
DEFAULT_SAMPLE_SCHEDULE = (
    (1, 8, 8, 0),
    (9, 15, 8, 0),
    (16, 25, 13, 0),
    (26, 50, 20, 0),
    (51, 90, 32, 0),
    (91, 150, 50, 1),
    (151, 280, 80, 1),
    (281, 500, 125, 2),
    (501, 1200, 200, 3),
    (1201, None, 315, 5),
)

# At or below this batch size the sample is the whole batch.
FULL_INSPECTION_THRESHOLD = 8


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


def validate_batch_size(batch_size):
    """Return the batch size as a positive integer count of units."""
    return _require_positive_int(batch_size, "batch_size")


def validate_schedule(schedule):
    """Return the sampling schedule as validated tuples.

    Bands ascend, touch without gaps and do not overlap, and only the last one
    may be open ended. A gap would leave a batch size with no plan at all, and
    silently falling through to full inspection there hides the hole.
    """
    if isinstance(schedule, dict) or not isinstance(schedule, (list, tuple)):
        raise ValueError("schedule must be a sequence of bands")
    if not schedule:
        raise ValueError("schedule contains no bands")
    bands = []
    expected_low = 1
    for index, band in enumerate(schedule):
        if not isinstance(band, (list, tuple)) or len(band) != 4:
            raise ValueError(
                "schedule[%d] must be (low, high, sample_size, acceptance_number)" % index
            )
        low, high, sample_size, acceptance_number = band
        _require_positive_int(low, "schedule[%d] low" % index)
        _require_positive_int(sample_size, "schedule[%d] sample_size" % index)
        _require_non_negative_int(acceptance_number, "schedule[%d] acceptance_number" % index)
        if low != expected_low:
            raise ValueError(
                "schedule[%d] starts at %d but the previous band ends before %d"
                % (index, low, expected_low)
            )
        if high is None:
            if index != len(schedule) - 1:
                raise ValueError("only the last schedule band may be open ended")
        else:
            _require_positive_int(high, "schedule[%d] high" % index)
            if high < low:
                raise ValueError("schedule[%d] ends (%d) below its start (%d)" % (index, high, low))
            expected_low = high + 1
        if acceptance_number >= sample_size:
            raise ValueError(
                "schedule[%d] accepts %d nonconforming units out of a sample of %d"
                % (index, acceptance_number, sample_size)
            )
        bands.append((low, high, sample_size, acceptance_number))
    return tuple(bands)


def schedule_band(batch_size, schedule=DEFAULT_SAMPLE_SCHEDULE):
    """Return the schedule band a batch of this size falls in."""
    size = validate_batch_size(batch_size)
    for band in validate_schedule(schedule):
        low, high, _, _ = band
        if size >= low and (high is None or size <= high):
            return band
    raise ValueError("no schedule band covers a batch of %d units" % size)


def select_sample_plan(
    batch_size,
    schedule=DEFAULT_SAMPLE_SCHEDULE,
    full_inspection_threshold=FULL_INSPECTION_THRESHOLD,
):
    """Return the sample size and acceptance number for a batch.

    Full inspection wins at or below the threshold, and the sample is capped
    at the batch in every case.
    """
    size = validate_batch_size(batch_size)
    threshold = _require_positive_int(full_inspection_threshold, "full_inspection_threshold")
    low, high, scheduled_sample, acceptance_number = schedule_band(size, schedule)
    if size <= threshold:
        return {
            "batch_size": size,
            "band": (low, high),
            "scheduled_sample_size": scheduled_sample,
            "sample_size": size,
            "acceptance_number": 0,
            "full_inspection": True,
            "capped_to_batch": scheduled_sample > size,
        }
    sample_size = min(scheduled_sample, size)
    return {
        "batch_size": size,
        "band": (low, high),
        "scheduled_sample_size": scheduled_sample,
        "sample_size": sample_size,
        "acceptance_number": acceptance_number,
        "full_inspection": sample_size == size,
        "capped_to_batch": scheduled_sample > size,
    }


def sampling_fraction(batch_size, schedule=DEFAULT_SAMPLE_SCHEDULE, **kwargs):
    """Return the drawn sample as a fraction of the batch it came from."""
    plan = select_sample_plan(batch_size, schedule, **kwargs)
    return plan["sample_size"] / float(plan["batch_size"])


def acceptance_number_for(batch_size, schedule=DEFAULT_SAMPLE_SCHEDULE, **kwargs):
    """Return the nonconforming count a batch of this size still accepts."""
    return select_sample_plan(batch_size, schedule, **kwargs)["acceptance_number"]


def destructive_sample_shortfall(
    batch_size,
    deliverable_quantity,
    schedule=DEFAULT_SAMPLE_SCHEDULE,
    **kwargs
):
    """Return how many units a destructive plan is short of, zero when it fits.

    Units consumed by a destructive acceptance test never ship, so the batch
    has to carry the sample on top of the order, not inside it.
    """
    plan = select_sample_plan(batch_size, schedule, **kwargs)
    wanted = _require_positive_int(deliverable_quantity, "deliverable_quantity")
    remaining = plan["batch_size"] - plan["sample_size"]
    return max(0, wanted - remaining)


def batch_disposition(
    batch_size,
    nonconforming_found,
    schedule=DEFAULT_SAMPLE_SCHEDULE,
    **kwargs
):
    """Return accept or reject for a batch from its sample result."""
    plan = select_sample_plan(batch_size, schedule, **kwargs)
    found = _require_non_negative_int(nonconforming_found, "nonconforming_found")
    if found > plan["sample_size"]:
        raise ValueError(
            "sample of %d units cannot yield %d nonconforming units"
            % (plan["sample_size"], found)
        )
    accepted = found <= plan["acceptance_number"]
    return {
        "sample_size": plan["sample_size"],
        "acceptance_number": plan["acceptance_number"],
        "nonconforming_found": found,
        "margin": plan["acceptance_number"] - found,
        "disposition": "accept" if accepted else "reject",
        "accepted": accepted,
    }


def assess_acceptance_sampling(spec):
    """Run the full clause 12.1.2 sample-size assessment for one batch.

    spec keys: batch_size, optional deliverable_quantity, optional
    nonconforming_found, optional destructive (default False), optional
    minimum_fraction, optional schedule, optional full_inspection_threshold.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "batch_size" not in spec:
        raise ValueError("spec missing required key 'batch_size'")
    destructive = spec.get("destructive", False)
    if not isinstance(destructive, bool):
        raise ValueError("destructive must be a boolean")
    schedule = spec.get("schedule", DEFAULT_SAMPLE_SCHEDULE)
    threshold = spec.get("full_inspection_threshold", FULL_INSPECTION_THRESHOLD)
    plan = select_sample_plan(spec["batch_size"], schedule, full_inspection_threshold=threshold)
    fraction = plan["sample_size"] / float(plan["batch_size"])

    findings = []
    minimum_fraction = spec.get("minimum_fraction")
    meets_minimum = True
    if minimum_fraction is not None:
        if not isinstance(minimum_fraction, (int, float)) or isinstance(minimum_fraction, bool):
            raise ValueError("minimum_fraction must be a number")
        if not 0.0 < minimum_fraction <= 1.0:
            raise ValueError("minimum_fraction must lie in (0, 1]")
        # The comparison absorbs representation error rather than relaxing the
        # contractual floor: a plan landing exactly on it meets it.
        meets_minimum = fraction >= minimum_fraction - 1e-9
        if not meets_minimum:
            findings.append(
                "sampling fraction %.4f is below the contractual minimum %.4f"
                % (fraction, minimum_fraction)
            )

    shortfall = 0
    if destructive:
        if "deliverable_quantity" not in spec:
            raise ValueError("a destructive plan needs a 'deliverable_quantity'")
        shortfall = destructive_sample_shortfall(
            spec["batch_size"],
            spec["deliverable_quantity"],
            schedule,
            full_inspection_threshold=threshold,
        )
        if shortfall:
            findings.append(
                "destructive sample leaves %d units short of the deliverable quantity"
                % shortfall
            )
        if plan["full_inspection"]:
            findings.append(
                "full inspection is destructive here; no unit of the batch survives to ship"
            )

    disposition = None
    if spec.get("nonconforming_found") is not None:
        result = batch_disposition(
            spec["batch_size"],
            spec["nonconforming_found"],
            schedule,
            full_inspection_threshold=threshold,
        )
        disposition = result["disposition"]
        if not result["accepted"]:
            findings.append(
                "%d nonconforming units found against an acceptance number of %d"
                % (result["nonconforming_found"], result["acceptance_number"])
            )

    return {
        "batch_size": plan["batch_size"],
        "band": plan["band"],
        "sample_size": plan["sample_size"],
        "scheduled_sample_size": plan["scheduled_sample_size"],
        "acceptance_number": plan["acceptance_number"],
        "full_inspection": plan["full_inspection"],
        "capped_to_batch": plan["capped_to_batch"],
        "sampling_fraction": fraction,
        "meets_minimum_fraction": meets_minimum,
        "destructive": destructive,
        "destructive_shortfall": shortfall,
        "disposition": disposition,
        "plan_is_workable": not findings,
        "findings": findings,
    }
