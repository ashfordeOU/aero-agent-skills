"""Preparation-for-delivery packaging, marking and protection logic.

Anchor: ECSS-Q-ST-20C clause 5.7.4 (5.7.4.1-5.7.4.2) -- preparing an item for
delivery: packaging against the defined packaging requirements, marking and
labelling the package, and protecting the item against mechanical damage,
electrostatic discharge and the environment it will see in transit and storage.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the item: mass, bearing area, fragility, sensitivity states.
2. Size the cushioning from the declared drop height and the fragility level of
   the item, and check the static stress the item puts on the cushion against
   the stress window the cushion material is rated over -- a cushion working
   outside its window transmits more shock, not less.
3. Size the desiccant charge from the barrier bag area, the water-vapour
   transmission rate of the barrier and the storage duration.
4. Derive the label fields the package owes from the states of the item, and
   name the ones the applied label does not carry.
5. Derive the protection means the item owes from the same states, and name the
   ones the prepared package does not provide.
6. Combine into a ready-for-delivery decision with every finding of the pass.
"""

import math

__all__ = [
    "STANDARD_GRAVITY",
    "BASE_LABEL_FIELDS",
    "BASE_PROTECTION_MEANS",
    "STRESS_TOLERANCE_KPA",
    "normalize_token",
    "validate_item",
    "static_stress_kpa",
    "cushion_thickness_mm",
    "cushion_stress_findings",
    "desiccant_units",
    "required_label_fields",
    "label_findings",
    "required_protection_means",
    "protection_findings",
    "assess_delivery_preparation",
]

STANDARD_GRAVITY = 9.80665

# Fields every delivery package carries regardless of what is inside it.
BASE_LABEL_FIELDS = (
    "part-number",
    "serial-number",
    "gross-mass",
    "handling-orientation",
    "lifting-points",
)

# Protection means every delivery package provides regardless of the item.
BASE_PROTECTION_MEANS = ("outer-container", "cushioning", "load-restraint")

# Stress window comparisons are a division of measured quantities; absorb the
# representation error at the window edge instead of widening the window.
STRESS_TOLERANCE_KPA = 1e-9

_MIN_DESICCANT_UNITS = 1


def normalize_token(value, label="token"):
    """Return a lowercase, hyphen-joined comparison token for a name."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = "-".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _positive(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v) or v <= 0.0:
        raise ValueError("%s must be positive and finite, got %r" % (label, value))
    return v


def _flag(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_item(item):
    """Return the validated item record for the preparation pass."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    for key in ("mass_kg", "bearing_area_mm2", "fragility_g"):
        if key not in item:
            raise ValueError("item is missing '%s'" % key)
    record = {
        "mass_kg": _positive(item["mass_kg"], "mass_kg"),
        "bearing_area_mm2": _positive(item["bearing_area_mm2"], "bearing_area_mm2"),
        "fragility_g": _positive(item["fragility_g"], "fragility_g"),
        "esd_sensitive": _flag(item.get("esd_sensitive", False), "esd_sensitive"),
        "moisture_sensitive": _flag(item.get("moisture_sensitive", False), "moisture_sensitive"),
        "temperature_limited": _flag(item.get("temperature_limited", False), "temperature_limited"),
        "cleanliness_controlled": _flag(
            item.get("cleanliness_controlled", False), "cleanliness_controlled"
        ),
        "hazardous": _flag(item.get("hazardous", False), "hazardous"),
        "pressurised": _flag(item.get("pressurised", False), "pressurised"),
    }
    return record


def static_stress_kpa(mass_kg, bearing_area_mm2):
    """Return the static bearing stress the item puts on the cushion, in kPa."""
    m = _positive(mass_kg, "mass_kg")
    a = _positive(bearing_area_mm2, "bearing_area_mm2")
    # N / mm^2 is MPa; report kPa so cushion curves read directly.
    return (m * STANDARD_GRAVITY / a) * 1000.0


