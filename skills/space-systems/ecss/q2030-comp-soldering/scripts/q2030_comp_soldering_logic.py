"""Complementary soldering requirements for an electrical harness.

Anchor: ECSS-Q-ST-20-30C section 7.3 (paraphrased into an implementable
procedure; no standard text is reproduced). Section 7.3 adds
requirements on top of the soldered-termination and crimp acceptance
criteria of the external basis; this module grades those additions.
The numeric constants below are the representative defaults a project
tailors; the procedure is what this module fixes.

Procedure implemented here:

1. Grade the alloy. A solder with too little lead behaves as near pure
   tin and grows whiskers, so it is admissible only behind a declared
   whisker mitigation plan. A stated composition that does not add up
   is an input error rather than a finding.
2. Grade the flux. A non-activated or mildly activated flux is
   admissible as used; an activated or water-soluble flux obliges a
   cleaning step, and an uncleaned joint made with one is a finding.
3. Grade the thermal exposure. The dwell a joint can take scales with
   the conductor cross-section, because a heavier conductor needs
   longer to reach temperature; reheats spend from the same budget, so
   the total exposure is dwell times the number of heat applications.
   An iron tip outside its temperature window is a finding in its own
   right: too cold makes a joint that never wetted, too hot damages
   insulation and the conductor.
4. Grade the geometry. The insulation has to stop short of the
   termination, inside a window: too close and the insulation is
   damaged and the joint cannot be inspected, too far and bare
   conductor is exposed.
5. Grade the wetting. A wetting angle above the acceptance value says
   the solder did not wet the conductor, whatever the joint looks like.
6. Grade the workmanship record: the inspection magnification owed by
   the conductor size, and the currency of the operator certification.

Stdlib only, offline, deterministic.
"""

# Lead content below which the alloy behaves as near pure tin.
MIN_LEAD_CONTENT_PERCENT = 3.0

FLUX_NON_ACTIVATED = "rosin-non-activated"
FLUX_MILDLY_ACTIVATED = "rosin-mildly-activated"
FLUX_ACTIVATED = "rosin-activated"
FLUX_WATER_SOLUBLE = "water-soluble"
VALID_FLUX_TYPES = (
    FLUX_NON_ACTIVATED,
    FLUX_MILDLY_ACTIVATED,
    FLUX_ACTIVATED,
    FLUX_WATER_SOLUBLE,
)
FLUX_REQUIRING_CLEANING = (FLUX_ACTIVATED, FLUX_WATER_SOLUBLE)

MIN_TIP_TEMPERATURE_C = 260.0
MAX_TIP_TEMPERATURE_C = 370.0

# Dwell scales with conductor cross-section, with a floor for fine
# gauges that reach temperature almost immediately.
DWELL_S_PER_MM2 = 3.0
MIN_DWELL_S = 1.0

# Heat applications a joint is allowed: the original plus the reheats.
MAX_HEAT_APPLICATIONS = 3

MIN_INSULATION_CLEARANCE_MM = 0.25
INSULATION_CLEARANCE_DIAMETER_FACTOR = 2.0

MAX_WETTING_ANGLE_DEG = 30.0

OPERATOR_CERTIFICATION_VALIDITY_DAYS = 730

# Inspection magnification owed by conductor cross-section: the finer
# the conductor, the higher the magnification.
MAGNIFICATION_BANDS = (
    (0.10, 10.0),
    (0.50, 6.0),
)
COARSE_MAGNIFICATION = 4.0

