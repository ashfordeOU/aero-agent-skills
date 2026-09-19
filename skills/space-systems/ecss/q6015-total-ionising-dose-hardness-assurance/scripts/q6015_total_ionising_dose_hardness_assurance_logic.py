"""Total-ionising-dose hardness assurance for an equipment parts list.

Anchor: ECSS-Q-ST-60-15C clause 5.1 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Fix the mission dose. The environment specification supplies a
   dose-depth curve -- ionising dose against equivalent aluminium
   shielding -- for a stated mission duration. A part does not see the
   curve's headline number, it sees the curve read at the shielding
   its own location provides.
2. Scale to the radiation lifetime the design has to cover. A curve
   issued for one duration is scaled to the required lifetime before
   it becomes a design dose, because the lifetime the equipment is
   qualified for is the lifetime the margin is carried over.
3. Divide the part's demonstrated dose capability by the design dose
   to get the achieved radiation design margin.
4. Pick the required margin from the evidence the capability rests on,
   and from the programme phase. Generic family data buys a wide
   margin early and stops being acceptable once the design is frozen;
   a flight-lot test buys the narrowest margin.
5. Group each part by the dose sensitivity of its demonstrated
   capability so families can be steered at selection time.
6. Aggregate: the tightest part drives the equipment verdict, and a
   part whose capability rests on no radiation test is reported even
   when its arithmetic margin looks comfortable.

Stdlib only, offline, deterministic.
"""

import math

# Required radiation design margin by the evidence the dose capability
# rests on. None means the capability is not supported by a radiation
# test at all, so no margin makes it usable as it stands.
EVIDENCE_REQUIRED_MARGIN = {
    "flight-lot-test": 2.0,
    "same-part-other-lot": 3.0,
    "similar-part-data": 5.0,
    "generic-family-data": 10.0,
    "no-test-evidence": None,
}

# Programme phases in order. From the design-freeze phase onward a
# capability resting on generic family data is a finding: the part is
# by then a specific part from a specific maker and owes real data.
PROGRAMME_PHASES = (
    "proposal",
    "phase-a",
    "phase-b",
    "phase-c",
    "phase-d",
)
DESIGN_FREEZE_PHASE = "phase-c"

# Dose sensitivity bands on the demonstrated capability, in krad(Si).
# Read as "at least this capability", highest band first.
DOSE_SENSITIVITY_BANDS = (
    (300.0, "dose-hard"),
    (100.0, "dose-tolerant"),
    (30.0, "dose-sensitive"),
    (10.0, "dose-very-sensitive"),
    (0.0, "dose-critical"),
)

# A margin is a quotient of two interpolated floats, so a part sitting
# exactly on its required margin can land a few units in the last place
# below it. This relative tolerance absorbs that representation error
# without relaxing the required margin itself.
MARGIN_RELATIVE_TOLERANCE = 1.0e-9

FINDING_MARGIN_SHORTFALL = "achieved-margin-below-required"
FINDING_CAPABILITY_BELOW_DOSE = "capability-below-design-dose"
FINDING_GENERIC_DATA_LATE = "generic-family-data-past-design-freeze"
FINDING_NO_TEST = "dose-capability-rests-on-no-radiation-test"


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def validate_dose_depth_curve(curve):
    """Validate a dose-depth curve and return it as a tuple of pairs."""
    if not isinstance(curve, (list, tuple)) or len(curve) < 2:
        raise ValueError("dose-depth curve needs at least two points")
    points = []
    previous_thickness = None
    previous_dose = None
    for index, point in enumerate(curve):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("curve point %d must be a (thickness, dose) pair" % index)
        thickness = _numeric("curve point %d thickness_mm" % index, point[0])
        dose = _numeric("curve point %d dose_krad" % index, point[1])
        if thickness <= 0.0:
            raise ValueError("curve point %d thickness_mm must be positive" % index)
        if dose <= 0.0:
            raise ValueError("curve point %d dose_krad must be positive" % index)
        if previous_thickness is not None and thickness <= previous_thickness:
            raise ValueError("curve thickness_mm must be strictly ascending")
        if previous_dose is not None and dose > previous_dose:
            raise ValueError("curve dose_krad must not rise with shielding")
        previous_thickness = thickness
        previous_dose = dose
        points.append((thickness, dose))
    return tuple(points)


