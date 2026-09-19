"""Particulate and molecular cleanliness level definitions and their units.

Anchor: ECSS-Q-ST-70-01C framework (what a cleanliness level means, how a
particulate level is expressed as a size-resolved count allowance over a
reference area, and how a molecular level is expressed as an areal mass).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. A particulate level is named by the largest particle size it admits. Its
   allowance at any smaller size follows a log-log distribution whose slope
   the programme declares, evaluated over a stated reference area. Nothing
   larger than the level label is admitted at all.
2. The allowance is only comparable with a measurement after it is scaled
   from the reference area onto the area actually inspected.
3. The obscuration a level implies is obtained from the incremental count in
   each size band times the projected area of a representative particle,
   expressed as a percentage of the surface.
4. A molecular level is an areal mass, so it is defined by a number and a
   unit; the unit is part of the level and every comparison converts to one
   canonical unit before grading.
5. A level definition record carries the label, the unit, the size channels
   with their allowances and the implied obscuration, plus any finding: a
   channel coarser than the level label, or a declared ladder step that does
   not bound the required limit.
"""

import math

__all__ = [
    "DEFAULT_DISTRIBUTION_SLOPE",
    "DEFAULT_REFERENCE_AREA_CM2",
    "MOLECULAR_UNITS_TO_NG_PER_CM2",
    "UNIT_TOLERANCE",
    "validate_positive",
    "validate_size_channels",
    "particle_count_allowance",
    "scale_allowance_to_area",
    "projected_area_cm2",
    "channel_allowances",
    "band_obscuration_percent",
    "level_obscuration_percent",
    "convert_molecular",
    "select_molecular_level",
    "define_levels",
]

# Slope of the log-log size distribution a particulate level curve follows.
# A programme declares its own; this is the fall-back used when none is given.
DEFAULT_DISTRIBUTION_SLOPE = 0.926

# Reference area the count allowance is quoted over, in square centimetres.
DEFAULT_REFERENCE_AREA_CM2 = 1000.0

# Areal mass units a molecular level may be expressed in, as the number of
# nanograms per square centimetre one unit of each represents.
MOLECULAR_UNITS_TO_NG_PER_CM2 = {
    "ng/cm2": 1.0,
    "ug/cm2": 1000.0,
    "mg/m2": 100.0,
    "g/m2": 100000.0,
}

# Comparisons against a level bound absorb representation error here rather
# than by moving the bound.
UNIT_TOLERANCE = 1e-9


def validate_positive(value, label):
    """Return value as a positive finite float, or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_size_channels(channels):
    """Return the size channels in micrometres, ascending and distinct."""
    if not isinstance(channels, (list, tuple)) or len(channels) < 2:
        raise ValueError("size channels must be a sequence of at least two sizes")
    sizes = [
        validate_positive(size, "size channel %d" % index)
        for index, size in enumerate(channels)
    ]
    for index in range(1, len(sizes)):
        if sizes[index] <= sizes[index - 1]:
            raise ValueError(
                "size channels must strictly increase (index %d)" % index
            )
    return sizes


def particle_count_allowance(
    level_um,
    size_um,
    slope=DEFAULT_DISTRIBUTION_SLOPE,
    reference_area_cm2=DEFAULT_REFERENCE_AREA_CM2,
):
    """Return the count of particles at or above a size the level allows."""
    level = validate_positive(level_um, "level_um")
    size = validate_positive(size_um, "size_um")
    gradient = validate_positive(slope, "slope")
    area = validate_positive(reference_area_cm2, "reference_area_cm2")
    if size > level and not math.isclose(size, level, rel_tol=UNIT_TOLERANCE):
        return 0.0
    exponent = gradient * (
        math.log10(level) ** 2 - math.log10(size) ** 2
    )
    per_reference = 10.0 ** exponent
    return per_reference * (area / DEFAULT_REFERENCE_AREA_CM2)


def scale_allowance_to_area(count, reference_area_cm2, inspected_area_cm2):
    """Scale a count allowance from its reference area onto the area inspected."""
    if not isinstance(count, (int, float)) or isinstance(count, bool):
        raise ValueError("count must be a real number")
    value = float(count)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("count must be non-negative and finite, got %r" % (count,))
    reference = validate_positive(reference_area_cm2, "reference_area_cm2")
    inspected = validate_positive(inspected_area_cm2, "inspected_area_cm2")
    return value * inspected / reference


def projected_area_cm2(size_um):
    """Return the projected area of one particle of the given size."""
    size = validate_positive(size_um, "size_um")
    radius_cm = 0.5 * size * 1e-4
    return math.pi * radius_cm * radius_cm


def channel_allowances(
    level_um,
    channels,
    slope=DEFAULT_DISTRIBUTION_SLOPE,
    reference_area_cm2=DEFAULT_REFERENCE_AREA_CM2,
):
    """Return the cumulative count allowance at each declared size channel."""
    level = validate_positive(level_um, "level_um")
    sizes = validate_size_channels(channels)
    return [
        {
            "size_um": size,
            "count_allowance": particle_count_allowance(
                level, size, slope, reference_area_cm2
            ),
            "above_level_label": size > level
            and not math.isclose(size, level, rel_tol=UNIT_TOLERANCE),
        }
        for size in sizes
    ]


def band_obscuration_percent(count, size_um, reference_area_cm2):
    """Return the percentage of a reference area a count of one size covers."""
    if not isinstance(count, (int, float)) or isinstance(count, bool):
        raise ValueError("count must be a real number")
    value = float(count)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("count must be non-negative and finite, got %r" % (count,))
    area = validate_positive(reference_area_cm2, "reference_area_cm2")
    return 100.0 * value * projected_area_cm2(size_um) / area


def level_obscuration_percent(
    level_um,
    channels,
    slope=DEFAULT_DISTRIBUTION_SLOPE,
    reference_area_cm2=DEFAULT_REFERENCE_AREA_CM2,
):
    """Return the obscuration a particulate level implies over its channels."""
    records = channel_allowances(level_um, channels, slope, reference_area_cm2)
    usable = [r for r in records if not r["above_level_label"]]
    if len(usable) < 2:
        raise ValueError(
            "at least two size channels at or below the level label are needed "
            "to form incremental bands"
        )
    total = 0.0
    for index in range(len(usable) - 1):
        lower = usable[index]
        upper = usable[index + 1]
        increment = lower["count_allowance"] - upper["count_allowance"]
        if increment < 0.0:
            increment = 0.0
        representative = math.sqrt(lower["size_um"] * upper["size_um"])
        total += band_obscuration_percent(
            increment, representative, reference_area_cm2
        )
    top = usable[-1]
    total += band_obscuration_percent(
        top["count_allowance"], top["size_um"], reference_area_cm2
    )
    return total


def convert_molecular(value, from_unit, to_unit="ng/cm2"):
    """Convert an areal mass between the molecular level units."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("value must be a real number")
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise ValueError("value must be non-negative and finite, got %r" % (value,))
    for label, unit in (("from_unit", from_unit), ("to_unit", to_unit)):
        if unit not in MOLECULAR_UNITS_TO_NG_PER_CM2:
            raise ValueError(
                "%s %r is not a recognised areal mass unit; expected one of %s"
                % (label, unit, ", ".join(sorted(MOLECULAR_UNITS_TO_NG_PER_CM2)))
            )
    canonical = number * MOLECULAR_UNITS_TO_NG_PER_CM2[from_unit]
    return canonical / MOLECULAR_UNITS_TO_NG_PER_CM2[to_unit]


