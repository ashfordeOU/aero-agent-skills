"""What a finished hybrid carries on its package body, and how hard-wearing it is.

Anchor: ECSS-Q-ST-60-05 clause 10.2.1 (the standard marking requirements: the
information a delivered hybrid shows on the body of its package, and the
durability and legibility that lettering has to keep).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The body mark is a fixed set of fields, not a free text. A field that is
  absent and a field that is present in the wrong form are different failures:
  the first leaves the unit unidentified, the second leaves it identified as
  something else, and only the second gets read by a human who trusts it.
* The lot date code and the serial number carry the traceability, so their
  form is checked and not merely their presence. A serial built from
  characters that read alike by eye is a transcription error waiting in every
  incoming inspection.
* Character height is set by the body that has to carry it. A small package is
  allowed smaller lettering, but there is a height below which no package is
  allowed to go, and a mark readable only under magnification is an open
  action even when it is within the height.
* Contrast is part of legibility. Lettering the same shade as the package is
  invisible whatever its height, so the mark-to-body reflectance ratio is
  judged alongside the geometry.
* Durability is demonstrated, not asserted. The evidence is a set of solvent
  exposures of at least the required dwell across the required distinct
  solutions, each followed by a legibility reading. Fewer exposures than
  required is an incomplete test, not a weaker pass; lettering lost after an
  exposure is a failure of the marking, not of the test.
* The marking-completeness index is weighted credit over total weight. It
  ranks what is outstanding; an absent mandatory field, a malformed mandatory
  field, lettering under the height floor, insufficient contrast or lost
  legibility decides the outcome on its own, at any index.
"""

from __future__ import annotations

import math

# Fields the body of a delivered hybrid carries, and the share of the
# identification each supplies.
FIELD_WEIGHTS = {
    "manufacturer-identification": 1.0,
    "part-or-type-number": 1.0,
    "lot-date-code": 1.0,
    "serial-number": 1.0,
    "pin-one-or-polarity-indicator": 0.9,
    "electrostatic-sensitivity-symbol": 0.5,
    "country-of-origin": 0.4,
    "screening-level-code": 0.4,
}

# Without these the unit is not identified at all.
MANDATORY_BODY_FIELDS = (
    "manufacturer-identification",
    "part-or-type-number",
    "lot-date-code",
    "serial-number",
    "pin-one-or-polarity-indicator",
)

FIELD_STATE_CREDIT = {
    "present-and-valid": 1.0,
    "present-with-format-finding": 0.5,
    "absent": 0.0,
}

# Character sets each field is written from.
UPPERCASE_ALPHANUMERIC = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
PART_NUMBER_CHARACTERS = UPPERCASE_ALPHANUMERIC | set("-/")
DIGITS = set("0123456789")

# Characters that read alike by eye and so are kept out of a hand-read serial.
AMBIGUOUS_SERIAL_CHARACTERS = set("IOQ")

MANUFACTURER_CODE_LENGTH = (2, 5)
PART_NUMBER_LENGTH = (3, 16)
SERIAL_NUMBER_LENGTH = (1, 8)
DATE_CODE_LENGTH = 4
MAXIMUM_ISO_WEEK = 53

# Forms the pin-one or polarity indicator may take.
INDICATOR_FORMS = ("printed-dot", "printed-bar", "printed-triangle", "package-chamfer", "package-notch")

# Levels a screening code may name.
SCREENING_LEVELS = ("level-1", "level-2", "level-3")

# Character height the body has to carry, by the area available on it.
LARGE_BODY_AREA_MM2 = 100.0
MEDIUM_BODY_AREA_MM2 = 25.0
LARGE_BODY_CHARACTER_HEIGHT_MM = 0.8
MEDIUM_BODY_CHARACTER_HEIGHT_MM = 0.5
SMALL_BODY_CHARACTER_HEIGHT_MM = 0.3

# Below this height the mark is read with an aid, whatever the package size.
UNAIDED_READING_HEIGHT_MM = 0.8

# Mark-to-body reflectance ratio the lettering has to stand out by.
MINIMUM_CONTRAST_RATIO = 2.0

# Solvent-resistance evidence the durability rests on.
KNOWN_SOLVENTS = ("polar-solvent", "non-polar-solvent", "aqueous-detergent")
REQUIRED_DISTINCT_SOLVENTS = 3
REQUIRED_IMMERSION_MINUTES = 1.0

POST_TEST_LEGIBILITY_STATES = (
    "fully-legible",
    "partially-illegible",
    "smeared",
    "removed",
)

# Marking-completeness index a compliant body mark has to reach.
ACCEPTANCE_INDEX = 0.90

