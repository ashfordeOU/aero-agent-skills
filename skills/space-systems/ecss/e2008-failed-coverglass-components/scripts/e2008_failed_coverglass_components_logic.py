#!/usr/bin/env python3
"""The status a coverglass takes once it shows a listed failure mode.

Anchor: ECSS-E-ST-20-08C clause 8.8.2. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The preceding criteria say what counts as a failure mode. This clause says
what happens to a piece that shows one: it is a failed component, and a
failed component is not part of what gets delivered. The rule is deliberately
blunt, and three properties of it are where implementations go wrong:

    one is enough    a piece showing a single listed mode takes the failed
                     status; modes do not vote and severity does not dilute
    it is per piece  the status attaches to the individual coverglass, not to
                     the batch it came out of and not to its sample group
    absence is not   a piece whose inspection is unfinished has no status
    a pass           yet; it is undetermined, which is a different word from
                     deliverable and must stay a different word

A failed component also has to be findable afterwards. Status without a
segregation record and a non-conformance reference is a word in a report and
nothing on the bench, so the piece can quietly walk back into the deliverable
population.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

RECOGNISED_FAILURE_MODES = (
    "coverglass-crack",
    "coating-delamination",
    "coating-blistering",
    "visible-discolouration",
    "chip-beyond-limit",
    "adhering-contamination",
    "coating-conduction-lost",
    "solar-transmittance-degradation-exceeded",
    "surface-conductivity-degradation-exceeded",
    "solar-absorptance-degradation-exceeded",
)

STATUS_FAILED_COMPONENT = "failed-component"
STATUS_DELIVERABLE_COMPONENT = "deliverable-component"
STATUS_UNDETERMINED = "status-undetermined"

POPULATION_STATUS_ASSIGNED = "population-status-assigned"
POPULATION_STATUS_INCOMPLETE = "population-status-incomplete"

REQUIRED_FAILED_COMPONENT_EVIDENCE = (
    "segregation_record",
    "nonconformance_reference",
)

DEFAULT_STATUS_POLICY = {
    "require_segregation_record": True,
    "require_nonconformance_reference": True,
    "admit_retest_clearance": False,
    "count_undetermined_as_deliverable": False,
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


def _require_mode_set(name, value):
    if value is None:
        return set()
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError("%s must be a sequence of failure modes, got %r" % (name, value))
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
    """The modes the preceding criteria can raise against a coverglass."""
    return tuple(RECOGNISED_FAILURE_MODES)


def required_failed_component_evidence():
    """What a failed component has to carry so it stays findable."""
    return tuple(REQUIRED_FAILED_COMPONENT_EVIDENCE)


def validate_status_policy(policy):
    """Check a status policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_flag("require_segregation_record", policy.get("require_segregation_record"))
    _require_flag(
        "require_nonconformance_reference",
        policy.get("require_nonconformance_reference"),
    )
    _require_flag("admit_retest_clearance", policy.get("admit_retest_clearance"))
    _require_flag(
        "count_undetermined_as_deliverable",
        policy.get("count_undetermined_as_deliverable"),
    )
    return policy


def standing_failure_modes(piece, policy=DEFAULT_STATUS_POLICY):
    """The modes still standing against a piece once clearance is applied."""
    validate_status_policy(policy)
    if not isinstance(piece, dict):
        raise ValueError("piece must be a mapping, got %r" % (piece,))
    observed = _require_mode_set("observed_modes", piece.get("observed_modes"))
    cleared = _require_mode_set("retest_cleared_modes", piece.get("retest_cleared_modes"))
    unknown = cleared - observed
    if unknown:
        raise ValueError(
            "retest clears %s, which was never observed on the piece"
            % ", ".join(sorted(unknown))
        )
    notes = []
    if cleared and not policy["admit_retest_clearance"]:
        notes.append(
            "retest clearance of %s is not admitted by the policy in force"
            % ", ".join(sorted(cleared))
        )
        cleared = set()
    elif cleared:
        authority = piece.get("clearance_authority")
        if not isinstance(authority, str) or not authority.strip():
            notes.append(
                "retest clearance of %s names no clearing authority, so it does "
                "not stand" % ", ".join(sorted(cleared))
            )
            cleared = set()
    return {
        "observed_modes": sorted(observed),
        "cleared_modes": sorted(cleared),
        "standing_modes": sorted(observed - cleared),
        "notes": notes,
    }


def failed_component_evidence(piece, policy=DEFAULT_STATUS_POLICY):
    """Which of the records a failed component owes are actually present."""
    validate_status_policy(policy)
    if not isinstance(piece, dict):
        raise ValueError("piece must be a mapping, got %r" % (piece,))
    missing = []
    if policy["require_segregation_record"]:
        value = piece.get("segregation_record")
        if not isinstance(value, str) or not value.strip():
            missing.append("segregation_record")
    if policy["require_nonconformance_reference"]:
        value = piece.get("nonconformance_reference")
        if not isinstance(value, str) or not value.strip():
            missing.append("nonconformance_reference")
    return sorted(missing)


