"""Control of the storage function of the on-board packet stores.

Anchor: ECSS-E-ST-70-41C clause 6.15.3.3 (paraphrased into an
implementable procedure; no standard text is reproduced).

What the clause controls. A packet store holds telemetry packets until
the ground can read them out. Two things decide what actually lands in
it: whether its storage function is switched on at all, and which
report types the store has been told to accept. This module is the
decision layer over both, and over the partial-failure behaviour that
makes a multi-store command safe to send.

The clause's normative items reduce to six implementable rules:

    1  the storage function is per store, switched on and off by an
       enable or a disable naming one or more stores
    2  a command naming a store the on-board application does not hold
       fails for that store alone; the stores it does hold are still
       acted on, and every rejection is notified
    3  the same store named twice in one command is a malformed
       command, not a pair of outcomes, because the second occurrence
       cannot be acted on independently of the first
    4  enabling a store whose storage is already on is accepted and
       changes nothing; the operator gets the state they asked for
    5  the report types a store accepts are a set, so adding a type
       already present changes nothing and deleting a type that is
       absent fails for that type alone
    6  a store with its storage function on keeps storing throughout a
       report-type change; the type list decides what is offered to
       the store, never whether the store is running

Why partial failure is the interesting part. The obvious implementation
rejects the whole command as soon as one named store is unknown. That
turns a typo in the ninth store identifier into nine stores that did
not get enabled, discovered only when the recorder comes back empty.
The clause instead makes each named store its own unit of success, and
requires the failures to be notified rather than silently dropped.

Stdlib only, offline, deterministic.
"""

STORAGE_ON = "on"
STORAGE_OFF = "off"
VALID_STORAGE_STATES = (STORAGE_ON, STORAGE_OFF)

COMMAND_ENABLE = "enable-storage"
COMMAND_DISABLE = "disable-storage"
COMMAND_ADD_TYPES = "add-report-types"
COMMAND_DELETE_TYPES = "delete-report-types"
VALID_COMMANDS = (
    COMMAND_ENABLE,
    COMMAND_DISABLE,
    COMMAND_ADD_TYPES,
    COMMAND_DELETE_TYPES,
)

OUTCOME_APPLIED = "applied"
OUTCOME_NO_CHANGE = "accepted-no-change"
OUTCOME_REJECTED_UNKNOWN_STORE = "rejected-unknown-packet-store"
OUTCOME_REJECTED_UNKNOWN_TYPE = "rejected-report-type-not-configured"

VERDICT_ACCEPTED = "storage-control-accepted"
VERDICT_PARTIAL = "storage-control-partially-rejected"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _choice(label, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (label, ", ".join(allowed), value)
        )
    return value


