#!/usr/bin/env python3
"""Configuration control of a test facility carrying a test campaign.

Anchor: ECSS-Q-ST-20-07 clause 5.6.2, the requirement that a test
facility's configuration is identified and that changes to it are
controlled. The procedure below is a paraphrase into implementable
steps; no standard text is reproduced.

Four things follow from what the clause is for.

A facility is a configuration, not a room. Chambers, shakers, fluid
lines, fixed instrumentation, control software and the fixtures holding
the article are each configuration items, and a facility with no item
list gives a change nothing to be controlled against.

Approved and applied are different flags. A change approved and not yet
applied is work standing in front of the campaign. A change applied and
not approved is the control failure the clause exists to catch, and it
outranks every finding downstream of it.

The as-run record is the evidence. Replaying the approved and applied
changes forward from the baseline version gives the configuration the
records say the facility should be in; an item the replay does not
reach has drifted, in whichever direction.

A chain that breaks part way is not a shorter chain. An approved and
applied record whose from-version nothing produces means the record set
disagrees with itself, and quietly reading only the records that happen
to link would hide precisely that.

The policy numbers below are declared test-centre values, not physical
constants: a test centre substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FACILITY_NOT_BASELINED = "test-facility-not-baselined"
UNAPPROVED_CHANGE_APPLIED = "test-facility-unapproved-change-applied"
CONFIGURATION_DRIFT = "test-facility-configuration-drift"
IDENTIFICATION_INCOMPLETE = "test-facility-identification-incomplete"
CHANGES_PENDING_APPROVAL = "test-facility-changes-pending-approval"
CONFIGURATION_UNDER_CONTROL = "test-facility-configuration-under-control"

DEFAULT_CONFIG_POLICY = {
    "min_identification_coverage": 1.0,
    "max_pending_changes": 0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    label = value.strip()
    if not label:
        raise ValueError("%s must not be blank" % name)
    return label


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_config_policy(policy):
    """Check the policy the facility configuration is graded against."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction(
        "min_identification_coverage", policy.get("min_identification_coverage")
    )
    _require_count("max_pending_changes", policy.get("max_pending_changes"))
    return policy


def validate_configuration_item(item):
    """Read one facility configuration item off the baseline."""
    if not isinstance(item, dict):
        raise ValueError("configuration item must be a mapping, got %r" % (item,))
    identification = item.get("identification", "")
    if identification is None:
        identification = ""
    if not isinstance(identification, str):
        raise ValueError(
            "identification must be a string or absent, got %r" % (identification,)
        )
    return {
        "item_id": _require_label("item_id", item.get("item_id")),
        "version": _require_count("version", item.get("version")),
        "identification": identification.strip(),
    }


