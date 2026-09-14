"""Evaluation test campaign assessment for a class 1 commercial EEE part type.

Anchor: ECSS-Q-ST-60-13C clause 4.2.3.4 (the evaluation test campaign that
qualifies a commercial part type for flight use). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the identity of the part type under evaluation: manufacturer,
   part number and the date-code or wafer-lot set the evaluation samples were
   drawn from. An evaluation with no traceable identity qualifies nothing.
2. Validate each executed test block: how many samples entered it, how many
   failed, how many failures the block admits, and how long the block ran.
3. Check the campaign covers every mandatory block; a block that is absent is
   not a zero-failure block, it is a coverage shortfall.
4. Hold every executed block to its sample-size floor and to its admissible
   failure count, and report each block verdict separately so the campaign
   reports all shortfalls rather than the first one found.
5. Check the lot diversity of the sample set against the declared minimum, so
   the verdict describes the part type and not a single good lot.
6. Accumulate endurance device-hours (samples x duration) across the endurance
   blocks and compare with the required floor under a named tolerance.
7. Return the per-block records, the aggregate figures and a qualification
   verdict carrying every finding.
"""

import math

__all__ = [
    "MANDATORY_BLOCKS",
    "DEVICE_HOUR_TOLERANCE",
    "ENDURANCE_BLOCKS",
    "validate_part_type",
    "lot_diversity",
    "validate_block",
    "block_device_hours",
    "assess_block",
    "campaign_device_hours",
    "missing_blocks",
    "assess_evaluation_campaign",
]

# Blocks an evaluation campaign has to execute before a commercial part type
# may be put forward for flight. Names are normalized (lower case, hyphenated).
MANDATORY_BLOCKS = (
    "construction-analysis",
    "electrical-characterization",
    "environmental-stress",
    "endurance",
    "radiation",
)

# Blocks whose accumulated device-hours count towards the endurance floor.
ENDURANCE_BLOCKS = ("endurance", "environmental-stress")

# Device-hours are a product of a count and a duration: an exactly-met floor
# can land a few ULPs low. Absorb the representation error here rather than
# lowering the engineering floor.
DEVICE_HOUR_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_count(value, label, minimum=0):
    """Return a validated non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def _require_positive_real(value, label, allow_zero=False):
    """Return a validated finite real quantity."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if allow_zero:
        if number < 0.0:
            raise ValueError("%s must not be negative, got %g" % (label, number))
    elif number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _normalize_block_name(value, label="block name"):
    """Return a block name in the normalized lower-case hyphenated form."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def validate_part_type(part_type):
    """Return the validated identity of the part type under evaluation."""
    if not isinstance(part_type, dict):
        raise ValueError("part_type must be a mapping")
    for key in ("manufacturer", "part_number", "date_codes"):
        if key not in part_type:
            raise ValueError("part_type missing required key '%s'" % key)
    manufacturer = _require_text(part_type["manufacturer"], "manufacturer")
    part_number = _require_text(part_type["part_number"], "part_number")
    raw_codes = part_type["date_codes"]
    if not isinstance(raw_codes, (list, tuple)) or not raw_codes:
        raise ValueError("date_codes must be a non-empty sequence")
    codes = []
    for index, code in enumerate(raw_codes):
        codes.append(_require_text(code, "date_codes[%d]" % index))
    return {
        "manufacturer": manufacturer,
        "part_number": part_number,
        "date_codes": codes,
    }


def lot_diversity(part_type):
    """Return how many distinct date-code or wafer lots the samples came from."""
    identity = validate_part_type(part_type)
    return len(set(identity["date_codes"]))


def validate_block(block):
    """Return one validated evaluation test-block record."""
    if not isinstance(block, dict):
        raise ValueError("each test block must be a mapping")
    for key in ("name", "samples", "failures"):
        if key not in block:
            raise ValueError("test block missing required key '%s'" % key)
    name = _normalize_block_name(block["name"])
    samples = _require_count(block["samples"], "samples for block '%s'" % name, minimum=1)
    failures = _require_count(block["failures"], "failures for block '%s'" % name)
    allowed = _require_count(
        block.get("allowed_failures", 0), "allowed_failures for block '%s'" % name
    )
    duration_h = _require_positive_real(
        block.get("duration_h", 0.0), "duration_h for block '%s'" % name, allow_zero=True
    )
    minimum_samples = block.get("minimum_samples")
    if minimum_samples is not None:
        minimum_samples = _require_count(
            minimum_samples, "minimum_samples for block '%s'" % name, minimum=1
        )
    if failures > samples:
        raise ValueError(
            "block '%s' reports %d failures out of %d samples" % (name, failures, samples)
        )
    return {
        "name": name,
        "samples": samples,
        "failures": failures,
        "allowed_failures": allowed,
        "duration_h": duration_h,
        "minimum_samples": minimum_samples,
    }


def block_device_hours(block):
    """Return the device-hours accumulated by one validated test block."""
    record = validate_block(block)
    return float(record["samples"]) * record["duration_h"]


def assess_block(block, default_minimum_samples):
    """Return a block record carrying its own verdict and findings."""
    record = validate_block(block)
    floor = record["minimum_samples"]
    if floor is None:
        floor = _require_count(default_minimum_samples, "default_minimum_samples", minimum=1)
    findings = []
    if record["samples"] < floor:
        findings.append(
            "block '%s' tested %d samples, below the floor of %d"
            % (record["name"], record["samples"], floor)
        )
    if record["failures"] > record["allowed_failures"]:
        findings.append(
            "block '%s' recorded %d failures against %d admissible"
            % (record["name"], record["failures"], record["allowed_failures"])
        )
    record["applied_minimum_samples"] = floor
    record["device_hours"] = float(record["samples"]) * record["duration_h"]
    record["findings"] = findings
    record["passed"] = not findings
    return record


def missing_blocks(records):
    """Return the mandatory block names absent from the executed set."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of block records")
    executed = set()
    for record in records:
        if not isinstance(record, dict) or "name" not in record:
            raise ValueError("each record must be a mapping carrying 'name'")
        executed.add(record["name"])
    return [name for name in MANDATORY_BLOCKS if name not in executed]


