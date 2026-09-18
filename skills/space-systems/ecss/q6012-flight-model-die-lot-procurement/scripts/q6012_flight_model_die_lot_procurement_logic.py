"""Flight-model MMIC die lot procurement from a selected foundry.

Anchor: ECSS-Q-ST-60-12C clause 4.2 (the steps by which flight standard
microwave die batches are obtained from a chosen foundry). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Confirm the chosen foundry's qualification is still valid on the day the
   wafers start, not on the day the order was signed, and report how much
   margin is left and whether it lapses before delivery.
2. Hold the batch to one wafer lot and one mask set, because the traceability
   the package no longer provides is carried by that identity alone.
3. Run the flight die count back up the procurement chain: the assembly
   attrition the receiving equipment will suffer, the dies consumed by the
   destructive sample draw and by lot validation testing, then every screening,
   visual and process yield stage in reverse, to the number of dies that have
   to be started.
4. Turn the die starts into whole wafers at the foundry's dies-per-wafer
   figure, and test the result against the largest lot the foundry will run.
5. Emit the ordered procurement steps with their gates, and the findings that
   have to be closed before the wafers are released to start.
"""

import math
from datetime import date

__all__ = [
    "CEIL_TOLERANCE",
    "MIN_YIELD",
    "MAX_YIELD",
    "STEP_KEYS",
    "ceil_units",
    "validate_yield",
    "validate_count",
    "validate_date",
    "validate_yield_stages",
    "chain_yield",
    "qualification_status",
    "delivered_dies_required",
    "good_dies_required",
    "die_starts_required",
    "wafers_to_start",
    "lot_identity_findings",
    "procurement_steps",
    "assess_flight_lot_procurement",
]

# Back-calculating through a yield divides, and a quotient that is exactly a
# whole number can land a few ULPs above it. Snap to the nearest integer inside
# this relative tolerance before rounding up, so an exact chain does not buy a
# spare die on one platform and not on another.
CEIL_TOLERANCE = 1e-9

# A yield is a surviving fraction: strictly above zero, at most everything.
MIN_YIELD = 0.0
MAX_YIELD = 1.0

_STEP_REGISTRY = (
    ("foundry-selection-confirmed",
     "Confirm the chosen foundry and its qualification standing", None),
    ("process-and-mask-set-frozen",
     "Freeze the process and the mask set the batch is run on", None),
    ("wafer-lot-started",
     "Start the identified wafer lot against the frozen mask set", None),
    ("process-monitor-data-reviewed",
     "Review the process control monitor data for the started lot", None),
    ("visual-and-rf-screening",
     "Screen the dies visually and at RF against the die specification", None),
    ("destructive-sample-drawn",
     "Draw the destructive analysis sample from the screened population",
     "destructive_sample_count"),
    ("lot-validation-testing",
     "Run lot validation testing on the drawn validation sample",
     "validation_sample_count"),
    ("radiation-lot-acceptance",
     "Run radiation lot acceptance on dies from the same wafer lot",
     "radiation_required"),
    ("delivery-and-traceability-pack",
     "Deliver the dies with the lot identity and traceability pack", None),
)

STEP_KEYS = tuple(entry[0] for entry in _STEP_REGISTRY)


def ceil_units(value, label="value"):
    """Round a die or wafer count up to a whole unit, tolerant of ULP noise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    if v < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    nearest = math.floor(v + 0.5)
    if abs(v - nearest) <= CEIL_TOLERANCE * max(1.0, abs(v)):
        return int(nearest)
    return int(math.ceil(v))


def validate_yield(value, label="yield"):
    """Return a surviving fraction in the open-above-zero, closed-at-one range."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    if v <= MIN_YIELD or v > MAX_YIELD:
        raise ValueError(
            "%s must be above %g and at most %g, got %r" % (label, MIN_YIELD, MAX_YIELD, value)
        )
    return v


