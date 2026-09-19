"""In-service feedback, launch-site procedures and monitoring for explosive items.

Anchor: ECSS-E-ST-33-11C Rev.1 clause 4.16 (in-service information feedback,
launch-site procedures and monitoring of explosive subsystems and devices).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Track age against shelf life and surveillance interval in whole days, and
   decide the disposition of an item: serviceable, surveillance due, life
   extension needed, or expired.
2. Propagate an in-service anomaly across the inventory: every item sharing the
   failed item's explosive batch owes an impact assessment, and a design-rooted
   anomaly reaches every item of the same build standard as well.
3. Validate a launch-site procedure as an ordered sequence, checking the
   precedence rules that keep an item inert until the area is clear and the
   crew has left.
4. Summarise the monitoring record into excursion count and accumulated
   excursion hours, and decide whether the accumulated exposure has used up the
   allowance and forces a return to qualification.
"""

import math

__all__ = [
    "HOUR_TOLERANCE",
    "KNOWN_ACTIONS",
    "HAZARDOUS_ACTIONS",
    "PRECEDENCE_RULES",
    "validate_day",
    "validate_non_negative",
    "remaining_shelf_life_days",
    "surveillance_status",
    "life_disposition",
    "impacted_items",
    "validate_launch_sequence",
    "excursion_summary",
    "requalification_decision",
    "assess_in_service",
]

# Accumulated hours are a sum of floats; absorb the representation error at the
# comparison rather than padding the allowance.
HOUR_TOLERANCE = 1e-9

# Launch-site actions this procedure model understands.
KNOWN_ACTIONS = (
    "area-clear",
    "measure-bridge-resistance",
    "connect-initiation-circuit",
    "remove-safing-device",
    "arm",
    "fire",
)

# Actions after which the item can no longer be treated as inert.
HAZARDOUS_ACTIONS = frozenset({"remove-safing-device", "arm", "fire"})

# (earlier, later) pairs the sequence has to respect.
PRECEDENCE_RULES = (
    ("area-clear", "remove-safing-device"),
    ("measure-bridge-resistance", "remove-safing-device"),
    ("connect-initiation-circuit", "remove-safing-device"),
    ("remove-safing-device", "arm"),
    ("arm", "fire"),
)


def validate_day(label, value):
    """Return value as a whole-day index."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer day index, got %r" % (label, value))
    return value


def validate_non_negative(label, value):
    """Return value as a non-negative finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def remaining_shelf_life_days(manufacture_day, today_day, shelf_life_days):
    """Return the days of declared shelf life left, negative once it is spent."""
    made = validate_day("manufacture_day", manufacture_day)
    today = validate_day("today_day", today_day)
    life = validate_day("shelf_life_days", shelf_life_days)
    if life <= 0:
        raise ValueError("shelf_life_days must be positive, got %d" % life)
    if today < made:
        raise ValueError("today_day %d precedes manufacture_day %d" % (today, made))
    return made + life - today


def surveillance_status(last_surveillance_day, today_day, interval_days):
    """Return how many days are left before the next surveillance test is owed."""
    last = validate_day("last_surveillance_day", last_surveillance_day)
    today = validate_day("today_day", today_day)
    interval = validate_day("interval_days", interval_days)
    if interval <= 0:
        raise ValueError("interval_days must be positive, got %d" % interval)
    if today < last:
        raise ValueError("today_day %d precedes last_surveillance_day %d" % (today, last))
    days_left = last + interval - today
    return {
        "days_to_next_surveillance": days_left,
        "due": days_left <= 0,
    }


def life_disposition(remaining_days, days_to_next_surveillance, life_extension_approved=False):
    """Decide what may be done with an item given its age and surveillance state."""
    for label, value in (
        ("remaining_days", remaining_days),
        ("days_to_next_surveillance", days_to_next_surveillance),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (label, value))
    if not isinstance(life_extension_approved, bool):
        raise ValueError("life_extension_approved must be a boolean")
    findings = []
    if remaining_days <= 0 and not life_extension_approved:
        state = "expired"
        findings.append(
            "declared shelf life spent by %d day(s) with no approved extension"
            % abs(remaining_days)
        )
    elif remaining_days <= 0:
        state = "life-extended"
    elif days_to_next_surveillance <= 0:
        state = "surveillance-due"
        findings.append(
            "surveillance test overdue by %d day(s)" % abs(days_to_next_surveillance)
        )
    else:
        state = "serviceable"
    return {
        "state": state,
        "remaining_days": remaining_days,
        "days_to_next_surveillance": days_to_next_surveillance,
        "usable": state in ("serviceable", "life-extended"),
        "findings": findings,
    }


