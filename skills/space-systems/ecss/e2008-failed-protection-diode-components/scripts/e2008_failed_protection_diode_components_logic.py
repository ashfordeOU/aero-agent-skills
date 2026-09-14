#!/usr/bin/env python3
"""The designation a protection diode takes once it shows a listed mode.

Anchor: ECSS-E-ST-20-08C clause 9.7.2. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The preceding clause says what counts as a failure mode for a protection
diode. This clause says what a part showing one becomes: a failed component,
and a failed component is not part of what is delivered. The rule is
deliberately blunt, and four properties of it are where implementations go
wrong:

    one is enough     a part showing a single listed mode takes the failed
                      designation; modes do not vote and severity does not
                      dilute it
    it is per part    the designation attaches to the individual diode, not
                      to the procurement lot it came from and not to the
                      subgroup it was drawn into
    absence is not    a part whose inspection is unfinished has no
    a pass            designation yet; it is undetermined, which is a
                      different word from deliverable and must stay one
    words need        a failed component needs a segregation record and a
    evidence          non-conformance reference, or nothing on the bench
                      keeps it out of the next shipment

A retest does not quietly restore a part either. A clearance stands only
where the policy in force admits it and a clearing authority is named, and
clearing a mode the inspection never raised is a data defect rather than good
news. The deliverable count is then derived, never carried over: it is what
is left once the failed parts are removed.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

RECOGNISED_FAILURE_MODES = (
    "diode-body-crack",
    "contact-metallisation-lifted",
    "solder-void-beyond-limit",
    "encapsulation-damage",
    "terminal-discolouration",
    "adhering-contamination",
    "diode-blocking-function-lost",
    "forward-voltage-drop-drift-exceeded",
    "reverse-leakage-current-drift-exceeded",
    "reverse-breakdown-voltage-drift-exceeded",
    "junction-thermal-resistance-drift-exceeded",
    "forward-voltage-drop-outside-absolute-limit",
    "reverse-leakage-current-outside-absolute-limit",
    "reverse-breakdown-voltage-outside-absolute-limit",
)

DESIGNATION_FAILED = "failed-protection-diode"
DESIGNATION_DELIVERABLE = "deliverable-protection-diode"
DESIGNATION_UNDETERMINED = "designation-undetermined"

POPULATION_DESIGNATION_ASSIGNED = "population-designation-assigned"
POPULATION_DESIGNATION_INCOMPLETE = "population-designation-incomplete"

REQUIRED_FAILED_COMPONENT_EVIDENCE = (
    "segregation_record",
    "nonconformance_reference",
)

DEFAULT_DESIGNATION_POLICY = {
    "require_segregation_record": True,
    "require_nonconformance_reference": True,
    "admit_retest_clearance": False,
    "count_undetermined_as_deliverable": False,
    "max_failed_fraction": 0.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _within(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return value


def _require_mode_set(name, value):
    if value is None:
        return set()
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError(
            "%s must be a sequence of failure modes, got %r" % (name, value)
        )
    read = set()
    for item in value:
        mode = _require_text("%s entry" % name, item)
        if mode not in RECOGNISED_FAILURE_MODES:
            raise ValueError("%s names an unrecognised failure mode %s" % (name, mode))
        read.add(mode)
    return read


def _require_id_set(name, value):
    if not isinstance(value, (list, tuple, set, frozenset)) or not value:
        raise ValueError("%s must be a non-empty sequence of identifiers" % name)
    read = set()
    for item in value:
        read.add(_require_text("%s entry" % name, item))
    return read


def recognised_failure_modes():
    """The modes the preceding criteria can raise against a diode."""
    return tuple(RECOGNISED_FAILURE_MODES)


def required_failed_component_evidence():
    """What a failed component has to carry so it stays findable."""
    return tuple(REQUIRED_FAILED_COMPONENT_EVIDENCE)


def validate_designation_policy(policy):
    """Check a designation policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_flag(
        "require_segregation_record", policy.get("require_segregation_record")
    )
    _require_flag(
        "require_nonconformance_reference",
        policy.get("require_nonconformance_reference"),
    )
    _require_flag("admit_retest_clearance", policy.get("admit_retest_clearance"))
    _require_flag(
        "count_undetermined_as_deliverable",
        policy.get("count_undetermined_as_deliverable"),
    )
    _require_fraction("max_failed_fraction", policy.get("max_failed_fraction"))
    return policy


def standing_failure_modes(part, policy=DEFAULT_DESIGNATION_POLICY):
    """The modes still standing against a part once clearance is applied."""
    validate_designation_policy(policy)
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    observed = _require_mode_set("observed_modes", part.get("observed_modes"))
    cleared = _require_mode_set("retest_cleared_modes", part.get("retest_cleared_modes"))
    unknown = cleared - observed
    if unknown:
        raise ValueError(
            "retest clears %s, which was never observed on the part"
            % ", ".join(sorted(unknown))
        )
    notes = []
    applied = set()
    if cleared and not policy["admit_retest_clearance"]:
        notes.append(
            "retest clearance offered for %s but the policy in force does not "
            "admit it" % ", ".join(sorted(cleared))
        )
    elif cleared:
        authority = part.get("clearing_authority")
        if not isinstance(authority, str) or not authority.strip():
            notes.append(
                "retest clearance offered for %s names no clearing authority, "
                "so it does not stand" % ", ".join(sorted(cleared))
            )
        else:
            applied = set(cleared)
            notes.append(
                "retest clearance for %s stands under %s"
                % (", ".join(sorted(cleared)), authority.strip())
            )
    standing = observed - applied
    return {
        "observed_modes": sorted(observed),
        "cleared_modes": sorted(applied),
        "standing_modes": sorted(standing),
        "notes": notes,
    }


