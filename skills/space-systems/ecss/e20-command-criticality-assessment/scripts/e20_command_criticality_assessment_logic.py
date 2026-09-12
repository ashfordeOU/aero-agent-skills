#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 4.1.3 -- spacecraft command criticality rating.

Deterministic, offline, stdlib-only helpers that rate a command from the
worst credible effect of its inadvertent or erroneous execution, apply
the equipment-level modifiers (reversibility, onboard recovery), confirm
the rating at system level (single-string critical function, multi-
subsystem propagation, bounded redundancy downgrade) and check the
protection the retained level demands.

Modelling assumptions (documented so a reviewer can challenge them):
  * Severity is taken from a fixed, ordered effect vocabulary; an
    unrecognized effect term is rejected rather than mapped to a
    default rank.
  * A modifier moves the level by whole steps and saturates at the ends
    of the level scale.
  * Ground-only recovery is not a downgrade; only autonomous onboard
    recovery bounds the consequence without an operator in the loop.

No network, no third-party imports, no randomness.
"""

# Ordered effect vocabulary; the value is the severity rank.
EFFECT_SEVERITY = {
    "no-effect": 0,
    "transient-nuisance": 1,
    "degraded-performance": 2,
    "loss-of-redundancy": 3,
    "loss-of-function": 4,
    "loss-of-mission": 5,
    "loss-of-vehicle": 6,
}

EFFECT_ALIASES = {
    "none": "no-effect",
    "nuisance": "transient-nuisance",
    "degraded": "degraded-performance",
    "redundancy-loss": "loss-of-redundancy",
    "function-loss": "loss-of-function",
    "mission-loss": "loss-of-mission",
    "vehicle-loss": "loss-of-vehicle",
    "catastrophic": "loss-of-vehicle",
}

# Criticality scale, lowest first.
LEVELS = (
    "non-critical",
    "mission-significant",
    "mission-critical",
    "hazardous",
)

# Entry level for each severity rank (index = rank).
SEVERITY_TO_LEVEL_INDEX = (0, 0, 1, 1, 2, 2, 3)

RECOVERY_MODES = ("none", "ground", "autonomous")

REQUIRED_PROTECTIONS = {
    "non-critical": (),
    "mission-significant": ("command-verification",),
    "mission-critical": ("command-verification", "arm-and-execute"),
    "hazardous": (
        "command-verification",
        "arm-and-execute",
        "command-authentication",
        "inhibit-status-telemetry",
    ),
}

REQUIRED_COMMAND_KEYS = ("id", "effect", "reversible", "onboard_recovery")


def _bool(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def _level_index(level):
    if not isinstance(level, str) or level not in LEVELS:
        raise ValueError("uncategorized criticality level %r" % (level,))
    return LEVELS.index(level)


def _shift(index, steps):
    return max(0, min(len(LEVELS) - 1, index + steps))


def categorize_command_effect(effect):
    """Normalise an effect term and return (canonical-term, severity)."""
    if not isinstance(effect, str):
        raise ValueError("command effect must be a string, got %r" % (effect,))
    key = effect.strip().lower().replace("_", "-").replace(" ", "-")
    if not key:
        raise ValueError("command effect must not be empty")
    key = EFFECT_ALIASES.get(key, key)
    if key not in EFFECT_SEVERITY:
        raise ValueError(
            "uncategorized command effect %r; expected one of %s"
            % (effect, sorted(EFFECT_SEVERITY))
        )
    return key, EFFECT_SEVERITY[key]


def rate_equipment_criticality(command):
    """Equipment-level criticality level of one command."""
    if not isinstance(command, dict):
        raise ValueError("command must be a mapping, got %r" % (type(command).__name__,))
    missing = [k for k in REQUIRED_COMMAND_KEYS if k not in command]
    if missing:
        raise ValueError("command missing required keys: %s" % ", ".join(sorted(missing)))
    effect, severity = categorize_command_effect(command["effect"])
    reversible = _bool(command["reversible"], "reversible")
    recovery = command["onboard_recovery"]
    if not isinstance(recovery, str) or recovery.strip().lower() not in RECOVERY_MODES:
        raise ValueError(
            "onboard_recovery must be one of %s, got %r" % (list(RECOVERY_MODES), recovery)
        )
    recovery = recovery.strip().lower()

    index = SEVERITY_TO_LEVEL_INDEX[severity]
    rationale = ["entry level %s from effect %s" % (LEVELS[index], effect)]
    if not reversible:
        index = _shift(index, 1)
        rationale.append("raised one step: effect is irreversible")
    if recovery == "autonomous":
        index = _shift(index, -1)
        rationale.append("lowered one step: autonomous onboard recovery")
    elif recovery == "ground":
        rationale.append("no downgrade: recovery depends on a ground pass")

    return {
        "id": command["id"],
        "effect": effect,
        "severity": severity,
        "equipment_level": LEVELS[index],
        "rationale": rationale,
    }


def bound_redundancy_downgrade(level, severity, redundancy):
    """Apply, at most one step, a downgrade claimed from redundancy."""
    index = _level_index(level)
    if not isinstance(severity, int) or isinstance(severity, bool):
        raise ValueError("severity must be an integer rank, got %r" % (severity,))
    if severity not in range(len(SEVERITY_TO_LEVEL_INDEX)):
        raise ValueError("severity rank %r outside the effect vocabulary" % (severity,))
    if not isinstance(redundancy, dict):
        raise ValueError("redundancy must be a mapping")
    for key in ("claimed", "path_available", "same_command_word"):
        if key not in redundancy:
            raise ValueError("redundancy missing required key %r" % (key,))
    claimed = _bool(redundancy["claimed"], "claimed")
    available = _bool(redundancy["path_available"], "path_available")
    same_word = _bool(redundancy["same_command_word"], "same_command_word")
    if not claimed:
        return {"level": LEVELS[index], "note": "no redundancy downgrade claimed"}
    if not available:
        return {"level": LEVELS[index], "note": "downgrade rejected: no redundant path on record"}
    if same_word:
        return {
            "level": LEVELS[index],
            "note": "downgrade rejected: the same command word drives both paths",
        }
    lowered = _shift(index, -1)
    if severity >= EFFECT_SEVERITY["loss-of-function"] and lowered < 1:
        lowered = 1
        return {"level": LEVELS[lowered], "note": "downgrade floored at mission-significant"}
    return {"level": LEVELS[lowered], "note": "downgrade applied, one step"}


def escalate_to_system_level(equipment_level, context):
    """Confirm or escalate an equipment-level rating in its system context."""
    index = _level_index(equipment_level)
    if not isinstance(context, dict):
        raise ValueError("context must be a mapping")
    for key in ("single_string_critical_function", "subsystems_affected"):
        if key not in context:
            raise ValueError("context missing required key %r" % (key,))
    single_string = _bool(
        context["single_string_critical_function"], "single_string_critical_function"
    )
    affected = context["subsystems_affected"]
    if isinstance(affected, bool) or not isinstance(affected, int):
        raise ValueError("subsystems_affected must be an integer, got %r" % (affected,))
    if affected < 1:
        raise ValueError("subsystems_affected must be at least 1, got %d" % affected)
    notes = []
    if single_string:
        floor = LEVELS.index("mission-critical")
        if index < floor:
            index = floor
            notes.append("escalated to mission-critical: single-string critical function")
    if affected >= 2:
        raised = _shift(index, 1)
        if raised != index:
            notes.append("raised one step: effect propagates across %d subsystems" % affected)
            index = raised
    if not notes:
        notes.append("equipment-level rating confirmed at system level")
    return {"system_level": LEVELS[index], "notes": notes}


def check_protection_measures(level, protections):
    """List the protections the retained level demands but does not have."""
    if level not in REQUIRED_PROTECTIONS:
        raise ValueError("uncategorized criticality level %r" % (level,))
    if not isinstance(protections, (list, tuple)):
        raise ValueError("protections must be a list of protection names")
    have = set()
    for item in protections:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("protection entry %r must be a non-empty string" % (item,))
        have.add(item.strip().lower())
    return [p for p in REQUIRED_PROTECTIONS[level] if p not in have]


def assess_command(command):
    """Full clause 4.1.3 rating of one command, equipment then system."""
    equipment = rate_equipment_criticality(command)
    context = command.get("system_context")
    if context is None:
        raise ValueError("command %r missing system_context" % (command.get("id"),))
    system = escalate_to_system_level(equipment["equipment_level"], context)
    redundancy = command.get("redundancy")
    if redundancy is None:
        redundancy = {"claimed": False, "path_available": False, "same_command_word": False}
    bounded = bound_redundancy_downgrade(
        system["system_level"], equipment["severity"], redundancy
    )
    retained = bounded["level"]
    missing = check_protection_measures(retained, command.get("protections", []))
    findings = [
        "missing protection for %s command: %s" % (retained, name) for name in missing
    ]
    return {
        "id": equipment["id"],
        "effect": equipment["effect"],
        "severity": equipment["severity"],
        "equipment_level": equipment["equipment_level"],
        "system_level": system["system_level"],
        "retained_level": retained,
        "escalated": LEVELS.index(system["system_level"])
        > LEVELS.index(equipment["equipment_level"]),
        "missing_protections": missing,
        "notes": equipment["rationale"] + system["notes"] + [bounded["note"]],
        "findings": findings,
        "compliant": not findings,
    }


def assess_command_set(commands):
    """Rate a command set and summarise the levels and the protection gaps."""
    if not isinstance(commands, list):
        raise ValueError("commands must be a list")
    if not commands:
        raise ValueError("commands must not be empty")
    results = [assess_command(item) for item in commands]
    seen = set()
    counts = {level: 0 for level in LEVELS}
    for result in results:
        if result["id"] in seen:
            raise ValueError("duplicate command id %r" % (result["id"],))
        seen.add(result["id"])
        counts[result["retained_level"]] += 1
    non_compliant = [r["id"] for r in results if not r["compliant"]]
    return {
        "assessed": len(results),
        "level_counts": counts,
        "escalated": [r["id"] for r in results if r["escalated"]],
        "non_compliant": non_compliant,
        "results": results,
        "all_compliant": not non_compliant,
    }
