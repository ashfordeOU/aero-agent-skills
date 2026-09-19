"""Management of the on-board packet stores: create, delete, reshape.

Anchor: ECSS-E-ST-70-41C clause 6.15.3.8 (paraphrased into an
implementable procedure; no standard text is reproduced).

What the clause manages. Everything in the storage and retrieval
service that changes the packet stores themselves rather than their
contents: creating a store, deleting one, resizing it, changing it
between bounded and circular, moving it to another virtual channel,
and reporting the resulting configuration.

The single idea underneath all of it is quiescence. A store is
reshapeable only while nothing is using it -- storage function off and
no retrieval engaged -- because every one of these operations changes
what the store means to a packet that is already inside it or to a
cursor that is already walking it. A resize while storage is on loses
whichever packets arrive during the change, and a type change while a
retrieval is open changes the overwrite rule underneath the cursor.

The clause's normative items reduce to nine implementable rules:

    1  a store is created with an identity that is not already in use,
       a positive capacity, a known type and a valid virtual channel
    2  the capacities of all stores together must fit the mass memory
       budget; a create or a resize that would exceed it is refused
    3  a store is deleted, resized, retyped or moved only while it is
       quiescent: storage function off and no retrieval engaged
    4  a resize below the store's current occupancy is refused, since
       accepting it would silently throw away the overflow
    5  a type change is refused on a store that still holds packets,
       because the overwrite rule those packets were stored under is
       not the rule they would then live by
    6  a virtual channel change takes a channel the spacecraft
       actually has
    7  deleting a store that still holds packets is permitted while
       quiescent and reported, because the content goes with it
    8  an operation naming a store the application does not hold fails
       for that store alone, and the failure is notified
    9  the configuration report carries one entry per store and the
       memory budget figures a receiver can check the set against

Stdlib only, offline, deterministic.
"""

STORE_TYPE_BOUNDED = "bounded"
STORE_TYPE_CIRCULAR = "circular"
VALID_STORE_TYPES = (STORE_TYPE_BOUNDED, STORE_TYPE_CIRCULAR)

STORAGE_ON = "on"
STORAGE_OFF = "off"
VALID_STORAGE_STATES = (STORAGE_ON, STORAGE_OFF)

COMMAND_CREATE = "create-packet-store"
COMMAND_DELETE = "delete-packet-store"
COMMAND_RESIZE = "resize-packet-store"
COMMAND_CHANGE_TYPE = "change-packet-store-type"
COMMAND_CHANGE_CHANNEL = "change-packet-store-virtual-channel"
VALID_COMMANDS = (
    COMMAND_CREATE,
    COMMAND_DELETE,
    COMMAND_RESIZE,
    COMMAND_CHANGE_TYPE,
    COMMAND_CHANGE_CHANNEL,
)

OUTCOME_APPLIED = "applied"
OUTCOME_NO_CHANGE = "accepted-no-change"
OUTCOME_REJECTED_UNKNOWN_STORE = "rejected-unknown-packet-store"
OUTCOME_REJECTED_DUPLICATE_STORE = "rejected-packet-store-already-exists"
OUTCOME_REJECTED_NOT_QUIESCENT = "rejected-packet-store-in-use"
OUTCOME_REJECTED_BUDGET = "rejected-mass-memory-budget-exceeded"
OUTCOME_REJECTED_BELOW_OCCUPANCY = "rejected-capacity-below-current-occupancy"
OUTCOME_REJECTED_NOT_EMPTY = "rejected-packet-store-not-empty"
OUTCOME_REJECTED_UNKNOWN_CHANNEL = "rejected-virtual-channel-not-available"

VERDICT_ACCEPTED = "packet-store-management-accepted"
VERDICT_PARTIAL = "packet-store-management-partially-rejected"

DEFAULT_VIRTUAL_CHANNELS = (0, 1, 2, 3, 4, 5, 6, 7)


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


