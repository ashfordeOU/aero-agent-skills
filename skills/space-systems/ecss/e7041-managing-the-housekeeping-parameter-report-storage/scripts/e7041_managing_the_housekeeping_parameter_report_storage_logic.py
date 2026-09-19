"""Housekeeping parameter report storage-control configuration of the
on-board storage and retrieval service.

Anchor: ECSS-E-ST-70-41C clause 6.15.4.5 (paraphrased into an
implementable procedure; no standard text is reproduced).

What the configuration is. Housekeeping telemetry is generated against
report structures that the housekeeping service defines per
application process. This configuration decides, one structure at a
time, which of those reports each packet store writes down. It is
keyed by packet store, then application process, then structure
identifier.

Why the structure identifier is the hard part. It is not a free
number: it only means something inside the application process that
defined it. The same identifier under two processes names two
unrelated reports, and an identifier that process never defined names
nothing at all. So every selection is checked against the housekeeping
definitions of that process before it is accepted.

Definitions move underneath the configuration. A structure deleted
from the housekeeping service leaves behind any selection that named
it -- a selection pointing at a report that can no longer be
generated. That is stale, not invalid: it stores nothing, it is easy
to miss because it looks exactly like a working selection, and it
comes back to life wrongly if the identifier is reused. The
configuration therefore has to be able to name its stale selections
and prune them. An all-structures wildcard cannot go stale, because it
follows the definitions rather than naming one.

Stdlib only, offline, deterministic.
"""

PACKET_STORE_ID_MAX_LENGTH = 32
APID_MIN = 0
APID_MAX = 2047
STRUCTURE_ID_MIN = 1
STRUCTURE_ID_MAX = 255

MAX_STRUCTURES_PER_APPLICATION_PROCESS = 64

ACCEPTED = "accepted"
REJECTED = "rejected"

REASON_UNKNOWN_PACKET_STORE = "packet-store-not-defined"
REASON_NO_HOUSEKEEPING_DEFINITIONS = (
    "application-process-defines-no-housekeeping-structures"
)
REASON_STRUCTURE_NOT_DEFINED = (
    "housekeeping-structure-not-defined-for-that-application-process"
)
REASON_ALREADY_STORED = "structure-already-in-the-storage-control-configuration"
REASON_SUBSUMED_BY_WILDCARD = "structure-subsumed-by-the-all-structures-wildcard"
REASON_NOT_IN_CONFIGURATION = "structure-absent-from-the-storage-control-configuration"
REASON_WILDCARD_NOT_PARTIALLY_DELETABLE = "all-structures-wildcard-not-partially-deletable"
REASON_STRUCTURE_CAPACITY = "housekeeping-structure-capacity-exhausted"

REASON_WILDCARD_SET = "all-structures-wildcard-set"
REASON_STRUCTURE_ADDED = "housekeeping-structure-added"
REASON_STRUCTURE_DELETED = "housekeeping-structure-deleted"
REASON_ENTRY_DELETED = "application-process-entry-deleted"


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


def normalize_defined_structures(defined):
    """Validate the housekeeping structure definitions held per process."""
    if not isinstance(defined, dict):
        raise ValueError("defined housekeeping structures must be a mapping")
    out = {}
    for apid, structure_ids in defined.items():
        clean_apid = _integer(
            "housekeeping application process", apid, APID_MIN, APID_MAX
        )
        if not isinstance(structure_ids, (list, tuple, set, frozenset)):
            raise ValueError(
                "housekeeping structures for application process %d must be a "
                "collection" % clean_apid
            )
        collected = set()
        for structure_id in structure_ids:
            collected.add(
                _integer(
                    "housekeeping structure identifier", structure_id,
                    STRUCTURE_ID_MIN, STRUCTURE_ID_MAX,
                )
            )
        out[clean_apid] = collected
    return out


def validate_structure_selection(item):
    """Validate one add/delete item and return it in normalized form."""
    if not isinstance(item, dict):
        raise ValueError("housekeeping storage selection must be a mapping")
    store_id = _text(
        "selection packet store", item.get("store_id"), PACKET_STORE_ID_MAX_LENGTH
    )
    apid = _integer(
        "selection application process", item.get("apid"), APID_MIN, APID_MAX
    )
    structure_id = item.get("structure_id")
    if structure_id is not None:
        structure_id = _integer(
            "selection housekeeping structure", structure_id,
            STRUCTURE_ID_MIN, STRUCTURE_ID_MAX,
        )
    return {"store_id": store_id, "apid": apid, "structure_id": structure_id}


