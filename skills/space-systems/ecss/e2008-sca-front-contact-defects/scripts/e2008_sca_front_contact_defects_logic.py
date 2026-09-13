#!/usr/bin/env python3
"""Front contact metallisation continuity on a solar cell assembly.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.1.7. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The front contact is the metallisation that collects photo-generated
current off the illuminated face: fine gridlines running across the cell
and busbars gathering them toward the interconnector terminals. The
clause keeps that metallisation free of interruptions and free of
delamination.

Freedom from an interruption is a topology question, not a counting one.
A break matters for where it sits, not for how wide it is:

    gridline break   orphans the metallisation on the far side of the
                     break from the busbar that feeds it
    busbar break     orphans every gridline whose feed point sits beyond
                     the break, so one short break can take a whole
                     region of the cell out of collection

Delamination is metallisation lifted off the cell. It may still conduct
on the day it is found, so a continuity reading does not see it; the
clause permits none of it regardless of whether the circuit is still
closed.

Two states are not defects and are not accepts either. A record set
shorter than the declared conductor list leaves the cell open, and an
inspection that cannot resolve a break of the required size cannot
support a statement that there is none.

The detection policy below is a declared policy, not a physical
constant; a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FRONT_CONTACT_DEFECT_KINDS = (
    "metallisation-interruption",
    "metallisation-delamination",
)

CONDUCTOR_ROLES = ("front-gridline", "front-busbar")

ACCEPT = "accept"
REJECT = "reject"
INSPECTION_INCOMPLETE = "inspection-incomplete"
DETECTION_INSUFFICIENT = "detection-insufficient"

FRONT_CONTACT_VERDICTS = (
    ACCEPT,
    REJECT,
    INSPECTION_INCOMPLETE,
    DETECTION_INSUFFICIENT,
)

DEFAULT_FRONT_CONTACT_POLICY = {
    "required_detection_mm": 0.05,
    "report_collection_loss": True,
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


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_front_contact_policy(policy):
    """Check a front contact detection policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "required_detection_mm", policy.get("required_detection_mm")
    )
    flag = policy.get("report_collection_loss")
    if not isinstance(flag, bool):
        raise ValueError(
            "report_collection_loss must be true or false, got %r" % (flag,)
        )
    return policy


def _defect_gaps(conductor_id, length_mm, defects):
    """Split one conductor's defect records into gaps and lifted spans."""
    if not isinstance(defects, (list, tuple)):
        raise ValueError("defects must be a list on conductor %s" % conductor_id)
    gaps = []
    lifted = []
    seen = set()
    for defect in defects:
        if not isinstance(defect, dict):
            raise ValueError(
                "each defect must be a mapping on conductor %s" % conductor_id
            )
        kind = _require_choice(
            "defect kind", defect.get("kind"), FRONT_CONTACT_DEFECT_KINDS
        )
        marker = defect.get("id")
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate defect id %r on conductor %s"
                    % (marker, conductor_id)
                )
            seen.add(marker)
        position = _require_non_negative(
            "defect position_mm on %s" % conductor_id, defect.get("position_mm")
        )
        if not _at_most(position, length_mm):
            raise ValueError(
                "defect at %g mm sits past the %g mm length of conductor %s"
                % (position, length_mm, conductor_id)
            )
        extent = _require_non_negative(
            "defect extent_mm on %s" % conductor_id, defect.get("extent_mm", 0.0)
        )
        start = max(0.0, position - extent / 2.0)
        end = min(length_mm, position + extent / 2.0)
        span = {
            "id": marker,
            "kind": kind,
            "start_mm": start,
            "end_mm": end,
            "position_mm": position,
            "extent_mm": extent,
        }
        if kind == "metallisation-interruption":
            gaps.append(span)
        else:
            lifted.append(span)
    return gaps, lifted


