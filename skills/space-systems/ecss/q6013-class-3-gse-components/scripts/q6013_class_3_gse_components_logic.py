"""Commercial components used in ground support equipment at the lowest class.

Anchor: ECSS-Q-ST-60-13C clause 6.1.5 (control of commercial parts fitted in
ground support equipment when the programme works at the lowest assurance
class). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate each declared ground part and the exposures it carries.
2. Derive the control elements the part owes from those exposures.
   Identification is owed by every part; interface isolation, calibration,
   functional verification, operator safety and spares provision are each
   pulled in by one specific exposure rather than applied across the rack.
3. Credit a declared control only where an evidence reference is cited. An
   asserted control earns nothing, and a waiver earns credit only where the
   element may be waived at this class at all and the justification is on
   record.
4. Weight the credited elements into a per-part coverage fraction.
5. Return the control tier each part earns, the governing part, ranked
   findings and one rack verdict.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "HAZARD_VOLTAGE_V",
    "LEAD_TIME_LIMIT_DAYS",
    "CONTROL_ELEMENTS",
    "CONTROL_STATES",
    "CONTROL_TIERS",
    "DATA_ROLES",
    "validate_identifier",
    "required_controls",
    "credited_controls",
    "control_coverage",
    "part_tier",
    "evaluate_gse_part",
    "assess_class3_gse_controls",
]

# Coverage is a ratio of summed weights; an exactly-met floor can land a few
# ULPs low. Absorb that here, never by moving the floor.
COVERAGE_TOLERANCE = 1e-9

# A rack supply at or above this potential owes an operator safety barrier
# whatever the assurance class of the programme.
HAZARD_VOLTAGE_V = 60.0

# Beyond this replacement lead time a bench part stops being a shelf item and
# owes a spares holding, because a dead part now costs schedule.
LEAD_TIME_LIMIT_DAYS = 30

# Control element -> the share of the control argument it carries, and whether
# the lowest assurance class allows it to be waived at all.
CONTROL_ELEMENTS = {
    "part-identification": {"weight": 0.20, "waivable": False},
    "flight-interface-isolation": {"weight": 0.25, "waivable": False},
    "operator-safety-barrier": {"weight": 0.20, "waivable": False},
    "calibration-record": {"weight": 0.15, "waivable": False},
    "functional-verification": {"weight": 0.10, "waivable": True},
    "spares-provision": {"weight": 0.10, "waivable": True},
}

CONTROL_STATES = ("evidenced", "asserted", "waived")

DATA_ROLES = ("none", "monitoring", "acceptance-evidence")

CONTROL_TIERS = ("catalogue-control", "recorded-control", "open-control")

_TIER_SEVERITY = {"open-control": 0, "recorded-control": 1, "catalogue-control": 2}


def validate_identifier(value, label):
    """Return a non-blank stripped identifier, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_bool(value, label):
    """Return a real boolean, or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _require_positive_float(value, label):
    """Return a strictly positive finite float, or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError("%s must be positive and finite, got %r" % (label, value))
    return number


def _require_non_negative_int(value, label):
    """Return a non-negative integer, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def required_controls(part):
    """Return the control elements a ground part owes, from its exposures."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    flight_connected = _require_bool(part.get("flight_connected"), "flight_connected")
    role = validate_identifier(part.get("data_role"), "data_role")
    if role not in DATA_ROLES:
        raise ValueError(
            "data_role %s is not one of %s" % (role, ", ".join(DATA_ROLES))
        )
    voltage = _require_positive_float(part.get("supply_voltage_v"), "supply_voltage_v")
    lead_days = _require_non_negative_int(
        part.get("replacement_lead_days", 0), "replacement_lead_days"
    )

    owed = {"part-identification"}
    if flight_connected:
        owed.add("flight-interface-isolation")
    if role == "acceptance-evidence":
        owed.add("calibration-record")
    if role in ("monitoring", "acceptance-evidence"):
        owed.add("functional-verification")
    if voltage >= HAZARD_VOLTAGE_V - COVERAGE_TOLERANCE:
        owed.add("operator-safety-barrier")
    if lead_days > LEAD_TIME_LIMIT_DAYS:
        owed.add("spares-provision")
    return tuple(sorted(owed))


def credited_controls(declared, required):
    """Return the credited control elements and the notes the record earns."""
    if not isinstance(declared, dict):
        raise ValueError("declared controls must be a mapping")
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required must be a non-empty sequence of element names")
    owed = []
    for name in required:
        element = validate_identifier(name, "required element")
        if element not in CONTROL_ELEMENTS:
            raise ValueError("unknown control element %s" % element)
        owed.append(element)

    notes = []
    credited = []
    for element in sorted(set(declared)):
        if element not in CONTROL_ELEMENTS:
            raise ValueError("unknown control element %s" % element)
        if element not in owed:
            notes.append("%s declared but no exposure triggers it" % element)

    for element in sorted(set(owed)):
        entry = declared.get(element)
        if entry is None:
            notes.append("%s owed but not declared" % element)
            continue
        if not isinstance(entry, dict):
            raise ValueError("control entry for %s must be a mapping" % element)
        state = validate_identifier(entry.get("state"), "state of %s" % element)
        if state not in CONTROL_STATES:
            raise ValueError(
                "state %s of %s is not one of %s"
                % (state, element, ", ".join(CONTROL_STATES))
            )
        if state == "evidenced":
            reference = entry.get("evidence")
            if not isinstance(reference, str) or not reference.strip():
                raise ValueError(
                    "%s is declared evidenced without an evidence reference" % element
                )
            credited.append(element)
        elif state == "asserted":
            notes.append("%s asserted without an evidence reference" % element)
        else:
            if not CONTROL_ELEMENTS[element]["waivable"]:
                notes.append("%s may not be waived at this class" % element)
                continue
            justification = entry.get("justification")
            if not isinstance(justification, str) or not justification.strip():
                notes.append("%s waived without a recorded justification" % element)
                continue
            notes.append("%s waived on a recorded justification" % element)
            credited.append(element)
    return tuple(sorted(credited)), tuple(notes)