def impacted_items(anomaly, inventory):
    """Return the inventory items an in-service anomaly reaches."""
    if not isinstance(anomaly, dict):
        raise ValueError("anomaly must be a mapping")
    for key in ("item_id", "explosive_batch", "build_standard", "design_rooted"):
        if key not in anomaly:
            raise ValueError("anomaly missing '%s'" % key)
    if not isinstance(anomaly["design_rooted"], bool):
        raise ValueError("anomaly['design_rooted'] must be a boolean")
    for key in ("item_id", "explosive_batch", "build_standard"):
        if not isinstance(anomaly[key], str) or not anomaly[key].strip():
            raise ValueError("anomaly['%s'] must be a non-empty string" % key)
    if not isinstance(inventory, (list, tuple)):
        raise ValueError("inventory must be a sequence of item mappings")
    batch = anomaly["explosive_batch"].strip()
    build = anomaly["build_standard"].strip()
    reached = []
    for index, unit in enumerate(inventory):
        if not isinstance(unit, dict):
            raise ValueError("inventory[%d] must be a mapping" % index)
        for key in ("item_id", "explosive_batch", "build_standard"):
            if key not in unit:
                raise ValueError("inventory[%d] missing '%s'" % (index, key))
            if not isinstance(unit[key], str) or not unit[key].strip():
                raise ValueError("inventory[%d]['%s'] must be a non-empty string" % (index, key))
        reasons = []
        if unit["explosive_batch"].strip() == batch:
            reasons.append("same explosive batch")
        if anomaly["design_rooted"] and unit["build_standard"].strip() == build:
            reasons.append("same build standard as a design-rooted anomaly")
        if reasons:
            reached.append({"item_id": unit["item_id"].strip(), "reasons": reasons})
    return {
        "anomaly_item": anomaly["item_id"].strip(),
        "impacted": reached,
        "impacted_count": len(reached),
        "quarantine_required": bool(reached),
    }


def validate_launch_sequence(steps):
    """Validate an ordered launch-site procedure against its precedence rules."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("steps must be a non-empty sequence of step mappings")
    seen_ids = set()
    normalized = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError("steps[%d] must be a mapping" % index)
        for key in ("step_id", "action", "personnel"):
            if key not in step:
                raise ValueError("steps[%d] missing '%s'" % (index, key))
        step_id = step["step_id"]
        if not isinstance(step_id, str) or not step_id.strip():
            raise ValueError("steps[%d]['step_id'] must be a non-empty string" % index)
        step_id = step_id.strip()
        if step_id in seen_ids:
            raise ValueError("duplicate step_id %r" % step_id)
        seen_ids.add(step_id)
        action = step["action"]
        if not isinstance(action, str):
            raise ValueError("steps[%d]['action'] must be a string" % index)
        action = action.strip().lower().replace(" ", "-").replace("_", "-")
        if action not in KNOWN_ACTIONS:
            raise ValueError(
                "unknown launch-site action %r; known actions are %s"
                % (step["action"], ", ".join(KNOWN_ACTIONS))
            )
        personnel = step["personnel"]
        if not isinstance(personnel, int) or isinstance(personnel, bool) or personnel < 0:
            raise ValueError("steps[%d]['personnel'] must be a non-negative integer" % index)
        normalized.append({"step_id": step_id, "action": action, "personnel": personnel})
    positions = {}
    for position, step in enumerate(normalized):
        positions.setdefault(step["action"], position)
    findings = []
    for earlier, later in PRECEDENCE_RULES:
        if earlier in positions and later in positions:
            if positions[earlier] > positions[later]:
                findings.append(
                    "'%s' is scheduled after '%s'" % (earlier, later)
                )
        elif later in positions and earlier not in positions:
            findings.append("'%s' is scheduled without a preceding '%s'" % (later, earlier))
    if "fire" in positions and positions["fire"] != len(normalized) - 1:
        findings.append("'fire' is not the last step of the procedure")
    disarm_point = positions.get("remove-safing-device")
    if disarm_point is not None:
        for step in normalized[disarm_point:]:
            if step["action"] in HAZARDOUS_ACTIONS and step["personnel"] < 2:
                findings.append(
                    "step %s ('%s') is staffed by %d person(s); a hazardous step needs two"
                    % (step["step_id"], step["action"], step["personnel"])
                )
    return {
        "steps": normalized,
        "actions": [step["action"] for step in normalized],
        "valid": not findings,
        "findings": findings,
    }


def excursion_summary(records, limits):
    """Summarise a monitoring record into excursion count and accumulated hours."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of record mappings")
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping")
    for key in ("temperature_min_c", "temperature_max_c"):
        if key not in limits:
            raise ValueError("limits missing '%s'" % key)
        if not isinstance(limits[key], (int, float)) or isinstance(limits[key], bool):
            raise ValueError("limits['%s'] must be a real number" % key)
    t_min = float(limits["temperature_min_c"])
    t_max = float(limits["temperature_max_c"])
    if t_min > t_max:
        raise ValueError("limits temperature range is inverted")
    hours = 0.0
    excursions = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("records[%d] must be a mapping" % index)
        for key in ("day", "temperature_c", "duration_h"):
            if key not in record:
                raise ValueError("records[%d] missing '%s'" % (index, key))
        day = validate_day("records[%d]['day']" % index, record["day"])
        temperature = record["temperature_c"]
        if not isinstance(temperature, (int, float)) or isinstance(temperature, bool):
            raise ValueError("records[%d]['temperature_c'] must be a real number" % index)
        temperature = float(temperature)
        if not math.isfinite(temperature):
            raise ValueError("records[%d]['temperature_c'] must be finite" % index)
        duration = validate_non_negative("records[%d]['duration_h']" % index, record["duration_h"])
        above = temperature > t_max and not math.isclose(
            temperature, t_max, rel_tol=0.0, abs_tol=HOUR_TOLERANCE
        )
        below = temperature < t_min and not math.isclose(
            temperature, t_min, rel_tol=0.0, abs_tol=HOUR_TOLERANCE
        )
        if above or below:
            hours += duration
            excursions.append(
                {
                    "day": day,
                    "temperature_c": temperature,
                    "duration_h": duration,
                    "direction": "above" if above else "below",
                }
            )
    return {
        "records_reviewed": len(records),
        "excursions": excursions,
        "excursion_count": len(excursions),
        "accumulated_hours": hours,
    }


