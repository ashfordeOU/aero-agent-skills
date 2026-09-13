#!/usr/bin/env python3
"""Visual inspection of every coverglass on a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause is a per-item screen: each coverglass fitted to the assembly
is checked against the defect criteria agreed for that assembly, and
the assembly is not closed until every coverglass carries a record.
Two things are decided per coverglass: whether it still covers the
active cell area it was fitted to protect, and whether each observed
defect is inside the criteria.

Defect kinds
    edge-chip             glass lost from an edge, working inward
    surface-scratch       a score line across a face
    cavity-or-inclusion   a bubble or a foreign particle in the glass
    coating-blemish       a flaw in the coating rather than the glass
    crack                 a separation running through the glass
    surface-contamination deposit on a surface, removable or not

Dispositions are accept, clean-and-reinspect, refer-for-review and
reject. The criteria below are a declared assembly criteria set, not a
physical constant; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

COVERGLASS_DEFECT_KINDS = (
    "edge-chip",
    "surface-scratch",
    "cavity-or-inclusion",
    "coating-blemish",
    "crack",
    "surface-contamination",
)

ACCEPT = "accept"
CLEAN = "clean-and-reinspect"
REFER = "refer-for-review"
REJECT = "reject"
COVERGLASS_DISPOSITIONS = (ACCEPT, CLEAN, REFER, REJECT)

INSPECTION_INCOMPLETE = "inspection-incomplete"

_SEVERITY_ORDER = {ACCEPT: 0, CLEAN: 1, REFER: 2, REJECT: 3}

REQUIRED_DEFECT_FIELDS = {
    "edge-chip": ("inward_extent_mm",),
    "surface-scratch": ("length_mm", "width_mm"),
    "cavity-or-inclusion": ("max_dimension_mm",),
    "coating-blemish": (),
    "crack": (),
    "surface-contamination": ("removable",),
}

DEFAULT_COVERGLASS_CRITERIA = {
    "crack_always_rejects": True,
    "chip_inward_fraction_of_margin": 0.5,
    "max_scratch_length_mm": 3.0,
    "max_scratch_width_mm": 0.05,
    "max_cavity_dimension_mm": 0.5,
    "cavity_review_factor": 2.0,
    "max_blemish_area_mm2": 2.0,
    "blemish_review_factor": 3.0,
    "cumulative_defect_area_fraction": 0.01,
    "max_exposed_active_area_fraction": 0.005,
    "max_accepted_defects_per_coverglass": 4,
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


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A limit is a product of a criteria value and a measured margin or
    area, so a measurement sitting exactly on the limit can evaluate a
    few units in the last place above it. The limit is never raised;
    only the comparison tolerates the representation error.
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


def validate_coverglass_criteria(criteria):
    """Check a coverglass criteria set is complete and self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    positive_keys = (
        "max_scratch_length_mm",
        "max_scratch_width_mm",
        "max_cavity_dimension_mm",
        "max_blemish_area_mm2",
        "cumulative_defect_area_fraction",
    )
    for key in positive_keys:
        _require_positive("criteria %s" % key, criteria.get(key))
    for key in ("cavity_review_factor", "blemish_review_factor"):
        factor = _require_positive("criteria %s" % key, criteria.get(key))
        if factor < 1.0:
            raise ValueError("criteria %s must be at least one, got %r" % (key, factor))
    fraction = _require_positive(
        "criteria chip_inward_fraction_of_margin",
        criteria.get("chip_inward_fraction_of_margin"),
    )
    if fraction > 1.0:
        raise ValueError(
            "criteria chip_inward_fraction_of_margin must not exceed one; a chip "
            "cannot be allowed past the coverglass overhang"
        )
    _require_non_negative(
        "criteria max_exposed_active_area_fraction",
        criteria.get("max_exposed_active_area_fraction"),
    )
    allowed = criteria.get("max_accepted_defects_per_coverglass")
    if not isinstance(allowed, int) or isinstance(allowed, bool) or allowed < 0:
        raise ValueError(
            "criteria max_accepted_defects_per_coverglass must be a non-negative "
            "integer, got %r" % (allowed,)
        )
    return criteria


