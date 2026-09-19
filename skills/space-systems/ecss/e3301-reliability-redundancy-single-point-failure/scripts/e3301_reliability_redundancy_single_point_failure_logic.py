#!/usr/bin/env python3
"""Reliability, redundancy and single-point failure control for a mechanism.

Anchor: ECSS-E-ST-33-01C clause 4.2.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A mechanism carries two obligations that are usually argued separately
and have to close together. The first is numerical: the mechanism must
demonstrate the reliability figure its mission-critical function was
apportioned. The second is structural: a single failure must not be
able to take the mission with it, and an active element -- anything
that moves, switches, releases or is commanded -- is held to a
redundancy rule of its own because its failure modes are wear driven
rather than random.

Redundancy schemes recognised here
    simplex          one element, nothing behind it
    active-parallel  n elements carrying the function together, any one
                     of which is sufficient
    cold-standby     one element running, n-1 unpowered spares brought
                     in by a switch that is itself imperfect

A single-point failure is a block whose loss defeats a mission-critical
function and which has no redundancy behind it. Clause 4.2.5 allows two
outcomes and no third: the failure mode is eliminated by design, or it
is formally accepted against a written rationale. A block recorded as
accepted with no rationale is not accepted, it is open.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REDUNDANCY_SCHEMES = ("simplex", "active-parallel", "cold-standby")
CRITICALITY_LEVELS = ("mission-critical", "mission-degrading", "benign")
DISPOSITIONS = ("eliminated", "accepted", "open")

DEFAULT_RELIABILITY_POLICY = {
    "required_mission_reliability": 0.99,
    "switch_reliability": 0.999,
    "active_elements_require_redundancy": True,
    "acceptance_requires_rationale": True,
    "minimum_rationale_characters": 20,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_non_negative(name, value)
    if value == 0.0:
        raise ValueError("%s must be greater than zero" % name)
    return value


def _require_probability(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if not 0.0 <= value <= 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_count(name, value, minimum):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A mechanism reliability is a product of exponentials, so a case
    built to sit exactly on its requirement can land a few units in the
    last place below it. The requirement is never lowered; only the
    comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_reliability_policy(policy):
    """Check an apportionment policy is complete and self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_probability(
        "required_mission_reliability", policy.get("required_mission_reliability")
    )
    _require_probability("switch_reliability", policy.get("switch_reliability"))
    for flag in ("active_elements_require_redundancy", "acceptance_requires_rationale"):
        if not isinstance(policy.get(flag), bool):
            raise ValueError("policy %s must be a boolean" % flag)
    _require_count(
        "minimum_rationale_characters",
        policy.get("minimum_rationale_characters"),
        1,
    )
    return policy


def validate_block(block):
    """Normalise one functional block of the mechanism reliability model."""
    if not isinstance(block, dict):
        raise ValueError("block must be a mapping, got %r" % (block,))
    identifier = block.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("block id must be a non-empty string, got %r" % (identifier,))
    scheme = _require_choice("scheme", block.get("scheme"), REDUNDANCY_SCHEMES)
    criticality = _require_choice(
        "criticality", block.get("criticality"), CRITICALITY_LEVELS
    )
    units = _require_count("units", block.get("units", 1), 1)
    if scheme == "simplex" and units != 1:
        raise ValueError("a simplex block carries exactly one unit, got %d" % units)
    if scheme != "simplex" and units < 2:
        raise ValueError("a %s block needs at least two units" % scheme)
    active = block.get("active_element")
    if not isinstance(active, bool):
        raise ValueError("block active_element must be a boolean, got %r" % (active,))
    disposition = block.get("disposition", "open")
    _require_choice("disposition", disposition, DISPOSITIONS)
    rationale = block.get("rationale", "")
    if not isinstance(rationale, str):
        raise ValueError("block rationale must be a string, got %r" % (rationale,))
    return {
        "id": identifier,
        "failure_rate_fit": _require_non_negative(
            "failure_rate_fit", block.get("failure_rate_fit")
        ),
        "scheme": scheme,
        "units": units,
        "criticality": criticality,
        "active_element": active,
        "disposition": disposition,
        "rationale": rationale,
    }


def block_reliability(block, mission_hours, switch_reliability=None):
    """Reliability of one block over the mission, given its scheme.

    Failure rates arrive in FIT, one failure per 1e9 operating hours.
    """
    record = validate_block(block)
    hours = _require_non_negative("mission_hours", mission_hours)
    if switch_reliability is None:
        switch_reliability = DEFAULT_RELIABILITY_POLICY["switch_reliability"]
    switch = _require_probability("switch_reliability", switch_reliability)
    load = record["failure_rate_fit"] * 1.0e-9 * hours
    single = math.exp(-load)
    if record["scheme"] == "simplex":
        return single
    if record["scheme"] == "active-parallel":
        return 1.0 - (1.0 - single) ** record["units"]
    spares = record["units"] - 1
    series = sum(
        (load ** k) / float(math.factorial(k)) * (switch ** k) for k in range(spares + 1)
    )
    return single * series


