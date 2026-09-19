"""Keeping a clean area under control while work is actually happening.

Anchor: the clean-area operating provisions of the contamination and
cleanliness control practice of ECSS-Q-ST-70-01C (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. People are the dominant particle source in an occupied clean area,
   and the rate depends on what they are doing far more than on who
   they are. Standing still, working with the hands and moving about
   differ by orders of magnitude, so a session is sized on the activity
   mix, not on a headcount alone.
2. Dilution is what removes the particles. The supply is filtered, so
   the room reaches a steady state where the occupants' generation
   equals the volumetric removal: concentration is generation divided by
   the volume flow the air change rate and the room volume produce.
   Inverting that gives the occupancy the room can actually carry at its
   class, which is usually lower than the occupancy the floor area
   suggests.
3. Gowning is graded against the class, not against habit. A garment
   set adequate for a looser class is a shortfall in a cleaner one, and
   the shortfall is named garment by garment so it can be fixed at the
   airlock rather than argued about afterwards.
4. Materials and tools are screened at the boundary. Fibre-shedding and
   abrading items are refused outright, and a tool with no cleaning
   record is refused whatever it looks like, because the record is the
   only evidence that survives the session.
5. Traffic discipline is part of the class. An interlock defeated so a
   trolley can be pushed through, or a transit rate above what the
   airlock was sized for, unfilters the room for as long as it lasts.

Stdlib only, offline, deterministic.
"""

import math

# Particles of at least half a micron released per second by one gowned
# occupant, by what that occupant is doing.
ACTIVITY_EMISSION_PER_S = {
    "still": 1.0e5,
    "seated-hand-work": 5.0e5,
    "standing-hand-work": 1.0e6,
    "walking": 2.5e6,
    "heavy-movement": 1.0e7,
}

# Garment sets by class band, cleanest first. A class is graded against
# the first band whose ceiling it does not exceed.
GOWNING_BY_CLASS_BAND = (
    (5, frozenset({"coverall", "hood", "face-cover", "boots", "gloves", "goggles"})),
    (6, frozenset({"coverall", "hood", "face-cover", "boots", "gloves"})),
    (7, frozenset({"coverall", "hood", "boots", "gloves"})),
    (9, frozenset({"coat", "hair-cover", "overshoes", "gloves"})),
)

# Items refused at the boundary of a clean area.
DEFAULT_REFUSED_MATERIALS = frozenset(
    {
        "cardboard",
        "wood",
        "standard-paper",
        "pencil",
        "eraser",
        "untreated-foam",
        "abrasive-cloth",
    }
)

# Class-designation relation constants, repeated here so the leaf stands
# alone: ceiling = 10**class * (0.1 / size)**2.08 per cubic metre.
SIZE_REFERENCE_UM = 0.1
SIZE_EXPONENT = 2.08
DEFAULT_THRESHOLD_UM = 0.5

SECONDS_PER_HOUR = 3600.0

# A concentration sitting exactly on a class ceiling is inside it.
RELATIVE_TOLERANCE = 1.0e-9


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