def active_area_coverage(
    cell_length_mm,
    cell_width_mm,
    coverglass_length_mm,
    coverglass_width_mm,
    offset_x_mm=0.0,
    offset_y_mm=0.0,
):
    """Coverage of the active cell area by the coverglass as placed.

    Both rectangles are taken about the cell centre; the offsets move
    the coverglass. The smallest of the four overhangs is the margin an
    edge chip has to work through before it reaches the active area,
    and a negative margin means the glass already stops short.
    """
    cell_length = _require_positive("cell_length_mm", cell_length_mm)
    cell_width = _require_positive("cell_width_mm", cell_width_mm)
    glass_length = _require_positive("coverglass_length_mm", coverglass_length_mm)
    glass_width = _require_positive("coverglass_width_mm", coverglass_width_mm)
    offset_x = _require_number("offset_x_mm", offset_x_mm)
    offset_y = _require_number("offset_y_mm", offset_y_mm)

    half_cell_l = cell_length / 2.0
    half_cell_w = cell_width / 2.0
    half_glass_l = glass_length / 2.0
    half_glass_w = glass_width / 2.0

    overlap_l = min(half_cell_l, offset_x + half_glass_l) - max(
        -half_cell_l, offset_x - half_glass_l
    )
    overlap_w = min(half_cell_w, offset_y + half_glass_w) - max(
        -half_cell_w, offset_y - half_glass_w
    )
    overlap_l = max(overlap_l, 0.0)
    overlap_w = max(overlap_w, 0.0)

    active_area = cell_length * cell_width
    covered = overlap_l * overlap_w
    exposed = max(active_area - covered, 0.0)
    margins = (
        half_glass_l - half_cell_l - offset_x,
        half_glass_l - half_cell_l + offset_x,
        half_glass_w - half_cell_w - offset_y,
        half_glass_w - half_cell_w + offset_y,
    )
    return {
        "active_area_mm2": active_area,
        "coverglass_area_mm2": glass_length * glass_width,
        "covered_area_mm2": covered,
        "exposed_area_mm2": exposed,
        "exposed_fraction": exposed / active_area,
        "edge_margin_mm": min(margins),
        "margins_mm": margins,
    }


