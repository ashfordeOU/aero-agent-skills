"""Completeness of a full visual examination of solar-array hardware.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.1 (the purpose of the full visual
inspection -- detecting imperfections across the complete hardware).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Take the declared inspection zones of the article, each with its area, the
   magnification and illuminance it was examined under, whether it was
   actually examined, and whether it was reachable without an access aid.
2. Compute the area coverage the examination achieved. The clause's purpose
   is detection across the complete hardware, so a zone left out is a gap in
   the purpose, not a rounding loss.
3. Derive, per zone, the smallest feature the magnification used there can
   resolve, and compare it with the imperfection size the requirement has to
   detect. A zone examined too coarsely was examined, but not for the thing
   that was being looked for.
4. Check each zone's illuminance against the floor, and require an access
   means to be declared for any zone the inspector could not reach directly.
5. Group the imperfections that were found by severity and derive the
   article disposition from the worst grade present.
6. Call the inspection complete only when coverage is whole and every
   examined zone met its optical and access conditions.
"""

import math

__all__ = [
    "BASE_ACUITY_MM",
    "COVERAGE_TOLERANCE",
    "FEATURE_TOLERANCE_MM",
    "DEFAULT_MIN_ILLUMINANCE_LUX",
    "SEVERITY_GRADES",
    "resolvable_feature_mm",
    "validate_zone",
    "coverage_fraction",
    "zone_optical_findings",
    "group_imperfections",
    "disposition_from_grades",
    "assess_full_visual_inspection",
]

# Smallest feature an unaided eye resolves at close working distance, in mm.
# Divided by the magnification actually used, it gives what a zone's optics
# could have shown the inspector.
BASE_ACUITY_MM = 0.10

# Coverage is a ratio of summed float areas; a whole article can land a few
# ULPs off 1.0. Absorb that here rather than by accepting a real gap.
COVERAGE_TOLERANCE = 1e-9

# Feature sizes come out of a division and compare against a specified size.
FEATURE_TOLERANCE_MM = 1e-12

# Illuminance floor for a detection-grade visual examination, in lux.
DEFAULT_MIN_ILLUMINANCE_LUX = 1000.0

# Imperfection severity grades, worst first; the disposition follows the worst
# grade present.
SEVERITY_GRADES = ("critical", "major", "minor")

DISPOSITIONS = {"critical": "reject", "major": "repair", "minor": "accept"}


def _real(label, value, allow_zero=False):
    """Return value as a validated positive (or non-negative) float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if allow_zero and number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    if not allow_zero and number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _flag(label, value, default=None):
    """Return value as a validated boolean, applying a default when absent."""
    if value is None:
        if default is None:
            raise ValueError("%s must be supplied" % label)
        return default
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean" % label)
    return value


def resolvable_feature_mm(magnification, base_acuity_mm=BASE_ACUITY_MM):
    """Return the smallest feature a given magnification can show."""
    factor = _real("magnification", magnification)
    if factor < 1.0:
        raise ValueError(
            "magnification %r is below unity; a de-magnifying view is not an "
            "inspection aid" % (magnification,)
        )
    acuity = _real("base_acuity_mm", base_acuity_mm)
    return acuity / factor


def validate_zone(zone):
    """Return one validated inspection zone of the article."""
    if not isinstance(zone, dict):
        raise ValueError("zone must be a mapping")
    for key in ("id", "area_cm2", "magnification", "illuminance_lux"):
        if key not in zone:
            raise ValueError("zone is missing required key '%s'" % key)
    zone_id = zone["id"]
    if not isinstance(zone_id, str) or not zone_id.strip():
        raise ValueError("zone['id'] must be a non-empty string")
    return {
        "id": zone_id.strip(),
        "area_cm2": _real("zone['area_cm2']", zone["area_cm2"]),
        "magnification": _real("zone['magnification']", zone["magnification"]),
        "illuminance_lux": _real("zone['illuminance_lux']", zone["illuminance_lux"]),
        "inspected": _flag("zone['inspected']", zone.get("inspected"), default=True),
        "directly_accessible": _flag(
            "zone['directly_accessible']", zone.get("directly_accessible"), default=True
        ),
        "access_means": zone.get("access_means"),
    }


def _validate_zones(zones):
    """Return the validated, uniquely identified zone list of the article."""
    if not isinstance(zones, (list, tuple)) or not zones:
        raise ValueError("zones must be a non-empty sequence of inspection zones")
    validated = []
    seen = set()
    for zone in zones:
        record = validate_zone(zone)
        if record["id"] in seen:
            raise ValueError("zone id '%s' is declared twice" % record["id"])
        seen.add(record["id"])
        validated.append(record)
    return validated


def coverage_fraction(zones):
    """Return the fraction of the article's area that was examined."""
    validated = _validate_zones(zones)
    total = sum(zone["area_cm2"] for zone in validated)
    examined = sum(zone["area_cm2"] for zone in validated if zone["inspected"])
    return examined / total