# Heights, ratios and indices are float quantities meant to be met exactly at
# their bounds; a case sitting on a bound can land a few units away from it.
MARKING_TOLERANCE = 1e-9

VERDICTS = (
    "body-marking-meets-standard-requirements",
    "body-marking-meets-requirements-with-open-actions",
    "body-marking-does-not-meet-requirements",
    "body-marking-assessment-incomplete",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return ``value`` as a finite positive float or raise."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _string(value, label):
    """Return ``value`` as a non-empty string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def field_weight(name):
    """Weight of one body-marking field; unknown field names are rejected."""
    if name not in FIELD_WEIGHTS:
        raise ValueError(
            "unknown body-marking field %r (known: %s)"
            % (name, ", ".join(sorted(FIELD_WEIGHTS)))
        )
    return FIELD_WEIGHTS[name]


def field_state_credit(state):
    """Credit a field state earns."""
    if state not in FIELD_STATE_CREDIT:
        raise ValueError(
            "unknown field state %r (known: %s)"
            % (state, ", ".join(sorted(FIELD_STATE_CREDIT)))
        )
    return FIELD_STATE_CREDIT[state]


def validate_manufacturer_identification(value):
    """Format findings on the code identifying who built the unit."""
    text = _string(value, "manufacturer-identification")
    findings = []
    low, high = MANUFACTURER_CODE_LENGTH
    if len(text) < low or len(text) > high:
        findings.append("manufacturer-code-length-outside-the-allowed-range")
    if any(character not in UPPERCASE_ALPHANUMERIC for character in text):
        findings.append("manufacturer-code-uses-characters-outside-the-set")
    return findings


def validate_part_number(value):
    """Format findings on the part or type number."""
    text = _string(value, "part-or-type-number")
    findings = []
    low, high = PART_NUMBER_LENGTH
    if len(text) < low or len(text) > high:
        findings.append("part-number-length-outside-the-allowed-range")
    if any(character not in PART_NUMBER_CHARACTERS for character in text):
        findings.append("part-number-uses-characters-outside-the-set")
    return findings


def validate_date_code(value):
    """Format findings on the four-figure year-and-week lot date code."""
    text = _string(value, "lot-date-code")
    findings = []
    if len(text) != DATE_CODE_LENGTH:
        findings.append("date-code-is-not-four-figures")
        return findings
    if any(character not in DIGITS for character in text):
        findings.append("date-code-is-not-all-figures")
        return findings
    week = int(text[2:])
    if week < 1 or week > MAXIMUM_ISO_WEEK:
        findings.append("date-code-week-outside-the-calendar")
    return findings


def validate_serial_number(value):
    """Format findings on the serial number, ambiguous characters included."""
    text = _string(value, "serial-number")
    findings = []
    low, high = SERIAL_NUMBER_LENGTH
    if len(text) < low or len(text) > high:
        findings.append("serial-number-length-outside-the-allowed-range")
    if any(character not in UPPERCASE_ALPHANUMERIC for character in text):
        findings.append("serial-number-uses-characters-outside-the-set")
    if any(character in AMBIGUOUS_SERIAL_CHARACTERS for character in text):
        findings.append("serial-number-uses-characters-that-read-alike")
    return findings


def validate_indicator(value):
    """Format findings on the pin-one or polarity indicator."""
    text = _string(value, "pin-one-or-polarity-indicator")
    if text not in INDICATOR_FORMS:
        return ["indicator-form-not-one-of-the-accepted-forms"]
    return []


def validate_country_of_origin(value):
    """Format findings on the two-letter country of origin."""
    text = _string(value, "country-of-origin")
    findings = []
    if len(text) != 2:
        findings.append("country-code-is-not-two-letters")
    if any(character not in UPPERCASE_ALPHANUMERIC for character in text):
        findings.append("country-code-uses-characters-outside-the-set")
    return findings


def validate_screening_level(value):
    """Format findings on the screening-level code."""
    text = _string(value, "screening-level-code")
    if text not in SCREENING_LEVELS:
        return ["screening-level-not-one-of-the-published-levels"]
    return []


def validate_symbol(value):
    """Format findings on the electrostatic sensitivity symbol."""
    text = _string(value, "electrostatic-sensitivity-symbol")
    if text != "sensitive-device-symbol":
        return ["electrostatic-symbol-not-the-published-symbol"]
    return []


FIELD_VALIDATORS = {
    "manufacturer-identification": validate_manufacturer_identification,
    "part-or-type-number": validate_part_number,
    "lot-date-code": validate_date_code,
    "serial-number": validate_serial_number,
    "pin-one-or-polarity-indicator": validate_indicator,
    "electrostatic-sensitivity-symbol": validate_symbol,
    "country-of-origin": validate_country_of_origin,
    "screening-level-code": validate_screening_level,
}


def field_format_findings(name, value):
    """Format findings for one body-marking field."""
    field_weight(name)  # validation only
    return FIELD_VALIDATORS[name](value)


def assess_field(name, value):
    """Grade one body-marking field into a credit and its findings."""
    weight = field_weight(name)
    mandatory = name in MANDATORY_BODY_FIELDS
    if value is None:
        state = "absent"
        findings = ["field-absent-from-the-body-mark"]
    else:
        format_findings = field_format_findings(name, value)
        state = "present-with-format-finding" if format_findings else "present-and-valid"
        findings = list(format_findings)
    credit = field_state_credit(state)
    return {
        "field": name,
        "value": value,
        "state": state,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory": mandatory,
        "mandatory_absent": mandatory and state == "absent",
        "mandatory_malformed": mandatory and state == "present-with-format-finding",
        "findings": findings,
    }


def optional_body_fields():
    """Fields the body may carry beyond the ones it must."""
    return tuple(name for name in sorted(FIELD_WEIGHTS) if name not in MANDATORY_BODY_FIELDS)


def applicable_field_set(applicable_optional=()):
    """Fields this delivery is graded on: the mandatory set plus those called for."""
    if not isinstance(applicable_optional, (list, tuple)):
        raise ValueError(
            "applicable_optional must be a list or tuple, got %r"
            % (type(applicable_optional).__name__,)
        )
    extra = []
    for name in applicable_optional:
        field_weight(name)  # validation only
        if name in MANDATORY_BODY_FIELDS:
            raise ValueError("%r is already a mandatory field" % (name,))
        if name not in extra:
            extra.append(name)
    return tuple(sorted(set(MANDATORY_BODY_FIELDS) | set(extra)))


def marking_completeness_index(records):
    """Weighted credit of a set of graded fields over the total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (type(records).__name__,))
    if len(records) == 0:
        raise ValueError("a body mark must carry at least one field")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total field weight must be positive")
    return earned / total_weight


