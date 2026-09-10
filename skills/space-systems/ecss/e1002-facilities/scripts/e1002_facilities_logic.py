"""Deterministic, offline logic for qualifying AIT facilities and test tools.

Implements the checkable procedure behind ECSS-E-ST-10-02C clause 5.2.6.6:
before a test facility or test tool is used on a flight article, its
capability envelope, calibration currency, quality accreditation (linked to
ECSS-Q-ST-20-07 test-centre quality requirements), and interface fit to the
article must all be verified. Stdlib only.
"""

FACILITY_TYPES = frozenset({
    "thermal-vacuum",
    "vibration",
    "acoustic",
    "emc",
    "clean-room",
    "mass-properties",
    "optical-alignment",
})

TOOL_TYPES = frozenset({
    "mechanical-gse",
    "electrical-gse",
    "software-gse",
    "measurement-instrument",
    "handling-equipment",
})

ACCREDITATION_STATUSES = frozenset({
    "accredited",
    "provisional",
    "not-accredited",
    "expired",
})

TEST_METHOD_TO_FACILITY_TYPE = {
    "thermal-balance": "thermal-vacuum",
    "thermal-vacuum": "thermal-vacuum",
    "sine-vibration": "vibration",
    "random-vibration": "vibration",
    "acoustic": "acoustic",
    "emc-emissions": "emc",
    "emc-susceptibility": "emc",
    "mass-properties": "mass-properties",
    "alignment": "optical-alignment",
    "cleanliness-inspection": "clean-room",
}

REQUIRED_PLAN_FIELDS = frozenset({
    "facility_id",
    "requirement_ref",
    "capability_check",
    "calibration_check",
    "accreditation_check",
    "qualification_date",
})


def required_facility_type_for_method(test_method):
    """Map a test method to the facility type that must host it."""
    if test_method not in TEST_METHOD_TO_FACILITY_TYPE:
        raise ValueError("unknown test method: %r" % (test_method,))
    return TEST_METHOD_TO_FACILITY_TYPE[test_method]


def validate_facility_type(facility_type):
    if facility_type not in FACILITY_TYPES:
        raise ValueError("unknown facility type: %r" % (facility_type,))


def validate_tool_type(tool_type):
    if tool_type not in TOOL_TYPES:
        raise ValueError("unknown tool type: %r" % (tool_type,))


def check_capability_envelope(required_min, required_max, facility_min, facility_max):
    """Return True if the facility's operating envelope covers the required range."""
    if required_min > required_max:
        raise ValueError("required range is inverted: min > max")
    if facility_min > facility_max:
        raise ValueError("facility range is inverted: min > max")
    return facility_min <= required_min and facility_max >= required_max


def check_calibration_currency(last_calibration_day, interval_days, current_day):
    """Return calibration currency of a measurement-relevant asset.

    Days are plain integers (day-of-epoch counters) so the check stays
    deterministic and free of timezone/locale concerns.
    """
    if interval_days <= 0:
        raise ValueError("calibration interval must be positive")
    if current_day < last_calibration_day:
        raise ValueError("current day precedes last calibration day")
    days_since = current_day - last_calibration_day
    days_remaining = interval_days - days_since
    return {"current": days_remaining >= 0, "days_remaining": days_remaining}


def check_qc_accreditation(accreditation_status, accreditation_standard):
    """Return True only for a live accreditation against Q-ST-20-07."""
    if accreditation_status not in ACCREDITATION_STATUSES:
        raise ValueError("unknown accreditation status: %r" % (accreditation_status,))
    if accreditation_status != "accredited":
        return False
    return accreditation_standard == "q-st-20-07"


def check_tool_interface_compatibility(tool_interfaces, article_interfaces):
    """Return (compatible, missing) -- missing is the set the tool lacks."""
    tool_set = set(tool_interfaces)
    article_set = set(article_interfaces)
    missing = article_set - tool_set
    return (len(missing) == 0, missing)


def qualify_facility(facility, requirement, current_day):
    """Aggregate the clause 5.2.6.6 facility qualification checks.

    facility: dict with type, capability_min, capability_max,
        accreditation_status, accreditation_standard,
        last_calibration_day, calibration_interval_days.
    requirement: dict with min, max (the test's required envelope).
    Returns {"status": "qualified"|"not-qualified", "findings": [...]}.
    """
    validate_facility_type(facility["type"])
    findings = []

    envelope_ok = check_capability_envelope(
        requirement["min"], requirement["max"],
        facility["capability_min"], facility["capability_max"],
    )
    if not envelope_ok:
        findings.append("capability-envelope-insufficient")

    accredited = check_qc_accreditation(
        facility["accreditation_status"], facility["accreditation_standard"],
    )
    if not accredited:
        findings.append("qc-accreditation-missing")

    cal = check_calibration_currency(
        facility["last_calibration_day"],
        facility["calibration_interval_days"],
        current_day,
    )
    if not cal["current"]:
        findings.append("calibration-expired")

    status = "qualified" if not findings else "not-qualified"
    return {"status": status, "findings": findings}


def qualify_tool(tool, article_interfaces, current_day):
    """Aggregate the tool-qualification checks (interface fit, calibration).

    tool: dict with type, interfaces, and (for measurement-instrument only)
        last_calibration_day, calibration_interval_days.
    article_interfaces: iterable of interface names the article requires.
    Returns {"status": "qualified"|"not-qualified", "findings": [...]}.
    """
    validate_tool_type(tool["type"])
    findings = []

    compatible, missing = check_tool_interface_compatibility(
        tool["interfaces"], article_interfaces,
    )
    if not compatible:
        findings.append("interface-incompatible")

    if tool["type"] == "measurement-instrument":
        cal = check_calibration_currency(
            tool["last_calibration_day"],
            tool["calibration_interval_days"],
            current_day,
        )
        if not cal["current"]:
            findings.append("calibration-expired")

    status = "qualified" if not findings else "not-qualified"
    return {"status": status, "findings": findings}


def check_plan_completeness(plan_record):
    """Return the set of required qualification-plan fields that are missing."""
    return REQUIRED_PLAN_FIELDS - set(plan_record.keys())


def roll_up_ait_readiness(qualification_results):
    """Roll many facility/tool qualification results up into one AIT gate.

    Readiness requires every result to be "qualified" -- one blocking item
    is enough to hold the gate.
    """
    if not qualification_results:
        raise ValueError("qualification_results must not be empty")
    blocking = [r for r in qualification_results if r["status"] != "qualified"]
    return {"ready": len(blocking) == 0, "blocking_count": len(blocking)}
