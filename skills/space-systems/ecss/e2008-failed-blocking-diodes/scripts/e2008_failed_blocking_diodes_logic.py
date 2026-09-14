#!/usr/bin/env python3
"""The designation a blocking diode showing a listed failure mode takes.

Anchor: ECSS-E-ST-20-08C clause 12.7.2. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The preceding clause says what a blocking diode failure mode is. This one says
what a part showing one becomes: a failed blocking diode, and a failed
blocking diode is not part of what is delivered. Three things follow and each
of them is a separate decision:

    designation   one standing mode is enough, modes do not vote, and the
                  word attaches to the individual part rather than to the lot
                  it came from or the subgroup it was drawn into. A part whose
                  inspection is unfinished is neither failed nor deliverable:
                  it is undetermined, and undetermined has to survive as its
                  own third word
    evidence      a designation with no segregation record, no non-conformance
                  reference and -- for a diode already assigned to a string --
                  no withdrawal of that allocation is a word in a report while
                  the part is still on the bench
    population    the deliverable count is what is left once the failed parts
                  are removed, and the offered parts and the inspection
                  records have to reconcile in both directions before that
                  count means anything

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

RECOGNISED_FAILURE_MODES = (
    "forward-voltage-drop-drift-exceeded",
    "forward-voltage-drop-outside-absolute-limit",
    "reverse-leakage-current-drift-exceeded",
    "reverse-leakage-current-outside-absolute-limit",
    "reverse-blocking-voltage-drift-exceeded",
    "reverse-blocking-voltage-outside-absolute-limit",
    "thermal-resistance-junction-to-case-drift-exceeded",
    "blocking-diode-reverse-blocking-lost",
    "blocking-diode-forward-conduction-lost",
    "die-crack",
    "contact-metallisation-lifted",
    "solder-void-beyond-limit",
    "encapsulation-damage",
)

DESIGNATION_FAILED = "failed-blocking-diode"
DESIGNATION_DELIVERABLE = "deliverable-blocking-diode"
DESIGNATION_UNDETERMINED = "undetermined-blocking-diode"

EVIDENCE_SEGREGATION = "segregation-record"
EVIDENCE_NONCONFORMANCE = "nonconformance-reference"
EVIDENCE_STRING_WITHDRAWAL = "string-allocation-withdrawal"

LOT_DESIGNATION_ASSIGNED = "lot-designation-assigned"
LOT_DESIGNATION_INCOMPLETE = "lot-designation-incomplete"
LOT_FAILED_SHARE_EXCEEDED = "lot-failed-share-exceeded"

DEFAULT_DESIGNATION_POLICY = {
    "policy_reference": "planar-blocking-diode-delivery-control-plan-issue-a",
    "segregation_record_required": True,
    "nonconformance_reference_required": True,
    "string_allocation_withdrawal_required": True,
    "retest_clearance_admitted": False,
    "undetermined_countable_as_deliverable": False,
    "max_failed_fraction": 0.10,
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


def _require_bool(name, value):
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


def recognised_failure_modes():
    """The modes the preceding clause can raise against a blocking diode."""
    return tuple(RECOGNISED_FAILURE_MODES)


def validate_designation_policy(policy):
    """Check a declared delivery-control policy can designate anything."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_text("policy_reference", policy.get("policy_reference"))
    _require_bool(
        "segregation_record_required", policy.get("segregation_record_required")
    )
    _require_bool(
        "nonconformance_reference_required",
        policy.get("nonconformance_reference_required"),
    )
    _require_bool(
        "string_allocation_withdrawal_required",
        policy.get("string_allocation_withdrawal_required"),
    )
    _require_bool(
        "retest_clearance_admitted", policy.get("retest_clearance_admitted")
    )
    _require_bool(
        "undetermined_countable_as_deliverable",
        policy.get("undetermined_countable_as_deliverable"),
    )
    _require_fraction("max_failed_fraction", policy.get("max_failed_fraction"))
    return policy


