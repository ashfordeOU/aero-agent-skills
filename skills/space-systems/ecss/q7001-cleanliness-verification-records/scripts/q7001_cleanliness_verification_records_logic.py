"""Traceability of cleanliness verification records to hardware and levels.

Anchor: ECSS-Q-ST-70-01 verification clause (recording the result of a
cleanliness verification so that it is traceable to the hardware item it was
taken from and to the cleanliness level it was graded against). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every verification record: it names a hardware item, a surface, a
   sampled area, a method, the instrument used, the day of measurement, the
   operator, the level achieved and the level required.
2. Grade the achieved level against the required level on the ladder the two
   share; a particulate result cannot be graded against a molecular limit.
3. Reject a record whose instrument calibration had already lapsed on the day
   the measurement was taken -- the figure is not traceable to a calibrated
   instrument, so it is not evidence.
4. Mark a record superseded when the same hardware surface was handled, opened
   or reworked after the measurement day; the barrier was broken afterwards,
   so the record no longer describes the delivered state.
5. Compare the surviving records against the declared inventory: report the
   hardware surfaces no record covers, and the records that point at a surface
   the inventory does not contain.
6. Return the per-record findings, the traceable coverage fraction and the
   dossier disposition.
"""

import math

__all__ = [
    "PARTICULATE_LEVELS",
    "MOLECULAR_LEVELS",
    "REQUIRED_RECORD_KEYS",
    "COVERAGE_TOLERANCE",
    "level_family",
    "level_rank",
    "meets_level",
    "validate_record",
    "validate_inventory",
    "record_findings",
    "superseded_record_ids",
    "acceptable_records",
    "coverage_gaps",
    "orphan_record_ids",
    "traceable_coverage",
    "assess_verification_records",
]

# Surface particulate ladder, cleanest first. The number is the largest
# particle size in micrometres the level tolerates on the witnessed area.
PARTICULATE_LEVELS = (
    "PCL-50",
    "PCL-100",
    "PCL-200",
    "PCL-300",
    "PCL-500",
    "PCL-750",
    "PCL-1000",
)

# Non-volatile residue ladder, cleanest first. The suffix is the fraction of
# the reference residue loading per witnessed area the level tolerates.
MOLECULAR_LEVELS = (
    "NVR-A/10",
    "NVR-A/5",
    "NVR-A/2",
    "NVR-A",
    "NVR-B",
    "NVR-C",
)

REQUIRED_RECORD_KEYS = (
    "record_id",
    "hardware_id",
    "surface",
    "area_m2",
    "method",
    "verified_level",
    "required_level",
    "instrument_id",
    "calibration_valid_until_day",
    "verification_day",
    "operator",
)

# Coverage is a ratio of small integer counts; absorb representation error at
# the completeness boundary instead of relaxing the completeness rule.
COVERAGE_TOLERANCE = 1e-9

_TEXT_KEYS = (
    "record_id",
    "hardware_id",
    "surface",
    "method",
    "instrument_id",
    "operator",
)


def _require_text(value, label):
    """Return a stripped non-empty string or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _require_day(value, label):
    """Return an integer day index (days from the dossier epoch) or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer day index, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def level_family(level_name):
    """Return 'particulate' or 'molecular' for a cleanliness level name."""
    name = _require_text(level_name, "level name")
    if name in PARTICULATE_LEVELS:
        return "particulate"
    if name in MOLECULAR_LEVELS:
        return "molecular"
    raise ValueError("unknown cleanliness level %r" % (level_name,))


def level_rank(level_name):
    """Return the ladder index of a level; lower index means cleaner."""
    name = _require_text(level_name, "level name")
    if name in PARTICULATE_LEVELS:
        return PARTICULATE_LEVELS.index(name)
    if name in MOLECULAR_LEVELS:
        return MOLECULAR_LEVELS.index(name)
    raise ValueError("unknown cleanliness level %r" % (level_name,))


def meets_level(verified_level, required_level):
    """Return True when the verified level is at least as clean as required."""
    family_verified = level_family(verified_level)
    family_required = level_family(required_level)
    if family_verified != family_required:
        raise ValueError(
            "cannot grade a %s result against a %s requirement"
            % (family_verified, family_required)
        )
    return level_rank(verified_level) <= level_rank(required_level)


