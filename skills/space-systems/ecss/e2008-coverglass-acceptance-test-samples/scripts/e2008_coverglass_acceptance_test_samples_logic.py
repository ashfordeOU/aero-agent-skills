#!/usr/bin/env python3
"""Coverglass acceptance test samples drawn from each shipment lot.

Anchor: ECSS-E-ST-20-08C clause 8.5.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Acceptance testing of coverglasses is run on a sample, and the clause
puts two conditions on that sample rather than one. It has to be big
enough -- at least forty pieces -- and it has to be drawn at random
from the lot. Only the first of the two is usually recorded, because a
count is easy to write down and a draw method is not, so a lot arrives
with forty pieces that all came off the end of one carrier and the
traveller reads as compliant.

A sample that is large but not random is the defect this leaf exists to
catch. Forty pieces taken from a single tray answer one question about
one tray; they say nothing about the lot the shipment is being accepted
on, and the whole point of the draw is that it speaks for the lot.

Each shipment lot is graded on its own. A sample pooled from two lots
is not a sample of either, so pooling is refused at validation rather
than absorbed into a score, and a draw carrying more pieces than the
lot ever held is refused the same way.

Spread is measured against the lot's own composition, not against an
even split. A lot declares its strata -- carriers, trays, boat
positions, coating runs -- with the size of each, so the share of the
draw a stratum should carry is that stratum's share of the lot. The
draw is graded on how far the largest stratum deviation sits from that
proportional allocation, and on whether any declared stratum was
missed altogether.

    reached      every declared stratum contributed at least one piece
    proportional no stratum's share of the draw deviates from its share
                 of the lot by more than the declared tolerance

A lot smaller than the floor is a real case and not an error. The floor
cannot be reached by any draw, so the lot closes only by being drawn
whole, and whether that substitution is permitted is a project
position read from policy.

The floor, the spread tolerance and the short-lot position below are
declared project policy, not physical constants; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

DRAW_SOUND = "coverglass-draw-sound"
DRAW_CLUSTERED = "coverglass-draw-clustered"
DRAW_SHORT = "coverglass-draw-short"
DRAW_ABSENT = "coverglass-draw-absent"

DRAW_RANK = {
    DRAW_ABSENT: 0,
    DRAW_SHORT: 1,
    DRAW_CLUSTERED: 2,
    DRAW_SOUND: 3,
}

SHIPMENT_ACCEPTED = "coverglass-shipment-sampling-accepted"
SHIPMENT_NOT_ACCEPTED = "coverglass-shipment-sampling-not-accepted"

DEFAULT_SAMPLING_POLICY = {
    "min_sample_size": 40,
    "min_stratum_coverage": 1.0,
    "max_stratum_deviation": 0.15,
    "accept_exhaustive_short_lot": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_count(name, value, minimum=1):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _require_fraction(name, value):
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if not 0.0 <= value <= 1.0:
        raise ValueError(
            "%s must sit between zero and one inclusive, got %r" % (name, value)
        )
    return float(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Every quantity compared here is a quotient of two piece counts, so a
    draw allocated exactly in proportion can evaluate a unit in the last
    place either side of its own target. The comparison absorbs that;
    the declared limit is untouched.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def resolve_sampling_policy(policy=None):
    """Merge project policy over the declared defaults and validate it."""
    settings = dict(DEFAULT_SAMPLING_POLICY)
    if policy is not None:
        settings.update(_require_mapping("policy", policy))
    _require_count("min_sample_size", settings.get("min_sample_size"))
    _require_fraction("min_stratum_coverage", settings.get("min_stratum_coverage"))
    _require_fraction("max_stratum_deviation", settings.get("max_stratum_deviation"))
    _require_flag(
        "accept_exhaustive_short_lot", settings.get("accept_exhaustive_short_lot")
    )
    return settings


def validate_lot_record(lot):
    """Check one shipment lot declares its strata and an own-lot draw.

    Refuses a pooled draw, a draw naming a stratum the lot never
    declared, a repeated piece and a draw larger than the lot.
    """
    _require_mapping("lot", lot)
    lot_id = _require_label("lot_id", lot.get("lot_id"))
    strata = _require_mapping("strata", lot.get("strata") or {})
    if not strata:
        raise ValueError("lot %r declares no strata to draw from" % lot_id)

    sizes = {}
    for label, size in strata.items():
        name = _require_label("stratum", label)
        sizes[name] = _require_count("size of stratum %r" % name, size)
    lot_size = sum(sizes.values())

    declared_size = lot.get("lot_size")
    if declared_size is not None:
        _require_count("lot_size", declared_size)
        if declared_size != lot_size:
            raise ValueError(
                "lot %r declares %d pieces but its strata sum to %d"
                % (lot_id, declared_size, lot_size)
            )

    draw = lot.get("draw")
    if draw is None:
        draw = []
    if not isinstance(draw, (list, tuple)):
        raise ValueError("draw must be a sequence, got %r" % (draw,))

    seen = set()
    pieces = []
    for entry in draw:
        _require_mapping("draw entry", entry)
        piece_id = _require_label("piece_id", entry.get("piece_id"))
        stratum = _require_label("stratum", entry.get("stratum"))
        if stratum not in sizes:
            raise ValueError(
                "piece %r names stratum %r, which lot %r never declared"
                % (piece_id, stratum, lot_id)
            )
        source_lot = entry.get("from_lot")
        if source_lot is not None:
            source_lot = _require_label("from_lot", source_lot)
            if source_lot != lot_id:
                raise ValueError(
                    "piece %r was drawn from lot %r and pooled into lot %r; a "
                    "pooled sample is a sample of neither lot"
                    % (piece_id, source_lot, lot_id)
                )
        if piece_id in seen:
            raise ValueError("piece %r appears twice in one draw" % piece_id)
        seen.add(piece_id)
        pieces.append({"piece_id": piece_id, "stratum": stratum})

    if len(pieces) > lot_size:
        raise ValueError(
            "lot %r holds %d pieces but its draw carries %d"
            % (lot_id, lot_size, len(pieces))
        )
    return {
        "lot_id": lot_id,
        "strata": sizes,
        "lot_size": lot_size,
        "draw": pieces,
    }


def sample_size_assessment(lot, policy=None):
    """Grade the draw size against the floor the clause puts on the lot."""
    settings = resolve_sampling_policy(policy)
    record = validate_lot_record(lot)
    floor = settings["min_sample_size"]
    lot_size = record["lot_size"]
    drawn = len(record["draw"])
    short_lot = lot_size < floor
    effective_floor = min(floor, lot_size)
    exhaustive = drawn == lot_size
    draw_fraction = drawn / lot_size

    meets_floor = drawn >= effective_floor
    if short_lot and not settings["accept_exhaustive_short_lot"]:
        meets_floor = False

    findings = []
    if drawn == 0:
        findings.append(
            "%s: no acceptance sample was drawn at all, so the lot has not been "
            "sampled rather than sampled thinly" % record["lot_id"]
        )
    elif drawn < effective_floor:
        findings.append(
            "%s: the draw carries %d piece(s) against a floor of %d"
            % (record["lot_id"], drawn, effective_floor)
        )
    elif short_lot and not settings["accept_exhaustive_short_lot"]:
        findings.append(
            "%s: the lot holds %d piece(s), below the floor of %d, and project "
            "policy does not accept an exhaustive draw as a substitute"
            % (record["lot_id"], lot_size, floor)
        )
    elif short_lot:
        findings.append(
            "%s: the lot holds %d piece(s), below the floor of %d, so it closes "
            "only on an exhaustive draw and %d piece(s) were drawn"
            % (record["lot_id"], lot_size, floor, drawn)
        )
    return {
        "lot_id": record["lot_id"],
        "lot_size": lot_size,
        "drawn": drawn,
        "floor": floor,
        "effective_floor": effective_floor,
        "short_lot": short_lot,
        "exhaustive": exhaustive,
        "draw_fraction": draw_fraction,
        "meets_floor": meets_floor,
        "findings": findings,
    }


def stratum_spread(lot, policy=None):
    """Measure the draw against the lot's own proportional allocation.

    A stratum's share of the draw is compared with that stratum's share
    of the lot, so a lot built from unequal carriers is graded on what
    it actually holds instead of on an even split it never had.
    """
    settings = resolve_sampling_policy(policy)
    record = validate_lot_record(lot)
    lot_size = record["lot_size"]
    drawn = len(record["draw"])

    counts = {name: 0 for name in record["strata"]}
    for piece in record["draw"]:
        counts[piece["stratum"]] += 1

    entries = []
    worst_deviation = 0.0
    worst_stratum = None
    for name in sorted(record["strata"]):
        size = record["strata"][name]
        expected_share = size / lot_size
        observed_share = (counts[name] / drawn) if drawn else 0.0
        deviation = observed_share - expected_share
        magnitude = abs(deviation)
        if magnitude > worst_deviation:
            worst_deviation = magnitude
            worst_stratum = name
        entries.append(
            {
                "stratum": name,
                "size": size,
                "drawn": counts[name],
                "expected_share": expected_share,
                "observed_share": observed_share,
                "deviation": deviation,
            }
        )

    reached = sum(1 for name in counts if counts[name] > 0)
    coverage = reached / len(counts)
    missed = sorted(name for name in counts if counts[name] == 0)

    meets_coverage = _at_least(coverage, settings["min_stratum_coverage"])
    proportional = _at_most(worst_deviation, settings["max_stratum_deviation"])

    findings = []
    if drawn and missed:
        findings.append(
            "%s: stratum/strata %s contributed nothing to the draw, so the "
            "sample speaks for part of the lot only"
            % (record["lot_id"], ", ".join(missed))
        )
    if drawn and not proportional:
        findings.append(
            "%s: stratum %s deviates %.4g from its proportional share against a "
            "declared tolerance of %.4g; that is a convenience draw, not a "
            "random one"
            % (
                record["lot_id"],
                worst_stratum,
                worst_deviation,
                settings["max_stratum_deviation"],
            )
        )
    return {
        "lot_id": record["lot_id"],
        "strata": entries,
        "reached": reached,
        "coverage": coverage,
        "missed": missed,
        "worst_stratum": worst_stratum,
        "worst_deviation": worst_deviation,
        "meets_coverage": meets_coverage,
        "proportional": proportional,
        "findings": findings,
    }


def assess_lot_sample(lot, policy=None):
    """Grade one shipment lot on both conditions the clause puts on a draw."""
    settings = resolve_sampling_policy(policy)
    size = sample_size_assessment(lot, settings)
    spread = stratum_spread(lot, settings)

    findings = list(size["findings"])
    findings.extend(spread["findings"])

    if size["drawn"] == 0:
        verdict = DRAW_ABSENT
    elif not size["meets_floor"]:
        verdict = DRAW_SHORT
    elif not (spread["meets_coverage"] and spread["proportional"]):
        verdict = DRAW_CLUSTERED
    else:
        verdict = DRAW_SOUND
    return {
        "lot_id": size["lot_id"],
        "size": size,
        "spread": spread,
        "verdict": verdict,
        "findings": findings,
    }


def assess_shipment_sampling(case):
    """Full clause 8.5.1 roll-up over every lot in one shipment."""
    _require_mapping("case", case)
    shipment_id = _require_label("shipment_id", case.get("shipment_id"))
    lots = case.get("lots")
    if not isinstance(lots, (list, tuple)) or not lots:
        raise ValueError("case must carry a non-empty lots sequence")
    settings = resolve_sampling_policy(case.get("policy"))

    seen = set()
    assessments = []
    for lot in lots:
        assessment = assess_lot_sample(lot, settings)
        if assessment["lot_id"] in seen:
            raise ValueError(
                "lot %r appears twice in one shipment" % assessment["lot_id"]
            )
        seen.add(assessment["lot_id"])
        assessments.append(assessment)

    findings = []
    for assessment in assessments:
        findings.extend(assessment["findings"])

    grouped = {}
    for assessment in assessments:
        grouped.setdefault(assessment["verdict"], []).append(assessment["lot_id"])
    for names in grouped.values():
        names.sort()

    weakest = min(
        assessments, key=lambda a: (DRAW_RANK[a["verdict"]], a["lot_id"])
    )
    total_drawn = sum(a["size"]["drawn"] for a in assessments)
    total_pieces = sum(a["size"]["lot_size"] for a in assessments)
    shipment_fraction = total_drawn / total_pieces

    sound = [a for a in assessments if a["verdict"] == DRAW_SOUND]
    verdict = (
        SHIPMENT_ACCEPTED if len(sound) == len(assessments) else SHIPMENT_NOT_ACCEPTED
    )
    return {
        "shipment_id": shipment_id,
        "lots": assessments,
        "grouped_lots": grouped,
        "total_drawn": total_drawn,
        "total_pieces": total_pieces,
        "shipment_fraction": shipment_fraction,
        "weakest_lot": weakest["lot_id"],
        "verdict": verdict,
        "findings": findings,
    }
