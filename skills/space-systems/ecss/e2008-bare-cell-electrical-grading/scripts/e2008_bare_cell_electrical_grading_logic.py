#!/usr/bin/env python3
"""Accepted bare solar cells are placed into performance grades by test current.

Anchor: ECSS-E-ST-20-08C clause 7.3.2.2.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Acceptance decides whether a bare cell may be delivered at all. Grading is
the step after it, and it answers a different question: which cells behave
closely enough alike to sit in the same string. The sorting quantity is the
current measured at the acceptance test condition, and the band ladder the
cells are placed on is the deliverable definition, so the ladder is checked
before any cell is placed on it:

    ladder       does the ladder rise, close and leave no gap between one
                 band and the next, with only the top band left open
    placement    which band holds the measured current of this cell
    boundary     is the cell far enough from the band edge for the placement
                 to mean anything, given the uncertainty of the measurement
    population   how many cells landed in each grade, and how many could not
                 be placed at all

A cell that straddles a band edge is held rather than pushed to one side:
the measurement never resolved which side it was on, and a string built on
an invented placement carries a mismatch loss nobody budgeted for. A cell
below the lowest band is reported separately from one above the highest,
because the first one contradicts the acceptance decision that let it
through and the second one is simply better than the ladder describes.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CELL_GRADED = "cell-graded"
CELL_BELOW_LOWEST_BAND = "cell-below-lowest-band"
CELL_ABOVE_HIGHEST_BAND = "cell-above-highest-band"
CELL_BOUNDARY_AMBIGUOUS = "cell-boundary-ambiguous"

LOT_GRADING_ACCEPTED = "lot-grading-accepted"
LOT_GRADING_OPEN = "lot-grading-open"

DEFAULT_GRADING_POLICY = {
    "current_uncertainty_fraction": 0.01,
    "min_band_width_fraction": 0.005,
    "require_contiguous_bands": True,
    "hold_boundary_ambiguous": True,
    "min_graded_fraction": 0.9,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or _close(value, limit)


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_current(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be a positive current in amperes, got %r" % (name, value))
    return value


def _require_fraction(name, value, minimum=0.0, maximum=1.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if value < minimum or value > maximum:
        raise ValueError(
            "%s must lie between %s and %s, got %r" % (name, minimum, maximum, value)
        )
    return value


def validate_grading_policy(policy):
    """Check a grading policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction(
        "current_uncertainty_fraction", policy.get("current_uncertainty_fraction"), 0.0, 0.5
    )
    _require_fraction(
        "min_band_width_fraction", policy.get("min_band_width_fraction"), 0.0, 1.0
    )
    _require_flag("require_contiguous_bands", policy.get("require_contiguous_bands"))
    _require_flag("hold_boundary_ambiguous", policy.get("hold_boundary_ambiguous"))
    _require_fraction("min_graded_fraction", policy.get("min_graded_fraction"), 0.0, 1.0)
    return policy


def validate_grade_bands(bands, policy=DEFAULT_GRADING_POLICY):
    """Read a grade ladder and refuse one that cannot place a cell.

    Returns the ladder in ascending current order. Only the top band may be
    left open at the high end; every other band closes, and a gap between two
    bands is refused where policy asks for a contiguous ladder because a cell
    landing in the gap would be silently dropped.
    """
    validate_grading_policy(policy)
    if not isinstance(bands, (list, tuple)) or not bands:
        raise ValueError("bands must be a non-empty sequence of mappings")
    read = []
    seen = set()
    for band in bands:
        if not isinstance(band, dict):
            raise ValueError("band must be a mapping, got %r" % (band,))
        grade = _require_text("grade", band.get("grade"))
        if grade in seen:
            raise ValueError("ladder declares grade %s twice" % grade)
        seen.add(grade)
        low = _require_current("min_current_a", band.get("min_current_a"))
        high = band.get("max_current_a")
        if high is not None:
            high = _require_current("max_current_a", high)
            if not high > low:
                raise ValueError(
                    "grade %s closes at or below where it opens (%r to %r)"
                    % (grade, low, high)
                )
            width = (high - low) / low
            if width < float(policy["min_band_width_fraction"]) and not _close(
                width, float(policy["min_band_width_fraction"])
            ):
                raise ValueError(
                    "grade %s is narrower than the ladder allows (%.6f of its lower edge)"
                    % (grade, width)
                )
        read.append({"grade": grade, "min_current_a": low, "max_current_a": high})
    read.sort(key=lambda entry: entry["min_current_a"])
    for index, band in enumerate(read[:-1]):
        if band["max_current_a"] is None:
            raise ValueError(
                "grade %s is left open at the high end but is not the top band"
                % band["grade"]
            )
        nxt = read[index + 1]
        if band["max_current_a"] > nxt["min_current_a"] and not _close(
            band["max_current_a"], nxt["min_current_a"]
        ):
            raise ValueError(
                "grades %s and %s overlap" % (band["grade"], nxt["grade"])
            )
        if policy["require_contiguous_bands"] and not _close(
            band["max_current_a"], nxt["min_current_a"]
        ):
            raise ValueError(
                "the ladder leaves a gap between %s and %s"
                % (band["grade"], nxt["grade"])
            )
    return tuple(read)


