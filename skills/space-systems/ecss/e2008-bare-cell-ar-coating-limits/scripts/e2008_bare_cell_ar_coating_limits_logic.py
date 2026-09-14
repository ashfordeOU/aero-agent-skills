#!/usr/bin/env python3
"""Antireflective coating limits on a bare solar cell.

Anchor: ECSS-E-ST-20-08C clause 7.5.1.4.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The antireflective coating is the reason the cell converts what it does.
Where the coating is missing, the bare semiconductor reflects a large
share of the light that lands on it, so the clause puts a ceiling on how
much of the coatable face may be left uncoated and bounds the individual
flaws that make up that total:

    uncoated patch   a region the coating never reached, usually at the
                     perimeter or under a handling mark
    coating void     a discrete hole, bubble or pinhole in an otherwise
                     coated area
    coating spatter  coating material deposited where it does not belong

The three are not interchangeable. A patch and a void both take coated
area away and both count toward the ceiling; spatter adds material and
takes nothing away, so it is bounded on its own obscuration budget and on
where it landed. Spatter on an interconnect attachment pad is the one
that is never a cosmetic question: an insulating film across a weld or
solder pad is a joint that will not be made.

Position matters for voids too. A void that reaches the cell edge is a
free edge in the coating, and a free edge is where delamination starts
under thermal cycling, so it is dispositioned on where it sits rather
than only on how wide it is.

The area ceiling and the optical arm are kept separate. The ceiling is
geometric and says how much coating is gone; the optical arm converts the
same fraction into the reflectance penalty it actually costs, using the
declared coated and bare reflectances, and a cell can sit inside the
geometric ceiling and still fail the penalty when the reflectance step
for that coating is large.

Dispositions are accept, refer-for-review and reject.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

UNCOATED_PATCH = "uncoated-patch"
COATING_VOID = "coating-void"
COATING_SPATTER = "coating-spatter"
AR_COATING_DEFECT_KINDS = (UNCOATED_PATCH, COATING_VOID, COATING_SPATTER)

ACCEPT = "accept"
REFER = "refer-for-review"
REJECT = "reject"
AR_COATING_DISPOSITIONS = (ACCEPT, REFER, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REFER: 1, REJECT: 2}

COATING_ACCEPTED = "bare-cell-ar-coating-accepted"
COATING_REFERRED = "bare-cell-ar-coating-referred"
COATING_REJECTED = "bare-cell-ar-coating-rejected"

_ROLLUP_BY_SEVERITY = {
    ACCEPT: COATING_ACCEPTED,
    REFER: COATING_REFERRED,
    REJECT: COATING_REJECTED,
}

DEFAULT_AR_COATING_CRITERIA = {
    # how much of the coatable face may be left without coating
    "max_uncoated_area_fraction": 0.01,
    # individual voids and patches
    "max_void_dimension_mm": 0.5,
    "void_review_factor": 2.0,
    "max_patch_area_mm2": 1.0,
    "patch_review_factor": 2.0,
    "edge_void_rejects": True,
    # spatter
    "max_spatter_area_mm2": 0.2,
    "spatter_review_factor": 2.5,
    "max_spatter_area_fraction": 0.002,
    # counts
    "max_voids_per_cell": 6,
    "max_spatter_spots_per_cell": 4,
    # optical arm
    "coated_reflectance": 0.02,
    "uncoated_reflectance": 0.33,
    "max_current_loss_fraction": 0.0025,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12

# A convex flaw of largest dimension d cannot enclose more than (pi/4)d**2.
_ISODIAMETRIC_FACTOR = math.pi / 4.0


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


def _require_fraction(name, value):
    fraction = _require_non_negative(name, value)
    if fraction > 1.0:
        raise ValueError("%s is a fraction and cannot exceed one, got %r" % (name, value))
    return fraction


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    The limits here are products of a criteria share and a measured area,
    so a measurement sitting exactly on one can evaluate a few units in
    the last place above it. The limit is never raised; only the
    comparison tolerates the representation error.
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


def validate_ar_coating_criteria(criteria):
    """Check an antireflective coating criteria set is usable."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    for key in ("max_void_dimension_mm", "max_patch_area_mm2", "max_spatter_area_mm2"):
        _require_positive("criteria %s" % key, criteria.get(key))
    for key in (
        "max_uncoated_area_fraction",
        "max_spatter_area_fraction",
        "max_current_loss_fraction",
    ):
        _require_fraction("criteria %s" % key, criteria.get(key))
    for key in ("void_review_factor", "patch_review_factor", "spatter_review_factor"):
        factor = _require_positive("criteria %s" % key, criteria.get(key))
        if factor < 1.0:
            raise ValueError(
                "criteria %s must be at least one; a review band cannot be "
                "tighter than the accept band, got %r" % (key, factor)
            )
    _require_count("criteria max_voids_per_cell", criteria.get("max_voids_per_cell"))
    _require_count(
        "criteria max_spatter_spots_per_cell",
        criteria.get("max_spatter_spots_per_cell"),
    )
    _require_flag("criteria edge_void_rejects", criteria.get("edge_void_rejects"))
    coated = _require_fraction("criteria coated_reflectance", criteria.get("coated_reflectance"))
    bare = _require_fraction(
        "criteria uncoated_reflectance", criteria.get("uncoated_reflectance")
    )
    if bare <= coated:
        raise ValueError(
            "criteria uncoated_reflectance %r must exceed coated_reflectance %r; "
            "a coating that does not lower reflectance is not antireflective"
            % (bare, coated)
        )
    return criteria


