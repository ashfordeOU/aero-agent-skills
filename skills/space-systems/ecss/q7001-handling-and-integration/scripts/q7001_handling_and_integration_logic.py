"""Clean handling and integration of exposed flight hardware.

Anchor: the handling and integration provisions of the contamination
and cleanliness control practice of ECSS-Q-ST-70-01C (paraphrased into
an implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. An uncovered sensitive surface accumulates fallout for as long as it
   is uncovered. The rate follows the airborne concentration around it
   and the way the surface faces, so exposure is a budget to be spent
   deliberately rather than a consequence of how long the shift ran.
2. Orientation is a design variable, not an accident of the trolley. A
   surface facing up collects what settles; the same surface turned
   vertical or facing down collects a fraction of it, and choosing the
   orientation is usually cheaper than choosing a cleaner room.
3. Gloves are consumables with a contact count. Transfer rises as a
   pair is used, so the number of pairs a task needs follows from the
   contacts it makes, and any contact with a non-clean surface ends
   that pair immediately whatever the count says.
4. Covers exist to shrink the exposure window. An aperture cover
   removed at the start of a shift for a task that needs ten minutes
   spends the whole allocation for nothing, and nothing in the record
   afterwards shows where the budget went.
5. Tooling enters the same way materials do: with a cleaning record, and
   with a lubricant that is approved for use near the surface. A tool
   that is clean but carries an unapproved lubricant is the more common
   of the two failures and the harder to see.

Stdlib only, offline, deterministic.
"""

import math

# How the way a surface faces scales what settles on it.
ORIENTATION_FACTOR = {
    "facing-up": 1.0,
    "vertical": 0.30,
    "facing-down": 0.05,
}

# Obscuration added per hour, per airborne particle per cubic metre, on
# an upward-facing surface. The model is declared here so a reviewer can
# argue with one number instead of an undocumented chain.
DEPOSITION_COEFFICIENT_PCT_PER_HOUR = 1.0e-7

# Contacts a glove pair is good for before transfer rises.
DEFAULT_CONTACTS_PER_GLOVE_PAIR = 25

# Class-designation relation constants, repeated so the leaf stands alone.
SIZE_REFERENCE_UM = 0.1
SIZE_EXPONENT = 2.08
DEFAULT_THRESHOLD_UM = 0.5

# A planned exposure landing exactly on its allocation is inside it.
RELATIVE_TOLERANCE = 1.0e-12


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return " ".join(value.split())


