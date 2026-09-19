"""Cleaning a repaired board and proving it is clean again.

Anchor: ECSS-Q-ST-70-28C, verification clause -- the cleaning that follows a
repair or modification of a printed circuit board assembly, and the ionic
cleanliness measurement that demonstrates the residues the repair introduced
were actually removed. The cleanliness levels themselves are held against the
contamination and cleanliness control standard (ECSS-Q-ST-70-01C), which this
clause defers to rather than restating. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Match the cleaning agent to the flux that was used. A water-soluble flux is
   not removed by a solvent that never dissolved it, and a rosin residue is not
   removed by water alone; a no-clean residue that a soldering iron has been
   through is no longer a no-clean residue.
2. Size the extract: the wetted area of the item and the volume of solvent the
   extraction uses, because the reported figure is a mass per unit area and a
   starved extract reports a low number for the wrong reason.
3. Convert the net conductivity of the extract -- the reading with the system
   blank taken off it -- into a sodium-chloride-equivalent surface density.
4. Grade that density against the limit the item's cleanliness category carries
   and report the utilisation, not just the verdict.
5. Grade the visual state of the repair area, because a measurement made on an
   extract cannot see a residue that never dissolved into it.
6. Grade the drying and the delay between cleaning and verification, since an
   unmeasured board goes on accumulating handling residues.
7. Return the disposition with every finding and the criterion that governed.
"""

import math

__all__ = [
    "CLEANLINESS_LIMITS_UG_NACL_PER_CM2",
    "DEFAULT_CLEANLINESS_CATEGORY",
    "EXTRACT_RESPONSE_UG_PER_ML_PER_US_CM",
    "MIN_EXTRACT_VOLUME_ML_PER_CM2",
    "MIN_DRYING_MINUTES",
    "MAX_VERIFICATION_DELAY_HOURS",
    "FLUX_CLEANING_AGENTS",
    "RESIDUE_OBSERVATIONS",
    "TOLERANCE",
    "cleanliness_limit",
    "extract_area_cm2",
    "extract_volume_findings",
    "nacl_equivalent_ug_per_cm2",
    "cleanliness_utilisation",
    "cleaning_agent_findings",
    "visual_findings",
    "timing_findings",
    "assess_cleanliness_after_repair",
]

# Surface density of sodium-chloride-equivalent ionic residue allowed, in
# micrograms per square centimetre, by the cleanliness category the item is
# held to. The categories come from the contamination-control standard this
# clause defers to; the repair clause only requires that one of them be met.
CLEANLINESS_LIMITS_UG_NACL_PER_CM2 = {
    "standard": 1.56,
    "high-reliability": 1.00,
    "crewed-compartment": 0.75,
}
DEFAULT_CLEANLINESS_CATEGORY = "high-reliability"

# Calibration of the extraction system: micrograms of sodium-chloride
# equivalent per millilitre of extract per microsiemens per centimetre of net
# conductivity.
EXTRACT_RESPONSE_UG_PER_ML_PER_US_CM = 0.5

# A starved extract does not wet the whole item and reports a low figure for
# the wrong reason.
MIN_EXTRACT_VOLUME_ML_PER_CM2 = 1.5

# Entrapped solvent under a part keeps evolving residue after the measurement.
MIN_DRYING_MINUTES = 30.0

# The verification is evidence about the item as cleaned; a long gap between
# the cleaning and the measurement means it is evidence about something else.
MAX_VERIFICATION_DELAY_HOURS = 24.0

# Cleaning agents that actually remove each flux residue. A no-clean residue
# is listed because a repair has disturbed it: the iron has been through it
# and the encapsulating film it relied on is broken.
FLUX_CLEANING_AGENTS = {
    "rosin": ("isopropanol", "saponifier-water", "iso-water-blend"),
    "resin": ("isopropanol", "saponifier-water", "iso-water-blend"),
    "water-soluble": ("deionised-water", "iso-water-blend", "saponifier-water"),
    "no-clean": ("isopropanol", "iso-water-blend", "saponifier-water"),
    "synthetic-activated": ("saponifier-water", "iso-water-blend"),
}

