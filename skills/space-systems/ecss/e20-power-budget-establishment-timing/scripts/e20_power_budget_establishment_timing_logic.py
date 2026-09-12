#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 5.2.1 power budget establishment and phase
review (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical and electronic engineering standard requires the spacecraft
power budget -- the rolled-up electrical demand of every consumer plus
the margin held against it -- to be established during phase B, when
the architecture is fixed but the equipment set is still immature, and
to be re-reviewed at each later project phase as predicted consumptions
are replaced by measured ones. The margin carried on an individual
equipment line reflects that line's design maturity (a flight-proven
unit needs less than a newly developed one), while the margin held at
subsystem level is the figure that must survive each phase gate and is
allowed to shrink only as the design matures.

This module implements maturity-dependent equipment margining, the
roll-up into a subsystem budget, the phase-dependent system margin
requirement, the establishment-timing check and the review-cadence
check. It does not size the power source, model degradation, or set
project-specific margin values beyond the defaults below.
"""

# Ordered project phases used for establishment and review timing.
PROJECT_PHASES = ("phase_0", "phase_a", "phase_b", "phase_c", "phase_d", "phase_e")

# Clause 5.2.1 anchor: the budget is established in phase B.
BUDGET_ESTABLISHMENT_PHASE = "phase_b"

# Margin added on top of an equipment's predicted consumption, keyed by
# the design maturity category of that equipment.
MATURITY_MARGIN = {
    "flight_proven": 0.05,
    "modified_existing": 0.10,
    "new_development": 0.20,
}

# System-level margin the rolled-up budget must still hold at each phase
# gate. The requirement tightens as predictions are replaced by measured
# consumptions; phases before establishment carry no requirement.
PHASE_SYSTEM_MARGIN = {
    "phase_b": 0.20,
    "phase_c": 0.10,
    "phase_d": 0.05,
    "phase_e": 0.02,
}

FINDING_KEYS = ("establishment", "review_cadence", "margin")


def phase_index(phase):
    """Position of a project phase in PROJECT_PHASES. Raises ValueError
    for a phase outside the recognized set."""
    try:
        return PROJECT_PHASES.index(phase)
    except ValueError:
        raise ValueError(
            "uncategorized project phase %r under E-ST-20C clause 5.2.1" % (phase,)
        )


def maturity_margin_fraction(maturity_category):
    """Margin fraction carried by one equipment line, from its design
    maturity category. Raises ValueError for an unrecognized category."""
    if maturity_category not in MATURITY_MARGIN:
        raise ValueError(
            "uncategorized equipment maturity %r; expected one of %s"
            % (maturity_category, sorted(MATURITY_MARGIN))
        )
    return MATURITY_MARGIN[maturity_category]


def equipment_budget_line(equipment_id, predicted_power_w, maturity_category):
    """One budget line: predicted consumption plus its maturity margin.

    Returns a dict with the predicted power, the margin fraction and
    power, and the budgeted power actually carried in the roll-up.
    Raises ValueError for a blank identifier, a negative predicted power
    or an unrecognized maturity category."""
    if not equipment_id:
        raise ValueError("equipment_id must be a non-empty identifier")
    if predicted_power_w < 0:
        raise ValueError("predicted_power_w must be >= 0")
    fraction = maturity_margin_fraction(maturity_category)
    margin_power_w = predicted_power_w * fraction
    return {
        "equipment_id": equipment_id,
        "predicted_power_w": predicted_power_w,
        "maturity_category": maturity_category,
        "margin_fraction": fraction,
        "margin_power_w": margin_power_w,
        "budgeted_power_w": predicted_power_w + margin_power_w,
    }


def roll_up_budget(lines):
    """Subsystem roll-up of equipment budget lines.

    Returns totals for predicted power, equipment margin and budgeted
    power, plus the line count. Raises ValueError for an empty line list
    or a duplicated equipment identifier."""
    lines = list(lines)
    if not lines:
        raise ValueError("roll_up_budget needs at least one equipment budget line")
    seen = set()
    for line in lines:
        equipment_id = line["equipment_id"]
        if equipment_id in seen:
            raise ValueError("duplicate equipment_id %r in budget" % (equipment_id,))
        seen.add(equipment_id)
    return {
        "predicted_power_w": sum(line["predicted_power_w"] for line in lines),
        "margin_power_w": sum(line["margin_power_w"] for line in lines),
        "budgeted_power_w": sum(line["budgeted_power_w"] for line in lines),
        "line_count": len(lines),
    }


def required_system_margin(phase):
    """System-level margin required at a phase gate. Raises ValueError
    for a phase before establishment (no budget exists yet) or for an
    unrecognized phase."""
    if phase not in PHASE_SYSTEM_MARGIN:
        if phase in PROJECT_PHASES:
            raise ValueError(
                "no system margin requirement at %r; the budget is established "
                "in %s" % (phase, BUDGET_ESTABLISHMENT_PHASE)
            )
        raise ValueError("uncategorized project phase %r" % (phase,))
    return PHASE_SYSTEM_MARGIN[phase]


def achieved_system_margin(available_power_w, budgeted_power_w):
    """Fraction of the available power still unspent once the budgeted
    demand is subtracted. Negative when the budget overruns supply.
    Raises ValueError for a non-positive availability or a negative
    budgeted demand."""
    if available_power_w <= 0:
        raise ValueError("available_power_w must be > 0")
    if budgeted_power_w < 0:
        raise ValueError("budgeted_power_w must be >= 0")
    return (available_power_w - budgeted_power_w) / available_power_w


def establishment_findings(established_phase):
    """Findings on when the budget was first established: none recorded,
    or recorded later than the clause 5.2.1 phase. Establishing earlier
    than phase B is acceptable and returns no finding."""
    if established_phase is None:
        return [
            {
                "issue": "power_budget_not_established",
                "required_phase": BUDGET_ESTABLISHMENT_PHASE,
            }
        ]
    if phase_index(established_phase) > phase_index(BUDGET_ESTABLISHMENT_PHASE):
        return [
            {
                "issue": "power_budget_established_late",
                "established_phase": established_phase,
                "required_phase": BUDGET_ESTABLISHMENT_PHASE,
            }
        ]
    return []


def expected_review_phases(established_phase, current_phase):
    """Phases at which the established budget owes a review: every phase
    after the later of the establishment phase and phase B, up to and
    including the current phase. Raises ValueError when the current
    phase precedes establishment."""
    start = max(
        phase_index(established_phase), phase_index(BUDGET_ESTABLISHMENT_PHASE)
    )
    end = phase_index(current_phase)
    if end < phase_index(established_phase):
        raise ValueError(
            "current_phase %r precedes established_phase %r"
            % (current_phase, established_phase)
        )
    return tuple(PROJECT_PHASES[start + 1 : end + 1])


def review_cadence_findings(established_phase, current_phase, reviewed_phases):
    """Findings for phase gates that passed without a budget review.

    reviewed_phases: the phases at which a review was actually held.
    Raises ValueError for an unrecognized phase anywhere in the inputs."""
    recorded = set()
    for phase in reviewed_phases:
        phase_index(phase)
        recorded.add(phase)
    findings = []
    for phase in expected_review_phases(established_phase, current_phase):
        if phase not in recorded:
            findings.append(
                {"issue": "budget_phase_review_skipped", "phase": phase}
            )
    return findings


def margin_findings(phase, available_power_w, budgeted_power_w):
    """Finding list for the system margin held at a phase gate: flags an
    achieved margin below the requirement for that phase."""
    required = required_system_margin(phase)
    achieved = achieved_system_margin(available_power_w, budgeted_power_w)
    if achieved < required:
        return [
            {
                "issue": "system_margin_below_phase_requirement",
                "phase": phase,
                "achieved_margin": achieved,
                "required_margin": required,
            }
        ]
    return []


def budget_review(record):
    """Full clause 5.2.1 review of one power budget record.

    record: {"established_phase": str | None, "current_phase": str,
    "reviewed_phases": [str], "equipment": [{"equipment_id",
    "predicted_power_w", "maturity_category"}], "available_power_w"}.
    Returns the roll-up, the priced lines, and a finding list under each
    of FINDING_KEYS. Raises ValueError through the helpers above."""
    established = record.get("established_phase")
    current = record["current_phase"]
    lines = [
        equipment_budget_line(
            item["equipment_id"], item["predicted_power_w"], item["maturity_category"]
        )
        for item in record.get("equipment", [])
    ]
    rollup = roll_up_budget(lines)
    cadence = (
        []
        if established is None
        else review_cadence_findings(
            established, current, record.get("reviewed_phases", ())
        )
    )
    return {
        "lines": lines,
        "rollup": rollup,
        "establishment": establishment_findings(established),
        "review_cadence": cadence,
        "margin": margin_findings(
            current, record["available_power_w"], rollup["budgeted_power_w"]
        ),
    }


def is_budget_compliant(review):
    """True when every finding list in a budget_review result is empty --
    the budget was established on time, reviewed at each later gate, and
    still holds the margin its phase requires."""
    return all(len(review[key]) == 0 for key in FINDING_KEYS)