def dose_at_shielding(curve, thickness_mm):
    """Ionising dose in krad(Si) at one equivalent aluminium thickness."""
    points = validate_dose_depth_curve(curve)
    thickness = _numeric("thickness_mm", thickness_mm)
    if thickness <= 0.0:
        raise ValueError("thickness_mm must be positive")
    low = points[0][0]
    high = points[-1][0]
    if thickness < low or thickness > high:
        raise ValueError(
            "thickness_mm %r is outside the tabulated curve span %r..%r; "
            "obtain curve data covering it rather than extrapolating"
            % (thickness, low, high)
        )
    for (t0, d0), (t1, d1) in zip(points, points[1:]):
        if t0 <= thickness <= t1:
            if d0 == d1:
                return d0
            fraction = (math.log(thickness) - math.log(t0)) / (
                math.log(t1) - math.log(t0)
            )
            return math.exp(math.log(d0) + fraction * (math.log(d1) - math.log(d0)))
    return points[-1][1]


def validate_mission(mission):
    """Validate the mission dose context and return a normalized copy."""
    if not isinstance(mission, dict):
        raise ValueError("mission must be a mapping")
    curve_years = _numeric(
        "mission curve_duration_years", mission.get("curve_duration_years")
    )
    if curve_years <= 0.0:
        raise ValueError("mission curve_duration_years must be positive")
    lifetime_years = _numeric(
        "mission required_lifetime_years", mission.get("required_lifetime_years")
    )
    if lifetime_years <= 0.0:
        raise ValueError("mission required_lifetime_years must be positive")
    phase = mission.get("phase")
    if phase not in PROGRAMME_PHASES:
        raise ValueError(
            "mission phase %r unknown (expected one of %s)"
            % (phase, ", ".join(PROGRAMME_PHASES))
        )
    return {
        "curve_duration_years": curve_years,
        "required_lifetime_years": lifetime_years,
        "phase": phase,
    }


def design_dose_krad(local_dose_krad, curve_duration_years, required_lifetime_years):
    """Scale a curve dose to the radiation lifetime the design covers."""
    local = _numeric("local_dose_krad", local_dose_krad)
    if local <= 0.0:
        raise ValueError("local_dose_krad must be positive")
    curve_years = _numeric("curve_duration_years", curve_duration_years)
    lifetime_years = _numeric("required_lifetime_years", required_lifetime_years)
    if curve_years <= 0.0 or lifetime_years <= 0.0:
        raise ValueError("durations must be positive")
    return local * (lifetime_years / curve_years)


def required_design_margin(evidence, phase):
    """Required radiation design margin for one evidence grade."""
    if evidence not in EVIDENCE_REQUIRED_MARGIN:
        raise ValueError(
            "evidence %r unknown (expected one of %s)"
            % (evidence, ", ".join(sorted(EVIDENCE_REQUIRED_MARGIN)))
        )
    if phase not in PROGRAMME_PHASES:
        raise ValueError("phase %r unknown" % (phase,))
    return EVIDENCE_REQUIRED_MARGIN[evidence]


def evidence_findings(evidence, phase):
    """Findings about the evidence grade at this programme phase."""
    required = required_design_margin(evidence, phase)
    findings = []
    if required is None:
        findings.append(FINDING_NO_TEST)
        return findings
    if evidence == "generic-family-data":
        if PROGRAMME_PHASES.index(phase) >= PROGRAMME_PHASES.index(
            DESIGN_FREEZE_PHASE
        ):
            findings.append(FINDING_GENERIC_DATA_LATE)
    return findings


def achieved_design_margin(capability_krad, dose_krad):
    """Achieved radiation design margin, capability over design dose."""
    capability = _numeric("capability_krad", capability_krad, 0.0)
    dose = _numeric("dose_krad", dose_krad)
    if dose <= 0.0:
        raise ValueError("dose_krad must be positive")
    return capability / dose


