#!/usr/bin/env python3
"""Continuity of the front bus bars and grid lines of a bare solar cell.

Anchor: ECSS-E-ST-20-08C clause 7.5.1.5.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause asks one question of the front metallization and refuses to
grade the answer: the bus bars and the grid lines have to run through,
without a break. That makes the survey two screens that must not be run
with the same rule.

    continuity broken   a full interruption or a crack through the metal
                        is decided by presence. There is no width below
                        which a break passes, because what is lost is the
                        path itself and every finger beyond the break
                        stops delivering into the bus bar.
    still conducting    a narrowing, an edge nick or a void inside the
                        line footprint leaves metal in place. That is
                        measured -- as the width that survived, and as
                        the current density the survivor now carries --
                        and dispositioned against the declared criteria.

Two derived numbers do the work that a width measurement alone cannot:

    residual width fraction   the narrowest surviving width over the
                              nominal line width. A bus bar is held
                              tighter than a finger because everything
                              the cell collects passes through it.
    orphaned collection       the share of a line's collection strip cut
                              off from any bus bar by a break. A finger
                              fed from a bus bar at both ends orphans
                              nothing when it breaks once; a finger fed
                              from one end orphans everything past the
                              break. The break is refused either way --
                              the number sizes the current loss for the
                              reviewer, it does not excuse the finding.

Line kinds
    front-bus-bar   the collecting bar the fingers deliver into
    grid-finger     a collection line running into a bus bar

Indication kinds
    line-break            the metal is interrupted across the full width
    line-crack-through    a fracture that separates the line electrically
    line-constriction     a local narrowing that still conducts
    line-edge-nick        metal lost from one side of the line
    line-void             a hole inside the line footprint

Dispositions are accept, review and reject. A bare cell front grid is
not reworkable in the way a solder joint is, so the middle disposition
holds the cell for a non-conformance decision rather than promising a
repair. The limits below are a declared project criteria set, not a
physical constant; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

LINE_KINDS = (
    "front-bus-bar",
    "grid-finger",
)

INDICATION_KINDS = (
    "line-break",
    "line-crack-through",
    "line-constriction",
    "line-edge-nick",
    "line-void",
)

CONTINUITY_BREAKING_KINDS = (
    "line-break",
    "line-crack-through",
)

ACCEPT = "accept"
REVIEW = "review"
REJECT = "reject"
DISPOSITIONS = (ACCEPT, REVIEW, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REVIEW: 1, REJECT: 2}

DEFAULT_GRID_CONTINUITY_CRITERIA = {
    # Narrowest surviving width over the nominal width of the line.
    "accept_residual_width_fraction": {
        "front-bus-bar": 0.85,
        "grid-finger": 0.75,
    },
    "review_residual_width_fraction": {
        "front-bus-bar": 0.65,
        "grid-finger": 0.55,
    },
    # Current density in the metal that survived the narrowing.
    "accept_current_density_a_per_mm2": 150.0,
    "review_current_density_a_per_mm2": 220.0,
}

_MEASURED_KINDS = (
    "line-constriction",
    "line-edge-nick",
    "line-void",
)

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _close(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A residual fraction is a quotient and a current density is a quotient
    of a quotient, so a measurement meant to sit exactly on a limit can
    evaluate a few units in the last place to either side of it. The
    limit is never moved; only the comparison tolerates the error.
    """
    return value <= limit or _close(value, limit)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or _close(value, limit)


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_grid_continuity_criteria(criteria):
    """Check a criteria set covers every line kind and stays self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    for key in ("accept_residual_width_fraction", "review_residual_width_fraction"):
        table = criteria.get(key)
        if not isinstance(table, dict):
            raise ValueError("criteria %s must be a mapping" % key)
        missing = set(LINE_KINDS) - set(table)
        if missing:
            raise ValueError(
                "criteria %s is missing line kinds: %s"
                % (key, ", ".join(sorted(missing)))
            )
        for line_kind in LINE_KINDS:
            fraction = _require_positive(
                "criteria %s[%s]" % (key, line_kind), table[line_kind]
            )
            if fraction > 1.0 and not _close(fraction, 1.0):
                raise ValueError(
                    "criteria %s[%s] cannot exceed one, got %r"
                    % (key, line_kind, table[line_kind])
                )
    for line_kind in LINE_KINDS:
        accept = criteria["accept_residual_width_fraction"][line_kind]
        review = criteria["review_residual_width_fraction"][line_kind]
        if review > accept and not _close(review, accept):
            raise ValueError(
                "criteria review_residual_width_fraction[%s] is above the "
                "accept fraction; the review band has to be the looser one"
                % line_kind
            )
    accept_density = _require_positive(
        "accept_current_density_a_per_mm2",
        criteria.get("accept_current_density_a_per_mm2"),
    )
    review_density = _require_positive(
        "review_current_density_a_per_mm2",
        criteria.get("review_current_density_a_per_mm2"),
    )
    if review_density < accept_density and not _close(review_density, accept_density):
        raise ValueError(
            "criteria review_current_density_a_per_mm2 is below the accept "
            "limit; the review band has to be the looser one"
        )
    return criteria


def residual_width_fraction(nominal_width_um, narrowest_width_um):
    """Share of the nominal line width that survived at the narrowest point."""
    nominal = _require_positive("nominal_width_um", nominal_width_um)
    narrowest = _require_non_negative("narrowest_width_um", narrowest_width_um)
    if narrowest > nominal and not _close(narrowest, nominal):
        raise ValueError(
            "narrowest width %.3f um exceeds the nominal width %.3f um; the "
            "measurement or the nominal is wrong" % (narrowest, nominal)
        )
    if narrowest > nominal:
        narrowest = nominal
    return narrowest / nominal


def orphaned_collection_fraction(line_length_mm, break_position_mm, feed_ends):
    """Share of a line's collection strip a break cuts off from a bus bar.

    feed_ends is 1 when the line reaches a bus bar at one end only and 2
    when it is fed from both. A line fed from both ends still delivers
    every part of itself after a single break, so the orphaned share is
    zero -- which is a statement about current loss, not about whether
    the break is acceptable.
    """
    length = _require_positive("line_length_mm", line_length_mm)
    position = _require_non_negative("break_position_mm", break_position_mm)
    if isinstance(feed_ends, bool) or feed_ends not in (1, 2):
        raise ValueError(
            "feed_ends must be 1 or 2, got %r; a grid line reaches a bus bar "
            "at one end or at both" % (feed_ends,)
        )
    if position > length and not _close(position, length):
        raise ValueError(
            "break position %.3f mm lies past the %.3f mm line length"
            % (position, length)
        )
    if position > length:
        position = length
    if feed_ends == 2:
        return 0.0
    return (length - position) / length


def local_current_density_a_per_mm2(line_current_a, width_um, thickness_um):
    """Current density in the metal left at the narrowest cross section."""
    current = _require_non_negative("line_current_a", line_current_a)
    width = _require_positive("width_um", width_um)
    thickness = _require_positive("metal_thickness_um", thickness_um)
    area_mm2 = (width / 1000.0) * (thickness / 1000.0)
    return current / area_mm2


def assess_grid_indication(indication, criteria=DEFAULT_GRID_CONTINUITY_CRITERIA):
    """Disposition one front-metallization indication against the criteria."""
    validate_grid_continuity_criteria(criteria)
    if not isinstance(indication, dict):
        raise ValueError("indication must be a mapping, got %r" % (indication,))
    kind = _require_choice("kind", indication.get("kind"), INDICATION_KINDS)
    line_kind = _require_choice(
        "line_kind", indication.get("line_kind"), LINE_KINDS
    )
    reasons = []
    measurements = {}
    continuity_broken = kind in CONTINUITY_BREAKING_KINDS

    if continuity_broken:
        length = indication.get("line_length_mm")
        position = indication.get("break_position_mm")
        feed_ends = indication.get("feed_ends")
        if length is None or position is None or feed_ends is None:
            raise ValueError(
                "a %s indication needs line_length_mm, break_position_mm and "
                "feed_ends so the orphaned collection share can be sized" % kind
            )
        orphaned = orphaned_collection_fraction(length, position, feed_ends)
        measurements["orphaned_collection_fraction"] = orphaned
        disposition = REJECT
        reasons.append(
            "%s interrupts a %s; the continuity requirement carries no width "
            "allowance and %.3f of the collection strip is orphaned"
            % (kind, line_kind, orphaned)
        )
    else:
        nominal = indication.get("nominal_width_um")
        narrowest = indication.get("narrowest_width_um")
        if nominal is None or narrowest is None:
            raise ValueError(
                "a %s indication needs nominal_width_um and narrowest_width_um "
                "to show how much metal survived" % kind
            )
        fraction = residual_width_fraction(nominal, narrowest)
        accept_fraction = criteria["accept_residual_width_fraction"][line_kind]
        review_fraction = criteria["review_residual_width_fraction"][line_kind]
        measurements["residual_width_fraction"] = fraction
        measurements["accept_residual_width_fraction"] = accept_fraction
        measurements["review_residual_width_fraction"] = review_fraction
        if _at_least(fraction, accept_fraction):
            disposition = ACCEPT
        elif _at_least(fraction, review_fraction):
            disposition = REVIEW
            reasons.append(
                "residual width %.3f of nominal is under the %.3f accept "
                "fraction for a %s; the line still conducts and the cell is "
                "held for a non-conformance decision"
                % (fraction, accept_fraction, line_kind)
            )
        else:
            disposition = REJECT
            reasons.append(
                "residual width %.3f of nominal is under the %.3f review "
                "fraction for a %s; too little metal is left to carry the "
                "line current" % (fraction, review_fraction, line_kind)
            )

        current = indication.get("line_current_a")
        thickness = indication.get("metal_thickness_um")
        if (current is None) != (thickness is None):
            raise ValueError(
                "line_current_a and metal_thickness_um are a pair; one without "
                "the other cannot produce a current density and silently drops "
                "the second half of the screen"
            )
        if current is not None:
            density = local_current_density_a_per_mm2(
                current, narrowest, thickness
            )
            accept_density = criteria["accept_current_density_a_per_mm2"]
            review_density = criteria["review_current_density_a_per_mm2"]
            measurements["local_current_density_a_per_mm2"] = density
            measurements["accept_current_density_a_per_mm2"] = accept_density
            measurements["review_current_density_a_per_mm2"] = review_density
            if _at_most(density, accept_density):
                density_call = ACCEPT
            elif _at_most(density, review_density):
                density_call = REVIEW
                reasons.append(
                    "current density %.1f A/mm2 in the surviving metal is over "
                    "the %.1f A/mm2 accept limit"
                    % (density, accept_density)
                )
            else:
                density_call = REJECT
                reasons.append(
                    "current density %.1f A/mm2 in the surviving metal is over "
                    "the %.1f A/mm2 review limit"
                    % (density, review_density)
                )
            disposition = _worst([disposition, density_call])

    return {
        "id": indication.get("id"),
        "kind": kind,
        "line_kind": line_kind,
        "continuity_broken": continuity_broken,
        "disposition": disposition,
        "measurements": measurements,
        "reasons": reasons,
    }


def group_indications_by_line_kind(indications):
    """Group a survey by line kind and count the continuity-breaking ones."""
    if not isinstance(indications, (list, tuple)):
        raise ValueError("indications must be a list, got %r" % (indications,))
    counts = dict((line_kind, 0) for line_kind in LINE_KINDS)
    broken = dict((line_kind, 0) for line_kind in LINE_KINDS)
    for indication in indications:
        if not isinstance(indication, dict):
            raise ValueError(
                "each indication must be a mapping, got %r" % (indication,)
            )
        kind = _require_choice("kind", indication.get("kind"), INDICATION_KINDS)
        line_kind = _require_choice(
            "line_kind", indication.get("line_kind"), LINE_KINDS
        )
        counts[line_kind] += 1
        if kind in CONTINUITY_BREAKING_KINDS:
            broken[line_kind] += 1
    return {
        "counts": counts,
        "continuity_broken_counts": broken,
        "continuity_broken_total": sum(broken.values()),
    }


def assess_cell_front_grid(cell, criteria=DEFAULT_GRID_CONTINUITY_CRITERIA):
    """Full clause 7.5.1.5.3 continuity screen of one bare cell front."""
    validate_grid_continuity_criteria(criteria)
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    cell_id = cell.get("cell_id")
    if not isinstance(cell_id, str) or not cell_id.strip():
        raise ValueError("cell needs a non-empty cell_id for traceability")
    indications = cell.get("indications")
    if not isinstance(indications, (list, tuple)):
        raise ValueError(
            "cell indications must be a list, got %r" % (indications,)
        )

    seen = set()
    assessed = []
    for indication in indications:
        result = assess_grid_indication(indication, criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate indication id %r on cell %s; the survey would "
                    "lose traceability to the measurement record"
                    % (marker, cell_id)
                )
            seen.add(marker)
        assessed.append(result)

    grouping = group_indications_by_line_kind(list(indications))
    calls = [result["disposition"] for result in assessed]
    verdict = _worst(calls) if calls else ACCEPT
    broken_ids = [
        result["id"] for result in assessed if result["continuity_broken"]
    ]
    orphaned_values = [
        result["measurements"]["orphaned_collection_fraction"]
        for result in assessed
        if "orphaned_collection_fraction" in result["measurements"]
    ]
    worst_orphaned = max(orphaned_values) if orphaned_values else 0.0

    findings = []
    if not assessed:
        findings.append(
            "no indications recorded; the front metallization was surveyed "
            "and runs through, and the record stands as the evidence"
        )
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))
    if broken_ids:
        findings.append(
            "continuity is broken at %s; no width measurement reaches those "
            "findings" % ", ".join(str(marker) for marker in broken_ids)
        )

    return {
        "cell_id": cell_id,
        "verdict": verdict,
        "indications": assessed,
        "reject_count": calls.count(REJECT),
        "review_count": calls.count(REVIEW),
        "accept_count": calls.count(ACCEPT),
        "continuity_broken_ids": broken_ids,
        "worst_orphaned_collection_fraction": worst_orphaned,
        "line_kind_counts": grouping["counts"],
        "nonconformance_review_required": verdict == REVIEW,
        "findings": findings,
    }
