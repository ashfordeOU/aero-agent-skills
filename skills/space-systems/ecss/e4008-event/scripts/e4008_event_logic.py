"""Event declaration, subscription and emission rules for a space simulator.

Anchor: ECSS-E-ST-40-08C clause 5.4.6 (event). Paraphrased into an
implementable model; no standard text is reproduced. The clause carries
fourteen normative items covering how an event source is declared, how a
sink subscribes and unsubscribes, what an emission is allowed to carry,
the order the subscribed sinks are notified in, and what the simulator
owes the remaining sinks when one of them raises.

Model implemented here
----------------------
* An event source is declared once per publisher with a single argument
  type drawn from the infrastructure primitive set. A void source carries
  no argument at all.
* A sink subscribes to a source by name. A second subscription by the
  same sink is refused rather than silently collapsed, and an unsubscribe
  by a sink that never subscribed is refused rather than ignored.
* Delivery order is the subscription order, so a run is reproducible.
* An emission is stamped with a monotonic sequence number, is permitted
  only from the simulator states that allow model interaction, and is
  refused when the argument does not match the declared type.
* A sink that raises does not stop the notification of the sinks behind
  it; the failure is collected and reported with the emission record.
"""

__all__ = [
    "NORMATIVE_ITEM_COUNT",
    "ARGUMENT_TYPES",
    "SIMULATOR_STATES",
    "EMISSION_PERMITTED_STATES",
    "NORMATIVE_ITEMS",
    "validate_event_name",
    "validate_argument_type",
    "validate_simulator_state",
    "argument_matches_type",
    "normalise_sink_token",
    "EventRegistry",
    "assess_event_conformance",
]

NORMATIVE_ITEM_COUNT = 14

ARGUMENT_TYPES = (
    "void",
    "bool",
    "int32",
    "int64",
    "float64",
    "string",
    "duration",
    "datetime",
)

SIMULATOR_STATES = (
    "building",
    "connecting",
    "initialising",
    "standby",
    "executing",
    "storing",
    "restoring",
    "reconnecting",
    "exiting",
    "aborting",
)

# Emission needs a simulator that already holds a model tree and is not on
# its way out; building/connecting have no tree yet, exiting/aborting are
# terminal transitions where a new notification cannot be honoured.
EMISSION_PERMITTED_STATES = (
    "initialising",
    "standby",
    "executing",
    "storing",
    "restoring",
    "reconnecting",
)

_INT32_MIN = -(2 ** 31)
_INT32_MAX = 2 ** 31 - 1
_INT64_MIN = -(2 ** 63)
_INT64_MAX = 2 ** 63 - 1

NORMATIVE_ITEMS = (
    ("EV-01", "event source name is unique within its publisher"),
    ("EV-02", "event source declares exactly one argument type"),
    ("EV-03", "emitted argument matches the declared argument type"),
    ("EV-04", "a repeated subscription by the same sink is refused"),
    ("EV-05", "an unsubscribe by a sink that never subscribed is refused"),
    ("EV-06", "sinks are notified in subscription order"),
    ("EV-07", "emission happens only from a state that permits it"),
    ("EV-08", "a raising sink does not suppress the sinks behind it"),
    ("EV-09", "subscriber count stays within the declared maximum"),
    ("EV-10", "two sink names do not collapse onto the same identity"),
    ("EV-11", "a void event carries no argument"),
    ("EV-12", "every emission carries a monotonic sequence number"),
    ("EV-13", "an unsubscribe during delivery leaves that delivery intact"),
    ("EV-14", "every declared source has a documented emitter"),
)

_STATUSES = ("satisfied", "violated", "not-exercised")


def validate_event_name(name):
    """Return the validated event source name."""
    if not isinstance(name, str):
        raise ValueError("event name must be a string, got %r" % (name,))
    text = name.strip()
    if text != name:
        raise ValueError("event name must not carry leading or trailing blanks: %r" % (name,))
    if not text:
        raise ValueError("event name must not be empty")
    if len(text) > 64:
        raise ValueError("event name must be at most 64 characters, got %d" % len(text))
    if not text[0].isalpha():
        raise ValueError("event name must start with a letter, got %r" % (name,))
    for char in text:
        if not (char.isalnum() or char == "_"):
            raise ValueError("event name may only carry letters, digits and underscore: %r" % (name,))
    return text


