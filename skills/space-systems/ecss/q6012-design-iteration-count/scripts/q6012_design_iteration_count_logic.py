#!/usr/bin/env python3
"""Planned development cycles before a microwave circuit design is frozen.

Anchor: ECSS-Q-ST-60-12C clause 7.1.3 (design iterations -- how many
development cycles the effort plans to run before the microwave circuit design
is frozen). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Derive the per-cycle convergence factor from the maturity of the process
   models the design is predicted with. A vendor-default model closes a
   smaller share of the predicted-to-required performance gap per cycle than a
   model calibrated on measured hardware, so it needs more cycles for the same
   gap.
2. Compute the cycles needed to bring the initial performance gap inside the
   acceptance gap, from the geometric closure the factor implies. The count is
   a whole number of foundry cycles, so the raw real-valued answer is rounded
   up -- with a named tolerance first, because a gap ratio that is an exact
   power of the factor lands on an integer that logarithms can put a few ULP
   either side of.
3. Apply the novelty floor. A design reusing a qualified cell set needs fewer
   cycles than a new circuit on a new process, and no analytic closure result
   is allowed to drop the plan below that floor.
4. Compute what the schedule can actually carry: the weeks left after the
   non-recurring front-end work, divided by the turnaround of one cycle.
5. Compare the planned cycle count against both the required count and the
   schedule capacity, and report whether the design can be frozen on the
   current plan, plus the residual gap the planned cycles actually reach.
"""

import math

__all__ = [
    "CONVERGENCE_FACTORS",
    "NOVELTY_FLOORS",
    "ITERATION_TOLERANCE",
    "convergence_factor",
    "novelty_floor",
    "iterations_for_gap",
    "residual_gap_db",
    "schedule_capacity",
    "plan_iterations",
]

# Model maturity -> the share of the performance gap that survives one cycle.
# A calibrated model converges faster because its prediction error is smaller,
# so more of the gap seen on the previous cycle is real and removable.
CONVERGENCE_FACTORS = {
    "measured-calibrated": 0.25,
    "process-calibrated": 0.40,
    "vendor-default": 0.60,
    "extrapolated": 0.80,
}

# Novelty -> the fewest cycles the design is allowed to plan whatever the
# analytic closure says. A new circuit on a new process cannot be frozen on a
# single run even if the first prediction looks close.
NOVELTY_FLOORS = {
    "qualified-heritage": 1,
    "derivative": 2,
    "new-design": 3,
}

# A gap ratio that is an exact power of the convergence factor gives an
# integer cycle count that log arithmetic can place a few ULP above it.
# Absorb that here rather than by padding the plan with a spare cycle.
ITERATION_TOLERANCE = 1e-9


