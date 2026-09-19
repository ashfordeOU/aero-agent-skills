"""Instances and sub-assemblies of an SMP Level-2 assembly artefact.

Anchor: ECSS-E-ST-40-08C clause 5.2.9 (assembly instance, or sub-assembly).
Paraphrased into an implementable procedure; no standard text is reproduced.

What this module decides
------------------------
An assembly artefact builds a tree. Each node is either an *instance* of a
model type taken from a catalogue, or a *sub-assembly*: a reference to another
assembly that is expanded in place. Thirteen checks decide whether the tree the
artefact describes can be built:

 1. every node declares a name;
 2. the name is a valid identifier;
 3. names are unique among siblings;
 4. a node names exactly one implementation -- a model type or a sub-assembly,
    never both and never neither;
 5. a named model type is declared in the catalogue;
 6. a named sub-assembly is declared in the assembly set;
 7. an abstract model type is not instantiated;
 8. sub-assembly expansion is acyclic, directly and transitively;
 9. the nesting depth stays within the declared maximum;
10. the instance path is unique across the flattened tree;
11. a node carries children only where containment is declared, and a
    sub-assembly node takes its children from the assembly it names;
12. the child count of a container respects its declared multiplicity;
13. every declared assembly is reached from the root, so nothing is carried
    that the artefact never builds.

Malformed input raises. Clause non-conformances are returned as findings so a
whole artefact is graded in one pass.
"""

import re

__all__ = [
    "UNBOUNDED",
    "AssemblyError",
    "assess_assembly",
    "container_multiplicity",
    "detect_sub_assembly_cycles",
    "flatten_instances",
    "instance_path",
    "validate_instance_name",
]

# A container upper multiplicity of -1 admits any number of children.
UNBOUNDED = -1

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class AssemblyError(ValueError):
    """A node that clause 5.2.9 does not admit."""


def validate_instance_name(name):
    """Return the instance name if it is a valid identifier."""
    if name is None:
        raise AssemblyError("instance declares no name")
    if not isinstance(name, str):
        raise ValueError("instance name must be a string")
    if _IDENTIFIER.match(name) is None:
        raise AssemblyError("instance name %r is not a valid identifier" % name)
    return name


def instance_path(prefix, name):
    """Return the dotted path of a node under its container path."""
    if not isinstance(prefix, str):
        raise ValueError("prefix must be a string")
    validate_instance_name(name)
    return name if not prefix else "%s.%s" % (prefix, name)


