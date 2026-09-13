#!/usr/bin/env python3
"""Visual inspection of the coverglass adhesive on a cell assembly.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.7. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The adhesive between the coverglass and the cell is examined for two
things: delamination, where the bond has let go, and discolouration,
where the adhesive has darkened and now absorbs light on its way to the
cell. One region is treated differently from the rest -- the bond line
lying over the rear weld footprint, where the welding heat is expected
to disturb the adhesive, carries an allowance of its own.

Indication kinds
    delamination     a void or lifted region in the bond line
    discolouration   adhesive darkened over an area, graded light,
                     moderate or dark

Zones
    active-cell-area   bond line over the illuminated cell
    cell-edge-margin   bond line outside the active area
    rear-weld-area     bond line over the rear interconnector welds

Dispositions are accept, rework and reject. The criteria below are a
declared project criteria set, not a physical constant; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ADHESIVE_INDICATION_KINDS = ("delamination", "discolouration")
ADHESIVE_ZONES = ("active-cell-area", "cell-edge-margin", "rear-weld-area")
DISCOLOURATION_GRADES = ("light", "moderate", "dark")

ACCEPT = "accept"
REWORK = "rework"
REJECT = "reject"
ADHESIVE_DISPOSITIONS = (ACCEPT, REWORK, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REWORK: 1, REJECT: 2}

DEFAULT_ADHESIVE_CRITERIA = {
    "weld_area_allowance_fraction": 1.0,
    "rework_delamination_area_fraction": 0.02,
    "max_delamination_area_fraction": 0.05,
    "max_single_delamination_dimension_mm": 3.0,
    "rework_transmission_loss": 0.01,
    "max_transmission_loss": 0.02,
    "transmission_loss_factor": {
        "light": 0.10,
        "moderate": 0.30,
        "dark": 0.60,
    },
    "optical_zones": ("active-cell-area",),
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


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A limit is a product of a criteria fraction and a measured area, so
    a measurement sitting exactly on the limit can evaluate a few units
    in the last place above it. The limit is never raised; only the
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


def validate_adhesive_criteria(criteria):
    """Check an adhesive criteria set is complete and self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    allowance = _require_non_negative(
        "criteria weld_area_allowance_fraction",
        criteria.get("weld_area_allowance_fraction"),
    )
    if allowance > 1.0:
        raise ValueError(
            "criteria weld_area_allowance_fraction must not exceed one; the "
            "allowance cannot be larger than the weld footprint it covers"
        )
    rework_area = _require_positive(
        "criteria rework_delamination_area_fraction",
        criteria.get("rework_delamination_area_fraction"),
    )
    max_area = _require_positive(
        "criteria max_delamination_area_fraction",
        criteria.get("max_delamination_area_fraction"),
    )
    if max_area < rework_area:
        raise ValueError(
            "criteria max_delamination_area_fraction is below the rework fraction"
        )
    _require_positive(
        "criteria max_single_delamination_dimension_mm",
        criteria.get("max_single_delamination_dimension_mm"),
    )
    rework_loss = _require_positive(
        "criteria rework_transmission_loss", criteria.get("rework_transmission_loss")
    )
    max_loss = _require_positive(
        "criteria max_transmission_loss", criteria.get("max_transmission_loss")
    )
    if max_loss < rework_loss:
        raise ValueError(
            "criteria max_transmission_loss is below the rework transmission loss"
        )
    factors = criteria.get("transmission_loss_factor")
    if not isinstance(factors, dict):
        raise ValueError("criteria transmission_loss_factor must be a mapping")
    missing = set(DISCOLOURATION_GRADES) - set(factors)
    if missing:
        raise ValueError(
            "criteria transmission_loss_factor is missing grades: %s"
            % ", ".join(sorted(missing))
        )
    previous = -1.0
    for grade in DISCOLOURATION_GRADES:
        factor = _require_non_negative(
            "criteria transmission_loss_factor[%s]" % grade, factors[grade]
        )
        if factor > 1.0:
            raise ValueError(
                "criteria transmission_loss_factor[%s] must not exceed one" % grade
            )
        if factor < previous:
            raise ValueError(
                "criteria transmission_loss_factor must not fall as the grade "
                "darkens; %s is lighter than the grade before it" % grade
            )
        previous = factor
    zones = criteria.get("optical_zones")
    if not isinstance(zones, (list, tuple)) or not zones:
        raise ValueError("criteria optical_zones must be a non-empty sequence")
    for zone in zones:
        _require_choice("criteria optical_zones entry", zone, ADHESIVE_ZONES)
    return criteria