def cushion_thickness_mm(drop_height_mm, fragility_g, efficiency):
    """Return the cushion thickness needed to keep a drop inside the fragility level."""
    h = _positive(drop_height_mm, "drop_height_mm")
    g = _positive(fragility_g, "fragility_g")
    if not isinstance(efficiency, (int, float)) or isinstance(efficiency, bool):
        raise ValueError("efficiency must be a real number, got %r" % (efficiency,))
    e = float(efficiency)
    if not math.isfinite(e) or e <= 0.0 or e > 1.0:
        raise ValueError("efficiency must lie in (0, 1], got %r" % (efficiency,))
    return h / (g * e)


def cushion_stress_findings(stress_kpa, rated_min_kpa, rated_max_kpa):
    """Return findings when the bearing stress sits outside the cushion's window."""
    s = _positive(stress_kpa, "stress_kpa")
    lo = _positive(rated_min_kpa, "rated_min_kpa")
    hi = _positive(rated_max_kpa, "rated_max_kpa")
    if lo > hi:
        raise ValueError("rated_min_kpa %g exceeds rated_max_kpa %g" % (lo, hi))
    findings = []
    if s < lo and not math.isclose(s, lo, rel_tol=0.0, abs_tol=STRESS_TOLERANCE_KPA):
        findings.append(
            "bearing stress %.3f kPa is below the cushion window minimum %.3f kPa" % (s, lo)
        )
    if s > hi and not math.isclose(s, hi, rel_tol=0.0, abs_tol=STRESS_TOLERANCE_KPA):
        findings.append(
            "bearing stress %.3f kPa is above the cushion window maximum %.3f kPa" % (s, hi)
        )
    return findings


def desiccant_units(bag_area_m2, wvtr_g_per_m2_day, duration_days, unit_capacity_g):
    """Return the whole desiccant units the barrier bag needs for the storage period."""
    area = _positive(bag_area_m2, "bag_area_m2")
    wvtr = _positive(wvtr_g_per_m2_day, "wvtr_g_per_m2_day")
    days = _positive(duration_days, "duration_days")
    capacity = _positive(unit_capacity_g, "unit_capacity_g")
    ingress_g = area * wvtr * days
    units = int(math.ceil(ingress_g / capacity))
    return max(units, _MIN_DESICCANT_UNITS)


def required_label_fields(item):
    """Return the label fields this item's states make mandatory."""
    record = validate_item(item)
    fields = list(BASE_LABEL_FIELDS)
    if record["esd_sensitive"]:
        fields.append("esd-sensitive-symbol")
    if record["moisture_sensitive"]:
        fields.append("moisture-barrier-seal-date")
    if record["temperature_limited"]:
        fields.append("transport-temperature-limits")
    if record["cleanliness_controlled"]:
        fields.append("cleanliness-level-marking")
    if record["hazardous"]:
        fields.append("hazard-marking")
    if record["pressurised"]:
        fields.append("pressurised-item-warning")
    return fields


def label_findings(applied_fields, required_fields):
    """Return the mandatory label fields the applied label does not carry."""
    if not isinstance(applied_fields, (list, tuple)):
        raise ValueError("applied_fields must be a sequence of field names")
    if not isinstance(required_fields, (list, tuple)):
        raise ValueError("required_fields must be a sequence of field names")
    have = {normalize_token(f, "applied label field") for f in applied_fields}
    findings = []
    for field in required_fields:
        token = normalize_token(field, "required label field")
        if token not in have:
            findings.append("package label does not carry %s" % token)
    return findings


def required_protection_means(item):
    """Return the protection means this item's states make mandatory."""
    record = validate_item(item)
    means = list(BASE_PROTECTION_MEANS)
    if record["esd_sensitive"]:
        means.extend(["static-shielding-bag", "connector-shunts", "grounded-handling-procedure"])
    if record["moisture_sensitive"]:
        means.extend(["sealed-moisture-barrier", "desiccant-charge", "humidity-indicator"])
    if record["temperature_limited"]:
        means.append("transport-temperature-recorder")
    if record["cleanliness_controlled"]:
        means.append("cleanroom-bagging")
    if record["pressurised"]:
        means.append("pressure-relief-provision")
    return means


