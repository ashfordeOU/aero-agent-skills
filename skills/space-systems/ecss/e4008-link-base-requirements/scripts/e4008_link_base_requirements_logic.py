#!/usr/bin/env python3
"""Base requirements on an SMP link base artefact.

Anchor: ECSS-E-ST-40-08C clause 5.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The assembly says which instances exist. The link base says how they
are wired: each link binds a reference declared on one instance to
another instance that provides the interface that reference requires.
It is a registry, not a script -- nothing about a link's meaning
depends on where in the file it appears -- and that is precisely why
its content has to carry every fact needed to resolve it.

The clause's base requirements reduce to five implementable checks:

    1  every link carries an identity, and no identity is registered
       twice in one base
    2  the source endpoint resolves: the instance exists and the named
       reference is declared on that instance's type
    3  the target endpoint resolves: the instance exists and its type
       provides the interface the reference requires, directly or
       through the interface inheritance chain
    4  the number of links bound to a reference sits inside that
       reference's declared multiplicity bounds
    5  the same source reference is not bound to the same target
       twice, and a reference that forbids it is not bound to its own
       instance

Standard library only, offline, deterministic.
"""

from __future__ import annotations

VERDICT_RESOLVABLE = "link-base-resolvable"
VERDICT_REJECTED = "link-base-rejected"

FINDING_LINK_UNNAMED = "link-identity-missing"
FINDING_LINK_DUPLICATE_NAME = "link-identity-duplicate"
FINDING_SOURCE_INSTANCE = "source-instance-unresolved"
FINDING_SOURCE_REFERENCE = "reference-not-on-source-type"
FINDING_TARGET_INSTANCE = "target-instance-unresolved"
FINDING_INTERFACE_NOT_PROVIDED = "target-does-not-provide-interface"
FINDING_MULTIPLICITY_LOW = "reference-below-lower-bound"
FINDING_MULTIPLICITY_HIGH = "reference-above-upper-bound"
FINDING_BINDING_DUPLICATE = "binding-registered-twice"
FINDING_SELF_BINDING = "reference-bound-to-its-own-instance"


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _require_sequence(name, value):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list, got %r" % (name, value))
    return list(value)


def _require_text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _finding(code, detail):
    return {"code": code, "detail": detail}


def interface_closure(interface, interfaces):
    """Every interface implied by one interface, including itself.

    An interface may extend a base interface, so a type providing the
    derived one also satisfies a reference written against the base.
    A cycle in the inheritance chain is a defect in the catalogue and
    raises rather than looping.
    """
    _require_text("interface", interface)
    _require_mapping("interfaces", interfaces)
    seen = []
    current = interface
    while current is not None:
        if current in seen:
            raise ValueError(
                "interface inheritance cycle through %r" % (current,)
            )
        seen.append(current)
        spec = interfaces.get(current)
        if spec is None:
            break
        _require_mapping("interface %s" % current, spec)
        current = spec.get("base")
        if current is not None:
            _require_text("interface %s base" % seen[-1], current)
    return set(seen)


def provided_interfaces(type_name, types, interfaces):
    """Every interface a type satisfies, closed over inheritance."""
    _require_mapping("types", types)
    spec = types.get(type_name)
    if not isinstance(spec, dict):
        raise ValueError("type %r is not declared" % (type_name,))
    provided = set()
    for entry in _require_sequence(
        "type %s provides" % type_name, spec.get("provides", [])
    ):
        provided |= interface_closure(_require_text("provided interface", entry), interfaces)
    return provided


def validate_model(instances, types, interfaces):
    """Check the assembly view a link base is resolved against."""
    _require_mapping("instances", instances)
    _require_mapping("types", types)
    _require_mapping("interfaces", interfaces)
    if not instances:
        raise ValueError("a link base cannot be resolved against an empty assembly")
    for path, entry in instances.items():
        _require_text("instance path", path)
        _require_mapping("instance %s" % path, entry)
        type_name = _require_text("instance %s type" % path, entry.get("type"))
        if type_name not in types:
            raise ValueError(
                "instance %s names a type %r the catalogue does not declare"
                % (path, type_name)
            )
    for type_name, spec in types.items():
        _require_mapping("type %s" % type_name, spec)
        references = _require_mapping(
            "type %s references" % type_name, spec.get("references", {})
        )
        for reference_name, reference in references.items():
            _require_text("reference name", reference_name)
            _require_mapping("reference %s" % reference_name, reference)
            _require_text(
                "reference %s.%s interface" % (type_name, reference_name),
                reference.get("interface"),
            )
            lower = reference.get("lower", 0)
            upper = reference.get("upper")
            if not isinstance(lower, int) or isinstance(lower, bool) or lower < 0:
                raise ValueError(
                    "reference %s.%s lower bound must be a non-negative integer"
                    % (type_name, reference_name)
                )
            if upper is not None:
                if not isinstance(upper, int) or isinstance(upper, bool):
                    raise ValueError(
                        "reference %s.%s upper bound must be an integer or None"
                        % (type_name, reference_name)
                    )
                if upper < lower:
                    raise ValueError(
                        "reference %s.%s upper bound is below its lower bound"
                        % (type_name, reference_name)
                    )
        # provided interfaces are closed here so a cycle surfaces early
        provided_interfaces(type_name, types, interfaces)
    return True


