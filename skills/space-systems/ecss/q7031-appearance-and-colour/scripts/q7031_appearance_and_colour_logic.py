#!/usr/bin/env python3
"""Colour and appearance verification of an applied space-hardware paint.

Anchor: ECSS-Q-ST-70-31C, the Quality clause on appearance and colour. The
procedure below is a paraphrased, implementable restatement -- no verbatim
standard text. Offline, deterministic, Python standard library only.

Where a paint is specified by colour it is verified against a reference, not
against an opinion. On a thermal-control finish the colour is the visible half
of a radiative specification, so the same panel also owes its solar-absorptance
and infrared-emittance numbers. This module grades one painted area on all
three axes -- colour difference, gloss, appearance defects -- and on the
thermo-optical band, then dispositions it.
"""

import math

__all__ = [
    "APPEARANCE_DEFECTS",
    "DEFAULT_DELTA_E_LIMIT",
    "validate_lab",
    "colour_difference_de76",
    "colour_within_tolerance",
    "gloss_within_band",
    "categorize_appearance_defect",
    "defect_density_per_m2",
    "defect_findings",
    "thermo_optical_findings",
    "assess_painted_area",
    "assess_appearance_survey",
]

# A colour difference that lands exactly on its contract tolerance is a pass,
# and a decimal tolerance compared against a square root lands a few ULP either
# side of the bound depending on the libm. These tolerances absorb that, and
# only that; the contract limit itself is never widened.
COLOUR_REL_TOL = 1e-9
COLOUR_ABS_TOL = 1e-12

DEFAULT_DELTA_E_LIMIT = 1.5

# Appearance defects are grouped by what produced them, because the disposition
# differs: a flow defect is an application-parameter problem, a surface defect
# a contamination problem, an inclusion a facility-cleanliness problem.
APPEARANCE_DEFECTS = {
    "run": "flow",
    "sag": "flow",
    "curtain": "flow",
    "orange-peel": "atomization",
    "dry-spray": "atomization",
    "overspray": "atomization",
    "crater": "surface-contamination",
    "fish-eye": "surface-contamination",
    "blister": "surface-contamination",
    "pinhole": "surface-contamination",
    "inclusion": "particulate",
    "fibre": "particulate",
    "colour-mottling": "pigment-dispersion",
    "streak": "pigment-dispersion",
}

# Defects that betray a broken film are never tolerated by density: one is one
# too many on a surface whose job is radiative and adhesive continuity.
ZERO_TOLERANCE_DEFECTS = ("blister", "pinhole", "crater", "fish-eye")

DEFAULT_DEFECT_DENSITY_LIMIT_PER_M2 = 4.0


