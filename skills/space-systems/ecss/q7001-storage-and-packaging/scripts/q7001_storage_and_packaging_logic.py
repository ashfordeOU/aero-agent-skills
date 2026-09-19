"""Packaging and storage that hold a cleanliness level while hardware waits.

Anchor: the packaging, handling and storage provisions of the
contamination and cleanliness control practice of ECSS-Q-ST-70-01C
(paraphrased into an implementable procedure; no standard text is
reproduced).

Procedure implemented here:

1. Packaging is a barrier count, not a bag. The layer against the
   hardware is the one that matters and it is the one that gets
   handled, so a sensitivity that demands three layers is not met by
   one good bag inside a crate.
2. Materials are qualified for contact, not for convenience. Plasticised
   films, untreated foams and board shed or transfer onto the surface
   they were bought to protect, and they do it slowly enough that
   nobody connects the residue to the packaging.
3. Cleanliness degrades in store. Residue accumulates inside a sealed
   bag at a slow rate that is measurable and roughly linear over the
   intervals hardware actually waits, so the level at the end of
   storage is projected, not assumed to equal the level at the start.
4. A purge is a consumable. Positive pressure decays through the seam
   and the film, and the day it reaches its floor is the day the bag
   stops being a barrier and starts being a cover.
5. The re-verification interval is the earliest of those two limits and
   whatever ceiling programme policy imposes, which is usually the
   binding one for short storage and never the binding one for long
   storage. Reporting which limit bound it is the point: it says
   whether to re-bag, to re-purge or to argue with the policy.
6. The store is graded too. An item bagged to a level it cannot be
   unbagged into has to travel to be opened, and that trip is normally
   discovered on the day somebody needs the item.

Stdlib only, offline, deterministic.
"""

import math

# Minimum barrier layers against the hardware, by how sensitive it is.
BARRIER_LAYERS_BY_SENSITIVITY = {
    "precision-clean": 3,
    "clean": 2,
    "general": 1,
}

# Materials refused in contact with flight hardware.
DEFAULT_REFUSED_CONTACT_MATERIALS = frozenset(
    {
        "plasticised-pvc-film",
        "untreated-polyurethane-foam",
        "corrugated-board",
        "natural-rubber",
        "sulphur-cured-elastomer",
    }
)

# Policy ceiling on how long a package may sit before it is opened and
# the level re-verified, whatever the projections say.
DEFAULT_POLICY_CEILING_DAYS = 365.0

# Which limit bound the interval.
BOUND_BY_RESIDUE = "residue-projection"
BOUND_BY_PURGE = "purge-pressure-hold"
BOUND_BY_POLICY = "policy-ceiling"

# A projection landing exactly on a limit is at the limit, not past it.
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


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def minimum_barrier_layers(sensitivity):
    """Layers a sensitivity demands between the hardware and the world."""
    name = _text("sensitivity", sensitivity)
    if name not in BARRIER_LAYERS_BY_SENSITIVITY:
        raise ValueError(
            "sensitivity %r is not one of %r"
            % (name, sorted(BARRIER_LAYERS_BY_SENSITIVITY))
        )
    return BARRIER_LAYERS_BY_SENSITIVITY[name]


def projected_level(initial_level, accumulation_per_day, days):
    """Level reached after a number of days of linear accumulation."""
    start = _non_negative("initial_level", initial_level)
    rate = _non_negative("accumulation_per_day", accumulation_per_day)
    span = _non_negative("days", days)
    return start + rate * span


def days_until_limit(initial_level, accumulation_per_day, limit):
    """Days of storage before the projection reaches the limit."""
    start = _non_negative("initial_level", initial_level)
    rate = _non_negative("accumulation_per_day", accumulation_per_day)
    bound = _positive("limit", limit)
    if start > bound * (1.0 + RELATIVE_TOLERANCE):
        raise ValueError(
            "the item is already at %r against a limit of %r; it cannot be "
            "put into store before it is recleaned" % (initial_level, limit)
        )
    if rate == 0.0:
        return float("inf")
    return (bound - start) / rate


def purge_hold_days(initial_pressure_kpa, minimum_pressure_kpa, decay_kpa_per_day):
    """Days before a purged bag falls to its minimum positive pressure."""
    start = _positive("initial_pressure_kpa", initial_pressure_kpa)
    floor = _positive("minimum_pressure_kpa", minimum_pressure_kpa)
    decay = _non_negative("decay_kpa_per_day", decay_kpa_per_day)
    if start < floor * (1.0 - RELATIVE_TOLERANCE):
        raise ValueError(
            "the bag was sealed at %r kPa, already below its floor of %r kPa"
            % (initial_pressure_kpa, minimum_pressure_kpa)
        )
    if decay == 0.0:
        return float("inf")
    return (start - floor) / decay


