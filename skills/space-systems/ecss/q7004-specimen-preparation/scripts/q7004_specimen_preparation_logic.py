#!/usr/bin/env python3
"""Specimen preparation for an ECSS thermal test campaign.

Anchor: ECSS-Q-ST-70-04C, test item preparation clauses. The procedure
below is a paraphrase into implementable steps; no standard text is
reproduced.

Preparation settles four things before a chamber door closes.

How many specimens. The objective fixes how many go through the run, the
item category fixes how many stay uncycled as the reference the retained
property is measured against, and a spare fraction covers handling loss.
A destructive post-test measurement consumes the cycled specimens, so the
references cannot be recovered from them afterwards.

Where the sensors go. An instrumented unit carries one sensor per thermal
zone, a redundant sensor on the zone that controls the run, and one
reference sensor on the fixture. The controlling zone is the slowest one,
because a profile controlled on a fast-responding zone leaves the slow
one short of the level it was supposed to reach.

How long the bake-out lasts. Absorbed volatiles leave a slab by
diffusion, and the late stage of that desorption is well described by the
first term of the series solution, so a target removal fraction, a
diffusivity and a half-thickness give a duration rather than a habit.

What is recorded first. Identification, a dimensional and mass baseline,
cleaning, conditioning and a pre-test inspection, in that order, because
a baseline taken after cleaning cannot be compared with a post-test
reading taken after the same cleaning was skipped.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MATERIAL = "material"
PROCESS = "process"
MECHANICAL_PART = "mechanical-part"
ASSEMBLY = "assembly"
ITEM_CATEGORIES = (MATERIAL, PROCESS, MECHANICAL_PART, ASSEMBLY)

SCREENING = "screening"
QUALIFICATION = "qualification"
ACCEPTANCE_VERIFICATION = "acceptance-verification"
OBJECTIVES = (SCREENING, QUALIFICATION, ACCEPTANCE_VERIFICATION)

# The one-term series solution for desorption from a slab only describes
# the late stage of the process; below this removed fraction it is not a
# usable model and a measured drying curve is owed instead.
MIN_ONE_TERM_REMOVAL_FRACTION = 0.5

DEFAULT_PREPARATION_POLICY = {
    "cycled_specimens": {
        SCREENING: 3,
        QUALIFICATION: 5,
        ACCEPTANCE_VERIFICATION: 2,
    },
    "reference_specimens": {
        MATERIAL: 1,
        PROCESS: 1,
        MECHANICAL_PART: 1,
        ASSEMBLY: 0,
    },
    "max_spare_fraction": 1.0,
}


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def validate_preparation_policy(policy):
    """Check a preparation policy covers every objective and category."""
    _require_mapping("policy", policy)
    cycled = _require_mapping("policy cycled_specimens", policy.get("cycled_specimens"))
    missing = set(OBJECTIVES) - set(cycled)
    if missing:
        raise ValueError(
            "policy cycled_specimens is missing: %s" % ", ".join(sorted(missing))
        )
    for objective in OBJECTIVES:
        count = cycled[objective]
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValueError(
                "policy cycled_specimens[%s] must be an integer of at least 1, got %r"
                % (objective, count)
            )
    references = _require_mapping(
        "policy reference_specimens", policy.get("reference_specimens")
    )
    missing = set(ITEM_CATEGORIES) - set(references)
    if missing:
        raise ValueError(
            "policy reference_specimens is missing: %s" % ", ".join(sorted(missing))
        )
    for category in ITEM_CATEGORIES:
        count = references[category]
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError(
                "policy reference_specimens[%s] must be a non-negative integer, got %r"
                % (category, count)
            )
    max_spare = _require_non_negative(
        "max_spare_fraction", policy.get("max_spare_fraction")
    )
    if max_spare > 2.0:
        raise ValueError("policy max_spare_fraction above 2.0 is not a spare policy")
    return policy


def specimen_allocation(
    category,
    objective,
    destructive_measurement=False,
    spare_fraction=0.0,
    policy=DEFAULT_PREPARATION_POLICY,
):
    """Cycled, reference and spare specimen counts the campaign has to cut."""
    validate_preparation_policy(policy)
    _require_choice("category", category, ITEM_CATEGORIES)
    _require_choice("objective", objective, OBJECTIVES)
    _require_bool("destructive_measurement", destructive_measurement)
    fraction = _require_non_negative("spare_fraction", spare_fraction)
    if fraction > policy["max_spare_fraction"]:
        raise ValueError(
            "spare_fraction %g exceeds the policy ceiling %g"
            % (fraction, policy["max_spare_fraction"])
        )
    cycled = policy["cycled_specimens"][objective]
    reference = policy["reference_specimens"][category]
    spare = int(math.ceil(cycled * fraction))
    notes = []
    if destructive_measurement and reference == 0:
        notes.append(
            "the post-test measurement is destructive and this category carries no "
            "reference specimen, so the retained property has no baseline to sit against"
        )
    if destructive_measurement and reference > 0:
        notes.append(
            "the post-test measurement is destructive, so the reference specimens are "
            "additional and are never drawn from the cycled set"
        )
    return {
        "cycled": cycled,
        "reference": reference,
        "spare": spare,
        "total": cycled + reference + spare,
        "notes": notes,
    }


def normalize_zones(zones):
    """Validate declared thermal zones and return them in a fixed order."""
    if not isinstance(zones, (list, tuple)):
        raise ValueError("zones must be a list, got %r" % (zones,))
    if not zones:
        raise ValueError("at least one thermal zone must be declared")
    seen = set()
    cleaned = []
    for zone in zones:
        _require_mapping("zone", zone)
        zone_id = zone.get("id")
        if not isinstance(zone_id, str) or not zone_id.strip():
            raise ValueError("every zone needs a non-empty string id, got %r" % (zone_id,))
        zone_id = zone_id.strip()
        if zone_id in seen:
            raise ValueError("zone id %r is declared twice" % zone_id)
        seen.add(zone_id)
        mass = _require_positive("zone %s mass_kg" % zone_id, zone.get("mass_kg"))
        cleaned.append({"id": zone_id, "mass_kg": mass})
    cleaned.sort(key=lambda z: z["id"])
    return tuple(cleaned)


def control_zone_id(zones):
    """Zone the profile is controlled on: the slowest, i.e. the heaviest.

    A tie is broken on the identifier so the choice is reproducible.
    """
    cleaned = normalize_zones(zones)
    best = cleaned[0]
    for zone in cleaned[1:]:
        if zone["mass_kg"] > best["mass_kg"]:
            best = zone
    return best["id"]


def sensor_plan(zones, instrumented=True):
    """Sensor count and placement for the specimen set."""
    _require_bool("instrumented", instrumented)
    cleaned = normalize_zones(zones)
    control = control_zone_id(cleaned)
    if not instrumented:
        return {
            "instrumented": False,
            "control_zone": control,
            "sensor_count": 2,
            "placement": (
                "fixture reference sensor beside the specimen set",
                "redundant fixture sensor",
            ),
        }
    placement = ["sensor on zone %s" % zone["id"] for zone in cleaned]
    placement.append("redundant sensor on the controlling zone %s" % control)
    placement.append("reference sensor on the fixture")
    return {
        "instrumented": True,
        "control_zone": control,
        "sensor_count": len(cleaned) + 2,
        "placement": tuple(placement),
    }


def bakeout_duration_s(half_thickness_m, diffusivity_m2_s, removal_fraction):
    """Bake-out time to remove a target fraction of the absorbed volatiles.

    Late-stage desorption from a slab of half-thickness L follows the first
    term of the series solution, so the time to reach a removed fraction F
    is -(4 L^2 / (pi^2 D)) ln((pi^2 / 8)(1 - F)).
    """
    half_thickness = _require_positive("half_thickness_m", half_thickness_m)
    diffusivity = _require_positive("diffusivity_m2_s", diffusivity_m2_s)
    fraction = _require_number("removal_fraction", removal_fraction)
    if fraction >= 1.0:
        raise ValueError(
            "removal_fraction must be below 1.0; complete removal takes unbounded time"
        )
    if fraction < MIN_ONE_TERM_REMOVAL_FRACTION:
        raise ValueError(
            "removal_fraction %g is below %g, where the one-term model does not "
            "describe the desorption; a measured drying curve is owed instead"
            % (fraction, MIN_ONE_TERM_REMOVAL_FRACTION)
        )
    time_scale = 4.0 * half_thickness * half_thickness / (math.pi * math.pi * diffusivity)
    return -time_scale * math.log((math.pi * math.pi / 8.0) * (1.0 - fraction))


def conditioning_sequence(case):
    """Ordered preparation steps for the declared specimen set."""
    _require_mapping("case", case)
    vacuum_run = _require_bool("vacuum_run", case.get("vacuum_run", False))
    moisture_sensitive = _require_bool(
        "moisture_sensitive", case.get("moisture_sensitive", False)
    )
    steps = [
        "mark every specimen with a unique identifier that survives the run",
        "record the as-received dimensional and mass baseline before any cleaning",
        "clean to the declared procedure and record the procedure used",
    ]
    if vacuum_run or moisture_sensitive:
        steps.append(
            "bake out to the computed duration and record the end-point mass"
        )
        steps.append(
            "hold in a dry enclosure from the end of the bake-out until the run"
        )
    steps.append("inspect before the run at the declared magnification and record it")
    steps.append("mount on the fixture and attach the sensors to the placement plan")
    return tuple(steps)


def prepare_specimens(case, policy=DEFAULT_PREPARATION_POLICY):
    """Full specimen preparation plan for one test item."""
    validate_preparation_policy(policy)
    _require_mapping("case", case)
    category = _require_choice(
        "item_category", case.get("item_category"), ITEM_CATEGORIES
    )
    objective = _require_choice("objective", case.get("objective"), OBJECTIVES)
    allocation = specimen_allocation(
        category,
        objective,
        bool(case.get("destructive_measurement", False)),
        case.get("spare_fraction", 0.0),
        policy,
    )
    sensors = sensor_plan(
        case.get("zones"), bool(case.get("instrumented", True))
    )
    steps = conditioning_sequence(case)
    findings = list(allocation["notes"])
    duties = []
    bakeout_s = None
    if case.get("vacuum_run") or case.get("moisture_sensitive"):
        bakeout_s = bakeout_duration_s(
            case.get("half_thickness_m"),
            case.get("diffusivity_m2_s"),
            case.get("removal_fraction"),
        )
        duties.append(
            "hold the bake-out for at least the computed duration and stop on the "
            "measured mass end point rather than on the clock alone"
        )
    if not sensors["instrumented"]:
        findings.append(
            "the specimens are not instrumented, so the profile is controlled on the "
            "fixture and the item's own lag is unmeasured"
        )
    duties.append(
        "control the profile on zone %s, the slowest zone declared"
        % sensors["control_zone"]
    )
    return {
        "item_category": category,
        "objective": objective,
        "allocation": allocation,
        "sensor_plan": sensors,
        "bakeout_duration_s": bakeout_s,
        "conditioning_steps": steps,
        "duties": duties,
        "findings": findings,
    }