def validate_record(record):
    """Return a normalized verification record, raising on anything missing."""
    if not isinstance(record, dict):
        raise ValueError("a verification record must be a mapping")
    for key in REQUIRED_RECORD_KEYS:
        if key not in record:
            raise ValueError("verification record missing required key '%s'" % key)
    normalized = {}
    for key in _TEXT_KEYS:
        normalized[key] = _require_text(record[key], key)
    area = record["area_m2"]
    if isinstance(area, bool) or not isinstance(area, (int, float)):
        raise ValueError("area_m2 must be a real number, got %r" % (area,))
    area = float(area)
    if not math.isfinite(area) or area <= 0.0:
        raise ValueError("area_m2 must be positive and finite, got %r" % (record["area_m2"],))
    normalized["area_m2"] = area
    normalized["verified_level"] = _require_text(record["verified_level"], "verified_level")
    normalized["required_level"] = _require_text(record["required_level"], "required_level")
    # Raises when either name is unknown or the two ladders do not match.
    meets_level(normalized["verified_level"], normalized["required_level"])
    normalized["level_family"] = level_family(normalized["verified_level"])
    normalized["verification_day"] = _require_day(
        record["verification_day"], "verification_day"
    )
    normalized["calibration_valid_until_day"] = _require_day(
        record["calibration_valid_until_day"], "calibration_valid_until_day"
    )
    return normalized


def validate_inventory(inventory):
    """Return the inventory as a list of (hardware_id, surface) pairs."""
    if not isinstance(inventory, (list, tuple)) or not inventory:
        raise ValueError("inventory must be a non-empty sequence of hardware items")
    pairs = []
    for index, item in enumerate(inventory):
        if not isinstance(item, dict):
            raise ValueError("inventory[%d] must be a mapping" % index)
        for key in ("hardware_id", "surfaces"):
            if key not in item:
                raise ValueError("inventory[%d] missing required key '%s'" % (index, key))
        hardware_id = _require_text(item["hardware_id"], "inventory[%d].hardware_id" % index)
        surfaces = item["surfaces"]
        if not isinstance(surfaces, (list, tuple)) or not surfaces:
            raise ValueError("inventory[%d].surfaces must be a non-empty sequence" % index)
        for surface in surfaces:
            name = _require_text(surface, "inventory[%d] surface" % index)
            pair = (hardware_id, name)
            if pair in pairs:
                raise ValueError(
                    "inventory declares %s/%s twice" % (hardware_id, name)
                )
            pairs.append(pair)
    return pairs


def record_findings(record):
    """Return the findings that disqualify one record as delivered evidence."""
    normalized = validate_record(record)
    findings = []
    if normalized["calibration_valid_until_day"] < normalized["verification_day"]:
        findings.append(
            "record %s used instrument %s whose calibration lapsed on day %d, "
            "before the measurement on day %d"
            % (
                normalized["record_id"],
                normalized["instrument_id"],
                normalized["calibration_valid_until_day"],
                normalized["verification_day"],
            )
        )
    if not meets_level(normalized["verified_level"], normalized["required_level"]):
        findings.append(
            "record %s verified %s on %s/%s but %s was required"
            % (
                normalized["record_id"],
                normalized["verified_level"],
                normalized["hardware_id"],
                normalized["surface"],
                normalized["required_level"],
            )
        )
    return findings


def superseded_record_ids(records, handling_events):
    """Return the ids of records the later handling of their surface voided."""
    normalized_records = [validate_record(record) for record in records or []]
    events = []
    for index, event in enumerate(handling_events or []):
        if not isinstance(event, dict):
            raise ValueError("handling_events[%d] must be a mapping" % index)
        for key in ("hardware_id", "surface", "day"):
            if key not in event:
                raise ValueError(
                    "handling_events[%d] missing required key '%s'" % (index, key)
                )
        events.append(
            (
                _require_text(event["hardware_id"], "handling event hardware_id"),
                _require_text(event["surface"], "handling event surface"),
                _require_day(event["day"], "handling event day"),
            )
        )
    superseded = []
    for record in normalized_records:
        for hardware_id, surface, day in events:
            if hardware_id != record["hardware_id"] or surface != record["surface"]:
                continue
            if day > record["verification_day"]:
                superseded.append(record["record_id"])
                break
    return superseded


