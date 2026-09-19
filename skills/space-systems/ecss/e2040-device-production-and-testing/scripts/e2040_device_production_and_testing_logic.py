"""Device production and production testing, reported per technology.

Anchor: ECSS-E-ST-20-40C clause 5.7.2 (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. The reporting unit is the implementation technology. Every
   technology the device is built on owes its own production and test
   report; a device with two technologies and one report has a gap.
2. A lot carries four nested counts -- started, completed, tested,
   passed -- and each has to be no larger than the one before it.
3. Coverage is tested over completed; yield is passed over tested.
   Both refuse a zero denominator rather than reporting zero.
4. Coverage is graded against an agreed floor and is a hard finding
   below it. Yield is graded against an expectation and a shortfall
   opens an investigation rather than rejecting the lot outright.
5. The test program is checked separately against the parameter list
   the technology owes, because unit coverage says nothing about which
   behaviour was exercised.

Stdlib only, offline, deterministic.
"""

import math

# A coverage or yield figure is a quotient of two integers, so a lot
# sitting exactly on a floor can land a few units in the last place
# under it. This tolerance absorbs that without lowering the floor.
FRACTION_TOLERANCE = 1.0e-12

FINDING_TECHNOLOGY_NOT_REPORTED = "declared-technology-without-a-production-report"
FINDING_COVERAGE_BELOW_FLOOR = "production-test-coverage-below-the-agreed-floor"
FINDING_YIELD_BELOW_EXPECTATION = "lot-yield-below-expectation-investigation-owed"
FINDING_PARAMETER_NOT_EXERCISED = "owed-parameter-absent-from-the-test-program"
FINDING_NO_LOTS_REPORTED = "technology-reported-without-a-single-lot"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _count(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return value


def _fraction(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if not 0.0 <= value <= 1.0:
        raise ValueError("%s must lie in 0..1, got %r" % (label, value))
    return value


def _names(label, values):
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("%s must be a non-empty sequence" % label)
    normalized = []
    for value in values:
        name = _text("%s entry" % label, value)
        if name in normalized:
            raise ValueError("%s lists %r twice" % (label, name))
        normalized.append(name)
    return normalized


def validate_device(device):
    """Validate the device record and return a normalized copy."""
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping")
    device_id = _text("device id", device.get("id"))
    technologies = _names(
        "device %s technologies" % device_id, device.get("technologies")
    )
    return {"id": device_id, "technologies": technologies}


def validate_lot(lot):
    """Validate one production lot and return a normalized copy."""
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping")
    lot_id = _text("lot id", lot.get("id"))
    started = _count("lot %s units_started" % lot_id, lot.get("units_started"))
    completed = _count("lot %s units_completed" % lot_id, lot.get("units_completed"))
    tested = _count("lot %s units_tested" % lot_id, lot.get("units_tested"))
    passed = _count("lot %s units_passed" % lot_id, lot.get("units_passed"))
    for upper_label, upper, lower_label, lower in (
        ("units_started", started, "units_completed", completed),
        ("units_completed", completed, "units_tested", tested),
        ("units_tested", tested, "units_passed", passed),
    ):
        if lower > upper:
            raise ValueError(
                "lot %s has %s %d above %s %d"
                % (lot_id, lower_label, lower, upper_label, upper)
            )
    return {
        "id": lot_id,
        "units_started": started,
        "units_completed": completed,
        "units_tested": tested,
        "units_passed": passed,
    }


def test_coverage_fraction(lot):
    """Units tested over units completed."""
    norm = validate_lot(lot)
    if norm["units_completed"] == 0:
        raise ValueError(
            "lot %s completed no units, so it has no coverage denominator"
            % norm["id"]
        )
    return norm["units_tested"] / norm["units_completed"]


def lot_yield_fraction(lot):
    """Units passed over units tested."""
    norm = validate_lot(lot)
    if norm["units_tested"] == 0:
        raise ValueError(
            "lot %s tested no units, so it has no yield denominator" % norm["id"]
        )
    return norm["units_passed"] / norm["units_tested"]


def meets_floor(value, floor):
    """True when a fraction reaches a floor within the named tolerance."""
    value = _fraction("value", value)
    floor = _fraction("floor", floor)
    return value >= floor - FRACTION_TOLERANCE


def validate_technology_report(report, device):
    """Validate one per-technology production report."""
    norm_device = validate_device(device)
    if not isinstance(report, dict):
        raise ValueError("technology report must be a mapping")
    technology = _text("technology report technology", report.get("technology"))
    if technology not in norm_device["technologies"]:
        raise ValueError(
            "report names technology %r which device %s does not use"
            % (technology, norm_device["id"])
        )
    owed_parameters = _names(
        "technology %s owed_parameters" % technology, report.get("owed_parameters")
    )
    program_parameters = report.get("program_parameters", [])
    if not isinstance(program_parameters, (list, tuple)):
        raise ValueError(
            "technology %s program_parameters must be a sequence" % technology
        )
    program = []
    for value in program_parameters:
        program.append(_text("technology %s program parameter" % technology, value))
    coverage_floor = _fraction(
        "technology %s coverage_floor" % technology, report.get("coverage_floor", 1.0)
    )
    yield_expectation = _fraction(
        "technology %s yield_expectation" % technology,
        report.get("yield_expectation", 0.9),
    )
    lots = report.get("lots", [])
    if not isinstance(lots, (list, tuple)):
        raise ValueError("technology %s lots must be a sequence" % technology)
    normalized_lots = []
    seen = set()
    for lot in lots:
        norm_lot = validate_lot(lot)
        if norm_lot["id"] in seen:
            raise ValueError(
                "technology %s lists lot %r twice" % (technology, norm_lot["id"])
            )
        seen.add(norm_lot["id"])
        normalized_lots.append(norm_lot)
    return {
        "technology": technology,
        "owed_parameters": owed_parameters,
        "program_parameters": program,
        "coverage_floor": coverage_floor,
        "yield_expectation": yield_expectation,
        "lots": normalized_lots,
    }


def unexercised_parameters(report, device):
    """Owed parameters the test program never exercises."""
    norm = validate_technology_report(report, device)
    program = set(norm["program_parameters"])
    return [name for name in norm["owed_parameters"] if name not in program]


def assess_technology(report, device):
    """Assess one technology's production and test evidence."""
    norm = validate_technology_report(report, device)
    findings = []
    for name in unexercised_parameters(norm, device):
        findings.append((name, FINDING_PARAMETER_NOT_EXERCISED))
    lot_results = []
    if not norm["lots"]:
        findings.append((norm["technology"], FINDING_NO_LOTS_REPORTED))
    for lot in norm["lots"]:
        coverage = test_coverage_fraction(lot)
        achieved_yield = lot_yield_fraction(lot)
        lot_findings = []
        if not meets_floor(coverage, norm["coverage_floor"]):
            lot_findings.append(FINDING_COVERAGE_BELOW_FLOOR)
        if not meets_floor(achieved_yield, norm["yield_expectation"]):
            lot_findings.append(FINDING_YIELD_BELOW_EXPECTATION)
        for name in lot_findings:
            findings.append((lot["id"], name))
        lot_results.append(
            {
                "id": lot["id"],
                "coverage": coverage,
                "yield": achieved_yield,
                "findings": lot_findings,
                "investigation_owed": FINDING_YIELD_BELOW_EXPECTATION in lot_findings,
                "acceptable": FINDING_COVERAGE_BELOW_FLOOR not in lot_findings,
            }
        )
    return {
        "technology": norm["technology"],
        "lots": lot_results,
        "unexercised_parameters": unexercised_parameters(norm, device),
        "findings": findings,
        "acceptable": all(result["acceptable"] for result in lot_results)
        and not unexercised_parameters(norm, device)
        and bool(lot_results),
    }


def assess_device_production_and_testing(device, reports):
    """Assess the clause 5.7.2 evidence across every technology used."""
    norm_device = validate_device(device)
    if not isinstance(reports, list):
        raise ValueError("reports must be a list")
    results = []
    seen = set()
    for report in reports:
        result = assess_technology(report, norm_device)
        if result["technology"] in seen:
            raise ValueError("duplicate report for technology %r" % (result["technology"],))
        seen.add(result["technology"])
        results.append(result)
    findings = []
    for technology in norm_device["technologies"]:
        if technology not in seen:
            findings.append((technology, FINDING_TECHNOLOGY_NOT_REPORTED))
    for result in results:
        findings.extend(result["findings"])
    investigations = [
        (result["technology"], lot["id"])
        for result in results
        for lot in result["lots"]
        if lot["investigation_owed"]
    ]
    return {
        "device_id": norm_device["id"],
        "technologies": results,
        "unreported_technologies": [
            technology
            for technology in norm_device["technologies"]
            if technology not in seen
        ],
        "investigations_owed": investigations,
        "findings": findings,
        "complete": not findings,
    }