# Things seen in the repair area that an extract conductivity cannot see.
RESIDUE_OBSERVATIONS = (
    "flux-residue",
    "white-residue",
    "particulate",
    "solvent-entrapment",
    "fibre",
    "solder-ball",
)

# Areas, volumes and conductivities are measured quantities; a value sitting on
# a bound is inside it, and this absorbs representation error only.
TOLERANCE = 1e-9


def _require_mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    return value


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _positive(value, label):
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _non_negative(value, label):
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, number))
    return number


def _token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def cleanliness_limit(category=DEFAULT_CLEANLINESS_CATEGORY):
    """Return the ionic cleanliness limit for a cleanliness category."""
    name = _token(category, "category")
    if name not in CLEANLINESS_LIMITS_UG_NACL_PER_CM2:
        raise ValueError(
            "unknown cleanliness category '%s'; known: %s"
            % (name, ", ".join(sorted(CLEANLINESS_LIMITS_UG_NACL_PER_CM2)))
        )
    return CLEANLINESS_LIMITS_UG_NACL_PER_CM2[name]


def extract_area_cm2(board_dimensions_mm, sides=2, extra_area_cm2=0.0):
    """Return the wetted area of the item in square centimetres."""
    if not isinstance(board_dimensions_mm, (list, tuple)) or len(board_dimensions_mm) != 2:
        raise ValueError("board_dimensions_mm must be a (length, width) pair in mm")
    length = _positive(board_dimensions_mm[0], "board length")
    width = _positive(board_dimensions_mm[1], "board width")
    if not isinstance(sides, int) or isinstance(sides, bool) or sides not in (1, 2):
        raise ValueError("sides must be 1 or 2, got %r" % (sides,))
    extra = _non_negative(extra_area_cm2, "extra_area_cm2")
    return (length * width / 100.0) * sides + extra


def extract_volume_findings(volume_ml, area_cm2):
    """Report an extract volume too small to wet the area it is measuring."""
    volume = _positive(volume_ml, "volume_ml")
    area = _positive(area_cm2, "area_cm2")
    ratio = volume / area
    findings = []
    if ratio < MIN_EXTRACT_VOLUME_ML_PER_CM2 - TOLERANCE:
        findings.append(
            "extract volume of %g mL over %g cm2 is %g mL/cm2, below the %g mL/cm2 "
            "the extraction needs to wet the item"
            % (volume, area, ratio, MIN_EXTRACT_VOLUME_ML_PER_CM2)
        )
    return findings


def nacl_equivalent_ug_per_cm2(
    conductivity_us_cm,
    blank_us_cm,
    volume_ml,
    area_cm2,
    response=EXTRACT_RESPONSE_UG_PER_ML_PER_US_CM,
):
    """Return the sodium-chloride-equivalent residue density of the extract."""
    reading = _non_negative(conductivity_us_cm, "conductivity_us_cm")
    blank = _non_negative(blank_us_cm, "blank_us_cm")
    volume = _positive(volume_ml, "volume_ml")
    area = _positive(area_cm2, "area_cm2")
    factor = _positive(response, "response")
    net = reading - blank
    if net < -TOLERANCE:
        raise ValueError(
            "extract conductivity %g uS/cm is below the system blank %g uS/cm; "
            "the blank or the reading is wrong" % (reading, blank)
        )
    if net < 0.0:
        net = 0.0
    return net * volume * factor / area


def cleanliness_utilisation(density_ug_per_cm2, category=DEFAULT_CLEANLINESS_CATEGORY):
    """Return the residue density as a fraction of its limit."""
    density = _non_negative(density_ug_per_cm2, "density_ug_per_cm2")
    return density / cleanliness_limit(category)


def cleaning_agent_findings(flux_category, agent):
    """Report a cleaning agent that does not remove the flux that was used."""
    flux = _token(flux_category, "flux_category")
    used = _token(agent, "agent")
    if flux not in FLUX_CLEANING_AGENTS:
        raise ValueError(
            "unknown flux category '%s'; known: %s"
            % (flux, ", ".join(sorted(FLUX_CLEANING_AGENTS)))
        )
    findings = []
    if used not in FLUX_CLEANING_AGENTS[flux]:
        findings.append(
            "cleaning agent '%s' does not remove a %s flux residue; use one of %s"
            % (used, flux, ", ".join(FLUX_CLEANING_AGENTS[flux]))
        )
    return findings