def _finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _at_or_below(value, bound):
    """True when value does not exceed bound, absorbing float noise at the bound."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=COLOUR_REL_TOL, abs_tol=COLOUR_ABS_TOL)


def validate_lab(colour, label="colour"):
    """Normalize one CIELAB triple, raising on anything unusable.

    L* is a lightness on a closed zero-to-hundred scale; a* and b* are signed
    opponent axes with no hard bound, but a magnitude past a few hundred is a
    transcription error rather than a measurement.
    """
    if isinstance(colour, dict):
        triple = (colour.get("L"), colour.get("a"), colour.get("b"))
    elif isinstance(colour, (list, tuple)) and len(colour) == 3:
        triple = tuple(colour)
    else:
        raise ValueError("%s must be an L,a,b triple or mapping, got %r" % (label, colour))
    lightness = _finite_number(triple[0], "%s L*" % label)
    a_axis = _finite_number(triple[1], "%s a*" % label)
    b_axis = _finite_number(triple[2], "%s b*" % label)
    if not 0.0 <= lightness <= 100.0:
        raise ValueError("%s L* must lie in 0..100, got %r" % (label, triple[0]))
    for name, axis in (("a*", a_axis), ("b*", b_axis)):
        if abs(axis) > 200.0:
            raise ValueError("%s %s magnitude %r is outside any real gamut" % (label, name, axis))
    return (lightness, a_axis, b_axis)


def colour_difference_de76(measured, reference):
    """Euclidean CIELAB colour difference between a measurement and its reference."""
    m_l, m_a, m_b = validate_lab(measured, "measured")
    r_l, r_a, r_b = validate_lab(reference, "reference")
    return math.sqrt((m_l - r_l) ** 2 + (m_a - r_a) ** 2 + (m_b - r_b) ** 2)


def colour_within_tolerance(measured, reference, limit=DEFAULT_DELTA_E_LIMIT):
    """True when the colour difference does not exceed the contract tolerance.

    A difference sitting exactly on the tolerance passes: the tolerance is the
    accepted value, not the first rejected one.
    """
    bound = _finite_number(limit, "delta_e_limit")
    if bound <= 0.0:
        raise ValueError("delta_e_limit must be strictly positive, got %r" % (limit,))
    return _at_or_below(colour_difference_de76(measured, reference), bound)


def gloss_within_band(gloss_units, band):
    """True when a specular gloss reading sits inside its specified band."""
    value = _finite_number(gloss_units, "gloss_units")
    if not 0.0 <= value <= 120.0:
        raise ValueError("gloss must lie in 0..120 gloss units, got %r" % (gloss_units,))
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("gloss band must be a low,high pair, got %r" % (band,))
    low = _finite_number(band[0], "gloss band low")
    high = _finite_number(band[1], "gloss band high")
    if high < low:
        raise ValueError("gloss band is inverted: %r" % (band,))
    return _at_or_below(low, value) and _at_or_below(value, high)


def categorize_appearance_defect(defect):
    """Return the mechanism family behind a named appearance defect."""
    if not isinstance(defect, str) or not defect.strip():
        raise ValueError("defect must be a non-empty string")
    key = defect.strip().lower()
    if key not in APPEARANCE_DEFECTS:
        raise ValueError("unrecognized appearance defect: %r" % (defect,))
    return APPEARANCE_DEFECTS[key]


def defect_density_per_m2(counts, area_m2):
    """Total defect count per square metre of inspected area."""
    area = _finite_number(area_m2, "area_m2")
    if area <= 0.0:
        raise ValueError("inspected area must be strictly positive, got %r" % (area_m2,))
    if not isinstance(counts, dict):
        raise ValueError("counts must be a mapping of defect to count")
    total = 0
    for defect, count in counts.items():
        categorize_appearance_defect(defect)
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError("count for %r must be an integer, got %r" % (defect, count))
        if count < 0:
            raise ValueError("count for %r cannot be negative" % (defect,))
        total += count
    return total / area


def defect_findings(counts, area_m2, density_limit=DEFAULT_DEFECT_DENSITY_LIMIT_PER_M2):
    """Findings raised by the appearance defect tally of one painted area."""
    limit = _finite_number(density_limit, "density_limit")
    if limit <= 0.0:
        raise ValueError("density_limit must be strictly positive, got %r" % (density_limit,))
    density = defect_density_per_m2(counts, area_m2)
    findings = []
    for defect, count in sorted(counts.items()):
        if count > 0 and defect.strip().lower() in ZERO_TOLERANCE_DEFECTS:
            findings.append("film-integrity-defect:%s" % defect.strip().lower())
    if not _at_or_below(density, limit):
        findings.append("defect-density-exceeded")
    families = sorted(
        {categorize_appearance_defect(d) for d, c in counts.items() if c > 0}
    )
    return {"density_per_m2": density, "families": families, "findings": sorted(findings)}


def thermo_optical_findings(measured, bands):
    """Findings from the solar-absorptance and infrared-emittance readings.

    A thermal-control paint that matches its colour chip but sits outside its
    absorptance or emittance band has failed the property the coating exists
    for, so both are graded whenever a band is on the drawing.
    """
    if bands is None:
        return ["thermo-optical-band-absent"]
    if not isinstance(bands, dict):
        raise ValueError("bands must be a mapping, got %r" % type(bands))
    if not isinstance(measured, dict):
        raise ValueError("measured thermo-optical values must be a mapping")
    findings = []
    for key, label in (("absorptance", "solar-absorptance"),
                       ("emittance", "infrared-emittance")):
        band = bands.get(key)
        if band is None:
            findings.append("%s-band-absent" % label)
            continue
        if not isinstance(band, (list, tuple)) or len(band) != 2:
            raise ValueError("%s band must be a low,high pair, got %r" % (label, band))
        low = _finite_number(band[0], "%s low" % label)
        high = _finite_number(band[1], "%s high" % label)
        if high < low:
            raise ValueError("%s band is inverted" % label)
        if key not in measured:
            findings.append("%s-not-measured" % label)
            continue
        value = _finite_number(measured[key], label)
        if not 0.0 <= value <= 1.0:
            raise ValueError("%s must lie in 0..1, got %r" % (label, measured[key]))
        if not (_at_or_below(low, value) and _at_or_below(value, high)):
            findings.append("%s-outside-band" % label)
    return sorted(findings)


def assess_painted_area(area):
    """Grade one painted area on colour, gloss, appearance and thermo-optics."""
    if not isinstance(area, dict):
        raise ValueError("area must be a mapping, got %r" % type(area))
    name = area.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("painted area requires a non-empty name")
    findings = []

    limit = area.get("delta_e_limit", DEFAULT_DELTA_E_LIMIT)
    delta_e = colour_difference_de76(area.get("measured_lab"), area.get("reference_lab"))
    if not colour_within_tolerance(area.get("measured_lab"), area.get("reference_lab"), limit):
        findings.append("colour-difference-exceeded")

    gloss_band = area.get("gloss_band")
    gloss = area.get("gloss_units")
    if gloss_band is None or gloss is None:
        findings.append("gloss-not-verified")
    elif not gloss_within_band(gloss, gloss_band):
        findings.append("gloss-outside-band")

    defects = defect_findings(
        area.get("defects", {}),
        area.get("area_m2"),
        area.get("defect_density_limit", DEFAULT_DEFECT_DENSITY_LIMIT_PER_M2),
    )
    findings.extend(defects["findings"])

    thermal = area.get("thermal_control", False)
    if thermal:
        findings.extend(
            thermo_optical_findings(area.get("thermo_optical", {}), area.get("thermo_optical_bands"))
        )

    findings = sorted(set(findings))
    integrity = [f for f in findings if f.startswith("film-integrity-defect")]
    optical = [f for f in findings if f.endswith("-outside-band") or f == "colour-difference-exceeded"]
    if not findings:
        disposition = "accepted"
    elif integrity or optical:
        disposition = "rework-required"
    else:
        disposition = "review-required"
    return {
        "name": name.strip(),
        "delta_e": delta_e,
        "defect_density_per_m2": defects["density_per_m2"],
        "defect_families": defects["families"],
        "findings": findings,
        "disposition": disposition,
        "accepted": disposition == "accepted",
    }


def assess_appearance_survey(areas):
    """Grade a set of painted areas; the survey passes only when each area does."""
    if not isinstance(areas, (list, tuple)) or not areas:
        raise ValueError("at least one painted area is required")
    results = [assess_painted_area(item) for item in areas]
    names = [item["name"] for item in results]
    if len(set(names)) != len(names):
        raise ValueError("painted area names must be unique within a survey")
    open_findings = sorted(
        "%s:%s" % (item["name"], finding)
        for item in results
        for finding in item["findings"]
    )
    return {
        "areas": results,
        "rework_areas": sorted(i["name"] for i in results if i["disposition"] == "rework-required"),
        "open_findings": open_findings,
        "survey_accepted": not open_findings,
    }