def validate_count(value, label="count", minimum=0):
    """Return a whole non-negative count of dies or wafers."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer" % label)
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def validate_date(value, label="date"):
    """Return an ISO calendar date; a free-text date is refused, not guessed."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string" % label)
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s '%s' is not an ISO calendar date" % (label, value))


def validate_yield_stages(stages):
    """Return the ordered yield stages as (name, surviving fraction) pairs."""
    if not isinstance(stages, (list, tuple)) or not stages:
        raise ValueError("yield_stages needs at least one (name, yield) stage")
    seen = set()
    validated = []
    for i, item in enumerate(stages):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("yield_stages[%d] must be a (name, yield) pair" % i)
        name, value = item
        if not isinstance(name, str) or not name.strip():
            raise ValueError("yield_stages[%d] needs a non-empty stage name" % i)
        key = name.strip().lower()
        if key in seen:
            raise ValueError("yield_stages carries the stage '%s' twice" % key)
        seen.add(key)
        validated.append((key, validate_yield(value, "yield_stages[%d] yield" % i)))
    return validated


def chain_yield(stages):
    """Return the product of the stage yields, the end-to-end surviving fraction."""
    product = 1.0
    for _name, value in validate_yield_stages(stages):
        product *= value
    return product


def qualification_status(qualification_expiry, wafer_start_date, delivery_date=None):
    """Grade the foundry qualification against wafer start, not against order date."""
    expiry = validate_date(qualification_expiry, "qualification_expiry")
    start = validate_date(wafer_start_date, "wafer_start_date")
    record = {
        "qualification_expiry": expiry.isoformat(),
        "wafer_start_date": start.isoformat(),
        "valid_at_wafer_start": start <= expiry,
        "margin_days": (expiry - start).days,
        "lapses_before_delivery": False,
        "delivery_date": None,
    }
    if delivery_date is not None:
        delivery = validate_date(delivery_date, "delivery_date")
        if delivery < start:
            raise ValueError("delivery_date precedes wafer_start_date")
        record["delivery_date"] = delivery.isoformat()
        record["lapses_before_delivery"] = delivery > expiry
    return record


def delivered_dies_required(flight_die_count, assembly_yield):
    """Return the good dies that must be delivered to survive assembly attrition."""
    count = validate_count(flight_die_count, "flight_die_count", minimum=1)
    fraction = validate_yield(assembly_yield, "assembly_yield")
    return ceil_units(count / fraction, "delivered dies")


def good_dies_required(delivered, destructive_sample_count, validation_sample_count):
    """Add the sample draws to the delivered need; samples are consumed, not shipped."""
    delivered = validate_count(delivered, "delivered", minimum=1)
    destructive = validate_count(destructive_sample_count, "destructive_sample_count")
    validation = validate_count(validation_sample_count, "validation_sample_count")
    return delivered + destructive + validation


def die_starts_required(good_needed, stages):
    """Walk the yield stages in reverse to the dies that have to be started."""
    needed = validate_count(good_needed, "good_needed", minimum=1)
    validated = validate_yield_stages(stages)
    cascade = []
    running = needed
    for name, value in reversed(validated):
        entering = ceil_units(running / value, "dies entering %s" % name)
        cascade.append({
            "stage": name,
            "stage_yield": value,
            "dies_out": running,
            "dies_in": entering,
            "dies_lost": entering - running,
        })
        running = entering
    cascade.reverse()
    return running, cascade


def wafers_to_start(die_starts, dies_per_wafer):
    """Return the whole wafers that carry the required die starts."""
    starts = validate_count(die_starts, "die_starts", minimum=1)
    per_wafer = validate_count(dies_per_wafer, "dies_per_wafer", minimum=1)
    return ceil_units(starts / float(per_wafer), "wafers")


