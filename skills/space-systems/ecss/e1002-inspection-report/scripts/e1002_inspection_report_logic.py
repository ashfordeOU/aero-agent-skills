"""ECSS-E-ST-10-02 clause 5.3.2.4 / Annex E inspection report DRD (paraphrase).

Common-knowledge summary (standards-map.yaml, ecss: gated false): where the
verification method is inspection, the evidence is a measurement or an
observation made on the actual article. The Annex E report records what was
inspected, by whom, with which equipment, and what was found. Two properties
decide whether the result counts: the measuring equipment must have been in
calibration ON THE DAY the measurement was taken -- calibration valid today
says nothing about a measurement taken after it lapsed -- and a variable
characteristic must be judged against its own tolerance band rather than
against a general impression of conformity.
"""

CHARACTERISTIC_KINDS = ("variable", "attribute")
ATTRIBUTE_RESULTS = ("conforming", "nonconforming")


def validate_kind(kind):
    """Return kind if it is a recognized characteristic kind, else raise."""
    if kind not in CHARACTERISTIC_KINDS:
        raise ValueError("unknown characteristic kind: %r" % (kind,))
    return kind


def tolerance_band(nominal, lower_tolerance, upper_tolerance):
    """(low, high) limits from a nominal and its tolerances.

    Tolerances are magnitudes, so a negative one is an input error rather
    than a reversed band -- reversing it silently would invert the test.
    """
    if lower_tolerance < 0 or upper_tolerance < 0:
        raise ValueError("tolerances are magnitudes and cannot be negative")
    return (nominal - lower_tolerance, nominal + upper_tolerance)


def within_tolerance(measured, nominal, lower_tolerance, upper_tolerance):
    """True when a measured value lies inside its tolerance band, limits
    included. A value exactly on a limit conforms: the band is the
    requirement, not an open interval."""
    low, high = tolerance_band(nominal, lower_tolerance, upper_tolerance)
    return low <= measured <= high


def calibration_valid(equipment, inspection_day):
    """True when the equipment's calibration covered the day of inspection.

    equipment: {"equipment_id": str, "calibration_due_day": int}
    Days are integer ordinals so the check stays offline and deterministic.
    Calibration that expired before the measurement invalidates it however
    recently the instrument has since been recalibrated.
    """
    due = equipment.get("calibration_due_day")
    if due is None:
        return False
    return inspection_day <= due


def equipment_violations(characteristic, inspection_day):
    """Findings for the measuring equipment behind one variable
    characteristic: none declared, or calibration lapsed at the time."""
    cid = characteristic.get("characteristic_id")
    equipment = characteristic.get("equipment")
    if not equipment or not equipment.get("equipment_id"):
        return [{"characteristic_id": cid, "issue": "no_measuring_equipment"}]
    if not calibration_valid(equipment, inspection_day):
        return [{"characteristic_id": cid, "equipment_id": equipment["equipment_id"],
                 "issue": "calibration_not_valid_at_inspection"}]
    return []


def characteristic_result(characteristic, inspection_day):
    """Conformity of one inspected characteristic: "conforming",
    "nonconforming" or "not_inspected".

    A variable characteristic is judged against its tolerance band; an
    attribute characteristic carries its own recorded result. A
    characteristic with no reading is not inspected -- distinct from one
    inspected and found out of tolerance.
    """
    kind = validate_kind(characteristic.get("kind"))
    if kind == "attribute":
        result = characteristic.get("result")
        if result is None:
            return "not_inspected"
        if result not in ATTRIBUTE_RESULTS:
            raise ValueError("unknown attribute result: %r" % (result,))
        return result
    measured = characteristic.get("measured")
    if measured is None:
        return "not_inspected"
    ok = within_tolerance(measured, characteristic["nominal"],
                          characteristic["lower_tolerance"],
                          characteristic["upper_tolerance"])
    return "conforming" if ok else "nonconforming"


def inspector_violations(report, qualified_inspectors):
    """Findings when the inspection was not performed by a qualified
    inspector. Qualification is checked against the roster, not asserted."""
    who = report.get("inspector")
    if not who:
        return [{"issue": "no_inspector_recorded"}]
    if who not in set(qualified_inspectors):
        return [{"inspector": who, "issue": "inspector_not_qualified"}]
    return []


def inspection_report_review(report, qualified_inspectors):
    """Full Annex E inspection report review.

    report: {"article_id", "inspector", "inspection_day": int,
             "characteristics": [{"characteristic_id", "kind", ...}]}

    Returns {"article_id", "conforming", "nonconforming", "not_inspected",
             "findings"}.
    """
    aid = report.get("article_id")
    if not aid:
        raise ValueError("inspection report with no article_id")
    day = report.get("inspection_day")
    if day is None:
        raise ValueError("inspection report with no inspection_day")
    buckets = {"conforming": [], "nonconforming": [], "not_inspected": []}
    findings = list(inspector_violations(report, qualified_inspectors))
    seen = set()
    for ch in report.get("characteristics", []):
        cid = ch.get("characteristic_id")
        if not cid:
            raise ValueError("characteristic with no characteristic_id")
        if cid in seen:
            raise ValueError("duplicate characteristic_id: %s" % cid)
        seen.add(cid)
        if validate_kind(ch.get("kind")) == "variable":
            findings += equipment_violations(ch, day)
        buckets[characteristic_result(ch, day)].append(cid)
    return {"article_id": aid, "conforming": buckets["conforming"],
            "nonconforming": buckets["nonconforming"],
            "not_inspected": buckets["not_inspected"], "findings": findings}


def is_inspection_acceptable(review):
    """True when every characteristic was inspected and conforms, with no
    finding against the inspector or the equipment."""
    return not (review["nonconforming"] or review["not_inspected"]
                or review["findings"])