def _integer(label, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def validate_store_definition(record):
    """Normalize one packet store definition and its current use."""
    if not isinstance(record, dict):
        raise ValueError("packet store must be a mapping, got %r" % (record,))
    store_id = _text("packet store id", record.get("id"))
    capacity = _integer(
        "packet store %s capacity_octets" % store_id,
        record.get("capacity_octets"),
        minimum=1,
    )
    occupied = _integer(
        "packet store %s occupied_octets" % store_id,
        record.get("occupied_octets", 0),
        minimum=0,
    )
    if occupied > capacity:
        raise ValueError(
            "packet store %s holds %d octets in a %d octet store"
            % (store_id, occupied, capacity)
        )
    retrieval = record.get("retrieval_engaged", False)
    if not isinstance(retrieval, bool):
        raise ValueError(
            "packet store %s retrieval_engaged must be a boolean" % store_id
        )
    return {
        "id": store_id,
        "store_type": _choice(
            "packet store %s store_type" % store_id,
            record.get("store_type"),
            VALID_STORE_TYPES,
        ),
        "capacity_octets": capacity,
        "occupied_octets": occupied,
        "virtual_channel": _integer(
            "packet store %s virtual_channel" % store_id,
            record.get("virtual_channel"),
            minimum=0,
        ),
        "storage_status": _choice(
            "packet store %s storage_status" % store_id,
            record.get("storage_status", STORAGE_OFF),
            VALID_STORAGE_STATES,
        ),
        "retrieval_engaged": retrieval,
    }


def validate_configuration(record):
    """Normalize the held stores, the memory budget and the channels."""
    if not isinstance(record, dict):
        raise ValueError("configuration must be a mapping, got %r" % (record,))
    raw = record.get("stores", [])
    if not isinstance(raw, (list, tuple)):
        raise ValueError("configuration stores must be a list, got %r" % (raw,))
    stores = {}
    order = []
    for item in raw:
        store = validate_store_definition(item)
        if store["id"] in stores:
            raise ValueError("duplicate packet store id %r" % store["id"])
        stores[store["id"]] = store
        order.append(store["id"])
    budget = _integer(
        "configuration memory_budget_octets",
        record.get("memory_budget_octets"),
        minimum=1,
    )
    channels_raw = record.get("virtual_channels", DEFAULT_VIRTUAL_CHANNELS)
    if not isinstance(channels_raw, (list, tuple)) or not channels_raw:
        raise ValueError("configuration virtual_channels must be a non-empty list")
    channels = []
    for item in channels_raw:
        channel = _integer("virtual channel", item, minimum=0)
        if channel in channels:
            raise ValueError("configuration repeats virtual channel %d" % channel)
        channels.append(channel)
    allocated = sum(stores[key]["capacity_octets"] for key in order)
    if allocated > budget:
        raise ValueError(
            "the packet stores allocate %d octets against a %d octet budget"
            % (allocated, budget)
        )
    for key in order:
        if stores[key]["virtual_channel"] not in channels:
            raise ValueError(
                "packet store %s uses virtual channel %d, which the spacecraft "
                "does not have" % (key, stores[key]["virtual_channel"])
            )
    return {
        "stores": stores,
        "order": order,
        "memory_budget_octets": budget,
        "virtual_channels": channels,
    }


def validate_command(record):
    """Normalize one management command against its action's arguments."""
    if not isinstance(record, dict):
        raise ValueError("command must be a mapping, got %r" % (record,))
    action = _choice("command action", record.get("action"), VALID_COMMANDS)
    command = {"action": action, "store_id": _text("command store_id",
                                                   record.get("store_id"))}
    if action == COMMAND_CREATE:
        command["store_type"] = _choice(
            "command store_type", record.get("store_type"), VALID_STORE_TYPES
        )
        command["capacity_octets"] = _integer(
            "command capacity_octets", record.get("capacity_octets"), minimum=1
        )
        command["virtual_channel"] = _integer(
            "command virtual_channel", record.get("virtual_channel"), minimum=0
        )
    elif action == COMMAND_RESIZE:
        command["capacity_octets"] = _integer(
            "command capacity_octets", record.get("capacity_octets"), minimum=1
        )
    elif action == COMMAND_CHANGE_TYPE:
        command["store_type"] = _choice(
            "command store_type", record.get("store_type"), VALID_STORE_TYPES
        )
    elif action == COMMAND_CHANGE_CHANNEL:
        command["virtual_channel"] = _integer(
            "command virtual_channel", record.get("virtual_channel"), minimum=0
        )
    return command


def is_quiescent(store):
    """True when nothing is writing to the store and nothing reading it."""
    record = validate_store_definition(store)
    return (
        record["storage_status"] == STORAGE_OFF
        and not record["retrieval_engaged"]
    )


def allocated_octets(state):
    """The capacity the current set of stores claims from mass memory."""
    return sum(
        state["stores"][store_id]["capacity_octets"] for store_id in state["order"]
    )


def budget_headroom(state, excluding=None, adding=0):
    """Budget left over once a named store is set aside and a size added."""
    allocated = allocated_octets(state)
    if excluding is not None and excluding in state["stores"]:
        allocated -= state["stores"][excluding]["capacity_octets"]
    return state["memory_budget_octets"] - allocated - adding


def _rejection(store_id, outcome):
    return {"store_id": store_id, "outcome": outcome, "changed": False}


def create_store(state, command):
    """Create a store, if its identity is free and the budget allows it."""
    store_id = command["store_id"]
    if store_id in state["stores"]:
        return _rejection(store_id, OUTCOME_REJECTED_DUPLICATE_STORE)
    if command["virtual_channel"] not in state["virtual_channels"]:
        return _rejection(store_id, OUTCOME_REJECTED_UNKNOWN_CHANNEL)
    if budget_headroom(state, adding=command["capacity_octets"]) < 0:
        return _rejection(store_id, OUTCOME_REJECTED_BUDGET)
    state["stores"][store_id] = {
        "id": store_id,
        "store_type": command["store_type"],
        "capacity_octets": command["capacity_octets"],
        "occupied_octets": 0,
        "virtual_channel": command["virtual_channel"],
        "storage_status": STORAGE_OFF,
        "retrieval_engaged": False,
    }
    state["order"].append(store_id)
    return {"store_id": store_id, "outcome": OUTCOME_APPLIED, "changed": True}


def delete_store(state, command):
    """Delete a quiescent store; its remaining content goes with it."""
    store_id = command["store_id"]
    store = state["stores"][store_id]
    if not is_quiescent(store):
        return _rejection(store_id, OUTCOME_REJECTED_NOT_QUIESCENT)
    lost = store["occupied_octets"]
    del state["stores"][store_id]
    state["order"].remove(store_id)
    return {
        "store_id": store_id,
        "outcome": OUTCOME_APPLIED,
        "changed": True,
        "lost_octets": lost,
    }


def resize_store(state, command):
    """Resize a quiescent store within its occupancy and the budget."""
    store_id = command["store_id"]
    store = state["stores"][store_id]
    wanted = command["capacity_octets"]
    if not is_quiescent(store):
        return _rejection(store_id, OUTCOME_REJECTED_NOT_QUIESCENT)
    if wanted < store["occupied_octets"]:
        return _rejection(store_id, OUTCOME_REJECTED_BELOW_OCCUPANCY)
    if budget_headroom(state, excluding=store_id, adding=wanted) < 0:
        return _rejection(store_id, OUTCOME_REJECTED_BUDGET)
    if wanted == store["capacity_octets"]:
        return {
            "store_id": store_id,
            "outcome": OUTCOME_NO_CHANGE,
            "changed": False,
        }
    store["capacity_octets"] = wanted
    return {"store_id": store_id, "outcome": OUTCOME_APPLIED, "changed": True}


def change_store_type(state, command):
    """Retype a quiescent, empty store between bounded and circular."""
    store_id = command["store_id"]
    store = state["stores"][store_id]
    if not is_quiescent(store):
        return _rejection(store_id, OUTCOME_REJECTED_NOT_QUIESCENT)
    if store["occupied_octets"] > 0:
        return _rejection(store_id, OUTCOME_REJECTED_NOT_EMPTY)
    if store["store_type"] == command["store_type"]:
        return {
            "store_id": store_id,
            "outcome": OUTCOME_NO_CHANGE,
            "changed": False,
        }
    store["store_type"] = command["store_type"]
    return {"store_id": store_id, "outcome": OUTCOME_APPLIED, "changed": True}


def change_virtual_channel(state, command):
    """Move a quiescent store to another virtual channel the craft has."""
    store_id = command["store_id"]
    store = state["stores"][store_id]
    wanted = command["virtual_channel"]
    if not is_quiescent(store):
        return _rejection(store_id, OUTCOME_REJECTED_NOT_QUIESCENT)
    if wanted not in state["virtual_channels"]:
        return _rejection(store_id, OUTCOME_REJECTED_UNKNOWN_CHANNEL)
    if store["virtual_channel"] == wanted:
        return {
            "store_id": store_id,
            "outcome": OUTCOME_NO_CHANGE,
            "changed": False,
        }
    store["virtual_channel"] = wanted
    return {"store_id": store_id, "outcome": OUTCOME_APPLIED, "changed": True}


def apply_command(state, command):
    """Apply one management command to the store it names."""
    request = validate_command(command)
    store_id = request["store_id"]
    findings = []
    if request["action"] == COMMAND_CREATE:
        result = create_store(state, request)
        if result["outcome"] == OUTCOME_REJECTED_DUPLICATE_STORE:
            findings.append(
                "packet store %s already exists; the create was refused rather "
                "than replacing a store that may hold data" % store_id
            )
    elif store_id not in state["stores"]:
        result = _rejection(store_id, OUTCOME_REJECTED_UNKNOWN_STORE)
        findings.append(
            "command %s names packet store %r, which the application does not "
            "hold; the command failed for that store only"
            % (request["action"], store_id)
        )
    elif request["action"] == COMMAND_DELETE:
        result = delete_store(state, request)
        if result.get("lost_octets"):
            findings.append(
                "packet store %s was deleted holding %d octets; that content is "
                "gone with the store" % (store_id, result["lost_octets"])
            )
    elif request["action"] == COMMAND_RESIZE:
        result = resize_store(state, request)
    elif request["action"] == COMMAND_CHANGE_TYPE:
        result = change_store_type(state, request)
    else:
        result = change_virtual_channel(state, request)
    if result["outcome"] == OUTCOME_REJECTED_NOT_QUIESCENT:
        findings.append(
            "packet store %s is storing or being read out; %s needs the store "
            "quiescent" % (store_id, request["action"])
        )
    elif result["outcome"] == OUTCOME_REJECTED_BELOW_OCCUPANCY:
        findings.append(
            "packet store %s holds more than the requested capacity; the resize "
            "was refused rather than discarding the overflow" % store_id
        )
    elif result["outcome"] == OUTCOME_REJECTED_NOT_EMPTY:
        findings.append(
            "packet store %s still holds packets; a type change would put them "
            "under an overwrite rule they were not stored under" % store_id
        )
    elif result["outcome"] == OUTCOME_REJECTED_BUDGET:
        findings.append(
            "packet store %s cannot take that capacity; the stores together "
            "would exceed the mass memory budget" % store_id
        )
    elif result["outcome"] == OUTCOME_REJECTED_UNKNOWN_CHANNEL:
        findings.append(
            "packet store %s was pointed at a virtual channel the spacecraft "
            "does not have" % store_id
        )
    result["action"] = request["action"]
    return {"action": request["action"], "result": result, "findings": findings}


def apply_commands(configuration, commands):
    """Run a management sequence against the held configuration, in order."""
    state = validate_configuration(configuration)
    if not isinstance(commands, (list, tuple)):
        raise ValueError("commands must be a list, got %r" % (commands,))
    steps = [apply_command(state, command) for command in commands]
    return {"state": state, "steps": steps}


def configuration_report(state):
    """One entry per store, plus the mass memory figures for the set."""
    entries = []
    for store_id in state["order"]:
        store = state["stores"][store_id]
        entries.append(
            {
                "id": store_id,
                "store_type": store["store_type"],
                "capacity_octets": store["capacity_octets"],
                "occupied_octets": store["occupied_octets"],
                "virtual_channel": store["virtual_channel"],
                "storage_status": store["storage_status"],
                "quiescent": is_quiescent(store),
            }
        )
    allocated = allocated_octets(state)
    budget = state["memory_budget_octets"]
    return {
        "entries": entries,
        "store_count": len(entries),
        "allocated_octets": allocated,
        "memory_budget_octets": budget,
        "free_octets": budget - allocated,
        "budget_utilisation": allocated / budget,
    }


def assess_packet_store_management(configuration, commands):
    """Full clause 6.15.3.8 handling: apply, report, and name the refusals."""
    run = apply_commands(configuration, commands)
    findings = []
    rejected = []
    for step in run["steps"]:
        findings.extend(step["findings"])
        if step["result"]["outcome"].startswith("rejected"):
            rejected.append((step["action"], step["result"]["store_id"]))
    report = configuration_report(run["state"])
    accepted = not rejected
    return {
        "report": report,
        "steps": run["steps"],
        "rejected": rejected,
        "rejected_count": len(rejected),
        "accepted": accepted,
        "verdict": VERDICT_ACCEPTED if accepted else VERDICT_PARTIAL,
        "findings": findings,
    }
