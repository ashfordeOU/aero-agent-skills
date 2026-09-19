"""Abort handling for on-board file copy operations.

Anchor: ECSS-E-ST-70-41C clause 6.23.5.4 (aborting the file copy operations of
the file management service). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold each copy operation as an entry with a four-part key, the octets it
   has to move, the octets it has moved, and whether it is running or
   suspended. An abort reaches both; nothing else is in the list.
2. Abort one named operation, or every operation at once, and in each case
   remove the entry rather than park it in an aborted state -- an aborted
   copy is no longer an operation the ground can act on.
3. Decide the disposition of the partially written target file. A target that
   received no octets was never created; one that received some is a partial
   file that has to be deleted, and its octets returned to the target
   repository's free space.
4. Keep the reclaimed octets auditable: the abort reports how many octets
   were discarded per operation and in total, because that is transfer effort
   that has to be spent again.
5. Refuse an abort of an operation the list does not hold, with that reason,
   instead of reporting a successful abort of nothing.
6. Report the campaign: the operations aborted, the ones refused, the octets
   discarded, the partial target files deleted and the resulting list.
"""

__all__ = [
    "ABORTABLE_STATES",
    "new_copy_operation",
    "build_operation_list",
    "find_operation",
    "partial_target_disposition",
    "abort_operation",
    "abort_all",
    "reclaimed_octets",
    "abort_report",
    "assess_abort_campaign",
]

# Both live states are abortable. A completed copy is not in the list at all,
# so "abort a completed operation" is a lookup failure, not a state refusal.
ABORTABLE_STATES = ("running", "suspended")


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


def new_copy_operation(source_repository, source_file, target_repository, target_file,
                       octets_total, octets_copied=0, state="running"):
    """Return a validated abortable copy operation entry."""
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
    if copied == total:
        raise ValueError(
            "an operation that has moved all %d octets has completed and left the list" % total
        )
    if state not in ABORTABLE_STATES:
        raise ValueError(
            "state must be one of %s, got %r" % (", ".join(ABORTABLE_STATES), state)
        )
    return {
        "key": key,
        "target_repository": key[2],
        "target_file": key[3],
        "octets_total": total,
        "octets_copied": copied,
        "state": state,
    }


def build_operation_list(operations):
    """Return a validated copy operation list with unique keys."""
    if not isinstance(operations, (list, tuple)):
        raise ValueError("operations must be a sequence of copy operations")
    entries = []
    seen = set()
    for item in operations:
        if not isinstance(item, dict):
            raise ValueError("each copy operation must be a mapping")
        for field in ("key", "octets_total", "octets_copied", "state"):
            if field not in item:
                raise ValueError("copy operation missing required key '%s'" % field)
        if item["key"] in seen:
            raise ValueError("duplicate copy operation key %r in the list" % (item["key"],))
        seen.add(item["key"])
        entries.append(item)
    return entries


def find_operation(operations, key):
    """Return the entry carrying this key, or None."""
    if not isinstance(key, tuple) or len(key) != 4:
        raise ValueError("key must be a four-part copy key")
    for entry in operations:
        if entry["key"] == key:
            return entry
    return None


def partial_target_disposition(entry):
    """Return what has to happen to the target file of an aborted operation."""
    if not isinstance(entry, dict) or "octets_copied" not in entry:
        raise ValueError("entry must carry 'octets_copied'")
    copied = _validate_octets(entry["octets_copied"], "octets_copied")
    if copied == 0:
        return {
            "action": "none",
            "octets_reclaimed": 0,
            "detail": "no octets landed, so no target file was created",
        }
    return {
        "action": "delete-partial-target",
        "octets_reclaimed": copied,
        "detail": "%d octets of a partial target file are deleted and returned to free space"
        % copied,
    }


def abort_operation(operations, key, repositories=None):
    """Abort one named copy operation and return the outcome."""
    entry = find_operation(operations, key)
    if entry is None:
        return {
            "key": key,
            "outcome": "refused",
            "reason": "no copy operation in the list carries this key",
            "octets_discarded": 0,
            "disposition": None,
        }
    disposition = partial_target_disposition(entry)
    operations.remove(entry)
    if repositories is not None:
        _return_octets(repositories, entry["target_repository"], disposition["octets_reclaimed"])
    return {
        "key": entry["key"],
        "outcome": "aborted",
        "reason": None,
        "octets_discarded": entry["octets_copied"],
        "disposition": disposition,
    }