def assess_adhesive_indication(indication, criteria=DEFAULT_ADHESIVE_CRITERIA):
    """Normalize and check one adhesive indication before it is counted."""
    validate_adhesive_criteria(criteria)
    if not isinstance(indication, dict):
        raise ValueError("indication must be a mapping, got %r" % (indication,))
    kind = _require_choice(
        "kind", indication.get("kind"), ADHESIVE_INDICATION_KINDS
    )
    zone = _require_choice("zone", indication.get("zone"), ADHESIVE_ZONES)
    area = _require_positive("area_mm2", indication.get("area_mm2"))
    record = {
        "id": indication.get("id"),
        "kind": kind,
        "zone": zone,
        "area_mm2": area,
        "grade": None,
        "max_dimension_mm": None,
        "oversize_void": False,
    }
    if kind == "delamination":
        dimension = _require_positive(
            "max_dimension_mm", indication.get("max_dimension_mm")
        )
        record["max_dimension_mm"] = dimension
        if zone != "rear-weld-area" and not _at_most(
            dimension, criteria["max_single_delamination_dimension_mm"]
        ):
            record["oversize_void"] = True
    else:
        record["grade"] = _require_choice(
            "grade", indication.get("grade"), DISCOLOURATION_GRADES
        )
    return record


def countable_delamination_area(
    indications, rear_weld_footprint_area_mm2, criteria=DEFAULT_ADHESIVE_CRITERIA
):
    """Delamination area left once the rear-weld allowance is applied.

    Delamination over the rear weld footprint is expected from the
    welding heat and is allowed up to the allowance the footprint buys.
    Anything beyond the remaining allowance, and everything outside that
    zone, is counted against the bond line.
    """
    validate_adhesive_criteria(criteria)
    if not isinstance(indications, (list, tuple)):
        raise ValueError("indications must be a list, got %r" % (indications,))
    footprint = _require_non_negative(
        "rear_weld_footprint_area_mm2", rear_weld_footprint_area_mm2
    )
    allowance = footprint * criteria["weld_area_allowance_fraction"]
    remaining = allowance
    countable = 0.0
    findings = []
    for indication in indications:
        record = assess_adhesive_indication(indication, criteria)
        if record["kind"] != "delamination":
            continue
        if record["zone"] != "rear-weld-area":
            countable += record["area_mm2"]
            continue
        covered = min(record["area_mm2"], remaining)
        remaining -= covered
        spill = record["area_mm2"] - covered
        if spill > 0.0:
            countable += spill
            findings.append(
                "%s: %.2f mm2 of weld-area delamination sits outside the %.2f mm2 "
                "allowance and is counted against the bond line"
                % (record["id"], spill, allowance)
            )
    if allowance > 0.0 and remaining <= 0.0:
        findings.append(
            "the rear-weld allowance of %.2f mm2 is fully used; further weld-area "
            "delamination counts in full" % allowance
        )
    return {
        "allowance_mm2": allowance,
        "allowance_used_mm2": allowance - remaining,
        "allowance_remaining_mm2": remaining,
        "countable_area_mm2": countable,
        "findings": findings,
    }


def discolouration_transmission_loss(
    indications, active_area_mm2, criteria=DEFAULT_ADHESIVE_CRITERIA
):
    """Fraction of the light to the cell lost in discoloured adhesive.

    Only discolouration in an optical zone blocks light; the same stain
    on the edge margin or over the weld footprint is recorded but costs
    the cell nothing.
    """
    validate_adhesive_criteria(criteria)
    if not isinstance(indications, (list, tuple)):
        raise ValueError("indications must be a list, got %r" % (indications,))
    active_area = _require_positive("active_area_mm2", active_area_mm2)
    optical_zones = tuple(criteria["optical_zones"])
    factors = criteria["transmission_loss_factor"]
    weighted = 0.0
    optical_area = 0.0
    outside_area = 0.0
    for indication in indications:
        record = assess_adhesive_indication(indication, criteria)
        if record["kind"] != "discolouration":
            continue
        if record["zone"] not in optical_zones:
            outside_area += record["area_mm2"]
            continue
        optical_area += record["area_mm2"]
        weighted += record["area_mm2"] * factors[record["grade"]]
    if not _at_most(optical_area, active_area):
        raise ValueError(
            "discoloured area %.2f mm2 exceeds the active area %.2f mm2"
            % (optical_area, active_area)
        )
    return {
        "transmission_loss": weighted / active_area,
        "discoloured_optical_area_mm2": optical_area,
        "discoloured_outside_optical_area_mm2": outside_area,
    }