def container_multiplicity(model, where="type"):
    """Return the (lower, upper) child multiplicity, or None when not a container."""
    if not isinstance(model, dict):
        raise ValueError("%s model must be a mapping" % where)
    container = model.get("container")
    if container is None:
        return None
    if not isinstance(container, dict):
        raise ValueError("%s container declaration must be a mapping" % where)
    lower = container.get("lower", 0)
    upper = container.get("upper", UNBOUNDED)
    for label, value in (("lower", lower), ("upper", upper)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s container %s multiplicity must be an integer" % (where, label))
    if lower < 0:
        raise ValueError("%s container lower multiplicity must not be negative" % where)
    if upper < UNBOUNDED:
        raise ValueError("%s container upper multiplicity must be -1 or non-negative" % where)
    if upper != UNBOUNDED and upper < lower:
        raise ValueError("%s container upper multiplicity is below its lower" % where)
    return (lower, upper)


def _assembly_entries(assemblies, name):
    """Return the validated node list of one assembly definition."""
    if name not in assemblies:
        raise AssemblyError("assembly %r is not declared" % name)
    definition = assemblies[name]
    if not isinstance(definition, dict):
        raise ValueError("assembly %r must be a mapping" % name)
    entries = definition.get("instances", [])
    if not isinstance(entries, (list, tuple)):
        raise ValueError("assembly %r must carry a sequence of instances" % name)
    return entries


def detect_sub_assembly_cycles(assemblies):
    """Return the assembly names that take part in a sub-assembly cycle."""
    if not isinstance(assemblies, dict) or not assemblies:
        raise ValueError("assemblies must be a non-empty mapping")
    edges = {}
    for name in assemblies:
        targets = set()
        for entry in _assembly_entries(assemblies, name):
            if isinstance(entry, dict) and isinstance(entry.get("assembly"), str):
                targets.add(entry["assembly"])
        edges[name] = targets
    colour = {}
    members = set()

    def visit(node, stack):
        colour[node] = "open"
        stack.append(node)
        for nxt in sorted(edges.get(node, ())):
            state = colour.get(nxt)
            if state == "open":
                members.update(stack[stack.index(nxt):])
            elif state is None and nxt in edges:
                visit(nxt, stack)
        stack.pop()
        colour[node] = "done"

    for node in sorted(edges):
        if node not in colour:
            visit(node, [])
    return sorted(members)


def flatten_instances(spec):
    """Expand the assembly tree from the root and grade every node.

    Returns (records, findings, visited_assemblies). A record carries the node
    path, its depth, and the model type or sub-assembly it names.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("catalogue", "assemblies", "root"):
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    catalogue = spec["catalogue"]
    assemblies = spec["assemblies"]
    if not isinstance(catalogue, dict):
        raise ValueError("spec['catalogue'] must be a mapping")
    if not isinstance(assemblies, dict) or not assemblies:
        raise ValueError("spec['assemblies'] must be a non-empty mapping")
    max_depth = spec.get("max_depth", 8)
    if not isinstance(max_depth, int) or isinstance(max_depth, bool) or max_depth < 1:
        raise ValueError("max_depth must be a positive integer")
    root = spec["root"]
    if root not in assemblies:
        raise ValueError("root assembly %r is not declared" % (root,))
    records = []
    findings = []
    visited = {root}
    seen_paths = {}

    def expand(assembly_name, entries, prefix, depth, stack):
        siblings = {}
        for position, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ValueError(
                    "node %d of assembly %r must be a mapping" % (position, assembly_name)
                )
            try:
                name = validate_instance_name(entry.get("name"))
            except AssemblyError as exc:
                findings.append("%s[%d]: %s" % (assembly_name, position, exc))
                continue
            if name in siblings:
                findings.append(
                    "%s: name %r is already used by a sibling at position %d"
                    % (assembly_name, name, siblings[name])
                )
                continue
            siblings[name] = position
            path = instance_path(prefix, name)
            if path in seen_paths:
                findings.append("%s: instance path %r is declared twice" % (assembly_name, path))
                continue
            has_type = isinstance(entry.get("type"), str)
            has_assembly = isinstance(entry.get("assembly"), str)
            if has_type and has_assembly:
                findings.append(
                    "%s: node %r names both a model type and a sub-assembly" % (path, name)
                )
                continue
            if not has_type and not has_assembly:
                findings.append(
                    "%s: node %r names neither a model type nor a sub-assembly" % (path, name)
                )
                continue
            if depth > max_depth:
                findings.append(
                    "%s: nesting depth %d exceeds the declared maximum %d"
                    % (path, depth, max_depth)
                )
                continue
            children = entry.get("instances")
            if children is not None and not isinstance(children, (list, tuple)):
                raise ValueError("children of node %r must be a sequence" % path)
            seen_paths[path] = assembly_name
            if has_type:
                type_name = entry["type"]
                if type_name not in catalogue:
                    findings.append(
                        "%s: model type %r is not declared in the catalogue" % (path, type_name)
                    )
                    continue
                model = catalogue[type_name]
                if not isinstance(model, dict):
                    raise ValueError("type model %r must be a mapping" % type_name)
                if model.get("abstract"):
                    findings.append(
                        "%s: model type %r is abstract and cannot be instantiated"
                        % (path, type_name)
                    )
                    continue
                records.append(
                    {"path": path, "depth": depth, "type": type_name, "assembly": None}
                )
                multiplicity = container_multiplicity(model, "type %r" % type_name)
                count = len(children or ())
                if multiplicity is None:
                    if count:
                        findings.append(
                            "%s: model type %r declares no containment but carries %d child(ren)"
                            % (path, type_name, count)
                        )
                    continue
                lower, upper = multiplicity
                if count < lower:
                    findings.append(
                        "%s: container holds %d child(ren) but at least %d are required"
                        % (path, count, lower)
                    )
                elif upper != UNBOUNDED and count > upper:
                    findings.append(
                        "%s: container holds %d child(ren) but at most %d are admitted"
                        % (path, count, upper)
                    )
                if children:
                    expand(assembly_name, children, path, depth + 1, stack)
                continue
            sub_name = entry["assembly"]
            if children:
                findings.append(
                    "%s: a sub-assembly node takes its children from %r and cannot declare "
                    "its own" % (path, sub_name)
                )
                continue
            if sub_name not in assemblies:
                findings.append("%s: sub-assembly %r is not declared" % (path, sub_name))
                continue
            records.append(
                {"path": path, "depth": depth, "type": None, "assembly": sub_name}
            )
            if sub_name in stack:
                findings.append(
                    "%s: sub-assembly %r is already being expanded; the composition is cyclic"
                    % (path, sub_name)
                )
                continue
            visited.add(sub_name)
            expand(
                sub_name,
                _assembly_entries(assemblies, sub_name),
                path,
                depth + 1,
                stack + (sub_name,),
            )

    expand(root, _assembly_entries(assemblies, root), "", 1, (root,))
    return records, findings, visited


def assess_assembly(spec):
    """Run the clause 5.2.9 assessment over a whole assembly artefact.

    spec keys: 'catalogue', 'assemblies', 'root', optional 'max_depth'.
    """
    records, findings, visited = flatten_instances(spec)
    assemblies = spec["assemblies"]
    cycle_members = detect_sub_assembly_cycles(assemblies)
    unreachable = sorted(set(assemblies) - visited)
    for name in unreachable:
        findings.append(
            "assembly %r is declared but never reached from the root" % name
        )
    depth = max((record["depth"] for record in records), default=0)
    return {
        "instances": records,
        "instance_count": len(records),
        "depth": depth,
        "cycle_members": cycle_members,
        "unreachable_assemblies": unreachable,
        "findings": findings,
        "compliant": not findings,
    }
