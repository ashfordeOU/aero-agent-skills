#!/usr/bin/env python3
"""Retriggerable current limiter class selection for a protected load.

Anchor: ECSS-E-ST-20-20C clause 5.2.2.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A retriggerable current limiter (RLCL) behaves like a latching limiter
until it trips: instead of staying open until commanded on, it waits a
hold-off period and closes again by itself, repeating up to a bounded
number of attempts. The standard fixes a discrete set of RLCL classes
and each class carries the figures the selection is shown against:

    max_continuous_current_a     highest steady load current carried
                                 without entering limitation
    limit_min_a / limit_max_a    band the output is held to in limitation
    trip_off_time_min_s /        shortest and longest delay from entering
    trip_off_time_max_s          limitation to opening
    retrigger_off_time_min_s /   shortest and longest hold-off before the
    retrigger_off_time_max_s     class closes again on its own
    max_retrigger_attempts       attempts before the class gives up

Automatic retriggering changes the selection in two ways that a latching
limiter never raises:

    Repetition is thermal. A sustained downstream fault is not one pulse
    but a train of them, so the harness sees a MEAN current set by the
    retrigger duty cycle, and each attempt dumps an energy pulse into the
    fault. The binding duty is the LONGEST trip-off delay against the
    SHORTEST hold-off, which is the most fault current per unit time a
    compliant unit may deliver.

    Retriggering is also a start-up mechanism. A capacitive load that
    cannot finish charging inside one trip-off delay can still come up
    over several attempts, provided the charge it keeps across the
    hold-off accumulates and the attempts needed stay inside the class
    allowance. That count is the figure the selection has to produce.

Derating, charge retention across the hold-off and the attempt advisory
fraction are declared project policy, not physical constants. The class
table is a placeholder shape for the project's own procurement table.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CLASS_FIELDS = (
    "name",
    "max_continuous_current_a",
    "limit_min_a",
    "limit_max_a",
    "trip_off_time_min_s",
    "trip_off_time_max_s",
    "retrigger_off_time_min_s",
    "retrigger_off_time_max_s",
    "max_retrigger_attempts",
)

LOAD_FIELDS = (
    "steady_state_current_a",
    "load_capacitance_f",
    "bus_voltage_v",
    "harness_peak_rating_a",
    "harness_mean_rating_a",
    "fault_energy_allowance_j",
)

VERDICT_SELECTED = "class-selected"
VERDICT_NO_CLASS = "no-class-meets-the-performance-figures"

FINDING_CAPABILITY = "continuous-capability-short"
FINDING_PEAK = "upper-limit-above-harness-peak-rating"
FINDING_MEAN = "retrigger-mean-current-above-harness-thermal-rating"
FINDING_ENERGY = "fault-energy-per-attempt-above-allowance"
FINDING_ATTEMPTS = "start-up-needs-more-attempts-than-allowed"
FINDING_NO_CHARGE = "lower-limit-leaves-no-current-to-charge-the-load"
FINDING_ATTEMPT_BUDGET = "attempt-allowance-mostly-consumed-by-start-up"

# Placeholder class table: the shape a project's own table has to take.
DEFAULT_CLASS_TABLE = (
    {
        "name": "rlcl-a",
        "max_continuous_current_a": 0.5,
        "limit_min_a": 0.60,
        "limit_max_a": 0.85,
        "trip_off_time_min_s": 6.0e-3,
        "trip_off_time_max_s": 12.0e-3,
        "retrigger_off_time_min_s": 80.0e-3,
        "retrigger_off_time_max_s": 140.0e-3,
        "max_retrigger_attempts": 5,
    },
    {
        "name": "rlcl-b",
        "max_continuous_current_a": 1.0,
        "limit_min_a": 1.20,
        "limit_max_a": 1.70,
        "trip_off_time_min_s": 6.0e-3,
        "trip_off_time_max_s": 12.0e-3,
        "retrigger_off_time_min_s": 80.0e-3,
        "retrigger_off_time_max_s": 140.0e-3,
        "max_retrigger_attempts": 5,
    },
    {
        "name": "rlcl-c",
        "max_continuous_current_a": 2.0,
        "limit_min_a": 2.40,
        "limit_max_a": 3.40,
        "trip_off_time_min_s": 8.0e-3,
        "trip_off_time_max_s": 16.0e-3,
        "retrigger_off_time_min_s": 100.0e-3,
        "retrigger_off_time_max_s": 180.0e-3,
        "max_retrigger_attempts": 4,
    },
    {
        "name": "rlcl-d",
        "max_continuous_current_a": 4.0,
        "limit_min_a": 4.80,
        "limit_max_a": 6.80,
        "trip_off_time_min_s": 10.0e-3,
        "trip_off_time_max_s": 20.0e-3,
        "retrigger_off_time_min_s": 120.0e-3,
        "retrigger_off_time_max_s": 220.0e-3,
        "max_retrigger_attempts": 4,
    },
    {
        "name": "rlcl-e",
        "max_continuous_current_a": 8.0,
        "limit_min_a": 9.60,
        "limit_max_a": 13.60,
        "trip_off_time_min_s": 12.0e-3,
        "trip_off_time_max_s": 24.0e-3,
        "retrigger_off_time_min_s": 150.0e-3,
        "retrigger_off_time_max_s": 280.0e-3,
        "max_retrigger_attempts": 3,
    },
)

DEFAULT_SELECTION_POLICY = {
    "derating_factor": 0.80,
    "charge_retention": 0.90,
    "attempt_advisory_fraction": 0.75,
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


def _require_positive_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least one, got %r" % (name, value))
    return int(value)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    Duty cycles, mean currents and energies are built by division and
    multiplication, so a case meant to sit exactly on a limit can land a
    few units in the last place above it. The limit is never widened;
    only the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_selection_policy(policy):
    """Check derating, charge retention and the advisory fraction are sane."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    derating = _require_positive("derating_factor", policy.get("derating_factor"))
    if derating > 1.0:
        raise ValueError("derating_factor must not exceed one, got %r" % (derating,))
    retention = _require_positive("charge_retention", policy.get("charge_retention"))
    if retention > 1.0:
        raise ValueError("charge_retention must not exceed one, got %r" % (retention,))
    fraction = _require_positive(
        "attempt_advisory_fraction", policy.get("attempt_advisory_fraction")
    )
    if fraction > 1.0:
        raise ValueError(
            "attempt_advisory_fraction must not exceed one, got %r" % (fraction,)
        )
    return policy


