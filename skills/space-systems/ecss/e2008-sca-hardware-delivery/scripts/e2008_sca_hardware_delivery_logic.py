"""Delivery of ordered solar cell assemblies with their documentation.

Anchor: ECSS-E-ST-20-08C clause 6.7. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The clause joins two things that are usually checked apart: the hardware
that was ordered, and the documentation package the preceding clause
asks for. A shipment is not releasable because the count is right, and it
is not releasable because a package exists. Both arms have to close, and
the join between them is narrower than it looks.

    the count arm         what was ordered against what is actually
                          shippable, per order line, short AND over --
                          a line that ships more than it sold is a
                          reconciliation defect, not generosity
    the paperwork arm     the package is released, and every lot the
                          shipment draws from is a lot that package
                          covers

The join is the second half of the paperwork arm. A released package
covers the lots it was written for; a unit drawn from a lot outside that
list ships with paperwork that does not describe it, which a check on the
package alone cannot see -- the package is fine, the unit is fine, and
the pairing is wrong.

Conformance sits under the count. A nonconforming unit is not shippable;
one carrying an accepted concession is, and it is counted separately so
the release is never silently made of concessions.

Short shipments are a policy question, not an arithmetic one. A project
that permits partial delivery still sets a floor under it, and a line
falling below that floor is held rather than sent with a backorder note.
The floor is inclusive: a line landing exactly on it releases, so the
comparison absorbs representation error instead of the floor being
nudged to make the arithmetic tidy.

The policy numbers below are declared project policy, not physical
constants; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "CONFORMANCE_STATES",
    "DEFAULT_DELIVERY_POLICY",
    "DELIVERY_HELD",
    "DELIVERY_RELEASABLE",
    "LINE_HELD",
    "LINE_RELEASABLE",
    "LINE_RELEASABLE_PARTIAL",
    "UNIT_HELD_LOT_UNCOVERED",
    "UNIT_HELD_NONCONFORMING",
    "UNIT_SHIPPABLE",
    "UNIT_SHIPPABLE_ON_CONCESSION",
    "assess_hardware_delivery",
    "assess_shipment_unit",
    "normalize_conformance",
    "reconcile_order_line",
    "validate_delivery_policy",
    "validate_documentation_release",
    "validate_order_line",
]

CONFORMANCE_STATES = (
    "conforming",
    "nonconforming-with-accepted-concession",
    "nonconforming",
)

UNIT_SHIPPABLE = "unit-shippable"
UNIT_SHIPPABLE_ON_CONCESSION = "unit-shippable-on-concession"
UNIT_HELD_NONCONFORMING = "unit-held-nonconforming"
UNIT_HELD_LOT_UNCOVERED = "unit-held-lot-uncovered"

LINE_RELEASABLE = "line-releasable"
LINE_RELEASABLE_PARTIAL = "line-releasable-partial"
LINE_HELD = "line-held"

DELIVERY_RELEASABLE = "delivery-releasable"
DELIVERY_HELD = "delivery-held"

DEFAULT_DELIVERY_POLICY = {
    "allow_partial_shipment": True,
    "minimum_release_fraction": 0.75,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _identifier(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %d" % (name, value))
    return value


def _require_fraction(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return float(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A release share is a quotient of two counts and the floor is a
    declared fraction, so a line sitting exactly on the floor can land a
    few units in the last place under it. The floor is never lowered;
    only the comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_delivery_policy(policy):
    """Return the release policy with both of its settings stated."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    unknown = sorted(set(policy) - set(DEFAULT_DELIVERY_POLICY))
    if unknown:
        raise ValueError("unrecognized policy key(s): %s" % ", ".join(unknown))
    for key in DEFAULT_DELIVERY_POLICY:
        if key not in policy:
            raise ValueError(
                "policy missing '%s'; an unstated release rule is not a default "
                "release rule" % key
            )
    allow = policy["allow_partial_shipment"]
    if not isinstance(allow, bool):
        raise ValueError(
            "allow_partial_shipment must be a boolean, got %r" % (allow,)
        )
    return {
        "allow_partial_shipment": allow,
        "minimum_release_fraction": _require_fraction(
            "minimum_release_fraction", policy["minimum_release_fraction"]
        ),
    }


def normalize_conformance(state):
    """Return a recognized conformance state, refusing anything else."""
    if not isinstance(state, str):
        raise ValueError("conformance must be a string, got %r" % (state,))
    cleaned = state.strip().lower()
    if cleaned not in CONFORMANCE_STATES:
        raise ValueError(
            "unrecognized conformance %r; recognized: %s"
            % (state, ", ".join(CONFORMANCE_STATES))
        )
    return cleaned