def reverification_interval(residue_days, purge_days, policy_ceiling_days):
    """Earliest of the residue, purge and policy limits, and which bound it."""
    for label, value in (("residue_days", residue_days), ("purge_days", purge_days)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be numeric, got %r" % (label, value))
        if value < 0:
            raise ValueError("%s must be non-negative, got %r" % (label, value))
    ceiling = _positive("policy_ceiling_days", policy_ceiling_days)
    candidates = (
        (BOUND_BY_RESIDUE, float(residue_days)),
        (BOUND_BY_PURGE, float(purge_days)),
        (BOUND_BY_POLICY, ceiling),
    )
    binding, interval = min(candidates, key=lambda pair: pair[1])
    return {
        "interval_days": interval,
        "whole_days": int(math.floor(interval)) if interval != float("inf") else None,
        "bound_by": binding,
        "residue_days": float(residue_days),
        "purge_days": float(purge_days),
        "policy_ceiling_days": ceiling,
    }


def validate_packaging(packaging, sensitivity, refused_materials=None):
    """Grade a packaging configuration against what the sensitivity demands."""
    if not isinstance(packaging, dict):
        raise ValueError("packaging must be a mapping")
    required = minimum_barrier_layers(sensitivity)
    layers = packaging.get("barrier_layers")
    if not isinstance(layers, int) or isinstance(layers, bool) or layers < 1:
        raise ValueError("barrier_layers must be a positive integer, got %r" % (layers,))
    materials = packaging.get("contact_materials", [])
    if not isinstance(materials, list) or not materials:
        raise ValueError("packaging must name at least one contact material")
    refused = frozenset(
        refused_materials
        if refused_materials is not None
        else DEFAULT_REFUSED_CONTACT_MATERIALS
    )
    named = [_text("contact material", material) for material in materials]
    findings = []
    if layers < required:
        findings.append("barrier-layers-below-the-minimum-for-the-sensitivity")
    present = sorted({material for material in named if material in refused})
    if present:
        findings.append("packaging-material-refused-in-contact-with-flight-hardware")
    return {
        "barrier_layers": layers,
        "required_barrier_layers": required,
        "contact_materials": named,
        "refused_materials_present": present,
        "findings": findings,
    }


def assess_storage(item, packaging, store):
    """Grade a stored item's packaging and say when it must be opened again."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    if not isinstance(store, dict):
        raise ValueError("store must be a mapping")
    item_id = _text("item id", item.get("id"))
    sensitivity = _text("item sensitivity", item.get("sensitivity"))
    limit = _positive("item residue_limit" , item.get("residue_limit"))
    initial = _non_negative("item residue_at_packing", item.get("residue_at_packing"))
    rate = _non_negative(
        "item residue_accumulation_per_day", item.get("residue_accumulation_per_day")
    )
    planned = _non_negative("planned_storage_days", store.get("planned_storage_days"))
    policy = _positive(
        "policy_ceiling_days", store.get("policy_ceiling_days", DEFAULT_POLICY_CEILING_DAYS)
    )

    packaging_row = validate_packaging(
        packaging, sensitivity, store.get("refused_materials")
    )
    findings = list(packaging_row["findings"])

    humidity_sensitive = _boolean(
        "item humidity_sensitive", item.get("humidity_sensitive", False)
    )
    desiccant = _boolean(
        "packaging desiccant_present", packaging.get("desiccant_present", False)
    )
    if humidity_sensitive and not desiccant:
        findings.append("no-desiccant-in-a-humidity-sensitive-package")

    purge_required = _boolean(
        "item purge_required", item.get("purge_required", False)
    )
    purge_days = float("inf")
    purge_detail = None
    if purge_required:
        initial_pressure = packaging.get("purge_pressure_kpa")
        floor = packaging.get("minimum_purge_pressure_kpa")
        decay = packaging.get("purge_decay_kpa_per_day")
        if initial_pressure is None or floor is None or decay is None:
            findings.append("purge-required-but-the-bag-declares-no-purge-state")
        else:
            purge_days = purge_hold_days(initial_pressure, floor, decay)
            purge_detail = {
                "initial_pressure_kpa": float(initial_pressure),
                "minimum_pressure_kpa": float(floor),
                "decay_kpa_per_day": float(decay),
                "hold_days": purge_days,
            }

    residue_days = days_until_limit(initial, rate, limit)
    interval = reverification_interval(residue_days, purge_days, policy)

    projected = projected_level(initial, rate, planned)
    if projected > limit * (1.0 + RELATIVE_TOLERANCE):
        findings.append("projected-level-at-end-of-storage-exceeds-the-requirement")
    if planned > interval["interval_days"] * (1.0 + RELATIVE_TOLERANCE):
        findings.append("planned-storage-longer-than-the-re-verification-interval")

    required_class = item.get("required_area_class")
    store_class = store.get("area_class")
    if required_class is not None:
        if not isinstance(required_class, int) or isinstance(required_class, bool):
            raise ValueError("required_area_class must be an integer class")
        if store_class is None:
            findings.append("store-area-class-not-recorded")
        else:
            if not isinstance(store_class, int) or isinstance(store_class, bool):
                raise ValueError("store area_class must be an integer class")
            if store_class > required_class:
                findings.append("store-cannot-be-used-to-unbag-the-item-it-holds")

    return {
        "item_id": item_id,
        "sensitivity": sensitivity,
        "packaging": packaging_row,
        "purge": purge_detail,
        "residue_limit": limit,
        "residue_at_packing": initial,
        "projected_residue_at_end": projected,
        "planned_storage_days": planned,
        "reverification": interval,
        "findings": findings,
        "verdict": "storage-configuration-acceptable"
        if not findings
        else "storage-configuration-rejected",
        "clear": not findings,
    }
