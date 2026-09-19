"""File access protection (on-board file management service).

Anchor: ECSS-E-ST-70-41C clause 6.23.4.3 (paraphrased into an
implementable procedure; no standard text is reproduced).

What protection is here. A file in an on-board repository can be
locked. A locked file cannot be deleted, cannot be renamed or moved,
cannot be overwritten, and cannot be the destination of a copy. It can
still be read, and it can still be downlinked. The lock is a guard
against loss of content, not a guard against access -- the inversion
that costs a mission a log file is reading it as the second.

Who is protected from whom. Two separate things refuse a destructive
operation and they compose rather than override:

  the lock       -- set deliberately by the ground or by an on-board
                    process that wants the content to survive; cleared
                    only by an explicit unlock.
  an open handle -- an uplink still writing the file or a downlink
                    still reading it. Nobody set it and nobody can
                    clear it except the transfer finishing.

A file can be unlocked and still held, or locked and idle. An
operation is permitted only when neither refuses it, and when one does
the report has to say which, because the fix is different: an unlock
command against the first, patience against the second.

Locking is idempotent, unlocking a file that is not locked is not.
Re-locking an already locked file changes nothing and is accepted;
unlocking one that was never locked is reported, because it usually
means the operator is working on the wrong file and believes they have
just cleared a guard that is still set somewhere else.

Stdlib only, offline, deterministic.
"""

PATH_SEPARATOR = "/"
MAX_NAME_OCTETS = 64

OP_READ = "read"
OP_DOWNLINK = "downlink"
OP_DELETE = "delete"
OP_RENAME = "rename"
OP_MOVE = "move"
OP_OVERWRITE = "overwrite"
OP_COPY_DESTINATION = "copy-destination"
VALID_OPERATIONS = (
    OP_READ,
    OP_DOWNLINK,
    OP_DELETE,
    OP_RENAME,
    OP_MOVE,
    OP_OVERWRITE,
    OP_COPY_DESTINATION,
)
# The operations a lock exists to refuse. Reading and downlinking are
# deliberately absent: the lock guards content, not access.
DESTRUCTIVE_OPERATIONS = (
    OP_DELETE,
    OP_RENAME,
    OP_MOVE,
    OP_OVERWRITE,
    OP_COPY_DESTINATION,
)

HANDLE_NONE = "none"
HANDLE_UPLINK = "uplink-writing"
HANDLE_DOWNLINK = "downlink-reading"
VALID_HANDLES = (HANDLE_NONE, HANDLE_UPLINK, HANDLE_DOWNLINK)

PERMITTED = "permitted"
REFUSED_LOCKED = "refused-file-locked"
REFUSED_HELD = "refused-transfer-in-progress"
REFUSED_UNKNOWN_FILE = "refused-file-not-found"

LOCK_APPLIED = "lock-applied"
LOCK_ALREADY_SET = "lock-already-set"
UNLOCK_APPLIED = "unlock-applied"
UNLOCK_WAS_NOT_LOCKED = "unlock-of-a-file-that-was-not-locked"
LOCK_REFUSED_UNKNOWN_FILE = "refused-file-not-found"

_FORBIDDEN_NAME_CHARS = (PATH_SEPARATOR, "\\", "\t", "\n", "\r", "\0")


