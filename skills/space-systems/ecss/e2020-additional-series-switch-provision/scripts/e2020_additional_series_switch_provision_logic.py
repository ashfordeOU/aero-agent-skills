#!/usr/bin/env python3
"""Additional series switch provision on a commandable power line.

Anchor: ECSS-E-ST-20-20C clause 5.2.13.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A commandable power line has one main switch. If that switch stays on
when it is told to open — welded contacts, a shorted output device, a
drive that never lets go — the line cannot be de-energised and the load
and its harness stay live through whatever comes next. The provision in
this clause is a second commandable switch placed IN SERIES with the
main one, so that opening either switch opens the line.

A second switch only buys that capability if four things hold, and each
is a separate question:

    1. ARRANGEMENT. The extra switch has to be in series. A switch in
       parallel with the main one cannot open the line at all; it is an
       availability provision, the opposite of this one.
    2. INDEPENDENCE. A second switch on the same command path or the
       same drive domain as the first fails with it. The provision is
       only worth its mass when the command and the drive that operate
       it are separate from the main switch's.
    3. CAPABILITY. The extra switch now carries the full line current
       continuously, holds off the bus voltage, and — the figure most
       often skipped — has to BREAK the prospective fault current. A
       switch that carries the line but cannot interrupt a fault is not
       a means of opening the line under the condition it exists for.
    4. COST. Two devices in series conduct in series, so their drops add
       and the sum has to stay inside the line's allowable drop.

The residual probability that the line still cannot be opened is not the
bare product of the two stuck-on probabilities. A shared cause — one
environment, one production lot, one drive rail sag — defeats both, so a
common-cause factor is folded in:

    residual = beta * max(p_main, p_aux) + (1 - beta)**2 * p_main * p_aux

with beta = 0 the fully independent product and beta = 1 the fully
shared case. The common-cause term takes the larger of the two unit
probabilities, because a shared cause cannot be less likely than the
more susceptible unit under it.

The derating factors, the common-cause factor and the allowable residual
below are declared project policy rather than physical constants; the
defaults here are a starting point a project substitutes its own values
into.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SWITCH_FIELDS = (
    "name",
    "command_path",
    "drive_domain",
    "technology",
    "continuous_rating_a",
    "voltage_rating_v",
    "breaking_capacity_a",
    "on_state_resistance_ohm",
    "stuck_on_probability",
)

LINE_FIELDS = (
    "load_current_a",
    "bus_voltage_v",
    "prospective_fault_current_a",
    "allowable_drop_v",
)

POLICY_FIELDS = (
    "current_derating_factor",
    "voltage_derating_factor",
    "common_cause_beta",
    "allowable_stuck_on_probability",
)

ARRANGEMENT_SERIES = "series"
ARRANGEMENT_PARALLEL = "parallel"
VALID_ARRANGEMENTS = (ARRANGEMENT_SERIES, ARRANGEMENT_PARALLEL)

VERDICT_ADEQUATE = "series-switch-provision-adequate"
VERDICT_INADEQUATE = "series-switch-provision-inadequate"

FINDING_NOT_IN_SERIES = "additional-switch-not-in-series-with-the-main-switch"
FINDING_SHARED_COMMAND = "additional-switch-shares-the-main-command-path"
FINDING_SHARED_DRIVE = "additional-switch-shares-the-main-drive-domain"
FINDING_CURRENT_RATING = "derated-continuous-rating-below-the-line-current"
FINDING_VOLTAGE_RATING = "derated-voltage-rating-below-the-bus-voltage"
FINDING_BREAKING = "breaking-capacity-below-the-prospective-fault-current"
FINDING_SERIES_DROP = "series-conduction-drop-above-the-allowable-line-drop"
FINDING_RESIDUAL = "residual-stuck-on-probability-above-the-allowable"

ADVISORY_SHARED_TECHNOLOGY = "both-switches-share-one-technology"
ADVISORY_THIN_INDEPENDENCE = "residual-dominated-by-the-common-cause-term"

# Placeholder devices and line: the shape a project's own data has to take.
DEFAULT_MAIN_SWITCH = {
    "name": "main-line-switch",
    "command_path": "command-path-a",
    "drive_domain": "drive-domain-a",
    "technology": "high-side-semiconductor-switch",
    "continuous_rating_a": 4.0,
    "voltage_rating_v": 100.0,
    "breaking_capacity_a": 12.0,
    "on_state_resistance_ohm": 0.035,
    "stuck_on_probability": 2.0e-4,
}

DEFAULT_ADDITIONAL_SWITCH = {
    "name": "additional-series-switch",
    "command_path": "command-path-b",
    "drive_domain": "drive-domain-b",
    "technology": "latching-relay",
    "continuous_rating_a": 4.0,
    "voltage_rating_v": 100.0,
    "breaking_capacity_a": 12.0,
    "on_state_resistance_ohm": 0.020,
    "stuck_on_probability": 5.0e-4,
    "arrangement": ARRANGEMENT_SERIES,
}

DEFAULT_LINE = {
    "load_current_a": 2.5,
    "bus_voltage_v": 28.0,
    "prospective_fault_current_a": 10.0,
    "allowable_drop_v": 0.5,
}

DEFAULT_PROVISION_POLICY = {
    "current_derating_factor": 0.75,
    "voltage_derating_factor": 0.80,
    "common_cause_beta": 0.10,
    "allowable_stuck_on_probability": 1.0e-4,
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


def _require_probability(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    return float(value)


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, required):
    """value >= required, absorbing floating-point representation error.

    A derated rating is a product of a rating and a factor, so a device
    meant to sit exactly on the line current can land a few units in the
    last place below it. The requirement is never relaxed; only the
    comparison tolerates the representation error.
    """
    return value >= required or math.isclose(
        value, required, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_switch(switch, require_arrangement=False):
    """Check one switch row carries the figures the provision is graded on."""
    if not isinstance(switch, dict):
        raise ValueError("switch must be a mapping, got %r" % (switch,))
    missing = [f for f in SWITCH_FIELDS if f not in switch]
    if require_arrangement and "arrangement" not in switch:
        missing.append("arrangement")
    if missing:
        raise ValueError("switch is missing figures: %s" % ", ".join(sorted(missing)))
    row = {
        "name": _require_label("name", switch["name"]),
        "command_path": _require_label("command_path", switch["command_path"]),
        "drive_domain": _require_label("drive_domain", switch["drive_domain"]),
        "technology": _require_label("technology", switch["technology"]),
        "continuous_rating_a": _require_positive(
            "continuous_rating_a", switch["continuous_rating_a"]
        ),
        "voltage_rating_v": _require_positive(
            "voltage_rating_v", switch["voltage_rating_v"]
        ),
        "breaking_capacity_a": _require_positive(
            "breaking_capacity_a", switch["breaking_capacity_a"]
        ),
        "on_state_resistance_ohm": _require_non_negative(
            "on_state_resistance_ohm", switch["on_state_resistance_ohm"]
        ),
        "stuck_on_probability": _require_probability(
            "stuck_on_probability", switch["stuck_on_probability"]
        ),
    }
    if row["breaking_capacity_a"] < row["continuous_rating_a"]:
        raise ValueError(
            "switch %s cannot break less than it carries (break %g A, carry %g A)"
            % (row["name"], row["breaking_capacity_a"], row["continuous_rating_a"])
        )
    if require_arrangement:
        arrangement = _require_label("arrangement", switch["arrangement"])
        if arrangement not in VALID_ARRANGEMENTS:
            raise ValueError(
                "arrangement must be one of %s, got %r"
                % (", ".join(VALID_ARRANGEMENTS), arrangement)
            )
        row["arrangement"] = arrangement
    return row


def validate_line(line):
    """Check the line the provision is being added to."""
    if not isinstance(line, dict):
        raise ValueError("line must be a mapping, got %r" % (line,))
    missing = [f for f in LINE_FIELDS if f not in line]
    if missing:
        raise ValueError("line is missing figures: %s" % ", ".join(sorted(missing)))
    row = {
        "load_current_a": _require_positive("load_current_a", line["load_current_a"]),
        "bus_voltage_v": _require_positive("bus_voltage_v", line["bus_voltage_v"]),
        "prospective_fault_current_a": _require_positive(
            "prospective_fault_current_a", line["prospective_fault_current_a"]
        ),
        "allowable_drop_v": _require_positive(
            "allowable_drop_v", line["allowable_drop_v"]
        ),
    }
    if row["prospective_fault_current_a"] < row["load_current_a"]:
        raise ValueError(
            "prospective fault current %g A is below the load current %g A"
            % (row["prospective_fault_current_a"], row["load_current_a"])
        )
    return row


def validate_provision_policy(policy):
    """Check the deratings, the common-cause factor and the allowable residual."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    missing = [f for f in POLICY_FIELDS if f not in policy]
    if missing:
        raise ValueError("policy is missing figures: %s" % ", ".join(sorted(missing)))
    current = _require_positive(
        "current_derating_factor", policy["current_derating_factor"]
    )
    if current > 1.0:
        raise ValueError(
            "current_derating_factor must not exceed one, got %r" % (current,)
        )
    voltage = _require_positive(
        "voltage_derating_factor", policy["voltage_derating_factor"]
    )
    if voltage > 1.0:
        raise ValueError(
            "voltage_derating_factor must not exceed one, got %r" % (voltage,)
        )
    beta = _require_probability("common_cause_beta", policy["common_cause_beta"])
    allowable = _require_positive(
        "allowable_stuck_on_probability", policy["allowable_stuck_on_probability"]
    )
    if allowable > 1.0:
        raise ValueError(
            "allowable_stuck_on_probability must not exceed one, got %r" % (allowable,)
        )
    return {
        "current_derating_factor": current,
        "voltage_derating_factor": voltage,
        "common_cause_beta": beta,
        "allowable_stuck_on_probability": allowable,
    }


