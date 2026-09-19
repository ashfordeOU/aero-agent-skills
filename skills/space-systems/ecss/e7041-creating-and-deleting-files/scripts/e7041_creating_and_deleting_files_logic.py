"""Creating and deleting on-board files.

Anchor: ECSS-E-ST-70-41C clause 6.23.4.1 (creating and deleting files in an
on-board repository). Paraphrased into an implementable procedure; no standard
text is reproduced.

Model implemented here
----------------------
A repository has a total capacity, a ceiling on any single file, a ceiling on
the number of files it holds, and the files themselves. A create request
reserves an allocation inside the capacity; a delete request gives it back.
Both requests fail on stated conditions rather than partially: a rejected
request leaves the repository exactly as it was, so a run of requests can be
replayed and the free space accounted after every accepted one.

Procedure implemented here
--------------------------
1. Validate a file name and a repository description.
2. Account the reserved and the free octets of a repository.
3. Apply a create request: refuse a duplicate name, an allocation past the
   per-file ceiling, an allocation past the free space and a repository
   already holding its maximum number of files.
4. Apply a delete request: refuse an absent file, a locked file and a file
   held open by a transfer.
5. Replay a run of requests, recording a verdict per request and the free
   space after each one.
6. Assemble the run verdict and its findings.
"""

__all__ = [
    "PATH_SEPARATOR",
    "MAX_NAME_CHARS",
    "OPERATIONS",
    "validate_file_name",
    "build_repository",
    "reserved_octets",
    "free_octets",
    "create_file",
    "delete_file",
    "apply_operations",
    "assess_file_operations",
]

PATH_SEPARATOR = "/"

# Model limit on a file name.
MAX_NAME_CHARS = 64

# The two requests clause 6.23.4.1 offers.
OPERATIONS = ("create", "delete")