def empty_configuration():
    """A housekeeping storage-control configuration storing nothing."""
    return {}


def normalize_configuration(config):
    """Validate a configuration and return an independent normalized copy."""
    if not isinstance(config, dict):
        raise ValueError("housekeeping storage configuration must be a mapping")
    out = {}
    for store_id, processes in config.items():
        clean_id = _text(
            "configuration packet store", store_id, PACKET_STORE_ID_MAX_LENGTH
        )
        if not isinstance(processes, dict):
            raise ValueError(
                "configuration for packet store %s must be a mapping" % clean_id
            )
        tree = {}
        for apid, entry in processes.items():
            clean_apid = _integer(
                "configuration application process", apid, APID_MIN, APID_MAX
            )
            if not isinstance(entry, dict):
                raise ValueError(
                    "entry %s/%d must be a mapping" % (clean_id, clean_apid)
                )
            all_structures = entry.get("all_structures", False)
            if not isinstance(all_structures, bool):
                raise ValueError(
                    "all_structures for %s/%d must be a boolean"
                    % (clean_id, clean_apid)
                )
            structure_ids = entry.get("structure_ids", [])
            if not isinstance(structure_ids, (list, tuple, set, frozenset)):
                raise ValueError(
                    "structure_ids for %s/%d must be a collection"
                    % (clean_id, clean_apid)
                )
            collected = set()
            for structure_id in structure_ids:
                collected.add(
                    _integer(
                        "configuration housekeeping structure", structure_id,
                        STRUCTURE_ID_MIN, STRUCTURE_ID_MAX,
                    )
                )
            if all_structures and collected:
                raise ValueError(
                    "entry %s/%d carries the all-structures wildcard and "
                    "explicit structures at the same time" % (clean_id, clean_apid)
                )
            tree[clean_apid] = {
                "all_structures": all_structures,
                "structure_ids": collected,
            }
        out[clean_id] = tree
    return out


def _add_one(working, known_stores, defined, selection):
    store_id = selection["store_id"]
    apid = selection["apid"]
    structure_id = selection["structure_id"]
    if store_id not in known_stores:
        return REJECTED, REASON_UNKNOWN_PACKET_STORE
    available = defined.get(apid)
    if not available:
        return REJECTED, REASON_NO_HOUSEKEEPING_DEFINITIONS
    if structure_id is not None and structure_id not in available:
        return REJECTED, REASON_STRUCTURE_NOT_DEFINED
    tree = working.setdefault(store_id, {})
    entry = tree.get(apid)
    if entry is None:
        entry = {"all_structures": False, "structure_ids": set()}
        tree[apid] = entry
    if structure_id is None:
        if entry["all_structures"]:
            return REJECTED, REASON_ALREADY_STORED
        entry["all_structures"] = True
        entry["structure_ids"] = set()
        return ACCEPTED, REASON_WILDCARD_SET
    if entry["all_structures"]:
        return REJECTED, REASON_SUBSUMED_BY_WILDCARD
    if structure_id in entry["structure_ids"]:
        return REJECTED, REASON_ALREADY_STORED
    if len(entry["structure_ids"]) >= MAX_STRUCTURES_PER_APPLICATION_PROCESS:
        return REJECTED, REASON_STRUCTURE_CAPACITY
    entry["structure_ids"].add(structure_id)
    return ACCEPTED, REASON_STRUCTURE_ADDED


def _delete_one(working, selection):
    store_id = selection["store_id"]
    apid = selection["apid"]
    structure_id = selection["structure_id"]
    tree = working.get(store_id)
    if tree is None:
        return REJECTED, REASON_NOT_IN_CONFIGURATION
    entry = tree.get(apid)
    if entry is None:
        return REJECTED, REASON_NOT_IN_CONFIGURATION
    if structure_id is None:
        del tree[apid]
        if not tree:
            del working[store_id]
        return ACCEPTED, REASON_ENTRY_DELETED
    if entry["all_structures"]:
        return REJECTED, REASON_WILDCARD_NOT_PARTIALLY_DELETABLE
    if structure_id not in entry["structure_ids"]:
        return REJECTED, REASON_NOT_IN_CONFIGURATION
    entry["structure_ids"].discard(structure_id)
    return ACCEPTED, REASON_STRUCTURE_DELETED


