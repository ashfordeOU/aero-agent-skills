"""Handling, packaging and storage protection for Class 3 EEE parts.

Anchor: ECSS-Q-ST-60C clause 6.4 (handling, packaging and storing Class 3 parts
so that they are neither damaged nor degraded before use). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Fix the moisture budget the part family is entitled to once its barrier bag
   has been opened, which is a property of the part rather than of the store.
2. Spend that budget across the exposure log, charging each interval at the rate
   its environment earns, so time in dry nitrogen costs nothing and time on an
   open bench costs more than time in a cleanroom.
3. Credit a recorded bake only where it reached the temperature and the duration
   the part family needs, and reset the budget rather than discount it.
4. Read the protective packaging as a chain from the part outwards, and report a
   layer that is missing or out of order rather than scoring the layers present.
5. Total the handling event ledger, letting a single severe event outrank any
   amount of accumulated minor exposure.
6. Return one verdict per lot with the remaining budget and every reason named.
"""

__all__ = [
    "STORAGE_VERDICTS",
    "MSL_FLOOR_LIFE_HOURS",
    "REQUIRED_BAKE_HOURS",
    "MINIMUM_BAKE_TEMPERATURE_C",
    "ENVIRONMENT_COST_TENTHS",
    "PACKAGING_LAYER_ORDER",
    "HANDLING_EVENT_WEIGHTS",
    "SEVERE_HANDLING_EVENTS",
    "REQUIRED_LOT_FIELDS",
    "floor_life_hours",
    "exposure_cost_tenths",
    "bake_qualifies",
    "floor_life_budget",
    "packaging_findings",
    "handling_event_score",
    "storage_verdict",
    "assess_handling_and_storage",
]

# Verdicts, from a lot that may be issued as it stands to one that may not move.
STORAGE_VERDICTS = (
    "fit-for-issue",
    "bake-before-use",
    "repack-and-requalify",
    "quarantine",
)

# Hours of open exposure a moisture level is entitled to at the reference
# ambient. Level 1 carries no budget at all because it needs none.
MSL_FLOOR_LIFE_HOURS = {
    1: None,
    2: 8760,
    3: 168,
    4: 72,
    5: 48,
    6: 6,
}

# Hours of bake a level needs before its budget may be reset.
REQUIRED_BAKE_HOURS = {
    2: 12,
    3: 24,
    4: 48,
    5: 48,
    6: 96,
}

# The floor below which a bake is a warm shelf rather than a bake.
MINIMUM_BAKE_TEMPERATURE_C = 110

# What one hour in each environment costs, in tenths of a budget hour. Integers
# throughout so the same log spends the same budget on every platform.
ENVIRONMENT_COST_TENTHS = {
    "sealed-dry-nitrogen": 0,
    "dry-cabinet": 1,
    "controlled-cleanroom": 10,
    "open-bench": 20,
}

# The protective chain, innermost first.
PACKAGING_LAYER_ORDER = (
    "conductive-inner-carrier",
    "moisture-barrier-bag",
    "cushioned-transit-outer",
)

# What each recorded handling event adds to the lot's exposure score.
HANDLING_EVENT_WEIGHTS = {
    "ungrounded-handling": 4,
    "unprotected-transfer": 3,
    "barrier-opened-outside-protected-area": 5,
    "container-drop": 8,
    "desiccant-absent-at-reseal": 2,
}

# One of these on its own ends the assessment, whatever the score says.
SEVERE_HANDLING_EVENTS = ("container-drop",)

REQUIRED_LOT_FIELDS = (
    "lot_id",
    "part_number",
    "moisture_sensitivity_level",
    "exposure_log",
    "packaging_chain",
)


