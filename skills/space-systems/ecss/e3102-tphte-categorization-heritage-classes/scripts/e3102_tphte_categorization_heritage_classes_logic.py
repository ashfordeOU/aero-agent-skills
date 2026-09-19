"""Two-phase heat transport equipment: type grouping and heritage categories.

Anchor: ECSS-E-ST-31-02C clause 4.1 and clause 5.4 with its qualification
depth table (grouping two-phase heat transport equipment by type -- constant
conductance heat pipe, variable conductance heat pipe, diode heat pipe and
capillary driven loop -- and by heritage category, and deriving the depth of
qualification each combination owes). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the equipment type of the candidate item and of the heritage
   reference it is being compared against.
2. Compare the candidate with its reference across the attributes that drive
   the heritage category: equipment type, working fluid, envelope material,
   wick type, the application it flies in, the geometric and power scaling
   ratios, and the operating temperature range.
3. Place the item in heritage category A (unchanged, in the same
   application), B (modified within the qualified envelope, delta
   qualification) or C (new development, full qualification), and carry the
   reasons that drove the placement.
4. Derive the qualification depth: the common test set the category owes,
   plus the tests that belong to the equipment type itself -- a variable
   conductance pipe owes its reservoir and control-range demonstrations, a
   diode owes its reverse-mode shut-off, a capillary driven loop owes its
   start-up and load-sharing runs -- and the number of qualification units.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "TEMPERATURE_TOLERANCE_K",
    "EQUIPMENT_TYPES",
    "HERITAGE_CATEGORIES",
    "SCALING_NEW_DEVELOPMENT_RATIO",
    "TEMPERATURE_EXTENSION_NEW_DEVELOPMENT_K",
    "CATEGORY_TESTS",
    "TYPE_TESTS",
    "CATEGORY_UNITS",
    "validate_equipment_type",
    "validate_positive",
    "validate_range_k",
    "scaling_ratio",
    "ratio_is_unity",
    "temperature_extension_k",
    "heritage_category",
    "qualification_tests",
    "qualification_units",
    "assess_tphte_item",
    "assess_tphte_programme",
]

# Ratios and temperature extensions are quotients and differences of floats.
# A candidate that is dimensionally identical to its reference must land on
# unity on every platform, so the comparison carries a named tolerance.
RATIO_TOLERANCE = 1e-9
TEMPERATURE_TOLERANCE_K = 1e-9

EQUIPMENT_TYPES = (
    "constant-conductance-heat-pipe",
    "variable-conductance-heat-pipe",
    "diode-heat-pipe",
    "capillary-driven-loop",
)

# Heritage categories, from unchanged to new development.
HERITAGE_CATEGORIES = ("A", "B", "C")

# A geometric or power scaling beyond this ratio takes the item out of the
# qualified envelope and into new development.
SCALING_NEW_DEVELOPMENT_RATIO = 1.5

# An operating range extended beyond the qualified range by more than this
# takes the item into new development.
TEMPERATURE_EXTENSION_NEW_DEVELOPMENT_K = 20.0

# The common qualification depth each heritage category owes.
CATEGORY_TESTS = {
    "A": ("acceptance-performance-test",),
    "B": (
        "performance-test",
        "thermal-cycling-test",
        "vibration-test",
        "thermal-vacuum-test",
    ),
    "C": (
        "performance-test",
        "thermal-cycling-test",
        "vibration-test",
        "thermal-vacuum-test",
        "shock-test",
        "burst-pressure-test",
        "life-test",
        "ageing-test",
    ),
}

# The demonstrations that belong to the equipment type itself, whatever the
# heritage category.
TYPE_TESTS = {
    "constant-conductance-heat-pipe": (),
    "variable-conductance-heat-pipe": (
        "reservoir-gas-inventory-test",
        "conductance-control-range-test",
    ),
    "diode-heat-pipe": ("reverse-mode-shutoff-test",),
    "capillary-driven-loop": ("start-up-test", "heat-load-sharing-test"),
}

# Qualification units each category owes.
CATEGORY_UNITS = {"A": 0, "B": 1, "C": 2}


def validate_equipment_type(equipment_type):
    """Return a validated two-phase heat transport equipment type."""
    if not isinstance(equipment_type, str):
        raise ValueError("equipment type must be a string")
    name = equipment_type.strip().lower()
    if name not in EQUIPMENT_TYPES:
        raise ValueError("unknown equipment type %r; expected one of %s"
                         % (equipment_type, EQUIPMENT_TYPES))
    return name


def validate_positive(value, label):
    """Return a validated strictly positive real quantity."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_range_k(range_pair, label):
    """Return a validated (low, high) operating temperature range in kelvin."""
    if not isinstance(range_pair, (list, tuple)) or len(range_pair) != 2:
        raise ValueError("%s must be a (low_k, high_k) pair" % label)
    low = validate_positive(range_pair[0], "%s low bound" % label)
    high = validate_positive(range_pair[1], "%s high bound" % label)
    if high <= low:
        raise ValueError("%s high bound %g must exceed the low bound %g" % (label, high, low))
    return (low, high)


