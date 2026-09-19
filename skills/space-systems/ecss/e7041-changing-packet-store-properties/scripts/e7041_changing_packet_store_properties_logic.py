"""Changing the properties of an on-board packet store.

Anchor: ECSS-E-ST-70-41C clause 6.15.3.9 (paraphrased into an
implementable procedure; no standard text is reproduced).

What the job is. The on-board storage and retrieval service holds a
table of packet stores. Each one carries an identifier, a capacity in
octets, a type that decides what happens when it fills, a virtual
channel it is read out on, a storage state and the octets it currently
holds. Clause 6.15.3.9 is the request that changes those properties on
a store that already exists and may already hold telemetry.

Why it is not a simple assignment. Every property change can destroy
content or corrupt a read-out in progress. Shrinking a store below the
octets it holds silently drops the difference. Changing the type while
content is held changes the meaning of the record already captured --
the operator asked for the oldest packets to be kept and would now get
them overwritten, or the reverse. Changing anything while storage is
enabled races the packet that is arriving, and changing anything while
a retrieval is open tears the record the ground is reading out.

So the service refuses the change instead of performing it, and says
which precondition failed. A request carries many changes and executes
per change, returning a disposition list rather than one verdict.

Stdlib only, offline, deterministic.
"""

PACKET_STORE_ID_MAX_LENGTH = 32
CAPACITY_MIN_OCTETS = 1024
CAPACITY_MAX_OCTETS = 268435456
ALLOCATION_BLOCK_OCTETS = 512
VIRTUAL_CHANNEL_MIN = 0
VIRTUAL_CHANNEL_MAX = 63

STORE_TYPE_BOUNDED = "bounded"
STORE_TYPE_CIRCULAR = "circular"
STORE_TYPES = (STORE_TYPE_BOUNDED, STORE_TYPE_CIRCULAR)

CHANGEABLE_PROPERTIES = ("capacity_octets", "store_type", "virtual_channel")

ACCEPTED = "accepted"
REJECTED = "rejected"

REASON_UNKNOWN_PACKET_STORE = "packet-store-not-defined"
REASON_STORAGE_ENABLED = "storage-still-enabled-on-the-store"
REASON_RETRIEVAL_OPEN = "retrieval-still-open-on-the-store"
REASON_CAPACITY_BELOW_OCCUPANCY = "capacity-below-the-octets-already-held"
REASON_CAPACITY_OUT_OF_RANGE = "capacity-outside-the-configured-range"
REASON_CAPACITY_NOT_BLOCK_ALIGNED = "capacity-not-a-whole-number-of-blocks"
REASON_TYPE_CHANGE_NEEDS_EMPTY_STORE = "type-change-needs-an-empty-store"
REASON_MEMORY_POOL_EXHAUSTED = "memory-pool-exhausted"
REASON_NOTHING_WOULD_CHANGE = "every-named-property-already-holds-that-value"

REASON_APPLIED = "properties-changed"


def _text(label, value, max_length):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    stripped = value.strip()
    if not stripped:
        raise ValueError("%s must not be empty" % label)
    if len(stripped) > max_length:
        raise ValueError(
            "%s must be at most %d characters, got %d"
            % (label, max_length, len(stripped))
        )
    return stripped


def _integer(label, value, low, high):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < low or value > high:
        raise ValueError("%s must be in [%d, %d], got %d" % (label, low, high, value))
    return value


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_store_type(store_type):
    """Validate a packet store type against the two the service supports."""
    if not isinstance(store_type, str):
        raise ValueError("packet store type must be a string, got %r" % (store_type,))
    normalized = store_type.strip().lower()
    if normalized not in STORE_TYPES:
        raise ValueError(
            "packet store type must be one of %s, got %r"
            % (", ".join(STORE_TYPES), store_type)
        )
    return normalized


def validate_packet_store(store):
    """Validate one packet store entry and return it in normalized form."""
    if not isinstance(store, dict):
        raise ValueError("packet store must be a mapping")
    store_id = _text(
        "packet store identifier", store.get("store_id"), PACKET_STORE_ID_MAX_LENGTH
    )
    capacity = _integer(
        "packet store capacity", store.get("capacity_octets"),
        CAPACITY_MIN_OCTETS, CAPACITY_MAX_OCTETS,
    )
    if capacity % ALLOCATION_BLOCK_OCTETS:
        raise ValueError(
            "packet store %s capacity %d is not a whole number of %d-octet blocks"
            % (store_id, capacity, ALLOCATION_BLOCK_OCTETS)
        )
    occupancy = _integer(
        "packet store occupancy", store.get("occupancy_octets", 0), 0, capacity
    )
    return {
        "store_id": store_id,
        "capacity_octets": capacity,
        "occupancy_octets": occupancy,
        "store_type": validate_store_type(store.get("store_type", STORE_TYPE_BOUNDED)),
        "virtual_channel": _integer(
            "packet store virtual channel", store.get("virtual_channel", 0),
            VIRTUAL_CHANNEL_MIN, VIRTUAL_CHANNEL_MAX,
        ),
        "storage_enabled": _boolean(
            "packet store storage state", store.get("storage_enabled", False)
        ),
        "retrieval_open": _boolean(
            "packet store retrieval state", store.get("retrieval_open", False)
        ),
    }


