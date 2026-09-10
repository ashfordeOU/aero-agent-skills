#!/usr/bin/env python3
"""ECSS-E-ST-10-04C Annex A natural EM radiation and solar/geomagnetic
index reference dataset logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
Annex A is the normative reference-data annex backing clause 6
(electromagnetic radiation) and clause 6.2.2 (solar/geomagnetic
activity indices). It splits into phase-dependent quantities -- total
solar irradiance (TSI), EUV/XUV band irradiance, F10.7, its 81-day-
smoothed companion F10.7A, and a geomagnetic index (Ap or Kp) -- each
defined separately for the minimum, mean, and maximum solar-cycle
phase, and phase-independent quantities -- Earth albedo and Earth IR
emission -- which are design constants that vary by orbit/season
rather than by solar cycle. Downstream leaves e1004-em-radiation
(clause 6.2) and e1004-indices (clause 6.2.2 + Annex A) consume this
table rather than re-deriving it. Reference: ECSS-E-ST-10-04C Annex A.
"""

from __future__ import annotations

PHASE_DEPENDENT_QUANTITIES = (
    "tsi",
    "euv_xuv_irradiance",
    "f10_7",
    "f10_7a",
    "geomagnetic_index",
)

PHASE_INDEPENDENT_QUANTITIES = (
    "earth_albedo",
    "earth_ir_emission",
)

REQUIRED_QUANTITIES = PHASE_DEPENDENT_QUANTITIES + PHASE_INDEPENDENT_QUANTITIES

PHASES = ("minimum", "mean", "maximum")
PHASE_INDEPENDENT_LABEL = "phase_independent"


def is_phase_dependent(quantity):
    """True if `quantity` is defined per solar-cycle phase, False if it
    is a phase-independent design constant. Raises ValueError for an
    unknown quantity name."""
    if quantity not in REQUIRED_QUANTITIES:
        raise ValueError(f"unknown Annex A quantity: {quantity!r}")
    return quantity in PHASE_DEPENDENT_QUANTITIES


def assess_entry(entry):
    """Return a list of issue strings for a single quantity entry
    (dict with value / citation keys); empty list means the entry is
    usable."""
    issues = []
    if entry.get("value") is None:
        issues.append("missing value")
    if not entry.get("citation"):
        issues.append("missing citation")
    return issues


def assess_quantity(quantity, phase_entries):
    """Assess one quantity's phase_entries dict (phase label -> entry).

    For a phase-dependent quantity, valid labels are minimum/mean/
    maximum; for a phase-independent quantity, the only valid label is
    "phase_independent". Returns a result dict with missing phases,
    per-phase issues (including stray/wrong labels), whether any
    supplied multi-phase ordering is non-decreasing, and an overall
    completeness flag. Raises ValueError for an unknown quantity."""
    dependent = is_phase_dependent(quantity)
    valid_labels = PHASES if dependent else (PHASE_INDEPENDENT_LABEL,)

    issues_by_phase = {}
    for label in sorted(set(phase_entries) - set(valid_labels)):
        expected = "minimum/mean/maximum" if dependent else PHASE_INDEPENDENT_LABEL
        issues_by_phase[label] = [f"wrong phase label, expected {expected}"]

    present_valid = [label for label in valid_labels if label in phase_entries]
    for label in present_valid:
        entry_issues = assess_entry(phase_entries[label])
        if entry_issues:
            issues_by_phase[label] = entry_issues

    missing_phases = [label for label in valid_labels if label not in phase_entries]

    ordering_ok = True
    if dependent and len(present_valid) >= 2 and not issues_by_phase:
        values = [phase_entries[label]["value"] for label in present_valid]
        ordering_ok = all(values[i] <= values[i + 1] for i in range(len(values) - 1))

    complete = not missing_phases and not issues_by_phase and ordering_ok
    return {
        "missing_phases": missing_phases,
        "issues_by_phase": issues_by_phase,
        "ordering_ok": ordering_ok,
        "complete": complete,
    }


def assess_dataset(dataset):
    """Assess a full Annex A dataset dict: {"quantities": {name:
    {phase_label: entry}}}. Returns missing top-level quantities, a
    per-quantity result from assess_quantity, and an overall
    completeness flag."""
    quantities = dataset.get("quantities", {})
    missing_quantities = sorted(set(REQUIRED_QUANTITIES) - set(quantities))

    quantity_results = {
        name: assess_quantity(name, quantities[name])
        for name in sorted(set(REQUIRED_QUANTITIES) & set(quantities))
    }

    complete = not missing_quantities and all(
        result["complete"] for result in quantity_results.values()
    )
    return {
        "missing_quantities": missing_quantities,
        "quantity_results": quantity_results,
        "complete": complete,
    }