def scaling_ratio(candidate_value, reference_value):
    """Return the candidate-to-reference ratio of a geometric or power attribute."""
    candidate = validate_positive(candidate_value, "candidate value")
    reference = validate_positive(reference_value, "reference value")
    return candidate / reference


def ratio_is_unity(ratio):
    """Return True when a scaling ratio is unity within the named tolerance."""
    if not isinstance(ratio, (int, float)) or isinstance(ratio, bool):
        raise ValueError("ratio must be a real number")
    value = float(ratio)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("ratio must be positive and finite, got %r" % (ratio,))
    return math.isclose(value, 1.0, rel_tol=RATIO_TOLERANCE, abs_tol=0.0)


def _ratio_beyond_envelope(ratio):
    """Return True when a scaling ratio leaves the qualified envelope."""
    upper = SCALING_NEW_DEVELOPMENT_RATIO
    lower = 1.0 / SCALING_NEW_DEVELOPMENT_RATIO
    if ratio > upper and not math.isclose(ratio, upper, rel_tol=RATIO_TOLERANCE, abs_tol=0.0):
        return True
    if ratio < lower and not math.isclose(ratio, lower, rel_tol=RATIO_TOLERANCE, abs_tol=0.0):
        return True
    return False


def temperature_extension_k(candidate_range_k, qualified_range_k):
    """Return how far a candidate range reaches beyond the qualified range."""
    candidate = validate_range_k(candidate_range_k, "candidate range")
    qualified = validate_range_k(qualified_range_k, "qualified range")
    below = qualified[0] - candidate[0]
    above = candidate[1] - qualified[1]
    extension = max(below, above)
    if extension < 0.0:
        return 0.0
    return extension


def heritage_category(candidate, reference):
    """Return the heritage category of a candidate item and the reasons for it.

    candidate keys: equipment_type, working_fluid, envelope_material, wick_type,
    application, length_m, transport_power_w, operating_range_k.
    reference keys: the same, describing the qualified heritage item.
    """
    for label, mapping in (("candidate", candidate), ("reference", reference)):
        if not isinstance(mapping, dict):
            raise ValueError("%s must be a mapping" % label)
    required = (
        "equipment_type", "working_fluid", "envelope_material", "wick_type",
        "application", "length_m", "transport_power_w", "operating_range_k",
    )
    for key in required:
        for label, mapping in (("candidate", candidate), ("reference", reference)):
            if key not in mapping:
                raise ValueError("%s missing required key '%s'" % (label, key))
    candidate_type = validate_equipment_type(candidate["equipment_type"])
    reference_type = validate_equipment_type(reference["equipment_type"])

    texts = {}
    for key in ("working_fluid", "envelope_material", "wick_type", "application"):
        for label, mapping in (("candidate", candidate), ("reference", reference)):
            value = mapping[key]
            if not isinstance(value, str) or not value.strip():
                raise ValueError("%s '%s' must be a non-empty string" % (label, key))
            texts[(label, key)] = value.strip().lower()

    length = scaling_ratio(candidate["length_m"], reference["length_m"])
    power = scaling_ratio(candidate["transport_power_w"], reference["transport_power_w"])
    extension = temperature_extension_k(
        candidate["operating_range_k"], reference["operating_range_k"]
    )

    new_development = []
    modified = []

    if candidate_type != reference_type:
        new_development.append(
            "equipment type changed from %s to %s" % (reference_type, candidate_type)
        )
    if texts[("candidate", "working_fluid")] != texts[("reference", "working_fluid")]:
        new_development.append("working fluid changed")
    if texts[("candidate", "envelope_material")] != texts[("reference", "envelope_material")]:
        new_development.append("envelope material changed")
    if texts[("candidate", "wick_type")] != texts[("reference", "wick_type")]:
        new_development.append("wick type changed")
    if _ratio_beyond_envelope(length):
        new_development.append("length scaled by a factor %.4f, outside the qualified envelope"
                               % length)
    elif not ratio_is_unity(length):
        modified.append("length scaled by a factor %.4f" % length)
    if _ratio_beyond_envelope(power):
        new_development.append(
            "transport power scaled by a factor %.4f, outside the qualified envelope" % power
        )
    elif not ratio_is_unity(power):
        modified.append("transport power scaled by a factor %.4f" % power)
    if extension > TEMPERATURE_EXTENSION_NEW_DEVELOPMENT_K and not math.isclose(
        extension, TEMPERATURE_EXTENSION_NEW_DEVELOPMENT_K,
        rel_tol=0.0, abs_tol=TEMPERATURE_TOLERANCE_K
    ):
        new_development.append(
            "operating range extended %.2f K beyond the qualified range" % extension
        )
    elif extension > 0.0 and not math.isclose(
        extension, 0.0, rel_tol=0.0, abs_tol=TEMPERATURE_TOLERANCE_K
    ):
        modified.append("operating range extended %.2f K beyond the qualified range" % extension)
    if texts[("candidate", "application")] != texts[("reference", "application")]:
        modified.append(
            "flown in %s rather than the qualified %s"
            % (texts[("candidate", "application")], texts[("reference", "application")])
        )

    if new_development:
        category = "C"
        reasons = new_development + modified
    elif modified:
        category = "B"
        reasons = modified
    else:
        category = "A"
        reasons = ["unchanged against the qualified reference in the same application"]
    return {
        "category": category,
        "equipment_type": candidate_type,
        "length_ratio": length,
        "power_ratio": power,
        "temperature_extension_k": extension,
        "reasons": reasons,
    }