def validate_documentation_release(documentation):
    """Grade the clause 6.6 package this shipment is meant to travel with."""
    if not isinstance(documentation, dict):
        raise ValueError("documentation must be a mapping")
    for key in ("package_reference", "released", "covered_lots"):
        if key not in documentation:
            raise ValueError("documentation missing required key '%s'" % key)
    reference = _identifier(documentation["package_reference"], "package_reference")
    released = documentation["released"]
    if not isinstance(released, bool):
        raise ValueError("documentation released must be a boolean, got %r" % (released,))
    raw_lots = documentation["covered_lots"]
    if not isinstance(raw_lots, (list, tuple)):
        raise ValueError("covered_lots must be a sequence of lot ids")
    covered = []
    for index, lot in enumerate(raw_lots):
        cleaned = _identifier(lot, "covered_lots[%d]" % index)
        if cleaned in covered:
            raise ValueError("lot %s is covered twice by package %s" % (cleaned, reference))
        covered.append(cleaned)

    findings = []
    if not released:
        findings.append(
            "documentation package %s is not released, so nothing may ship "
            "against it" % reference
        )
    if not covered:
        findings.append(
            "documentation package %s covers no lot, so no unit in the shipment "
            "can be matched to it" % reference
        )
    return {
        "package_reference": reference,
        "released": released,
        "covered_lots": tuple(covered),
        "findings": findings,
        "usable": released and bool(covered),
    }


def assess_shipment_unit(unit, covered_lots):
    """Disposition one cell assembly offered for shipment."""
    if not isinstance(unit, dict):
        raise ValueError("unit must be a mapping")
    for key in ("unit_id", "line_id", "lot_id", "conformance"):
        if key not in unit:
            raise ValueError("unit missing required key '%s'" % key)
    if not isinstance(covered_lots, (list, tuple, set, frozenset)):
        raise ValueError("covered_lots must be a collection of lot ids")
    covered = set(covered_lots)
    record = {
        "unit_id": _identifier(unit["unit_id"], "unit_id"),
        "line_id": _identifier(unit["line_id"], "line_id"),
        "lot_id": _identifier(unit["lot_id"], "lot_id"),
        "conformance": normalize_conformance(unit["conformance"]),
        "findings": [],
    }
    if record["lot_id"] not in covered:
        record["disposition"] = UNIT_HELD_LOT_UNCOVERED
        record["shippable"] = False
        record["findings"].append(
            "unit %s comes from lot %s, which the documentation package does "
            "not cover; the paperwork travelling with it does not describe it"
            % (record["unit_id"], record["lot_id"])
        )
        return record
    if record["conformance"] == "conforming":
        record["disposition"] = UNIT_SHIPPABLE
        record["shippable"] = True
    elif record["conformance"] == "nonconforming-with-accepted-concession":
        record["disposition"] = UNIT_SHIPPABLE_ON_CONCESSION
        record["shippable"] = True
        record["findings"].append(
            "unit %s ships on an accepted concession rather than as conforming"
            % record["unit_id"]
        )
    else:
        record["disposition"] = UNIT_HELD_NONCONFORMING
        record["shippable"] = False
        record["findings"].append(
            "unit %s is nonconforming with no accepted concession and is held"
            % record["unit_id"]
        )
    return record


def validate_order_line(line):
    """Return one order line as a validated entry."""
    if not isinstance(line, dict):
        raise ValueError("order line must be a mapping")
    for key in ("line_id", "assembly_type", "ordered_quantity"):
        if key not in line:
            raise ValueError("order line missing required key '%s'" % key)
    return {
        "line_id": _identifier(line["line_id"], "line_id"),
        "assembly_type": _identifier(line["assembly_type"], "assembly_type"),
        "ordered_quantity": _require_count(
            "ordered_quantity", line["ordered_quantity"]
        ),
    }