def series_conduction_drop_v(main_switch, additional_switch, load_current_a):
    """Steady drop of the two devices conducting in series.

    Two switches in series conduct the same current, so their on-state
    drops add: V = I * (R_main + R_aux).
    """
    main = validate_switch(main_switch)
    aux = validate_switch(additional_switch)
    current = _require_positive("load_current_a", load_current_a)
    return current * (
        main["on_state_resistance_ohm"] + aux["on_state_resistance_ohm"]
    )


def residual_stuck_on_probability(
    main_probability, additional_probability, common_cause_beta
):
    """Probability the line still cannot be opened, with a shared cause.

    A shared cause defeats both devices at once, so the bare product of
    the two unit probabilities understates the residual. The shared term
    takes the larger unit probability: a cause common to both cannot be
    less likely than the more susceptible device under it.
    """
    p_main = _require_probability("main_probability", main_probability)
    p_aux = _require_probability("additional_probability", additional_probability)
    beta = _require_probability("common_cause_beta", common_cause_beta)
    shared = beta * max(p_main, p_aux)
    independent = ((1.0 - beta) ** 2) * p_main * p_aux
    return shared + independent


def assess_independence(main_switch, additional_switch):
    """Whether the extra switch can be commanded when the main one cannot."""
    main = validate_switch(main_switch)
    aux = validate_switch(additional_switch)
    shares_command = main["command_path"] == aux["command_path"]
    shares_drive = main["drive_domain"] == aux["drive_domain"]
    shares_technology = main["technology"] == aux["technology"]
    findings = []
    if shares_command:
        findings.append(
            "%s: both switches are commanded over %s"
            % (FINDING_SHARED_COMMAND, main["command_path"])
        )
    if shares_drive:
        findings.append(
            "%s: both switches are driven from %s"
            % (FINDING_SHARED_DRIVE, main["drive_domain"])
        )
    advisories = []
    if shares_technology:
        advisories.append(
            "%s: both switches are %s, so the common-cause factor should be "
            "raised rather than left at its default"
            % (ADVISORY_SHARED_TECHNOLOGY, main["technology"])
        )
    return {
        "shares_command_path": shares_command,
        "shares_drive_domain": shares_drive,
        "shares_technology": shares_technology,
        "independent": not (shares_command or shares_drive),
        "findings": findings,
        "advisories": advisories,
    }