def coatable_area(geometry):
    """The face area the coating is actually expected to cover.

    The contacts are not coated and were never meant to be, so counting
    their footprint as uncoated area charges the coating for metal that is
    doing its own job.
    """
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be a mapping, got %r" % (geometry,))
    length = _require_positive("cell_length_mm", geometry.get("cell_length_mm"))
    width = _require_positive("cell_width_mm", geometry.get("cell_width_mm"))
    contacts = _require_non_negative(
        "contact_area_mm2", geometry.get("contact_area_mm2")
    )
    cell_area = length * width
    if not contacts < cell_area:
        raise ValueError(
            "a contact footprint of %.3f mm2 leaves no coatable face on a "
            "%.3f mm2 cell" % (contacts, cell_area)
        )
    return {
        "cell_length_mm": length,
        "cell_width_mm": width,
        "cell_area_mm2": cell_area,
        "contact_area_mm2": contacts,
        "coatable_area_mm2": cell_area - contacts,
    }


def estimate_current_loss_fraction(
    uncoated_fraction, criteria=DEFAULT_AR_COATING_CRITERIA
):
    """Reflectance penalty the uncoated share costs, as a current fraction.

    Uncoated semiconductor reflects at the bare reflectance instead of the
    coated one. The extra light lost is the uncoated share times the step
    between the two, normalised by the light the coated face keeps.
    """
    validate_ar_coating_criteria(criteria)
    fraction = _require_fraction("uncoated_fraction", uncoated_fraction)
    coated = criteria["coated_reflectance"]
    bare = criteria["uncoated_reflectance"]
    return fraction * (bare - coated) / (1.0 - coated)