def dose_sensitivity_group(capability_krad):
    """Group one demonstrated dose capability into a sensitivity band."""
    capability = _numeric("capability_krad", capability_krad, 0.0)
    for floor, name in DOSE_SENSITIVITY_BANDS:
        if capability >= floor:
            return name
    return DOSE_SENSITIVITY_BANDS[-1][1]


def margin_meets_requirement(achieved, required):
    """True when an achieved margin meets a required one at equality."""
    achieved = _numeric("achieved", achieved, 0.0)
    required = _numeric("required", required)
    if required <= 0.0:
        raise ValueError("required margin must be positive")
    return achieved >= required * (1.0 - MARGIN_RELATIVE_TOLERANCE)


def validate_part(part):
    """Validate one parts-list entry and return a normalized copy."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    part_id = part.get("id")
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part needs a non-empty string id")
    family = part.get("family")
    if not isinstance(family, str) or not family.strip():
        raise ValueError("part %s needs a non-empty family" % part_id)
    evidence = part.get("evidence")
    if evidence not in EVIDENCE_REQUIRED_MARGIN:
        raise ValueError(
            "part %s has unknown evidence %r" % (part_id, evidence)
        )
    shielding = _numeric("part %s shielding_mm" % part_id, part.get("shielding_mm"))
    if shielding <= 0.0:
        raise ValueError("part %s shielding_mm must be positive" % part_id)
    capability = _numeric(
        "part %s capability_krad" % part_id, part.get("capability_krad")
    )
    if capability <= 0.0:
        raise ValueError("part %s capability_krad must be positive" % part_id)
    return {
        "id": part_id,
        "family": family,
        "evidence": evidence,
        "shielding_mm": shielding,
        "capability_krad": capability,
    }


def assess_part(part, curve, mission):
    """Assess one part against the clause 5.1 dose requirement."""
    norm = validate_part(part)
    context = validate_mission(mission)
    local = dose_at_shielding(curve, norm["shielding_mm"])
    design = design_dose_krad(
        local, context["curve_duration_years"], context["required_lifetime_years"]
    )
    achieved = achieved_design_margin(norm["capability_krad"], design)
    required = required_design_margin(norm["evidence"], context["phase"])
    findings = evidence_findings(norm["evidence"], context["phase"])
    if achieved < 1.0 - MARGIN_RELATIVE_TOLERANCE:
        findings.append(FINDING_CAPABILITY_BELOW_DOSE)
    if required is not None and not margin_meets_requirement(achieved, required):
        findings.append(FINDING_MARGIN_SHORTFALL)
    return {
        "id": norm["id"],
        "family": norm["family"],
        "evidence": norm["evidence"],
        "local_dose_krad": local,
        "design_dose_krad": design,
        "achieved_margin": achieved,
        "required_margin": required,
        "sensitivity_group": dose_sensitivity_group(norm["capability_krad"]),
        "findings": findings,
        "compliant": not findings,
    }


def assess_total_ionising_dose(parts, curve, mission):
    """Run the clause 5.1 dose assurance over an equipment parts list."""
    if not isinstance(parts, list) or not parts:
        raise ValueError("parts must be a non-empty list")
    validate_dose_depth_curve(curve)
    validate_mission(mission)
    results = []
    seen = set()
    for part in parts:
        result = assess_part(part, curve, mission)
        if result["id"] in seen:
            raise ValueError("duplicate part id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    groups = {}
    for result in results:
        groups.setdefault(result["sensitivity_group"], []).append(result["id"])
    for name in groups:
        groups[name].sort()
    tightest = min(results, key=lambda r: (r["achieved_margin"], r["id"]))
    non_compliant = [r["id"] for r in results if not r["compliant"]]
    return {
        "parts": results,
        "sensitivity_groups": groups,
        "tightest_part_id": tightest["id"],
        "tightest_margin": tightest["achieved_margin"],
        "non_compliant_ids": non_compliant,
        "compliant": not non_compliant,
    }