def _return_octets(repositories, repository_name, octets):
    """Return reclaimed octets to a repository's free-space accounting."""
    if not isinstance(repositories, dict):
        raise ValueError("repositories must be a mapping of name to free octets")
    if repository_name not in repositories:
        raise ValueError("unknown target repository '%s'" % repository_name)
    free = repositories[repository_name]
    if isinstance(free, bool) or not isinstance(free, int):
        raise ValueError("free octets of '%s' must be a whole number" % repository_name)
    repositories[repository_name] = free + octets
    return repositories[repository_name]


def abort_all(operations, repositories=None):
    """Abort every copy operation in the list; return one outcome per entry."""
    outcomes = []
    for entry in list(operations):
        outcomes.append(abort_operation(operations, entry["key"], repositories))
    return outcomes


def reclaimed_octets(outcomes):
    """Return the total octets returned to free space by a set of abort outcomes."""
    if not isinstance(outcomes, (list, tuple)):
        raise ValueError("outcomes must be a sequence")
    total = 0
    for outcome in outcomes:
        if not isinstance(outcome, dict) or "disposition" not in outcome:
            raise ValueError("each outcome must carry a 'disposition'")
        if outcome["disposition"] is not None:
            total += outcome["disposition"]["octets_reclaimed"]
    return total


def abort_report(outcomes, operations):
    """Return the tally of an abort action and the list it leaves behind."""
    if not isinstance(outcomes, (list, tuple)):
        raise ValueError("outcomes must be a sequence")
    aborted = [o for o in outcomes if o["outcome"] == "aborted"]
    refused = [o for o in outcomes if o["outcome"] == "refused"]
    deleted = [
        o["key"]
        for o in aborted
        if o["disposition"]["action"] == "delete-partial-target"
    ]
    return {
        "aborted": len(aborted),
        "refused": len(refused),
        "octets_discarded": sum(o["octets_discarded"] for o in aborted),
        "octets_reclaimed": reclaimed_octets(outcomes),
        "partial_targets_deleted": deleted,
        "remaining": len(operations),
    }


def assess_abort_campaign(spec):
    """Apply a sequence of abort directives to a copy operation list and report.

    spec keys: operations (sequence of copy operations), directives (sequence
    of mappings with 'directive' of 'abort' or 'abort-all' and optional 'key'),
    optional repositories (mapping of repository name to free octets).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for field in ("operations", "directives"):
        if field not in spec:
            raise ValueError("spec missing required key '%s'" % field)
    operations = build_operation_list(spec["operations"])
    directives = spec["directives"]
    if not isinstance(directives, (list, tuple)):
        raise ValueError("spec['directives'] must be a sequence")
    repositories = spec.get("repositories")
    outcomes = []
    for item in directives:
        if not isinstance(item, dict) or "directive" not in item:
            raise ValueError("each directive must be a mapping carrying 'directive'")
        directive = item["directive"]
        if directive == "abort":
            if "key" not in item:
                raise ValueError("directive 'abort' needs the key of one copy operation")
            outcomes.append(abort_operation(operations, item["key"], repositories))
        elif directive == "abort-all":
            if "key" in item:
                raise ValueError("directive 'abort-all' applies to the list and takes no key")
            outcomes.extend(abort_all(operations, repositories))
        else:
            raise ValueError("directive must be 'abort' or 'abort-all', got %r" % (directive,))
    report = abort_report(outcomes, operations)
    findings = []
    if report["refused"]:
        findings.append(
            "%d abort directive(s) named an operation the list does not hold" % report["refused"]
        )
    if report["octets_discarded"]:
        findings.append(
            "%d octets of transfer effort were discarded and have to be moved again"
            % report["octets_discarded"]
        )
    if report["partial_targets_deleted"]:
        findings.append(
            "%d partial target file(s) were deleted; no truncated file is left behind"
            % len(report["partial_targets_deleted"])
        )
    return {
        "operations": operations,
        "outcomes": outcomes,
        "report": report,
        "repositories": repositories,
        "findings": findings,
    }