def assess_coating_defect(defect, resolved_geometry, criteria=DEFAULT_AR_COATING_CRITERIA):
    """Disposition one coating defect against the criteria set."""
    validate_ar_coating_criteria(criteria)
    if not isinstance(defect, dict):
        raise ValueError("defect must be a mapping, got %r" % (defect,))
    if not isinstance(resolved_geometry, dict):
        raise ValueError("resolved_geometry must be a mapping, got %r" % (resolved_geometry,))
    kind = _require_choice("kind", defect.get("kind"), AR_COATING_DEFECT_KINDS)
    area = _require_positive("area_mm2", defect.get("area_mm2"))
    dimension = _require_positive("max_dimension_mm", defect.get("max_dimension_mm"))
    if not _at_most(area, _ISODIAMETRIC_FACTOR * dimension * dimension):
        raise ValueError(
            "a %s of %.4f mm2 cannot fit inside a largest dimension of %.4f mm; "
            "the two measurements disagree" % (kind, area, dimension)
        )
    if not _at_most(area, resolved_geometry["coatable_area_mm2"]):
        raise ValueError(
            "a %s of %.3f mm2 is larger than the %.3f mm2 coatable face"
            % (kind, area, resolved_geometry["coatable_area_mm2"])
        )

    reasons = []
    dispositions = []
    uncoated_area = 0.0
    spatter_area = 0.0

    if kind == COATING_SPATTER:
        on_pad = defect.get("on_attachment_pad")
        if not isinstance(on_pad, bool):
            raise ValueError(
                "a coating-spatter defect needs on_attachment_pad as a boolean, "
                "got %r" % (on_pad,)
            )
        spatter_area = area
        if on_pad:
            dispositions.append(REJECT)
            reasons.append(
                "spatter sits on an interconnect attachment pad; an insulating "
                "film across the pad is a joint that will not be made"
            )
        else:
            limit = criteria["max_spatter_area_mm2"]
            review_limit = limit * criteria["spatter_review_factor"]
            if _at_most(area, limit):
                dispositions.append(ACCEPT)
            elif _at_most(area, review_limit):
                dispositions.append(REFER)
                reasons.append(
                    "spatter area %.4f mm2 exceeds the %.4f mm2 limit"
                    % (area, limit)
                )
            else:
                dispositions.append(REJECT)
                reasons.append(
                    "spatter area %.4f mm2 exceeds the %.4f mm2 review limit"
                    % (area, review_limit)
                )
    else:
        uncoated_area = area
        touches_edge = defect.get("touches_cell_edge", False)
        if not isinstance(touches_edge, bool):
            raise ValueError(
                "touches_cell_edge must be a boolean, got %r" % (touches_edge,)
            )
        if kind == COATING_VOID:
            limit = criteria["max_void_dimension_mm"]
            review_limit = limit * criteria["void_review_factor"]
            if _at_most(dimension, limit):
                dispositions.append(ACCEPT)
            elif _at_most(dimension, review_limit):
                dispositions.append(REFER)
                reasons.append(
                    "void %.4f mm across exceeds the %.4f mm limit"
                    % (dimension, limit)
                )
            else:
                dispositions.append(REJECT)
                reasons.append(
                    "void %.4f mm across exceeds the %.4f mm review limit"
                    % (dimension, review_limit)
                )
        else:
            limit = criteria["max_patch_area_mm2"]
            review_limit = limit * criteria["patch_review_factor"]
            if _at_most(area, limit):
                dispositions.append(ACCEPT)
            elif _at_most(area, review_limit):
                dispositions.append(REFER)
                reasons.append(
                    "uncoated patch %.4f mm2 exceeds the %.4f mm2 limit"
                    % (area, limit)
                )
            else:
                dispositions.append(REJECT)
                reasons.append(
                    "uncoated patch %.4f mm2 exceeds the %.4f mm2 review limit"
                    % (area, review_limit)
                )
        if touches_edge:
            if criteria["edge_void_rejects"]:
                dispositions.append(REJECT)
                reasons.append(
                    "the missing coating reaches the cell edge, so the coating "
                    "has a free edge to delaminate from under thermal cycling"
                )
            else:
                dispositions.append(REFER)
                reasons.append(
                    "the missing coating reaches the cell edge; the free edge is "
                    "carried to review rather than rejected by policy"
                )

    return {
        "id": defect.get("id"),
        "kind": kind,
        "area_mm2": area,
        "max_dimension_mm": dimension,
        "uncoated_area_mm2": uncoated_area,
        "spatter_area_mm2": spatter_area,
        "disposition": _worst(dispositions),
        "reasons": reasons,
    }


