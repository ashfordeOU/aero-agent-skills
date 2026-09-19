"""Loading, activating and deleting on-board control procedures.

Anchor: ECSS-E-ST-70-41C clause 6.18.4.4 (paraphrased into an
implementable procedure; no standard text is reproduced).

What this job is. An on-board control procedure gets aboard, gets run,
and eventually gets removed, and every one of those three moves has
preconditions that the spacecraft has to enforce for itself. The ground
is a round trip away; by the time it learns a command was wrong the
wrong thing has already happened. So the store refuses, on board, and
says why.

The three moves and what each one actually checks:

  load     -- copy a procedure into the on-board store. It has to fit
              the free space, it has to arrive intact, and the id it
              claims has to be free. An uplink that flipped a bit
              produces a procedure that is syntactically a procedure
              and behaviourally something else, so the checksum is the
              gate, not a formality.
  activate -- hand a loaded procedure to the engine and start it. It
              has to be aboard, it must not already be running, and
              there has to be an engine slot free. Activating twice is
              not idempotent: it is two runs of the same sequence, and
              for a deployment that is the difference between one
              release and two attempts.
  delete   -- remove it from the store and get the octets back. It must
              be aboard, it must not be running, and it must not be one
              of the procedures the mission has marked as permanent.

Why each refusal is separate. "It did not work" is not an operations
product. A store that answers with a single failure code makes the
ground guess between a full store, a corrupted uplink and an id
collision -- three problems with three different fixes, one of which is
a re-uplink that will fail exactly the same way.

What this module deliberately does not do. It does not hold or release
a running procedure (that is the suspend-and-resume job) and it does
not settle what a status means (that is the execution-status job). It
moves procedures in and out of the store and in and out of the engine.

Stdlib only, offline, deterministic.
"""

import zlib

OUTCOME_LOADED = "loaded"
OUTCOME_REFUSED_ALREADY_LOADED = "refused-same-version-already-loaded"
OUTCOME_REFUSED_VERSION_CONFLICT = "refused-different-version-occupies-id"
OUTCOME_REFUSED_STORE_FULL = "refused-store-has-no-room"
OUTCOME_REFUSED_CHECKSUM_MISMATCH = "refused-checksum-mismatch-on-uplink"
OUTCOME_REFUSED_OVER_ENGINE_LIMIT = "refused-over-engine-procedure-size-limit"

OUTCOME_ACTIVATED = "activated"
OUTCOME_REFUSED_NOT_LOADED = "refused-not-loaded"
OUTCOME_REFUSED_ALREADY_ACTIVE = "refused-already-active"
OUTCOME_REFUSED_NO_ENGINE_SLOT = "refused-no-free-engine-slot"

OUTCOME_STOPPED = "stopped"
OUTCOME_REFUSED_NOT_ACTIVE = "refused-not-active"

OUTCOME_DELETED = "deleted"
OUTCOME_REFUSED_ACTIVE = "refused-active-procedure-cannot-be-deleted"
OUTCOME_REFUSED_PROTECTED = "refused-procedure-marked-permanent"

OPERATION_LOAD = "load"
OPERATION_ACTIVATE = "activate"
OPERATION_STOP = "stop"
OPERATION_DELETE = "delete"
VALID_OPERATIONS = (
    OPERATION_LOAD,
    OPERATION_ACTIVATE,
    OPERATION_STOP,
    OPERATION_DELETE,
)

ACCEPTING_OUTCOMES = (
    OUTCOME_LOADED,
    OUTCOME_ACTIVATED,
    OUTCOME_STOPPED,
    OUTCOME_DELETED,
)


