#!/usr/bin/env python3
"""Delivered bare cells, against the approved process identification document.

Anchor: ECSS-E-ST-20-08C clause 7.1.2. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

What is delivered under this clause is not a pile of cells. It is a population
of cells made by the process the customer approved and inspected by the
inspections that process calls for. Bare cells arrive as sub-lots -- a wafer
run, a coating run, a metallization run -- each with its own build record and
its own cell count, and the release question is answered per sub-lot and then
weighted by how many cells each sub-lot actually carries.

Three things decide a sub-lot.

Did an approved process document govern the build?
    A draft was circulated and signed by nobody. A withdrawn document was
    pulled. A build to an issue the customer did not approve is a build to
    somebody else's process.

Was the cell made only with steps that document declares?
    A step used but not declared is an undeclared process, whatever its
    merits. A step declared but not used is a note, not a defect.

How many cells survived the inspections, and how sure are we?
    Per-cell inspections report a count inspected and a count passed. From
    counts alone the set of cells that passed every inspection is not known
    exactly, only bracketed: at most the smallest pass count, at least the
    cell count less every failure. Reporting the bracket rather than one
    number is the honest answer, and the lower bound is what is released
    against.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "PID_STATES",
    "INSPECTION_MODES",
    "REQUIRED_INSPECTIONS",
    "SAMPLED_FRACTION_FLOOR",
    "STANDING_CURRENT",
    "STANDING_OFF_ISSUE",
    "STANDING_NONE",
    "DELIVERABLE",
    "CONCESSION",
    "WITHHELD",
    "DISPOSITION_RANK",
    "LOT_RELEASABLE",
    "LOT_RELEASABLE_WITH_CONCESSIONS",
    "LOT_WITHHELD",
    "pid_standing",
    "process_step_coverage",
    "inspection_yield",
    "deliverable_cell_bounds",
    "disposition_sub_lot",
    "assess_bare_cell_delivery",
]

PID_STATES = ("approved", "draft", "superseded", "withdrawn")

INSPECTION_MODES = ("per-cell", "sampled")

# The inspections the process document has to call for, with the mode each is
# run in. A per-cell inspection screens the population; a sampled inspection
# speaks for it.
REQUIRED_INSPECTIONS = (
    ("visual-inspection", "per-cell"),
    ("electrical-performance", "per-cell"),
    ("dimensional-measurement", "sampled"),
    ("contact-integrity", "sampled"),
)

# Smallest share of a sub-lot a sampled inspection may be run on.
SAMPLED_FRACTION_FLOOR = 0.10

STANDING_CURRENT = "governing-current-issue"
STANDING_OFF_ISSUE = "governing-off-issue"
STANDING_NONE = "not-governing"

DELIVERABLE = "deliverable"
CONCESSION = "deliverable-under-concession"
WITHHELD = "withheld"

DISPOSITION_RANK = {WITHHELD: 0, CONCESSION: 1, DELIVERABLE: 2}

LOT_RELEASABLE = "delivery-releasable"
LOT_RELEASABLE_WITH_CONCESSIONS = "delivery-releasable-with-concessions"
LOT_WITHHELD = "delivery-withheld"

# Sampling shares are quotients of counts compared with a written floor, so a
# sample physically on the floor can evaluate a few units in the last place
# under it. The comparison absorbs that; the floor stays as written.
_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _label(name, value):
    """Return a non-empty stripped string, or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _count(name, value, allow_zero=True):
    """Return a non-negative integer count, or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    if not allow_zero and value == 0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return value


def _at_least(value, bound):
    """True when value is at or above bound, absorbing representation error."""
    return value > bound or math.isclose(value, bound, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def pid_standing(state, approved_issue, build_issue):
    """Return how far the cited process identification document governs a build."""
    if state not in PID_STATES:
        raise ValueError(
            "process document state must be one of %s, got %r" % (PID_STATES, state)
        )
    approved = _label("approved_issue", approved_issue)
    built = _label("build_issue", build_issue)
    findings = []
    if state == "draft":
        findings.append(
            "the cited process document is a draft; it was approved by nobody "
            "and governs no delivered cell"
        )
        return {"standing": STANDING_NONE, "findings": findings}
    if state == "withdrawn":
        findings.append(
            "the cited process document has been withdrawn; it cannot govern a "
            "delivery made after the withdrawal"
        )
        return {"standing": STANDING_NONE, "findings": findings}
    if state == "superseded":
        findings.append(
            "the cited process document was superseded after the build; the "
            "difference between issue %s and issue %s needs dispositioning"
            % (built, approved)
        )
        return {"standing": STANDING_OFF_ISSUE, "findings": findings}
    if built != approved:
        findings.append(
            "the customer approved issue %s and the cells were built to issue "
            "%s" % (approved, built)
        )
        return {"standing": STANDING_OFF_ISSUE, "findings": findings}
    return {"standing": STANDING_CURRENT, "findings": findings}


def process_step_coverage(steps_used, steps_declared):
    """Compare the steps a sub-lot was built with against the declared set."""
    for name, value in (("steps_used", steps_used), ("steps_declared", steps_declared)):
        if not isinstance(value, (list, tuple)):
            raise ValueError("%s must be a sequence of step names" % name)
    used = [_label("process step", item) for item in steps_used]
    declared = [_label("declared step", item) for item in steps_declared]
    if not declared:
        raise ValueError("a process document declaring no step governs nothing")
    if not used:
        raise ValueError("a sub-lot built with no process step is an input error")
    declared_set = set(declared)
    used_set = set(used)
    undeclared = sorted(used_set - declared_set)
    unused = sorted(declared_set - used_set)
    findings = []
    for step in undeclared:
        findings.append(
            "step '%s' was used in the build and the process document does not "
            "declare it" % step
        )
    return {
        "used": sorted(used_set),
        "declared": sorted(declared_set),
        "undeclared": undeclared,
        "unused_declared": unused,
        "on_document": not undeclared,
        "findings": findings,
    }


def inspection_yield(record, sub_lot_cells):
    """Grade one inspection record against the sub-lot it was run on.

    record keys: kind, mode, inspected, passed.
    """
    if not isinstance(record, dict):
        raise ValueError("inspection record must be a mapping")
    for key in ("kind", "mode", "inspected", "passed"):
        if key not in record:
            raise ValueError("inspection record missing required key '%s'" % key)
    kind = _label("inspection kind", record["kind"])
    mode = record["mode"]
    if mode not in INSPECTION_MODES:
        raise ValueError(
            "inspection mode must be one of %s, got %r" % (INSPECTION_MODES, mode)
        )
    cells = _count("sub_lot_cells", sub_lot_cells, allow_zero=False)
    inspected = _count("inspected", record["inspected"])
    passed = _count("passed", record["passed"])
    if inspected > cells:
        raise ValueError(
            "inspection '%s' reports %d cells inspected from a sub-lot of %d"
            % (kind, inspected, cells)
        )
    if passed > inspected:
        raise ValueError(
            "inspection '%s' reports %d passes from %d inspected"
            % (kind, passed, inspected)
        )
    failed = inspected - passed
    inspected_fraction = float(inspected) / float(cells)
    pass_fraction = 1.0 if inspected == 0 else float(passed) / float(inspected)

    findings = []
    coverage_ok = True
    if mode == "per-cell":
        coverage_ok = inspected == cells
        if not coverage_ok:
            findings.append(
                "%s is a per-cell screen and %d of %d cells carry no record"
                % (kind, cells - inspected, cells)
            )
    else:
        coverage_ok = inspected > 0 and _at_least(
            inspected_fraction, SAMPLED_FRACTION_FLOOR
        )
        if not coverage_ok:
            findings.append(
                "%s sampled %d of %d cells, under the %.0f%% sampling floor"
                % (kind, inspected, cells, SAMPLED_FRACTION_FLOOR * 100.0)
            )
        if failed:
            findings.append(
                "%s is a sampled inspection and %d sampled cell(s) failed; the "
                "population it speaks for is suspect" % (kind, failed)
            )

    return {
        "kind": kind,
        "mode": mode,
        "inspected": inspected,
        "passed": passed,
        "failed": failed,
        "inspected_fraction": inspected_fraction,
        "pass_fraction": pass_fraction,
        "coverage_ok": coverage_ok,
        "sample_clean": (mode != "sampled") or failed == 0,
        "findings": findings,
    }


def deliverable_cell_bounds(sub_lot_cells, yields):
    """Bracket the count of cells that passed every per-cell inspection."""
    cells = _count("sub_lot_cells", sub_lot_cells, allow_zero=False)
    if not isinstance(yields, (list, tuple)):
        raise ValueError("yields must be a sequence of graded inspections")
    per_cell = [y for y in yields if y.get("mode") == "per-cell"]
    if not per_cell:
        return {"lower": 0, "upper": 0, "determinate": False}
    upper = min(item["passed"] for item in per_cell)
    total_failed = sum(item["failed"] for item in per_cell)
    lower = max(0, cells - total_failed)
    unrecorded = max(0, cells - min(item["inspected"] for item in per_cell))
    lower = max(0, lower - unrecorded)
    lower = min(lower, upper)
    return {
        "lower": lower,
        "upper": upper,
        "determinate": lower == upper,
        "unrecorded": unrecorded,
    }


def disposition_sub_lot(sub_lot):
    """Disposition one sub-lot of bare cells for delivery.

    sub_lot keys: identifier, cells, document_state, approved_issue,
    build_issue, steps_used, steps_declared, inspections.
    """
    if not isinstance(sub_lot, dict):
        raise ValueError("sub_lot must be a mapping")
    required_keys = (
        "identifier",
        "cells",
        "document_state",
        "approved_issue",
        "build_issue",
        "steps_used",
        "steps_declared",
        "inspections",
    )
    for key in required_keys:
        if key not in sub_lot:
            raise ValueError("sub_lot missing required key '%s'" % key)
    identifier = _label("identifier", sub_lot["identifier"])
    cells = _count("cells", sub_lot["cells"], allow_zero=False)
    standing = pid_standing(
        sub_lot["document_state"], sub_lot["approved_issue"], sub_lot["build_issue"]
    )
    steps = process_step_coverage(sub_lot["steps_used"], sub_lot["steps_declared"])

    records = sub_lot["inspections"]
    if not isinstance(records, (list, tuple)):
        raise ValueError("sub_lot['inspections'] must be a sequence")
    yields = [inspection_yield(record, cells) for record in records]
    seen = set()
    for item in yields:
        if item["kind"] in seen:
            raise ValueError(
                "inspection '%s' is recorded twice for sub-lot %s"
                % (item["kind"], identifier)
            )
        seen.add(item["kind"])

    findings = list(standing["findings"]) + list(steps["findings"])
    missing = []
    wrong_mode = []
    for kind, mode in REQUIRED_INSPECTIONS:
        match = next((y for y in yields if y["kind"] == kind), None)
        if match is None:
            missing.append(kind)
            continue
        if match["mode"] != mode:
            wrong_mode.append(kind)
    for kind in missing:
        findings.append(
            "inspection '%s' is called for by the process document and no "
            "record exists for sub-lot %s" % (kind, identifier)
        )
    for kind in wrong_mode:
        findings.append(
            "inspection '%s' was run in the wrong mode for sub-lot %s; a sample "
            "does not discharge a screen and a screen is not a sample"
            % (kind, identifier)
        )
    for item in yields:
        findings.extend(item["findings"])

    bounds = deliverable_cell_bounds(cells, yields)

    blocking = (
        standing["standing"] == STANDING_NONE
        or not steps["on_document"]
        or bool(missing)
        or bool(wrong_mode)
        or any(not item["sample_clean"] for item in yields)
        or any(item["mode"] == "sampled" and not item["coverage_ok"] for item in yields)
    )
    conditional = standing["standing"] == STANDING_OFF_ISSUE or any(
        item["mode"] == "per-cell" and not item["coverage_ok"] for item in yields
    )

    if blocking:
        disposition = WITHHELD
        releasable = 0
    elif conditional:
        disposition = CONCESSION
        releasable = bounds["lower"]
    else:
        disposition = DELIVERABLE
        releasable = bounds["lower"]

    return {
        "identifier": identifier,
        "cells": cells,
        "standing": standing["standing"],
        "steps": steps,
        "yields": yields,
        "missing_inspections": missing,
        "wrong_mode_inspections": wrong_mode,
        "deliverable_bounds": bounds,
        "releasable_cells": releasable,
        "disposition": disposition,
        "findings": findings,
    }


def assess_bare_cell_delivery(spec):
    """Grade a whole bare-cell delivery, weighted by the cells each sub-lot holds.

    spec keys: sub_lots (a non-empty sequence), optional required_release_share.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "sub_lots" not in spec:
        raise ValueError("spec missing required key 'sub_lots'")
    sub_lots = spec["sub_lots"]
    if not isinstance(sub_lots, (list, tuple)) or not sub_lots:
        raise ValueError("spec['sub_lots'] must be a non-empty sequence")

    required_share = spec.get("required_release_share", 1.0)
    if isinstance(required_share, bool) or not isinstance(required_share, (int, float)):
        raise ValueError("required_release_share must be a real number")
    required_share = float(required_share)
    if not math.isfinite(required_share) or not 0.0 <= required_share <= 1.0:
        raise ValueError(
            "required_release_share must lie in [0, 1], got %r"
            % (spec.get("required_release_share"),)
        )

    results = [disposition_sub_lot(item) for item in sub_lots]
    seen = set()
    for item in results:
        if item["identifier"] in seen:
            raise ValueError("sub-lot %s is presented twice" % item["identifier"])
        seen.add(item["identifier"])

    total_cells = sum(item["cells"] for item in results)
    released = sum(item["releasable_cells"] for item in results)
    release_share = float(released) / float(total_cells)

    worst = min(DISPOSITION_RANK[item["disposition"]] for item in results)
    findings = []
    for item in results:
        findings.extend(item["findings"])
    if not _at_least(release_share, required_share):
        findings.append(
            "released cell share is %.4f against a required %.4f"
            % (release_share, required_share)
        )

    if worst == DISPOSITION_RANK[WITHHELD] or not _at_least(
        release_share, required_share
    ):
        verdict = LOT_WITHHELD
    elif worst == DISPOSITION_RANK[CONCESSION]:
        verdict = LOT_RELEASABLE_WITH_CONCESSIONS
    else:
        verdict = LOT_RELEASABLE

    return {
        "sub_lots": results,
        "total_cells": total_cells,
        "released_cells": released,
        "release_share": release_share,
        "required_release_share": required_share,
        "withheld": [i["identifier"] for i in results if i["disposition"] == WITHHELD],
        "under_concession": [
            i["identifier"] for i in results if i["disposition"] == CONCESSION
        ],
        "verdict": verdict,
        "findings": findings,
    }
