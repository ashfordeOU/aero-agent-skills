#!/usr/bin/env python3
"""Loading a bare-cell lot into the ambient pressure chamber, then judging
the contact and diode attachment adherence that follows.

Anchor: ECSS-E-ST-20-08C clause 7.5.7.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause puts every cell of the lot into the chamber, at ambient
pressure, for the declared soak, and only then pulls the contacts. Each
of those words does work:

    every cell        a lot is sentenced from what went in. Cells left
                      on the bench are not covered by the result, and a
                      partial load is reported as partial rather than
                      averaged away
    ambient pressure  the soak is run in the band the clause names. A
                      chamber that drifted out of it ran a different
                      test, and the cells in it were conditioned to an
                      unknown state
    the declared soak the dwell is what turns a stack of cells into
                      conditioned cells. Short dwell, no conditioning
    then pulled       adherence is judged after the soak, at three
                      sites per cell: the front contact, the rear
                      contact and, where the cell carries one, the
                      bypass diode attachment

Loading geometry is part of the test, not housekeeping. Cells packed
edge to edge shadow each other from the circulating air, so the chamber
has a packing cap and every cell carries an edge clearance; a shelf
filled past the cap has conditioned its outer cells and warmed its inner
ones.

A cell is sentenced by its weakest site, because a string does not care
which joint let go.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FRONT_CONTACT = "front-contact"
REAR_CONTACT = "rear-contact"
DIODE_ATTACHMENT = "diode-attachment"

ATTACHMENT_SITES = (FRONT_CONTACT, REAR_CONTACT, DIODE_ATTACHMENT)

ADHERENT = "adherent"
BELOW_LIMIT = "below-limit"
DETACHED = "detached"

ADHERENCE_CATEGORIES = (ADHERENT, BELOW_LIMIT, DETACHED)

CONTACT_ADHERENCE_RUN_PASSED = "contact-adherence-run-passed"
CONTACT_ADHERENCE_RUN_FAILED = "contact-adherence-run-failed"
CONTACT_ADHERENCE_RUN_NOT_EVALUATED = "contact-adherence-run-not-evaluated"

RUN_VERDICTS = (
    CONTACT_ADHERENCE_RUN_PASSED,
    CONTACT_ADHERENCE_RUN_FAILED,
    CONTACT_ADHERENCE_RUN_NOT_EVALUATED,
)

# Declared chamber and acceptance policy: project numbers, not physical
# constants.
DEFAULT_CELL_LOADING_POLICY = {
    "min_chamber_pressure_kpa": 86.0,
    "max_chamber_pressure_kpa": 106.0,
    "max_shelf_packing_fraction": 0.75,
    "min_edge_clearance_mm": 2.0,
    "min_soak_dwell_h": 24.0,
    "min_pull_load_n": 2.0,
    "detached_load_n": 0.2,
    "max_reject_fraction": 0.05,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("%s must be an integer of at least 1, got %r" % (name, value))
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A clearance, a dwell and a pull load are measured quantities held
    against declared floors, so a cell set exactly on a floor can land a
    few units in the last place below it. The floor is never lowered;
    only the comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_cell_loading_policy(policy=DEFAULT_CELL_LOADING_POLICY):
    """Check a chamber and acceptance policy is usable before it is used."""
    _require_mapping("policy", policy)
    low = _require_positive(
        "min_chamber_pressure_kpa", policy.get("min_chamber_pressure_kpa")
    )
    high = _require_positive(
        "max_chamber_pressure_kpa", policy.get("max_chamber_pressure_kpa")
    )
    if high <= low:
        raise ValueError(
            "max_chamber_pressure_kpa must exceed min_chamber_pressure_kpa"
        )
    packing = _require_positive(
        "max_shelf_packing_fraction", policy.get("max_shelf_packing_fraction")
    )
    if packing > 1.0:
        raise ValueError(
            "max_shelf_packing_fraction must not exceed 1.0, got %r" % (packing,)
        )
    _require_non_negative(
        "min_edge_clearance_mm", policy.get("min_edge_clearance_mm")
    )
    _require_positive("min_soak_dwell_h", policy.get("min_soak_dwell_h"))
    pull = _require_positive("min_pull_load_n", policy.get("min_pull_load_n"))
    detached = _require_non_negative(
        "detached_load_n", policy.get("detached_load_n")
    )
    if detached >= pull:
        raise ValueError(
            "detached_load_n must sit below min_pull_load_n, otherwise every "
            "weak joint is reported as detached"
        )
    reject = _require_non_negative(
        "max_reject_fraction", policy.get("max_reject_fraction")
    )
    if reject > 1.0:
        raise ValueError(
            "max_reject_fraction must not exceed 1.0, got %r" % (reject,)
        )
    return policy


def cell_loading_footprint_mm2(cell_length_mm, cell_width_mm, edge_clearance_mm):
    """Shelf area one cell occupies once its edge clearance is included.

    The clearance is the air gap that lets the soak reach the cell, so it
    is part of the footprint rather than a separate allowance, and it is
    added on every side.
    """
    length = _require_positive("cell_length_mm", cell_length_mm)
    width = _require_positive("cell_width_mm", cell_width_mm)
    clearance = _require_non_negative("edge_clearance_mm", edge_clearance_mm)
    return (length + 2.0 * clearance) * (width + 2.0 * clearance)


def required_shelf_area_mm2(cells_loaded, footprint_mm2):
    """Shelf area the whole load needs."""
    count = _require_count("cells_loaded", cells_loaded)
    footprint = _require_positive("footprint_mm2", footprint_mm2)
    return count * footprint


def shelf_packing_fraction(required_area_mm2, usable_shelf_area_mm2):
    """Share of the usable shelf the load occupies."""
    required = _require_positive("required_area_mm2", required_area_mm2)
    usable = _require_positive("usable_shelf_area_mm2", usable_shelf_area_mm2)
    return required / usable


def chamber_pressure_in_band(pressure_kpa, policy=DEFAULT_CELL_LOADING_POLICY):
    """Did the chamber hold the ambient band the soak is defined in?"""
    validate_cell_loading_policy(policy)
    pressure = _require_positive("pressure_kpa", pressure_kpa)
    return _at_least(
        pressure, float(policy["min_chamber_pressure_kpa"])
    ) and _at_most(pressure, float(policy["max_chamber_pressure_kpa"]))


def loading_completeness(lot_size, cells_loaded):
    """Every cell of the lot goes in; report what did not.

    A lot is sentenced from what was conditioned. Cells that never
    entered the chamber are not evidence about the lot, so they are
    counted and named instead of being quietly dropped from the
    denominator.
    """
    lot = _require_count("lot_size", lot_size)
    loaded = _require_count("cells_loaded", cells_loaded)
    if loaded > lot:
        raise ValueError(
            "cells_loaded %d exceeds the lot size %d" % (loaded, lot)
        )
    missing = lot - loaded
    findings = []
    if missing:
        findings.append(
            "%d of %d cells never entered the chamber, so the run covers only "
            "part of the lot" % (missing, lot)
        )
    return {
        "lot_size": lot,
        "cells_loaded": loaded,
        "cells_not_loaded": missing,
        "complete": missing == 0,
        "loaded_fraction": loaded / lot,
        "findings": findings,
    }


def assess_chamber_loading(loading, policy=DEFAULT_CELL_LOADING_POLICY):
    """Grade the load itself before any contact is pulled.

    Five things have to be true together: the whole lot went in, each
    cell kept its clearance, the shelf stayed under the packing cap, the
    pressure held the ambient band and the dwell reached the declared
    soak. A failure in any of them means the cells were not conditioned
    as the clause asks, and the adherence numbers that follow describe
    something else.
    """
    validate_cell_loading_policy(policy)
    _require_mapping("loading", loading)

    completeness = loading_completeness(
        loading.get("lot_size"), loading.get("cells_loaded")
    )
    clearance = _require_non_negative(
        "edge_clearance_mm", loading.get("edge_clearance_mm")
    )
    footprint = cell_loading_footprint_mm2(
        loading.get("cell_length_mm"), loading.get("cell_width_mm"), clearance
    )
    required_area = required_shelf_area_mm2(
        completeness["cells_loaded"], footprint
    )
    packing = shelf_packing_fraction(
        required_area, loading.get("usable_shelf_area_mm2")
    )
    pressure = _require_positive(
        "chamber_pressure_kpa", loading.get("chamber_pressure_kpa")
    )
    dwell = _require_non_negative("soak_dwell_h", loading.get("soak_dwell_h"))

    clearance_ok = _at_least(clearance, float(policy["min_edge_clearance_mm"]))
    packing_ok = _at_most(packing, float(policy["max_shelf_packing_fraction"]))
    pressure_ok = chamber_pressure_in_band(pressure, policy)
    dwell_ok = _at_least(dwell, float(policy["min_soak_dwell_h"]))

    findings = list(completeness["findings"])
    if not clearance_ok:
        findings.append(
            "edge clearance %.3f mm is under the %.3f mm the load plan requires, "
            "so the inner cells are shadowed from the circulating air"
            % (clearance, float(policy["min_edge_clearance_mm"]))
        )
    if not packing_ok:
        findings.append(
            "shelf packing %.4f exceeds the cap %.4f; the load blocks its own "
            "circulation and the cells are not conditioned alike"
            % (packing, float(policy["max_shelf_packing_fraction"]))
        )
    if not pressure_ok:
        findings.append(
            "chamber pressure %.2f kPa is outside the ambient band %.2f-%.2f kPa"
            % (
                pressure,
                float(policy["min_chamber_pressure_kpa"]),
                float(policy["max_chamber_pressure_kpa"]),
            )
        )
    if not dwell_ok:
        findings.append(
            "soak dwell %.3f h is short of the declared %.3f h, so the cells "
            "leave the chamber unconditioned"
            % (dwell, float(policy["min_soak_dwell_h"]))
        )

    return {
        "cells_loaded": completeness["cells_loaded"],
        "cells_not_loaded": completeness["cells_not_loaded"],
        "loaded_fraction": completeness["loaded_fraction"],
        "cell_footprint_mm2": footprint,
        "required_shelf_area_mm2": required_area,
        "shelf_packing_fraction": packing,
        "chamber_pressure_kpa": pressure,
        "soak_dwell_h": dwell,
        "complete": completeness["complete"],
        "clearance_adequate": clearance_ok,
        "packing_acceptable": packing_ok,
        "pressure_in_band": pressure_ok,
        "dwell_adequate": dwell_ok,
        "valid": bool(
            completeness["complete"]
            and clearance_ok
            and packing_ok
            and pressure_ok
            and dwell_ok
        ),
        "findings": findings,
    }


def categorize_attachment(pull_load_n, policy=DEFAULT_CELL_LOADING_POLICY):
    """Group one site's pull load against the declared acceptance numbers."""
    validate_cell_loading_policy(policy)
    load = _require_non_negative("pull_load_n", pull_load_n)
    if _at_least(load, float(policy["min_pull_load_n"])):
        return ADHERENT
    if _at_least(load, float(policy["detached_load_n"])):
        return BELOW_LIMIT
    return DETACHED


