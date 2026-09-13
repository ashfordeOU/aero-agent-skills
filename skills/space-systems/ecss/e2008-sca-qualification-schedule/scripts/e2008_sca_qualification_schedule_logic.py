#!/usr/bin/env python3
"""Production and test schedule for qualifying a cell assembly design.

Anchor: ECSS-E-ST-20-08C clause 6.4.2. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

Qualifying a solar cell assembly design runs as an ordered schedule of
production and test steps, and the order is not presentation. A test that
runs before the step that made its article measures nothing; an
environmental exposure that runs before the baseline measurement leaves no
before-and-after to compare against; a final inspection that runs before the
exposure it is supposed to reveal is a signature on a blank page. So a
declared schedule is asked three questions:

    presence    is every step of the schedule actually in the sequence
    order       does each step follow the steps it depends on, rather than
                merely appearing somewhere in the list
    coupons     do the coupons the schedule starts with survive the steps
                that consume them, in the order those steps are declared

The three arms are ranked. An absent prerequisite is reported ahead of a
misplaced one, and a misplaced one ahead of a coupon shortfall, because
re-sizing a coupon batch for a sequence that is still in the wrong order
buys hardware for a schedule nobody can run.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STEP_KINDS = ("production", "test", "documentation")

REQUIRED_SCHEDULE_STEPS = {
    "coupon-manufacture": {
        "kind": "production",
        "prerequisites": (),
        "coupons_consumed": 0,
    },
    "initial-visual-inspection": {
        "kind": "test",
        "prerequisites": ("coupon-manufacture",),
        "coupons_consumed": 0,
    },
    "initial-electrical-measurement": {
        "kind": "test",
        "prerequisites": ("coupon-manufacture",),
        "coupons_consumed": 0,
    },
    "thermal-cycling": {
        "kind": "test",
        "prerequisites": (
            "initial-visual-inspection",
            "initial-electrical-measurement",
        ),
        "coupons_consumed": 2,
    },
    "humidity-exposure": {
        "kind": "test",
        "prerequisites": (
            "initial-visual-inspection",
            "initial-electrical-measurement",
        ),
        "coupons_consumed": 2,
    },
    "electrostatic-discharge-test": {
        "kind": "test",
        "prerequisites": ("initial-electrical-measurement",),
        "coupons_consumed": 1,
    },
    "final-electrical-measurement": {
        "kind": "test",
        "prerequisites": ("thermal-cycling", "humidity-exposure"),
        "coupons_consumed": 0,
    },
    "final-visual-inspection": {
        "kind": "test",
        "prerequisites": ("thermal-cycling", "humidity-exposure"),
        "coupons_consumed": 0,
    },
    "qualification-report": {
        "kind": "documentation",
        "prerequisites": (
            "final-electrical-measurement",
            "final-visual-inspection",
            "electrostatic-discharge-test",
        ),
        "coupons_consumed": 0,
    },
}

STEP_ORDERED = "step-ordered"
STEP_PREREQUISITE_ABSENT = "step-prerequisite-absent"
STEP_OUT_OF_ORDER = "step-out-of-order"
STEP_COUPONS_EXHAUSTED = "step-coupons-exhausted"

SCHEDULE_RUNNABLE = "qualification-schedule-runnable"
SCHEDULE_NOT_RUNNABLE = "qualification-schedule-not-runnable"

DEFAULT_SCHEDULE_POLICY = {
    "coupon_margin": 1,
    "require_documentation_last": True,
    "allow_extra_coupons": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_schedule_policy(policy):
    """Check a qualification schedule policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_count("coupon_margin", policy.get("coupon_margin"), 0)
    _require_flag(
        "require_documentation_last", policy.get("require_documentation_last")
    )
    _require_flag("allow_extra_coupons", policy.get("allow_extra_coupons"))
    return policy


def required_schedule_steps():
    """The production and test steps a qualification schedule owes."""
    return {
        name: {
            "kind": body["kind"],
            "prerequisites": tuple(body["prerequisites"]),
            "coupons_consumed": body["coupons_consumed"],
        }
        for name, body in REQUIRED_SCHEDULE_STEPS.items()
    }


def step_definition(step):
    """Kind, prerequisites and coupon consumption of one schedule step."""
    name = _require_text("step", step)
    if name not in REQUIRED_SCHEDULE_STEPS:
        raise ValueError("unknown schedule step %s" % name)
    return required_schedule_steps()[name]


def step_prerequisites(step):
    """The steps one schedule step depends on."""
    return step_definition(step)["prerequisites"]


def minimum_coupon_demand(policy=DEFAULT_SCHEDULE_POLICY):
    """Coupons a full schedule consumes, plus the declared margin."""
    validate_schedule_policy(policy)
    consumed = sum(
        body["coupons_consumed"] for body in REQUIRED_SCHEDULE_STEPS.values()
    )
    return consumed + int(policy["coupon_margin"])


def validate_sequence(sequence):
    """Check a declared sequence names known steps exactly once each."""
    if not isinstance(sequence, (list, tuple)) or not sequence:
        raise ValueError("sequence must be a non-empty sequence of step names")
    ordered = []
    for entry in sequence:
        name = _require_text("step", entry)
        if name not in REQUIRED_SCHEDULE_STEPS:
            raise ValueError("sequence names an unknown step %s" % name)
        if name in ordered:
            raise ValueError("sequence declares %s twice" % name)
        ordered.append(name)
    return ordered