def _read_modes(name, value):
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError("%s must be a sequence, got %r" % (name, value))
    modes = []
    for mode in value:
        mode = _require_text("%s entry" % name, mode)
        if mode not in RECOGNISED_FAILURE_MODES:
            raise ValueError("%s names an unrecognised failure mode %s" % (name, mode))
        modes.append(mode)
    return modes


def standing_modes(record, policy=DEFAULT_DESIGNATION_POLICY):
    """The modes still standing against a part once clearances are applied."""
    validate_designation_policy(policy)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    observed = set(_read_modes("failure_modes", record.get("failure_modes", ())))
    claimed = _read_modes("cleared_modes", record.get("cleared_modes", ()))

    findings = []
    cleared = set()
    for mode in claimed:
        if mode not in observed:
            raise ValueError(
                "a clearance names %s, which the inspection never raised against "
                "this part" % mode
            )
        if not policy["retest_clearance_admitted"]:
            findings.append(
                "the policy in force does not admit a retest clearance, so %s "
                "still stands" % mode
            )
            continue
        authority = record.get("clearing_authority")
        if not isinstance(authority, str) or not authority.strip():
            findings.append(
                "the clearance of %s names no clearing authority, so it is a "
                "second opinion rather than a disposition" % mode
            )
            continue
        cleared.add(mode)

    return {
        "observed_modes": sorted(observed),
        "cleared_modes": sorted(cleared),
        "standing_modes": sorted(observed - cleared),
        "findings": findings,
    }


def required_failed_evidence(record, policy=DEFAULT_DESIGNATION_POLICY):
    """The evidence a failed blocking diode still owes before it counts as handled."""
    validate_designation_policy(policy)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    missing = []
    if policy["segregation_record_required"]:
        value = record.get("segregation_record")
        if not isinstance(value, str) or not value.strip():
            missing.append(EVIDENCE_SEGREGATION)
    if policy["nonconformance_reference_required"]:
        value = record.get("nonconformance_reference")
        if not isinstance(value, str) or not value.strip():
            missing.append(EVIDENCE_NONCONFORMANCE)
    if policy["string_allocation_withdrawal_required"] and record.get(
        "string_allocation"
    ):
        _require_text("string_allocation", record.get("string_allocation"))
        if not _require_bool(
            "string_allocation_withdrawn",
            record.get("string_allocation_withdrawn", False),
        ):
            missing.append(EVIDENCE_STRING_WITHDRAWAL)
    return sorted(missing)


def designate_blocking_diode(record, policy=DEFAULT_DESIGNATION_POLICY):
    """The designation clause 12.7.2 gives one blocking diode."""
    validate_designation_policy(policy)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    part_id = _require_text("part_id", record.get("part_id"))
    complete = _require_bool(
        "inspection_complete", record.get("inspection_complete", True)
    )

    modes = standing_modes(record, policy)
    findings = list(modes["findings"])
    standing = modes["standing_modes"]
    missing_evidence = []

    if standing:
        designation = DESIGNATION_FAILED
        missing_evidence = required_failed_evidence(record, policy)
        for item in missing_evidence:
            findings.append(
                "%s is a failed blocking diode with no %s, so nothing on the "
                "bench keeps it out of the next delivery" % (part_id, item)
            )
    elif not complete:
        designation = DESIGNATION_UNDETERMINED
        findings.append(
            "%s has not finished inspection, so it is neither failed nor "
            "deliverable" % part_id
        )
    else:
        designation = DESIGNATION_DELIVERABLE

    documented = designation != DESIGNATION_FAILED or not missing_evidence
    return {
        "part_id": part_id,
        "designation": designation,
        "failed": designation == DESIGNATION_FAILED,
        "deliverable": designation == DESIGNATION_DELIVERABLE,
        "inspection_complete": complete,
        "observed_modes": modes["observed_modes"],
        "cleared_modes": modes["cleared_modes"],
        "standing_modes": standing,
        "missing_evidence": missing_evidence,
        "documented": documented,
        "findings": findings,
    }