def assess_defect(defect, edge_margin_mm, criteria=DEFAULT_COVERGLASS_CRITERIA):
    """Disposition one coverglass defect against the criteria set."""
    validate_coverglass_criteria(criteria)
    if not isinstance(defect, dict):
        raise ValueError("defect must be a mapping, got %r" % (defect,))
    kind = _require_choice("kind", defect.get("kind"), COVERGLASS_DEFECT_KINDS)
    margin = _require_number("edge_margin_mm", edge_margin_mm)
    area = _require_non_negative("area_mm2", defect.get("area_mm2"))
    for field in REQUIRED_DEFECT_FIELDS[kind]:
        if defect.get(field) is None:
            raise ValueError("a %s defect needs %s" % (kind, field))

    reasons = []
    counts_toward_area = True

    if kind == "crack":
        disposition = REJECT if criteria.get("crack_always_rejects", True) else REFER
        reasons.append(
            "a crack runs through the glass and will grow under thermal cycling"
        )
    elif kind == "edge-chip":
        inward = _require_positive("inward_extent_mm", defect.get("inward_extent_mm"))
        allowed = margin * criteria["chip_inward_fraction_of_margin"]
        if margin <= 0.0:
            disposition = REJECT
            reasons.append(
                "the coverglass has no overhang left at this edge, so any chip "
                "opens the active area"
            )
        elif _at_most(inward, allowed):
            disposition = ACCEPT
        elif _at_most(inward, margin):
            disposition = REFER
            reasons.append(
                "chip reaches %.3f mm into a %.3f mm overhang, past the %.3f mm "
                "allowance" % (inward, margin, allowed)
            )
        else:
            disposition = REJECT
            reasons.append(
                "chip reaches %.3f mm, past the %.3f mm overhang and into the "
                "active area" % (inward, margin)
            )
    elif kind == "surface-scratch":
        length = _require_positive("length_mm", defect.get("length_mm"))
        width = _require_positive("width_mm", defect.get("width_mm"))
        if not _at_most(width, criteria["max_scratch_width_mm"]):
            disposition = REJECT
            reasons.append(
                "scratch width %.4f mm exceeds the %.4f mm limit; a wide score "
                "line is a stress raiser, not a cosmetic mark"
                % (width, criteria["max_scratch_width_mm"])
            )
        elif not _at_most(length, criteria["max_scratch_length_mm"]):
            disposition = REFER
            reasons.append(
                "scratch length %.3f mm exceeds the %.3f mm limit"
                % (length, criteria["max_scratch_length_mm"])
            )
        else:
            disposition = ACCEPT
    elif kind == "cavity-or-inclusion":
        dimension = _require_positive(
            "max_dimension_mm", defect.get("max_dimension_mm")
        )
        limit = criteria["max_cavity_dimension_mm"]
        review_limit = limit * criteria["cavity_review_factor"]
        if _at_most(dimension, limit):
            disposition = ACCEPT
        elif _at_most(dimension, review_limit):
            disposition = REFER
            reasons.append(
                "inclusion %.3f mm across exceeds the %.3f mm limit"
                % (dimension, limit)
            )
        else:
            disposition = REJECT
            reasons.append(
                "inclusion %.3f mm across exceeds the %.3f mm review limit"
                % (dimension, review_limit)
            )
    elif kind == "coating-blemish":
        limit = criteria["max_blemish_area_mm2"]
        review_limit = limit * criteria["blemish_review_factor"]
        if _at_most(area, limit):
            disposition = ACCEPT
        elif _at_most(area, review_limit):
            disposition = REFER
            reasons.append(
                "blemish area %.3f mm2 exceeds the %.3f mm2 limit" % (area, limit)
            )
        else:
            disposition = REJECT
            reasons.append(
                "blemish area %.3f mm2 exceeds the %.3f mm2 review limit"
                % (area, review_limit)
            )
    else:  # surface-contamination
        removable = defect.get("removable")
        if not isinstance(removable, bool):
            raise ValueError(
                "a surface-contamination defect needs removable as a boolean, got %r"
                % (removable,)
            )
        counts_toward_area = not removable
        if removable:
            disposition = CLEAN
            reasons.append(
                "deposit is removable; clean and inspect the coverglass again "
                "before it counts as accepted"
            )
        else:
            disposition = REFER
            reasons.append(
                "deposit is not removable and stays in the optical path"
            )

    return {
        "id": defect.get("id"),
        "kind": kind,
        "area_mm2": area,
        "counted_area_mm2": area if counts_toward_area else 0.0,
        "disposition": disposition,
        "reasons": reasons,
    }