def assess_ar_coating(cell, criteria=DEFAULT_AR_COATING_CRITERIA):
    """Clause 7.5.1.4.2 screen of the coating on one bare cell."""
    validate_ar_coating_criteria(criteria)
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    cell_id = cell.get("cell_id")
    if not isinstance(cell_id, str) or not cell_id.strip():
        raise ValueError("each cell needs a non-empty cell_id")
    geometry = coatable_area(cell.get("geometry"))
    defects = cell.get("coating_defects", [])
    if not isinstance(defects, (list, tuple)):
        raise ValueError("coating_defects must be a list, got %r" % (defects,))

    seen = set()
    assessed = []
    for defect in defects:
        result = assess_coating_defect(defect, geometry, criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate coating defect id %r on cell %s" % (marker, cell_id)
                )
            seen.add(marker)
        assessed.append(result)

    findings = []
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))
    verdict = _worst([result["disposition"] for result in assessed])

    uncoated_area = sum(result["uncoated_area_mm2"] for result in assessed)
    spatter_area = sum(result["spatter_area_mm2"] for result in assessed)
    if not _at_most(uncoated_area, geometry["coatable_area_mm2"]):
        raise ValueError(
            "uncoated area %.3f mm2 exceeds the %.3f mm2 coatable face on %s"
            % (uncoated_area, geometry["coatable_area_mm2"], cell_id)
        )
    uncoated_fraction = uncoated_area / geometry["coatable_area_mm2"]
    spatter_fraction = spatter_area / geometry["coatable_area_mm2"]
    current_loss = estimate_current_loss_fraction(uncoated_fraction, criteria)

    if not _at_most(uncoated_fraction, criteria["max_uncoated_area_fraction"]):
        verdict = _worst((verdict, REFER))
        findings.append(
            "%.5f of the coatable face carries no coating, past the %.5f "
            "ceiling, even though no single flaw did"
            % (uncoated_fraction, criteria["max_uncoated_area_fraction"])
        )
    if not _at_most(current_loss, criteria["max_current_loss_fraction"]):
        verdict = _worst((verdict, REFER))
        findings.append(
            "the uncoated share costs an estimated %.5f of the current, past "
            "the %.5f allowance for this coating"
            % (current_loss, criteria["max_current_loss_fraction"])
        )
    if not _at_most(spatter_fraction, criteria["max_spatter_area_fraction"]):
        verdict = _worst((verdict, REFER))
        findings.append(
            "spatter obscures %.5f of the coatable face, past the %.5f "
            "allowance" % (spatter_fraction, criteria["max_spatter_area_fraction"])
        )

    void_count = sum(1 for result in assessed if result["kind"] == COATING_VOID)
    spatter_count = sum(1 for result in assessed if result["kind"] == COATING_SPATTER)
    patch_count = sum(1 for result in assessed if result["kind"] == UNCOATED_PATCH)
    if void_count > criteria["max_voids_per_cell"]:
        verdict = _worst((verdict, REFER))
        findings.append(
            "%d voids exceed the %d allowed on one cell"
            % (void_count, criteria["max_voids_per_cell"])
        )
    if spatter_count > criteria["max_spatter_spots_per_cell"]:
        verdict = _worst((verdict, REFER))
        findings.append(
            "%d spatter spots exceed the %d allowed on one cell"
            % (spatter_count, criteria["max_spatter_spots_per_cell"])
        )

    return {
        "cell_id": cell_id,
        "verdict": _ROLLUP_BY_SEVERITY[verdict],
        "disposition": verdict,
        "defects": assessed,
        "coatable_area_mm2": geometry["coatable_area_mm2"],
        "uncoated_area_mm2": uncoated_area,
        "uncoated_fraction": uncoated_fraction,
        "spatter_area_mm2": spatter_area,
        "spatter_fraction": spatter_fraction,
        "estimated_current_loss_fraction": current_loss,
        "defect_counts": {
            UNCOATED_PATCH: patch_count,
            COATING_VOID: void_count,
            COATING_SPATTER: spatter_count,
        },
        "not_accepted_ids": [
            result["id"] for result in assessed if result["disposition"] != ACCEPT
        ],
        "findings": findings,
    }
