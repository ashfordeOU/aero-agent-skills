"""General management of the content of a position-based schedule.

Anchor: ECSS-E-ST-70-41C clause 6.22.6.2 (managing the position-based
schedule, general). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Hold the schedule as entries keyed by a request identifier, each pinned to
   an orbit position of a whole orbit number and an angle from the ascending
   node.
2. Apply insertion and deletion operations one at a time, in the order they
   arrive, so a later operation sees the effect of an earlier one.
3. Enforce the two invariants the schedule content depends on: the capacity
   of the store and the uniqueness of the request identifier.
4. Keep the entries ordered by orbit position so the execution function can
   read the next one off the front.
5. Report the resulting schedule, the operations accepted and rejected, and
   the occupancy the schedule ended at.
"""

__all__ = [
    "DEGREES_PER_REVOLUTION",
    "OPERATION_INSERT",
    "OPERATION_DELETE",
    "SUPPORTED_OPERATIONS",
    "normalise_entry",
    "schedule_key",
    "order_schedule",
    "insert_entry",
    "delete_entry",
    "apply_schedule_operations",
]

DEGREES_PER_REVOLUTION = 360.0

OPERATION_INSERT = "insert"
OPERATION_DELETE = "delete"
SUPPORTED_OPERATIONS = (OPERATION_INSERT, OPERATION_DELETE)


def _require_non_negative_int(value, label):
    """Return value as a non-negative whole count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _require_positive_int(value, label):
    """Return value as a positive whole count."""
    value = _require_non_negative_int(value, label)
    if value == 0:
        raise ValueError("%s must be positive, got 0" % label)
    return value


def _require_angle(value, label):
    """Return an ascending-node angle inside one revolution."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    angle = float(value)
    if angle != angle or angle in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if angle < 0.0 or angle >= DEGREES_PER_REVOLUTION:
        raise ValueError(
            "%s %r falls outside one revolution from the ascending node"
            % (label, value)
        )
    return angle


def normalise_entry(entry):
    """Return one schedule entry as a validated dict."""
    if not isinstance(entry, dict):
        raise ValueError("schedule entry must be a mapping, got %r" % (entry,))
    for key in ("request_id", "orbit_number", "angle_degrees"):
        if key not in entry:
            raise ValueError("schedule entry missing required key '%s'" % key)
    request_id = entry["request_id"]
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("request_id must be a non-empty string, got %r" % (request_id,))
    return {
        "request_id": request_id.strip(),
        "orbit_number": _require_non_negative_int(entry["orbit_number"], "orbit_number"),
        "angle_degrees": _require_angle(entry["angle_degrees"], "angle_degrees"),
    }


def schedule_key(entry):
    """Return the ordering key of a schedule entry, in degrees flown."""
    return (
        entry["orbit_number"] * DEGREES_PER_REVOLUTION + entry["angle_degrees"],
        entry["request_id"],
    )


def order_schedule(entries):
    """Return the entries ordered by orbit position then request identifier."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a list or tuple")
    normalised = [normalise_entry(item) for item in entries]
    seen = set()
    for item in normalised:
        if item["request_id"] in seen:
            raise ValueError(
                "request identifier '%s' appears more than once in the schedule"
                % item["request_id"]
            )
        seen.add(item["request_id"])
    return tuple(sorted(normalised, key=schedule_key))


def insert_entry(schedule, entry, capacity):
    """Return the schedule with one entry inserted, or raise on refusal."""
    limit = _require_positive_int(capacity, "capacity")
    candidate = normalise_entry(entry)
    for item in schedule:
        if item["request_id"] == candidate["request_id"]:
            raise ValueError(
                "request identifier '%s' is already scheduled at orbit %d angle %g"
                % (item["request_id"], item["orbit_number"], item["angle_degrees"])
            )
    if len(schedule) >= limit:
        raise ValueError(
            "schedule already holds its capacity of %d entries" % limit
        )
    return tuple(sorted(tuple(schedule) + (candidate,), key=schedule_key))


def delete_entry(schedule, request_id):
    """Return the schedule with one entry deleted, or raise when absent."""
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("request_id must be a non-empty string, got %r" % (request_id,))
    target = request_id.strip()
    remaining = tuple(item for item in schedule if item["request_id"] != target)
    if len(remaining) == len(schedule):
        raise ValueError("request identifier '%s' is not in the schedule" % target)
    return remaining


def apply_schedule_operations(spec):
    """Apply a clause 6.22.6.2 run of schedule management operations.

    spec keys: initial_entries, capacity, operations. Each operation is a
    mapping with 'operation' of 'insert' (plus entry fields) or 'delete'
    (plus request_id).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("initial_entries", "capacity", "operations"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    capacity = _require_positive_int(spec["capacity"], "capacity")
    schedule = order_schedule(spec["initial_entries"])
    if len(schedule) > capacity:
        raise ValueError(
            "initial schedule holds %d entries, past the capacity of %d"
            % (len(schedule), capacity)
        )
    operations = spec["operations"]
    if not isinstance(operations, (list, tuple)):
        raise ValueError("operations must be a list or tuple")

    accepted = []
    rejected = []
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict) or "operation" not in operation:
            raise ValueError(
                "operation %d must be a mapping carrying an 'operation' key" % index
            )
        name = operation["operation"]
        if name not in SUPPORTED_OPERATIONS:
            raise ValueError(
                "operation %d names '%r', which is not one of %s"
                % (index, name, ", ".join(SUPPORTED_OPERATIONS))
            )
        try:
            if name == OPERATION_INSERT:
                schedule = insert_entry(schedule, operation, capacity)
                accepted.append((index, name, operation["request_id"]))
            else:
                if "request_id" not in operation:
                    raise ValueError("a delete operation needs a request_id")
                schedule = delete_entry(schedule, operation["request_id"])
                accepted.append((index, name, operation["request_id"]))
        except ValueError as refusal:
            rejected.append((index, name, str(refusal)))

    return {
        "capacity": capacity,
        "schedule": schedule,
        "scheduled_request_ids": tuple(item["request_id"] for item in schedule),
        "occupancy": len(schedule),
        "free_slots": capacity - len(schedule),
        "accepted_operations": tuple(accepted),
        "rejected_operations": tuple(rejected),
        "all_operations_accepted": not rejected,
    }
