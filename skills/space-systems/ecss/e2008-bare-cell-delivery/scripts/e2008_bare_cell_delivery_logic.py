"""Dispatch of ordered bare solar cells with their documentation set.

Anchor: ECSS-E-ST-20-08C clause 7.8. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Two arms have to close before a bare-cell shipment leaves, and grading
one of them is the failure this check exists to catch.

    hardware arm        the cells themselves: each one drawn from a lot,
                        each one carrying a grade, each one either clean,
                        clean only because a concession was accepted, or
                        held
    documentation arm   the data package released for the lot each cell
                        came from. A cell whose lot has no released
                        package is not a cell with late paperwork -- it
                        is a cell nobody downstream can trace

A count that reaches the ordered quantity therefore proves nothing on its
own. The quantity can be made up entirely of cells drawn from a lot whose
package was never released, and a pure counting check will pass it.

Bare cells are ordered by grade, which adds the substitution question an
assembly-level delivery never has to answer. A line asking for a lower
grade can be filled from a higher one when the order permits the upgrade,
because the customer gets more than they paid for; it can never be filled
from a lower grade, because that is a quiet downgrade of the article. So
allocation is ordered: exact grade first, then the nearest permitted
upgrade, so a high grade is not spent on a low line while a high line
goes short.

What is left over is not slack. A shippable cell that no order line wants
is surplus the shipment was never asked for, and it is reported rather
than quietly loaded.

Finally a partial dispatch is a decision, not an accident. The order
declares the fraction of a line below which a partial delivery is refused
outright; a line that clears the floor without being complete still ships,
and is still named as partial.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

__all__ = [
    "CELL_DISPOSITIONS",
    "CONCESSION_STATES",
    "DELIVERY_HELD",
    "DELIVERY_RELEASABLE",
    "FILL_TOLERANCE",
    "GRADE_LADDER",
    "HELD",
    "LINE_COMPLETE",
    "LINE_PARTIAL",
    "LINE_REFUSED",
    "SHIPPABLE",
    "SHIPPABLE_ON_CONCESSION",
    "allocate_cells_to_lines",
    "assess_cell",
    "assess_cells",
    "evaluate_delivery",
    "grade_rank",
    "normalize_grade",
    "released_lot_ids",
    "validate_order",
    "validate_order_line",
]

# Lowest grade first. Rank is the index, so a higher rank is a better
# cell and an upgrade is a move up this ladder.
GRADE_LADDER = ("grade-c", "grade-b", "grade-a")

CONCESSION_STATES = ("accepted", "submitted", "rejected")

SHIPPABLE = "shippable"
SHIPPABLE_ON_CONCESSION = "shippable-on-accepted-concession"
HELD = "held"

CELL_DISPOSITIONS = (SHIPPABLE, SHIPPABLE_ON_CONCESSION, HELD)

LINE_COMPLETE = "line-complete"
LINE_PARTIAL = "line-partial-within-floor"
LINE_REFUSED = "line-below-partial-delivery-floor"

DELIVERY_RELEASABLE = "delivery-releasable"
DELIVERY_HELD = "delivery-held"

# A fill fraction is a ratio of two small integers, but the declared
# floor arrives as a decimal literal. Comparing them without a tolerance
# makes a line that exactly meets its floor pass on one platform and fail
# on another, so the comparison absorbs representation error by name.
FILL_TOLERANCE = 1e-9


def _identifier(value, label):
    """Return a trimmed non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _count(value, label):
    """Return a positive integer count, refusing a bool or a float."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def normalize_grade(grade, label="grade"):
    """Return a recognized bare-cell grade, refusing anything else."""
    if not isinstance(grade, str):
        raise ValueError("%s must be a string, got %r" % (label, grade))
    cleaned = grade.strip().lower()
    if cleaned not in GRADE_LADDER:
        raise ValueError(
            "unrecognized %s %r; recognized: %s"
            % (label, grade, ", ".join(GRADE_LADDER))
        )
    return cleaned


def grade_rank(grade):
    """Return the ladder position of a grade; higher is better."""
    return GRADE_LADDER.index(normalize_grade(grade))


def validate_order_line(line, label="order line"):
    """Return one validated order line."""
    if not isinstance(line, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("line_id", "grade", "ordered_count"):
        if key not in line:
            raise ValueError("%s missing required key '%s'" % (label, key))
    allow = line.get("allow_upgrade_substitution", False)
    if not isinstance(allow, bool):
        raise ValueError(
            "%s allow_upgrade_substitution must be a boolean, got %r" % (label, allow)
        )
    return {
        "line_id": _identifier(line["line_id"], "%s line_id" % label),
        "grade": normalize_grade(line["grade"], "%s grade" % label),
        "ordered_count": _count(line["ordered_count"], "%s ordered_count" % label),
        "allow_upgrade_substitution": allow,
    }


def validate_order(order):
    """Return the validated order, with its partial-delivery floor."""
    if not isinstance(order, dict):
        raise ValueError("order must be a mapping")
    for key in ("order_id", "lines", "partial_delivery_floor"):
        if key not in order:
            raise ValueError("order missing required key '%s'" % key)
    floor = order["partial_delivery_floor"]
    if isinstance(floor, bool) or not isinstance(floor, (int, float)):
        raise ValueError("partial_delivery_floor must be a number, got %r" % (floor,))
    floor = float(floor)
    if not 0.0 <= floor <= 1.0:
        raise ValueError(
            "partial_delivery_floor must lie between 0 and 1, got %r" % (floor,)
        )
    lines = order["lines"]
    if not isinstance(lines, (list, tuple)) or not lines:
        raise ValueError("order must carry at least one line")
    validated = []
    seen = set()
    for index, line in enumerate(lines):
        entry = validate_order_line(line, "order line[%d]" % index)
        if entry["line_id"] in seen:
            raise ValueError("order line %s appears twice" % entry["line_id"])
        seen.add(entry["line_id"])
        validated.append(entry)
    return {
        "order_id": _identifier(order["order_id"], "order_id"),
        "lines": tuple(validated),
        "partial_delivery_floor": floor,
    }


def released_lot_ids(lot_packages):
    """Return the lots whose clause 7.7 data package is released.

    A lot that is present but not released is not a released lot; the
    documentation arm turns on the state, not on the entry existing.
    """
    if not isinstance(lot_packages, (list, tuple)):
        raise ValueError("lot_packages must be a sequence of lot package mappings")
    released = []
    seen = set()
    for index, package in enumerate(lot_packages):
        if not isinstance(package, dict):
            raise ValueError("lot_packages[%d] must be a mapping" % index)
        for key in ("lot_id", "package_released"):
            if key not in package:
                raise ValueError("lot_packages[%d] missing key '%s'" % (index, key))
        lot_id = _identifier(package["lot_id"], "lot_packages[%d] lot_id" % index)
        if lot_id in seen:
            raise ValueError("lot %s has two package entries" % lot_id)
        seen.add(lot_id)
        state = package["package_released"]
        if not isinstance(state, bool):
            raise ValueError(
                "lot %s package_released must be a boolean, got %r" % (lot_id, state)
            )
        if state:
            released.append(lot_id)
    return tuple(released)


def _concession(value, label):
    """Return a validated concession, or None when none is offered."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping or None" % label)
    for key in ("reference", "state"):
        if key not in value:
            raise ValueError("%s missing key '%s'" % (label, key))
    state = value["state"]
    if not isinstance(state, str) or state.strip().lower() not in CONCESSION_STATES:
        raise ValueError(
            "%s state must be one of %s, got %r"
            % (label, ", ".join(CONCESSION_STATES), state)
        )
    return {
        "reference": _identifier(value["reference"], "%s reference" % label),
        "state": state.strip().lower(),
    }


