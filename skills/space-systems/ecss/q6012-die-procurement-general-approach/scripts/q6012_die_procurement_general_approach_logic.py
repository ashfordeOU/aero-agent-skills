"""Microwave die procurement, wafer start to accepted delivery: general approach.

Anchor: ECSS-Q-ST-60-12C clause 10.1 -- the overall framing of how microwave
dies travel from wafer fabrication to a delivery the customer accepts.
Paraphrased into an implementable sizing and route-integrity procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the declared stage chain against the canonical route: reject an
   unknown or repeated stage, and report the stages left out and the pairs
   declared out of sequence.
2. Multiply the per-stage yields into a cumulative survival fraction for one
   wafer travelling the whole route.
3. Work the required flight quantity plus its contingency back to a wafer
   start, then step that start up until the forward projection, which floors
   a part count at every stage, actually meets the target.
4. Project the surviving population forward stage by stage, changing the unit
   from wafers to dies where the route dices.
5. Name every stage that declares no owner or no exit criterion, because a
   stage nobody owns has no handover and cannot be an acceptance point.
"""

import math

__all__ = [
    "MAX_START_ADJUSTMENT",
    "CANONICAL_ROUTE",
    "STAGE_UNITS",
    "validate_stage",
    "validate_route",
    "cumulative_survival",
    "analytic_wafer_start",
    "forward_projection",
    "delivered_quantity",
    "size_wafer_start",
    "ownership_gaps",
    "assess_die_procurement_approach",
]

# Flooring a part count at every stage can cost a few dies against the
# analytic start. Step the start up rather than rounding the yields.
MAX_START_ADJUSTMENT = 50

CANONICAL_ROUTE = (
    "wafer_fabrication",
    "wafer_acceptance",
    "dicing",
    "die_visual_inspection",
    "die_screening",
    "die_lot_acceptance",
    "packing_and_storage",
    "delivery_acceptance",
)

# 'transition' is the stage where the population stops being counted in
# wafers and starts being counted in dies.
STAGE_UNITS = {
    "wafer_fabrication": "wafer",
    "wafer_acceptance": "wafer",
    "dicing": "transition",
    "die_visual_inspection": "die",
    "die_screening": "die",
    "die_lot_acceptance": "die",
    "packing_and_storage": "die",
    "delivery_acceptance": "die",
}

_RANK = {name: index for index, name in enumerate(CANONICAL_ROUTE)}