def _positive(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return float(value)


def _non_negative(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return float(value)


def _non_negative_int(label, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative integer, got %r" % (label, value))
    return value


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def orientation_factor(orientation):
    """Scaling the way a surface faces applies to what settles on it."""
    name = _text("orientation", orientation)
    if name not in ORIENTATION_FACTOR:
        raise ValueError(
            "orientation %r is not one of %r" % (name, sorted(ORIENTATION_FACTOR))
        )
    return ORIENTATION_FACTOR[name]


def area_concentration_per_m3(iso_class, threshold_um=DEFAULT_THRESHOLD_UM):
    """Airborne concentration to plan against for a clean-area class."""
    if not isinstance(iso_class, (int, float)) or isinstance(iso_class, bool):
        raise ValueError("class designation must be numeric, got %r" % (iso_class,))
    if iso_class < 1 or iso_class > 9:
        raise ValueError("class designation %r lies outside 1..9" % (iso_class,))
    size = _positive("threshold particle size", threshold_um)
    return (10.0 ** float(iso_class)) * ((SIZE_REFERENCE_UM / size) ** SIZE_EXPONENT)


def fallout_rate_pct_per_hour(concentration_per_m3, orientation,
                              coefficient=DEPOSITION_COEFFICIENT_PCT_PER_HOUR):
    """Obscuration added per hour on a surface facing a given way."""
    concentration = _non_negative("concentration_per_m3", concentration_per_m3)
    factor = orientation_factor(orientation)
    coeff = _positive("coefficient", coefficient)
    return coeff * concentration * factor


def accumulated_obscuration_pct(rate_pct_per_hour, exposure_hours):
    """Obscuration a surface picks up over an uncovered interval."""
    rate = _non_negative("rate_pct_per_hour", rate_pct_per_hour)
    hours = _non_negative("exposure_hours", exposure_hours)
    return rate * hours


def affordable_exposure_hours(allocation_pct, rate_pct_per_hour):
    """Hours of exposure the obscuration allocation pays for."""
    allocation = _positive("allocation_pct", allocation_pct)
    rate = _non_negative("rate_pct_per_hour", rate_pct_per_hour)
    if rate == 0.0:
        return float("inf")
    return allocation / rate


def required_glove_pairs(contacts, contacts_per_pair=DEFAULT_CONTACTS_PER_GLOVE_PAIR,
                         non_clean_contacts=0):
    """Glove pairs a task needs from its contact count."""
    total = _non_negative_int("contacts", contacts)
    per_pair = contacts_per_pair
    if not isinstance(per_pair, int) or isinstance(per_pair, bool) or per_pair < 1:
        raise ValueError(
            "contacts_per_pair must be a positive integer, got %r" % (contacts_per_pair,)
        )
    spoiled = _non_negative_int("non_clean_contacts", non_clean_contacts)
    if spoiled > total:
        raise ValueError(
            "non_clean_contacts %r exceeds the total contact count %r"
            % (non_clean_contacts, contacts)
        )
    if total == 0:
        return 1
    from_wear = int(math.ceil(total / float(per_pair)))
    return max(1, from_wear) + spoiled


def assess_tooling(tools, approved_lubricants):
    """Name the tools with no cleaning record and the unapproved lubricants."""
    if not isinstance(tools, list):
        raise ValueError("tools must be a list")
    approved = {
        _text("approved lubricant", name) for name in (approved_lubricants or [])
    }
    unrecorded = []
    unapproved = []
    seen = set()
    for tool in tools:
        if not isinstance(tool, dict):
            raise ValueError("tool must be a mapping")
        tid = _text("tool id", tool.get("id"))
        if tid in seen:
            raise ValueError("duplicate tool id %r" % (tid,))
        seen.add(tid)
        record = tool.get("cleaning_record")
        if record is None or not str(record).strip():
            unrecorded.append(tid)
        lubricant = tool.get("lubricant")
        if lubricant is not None:
            name = _text("tool %s lubricant" % tid, lubricant)
            if name not in approved:
                unapproved.append({"tool_id": tid, "lubricant": name})
    return {
        "tools_without_a_cleaning_record": sorted(unrecorded),
        "unapproved_lubricants": sorted(unapproved, key=lambda row: row["tool_id"]),
    }


def assess_handling_operation(operation, area):
    """Grade a handling or integration operation against its fallout budget."""
    if not isinstance(operation, dict):
        raise ValueError("operation must be a mapping")
    if not isinstance(area, dict):
        raise ValueError("area must be a mapping")
    op_id = _text("operation id", operation.get("id"))
    orientation = _text("operation orientation", operation.get("orientation"))
    allocation = _positive(
        "operation obscuration_allocation_pct",
        operation.get("obscuration_allocation_pct"),
    )
    planned_hours = _non_negative(
        "operation planned_exposure_hours", operation.get("planned_exposure_hours")
    )
    cover_open_hours = _non_negative(
        "operation cover_open_hours",
        operation.get("cover_open_hours", planned_hours),
    )
    contacts = _non_negative_int("operation contacts", operation.get("contacts", 0))
    non_clean = _non_negative_int(
        "operation non_clean_contacts", operation.get("non_clean_contacts", 0)
    )
    planned_pairs = _non_negative_int(
        "operation planned_glove_pairs", operation.get("planned_glove_pairs", 1)
    )
    per_pair = operation.get("contacts_per_glove_pair", DEFAULT_CONTACTS_PER_GLOVE_PAIR)
    required_class = operation.get("required_area_class")

    if "particle_concentration_per_m3" in area:
        concentration = _non_negative(
            "area particle_concentration_per_m3",
            area.get("particle_concentration_per_m3"),
        )
    else:
        concentration = area_concentration_per_m3(
            area.get("iso_class"), area.get("threshold_um", DEFAULT_THRESHOLD_UM)
        )

    coefficient = _positive(
        "deposition coefficient",
        area.get("deposition_coefficient", DEPOSITION_COEFFICIENT_PCT_PER_HOUR),
    )
    rate = fallout_rate_pct_per_hour(concentration, orientation, coefficient)
    affordable = affordable_exposure_hours(allocation, rate)
    accumulated = accumulated_obscuration_pct(rate, cover_open_hours)

    findings = []
    if cover_open_hours > affordable * (1.0 + RELATIVE_TOLERANCE):
        findings.append("uncovered-time-longer-than-the-fallout-allocation-pays-for")
    if cover_open_hours > planned_hours * (1.0 + RELATIVE_TOLERANCE):
        findings.append("aperture-left-open-outside-the-task-that-needed-it")
    if orientation == "facing-up" and cover_open_hours > 0.0:
        findings.append("sensitive-surface-left-facing-up-while-uncovered")

    pairs_needed = required_glove_pairs(contacts, per_pair, non_clean)
    if planned_pairs < pairs_needed:
        findings.append("fewer-glove-pairs-planned-than-the-contact-count-needs")

    tooling = assess_tooling(
        operation.get("tools", []), operation.get("approved_lubricants", [])
    )
    if tooling["tools_without_a_cleaning_record"]:
        findings.append("tool-used-with-no-cleaning-record")
    if tooling["unapproved_lubricants"]:
        findings.append("unapproved-lubricant-on-a-tool-near-a-sensitive-surface")

    if required_class is not None:
        if not isinstance(required_class, int) or isinstance(required_class, bool):
            raise ValueError("required_area_class must be an integer class")
        area_class = area.get("iso_class")
        if area_class is None:
            findings.append("handling-area-class-not-recorded")
        else:
            if not isinstance(area_class, int) or isinstance(area_class, bool):
                raise ValueError("area iso_class must be an integer class")
            if area_class > required_class:
                findings.append("handling-in-an-area-dirtier-than-the-operation-needs")

    return {
        "operation_id": op_id,
        "orientation": orientation,
        "orientation_factor": orientation_factor(orientation),
        "concentration_per_m3": concentration,
        "fallout_rate_pct_per_hour": rate,
        "obscuration_allocation_pct": allocation,
        "affordable_exposure_hours": affordable,
        "planned_exposure_hours": planned_hours,
        "cover_open_hours": cover_open_hours,
        "accumulated_obscuration_pct": accumulated,
        "allocation_utilization_fraction": accumulated / allocation,
        "glove_pairs_needed": pairs_needed,
        "glove_pairs_planned": planned_pairs,
        "tooling": tooling,
        "findings": findings,
        "verdict": "handling-plan-acceptable" if not findings else "handling-plan-rejected",
        "clear": not findings,
    }
