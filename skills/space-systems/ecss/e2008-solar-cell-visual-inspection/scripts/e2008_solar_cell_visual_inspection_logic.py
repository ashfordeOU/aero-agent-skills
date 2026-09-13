#!/usr/bin/env python3
"""Defect quantity limits across the solar cells of an inspected coupon.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.8. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause is a counting screen rather than a sizing one. Every cell on
the coupon is looked at, each observation is recorded against its kind,
and the coupon is dispositioned on how many of each kind turned up --
how many on one cell, and on how many cells across the coupon. A defect
that is individually small still consumes a quantity allowance.

Two allowances run in parallel:

    per-cell         how many occurrences of a kind one cell may carry
    per-coupon       what fraction of the inspected cells may carry that
                     kind at all

A kind whose per-cell allowance is zero is not permitted at any
quantity; a single occurrence takes the cell out of the accept band.

Dispositions are accept, refer-for-review and reject. The limits below
are a declared coupon limit set, not a physical constant; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CELL_DEFECT_KINDS = (
    "edge-chip",
    "corner-chip",
    "front-contact-void",
    "antireflective-coating-blemish",
    "cell-crack",
    "handling-scratch",
)

ACCEPT = "accept"
REFER = "refer-for-review"
REJECT = "reject"
CELL_DISPOSITIONS = (ACCEPT, REFER, REJECT)

INSPECTION_INCOMPLETE = "inspection-incomplete"

_SEVERITY_ORDER = {ACCEPT: 0, REFER: 1, REJECT: 2}

DEFAULT_CELL_DEFECT_LIMITS = {
    "per_cell_kind_allowance": {
        "edge-chip": 2,
        "corner-chip": 1,
        "front-contact-void": 2,
        "antireflective-coating-blemish": 3,
        "cell-crack": 0,
        "handling-scratch": 2,
    },
    "affected_cell_fraction": {
        "edge-chip": 0.10,
        "corner-chip": 0.05,
        "front-contact-void": 0.10,
        "antireflective-coating-blemish": 0.20,
        "cell-crack": 0.0,
        "handling-scratch": 0.10,
    },
    "max_defects_per_cell": 4,
    "max_affected_cell_fraction": 0.25,
    "review_margin_factor": 1.5,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_fraction(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    return float(value)


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative integer, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A coupon allowance is a product of a declared fraction and a counted
    number of cells, so an affected count sitting exactly on the
    allowance can evaluate a few units in the last place above it. The
    allowance is never raised; only the comparison tolerates the
    representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_cell_defect_limits(limits):
    """Check a coupon quantity limit set is complete and self-consistent."""
    if not isinstance(limits, dict):
        raise ValueError("limits must be a mapping, got %r" % (limits,))
    per_cell = limits.get("per_cell_kind_allowance")
    if not isinstance(per_cell, dict):
        raise ValueError("limits per_cell_kind_allowance must be a mapping")
    per_coupon = limits.get("affected_cell_fraction")
    if not isinstance(per_coupon, dict):
        raise ValueError("limits affected_cell_fraction must be a mapping")
    for kind in CELL_DEFECT_KINDS:
        if kind not in per_cell:
            raise ValueError("limits per_cell_kind_allowance is missing %s" % kind)
        if kind not in per_coupon:
            raise ValueError("limits affected_cell_fraction is missing %s" % kind)
        _require_count("limits per_cell_kind_allowance %s" % kind, per_cell[kind])
        _require_fraction("limits affected_cell_fraction %s" % kind, per_coupon[kind])
        if per_cell[kind] == 0 and per_coupon[kind] > 0.0:
            raise ValueError(
                "limits allow %s on a fraction of the coupon while permitting "
                "none of it on any single cell; the two allowances contradict "
                "each other" % kind
            )
    _require_count("limits max_defects_per_cell", limits.get("max_defects_per_cell"))
    _require_fraction(
        "limits max_affected_cell_fraction", limits.get("max_affected_cell_fraction")
    )
    factor = limits.get("review_margin_factor")
    if not _is_finite_number(factor) or factor < 1.0:
        raise ValueError(
            "limits review_margin_factor must be at least one, got %r" % (factor,)
        )
    return limits


def count_cell_defects(cell):
    """Tally one cell record by defect kind, rejecting a malformed record."""
    if not isinstance(cell, dict):
        raise ValueError("cell record must be a mapping, got %r" % (cell,))
    cell_id = cell.get("cell_id")
    if not isinstance(cell_id, str) or not cell_id.strip():
        raise ValueError("each cell record needs a non-empty cell_id")
    defects = cell.get("defects", [])
    if not isinstance(defects, (list, tuple)):
        raise ValueError("defects must be a list on cell %s" % cell_id)
    counts = dict((kind, 0) for kind in CELL_DEFECT_KINDS)
    seen = set()
    for defect in defects:
        if not isinstance(defect, dict):
            raise ValueError("each defect must be a mapping on cell %s" % cell_id)
        kind = _require_choice("kind", defect.get("kind"), CELL_DEFECT_KINDS)
        marker = defect.get("id")
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate defect id %r on cell %s" % (marker, cell_id)
                )
            seen.add(marker)
        counts[kind] += 1
    return {
        "cell_id": cell_id,
        "counts": counts,
        "total": sum(counts.values()),
    }


def assess_cell(cell, limits=DEFAULT_CELL_DEFECT_LIMITS):
    """Disposition one cell against the per-cell quantity allowances."""
    validate_cell_defect_limits(limits)
    tally = count_cell_defects(cell)
    per_cell = limits["per_cell_kind_allowance"]
    factor = limits["review_margin_factor"]

    findings = []
    dispositions = [ACCEPT]
    exceeded = []
    for kind in CELL_DEFECT_KINDS:
        count = tally["counts"][kind]
        allowed = per_cell[kind]
        if count <= allowed:
            continue
        exceeded.append(kind)
        review_limit = allowed * factor
        if allowed == 0:
            dispositions.append(REJECT)
            findings.append(
                "%d %s on one cell; the kind is not permitted at any quantity"
                % (count, kind)
            )
        elif _at_most(count, review_limit):
            dispositions.append(REFER)
            findings.append(
                "%d %s on one cell, past the allowance of %d"
                % (count, kind, allowed)
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "%d %s on one cell, past the review margin of %.2f on an "
                "allowance of %d" % (count, kind, review_limit, allowed)
            )

    if tally["total"] > limits["max_defects_per_cell"]:
        dispositions.append(REFER)
        findings.append(
            "%d defects on one cell exceed the %d allowed in total even though "
            "no single kind did"
            % (tally["total"], limits["max_defects_per_cell"])
        )

    return {
        "cell_id": tally["cell_id"],
        "verdict": _worst(dispositions),
        "counts": tally["counts"],
        "defect_total": tally["total"],
        "kinds_over_allowance": exceeded,
        "findings": findings,
    }


def inspect_coupon_cells(coupon, limits=DEFAULT_CELL_DEFECT_LIMITS):
    """Clause 5.5.3.2.8 quantity screen over the cells of one coupon."""
    validate_cell_defect_limits(limits)
    if not isinstance(coupon, dict):
        raise ValueError("coupon must be a mapping, got %r" % (coupon,))
    coupon_id = coupon.get("coupon_id")
    if not isinstance(coupon_id, str) or not coupon_id.strip():
        raise ValueError("coupon needs a non-empty coupon_id")
    declared = coupon.get("declared_cell_count")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
        raise ValueError(
            "declared_cell_count must be a positive integer, got %r" % (declared,)
        )
    records = coupon.get("cells")
    if not isinstance(records, (list, tuple)):
        raise ValueError("cells must be a list, got %r" % (records,))
    if len(records) > declared:
        raise ValueError(
            "%d cell records against a declared count of %d on %s"
            % (len(records), declared, coupon_id)
        )

    seen = set()
    screened = []
    for record in records:
        result = assess_cell(record, limits)
        if result["cell_id"] in seen:
            raise ValueError(
                "duplicate cell id %r on coupon %s" % (result["cell_id"], coupon_id)
            )
        seen.add(result["cell_id"])
        screened.append(result)

    inspected = len(screened)
    findings = []
    dispositions = [result["verdict"] for result in screened] or [ACCEPT]
    affected_cells = dict((kind, 0) for kind in CELL_DEFECT_KINDS)
    occurrences = dict((kind, 0) for kind in CELL_DEFECT_KINDS)
    for result in screened:
        for kind in CELL_DEFECT_KINDS:
            count = result["counts"][kind]
            occurrences[kind] += count
            if count > 0:
                affected_cells[kind] += 1
        for finding in result["findings"]:
            findings.append("%s %s" % (result["cell_id"], finding))

    fractions = {}
    kinds_over_coupon_allowance = []
    factor = limits["review_margin_factor"]
    for kind in CELL_DEFECT_KINDS:
        if inspected == 0:
            fractions[kind] = 0.0
            continue
        fraction = affected_cells[kind] / float(inspected)
        fractions[kind] = fraction
        allowed_cells = limits["affected_cell_fraction"][kind] * inspected
        if _at_most(affected_cells[kind], allowed_cells):
            continue
        kinds_over_coupon_allowance.append(kind)
        if limits["affected_cell_fraction"][kind] == 0.0:
            dispositions.append(REJECT)
            findings.append(
                "%d of %d cells carry a %s; the coupon allows none"
                % (affected_cells[kind], inspected, kind)
            )
        elif _at_most(affected_cells[kind], allowed_cells * factor):
            dispositions.append(REFER)
            findings.append(
                "%d of %d cells carry a %s, past the %.2f cells the coupon "
                "allowance permits" % (affected_cells[kind], inspected, kind, allowed_cells)
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "%d of %d cells carry a %s, past the review margin of %.2f "
                "cells" % (affected_cells[kind], inspected, kind, allowed_cells * factor)
            )

    cells_with_any = sum(1 for result in screened if result["defect_total"] > 0)
    affected_fraction = cells_with_any / float(inspected) if inspected else 0.0
    if inspected and not _at_most(
        cells_with_any, limits["max_affected_cell_fraction"] * inspected
    ):
        dispositions.append(REFER)
        findings.append(
            "%d of %d cells carry at least one defect, past the %.2f allowed "
            "across all kinds"
            % (
                cells_with_any,
                inspected,
                limits["max_affected_cell_fraction"] * inspected,
            )
        )

    verdict = _worst(dispositions)
    missing = declared - inspected
    complete = missing == 0
    if not complete:
        verdict = INSPECTION_INCOMPLETE
        findings.append(
            "%d of %d cells carry no inspection record; a quantity limit read "
            "off a short set understates every count" % (missing, declared)
        )

    counts = dict((state, 0) for state in CELL_DISPOSITIONS)
    for result in screened:
        counts[result["verdict"]] += 1

    return {
        "coupon_id": coupon_id,
        "verdict": verdict,
        "inspection_complete": complete,
        "missing_record_count": missing,
        "inspected_cell_count": inspected,
        "disposition_counts": counts,
        "defect_occurrences": occurrences,
        "affected_cell_counts": affected_cells,
        "affected_cell_fractions": fractions,
        "affected_any_fraction": affected_fraction,
        "kinds_over_coupon_allowance": kinds_over_coupon_allowance,
        "not_accepted_ids": [
            result["cell_id"] for result in screened if result["verdict"] != ACCEPT
        ],
        "cells": screened,
        "findings": findings,
    }