def normalize_store_table(stores):
    """Validate a packet store table and return an independent normalized copy."""
    if not isinstance(stores, (list, tuple)):
        raise ValueError("packet store table must be a list")
    table = {}
    for store in stores:
        normalized = validate_packet_store(store)
        if normalized["store_id"] in table:
            raise ValueError(
                "packet store identifier %s appears twice in the table"
                % normalized["store_id"]
            )
        table[normalized["store_id"]] = normalized
    return table


def validate_change_item(item):
    """Validate one property-change item and return it in normalized form."""
    if not isinstance(item, dict):
        raise ValueError("property change item must be a mapping")
    change = {
        "store_id": _text(
            "change packet store identifier", item.get("store_id"),
            PACKET_STORE_ID_MAX_LENGTH,
        )
    }
    named = 0
    if item.get("capacity_octets") is not None:
        change["capacity_octets"] = _integer(
            "requested capacity", item.get("capacity_octets"), 1, CAPACITY_MAX_OCTETS
        )
        named += 1
    if item.get("store_type") is not None:
        change["store_type"] = validate_store_type(item.get("store_type"))
        named += 1
    if item.get("virtual_channel") is not None:
        change["virtual_channel"] = _integer(
            "requested virtual channel", item.get("virtual_channel"),
            VIRTUAL_CHANNEL_MIN, VIRTUAL_CHANNEL_MAX,
        )
        named += 1
    if not named:
        raise ValueError(
            "property change for packet store %s names no property to change"
            % change["store_id"]
        )
    return change


def pool_committed_octets(table):
    """Total capacity the packet store table commits from the memory pool."""
    return sum(store["capacity_octets"] for store in table.values())


def assess_property_change(store, change, pool_octets, committed_elsewhere):
    """Decide one property change against its preconditions; no side effects."""
    if store["storage_enabled"]:
        return REJECTED, REASON_STORAGE_ENABLED
    if store["retrieval_open"]:
        return REJECTED, REASON_RETRIEVAL_OPEN
    if "capacity_octets" in change:
        capacity = change["capacity_octets"]
        if capacity < CAPACITY_MIN_OCTETS or capacity > CAPACITY_MAX_OCTETS:
            return REJECTED, REASON_CAPACITY_OUT_OF_RANGE
        if capacity % ALLOCATION_BLOCK_OCTETS:
            return REJECTED, REASON_CAPACITY_NOT_BLOCK_ALIGNED
        if capacity < store["occupancy_octets"]:
            return REJECTED, REASON_CAPACITY_BELOW_OCCUPANCY
        if committed_elsewhere + capacity > pool_octets:
            return REJECTED, REASON_MEMORY_POOL_EXHAUSTED
    if "store_type" in change:
        if change["store_type"] != store["store_type"] and store["occupancy_octets"]:
            return REJECTED, REASON_TYPE_CHANGE_NEEDS_EMPTY_STORE
    if all(
        store[name] == change[name] for name in CHANGEABLE_PROPERTIES if name in change
    ):
        return REJECTED, REASON_NOTHING_WOULD_CHANGE
    return ACCEPTED, REASON_APPLIED


def apply_property_changes(stores, items, pool_octets):
    """Apply a change request; return the new table and the per-item outcome."""
    table = normalize_store_table(stores)
    _integer("memory pool", pool_octets, CAPACITY_MIN_OCTETS, CAPACITY_MAX_OCTETS * 64)
    committed = pool_committed_octets(table)
    if committed > pool_octets:
        raise ValueError(
            "packet store table commits %d octets from a %d octet memory pool"
            % (committed, pool_octets)
        )
    if not isinstance(items, (list, tuple)):
        raise ValueError("property change items must be a list")
    dispositions = []
    for index, raw in enumerate(items):
        change = validate_change_item(raw)
        store = table.get(change["store_id"])
        if store is None:
            status, reason = REJECTED, REASON_UNKNOWN_PACKET_STORE
            changed = []
        else:
            elsewhere = pool_committed_octets(table) - store["capacity_octets"]
            status, reason = assess_property_change(
                store, change, pool_octets, elsewhere
            )
            changed = []
            if status == ACCEPTED:
                for name in CHANGEABLE_PROPERTIES:
                    if name in change and change[name] != store[name]:
                        store[name] = change[name]
                        changed.append(name)
        dispositions.append(
            {
                "index": index,
                "store_id": change["store_id"],
                "status": status,
                "reason": reason,
                "properties_changed": changed,
            }
        )
    return table, dispositions


def report_store_table(table, pool_octets):
    """Deterministic report of the packet store table and its pool usage."""
    if not isinstance(table, dict):
        raise ValueError("packet store table report needs a normalized table")
    _integer("memory pool", pool_octets, CAPACITY_MIN_OCTETS, CAPACITY_MAX_OCTETS * 64)
    entries = []
    for store_id in sorted(table):
        store = table[store_id]
        entries.append(
            {
                "store_id": store_id,
                "capacity_octets": store["capacity_octets"],
                "occupancy_octets": store["occupancy_octets"],
                "store_type": store["store_type"],
                "virtual_channel": store["virtual_channel"],
                "fill_fraction": (
                    store["occupancy_octets"] / float(store["capacity_octets"])
                ),
                "changeable_now": not (
                    store["storage_enabled"] or store["retrieval_open"]
                ),
            }
        )
    committed = pool_committed_octets(table)
    return {
        "packet_stores": entries,
        "packet_store_count": len(entries),
        "pool_octets": pool_octets,
        "pool_committed_octets": committed,
        "pool_free_octets": pool_octets - committed,
    }