def reconcile_order_line(line, unit_records, policy=None):
    """Match one order line's ordered count against what may actually ship."""
    entry = validate_order_line(line)
    resolved = validate_delivery_policy(
        DEFAULT_DELIVERY_POLICY if policy is None else policy
    )
    mine = [r for r in unit_records if r["line_id"] == entry["line_id"]]
    shippable = [r for r in mine if r["shippable"]]
    on_concession = [
        r for r in shippable if r["disposition"] == UNIT_SHIPPABLE_ON_CONCESSION
    ]
    ordered = entry["ordered_quantity"]
    count = len(shippable)
    share = float(count) / float(ordered)

    findings = []
    if count > ordered:
        verdict = LINE_HELD
        findings.append(
            "line %s has %d shippable unit(s) against an ordered %d; an over "
            "shipment is a reconciliation defect, not a surplus"
            % (entry["line_id"], count, ordered)
        )
    elif count == ordered:
        verdict = LINE_RELEASABLE
    elif not resolved["allow_partial_shipment"]:
        verdict = LINE_HELD
        findings.append(
            "line %s can ship %d of %d and the order does not permit a partial "
            "delivery" % (entry["line_id"], count, ordered)
        )
    elif _at_least(share, resolved["minimum_release_fraction"]):
        verdict = LINE_RELEASABLE_PARTIAL
        findings.append(
            "line %s ships %d of %d as a permitted partial delivery; %d unit(s) "
            "remain on backorder"
            % (entry["line_id"], count, ordered, ordered - count)
        )
    else:
        verdict = LINE_HELD
        findings.append(
            "line %s can ship %d of %d, below the %.4g release floor this order "
            "sets" % (entry["line_id"], count, ordered,
                      resolved["minimum_release_fraction"])
        )

    return {
        "line_id": entry["line_id"],
        "assembly_type": entry["assembly_type"],
        "ordered_quantity": ordered,
        "offered_quantity": len(mine),
        "shippable_quantity": count,
        "concession_quantity": len(on_concession),
        "shortfall": max(ordered - count, 0),
        "overage": max(count - ordered, 0),
        "release_share": share,
        "verdict": verdict,
        "releasable": verdict in (LINE_RELEASABLE, LINE_RELEASABLE_PARTIAL),
        "findings": findings,
    }


def assess_hardware_delivery(case, policy=None):
    """Run the full clause 6.7 release check of one cell assembly shipment.

    case keys: delivery_id, order_lines, units, documentation.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("delivery_id", "order_lines", "units", "documentation"):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)
    delivery_id = _identifier(case["delivery_id"], "delivery_id")
    resolved = validate_delivery_policy(
        DEFAULT_DELIVERY_POLICY if policy is None else policy
    )
    documentation = validate_documentation_release(case["documentation"])

    order_lines = case["order_lines"]
    if not isinstance(order_lines, (list, tuple)) or not order_lines:
        raise ValueError("order_lines must be a non-empty sequence of order lines")
    lines = []
    line_ids = []
    for item in order_lines:
        entry = validate_order_line(item)
        if entry["line_id"] in line_ids:
            raise ValueError("order line %s appears twice" % entry["line_id"])
        line_ids.append(entry["line_id"])
        lines.append(entry)

    units = case["units"]
    if not isinstance(units, (list, tuple)):
        raise ValueError("units must be a sequence of offered units")
    unit_records = []
    unit_ids = set()
    for item in units:
        record = assess_shipment_unit(item, documentation["covered_lots"])
        if record["unit_id"] in unit_ids:
            raise ValueError("unit %s is offered twice" % record["unit_id"])
        unit_ids.add(record["unit_id"])
        if record["line_id"] not in line_ids:
            raise ValueError(
                "unit %s cites line %s, which this order does not contain"
                % (record["unit_id"], record["line_id"])
            )
        unit_records.append(record)

    line_results = [
        reconcile_order_line(line, unit_records, resolved) for line in lines
    ]

    findings = list(documentation["findings"])
    for record in unit_records:
        findings.extend(record["findings"])
    for result in line_results:
        findings.extend(result["findings"])

    uncovered = tuple(
        r["unit_id"]
        for r in unit_records
        if r["disposition"] == UNIT_HELD_LOT_UNCOVERED
    )
    all_lines_releasable = all(r["releasable"] for r in line_results)
    releasable = (
        documentation["usable"] and all_lines_releasable and not uncovered
    )

    return {
        "delivery_id": delivery_id,
        "documentation": documentation,
        "units": tuple(unit_records),
        "lines": tuple(line_results),
        "uncovered_unit_ids": uncovered,
        "shippable_quantity": sum(r["shippable_quantity"] for r in line_results),
        "ordered_quantity": sum(r["ordered_quantity"] for r in line_results),
        "verdict": DELIVERY_RELEASABLE if releasable else DELIVERY_HELD,
        "releasable": releasable,
        "findings": findings,
    }
