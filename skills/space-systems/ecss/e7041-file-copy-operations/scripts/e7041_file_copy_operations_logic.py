"""Admission and progress tracking for on-board file copy operations.

Anchor: ECSS-E-ST-70-41C clause 6.23.5.2 (the file copy operations of the file
management service). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate the on-board repositories a copy request names: each repository has
   a capacity in octets and a set of files with their sizes, so its free space
   is derived, never carried as a second number that can drift.
2. Validate a copy request: a source repository and file that exist, a target
   repository that exists, and a target file name that is still free.
3. Decide admission against the copy operation list: refuse a request that
   copies a file onto itself, one whose source-to-target pair is already in the
   list, one the target repository has no room for, and one that arrives when
   the list is full. Each refusal carries its own reason.
4. Admit a request as an entry carrying the total octets to move and zero moved
   so far, and reserve nothing at the target until the octets actually land.
5. Advance an entry as octets are moved, complete it when the whole file has
   landed, create the target file at that instant and remove the entry.
6. Report the list: every entry with its progress, plus the accepted and
   refused counts of a whole request campaign and the findings it raised.
"""

__all__ = [
    "DEFAULT_LIST_CAPACITY",
    "validate_identifier",
    "validate_repository",
    "validate_filesystem",
    "repository_used_octets",
    "repository_free_octets",
    "copy_key",
    "new_copy_list",
    "refusal_reason",
    "admit_copy_request",
    "advance_copy",
    "copy_progress_fraction",
    "status_report",
    "assess_copy_campaign",
]

# The copy operation list is a bounded on-board resource; a subservice that
# accepts an unbounded number of concurrent copies has no list at all.
DEFAULT_LIST_CAPACITY = 8


def validate_identifier(value, label):
    """Return a validated repository or file name."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty or blank" % label)
    if text != value:
        raise ValueError("%s must not carry leading or trailing blanks: %r" % (label, value))
    return text


def _validate_octet_count(value, label, allow_zero=True):
    """Return a validated non-negative whole number of octets."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number of octets, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    if value == 0 and not allow_zero:
        raise ValueError("%s must be positive, got 0" % label)
    return value


