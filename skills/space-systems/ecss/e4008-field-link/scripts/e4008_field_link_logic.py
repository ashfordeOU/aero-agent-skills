"""Field links of an SMP Level-2 assembly artefact.

Anchor: ECSS-E-ST-40-08C clause 5.2.7.4 (field link). Paraphrased into an
implementable procedure; no standard text is reproduced.

What this module decides
------------------------
A field link copies the value of one component's field into another
component's field every time the assembly applies its data flow. Six normative
checks decide whether the copy is admissible:

1. the source endpoint resolves to a field the source type declares, and that
   field is readable -- an output or a state field, never a pure input;
2. the target endpoint resolves to a field the target type declares, and that
   field is writeable -- an input or a state field, never a model-produced
   output;
3. the two fields carry the same primitive datatype; the copy is a transfer,
   not a conversion, so a widening pair is still a mismatch;
4. the two fields carry the same array shape, an unset shape meaning scalar;
5. no target field receives more than one incoming link, because two writers
   into one field make the value depend on application order;
6. a link does not join a field to itself.

The accepted links also yield the set of driven target fields, which the
component-configuration check consumes: a field written every step must not
also carry a configured value. A cycle purely inside the field-link graph is
reported as an advisory, since it makes the propagated values order-dependent
without being a defect of any single link.
"""

__all__ = [
    "READABLE_DIRECTIONS",
    "WRITEABLE_DIRECTIONS",
    "FieldLinkError",
    "assess_field_links",
    "detect_dataflow_cycles",
    "field_shape",
    "resolve_field_endpoint",
    "shapes_match",
]

# A field the model writes can be read by a link; a pure input carries only
# what something else put there, so it is not a data source.
READABLE_DIRECTIONS = ("output", "state")

# A field the model reads can be written by a link; a pure output is produced
# by the model and would overwrite the link on the next update.
WRITEABLE_DIRECTIONS = ("input", "state")


class FieldLinkError(ValueError):
    """A field link that clause 5.2.7.4 does not admit."""


def field_shape(descriptor):
    """Return the array shape of a field descriptor as a tuple; () is scalar."""
    if not isinstance(descriptor, dict):
        raise ValueError("field descriptor must be a mapping")
    dimensions = descriptor.get("dimensions")
    if dimensions is None:
        return ()
    if not isinstance(dimensions, (list, tuple)) or not dimensions:
        raise ValueError("field dimensions must be a non-empty sequence when declared")
    shape = []
    for extent in dimensions:
        if not isinstance(extent, int) or isinstance(extent, bool) or extent <= 0:
            raise ValueError("array extent %r must be a positive integer" % (extent,))
        shape.append(extent)
    return tuple(shape)


def shapes_match(source_descriptor, target_descriptor):
    """Return True when two field descriptors carry the same array shape."""
    return field_shape(source_descriptor) == field_shape(target_descriptor)


def resolve_field_endpoint(catalogue, instances, instance_path, field_name, role):
    """Resolve one endpoint onto a declared field with the direction its role needs."""
    if role not in ("source", "target"):
        raise ValueError("role must be 'source' or 'target'")
    if not isinstance(catalogue, dict) or not catalogue:
        raise ValueError("catalogue must be a non-empty mapping of type name to type model")
    if not isinstance(instances, dict) or not instances:
        raise ValueError("instances must be a non-empty mapping of path to type name")
    if not isinstance(instance_path, str) or not instance_path:
        raise ValueError("instance path must be a non-empty string")
    if not isinstance(field_name, str) or not field_name:
        raise ValueError("field name must be a non-empty string")
    if instance_path not in instances:
        raise FieldLinkError("%r is not an instance of this assembly" % (instance_path,))
    type_name = instances[instance_path]
    if type_name not in catalogue:
        raise ValueError("instance %r names undeclared type %r" % (instance_path, type_name))
    model = catalogue[type_name]
    if not isinstance(model, dict):
        raise ValueError("type model %r must be a mapping" % type_name)
    fields = model.get("fields")
    if not isinstance(fields, dict):
        fields = {}
    if field_name not in fields:
        raise FieldLinkError("type %r declares no field %r" % (type_name, field_name))
    descriptor = fields[field_name]
    if not isinstance(descriptor, dict) or "datatype" not in descriptor:
        raise ValueError("field %r must declare a datatype" % field_name)
    direction = descriptor.get("direction", "input")
    admitted = READABLE_DIRECTIONS if role == "source" else WRITEABLE_DIRECTIONS
    if direction not in ("input", "output", "state"):
        raise ValueError("field %r declares an unknown direction %r" % (field_name, direction))
    if direction not in admitted:
        raise FieldLinkError(
            "field %s.%s is an %s field and cannot be the %s of a field link"
            % (instance_path, field_name, direction, role)
        )
    return {
        "instance": instance_path,
        "type": type_name,
        "field": field_name,
        "path": "%s.%s" % (instance_path, field_name),
        "direction": direction,
        "datatype": descriptor["datatype"],
        "shape": field_shape(descriptor),
    }