def zone_optical_findings(zone, smallest_feature_mm,
                          min_illuminance_lux=DEFAULT_MIN_ILLUMINANCE_LUX):
    """Return the findings against the conditions one zone was examined under."""
    record = validate_zone(zone)
    target = _real("smallest_feature_mm", smallest_feature_mm)
    floor = _real("min_illuminance_lux", min_illuminance_lux)
    findings = []
    if not record["inspected"]:
        findings.append("zone '%s' was not examined" % record["id"])
        return findings
    resolvable = resolvable_feature_mm(record["magnification"])
    if resolvable > target and not math.isclose(
        resolvable, target, rel_tol=0.0, abs_tol=FEATURE_TOLERANCE_MM
    ):
        findings.append(
            "zone '%s' was examined at x%g, which resolves %.4g mm and cannot show "
            "the %.4g mm imperfection the requirement targets"
            % (record["id"], record["magnification"], resolvable, target)
        )
    if record["illuminance_lux"] < floor and not math.isclose(
        record["illuminance_lux"], floor, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    ):
        findings.append(
            "zone '%s' was examined at %g lux, below the %g lux floor for detection"
            % (record["id"], record["illuminance_lux"], floor)
        )
    if not record["directly_accessible"]:
        means = record["access_means"]
        if not isinstance(means, str) or not means.strip():
            findings.append(
                "zone '%s' is not directly reachable and declares no access means"
                % record["id"]
            )
    return findings


def group_imperfections(imperfections, zone_ids):
    """Return the imperfection counts grouped by severity grade."""
    if imperfections is None:
        return {grade: 0 for grade in SEVERITY_GRADES}
    if not isinstance(imperfections, (list, tuple)):
        raise ValueError("imperfections must be a sequence of findings")
    known = set(zone_ids)
    totals = {grade: 0 for grade in SEVERITY_GRADES}
    for index, item in enumerate(imperfections):
        if not isinstance(item, dict):
            raise ValueError("imperfections[%d] must be a mapping" % index)
        for key in ("zone", "severity"):
            if key not in item:
                raise ValueError(
                    "imperfections[%d] is missing required key '%s'" % (index, key)
                )
        if item["severity"] not in SEVERITY_GRADES:
            raise ValueError(
                "imperfections[%d] carries unknown severity %r; use one of %s"
                % (index, item["severity"], ", ".join(SEVERITY_GRADES))
            )
        if item["zone"] not in known:
            raise ValueError(
                "imperfections[%d] names zone %r, which is not a declared zone"
                % (index, item["zone"])
            )
        totals[item["severity"]] += 1
    return totals


def disposition_from_grades(totals):
    """Return the article disposition implied by the worst grade present."""
    if not isinstance(totals, dict):
        raise ValueError("totals must be a mapping of severity grade to count")
    for grade in SEVERITY_GRADES:
        count = totals.get(grade, 0)
        if not isinstance(count, int) or isinstance(count, bool):
            raise ValueError("totals['%s'] must be an integer" % grade)
        if count < 0:
            raise ValueError("totals['%s'] must be non-negative" % grade)
        if count > 0:
            return DISPOSITIONS[grade]
    return "accept"


def assess_full_visual_inspection(spec):
    """Run the full clause 5.5.3.2.1 visual-examination completeness assessment.

    spec keys: zones (non-empty list), smallest_feature_mm, optional
    min_illuminance_lux and imperfections.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("zones", "smallest_feature_mm"):
        if key not in spec:
            raise ValueError("spec is missing required key '%s'" % key)
    zones = _validate_zones(spec["zones"])
    target = _real("spec['smallest_feature_mm']", spec["smallest_feature_mm"])
    floor = _real(
        "spec['min_illuminance_lux']",
        spec.get("min_illuminance_lux", DEFAULT_MIN_ILLUMINANCE_LUX),
    )
    total_area = sum(zone["area_cm2"] for zone in zones)
    examined_area = sum(zone["area_cm2"] for zone in zones if zone["inspected"])
    coverage = examined_area / total_area
    findings = []
    zone_records = []
    for zone in zones:
        zone_findings = zone_optical_findings(zone, target, floor)
        zone_records.append(
            {
                "id": zone["id"],
                "area_cm2": zone["area_cm2"],
                "inspected": zone["inspected"],
                "magnification": zone["magnification"],
                "resolvable_feature_mm": resolvable_feature_mm(zone["magnification"]),
                "illuminance_lux": zone["illuminance_lux"],
                "findings": zone_findings,
                "adequate": not zone_findings,
            }
        )
        findings.extend(zone_findings)
    totals = group_imperfections(
        spec.get("imperfections"), [zone["id"] for zone in zones]
    )
    whole = math.isclose(coverage, 1.0, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE)
    uninspected = [zone["id"] for zone in zones if not zone["inspected"]]
    return {
        "zone_records": zone_records,
        "total_area_cm2": total_area,
        "examined_area_cm2": examined_area,
        "coverage_fraction": coverage,
        "coverage_complete": whole,
        "uninspected_zones": uninspected,
        "imperfection_totals": totals,
        "disposition": disposition_from_grades(totals),
        "findings": findings,
        "complete": whole and not findings,
    }