def component_status(piece, policy=DEFAULT_STATUS_POLICY):
    """The status one coverglass takes under clause 8.8.2."""
    validate_status_policy(policy)
    if not isinstance(piece, dict):
        raise ValueError("piece must be a mapping, got %r" % (piece,))
    piece_id = _require_text("piece_id", piece.get("piece_id"))
    inspection_complete = _require_flag(
        "inspection_complete", piece.get("inspection_complete")
    )

    modes = standing_failure_modes(piece, policy)
    findings = list(
        "%s: %s" % (piece_id, note) for note in modes["notes"]
    )
    standing = modes["standing_modes"]
    missing_evidence = []

    if standing:
        status = STATUS_FAILED_COMPONENT
        findings.append(
            "%s shows %s, so it is a failed component and leaves the deliverable "
            "population" % (piece_id, ", ".join(standing))
        )
        missing_evidence = failed_component_evidence(piece, policy)
        for field in missing_evidence:
            findings.append(
                "failed component %s carries no %s, so nothing on the bench "
                "keeps it out of the delivery" % (piece_id, field)
            )
    elif not inspection_complete:
        status = STATUS_UNDETERMINED
        findings.append(
            "%s has not finished inspection, so it has no status yet and is not "
            "deliverable by default" % piece_id
        )
    else:
        status = STATUS_DELIVERABLE_COMPONENT
        if modes["cleared_modes"]:
            findings.append(
                "%s carried %s, cleared on retest by %s"
                % (
                    piece_id,
                    ", ".join(modes["cleared_modes"]),
                    piece.get("clearance_authority", "an unnamed authority"),
                )
            )

    return {
        "piece_id": piece_id,
        "status": status,
        "failed": status == STATUS_FAILED_COMPONENT,
        "deliverable": status == STATUS_DELIVERABLE_COMPONENT,
        "observed_modes": modes["observed_modes"],
        "cleared_modes": modes["cleared_modes"],
        "standing_modes": standing,
        "missing_evidence": missing_evidence,
        "status_complete": bool(status != STATUS_UNDETERMINED and not missing_evidence),
        "findings": findings,
    }


def assess_component_population(population, policy=DEFAULT_STATUS_POLICY):
    """Full clause 8.8.2 sweep: status every offered coverglass, then count."""
    validate_status_policy(policy)
    if not isinstance(population, dict):
        raise ValueError("population must be a mapping, got %r" % (population,))
    batch_id = _require_text("batch_id", population.get("batch_id"))
    offered = _require_id_set("offered_piece_ids", population.get("offered_piece_ids"))

    pieces = population.get("pieces")
    if not isinstance(pieces, (list, tuple)) or not pieces:
        raise ValueError("population pieces must be a non-empty sequence of mappings")

    seen = set()
    statuses = []
    foreign = []
    findings = []
    for piece in pieces:
        assessed = component_status(piece, policy)
        piece_id = assessed["piece_id"]
        if piece_id in seen:
            raise ValueError("population declares piece %s twice" % piece_id)
        seen.add(piece_id)
        if piece_id not in offered:
            foreign.append(piece_id)
            findings.append(
                "batch %s carries a status record for %s, which the batch does "
                "not offer" % (batch_id, piece_id)
            )
            continue
        statuses.append(assessed)
    statuses.sort(key=lambda entry: entry["piece_id"])

    unrecorded = sorted(offered - seen)
    for piece_id in unrecorded:
        findings.append(
            "offered piece %s has no status record at all, so it is undetermined"
            % piece_id
        )
    for entry in statuses:
        findings.extend(entry["findings"])

    failed = sorted(e["piece_id"] for e in statuses if e["failed"])
    deliverable = sorted(e["piece_id"] for e in statuses if e["deliverable"])
    undetermined = sorted(
        [e["piece_id"] for e in statuses if e["status"] == STATUS_UNDETERMINED]
        + unrecorded
    )
    incomplete_evidence = sorted(
        e["piece_id"] for e in statuses if e["failed"] and e["missing_evidence"]
    )

    offered_count = len(offered)
    failed_fraction = len(failed) / float(offered_count)
    if policy["count_undetermined_as_deliverable"]:
        deliverable = sorted(set(deliverable) | set(undetermined))

    grouped = {}
    for entry in statuses:
        grouped.setdefault(entry["status"], []).append(entry["piece_id"])
    for piece_id in unrecorded:
        grouped.setdefault(STATUS_UNDETERMINED, []).append(piece_id)

    mode_tally = {}
    for entry in statuses:
        for mode in entry["standing_modes"]:
            mode_tally.setdefault(mode, []).append(entry["piece_id"])

    settled = (
        not foreign
        and not incomplete_evidence
        and (policy["count_undetermined_as_deliverable"] or not undetermined)
    )
    return {
        "verdict": POPULATION_STATUS_ASSIGNED if settled else POPULATION_STATUS_INCOMPLETE,
        "batch_id": batch_id,
        "piece_statuses": statuses,
        "grouped_by_status": {k: sorted(v) for k, v in grouped.items()},
        "failed_piece_ids": failed,
        "deliverable_piece_ids": deliverable,
        "undetermined_piece_ids": undetermined,
        "foreign_piece_ids": sorted(foreign),
        "incomplete_evidence_piece_ids": incomplete_evidence,
        "offered_count": offered_count,
        "deliverable_count": len(deliverable),
        "failed_count": len(failed),
        "failed_fraction": failed_fraction,
        "every_offered_piece_statused": not undetermined,
        "findings": findings,
    }


def deliverable_share_within(population_result, allowance):
    """Is the failed share of a statused batch inside a declared allowance."""
    if not isinstance(population_result, dict):
        raise ValueError("population_result must be a mapping, got %r" % (population_result,))
    if isinstance(allowance, bool) or not isinstance(allowance, (int, float)):
        raise ValueError("allowance must be a number, got %r" % (allowance,))
    allowance = float(allowance)
    if not math.isfinite(allowance) or allowance < 0.0 or allowance > 1.0:
        raise ValueError("allowance must lie between 0 and 1, got %r" % (allowance,))
    fraction = population_result.get("failed_fraction")
    if fraction is None:
        raise ValueError("population_result carries no failed_fraction")
    return _within(float(fraction), allowance)