def detect_dataflow_cycles(accepted):
    """Return the instance paths that take part in a field-link cycle."""
    if not isinstance(accepted, (list, tuple)):
        raise ValueError("accepted must be a sequence of resolved links")
    edges = {}
    for link in accepted:
        if not isinstance(link, dict) or "source" not in link or "target" not in link:
            raise ValueError("each accepted link must carry 'source' and 'target'")
        edges.setdefault(link["source"]["instance"], set()).add(link["target"]["instance"])
    colour = {}
    cycle_members = set()

    def visit(node, stack):
        colour[node] = "open"
        stack.append(node)
        for nxt in sorted(edges.get(node, ())):
            state = colour.get(nxt)
            if state == "open":
                cycle_members.update(stack[stack.index(nxt):])
            elif state is None:
                visit(nxt, stack)
        stack.pop()
        colour[node] = "done"

    for node in sorted(edges):
        if node not in colour:
            visit(node, [])
    return sorted(cycle_members)


def assess_field_links(spec):
    """Grade a whole field-link set against the six clause 5.2.7.4 checks.

    spec keys: 'catalogue', 'instances', 'links' (mappings with 'name',
    'source', 'source_field', 'target', 'target_field'), optional
    'allow_self_links'.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("catalogue", "instances", "links"):
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    links = spec["links"]
    if not isinstance(links, (list, tuple)):
        raise ValueError("spec['links'] must be a sequence")
    allow_self = bool(spec.get("allow_self_links", False))
    catalogue = spec["catalogue"]
    instances = spec["instances"]
    accepted = []
    findings = []
    writers = {}
    for position, link in enumerate(links):
        if not isinstance(link, dict):
            raise ValueError("link at position %d must be a mapping" % position)
        for key in ("name", "source", "source_field", "target", "target_field"):
            if key not in link:
                raise ValueError("link at position %d is missing %r" % (position, key))
        label = link["name"]
        try:
            source = resolve_field_endpoint(
                catalogue, instances, link["source"], link["source_field"], "source"
            )
            target = resolve_field_endpoint(
                catalogue, instances, link["target"], link["target_field"], "target"
            )
        except FieldLinkError as exc:
            findings.append("%s: %s" % (label, exc))
            continue
        if source["path"] == target["path"]:
            findings.append("%s: a field cannot be linked to itself" % label)
            continue
        if source["instance"] == target["instance"] and not allow_self:
            findings.append(
                "%s: both fields sit on instance %r; a self-link is not admitted"
                % (label, source["instance"])
            )
            continue
        if source["datatype"] != target["datatype"]:
            findings.append(
                "%s: source carries %s but the target field is %s; a field link copies, "
                "it does not convert" % (label, source["datatype"], target["datatype"])
            )
            continue
        if source["shape"] != target["shape"]:
            findings.append(
                "%s: source shape %r does not match target shape %r"
                % (label, source["shape"], target["shape"])
            )
            continue
        if target["path"] in writers:
            findings.append(
                "%s: target %s is already written by link %r; two writers make the "
                "value order-dependent" % (label, target["path"], writers[target["path"]])
            )
            continue
        writers[target["path"]] = label
        accepted.append({"name": label, "source": source, "target": target})
    cycle_members = detect_dataflow_cycles(accepted)
    advisories = []
    if cycle_members:
        advisories.append(
            "field links form a cycle through %s; the propagated values depend on the "
            "order the assembly applies them" % ", ".join(cycle_members)
        )
    return {
        "accepted": accepted,
        "driven_fields": sorted(writers),
        "cycle_members": cycle_members,
        "advisories": advisories,
        "findings": findings,
        "compliant": not findings,
    }