def _non_negative_int(label, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative integer, got %r" % (label, value))
    return value


def class_ceiling_per_m3(iso_class, threshold_um=DEFAULT_THRESHOLD_UM):
    """Concentration ceiling of a class at a threshold particle size."""
    if not isinstance(iso_class, (int, float)) or isinstance(iso_class, bool):
        raise ValueError("class designation must be numeric, got %r" % (iso_class,))
    if iso_class < 1 or iso_class > 9:
        raise ValueError("class designation %r lies outside 1..9" % (iso_class,))
    size = _positive("threshold particle size", threshold_um)
    return (10.0 ** float(iso_class)) * ((SIZE_REFERENCE_UM / size) ** SIZE_EXPONENT)


def required_gowning(iso_class):
    """Garment set a class demands, as a frozen set of garment names."""
    if not isinstance(iso_class, (int, float)) or isinstance(iso_class, bool):
        raise ValueError("class designation must be numeric, got %r" % (iso_class,))
    if iso_class < 1 or iso_class > 9:
        raise ValueError("class designation %r lies outside 1..9" % (iso_class,))
    for ceiling, garments in GOWNING_BY_CLASS_BAND:
        if iso_class <= ceiling:
            return garments
    return GOWNING_BY_CLASS_BAND[-1][1]


def removal_flow_m3_per_s(air_changes_per_hour, volume_m3):
    """Volume flow the air change rate produces in the room, per second."""
    ach = _positive("air_changes_per_hour", air_changes_per_hour)
    volume = _positive("volume_m3", volume_m3)
    return ach * volume / SECONDS_PER_HOUR


def occupant_generation_per_s(occupants):
    """Total particle generation of a list of occupants, per second."""
    if not isinstance(occupants, list) or not occupants:
        raise ValueError("occupants must be a non-empty list")
    total = 0.0
    for occupant in occupants:
        if not isinstance(occupant, dict):
            raise ValueError("occupant must be a mapping")
        oid = _text("occupant id", occupant.get("id"))
        activity = _text("occupant %s activity" % oid, occupant.get("activity"))
        if activity not in ACTIVITY_EMISSION_PER_S:
            raise ValueError(
                "occupant %s declares activity %r, which is not one of %r"
                % (oid, activity, sorted(ACTIVITY_EMISSION_PER_S))
            )
        total += ACTIVITY_EMISSION_PER_S[activity]
    return total


def steady_state_concentration_per_m3(generation_per_s, air_changes_per_hour, volume_m3):
    """Concentration the room settles at for a sustained generation rate."""
    generation = generation_per_s
    if not isinstance(generation, (int, float)) or isinstance(generation, bool):
        raise ValueError("generation_per_s must be numeric, got %r" % (generation,))
    if generation < 0:
        raise ValueError("generation_per_s must be non-negative, got %r" % (generation,))
    return float(generation) / removal_flow_m3_per_s(air_changes_per_hour, volume_m3)


def supported_occupancy(iso_class, activity, air_changes_per_hour, volume_m3,
                        threshold_um=DEFAULT_THRESHOLD_UM, safety_factor=2.0):
    """How many occupants at one activity the room holds inside its class."""
    activity = _text("activity", activity)
    if activity not in ACTIVITY_EMISSION_PER_S:
        raise ValueError(
            "activity %r is not one of %r" % (activity, sorted(ACTIVITY_EMISSION_PER_S))
        )
    factor = _positive("safety_factor", safety_factor)
    if factor < 1.0:
        raise ValueError("safety_factor must be at least 1, got %r" % (safety_factor,))
    ceiling = class_ceiling_per_m3(iso_class, threshold_um)
    flow = removal_flow_m3_per_s(air_changes_per_hour, volume_m3)
    allowable_generation = ceiling * flow / factor
    return int(math.floor(allowable_generation / ACTIVITY_EMISSION_PER_S[activity]))


def assess_gowning(occupants, iso_class):
    """Name, per occupant, the garments the class demands and they lack."""
    required = required_gowning(iso_class)
    shortfalls = []
    for occupant in occupants:
        oid = _text("occupant id", occupant.get("id"))
        worn = occupant.get("gowning", [])
        if not isinstance(worn, (list, tuple, set, frozenset)):
            raise ValueError("occupant %s gowning must be a list of garments" % oid)
        worn_set = {_text("occupant %s garment" % oid, item) for item in worn}
        missing = sorted(required - worn_set)
        if missing:
            shortfalls.append({"occupant_id": oid, "missing_garments": missing})
    return shortfalls


def assess_operational_control(area, session):
    """Grade one clean-area work session against the class the area holds."""
    if not isinstance(area, dict):
        raise ValueError("area must be a mapping")
    if not isinstance(session, dict):
        raise ValueError("session must be a mapping")
    area_id = _text("area id", area.get("id"))
    iso_class = area.get("iso_class")
    ceiling = class_ceiling_per_m3(iso_class, area.get("threshold_um", DEFAULT_THRESHOLD_UM))
    volume = _positive("area %s volume_m3" % area_id, area.get("volume_m3"))
    ach = _positive(
        "area %s air_changes_per_hour" % area_id, area.get("air_changes_per_hour")
    )
    transit_ceiling = _positive(
        "area %s transit_ceiling_per_hour" % area_id,
        area.get("transit_ceiling_per_hour", 12.0),
    )

    occupants = session.get("occupants")
    if not isinstance(occupants, list) or not occupants:
        raise ValueError("session must list at least one occupant")
    ids = set()
    for occupant in occupants:
        if not isinstance(occupant, dict):
            raise ValueError("occupant must be a mapping")
        oid = _text("occupant id", occupant.get("id"))
        if oid in ids:
            raise ValueError("duplicate occupant id %r" % (oid,))
        ids.add(oid)

    findings = []
    generation = occupant_generation_per_s(occupants)
    concentration = steady_state_concentration_per_m3(generation, ach, volume)
    if concentration > ceiling * (1.0 + RELATIVE_TOLERANCE):
        findings.append("predicted-working-concentration-above-the-class-ceiling")

    shortfalls = assess_gowning(occupants, iso_class)
    if shortfalls:
        findings.append("gowning-short-of-what-the-class-demands")

    refused = set(session.get("refused_materials", DEFAULT_REFUSED_MATERIALS))
    materials = session.get("materials", [])
    if not isinstance(materials, list):
        raise ValueError("session materials must be a list")
    refused_present = sorted(
        {
            _text("material", item)
            for item in materials
            if _text("material", item) in refused
        }
    )
    if refused_present:
        findings.append("material-not-permitted-in-the-clean-area")

    tools = session.get("tools", [])
    if not isinstance(tools, list):
        raise ValueError("session tools must be a list")
    uncertified = []
    for tool in tools:
        if not isinstance(tool, dict):
            raise ValueError("tool must be a mapping")
        tid = _text("tool id", tool.get("id"))
        record = tool.get("cleaning_record")
        if record is None or not str(record).strip():
            uncertified.append(tid)
    if uncertified:
        findings.append("tool-admitted-with-no-cleaning-record")

    interlock = session.get("airlock_interlock_respected", True)
    if not isinstance(interlock, bool):
        raise ValueError("airlock_interlock_respected must be a boolean")
    if not interlock:
        findings.append("airlock-interlock-defeated-during-the-session")

    transits = _non_negative_int(
        "session transits_per_hour", session.get("transits_per_hour", 0)
    )
    if transits > transit_ceiling:
        findings.append("transit-rate-above-what-the-airlock-was-sized-for")

    activity_mix = sorted({occupant["activity"] for occupant in occupants})
    heaviest = max(occupants, key=lambda o: ACTIVITY_EMISSION_PER_S[o["activity"]])
    capacity = supported_occupancy(
        iso_class,
        heaviest["activity"],
        ach,
        volume,
        area.get("threshold_um", DEFAULT_THRESHOLD_UM),
        session.get("safety_factor", 2.0),
    )
    if len(occupants) > capacity:
        findings.append("headcount-above-the-occupancy-the-ventilation-supports")

    return {
        "area_id": area_id,
        "iso_class": iso_class,
        "class_ceiling_per_m3": ceiling,
        "removal_flow_m3_per_s": removal_flow_m3_per_s(ach, volume),
        "occupant_count": len(occupants),
        "activity_mix": activity_mix,
        "generation_per_s": generation,
        "predicted_concentration_per_m3": concentration,
        "class_utilization_fraction": concentration / ceiling,
        "supported_occupancy_at_heaviest_activity": capacity,
        "gowning_shortfalls": shortfalls,
        "refused_materials_present": refused_present,
        "tools_without_a_cleaning_record": sorted(uncertified),
        "transits_per_hour": transits,
        "findings": findings,
        "verdict": "session-under-control" if not findings else "session-not-under-control",
        "clear": not findings,
    }