def _type_list(label, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list, got %r" % (label, value))
    types = []
    for item in value:
        name = _text("%s entry" % label, item)
        if name in types:
            raise ValueError("%s repeats report type %r" % (label, name))
        types.append(name)
    return types


def validate_packet_store(record):
    """Normalize one packet store's storage-control configuration."""
    if not isinstance(record, dict):
        raise ValueError("packet store must be a mapping, got %r" % (record,))
    store_id = _text("packet store id", record.get("id"))
    return {
        "id": store_id,
        "storage_status": _choice(
            "packet store %s storage_status" % store_id,
            record.get("storage_status"),
            VALID_STORAGE_STATES,
        ),
        "report_types": _type_list(
            "packet store %s report_types" % store_id, record.get("report_types", [])
        ),
    }


def validate_store_set(records):
    """Normalize the held packet stores and reject a duplicate identity."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("packet stores must be a list, got %r" % (records,))
    stores = {}
    order = []
    for raw in records:
        store = validate_packet_store(raw)
        if store["id"] in stores:
            raise ValueError("duplicate packet store id %r" % store["id"])
        stores[store["id"]] = store
        order.append(store["id"])
    return {"stores": stores, "order": order}


def validate_command(record):
    """Normalize one storage-control command and reject a repeated store."""
    if not isinstance(record, dict):
        raise ValueError("command must be a mapping, got %r" % (record,))
    action = _choice("command action", record.get("action"), VALID_COMMANDS)
    raw = record.get("store_ids")
    if not isinstance(raw, (list, tuple)):
        raise ValueError("command store_ids must be a list, got %r" % (raw,))
    if not raw:
        raise ValueError("command %s names no packet store" % action)
    store_ids = []
    for item in raw:
        store_id = _text("command store id", item)
        if store_id in store_ids:
            raise ValueError(
                "command %s names packet store %r twice" % (action, store_id)
            )
        store_ids.append(store_id)
    command = {"action": action, "store_ids": store_ids}
    if action in (COMMAND_ADD_TYPES, COMMAND_DELETE_TYPES):
        types = _type_list("command report_types", record.get("report_types"))
        if not types:
            raise ValueError("command %s names no report type" % action)
        command["report_types"] = types
    elif record.get("report_types"):
        raise ValueError("command %s does not take report types" % action)
    return command


def set_storage_status(store, status):
    """Switch one store's storage function, reporting whether it moved."""
    current = validate_packet_store(store)
    wanted = _choice("storage status", status, VALID_STORAGE_STATES)
    changed = current["storage_status"] != wanted
    current["storage_status"] = wanted
    return {
        "store": current,
        "changed": changed,
        "outcome": OUTCOME_APPLIED if changed else OUTCOME_NO_CHANGE,
    }


def add_report_types(store, report_types):
    """Add report types to a store's list, ignoring the ones already held."""
    current = validate_packet_store(store)
    wanted = _type_list("report_types", report_types)
    added = [name for name in wanted if name not in current["report_types"]]
    current["report_types"] = current["report_types"] + added
    return {
        "store": current,
        "added": added,
        "already_present": [name for name in wanted if name not in added],
        "changed": bool(added),
        "outcome": OUTCOME_APPLIED if added else OUTCOME_NO_CHANGE,
    }


def delete_report_types(store, report_types):
    """Remove report types from a store's list, naming the absent ones."""
    current = validate_packet_store(store)
    wanted = _type_list("report_types", report_types)
    removed = [name for name in wanted if name in current["report_types"]]
    missing = [name for name in wanted if name not in removed]
    current["report_types"] = [
        name for name in current["report_types"] if name not in removed
    ]
    result = {
        "store": current,
        "removed": removed,
        "missing": missing,
        "changed": bool(removed),
        "outcome": OUTCOME_APPLIED if removed else OUTCOME_NO_CHANGE,
    }
    if missing:
        result["outcome"] = OUTCOME_REJECTED_UNKNOWN_TYPE
    return result


def apply_command(state, command):
    """Apply one command across the stores it names, store by store."""
    held = state["stores"]
    request = validate_command(command)
    results = []
    findings = []
    for store_id in request["store_ids"]:
        if store_id not in held:
            results.append(
                {
                    "store_id": store_id,
                    "outcome": OUTCOME_REJECTED_UNKNOWN_STORE,
                    "changed": False,
                }
            )
            findings.append(
                "command %s names packet store %r, which the application does "
                "not hold; the command failed for that store only"
                % (request["action"], store_id)
            )
            continue
        store = held[store_id]
        if request["action"] == COMMAND_ENABLE:
            step = set_storage_status(store, STORAGE_ON)
        elif request["action"] == COMMAND_DISABLE:
            step = set_storage_status(store, STORAGE_OFF)
        elif request["action"] == COMMAND_ADD_TYPES:
            step = add_report_types(store, request["report_types"])
        else:
            step = delete_report_types(store, request["report_types"])
        held[store_id] = step["store"]
        entry = {
            "store_id": store_id,
            "outcome": step["outcome"],
            "changed": step["changed"],
        }
        for key in ("added", "removed", "missing", "already_present"):
            if key in step:
                entry[key] = step[key]
        results.append(entry)
        for name in step.get("missing", []):
            findings.append(
                "packet store %s was not storing report type %r, so it could "
                "not be deleted" % (store_id, name)
            )
    return {"action": request["action"], "results": results, "findings": findings}


def apply_commands(records, commands):
    """Run a command sequence against the held stores, in order."""
    state = validate_store_set(records)
    if not isinstance(commands, (list, tuple)):
        raise ValueError("commands must be a list, got %r" % (commands,))
    steps = [apply_command(state, command) for command in commands]
    return {"state": state, "steps": steps}


def storage_control_configuration(state):
    """Report each store's storage status and report-type list, in order."""
    return {
        "entries": [
            {
                "id": store_id,
                "storage_status": state["stores"][store_id]["storage_status"],
                "report_types": list(state["stores"][store_id]["report_types"]),
                "report_type_count": len(state["stores"][store_id]["report_types"]),
            }
            for store_id in state["order"]
        ],
        "store_count": len(state["order"]),
        "storing_count": sum(
            1
            for store_id in state["order"]
            if state["stores"][store_id]["storage_status"] == STORAGE_ON
        ),
    }


def assess_storage_control(records, commands):
    """Full clause 6.15.3.3 handling: apply, report, and name the failures."""
    run = apply_commands(records, commands)
    findings = []
    rejected = []
    for step in run["steps"]:
        findings.extend(step["findings"])
        for entry in step["results"]:
            if entry["outcome"].startswith("rejected"):
                rejected.append((step["action"], entry["store_id"]))
    configuration = storage_control_configuration(run["state"])
    accepted = not rejected
    return {
        "configuration": configuration,
        "steps": run["steps"],
        "rejected": rejected,
        "rejected_count": len(rejected),
        "accepted": accepted,
        "verdict": VERDICT_ACCEPTED if accepted else VERDICT_PARTIAL,
        "findings": findings,
    }
