"""Attributes of an on-board file.

Anchor: ECSS-E-ST-70-41C clause 6.23.3.4 (attributes of an on-board file of
the file management service). Paraphrased into an implementable procedure; no
standard text is reproduced.

Model implemented here
----------------------
An on-board file is described by the repository it sits in, its name, the
octets it currently holds, the octets it is allowed to grow to, and whether it
is locked. Those five together are one record: a size above the allocation is
not a large file, it is an inconsistent record, and a lock is not advisory —
it is what makes a write or a delete inadmissible.

Procedure implemented here
--------------------------
1. Validate a file name and a repository path.
2. Validate the attribute record as a whole and normalise it.
3. Derive the octets left inside the allocation and the occupancy of the file.
4. Decide whether a write of a given length is admissible, and whether a
   delete is.
5. Lock and unlock a file without touching the rest of the record.
6. Summarise a repository of such records and report its findings.
"""

__all__ = [
    "FILE_ATTRIBUTE_FIELDS",
    "PATH_SEPARATOR",
    "MAX_NAME_CHARS",
    "OCCUPANCY_TOLERANCE",
    "DEFAULT_NEAR_FULL_RATIO",
    "validate_file_name",
    "validate_repository_path",
    "validate_file_attributes",
    "remaining_octets",
    "occupancy_ratio",
    "may_write",
    "may_delete",
    "set_lock",
    "assess_file_attributes",
]

# The five attributes this record carries.
FILE_ATTRIBUTE_FIELDS = (
    "repository_path",
    "file_name",
    "size_octets",
    "allocated_octets",
    "locked",
)

PATH_SEPARATOR = "/"

# Model limit on a file name.
MAX_NAME_CHARS = 64

# Representation tolerance used when an occupancy lands on a threshold.
OCCUPANCY_TOLERANCE = 1e-9

# Occupancy at or above which a file is reported as near full.
DEFAULT_NEAR_FULL_RATIO = 0.9


