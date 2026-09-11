#!/usr/bin/env python3
"""ECSS-E-ST-10C §4.6.7 operations design ergonomics (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false):
operations design ergonomics under ECSS-E-ST-10C §4.6.7 covers three
interlocking concerns: procedure design (step count, decision-branch
density, and time-critical verification), automation allocation (matching
function response-time requirements and consequence severity to the
correct automation level), and error tolerance (ensuring that safety-
critical commands require more than one independent inhibit action before
execution). This module implements procedure assessment, automation-level
adequacy checking, and error-tolerance inhibit verification; it does not
define the mission-specific response-time budgets, the automation
architecture design, or the human-factors verification methods themselves.
"""

# ---------------------------------------------------------------------------
# Constants (paraphrased from ECSS-E-ST-10C §4.6.7 ergonomics guidance)
# ---------------------------------------------------------------------------
MAX_PROCEDURE_STEPS = 15            # recommended upper bound; exceeded → split
MAX_DECISION_BRANCHES = 3           # branches at one step; exceeded → restructure
MIN_SAFETY_INHIBITS = 2             # minimum independent inhibit actions for safety-critical commands

HUMAN_RESPONSE_FLOOR_S = 2.0        # below this, human action in the response path is not reliable
SUPERVISED_RESPONSE_FLOOR_S = 10.0  # below this, purely manual allocation is not adequate

# Ordered from least to most autonomous; .index() gives the level's rank.
AUTOMATION_LEVELS = ("manual", "supervised", "automated")
CONSEQUENCE_LEVELS = ("low", "medium", "high", "catastrophic")


# ---------------------------------------------------------------------------
# Procedure assessment
# ---------------------------------------------------------------------------

def assess_procedure(proc_id, steps):
    """Ergonomic findings for one operational procedure.

    steps: iterable of dicts with keys:
      "step_id": str,
      "has_verification": bool,
      "decision_branches": int  (optional, default 0),
      "is_time_critical": bool  (optional, default False).
    Returns a list of finding dicts; empty list means compliant.
    """
    steps = list(steps)
    findings = []

    if len(steps) > MAX_PROCEDURE_STEPS:
        findings.append({
            "issue": "procedure_step_count_exceeds_limit",
            "proc_id": proc_id,
            "step_count": len(steps),
            "limit": MAX_PROCEDURE_STEPS,
        })

    for step in steps:
        step_id = step["step_id"]
        branches = step.get("decision_branches", 0)
        time_critical = step.get("is_time_critical", False)
        has_verification = step.get("has_verification", False)

        if branches > MAX_DECISION_BRANCHES:
            findings.append({
                "issue": "decision_branch_density_exceeds_limit",
                "proc_id": proc_id,
                "step_id": step_id,
                "decision_branches": branches,
                "limit": MAX_DECISION_BRANCHES,
            })

        if time_critical and not has_verification:
            findings.append({
                "issue": "time_critical_step_missing_verification",
                "proc_id": proc_id,
                "step_id": step_id,
            })

    return findings


# ---------------------------------------------------------------------------
# Automation allocation
# ---------------------------------------------------------------------------

def recommended_automation_level(required_response_time_s, consequence):
    """Minimum acceptable automation level for a function.

    required_response_time_s: float or None (None means not time-critical).
    consequence: one of CONSEQUENCE_LEVELS.
    Returns one of AUTOMATION_LEVELS.
    Raises ValueError for an unrecognized consequence level.
    """
    if consequence not in CONSEQUENCE_LEVELS:
        raise ValueError(
            "unrecognized consequence level %r; expected one of %s"
            % (consequence, CONSEQUENCE_LEVELS)
        )

    if required_response_time_s is not None:
        if required_response_time_s < HUMAN_RESPONSE_FLOOR_S:
            return "automated"
        if required_response_time_s < SUPERVISED_RESPONSE_FLOOR_S:
            return "supervised"

    if consequence == "catastrophic":
        return "supervised"

    return "manual"


def automation_allocation_violations(function_id, required_response_time_s, consequence, proposed_level):
    """Violation list (empty if compliant) for an automation allocation.

    Raises ValueError for an unrecognized proposed_level or consequence.
    Does not mutate inputs.
    """
    if proposed_level not in AUTOMATION_LEVELS:
        raise ValueError(
            "unrecognized automation level %r; expected one of %s"
            % (proposed_level, AUTOMATION_LEVELS)
        )

    minimum = recommended_automation_level(required_response_time_s, consequence)
    min_index = AUTOMATION_LEVELS.index(minimum)
    proposed_index = AUTOMATION_LEVELS.index(proposed_level)

    if proposed_index < min_index:
        return [{
            "issue": "automation_level_below_minimum",
            "function_id": function_id,
            "proposed_level": proposed_level,
            "minimum_required": minimum,
            "required_response_time_s": required_response_time_s,
            "consequence": consequence,
        }]
    return []


# ---------------------------------------------------------------------------
# Error tolerance
# ---------------------------------------------------------------------------

def error_tolerance_violations(command_id, inhibit_count, is_safety_critical):
    """Violation list (empty if compliant) for a command's inhibit coverage.

    inhibit_count: number of independent inhibit actions required before the
    command executes. Raises ValueError for a negative count.
    """
    if inhibit_count < 0:
        raise ValueError("inhibit_count must be >= 0 for command %r" % (command_id,))

    if is_safety_critical and inhibit_count < MIN_SAFETY_INHIBITS:
        return [{
            "issue": "safety_critical_command_insufficient_inhibits",
            "command_id": command_id,
            "inhibit_count": inhibit_count,
            "minimum_required": MIN_SAFETY_INHIBITS,
        }]
    return []


# ---------------------------------------------------------------------------
# Aggregate review
# ---------------------------------------------------------------------------

def ops_ergo_review(procedures, allocations, commands):
    """Full §4.6.7 operations ergonomics review.

    procedures: iterable of {"proc_id": str, "steps": [step_dict, ...]}.
    allocations: iterable of {"function_id": str,
                               "required_response_time_s": float | None,
                               "consequence": str,
                               "proposed_level": str}.
    commands: iterable of {"command_id": str, "inhibit_count": int,
                            "is_safety_critical": bool}.
    Returns {"procedure": [...], "automation": [...], "error_tolerance": [...]}.
    Raises ValueError for unrecognized level or consequence codes.
    """
    procedure_findings = []
    for proc in procedures:
        procedure_findings.extend(
            assess_procedure(proc["proc_id"], proc["steps"])
        )

    automation_findings = []
    for alloc in allocations:
        automation_findings.extend(
            automation_allocation_violations(
                alloc["function_id"],
                alloc["required_response_time_s"],
                alloc["consequence"],
                alloc["proposed_level"],
            )
        )

    error_tolerance_findings = []
    for cmd in commands:
        error_tolerance_findings.extend(
            error_tolerance_violations(
                cmd["command_id"],
                cmd["inhibit_count"],
                cmd["is_safety_critical"],
            )
        )

    return {
        "procedure": procedure_findings,
        "automation": automation_findings,
        "error_tolerance": error_tolerance_findings,
    }


def is_ops_ergo_compliant(review):
    """True when all three categories in an ops_ergo_review result are empty."""
    return all(len(findings) == 0 for findings in review.values())
