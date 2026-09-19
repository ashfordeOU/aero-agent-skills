"""Particulate cleanliness level selection for a hardware sensitivity category.

Anchor: ECSS-Q-ST-70-01C framework (choosing the particulate cleanliness level
a hardware item is required to meet, given the category it falls into and the
obscuration its function can tolerate at the end of its exposure).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the hardware category, the obscuration budget the function can
   absorb, the exposure the item still faces and the fallout rate of the
   environment it faces it in.
2. Project the fallout accumulated over the remaining exposure. That
   accumulation is independent of the delivered level: if it alone eats the
   budget, no level can recover it and tightening the level is wasted effort.
3. For every candidate level on the declared ladder, work out the obscuration
   the level itself implies at delivery, add the projected accumulation, apply
   the required margin factor, and keep the candidates that stay inside the
   budget.
4. Apply the two ladder constraints: the category ceiling, which is the
   coarsest level the item's sensitivity band permits whatever the arithmetic
   says, and the verification floor, the finest level the programme can
   actually verify.
5. Select the coarsest admissible candidate, name the constraint that bound
   the choice -- the obscuration budget, the category ceiling, or the end of
   the ladder -- and report the findings when no candidate is admissible,
   including the case where the verification floor excluded them all.
"""

import math

__all__ = [
    "BANDS",
    "DEFAULT_CATEGORY_CEILING_UM",
    "DEFAULT_LEVEL_LADDER_UM",
    "DEFAULT_DISTRIBUTION_SLOPE",
    "DEFAULT_REFERENCE_AREA_CM2",
    "SELECTION_TOLERANCE",
    "validate_positive",
    "validate_non_negative",
    "validate_band",
    "validate_ladder",
    "category_ceiling_um",
    "projected_fallout_percent",
    "level_obscuration_percent",
    "evaluate_candidate",
    "select_particulate_level",
]

# Hardware sensitivity bands, least to most demanding. They are the input to
# the ceiling lookup; the banding itself is decided elsewhere.
BANDS = ("tolerant", "moderate", "sensitive", "highly-sensitive")

# Coarsest level each band permits, in micrometres. A programme declares its
# own ceilings; these are the fall-back used when none are supplied.
DEFAULT_CATEGORY_CEILING_UM = {
    "tolerant": 1000.0,
    "moderate": 500.0,
    "sensitive": 300.0,
    "highly-sensitive": 100.0,
}

# Candidate levels a selection runs over when no ladder is declared.
DEFAULT_LEVEL_LADDER_UM = (50.0, 100.0, 200.0, 300.0, 500.0, 750.0, 1000.0)

# Slope of the log-log size distribution the level curve follows, and the
# reference area the count allowance is quoted over.
DEFAULT_DISTRIBUTION_SLOPE = 0.926
DEFAULT_REFERENCE_AREA_CM2 = 1000.0

# Budget comparisons absorb representation error here, not by moving the
# budget.
SELECTION_TOLERANCE = 1e-9


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