# Times, angles and distances are products of measured floats, so a
# value sitting exactly on its limit can land a few units in the last
# place beyond it. These tolerances are far below any shop-floor
# resolution and absorb that representation error without relaxing the
# limits themselves.
TIME_TOLERANCE_S = 1.0e-9
DISTANCE_TOLERANCE_MM = 1.0e-9
ANGLE_TOLERANCE_DEG = 1.0e-9
TEMPERATURE_TOLERANCE_C = 1.0e-9
PERCENT_TOLERANCE = 1.0e-9


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_termination(termination):
    """Validate one soldered termination record and normalize it."""
    if not isinstance(termination, dict):
        raise ValueError("termination must be a mapping")
    term_id = termination.get("id")
    if not isinstance(term_id, str) or not term_id.strip():
        raise ValueError("termination needs a non-empty string id")
    tin = _numeric("termination %s tin_percent" % term_id, termination.get("tin_percent"), 0.0)
    lead = _numeric(
        "termination %s lead_percent" % term_id, termination.get("lead_percent"), 0.0
    )
    if tin + lead > 100.0 + PERCENT_TOLERANCE:
        raise ValueError(
            "termination %s alloy composition sums above 100 percent" % term_id
        )
    if tin + lead <= 0.0:
        raise ValueError("termination %s has no alloy composition" % term_id)
    flux = termination.get("flux_type")
    if flux not in VALID_FLUX_TYPES:
        raise ValueError(
            "termination %s has unknown flux_type %r (expected one of %s)"
            % (term_id, flux, ", ".join(VALID_FLUX_TYPES))
        )
    area = _numeric(
        "termination %s cross_section_mm2" % term_id,
        termination.get("cross_section_mm2"),
    )
    if area <= 0:
        raise ValueError("termination %s cross_section_mm2 must be positive" % term_id)
    insulation_diameter = _numeric(
        "termination %s insulation_diameter_mm" % term_id,
        termination.get("insulation_diameter_mm"),
    )
    if insulation_diameter <= 0:
        raise ValueError(
            "termination %s insulation_diameter_mm must be positive" % term_id
        )
    reheats = termination.get("reheats", 0)
    if not isinstance(reheats, int) or isinstance(reheats, bool) or reheats < 0:
        raise ValueError("termination %s reheats must be an integer >= 0" % term_id)
    days = termination.get("days_since_operator_certification", 0)
    if not isinstance(days, int) or isinstance(days, bool) or days < 0:
        raise ValueError(
            "termination %s days_since_operator_certification must be an "
            "integer >= 0" % term_id
        )
    return {
        "id": term_id,
        "tin_percent": tin,
        "lead_percent": lead,
        "whisker_mitigation_plan": _boolean(
            "termination %s whisker_mitigation_plan" % term_id,
            termination.get("whisker_mitigation_plan", False),
        ),
        "flux_type": flux,
        "cleaned_after_soldering": _boolean(
            "termination %s cleaned_after_soldering" % term_id,
            termination.get("cleaned_after_soldering", False),
        ),
        "cross_section_mm2": area,
        "insulation_diameter_mm": insulation_diameter,
        "insulation_clearance_mm": _numeric(
            "termination %s insulation_clearance_mm" % term_id,
            termination.get("insulation_clearance_mm", 0.0),
            0.0,
        ),
        "tip_temperature_c": _numeric(
            "termination %s tip_temperature_c" % term_id,
            termination.get("tip_temperature_c"),
        ),
        "dwell_s": _numeric(
            "termination %s dwell_s" % term_id, termination.get("dwell_s"), 0.0
        ),
        "reheats": reheats,
        "wetting_angle_deg": _numeric(
            "termination %s wetting_angle_deg" % term_id,
            termination.get("wetting_angle_deg", 0.0),
            0.0,
        ),
        "inspection_magnification": _numeric(
            "termination %s inspection_magnification" % term_id,
            termination.get("inspection_magnification", 0.0),
            0.0,
        ),
        "days_since_operator_certification": days,
    }


def allowable_dwell_s(cross_section_mm2):
    """Dwell one heat application may take, in seconds."""
    area = _numeric("cross_section_mm2", cross_section_mm2)
    if area <= 0:
        raise ValueError("cross_section_mm2 must be positive")
    scaled = DWELL_S_PER_MM2 * area
    return scaled if scaled > MIN_DWELL_S else MIN_DWELL_S


def thermal_exposure_budget_s(cross_section_mm2):
    """Total heat time a termination may take across all applications."""
    return allowable_dwell_s(cross_section_mm2) * MAX_HEAT_APPLICATIONS


def total_thermal_exposure_s(dwell_s, reheats):
    """Heat time actually spent: one dwell per heat application."""
    dwell = _numeric("dwell_s", dwell_s, 0.0)
    if not isinstance(reheats, int) or isinstance(reheats, bool) or reheats < 0:
        raise ValueError("reheats must be an integer >= 0")
    return dwell * (reheats + 1)


def insulation_clearance_window_mm(insulation_diameter_mm):
    """Window the insulation end may sit in, in mm."""
    diameter = _numeric("insulation_diameter_mm", insulation_diameter_mm)
    if diameter <= 0:
        raise ValueError("insulation_diameter_mm must be positive")
    upper = INSULATION_CLEARANCE_DIAMETER_FACTOR * diameter
    if upper <= MIN_INSULATION_CLEARANCE_MM:
        raise ValueError(
            "insulation diameter %r gives no usable clearance window"
            % (insulation_diameter_mm,)
        )
    return MIN_INSULATION_CLEARANCE_MM, upper


def minimum_inspection_magnification(cross_section_mm2):
    """Magnification the conductor size obliges for inspection."""
    area = _numeric("cross_section_mm2", cross_section_mm2)
    if area <= 0:
        raise ValueError("cross_section_mm2 must be positive")
    for upper, magnification in MAGNIFICATION_BANDS:
        if area <= upper:
            return magnification
    return COARSE_MAGNIFICATION


