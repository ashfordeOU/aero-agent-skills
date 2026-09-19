"""Suspension and resumption of on-board file copy operations.

Anchor: ECSS-E-ST-70-41C clause 6.23.5.3 (suspending and resuming the file
copy operations of the file management service). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold each copy operation as an entry with a four-part key, a total octet
   count, the octets moved so far and a lifecycle state: running, suspended or
   completed.
2. Apply a suspend directive to one named operation or to every operation at
   once, and the matching resume directive the same two ways.
3. Enforce the transitions: only a running operation suspends, only a
   suspended operation resumes, a completed operation does neither, and an
   operation nobody holds is a finding rather than a silent no-op.
4. Preserve progress across the pause. Resumption continues from the octet
   the suspension stopped at; it never restarts the file and never discards
   what has already landed.
5. Refuse to move octets for a suspended operation, because a subservice that
   keeps copying through a suspension has not suspended anything.
6. Report the outcome of a directive campaign: which operations changed
   state, which directives were redundant, which were refused and why, and
   the resulting state of the whole list.
"""

__all__ = [
    "OPERATION_STATES",
    "TERMINAL_STATES",
    "new_operation",
    "validate_operation",
    "build_list",
    "find_operation",
    "suspend_operation",
    "resume_operation",
    "suspend_all",
    "resume_all",
    "advance_operation",
    "apply_directive",
    "list_summary",
    "assess_directive_campaign",
]

OPERATION_STATES = ("running", "suspended", "completed")
# A completed copy has left the controllable population: neither directive
# applies to it, and pretending otherwise invents a state transition.
TERMINAL_STATES = ("completed",)

_DIRECTIVES = ("suspend", "resume", "suspend-all", "resume-all")


def _validate_name(value, label):
    """Return a validated non-blank repository or file name."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    if not value.strip():
        raise ValueError("%s must not be empty or blank" % label)
    if value != value.strip():
        raise ValueError("%s must not carry leading or trailing blanks: %r" % (label, value))
    return value


def _validate_octets(value, label, allow_zero=True):
    """Return a validated whole number of octets."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number of octets, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    if value == 0 and not allow_zero:
        raise ValueError("%s must be positive, got 0" % label)
    return value


def new_operation(source_repository, source_file, target_repository, target_file,
                  octets_total, octets_copied=0, state="running"):
    """Return a validated copy operation entry."""
    key = (
        _validate_name(source_repository, "source_repository"),
        _validate_name(source_file, "source_file"),
        _validate_name(target_repository, "target_repository"),
        _validate_name(target_file, "target_file"),
    )
    total = _validate_octets(octets_total, "octets_total", allow_zero=False)
    copied = _validate_octets(octets_copied, "octets_copied")
    if copied > total:
        raise ValueError("octets_copied %d exceeds octets_total %d" % (copied, total))
    if state not in OPERATION_STATES:
        raise ValueError("state must be one of %s, got %r" % (", ".join(OPERATION_STATES), state))
    if state == "completed" and copied != total:
        raise ValueError("a completed operation must have moved all %d octets" % total)
    return {
        "key": key,
        "octets_total": total,
        "octets_copied": copied,
        "state": state,
    }


def validate_operation(entry):
    """Return the entry after checking it is a well-formed copy operation."""
    if not isinstance(entry, dict):
        raise ValueError("copy operation must be a mapping")
    for field in ("key", "octets_total", "octets_copied", "state"):
        if field not in entry:
            raise ValueError("copy operation missing required key '%s'" % field)
    if not isinstance(entry["key"], tuple) or len(entry["key"]) != 4:
        raise ValueError("copy operation key must be a four-part tuple")
    if entry["state"] not in OPERATION_STATES:
        raise ValueError("unknown operation state %r" % (entry["state"],))
    if entry["octets_copied"] > entry["octets_total"]:
        raise ValueError("octets_copied exceeds octets_total")
    return entry


def build_list(operations):
    """Return a validated copy operation list with unique keys."""
    if not isinstance(operations, (list, tuple)):
        raise ValueError("operations must be a sequence of copy operations")
    entries = []
    seen = set()
    for item in operations:
        entry = validate_operation(item)
        if entry["key"] in seen:
            raise ValueError("duplicate copy operation key %r in the list" % (entry["key"],))
        seen.add(entry["key"])
        entries.append(entry)
    return entries


def find_operation(operations, key):
    """Return the entry carrying this key, or None."""
    if not isinstance(key, tuple) or len(key) != 4:
        raise ValueError("key must be a four-part copy key")
    for entry in operations:
        if entry["key"] == key:
            return entry
    return None