def assess_cell(cell, released_lots):
    """Disposition one bare cell against both arms of the dispatch."""
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping")
    for key in ("cell_id", "lot_id", "grade", "nonconformance_open"):
        if key not in cell:
            raise ValueError("cell missing required key '%s'" % key)
    cell_id = _identifier(cell["cell_id"], "cell_id")
    lot_id = _identifier(cell["lot_id"], "lot_id")
    grade = normalize_grade(cell["grade"], "cell %s grade" % cell_id)
    open_ncr = cell["nonconformance_open"]
    if not isinstance(open_ncr, bool):
        raise ValueError(
            "cell %s nonconformance_open must be a boolean, got %r"
            % (cell_id, open_ncr)
        )
    concession = _concession(
        cell.get("concession"), "cell %s concession" % cell_id
    )

    reasons = []
    documented = lot_id in tuple(released_lots)
    if not documented:
        reasons.append(
            "cell %s comes from lot %s, whose data package is not released, so "
            "nothing downstream can trace it" % (cell_id, lot_id)
        )
    on_concession = False
    if open_ncr:
        if concession is None:
            reasons.append(
                "cell %s carries an open nonconformance and no concession" % cell_id
            )
        elif concession["state"] != "accepted":
            reasons.append(
                "cell %s carries an open nonconformance and concession %s is '%s' "
                "rather than accepted"
                % (cell_id, concession["reference"], concession["state"])
            )
        else:
            on_concession = True

    if reasons:
        disposition = HELD
    elif on_concession:
        disposition = SHIPPABLE_ON_CONCESSION
    else:
        disposition = SHIPPABLE

    return {
        "cell_id": cell_id,
        "lot_id": lot_id,
        "grade": grade,
        "grade_rank": GRADE_LADDER.index(grade),
        "documentation_released": documented,
        "concession": concession,
        "disposition": disposition,
        "shippable": disposition != HELD,
        "reasons": tuple(reasons),
    }