def alloy_findings(termination):
    """Findings about the solder alloy of one termination."""
    norm = validate_termination(termination)
    if norm["lead_percent"] + PERCENT_TOLERANCE < MIN_LEAD_CONTENT_PERCENT:
        if not norm["whisker_mitigation_plan"]:
            return ["near-pure-tin-alloy-without-a-whisker-mitigation-plan"]
    return []


def flux_findings(termination):
    """Findings about the flux used on one termination."""
    norm = validate_termination(termination)
    if norm["flux_type"] in FLUX_REQUIRING_CLEANING and not norm["cleaned_after_soldering"]:
        return ["activated-flux-residue-left-on-the-termination"]
    return []


def thermal_findings(termination):
    """Findings about the thermal exposure of one termination."""
    norm = validate_termination(termination)
    findings = []
    tip = norm["tip_temperature_c"]
    if tip + TEMPERATURE_TOLERANCE_C < MIN_TIP_TEMPERATURE_C:
        findings.append("iron-tip-temperature-below-the-window")
    elif tip > MAX_TIP_TEMPERATURE_C + TEMPERATURE_TOLERANCE_C:
        findings.append("iron-tip-temperature-above-the-window")
    if norm["reheats"] + 1 > MAX_HEAT_APPLICATIONS:
        findings.append("heat-applications-above-the-allowance")
    spent = total_thermal_exposure_s(norm["dwell_s"], norm["reheats"])
    if spent > thermal_exposure_budget_s(norm["cross_section_mm2"]) + TIME_TOLERANCE_S:
        findings.append("thermal-exposure-above-the-scaled-budget")
    return findings


def geometry_findings(termination):
    """Findings about the insulation clearance of one termination."""
    norm = validate_termination(termination)
    lower, upper = insulation_clearance_window_mm(norm["insulation_diameter_mm"])
    clearance = norm["insulation_clearance_mm"]
    if clearance + DISTANCE_TOLERANCE_MM < lower:
        return ["insulation-clearance-below-the-window"]
    if clearance > upper + DISTANCE_TOLERANCE_MM:
        return ["insulation-clearance-above-the-window"]
    return []


def wetting_findings(termination):
    """Findings about the wetting of one termination."""
    norm = validate_termination(termination)
    if norm["wetting_angle_deg"] > MAX_WETTING_ANGLE_DEG + ANGLE_TOLERANCE_DEG:
        return ["wetting-angle-above-the-acceptance-value"]
    return []


def workmanship_findings(termination):
    """Findings about inspection and operator certification."""
    norm = validate_termination(termination)
    findings = []
    owed = minimum_inspection_magnification(norm["cross_section_mm2"])
    if norm["inspection_magnification"] + DISTANCE_TOLERANCE_MM < owed:
        findings.append("inspection-magnification-below-the-owed-value")
    if norm["days_since_operator_certification"] > OPERATOR_CERTIFICATION_VALIDITY_DAYS:
        findings.append("operator-certification-out-of-currency")
    return findings


def assess_solder_termination(termination):
    """Assess one soldered termination against section 7.3."""
    norm = validate_termination(termination)
    findings = list(alloy_findings(norm))
    findings.extend(flux_findings(norm))
    findings.extend(thermal_findings(norm))
    findings.extend(geometry_findings(norm))
    findings.extend(wetting_findings(norm))
    findings.extend(workmanship_findings(norm))
    lower, upper = insulation_clearance_window_mm(norm["insulation_diameter_mm"])
    return {
        "id": norm["id"],
        "allowable_dwell_s": allowable_dwell_s(norm["cross_section_mm2"]),
        "thermal_exposure_budget_s": thermal_exposure_budget_s(norm["cross_section_mm2"]),
        "thermal_exposure_s": total_thermal_exposure_s(norm["dwell_s"], norm["reheats"]),
        "insulation_clearance_window_mm": (lower, upper),
        "owed_inspection_magnification": minimum_inspection_magnification(
            norm["cross_section_mm2"]
        ),
        "findings": findings,
        "compliant": not findings,
    }


def assess_soldering_lot(terminations):
    """Run the section 7.3 assessment over a lot of terminations."""
    if not isinstance(terminations, list) or not terminations:
        raise ValueError("terminations must be a non-empty list")
    results = []
    seen = set()
    for termination in terminations:
        result = assess_solder_termination(termination)
        if result["id"] in seen:
            raise ValueError("duplicate termination id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    non_compliant = [r["id"] for r in results if not r["compliant"]]
    grouped = {}
    for result in results:
        for finding in result["findings"]:
            grouped[finding] = grouped.get(finding, 0) + 1
    return {
        "terminations": results,
        "findings_by_type": grouped,
        "non_compliant_ids": non_compliant,
        "non_compliant_fraction": len(non_compliant) / len(results),
        "compliant": not non_compliant,
    }