def connected_span(length_mm, feed_position_mm, gaps):
    """Span of one conductor still tied to its feed point.

    The feed point is where the conductor meets the metallisation that
    carries its current away. Metallisation beyond the nearest break on
    either side of that point is orphaned, whatever its own condition.
    """
    length = _require_positive("length_mm", length_mm)
    feed = _require_non_negative("feed_position_mm", feed_position_mm)
    if not _at_most(feed, length):
        raise ValueError(
            "feed_position_mm %g sits past the conductor length %g"
            % (feed, length)
        )
    lower = 0.0
    upper = length
    for gap in gaps:
        start = gap["start_mm"]
        end = gap["end_mm"]
        if start <= feed <= end:
            return (feed, feed, 0.0)
        if end < feed:
            lower = max(lower, end)
        elif start > feed:
            upper = min(upper, start)
    return (lower, upper, max(0.0, upper - lower))


def assess_conductor(conductor):
    """Read one conductor record and work out what stays connected."""
    if not isinstance(conductor, dict):
        raise ValueError("conductor record must be a mapping, got %r" % (conductor,))
    conductor_id = _require_text("conductor_id", conductor.get("conductor_id"))
    role = _require_choice("role", conductor.get("role"), CONDUCTOR_ROLES)
    length = _require_positive(
        "length_mm on %s" % conductor_id, conductor.get("length_mm")
    )
    feed = _require_non_negative(
        "feed_position_mm on %s" % conductor_id,
        conductor.get("feed_position_mm", 0.0),
    )
    if not _at_most(feed, length):
        raise ValueError(
            "feed_position_mm %g sits past the %g mm length of conductor %s"
            % (feed, length, conductor_id)
        )
    gaps, lifted = _defect_gaps(
        conductor_id, length, conductor.get("defects", [])
    )
    lower, upper, connected = connected_span(length, feed, gaps)
    delaminated = sum(span["end_mm"] - span["start_mm"] for span in lifted)
    lifted_over_gap = [
        span["id"]
        for span in lifted
        if any(
            span["start_mm"] < gap["end_mm"] and gap["start_mm"] < span["end_mm"]
            for gap in gaps
        )
    ]
    return {
        "conductor_id": conductor_id,
        "role": role,
        "length_mm": length,
        "feed_position_mm": feed,
        "connected_from_mm": lower,
        "connected_to_mm": upper,
        "connected_length_mm": connected,
        "orphaned_length_mm": max(0.0, length - connected),
        "interruption_count": len(gaps),
        "delamination_count": len(lifted),
        "delaminated_length_mm": delaminated,
        "delamination_over_interruption": lifted_over_gap,
        "interruptions": gaps,
        "delaminations": lifted,
    }


def _feed_is_live(busbar_result, feeds_at_mm):
    """True when a gridline feed point still reaches its busbar terminal."""
    if busbar_result["connected_length_mm"] <= 0.0:
        return False
    return _at_least(feeds_at_mm, busbar_result["connected_from_mm"]) and _at_most(
        feeds_at_mm, busbar_result["connected_to_mm"]
    )


