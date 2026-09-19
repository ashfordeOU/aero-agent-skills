"""Typical test process sequence used as the reference flow for a campaign.

Anchor: ECSS-Q-ST-20-07C Annex B, informative (the typical sequence a test
process runs through, offered as the reference flow a campaign plan is laid
against). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Hold the reference flow as an ordered set of phases, each marked
   mandatory or optional for a campaign that follows the typical process.
2. Normalise a proposed campaign plan: the phases the planner intends to
   run, in the planner's own order, with a duration for each.
3. Grade coverage: every mandatory reference phase is either planned, or
   omitted against a recorded tailoring rationale. An omission with no
   rationale is a finding; a rationale for a phase that is planned anyway
   is a stale entry and is reported as one.
4. Grade order: the planned phases must not run backwards through the
   reference flow. Every adjacent inversion is named as a pair.
5. Lay the durations out into day windows from the campaign start so the
   plan carries a schedule and not only a list.
6. Return the coverage fraction and the conformance decision: conforms,
   conforms with tailoring, or non-conforming.
"""

__all__ = [
    "REFERENCE_SEQUENCE",
    "MANDATORY_PHASES",
    "OPTIONAL_PHASES",
    "normalise_identifier",
    "reference_index",
    "is_mandatory",
    "critical_reference_path",
    "validate_plan",
    "validate_tailoring",
    "coverage_findings",
    "order_findings",
    "phase_windows",
    "assess_test_sequence",
]

# The typical test process sequence, in order. True marks a phase a campaign
# following the typical process is expected to run.
REFERENCE_SEQUENCE = (
    ("test-request", True),
    ("feasibility-and-facility-selection", False),
    ("test-specification", True),
    ("test-procedure-preparation", True),
    ("facility-configuration-and-readiness", True),
    ("test-item-incoming-inspection", False),
    ("pre-test-review", True),
    ("test-execution", True),
    ("post-test-inspection", False),
    ("test-data-package", True),
    ("test-report-and-close-out", True),
    ("test-item-return", False),
)

MANDATORY_PHASES = tuple(name for name, required in REFERENCE_SEQUENCE if required)

OPTIONAL_PHASES = tuple(name for name, required in REFERENCE_SEQUENCE if not required)

_INDEX = {name: position for position, (name, _required) in enumerate(REFERENCE_SEQUENCE)}


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def reference_index(phase):
    """Return the position of a phase in the reference flow."""
    name = normalise_identifier(phase, "phase")
    if name not in _INDEX:
        raise ValueError(
            "unknown phase %r; the reference flow is %s"
            % (name, " -> ".join(_INDEX))
        )
    return _INDEX[name]


def is_mandatory(phase):
    """Return True when the reference flow expects the phase to be run."""
    return normalise_identifier(phase, "phase") in MANDATORY_PHASES


def critical_reference_path():
    """Return the mandatory phases in reference order."""
    return MANDATORY_PHASES


def _positive_int(value, label):
    """Return value as a strictly positive integer."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def validate_plan(plan):
    """Return the normalised campaign plan in the planner's order."""
    if not isinstance(plan, (list, tuple)) or not plan:
        raise ValueError("plan must be a non-empty sequence of planned phases")
    seen = set()
    entries = []
    for position, item in enumerate(plan):
        if not isinstance(item, dict):
            raise ValueError("plan[%d] must be a mapping" % position)
        phase = normalise_identifier(item.get("phase"), "plan[%d].phase" % position)
        index = reference_index(phase)
        if phase in seen:
            raise ValueError("phase %r is planned twice" % phase)
        seen.add(phase)
        entries.append({
            "phase": phase,
            "position": position,
            "reference_index": index,
            "mandatory": phase in MANDATORY_PHASES,
            "duration_days": _positive_int(
                item.get("duration_days"), "plan[%d].duration_days" % position
            ),
        })
    return entries


