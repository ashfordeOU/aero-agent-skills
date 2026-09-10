#!/usr/bin/env python3
"""ECSS-E-ST-10-03C clause 5.5.2 equipment mechanical test logic
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
equipment mechanical test set covers physical properties, acceleration
(static/spin/sine-burst), sinusoidal vibration, random vibration,
acoustic, shock, and micro-vibration (source and/or sensitive role).
This module implements which of those tests apply to a given
equipment item, the evidence each applicable test needs, and the
per-item and per-campaign completeness check; it does not set test
levels/durations or the qualification/acceptance/protoflight baseline
(clauses 5.2-5.4, sibling leaves) or general test rules (clause 5.1).
"""

ACCELERATION_METHODS = ("static", "spin", "sine_burst")

TEST_NAMES = (
    "physical_properties",
    "acceleration",
    "sine_vibration",
    "random_vibration",
    "acoustic",
    "shock",
    "microvibration_source",
    "microvibration_sensitive",
)


def acceleration_method(equipment):
    """Acceleration test method for one equipment dict, or None if
    acceleration does not apply. Required key: static_load_significant
    (bool). Optional keys: use_sine_burst, spinning_mounted (bools).
    sine-burst and spin are alternative methods for the same purpose;
    requesting both is an ambiguous configuration and raises
    ValueError."""
    if not equipment.get("static_load_significant", False):
        return None
    use_sine_burst = equipment.get("use_sine_burst", False)
    spinning_mounted = equipment.get("spinning_mounted", False)
    if use_sine_burst and spinning_mounted:
        raise ValueError(
            "ambiguous acceleration method: both use_sine_burst and "
            "spinning_mounted set for %r" % (equipment.get("id"),)
        )
    if use_sine_burst:
        return "sine_burst"
    if spinning_mounted:
        return "spin"
    return "static"


def required_tests(equipment):
    """Ordered list of (test_name, evidence_needed) tuples applicable
    to one equipment dict. physical_properties is always included.
    acceleration is included (with its method-specific evidence) only
    when acceleration_method() is not None. sine_vibration and
    random_vibration are included unless the item is enveloped by a
    higher-level test. acoustic is included when area-to-mass ratio is
    high. shock is included when shock exposed. microvibration_source
    / microvibration_sensitive are included per their independent role
    flags."""
    tests = [("physical_properties", "physical_properties_result")]

    method = acceleration_method(equipment)
    if method is not None:
        tests.append(("acceleration", "acceleration_%s_result" % method))

    if not equipment.get("enveloped_by_higher_level_test", False):
        tests.append(("sine_vibration", "sine_vibration_result"))
        tests.append(("random_vibration", "random_vibration_result"))

    if equipment.get("area_to_mass_ratio_high", False):
        tests.append(("acoustic", "acoustic_result"))

    if equipment.get("shock_exposed", False):
        tests.append(("shock", "shock_result"))

    if equipment.get("microvibration_source", False):
        tests.append(("microvibration_source", "microvibration_source_result"))

    if equipment.get("microvibration_sensitive", False):
        tests.append(("microvibration_sensitive", "microvibration_sensitive_result"))

    return tests


def assess_equipment(equipment):
    """Full mechanical-test assessment for one equipment dict. Required
    key: id. Optional key: evidence (set/list of evidence type strings
    already supplied). Returns a new dict with the applicable test
    list (each with its status) and an overall status; does not mutate
    the input. Raises ValueError if 'id' is missing."""
    if "id" not in equipment:
        raise ValueError("equipment is missing an id")
    supplied = equipment.get("evidence", ())
    tests = []
    for test_name, evidence_needed in required_tests(equipment):
        tests.append({
            "test": test_name,
            "evidence_needed": evidence_needed,
            "status": "closed" if evidence_needed in supplied else "open",
        })
    overall = "closed" if all(t["status"] == "closed" for t in tests) else "open"
    return {
        "id": equipment["id"],
        "tests": tests,
        "status": overall,
        "_evidence": tuple(supplied),
    }


def build_mechanical_test_record(equipment_items):
    """Mechanical test record: one assessment dict per equipment item,
    in input order. Raises ValueError on a duplicate equipment id."""
    record = []
    seen_ids = set()
    for equipment in equipment_items:
        assessment = assess_equipment(equipment)
        if assessment["id"] in seen_ids:
            raise ValueError("duplicate equipment id: %r" % (assessment["id"],))
        seen_ids.add(assessment["id"])
        record.append(assessment)
    return record


def open_tests(assessment):
    """Test names still open for one equipment assessment, in
    assessment order."""
    return [t["test"] for t in assessment["tests"] if t["status"] == "open"]


def open_equipment(record):
    """Equipment ids in the record with at least one open test, in
    record order."""
    return [entry["id"] for entry in record if entry["status"] == "open"]


def campaign_complete(record):
    """True when every equipment item in the record has every
    applicable test closed."""
    return len(open_equipment(record)) == 0


def find_incomplete_dual_role_microvibration(record):
    """Equipment ids that are both a micro-vibration source and
    micro-vibration-sensitive (per their test list) but have only one
    of the two roles closed -- the role missed by treating a dual-role
    item as fully tested once either role's evidence is supplied."""
    flagged = []
    for entry in record:
        by_name = {t["test"]: t["status"] for t in entry["tests"]}
        if "microvibration_source" in by_name and "microvibration_sensitive" in by_name:
            if by_name["microvibration_source"] != by_name["microvibration_sensitive"]:
                flagged.append(entry["id"])
    return flagged
