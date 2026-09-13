#!/usr/bin/env python3
"""Bond integrity inspection across the full cell population of a coupon.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.20. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause is a full-population check: every solar cell bonded onto the
coupon is examined for the integrity of its bond to the substrate, and
the coupon is not closed until every cell carries a record. Two numbers
decide a cell. The first is how much of the bond footprint is still
bonded. The second is where the missing bond sits, because a void in
the middle of the footprint is a lost thermal path while the same area
sitting at a corner is a peel crack waiting for the first thermal
cycle.

Anomaly kinds
    adhesive-void    unbonded area inside the footprint
    edge-disbond     bond missing inward from an edge
    corner-disbond   bond missing at a corner, the peel initiation site
    missing-fillet   adhesive fillet absent along part of the perimeter
    adhesive-bridge  adhesive reaching a neighbouring part
    cell-lift        the cell standing off the substrate

Dispositions are accept, rework-and-reinspect, refer-for-review and
reject. The criteria below are a declared coupon criteria set, not a
physical constant; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

BOND_ANOMALY_KINDS = (
    "adhesive-void",
    "edge-disbond",
    "corner-disbond",
    "missing-fillet",
    "adhesive-bridge",
    "cell-lift",
)

ACCEPT = "accept"
REWORK = "rework-and-reinspect"
REFER = "refer-for-review"
REJECT = "reject"
BOND_DISPOSITIONS = (ACCEPT, REWORK, REFER, REJECT)

POPULATION_INCOMPLETE = "population-incomplete"

_SEVERITY_ORDER = {ACCEPT: 0, REWORK: 1, REFER: 2, REJECT: 3}

REQUIRED_ANOMALY_FIELDS = {
    "adhesive-void": ("area_mm2", "distance_from_corner_mm"),
    "edge-disbond": ("inward_extent_mm", "along_edge_length_mm"),
    "corner-disbond": ("inward_extent_mm",),
    "missing-fillet": ("along_edge_length_mm",),
    "adhesive-bridge": ("removable",),
    "cell-lift": (),
}

DEFAULT_BOND_CRITERIA = {
    "min_bonded_area_fraction": 0.90,
    "max_single_void_area_fraction": 0.02,
    "void_review_factor": 2.0,
    "corner_zone_fraction_of_span": 0.10,
    "corner_peel_weight": 2.5,
    "max_edge_disbond_fraction_of_span": 0.10,
    "edge_disbond_review_factor": 2.0,
    "max_missing_fillet_fraction_of_perimeter": 0.05,
    "cell_lift_always_rejects": True,
    "max_accepted_anomalies_per_cell": 3,
}

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


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    number = _require_positive(name, value)
    if number > 1.0:
        raise ValueError("%s must not exceed one, got %r" % (name, value))
    return number


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    Every limit here is a product of a criteria value and a measured
    span, area or perimeter, so a measurement sitting exactly on the
    limit can evaluate a few units in the last place above it. The
    limit is never raised; only the comparison tolerates the
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


def validate_bond_criteria(criteria):
    """Check a bond criteria set is complete and self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    for key in (
        "min_bonded_area_fraction",
        "max_single_void_area_fraction",
        "corner_zone_fraction_of_span",
        "max_edge_disbond_fraction_of_span",
        "max_missing_fillet_fraction_of_perimeter",
    ):
        _require_fraction("criteria %s" % key, criteria.get(key))
    for key in ("void_review_factor", "edge_disbond_review_factor"):
        factor = _require_positive("criteria %s" % key, criteria.get(key))
        if factor < 1.0:
            raise ValueError(
                "criteria %s must be at least one, got %r" % (key, factor)
            )
    weight = _require_positive(
        "criteria corner_peel_weight", criteria.get("corner_peel_weight")
    )
    if weight < 1.0:
        raise ValueError(
            "criteria corner_peel_weight must be at least one; a corner cannot "
            "be more forgiving than the middle of the footprint"
        )
    allowed = criteria.get("max_accepted_anomalies_per_cell")
    if not isinstance(allowed, int) or isinstance(allowed, bool) or allowed < 0:
        raise ValueError(
            "criteria max_accepted_anomalies_per_cell must be a non-negative "
            "integer, got %r" % (allowed,)
        )
    return criteria