def _known_store_set(packet_store_ids):
    if not isinstance(packet_store_ids, (list, tuple, set, frozenset)):
        raise ValueError("packet_store_ids must be a collection")
    known = set()
    for store_id in packet_store_ids:
        known.add(_text("packet store", store_id, PACKET_STORE_ID_MAX_LENGTH))
    if not known:
        raise ValueError("packet_store_ids must not be empty")
    return known


def _run(config, items, handler):
    working = normalize_configuration(config)
    if not isinstance(items, (list, tuple)):
        raise ValueError("request items must be a list")
    dispositions = []
    for index, raw in enumerate(items):
        selection = validate_structure_selection(raw)
        status, reason = handler(working, selection)
        dispositions.append(
            {
                "index": index,
                "store_id": selection["store_id"],
                "apid": selection["apid"],
                "structure_id": selection["structure_id"],
                "status": status,
                "reason": reason,
            }
        )
    return working, dispositions


def add_housekeeping_storage_selections(config, packet_store_ids,
                                        defined_structures, items):
    """Apply an add request; return the new configuration and per-item outcome."""
    known = _known_store_set(packet_store_ids)
    defined = normalize_defined_structures(defined_structures)
    return _run(config, items, lambda w, s: _add_one(w, known, defined, s))


def delete_housekeeping_storage_selections(config, items):
    """Apply a delete request; return the new configuration and per-item outcome."""
    return _run(config, items, _delete_one)


def is_structure_stored(config, store_id, apid, structure_id):
    """Decide whether one packet store stores one housekeeping structure."""
    working = normalize_configuration(config)
    clean_id = _text("packet store identifier", store_id, PACKET_STORE_ID_MAX_LENGTH)
    _integer("application process identifier", apid, APID_MIN, APID_MAX)
    _integer(
        "housekeeping structure identifier", structure_id,
        STRUCTURE_ID_MIN, STRUCTURE_ID_MAX,
    )
    tree = working.get(clean_id)
    if tree is None:
        return False
    entry = tree.get(apid)
    if entry is None:
        return False
    if entry["all_structures"]:
        return True
    return structure_id in entry["structure_ids"]


def packet_stores_storing_structure(config, apid, structure_id):
    """Every packet store that writes one housekeeping structure down."""
    working = normalize_configuration(config)
    return sorted(
        store_id
        for store_id in working
        if is_structure_stored(working, store_id, apid, structure_id)
    )


def stale_selections(config, defined_structures):
    """Selections naming a housekeeping structure that no longer exists."""
    working = normalize_configuration(config)
    defined = normalize_defined_structures(defined_structures)
    stale = []
    for store_id in sorted(working):
        tree = working[store_id]
        for apid in sorted(tree):
            entry = tree[apid]
            available = defined.get(apid, set())
            for structure_id in sorted(entry["structure_ids"]):
                if structure_id not in available:
                    stale.append((store_id, apid, structure_id))
    return stale


def prune_stale_selections(config, defined_structures):
    """Remove the stale selections and say which ones were removed."""
    working = normalize_configuration(config)
    removed = stale_selections(working, defined_structures)
    for store_id, apid, structure_id in removed:
        working[store_id][apid]["structure_ids"].discard(structure_id)
    for store_id in list(working):
        tree = working[store_id]
        for apid in list(tree):
            entry = tree[apid]
            if not entry["all_structures"] and not entry["structure_ids"]:
                del tree[apid]
        if not tree:
            del working[store_id]
    return working, removed


def report_configuration(config):
    """Deterministic report of the configuration, sorted at every level."""
    working = normalize_configuration(config)
    stores = []
    selection_counts = {}
    for store_id in sorted(working):
        tree = working[store_id]
        processes = []
        for apid in sorted(tree):
            entry = tree[apid]
            structure_ids = sorted(entry["structure_ids"])
            for structure_id in structure_ids:
                key = (apid, structure_id)
                selection_counts[key] = selection_counts.get(key, 0) + 1
            processes.append(
                {
                    "apid": apid,
                    "all_structures": entry["all_structures"],
                    "structure_ids": structure_ids,
                    "structure_count": len(structure_ids),
                }
            )
        stores.append(
            {
                "store_id": store_id,
                "application_processes": processes,
                "application_process_count": len(processes),
            }
        )
    duplicated = sorted(key for key, count in selection_counts.items() if count > 1)
    return {
        "packet_stores": stores,
        "packet_store_count": len(stores),
        "structures_stored_by_more_than_one_store": duplicated,
        "stores_nothing": not stores,
    }