def assess_switch_capability(switch, line, policy=DEFAULT_PROVISION_POLICY):
    """Whether one device can carry, hold off and break what the line offers."""
    row = validate_switch(switch)
    case = validate_line(line)
    rules = validate_provision_policy(policy)

    derated_current = row["continuous_rating_a"] * rules["current_derating_factor"]
    derated_voltage = row["voltage_rating_v"] * rules["voltage_derating_factor"]

    carries = _at_least(derated_current, case["load_current_a"])
    holds_off = _at_least(derated_voltage, case["bus_voltage_v"])
    breaks = _at_least(
        row["breaking_capacity_a"], case["prospective_fault_current_a"]
    )

    findings = []
    if not carries:
        findings.append(
            "%s: %s derates to %.4f A against a line current of %.4f A"
            % (FINDING_CURRENT_RATING, row["name"], derated_current, case["load_current_a"])
        )
    if not holds_off:
        findings.append(
            "%s: %s derates to %.4f V against a bus voltage of %.4f V"
            % (FINDING_VOLTAGE_RATING, row["name"], derated_voltage, case["bus_voltage_v"])
        )
    if not breaks:
        findings.append(
            "%s: %s breaks %.4f A against a prospective fault of %.4f A"
            % (
                FINDING_BREAKING,
                row["name"],
                row["breaking_capacity_a"],
                case["prospective_fault_current_a"],
            )
        )
    return {
        "name": row["name"],
        "derated_continuous_rating_a": derated_current,
        "derated_voltage_rating_v": derated_voltage,
        "current_slack_a": derated_current - case["load_current_a"],
        "voltage_slack_v": derated_voltage - case["bus_voltage_v"],
        "breaking_slack_a": row["breaking_capacity_a"]
        - case["prospective_fault_current_a"],
        "carries_line_current": carries,
        "holds_off_bus_voltage": holds_off,
        "breaks_fault_current": breaks,
        "capable": carries and holds_off and breaks,
        "findings": findings,
    }