def validate_non_negative(value, label):
    """Return value as a non-negative finite float, or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return number


def validate_band(band):
    """Return a recognised hardware sensitivity band, or raise ValueError."""
    if not isinstance(band, str):
        raise ValueError("band must be a string")
    name = band.strip().lower()
    if name not in BANDS:
        raise ValueError(
            "unknown sensitivity band %r; expected one of %s"
            % (band, ", ".join(BANDS))
        )
    return name


def validate_ladder(ladder=None):
    """Return the candidate level ladder, ascending and distinct."""
    source = DEFAULT_LEVEL_LADDER_UM if ladder is None else ladder
    if not isinstance(source, (list, tuple)) or not source:
        raise ValueError("ladder must be a non-empty sequence of level labels")
    levels = [
        validate_positive(level, "ladder[%d]" % index)
        for index, level in enumerate(source)
    ]
    ordered = sorted(levels)
    for index in range(1, len(ordered)):
        if math.isclose(ordered[index], ordered[index - 1], rel_tol=SELECTION_TOLERANCE):
            raise ValueError("ladder repeats the level %g" % ordered[index])
    return ordered


def category_ceiling_um(band, ceilings=None):
    """Return the coarsest level a sensitivity band permits."""
    name = validate_band(band)
    table = DEFAULT_CATEGORY_CEILING_UM if ceilings is None else ceilings
    if not isinstance(table, dict):
        raise ValueError("ceilings must be a mapping of band to level")
    if name not in table:
        raise ValueError("no ceiling declared for the %r band" % name)
    return validate_positive(table[name], "ceiling for %r" % name)


def projected_fallout_percent(fallout_rate_percent_per_day, exposure_days):
    """Return the obscuration the environment adds over the exposure left."""
    rate = validate_non_negative(
        fallout_rate_percent_per_day, "fallout_rate_percent_per_day"
    )
    days = validate_non_negative(exposure_days, "exposure_days")
    return rate * days


def _count_allowance(level_um, size_um, slope, reference_area_cm2):
    """Return the cumulative count a level admits at or above one size."""
    if size_um > level_um and not math.isclose(
        size_um, level_um, rel_tol=SELECTION_TOLERANCE
    ):
        return 0.0
    exponent = slope * (math.log10(level_um) ** 2 - math.log10(size_um) ** 2)
    return (10.0 ** exponent) * (reference_area_cm2 / DEFAULT_REFERENCE_AREA_CM2)


def level_obscuration_percent(
    level_um,
    channels=None,
    slope=DEFAULT_DISTRIBUTION_SLOPE,
    reference_area_cm2=DEFAULT_REFERENCE_AREA_CM2,
):
    """Return the obscuration a particulate level implies at delivery."""
    level = validate_positive(level_um, "level_um")
    gradient = validate_positive(slope, "slope")
    area = validate_positive(reference_area_cm2, "reference_area_cm2")
    if channels is None:
        sizes = [level * factor for factor in (0.05, 0.15, 0.3, 0.6, 1.0)]
    else:
        if not isinstance(channels, (list, tuple)) or len(channels) < 2:
            raise ValueError("channels must be a sequence of at least two sizes")
        sizes = [
            validate_positive(size, "channels[%d]" % index)
            for index, size in enumerate(channels)
        ]
        for index in range(1, len(sizes)):
            if sizes[index] <= sizes[index - 1]:
                raise ValueError("channels must strictly increase (index %d)" % index)
        sizes = [
            size
            for size in sizes
            if size < level or math.isclose(size, level, rel_tol=SELECTION_TOLERANCE)
        ]
        if len(sizes) < 2:
            raise ValueError(
                "at least two channels at or below the level label are needed"
            )
    counts = [_count_allowance(level, size, gradient, area) for size in sizes]
    total = 0.0
    for index in range(len(sizes) - 1):
        increment = counts[index] - counts[index + 1]
        if increment < 0.0:
            increment = 0.0
        representative = math.sqrt(sizes[index] * sizes[index + 1])
        radius_cm = 0.5 * representative * 1e-4
        total += 100.0 * increment * math.pi * radius_cm * radius_cm / area
    radius_cm = 0.5 * sizes[-1] * 1e-4
    total += 100.0 * counts[-1] * math.pi * radius_cm * radius_cm / area
    return total


def evaluate_candidate(level_um, spec):
    """Return the end-of-exposure obscuration record for one candidate level."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    level = validate_positive(level_um, "level_um")
    budget = validate_positive(
        spec["allowed_obscuration_percent"], "allowed_obscuration_percent"
    )
    margin = validate_positive(spec.get("margin_factor", 1.0), "margin_factor")
    if margin < 1.0:
        raise ValueError("margin_factor below unity removes margin instead of adding it")
    delivered = level_obscuration_percent(
        level,
        spec.get("size_channels"),
        spec.get("slope", DEFAULT_DISTRIBUTION_SLOPE),
        spec.get("reference_area_cm2", DEFAULT_REFERENCE_AREA_CM2),
    )
    accumulated = projected_fallout_percent(
        spec.get("fallout_rate_percent_per_day", 0.0), spec.get("exposure_days", 0.0)
    )
    end_of_exposure = delivered + accumulated
    with_margin = end_of_exposure * margin
    inside = with_margin < budget or math.isclose(
        with_margin, budget, rel_tol=SELECTION_TOLERANCE
    )
    return {
        "level_um": level,
        "delivered_obscuration_percent": delivered,
        "accumulated_obscuration_percent": accumulated,
        "end_of_exposure_percent": end_of_exposure,
        "with_margin_percent": with_margin,
        "budget_percent": budget,
        "inside_budget": inside,
    }