def guard_band_half_width(current_a, policy=DEFAULT_GRADING_POLICY):
    """How far from a band edge a measurement has to sit to resolve the side."""
    validate_grading_policy(policy)
    return _require_current("current_a", current_a) * float(
        policy["current_uncertainty_fraction"]
    )


def ladder_boundaries(bands):
    """The interior edges of a ladder, the places a placement can be ambiguous."""
    if not isinstance(bands, (list, tuple)) or not bands:
        raise ValueError("bands must be a non-empty sequence")
    edges = []
    for index, band in enumerate(bands):
        if index:
            edges.append(band["min_current_a"])
        if band["max_current_a"] is not None and index == len(bands) - 1:
            edges.append(band["max_current_a"])
    return tuple(edges)


def read_cell(cell):
    """Read one accepted bare cell and its measured test current."""
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    cell_id = _require_text("cell_id", cell.get("cell_id"))
    accepted = cell.get("accepted")
    if accepted is None:
        accepted = True
    _require_flag("accepted", accepted)
    if not accepted:
        raise ValueError(
            "cell %s was not accepted; grading applies to accepted cells only" % cell_id
        )
    current = _require_current("test_current_a", cell.get("test_current_a"))
    return {"cell_id": cell_id, "test_current_a": current, "accepted": True}


def place_cell(cell, bands, policy=DEFAULT_GRADING_POLICY):
    """Place one accepted cell on the grade ladder, or say why it was held."""
    validate_grading_policy(policy)
    read = read_cell(cell)
    ladder = tuple(bands)
    if not ladder:
        raise ValueError("bands must be a non-empty sequence")
    current = read["test_current_a"]
    guard = guard_band_half_width(current, policy)
    findings = []

    near = []
    if guard > 0.0:
        # A zero guard band means the declared measurement is exact, and an
        # exact measurement always resolves which side of an edge it is on.
        for edge in ladder_boundaries(ladder):
            offset = abs(current - edge)
            if offset < guard or _close(offset, guard):
                near.append(edge)
    if near and policy["hold_boundary_ambiguous"]:
        neighbours = sorted(
            band["grade"]
            for band in ladder
            if any(
                _close(band["min_current_a"], edge)
                or (
                    band["max_current_a"] is not None
                    and _close(band["max_current_a"], edge)
                )
                for edge in near
            )
        )
        findings.append(
            "cell %s sits within the measurement guard band of a grade edge, so the "
            "measurement did not resolve which of %s it belongs to"
            % (read["cell_id"], ", ".join(neighbours))
        )
        return {
            "cell_id": read["cell_id"],
            "test_current_a": current,
            "guard_band_a": guard,
            "grade": None,
            "status": CELL_BOUNDARY_AMBIGUOUS,
            "boundary_candidates": neighbours,
            "findings": findings,
        }

    lowest = ladder[0]
    highest = ladder[-1]
    if current < lowest["min_current_a"] and not _close(
        current, lowest["min_current_a"]
    ):
        findings.append(
            "cell %s measures below the lowest grade, so it was accepted against a "
            "limit the delivery ladder does not reach" % read["cell_id"]
        )
        return {
            "cell_id": read["cell_id"],
            "test_current_a": current,
            "guard_band_a": guard,
            "grade": None,
            "status": CELL_BELOW_LOWEST_BAND,
            "boundary_candidates": [],
            "findings": findings,
        }
    if highest["max_current_a"] is not None and current > highest["max_current_a"]:
        findings.append(
            "cell %s measures above the highest grade the ladder describes"
            % read["cell_id"]
        )
        return {
            "cell_id": read["cell_id"],
            "test_current_a": current,
            "guard_band_a": guard,
            "grade": None,
            "status": CELL_ABOVE_HIGHEST_BAND,
            "boundary_candidates": [],
            "findings": findings,
        }

    placed = None
    for band in ladder:
        above_low = _at_least(current, band["min_current_a"])
        below_high = band["max_current_a"] is None or (
            current < band["max_current_a"] and not _close(current, band["max_current_a"])
        )
        if above_low and below_high:
            placed = band
            break
    if placed is None:
        placed = highest
    return {
        "cell_id": read["cell_id"],
        "test_current_a": current,
        "guard_band_a": guard,
        "grade": placed["grade"],
        "status": CELL_GRADED,
        "boundary_candidates": [],
        "findings": findings,
    }