def bond_footprint(cell_length_mm, cell_width_mm, criteria=DEFAULT_BOND_CRITERIA):
    """Geometry of the bond a cell sits on.

    The shortest side is the span an edge disbond has to work through,
    and the corner zone is the distance from a corner inside which a
    missing bond behaves as a peel initiation site rather than as a
    lost thermal path.
    """
    validate_bond_criteria(criteria)
    length = _require_positive("cell_length_mm", cell_length_mm)
    width = _require_positive("cell_width_mm", cell_width_mm)
    min_span = min(length, width)
    return {
        "bond_area_mm2": length * width,
        "perimeter_mm": 2.0 * (length + width),
        "min_span_mm": min_span,
        "corner_zone_mm": min_span * criteria["corner_zone_fraction_of_span"],
    }


def assess_bond_anomaly(anomaly, footprint, criteria=DEFAULT_BOND_CRITERIA):
    """Disposition one bond anomaly against the criteria set."""
    validate_bond_criteria(criteria)
    if not isinstance(anomaly, dict):
        raise ValueError("anomaly must be a mapping, got %r" % (anomaly,))
    if not isinstance(footprint, dict):
        raise ValueError("footprint must be a mapping, got %r" % (footprint,))
    kind = _require_choice("kind", anomaly.get("kind"), BOND_ANOMALY_KINDS)
    bond_area = _require_positive("footprint bond_area_mm2", footprint.get("bond_area_mm2"))
    perimeter = _require_positive("footprint perimeter_mm", footprint.get("perimeter_mm"))
    min_span = _require_positive("footprint min_span_mm", footprint.get("min_span_mm"))
    corner_zone = _require_non_negative(
        "footprint corner_zone_mm", footprint.get("corner_zone_mm")
    )
    for field in REQUIRED_ANOMALY_FIELDS[kind]:
        if anomaly.get(field) is None:
            raise ValueError("a %s anomaly needs %s" % (kind, field))

    reasons = []
    disbonded_area = 0.0
    peel_weight = 1.0

    if kind == "cell-lift":
        disposition = (
            REJECT if criteria.get("cell_lift_always_rejects", True) else REFER
        )
        disbonded_area = bond_area
        peel_weight = criteria["corner_peel_weight"]
        reasons.append(
            "the cell is standing off its substrate, so the bond is carrying no "
            "load and no heat at all"
        )
    elif kind == "adhesive-void":
        area = _require_positive("area_mm2", anomaly.get("area_mm2"))
        distance = _require_non_negative(
            "distance_from_corner_mm", anomaly.get("distance_from_corner_mm")
        )
        disbonded_area = area
        in_corner = _at_most(distance, corner_zone)
        peel_weight = criteria["corner_peel_weight"] if in_corner else 1.0
        weighted = (area / bond_area) * peel_weight
        limit = criteria["max_single_void_area_fraction"]
        review_limit = limit * criteria["void_review_factor"]
        if _at_most(weighted, limit):
            disposition = ACCEPT
        elif _at_most(weighted, review_limit):
            disposition = REFER
            reasons.append(
                "void weighs %.5f of the footprint against the %.5f allowance"
                % (weighted, limit)
            )
        else:
            disposition = REJECT
            reasons.append(
                "void weighs %.5f of the footprint, past the %.5f review limit"
                % (weighted, review_limit)
            )
        if in_corner and disposition != ACCEPT:
            reasons.append(
                "the void sits within %.3f mm of a corner, where a disbond peels "
                "rather than simply blocking a heat path" % (corner_zone,)
            )
    elif kind == "edge-disbond":
        inward = _require_positive("inward_extent_mm", anomaly.get("inward_extent_mm"))
        along = _require_positive(
            "along_edge_length_mm", anomaly.get("along_edge_length_mm")
        )
        disbonded_area = inward * along
        allowed = min_span * criteria["max_edge_disbond_fraction_of_span"]
        review_limit = allowed * criteria["edge_disbond_review_factor"]
        if _at_most(inward, allowed):
            disposition = ACCEPT
        elif _at_most(inward, review_limit):
            disposition = REFER
            reasons.append(
                "disbond reaches %.3f mm inward against the %.3f mm allowance on a "
                "%.3f mm span" % (inward, allowed, min_span)
            )
        else:
            disposition = REJECT
            reasons.append(
                "disbond reaches %.3f mm inward, past the %.3f mm review limit"
                % (inward, review_limit)
            )
    elif kind == "corner-disbond":
        inward = _require_positive("inward_extent_mm", anomaly.get("inward_extent_mm"))
        peel_weight = criteria["corner_peel_weight"]
        disbonded_area = 0.5 * inward * inward
        edge_allowance = min_span * criteria["max_edge_disbond_fraction_of_span"]
        allowed = edge_allowance / peel_weight
        review_limit = allowed * criteria["edge_disbond_review_factor"]
        if _at_most(inward, allowed):
            disposition = ACCEPT
        elif _at_most(inward, review_limit):
            disposition = REFER
            reasons.append(
                "corner disbond reaches %.3f mm against the %.3f mm corner "
                "allowance, which is the edge allowance divided by the peel "
                "weight" % (inward, allowed)
            )
        else:
            disposition = REJECT
            reasons.append(
                "corner disbond reaches %.3f mm, past the %.3f mm review limit at "
                "the worst geometry on the cell" % (inward, review_limit)
            )
    elif kind == "missing-fillet":
        along = _require_positive(
            "along_edge_length_mm", anomaly.get("along_edge_length_mm")
        )
        allowed = perimeter * criteria["max_missing_fillet_fraction_of_perimeter"]
        if _at_most(along, allowed):
            disposition = ACCEPT
        else:
            disposition = REWORK
            reasons.append(
                "fillet missing along %.3f mm of a %.3f mm perimeter, past the "
                "%.3f mm allowance; the fillet can be applied and the cell looked "
                "at again" % (along, perimeter, allowed)
            )
    else:  # adhesive-bridge
        removable = _require_bool("removable", anomaly.get("removable"))
        if removable:
            disposition = REWORK
            reasons.append(
                "the bridge can be trimmed back; do that and inspect the bond "
                "again before it counts as accepted"
            )
        else:
            disposition = REFER
            reasons.append(
                "the bridge cannot be trimmed, so it ties the cell to its "
                "neighbour and both expand against each other under cycling"
            )

    if not _at_most(disbonded_area, bond_area):
        raise ValueError(
            "anomaly %r claims %.3f mm2 of a %.3f mm2 bond footprint"
            % (anomaly.get("id"), disbonded_area, bond_area)
        )
    return {
        "id": anomaly.get("id"),
        "kind": kind,
        "disbonded_area_mm2": disbonded_area,
        "peel_weight": peel_weight,
        "weighted_area_mm2": disbonded_area * peel_weight,
        "disposition": disposition,
        "reasons": reasons,
    }


