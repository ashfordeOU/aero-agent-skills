"""Programming controls for a programmable device at the lowest class.

Anchor: ECSS-Q-ST-60-13C clause 6.6.4 (controls over the programming of
programmable devices where the programme works at the lowest commercial
assurance class). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Group the declared device family into one of three categories: one time
   programmable, reprogrammable non-volatile or reprogrammable volatile. The
   category, not the part number, decides which controls the operation owes.
2. Derive the control set that category carries at the lowest class, made of
   the controls every programming operation owes plus the ones specific to
   the category, and name every required control the record leaves open.
3. Refuse a record with no pattern identity, and refuse one whose readback
   does not reproduce the pattern that was meant to be loaded. At the lowest
   class the programming record is the only assurance evidence there is, so
   an unverified pattern leaves nothing behind it.
4. Compare the devices actually verified against the batch, through the
   verification floor the category carries.
5. For a reprogrammable part, compare the programming operations already
   spent against the rated endurance derated by its declared fraction, and
   count an exact landing on the budget as met.
6. Return one verdict in precedence order, with every open control named.
"""

import math

__all__ = [
    "BUDGET_TOLERANCE",
    "DEVICE_CATEGORIES",
    "FAMILY_CATEGORY",
    "COMMON_CONTROLS",
    "CATEGORY_CONTROLS",
    "VERIFICATION_FLOOR",
    "DEFAULT_ENDURANCE_DERATING",
    "PROGRAMMING_VERDICTS",
    "validate_identifier",
    "categorize_family",
    "required_controls",
    "open_controls",
    "verification_coverage",
    "cycle_budget",
    "assess_programming_record",
]

# Coverage and cycle budgets are products and quotients that can land a few
# ULPs either side of a bound they should sit exactly on. Absorb that here,
# never by moving the bound.
BUDGET_TOLERANCE = 1e-9

DEVICE_CATEGORIES = (
    "one-time-programmable",
    "reprogrammable-non-volatile",
    "reprogrammable-volatile",
)

# Declared family -> the category whose controls it owes. A family absent
# from this map is an input error, not a default.
FAMILY_CATEGORY = {
    "antifuse-fpga": "one-time-programmable",
    "fuse-prom": "one-time-programmable",
    "otp-microcontroller": "one-time-programmable",
    "otp-eprom": "one-time-programmable",
    "flash-fpga": "reprogrammable-non-volatile",
    "eeprom": "reprogrammable-non-volatile",
    "flash-memory": "reprogrammable-non-volatile",
    "flash-microcontroller": "reprogrammable-non-volatile",
    "sram-fpga": "reprogrammable-volatile",
    "sram-configuration-logic": "reprogrammable-volatile",
}

# Controls every programming operation owes whatever the device is.
COMMON_CONTROLS = (
    "esd-controlled-programming-station",
    "pattern-identity-record",
    "programming-equipment-calibration-record",
)

# Controls the category adds on top of the common set.
CATEGORY_CONTROLS = {
    "one-time-programmable": (
        "batch-functional-sample-check",
        "blank-verification",
        "post-program-readback",
    ),
    "reprogrammable-non-volatile": (
        "erase-verification",
        "post-program-readback",
        "program-cycle-count-record",
    ),
    "reprogrammable-volatile": (
        "configuration-load-verification",
        "configuration-scrub-provision",
        "power-up-load-integrity-check",
    ),
}

# Share of the batch whose programming has to be verified device by device.
# A part that cannot be reprogrammed is scrap when it is wrong, so nothing
# less than the whole batch is meaningful there.
VERIFICATION_FLOOR = {
    "one-time-programmable": 1.0,
    "reprogrammable-non-volatile": 1.0,
    "reprogrammable-volatile": 0.25,
}

# Share of the rated programming endurance a lowest-class programme may spend
# before the device is treated as used up.
DEFAULT_ENDURANCE_DERATING = 0.5