def _transition(entry, wanted_from, wanted_to, verb):
    """Return the outcome of one state transition on one entry."""
    before = entry["state"]
    if before in TERMINAL_STATES:
        return {
            "key": entry["key"],
            "outcome": "refused",
            "state": before,
            "reason": "a %s operation cannot be %sed" % (before, verb),
        }
    if before == wanted_to:
        return {
            "key": entry["key"],
            "outcome": "redundant",
            "state": before,
            "reason": "the operation is already %sed" % verb,
        }
    if before != wanted_from:
        return {
            "key": entry["key"],
            "outcome": "refused",
            "state": before,
            "reason": "only a %s operation can be %sed" % (wanted_from, verb),
        }
    entry["state"] = wanted_to
    return {"key": entry["key"], "outcome": "changed", "state": wanted_to, "reason": None}


def suspend_operation(operations, key):
    """Suspend one named copy operation and return the outcome."""
    entry = find_operation(operations, key)
    if entry is None:
        return {
            "key": key,
            "outcome": "refused",
            "state": None,
            "reason": "no copy operation in the list carries this key",
        }
    return _transition(entry, "running", "suspended", "suspend")


def resume_operation(operations, key):
    """Resume one named copy operation and return the outcome."""
    entry = find_operation(operations, key)
    if entry is None:
        return {
            "key": key,
            "outcome": "refused",
            "state": None,
            "reason": "no copy operation in the list carries this key",
        }
    return _transition(entry, "suspended", "running", "resume")


def suspend_all(operations):
    """Suspend every running copy operation; return one outcome per entry."""
    return [_transition(entry, "running", "suspended", "suspend") for entry in operations]


def resume_all(operations):
    """Resume every suspended copy operation; return one outcome per entry."""
    return [_transition(entry, "suspended", "running", "resume") for entry in operations]


def advance_operation(operations, key, octets):
    """Move octets for one running operation; refuse while it is suspended."""
    _validate_octets(octets, "octets", allow_zero=False)
    entry = find_operation(operations, key)
    if entry is None:
        raise ValueError("no copy operation in the list carries this key")
    if entry["state"] == "suspended":
        raise ValueError("a suspended copy operation must not move octets")
    if entry["state"] in TERMINAL_STATES:
        raise ValueError("a completed copy operation has nothing left to move")
    remaining = entry["octets_total"] - entry["octets_copied"]
    if octets > remaining:
        raise ValueError("asked to move %d octets but only %d remain" % (octets, remaining))
    entry["octets_copied"] += octets
    if entry["octets_copied"] == entry["octets_total"]:
        entry["state"] = "completed"
    return entry


def apply_directive(operations, directive, key=None):
    """Apply one suspend or resume directive and return its outcomes."""
    if directive not in _DIRECTIVES:
        raise ValueError("directive must be one of %s, got %r" % (", ".join(_DIRECTIVES), directive))
    if directive in ("suspend", "resume"):
        if key is None:
            raise ValueError("directive '%s' needs the key of one copy operation" % directive)
        single = suspend_operation if directive == "suspend" else resume_operation
        return [single(operations, key)]
    if key is not None:
        raise ValueError("directive '%s' applies to the whole list and takes no key" % directive)
    return suspend_all(operations) if directive == "suspend-all" else resume_all(operations)


def list_summary(operations):
    """Return the population of the list by lifecycle state."""
    summary = dict((state, 0) for state in OPERATION_STATES)
    octets_pending = 0
    for entry in operations:
        summary[entry["state"]] += 1
        if entry["state"] != "completed":
            octets_pending += entry["octets_total"] - entry["octets_copied"]
    summary["total"] = len(operations)
    summary["octets_pending"] = octets_pending
    return summary


def assess_directive_campaign(spec):
    """Apply a sequence of directives to a copy operation list and report.

    spec keys: operations (sequence of copy operations), directives (sequence
    of mappings with 'directive' and optional 'key').
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for field in ("operations", "directives"):
        if field not in spec:
            raise ValueError("spec missing required key '%s'" % field)
    operations = build_list(spec["operations"])
    directives = spec["directives"]
    if not isinstance(directives, (list, tuple)):
        raise ValueError("spec['directives'] must be a sequence")
    outcomes = []
    for item in directives:
        if not isinstance(item, dict) or "directive" not in item:
            raise ValueError("each directive must be a mapping carrying 'directive'")
        for outcome in apply_directive(operations, item["directive"], item.get("key")):
            outcome = dict(outcome)
            outcome["directive"] = item["directive"]
            outcomes.append(outcome)
    findings = []
    refused = [o for o in outcomes if o["outcome"] == "refused"]
    redundant = [o for o in outcomes if o["outcome"] == "redundant"]
    if refused:
        findings.append("%d directive outcome(s) were refused" % len(refused))
    if redundant:
        findings.append("%d directive outcome(s) changed nothing" % len(redundant))
    summary = list_summary(operations)
    if summary["suspended"] and not summary["running"]:
        findings.append("every uncompleted copy operation is suspended; nothing is progressing")
    return {
        "operations": operations,
        "outcomes": outcomes,
        "summary": summary,
        "findings": findings,
    }
