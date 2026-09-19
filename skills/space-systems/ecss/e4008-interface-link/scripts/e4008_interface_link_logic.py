"""Interface links of an SMP Level-2 assembly artefact.

Anchor: ECSS-E-ST-40-08C clause 5.2.7.2 (interface link). Paraphrased into an
implementable procedure; no standard text is reproduced.

What this module decides
------------------------
An interface link binds a *reference* declared by a consumer component -- the
interface that component requires in order to work -- to an *interface* that a
provider component publishes. Seven checks decide whether the binding holds:

1. the consumer endpoint names a reference declared by the consumer's type;
2. the provider endpoint names an interface published by the provider's type;
3. the published interface is the required interface type, or derives from it
   through the declared interface hierarchy;
4. the number of bindings into one reference stays within its upper
   multiplicity, where an unbounded upper is written as -1;
5. every reference is bound at least as many times as its lower multiplicity
   requires, so a mandatory reference is never left unresolved;
6. the same provider interface is not bound into the same reference twice;
7. a reference is not satisfied by an interface published by the very instance
   that declares it, unless the assembly explicitly permits self-binding.

Malformed input raises. Clause non-conformances are returned as findings so a
whole assembly of interface links is graded in one pass.
"""

__all__ = [
    "UNBOUNDED",
    "InterfaceLinkError",
    "assess_interface_links",
    "interface_derives_from",
    "multiplicity_report",
    "resolve_provided_interface",
    "resolve_reference",
    "validate_multiplicity",
]

# An upper multiplicity written as -1 means the reference accepts any number of
# bindings; any other negative value is a malformed declaration.
UNBOUNDED = -1


class InterfaceLinkError(ValueError):
    """An interface link that clause 5.2.7.2 does not admit."""


def _instance_type(catalogue, instances, path, role):
    """Return the type model of a declared instance."""
    if not isinstance(instances, dict) or not instances:
        raise ValueError("instances must be a non-empty mapping of path to type name")
    if not isinstance(catalogue, dict) or not catalogue:
        raise ValueError("catalogue must be a non-empty mapping of type name to type model")
    if not isinstance(path, str) or not path:
        raise ValueError("%s instance path must be a non-empty string" % role)
    if path not in instances:
        raise InterfaceLinkError("%s %r is not an instance of this assembly" % (role, path))
    type_name = instances[path]
    if type_name not in catalogue:
        raise ValueError("instance %r names undeclared type %r" % (path, type_name))
    model = catalogue[type_name]
    if not isinstance(model, dict):
        raise ValueError("type model %r must be a mapping" % type_name)
    return type_name, model