def reference_spec(instance_path, reference_name, instances, types):
    """The reference declaration a link's source names, or None."""
    entry = instances.get(instance_path)
    if not isinstance(entry, dict):
        return None
    spec = types.get(entry.get("type"))
    if not isinstance(spec, dict):
        return None
    reference = spec.get("references", {}).get(reference_name)
    return reference if isinstance(reference, dict) else None


def count_bindings(links):
    """Links registered against each (instance path, reference) pair."""
    counts = {}
    for link in _require_sequence("links", links):
        _require_mapping("link", link)
        source = link.get("source")
        reference = link.get("reference")
        if isinstance(source, str) and isinstance(reference, str):
            key = (source.strip(), reference.strip())
            counts[key] = counts.get(key, 0) + 1
    return counts


def evaluate_link_base(links, instances, types, interfaces):
    """Full clause 5.3 base check on a link base, with a verdict."""
    validate_model(instances, types, interfaces)
    entries = _require_sequence("links", links)

    findings = []
    seen_names = set()
    seen_bindings = set()
    resolved = []

    for index, raw in enumerate(entries):
        _require_mapping("link", raw)
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            findings.append(_finding(FINDING_LINK_UNNAMED, "link at position %d" % index))
            name = None
        else:
            name = name.strip()
            if name in seen_names:
                findings.append(_finding(FINDING_LINK_DUPLICATE_NAME, name))
            seen_names.add(name)
        label = name or "position %d" % index

        source = _require_text("link %s source" % label, raw.get("source"))
        reference_name = _require_text("link %s reference" % label, raw.get("reference"))
        target = _require_text("link %s target" % label, raw.get("target"))

        if source not in instances:
            findings.append(_finding(FINDING_SOURCE_INSTANCE, "%s -> %s" % (label, source)))
            continue
        reference = reference_spec(source, reference_name, instances, types)
        if reference is None:
            findings.append(
                _finding(
                    FINDING_SOURCE_REFERENCE, "%s -> %s.%s" % (label, source, reference_name)
                )
            )
            continue
        if target not in instances:
            findings.append(_finding(FINDING_TARGET_INSTANCE, "%s -> %s" % (label, target)))
            continue

        required = reference["interface"]
        provided = provided_interfaces(instances[target]["type"], types, interfaces)
        if required not in provided:
            findings.append(
                _finding(
                    FINDING_INTERFACE_NOT_PROVIDED,
                    "%s: %s does not provide %s" % (label, target, required),
                )
            )
            continue

        if target == source and not reference.get("allow_self", False):
            findings.append(
                _finding(FINDING_SELF_BINDING, "%s: %s.%s" % (label, source, reference_name))
            )
            continue

        binding = (source, reference_name, target)
        if binding in seen_bindings:
            findings.append(
                _finding(
                    FINDING_BINDING_DUPLICATE,
                    "%s: %s.%s -> %s" % (label, source, reference_name, target),
                )
            )
            continue
        seen_bindings.add(binding)
        resolved.append(
            {
                "name": name,
                "source": source,
                "reference": reference_name,
                "target": target,
                "interface": required,
            }
        )

    counts = {}
    for entry in resolved:
        key = (entry["source"], entry["reference"])
        counts[key] = counts.get(key, 0) + 1

    for path in sorted(instances):
        spec = types[instances[path]["type"]]
        for reference_name in sorted(spec.get("references", {})):
            reference = spec["references"][reference_name]
            count = counts.get((path, reference_name), 0)
            lower = reference.get("lower", 0)
            upper = reference.get("upper")
            if count < lower:
                findings.append(
                    _finding(
                        FINDING_MULTIPLICITY_LOW,
                        "%s.%s has %d of at least %d" % (path, reference_name, count, lower),
                    )
                )
            if upper is not None and count > upper:
                findings.append(
                    _finding(
                        FINDING_MULTIPLICITY_HIGH,
                        "%s.%s has %d of at most %d" % (path, reference_name, count, upper),
                    )
                )

    return {
        "verdict": VERDICT_RESOLVABLE if not findings else VERDICT_REJECTED,
        "resolvable": not findings,
        "resolved_links": resolved,
        "resolved_count": len(resolved),
        "binding_counts": counts,
        "findings": findings,
        "finding_codes": sorted({entry["code"] for entry in findings}),
    }