def _require_non_negative_int(value, label):
    """Return value when it is a non-negative integer, else raise."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative integer, got %r" % (label, value))
    return value


def floor_life_hours(moisture_sensitivity_level):
    """Return the open-exposure budget a moisture level carries, or None."""
    if (
        not isinstance(moisture_sensitivity_level, int)
        or isinstance(moisture_sensitivity_level, bool)
        or moisture_sensitivity_level not in MSL_FLOOR_LIFE_HOURS
    ):
        raise ValueError(
            "moisture_sensitivity_level must be one of %s, got %r"
            % (sorted(MSL_FLOOR_LIFE_HOURS), moisture_sensitivity_level)
        )
    return MSL_FLOOR_LIFE_HOURS[moisture_sensitivity_level]


def exposure_cost_tenths(exposure_log):
    """Return what an exposure log costs, in tenths of a budget hour.

    Charging every environment alike is what turns a lot that lived in a dry
    cabinet into a lot that lived on a bench; the rates are what separate them.
    """
    if not isinstance(exposure_log, (list, tuple)):
        raise ValueError("exposure_log must be a sequence of exposure intervals")
    total = 0
    for index, interval in enumerate(exposure_log):
        if not isinstance(interval, dict):
            raise ValueError("exposure_log[%d] must be a mapping" % index)
        for key in ("hours", "environment"):
            if key not in interval:
                raise ValueError("exposure_log[%d] missing key '%s'" % (index, key))
        hours = _require_non_negative_int(
            interval["hours"], "exposure_log[%d]['hours']" % index
        )
        environment = str(interval["environment"]).strip()
        if environment not in ENVIRONMENT_COST_TENTHS:
            raise ValueError(
                "exposure_log[%d] names unknown environment %r" % (index, environment)
            )
        total += hours * ENVIRONMENT_COST_TENTHS[environment]
    return total


def bake_qualifies(bake, moisture_sensitivity_level):
    """Return whether a recorded bake may reset the budget, and why it may not."""
    if moisture_sensitivity_level not in MSL_FLOOR_LIFE_HOURS:
        raise ValueError(
            "moisture_sensitivity_level %r is not a recognised level"
            % (moisture_sensitivity_level,)
        )
    if bake is None:
        return {"qualifies": False, "reasons": ("no bake recorded",)}
    if not isinstance(bake, dict):
        raise ValueError("bake must be a mapping or None")
    for key in ("hours", "temperature_c"):
        if key not in bake:
            raise ValueError("bake missing key '%s'" % key)
    hours = _require_non_negative_int(bake["hours"], "bake['hours']")
    temperature = bake["temperature_c"]
    if not isinstance(temperature, int) or isinstance(temperature, bool):
        raise ValueError("bake['temperature_c'] must be an integer")
    needed = REQUIRED_BAKE_HOURS.get(moisture_sensitivity_level)
    if needed is None:
        return {"qualifies": False, "reasons": ("this level carries no budget to reset",)}
    reasons = []
    if temperature < MINIMUM_BAKE_TEMPERATURE_C:
        reasons.append(
            "held at %d C, below the %d C floor" % (temperature, MINIMUM_BAKE_TEMPERATURE_C)
        )
    if hours < needed:
        reasons.append("ran %d hours against the %d hours this level needs" % (hours, needed))
    return {"qualifies": not reasons, "reasons": tuple(reasons)}


def floor_life_budget(moisture_sensitivity_level, exposure_log, bake=None):
    """Return the open-exposure budget, what the log spent and what is left.

    A qualifying bake resets the spend to zero rather than discounting it, which
    is the whole point of baking: the moisture is driven out, not averaged away.
    """
    budget = floor_life_hours(moisture_sensitivity_level)
    spent_tenths = exposure_cost_tenths(exposure_log)
    bake_result = bake_qualifies(bake, moisture_sensitivity_level) if bake is not None else None
    reset = bool(bake_result and bake_result["qualifies"])
    if reset:
        spent_tenths = 0
    if budget is None:
        return {
            "budget_hours": None,
            "spent_hours_tenths": spent_tenths,
            "remaining_hours_tenths": None,
            "within_budget": True,
            "bake_reset": reset,
            "margin": 1.0,
        }
    budget_tenths = budget * 10
    remaining = budget_tenths - spent_tenths
    return {
        "budget_hours": budget,
        "spent_hours_tenths": spent_tenths,
        "remaining_hours_tenths": remaining,
        "within_budget": spent_tenths <= budget_tenths,
        "bake_reset": reset,
        "margin": remaining / budget_tenths,
    }


def packaging_findings(packaging_chain, moisture_sensitivity_level):
    """Return what is wrong with the protective chain, innermost layer first."""
    if not isinstance(packaging_chain, (list, tuple)):
        raise ValueError("packaging_chain must be a sequence of layer names")
    layers = [str(name).strip() for name in packaging_chain]
    for name in layers:
        if name not in PACKAGING_LAYER_ORDER:
            raise ValueError("packaging_chain names unknown layer %r" % (name,))
    if len(set(layers)) != len(layers):
        raise ValueError("packaging_chain repeats a layer")
    needed = ["conductive-inner-carrier", "cushioned-transit-outer"]
    if floor_life_hours(moisture_sensitivity_level) is not None:
        needed.insert(1, "moisture-barrier-bag")
    findings = []
    for name in needed:
        if name not in layers:
            findings.append("the %s layer is absent" % name)
    present = [name for name in layers if name in needed]
    expected_order = [name for name in PACKAGING_LAYER_ORDER if name in present]
    if present != expected_order:
        findings.append("the layers are recorded out of order, innermost first")
    return tuple(findings)


def handling_event_score(handling_events):
    """Return the exposure score a handling ledger carries and its severe flag."""
    if not isinstance(handling_events, (list, tuple)):
        raise ValueError("handling_events must be a sequence of event names")
    score = 0
    severe = False
    counted = []
    for name in handling_events:
        event = str(name).strip()
        if event not in HANDLING_EVENT_WEIGHTS:
            raise ValueError("unknown handling event %r" % (event,))
        score += HANDLING_EVENT_WEIGHTS[event]
        counted.append(event)
        if event in SEVERE_HANDLING_EVENTS:
            severe = True
    return {"score": score, "severe": severe, "events": tuple(sorted(counted))}


def storage_verdict(within_budget, bake_available, packaging_ok, severe_event,
                    score, score_limit=6):
    """Return the verdict one stored lot has earned."""
    for label, flag in (
        ("within_budget", within_budget),
        ("bake_available", bake_available),
        ("packaging_ok", packaging_ok),
        ("severe_event", severe_event),
    ):
        if not isinstance(flag, bool):
            raise ValueError("%s must be a bool, got %r" % (label, flag))
    _require_non_negative_int(score, "score")
    _require_non_negative_int(score_limit, "score_limit")
    if severe_event:
        return "quarantine"
    if not packaging_ok:
        return "repack-and-requalify"
    if not within_budget:
        return "bake-before-use" if bake_available else "quarantine"
    if score > score_limit:
        return "repack-and-requalify"
    return "fit-for-issue"


def assess_handling_and_storage(lot, score_limit=6):
    """Run the full clause 6.4 handling and storage assessment for one lot."""
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping")
    for field in REQUIRED_LOT_FIELDS:
        if field not in lot or lot[field] in (None, ""):
            raise ValueError("lot missing required field '%s'" % field)
    lot_id = str(lot["lot_id"]).strip()
    msl = lot["moisture_sensitivity_level"]
    budget = floor_life_budget(msl, lot["exposure_log"], lot.get("bake"))
    packaging = packaging_findings(lot["packaging_chain"], msl)
    ledger = handling_event_score(lot.get("handling_events", []) or [])
    bake_available = bool(lot.get("bake_facility_available", True))
    if not isinstance(bake_available, bool):
        raise ValueError("bake_facility_available must be a bool")
    verdict = storage_verdict(
        budget["within_budget"],
        bake_available,
        not packaging,
        ledger["severe"],
        ledger["score"],
        score_limit,
    )

    findings = []
    if not budget["within_budget"]:
        findings.append(
            "lot %s has spent %d tenths of an hour against a budget of %d"
            % (lot_id, budget["spent_hours_tenths"], budget["budget_hours"] * 10)
        )
    findings.extend("lot %s: %s" % (lot_id, note) for note in packaging)
    if ledger["severe"]:
        findings.append(
            "lot %s carries a severe handling event: %s"
            % (lot_id, ", ".join(e for e in ledger["events"] if e in SEVERE_HANDLING_EVENTS))
        )
    elif ledger["score"] > score_limit:
        findings.append(
            "lot %s carries a handling score of %d against a limit of %d"
            % (lot_id, ledger["score"], score_limit)
        )
    bake = lot.get("bake")
    if bake is not None:
        bake_result = bake_qualifies(bake, msl)
        if not bake_result["qualifies"]:
            findings.append(
                "lot %s recorded a bake that does not reset the budget: %s"
                % (lot_id, "; ".join(bake_result["reasons"]))
            )
    return {
        "lot_id": lot_id,
        "part_number": str(lot["part_number"]).strip().upper(),
        "moisture_sensitivity_level": msl,
        "budget": budget,
        "packaging_findings": packaging,
        "handling": ledger,
        "verdict": verdict,
        "findings": findings,
        "fit_as_stored": verdict == "fit-for-issue",
    }