def lot_identity_findings(wafer_lot_ids, mask_set_ids):
    """Report a batch that is not one wafer lot on one mask set."""
    findings = []
    for label, values in (("wafer lot", wafer_lot_ids), ("mask set", mask_set_ids)):
        if not isinstance(values, (list, tuple)) or not values:
            raise ValueError("%s identifiers must be a non-empty sequence" % label)
        tokens = set()
        for item in values:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("%s identifiers must be non-empty strings" % label)
            tokens.add(item.strip().lower())
        if len(tokens) > 1:
            findings.append(
                "the batch spans %d %s identifiers; a flight batch is one %s"
                % (len(tokens), label, label)
            )
    return findings


def procurement_steps(case):
    """Return the ordered procurement steps that apply to this case."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    steps = []
    position = 0
    for key, gate, flag in _STEP_REGISTRY:
        if flag is not None:
            value = case.get(flag)
            if flag == "radiation_required":
                if not value:
                    continue
            elif not isinstance(value, int) or isinstance(value, bool) or value < 1:
                continue
        position += 1
        steps.append({"position": position, "key": key, "gate": gate})
    return steps


def assess_flight_lot_procurement(spec):
    """Run the full clause 4.2 flight die lot procurement assessment.

    spec keys: flight_die_count, assembly_yield, destructive_sample_count,
    validation_sample_count, yield_stages, dies_per_wafer, max_wafers_per_lot,
    qualification_expiry, wafer_start_date, wafer_lot_ids, mask_set_ids,
    optional delivery_date and radiation_required.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "flight_die_count", "assembly_yield", "destructive_sample_count",
        "validation_sample_count", "yield_stages", "dies_per_wafer",
        "max_wafers_per_lot", "qualification_expiry", "wafer_start_date",
        "wafer_lot_ids", "mask_set_ids",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    qualification = qualification_status(
        spec["qualification_expiry"], spec["wafer_start_date"], spec.get("delivery_date")
    )
    delivered = delivered_dies_required(spec["flight_die_count"], spec["assembly_yield"])
    destructive = validate_count(spec["destructive_sample_count"], "destructive_sample_count")
    validation = validate_count(spec["validation_sample_count"], "validation_sample_count")
    good_needed = good_dies_required(delivered, destructive, validation)
    starts, cascade = die_starts_required(good_needed, spec["yield_stages"])
    per_wafer = validate_count(spec["dies_per_wafer"], "dies_per_wafer", minimum=1)
    wafers = wafers_to_start(starts, per_wafer)
    max_wafers = validate_count(spec["max_wafers_per_lot"], "max_wafers_per_lot", minimum=1)

    findings = list(lot_identity_findings(spec["wafer_lot_ids"], spec["mask_set_ids"]))
    if not qualification["valid_at_wafer_start"]:
        findings.append(
            "the foundry qualification expired %d days before wafer start; the lot cannot start"
            % (-qualification["margin_days"])
        )
    if qualification["lapses_before_delivery"]:
        findings.append(
            "the foundry qualification lapses between wafer start and delivery; "
            "confirm the lot is covered by the standing at start"
        )
    if destructive < 1:
        findings.append(
            "no destructive analysis sample is drawn; a flight lot owes a destructive draw"
        )
    if validation < 1:
        findings.append(
            "no lot validation sample is drawn; the lot has nothing to be graded on"
        )
    if wafers > max_wafers:
        findings.append(
            "the need is %d wafers but the foundry runs at most %d per lot; "
            "one flight batch cannot cover it" % (wafers, max_wafers)
        )

    case = dict(spec)
    case["radiation_required"] = bool(spec.get("radiation_required", False))
    return {
        "qualification": qualification,
        "delivered_dies_required": delivered,
        "good_dies_required": good_needed,
        "die_starts_required": starts,
        "cascade": cascade,
        "chain_yield": chain_yield(spec["yield_stages"]),
        "wafers_to_start": wafers,
        "dies_available": wafers * per_wafer,
        "spare_dies": wafers * per_wafer - starts,
        "steps": procurement_steps(case),
        "findings": findings,
        "releasable": not findings,
    }
