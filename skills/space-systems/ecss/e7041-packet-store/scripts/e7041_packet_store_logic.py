"""On-board packet store of the storage and retrieval service.

Anchor: ECSS-E-ST-70-41C clause 6.15.3.1 (paraphrased into an
implementable procedure; no standard text is reproduced).

What a packet store is. A packet store is a bounded region of on-board
mass memory that accepts telemetry packets and holds them in the order
they arrived, so the ground can retrieve them later over a link that
was not available when they were produced. Each store has an identity,
a capacity, a storage state that can be turned on and off independently
of everything else, and a type that decides what happens when it fills.

The two types differ only at the moment the store is full, and that is
the decision this module exists to make.

  bounded  -- the store stops accepting. The oldest packets are kept
              and the newest are lost. Chosen when the earliest part of
              a record is the part that matters: the run-up to an
              anomaly, the first seconds of a separation sequence.
  circular -- the store keeps accepting and overwrites its oldest
              packets to make room. The newest packets are kept and the
              oldest are lost. Chosen when the current picture matters
              more than the history.

Neither type is the safe default. Both lose data when the store fills
and the ground has not emptied it; they differ in which end of the
record they lose.

Open retrieval. While a retrieval is walking a circular store, the
packets it has not yet read cannot be overwritten -- doing so would
hand the ground a record with a hole in the middle that nothing in the
downlink marks. A circular store therefore behaves like a bounded one
against the part of its content an open retrieval still needs.

Stdlib only, offline, deterministic.
"""

STORE_TYPE_BOUNDED = "bounded"
STORE_TYPE_CIRCULAR = "circular"
VALID_STORE_TYPES = (STORE_TYPE_BOUNDED, STORE_TYPE_CIRCULAR)

STORAGE_ENABLED = "enabled"
STORAGE_DISABLED = "disabled"
VALID_STORAGE_STATES = (STORAGE_ENABLED, STORAGE_DISABLED)

OUTCOME_STORED = "stored"
OUTCOME_STORED_AFTER_OVERWRITE = "stored-after-overwriting-oldest"
OUTCOME_DISCARDED_STORAGE_DISABLED = "discarded-storage-disabled"
OUTCOME_DISCARDED_STORE_FULL = "discarded-bounded-store-full"
OUTCOME_DISCARDED_OPEN_RETRIEVAL = "discarded-overwrite-blocked-by-open-retrieval"

# A fill fraction is a quotient of two byte counts, so a store filled to
# exactly its capacity can land a few units in the last place either
# side of one. This tolerance absorbs that; the capacity itself is
# never widened, because the admission test works on integer bytes.
FILL_TOLERANCE = 1.0e-12