def assess_front_contact(cell, policy=DEFAULT_FRONT_CONTACT_POLICY):
    """Clause 6.4.3.1.7 judgement for one solar cell assembly front contact."""
    validate_front_contact_policy(policy)
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    cell_id = _require_text("cell_id", cell.get("cell_id"))
    declared = cell.get("declared_conductor_count")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
        raise ValueError(
            "declared_conductor_count must be a positive integer, got %r"
            % (declared,)
        )
    records = cell.get("conductors")
    if not isinstance(records, (list, tuple)):
        raise ValueError("conductors must be a list, got %r" % (records,))
    if len(records) > declared:
        raise ValueError(
            "%d conductor records against a declared count of %d on %s"
            % (len(records), declared, cell_id)
        )

    results = []
    by_id = {}
    for record in records:
        result = assess_conductor(record)
        if result["conductor_id"] in by_id:
            raise ValueError(
                "duplicate conductor id %r on cell %s"
                % (result["conductor_id"], cell_id)
            )
        by_id[result["conductor_id"]] = result
        results.append(result)

    busbars = [r for r in results if r["role"] == "front-busbar"]
    gridlines = [r for r in results if r["role"] == "front-gridline"]

    findings = []
    total_gridline_mm = 0.0
    lost_gridline_mm = 0.0
    orphaned_gridline_ids = []

    for record, result in zip(records, results):
        if result["role"] != "front-gridline":
            continue
        total_gridline_mm += result["length_mm"]
        busbar_id = record.get("feeds_busbar_id")
        live_feed = True
        if busbar_id is not None:
            _require_text("feeds_busbar_id", busbar_id)
            if busbar_id not in by_id:
                raise ValueError(
                    "gridline %s feeds unknown busbar %r"
                    % (result["conductor_id"], busbar_id)
                )
            busbar = by_id[busbar_id]
            if busbar["role"] != "front-busbar":
                raise ValueError(
                    "gridline %s feeds %s, which is not a busbar"
                    % (result["conductor_id"], busbar_id)
                )
            feeds_at = _require_non_negative(
                "feeds_at_mm on %s" % result["conductor_id"],
                record.get("feeds_at_mm", busbar["feed_position_mm"]),
            )
            if not _at_most(feeds_at, busbar["length_mm"]):
                raise ValueError(
                    "gridline %s meets busbar %s at %g mm, past its %g mm length"
                    % (result["conductor_id"], busbar_id, feeds_at, busbar["length_mm"])
                )
            live_feed = _feed_is_live(busbar, feeds_at)
        result["feed_is_live"] = live_feed
        if live_feed:
            live_length = result["connected_length_mm"]
        else:
            live_length = 0.0
            orphaned_gridline_ids.append(result["conductor_id"])
            findings.append(
                "gridline %s is cut off at its busbar feed, so the whole %g mm "
                "of it stops collecting" % (result["conductor_id"], result["length_mm"])
            )
        result["live_length_mm"] = live_length
        lost_gridline_mm += result["length_mm"] - live_length

    for result in results:
        if result["interruption_count"]:
            findings.append(
                "%s carries %d interruption(s); the front contact is required "
                "to be continuous"
                % (result["conductor_id"], result["interruption_count"])
            )
        if result["delamination_count"]:
            findings.append(
                "%s carries %.3f mm of delaminated metallisation; none is "
                "permitted" % (result["conductor_id"], result["delaminated_length_mm"])
            )
        for marker in result["delamination_over_interruption"]:
            findings.append(
                "delamination %r on %s overlaps an interruption, so the lifted "
                "metallisation is already open" % (marker, result["conductor_id"])
            )

    total_metallisation_mm = sum(r["length_mm"] for r in results)
    delaminated_mm = sum(r["delaminated_length_mm"] for r in results)
    interruption_total = sum(r["interruption_count"] for r in results)
    delamination_total = sum(r["delamination_count"] for r in results)

    collection_loss = (
        lost_gridline_mm / total_gridline_mm if total_gridline_mm > 0.0 else 0.0
    )
    delaminated_fraction = (
        delaminated_mm / total_metallisation_mm
        if total_metallisation_mm > 0.0
        else 0.0
    )

    missing = declared - len(results)
    resolution = cell.get("min_detectable_feature_mm")
    detection_ok = None
    if resolution is not None:
        resolution = _require_positive("min_detectable_feature_mm", resolution)
        detection_ok = _at_most(resolution, float(policy["required_detection_mm"]))

    if interruption_total or delamination_total:
        verdict = REJECT
    elif missing > 0:
        verdict = INSPECTION_INCOMPLETE
        findings.append(
            "%d of %d conductors carry no inspection record; an absent record "
            "is not a clean one" % (missing, declared)
        )
    elif detection_ok is False:
        verdict = DETECTION_INSUFFICIENT
        findings.append(
            "the inspection resolves %.4f mm while a break of %.4f mm has to "
            "be visible, so a clean reading is not evidence of continuity"
            % (resolution, float(policy["required_detection_mm"]))
        )
    else:
        verdict = ACCEPT

    return {
        "cell_id": cell_id,
        "verdict": verdict,
        "inspection_complete": missing == 0,
        "missing_record_count": missing,
        "detection_adequate": detection_ok,
        "busbar_count": len(busbars),
        "gridline_count": len(gridlines),
        "interruption_count": interruption_total,
        "delamination_count": delamination_total,
        "delaminated_length_mm": delaminated_mm,
        "delaminated_fraction": delaminated_fraction,
        "orphaned_gridline_ids": orphaned_gridline_ids,
        "gridline_length_mm": total_gridline_mm,
        "gridline_length_lost_mm": lost_gridline_mm,
        "collection_loss_fraction": collection_loss,
        "conductors": results,
        "findings": findings,
    }