def protection_findings(provided_means, required_means):
    """Return the mandatory protection means the prepared package does not provide."""
    if not isinstance(provided_means, (list, tuple)):
        raise ValueError("provided_means must be a sequence of means")
    if not isinstance(required_means, (list, tuple)):
        raise ValueError("required_means must be a sequence of means")
    have = {normalize_token(m, "provided protection mean") for m in provided_means}
    findings = []
    for mean in required_means:
        token = normalize_token(mean, "required protection mean")
        if token not in have:
            findings.append("package does not provide %s" % token)
    return findings


def assess_delivery_preparation(spec):
    """Run the full clause 5.7.4 preparation-for-delivery assessment.

    spec keys: item, drop_height_mm, cushion (efficiency, thickness_mm,
    rated_min_kpa, rated_max_kpa), applied_label_fields, provided_protection,
    optional storage (bag_area_m2, wvtr_g_per_m2_day, duration_days,
    unit_capacity_g, units_fitted).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("item", "drop_height_mm", "cushion", "applied_label_fields", "provided_protection"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    item = validate_item(spec["item"])
    cushion = spec["cushion"]
    if not isinstance(cushion, dict):
        raise ValueError("spec['cushion'] must be a mapping")
    for key in ("efficiency", "thickness_mm", "rated_min_kpa", "rated_max_kpa"):
        if key not in cushion:
            raise ValueError("spec['cushion'] is missing '%s'" % key)

    findings = []
    required_mm = cushion_thickness_mm(
        spec["drop_height_mm"], item["fragility_g"], cushion["efficiency"]
    )
    fitted_mm = _positive(cushion["thickness_mm"], "cushion['thickness_mm']")
    if fitted_mm < required_mm and not math.isclose(
        fitted_mm, required_mm, rel_tol=1e-12, abs_tol=0.0
    ):
        findings.append(
            "cushion thickness %.3f mm is below the %.3f mm the drop height and fragility need"
            % (fitted_mm, required_mm)
        )
    stress = static_stress_kpa(item["mass_kg"], item["bearing_area_mm2"])
    findings.extend(
        cushion_stress_findings(stress, cushion["rated_min_kpa"], cushion["rated_max_kpa"])
    )

    desiccant = None
    if item["moisture_sensitive"]:
        storage = spec.get("storage")
        if not isinstance(storage, dict):
            raise ValueError("a moisture-sensitive item needs a spec['storage'] mapping")
        for key in ("bag_area_m2", "wvtr_g_per_m2_day", "duration_days", "unit_capacity_g"):
            if key not in storage:
                raise ValueError("spec['storage'] is missing '%s'" % key)
        needed = desiccant_units(
            storage["bag_area_m2"],
            storage["wvtr_g_per_m2_day"],
            storage["duration_days"],
            storage["unit_capacity_g"],
        )
        fitted = storage.get("units_fitted", 0)
        if not isinstance(fitted, int) or isinstance(fitted, bool) or fitted < 0:
            raise ValueError("storage['units_fitted'] must be a non-negative integer")
        desiccant = {"units_required": needed, "units_fitted": fitted}
        if fitted < needed:
            findings.append(
                "desiccant charge is %d units against the %d units the barrier needs"
                % (fitted, needed)
            )

    label_required = required_label_fields(item)
    label_gaps = label_findings(spec["applied_label_fields"], label_required)
    protection_required = required_protection_means(item)
    protection_gaps = protection_findings(spec["provided_protection"], protection_required)
    findings.extend(label_gaps)
    findings.extend(protection_gaps)
    return {
        "item": item,
        "required_cushion_thickness_mm": required_mm,
        "fitted_cushion_thickness_mm": fitted_mm,
        "static_stress_kpa": stress,
        "desiccant": desiccant,
        "required_label_fields": label_required,
        "label_findings": label_gaps,
        "required_protection_means": protection_required,
        "protection_findings": protection_gaps,
        "findings": findings,
        "ready_for_delivery": not findings,
    }