def select_particulate_level(spec):
    """Select the coarsest particulate level a hardware item may be held to.

    spec keys: band, allowed_obscuration_percent; optional ladder, ceilings,
    verification_floor_um, margin_factor, fallout_rate_percent_per_day,
    exposure_days, size_channels, slope and reference_area_cm2.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("band", "allowed_obscuration_percent"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    band = validate_band(spec["band"])
    ladder = validate_ladder(spec.get("ladder"))
    ceiling = category_ceiling_um(band, spec.get("ceilings"))
    floor = spec.get("verification_floor_um")
    if floor is not None:
        floor = validate_positive(floor, "verification_floor_um")
        if floor > ceiling and not math.isclose(
            floor, ceiling, rel_tol=SELECTION_TOLERANCE
        ):
            raise ValueError(
                "verification floor %g um is coarser than the %r band ceiling %g um"
                % (floor, band, ceiling)
            )
    records = [evaluate_candidate(level, spec) for level in ladder]
    findings = []
    budget = records[0]["budget_percent"]
    accumulated = records[0]["accumulated_obscuration_percent"]
    margin = validate_positive(spec.get("margin_factor", 1.0), "margin_factor")
    if accumulated * margin > budget and not math.isclose(
        accumulated * margin, budget, rel_tol=SELECTION_TOLERANCE
    ):
        findings.append(
            "projected fallout of %.6g%% already exceeds the %.6g%% budget with "
            "margin; no delivered level can recover it" % (accumulated, budget)
        )
    admissible = []
    for record in records:
        level = record["level_um"]
        record["within_ceiling"] = level < ceiling or math.isclose(
            level, ceiling, rel_tol=SELECTION_TOLERANCE
        )
        record["above_verification_floor"] = floor is None or (
            level > floor or math.isclose(level, floor, rel_tol=SELECTION_TOLERANCE)
        )
        if (
            record["inside_budget"]
            and record["within_ceiling"]
            and record["above_verification_floor"]
        ):
            admissible.append(record)
    selected = admissible[-1] if admissible else None
    driver = None
    if selected is None:
        if not any(r["inside_budget"] for r in records):
            findings.append(
                "no candidate level keeps the end-of-exposure obscuration inside "
                "the %.6g%% budget with the declared margin" % budget
            )
        elif not any(r["inside_budget"] and r["within_ceiling"] for r in records):
            findings.append(
                "every level inside the budget is coarser than the %g um ceiling "
                "the %r band sets" % (ceiling, band)
            )
        else:
            findings.append(
                "every admissible level is finer than the %g um verification floor"
                % floor
            )
    else:
        coarser = [r for r in records if r["level_um"] > selected["level_um"]]
        if not coarser:
            driver = "ladder-exhausted"
        elif not coarser[0]["within_ceiling"]:
            driver = "category-ceiling"
        else:
            driver = "obscuration-budget"
    return {
        "band": band,
        "ceiling_um": ceiling,
        "verification_floor_um": floor,
        "candidates": records,
        "admissible_levels_um": [r["level_um"] for r in admissible],
        "selected_level_um": None if selected is None else selected["level_um"],
        "selection": selected,
        "binding_constraint": driver,
        "selected": selected is not None,
        "findings": findings,
    }
