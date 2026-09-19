"""Required contents of the published device data sheet.

Anchor: ECSS-E-ST-20-40C Annex H (device data sheet data item -- the
characteristics of the device and the ratings inside which it may be
operated). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Check the supplied section list against the required contents.
2. Validate every characteristic: identifier, real unit, and minimum,
   typical and maximum ordered where present.
3. Report the content defects of the characteristic table: placeholder unit,
   absent test conditions, an entry carrying no value at all.
4. Validate every rating and place the recommended range inside the absolute
   range at both ends.
5. Compute the derating margin each recommended limit leaves against its
   absolute rating, and grade it against the required derating factor with a
   tolerance so a limit landing exactly on the requirement is met.
6. Report the worst-margin parameter together with the findings.
"""

import math

__all__ = [
    "REQUIRED_SECTIONS",
    "PLACEHOLDER_UNITS",
    "DERATING_TOLERANCE",
    "missing_sections",
    "validate_characteristic",
    "validate_characteristics",
    "characteristic_findings",
    "validate_rating",
    "validate_ratings",
    "envelope_containment",
    "derating_margin",
    "grade_rating",
    "worst_margin_parameter",
    "assess_data_sheet",
]

REQUIRED_SECTIONS = (
    "scope",
    "device-description",
    "absolute-maximum-ratings",
    "recommended-operating-conditions",
    "electrical-characteristics",
    "test-conditions",
)

PLACEHOLDER_UNITS = ("tbd", "tbc", "n/a", "na", "-", "none", "unit")

# A derating margin equal to the requirement is met; the difference of a
# quotient from one lands a few ULPs either side of the stated fraction.
DERATING_TOLERANCE = 1e-9


