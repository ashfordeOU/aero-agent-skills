"""Method variants of the thermal-vacuum outgassing screening test.

Anchor: ECSS-Q-ST-70-02C, the method-control clause governing permitted
departures from the baseline screening run (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. The baseline run is fixed: a preconditioning period at laboratory
   humidity, a bake at the screening temperature for the screening
   duration, and a condensable collection. Every variant is a named
   departure from exactly one of those.
2. Variants are indicated by properties of the material, not chosen for
   convenience. A hygroscopic material indicates the water-vapour
   regained determination and a longer preconditioning period; a
   material whose maximum use temperature sits under the screening
   temperature indicates a reduced bake; a thick specimen indicates a
   longer bake.
3. The water-vapour regained determination adds a reconditioning
   weighing after the bake. The regained mass, over the mass the
   specimen started with, is the regained figure, and the total loss
   with that figure removed is the recovered mass loss. It adds
   information without changing the bake, so results stay comparable
   with the baseline data set.
4. Changing the bake itself does not. A run at a lower temperature or
   for a longer period produces a number that is defensible for that
   material and not interchangeable with a baseline figure, and saying
   so is part of the result.
5. A variant applied without the property that indicates it, and an
   indicated variant left unapplied, are both findings -- the first
   invents a departure, the second tests a material under conditions it
   cannot equilibrate to.

Stdlib only, offline, deterministic.
"""

STANDARD_PRECONDITIONING_DURATION_H = 24.0
STANDARD_BAKE_TEMPERATURE_C = 125.0
STANDARD_BAKE_DURATION_H = 24.0
STANDARD_RECONDITIONING_DURATION_H = 24.0

# A bake far under the screening temperature stops mobilising the
# species the screening exists to find.
MIN_BAKE_TEMPERATURE_C = 50.0

# Material properties that indicate a variant.
HYGROSCOPIC_UPTAKE_PCT = 0.50
THICK_SPECIMEN_MM = 3.0

WATER_VAPOUR_REGAINED = "water-vapour-regained"
EXTENDED_PRECONDITIONING = "extended-preconditioning"
REDUCED_BAKE_TEMPERATURE = "reduced-bake-temperature"
EXTENDED_BAKE_DURATION = "extended-bake-duration"

# Each variant: what it alters, and whether a result produced under it
# stays directly comparable with baseline screening data.
VARIANTS = {
    WATER_VAPOUR_REGAINED: {
        "alters": "adds-a-reconditioning-weighing-after-the-bake",
        "comparable": True,
    },
    EXTENDED_PRECONDITIONING: {
        "alters": "lengthens-the-preconditioning-period",
        "comparable": True,
    },
    REDUCED_BAKE_TEMPERATURE: {
        "alters": "lowers-the-bake-temperature",
        "comparable": False,
    },
    EXTENDED_BAKE_DURATION: {
        "alters": "lengthens-the-bake-period",
        "comparable": False,
    },
}

VALID_VARIANTS = tuple(sorted(VARIANTS))

DIRECTLY_COMPARABLE = "directly-comparable-with-baseline-screening"
NOT_DIRECTLY_COMPARABLE = "not-directly-comparable-with-baseline-screening"

# Durations and percentages are compared against decimal literals, so a
# value sitting exactly on a bound can land a few units in the last
# place past it. This tolerance absorbs that representation error only.
TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None):
    """Return value as a float, raising on anything that is not a number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def variant_record(name):
    """Definition of one named variant, as a copied mapping."""
    if name not in VARIANTS:
        raise ValueError(
            "unknown method variant %r (expected one of %s)"
            % (name, ", ".join(VALID_VARIANTS))
        )
    return dict(VARIANTS[name])


def indicated_variants(material):
    """Variants the material's own properties call for."""
    if not isinstance(material, dict):
        raise ValueError("material must be a mapping")
    indicated = []
    uptake = material.get("moisture_uptake_pct")
    if uptake is not None:
        if _numeric("moisture_uptake_pct", uptake, 0.0) >= (
            HYGROSCOPIC_UPTAKE_PCT - TOLERANCE
        ):
            indicated.append(WATER_VAPOUR_REGAINED)
            indicated.append(EXTENDED_PRECONDITIONING)
    max_use = material.get("maximum_use_temperature_c")
    if max_use is not None:
        if _numeric("maximum_use_temperature_c", max_use) < (
            STANDARD_BAKE_TEMPERATURE_C - TOLERANCE
        ):
            indicated.append(REDUCED_BAKE_TEMPERATURE)
    thickness = material.get("specimen_thickness_mm")
    if thickness is not None:
        if _numeric("specimen_thickness_mm", thickness, 0.0) > (
            THICK_SPECIMEN_MM + TOLERANCE
        ):
            indicated.append(EXTENDED_BAKE_DURATION)
    return sorted(set(indicated))