def qualification_tests(category, equipment_type):
    """Return the qualification test set a category and equipment type owe."""
    if not isinstance(category, str) or category.strip().upper() not in HERITAGE_CATEGORIES:
        raise ValueError("unknown heritage category %r; expected one of %s"
                         % (category, HERITAGE_CATEGORIES))
    name = category.strip().upper()
    kind = validate_equipment_type(equipment_type)
    return tuple(sorted(set(CATEGORY_TESTS[name]) | set(TYPE_TESTS[kind])))


def qualification_units(category):
    """Return the number of dedicated qualification units a category owes."""
    if not isinstance(category, str) or category.strip().upper() not in HERITAGE_CATEGORIES:
        raise ValueError("unknown heritage category %r; expected one of %s"
                         % (category, HERITAGE_CATEGORIES))
    return CATEGORY_UNITS[category.strip().upper()]


def assess_tphte_item(item):
    """Place one two-phase item in its heritage category and derive its depth.

    item keys: id, candidate, reference.
    """
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    for key in ("id", "candidate", "reference"):
        if key not in item:
            raise ValueError("item missing required key '%s'" % key)
    identifier = item["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("item id must be a non-empty string")
    placement = heritage_category(item["candidate"], item["reference"])
    tests = qualification_tests(placement["category"], placement["equipment_type"])
    units = qualification_units(placement["category"])
    record = dict(placement)
    record["id"] = identifier.strip()
    record["qualification_tests"] = tests
    record["qualification_units"] = units
    record["acceptance_only"] = placement["category"] == "A"
    return record


def assess_tphte_programme(spec):
    """Run the clause 4.1 and 5.4 grouping across a set of two-phase items.

    spec keys: items (sequence of item mappings).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "items" not in spec:
        raise ValueError("spec missing required key 'items'")
    items = spec["items"]
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("spec['items'] must be a non-empty sequence")
    records = []
    seen = set()
    for item in items:
        record = assess_tphte_item(item)
        if record["id"] in seen:
            raise ValueError("duplicate item id %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
    counts = {name: 0 for name in HERITAGE_CATEGORIES}
    for record in records:
        counts[record["category"]] += 1
    deepest = min(
        records, key=lambda r: (-HERITAGE_CATEGORIES.index(r["category"]), r["id"])
    )["id"]
    total_units = sum(record["qualification_units"] for record in records)
    combined = set()
    for record in records:
        combined.update(record["qualification_tests"])
    return {
        "items": records,
        "category_counts": counts,
        "deepest_qualification_item": deepest,
        "total_qualification_units": total_units,
        "combined_test_set": tuple(sorted(combined)),
    }