def ordering_status(sequence):
    """Which prerequisites are absent from, or placed after, each step."""
    ordered = validate_sequence(sequence)
    position = {name: index for index, name in enumerate(ordered)}
    report = {}
    for name in ordered:
        absent = []
        late = []
        for prerequisite in step_prerequisites(name):
            if prerequisite not in position:
                absent.append(prerequisite)
            elif position[prerequisite] > position[name]:
                late.append(prerequisite)
        report[name] = {
            "step": name,
            "position": position[name],
            "absent_prerequisites": sorted(absent),
            "late_prerequisites": sorted(late),
            "ordered": not absent and not late,
        }
    return report


def coupon_flow(sequence, initial_coupons, policy=DEFAULT_SCHEDULE_POLICY):
    """Walk the declared order and report the coupon balance at each step."""
    validate_schedule_policy(policy)
    ordered = validate_sequence(sequence)
    balance = _require_count("initial_coupons", initial_coupons, 0)
    trace = []
    exhausted = []
    for name in ordered:
        consumed = step_definition(name)["coupons_consumed"]
        opening = balance
        balance -= consumed
        short = balance < 0
        if short:
            exhausted.append(name)
            balance = 0
        trace.append(
            {
                "step": name,
                "opening_balance": opening,
                "coupons_consumed": consumed,
                "closing_balance": balance,
                "sufficient": not short,
            }
        )
    demand = minimum_coupon_demand(policy)
    findings = []
    for name in exhausted:
        findings.append("the schedule runs out of coupons at %s" % name)
    if initial_coupons < demand:
        findings.append(
            "the schedule starts with %d coupons against a demand of %d "
            "including margin" % (initial_coupons, demand)
        )
    surplus = initial_coupons - demand
    if surplus > 0 and not policy["allow_extra_coupons"]:
        findings.append(
            "the schedule starts with %d coupons more than the demand" % surplus
        )
    return {
        "initial_coupons": initial_coupons,
        "required_coupons": demand,
        "trace": trace,
        "exhausted_at": exhausted,
        "surplus_coupons": surplus,
        "meets_demand": initial_coupons >= demand,
        "findings": findings,
    }


def assess_schedule_step(step, ordering, flow_by_step):
    """Ranked verdict for one step of a declared qualification schedule."""
    name = _require_text("step", step)
    if name not in ordering:
        raise ValueError("step %s is not part of the ordering report" % name)
    if name not in flow_by_step:
        raise ValueError("step %s is not part of the coupon trace" % name)
    place = ordering[name]
    flow = flow_by_step[name]
    findings = []
    if place["absent_prerequisites"]:
        findings.append(
            "%s runs without %s, which the schedule never declares"
            % (name, ", ".join(place["absent_prerequisites"]))
        )
    if place["late_prerequisites"]:
        findings.append(
            "%s is placed before %s, which it depends on"
            % (name, ", ".join(place["late_prerequisites"]))
        )
    if not flow["sufficient"]:
        findings.append(
            "%s needs %d coupons and the schedule has %d left"
            % (name, flow["coupons_consumed"], flow["opening_balance"])
        )
    if place["absent_prerequisites"]:
        verdict = STEP_PREREQUISITE_ABSENT
    elif place["late_prerequisites"]:
        verdict = STEP_OUT_OF_ORDER
    elif not flow["sufficient"]:
        verdict = STEP_COUPONS_EXHAUSTED
    else:
        verdict = STEP_ORDERED
    return {
        "step": name,
        "kind": step_definition(name)["kind"],
        "position": place["position"],
        "ordering": place,
        "coupons": flow,
        "verdict": verdict,
        "runnable": verdict == STEP_ORDERED,
        "findings": findings,
    }


def assess_qualification_schedule(case, policy=DEFAULT_SCHEDULE_POLICY):
    """Full clause 6.4.2 sweep over a declared qualification schedule."""
    validate_schedule_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    ordered = validate_sequence(case.get("sequence"))
    initial = _require_count("initial_coupons", case.get("initial_coupons"), 0)
    ordering = ordering_status(ordered)
    flow = coupon_flow(ordered, initial, policy)
    flow_by_step = {entry["step"]: entry for entry in flow["trace"]}
    records = [
        assess_schedule_step(name, ordering, flow_by_step) for name in ordered
    ]
    missing = sorted(set(REQUIRED_SCHEDULE_STEPS) - set(ordered))
    grouped = {}
    for record in records:
        grouped.setdefault(record["verdict"], []).append(record["step"])
    findings = []
    for record in records:
        findings.extend(record["findings"])
    for name in missing:
        findings.append("the schedule never declares %s" % name)
    documentation_last = True
    if policy["require_documentation_last"]:
        documentation_steps = [
            name
            for name in ordered
            if step_definition(name)["kind"] == "documentation"
        ]
        for name in documentation_steps:
            if ordering[name]["position"] != len(ordered) - 1:
                documentation_last = False
                findings.append(
                    "%s is a documentation step and does not close the schedule"
                    % name
                )
    for text in flow["findings"]:
        if text not in findings:
            findings.append(text)
    open_steps = sorted(
        set(missing) | {record["step"] for record in records if not record["runnable"]}
    )
    runnable = (
        not open_steps
        and documentation_last
        and flow["meets_demand"]
        and not flow["exhausted_at"]
    )
    completeness = len(ordered) / float(len(REQUIRED_SCHEDULE_STEPS))
    return {
        "verdict": SCHEDULE_RUNNABLE if runnable else SCHEDULE_NOT_RUNNABLE,
        "step_records": records,
        "grouped_by_verdict": grouped,
        "declared_sequence": ordered,
        "missing_steps": missing,
        "open_steps": open_steps,
        "coupons": flow,
        "documentation_closes_schedule": documentation_last,
        "completeness_fraction": completeness,
        "fully_declared": _at_least(completeness, 1.0),
        "findings": findings,
    }