def minimum_character_height_mm(body_area_mm2):
    """Smallest lettering the body of a given size may carry."""
    area = _positive(body_area_mm2, "body_area_mm2")
    if area >= LARGE_BODY_AREA_MM2 - MARKING_TOLERANCE:
        return LARGE_BODY_CHARACTER_HEIGHT_MM
    if area >= MEDIUM_BODY_AREA_MM2 - MARKING_TOLERANCE:
        return MEDIUM_BODY_CHARACTER_HEIGHT_MM
    return SMALL_BODY_CHARACTER_HEIGHT_MM


def assess_character_height(character_height_mm, body_area_mm2):
    """Grade the lettering height against the body carrying it."""
    height = _positive(character_height_mm, "character_height_mm")
    required = minimum_character_height_mm(body_area_mm2)
    findings = []
    if height < required - MARKING_TOLERANCE:
        findings.append("character-height-below-the-minimum-for-this-body")
    elif height < UNAIDED_READING_HEIGHT_MM - MARKING_TOLERANCE:
        findings.append("marking-readable-only-under-magnification")
    return {
        "character_height_mm": height,
        "required_height_mm": required,
        "adequate": "character-height-below-the-minimum-for-this-body" not in findings,
        "findings": findings,
    }


def contrast_ratio(mark_reflectance, body_reflectance):
    """Reflectance ratio between the lettering and the package around it."""
    mark = _positive(mark_reflectance, "mark_reflectance")
    body = _positive(body_reflectance, "body_reflectance")
    for value, label in ((mark, "mark_reflectance"), (body, "body_reflectance")):
        if value > 1.0:
            raise ValueError("%s must not exceed unity, got %r" % (label, value))
    return max(mark, body) / min(mark, body)


def contrast_is_sufficient(mark_reflectance, body_reflectance):
    """True when the lettering stands out from the package by enough."""
    return (
        contrast_ratio(mark_reflectance, body_reflectance)
        >= MINIMUM_CONTRAST_RATIO - MARKING_TOLERANCE
    )


def normalize_exposure(raw):
    """Validate one solvent exposure and its post-test legibility reading."""
    if not isinstance(raw, dict):
        raise ValueError("exposure must be a mapping, got %r" % (type(raw).__name__,))
    solvent = raw.get("solvent")
    if solvent not in KNOWN_SOLVENTS:
        raise ValueError(
            "unknown solvent %r (known: %s)" % (solvent, ", ".join(sorted(KNOWN_SOLVENTS)))
        )
    minutes = _real(raw.get("immersion_minutes"), "immersion_minutes")
    if minutes < 0.0:
        raise ValueError("immersion_minutes must not be negative, got %r" % (minutes,))
    legibility = raw.get("post_test_legibility")
    if legibility not in POST_TEST_LEGIBILITY_STATES:
        raise ValueError(
            "unknown post-test legibility %r (known: %s)"
            % (legibility, ", ".join(sorted(POST_TEST_LEGIBILITY_STATES)))
        )
    return {
        "solvent": solvent,
        "immersion_minutes": minutes,
        "post_test_legibility": legibility,
    }


