"""Ground support equipment configuration control logic.

Anchor: ECSS-Q-ST-20C clause 5.8.2 -- configuration control of ground support
equipment: identifying each GSE configuration item, holding it against a
baseline, and controlling every change away from that baseline. Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the identification of each GSE configuration item: an item cannot
   be held under configuration control without a part number, an individual
   serial and a whole version number.
2. Validate the baseline as a set: one entry per item, no item entered twice.
3. Replay the change log against that baseline in its stated order. A change is
   applied only when it is approved, when it starts from the version the item
   is actually at, and when it steps that version by one.
4. Report every change that was refused, and why, rather than stopping at the
   first one.
5. Compare the resulting as-built configuration with the configuration the GSE
   is declared to be at, and return whether the equipment is under control.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "normalize_token",
    "validate_item",
    "validate_baseline",
    "validate_change",
    "validate_change_log",
    "identification_findings",
    "replay_changes",
    "applied_ratio",
    "declared_configuration_findings",
    "assess_gse_configuration",
]

# Ratios of small integers can land a few ULPs off an exact value; absorb the
# representation error here rather than by rounding the ratio.
RATIO_TOLERANCE = 1e-9


def normalize_token(value, label="token"):
    """Return a lowercase, hyphen-joined comparison token for an identifier."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = "-".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _whole(value, label, minimum=1):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def validate_item(item, index=0):
    """Return one validated GSE configuration item."""
    if not isinstance(item, dict):
        raise ValueError("baseline[%d] must be a mapping" % index)
    if "item_id" not in item:
        raise ValueError("baseline[%d] is missing 'item_id'" % index)
    if "version" not in item:
        raise ValueError("baseline[%d] is missing 'version'" % index)
    item_id = normalize_token(item["item_id"], "baseline[%d]['item_id']" % index)
    part_number = item.get("part_number")
    serial_number = item.get("serial_number")
    return {
        "item_id": item_id,
        "part_number": None if part_number is None else normalize_token(
            part_number, "baseline[%d]['part_number']" % index
        ),
        "serial_number": None if serial_number is None else normalize_token(
            serial_number, "baseline[%d]['serial_number']" % index
        ),
        "version": _whole(item["version"], "baseline[%d]['version']" % index),
    }


