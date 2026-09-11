#!/usr/bin/env python3
"""ECSS-E-ST-10-11C §4.7.9 medical facilities and provisions assessment
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
HFE standard's medical facilities clause requires each crewed mission to
carry provisions commensurate with crew size and mission duration; items
are grouped into four capability families — emergency, diagnostic,
routine, and preventive — and the minimum required set grows with
mission duration across three tiers (short ≤30 days, medium 31–180 days,
long >180 days); consumables must cover crew size × duration × 1.10
margin. This module implements provision categorization, duration-tier
selection, provision-set completeness checking, consumable-quantity
adequacy checking, and the aggregated medical HFE review; it does not
define the specific quantity rates for individual medications or the
clinical protocols themselves.
"""

# ---------------------------------------------------------------------------
# Provision type catalogue
# ---------------------------------------------------------------------------

EMERGENCY_PROVISIONS = frozenset({
    "trauma_kit",
    "defibrillator",
    "emergency_medications",
    "oxygen_supply",
    "iv_kit",
})

DIAGNOSTIC_PROVISIONS = frozenset({
    "blood_pressure_monitor",
    "pulse_oximeter",
    "thermometer",
    "ultrasound",
})

ROUTINE_PROVISIONS = frozenset({
    "first_aid_kit",
    "wound_care",
    "oral_care",
    "eye_care",
})

PREVENTIVE_PROVISIONS = frozenset({
    "vitamins",
    "exercise_equipment",
    "radiation_dosimeter",
})

_ALL_KNOWN_PROVISIONS = (
    EMERGENCY_PROVISIONS
    | DIAGNOSTIC_PROVISIONS
    | ROUTINE_PROVISIONS
    | PREVENTIVE_PROVISIONS
)

_PROVISION_FAMILY = {}
for _p in EMERGENCY_PROVISIONS:
    _PROVISION_FAMILY[_p] = "emergency"
for _p in DIAGNOSTIC_PROVISIONS:
    _PROVISION_FAMILY[_p] = "diagnostic"
for _p in ROUTINE_PROVISIONS:
    _PROVISION_FAMILY[_p] = "routine"
for _p in PREVENTIVE_PROVISIONS:
    _PROVISION_FAMILY[_p] = "preventive"

# ---------------------------------------------------------------------------
# Mission duration thresholds (days, inclusive upper bound for the tier)
# ---------------------------------------------------------------------------

SHORT_DURATION_MAX_DAYS = 30
MEDIUM_DURATION_MAX_DAYS = 180

# ---------------------------------------------------------------------------
# Minimum required provision sets per duration tier (monotonically growing)
# ---------------------------------------------------------------------------

REQUIRED_SHORT = frozenset({
    "trauma_kit",
    "emergency_medications",
    "oxygen_supply",
    "pulse_oximeter",
    "thermometer",
    "first_aid_kit",
})

REQUIRED_MEDIUM = REQUIRED_SHORT | frozenset({
    "defibrillator",
    "iv_kit",
    "blood_pressure_monitor",
    "wound_care",
    "oral_care",
    "eye_care",
    "ultrasound",
    "radiation_dosimeter",
})

REQUIRED_LONG = REQUIRED_MEDIUM | frozenset({
    "vitamins",
    "exercise_equipment",
})

# ---------------------------------------------------------------------------
# Consumable margin
# ---------------------------------------------------------------------------

CONSUMABLE_MARGIN = 1.1  # 10 % margin above baseline


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def categorize_provision(provision_type):
    """Capability family for a provision item type: "emergency",
    "diagnostic", "routine", or "preventive". Raises ValueError for a
    type outside all known sets."""
    family = _PROVISION_FAMILY.get(provision_type)
    if family is None:
        raise ValueError(
            "unrecognized medical provision type %r under "
            "E-ST-10-11C §4.7.9" % (provision_type,)
        )
    return family


def mission_duration_category(duration_days):
    """Mission duration tier: "short" (≤30 days), "medium" (31–180 days),
    or "long" (>180 days). Raises ValueError for a non-positive duration."""
    if duration_days <= 0:
        raise ValueError(
            "duration_days must be > 0, got %r" % (duration_days,)
        )
    if duration_days <= SHORT_DURATION_MAX_DAYS:
        return "short"
    if duration_days <= MEDIUM_DURATION_MAX_DAYS:
        return "medium"
    return "long"