def validate_multiplicity(lower, upper, where="reference"):
    """Return the validated (lower, upper) multiplicity pair of a reference."""
    for label, value in (("lower", lower), ("upper", upper)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s %s multiplicity must be an integer" % (where, label))
    if lower < 0:
        raise ValueError("%s lower multiplicity must not be negative" % where)
    if upper < UNBOUNDED:
        raise ValueError("%s upper multiplicity must be -1 or a non-negative integer" % where)
    if upper != UNBOUNDED and upper < lower:
        raise ValueError("%s upper multiplicity is below its lower multiplicity" % where)
    return (lower, upper)


def resolve_reference(catalogue, instances, consumer_path, reference_name):
    """Return the declared reference of a consumer instance."""
    type_name, model = _instance_type(catalogue, instances, consumer_path, "consumer")
    references = model.get("references")
    if not isinstance(references, dict):
        references = {}
    if reference_name not in references:
        raise InterfaceLinkError(
            "type %r declares no reference %r" % (type_name, reference_name)
        )
    declared = references[reference_name]
    if not isinstance(declared, dict) or "interface" not in declared:
        raise ValueError("reference %r must declare an interface type" % reference_name)
    lower, upper = validate_multiplicity(
        declared.get("lower", 1), declared.get("upper", 1),
        "reference %r" % reference_name,
    )
    return {
        "instance": consumer_path,
        "type": type_name,
        "name": reference_name,
        "interface": declared["interface"],
        "lower": lower,
        "upper": upper,
    }


def resolve_provided_interface(catalogue, instances, provider_path, interface_name):
    """Return the interface a provider instance publishes under a given name."""
    type_name, model = _instance_type(catalogue, instances, provider_path, "provider")
    provided = model.get("interfaces")
    if not isinstance(provided, dict):
        provided = {}
    if interface_name not in provided:
        raise InterfaceLinkError(
            "type %r publishes no interface named %r" % (type_name, interface_name)
        )
    interface_type = provided[interface_name]
    if not isinstance(interface_type, str) or not interface_type:
        raise ValueError("published interface %r must name an interface type" % interface_name)
    return {
        "instance": provider_path,
        "type": type_name,
        "name": interface_name,
        "interface": interface_type,
    }


def interface_derives_from(hierarchy, derived, base):
    """Return True when 'derived' is 'base' or inherits from it."""
    if not isinstance(hierarchy, dict):
        raise ValueError("hierarchy must be a mapping of interface to its base")
    if not isinstance(derived, str) or not isinstance(base, str):
        raise ValueError("interface names must be strings")
    seen = set()
    current = derived
    while True:
        if current == base:
            return True
        if current in seen:
            raise ValueError("interface hierarchy contains a cycle at %r" % current)
        seen.add(current)
        if current not in hierarchy:
            return False
        parent = hierarchy[current]
        if not isinstance(parent, str) or not parent:
            raise ValueError("interface %r declares a malformed base" % current)
        current = parent


def multiplicity_report(reference, bound_count):
    """Return the multiplicity verdict for one reference."""
    if not isinstance(reference, dict) or "lower" not in reference or "upper" not in reference:
        raise ValueError("reference must carry its multiplicity")
    if not isinstance(bound_count, int) or isinstance(bound_count, bool) or bound_count < 0:
        raise ValueError("bound_count must be a non-negative integer")
    upper = reference["upper"]
    over = upper != UNBOUNDED and bound_count > upper
    under = bound_count < reference["lower"]
    return {
        "reference": "%s.%s" % (reference["instance"], reference["name"]),
        "bound": bound_count,
        "lower": reference["lower"],
        "upper": upper,
        "satisfied": not over and not under,
        "over_bound": over,
        "under_bound": under,
    }


def assess_interface_links(spec):
    """Grade a whole interface-link set against the seven clause 5.2.7.2 checks.

    spec keys: 'catalogue', 'instances', 'links' (mappings with 'name',
    'consumer', 'reference', 'provider', 'interface'), optional
    'interface_hierarchy' and 'allow_self_binding'.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("catalogue", "instances", "links"):
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    links = spec["links"]
    if not isinstance(links, (list, tuple)):
        raise ValueError("spec['links'] must be a sequence")
    hierarchy = spec.get("interface_hierarchy") or {}
    allow_self = bool(spec.get("allow_self_binding", False))
    catalogue = spec["catalogue"]
    instances = spec["instances"]
    findings = []
    accepted = []
    bindings = {}
    for position, link in enumerate(links):
        if not isinstance(link, dict):
            raise ValueError("link at position %d must be a mapping" % position)
        for key in ("name", "consumer", "reference", "provider", "interface"):
            if key not in link:
                raise ValueError("link at position %d is missing %r" % (position, key))
        label = link["name"]
        try:
            reference = resolve_reference(
                catalogue, instances, link["consumer"], link["reference"]
            )
            provided = resolve_provided_interface(
                catalogue, instances, link["provider"], link["interface"]
            )
        except InterfaceLinkError as exc:
            findings.append("%s: %s" % (label, exc))
            continue
        if not interface_derives_from(hierarchy, provided["interface"], reference["interface"]):
            findings.append(
                "%s: published interface %r does not satisfy required interface %r"
                % (label, provided["interface"], reference["interface"])
            )
            continue
        if reference["instance"] == provided["instance"] and not allow_self:
            findings.append(
                "%s: reference and published interface sit on instance %r; "
                "self-binding is not admitted" % (label, reference["instance"])
            )
            continue
        key = (reference["instance"], reference["name"])
        source = "%s.%s" % (provided["instance"], provided["name"])
        entry = bindings.setdefault(key, {"reference": reference, "providers": []})
        if source in entry["providers"]:
            findings.append(
                "%s: interface %r is already bound into reference %s.%s"
                % (label, source, key[0], key[1])
            )
            continue
        entry["providers"].append(source)
        accepted.append(
            {"name": label, "reference": reference, "provider": provided}
        )
    reports = []
    for key in sorted(bindings):
        entry = bindings[key]
        report = multiplicity_report(entry["reference"], len(entry["providers"]))
        report["providers"] = list(entry["providers"])
        reports.append(report)
        if report["over_bound"]:
            findings.append(
                "reference %s takes at most %d binding(s) but %d were declared"
                % (report["reference"], report["upper"], report["bound"])
            )
    for report in _unbound_mandatory_references(catalogue, instances, bindings):
        reports.append(report)
        findings.append(
            "reference %s is mandatory (lower %d) but no interface link binds it"
            % (report["reference"], report["lower"])
        )
    return {
        "accepted": accepted,
        "reference_reports": reports,
        "findings": findings,
        "compliant": not findings,
    }


def _unbound_mandatory_references(catalogue, instances, bindings):
    """Yield a report for every mandatory reference no link reached."""
    for path in sorted(instances):
        type_name = instances[path]
        model = catalogue.get(type_name)
        if not isinstance(model, dict):
            raise ValueError("instance %r names undeclared type %r" % (path, type_name))
        references = model.get("references")
        if not isinstance(references, dict):
            continue
        for name in sorted(references):
            if (path, name) in bindings:
                continue
            reference = resolve_reference(catalogue, instances, path, name)
            if reference["lower"] > 0:
                yield multiplicity_report(reference, 0)