def designate_lot(lot, policy=DEFAULT_DESIGNATION_POLICY):
    """Full clause 12.7.2 sweep over one offered blocking diode lot."""
    validate_designation_policy(policy)
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    lot_id = _require_text("lot_id", lot.get("lot_id"))

    offered = lot.get("offered_part_ids")
    if not isinstance(offered, (list, tuple)) or not offered:
        raise ValueError("offered_part_ids must be a non-empty sequence")
    offered_ids = []
    for part_id in offered:
        part_id = _require_text("offered part id", part_id)
        if part_id in offered_ids:
            raise ValueError("lot offers part %s twice" % part_id)
        offered_ids.append(part_id)

    records = lot.get("part_records", ())
    if not isinstance(records, (list, tuple)):
        raise ValueError("part_records must be a sequence, got %r" % (records,))

    findings = []
    designations = []
    seen = set()
    foreign = []
    offered_set = set(offered_ids)

    for record in records:
        designated = designate_blocking_diode(record, policy)
        part_id = designated["part_id"]
        if part_id in seen:
            raise ValueError("lot records part %s twice" % part_id)
        seen.add(part_id)
        if part_id not in offered_set:
            foreign.append(part_id)
            findings.append(
                "a record for %s rides along with lot %s, which does not offer "
                "that part, so it may describe another lot entirely"
                % (part_id, lot_id)
            )
            continue
        designations.append(designated)
        findings.extend(designated["findings"])

    unrecorded = sorted(offered_set - seen)
    for part_id in unrecorded:
        designations.append(
            {
                "part_id": part_id,
                "designation": DESIGNATION_UNDETERMINED,
                "failed": False,
                "deliverable": False,
                "inspection_complete": False,
                "observed_modes": [],
                "cleared_modes": [],
                "standing_modes": [],
                "missing_evidence": [],
                "documented": True,
                "findings": [],
            }
        )
        findings.append(
            "lot %s offers %s with no inspection record at all, so it is "
            "undetermined rather than deliverable" % (lot_id, part_id)
        )

    designations.sort(key=lambda entry: entry["part_id"])

    grouped = {
        DESIGNATION_FAILED: [],
        DESIGNATION_DELIVERABLE: [],
        DESIGNATION_UNDETERMINED: [],
    }
    for entry in designations:
        grouped[entry["designation"]].append(entry["part_id"])

    total = len(offered_ids)
    failed_ids = sorted(grouped[DESIGNATION_FAILED])
    undetermined_ids = sorted(grouped[DESIGNATION_UNDETERMINED])
    deliverable_ids = sorted(grouped[DESIGNATION_DELIVERABLE])
    if policy["undetermined_countable_as_deliverable"]:
        deliverable_ids = sorted(deliverable_ids + undetermined_ids)

    failed_fraction = len(failed_ids) / float(total)
    allowance = float(policy["max_failed_fraction"])
    share_ok = _within(failed_fraction, allowance)

    undocumented = sorted(
        entry["part_id"] for entry in designations if not entry["documented"]
    )
    if not share_ok:
        findings.append(
            "lot %s carries %d failed blocking diodes of %d offered, a share of "
            "%.4f against an allowance of %.4f"
            % (lot_id, len(failed_ids), total, failed_fraction, allowance)
        )

    settled = not undetermined_ids or policy["undetermined_countable_as_deliverable"]
    if not settled or undocumented or foreign:
        verdict = LOT_DESIGNATION_INCOMPLETE
    elif not share_ok:
        verdict = LOT_FAILED_SHARE_EXCEEDED
    else:
        verdict = LOT_DESIGNATION_ASSIGNED

    return {
        "verdict": verdict,
        "lot_id": lot_id,
        "part_designations": designations,
        "designations_by_group": {k: sorted(v) for k, v in grouped.items()},
        "failed_part_ids": failed_ids,
        "undetermined_part_ids": undetermined_ids,
        "deliverable_part_ids": deliverable_ids,
        "deliverable_count": len(deliverable_ids),
        "offered_count": total,
        "undocumented_failed_part_ids": undocumented,
        "foreign_record_part_ids": sorted(foreign),
        "unrecorded_offered_part_ids": unrecorded,
        "failed_fraction": failed_fraction,
        "allowed_failed_fraction": allowance,
        "failed_share_within_allowance": share_ok,
        "findings": findings,
    }