def _flag(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_file_name(name):
    """Validate a file name inside a repository and return it unchanged."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("file name must be a non-empty string")
    if name != name.strip():
        raise ValueError("file name %r has leading or trailing whitespace" % (name,))
    for bad in _FORBIDDEN_NAME_CHARS:
        if bad in name:
            raise ValueError("file name %r contains a forbidden character" % (name,))
    if name in (".", ".."):
        raise ValueError("file name %r is a relative marker, not a name" % (name,))
    if len(name.encode("utf-8")) > MAX_NAME_OCTETS:
        raise ValueError(
            "file name %r is longer than %d octets" % (name, MAX_NAME_OCTETS)
        )
    return name


def validate_operation(operation):
    """Validate an operation token against the known set."""
    if operation not in VALID_OPERATIONS:
        raise ValueError(
            "unknown operation %r (expected one of %s)"
            % (operation, ", ".join(VALID_OPERATIONS))
        )
    return operation


def validate_protected_file(record):
    """Validate one file's protection state and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("protected file record must be a mapping")
    name = validate_file_name(record.get("name"))
    locked = _flag("file %s locked" % name, record.get("locked", False))
    handle = record.get("handle", HANDLE_NONE)
    if handle not in VALID_HANDLES:
        raise ValueError("file %s has unknown handle state %r" % (name, handle))
    return {"name": name, "locked": locked, "handle": handle}


def build_protection_table(records):
    """Build a name-to-protection-state table for one repository."""
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    table = {}
    for record in records:
        normalized = validate_protected_file(record)
        if normalized["name"] in table:
            raise ValueError("duplicate file name %r" % (normalized["name"],))
        table[normalized["name"]] = normalized
    return table


def is_destructive(operation):
    """Is this an operation the lock exists to refuse?"""
    return validate_operation(operation) in DESTRUCTIVE_OPERATIONS


def is_held(record):
    """Does a transfer currently hold this file open?"""
    return validate_protected_file(record)["handle"] != HANDLE_NONE


def assess_operation(table, file_name, operation):
    """Decide one operation against one file's protection state."""
    if not isinstance(table, dict):
        raise ValueError("protection table must be a mapping")
    name = validate_file_name(file_name)
    op = validate_operation(operation)
    record = table.get(name)
    if record is None:
        return {
            "file_name": name,
            "operation": op,
            "verdict": REFUSED_UNKNOWN_FILE,
            "blocked_by_lock": False,
            "blocked_by_handle": False,
            "remedy": "check the repository and the file name",
        }
    record = validate_protected_file(record)
    if not is_destructive(op):
        return {
            "file_name": name,
            "operation": op,
            "verdict": PERMITTED,
            "blocked_by_lock": False,
            "blocked_by_handle": False,
            "remedy": None,
        }
    by_lock = record["locked"]
    by_handle = record["handle"] != HANDLE_NONE
    if by_lock:
        verdict = REFUSED_LOCKED
        remedy = "unlock the file, then reissue"
    elif by_handle:
        verdict = REFUSED_HELD
        remedy = "wait for the %s to finish, then reissue" % record["handle"]
    else:
        verdict = PERMITTED
        remedy = None
    return {
        "file_name": name,
        "operation": op,
        "verdict": verdict,
        "blocked_by_lock": by_lock,
        "blocked_by_handle": by_handle,
        "remedy": remedy,
    }


def lock_file(table, file_name):
    """Apply a lock; return the new table and the outcome."""
    if not isinstance(table, dict):
        raise ValueError("protection table must be a mapping")
    name = validate_file_name(file_name)
    working = {k: dict(v) for k, v in table.items()}
    record = working.get(name)
    if record is None:
        return working, LOCK_REFUSED_UNKNOWN_FILE
    if record["locked"]:
        return working, LOCK_ALREADY_SET
    record["locked"] = True
    return working, LOCK_APPLIED


def unlock_file(table, file_name):
    """Clear a lock; return the new table and the outcome."""
    if not isinstance(table, dict):
        raise ValueError("protection table must be a mapping")
    name = validate_file_name(file_name)
    working = {k: dict(v) for k, v in table.items()}
    record = working.get(name)
    if record is None:
        return working, LOCK_REFUSED_UNKNOWN_FILE
    if not record["locked"]:
        return working, UNLOCK_WAS_NOT_LOCKED
    record["locked"] = False
    return working, UNLOCK_APPLIED


def set_handle(table, file_name, handle):
    """Record that a transfer opened or released a file."""
    if handle not in VALID_HANDLES:
        raise ValueError("unknown handle state %r" % (handle,))
    name = validate_file_name(file_name)
    working = {k: dict(v) for k, v in table.items()}
    if name not in working:
        raise ValueError("no such file %r in this repository" % (name,))
    working[name]["handle"] = handle
    return working


def report_protection_state(table):
    """Deterministic protection report for one repository."""
    if not isinstance(table, dict):
        raise ValueError("protection table must be a mapping")
    rows = []
    for name in sorted(table):
        record = validate_protected_file(table[name])
        rows.append(
            {
                "file_name": record["name"],
                "locked": record["locked"],
                "handle": record["handle"],
                "held": record["handle"] != HANDLE_NONE,
                "destructive_operations_refused": record["locked"]
                or record["handle"] != HANDLE_NONE,
            }
        )
    return {
        "files": rows,
        "file_count": len(rows),
        "locked_count": sum(1 for r in rows if r["locked"]),
        "held_count": sum(1 for r in rows if r["held"]),
        "protected_count": sum(
            1 for r in rows if r["destructive_operations_refused"]
        ),
        "fully_unprotected": all(
            not r["destructive_operations_refused"] for r in rows
        ),
    }


def screen_operation_plan(records, plan):
    """Screen a planned operation set against the protection state."""
    table = build_protection_table(records)
    if not isinstance(plan, list):
        raise ValueError("plan must be a list")
    verdicts = []
    for item in plan:
        if not isinstance(item, dict):
            raise ValueError("each planned operation must be a mapping")
        verdicts.append(
            assess_operation(table, item.get("file_name"), item.get("operation"))
        )
    refused = [v for v in verdicts if v["verdict"] != PERMITTED]
    grouped = {}
    for verdict in refused:
        grouped[verdict["verdict"]] = grouped.get(verdict["verdict"], 0) + 1
    return {
        "verdicts": verdicts,
        "permitted_count": len(verdicts) - len(refused),
        "refused_count": len(refused),
        "refusals_by_reason": grouped,
        "unlock_would_clear": sum(
            1
            for v in refused
            if v["blocked_by_lock"] and not v["blocked_by_handle"]
        ),
        "waiting_would_clear": sum(
            1
            for v in refused
            if v["blocked_by_handle"] and not v["blocked_by_lock"]
        ),
        "plan_executable": not refused,
    }