def _require_positive_int(value, label):
    """Return value as a positive whole octet or item count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def validate_file_name(name):
    """Return a file name after validating it."""
    if not isinstance(name, str):
        raise ValueError("file name must be a string, got %r" % (name,))
    if not name:
        raise ValueError("file name must not be empty")
    if len(name) > MAX_NAME_CHARS:
        raise ValueError(
            "file name is %d characters, past the model limit of %d"
            % (len(name), MAX_NAME_CHARS)
        )
    if PATH_SEPARATOR in name:
        raise ValueError(
            "file name %r carries the path separator; a name is one component" % name
        )
    if name.strip() != name:
        raise ValueError("file name %r carries leading or trailing whitespace" % name)
    return name


def build_repository(spec):
    """Return a repository state from its description.

    spec keys: path, capacity_octets, max_file_octets, max_files. Optional
    key: files, a mapping of name to {allocated_octets, locked, open}.
    """
    if not isinstance(spec, dict):
        raise ValueError("repository spec must be a mapping")
    for key in ("path", "capacity_octets", "max_file_octets", "max_files"):
        if key not in spec:
            raise ValueError("repository spec missing required key '%s'" % key)
    if not isinstance(spec["path"], str) or not spec["path"].startswith(PATH_SEPARATOR):
        raise ValueError(
            "repository path %r must start at the root of the file store"
            % (spec["path"],)
        )
    capacity = _require_positive_int(spec["capacity_octets"], "capacity_octets")
    per_file = _require_positive_int(spec["max_file_octets"], "max_file_octets")
    max_files = _require_positive_int(spec["max_files"], "max_files")
    if per_file > capacity:
        raise ValueError(
            "the per-file ceiling of %d octets is past the repository capacity of %d"
            % (per_file, capacity)
        )

    raw_files = spec.get("files", {})
    if not isinstance(raw_files, dict):
        raise ValueError("repository files must be a mapping of name to record")
    files = {}
    for name, record in raw_files.items():
        clean = validate_file_name(name)
        if not isinstance(record, dict):
            raise ValueError("file %r record must be a mapping" % clean)
        allocation = _require_positive_int(
            record.get("allocated_octets"), "allocated_octets of %r" % clean
        )
        if allocation > per_file:
            raise ValueError(
                "file %r is allocated %d octets, past the per-file ceiling of %d"
                % (clean, allocation, per_file)
            )
        locked = record.get("locked", False)
        held_open = record.get("open", False)
        for label, flag in (("locked", locked), ("open", held_open)):
            if not isinstance(flag, bool):
                raise ValueError(
                    "%s of file %r must be a boolean, got %r" % (label, clean, flag)
                )
        files[clean] = {
            "allocated_octets": allocation,
            "locked": locked,
            "open": held_open,
        }

    if len(files) > max_files:
        raise ValueError(
            "the repository already holds %d files, past its maximum of %d"
            % (len(files), max_files)
        )
    state = {
        "path": spec["path"],
        "capacity_octets": capacity,
        "max_file_octets": per_file,
        "max_files": max_files,
        "files": files,
    }
    if reserved_octets(state) > capacity:
        raise ValueError(
            "the declared files reserve %d octets, past the repository capacity of %d"
            % (reserved_octets(state), capacity)
        )
    return state


def _copy_repository(repository):
    """Return an independent copy of a repository state."""
    if not isinstance(repository, dict):
        raise ValueError("repository must be a mapping")
    for key in ("path", "capacity_octets", "max_file_octets", "max_files", "files"):
        if key not in repository:
            raise ValueError("repository missing required key '%s'" % key)
    return {
        "path": repository["path"],
        "capacity_octets": repository["capacity_octets"],
        "max_file_octets": repository["max_file_octets"],
        "max_files": repository["max_files"],
        "files": dict((name, dict(rec)) for name, rec in repository["files"].items()),
    }


def reserved_octets(repository):
    """Return the octets the repository has already reserved."""
    if not isinstance(repository, dict) or "files" not in repository:
        raise ValueError("repository must be a mapping carrying 'files'")
    return sum(record["allocated_octets"] for record in repository["files"].values())


def free_octets(repository):
    """Return the octets a new file could still be allocated."""
    state = _copy_repository(repository)
    return state["capacity_octets"] - reserved_octets(state)


def create_file(repository, name, allocation_octets):
    """Apply a create request. Returns (repository, verdict)."""
    state = _copy_repository(repository)
    clean = validate_file_name(name)
    allocation = _require_positive_int(allocation_octets, "allocation_octets")

    if clean in state["files"]:
        return state, {
            "operation": "create",
            "name": clean,
            "accepted": False,
            "reason": "a file of that name is already in the repository",
        }
    if len(state["files"]) >= state["max_files"]:
        return state, {
            "operation": "create",
            "name": clean,
            "accepted": False,
            "reason": "the repository already holds its maximum of %d files"
            % state["max_files"],
        }
    if allocation > state["max_file_octets"]:
        return state, {
            "operation": "create",
            "name": clean,
            "accepted": False,
            "reason": "an allocation of %d octets is past the per-file ceiling of %d"
            % (allocation, state["max_file_octets"]),
        }
    room = free_octets(state)
    if allocation > room:
        return state, {
            "operation": "create",
            "name": clean,
            "accepted": False,
            "reason": "an allocation of %d octets is past the %d octets free"
            % (allocation, room),
        }

    state["files"][clean] = {
        "allocated_octets": allocation,
        "locked": False,
        "open": False,
    }
    return state, {
        "operation": "create",
        "name": clean,
        "accepted": True,
        "reason": "",
    }


def delete_file(repository, name):
    """Apply a delete request. Returns (repository, verdict)."""
    state = _copy_repository(repository)
    clean = validate_file_name(name)

    record = state["files"].get(clean)
    if record is None:
        return state, {
            "operation": "delete",
            "name": clean,
            "accepted": False,
            "reason": "no file of that name is in the repository",
        }
    if record["locked"]:
        return state, {
            "operation": "delete",
            "name": clean,
            "accepted": False,
            "reason": "the file is locked",
        }
    if record["open"]:
        return state, {
            "operation": "delete",
            "name": clean,
            "accepted": False,
            "reason": "the file is held open by a transfer",
        }

    del state["files"][clean]
    return state, {
        "operation": "delete",
        "name": clean,
        "accepted": True,
        "reason": "",
    }


def apply_operations(repository, operations):
    """Replay a run of create and delete requests over a repository."""
    if not isinstance(operations, (list, tuple)):
        raise ValueError("operations must be a sequence")
    state = _copy_repository(repository)
    verdicts = []
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise ValueError("operations[%d] must be a mapping" % index)
        kind = operation.get("operation")
        if kind not in OPERATIONS:
            raise ValueError(
                "operations[%d] must be one of %s, got %r"
                % (index, ", ".join(OPERATIONS), kind)
            )
        if "name" not in operation:
            raise ValueError("operations[%d] missing required key 'name'" % index)
        if kind == "create":
            if "allocation_octets" not in operation:
                raise ValueError(
                    "operations[%d] missing required key 'allocation_octets'" % index
                )
            state, verdict = create_file(
                state, operation["name"], operation["allocation_octets"]
            )
        else:
            state, verdict = delete_file(state, operation["name"])
        verdict["index"] = index
        verdict["free_octets_after"] = free_octets(state)
        verdicts.append(verdict)
    return state, tuple(verdicts)


def assess_file_operations(spec):
    """Assess a clause 6.23.4.1 run of create and delete requests.

    spec keys: repository, operations.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("repository", "operations"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    start = build_repository(spec["repository"])
    opening_free = free_octets(start)
    final, verdicts = apply_operations(start, spec["operations"])

    accepted = tuple(v for v in verdicts if v["accepted"])
    rejected = tuple(v for v in verdicts if not v["accepted"])

    findings = []
    for verdict in rejected:
        findings.append(
            "request %d (%s %s) was refused: %s"
            % (verdict["index"], verdict["operation"], verdict["name"], verdict["reason"])
        )
    closing_free = free_octets(final)
    if closing_free < 0:
        raise ValueError("the run over-committed the repository capacity")
    if final["files"] and len(final["files"]) == final["max_files"]:
        findings.append(
            "the repository now holds its maximum of %d files; no create can be "
            "accepted until one is deleted" % final["max_files"]
        )

    return {
        "repository_path": final["path"],
        "opening_free_octets": opening_free,
        "closing_free_octets": closing_free,
        "reserved_octets": reserved_octets(final),
        "file_count": len(final["files"]),
        "file_names": tuple(sorted(final["files"])),
        "verdicts": verdicts,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "clean": not findings,
        "findings": findings,
    }
