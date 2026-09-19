#!/usr/bin/env python3
"""Cleanliness margin management against an apportioned contamination budget.

Anchor: ECSS-Q-ST-70-01C, cleanliness data. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A cleanliness budget is an end-of-life figure. It is apportioned across
the programme phases that sit between the last cleaning and the moment
the mission needs the surface clean, with a reserve held at programme
level against phases nobody has costed yet. Margin management is the
running answer to one question: how much of that allowance is left,
and which phase spent it.

Molecular deposition (areal mass, mg/m2) and particulate fallout
(obscuration, percentage area coverage) are separate ledgers with
separate limits and are never summed together.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

MOLECULAR = "molecular"
PARTICULATE = "particulate"

CONTAMINANT_KINDS = (MOLECULAR, PARTICULATE)

UNITS = {
    MOLECULAR: "mg/m2",
    PARTICULATE: "percent-area-coverage",
}

# Fraction of its own allocation a phase must still hold to read healthy.
HEALTHY_MARGIN_FRACTION = 0.20

# Representation tolerance: a phase landing exactly on its allocation
# must not read as an overrun because of float rounding.
TOL = 1e-9

PHASE_HEALTHY = "margin-healthy"
PHASE_THIN = "margin-thin"
PHASE_OVERRUN = "allocation-overrun"

VERDICT_WITHIN = "budget-within-margin"
VERDICT_THIN = "budget-margin-thin"
VERDICT_EXCEEDED = "budget-exceeded"


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_number(name, value, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be at least %s, got %r" % (name, minimum, value))
    return float(value)


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def contaminant_unit(kind):
    """Unit the ledger is kept in; the two kinds never convert."""
    if kind not in CONTAMINANT_KINDS:
        raise ValueError(
            "kind must be one of %s, got %r" % (", ".join(CONTAMINANT_KINDS), kind)
        )
    return UNITS[kind]


def normalise_phase(entry, index=0):
    """One phase allocation line, validated rather than defaulted."""
    if not isinstance(entry, dict):
        raise ValueError("phase[%d] must be a mapping, got %r" % (index, entry))
    return {
        "phase": _require_text("phase[%d].phase" % index, entry.get("phase")),
        "allocated": _require_number(
            "phase[%d].allocated" % index, entry.get("allocated"), minimum=0.0
        ),
        "consumed": _require_number(
            "phase[%d].consumed" % index, entry.get("consumed", 0.0), minimum=0.0
        ),
        "complete": _require_flag(
            "phase[%d].complete" % index, entry.get("complete", False)
        ),
    }


def normalise_phases(phases):
    """The apportionment, with duplicate phase names refused."""
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("phases must be a non-empty list, got %r" % (phases,))
    out = []
    seen = set()
    for i, entry in enumerate(phases):
        row = normalise_phase(entry, i)
        if row["phase"] in seen:
            raise ValueError("duplicate phase allocation: %r" % row["phase"])
        seen.add(row["phase"])
        out.append(row)
    return tuple(out)


def apportionment_check(budget, reserve_fraction, phases):
    """Do the phase allocations plus the reserve fit inside the budget."""
    total_budget = _require_number("budget", budget, minimum=0.0)
    if total_budget <= 0.0:
        raise ValueError("budget must be greater than zero, got %r" % (budget,))
    fraction = _require_number("reserve_fraction", reserve_fraction, minimum=0.0)
    if fraction >= 1.0:
        raise ValueError(
            "reserve_fraction must be below 1.0, got %r" % (reserve_fraction,)
        )
    rows = normalise_phases(phases)
    reserve = total_budget * fraction
    allocatable = total_budget - reserve
    allocated = sum(row["allocated"] for row in rows)
    over = allocated - allocatable
    return {
        "budget": total_budget,
        "reserve": reserve,
        "allocatable": allocatable,
        "allocated": allocated,
        "unallocated": allocatable - allocated,
        "over_subscribed_by": over if over > TOL else 0.0,
        "valid": over <= TOL,
    }


def phase_margin(allocated, consumed):
    """Margin a single phase still carries inside its own allocation."""
    alloc = _require_number("allocated", allocated, minimum=0.0)
    used = _require_number("consumed", consumed, minimum=0.0)
    margin = alloc - used
    if alloc == 0.0:
        fraction = 0.0 if used == 0.0 else -1.0
    else:
        fraction = margin / alloc
    if margin < -TOL:
        status = PHASE_OVERRUN
    elif fraction >= HEALTHY_MARGIN_FRACTION - TOL:
        status = PHASE_HEALTHY
    else:
        status = PHASE_THIN
    return {
        "allocated": alloc,
        "consumed": used,
        "margin": margin,
        "margin_fraction": fraction,
        "status": status,
    }


def consumption_rate(phases):
    """Average spend per COMPLETED phase; phases not started spend nothing."""
    rows = normalise_phases(phases)
    done = [row for row in rows if row["complete"]]
    if not done:
        return {
            "completed_phases": 0,
            "consumed_to_date": 0.0,
            "rate_per_completed_phase": None,
        }
    spent = sum(row["consumed"] for row in done)
    return {
        "completed_phases": len(done),
        "consumed_to_date": spent,
        "rate_per_completed_phase": spent / len(done),
    }


def forecast_end_of_programme(phases):
    """Total at completion: actuals where complete, allocations elsewhere."""
    rows = normalise_phases(phases)
    total = 0.0
    for row in rows:
        total += row["consumed"] if row["complete"] else max(
            row["allocated"], row["consumed"]
        )
    return total


def worst_phase(phases):
    """Phase whose overrun, if recovered, buys back the most allowance."""
    rows = normalise_phases(phases)
    worst = None
    worst_over = 0.0
    for row in rows:
        over = row["consumed"] - row["allocated"]
        if over > worst_over + TOL:
            worst_over = over
            worst = row["phase"]
    return {"phase": worst, "overrun": worst_over if worst else 0.0}


def manage_cleanliness_margin(case):
    """Full margin-management rollup for one contaminant ledger."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    item = _require_text("item", case.get("item"))
    kind = case.get("kind")
    unit = contaminant_unit(kind)
    phases = normalise_phases(case.get("phases"))
    apportionment = apportionment_check(
        case.get("budget"), case.get("reserve_fraction", 0.0), phases
    )
    per_phase = []
    for row in phases:
        margin = phase_margin(row["allocated"], row["consumed"])
        margin["phase"] = row["phase"]
        margin["complete"] = row["complete"]
        per_phase.append(margin)
    consumed = sum(row["consumed"] for row in phases)
    available = apportionment["allocatable"]
    programme_margin = available - consumed
    programme_fraction = programme_margin / available if available > 0.0 else -1.0
    forecast = forecast_end_of_programme(phases)
    findings = []
    if not apportionment["valid"]:
        findings.append(
            "apportionment over-subscribed by %.6g %s before any hardware is built"
            % (apportionment["over_subscribed_by"], unit)
        )
    for margin in per_phase:
        if margin["status"] == PHASE_OVERRUN:
            findings.append(
                "phase %s overran its allocation by %.6g %s"
                % (margin["phase"], -margin["margin"], unit)
            )
    if forecast > available + TOL:
        findings.append(
            "end-of-programme forecast of %.6g %s exceeds the allocatable %.6g %s"
            % (forecast, unit, available, unit)
        )
    if programme_margin < -TOL:
        verdict = VERDICT_EXCEEDED
    elif programme_fraction >= HEALTHY_MARGIN_FRACTION - TOL:
        verdict = VERDICT_WITHIN
    else:
        verdict = VERDICT_THIN
    return {
        "item": item,
        "kind": kind,
        "unit": unit,
        "apportionment": apportionment,
        "phases": tuple(per_phase),
        "consumed_to_date": consumed,
        "programme_margin": programme_margin,
        "programme_margin_fraction": programme_fraction,
        "consumption": consumption_rate(phases),
        "forecast_at_completion": forecast,
        "forecast_margin": available - forecast,
        "worst_phase": worst_phase(phases),
        "findings": tuple(findings),
        "compliant": programme_margin >= -TOL and apportionment["valid"],
        "verdict": verdict,
    }