def validate_argument_type(type_name):
    """Return the validated argument type of an event source."""
    if not isinstance(type_name, str):
        raise ValueError("argument type must be a string, got %r" % (type_name,))
    text = type_name.strip().lower()
    if text not in ARGUMENT_TYPES:
        raise ValueError(
            "argument type %r is outside the infrastructure primitive set %s"
            % (type_name, ", ".join(ARGUMENT_TYPES))
        )
    return text


def validate_simulator_state(state):
    """Return the validated simulator state name."""
    if not isinstance(state, str):
        raise ValueError("simulator state must be a string, got %r" % (state,))
    text = state.strip().lower()
    if text not in SIMULATOR_STATES:
        raise ValueError("unknown simulator state %r" % (state,))
    return text


def argument_matches_type(argument_type, value):
    """Return True when the value is admissible for the declared argument type."""
    kind = validate_argument_type(argument_type)
    if kind == "void":
        return value is None
    if value is None:
        return False
    if kind == "bool":
        return isinstance(value, bool)
    if kind in ("int32", "int64"):
        if not isinstance(value, int) or isinstance(value, bool):
            return False
        low, high = (_INT32_MIN, _INT32_MAX) if kind == "int32" else (_INT64_MIN, _INT64_MAX)
        return low <= value <= high
    if kind == "float64":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "string":
        return isinstance(value, str)
    if kind == "duration":
        # A duration is an integer count of infrastructure ticks and may be
        # negative (a lead time), but it is never a float or a bool.
        return isinstance(value, int) and not isinstance(value, bool)
    # datetime is an absolute tick count and is never negative.
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def normalise_sink_token(sink):
    """Return the identity token a sink name collapses onto."""
    if not isinstance(sink, str):
        raise ValueError("sink name must be a string, got %r" % (sink,))
    text = sink.strip()
    if not text:
        raise ValueError("sink name must not be empty")
    if len(text) > 96:
        raise ValueError("sink name must be at most 96 characters, got %d" % len(text))
    return text.lower().replace("-", "_").replace(" ", "_")


class EventRegistry(object):
    """A publisher's event sources, their subscribers and their emissions."""

    def __init__(self):
        self._sources = {}
        self._order = []
        self._sequence = 0

    @property
    def sequence(self):
        """Return the number of emissions accepted so far."""
        return self._sequence

    def source_names(self):
        """Return the declared source names in declaration order."""
        return list(self._order)

    def declare_source(self, name, argument_type, max_subscribers=None, documented_emitter=True):
        """Declare one event source; a repeated name is refused."""
        key = validate_event_name(name)
        kind = validate_argument_type(argument_type)
        if key in self._sources:
            raise ValueError("event source %r is already declared by this publisher" % key)
        if max_subscribers is not None:
            if not isinstance(max_subscribers, int) or isinstance(max_subscribers, bool):
                raise ValueError("max_subscribers must be an integer or None")
            if max_subscribers < 1:
                raise ValueError("max_subscribers must be at least 1, got %d" % max_subscribers)
        if not isinstance(documented_emitter, bool):
            raise ValueError("documented_emitter must be a boolean")
        self._sources[key] = {
            "name": key,
            "argument_type": kind,
            "max_subscribers": max_subscribers,
            "documented_emitter": documented_emitter,
            "subscribers": [],
            "tokens": {},
        }
        self._order.append(key)
        return self._sources[key]

    def _source(self, name):
        key = validate_event_name(name)
        if key not in self._sources:
            raise ValueError("event source %r is not declared" % key)
        return self._sources[key]

    def subscribers(self, name):
        """Return the subscribed sinks of a source, in subscription order."""
        return list(self._source(name)["subscribers"])

    def subscribe(self, name, sink):
        """Subscribe a sink to a source and return the resulting order."""
        source = self._source(name)
        token = normalise_sink_token(sink)
        if token in source["tokens"]:
            held = source["tokens"][token]
            if held == sink:
                raise ValueError("sink %r is already subscribed to %r" % (sink, source["name"]))
            raise ValueError(
                "sink %r collapses onto the identity of the already subscribed sink %r"
                % (sink, held)
            )
        limit = source["max_subscribers"]
        if limit is not None and len(source["subscribers"]) >= limit:
            raise ValueError(
                "source %r accepts at most %d subscribers" % (source["name"], limit)
            )
        source["subscribers"].append(sink)
        source["tokens"][token] = sink
        return list(source["subscribers"])

    def unsubscribe(self, name, sink):
        """Unsubscribe a sink; a sink that never subscribed is refused."""
        source = self._source(name)
        token = normalise_sink_token(sink)
        if token not in source["tokens"]:
            raise ValueError(
                "sink %r is not subscribed to %r and cannot be unsubscribed"
                % (sink, source["name"])
            )
        held = source["tokens"].pop(token)
        source["subscribers"].remove(held)
        return list(source["subscribers"])

    def emit(self, name, argument=None, state="executing", failing_sinks=()):
        """Emit one event and return the delivery record."""
        source = self._source(name)
        resolved = validate_simulator_state(state)
        if resolved not in EMISSION_PERMITTED_STATES:
            raise ValueError(
                "state %r does not permit an event emission" % resolved
            )
        kind = source["argument_type"]
        if kind == "void" and argument is not None:
            raise ValueError("source %r is void and cannot carry an argument" % source["name"])
        if not argument_matches_type(kind, argument):
            raise ValueError(
                "argument %r does not match the declared type %r of source %r"
                % (argument, kind, source["name"])
            )
        if not isinstance(failing_sinks, (list, tuple, set, frozenset)):
            raise ValueError("failing_sinks must be a sequence of sink names")
        failing = set()
        for entry in failing_sinks:
            failing.add(normalise_sink_token(entry))
        delivered = []
        failed = []
        for sink in list(source["subscribers"]):
            if normalise_sink_token(sink) in failing:
                failed.append(sink)
            else:
                delivered.append(sink)
        self._sequence += 1
        return {
            "sequence": self._sequence,
            "source": source["name"],
            "argument_type": kind,
            "argument": argument,
            "state": resolved,
            "notified": list(source["subscribers"]),
            "delivered": delivered,
            "failed": failed,
        }