def assess_cells(cells, released_lots):
    """Disposition every offered cell, refusing a repeated cell id."""
    if not isinstance(cells, (list, tuple)) or not cells:
        raise ValueError("cells must be a non-empty sequence of offered cells")
    seen = set()
    out = []
    for cell in cells:
        result = assess_cell(cell, released_lots)
        if result["cell_id"] in seen:
            raise ValueError("cell %s is offered twice" % result["cell_id"])
        seen.add(result["cell_id"])
        out.append(result)
    return tuple(out)


def allocate_cells_to_lines(assessed, order):
    """Fill each order line from the shippable cells, exact grade first.

    Exact grade is spent before any upgrade so that a better cell is not
    consumed by a lower line while a higher line goes short. A lower grade
    never fills a higher line: that is a downgrade of the article, not a
    substitution.
    """
    validated = validate_order(order)
    pool = [c for c in assessed if c["shippable"]]
    taken = set()
    lines = []
    for line in validated["lines"]:
        wanted = line["ordered_count"]
        line_rank = GRADE_LADDER.index(line["grade"])
        allocated = []
        candidates = sorted(
            (c for c in pool if c["cell_id"] not in taken),
            key=lambda c: (c["grade_rank"], c["cell_id"]),
        )
        for cell in candidates:
            if len(allocated) >= wanted:
                break
            if cell["grade_rank"] == line_rank:
                allocated.append(cell)
                taken.add(cell["cell_id"])
        if len(allocated) < wanted and line["allow_upgrade_substitution"]:
            for cell in candidates:
                if len(allocated) >= wanted:
                    break
                if cell["cell_id"] in taken:
                    continue
                if cell["grade_rank"] > line_rank:
                    allocated.append(cell)
                    taken.add(cell["cell_id"])
        shipped = len(allocated)
        fill = shipped / float(wanted)
        substituted = tuple(
            c["cell_id"] for c in allocated if c["grade_rank"] > line_rank
        )
        if shipped >= wanted:
            state = LINE_COMPLETE
        elif fill + FILL_TOLERANCE >= validated["partial_delivery_floor"]:
            state = LINE_PARTIAL
        else:
            state = LINE_REFUSED
        lines.append(
            {
                "line_id": line["line_id"],
                "grade": line["grade"],
                "ordered_count": wanted,
                "shipped_count": shipped,
                "short_count": max(0, wanted - shipped),
                "fill_fraction": fill,
                "substituted_cell_ids": substituted,
                "allocated_cell_ids": tuple(c["cell_id"] for c in allocated),
                "state": state,
                "accepted": state != LINE_REFUSED,
            }
        )
    surplus = tuple(c["cell_id"] for c in pool if c["cell_id"] not in taken)
    return {"lines": tuple(lines), "surplus_cell_ids": surplus}


def evaluate_delivery(spec):
    """Run the clause 7.8 dispatch check over one offered shipment.

    spec keys: shipment_id, order, lot_packages, cells.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("shipment_id", "order", "lot_packages", "cells"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    shipment_id = _identifier(spec["shipment_id"], "shipment_id")
    order = validate_order(spec["order"])
    released = released_lot_ids(spec["lot_packages"])
    assessed = assess_cells(spec["cells"], released)
    allocation = allocate_cells_to_lines(assessed, order)

    findings = []
    for cell in assessed:
        findings.extend(cell["reasons"])
    for line in allocation["lines"]:
        if line["state"] == LINE_REFUSED:
            findings.append(
                "order line %s shipped %d of %d ordered cells, below the declared "
                "partial-delivery floor"
                % (line["line_id"], line["shipped_count"], line["ordered_count"])
            )
    for cell_id in allocation["surplus_cell_ids"]:
        findings.append(
            "shipment %s offers cell %s, which no line of order %s asks for"
            % (shipment_id, cell_id, order["order_id"])
        )

    ordered_total = sum(l["ordered_count"] for l in allocation["lines"])
    shipped_total = sum(l["shipped_count"] for l in allocation["lines"])
    return {
        "shipment_id": shipment_id,
        "order_id": order["order_id"],
        "released_lots": released,
        "cells": assessed,
        "lines": allocation["lines"],
        "surplus_cell_ids": allocation["surplus_cell_ids"],
        "held_cell_ids": tuple(c["cell_id"] for c in assessed if not c["shippable"]),
        "concession_cell_ids": tuple(
            c["cell_id"] for c in assessed
            if c["disposition"] == SHIPPABLE_ON_CONCESSION
        ),
        "ordered_total": ordered_total,
        "shipped_total": shipped_total,
        "shipment_fill_fraction": shipped_total / float(ordered_total),
        "partial": shipped_total < ordered_total,
        "findings": findings,
        "verdict": DELIVERY_RELEASABLE if not findings else DELIVERY_HELD,
        "accepted": not findings,
    }