def control_coverage(credited, required):
    """Return the weighted share of the owed control set that is credited."""
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required must be a non-empty sequence of element names")
    if not isinstance(credited, (list, tuple)):
        raise ValueError("credited must be a sequence of element names")
    owed = set()
    for name in required:
        element = validate_identifier(name, "required element")
        if element not in CONTROL_ELEMENTS:
            raise ValueError("unknown control element %s" % element)
        owed.add(element)
    earned = set()
    for name in credited:
        element = validate_identifier(name, "credited element")
        if element not in owed:
            raise ValueError("%s is credited but was never owed" % element)
        earned.add(element)
    denominator = math.fsum(CONTROL_ELEMENTS[name]["weight"] for name in sorted(owed))
    numerator = math.fsum(CONTROL_ELEMENTS[name]["weight"] for name in sorted(earned))
    return numerator / denominator


def part_tier(required, credited):
    """Return the control tier a ground part earns from what it discharged."""
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required must be a non-empty sequence of element names")
    if not isinstance(credited, (list, tuple)):
        raise ValueError("credited must be a sequence of element names")
    owed = set(validate_identifier(name, "required element") for name in required)
    earned = set(validate_identifier(name, "credited element") for name in credited)
    for element in owed | earned:
        if element not in CONTROL_ELEMENTS:
            raise ValueError("unknown control element %s" % element)
    if earned - owed:
        raise ValueError("credited elements that were never owed: %s" % ", ".join(sorted(earned - owed)))
    if owed - earned:
        return "open-control"
    if owed == {"part-identification"}:
        return "catalogue-control"
    return "recorded-control"


def evaluate_gse_part(item):
    """Return the control record of one ground support equipment part.

    item keys: part_id, flight_connected, data_role, supply_voltage_v,
    optional replacement_lead_days (default 0), optional controls mapping,
    optional quantity (default 1).
    """
    if not isinstance(item, dict):
        raise ValueError("each part item must be a mapping")
    part_id = validate_identifier(item.get("part_id"), "part_id")
    quantity = item.get("quantity", 1)
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("quantity of %s must be a positive integer" % part_id)
    owed = required_controls(item)
    declared = item.get("controls", {})
    credited, notes = credited_controls(declared, owed)
    coverage = control_coverage(credited, owed)
    missing = tuple(sorted(set(owed) - set(credited)))
    return {
        "part_id": part_id,
        "quantity": quantity,
        "required_controls": owed,
        "credited_controls": credited,
        "missing_controls": missing,
        "coverage": coverage,
        "tier": part_tier(owed, credited),
        "notes": notes,
    }


def assess_class3_gse_controls(spec):
    """Run the full clause 6.1.5 ground support equipment control assessment.

    spec keys: parts (non-empty sequence of part items), optional floor
    (default 0.9).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "parts" not in spec:
        raise ValueError("spec missing required key 'parts'")
    parts = spec["parts"]
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("spec['parts'] must be a non-empty sequence")
    floor = spec.get("floor", 0.9)
    if isinstance(floor, bool) or not isinstance(floor, (int, float)):
        raise ValueError("floor must be a real number")
    floor = float(floor)
    if not math.isfinite(floor) or floor < 0.0 or floor > 1.0:
        raise ValueError("floor must lie in [0, 1], got %r" % (spec.get("floor"),))

    records = [evaluate_gse_part(item) for item in parts]
    seen = set()
    for record in records:
        if record["part_id"] in seen:
            raise ValueError("part_id %s is declared twice" % record["part_id"])
        seen.add(record["part_id"])

    total_quantity = sum(record["quantity"] for record in records)
    rack_coverage = (
        math.fsum(record["coverage"] * record["quantity"] for record in records)
        / total_quantity
    )
    counts = {tier: 0 for tier in CONTROL_TIERS}
    for record in records:
        counts[record["tier"]] += 1

    governing = sorted(records, key=lambda r: (r["coverage"], r["part_id"]))[0]

    findings = []
    for record in records:
        if record["tier"] == "open-control":
            findings.append(
                {
                    "severity": 0,
                    "part_id": record["part_id"],
                    "detail": "%s has not discharged %s"
                    % (record["part_id"], ", ".join(record["missing_controls"])),
                }
            )
        elif record["notes"]:
            findings.append(
                {
                    "severity": 1,
                    "part_id": record["part_id"],
                    "detail": "%s: %s" % (record["part_id"], "; ".join(record["notes"])),
                }
            )
    findings.sort(key=lambda item: (item["severity"], item["part_id"]))

    meets_floor = rack_coverage > floor or math.isclose(
        rack_coverage, floor, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )
    compliant = counts["open-control"] == 0 and meets_floor
    return {
        "records": records,
        "rack_coverage": rack_coverage,
        "floor": floor,
        "meets_floor": meets_floor,
        "tier_counts": counts,
        "governing_part": governing,
        "findings": findings,
        "compliant": compliant,
        "verdict": "accept" if compliant else "escalate",
        "tier_severity": dict(_TIER_SEVERITY),
    }