def mechanism_reliability(blocks, mission_hours, policy=DEFAULT_RELIABILITY_POLICY):
    """Series combination of every block in the mechanism function chain."""
    validate_reliability_policy(policy)
    if not isinstance(blocks, (list, tuple)) or not blocks:
        raise ValueError("blocks must be a non-empty sequence")
    seen = set()
    total = 1.0
    for block in blocks:
        record = validate_block(block)
        if record["id"] in seen:
            raise ValueError("duplicate block id %r in the model" % record["id"])
        seen.add(record["id"])
        total *= block_reliability(block, mission_hours, policy["switch_reliability"])
    return total


def redundancy_order(block):
    """How many independent units stand behind the function of a block."""
    record = validate_block(block)
    return record["units"]


def single_point_failures(blocks, policy=DEFAULT_RELIABILITY_POLICY):
    """Blocks whose single failure defeats a mission-critical function."""
    validate_reliability_policy(policy)
    if not isinstance(blocks, (list, tuple)) or not blocks:
        raise ValueError("blocks must be a non-empty sequence")
    found = []
    for block in blocks:
        record = validate_block(block)
        if record["units"] > 1:
            continue
        reasons = []
        if record["criticality"] == "mission-critical":
            reasons.append("loss defeats a mission-critical function")
        if policy["active_elements_require_redundancy"] and record["active_element"]:
            reasons.append("active element carried without a redundant unit")
        if reasons:
            found.append({"id": record["id"], "reasons": reasons})
    return found


def disposition_of(block, policy=DEFAULT_RELIABILITY_POLICY):
    """Effective disposition of a single-point failure and why.

    A record marked accepted without a rationale of substance is not an
    acceptance; it is reported back as open.
    """
    validate_reliability_policy(policy)
    record = validate_block(block)
    declared = record["disposition"]
    if declared != "accepted":
        return {"id": record["id"], "disposition": declared, "findings": []}
    if not policy["acceptance_requires_rationale"]:
        return {"id": record["id"], "disposition": "accepted", "findings": []}
    rationale = record["rationale"].strip()
    if len(rationale) < policy["minimum_rationale_characters"]:
        return {
            "id": record["id"],
            "disposition": "open",
            "findings": [
                "block %s is recorded as accepted with no rationale of substance; "
                "it is carried as open" % record["id"]
            ],
        }
    return {"id": record["id"], "disposition": "accepted", "findings": []}


def reliability_margin(achieved, required):
    """Signed distance of the demonstrated figure from the requirement."""
    return _require_probability("achieved", achieved) - _require_probability(
        "required", required
    )


def assess_reliability_case(case, policy=DEFAULT_RELIABILITY_POLICY):
    """Full clause 4.2.5 verdict: the figure and the failure-mode ledger."""
    validate_reliability_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    blocks = case.get("blocks")
    hours = _require_positive("mission_hours", case.get("mission_hours"))
    achieved = mechanism_reliability(blocks, hours, policy)
    required = _require_probability(
        "required_mission_reliability",
        case.get(
            "required_mission_reliability", policy["required_mission_reliability"]
        ),
    )
    figure_met = _at_least(achieved, required)
    findings = []
    by_id = {}
    for block in blocks:
        record = validate_block(block)
        by_id[record["id"]] = record
    spf = single_point_failures(blocks, policy)
    ledger = []
    open_count = 0
    accepted_count = 0
    eliminated_count = 0
    for entry in spf:
        verdict = disposition_of(by_id[entry["id"]], policy)
        findings.extend(verdict["findings"])
        ledger.append(
            {
                "id": entry["id"],
                "reasons": entry["reasons"],
                "disposition": verdict["disposition"],
            }
        )
        if verdict["disposition"] == "open":
            open_count += 1
            findings.append(
                "single-point failure %s is neither eliminated nor accepted"
                % entry["id"]
            )
        elif verdict["disposition"] == "accepted":
            accepted_count += 1
        else:
            eliminated_count += 1
    if not figure_met:
        findings.append(
            "demonstrated reliability %.6f is below the apportioned %.6f"
            % (achieved, required)
        )
    compliant = figure_met and open_count == 0
    if compliant:
        verdict = "reliability-case-closed"
    elif open_count:
        verdict = "single-point-failures-open"
    else:
        verdict = "reliability-figure-not-met"
    return {
        "achieved_reliability": achieved,
        "required_reliability": required,
        "reliability_margin": achieved - required,
        "figure_met": figure_met,
        "single_point_failures": ledger,
        "open_single_point_failures": open_count,
        "accepted_single_point_failures": accepted_count,
        "eliminated_single_point_failures": eliminated_count,
        "compliant": compliant,
        "verdict": verdict,
        "findings": findings,
    }