def validate_request(request):
    """Validate a variant request and return a normalized copy."""
    if not isinstance(request, dict):
        raise ValueError("request must be a mapping")
    applied = request.get("applied_variants", [])
    if not isinstance(applied, (list, tuple)):
        raise ValueError("applied_variants must be a sequence")
    names = []
    for name in applied:
        variant_record(name)
        if name in names:
            raise ValueError("variant %r applied twice" % (name,))
        names.append(name)

    precondition = _numeric(
        "preconditioning_duration_h",
        request.get("preconditioning_duration_h", STANDARD_PRECONDITIONING_DURATION_H),
        0.0,
    )
    bake_temp = _numeric(
        "bake_temperature_c",
        request.get("bake_temperature_c", STANDARD_BAKE_TEMPERATURE_C),
    )
    bake_hours = _numeric(
        "bake_duration_h",
        request.get("bake_duration_h", STANDARD_BAKE_DURATION_H),
        0.0,
    )
    recondition = request.get("reconditioning_duration_h")
    if recondition is not None:
        recondition = _numeric("reconditioning_duration_h", recondition, 0.0)

    if bake_temp > STANDARD_BAKE_TEMPERATURE_C + TOLERANCE:
        raise ValueError(
            "bake_temperature_c %r is above the screening temperature %r"
            % (bake_temp, STANDARD_BAKE_TEMPERATURE_C)
        )
    if bake_temp < MIN_BAKE_TEMPERATURE_C - TOLERANCE:
        raise ValueError(
            "bake_temperature_c %r is below the floor the method permits %r"
            % (bake_temp, MIN_BAKE_TEMPERATURE_C)
        )
    if precondition < STANDARD_PRECONDITIONING_DURATION_H - TOLERANCE:
        raise ValueError(
            "preconditioning_duration_h %r is under the baseline period %r"
            % (precondition, STANDARD_PRECONDITIONING_DURATION_H)
        )
    if bake_hours < STANDARD_BAKE_DURATION_H - TOLERANCE:
        raise ValueError(
            "bake_duration_h %r is under the baseline period %r"
            % (bake_hours, STANDARD_BAKE_DURATION_H)
        )
    return {
        "applied_variants": sorted(names),
        "preconditioning_duration_h": precondition,
        "bake_temperature_c": bake_temp,
        "bake_duration_h": bake_hours,
        "reconditioning_duration_h": recondition,
        "material": request.get("material", {}),
    }


def check_variant_settings(request):
    """Findings where an applied variant and the run settings disagree."""
    norm = validate_request(request)
    applied = set(norm["applied_variants"])
    findings = []

    extended_precondition = norm["preconditioning_duration_h"] > (
        STANDARD_PRECONDITIONING_DURATION_H + TOLERANCE
    )
    if EXTENDED_PRECONDITIONING in applied and not extended_precondition:
        findings.append("extended-preconditioning-declared-at-the-baseline-period")
    if extended_precondition and EXTENDED_PRECONDITIONING not in applied:
        findings.append("preconditioning-lengthened-without-declaring-the-variant")

    reduced_bake = norm["bake_temperature_c"] < (
        STANDARD_BAKE_TEMPERATURE_C - TOLERANCE
    )
    if REDUCED_BAKE_TEMPERATURE in applied and not reduced_bake:
        findings.append("reduced-bake-declared-at-the-screening-temperature")
    if reduced_bake and REDUCED_BAKE_TEMPERATURE not in applied:
        findings.append("bake-temperature-lowered-without-declaring-the-variant")

    extended_bake = norm["bake_duration_h"] > (STANDARD_BAKE_DURATION_H + TOLERANCE)
    if EXTENDED_BAKE_DURATION in applied and not extended_bake:
        findings.append("extended-bake-declared-at-the-baseline-period")
    if extended_bake and EXTENDED_BAKE_DURATION not in applied:
        findings.append("bake-lengthened-without-declaring-the-variant")

    recondition = norm["reconditioning_duration_h"]
    if WATER_VAPOUR_REGAINED in applied:
        if recondition is None:
            findings.append("water-vapour-variant-without-a-reconditioning-period")
        elif recondition < STANDARD_RECONDITIONING_DURATION_H - TOLERANCE:
            findings.append("reconditioning-period-shorter-than-the-method-requires")
    elif recondition is not None:
        findings.append("reconditioning-recorded-without-declaring-the-variant")
    return findings