def select_molecular_level(ladder, required_ng_per_cm2):
    """Return the coarsest ladder step that still meets the required limit."""
    if not isinstance(ladder, (list, tuple)) or not ladder:
        raise ValueError("ladder must be a non-empty sequence of (label, value, unit)")
    required = validate_positive(required_ng_per_cm2, "required_ng_per_cm2")
    steps = []
    labels = set()
    for index, entry in enumerate(ladder):
        if not isinstance(entry, (list, tuple)) or len(entry) != 3:
            raise ValueError("ladder[%d] must be a (label, value, unit) triple" % index)
        label, value, unit = entry
        if not isinstance(label, str) or not label.strip():
            raise ValueError("ladder[%d] label must be a non-empty string" % index)
        if label in labels:
            raise ValueError("duplicate ladder label %r" % label)
        labels.add(label)
        steps.append(
            {
                "label": label,
                "allowance_ng_per_cm2": convert_molecular(
                    validate_positive(value, "ladder[%d] value" % index), unit
                ),
                "declared_unit": unit,
            }
        )
    steps.sort(key=lambda step: step["allowance_ng_per_cm2"])
    admissible = [
        step
        for step in steps
        if step["allowance_ng_per_cm2"] < required
        or math.isclose(
            step["allowance_ng_per_cm2"], required, rel_tol=UNIT_TOLERANCE
        )
    ]
    if not admissible:
        return None
    return admissible[-1]


def define_levels(spec):
    """Build the cleanliness level definition record for one item.

    spec keys: particulate_level_um and size_channels; optional slope,
    reference_area_cm2, inspected_area_cm2, molecular_ladder and
    required_molecular_ng_per_cm2.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("particulate_level_um", "size_channels"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    level = validate_positive(spec["particulate_level_um"], "particulate_level_um")
    slope = spec.get("slope", DEFAULT_DISTRIBUTION_SLOPE)
    reference = spec.get("reference_area_cm2", DEFAULT_REFERENCE_AREA_CM2)
    records = channel_allowances(level, spec["size_channels"], slope, reference)
    findings = []
    for record in records:
        if record["above_level_label"]:
            findings.append(
                "size channel %g um is coarser than the level label %g um, so the "
                "level admits nothing there" % (record["size_um"], level)
            )
    inspected = spec.get("inspected_area_cm2")
    if inspected is not None:
        for record in records:
            record["allowance_on_inspected_area"] = scale_allowance_to_area(
                record["count_allowance"], reference, inspected
            )
    particulate = {
        "label": level,
        "label_unit": "um",
        "count_unit": "particles per %g cm2" % validate_positive(
            reference, "reference_area_cm2"
        ),
        "slope": validate_positive(slope, "slope"),
        "channels": records,
        "implied_obscuration_percent": level_obscuration_percent(
            level, spec["size_channels"], slope, reference
        ),
    }
    molecular = None
    ladder = spec.get("molecular_ladder")
    required = spec.get("required_molecular_ng_per_cm2")
    if ladder is not None:
        if required is None:
            raise ValueError(
                "molecular_ladder needs required_molecular_ng_per_cm2 to select from"
            )
        step = select_molecular_level(ladder, required)
        if step is None:
            findings.append(
                "no molecular ladder step meets the required %g ng/cm2" % required
            )
        else:
            molecular = dict(step, unit="ng/cm2", required_ng_per_cm2=float(required))
    return {
        "particulate": particulate,
        "molecular": molecular,
        "findings": findings,
        "consistent": not findings,
    }