def validate_repository(repository, label="repository"):
    """Return a validated repository: capacity in octets and its held files."""
    if not isinstance(repository, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("capacity_octets", "files"):
        if key not in repository:
            raise ValueError("%s missing required key '%s'" % (label, key))
    capacity = _validate_octet_count(
        repository["capacity_octets"], "%s capacity_octets" % label, allow_zero=False
    )
    files = repository["files"]
    if not isinstance(files, dict):
        raise ValueError("%s files must be a mapping of name to size" % label)
    held = {}
    for name, size in files.items():
        clean = validate_identifier(name, "%s file name" % label)
        held[clean] = _validate_octet_count(size, "%s file '%s' size" % (label, clean))
    used = sum(held.values())
    if used > capacity:
        raise ValueError(
            "%s holds %d octets but its capacity is %d" % (label, used, capacity)
        )
    return {"capacity_octets": capacity, "files": held}


def validate_filesystem(filesystem):
    """Return the validated set of on-board repositories, keyed by name."""
    if not isinstance(filesystem, dict) or not filesystem:
        raise ValueError("filesystem must be a non-empty mapping of repository name to repository")
    validated = {}
    for name, repository in filesystem.items():
        clean = validate_identifier(name, "repository name")
        validated[clean] = validate_repository(repository, "repository '%s'" % clean)
    return validated


def repository_used_octets(repository):
    """Return the octets currently held by a repository."""
    return sum(validate_repository(repository)["files"].values())


def repository_free_octets(repository):
    """Return the octets still free in a repository."""
    validated = validate_repository(repository)
    return validated["capacity_octets"] - sum(validated["files"].values())


def copy_key(source_repository, source_file, target_repository, target_file):
    """Return the four-part identity of a copy operation."""
    return (
        validate_identifier(source_repository, "source_repository"),
        validate_identifier(source_file, "source_file"),
        validate_identifier(target_repository, "target_repository"),
        validate_identifier(target_file, "target_file"),
    )


def _request_key(request):
    """Return the copy key of a request mapping."""
    if not isinstance(request, dict):
        raise ValueError("copy request must be a mapping")
    for field in ("source_repository", "source_file", "target_repository", "target_file"):
        if field not in request:
            raise ValueError("copy request missing required key '%s'" % field)
    return copy_key(
        request["source_repository"],
        request["source_file"],
        request["target_repository"],
        request["target_file"],
    )


def new_copy_list(capacity=DEFAULT_LIST_CAPACITY):
    """Return an empty copy operation list of the given entry capacity."""
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise ValueError("capacity must be an integer number of entries")
    if capacity < 1:
        raise ValueError("capacity must be at least one entry, got %d" % capacity)
    return {"capacity": capacity, "operations": []}


def _validate_list(state):
    """Return the validated copy operation list state."""
    if not isinstance(state, dict):
        raise ValueError("copy list state must be a mapping")
    for key in ("capacity", "operations"):
        if key not in state:
            raise ValueError("copy list state missing required key '%s'" % key)
    if not isinstance(state["operations"], list):
        raise ValueError("copy list operations must be a list")
    return state


def _find_entry(state, key):
    """Return the entry carrying this copy key, or None."""
    for entry in state["operations"]:
        if entry["key"] == key:
            return entry
    return None


def _reserved_octets(state, repository_name):
    """Return the octets already landed at a repository by running copies."""
    total = 0
    for entry in state["operations"]:
        if entry["key"][2] == repository_name:
            total += entry["octets_copied"]
    return total


def refusal_reason(state, filesystem, request):
    """Return why this copy request cannot be admitted, or None when it can."""
    _validate_list(state)
    repositories = validate_filesystem(filesystem)
    key = _request_key(request)
    src_repo, src_file, dst_repo, dst_file = key
    if src_repo not in repositories:
        return "source repository '%s' is not an on-board repository" % src_repo
    if src_file not in repositories[src_repo]["files"]:
        return "source file '%s' does not exist in repository '%s'" % (src_file, src_repo)
    if dst_repo not in repositories:
        return "target repository '%s' is not an on-board repository" % dst_repo
    if src_repo == dst_repo and src_file == dst_file:
        return "source and target name the same file, a copy onto itself"
    if dst_file in repositories[dst_repo]["files"]:
        return "target file '%s' already exists in repository '%s'" % (dst_file, dst_repo)
    if _find_entry(state, key) is not None:
        return "an identical copy operation is already in the copy operation list"
    for entry in state["operations"]:
        if entry["key"][2] == dst_repo and entry["key"][3] == dst_file:
            return (
                "another copy operation is already writing '%s' into repository '%s'"
                % (dst_file, dst_repo)
            )
    size = repositories[src_repo]["files"][src_file]
    free = repository_free_octets(repositories[dst_repo]) - _reserved_octets(state, dst_repo)
    if size > free:
        return (
            "target repository '%s' has %d octets free but the file needs %d"
            % (dst_repo, free, size)
        )
    if len(state["operations"]) >= state["capacity"]:
        return "the copy operation list already holds its %d entries" % state["capacity"]
    return None


def admit_copy_request(state, filesystem, request):
    """Admit a copy request into the list and return its new entry."""
    reason = refusal_reason(state, filesystem, request)
    if reason is not None:
        raise ValueError("copy request refused: %s" % reason)
    repositories = validate_filesystem(filesystem)
    key = _request_key(request)
    entry = {
        "key": key,
        "source_repository": key[0],
        "source_file": key[1],
        "target_repository": key[2],
        "target_file": key[3],
        "octets_total": repositories[key[0]]["files"][key[1]],
        "octets_copied": 0,
        "state": "running",
    }
    state["operations"].append(entry)
    return entry


def advance_copy(state, filesystem, key, octets):
    """Move octets for one copy operation; complete and clear it when done."""
    _validate_list(state)
    if not isinstance(key, tuple) or len(key) != 4:
        raise ValueError("key must be a four-part copy key")
    _validate_octet_count(octets, "octets", allow_zero=False)
    entry = _find_entry(state, key)
    if entry is None:
        raise ValueError("no copy operation in the list carries this key")
    remaining = entry["octets_total"] - entry["octets_copied"]
    if octets > remaining:
        raise ValueError(
            "asked to move %d octets but only %d remain for this operation" % (octets, remaining)
        )
    entry["octets_copied"] += octets
    if entry["octets_copied"] < entry["octets_total"]:
        return {"completed": False, "entry": entry}
    repositories = validate_filesystem(filesystem)
    target = filesystem[entry["target_repository"]]
    if entry["octets_total"] > repository_free_octets(target):
        raise ValueError(
            "completing the copy would overfill repository '%s'" % entry["target_repository"]
        )
    entry["state"] = "completed"
    target["files"][entry["target_file"]] = entry["octets_total"]
    state["operations"].remove(entry)
    return {"completed": True, "entry": entry}


def copy_progress_fraction(entry):
    """Return the fraction of the file moved so far, as a float in [0, 1]."""
    if not isinstance(entry, dict) or "octets_total" not in entry or "octets_copied" not in entry:
        raise ValueError("entry must carry 'octets_total' and 'octets_copied'")
    total = entry["octets_total"]
    if total <= 0:
        raise ValueError("octets_total must be positive to have a progress fraction")
    return entry["octets_copied"] / total


def status_report(state):
    """Return the status of every copy operation currently in the list."""
    _validate_list(state)
    rows = []
    for entry in state["operations"]:
        rows.append(
            {
                "source": "%s/%s" % (entry["source_repository"], entry["source_file"]),
                "target": "%s/%s" % (entry["target_repository"], entry["target_file"]),
                "octets_total": entry["octets_total"],
                "octets_copied": entry["octets_copied"],
                "progress": copy_progress_fraction(entry),
                "state": entry["state"],
            }
        )
    return {
        "capacity": state["capacity"],
        "in_progress": len(rows),
        "free_entries": state["capacity"] - len(rows),
        "operations": rows,
    }


def assess_copy_campaign(spec):
    """Run a sequence of copy requests against a filesystem and report the outcome.

    spec keys: filesystem (mapping of repository name to repository),
    requests (sequence of copy request mappings), optional list_capacity.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("filesystem", "requests"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    requests = spec["requests"]
    if not isinstance(requests, (list, tuple)):
        raise ValueError("spec['requests'] must be a sequence of copy requests")
    filesystem = spec["filesystem"]
    validate_filesystem(filesystem)
    state = new_copy_list(spec.get("list_capacity", DEFAULT_LIST_CAPACITY))
    accepted = []
    refused = []
    for request in requests:
        reason = refusal_reason(state, filesystem, request)
        if reason is None:
            entry = admit_copy_request(state, filesystem, request)
            accepted.append(entry["key"])
        else:
            refused.append({"request": _request_key(request), "reason": reason})
    findings = []
    if not accepted and requests:
        findings.append("no copy request in the campaign was admitted")
    for item in refused:
        if "already in the copy operation list" in item["reason"]:
            findings.append(
                "duplicate copy request for %s/%s to %s/%s"
                % (item["request"][0], item["request"][1], item["request"][2], item["request"][3])
            )
    if len(state["operations"]) == state["capacity"]:
        findings.append("the copy operation list is full; further requests will be turned away")
    return {
        "state": state,
        "accepted": accepted,
        "refused": refused,
        "report": status_report(state),
        "findings": findings,
    }