def water_vapour_regained_pct(
    mass_after_bake_g, mass_after_reconditioning_g, initial_mass_g
):
    """Mass regained in reconditioning, as a percentage of the initial mass."""
    baked = _numeric("mass_after_bake_g", mass_after_bake_g, 0.0)
    recovered = _numeric("mass_after_reconditioning_g", mass_after_reconditioning_g, 0.0)
    initial = _numeric("initial_mass_g", initial_mass_g)
    if initial <= 0:
        raise ValueError("initial_mass_g must be positive")
    if recovered < baked - TOLERANCE:
        raise ValueError(
            "reconditioned mass %r is below the post-bake mass %r"
            % (recovered, baked)
        )
    if recovered > initial + TOLERANCE:
        raise ValueError(
            "reconditioned mass %r exceeds the initial mass %r" % (recovered, initial)
        )
    return (recovered - baked) / initial * 100.0


def recovered_mass_loss_pct(total_mass_loss_pct, water_vapour_regained):
    """Total mass loss with the regained water removed, in percent."""
    tml = _numeric("total_mass_loss_pct", total_mass_loss_pct, 0.0)
    wvr = _numeric("water_vapour_regained", water_vapour_regained, 0.0)
    if wvr > tml + TOLERANCE:
        raise ValueError(
            "water_vapour_regained %r exceeds total_mass_loss_pct %r" % (wvr, tml)
        )
    return max(tml - wvr, 0.0)


def comparability(applied_variants):
    """Whether results under these variants compare with baseline data."""
    if not isinstance(applied_variants, (list, tuple)):
        raise ValueError("applied_variants must be a sequence")
    breaking = []
    for name in applied_variants:
        if not variant_record(name)["comparable"]:
            breaking.append(name)
    status = NOT_DIRECTLY_COMPARABLE if breaking else DIRECTLY_COMPARABLE
    return status, sorted(set(breaking))


def assess_method_variants(request):
    """Assess a variant request against the material that indicated it."""
    norm = validate_request(request)
    material = norm["material"]
    if not isinstance(material, dict):
        raise ValueError("material must be a mapping")

    applied = norm["applied_variants"]
    indicated = indicated_variants(material)
    findings = list(check_variant_settings(norm))

    missing = [name for name in indicated if name not in applied]
    unindicated = [name for name in applied if name not in indicated]
    if missing:
        findings.append("indicated-variant-not-applied")
    if unindicated and material:
        findings.append("variant-applied-without-an-indicating-material-property")

    status, breaking = comparability(applied)

    regained = None
    recovered = None
    weighings = request.get("weighings")
    if WATER_VAPOUR_REGAINED in applied and isinstance(weighings, dict):
        regained = water_vapour_regained_pct(
            weighings.get("mass_after_bake_g"),
            weighings.get("mass_after_reconditioning_g"),
            weighings.get("initial_mass_g"),
        )
        total = weighings.get("total_mass_loss_pct")
        if total is not None:
            recovered = recovered_mass_loss_pct(total, regained)

    return {
        "applied_variants": applied,
        "indicated_variants": indicated,
        "missing_variants": missing,
        "unindicated_variants": unindicated,
        "comparability": status,
        "comparability_breaking_variants": breaking,
        "water_vapour_regained_pct": regained,
        "recovered_mass_loss_pct": recovered,
        "findings": findings,
        "acceptable": not findings,
    }