def inspect_cell_bond(record, criteria=DEFAULT_BOND_CRITERIA):
    """Screen the bond under one cell: every anomaly plus the area rollup."""
    validate_bond_criteria(criteria)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    cell_id = record.get("cell_id")
    if not isinstance(cell_id, str) or not cell_id.strip():
        raise ValueError("each cell record needs a non-empty cell_id")
    footprint = bond_footprint(
        record.get("cell_length_mm"), record.get("cell_width_mm"), criteria
    )
    anomalies = record.get("anomalies", [])
    if not isinstance(anomalies, (list, tuple)):
        raise ValueError("anomalies must be a list, got %r" % (anomalies,))

    seen = set()
    assessed = []
    for anomaly in anomalies:
        result = assess_bond_anomaly(anomaly, footprint, criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate anomaly id %r on cell %s" % (marker, cell_id)
                )
            seen.add(marker)
        assessed.append(result)

    lifted = any(result["kind"] == "cell-lift" for result in assessed)
    if lifted:
        # A cell standing off its substrate has no bond left anywhere, so the
        # other anomalies describe parts of an area that is already gone. They
        # are not added on top of it.
        disbonded = footprint["bond_area_mm2"]
    else:
        disbonded = sum(result["disbonded_area_mm2"] for result in assessed)
        if not _at_most(disbonded, footprint["bond_area_mm2"]):
            raise ValueError(
                "disbonded area %.3f mm2 exceeds the %.3f mm2 footprint on cell %s"
                % (disbonded, footprint["bond_area_mm2"], cell_id)
            )
    bonded_fraction = max(
        (footprint["bond_area_mm2"] - disbonded) / footprint["bond_area_mm2"], 0.0
    )

    findings = []
    verdict = _worst([result["disposition"] for result in assessed])
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))

    minimum = criteria["min_bonded_area_fraction"]
    if bonded_fraction < minimum and not math.isclose(
        bonded_fraction, minimum, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        verdict = REJECT
        findings.append(
            "only %.4f of the bond footprint is still bonded against the %.4f "
            "minimum; the cell has lost its load path whatever each single "
            "anomaly was graded" % (bonded_fraction, minimum)
        )
    accepted = sum(1 for result in assessed if result["disposition"] == ACCEPT)
    if accepted > criteria["max_accepted_anomalies_per_cell"]:
        verdict = _worst((verdict, REFER))
        findings.append(
            "%d accepted anomalies exceed the %d allowed on one bond"
            % (accepted, criteria["max_accepted_anomalies_per_cell"])
        )
    return {
        "cell_id": cell_id,
        "verdict": verdict,
        "anomalies": assessed,
        "accepted_anomaly_count": accepted,
        "disbonded_area_mm2": disbonded,
        "bonded_area_fraction": bonded_fraction,
        "weighted_disbonded_area_mm2": sum(
            result["weighted_area_mm2"] for result in assessed
        ),
        "footprint": footprint,
        "findings": findings,
    }


def inspect_bond_population(coupon, criteria=DEFAULT_BOND_CRITERIA):
    """Clause 5.5.3.2.20 check over every bonded cell on the coupon."""
    validate_bond_criteria(criteria)
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
            "%d cell records against a declared population of %d on %s"
            % (len(records), declared, coupon_id)
        )

    seen = set()
    screened = []
    for record in records:
        result = inspect_cell_bond(record, criteria)
        marker = result["cell_id"]
        if marker in seen:
            raise ValueError("duplicate cell id %r on coupon %s" % (marker, coupon_id))
        seen.add(marker)
        screened.append(result)

    findings = []
    counts = dict((state, 0) for state in BOND_DISPOSITIONS)
    for result in screened:
        counts[result["verdict"]] += 1
        for finding in result["findings"]:
            findings.append("%s %s" % (result["cell_id"], finding))

    missing = declared - len(screened)
    verdict = _worst([result["verdict"] for result in screened])
    complete = missing == 0
    if not complete:
        verdict = POPULATION_INCOMPLETE
        findings.append(
            "%d of %d bonded cells carry no record; the clause asks for the full "
            "population, so the coupon cannot be closed on the ones that were "
            "looked at" % (missing, declared)
        )
    worst_bonded = min(
        (result["bonded_area_fraction"] for result in screened), default=None
    )
    return {
        "coupon_id": coupon_id,
        "verdict": verdict,
        "population_complete": complete,
        "missing_record_count": missing,
        "screened_count": len(screened),
        "disposition_counts": counts,
        "worst_bonded_area_fraction": worst_bonded,
        "not_accepted_ids": [
            result["cell_id"] for result in screened if result["verdict"] != ACCEPT
        ],
        "cells": screened,
        "findings": findings,
    }