def evaluate_cell(cell, policy=DEFAULT_CELL_LOADING_POLICY):
    """Reduce one conditioned cell to a per-site grouping and a verdict.

    A cell declared to carry a bypass diode has to bring a diode
    attachment reading with it. A missing reading is refused rather than
    treated as a pass, because the site the clause names was not tested.
    """
    validate_cell_loading_policy(policy)
    _require_mapping("cell", cell)

    sites = {}
    sites[FRONT_CONTACT] = _require_non_negative(
        "front_contact_pull_load_n", cell.get("front_contact_pull_load_n")
    )
    sites[REAR_CONTACT] = _require_non_negative(
        "rear_contact_pull_load_n", cell.get("rear_contact_pull_load_n")
    )
    carries_diode = bool(cell.get("carries_bypass_diode", False))
    if carries_diode:
        if cell.get("diode_attachment_pull_load_n") is None:
            raise ValueError(
                "cell %r declares a bypass diode but carries no diode "
                "attachment reading" % (cell.get("id"),)
            )
        sites[DIODE_ATTACHMENT] = _require_non_negative(
            "diode_attachment_pull_load_n",
            cell.get("diode_attachment_pull_load_n"),
        )

    categories = {
        site: categorize_attachment(load, policy) for site, load in sites.items()
    }
    weakest_site = min(sites, key=lambda site: sites[site])
    rank = {ADHERENT: 0, BELOW_LIMIT: 1, DETACHED: 2}
    worst_category = max(categories.values(), key=lambda name: rank[name])

    findings = []
    for site in ATTACHMENT_SITES:
        if site not in categories:
            continue
        if categories[site] == BELOW_LIMIT:
            findings.append(
                "cell %r %s held only %.3f N, under the %.3f N floor"
                % (
                    cell.get("id"),
                    site,
                    sites[site],
                    float(policy["min_pull_load_n"]),
                )
            )
        elif categories[site] == DETACHED:
            findings.append(
                "cell %r %s came away at %.3f N; the joint is gone, not weak"
                % (cell.get("id"), site, sites[site])
            )

    return {
        "id": cell.get("id"),
        "carries_bypass_diode": carries_diode,
        "site_loads_n": sites,
        "site_categories": categories,
        "weakest_site": weakest_site,
        "weakest_load_n": sites[weakest_site],
        "category": worst_category,
        "acceptable": worst_category == ADHERENT,
        "findings": findings,
    }