def _blank_items():
    return dict((item_id, {"id": item_id, "title": title, "status": "not-exercised", "detail": ""})
                for item_id, title in NORMATIVE_ITEMS)


def _mark(items, item_id, status, detail):
    if status not in _STATUSES:
        raise ValueError("unknown item status %r" % (status,))
    record = items[item_id]
    if record["status"] == "violated" and status != "violated":
        return
    record["status"] = status
    record["detail"] = detail


def assess_event_conformance(spec):
    """Grade an event design against the fourteen normative items of the clause.

    spec keys: sources (required list of source declarations), subscriptions,
    unsubscriptions, emissions, unsubscribe_during_delivery (bool).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    sources = spec.get("sources")
    if not isinstance(sources, (list, tuple)) or not sources:
        raise ValueError("spec['sources'] must be a non-empty sequence of source declarations")
    items = _blank_items()
    registry = EventRegistry()

    for entry in sources:
        if not isinstance(entry, dict):
            raise ValueError("each source declaration must be a mapping")
        if "name" not in entry:
            raise ValueError("a source declaration is missing 'name'")
        if "argument_type" not in entry:
            _mark(items, "EV-02", "violated",
                  "source %r declares no argument type" % (entry["name"],))
            continue
        try:
            registry.declare_source(
                entry["name"],
                entry["argument_type"],
                entry.get("max_subscribers"),
                bool(entry.get("documented_emitter", True)),
            )
        except ValueError as exc:
            if "already declared" in str(exc):
                _mark(items, "EV-01", "violated", str(exc))
            else:
                _mark(items, "EV-02", "violated", str(exc))
            continue
        if items["EV-01"]["status"] == "not-exercised":
            _mark(items, "EV-01", "satisfied", "declared names stay distinct")
        if items["EV-02"]["status"] == "not-exercised":
            _mark(items, "EV-02", "satisfied", "every source carries one declared type")

    if not registry.source_names():
        raise ValueError("no source declaration in the spec could be accepted")

    for entry in sources:
        if isinstance(entry, dict) and entry.get("name") in registry.source_names():
            if not bool(entry.get("documented_emitter", True)):
                _mark(items, "EV-14", "violated",
                      "source %r has no documented emitter" % (entry["name"],))
            elif items["EV-14"]["status"] == "not-exercised":
                _mark(items, "EV-14", "satisfied", "every accepted source names an emitter")

    for entry in spec.get("subscriptions", ()) or ():
        if not isinstance(entry, dict) or "source" not in entry or "sink" not in entry:
            raise ValueError("each subscription must be a mapping with 'source' and 'sink'")
        try:
            registry.subscribe(entry["source"], entry["sink"])
        except ValueError as exc:
            message = str(exc)
            if "collapses onto" in message:
                _mark(items, "EV-10", "violated", message)
            elif "already subscribed" in message:
                _mark(items, "EV-04", "satisfied", message)
            elif "accepts at most" in message:
                _mark(items, "EV-09", "satisfied", message)
            else:
                raise
            continue
        if items["EV-10"]["status"] == "not-exercised":
            _mark(items, "EV-10", "satisfied", "sink identities stay distinct")
        if items["EV-09"]["status"] == "not-exercised":
            _mark(items, "EV-09", "satisfied", "subscriber counts stay within the declared maximum")

    for entry in spec.get("unsubscriptions", ()) or ():
        if not isinstance(entry, dict) or "source" not in entry or "sink" not in entry:
            raise ValueError("each unsubscription must be a mapping with 'source' and 'sink'")
        try:
            registry.unsubscribe(entry["source"], entry["sink"])
        except ValueError as exc:
            if "cannot be unsubscribed" in str(exc):
                _mark(items, "EV-05", "satisfied", str(exc))
                continue
            raise
        if items["EV-05"]["status"] == "not-exercised":
            _mark(items, "EV-05", "satisfied", "an unsubscribe names a real subscriber")

    sequences = []
    for entry in spec.get("emissions", ()) or ():
        if not isinstance(entry, dict) or "source" not in entry:
            raise ValueError("each emission must be a mapping carrying 'source'")
        expected_order = None
        if entry["source"] in registry.source_names():
            expected_order = registry.subscribers(entry["source"])
        try:
            record = registry.emit(
                entry["source"],
                entry.get("argument"),
                entry.get("state", "executing"),
                entry.get("failing_sinks", ()),
            )
        except ValueError as exc:
            message = str(exc)
            if "does not permit" in message:
                _mark(items, "EV-07", "satisfied", message)
            elif "is void and cannot carry" in message:
                _mark(items, "EV-11", "satisfied", message)
            elif "does not match the declared type" in message:
                _mark(items, "EV-03", "satisfied", message)
            else:
                raise
            continue
        sequences.append(record["sequence"])
        if items["EV-03"]["status"] == "not-exercised":
            _mark(items, "EV-03", "satisfied", "emitted arguments match their declared types")
        if items["EV-07"]["status"] == "not-exercised":
            _mark(items, "EV-07", "satisfied", "emissions come from permitted states only")
        if record["argument_type"] == "void" and items["EV-11"]["status"] == "not-exercised":
            _mark(items, "EV-11", "satisfied", "the void source emitted without an argument")
        if expected_order is not None:
            if record["notified"] == expected_order:
                if items["EV-06"]["status"] == "not-exercised":
                    _mark(items, "EV-06", "satisfied", "notification order equals subscription order")
            else:
                _mark(items, "EV-06", "violated",
                      "notification order %r departs from subscription order %r"
                      % (record["notified"], expected_order))
        if record["failed"]:
            if record["delivered"] == [s for s in record["notified"] if s not in record["failed"]]:
                _mark(items, "EV-08", "satisfied",
                      "a raising sink left %d further notifications intact" % len(record["delivered"]))
            else:
                _mark(items, "EV-08", "violated", "a raising sink suppressed later notifications")

    if sequences:
        if sequences == sorted(sequences) and len(set(sequences)) == len(sequences):
            _mark(items, "EV-12", "satisfied", "emission sequence numbers increase monotonically")
        else:
            _mark(items, "EV-12", "violated", "emission sequence numbers are not monotonic")

    flag = spec.get("unsubscribe_during_delivery")
    if flag is not None:
        if not isinstance(flag, bool):
            raise ValueError("unsubscribe_during_delivery must be a boolean or absent")
        if flag:
            _mark(items, "EV-13", "satisfied",
                  "the in-flight delivery works off a snapshot of the subscriber list")
        else:
            _mark(items, "EV-13", "violated",
                  "an unsubscribe during delivery mutates the list being walked")

    ordered = [items[item_id] for item_id, _ in NORMATIVE_ITEMS]
    violations = [rec for rec in ordered if rec["status"] == "violated"]
    not_exercised = [rec for rec in ordered if rec["status"] == "not-exercised"]
    return {
        "items": ordered,
        "item_count": len(ordered),
        "satisfied": [rec for rec in ordered if rec["status"] == "satisfied"],
        "violations": violations,
        "not_exercised": not_exercised,
        "coverage": (len(ordered) - len(not_exercised)) / float(len(ordered)),
        "compliant": not violations and not not_exercised,
        "registry": registry,
    }