def campaign_device_hours(records):
    """Return the device-hours accumulated across the endurance-bearing blocks."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of block records")
    total = 0.0
    for record in records:
        if not isinstance(record, dict) or "name" not in record:
            raise ValueError("each record must be a mapping carrying 'name'")
        if record["name"] in ENDURANCE_BLOCKS:
            total += float(record.get("device_hours", 0.0))
    return total


def assess_evaluation_campaign(spec):
    """Run the full clause 4.2.3.4 evaluation-campaign assessment.

    spec keys: part_type, blocks, minimum_samples, minimum_lots,
    required_device_hours.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("part_type", "blocks", "minimum_samples", "minimum_lots",
                "required_device_hours"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    identity = validate_part_type(spec["part_type"])
    blocks = spec["blocks"]
    if not isinstance(blocks, (list, tuple)) or not blocks:
        raise ValueError("spec['blocks'] must be a non-empty sequence of test blocks")
    default_minimum = _require_count(spec["minimum_samples"], "minimum_samples", minimum=1)
    minimum_lots = _require_count(spec["minimum_lots"], "minimum_lots", minimum=1)
    required_hours = _require_positive_real(
        spec["required_device_hours"], "required_device_hours", allow_zero=True
    )

    records = []
    seen = set()
    for block in blocks:
        record = assess_block(block, default_minimum)
        if record["name"] in seen:
            raise ValueError("test block '%s' is declared twice" % record["name"])
        seen.add(record["name"])
        records.append(record)

    findings = []
    absent = missing_blocks(records)
    for name in absent:
        findings.append("mandatory evaluation block '%s' was not executed" % name)
    for record in records:
        findings.extend(record["findings"])

    lots = len(set(identity["date_codes"]))
    if lots < minimum_lots:
        findings.append(
            "samples came from %d lot(s), below the declared minimum of %d"
            % (lots, minimum_lots)
        )

    accumulated = campaign_device_hours(records)
    hours_met = accumulated > required_hours or math.isclose(
        accumulated, required_hours, rel_tol=0.0, abs_tol=DEVICE_HOUR_TOLERANCE
    )
    if not hours_met:
        findings.append(
            "endurance accumulated %.3f device-hours, below the required %.3f"
            % (accumulated, required_hours)
        )

    return {
        "part_type": identity,
        "blocks": records,
        "missing_blocks": absent,
        "lots": lots,
        "minimum_lots": minimum_lots,
        "accumulated_device_hours": accumulated,
        "required_device_hours": required_hours,
        "device_hours_met": hours_met,
        "qualified": not findings,
        "findings": findings,
    }