def required_provisions(duration_days):
    """Frozenset of provision type strings that must be present in the
    on-board inventory for the given mission duration. Raises ValueError
    for a non-positive duration."""
    category = mission_duration_category(duration_days)
    if category == "short":
        return REQUIRED_SHORT
    if category == "medium":
        return REQUIRED_MEDIUM
    return REQUIRED_LONG


def missing_provisions(available_types, duration_days):
    """Sorted list of provision type strings that are required for the
    mission duration but absent from available_types. available_types may
    be any iterable of provision type strings (unknown types are ignored
    for the completeness check — they are caught by categorize_provision
    if called separately). Raises ValueError for a non-positive duration."""
    required = required_provisions(duration_days)
    present = frozenset(available_types)
    return sorted(required - present)


def consumable_requirement(crew_size, duration_days, daily_rate_per_person):
    """Minimum required quantity for a consumable item:
    daily_rate_per_person × crew_size × duration_days × CONSUMABLE_MARGIN.
    Raises ValueError for non-positive crew_size or duration_days, or a
    negative daily_rate_per_person."""
    if crew_size <= 0:
        raise ValueError("crew_size must be > 0, got %r" % (crew_size,))
    if duration_days <= 0:
        raise ValueError(
            "duration_days must be > 0, got %r" % (duration_days,)
        )
    if daily_rate_per_person < 0:
        raise ValueError(
            "daily_rate_per_person must be >= 0, got %r" % (daily_rate_per_person,)
        )
    return daily_rate_per_person * crew_size * duration_days * CONSUMABLE_MARGIN


def consumable_shortfall(provision_id, available_qty, crew_size,
                         duration_days, daily_rate_per_person):
    """Shortfall finding list (empty if adequate) for one consumable item.
    Returns a single-element list with the finding dict when the available
    quantity is below the computed requirement; returns an empty list when
    adequate. Raises ValueError for invalid numeric inputs."""
    required = consumable_requirement(crew_size, duration_days, daily_rate_per_person)
    if available_qty < required:
        return [
            {
                "issue": "consumable_quantity_shortfall",
                "provision_id": provision_id,
                "available": available_qty,
                "required": required,
            }
        ]
    return []


def medical_hfe_review(config):
    """Full §4.7.9 medical HFE review for one spacecraft configuration.

    config: {
        "crew_size": int,
        "duration_days": int or float,
        "provisions": [
            {
                "provision_type": str,       # must be a known type
                "available_qty": float,      # optional; omit for non-consumables
                "daily_rate_per_person": float  # optional; omit for non-consumables
            },
            ...
        ]
    }

    Returns {
        "missing_provisions": [str, ...],      # types that are required but absent
        "consumable_shortfalls": [{...}, ...]  # shortfall findings for consumables
    }.

    Raises ValueError when an unrecognized provision_type is encountered or
    when any numeric field is invalid. Does not mutate config."""
    crew_size = config["crew_size"]
    duration_days = config["duration_days"]

    # Validate every provision type before any completeness check so that
    # an unrecognized type surfaces immediately rather than silently failing.
    for entry in config.get("provisions", []):
        categorize_provision(entry["provision_type"])

    available_types = [e["provision_type"] for e in config.get("provisions", [])]
    absent = missing_provisions(available_types, duration_days)

    shortfalls = []
    for entry in config.get("provisions", []):
        if "daily_rate_per_person" in entry and "available_qty" in entry:
            shortfalls.extend(
                consumable_shortfall(
                    entry["provision_type"],
                    entry["available_qty"],
                    crew_size,
                    duration_days,
                    entry["daily_rate_per_person"],
                )
            )

    return {
        "missing_provisions": absent,
        "consumable_shortfalls": shortfalls,
    }


def is_medical_hfe_compliant(review):
    """True when a medical_hfe_review result contains no findings — both
    missing_provisions and consumable_shortfalls are empty."""
    return (
        len(review["missing_provisions"]) == 0
        and len(review["consumable_shortfalls"]) == 0
    )