def _require_real(value, label, positive=False, non_negative=False):
    """Return value as a finite float, raising on anything that is not one."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive and out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    if non_negative and out < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return out


def _normalise_token(token, label):
    """Return a lowercase hyphenated token, raising on an empty or non-string."""
    if not isinstance(token, str):
        raise ValueError("%s must be a string, got %r" % (label, token))
    out = token.strip().lower().replace("_", "-").replace(" ", "-")
    while "--" in out:
        out = out.replace("--", "-")
    if not out:
        raise ValueError("%s must not be empty" % label)
    return out


def convergence_factor(model_maturity):
    """Return the share of the performance gap surviving one design cycle."""
    key = _normalise_token(model_maturity, "model_maturity")
    if key not in CONVERGENCE_FACTORS:
        raise ValueError(
            "unknown model maturity %r; expected one of %s"
            % (model_maturity, ", ".join(sorted(CONVERGENCE_FACTORS)))
        )
    return CONVERGENCE_FACTORS[key]


def novelty_floor(novelty):
    """Return the fewest design cycles a novelty category may plan."""
    key = _normalise_token(novelty, "novelty")
    if key not in NOVELTY_FLOORS:
        raise ValueError(
            "unknown novelty category %r; expected one of %s"
            % (novelty, ", ".join(sorted(NOVELTY_FLOORS)))
        )
    return NOVELTY_FLOORS[key]


def iterations_for_gap(initial_gap_db, acceptance_gap_db, factor):
    """Return the whole cycles needed to close an initial gap to acceptance."""
    initial = _require_real(initial_gap_db, "initial_gap_db", non_negative=True)
    target = _require_real(acceptance_gap_db, "acceptance_gap_db", positive=True)
    ratio = _require_real(factor, "factor", positive=True)
    if ratio >= 1.0:
        raise ValueError(
            "convergence factor must be below one, got %r; a cycle that does "
            "not close any gap never converges" % (factor,)
        )
    if initial <= target:
        return 0
    raw = math.log(target / initial) / math.log(ratio)
    return max(0, int(math.ceil(raw - ITERATION_TOLERANCE)))


def residual_gap_db(initial_gap_db, factor, cycles):
    """Return the performance gap remaining after a whole number of cycles."""
    initial = _require_real(initial_gap_db, "initial_gap_db", non_negative=True)
    ratio = _require_real(factor, "factor", positive=True)
    if ratio >= 1.0:
        raise ValueError("convergence factor must be below one, got %r" % (factor,))
    if not isinstance(cycles, int) or isinstance(cycles, bool):
        raise ValueError("cycles must be an integer, got %r" % (cycles,))
    if cycles < 0:
        raise ValueError("cycles must not be negative, got %d" % cycles)
    return initial * (ratio ** cycles)


def schedule_capacity(available_weeks, cycle_weeks, front_end_weeks=0.0):
    """Return the whole design cycles the remaining schedule can carry."""
    available = _require_real(available_weeks, "available_weeks", non_negative=True)
    per_cycle = _require_real(cycle_weeks, "cycle_weeks", positive=True)
    front_end = _require_real(front_end_weeks, "front_end_weeks", non_negative=True)
    if front_end > available:
        return 0
    usable = available - front_end
    raw = usable / per_cycle
    return max(0, int(math.floor(raw + ITERATION_TOLERANCE)))


def plan_iterations(spec):
    """Run the clause 7.1.3 design-cycle planning assessment.

    spec keys: initial_gap_db, acceptance_gap_db, model_maturity, novelty,
    planned_cycles, available_weeks, cycle_weeks, optional front_end_weeks.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "initial_gap_db",
        "acceptance_gap_db",
        "model_maturity",
        "novelty",
        "planned_cycles",
        "available_weeks",
        "cycle_weeks",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    planned = spec["planned_cycles"]
    if not isinstance(planned, int) or isinstance(planned, bool):
        raise ValueError("planned_cycles must be an integer, got %r" % (planned,))
    if planned < 0:
        raise ValueError("planned_cycles must not be negative, got %d" % planned)

    factor = convergence_factor(spec["model_maturity"])
    floor_cycles = novelty_floor(spec["novelty"])
    closure_cycles = iterations_for_gap(
        spec["initial_gap_db"], spec["acceptance_gap_db"], factor
    )
    required = max(closure_cycles, floor_cycles)
    capacity = schedule_capacity(
        spec["available_weeks"],
        spec["cycle_weeks"],
        spec.get("front_end_weeks", 0.0),
    )
    residual = residual_gap_db(spec["initial_gap_db"], factor, planned)
    acceptance = _require_real(spec["acceptance_gap_db"], "acceptance_gap_db", positive=True)
    gap_closed = residual <= acceptance or math.isclose(
        residual, acceptance, rel_tol=0.0, abs_tol=ITERATION_TOLERANCE
    )

    findings = []
    if planned < required:
        driver = "novelty floor" if floor_cycles > closure_cycles else "gap closure"
        findings.append(
            "plan carries %d cycle(s) against %d required by the %s"
            % (planned, required, driver)
        )
    if capacity < required:
        findings.append(
            "schedule carries only %d cycle(s); %d are required, so the freeze "
            "date and the required cycle count disagree" % (capacity, required)
        )
    if planned > capacity:
        findings.append(
            "plan of %d cycle(s) exceeds the %d the schedule can run"
            % (planned, capacity)
        )
    if not gap_closed and planned >= required:
        findings.append(
            "planned cycles leave a residual gap of %.6g dB against an "
            "acceptance gap of %.6g dB" % (residual, acceptance)
        )

    return {
        "convergence_factor": factor,
        "closure_cycles": closure_cycles,
        "novelty_floor": floor_cycles,
        "required_cycles": required,
        "planned_cycles": planned,
        "schedule_capacity_cycles": capacity,
        "residual_gap_db": residual,
        "acceptance_gap_db": acceptance,
        "gap_closed": gap_closed,
        "freeze_supported": planned >= required and capacity >= planned and gap_closed,
        "findings": findings,
    }