def missing_failed_component_evidence(part, policy=DEFAULT_DESIGNATION_POLICY):
    """Which required evidence a failed component does not carry."""
    validate_designation_policy(policy)
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    demanded = []
    if policy["require_segregation_record"]:
        demanded.append("segregation_record")
    if policy["require_nonconformance_reference"]:
        demanded.append("nonconformance_reference")
    missing = []
    for field in demanded:
        value = part.get(field)
        if not isinstance(value, str) or not value.strip():
            missing.append(field)
    return sorted(missing)


def designate_part(part, policy=DEFAULT_DESIGNATION_POLICY):
    """The designation one offered protection diode takes."""
    validate_designation_policy(policy)
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    part_id = _require_text("part_id", part.get("part_id"))
    inspection_complete = part.get("inspection_complete")
    if inspection_complete is None:
        inspection_complete = True
    _require_flag("inspection_complete", inspection_complete)

    modes = standing_failure_modes(part, policy)
    findings = list(modes["notes"])
    standing = modes["standing_modes"]
    missing_evidence = []

    if standing:
        designation = DESIGNATION_FAILED
        findings.append(
            "%s shows %s, so it is a failed component and not deliverable"
            % (part_id, ", ".join(standing))
        )
        missing_evidence = missing_failed_component_evidence(part, policy)
        for field in missing_evidence:
            findings.append(
                "%s is a failed component carrying no %s, so nothing on the "
                "bench keeps it out of the next shipment" % (part_id, field)
            )
    elif not inspection_complete:
        designation = DESIGNATION_UNDETERMINED
        findings.append(
            "%s has not finished inspection, so it is undetermined rather than "
            "deliverable" % part_id
        )
    else:
        designation = DESIGNATION_DELIVERABLE

    documented = designation != DESIGNATION_FAILED or not missing_evidence
    settled = designation != DESIGNATION_UNDETERMINED
    return {
        "part_id": part_id,
        "designation": designation,
        "failed": designation == DESIGNATION_FAILED,
        "deliverable": designation == DESIGNATION_DELIVERABLE,
        "settled": settled,
        "documented": documented,
        "standing_modes": standing,
        "cleared_modes": modes["cleared_modes"],
        "observed_modes": modes["observed_modes"],
        "missing_evidence": missing_evidence,
        "findings": findings,
    }


def designate_lot(lot, policy=DEFAULT_DESIGNATION_POLICY):
    """Full clause 9.7.2 sweep over one offered protection diode lot."""
    validate_designation_policy(policy)
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    lot_id = _require_text("lot_id", lot.get("lot_id"))
    offered = _require_id_set("offered_part_ids", lot.get("offered_part_ids"))

    records = lot.get("part_records")
    if not isinstance(records, (list, tuple)):
        raise ValueError("part_records must be a sequence of mappings")

    seen = set()
    designations = []
    foreign = []
    findings = []
    for record in records:
        result = designate_part(record, policy)
        part_id = result["part_id"]
        if part_id in seen:
            raise ValueError("lot declares part %s twice" % part_id)
        seen.add(part_id)
        if part_id not in offered:
            foreign.append(part_id)
            findings.append(
                "record for %s describes a part lot %s does not offer, which is "
                "reported rather than absorbed" % (part_id, lot_id)
            )
            continue
        designations.append(result)

    unrecorded = sorted(offered - seen)
    for part_id in unrecorded:
        findings.append(
            "%s is offered by lot %s with no record at all, so it is "
            "undetermined" % (part_id, lot_id)
        )
        designations.append(
            {
                "part_id": part_id,
                "designation": DESIGNATION_UNDETERMINED,
                "failed": False,
                "deliverable": False,
                "settled": False,
                "documented": True,
                "standing_modes": [],
                "cleared_modes": [],
                "observed_modes": [],
                "missing_evidence": [],
                "findings": [],
            }
        )

    designations.sort(key=lambda entry: entry["part_id"])
    for entry in designations:
        findings.extend(entry["findings"])

    failed = [e["part_id"] for e in designations if e["designation"] == DESIGNATION_FAILED]
    undetermined = [
        e["part_id"] for e in designations if e["designation"] == DESIGNATION_UNDETERMINED
    ]
    deliverable = [
        e["part_id"] for e in designations if e["designation"] == DESIGNATION_DELIVERABLE
    ]
    if policy["count_undetermined_as_deliverable"]:
        deliverable = sorted(set(deliverable) | set(undetermined))

    total = len(offered)
    failed_fraction = len(failed) / float(total)
    allowance = float(policy["max_failed_fraction"])
    share_ok = _within(failed_fraction, allowance)
    undocumented = sorted(e["part_id"] for e in designations if not e["documented"])

    if not share_ok:
        findings.append(
            "lot %s carries %d failed components of %d offered, a share of %.4f "
            "against an allowance of %.4f"
            % (lot_id, len(failed), total, failed_fraction, allowance)
        )

    complete = not undetermined and not undocumented and not foreign
    verdict = (
        POPULATION_DESIGNATION_ASSIGNED if complete else POPULATION_DESIGNATION_INCOMPLETE
    )
    return {
        "verdict": verdict,
        "lot_id": lot_id,
        "part_designations": designations,
        "failed_part_ids": sorted(failed),
        "undetermined_part_ids": sorted(undetermined),
        "deliverable_part_ids": sorted(deliverable),
        "deliverable_count": len(deliverable),
        "offered_count": total,
        "failed_fraction": failed_fraction,
        "allowed_failed_fraction": allowance,
        "failed_share_within_allowance": share_ok,
        "foreign_record_ids": sorted(foreign),
        "unrecorded_part_ids": unrecorded,
        "undocumented_failed_ids": undocumented,
        "findings": findings,
    }