def validate_rlcl_class_entry(entry):
    """Check one class row carries a consistent set of performance figures."""
    if not isinstance(entry, dict):
        raise ValueError("class entry must be a mapping, got %r" % (entry,))
    missing = [f for f in CLASS_FIELDS if f not in entry]
    if missing:
        raise ValueError(
            "class entry is missing figures: %s" % ", ".join(sorted(missing))
        )
    name = entry["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("class name must be a non-empty string, got %r" % (name,))
    carried = _require_positive(
        "max_continuous_current_a", entry["max_continuous_current_a"]
    )
    low = _require_positive("limit_min_a", entry["limit_min_a"])
    high = _require_positive("limit_max_a", entry["limit_max_a"])
    trip_low = _require_positive("trip_off_time_min_s", entry["trip_off_time_min_s"])
    trip_high = _require_positive("trip_off_time_max_s", entry["trip_off_time_max_s"])
    hold_low = _require_positive(
        "retrigger_off_time_min_s", entry["retrigger_off_time_min_s"]
    )
    hold_high = _require_positive(
        "retrigger_off_time_max_s", entry["retrigger_off_time_max_s"]
    )
    attempts = _require_positive_int(
        "max_retrigger_attempts", entry["max_retrigger_attempts"]
    )
    if high < low:
        raise ValueError(
            "class %s has an inverted limiting band (%g A .. %g A)" % (name, low, high)
        )
    if trip_high < trip_low:
        raise ValueError(
            "class %s has an inverted trip-off window (%g s .. %g s)"
            % (name, trip_low, trip_high)
        )
    if hold_high < hold_low:
        raise ValueError(
            "class %s has an inverted hold-off window (%g s .. %g s)"
            % (name, hold_low, hold_high)
        )
    if low <= carried:
        raise ValueError(
            "class %s would enter limitation at its own continuous rating "
            "(lower limit %g A, continuous %g A)" % (name, low, carried)
        )
    return {
        "name": name,
        "max_continuous_current_a": carried,
        "limit_min_a": low,
        "limit_max_a": high,
        "trip_off_time_min_s": trip_low,
        "trip_off_time_max_s": trip_high,
        "retrigger_off_time_min_s": hold_low,
        "retrigger_off_time_max_s": hold_high,
        "max_retrigger_attempts": attempts,
    }


def validate_rlcl_class_table(table):
    """Normalise a class table and require unique, ascending class rows."""
    if isinstance(table, dict) or not hasattr(table, "__iter__"):
        raise ValueError("class table must be a sequence of entries")
    rows = [validate_rlcl_class_entry(e) for e in table]
    if not rows:
        raise ValueError("class table is empty; nothing can be selected from it")
    seen = set()
    for row in rows:
        if row["name"] in seen:
            raise ValueError("class table repeats the name %r" % (row["name"],))
        seen.add(row["name"])
    for earlier, later in zip(rows, rows[1:]):
        if later["max_continuous_current_a"] <= earlier["max_continuous_current_a"]:
            raise ValueError(
                "class table is not ascending in continuous rating: %s then %s"
                % (earlier["name"], later["name"])
            )
    return tuple(rows)


def validate_load(load):
    """Check the protected load carries every figure the selection needs."""
    if not isinstance(load, dict):
        raise ValueError("load must be a mapping, got %r" % (load,))
    missing = [f for f in LOAD_FIELDS if f not in load]
    if missing:
        raise ValueError("load is missing figures: %s" % ", ".join(sorted(missing)))
    case = {name: _require_positive(name, load[name]) for name in LOAD_FIELDS}
    if case["harness_mean_rating_a"] > case["harness_peak_rating_a"]:
        raise ValueError(
            "harness mean rating %g A exceeds its peak rating %g A"
            % (case["harness_mean_rating_a"], case["harness_peak_rating_a"])
        )
    return case


def retrigger_duty_cycle(on_time_s, off_time_s):
    """Share of a sustained fault the class spends delivering current."""
    on_time = _require_positive("on_time_s", on_time_s)
    off_time = _require_positive("off_time_s", off_time_s)
    return on_time / (on_time + off_time)


def worst_case_duty_cycle(entry):
    """Highest duty a compliant unit of this class may present.

    The longest trip-off delay against the shortest hold-off: the most
    conduction per retrigger cycle the class allows.
    """
    row = validate_rlcl_class_entry(entry)
    return retrigger_duty_cycle(
        row["trip_off_time_max_s"], row["retrigger_off_time_min_s"]
    )


def mean_fault_current_a(limit_max_a, duty_cycle):
    """Current the harness sees on average through a retrigger train."""
    peak = _require_positive("limit_max_a", limit_max_a)
    duty = _require_positive("duty_cycle", duty_cycle)
    if duty > 1.0:
        raise ValueError("duty_cycle must not exceed one, got %r" % (duty,))
    return peak * duty


def fault_energy_per_attempt_j(bus_voltage_v, limit_max_a, on_time_s):
    """Energy one retrigger attempt delivers into a hard downstream fault."""
    voltage = _require_positive("bus_voltage_v", bus_voltage_v)
    current = _require_positive("limit_max_a", limit_max_a)
    on_time = _require_positive("on_time_s", on_time_s)
    return voltage * current * on_time


def startup_attempts_needed(entry, load, policy=DEFAULT_SELECTION_POLICY):
    """Retrigger attempts a capacitive load needs before it is up.

    Each attempt delivers the charging current left over after the load's
    own steady draw, for the shortest trip-off delay. Between attempts
    the load keeps a declared fraction of the charge it has accumulated.
    Returns the attempt count, or None when the class allowance runs out
    first.
    """
    validate_selection_policy(policy)
    row = validate_rlcl_class_entry(entry)
    case = validate_load(load)
    charging_current = row["limit_min_a"] - case["steady_state_current_a"]
    if charging_current <= 0.0:
        raise ValueError(
            "class %s leaves no current to charge the load: lower limit %g A "
            "against a steady draw of %g A"
            % (row["name"], row["limit_min_a"], case["steady_state_current_a"])
        )
    required_charge = case["load_capacitance_f"] * case["bus_voltage_v"]
    per_attempt = charging_current * row["trip_off_time_min_s"]
    retention = float(policy["charge_retention"])
    accumulated = 0.0
    for attempt in range(1, row["max_retrigger_attempts"] + 1):
        accumulated += per_attempt
        if _at_least(accumulated, required_charge):
            return attempt
        accumulated *= retention
    return None


def assess_rlcl_class(entry, load, policy=DEFAULT_SELECTION_POLICY):
    """Assess one class against every retrigger performance question."""
    validate_selection_policy(policy)
    row = validate_rlcl_class_entry(entry)
    case = validate_load(load)
    findings = []
    advisories = []

    capability = row["max_continuous_current_a"] * float(policy["derating_factor"])
    steady = case["steady_state_current_a"]
    carries = _at_most(steady, capability)
    if not carries:
        findings.append(
            "%s: steady load %.4f A exceeds the derated capability %.4f A"
            % (FINDING_CAPABILITY, steady, capability)
        )

    protects_peak = _at_most(row["limit_max_a"], case["harness_peak_rating_a"])
    if not protects_peak:
        findings.append(
            "%s: upper limiting current %.4f A is above the harness peak rating %.4f A"
            % (FINDING_PEAK, row["limit_max_a"], case["harness_peak_rating_a"])
        )

    duty = worst_case_duty_cycle(row)
    mean_current = mean_fault_current_a(row["limit_max_a"], duty)
    protects_mean = _at_most(mean_current, case["harness_mean_rating_a"])
    if not protects_mean:
        findings.append(
            "%s: retrigger duty %.4f gives a mean fault current of %.4f A "
            "against a harness thermal rating of %.4f A"
            % (FINDING_MEAN, duty, mean_current, case["harness_mean_rating_a"])
        )

    energy = fault_energy_per_attempt_j(
        case["bus_voltage_v"], row["limit_max_a"], row["trip_off_time_max_s"]
    )
    energy_ok = _at_most(energy, case["fault_energy_allowance_j"])
    if not energy_ok:
        findings.append(
            "%s: %.6f J per attempt against an allowance of %.6f J"
            % (FINDING_ENERGY, energy, case["fault_energy_allowance_j"])
        )

    charging_current = row["limit_min_a"] - steady
    if charging_current <= 0.0:
        attempts = None
        starts = False
        findings.append(
            "%s: lower limiting current %.4f A against a steady draw of %.4f A"
            % (FINDING_NO_CHARGE, row["limit_min_a"], steady)
        )
    else:
        attempts = startup_attempts_needed(row, case, policy)
        starts = attempts is not None
        if not starts:
            findings.append(
                "%s: the load is still charging after the %d attempts the class allows"
                % (FINDING_ATTEMPTS, row["max_retrigger_attempts"])
            )
        else:
            used = attempts / row["max_retrigger_attempts"]
            if used > float(policy["attempt_advisory_fraction"]):
                advisories.append(
                    "%s: start-up uses %d of the %d attempts allowed"
                    % (
                        FINDING_ATTEMPT_BUDGET,
                        attempts,
                        row["max_retrigger_attempts"],
                    )
                )

    return {
        "name": row["name"],
        "derated_capability_a": capability,
        "utilisation": steady / capability,
        "worst_case_duty_cycle": duty,
        "mean_fault_current_a": mean_current,
        "fault_energy_per_attempt_j": energy,
        "startup_attempts_needed": attempts,
        "attempt_allowance": row["max_retrigger_attempts"],
        "harness_peak_slack_a": case["harness_peak_rating_a"] - row["limit_max_a"],
        "harness_mean_slack_a": case["harness_mean_rating_a"] - mean_current,
        "carries_steady_load": carries,
        "protects_harness_peak": protects_peak,
        "protects_harness_mean": protects_mean,
        "energy_within_allowance": energy_ok,
        "permits_start_up": starts,
        "adequate": bool(
            carries and protects_peak and protects_mean and energy_ok and starts
        ),
        "findings": findings,
        "advisories": advisories,
    }


def candidate_rlcl_classes(table, load, policy=DEFAULT_SELECTION_POLICY):
    """Every class in the table that meets all five performance questions."""
    rows = validate_rlcl_class_table(table)
    return [
        a for a in (assess_rlcl_class(r, load, policy) for r in rows) if a["adequate"]
    ]


def select_rlcl_class(table, load, policy=DEFAULT_SELECTION_POLICY):
    """Full clause 5.2.2.1.1 class choice with a compliance verdict.

    The smallest adequate class wins: a larger class holds a higher fault
    current for longer at a comparable duty, so the harness and the bus
    absorb more from every retrigger train for no benefit.
    """
    rows = validate_rlcl_class_table(table)
    assessments = [assess_rlcl_class(r, load, policy) for r in rows]
    adequate = [a for a in assessments if a["adequate"]]
    if not adequate:
        reasons = []
        for a in assessments:
            reasons.extend("%s %s" % (a["name"], f) for f in a["findings"])
        return {
            "verdict": VERDICT_NO_CLASS,
            "selected": None,
            "assessments": assessments,
            "candidates": [],
            "findings": reasons,
            "advisories": [],
        }
    chosen = adequate[0]
    return {
        "verdict": VERDICT_SELECTED,
        "selected": chosen["name"],
        "selected_assessment": chosen,
        "assessments": assessments,
        "candidates": [a["name"] for a in adequate],
        "findings": [],
        "advisories": list(chosen["advisories"]),
    }