def visual_findings(observations):
    """Report residues seen in the repair area that an extract cannot see."""
    if isinstance(observations, str) or not isinstance(observations, (list, tuple, set)):
        raise ValueError("observations must be a sequence of observation tokens")
    findings = []
    for raw in observations:
        seen = _token(raw, "observation")
        if seen not in RESIDUE_OBSERVATIONS:
            raise ValueError(
                "unknown observation '%s'; known: %s"
                % (seen, ", ".join(RESIDUE_OBSERVATIONS))
            )
        findings.append(
            "'%s' remains visible in the repair area after cleaning" % seen
        )
    return findings


def timing_findings(drying_minutes, verification_delay_hours):
    """Grade the drying time and the gap between cleaning and verification."""
    drying = _non_negative(drying_minutes, "drying_minutes")
    delay = _non_negative(verification_delay_hours, "verification_delay_hours")
    findings = []
    if drying < MIN_DRYING_MINUTES - TOLERANCE:
        findings.append(
            "drying ran %g min, short of the %g min the item needs before a "
            "cleanliness measurement" % (drying, MIN_DRYING_MINUTES)
        )
    if delay > MAX_VERIFICATION_DELAY_HOURS + TOLERANCE:
        findings.append(
            "verification was made %g h after cleaning, beyond the %g h window; "
            "the result describes a differently handled item"
            % (delay, MAX_VERIFICATION_DELAY_HOURS)
        )
    return findings


def assess_cleanliness_after_repair(record):
    """Decide whether a repaired assembly has been shown to be clean.

    record keys: board_dimensions_mm, flux_category, cleaning_agent,
    extract_volume_ml, extract_conductivity_us_cm, blank_conductivity_us_cm,
    and optionally sides, extra_area_cm2, cleanliness_category,
    visual_observations, drying_minutes, verification_delay_hours.
    """
    _require_mapping(record, "record")
    required = (
        "board_dimensions_mm",
        "flux_category",
        "cleaning_agent",
        "extract_volume_ml",
        "extract_conductivity_us_cm",
        "blank_conductivity_us_cm",
    )
    for key in required:
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)

    category = record.get("cleanliness_category", DEFAULT_CLEANLINESS_CATEGORY)
    limit = cleanliness_limit(category)
    area = extract_area_cm2(
        record["board_dimensions_mm"],
        record.get("sides", 2),
        record.get("extra_area_cm2", 0.0),
    )
    volume = _positive(record["extract_volume_ml"], "extract_volume_ml")
    density = nacl_equivalent_ug_per_cm2(
        record["extract_conductivity_us_cm"],
        record["blank_conductivity_us_cm"],
        volume,
        area,
    )
    utilisation = density / limit

    findings = []
    findings.extend(cleaning_agent_findings(record["flux_category"], record["cleaning_agent"]))
    findings.extend(extract_volume_findings(volume, area))
    findings.extend(visual_findings(record.get("visual_observations", ())))
    findings.extend(
        timing_findings(
            record.get("drying_minutes", MIN_DRYING_MINUTES),
            record.get("verification_delay_hours", 0.0),
        )
    )

    over_limit = utilisation > 1.0 + TOLERANCE
    if over_limit:
        findings.append(
            "ionic residue of %g ug NaCl-eq/cm2 is %.3f times the %g ug/cm2 limit "
            "of the '%s' cleanliness category"
            % (density, utilisation, limit, _token(category, "category"))
        )
        governing = "ionic-cleanliness-limit"
    elif findings:
        governing = "supporting-evidence"
    else:
        governing = "ionic-cleanliness-limit"

    return {
        "cleanliness_category": _token(category, "category"),
        "limit_ug_per_cm2": limit,
        "wetted_area_cm2": area,
        "extract_volume_ml": volume,
        "residue_ug_per_cm2": density,
        "utilisation": utilisation,
        "margin_ug_per_cm2": limit - density,
        "governing_criterion": governing,
        "findings": findings,
        "verified_clean": not findings,
    }