def assess_durability(exposures):
    """Grade the solvent-resistance evidence behind the lettering."""
    if not isinstance(exposures, (list, tuple)):
        raise ValueError("exposures must be a list or tuple, got %r" % (type(exposures).__name__,))
    records = [normalize_exposure(raw) for raw in exposures]
    findings = []
    short = [r for r in records if r["immersion_minutes"] < REQUIRED_IMMERSION_MINUTES - MARKING_TOLERANCE]
    lost = [r for r in records if r["post_test_legibility"] != "fully-legible"]
    solvents = sorted({r["solvent"] for r in records})
    if len(solvents) < REQUIRED_DISTINCT_SOLVENTS:
        findings.append("durability-evidence-misses-a-required-solvent")
    for record in short:
        findings.append("immersion-shorter-than-the-required-dwell")
    for record in lost:
        findings.append("lettering-not-fully-legible-after-exposure")
    complete = len(solvents) >= REQUIRED_DISTINCT_SOLVENTS and len(short) == 0
    return {
        "exposure_count": len(records),
        "solvents": solvents,
        "short_immersions": len(short),
        "exposures_losing_legibility": len(lost),
        "complete": complete,
        "demonstrated": complete and len(lost) == 0,
        "findings": findings,
    }


def assess_body_marking(
    unit_id,
    fields,
    character_height_mm,
    body_area_mm2,
    mark_reflectance,
    body_reflectance,
    solvent_exposures,
    applicable_optional=(),
):
    """Grade the body mark of one delivered hybrid and name a verdict."""
    _string(unit_id, "unit_id")
    if not isinstance(fields, dict):
        raise ValueError("fields must be a mapping, got %r" % (type(fields).__name__,))
    for name in fields:
        field_weight(name)  # rejects a field the body mark has no place for

    graded = set(applicable_field_set(applicable_optional)) | set(fields)
    field_records = []
    for name in sorted(graded):
        field_records.append(assess_field(name, fields.get(name)))
    index = marking_completeness_index(field_records)

    height_record = assess_character_height(character_height_mm, body_area_mm2)
    ratio = contrast_ratio(mark_reflectance, body_reflectance)
    contrast_ok = ratio >= MINIMUM_CONTRAST_RATIO - MARKING_TOLERANCE
    durability = assess_durability(solvent_exposures)

    findings = []
    for record in field_records:
        for finding in record["findings"]:
            findings.append(
                {"item": record["field"], "finding": finding, "detail": record["state"]}
            )
    for finding in height_record["findings"]:
        findings.append(
            {
                "item": "character-height",
                "finding": finding,
                "detail": "%.2f mm against %.2f mm required"
                % (height_record["character_height_mm"], height_record["required_height_mm"]),
            }
        )
    if not contrast_ok:
        findings.append(
            {
                "item": "marking-contrast",
                "finding": "mark-to-body-contrast-below-the-minimum",
                "detail": "ratio %.2f" % (ratio,),
            }
        )
    for finding in durability["findings"]:
        findings.append(
            {
                "item": "solvent-resistance",
                "finding": finding,
                "detail": "%d exposures across %d solvents"
                % (durability["exposure_count"], len(durability["solvents"])),
            }
        )

    incomplete = (
        any(record["mandatory_absent"] for record in field_records) or not durability["complete"]
    )
    non_conforming = (
        any(record["mandatory_malformed"] for record in field_records)
        or not height_record["adequate"]
        or not contrast_ok
        or not durability["demonstrated"]
        or index < ACCEPTANCE_INDEX - MARKING_TOLERANCE
    )
    if incomplete:
        verdict = "body-marking-assessment-incomplete"
    elif non_conforming:
        verdict = "body-marking-does-not-meet-requirements"
    elif findings:
        verdict = "body-marking-meets-requirements-with-open-actions"
    else:
        verdict = "body-marking-meets-standard-requirements"
    return {
        "unit_id": unit_id,
        "graded_fields": sorted(graded),
        "field_records": field_records,
        "marking_completeness_index": index,
        "character_height": height_record,
        "contrast_ratio": ratio,
        "contrast_sufficient": contrast_ok,
        "durability": durability,
        "findings": findings,
        "verdict": verdict,
        "marking_accepted": verdict
        in (
            "body-marking-meets-standard-requirements",
            "body-marking-meets-requirements-with-open-actions",
        ),
    }