PROGRAMMING_VERDICTS = (
    "programming-record-accepted",
    "accepted-with-open-advisory-control",
    "escalate-to-parts-control-board",
    "refuse-unverified-pattern",
)


def validate_identifier(value, label):
    """Return a non-blank stripped identifier, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_non_negative_int(value, label):
    """Return a non-negative integer, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _require_fraction(value, label):
    """Return a finite real number inside the unit interval, or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        raise ValueError("%s must lie in [0, 1], got %r" % (label, value))
    return number


def _meets_floor(value, floor):
    """Return True when value reaches its floor, an exact landing counted in."""
    return value > floor or math.isclose(
        value, floor, rel_tol=0.0, abs_tol=BUDGET_TOLERANCE
    )


def _within_budget(value, budget):
    """Return True when value stays inside a budget, an exact landing counted in."""
    return value < budget or math.isclose(
        value, budget, rel_tol=0.0, abs_tol=BUDGET_TOLERANCE
    )


def categorize_family(family):
    """Return the control category a declared device family belongs to."""
    name = validate_identifier(family, "device family").lower()
    if name not in FAMILY_CATEGORY:
        raise ValueError(
            "device family %s is not in the recognised set; add it to the "
            "family map before grading a record against it" % name
        )
    return FAMILY_CATEGORY[name]


def required_controls(category):
    """Return the controls a category owes at the lowest assurance class."""
    name = validate_identifier(category, "device category")
    if name not in CATEGORY_CONTROLS:
        raise ValueError("unknown device category %s" % name)
    return tuple(sorted(set(COMMON_CONTROLS) | set(CATEGORY_CONTROLS[name])))


def open_controls(category, performed):
    """Return the required controls the performed set does not cover."""
    needed = set(required_controls(category))
    if not isinstance(performed, (list, tuple, set, frozenset)):
        raise ValueError("performed controls must be a sequence or a set")
    done = set()
    for item in performed:
        control = validate_identifier(item, "performed control")
        if control in done:
            raise ValueError("control %s is recorded twice" % control)
        done.add(control)
    return tuple(sorted(needed - done))


def verification_coverage(verified_devices, batch_size):
    """Return the share of a programmed batch verified device by device."""
    batch = _require_non_negative_int(batch_size, "batch_size")
    verified = _require_non_negative_int(verified_devices, "verified_devices")
    if batch == 0:
        raise ValueError("batch_size must be positive")
    if verified > batch:
        raise ValueError(
            "verified_devices (%d) cannot exceed batch_size (%d)" % (verified, batch)
        )
    return verified / batch


def cycle_budget(rated_cycles, cycles_used, derating=None):
    """Return the programming-endurance budget of a reprogrammable device."""
    rated = _require_non_negative_int(rated_cycles, "rated_cycles")
    used = _require_non_negative_int(cycles_used, "cycles_used")
    if rated == 0:
        raise ValueError("rated_cycles must be positive for a reprogrammable device")
    share = _require_fraction(
        DEFAULT_ENDURANCE_DERATING if derating is None else derating,
        "endurance derating",
    )
    if share <= 0.0:
        raise ValueError("endurance derating must be positive")
    usable = rated * share
    return {
        "rated_cycles": rated,
        "derating": share,
        "usable_cycles": usable,
        "cycles_used": used,
        "remaining_cycles": usable - used,
        "within_budget": _within_budget(float(used), usable),
    }


def assess_programming_record(record):
    """Run the full clause 6.6.4 lowest-class programming-control assessment.

    record keys: reference, family, controls_performed, pattern_identity,
    declared_checksum, readback_checksum, batch_size, verified_devices, and
    for a reprogrammable device rated_cycles and cycles_used. Optional keys:
    derating, advisory_controls.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in ("reference", "family", "batch_size", "verified_devices"):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    reference = validate_identifier(record["reference"], "device reference")
    category = categorize_family(record["family"])
    needed = required_controls(category)
    missing = open_controls(category, record.get("controls_performed", ()))
    coverage = verification_coverage(
        record["verified_devices"], record["batch_size"]
    )
    floor = VERIFICATION_FLOOR[category]
    coverage_met = _meets_floor(coverage, floor)

    pattern = record.get("pattern_identity")
    pattern_recorded = isinstance(pattern, str) and bool(pattern.strip())
    declared = record.get("declared_checksum")
    readback = record.get("readback_checksum")
    checksums_present = isinstance(declared, str) and isinstance(readback, str)
    checksums_agree = (
        checksums_present
        and bool(declared.strip())
        and declared.strip().lower() == readback.strip().lower()
    )

    reprogrammable = category != "one-time-programmable"
    budget = None
    if reprogrammable:
        if "rated_cycles" not in record or "cycles_used" not in record:
            raise ValueError(
                "a reprogrammable device needs rated_cycles and cycles_used"
            )
        budget = cycle_budget(
            record["rated_cycles"], record["cycles_used"], record.get("derating")
        )
    else:
        spent = _require_non_negative_int(
            record.get("cycles_used", 0), "cycles_used"
        )
        budget = {
            "rated_cycles": 1,
            "derating": 1.0,
            "usable_cycles": 1.0,
            "cycles_used": spent,
            "remaining_cycles": 1.0 - spent,
            "within_budget": _within_budget(float(spent), 1.0),
        }

    advisory = tuple(
        sorted(
            {
                validate_identifier(item, "advisory control")
                for item in record.get("advisory_controls", ())
            }
        )
    )
    advisory_open = tuple(item for item in advisory if item in missing)

    findings = []
    if not pattern_recorded:
        findings.append(
            {
                "severity": 0,
                "reference": reference,
                "detail": "no pattern identity was recorded for the operation",
            }
        )
    if not checksums_present or not checksums_agree:
        findings.append(
            {
                "severity": 0,
                "reference": reference,
                "detail": "the readback does not reproduce the declared pattern",
            }
        )
    if not reprogrammable and budget["cycles_used"] > 1:
        findings.append(
            {
                "severity": 1,
                "reference": reference,
                "detail": "a one time device shows %d programming operations"
                % budget["cycles_used"],
            }
        )
    for control in missing:
        findings.append(
            {
                "severity": 1 if control not in advisory_open else 2,
                "reference": control,
                "detail": "required control %s is open on the record" % control,
            }
        )
    if not coverage_met:
        findings.append(
            {
                "severity": 1,
                "reference": reference,
                "detail": "programming verification covers %.4f of the batch, "
                "below the %.4f floor for this category" % (coverage, floor),
            }
        )
    if not budget["within_budget"]:
        findings.append(
            {
                "severity": 1,
                "reference": reference,
                "detail": "programming operations spent exceed the derated "
                "endurance budget of %.4f" % budget["usable_cycles"],
            }
        )
    findings.sort(key=lambda item: (item["severity"], item["reference"]))

    mandatory_open = tuple(item for item in missing if item not in advisory_open)

    if not pattern_recorded or not checksums_agree:
        verdict = "refuse-unverified-pattern"
    elif (
        mandatory_open
        or not coverage_met
        or not budget["within_budget"]
        or (not reprogrammable and budget["cycles_used"] > 1)
    ):
        verdict = "escalate-to-parts-control-board"
    elif advisory_open:
        verdict = "accepted-with-open-advisory-control"
    else:
        verdict = "programming-record-accepted"

    return {
        "reference": reference,
        "category": category,
        "required_controls": needed,
        "open_controls": missing,
        "mandatory_open_controls": mandatory_open,
        "advisory_open_controls": advisory_open,
        "pattern_recorded": pattern_recorded,
        "checksums_agree": checksums_agree,
        "verification_coverage": coverage,
        "verification_floor": floor,
        "verification_met": coverage_met,
        "cycle_budget": budget,
        "findings": findings,
        "verdict": verdict,
    }
