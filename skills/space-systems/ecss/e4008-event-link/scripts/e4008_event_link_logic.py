"""Event links of an SMP Level-2 assembly artefact.

Anchor: ECSS-E-ST-40-08C clause 5.2.7.3 (event link). Paraphrased into an
implementable procedure; no standard text is reproduced.

What this module decides
------------------------
An event link wires an event source published by one component instance to an
event sink published by another, so that emitting the source invokes the sink.
Two normative checks decide whether the link holds:

1. the endpoints resolve to declared event elements with the right roles -- a
   source at the emitting end, a sink at the receiving end;
2. the argument the sink expects agrees with the argument the source carries;
   an argument-less event is written as the void argument and is not
   interchangeable with an event that carries a value, unless the assembly
   explicitly permits a void sink to discard an argument.

Around those two, the module also keeps the structural bookkeeping an event
link set needs: fan-out from one source to many sinks is admitted, fan-in into
one sink is admitted but reported as an ordering advisory, an identical link
declared twice is refused, and a link joining an instance to itself is refused
unless the assembly permits it.
"""

__all__ = [
    "EVENT_ROLES",
    "VOID_ARGUMENT",
    "EventLinkError",
    "argument_compatible",
    "assess_event_links",
    "event_signature",
    "fan_out_map",
    "resolve_event",
]

EVENT_ROLES = ("source", "sink")

# An event that carries no value declares the void argument. It is a distinct
# argument type, not a missing one.
VOID_ARGUMENT = "void"


class EventLinkError(ValueError):
    """An event link that clause 5.2.7.3 does not admit."""


def resolve_event(catalogue, instances, instance_path, element, role):
    """Resolve one endpoint onto a declared event element of the required role."""
    if role not in EVENT_ROLES:
        raise ValueError("role must be one of %s" % (", ".join(EVENT_ROLES),))
    if not isinstance(catalogue, dict) or not catalogue:
        raise ValueError("catalogue must be a non-empty mapping of type name to type model")
    if not isinstance(instances, dict) or not instances:
        raise ValueError("instances must be a non-empty mapping of path to type name")
    if not isinstance(instance_path, str) or not instance_path:
        raise ValueError("instance path must be a non-empty string")
    if not isinstance(element, str) or not element:
        raise ValueError("event element name must be a non-empty string")
    if instance_path not in instances:
        raise EventLinkError(
            "%r is not an instance of this assembly" % (instance_path,)
        )
    type_name = instances[instance_path]
    if type_name not in catalogue:
        raise ValueError("instance %r names undeclared type %r" % (instance_path, type_name))
    model = catalogue[type_name]
    if not isinstance(model, dict):
        raise ValueError("type model %r must be a mapping" % type_name)
    events = model.get("events")
    if not isinstance(events, dict):
        events = {}
    if element not in events:
        raise EventLinkError("type %r declares no event %r" % (type_name, element))
    declared = events[element]
    if not isinstance(declared, dict) or "role" not in declared:
        raise ValueError("event %r must declare a role" % element)
    if declared["role"] not in EVENT_ROLES:
        raise ValueError("event %r declares an unknown role %r" % (element, declared["role"]))
    if declared["role"] != role:
        raise EventLinkError(
            "event %s.%s is an event %s and cannot act as an event %s"
            % (instance_path, element, declared["role"], role)
        )
    argument = declared.get("argument", VOID_ARGUMENT)
    if not isinstance(argument, str) or not argument:
        raise ValueError("event %r declares a malformed argument type" % element)
    return {
        "instance": instance_path,
        "type": type_name,
        "element": element,
        "role": role,
        "argument": argument,
    }


def argument_compatible(source_argument, sink_argument, allow_discard=False):
    """Return True when a sink can receive what a source emits."""
    for label, value in (("source", source_argument), ("sink", sink_argument)):
        if not isinstance(value, str) or not value:
            raise ValueError("%s argument type must be a non-empty string" % label)
    if source_argument == sink_argument:
        return True
    if allow_discard and sink_argument == VOID_ARGUMENT:
        return True
    return False


def event_signature(source, sink):
    """Return the duplicate-detection signature of a resolved event link."""
    for label, value in (("source", source), ("sink", sink)):
        if not isinstance(value, dict) or "instance" not in value or "element" not in value:
            raise ValueError("%s endpoint must carry 'instance' and 'element'" % label)
    return (
        "%s.%s" % (source["instance"], source["element"]),
        "%s.%s" % (sink["instance"], sink["element"]),
    )


def fan_out_map(accepted):
    """Return the map from each event source to the sinks it reaches."""
    if not isinstance(accepted, (list, tuple)):
        raise ValueError("accepted must be a sequence of resolved links")
    mapping = {}
    for link in accepted:
        if not isinstance(link, dict) or "source" not in link or "sink" not in link:
            raise ValueError("each accepted link must carry 'source' and 'sink'")
        key, value = event_signature(link["source"], link["sink"])
        mapping.setdefault(key, []).append(value)
    return mapping


def assess_event_links(spec):
    """Grade a whole event-link set against the two clause 5.2.7.3 checks.

    spec keys: 'catalogue', 'instances', 'links' (mappings with 'name',
    'source', 'source_event', 'sink', 'sink_event'), optional
    'allow_argument_discard' and 'allow_self_links'.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("catalogue", "instances", "links"):
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    links = spec["links"]
    if not isinstance(links, (list, tuple)):
        raise ValueError("spec['links'] must be a sequence")
    allow_discard = bool(spec.get("allow_argument_discard", False))
    allow_self = bool(spec.get("allow_self_links", False))
    catalogue = spec["catalogue"]
    instances = spec["instances"]
    accepted = []
    findings = []
    advisories = []
    signatures = {}
    sink_sources = {}
    for position, link in enumerate(links):
        if not isinstance(link, dict):
            raise ValueError("link at position %d must be a mapping" % position)
        for key in ("name", "source", "source_event", "sink", "sink_event"):
            if key not in link:
                raise ValueError("link at position %d is missing %r" % (position, key))
        label = link["name"]
        try:
            source = resolve_event(
                catalogue, instances, link["source"], link["source_event"], "source"
            )
            sink = resolve_event(
                catalogue, instances, link["sink"], link["sink_event"], "sink"
            )
        except EventLinkError as exc:
            findings.append("%s: %s" % (label, exc))
            continue
        if not argument_compatible(source["argument"], sink["argument"], allow_discard):
            findings.append(
                "%s: source emits %r but the sink expects %r"
                % (label, source["argument"], sink["argument"])
            )
            continue
        if source["instance"] == sink["instance"] and not allow_self:
            findings.append(
                "%s: source and sink sit on instance %r; a self-link is not admitted"
                % (label, source["instance"])
            )
            continue
        signature = event_signature(source, sink)
        if signature in signatures:
            findings.append(
                "%s: duplicates event link %r between the same source and sink"
                % (label, signatures[signature])
            )
            continue
        signatures[signature] = label
        sink_sources.setdefault(signature[1], []).append(signature[0])
        accepted.append({"name": label, "source": source, "sink": sink})
    for sink_path in sorted(sink_sources):
        sources = sink_sources[sink_path]
        if len(sources) > 1:
            advisories.append(
                "sink %s is reached by %d sources; the invocation order follows the "
                "assembly declaration order" % (sink_path, len(sources))
            )
    return {
        "accepted": accepted,
        "fan_out": fan_out_map(accepted),
        "advisories": advisories,
        "findings": findings,
        "compliant": not findings,
    }