def _identifier(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    out = value.strip()
    if not out:
        raise ValueError("%s must not be empty" % label)
    return out


def _real_or_none(value, label):
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number or None, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _real(value, label):
    out = _real_or_none(value, label)
    if out is None:
        raise ValueError("%s is required" % label)
    return out


def missing_sections(sections):
    """Return the required sections absent from the supplied section list."""
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be a list or tuple of section names")
    present = set()
    for i, name in enumerate(sections):
        present.add(_identifier(name, "sections[%d]" % i).lower())
    return [name for name in REQUIRED_SECTIONS if name not in present]


def validate_characteristic(characteristic):
    """Return a normalized characteristic with its minimum, typical and maximum."""
    if not isinstance(characteristic, dict):
        raise ValueError("characteristic must be a mapping")
    for key in ("id", "unit"):
        if key not in characteristic:
            raise ValueError("characteristic missing required key '%s'" % key)
    identifier = _identifier(characteristic["id"], "characteristic id")
    unit = _identifier(characteristic["unit"], "unit of %s" % identifier)
    minimum = _real_or_none(characteristic.get("minimum"), "minimum of %s" % identifier)
    typical = _real_or_none(characteristic.get("typical"), "typical of %s" % identifier)
    maximum = _real_or_none(characteristic.get("maximum"), "maximum of %s" % identifier)
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError(
            "minimum %g of %s exceeds its maximum %g" % (minimum, identifier, maximum)
        )
    if minimum is not None and typical is not None and typical < minimum:
        raise ValueError(
            "typical %g of %s sits below its minimum %g" % (typical, identifier, minimum)
        )
    if maximum is not None and typical is not None and typical > maximum:
        raise ValueError(
            "typical %g of %s sits above its maximum %g" % (typical, identifier, maximum)
        )
    conditions = characteristic.get("test_conditions")
    if conditions is not None:
        conditions = _identifier(conditions, "test_conditions of %s" % identifier)
    return {
        "id": identifier,
        "unit": unit,
        "minimum": minimum,
        "typical": typical,
        "maximum": maximum,
        "test_conditions": conditions,
    }


def validate_characteristics(characteristics):
    """Return the normalized characteristic table, rejecting duplicate identifiers."""
    if not isinstance(characteristics, (list, tuple)) or not characteristics:
        raise ValueError("characteristics must be a non-empty sequence")
    records = []
    seen = set()
    for item in characteristics:
        record = validate_characteristic(item)
        if record["id"] in seen:
            raise ValueError("duplicate characteristic identifier %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
    return records


def characteristic_findings(records):
    """Return the content defects of a normalized characteristic table."""
    findings = []
    for record in records:
        if record["unit"].strip().lower() in PLACEHOLDER_UNITS:
            findings.append(
                "characteristic %s carries the placeholder unit %r"
                % (record["id"], record["unit"])
            )
        if record["test_conditions"] is None:
            findings.append("characteristic %s names no test conditions" % record["id"])
        if record["minimum"] is None and record["typical"] is None and record["maximum"] is None:
            findings.append("characteristic %s carries no value at all" % record["id"])
        elif record["minimum"] is None and record["maximum"] is None:
            findings.append(
                "characteristic %s publishes a typical value with no guaranteed edge"
                % record["id"]
            )
    return findings


def validate_rating(rating):
    """Return a normalized operating rating."""
    if not isinstance(rating, dict):
        raise ValueError("rating must be a mapping")
    for key in ("id", "absolute_maximum", "recommended_maximum"):
        if key not in rating:
            raise ValueError("rating missing required key '%s'" % key)
    identifier = _identifier(rating["id"], "rating id")
    absolute_max = _real(rating["absolute_maximum"], "absolute_maximum of %s" % identifier)
    if absolute_max <= 0.0:
        raise ValueError(
            "absolute_maximum of %s must be positive for a derating fraction, got %g"
            % (identifier, absolute_max)
        )
    recommended_max = _real(
        rating["recommended_maximum"], "recommended_maximum of %s" % identifier
    )
    absolute_min = _real_or_none(
        rating.get("absolute_minimum"), "absolute_minimum of %s" % identifier
    )
    recommended_min = _real_or_none(
        rating.get("recommended_minimum"), "recommended_minimum of %s" % identifier
    )
    if absolute_min is not None and absolute_min >= absolute_max:
        raise ValueError(
            "absolute_minimum %g of %s is not below its absolute_maximum %g"
            % (absolute_min, identifier, absolute_max)
        )
    if recommended_min is not None and recommended_min > recommended_max:
        raise ValueError(
            "recommended_minimum %g of %s exceeds its recommended_maximum %g"
            % (recommended_min, identifier, recommended_max)
        )
    if recommended_min is not None and absolute_min is None:
        raise ValueError(
            "rating %s gives a recommended minimum with no absolute minimum to hold it"
            % identifier
        )
    return {
        "id": identifier,
        "absolute_maximum": absolute_max,
        "recommended_maximum": recommended_max,
        "absolute_minimum": absolute_min,
        "recommended_minimum": recommended_min,
    }


def validate_ratings(ratings):
    """Return the normalized rating table, rejecting duplicate identifiers."""
    if not isinstance(ratings, (list, tuple)) or not ratings:
        raise ValueError("ratings must be a non-empty sequence")
    records = []
    seen = set()
    for item in ratings:
        record = validate_rating(item)
        if record["id"] in seen:
            raise ValueError("duplicate rating identifier %r" % record["id"])
        seen.add(record["id"])
        records.append(record)
    return records


def envelope_containment(rating):
    """Return the reasons a recommended range is not strictly inside the absolute one."""
    reasons = []
    if rating["recommended_maximum"] >= rating["absolute_maximum"]:
        reasons.append(
            "recommended maximum %g is at or beyond the absolute maximum %g"
            % (rating["recommended_maximum"], rating["absolute_maximum"])
        )
    if rating["absolute_minimum"] is not None and rating["recommended_minimum"] is not None:
        if rating["recommended_minimum"] <= rating["absolute_minimum"]:
            reasons.append(
                "recommended minimum %g is at or beyond the absolute minimum %g"
                % (rating["recommended_minimum"], rating["absolute_minimum"])
            )
    return reasons


def derating_margin(recommended_maximum, absolute_maximum):
    """Return the unused fraction of the absolute rating, one minus the quotient."""
    recommended = _real(recommended_maximum, "recommended_maximum")
    absolute = _real(absolute_maximum, "absolute_maximum")
    if absolute <= 0.0:
        raise ValueError("absolute_maximum must be positive, got %g" % absolute)
    return 1.0 - (recommended / absolute)


def grade_rating(rating, required_margin):
    """Return the graded rating with its derating margin and containment reasons."""
    record = validate_rating(rating)
    required = _real(required_margin, "required_margin")
    if required < 0.0 or required >= 1.0:
        raise ValueError("required_margin must lie in [0, 1), got %g" % required)
    margin = derating_margin(record["recommended_maximum"], record["absolute_maximum"])
    met = margin > required or math.isclose(
        margin, required, rel_tol=0.0, abs_tol=DERATING_TOLERANCE
    )
    reasons = envelope_containment(record)
    record["derating_margin"] = margin
    record["required_margin"] = required
    record["margin_met"] = met
    record["containment_reasons"] = reasons
    record["contained"] = not reasons
    return record


def worst_margin_parameter(graded_ratings):
    """Return the rating with the smallest derating margin (lowest id wins ties)."""
    if not isinstance(graded_ratings, (list, tuple)) or not graded_ratings:
        raise ValueError("graded_ratings must be a non-empty sequence")
    worst = None
    for record in graded_ratings:
        if "derating_margin" not in record:
            raise ValueError("each record must carry 'derating_margin'")
        if worst is None:
            worst = record
            continue
        if math.isclose(
            record["derating_margin"], worst["derating_margin"], rel_tol=0.0, abs_tol=1e-15
        ):
            if record["id"] < worst["id"]:
                worst = record
        elif record["derating_margin"] < worst["derating_margin"]:
            worst = record
    return worst


def assess_data_sheet(sheet):
    """Run the full Annex H device data sheet content assessment.

    sheet keys: sections, characteristics, ratings, required_derating_margin.
    """
    if not isinstance(sheet, dict):
        raise ValueError("sheet must be a mapping")
    for key in ("sections", "characteristics", "ratings", "required_derating_margin"):
        if key not in sheet:
            raise ValueError("sheet missing required key '%s'" % key)
    required = _real(sheet["required_derating_margin"], "required_derating_margin")
    if required < 0.0 or required >= 1.0:
        raise ValueError("required_derating_margin must lie in [0, 1), got %g" % required)

    absent = missing_sections(sheet["sections"])
    characteristics = validate_characteristics(sheet["characteristics"])
    ratings = [grade_rating(r, required) for r in validate_ratings(sheet["ratings"])]
    worst = worst_margin_parameter(ratings)

    findings = []
    for name in absent:
        findings.append("required section %r is absent from the data sheet" % name)
    findings.extend(characteristic_findings(characteristics))
    for record in ratings:
        for reason in record["containment_reasons"]:
            findings.append("rating %s: %s" % (record["id"], reason))
        if not record["margin_met"]:
            findings.append(
                "rating %s leaves a derating margin of %.4f, below the required %.4f"
                % (record["id"], record["derating_margin"], required)
            )
    return {
        "missing_sections": absent,
        "characteristics": characteristics,
        "ratings": ratings,
        "required_derating_margin": required,
        "worst_margin_parameter": worst["id"],
        "worst_derating_margin": worst["derating_margin"],
        "compliant": not findings,
        "findings": findings,
    }