def _integer(label, value, minimum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def code_checksum(code):
    """Checksum of a procedure image, as the on-board loader computes it."""
    if not isinstance(code, str) or not code:
        raise ValueError("procedure code must be a non-empty string")
    return zlib.crc32(code.encode("utf-8")) & 0xFFFFFFFF


def code_octets(code):
    """Size of a procedure image in octets."""
    if not isinstance(code, str) or not code:
        raise ValueError("procedure code must be a non-empty string")
    return len(code.encode("utf-8"))


def validate_upload(upload):
    """Validate an uplinked procedure image and return a normalized copy."""
    if not isinstance(upload, dict):
        raise ValueError("procedure upload must be a mapping")
    proc_id = _text("procedure id", upload.get("id"))
    version = _integer("procedure %s version" % proc_id, upload.get("version"), 1)
    code = upload.get("code")
    if not isinstance(code, str) or not code:
        raise ValueError(
            "procedure %s carries no code image" % proc_id
        )
    permanent = upload.get("permanent", False)
    if not isinstance(permanent, bool):
        raise ValueError(
            "procedure %s permanent flag must be a boolean, got %r"
            % (proc_id, permanent)
        )
    declared = upload.get("declared_checksum")
    if declared is not None:
        _integer("procedure %s declared_checksum" % proc_id, declared, 0)
    return {
        "id": proc_id,
        "version": version,
        "code": code,
        "octets": code_octets(code),
        "computed_checksum": code_checksum(code),
        "declared_checksum": declared,
        "permanent": permanent,
    }


def upload_is_intact(upload):
    """Did the image survive the uplink, as far as the checksum can say?"""
    working = validate_upload(upload)
    if working["declared_checksum"] is None:
        # No declared checksum means nothing was promised, so nothing can
        # be contradicted. The loader takes it; the operator carries the
        # risk knowingly.
        return True
    return working["declared_checksum"] == working["computed_checksum"]


def create_store(capacity_octets, max_active, max_procedure_octets=None):
    """Create an empty on-board procedure store."""
    capacity = _integer("capacity_octets", capacity_octets, 1)
    slots = _integer("max_active", max_active, 1)
    limit = capacity
    if max_procedure_octets is not None:
        limit = _integer("max_procedure_octets", max_procedure_octets, 1)
        if limit > capacity:
            raise ValueError(
                "engine procedure limit %d exceeds the whole store capacity %d"
                % (limit, capacity)
            )
    return {
        "capacity_octets": capacity,
        "max_active": slots,
        "max_procedure_octets": limit,
        "procedures": {},
        "load_order": [],
    }


def validate_store(store):
    """Validate a store and return an independent working copy."""
    if not isinstance(store, dict):
        raise ValueError("procedure store must be a mapping")
    capacity = _integer("capacity_octets", store.get("capacity_octets"), 1)
    slots = _integer("max_active", store.get("max_active"), 1)
    limit = _integer(
        "max_procedure_octets", store.get("max_procedure_octets", capacity), 1
    )
    if limit > capacity:
        raise ValueError(
            "engine procedure limit %d exceeds the whole store capacity %d"
            % (limit, capacity)
        )
    procedures = store.get("procedures", {})
    if not isinstance(procedures, dict):
        raise ValueError("store procedures must be a mapping")
    order = store.get("load_order", [])
    if not isinstance(order, list):
        raise ValueError("store load_order must be a list")
    copied = {}
    used = 0
    active = 0
    for proc_id, record in procedures.items():
        if not isinstance(record, dict):
            raise ValueError("stored procedure %r must be a mapping" % (proc_id,))
        entry = {
            "id": _text("stored procedure id", record.get("id", proc_id)),
            "version": _integer("stored procedure version",
                                record.get("version"), 1),
            "octets": _integer("stored procedure octets",
                               record.get("octets"), 1),
            "checksum": _integer("stored procedure checksum",
                                 record.get("checksum"), 0),
            "permanent": bool(record.get("permanent", False)),
            "active": bool(record.get("active", False)),
        }
        if entry["id"] != proc_id:
            raise ValueError(
                "stored procedure keyed %r carries id %r" % (proc_id, entry["id"])
            )
        used += entry["octets"]
        active += 1 if entry["active"] else 0
        copied[proc_id] = entry
    if used > capacity:
        raise ValueError(
            "store holds %d octets over its %d octet capacity" % (used, capacity)
        )
    if active > slots:
        raise ValueError(
            "store has %d active procedures over its %d engine slots"
            % (active, slots)
        )
    if sorted(order) != sorted(copied):
        raise ValueError("store load_order does not match its procedures")
    return {
        "capacity_octets": capacity,
        "max_active": slots,
        "max_procedure_octets": limit,
        "procedures": copied,
        "load_order": list(order),
    }


def used_octets(store):
    """Octets the store currently holds."""
    working = validate_store(store)
    return sum(p["octets"] for p in working["procedures"].values())


def free_octets(store):
    """Octets the store can still take."""
    working = validate_store(store)
    return working["capacity_octets"] - used_octets(working)


def is_loaded(store, proc_id):
    """Is any version of this procedure aboard?"""
    return _text("procedure id", proc_id) in validate_store(store)["procedures"]


def is_active(store, proc_id):
    """Is this procedure running on the engine now?"""
    working = validate_store(store)
    record = working["procedures"].get(_text("procedure id", proc_id))
    return bool(record and record["active"])


def active_count(store):
    """How many engine slots are taken."""
    working = validate_store(store)
    return sum(1 for p in working["procedures"].values() if p["active"])


def free_engine_slots(store):
    """How many engine slots are left."""
    working = validate_store(store)
    return working["max_active"] - active_count(working)


def load_procedure(store, upload):
    """Load an uplinked procedure into the store; return store and outcome."""
    working = validate_store(store)
    image = validate_upload(upload)
    existing = working["procedures"].get(image["id"])
    if existing is not None:
        if existing["version"] == image["version"]:
            return working, OUTCOME_REFUSED_ALREADY_LOADED
        return working, OUTCOME_REFUSED_VERSION_CONFLICT
    if image["octets"] > working["max_procedure_octets"]:
        return working, OUTCOME_REFUSED_OVER_ENGINE_LIMIT
    if not upload_is_intact(image):
        return working, OUTCOME_REFUSED_CHECKSUM_MISMATCH
    if image["octets"] > free_octets(working):
        return working, OUTCOME_REFUSED_STORE_FULL
    working["procedures"][image["id"]] = {
        "id": image["id"],
        "version": image["version"],
        "octets": image["octets"],
        "checksum": image["computed_checksum"],
        "permanent": image["permanent"],
        "active": False,
    }
    working["load_order"].append(image["id"])
    return working, OUTCOME_LOADED


def activate_procedure(store, proc_id):
    """Start a loaded procedure on the engine; return store and outcome."""
    working = validate_store(store)
    name = _text("procedure id", proc_id)
    record = working["procedures"].get(name)
    if record is None:
        return working, OUTCOME_REFUSED_NOT_LOADED
    if record["active"]:
        return working, OUTCOME_REFUSED_ALREADY_ACTIVE
    if free_engine_slots(working) <= 0:
        return working, OUTCOME_REFUSED_NO_ENGINE_SLOT
    record["active"] = True
    return working, OUTCOME_ACTIVATED


def stop_procedure(store, proc_id):
    """Stop a running procedure and release its engine slot."""
    working = validate_store(store)
    name = _text("procedure id", proc_id)
    record = working["procedures"].get(name)
    if record is None:
        return working, OUTCOME_REFUSED_NOT_LOADED
    if not record["active"]:
        return working, OUTCOME_REFUSED_NOT_ACTIVE
    record["active"] = False
    return working, OUTCOME_STOPPED


def delete_procedure(store, proc_id):
    """Remove a procedure from the store and give the octets back."""
    working = validate_store(store)
    name = _text("procedure id", proc_id)
    record = working["procedures"].get(name)
    if record is None:
        return working, OUTCOME_REFUSED_NOT_LOADED
    if record["active"]:
        return working, OUTCOME_REFUSED_ACTIVE
    if record["permanent"]:
        return working, OUTCOME_REFUSED_PROTECTED
    del working["procedures"][name]
    working["load_order"] = [i for i in working["load_order"] if i != name]
    return working, OUTCOME_DELETED


def apply_operations(store, operations):
    """Apply a command sequence to the store; return the store and outcomes."""
    if not isinstance(operations, list):
        raise ValueError("operations must be a list")
    working = validate_store(store)
    results = []
    for operation in operations:
        if not isinstance(operation, dict):
            raise ValueError("each operation must be a mapping")
        kind = operation.get("operation")
        if kind not in VALID_OPERATIONS:
            raise ValueError(
                "unknown operation %r (expected one of %s)"
                % (kind, ", ".join(VALID_OPERATIONS))
            )
        if kind == OPERATION_LOAD:
            upload = operation.get("upload")
            working, outcome = load_procedure(working, upload)
            name = validate_upload(upload)["id"]
        else:
            name = _text("procedure id", operation.get("id"))
            if kind == OPERATION_ACTIVATE:
                working, outcome = activate_procedure(working, name)
            elif kind == OPERATION_STOP:
                working, outcome = stop_procedure(working, name)
            else:
                working, outcome = delete_procedure(working, name)
        results.append({
            "operation": kind,
            "id": name,
            "outcome": outcome,
            "accepted": outcome in ACCEPTING_OUTCOMES,
        })
    return working, results


def report_store(store):
    """Deterministic report of what the store holds and what is running."""
    working = validate_store(store)
    used = used_octets(working)
    return {
        "capacity_octets": working["capacity_octets"],
        "used_octets": used,
        "free_octets": working["capacity_octets"] - used,
        "fill_fraction": used / float(working["capacity_octets"]),
        "procedure_count": len(working["procedures"]),
        "loaded_ids": list(working["load_order"]),
        "active_ids": [
            i for i in working["load_order"]
            if working["procedures"][i]["active"]
        ],
        "permanent_ids": [
            i for i in working["load_order"]
            if working["procedures"][i]["permanent"]
        ],
        "max_active": working["max_active"],
        "active_count": active_count(working),
        "free_engine_slots": free_engine_slots(working),
        "full": used == working["capacity_octets"],
    }


def assess_command_sequence(store_spec, operations):
    """Run a whole command sequence against a fresh store and grade it."""
    if not isinstance(store_spec, dict):
        raise ValueError("store_spec must be a mapping")
    store = create_store(
        store_spec.get("capacity_octets"),
        store_spec.get("max_active"),
        store_spec.get("max_procedure_octets"),
    )
    store, results = apply_operations(store, operations)
    refusals = [r for r in results if not r["accepted"]]
    grouped = {}
    for result in results:
        grouped.setdefault(result["outcome"], []).append(result["id"])
    return {
        "store": report_store(store),
        "results": results,
        "grouped_by_outcome": grouped,
        "accepted_count": len(results) - len(refusals),
        "refused_count": len(refusals),
        "first_refusal": refusals[0] if refusals else None,
        "all_accepted": not refusals,
    }