def validate_tailoring(tailoring):
    """Return the normalised tailoring rationales keyed by phase."""
    if tailoring is None:
        tailoring = {}
    if not isinstance(tailoring, dict):
        raise ValueError("tailoring must be a mapping of phase to rationale")
    out = {}
    for key, value in tailoring.items():
        phase = normalise_identifier(key, "tailoring key")
        reference_index(phase)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("tailoring rationale for %r must be a non-empty string" % phase)
        out[phase] = value.strip()
    return out


def coverage_findings(entries, tailoring):
    """Report omitted mandatory phases and rationales that are not needed."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be the normalised plan")
    if not isinstance(tailoring, dict):
        raise ValueError("tailoring must be the normalised rationale mapping")
    planned = {entry["phase"] for entry in entries}
    findings = []
    for phase in MANDATORY_PHASES:
        if phase in planned:
            continue
        if phase in tailoring:
            findings.append({
                "code": "mandatory-phase-tailored",
                "severity": "advisory",
                "phase": phase,
                "message": "%s is omitted against a recorded rationale" % phase,
            })
        else:
            findings.append({
                "code": "mandatory-phase-omitted",
                "severity": "blocking",
                "phase": phase,
                "message": "%s is in the reference flow but neither planned nor tailored"
                           % phase,
            })
    for phase in sorted(tailoring):
        if phase in planned:
            findings.append({
                "code": "tailoring-rationale-unused",
                "severity": "advisory",
                "phase": phase,
                "message": "a tailoring rationale is recorded for %s although it is planned"
                           % phase,
            })
    return findings


def order_findings(entries):
    """Report every adjacent pair that runs backwards through the reference flow."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be the normalised plan")
    findings = []
    for position in range(1, len(entries)):
        previous = entries[position - 1]
        current = entries[position]
        if current["reference_index"] < previous["reference_index"]:
            findings.append({
                "code": "phase-out-of-reference-order",
                "severity": "blocking",
                "phase": current["phase"],
                "message": "%s is planned after %s, which reverses the reference flow"
                           % (current["phase"], previous["phase"]),
            })
    return findings


def phase_windows(entries, campaign_start_day=0):
    """Lay the planned durations out into day windows from the campaign start."""
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("entries must be the non-empty normalised plan")
    if not isinstance(campaign_start_day, int) or isinstance(campaign_start_day, bool):
        raise ValueError("campaign_start_day must be an integer")
    if campaign_start_day < 0:
        raise ValueError("campaign_start_day must not be negative")
    day = campaign_start_day
    windows = []
    for entry in entries:
        start = day
        end = start + entry["duration_days"]
        windows.append({
            "phase": entry["phase"],
            "start_day": start,
            "end_day": end,
            "duration_days": entry["duration_days"],
        })
        day = end
    return windows


def assess_test_sequence(spec):
    """Lay a campaign plan against the Annex B reference flow.

    spec keys: plan (sequence of planned phases with durations), optional
    tailoring (phase to rationale) and campaign_start_day.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "plan" not in spec:
        raise ValueError("spec missing required key 'plan'")
    entries = validate_plan(spec["plan"])
    tailoring = validate_tailoring(spec.get("tailoring"))
    findings = coverage_findings(entries, tailoring)
    findings.extend(order_findings(entries))
    windows = phase_windows(entries, spec.get("campaign_start_day", 0))
    planned = {entry["phase"] for entry in entries}
    covered = sum(1 for phase in MANDATORY_PHASES if phase in planned)
    blocking = [f for f in findings if f["severity"] == "blocking"]
    tailored = [f for f in findings if f["code"] == "mandatory-phase-tailored"]
    if blocking:
        decision = "non-conforming"
    elif tailored:
        decision = "conforms-with-tailoring"
    else:
        decision = "conforms"
    return {
        "entries": entries,
        "windows": windows,
        "total_duration_days": windows[-1]["end_day"] - windows[0]["start_day"],
        "mandatory_coverage": covered / float(len(MANDATORY_PHASES)),
        "ordered": not any(f["code"] == "phase-out-of-reference-order" for f in findings),
        "optional_phases_not_planned": tuple(
            phase for phase in OPTIONAL_PHASES if phase not in planned
        ),
        "findings": findings,
        "blocking_findings": blocking,
        "decision": decision,
    }