def acceptable_records(records, handling_events=None):
    """Return the normalized records that stand as delivered evidence."""
    voided = set(superseded_record_ids(records, handling_events))
    kept = []
    for record in records or []:
        normalized = validate_record(record)
        if normalized["record_id"] in voided:
            continue
        if record_findings(record):
            continue
        kept.append(normalized)
    return kept


def coverage_gaps(inventory, records, handling_events=None):
    """Return the inventory surfaces no acceptable record covers."""
    pairs = validate_inventory(inventory)
    covered = set(
        (record["hardware_id"], record["surface"])
        for record in acceptable_records(records, handling_events)
    )
    return [pair for pair in pairs if pair not in covered]


def orphan_record_ids(inventory, records):
    """Return the ids of records pointing at a surface the inventory lacks."""
    pairs = set(validate_inventory(inventory))
    orphans = []
    for record in records or []:
        normalized = validate_record(record)
        if (normalized["hardware_id"], normalized["surface"]) not in pairs:
            orphans.append(normalized["record_id"])
    return orphans


def traceable_coverage(inventory, records, handling_events=None):
    """Return the fraction of inventory surfaces backed by usable evidence."""
    pairs = validate_inventory(inventory)
    gaps = coverage_gaps(inventory, records, handling_events)
    return float(len(pairs) - len(gaps)) / float(len(pairs))


def assess_verification_records(dossier):
    """Run the full verification-record traceability assessment.

    dossier keys: inventory (sequence of hardware items with surfaces),
    records (sequence of verification records), optional handling_events.
    """
    if not isinstance(dossier, dict):
        raise ValueError("dossier must be a mapping")
    for key in ("inventory", "records"):
        if key not in dossier:
            raise ValueError("dossier missing required key '%s'" % key)
    records = dossier["records"]
    if not isinstance(records, (list, tuple)):
        raise ValueError("dossier['records'] must be a sequence")
    handling_events = dossier.get("handling_events")
    pairs = validate_inventory(dossier["inventory"])

    per_record = []
    findings = []
    voided = set(superseded_record_ids(records, handling_events))
    seen_ids = set()
    for record in records:
        normalized = validate_record(record)
        record_id = normalized["record_id"]
        if record_id in seen_ids:
            raise ValueError("record id %r appears twice in the dossier" % record_id)
        seen_ids.add(record_id)
        own = record_findings(record)
        superseded = record_id in voided
        if superseded:
            own = own + [
                "record %s was superseded by later handling of %s/%s"
                % (record_id, normalized["hardware_id"], normalized["surface"])
            ]
        findings.extend(own)
        per_record.append(
            {
                "record_id": record_id,
                "hardware_id": normalized["hardware_id"],
                "surface": normalized["surface"],
                "verified_level": normalized["verified_level"],
                "required_level": normalized["required_level"],
                "level_family": normalized["level_family"],
                "area_m2": normalized["area_m2"],
                "superseded": superseded,
                "usable": not own,
                "findings": own,
            }
        )

    orphans = orphan_record_ids(dossier["inventory"], records)
    for record_id in orphans:
        findings.append(
            "record %s points at a surface the inventory does not declare" % record_id
        )
    gaps = coverage_gaps(dossier["inventory"], records, handling_events)
    for hardware_id, surface in gaps:
        findings.append(
            "no usable verification record covers %s/%s" % (hardware_id, surface)
        )
    coverage = float(len(pairs) - len(gaps)) / float(len(pairs))
    complete = math.isclose(coverage, 1.0, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE)
    return {
        "records": per_record,
        "surface_count": len(pairs),
        "gaps": gaps,
        "orphan_record_ids": orphans,
        "traceable_coverage": coverage,
        "disposition": "records-complete" if complete and not findings else "records-incomplete",
        "findings": findings,
    }