def _integer(label, value, minimum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def validate_store_definition(definition):
    """Validate one packet store definition and return a normalized copy."""
    if not isinstance(definition, dict):
        raise ValueError("store definition must be a mapping")
    store_id = definition.get("id")
    if not isinstance(store_id, str) or not store_id.strip():
        raise ValueError("packet store needs a non-empty string id")
    store_type = definition.get("type")
    if store_type not in VALID_STORE_TYPES:
        raise ValueError(
            "packet store %s has unknown type %r (expected one of %s)"
            % (store_id, store_type, ", ".join(VALID_STORE_TYPES))
        )
    capacity = _integer("packet store %s capacity_octets" % store_id,
                        definition.get("capacity_octets"), 1)
    state = definition.get("storage_state", STORAGE_ENABLED)
    if state not in VALID_STORAGE_STATES:
        raise ValueError(
            "packet store %s has unknown storage state %r" % (store_id, state)
        )
    return {
        "id": store_id,
        "type": store_type,
        "capacity_octets": capacity,
        "storage_state": state,
    }


def create_store(definition):
    """Create an empty packet store from a validated definition."""
    normalized = validate_store_definition(definition)
    normalized["packets"] = []
    normalized["open_retrieval_index"] = None
    normalized["discarded_count"] = 0
    normalized["overwritten_count"] = 0
    return normalized


def validate_store(store):
    """Validate a live packet store and return an independent copy."""
    if not isinstance(store, dict):
        raise ValueError("packet store must be a mapping")
    normalized = validate_store_definition(store)
    packets = store.get("packets", [])
    if not isinstance(packets, list):
        raise ValueError("packet store %s packets must be a list" % normalized["id"])
    normalized["packets"] = [validate_packet(p) for p in packets]
    used = sum(p["size_octets"] for p in normalized["packets"])
    if used > normalized["capacity_octets"]:
        raise ValueError(
            "packet store %s holds %d octets over its %d octet capacity"
            % (normalized["id"], used, normalized["capacity_octets"])
        )
    index = store.get("open_retrieval_index")
    if index is not None:
        _integer("packet store %s open_retrieval_index" % normalized["id"], index, 0)
        if index > len(normalized["packets"]):
            raise ValueError(
                "packet store %s open retrieval index %d is past its content"
                % (normalized["id"], index)
            )
    normalized["open_retrieval_index"] = index
    normalized["discarded_count"] = _integer(
        "packet store %s discarded_count" % normalized["id"],
        store.get("discarded_count", 0), 0,
    )
    normalized["overwritten_count"] = _integer(
        "packet store %s overwritten_count" % normalized["id"],
        store.get("overwritten_count", 0), 0,
    )
    return normalized


def validate_packet(packet):
    """Validate one telemetry packet offered to a store."""
    if not isinstance(packet, dict):
        raise ValueError("packet must be a mapping")
    packet_id = packet.get("id")
    if not isinstance(packet_id, str) or not packet_id.strip():
        raise ValueError("packet needs a non-empty string id")
    size = _integer("packet %s size_octets" % packet_id, packet.get("size_octets"), 1)
    return {"id": packet_id, "size_octets": size}


def used_octets(store):
    """Octets a packet store currently holds."""
    working = validate_store(store)
    return sum(p["size_octets"] for p in working["packets"])


def free_octets(store):
    """Octets a packet store can still take without losing anything."""
    working = validate_store(store)
    return working["capacity_octets"] - used_octets(working)


def fill_fraction(store):
    """Fraction of a packet store's capacity currently occupied."""
    working = validate_store(store)
    return used_octets(working) / float(working["capacity_octets"])


def is_full(store):
    """Is the store holding its full capacity?"""
    return free_octets(store) == 0


def packet_fits_in_capacity(store, packet):
    """Could this packet ever be held by this store, even when empty?"""
    working = validate_store(store)
    candidate = validate_packet(packet)
    return candidate["size_octets"] <= working["capacity_octets"]


def store_packet(store, packet):
    """Offer one packet to a store; return the new store and the outcome."""
    working = validate_store(store)
    candidate = validate_packet(packet)
    if not packet_fits_in_capacity(working, candidate):
        raise ValueError(
            "packet %s of %d octets can never fit packet store %s of %d octets"
            % (
                candidate["id"], candidate["size_octets"],
                working["id"], working["capacity_octets"],
            )
        )
    if working["storage_state"] == STORAGE_DISABLED:
        working["discarded_count"] += 1
        return working, OUTCOME_DISCARDED_STORAGE_DISABLED
    if candidate["size_octets"] <= free_octets(working):
        working["packets"].append(candidate)
        return working, OUTCOME_STORED
    if working["type"] == STORE_TYPE_BOUNDED:
        working["discarded_count"] += 1
        return working, OUTCOME_DISCARDED_STORE_FULL
    protected = working["open_retrieval_index"]
    removed = []
    while candidate["size_octets"] > free_octets(working):
        if protected is not None and len(removed) >= protected:
            # The next packet to overwrite is one the open retrieval has
            # not handed to the ground yet. Put back everything taken so
            # far and discard the new packet instead of tearing a hole
            # in the middle of a record already being read out.
            working["packets"] = removed + working["packets"]
            working["discarded_count"] += 1
            return working, OUTCOME_DISCARDED_OPEN_RETRIEVAL
        removed.append(working["packets"].pop(0))
    working["overwritten_count"] += len(removed)
    if protected is not None:
        working["open_retrieval_index"] = protected - len(removed)
    working["packets"].append(candidate)
    return working, OUTCOME_STORED_AFTER_OVERWRITE


def store_packets(store, packets):
    """Offer a sequence of packets to a store; return the store and outcomes."""
    if not isinstance(packets, (list, tuple)):
        raise ValueError("packets must be a list")
    working = validate_store(store)
    outcomes = []
    for packet in packets:
        working, outcome = store_packet(working, packet)
        outcomes.append({"packet_id": validate_packet(packet)["id"], "outcome": outcome})
    return working, outcomes


def set_storage_state(store, state):
    """Turn storage of this packet store on or off; content is untouched."""
    working = validate_store(store)
    if state not in VALID_STORAGE_STATES:
        raise ValueError("unknown storage state %r" % (state,))
    working["storage_state"] = state
    return working


def open_retrieval(store):
    """Open a retrieval at the oldest packet the store holds."""
    working = validate_store(store)
    if working["open_retrieval_index"] is not None:
        raise ValueError(
            "packet store %s already has an open retrieval" % working["id"]
        )
    working["open_retrieval_index"] = 0
    return working


def close_retrieval(store):
    """Close the open retrieval, freeing its content for overwrite."""
    working = validate_store(store)
    if working["open_retrieval_index"] is None:
        raise ValueError("packet store %s has no open retrieval" % working["id"])
    working["open_retrieval_index"] = None
    return working


def advance_retrieval(store, count):
    """Advance the open retrieval past packets the ground has received."""
    working = validate_store(store)
    _integer("retrieval advance count", count, 0)
    if working["open_retrieval_index"] is None:
        raise ValueError("packet store %s has no open retrieval" % working["id"])
    index = working["open_retrieval_index"] + count
    if index > len(working["packets"]):
        raise ValueError(
            "advancing the retrieval of packet store %s past its content"
            % working["id"]
        )
    working["open_retrieval_index"] = index
    return working


def report_store_status(store):
    """Deterministic status report for one packet store."""
    working = validate_store(store)
    used = used_octets(working)
    return {
        "id": working["id"],
        "type": working["type"],
        "storage_state": working["storage_state"],
        "capacity_octets": working["capacity_octets"],
        "used_octets": used,
        "free_octets": working["capacity_octets"] - used,
        "fill_fraction": fill_fraction(working),
        "packet_count": len(working["packets"]),
        "oldest_packet_id": working["packets"][0]["id"] if working["packets"] else None,
        "newest_packet_id": working["packets"][-1]["id"] if working["packets"] else None,
        "open_retrieval": working["open_retrieval_index"] is not None,
        "discarded_count": working["discarded_count"],
        "overwritten_count": working["overwritten_count"],
        "full": used == working["capacity_octets"],
    }


def assess_packet_store_set(definitions, traffic):
    """Route a packet stream into a set of stores and report each store."""
    if not isinstance(definitions, list) or not definitions:
        raise ValueError("definitions must be a non-empty list")
    stores = {}
    order = []
    for definition in definitions:
        created = create_store(definition)
        if created["id"] in stores:
            raise ValueError("duplicate packet store id %r" % (created["id"],))
        stores[created["id"]] = created
        order.append(created["id"])
    if not isinstance(traffic, list):
        raise ValueError("traffic must be a list")
    outcomes = []
    for item in traffic:
        if not isinstance(item, dict):
            raise ValueError("traffic item must be a mapping")
        store_id = item.get("store_id")
        if store_id not in stores:
            raise ValueError("traffic names unknown packet store %r" % (store_id,))
        stores[store_id], outcome = store_packet(stores[store_id], item.get("packet"))
        outcomes.append({"store_id": store_id, "outcome": outcome})
    reports = [report_store_status(stores[sid]) for sid in order]
    return {
        "stores": reports,
        "outcomes": outcomes,
        "lost_packet_count": sum(r["discarded_count"] for r in reports)
        + sum(r["overwritten_count"] for r in reports),
        "lossless": all(
            r["discarded_count"] == 0 and r["overwritten_count"] == 0 for r in reports
        ),
    }