def requalification_decision(summary, allowance_h):
    """Decide whether accumulated excursion exposure forces a return to qualification."""
    if not isinstance(summary, dict) or "accumulated_hours" not in summary:
        raise ValueError("summary must be a mapping carrying 'accumulated_hours'")
    allowance = validate_non_negative("allowance_h", allowance_h)
    accumulated = validate_non_negative("accumulated_hours", summary["accumulated_hours"])
    over = accumulated > allowance and not math.isclose(
        accumulated, allowance, rel_tol=HOUR_TOLERANCE, abs_tol=0.0
    )
    findings = []
    if over:
        findings.append(
            "accumulated excursion exposure %.6g h exceeds the %.6g h allowance"
            % (accumulated, allowance)
        )
    return {
        "accumulated_hours": accumulated,
        "allowance_h": allowance,
        "requalification_required": over,
        "findings": findings,
    }


def assess_in_service(spec):
    """Run the full clause 4.16 in-service, launch-site and monitoring assessment.

    spec keys: item (manufacture_day, shelf_life_days, last_surveillance_day,
    surveillance_interval_days, optional life_extension_approved), today_day,
    optional anomaly and inventory, launch_sequence, monitoring (records,
    limits, allowance_h).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("item", "today_day"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    item = spec["item"]
    if not isinstance(item, dict):
        raise ValueError("spec['item'] must be a mapping")
    for key in ("manufacture_day", "shelf_life_days", "last_surveillance_day",
                "surveillance_interval_days"):
        if key not in item:
            raise ValueError("spec['item'] missing '%s'" % key)
    today = validate_day("today_day", spec["today_day"])
    remaining = remaining_shelf_life_days(
        item["manufacture_day"], today, item["shelf_life_days"]
    )
    surveillance = surveillance_status(
        item["last_surveillance_day"], today, item["surveillance_interval_days"]
    )
    disposition = life_disposition(
        remaining,
        surveillance["days_to_next_surveillance"],
        bool(item.get("life_extension_approved", False)),
    )
    feedback = None
    if "anomaly" in spec:
        feedback = impacted_items(spec["anomaly"], spec.get("inventory") or [])
    sequence = None
    if "launch_sequence" in spec:
        sequence = validate_launch_sequence(spec["launch_sequence"])
    monitoring = None
    requalification = None
    if "monitoring" in spec:
        block = spec["monitoring"]
        if not isinstance(block, dict):
            raise ValueError("spec['monitoring'] must be a mapping")
        for key in ("records", "limits", "allowance_h"):
            if key not in block:
                raise ValueError("spec['monitoring'] missing '%s'" % key)
        monitoring = excursion_summary(block["records"], block["limits"])
        requalification = requalification_decision(monitoring, block["allowance_h"])
    findings = list(disposition["findings"])
    if sequence is not None:
        findings.extend(sequence["findings"])
    if requalification is not None:
        findings.extend(requalification["findings"])
    if feedback is not None and feedback["quarantine_required"]:
        findings.append(
            "anomaly on %s reaches %d other item(s); quarantine and assess them"
            % (feedback["anomaly_item"], feedback["impacted_count"])
        )
    return {
        "disposition": disposition,
        "surveillance": surveillance,
        "feedback": feedback,
        "launch_sequence": sequence,
        "monitoring": monitoring,
        "requalification": requalification,
        "clear_to_use": not findings,
        "findings": findings,
    }