def validate_baseline(items):
    """Read the whole baseline, refusing the same item twice."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("baseline must be a sequence of configuration items")
    checked = []
    seen = set()
    for item in items:
        record = validate_configuration_item(item)
        if record["item_id"] in seen:
            raise ValueError("configuration item %r appears twice" % record["item_id"])
        seen.add(record["item_id"])
        checked.append(record)
    if not checked:
        raise ValueError("the baseline declares no configuration items at all")
    return tuple(checked)


def identification_coverage(items):
    """Share of baseline items carrying a non-blank identification."""
    checked = validate_baseline(items)
    identified = sum(1 for record in checked if record["identification"])
    return identified / float(len(checked))


def unidentified_items(items):
    """Baseline items a change record could not point at."""
    return tuple(
        record["item_id"]
        for record in validate_baseline(items)
        if not record["identification"]
    )


def validate_change_record(change):
    """Read one change record: what it moves, from where, to where."""
    if not isinstance(change, dict):
        raise ValueError("change must be a mapping, got %r" % (change,))
    from_version = _require_count("from_version", change.get("from_version"))
    to_version = _require_count("to_version", change.get("to_version"))
    if to_version <= from_version:
        raise ValueError(
            "change %r does not advance the version it names: %d to %d"
            % (change.get("change_id"), from_version, to_version)
        )
    return {
        "change_id": _require_label("change_id", change.get("change_id")),
        "item_id": _require_label("item_id", change.get("item_id")),
        "from_version": from_version,
        "to_version": to_version,
        "approved": _require_flag("approved", change.get("approved")),
        "applied": _require_flag("applied", change.get("applied")),
    }


def validate_changes(changes):
    """Read every change record, refusing the same identifier twice."""
    if not isinstance(changes, (list, tuple)):
        raise ValueError("changes must be a sequence of change records")
    checked = []
    seen = set()
    for change in changes:
        record = validate_change_record(change)
        if record["change_id"] in seen:
            raise ValueError("change %r appears twice" % record["change_id"])
        seen.add(record["change_id"])
        checked.append(record)
    return tuple(checked)


def unapproved_applied_changes(changes):
    """Change records applied to the facility without an approval."""
    return tuple(
        record["change_id"]
        for record in validate_changes(changes)
        if record["applied"] and not record["approved"]
    )


def pending_changes(changes):
    """Change records approved or raised but not yet applied."""
    return tuple(
        record["change_id"]
        for record in validate_changes(changes)
        if not record["applied"]
    )


def replay_item_version(baseline_version, changes):
    """Walk the approved and applied changes forward from the baseline."""
    start = _require_count("baseline_version", baseline_version)
    effective = [
        record
        for record in validate_changes(changes)
        if record["approved"] and record["applied"]
    ]
    current = start
    remaining = list(effective)
    while remaining:
        step = None
        for record in remaining:
            if record["from_version"] == current:
                step = record
                break
        if step is None:
            broken = sorted(record["change_id"] for record in remaining)
            raise ValueError(
                "the change chain breaks at version %d; %s do not link"
                % (current, ", ".join(broken))
            )
        current = step["to_version"]
        remaining.remove(step)
    return current


def expected_configuration(baseline, changes):
    """Version each baseline item should be at, per the change records."""
    checked = validate_baseline(baseline)
    records = validate_changes(changes)
    expected = {}
    for item in checked:
        for_item = [r for r in records if r["item_id"] == item["item_id"]]
        expected[item["item_id"]] = replay_item_version(item["version"], for_item)
    orphans = sorted(
        {r["item_id"] for r in records} - {item["item_id"] for item in checked}
    )
    if orphans:
        raise ValueError(
            "change records name items the baseline never declared: %s"
            % ", ".join(orphans)
        )
    return expected


def validate_as_run(as_run):
    """Read the as-run configuration recorded at the facility."""
    if not isinstance(as_run, dict):
        raise ValueError("as_run must be a mapping of item to version")
    read_back = {}
    for item_id, version in as_run.items():
        name = _require_label("as_run item_id", item_id)
        if name in read_back:
            raise ValueError("as-run item %r appears twice" % name)
        read_back[name] = _require_count("as_run version", version)
    return read_back


def configuration_drift(baseline, changes, as_run):
    """Items whose as-run version the approved change chain never reaches."""
    expected = expected_configuration(baseline, changes)
    recorded = validate_as_run(as_run)
    undeclared = sorted(set(recorded) - set(expected))
    if undeclared:
        raise ValueError(
            "the as-run record carries items the baseline never declared: %s"
            % ", ".join(undeclared)
        )
    missing = sorted(set(expected) - set(recorded))
    if missing:
        raise ValueError(
            "the as-run record says nothing about %s" % ", ".join(missing)
        )
    drift = []
    for item_id in sorted(expected):
        if recorded[item_id] != expected[item_id]:
            drift.append(
                {
                    "item_id": item_id,
                    "expected_version": expected[item_id],
                    "as_run_version": recorded[item_id],
                }
            )
    return tuple(drift)


def assess_test_facility_configuration(case):
    """Grade a facility's configuration control and name what it obliges."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    policy = validate_config_policy(case.get("policy") or DEFAULT_CONFIG_POLICY)

    findings = []
    advisories = []
    result = {
        "items_baselined": 0,
        "identification_coverage": None,
        "unidentified_items": (),
        "unapproved_applied": (),
        "pending_changes": (),
        "drift": (),
        "verdict": None,
        "findings": findings,
        "advisories": advisories,
    }

    facility = case.get("facility")
    if facility is None:
        findings.append(
            "no facility record was supplied, so there is no configuration to "
            "control"
        )
        result["verdict"] = FACILITY_NOT_BASELINED
        return result
    if not isinstance(facility, dict):
        raise ValueError("facility must be a mapping, got %r" % (facility,))

    baseline = facility.get("baseline")
    if not baseline:
        findings.append(
            "the facility carries no configuration baseline, so no change to "
            "it can be controlled against anything"
        )
        result["verdict"] = FACILITY_NOT_BASELINED
        return result

    checked = validate_baseline(baseline)
    changes = validate_changes(facility.get("changes", ()))
    result["items_baselined"] = len(checked)
    result["identification_coverage"] = identification_coverage(checked)
    result["unidentified_items"] = unidentified_items(checked)
    result["pending_changes"] = pending_changes(changes)

    unapproved = unapproved_applied_changes(changes)
    result["unapproved_applied"] = unapproved
    if unapproved:
        findings.append(
            "change record(s) %s were applied to the facility without an "
            "approval, which is a control failure rather than a drift"
            % ", ".join(unapproved)
        )
        result["verdict"] = UNAPPROVED_CHANGE_APPLIED
        return result

    as_run = facility.get("as_run")
    if as_run is None:
        raise ValueError("the facility declares no as-run configuration to compare")
    drift = configuration_drift(checked, changes, as_run)
    result["drift"] = drift
    if drift:
        findings.append(
            "%d item(s) sit at a version the approved change chain does not "
            "reach: %s"
            % (
                len(drift),
                ", ".join(
                    "%s at %d against %d"
                    % (
                        entry["item_id"],
                        entry["as_run_version"],
                        entry["expected_version"],
                    )
                    for entry in drift
                ),
            )
        )
        result["verdict"] = CONFIGURATION_DRIFT
        return result

    if not _at_least(
        result["identification_coverage"],
        float(policy["min_identification_coverage"]),
    ):
        findings.append(
            "%d of %d configuration item(s) carry no identification, so a "
            "change record has nothing to point at: %s"
            % (
                len(result["unidentified_items"]),
                len(checked),
                ", ".join(result["unidentified_items"]),
            )
        )
        result["verdict"] = IDENTIFICATION_INCOMPLETE
        return result

    if len(result["pending_changes"]) > int(policy["max_pending_changes"]):
        advisories.append(
            "%d change(s) stand pending application against the %d allowed "
            "during a campaign: %s"
            % (
                len(result["pending_changes"]),
                int(policy["max_pending_changes"]),
                ", ".join(result["pending_changes"]),
            )
        )
        result["verdict"] = CHANGES_PENDING_APPROVAL
        return result

    result["verdict"] = CONFIGURATION_UNDER_CONTROL
    return result