def evaluate_cell_contact_adherence_process(run, policy=DEFAULT_CELL_LOADING_POLICY):
    """Full clause 7.5.7.2.2 chamber loading and adherence run with a verdict."""
    validate_cell_loading_policy(policy)
    _require_mapping("run", run)

    loading = assess_chamber_loading(run.get("loading"), policy)
    cells = run.get("cells")
    if not isinstance(cells, (list, tuple)) or not cells:
        raise ValueError("run must carry a non-empty cells sequence")

    evaluated = [evaluate_cell(cell, policy) for cell in cells]
    if len(evaluated) != loading["cells_loaded"]:
        raise ValueError(
            "the run records %d cell result(s) but %d cell(s) were loaded"
            % (len(evaluated), loading["cells_loaded"])
        )

    findings = list(loading["findings"])
    rejected = [record["id"] for record in evaluated if not record["acceptable"]]
    detached = [
        record["id"] for record in evaluated if record["category"] == DETACHED
    ]
    reject_fraction = len(rejected) / len(evaluated)

    result = {
        "lot_id": run.get("lot_id"),
        "loading": loading,
        "cells": evaluated,
        "rejected_cell_ids": rejected,
        "detached_cell_ids": detached,
        "reject_fraction": reject_fraction,
        "findings": findings,
    }

    if not loading["valid"]:
        findings.append(
            "the load never met the chamber conditions, so the contacts were "
            "pulled on cells conditioned to an unknown state and the run is "
            "repeated rather than sentenced"
        )
        result.update(
            {
                "compliant": None,
                "verdict": CONTACT_ADHERENCE_RUN_NOT_EVALUATED,
            }
        )
        return result

    for record in evaluated:
        findings.extend(record["findings"])

    reasons = []
    if detached:
        reasons.append(
            "%d cell(s) lost an attachment outright: %s"
            % (len(detached), ", ".join(repr(item) for item in detached))
        )
    if not _at_most(reject_fraction, float(policy["max_reject_fraction"])):
        reasons.append(
            "rejected share %.4f exceeds the allowed %.4f"
            % (reject_fraction, float(policy["max_reject_fraction"]))
        )

    compliant = not reasons
    findings.extend(reasons)
    result.update(
        {
            "compliant": compliant,
            "verdict": CONTACT_ADHERENCE_RUN_PASSED
            if compliant
            else CONTACT_ADHERENCE_RUN_FAILED,
        }
    )
    return result