def _require_non_negative_int(value, label):
    """Return value as a non-negative whole octet count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _require_positive_int(value, label):
    """Return value as a positive whole octet count."""
    value = _require_non_negative_int(value, label)
    if value == 0:
        raise ValueError("%s must be positive, got 0" % label)
    return value


def validate_file_name(name):
    """Return a file name after validating it."""
    if not isinstance(name, str):
        raise ValueError("file_name must be a string, got %r" % (name,))
    if not name:
        raise ValueError("file_name must not be empty")
    if len(name) > MAX_NAME_CHARS:
        raise ValueError(
            "file_name is %d characters, past the model limit of %d"
            % (len(name), MAX_NAME_CHARS)
        )
    if PATH_SEPARATOR in name:
        raise ValueError(
            "file_name %r carries the path separator; a name is one component" % name
        )
    if name.strip() != name:
        raise ValueError("file_name %r carries leading or trailing whitespace" % name)
    return name


def validate_repository_path(path):
    """Return a repository path after validating its shape."""
    if not isinstance(path, str):
        raise ValueError("repository_path must be a string, got %r" % (path,))
    if not path.startswith(PATH_SEPARATOR):
        raise ValueError(
            "repository_path %r must start at the root of the file store" % path
        )
    body = path[1:]
    if not body:
        raise ValueError("repository_path names no repository")
    if body.endswith(PATH_SEPARATOR):
        raise ValueError("repository_path must not end with the path separator")
    for component in body.split(PATH_SEPARATOR):
        if not component:
            raise ValueError("repository_path %r has an empty component" % path)
        if component.strip() != component:
            raise ValueError(
                "repository_path %r has a padded component" % path
            )
    return path


def validate_file_attributes(attributes):
    """Return a normalised, self-consistent file attribute record."""
    if not isinstance(attributes, dict):
        raise ValueError("attributes must be a mapping")
    for key in FILE_ATTRIBUTE_FIELDS:
        if key not in attributes:
            raise ValueError("attributes missing required key '%s'" % key)
    if not isinstance(attributes["locked"], bool):
        raise ValueError(
            "locked must be a boolean, got %r" % (attributes["locked"],)
        )
    size = _require_non_negative_int(attributes["size_octets"], "size_octets")
    allocated = _require_positive_int(attributes["allocated_octets"], "allocated_octets")
    if size > allocated:
        raise ValueError(
            "size %d octets is past the allocation of %d octets; the record is "
            "inconsistent" % (size, allocated)
        )
    return {
        "repository_path": validate_repository_path(attributes["repository_path"]),
        "file_name": validate_file_name(attributes["file_name"]),
        "size_octets": size,
        "allocated_octets": allocated,
        "locked": attributes["locked"],
    }


def remaining_octets(attributes):
    """Return the octets the file may still grow by."""
    record = validate_file_attributes(attributes)
    return record["allocated_octets"] - record["size_octets"]


def occupancy_ratio(attributes):
    """Return the occupancy of the file as a fraction of its allocation."""
    record = validate_file_attributes(attributes)
    return record["size_octets"] / float(record["allocated_octets"])


def may_write(attributes, octets):
    """Decide whether a write of this many octets is admissible."""
    record = validate_file_attributes(attributes)
    wanted = _require_positive_int(octets, "octets")
    if record["locked"]:
        return {
            "permitted": False,
            "reason": "the file is locked",
            "resulting_size_octets": record["size_octets"],
        }
    room = record["allocated_octets"] - record["size_octets"]
    if wanted > room:
        return {
            "permitted": False,
            "reason": "a write of %d octets is past the %d octets left in the "
            "allocation" % (wanted, room),
            "resulting_size_octets": record["size_octets"],
        }
    return {
        "permitted": True,
        "reason": "",
        "resulting_size_octets": record["size_octets"] + wanted,
    }


def may_delete(attributes):
    """Decide whether the file may be deleted."""
    record = validate_file_attributes(attributes)
    if record["locked"]:
        return {"permitted": False, "reason": "the file is locked"}
    return {"permitted": True, "reason": ""}


def set_lock(attributes, locked):
    """Return the record with its lock status set, nothing else changed."""
    if not isinstance(locked, bool):
        raise ValueError("locked must be a boolean, got %r" % (locked,))
    record = validate_file_attributes(attributes)
    record["locked"] = locked
    return record


def assess_file_attributes(spec):
    """Assess a clause 6.23.3.4 set of file attribute records.

    spec keys: files. Optional keys: near_full_ratio, pending_write_octets.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "files" not in spec:
        raise ValueError("spec missing required key 'files'")
    if not isinstance(spec["files"], (list, tuple)):
        raise ValueError("spec['files'] must be a sequence")

    threshold = spec.get("near_full_ratio", DEFAULT_NEAR_FULL_RATIO)
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise ValueError("near_full_ratio must be a number, got %r" % (threshold,))
    threshold = float(threshold)
    if threshold <= 0.0 or threshold > 1.0:
        raise ValueError(
            "near_full_ratio %r must sit in the half-open span (0, 1]" % (threshold,)
        )
    pending = spec.get("pending_write_octets")
    if pending is not None:
        pending = _require_positive_int(pending, "pending_write_octets")

    records = []
    seen = set()
    for index, raw in enumerate(spec["files"]):
        try:
            record = validate_file_attributes(raw)
        except ValueError as exc:
            raise ValueError("files[%d]: %s" % (index, exc))
        key = (record["repository_path"], record["file_name"])
        if key in seen:
            raise ValueError(
                "file %s%s%s is declared twice"
                % (record["repository_path"], PATH_SEPARATOR, record["file_name"])
            )
        seen.add(key)
        records.append(record)

    findings = []
    near_full = []
    locked = []
    write_blocked = []
    for record in records:
        ratio = occupancy_ratio(record)
        name = record["repository_path"] + PATH_SEPARATOR + record["file_name"]
        if ratio >= threshold - OCCUPANCY_TOLERANCE:
            near_full.append(name)
        if record["locked"]:
            locked.append(name)
        if pending is not None and not may_write(record, pending)["permitted"]:
            write_blocked.append(name)

    if near_full:
        findings.append(
            "%d files sit at or above the near-full occupancy of %g"
            % (len(near_full), threshold)
        )
    if pending is not None and write_blocked:
        findings.append(
            "a pending write of %d octets is inadmissible on %d files"
            % (pending, len(write_blocked))
        )

    total_size = sum(r["size_octets"] for r in records)
    total_allocated = sum(r["allocated_octets"] for r in records)
    return {
        "file_count": len(records),
        "total_size_octets": total_size,
        "total_allocated_octets": total_allocated,
        "total_remaining_octets": total_allocated - total_size,
        "overall_occupancy": (
            total_size / float(total_allocated) if total_allocated else 0.0
        ),
        "near_full": tuple(near_full),
        "locked": tuple(locked),
        "write_blocked": tuple(write_blocked),
        "attribute_fields": FILE_ATTRIBUTE_FIELDS,
        "clean": not findings,
        "findings": findings,
    }