def validate_baseline(items):
    """Return the validated baseline, refusing an item entered twice."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("baseline must be a non-empty sequence of configuration items")
    seen = set()
    validated = []
    for i, item in enumerate(items):
        record = validate_item(item, i)
        if record["item_id"] in seen:
            raise ValueError("baseline holds %s twice" % record["item_id"])
        seen.add(record["item_id"])
        validated.append(record)
    return validated


def identification_findings(baseline):
    """Return the items that cannot be held under configuration control as identified."""
    findings = []
    for item in baseline:
        if item["part_number"] is None:
            findings.append("GSE item %s carries no part number" % item["item_id"])
        if item["serial_number"] is None:
            findings.append(
                "GSE item %s carries no individual serial, so it cannot be controlled as one unit"
                % item["item_id"]
            )
    return findings


def validate_change(change, index=0):
    """Return one validated GSE change record."""
    if not isinstance(change, dict):
        raise ValueError("changes[%d] must be a mapping" % index)
    for key in ("id", "item_id", "from_version", "to_version"):
        if key not in change:
            raise ValueError("changes[%d] is missing '%s'" % (index, key))
    approved = change.get("approved", False)
    if not isinstance(approved, bool):
        raise ValueError("changes[%d]['approved'] must be a boolean" % index)
    return {
        "id": normalize_token(change["id"], "changes[%d]['id']" % index),
        "item_id": normalize_token(change["item_id"], "changes[%d]['item_id']" % index),
        "from_version": _whole(change["from_version"], "changes[%d]['from_version']" % index),
        "to_version": _whole(change["to_version"], "changes[%d]['to_version']" % index),
        "approved": approved,
    }


def validate_change_log(changes):
    """Return the validated change log, refusing a duplicated change identifier."""
    if changes is None:
        changes = []
    if not isinstance(changes, (list, tuple)):
        raise ValueError("changes must be a sequence of change records")
    seen = set()
    validated = []
    for i, change in enumerate(changes):
        record = validate_change(change, i)
        if record["id"] in seen:
            raise ValueError("change %s is logged twice" % record["id"])
        seen.add(record["id"])
        validated.append(record)
    return validated


def replay_changes(baseline, changes):
    """Replay the change log against the baseline and return the as-built state."""
    current = {item["item_id"]: item["version"] for item in baseline}
    applied = []
    refused = []
    findings = []
    for change in changes:
        item_id = change["item_id"]
        if item_id not in current:
            findings.append(
                "change %s targets %s, which is not in the GSE baseline" % (change["id"], item_id)
            )
            refused.append(change["id"])
            continue
        if not change["approved"]:
            findings.append(
                "change %s against %s was never approved and was not applied"
                % (change["id"], item_id)
            )
            refused.append(change["id"])
            continue
        if change["from_version"] != current[item_id]:
            findings.append(
                "change %s starts from version %d but %s is at version %d"
                % (change["id"], change["from_version"], item_id, current[item_id])
            )
            refused.append(change["id"])
            continue
        if change["to_version"] != change["from_version"] + 1:
            findings.append(
                "change %s steps %s from version %d to %d instead of one increment"
                % (change["id"], item_id, change["from_version"], change["to_version"])
            )
            refused.append(change["id"])
            continue
        current[item_id] = change["to_version"]
        applied.append(change["id"])
    as_built = [
        {"item_id": item["item_id"], "version": current[item["item_id"]]} for item in baseline
    ]
    return {
        "as_built": as_built,
        "applied": applied,
        "refused": refused,
        "findings": findings,
    }


def applied_ratio(applied, refused):
    """Return the fraction of logged changes that actually reached the configuration."""
    if not isinstance(applied, (list, tuple)) or not isinstance(refused, (list, tuple)):
        raise ValueError("applied and refused must be sequences of change identifiers")
    total = len(applied) + len(refused)
    if total == 0:
        raise ValueError("an empty change log has no application ratio")
    return float(len(applied)) / float(total)


def declared_configuration_findings(as_built, declared):
    """Return the differences between the replayed state and the declared configuration."""
    if not isinstance(declared, (list, tuple)):
        raise ValueError("declared configuration must be a sequence of item records")
    stated = {}
    for i, item in enumerate(declared):
        if not isinstance(item, dict):
            raise ValueError("declared[%d] must be a mapping" % i)
        for key in ("item_id", "version"):
            if key not in item:
                raise ValueError("declared[%d] is missing '%s'" % (i, key))
        item_id = normalize_token(item["item_id"], "declared[%d]['item_id']" % i)
        if item_id in stated:
            raise ValueError("declared configuration holds %s twice" % item_id)
        stated[item_id] = _whole(item["version"], "declared[%d]['version']" % i)
    findings = []
    built = {item["item_id"]: item["version"] for item in as_built}
    for item_id in sorted(built):
        if item_id not in stated:
            findings.append("declared configuration does not list GSE item %s" % item_id)
        elif stated[item_id] != built[item_id]:
            findings.append(
                "GSE item %s is declared at version %d but the change log builds version %d"
                % (item_id, stated[item_id], built[item_id])
            )
    for item_id in sorted(stated):
        if item_id not in built:
            findings.append(
                "declared configuration lists %s, which is not a baselined GSE item" % item_id
            )
    return findings


def assess_gse_configuration(spec):
    """Run the full clause 5.8.2 GSE configuration control assessment.

    spec keys: baseline, optional changes, declared, required_applied_ratio.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "baseline" not in spec:
        raise ValueError("spec missing required key 'baseline'")
    baseline = validate_baseline(spec["baseline"])
    changes = validate_change_log(spec.get("changes"))
    identification = identification_findings(baseline)
    replay = replay_changes(baseline, changes)

    ratio = None
    ratio_findings = []
    required_ratio = spec.get("required_applied_ratio")
    if changes:
        ratio = applied_ratio(replay["applied"], replay["refused"])
        if required_ratio is not None:
            if not isinstance(required_ratio, (int, float)) or isinstance(required_ratio, bool):
                raise ValueError("required_applied_ratio must be a real number")
            required_ratio = float(required_ratio)
            if not math.isfinite(required_ratio) or not 0.0 <= required_ratio <= 1.0:
                raise ValueError("required_applied_ratio must lie in [0, 1]")
            if ratio < required_ratio and not math.isclose(
                ratio, required_ratio, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
            ):
                ratio_findings.append(
                    "only %.3f of the logged changes reached the configuration, below the "
                    "required %.3f" % (ratio, required_ratio)
                )

    declared_findings = []
    if "declared" in spec:
        declared_findings = declared_configuration_findings(replay["as_built"], spec["declared"])

    findings = (
        list(identification)
        + list(replay["findings"])
        + list(ratio_findings)
        + list(declared_findings)
    )
    return {
        "baseline": baseline,
        "as_built": replay["as_built"],
        "applied": replay["applied"],
        "refused": replay["refused"],
        "identification_findings": identification,
        "change_findings": replay["findings"],
        "ratio_findings": ratio_findings,
        "declared_findings": declared_findings,
        "applied_ratio": ratio,
        "findings": findings,
        "under_control": not findings,
    }