def grade_populations(records):
    """Group placed cells by the grade they landed in."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence, got %r" % (records,))
    grouped = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("record must be a mapping, got %r" % (record,))
        if record.get("status") != CELL_GRADED:
            continue
        grouped.setdefault(record["grade"], []).append(record["cell_id"])
    return {grade: sorted(ids) for grade, ids in grouped.items()}


def grade_yields(records):
    """The share of the graded population that landed in each grade."""
    grouped = grade_populations(records)
    total = sum(len(ids) for ids in grouped.values())
    if not total:
        return {}
    return {grade: len(ids) / float(total) for grade, ids in grouped.items()}


def assess_bare_cell_grading(case, policy=DEFAULT_GRADING_POLICY):
    """Full clause 7.3.2.2.4 sweep over one lot of accepted bare cells."""
    validate_grading_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    ladder = validate_grade_bands(case.get("bands"), policy)
    cells = case.get("cells")
    if not isinstance(cells, (list, tuple)) or not cells:
        raise ValueError("case cells must be a non-empty sequence of mappings")
    seen = set()
    records = []
    for cell in cells:
        record = place_cell(cell, ladder, policy)
        if record["cell_id"] in seen:
            raise ValueError("case declares cell %s twice" % record["cell_id"])
        seen.add(record["cell_id"])
        records.append(record)
    records.sort(key=lambda entry: entry["cell_id"])

    findings = []
    for record in records:
        findings.extend(record["findings"])
    graded = [r["cell_id"] for r in records if r["status"] == CELL_GRADED]
    held = {
        CELL_BOUNDARY_AMBIGUOUS: sorted(
            r["cell_id"] for r in records if r["status"] == CELL_BOUNDARY_AMBIGUOUS
        ),
        CELL_BELOW_LOWEST_BAND: sorted(
            r["cell_id"] for r in records if r["status"] == CELL_BELOW_LOWEST_BAND
        ),
        CELL_ABOVE_HIGHEST_BAND: sorted(
            r["cell_id"] for r in records if r["status"] == CELL_ABOVE_HIGHEST_BAND
        ),
    }
    total = len(records)
    graded_fraction = len(graded) / float(total)
    minimum = float(policy["min_graded_fraction"])
    yield_ok = _at_least(graded_fraction, minimum)
    if not yield_ok:
        findings.append(
            "the lot placed %d of %d accepted cells against a required share of %.3f"
            % (len(graded), total, minimum)
        )
    below = held[CELL_BELOW_LOWEST_BAND]
    return {
        "verdict": LOT_GRADING_ACCEPTED
        if yield_ok and not below
        else LOT_GRADING_OPEN,
        "cell_records": records,
        "ladder": [dict(band) for band in ladder],
        "grade_populations": grade_populations(records),
        "grade_yields": grade_yields(records),
        "graded_cell_ids": sorted(graded),
        "held_cell_ids": held,
        "graded_fraction": graded_fraction,
        "required_graded_fraction": minimum,
        "graded_fraction_met": yield_ok,
        "findings": findings,
    }