def evaluate_series_switch_provision(
    main_switch=DEFAULT_MAIN_SWITCH,
    additional_switch=DEFAULT_ADDITIONAL_SWITCH,
    line=DEFAULT_LINE,
    policy=DEFAULT_PROVISION_POLICY,
):
    """Full clause 5.2.13.3.1 provision with a compliance verdict.

    The provision is adequate when the extra switch is in series with the
    main one, is commanded and driven independently of it, can carry,
    hold off and break what the line offers, the two drops together stay
    inside the allowable line drop, and the residual probability that the
    line cannot be opened stays under the allowable.
    """
    main = validate_switch(main_switch)
    aux = validate_switch(additional_switch, require_arrangement=True)
    case = validate_line(line)
    rules = validate_provision_policy(policy)

    in_series = aux["arrangement"] == ARRANGEMENT_SERIES
    independence = assess_independence(main, aux)
    main_capability = assess_switch_capability(main, case, rules)
    aux_capability = assess_switch_capability(aux, case, rules)

    drop = case["load_current_a"] * (
        main["on_state_resistance_ohm"] + aux["on_state_resistance_ohm"]
    )
    drop_within = _at_most(drop, case["allowable_drop_v"])

    residual = residual_stuck_on_probability(
        main["stuck_on_probability"],
        aux["stuck_on_probability"],
        rules["common_cause_beta"],
    )
    residual_within = _at_most(residual, rules["allowable_stuck_on_probability"])

    findings = []
    if not in_series:
        findings.append(
            "%s: the extra switch is declared %s, which cannot open the line"
            % (FINDING_NOT_IN_SERIES, aux["arrangement"])
        )
    findings.extend(independence["findings"])
    findings.extend(aux_capability["findings"])
    findings.extend(main_capability["findings"])
    if not drop_within:
        findings.append(
            "%s: the two devices drop %.4f V against an allowable %.4f V"
            % (FINDING_SERIES_DROP, drop, case["allowable_drop_v"])
        )
    if not residual_within:
        findings.append(
            "%s: residual %.3e against an allowable %.3e"
            % (FINDING_RESIDUAL, residual, rules["allowable_stuck_on_probability"])
        )

    shared_term = rules["common_cause_beta"] * max(
        main["stuck_on_probability"], aux["stuck_on_probability"]
    )
    advisories = list(independence["advisories"])
    if residual > 0.0 and shared_term > 0.5 * residual:
        advisories.append(
            "%s: the shared-cause term is %.3e of a %.3e residual, so adding a "
            "third device buys little" % (ADVISORY_THIN_INDEPENDENCE, shared_term, residual)
        )

    adequate = (
        in_series
        and independence["independent"]
        and main_capability["capable"]
        and aux_capability["capable"]
        and drop_within
        and residual_within
    )
    return {
        "verdict": VERDICT_ADEQUATE if adequate else VERDICT_INADEQUATE,
        "adequate": adequate,
        "in_series": in_series,
        "independence": independence,
        "main_capability": main_capability,
        "additional_capability": aux_capability,
        "series_drop_v": drop,
        "drop_slack_v": case["allowable_drop_v"] - drop,
        "residual_stuck_on_probability": residual,
        "residual_margin": rules["allowable_stuck_on_probability"] - residual,
        "improvement_factor": (
            main["stuck_on_probability"] / residual if residual > 0.0 else float("inf")
        ),
        "findings": findings,
        "advisories": advisories,
    }