def inspect_coverglass(record, criteria=DEFAULT_COVERGLASS_CRITERIA):
    """Screen one coverglass: coverage geometry plus every defect."""
    validate_coverglass_criteria(criteria)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    coverglass_id = record.get("coverglass_id")
    if not isinstance(coverglass_id, str) or not coverglass_id.strip():
        raise ValueError("each coverglass record needs a non-empty coverglass_id")
    coverage = active_area_coverage(
        record.get("cell_length_mm"),
        record.get("cell_width_mm"),
        record.get("coverglass_length_mm"),
        record.get("coverglass_width_mm"),
        record.get("offset_x_mm", 0.0),
        record.get("offset_y_mm", 0.0),
    )
    defects = record.get("defects", [])
    if not isinstance(defects, (list, tuple)):
        raise ValueError("defects must be a list, got %r" % (defects,))

    seen = set()
    assessed = []
    for defect in defects:
        result = assess_defect(defect, coverage["edge_margin_mm"], criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate defect id %r on coverglass %s"
                    % (marker, coverglass_id)
                )
            seen.add(marker)
        assessed.append(result)

    counted_area = sum(result["counted_area_mm2"] for result in assessed)
    if not _at_most(counted_area, coverage["coverglass_area_mm2"]):
        raise ValueError(
            "defect area %.3f mm2 exceeds the coverglass area %.3f mm2 on %s"
            % (counted_area, coverage["coverglass_area_mm2"], coverglass_id)
        )
    area_fraction = counted_area / coverage["coverglass_area_mm2"]

    findings = []
    verdict = _worst([result["disposition"] for result in assessed])
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))

    if not _at_most(
        coverage["exposed_fraction"], criteria["max_exposed_active_area_fraction"]
    ):
        verdict = REJECT
        findings.append(
            "%.4f of the active cell area is left uncovered, past the %.4f "
            "allowance; the glass is not protecting the cell it was fitted to"
            % (
                coverage["exposed_fraction"],
                criteria["max_exposed_active_area_fraction"],
            )
        )
    if not _at_most(area_fraction, criteria["cumulative_defect_area_fraction"]):
        verdict = _worst((verdict, REFER))
        findings.append(
            "cumulative defect area fraction %.4f exceeds the %.4f limit even "
            "though no single defect did"
            % (area_fraction, criteria["cumulative_defect_area_fraction"])
        )
    accepted_defects = sum(
        1 for result in assessed if result["disposition"] == ACCEPT
    )
    if accepted_defects > criteria["max_accepted_defects_per_coverglass"]:
        verdict = _worst((verdict, REFER))
        findings.append(
            "%d accepted defects exceed the %d allowed on one coverglass"
            % (accepted_defects, criteria["max_accepted_defects_per_coverglass"])
        )
    return {
        "coverglass_id": coverglass_id,
        "verdict": verdict,
        "defects": assessed,
        "accepted_defect_count": accepted_defects,
        "defect_area_fraction": area_fraction,
        "exposed_active_fraction": coverage["exposed_fraction"],
        "edge_margin_mm": coverage["edge_margin_mm"],
        "findings": findings,
    }


def inspect_coverglass_set(assembly, criteria=DEFAULT_COVERGLASS_CRITERIA):
    """Clause 5.5.3.2.6 screen over every coverglass on the assembly."""
    validate_coverglass_criteria(criteria)
    if not isinstance(assembly, dict):
        raise ValueError("assembly must be a mapping, got %r" % (assembly,))
    assembly_id = assembly.get("assembly_id")
    if not isinstance(assembly_id, str) or not assembly_id.strip():
        raise ValueError("assembly needs a non-empty assembly_id")
    declared = assembly.get("declared_coverglass_count")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
        raise ValueError(
            "declared_coverglass_count must be a positive integer, got %r"
            % (declared,)
        )
    records = assembly.get("coverglasses")
    if not isinstance(records, (list, tuple)):
        raise ValueError("coverglasses must be a list, got %r" % (records,))
    if len(records) > declared:
        raise ValueError(
            "%d coverglass records against a declared count of %d on %s"
            % (len(records), declared, assembly_id)
        )

    seen = set()
    screened = []
    for record in records:
        result = inspect_coverglass(record, criteria)
        marker = result["coverglass_id"]
        if marker in seen:
            raise ValueError(
                "duplicate coverglass id %r on assembly %s" % (marker, assembly_id)
            )
        seen.add(marker)
        screened.append(result)

    findings = []
    missing = declared - len(screened)
    counts = dict((state, 0) for state in COVERGLASS_DISPOSITIONS)
    for result in screened:
        counts[result["verdict"]] += 1
        for finding in result["findings"]:
            findings.append("%s %s" % (result["coverglass_id"], finding))

    verdict = _worst([result["verdict"] for result in screened])
    complete = missing == 0
    if not complete:
        verdict = INSPECTION_INCOMPLETE
        findings.append(
            "%d of %d coverglasses carry no inspection record; the clause asks "
            "for every one, so the assembly cannot be closed" % (missing, declared)
        )
    return {
        "assembly_id": assembly_id,
        "verdict": verdict,
        "inspection_complete": complete,
        "missing_record_count": missing,
        "screened_count": len(screened),
        "disposition_counts": counts,
        "not_accepted_ids": [
            result["coverglass_id"]
            for result in screened
            if result["verdict"] != ACCEPT
        ],
        "coverglasses": screened,
        "findings": findings,
    }
