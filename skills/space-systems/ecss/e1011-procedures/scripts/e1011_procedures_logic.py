#!/usr/bin/env python3
"""ECSS-E-ST-10-11C §4.9.1 operational procedure development, format
validation, and HFE review (paraphrase, not verbatim copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
human factors engineering standard's procedure-development clause requires
that operational procedures for space systems carry a clearly stated
purpose, a complete set of preconditions, numbered action steps each
introduced by an imperative verb, interspersed verification checkpoints
to limit operator cognitive load, and a defined expected outcome; each
procedure must be typed into one of the accepted operational categories
before its format is validated; and the complete draft must pass an HFE
review for step clarity, word-count bounds, and checkpoint spacing before
it may be approved for use. This module implements procedure field
completeness checks, step format validation (imperative-verb lead,
word-count bound, compound-action detection), checkpoint-spacing
enforcement, step-ID uniqueness verification, and an overall approval
determination; it does not define the specific task-analysis or
crew-workload models that feed into the upstream HFE requirements.
"""

PROCEDURE_TYPES = frozenset(
    {"nominal", "contingency", "maintenance", "test", "launch_countdown", "on_orbit"}
)

REQUIRED_PROCEDURE_FIELDS = (
    "procedure_id",
    "title",
    "purpose",
    "procedure_type",
    "preconditions",
    "steps",
    "expected_outcome",
)

REQUIRED_STEP_FIELDS = ("step_id", "action")

# Imperative verbs that constitute an acceptable step opener.
STEP_ACTION_VERBS = frozenset({
    "activate", "adjust", "align", "apply", "check", "close", "command",
    "configure", "confirm", "connect", "deactivate", "deploy", "disable",
    "disconnect", "document", "enable", "enter", "execute", "initialize",
    "initiate", "inspect", "install", "load", "lock", "measure", "monitor",
    "note", "notify", "open", "perform", "place", "power", "press", "read",
    "record", "release", "remove", "report", "reset", "retract", "rotate",
    "run", "secure", "select", "send", "set", "start", "stop", "switch",
    "tag", "terminate", "test", "unlock", "unload", "update", "validate",
    "verify", "wait",
})

# HFE thresholds derived from §4.9.1 human-factors requirements (paraphrased).
HFE_MAX_STEP_WORDS = 30
HFE_MAX_STEPS_WITHOUT_CHECKPOINT = 10

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"


def _check_field_present(obj, field, context):
    """Return a finding dict if field is absent or empty in obj, else None."""
    if field not in obj:
        return {
            "severity": SEVERITY_ERROR,
            "issue": "missing_field",
            "field": field,
            "context": context,
        }
    value = obj[field]
    if value is None or value == "" or value == [] or value == {}:
        return {
            "severity": SEVERITY_ERROR,
            "issue": "empty_field",
            "field": field,
            "context": context,
        }
    return None


def validate_procedure_fields(procedure):
    """Return a list of field-level findings (dicts with severity, issue,
    field, context) for missing or empty required procedure fields.
    Does not mutate procedure."""
    findings = []
    for field in REQUIRED_PROCEDURE_FIELDS:
        finding = _check_field_present(procedure, field, "procedure")
        if finding is not None:
            findings.append(finding)
    return findings


def validate_step(step, step_index):
    """Return a list of findings for one step dict.

    Checks: required fields present; action begins with a recognized
    imperative verb; action word count does not exceed HFE_MAX_STEP_WORDS;
    compound-action pattern (two imperative verbs joined by ' and ')
    is flagged as a warning. Raises ValueError when step is not a dict."""
    if not isinstance(step, dict):
        raise ValueError("step at index %d is not a dict" % step_index)
    findings = []
    for field in REQUIRED_STEP_FIELDS:
        finding = _check_field_present(step, field, "step[%d]" % step_index)
        if finding is not None:
            findings.append(finding)
    action = step.get("action", "")
    if not isinstance(action, str) or not action.strip():
        return findings
    words = action.strip().split()
    first_word = words[0].rstrip(".,;:").lower()
    if first_word not in STEP_ACTION_VERBS:
        findings.append({
            "severity": SEVERITY_WARNING,
            "issue": "step_action_not_imperative_verb",
            "step_id": step.get("step_id", step_index),
            "first_word": first_word,
        })
    if len(words) > HFE_MAX_STEP_WORDS:
        findings.append({
            "severity": SEVERITY_ERROR,
            "issue": "step_action_exceeds_word_limit",
            "step_id": step.get("step_id", step_index),
            "word_count": len(words),
            "limit": HFE_MAX_STEP_WORDS,
        })
    lower_action = action.lower()
    if " and " in lower_action:
        parts = lower_action.split(" and ", 1)
        left_first = (
            parts[0].strip().split()[0].rstrip(".,;:")
            if parts[0].strip()
            else ""
        )
        right_first = (
            parts[1].strip().split()[0].rstrip(".,;:")
            if parts[1].strip()
            else ""
        )
        if left_first in STEP_ACTION_VERBS and right_first in STEP_ACTION_VERBS:
            findings.append({
                "severity": SEVERITY_WARNING,
                "issue": "compound_action_should_split",
                "step_id": step.get("step_id", step_index),
            })
    return findings


