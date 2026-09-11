"""
Cue-card engineering logic — ECSS-E-ST-10-11C §4.9.2.

Cue cards are compact quick-reference documents for crew use during
emergency and contingency operations on crewed space systems.
All functions are deterministic and offline; stdlib only.
"""

from typing import Dict, List, Optional, Set

# Maximum steps per card face — human-factors brevity limit for time-critical reading
MAX_STEPS_PER_FACE = 9

# Maximum character length per step for crew legibility under degraded conditions
MAX_STEP_CHARS = 80

# Recognized scenario types
SCENARIO_TYPES = {"emergency", "contingency"}

# Recognized severity levels (CRITICAL = immediate life-safety threat)
SEVERITY_LEVELS = {"CRITICAL", "HIGH", "MEDIUM"}

# Recognized imperative action verbs for step compliance checking
ACTION_VERBS = {
    "activate", "check", "close", "command", "confirm", "connect",
    "decrease", "deploy", "disable", "disconnect", "enable", "execute",
    "increase", "inhibit", "initiate", "isolate", "monitor", "move",
    "open", "operate", "place", "position", "press", "proceed", "record",
    "release", "remove", "report", "reset", "rotate", "seal", "select", "set",
    "shut", "start", "stop", "switch", "toggle", "turn", "verify",
    "wait", "warn",
}


class CueCardError(ValueError):
    """Raised when a cue card fails a structural or content check."""


def validate_card_structure(card: Dict) -> List[str]:
    """
    Check that a cue card dict contains all required fields.
    Returns a list of finding strings; empty list means structurally valid.
    Required fields: title, scenario_type, severity, steps.
    """
    required = {"title", "scenario_type", "severity", "steps"}
    findings = []
    missing = required - set(card.keys())
    for field in sorted(missing):
        findings.append(f"missing required field: {field!r}")
    return findings


def check_step_count(steps: List, max_steps: int = MAX_STEPS_PER_FACE) -> List[str]:
    """
    Verify the step list does not exceed the maximum steps per card face.
    Returns a list of findings; empty list means within limit.
    """
    findings = []
    if not isinstance(steps, list):
        findings.append("steps must be a list")
        return findings
    if len(steps) == 0:
        findings.append("card must have at least one step")
    elif len(steps) > max_steps:
        findings.append(
            f"step count {len(steps)} exceeds maximum {max_steps} per card face"
        )
    return findings


def check_step_length(step: str, max_chars: int = MAX_STEP_CHARS) -> List[str]:
    """
    Verify a single step is within the legibility character limit.
    Returns a list of findings.
    """
    findings = []
    if not isinstance(step, str):
        findings.append(f"step must be a string, got {type(step).__name__}")
        return findings
    if len(step.strip()) == 0:
        findings.append("step must not be blank")
    elif len(step) > max_chars:
        findings.append(
            f"step length {len(step)} exceeds maximum {max_chars} characters"
        )
    return findings


def check_action_verb(step: str, action_verbs: Optional[Set[str]] = None) -> List[str]:
    """
    Verify that a step begins with a recognized imperative action verb.
    Returns a list of findings; empty list means the step is compliant.
    """
    if action_verbs is None:
        action_verbs = ACTION_VERBS
    findings = []
    if not isinstance(step, str) or len(step.strip()) == 0:
        findings.append("step is empty or not a string")
        return findings
    first_word = step.strip().split()[0].lower().rstrip(".,;:")
    if first_word not in action_verbs:
        findings.append(
            f"step does not begin with a recognized action verb: {first_word!r}"
        )
    return findings


def categorize_card(card: Dict) -> str:
    """
    Return the scenario category string for a card dict.
    Raises CueCardError for an unrecognized scenario type.
    Valid return values: 'emergency', 'contingency'.
    """
    scenario_type = card.get("scenario_type", "")
    if scenario_type not in SCENARIO_TYPES:
        raise CueCardError(
            f"unrecognized scenario type {scenario_type!r}; "
            f"must be one of {sorted(SCENARIO_TYPES)}"
        )
    return scenario_type


def validate_severity(card: Dict) -> List[str]:
    """
    Verify the card has a recognized severity level.
    Returns a list of findings; empty list means severity is valid.
    """
    findings = []
    severity = card.get("severity", "")
    if not severity:
        findings.append("severity field is missing or empty")
    elif severity not in SEVERITY_LEVELS:
        findings.append(
            f"unrecognized severity {severity!r}; "
            f"must be one of {sorted(SEVERITY_LEVELS)}"
        )
    return findings


def audit_card(card: Dict) -> Dict:
    """
    Run all checks on a single cue card dict and return an audit result.

    Returns a dict with keys:
        title    (str)  — card title or '<no title>'
        findings (list) — list of finding strings; empty means all checks pass
        passed   (bool) — True when findings is empty
    """
    findings = []
    findings.extend(validate_card_structure(card))

    if "steps" in card:
        findings.extend(check_step_count(card["steps"]))
        if isinstance(card["steps"], list):
            for i, step in enumerate(card["steps"], start=1):
                for finding in check_step_length(step):
                    findings.append(f"step {i}: {finding}")
                for finding in check_action_verb(step):
                    findings.append(f"step {i}: {finding}")

    findings.extend(validate_severity(card))

    try:
        categorize_card(card)
    except CueCardError as exc:
        findings.append(str(exc))

    return {
        "title": card.get("title", "<no title>"),
        "findings": findings,
        "passed": len(findings) == 0,
    }


def check_card_set_coverage(cards: List[Dict], required_scenarios: List[str]) -> List[str]:
    """
    Verify that a set of cue cards covers every required scenario title.
    Comparison is case-insensitive on the card title field.
    Returns a list of findings for uncovered scenarios.
    """
    covered = {card.get("title", "").lower() for card in cards}
    findings = []
    for scenario in required_scenarios:
        if scenario.lower() not in covered:
            findings.append(f"no cue card found for required scenario: {scenario!r}")
    return findings


def compute_card_metrics(card: Dict) -> Dict:
    """
    Compute legibility metrics for a cue card.
    Returns a dict with step_count, avg_step_chars, max_step_chars.
    Steps field must be a list; non-string entries are skipped.
    """
    steps = card.get("steps", [])
    if not isinstance(steps, list) or len(steps) == 0:
        return {"step_count": 0, "avg_step_chars": 0.0, "max_step_chars": 0}
    lengths = [len(s) for s in steps if isinstance(s, str)]
    if not lengths:
        return {"step_count": 0, "avg_step_chars": 0.0, "max_step_chars": 0}
    return {
        "step_count": len(lengths),
        "avg_step_chars": sum(lengths) / len(lengths),
        "max_step_chars": max(lengths),
    }
