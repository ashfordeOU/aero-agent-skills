#!/usr/bin/env python3
"""Requirements on an assembly Instance in a simulation assembly.

Anchor: ECSS-E-ST-40-08C clause 4.2.2.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An assembly Instance is a composite: an instance that contains other
instances. The clause carries two normative items, and both are about
containment rather than about the composite's own fields:

    1 the assembly declares the child instances it contains, each with
      a legal name that is unique inside the containment, and the
      containment nests without closing on itself
    2 every link the assembly declares resolves at both ends, either to
      a child it contains or to an interface it explicitly exports

The second item is where composites actually fail. A link whose
endpoint names a child that was renamed, or that reaches a sibling
outside the assembly without an export to carry it, leaves the composite
half wired: it builds, and the signal is never delivered.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import re

NORMATIVE_ITEMS = (
    "assembly-declares-its-child-instances",
    "assembly-links-resolve-within-the-containment-or-through-an-export",
)

ASSEMBLY_VERDICTS = ("assembly-instance-compliant", "assembly-instance-non-compliant")

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MAX_IDENTIFIER_LENGTH = 64
PATH_SEPARATOR = "/"
ENDPOINT_SEPARATOR = "."
SELF_OWNER = "self"


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a sequence, got %r" % (name, value))
    return value


def is_legal_identifier(name):
    """Whether a name may be used as an instance, port or export identifier."""
    return (
        isinstance(name, str)
        and 0 < len(name) <= MAX_IDENTIFIER_LENGTH
        and IDENTIFIER_PATTERN.match(name) is not None
    )


def validate_identifier(name, label="identifier"):
    """Return the name, or raise when it cannot address anything."""
    if not is_legal_identifier(name):
        raise ValueError(
            "%s %r is not a legal identifier (letter or underscore first, then "
            "letters, digits or underscores, at most %d characters)"
            % (label, name, MAX_IDENTIFIER_LENGTH)
        )
    return name


def child_path(parent_path, name):
    """Hierarchy path a child occupies under its containing assembly."""
    validate_identifier(name, "child name")
    if parent_path in (None, "", PATH_SEPARATOR):
        return PATH_SEPARATOR + name
    if not isinstance(parent_path, str) or not parent_path.startswith(PATH_SEPARATOR):
        raise ValueError(
            "parent_path must be an absolute path starting with %r, got %r"
            % (PATH_SEPARATOR, parent_path)
        )
    return parent_path.rstrip(PATH_SEPARATOR) + PATH_SEPARATOR + name


def parse_endpoint(endpoint):
    """Split an owner.port link endpoint into its two identifiers."""
    if not isinstance(endpoint, str) or ENDPOINT_SEPARATOR not in endpoint:
        raise ValueError(
            "link endpoint %r must be written owner%sport" % (endpoint, ENDPOINT_SEPARATOR)
        )
    owner, _sep, port = endpoint.partition(ENDPOINT_SEPARATOR)
    if ENDPOINT_SEPARATOR in port:
        raise ValueError(
            "link endpoint %r reaches through more than one level; a composite "
            "links its own children only" % endpoint
        )
    validate_identifier(owner, "link endpoint owner")
    validate_identifier(port, "link endpoint port")
    return (owner, port)


def flatten_containment(assembly, parent_path=None, definition_stack=()):
    """Walk the containment tree, refusing duplicates and cycles."""
    _require_mapping("assembly", assembly)
    name = validate_identifier(assembly.get("name"), "assembly name")
    definition = assembly.get("definition")
    if definition is not None and not is_legal_identifier(definition):
        raise ValueError(
            "assembly %r declares definition %r, which is not a legal identifier"
            % (name, definition)
        )
    here = child_path(
        parent_path if parent_path is not None else assembly.get("parent_path"), name
    )
    if definition is not None and definition in definition_stack:
        raise ValueError(
            "containment cycle at %s: definition %r already contains itself via %s"
            % (here, definition, " -> ".join(definition_stack))
        )
    next_stack = definition_stack + ((definition,) if definition is not None else ())
    nodes = {here: assembly}
    children = _require_sequence("children", assembly.get("children", []))
    seen = set()
    for child in children:
        _require_mapping("child instance", child)
        child_name = validate_identifier(child.get("name"), "child name")
        if child_name in seen:
            raise ValueError(
                "assembly %s declares the child name %r twice" % (here, child_name)
            )
        seen.add(child_name)
        nodes.update(flatten_containment(child, here, next_stack))
    return nodes


def direct_child_names(assembly):
    """Names of the instances the assembly contains at its own level."""
    _require_mapping("assembly", assembly)
    children = _require_sequence("children", assembly.get("children", []))
    names = []
    for child in children:
        _require_mapping("child instance", child)
        names.append(validate_identifier(child.get("name"), "child name"))
    return names


def declared_exports(assembly):
    """Interface names the assembly exposes beyond its own containment."""
    _require_mapping("assembly", assembly)
    exports = _require_sequence("exports", assembly.get("exports", []))
    names = []
    for export in exports:
        names.append(validate_identifier(export, "export name"))
    if len(set(names)) != len(names):
        raise ValueError("assembly %r declares an export twice" % assembly.get("name"))
    return names


def resolve_link(link, child_names, exports):
    """Resolve both ends of one link against children and exports."""
    _require_mapping("link", link)
    name = validate_identifier(link.get("name"), "link name")
    children = set(child_names)
    exported = set(exports)
    unresolved = []
    endpoints = {}
    for role in ("source", "target"):
        owner, port = parse_endpoint(link.get(role))
        if owner == SELF_OWNER:
            if port not in exported:
                unresolved.append(
                    "%s %s reaches outside the assembly through %r, which is not "
                    "an exported interface" % (role, link.get(role), port)
                )
            else:
                endpoints[role] = ("export", port)
            continue
        if owner not in children:
            unresolved.append(
                "%s %s names %r, which the assembly does not contain"
                % (role, link.get(role), owner)
            )
            continue
        endpoints[role] = ("child", owner)
    resolved = not unresolved
    return {
        "name": name,
        "endpoints": endpoints,
        "resolved": resolved,
        "findings": unresolved,
    }


def evaluate_assembly_instance(assembly):
    """Grade one assembly Instance against the two items of 4.2.2.3."""
    _require_mapping("assembly", assembly)
    items = []
    findings = []

    containment_error = None
    nodes = {}
    try:
        nodes = flatten_containment(assembly)
    except ValueError as error:
        containment_error = str(error)
    children = []
    if containment_error is None:
        children = direct_child_names(assembly)
        if not children:
            containment_error = (
                "assembly %r declares no child instances; a composite that "
                "contains nothing is not an assembly" % assembly.get("name")
            )
    if containment_error is None:
        items.append({"item": NORMATIVE_ITEMS[0], "satisfied": True, "finding": None})
    else:
        items.append(
            {"item": NORMATIVE_ITEMS[0], "satisfied": False, "finding": containment_error}
        )
        findings.append(containment_error)

    exports = declared_exports(assembly) if containment_error is None else []
    links = _require_sequence("links", assembly.get("links", []))
    resolved_links = []
    link_findings = []
    seen_link_names = set()
    for link in links:
        result = resolve_link(link, children, exports)
        if result["name"] in seen_link_names:
            raise ValueError("assembly declares the link name %r twice" % result["name"])
        seen_link_names.add(result["name"])
        resolved_links.append(result)
        link_findings.extend("%s: %s" % (result["name"], n) for n in result["findings"])
    if link_findings:
        items.append(
            {
                "item": NORMATIVE_ITEMS[1],
                "satisfied": False,
                "finding": "; ".join(link_findings),
            }
        )
        findings.extend(link_findings)
    else:
        items.append({"item": NORMATIVE_ITEMS[1], "satisfied": True, "finding": None})

    unlinked = sorted(
        set(children)
        - {
            owner
            for result in resolved_links
            for kind, owner in result["endpoints"].values()
            if kind == "child"
        }
    )
    satisfied = sum(1 for entry in items if entry["satisfied"])
    compliant = satisfied == len(NORMATIVE_ITEMS)
    return {
        "name": assembly.get("name"),
        "children": children,
        "contained_paths": sorted(nodes),
        "exports": exports,
        "links": resolved_links,
        "unlinked_children": unlinked,
        "items": items,
        "satisfied": satisfied,
        "required": len(NORMATIVE_ITEMS),
        "compliant": compliant,
        "verdict": "assembly-instance-compliant"
        if compliant
        else "assembly-instance-non-compliant",
        "findings": findings,
    }