def inspect_coverglass_adhesive(cell, criteria=DEFAULT_ADHESIVE_CRITERIA):
    """Full clause 5.5.3.2.7 adhesive examination with a cell verdict."""
    validate_adhesive_criteria(criteria)
    if not isinstance(cell, dict):
        raise ValueError("cell must be a mapping, got %r" % (cell,))
    cell_id = cell.get("cell_id")
    if not isinstance(cell_id, str) or not cell_id.strip():
        raise ValueError("each assembly record needs a non-empty cell_id")
    bonded_area = _require_positive("bonded_area_mm2", cell.get("bonded_area_mm2"))
    active_area = _require_positive("active_area_mm2", cell.get("active_area_mm2"))
    if not _at_most(active_area, bonded_area):
        raise ValueError(
            "active area %.2f mm2 exceeds the bonded area %.2f mm2; the coverglass "
            "cannot be smaller than the cell it protects" % (active_area, bonded_area)
        )
    footprint = _require_non_negative(
        "rear_weld_footprint_area_mm2", cell.get("rear_weld_footprint_area_mm2", 0.0)
    )
    if not _at_most(footprint, bonded_area):
        raise ValueError(
            "rear weld footprint %.2f mm2 exceeds the bonded area %.2f mm2"
            % (footprint, bonded_area)
        )
    indications = cell.get("indications")
    if not isinstance(indications, (list, tuple)):
        raise ValueError("cell indications must be a list, got %r" % (indications,))

    seen = set()
    assessed = []
    total_area = 0.0
    for indication in indications:
        record = assess_adhesive_indication(indication, criteria)
        marker = record["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate indication id %r on cell %s" % (marker, cell_id)
                )
            seen.add(marker)
        total_area += record["area_mm2"]
        assessed.append(record)
    if not _at_most(total_area, bonded_area):
        raise ValueError(
            "indication area %.2f mm2 exceeds the bonded area %.2f mm2 on %s"
            % (total_area, bonded_area, cell_id)
        )

    delamination = countable_delamination_area(list(indications), footprint, criteria)
    optical = discolouration_transmission_loss(list(indications), active_area, criteria)
    delamination_fraction = delamination["countable_area_mm2"] / bonded_area
    loss = optical["transmission_loss"]

    findings = list(delamination["findings"])
    verdict = ACCEPT

    oversize = [record["id"] for record in assessed if record["oversize_void"]]
    if oversize:
        verdict = REJECT
        findings.append(
            "single delamination beyond the %.2f mm limit on %s; a void that wide "
            "will grow under thermal cycling whatever the total area says"
            % (criteria["max_single_delamination_dimension_mm"], ", ".join(
                str(marker) for marker in oversize
            ))
        )
    if not _at_most(delamination_fraction, criteria["max_delamination_area_fraction"]):
        verdict = REJECT
        findings.append(
            "counted delamination fraction %.4f exceeds the %.4f limit"
            % (delamination_fraction, criteria["max_delamination_area_fraction"])
        )
    elif not _at_most(
        delamination_fraction, criteria["rework_delamination_area_fraction"]
    ):
        verdict = _worst((verdict, REWORK))
        findings.append(
            "counted delamination fraction %.4f exceeds the %.4f rework fraction"
            % (delamination_fraction, criteria["rework_delamination_area_fraction"])
        )
    if not _at_most(loss, criteria["max_transmission_loss"]):
        verdict = REJECT
        findings.append(
            "discoloured adhesive costs %.4f of the light to the cell, past the "
            "%.4f limit" % (loss, criteria["max_transmission_loss"])
        )
    elif not _at_most(loss, criteria["rework_transmission_loss"]):
        verdict = _worst((verdict, REWORK))
        findings.append(
            "discoloured adhesive costs %.4f of the light to the cell, past the "
            "%.4f rework limit" % (loss, criteria["rework_transmission_loss"])
        )
    if not assessed:
        findings.append(
            "no delamination or discolouration recorded; the bond line is "
            "examined and clean"
        )
    return {
        "cell_id": cell_id,
        "verdict": verdict,
        "indications": assessed,
        "countable_delamination_area_mm2": delamination["countable_area_mm2"],
        "delamination_area_fraction": delamination_fraction,
        "weld_allowance_mm2": delamination["allowance_mm2"],
        "weld_allowance_used_mm2": delamination["allowance_used_mm2"],
        "weld_allowance_remaining_mm2": delamination["allowance_remaining_mm2"],
        "transmission_loss": loss,
        "discoloured_optical_area_mm2": optical["discoloured_optical_area_mm2"],
        "oversize_void_ids": oversize,
        "findings": findings,
    }