def check_checkpoint_spacing(steps):
    """Return a list of HFE findings for checkpoint spacing. An error is
    added when more than HFE_MAX_STEPS_WITHOUT_CHECKPOINT consecutive
    steps pass without one where is_checkpoint is True. After each
    violation the counter resets to avoid cascading duplicates.
    Does not mutate steps."""
    findings = []
    consecutive = 0
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        if step.get("is_checkpoint", False):
            consecutive = 0
        else:
            consecutive += 1
            if consecutive > HFE_MAX_STEPS_WITHOUT_CHECKPOINT:
                findings.append({
                    "severity": SEVERITY_ERROR,
                    "issue": "checkpoint_spacing_exceeded",
                    "step_index": i,
                    "consecutive_non_checkpoint_steps": consecutive,
                    "limit": HFE_MAX_STEPS_WITHOUT_CHECKPOINT,
                })
                consecutive = 0
    return findings


def check_step_id_uniqueness(steps):
    """Return a list of findings for duplicate step IDs within a procedure.
    Does not mutate steps."""
    seen = {}
    findings = []
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        step_id = step.get("step_id")
        if step_id is None:
            continue
        if step_id in seen:
            findings.append({
                "severity": SEVERITY_ERROR,
                "issue": "duplicate_step_id",
                "step_id": step_id,
                "first_at_index": seen[step_id],
                "duplicate_at_index": i,
            })
        else:
            seen[step_id] = i
    return findings


def validate_procedure(procedure):
    """Full §4.9.1 validation of a procedure dict.

    procedure: {
        "procedure_id": str,
        "title": str,
        "purpose": str,
        "procedure_type": str,      # must be in PROCEDURE_TYPES
        "preconditions": [str, ...],
        "steps": [
            {
                "step_id": str,
                "action": str,
                "is_checkpoint": bool,  # optional, default False
            },
            ...
        ],
        "expected_outcome": str,
    }

    Returns {
        "field_findings": [...],   # field completeness errors/warnings
        "step_findings": [...],    # per-step format findings
        "hfe_findings": [...],     # checkpoint spacing + step-ID uniqueness
    }.
    Raises ValueError for an unrecognized procedure_type."""
    field_findings = validate_procedure_fields(procedure)

    proc_type = procedure.get("procedure_type")
    if proc_type is not None and proc_type not in PROCEDURE_TYPES:
        raise ValueError(
            "unrecognized procedure_type %r under E-ST-10-11C §4.9.1; "
            "accepted: %s" % (proc_type, sorted(PROCEDURE_TYPES))
        )

    steps = procedure.get("steps") or []
    step_findings = []
    for i, step in enumerate(steps):
        step_findings.extend(validate_step(step, i))

    hfe_findings = []
    hfe_findings.extend(check_checkpoint_spacing(steps))
    hfe_findings.extend(check_step_id_uniqueness(steps))

    return {
        "field_findings": field_findings,
        "step_findings": step_findings,
        "hfe_findings": hfe_findings,
    }


def is_procedure_approved(validation_result):
    """True when no error-severity findings exist across all categories
    in the validate_procedure result dict -- the procedure satisfies
    §4.9.1 format and HFE requirements for this assessment."""
    for findings in validation_result.values():
        for finding in findings:
            if finding.get("severity") == SEVERITY_ERROR:
                return False
    return True