def _positive_number(value, label, allow_zero=False):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0 or (number == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_stage(stage, index=0):
    """Return one declared route stage in canonical form."""
    if not isinstance(stage, dict):
        raise ValueError("stage %d must be a mapping" % index)
    if "stage" not in stage:
        raise ValueError("stage %d must name a 'stage'" % index)
    name = stage["stage"]
    if not isinstance(name, str):
        raise ValueError("stage %d name must be a string" % index)
    key = name.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in _RANK:
        raise ValueError("stage %d names an unknown route stage %r" % (index, name))
    if "yield_fraction" not in stage:
        raise ValueError("stage '%s' must declare a yield_fraction" % key)
    yield_fraction = _positive_number(stage["yield_fraction"], "yield of stage '%s'" % key)
    if yield_fraction > 1.0:
        raise ValueError("yield of stage '%s' cannot exceed one, got %r"
                         % (key, stage["yield_fraction"]))
    owner = stage.get("owner")
    exit_criterion = stage.get("exit_criterion")
    for label, value in (("owner", owner), ("exit_criterion", exit_criterion)):
        if value is not None and not isinstance(value, str):
            raise ValueError("stage '%s' %s must be text" % (key, label))
    return {
        "stage": key,
        "rank": _RANK[key],
        "unit": STAGE_UNITS[key],
        "yield_fraction": yield_fraction,
        "owner": (owner or "").strip(),
        "exit_criterion": (exit_criterion or "").strip(),
    }


def validate_route(stages):
    """Return the canonical route records plus the sequence findings."""
    if not isinstance(stages, (list, tuple)) or not stages:
        raise ValueError("stages must be a non-empty sequence")
    records = []
    seen = set()
    for index, stage in enumerate(stages):
        record = validate_stage(stage, index)
        if record["stage"] in seen:
            raise ValueError("stage '%s' is declared twice" % record["stage"])
        seen.add(record["stage"])
        records.append(record)
    out_of_sequence = []
    for i in range(1, len(records)):
        if records[i]["rank"] < records[i - 1]["rank"]:
            out_of_sequence.append((records[i - 1]["stage"], records[i]["stage"]))
    absent = tuple(name for name in CANONICAL_ROUTE if name not in seen)
    return {
        "records": records,
        "absent_stages": absent,
        "out_of_sequence": tuple(out_of_sequence),
    }


def cumulative_survival(records):
    """Return the fraction of a starting population that reaches delivery."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of route stages")
    survival = 1.0
    for record in records:
        survival *= record["yield_fraction"]
    return survival


def analytic_wafer_start(dice_required, dice_per_wafer, survival, contingency_fraction=0.0):
    """Return the unfloored wafer start the target quantity implies."""
    if not isinstance(dice_required, int) or isinstance(dice_required, bool):
        raise ValueError("dice_required must be an integer")
    if dice_required < 1:
        raise ValueError("dice_required must be at least one, got %d" % dice_required)
    if not isinstance(dice_per_wafer, int) or isinstance(dice_per_wafer, bool):
        raise ValueError("dice_per_wafer must be an integer")
    if dice_per_wafer < 1:
        raise ValueError("dice_per_wafer must be at least one, got %d" % dice_per_wafer)
    survival = _positive_number(survival, "survival fraction")
    if survival > 1.0:
        raise ValueError("survival fraction cannot exceed one, got %r" % (survival,))
    contingency = _positive_number(contingency_fraction, "contingency_fraction",
                                   allow_zero=True)
    target = dice_required * (1.0 + contingency)
    return math.ceil(target / (dice_per_wafer * survival))


def forward_projection(wafer_start, dice_per_wafer, records):
    """Project the surviving population through the route, stage by stage."""
    if not isinstance(wafer_start, int) or isinstance(wafer_start, bool):
        raise ValueError("wafer_start must be an integer")
    if wafer_start < 1:
        raise ValueError("wafer_start must be at least one, got %d" % wafer_start)
    if not isinstance(dice_per_wafer, int) or isinstance(dice_per_wafer, bool):
        raise ValueError("dice_per_wafer must be an integer")
    if dice_per_wafer < 1:
        raise ValueError("dice_per_wafer must be at least one, got %d" % dice_per_wafer)
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of route stages")
    quantity = wafer_start
    unit = "wafer"
    rows = []
    for record in records:
        entering = quantity
        entering_unit = unit
        if record["unit"] == "transition":
            leaving = int(math.floor(entering * record["yield_fraction"] * dice_per_wafer))
            unit = "die"
        else:
            leaving = int(math.floor(entering * record["yield_fraction"]))
        if leaving < 0:
            leaving = 0
        rows.append(
            {
                "stage": record["stage"],
                "entering": entering,
                "entering_unit": entering_unit,
                "leaving": leaving,
                "leaving_unit": unit,
            }
        )
        quantity = leaving
    return rows


def delivered_quantity(projection):
    """Return the population leaving the last stage of a projection."""
    if not isinstance(projection, (list, tuple)) or not projection:
        raise ValueError("projection must be a non-empty sequence")
    return projection[-1]["leaving"]


def size_wafer_start(dice_required, dice_per_wafer, records, contingency_fraction=0.0):
    """Return the wafer start that actually delivers the target after flooring."""
    survival = cumulative_survival(records)
    start = analytic_wafer_start(dice_required, dice_per_wafer, survival,
                                 contingency_fraction)
    contingency = _positive_number(contingency_fraction, "contingency_fraction",
                                   allow_zero=True)
    target = int(math.ceil(dice_required * (1.0 + contingency)))
    adjustment = 0
    projection = forward_projection(start, dice_per_wafer, records)
    while delivered_quantity(projection) < target and adjustment < MAX_START_ADJUSTMENT:
        adjustment += 1
        projection = forward_projection(start + adjustment, dice_per_wafer, records)
    return {
        "analytic_start": start,
        "adjustment": adjustment,
        "wafer_start": start + adjustment,
        "target_dice": target,
        "projection": projection,
        "delivered_dice": delivered_quantity(projection),
        "target_met": delivered_quantity(projection) >= target,
    }


def ownership_gaps(records):
    """Return the stages declaring no owner and the stages declaring no exit criterion."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of route stages")
    unowned = tuple(record["stage"] for record in records if not record["owner"])
    uncriteria = tuple(
        record["stage"] for record in records if not record["exit_criterion"]
    )
    return {"stages_without_owner": unowned, "stages_without_exit_criterion": uncriteria}


def assess_die_procurement_approach(case):
    """Size and grade a microwave die procurement from wafer start to delivery.

    case keys: stages (sequence of {stage, yield_fraction, owner, exit_criterion}),
    dice_required, dice_per_wafer, optional contingency_fraction.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("stages", "dice_required", "dice_per_wafer"):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)
    route = validate_route(case["stages"])
    records = route["records"]
    survival = cumulative_survival(records)
    sizing = size_wafer_start(
        case["dice_required"],
        case["dice_per_wafer"],
        records,
        case.get("contingency_fraction", 0.0),
    )
    gaps = ownership_gaps(records)

    findings = []
    for name in route["absent_stages"]:
        findings.append("canonical route stage '%s' is not declared" % name)
    for before, after in route["out_of_sequence"]:
        findings.append("stage '%s' is declared before '%s'" % (after, before))
    for name in gaps["stages_without_owner"]:
        findings.append("stage '%s' declares no owner, so its handover is undefined"
                        % name)
    for name in gaps["stages_without_exit_criterion"]:
        findings.append("stage '%s' declares no exit criterion, so it cannot be closed"
                        % name)
    if sizing["adjustment"]:
        findings.append(
            "the analytic start of %d wafers was raised by %d to survive the "
            "per-stage flooring" % (sizing["analytic_start"], sizing["adjustment"])
        )
    if not sizing["target_met"]:
        findings.append(
            "no start within %d wafers of the analytic value reaches the target "
            "of %d dies" % (MAX_START_ADJUSTMENT, sizing["target_dice"])
        )

    viable = (
        sizing["target_met"]
        and not route["absent_stages"]
        and not route["out_of_sequence"]
        and not gaps["stages_without_owner"]
        and not gaps["stages_without_exit_criterion"]
    )
    return {
        "route": route,
        "cumulative_survival": survival,
        "sizing": sizing,
        "ownership_gaps": gaps,
        "findings": findings,
        "viable": viable,
    }
