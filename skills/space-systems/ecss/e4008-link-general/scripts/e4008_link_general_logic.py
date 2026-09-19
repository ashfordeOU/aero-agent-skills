"""General rules common to every link of an SMP Level-2 assembly artefact.

Anchor: ECSS-E-ST-40-08C clause 5.2.7.1 (link general). Paraphrased into an
implementable procedure; no standard text is reproduced.

What this module decides
------------------------
An assembly connects the instances it has created with links. Three kinds exist
-- interface, event and field -- and each kind adds its own typing rules, but
six checks apply to all of them before any kind-specific rule is reached:

1. every link carries a name that is a valid identifier;
2. link names are unique within the assembly;
3. the declared kind is one of the three the artefact defines;
4. the source endpoint resolves to an element of an instance declared in this
   assembly, by longest declared-path match, with an element left over;
5. the target endpoint resolves the same way, so no endpoint dangles or reaches
   outside the scope of the assembly;
6. the same kind, source and target are not declared twice, and a link does not
   join an instance to itself unless the assembly explicitly permits it.

Malformed input (a link that is not a mapping, an instance list that is not a
sequence) raises. Clause non-conformances are collected as findings so a whole
link set is graded in one pass.
"""

import re

__all__ = [
    "LINK_KINDS",
    "LinkError",
    "assess_link_set",
    "endpoint_signature",
    "instance_scope",
    "link_signature",
    "normalize_path",
    "resolve_endpoint",
    "validate_identifier",
]

# The three link kinds an assembly artefact can declare. A kind outside this set
# cannot be graded by any downstream typing rule, so it is refused here.
LINK_KINDS = ("interface", "event", "field")

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class LinkError(ValueError):
    """A link that the general rules of clause 5.2.7.1 do not admit."""


def validate_identifier(name, what="name"):
    """Return the identifier if it is a valid single path segment."""
    if not isinstance(name, str):
        raise ValueError("%s must be a string" % what)
    if _IDENTIFIER.match(name) is None:
        raise LinkError("%s %r is not a valid identifier" % (what, name))
    return name


def normalize_path(path, what="path"):
    """Return the path as a tuple of validated segments."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("%s must be a non-empty string" % what)
    segments = path.strip().split(".")
    for segment in segments:
        validate_identifier(segment, "%s segment" % what)
    return tuple(segments)


def instance_scope(instances):
    """Return the set of declared instance paths, as tuples of segments."""
    if not isinstance(instances, (list, tuple)) or not instances:
        raise ValueError("instances must be a non-empty sequence of instance paths")
    scope = set()
    for item in instances:
        path = normalize_path(item, "instance path")
        if path in scope:
            raise ValueError("instance path %r is declared twice" % (".".join(path),))
        scope.add(path)
    return scope


def resolve_endpoint(scope, endpoint):
    """Resolve an endpoint path onto (instance path, element name).

    The instance is the longest declared path that prefixes the endpoint; what
    remains is the element the link attaches to. An endpoint with no declared
    prefix dangles; one that exactly equals an instance names no element.
    """
    if not isinstance(scope, (set, frozenset)):
        raise ValueError("scope must be a set of instance path tuples")
    path = normalize_path(endpoint, "endpoint")
    best = None
    for candidate in scope:
        if len(candidate) < len(path) and path[: len(candidate)] == candidate:
            if best is None or len(candidate) > len(best):
                best = candidate
    if best is None:
        if path in scope:
            raise LinkError(
                "endpoint %r names an instance but no element on it" % (".".join(path),)
            )
        raise LinkError(
            "endpoint %r does not resolve to an instance declared in this assembly"
            % (".".join(path),)
        )
    remainder = path[len(best):]
    return {"instance": ".".join(best), "element": ".".join(remainder)}


def endpoint_signature(resolved):
    """Return the comparable text form of a resolved endpoint."""
    if not isinstance(resolved, dict) or "instance" not in resolved or "element" not in resolved:
        raise ValueError("resolved endpoint must carry 'instance' and 'element'")
    return "%s.%s" % (resolved["instance"], resolved["element"])


def link_signature(kind, source, target):
    """Return the duplicate-detection signature of a resolved link."""
    if kind not in LINK_KINDS:
        raise LinkError("link kind %r is not one of the declared kinds" % (kind,))
    return (kind, endpoint_signature(source), endpoint_signature(target))


def assess_link_set(spec):
    """Grade a whole link set against the six general checks of clause 5.2.7.1.

    spec keys: 'instances' (declared instance paths), 'links' (mappings with
    'name', 'kind', 'source', 'target'), optional 'allow_self_links'.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "instances" not in spec or "links" not in spec:
        raise ValueError("spec must carry 'instances' and 'links'")
    links = spec["links"]
    if not isinstance(links, (list, tuple)):
        raise ValueError("spec['links'] must be a sequence")
    allow_self = bool(spec.get("allow_self_links", False))
    scope = instance_scope(spec["instances"])
    accepted = []
    findings = []
    names = {}
    signatures = {}
    for position, link in enumerate(links):
        if not isinstance(link, dict):
            raise ValueError("link at position %d must be a mapping" % position)
        for key in ("name", "kind", "source", "target"):
            if key not in link:
                raise ValueError("link at position %d is missing %r" % (position, key))
        label = link["name"] if isinstance(link["name"], str) else "<position %d>" % position
        try:
            name = validate_identifier(link["name"], "link name")
        except LinkError as exc:
            findings.append(str(exc))
            continue
        if name in names:
            findings.append(
                "link name %r is already used at position %d" % (name, names[name])
            )
            continue
        kind = link["kind"]
        if kind not in LINK_KINDS:
            findings.append(
                "%s: kind %r is not one of %s" % (label, kind, ", ".join(LINK_KINDS))
            )
            continue
        try:
            source = resolve_endpoint(scope, link["source"])
            target = resolve_endpoint(scope, link["target"])
        except LinkError as exc:
            findings.append("%s: %s" % (label, exc))
            continue
        if source["instance"] == target["instance"] and not allow_self:
            findings.append(
                "%s: both endpoints sit on instance %r; a self-link is not admitted"
                % (label, source["instance"])
            )
            continue
        signature = link_signature(kind, source, target)
        if signature in signatures:
            findings.append(
                "%s: duplicates link %r (same kind, source and target)"
                % (label, signatures[signature])
            )
            continue
        names[name] = position
        signatures[signature] = name
        accepted.append(
            {"name": name, "kind": kind, "source": source, "target": target}
        )
    per_kind = {kind: 0 for kind in LINK_KINDS}
    for link in accepted:
        per_kind[link["kind"]] += 1
    return {
        "accepted": accepted,
        "per_kind": per_kind,
        "findings": findings,
        "compliant": not findings,
    }
