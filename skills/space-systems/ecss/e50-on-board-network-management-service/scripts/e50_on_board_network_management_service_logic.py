"""Management service for an on-board network.

Anchor: ECSS-E-ST-50C clause 5.7.2.4 -- the on-board network management
service. Paraphrased into an implementable procedure; no standard text is
reproduced.

The single normative item is that the network provides a management service
for its own resources. Two independent things decide whether that service
exists for a given resource, and a review that asks only the first passes
designs that cannot be managed at the moment management is needed.

The first is operation coverage: every managed resource is reachable for every
management operation the design owes it -- typically setting its configuration,
reading its state, and commanding it. A resource that can be read but not
commanded is monitored, not managed.

The second is path independence: the management traffic for a resource must
not have to pass through that resource. A router managed only through itself
is manageable exactly while it is working, which is when nobody needs to.

Both are computed over a declared inventory, so the output is a per-resource
verdict, a gap list, and a coverage ratio over the whole network.
"""

__all__ = [
    "MANAGED",
    "PARTIAL",
    "UNREACHABLE",
    "DEFAULT_OPERATIONS",
    "validate_name",
    "validate_operations",
    "normalise_resource",
    "missing_operations",
    "path_faults",
    "assess_resource",
    "assess_management_service",
]

MANAGED = "managed"
PARTIAL = "partial"
UNREACHABLE = "unreachable"

# The operations a managed network resource owes by default. Override the set
# when a programme owes more; never shorten it silently, because a shorter set
# turns a gap into a pass.
DEFAULT_OPERATIONS = ("configure", "monitor", "control")


def validate_name(value, name="name"):
    """Return a non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def validate_operations(value, name="operations"):
    """Return an ordered tuple of distinct operation names."""
    if isinstance(value, str):
        raise ValueError("%s must be a list of names, not a single string" % name)
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list of names, got %r" % (name, type(value).__name__))
    out = []
    for index, item in enumerate(value):
        op = validate_name(item, "%s[%d]" % (name, index))
        if op in out:
            raise ValueError("%s repeats %r" % (name, op))
        out.append(op)
    return tuple(out)


def normalise_resource(resource):
    """Return a validated copy of one declared managed network resource."""
    if not isinstance(resource, dict):
        raise ValueError("resource must be a mapping, got %r" % type(resource).__name__)
    name = validate_name(resource.get("name"), "resource name")
    supported = validate_operations(resource.get("operations", []), "operations")
    hops = validate_operations(resource.get("management_path", []), "management_path")
    return {"name": name, "operations": supported, "management_path": hops}


def missing_operations(resource, required=DEFAULT_OPERATIONS):
    """Return the required operations this resource does not support."""
    resource = normalise_resource(resource)
    required = validate_operations(required, "required")
    return tuple(op for op in required if op not in resource["operations"])


def path_faults(resource, known_names):
    """Return the reasons a resource's management path cannot be relied on.

    Two faults matter. A path that runs through the resource itself is a
    self-dependency: it works only while the resource does. A path hop that is
    not itself a declared resource is an unmanaged dependency, so nothing in
    the inventory says who configures it or reports its state.
    """
    resource = normalise_resource(resource)
    if not isinstance(known_names, (set, frozenset, list, tuple)):
        raise ValueError("known_names must be a collection of resource names")
    known = set(known_names)
    faults = []
    if resource["name"] in resource["management_path"]:
        faults.append(
            "management path for %s runs through %s itself" % (resource["name"], resource["name"])
        )
    for hop in resource["management_path"]:
        if hop != resource["name"] and hop not in known:
            faults.append(
                "management path for %s depends on %s, which is not a managed resource"
                % (resource["name"], hop)
            )
    return tuple(faults)


def assess_resource(resource, known_names, required=DEFAULT_OPERATIONS):
    """Judge one network resource against the management service it is owed."""
    resource = normalise_resource(resource)
    required = validate_operations(required, "required")
    gaps = missing_operations(resource, required)
    faults = path_faults(resource, known_names)
    supported = len(required) - len(gaps)
    if faults:
        verdict = UNREACHABLE
    elif gaps:
        verdict = PARTIAL
    else:
        verdict = MANAGED
    reasons = list(faults)
    if gaps:
        reasons.append(
            "%s offers no %s operation" % (resource["name"], ", ".join(gaps))
        )
    return {
        "resource": resource["name"],
        "required": list(required),
        "supported": list(resource["operations"]),
        "missing": list(gaps),
        "coverage": (supported / float(len(required))) if required else None,
        "path_faults": list(faults),
        "verdict": verdict,
        "reasons": reasons,
    }


def assess_management_service(resources, required=DEFAULT_OPERATIONS):
    """Assess the management service a declared on-board network inventory offers."""
    if not isinstance(resources, (list, tuple)):
        raise ValueError("resources must be a list")
    if not resources:
        raise ValueError("at least one managed resource must be declared")
    normalised = [normalise_resource(r) for r in resources]
    names = [r["name"] for r in normalised]
    if len(set(names)) != len(names):
        raise ValueError("duplicate resource name in the declared inventory")
    required = validate_operations(required, "required")
    known = set(names)
    per_resource = [assess_resource(r, known, required) for r in normalised]
    unreachable = [r["resource"] for r in per_resource if r["verdict"] == UNREACHABLE]
    partial = [r["resource"] for r in per_resource if r["verdict"] == PARTIAL]
    # Coverage is counted over every resource with a gap, not only the ones
    # whose verdict is partial: a resource with an unreliable path can be
    # missing operations too, and the path fault must not hide them.
    with_gaps = [r["resource"] for r in per_resource if r["missing"]]
    total_required = len(required) * len(normalised)
    total_supported = sum(len(r["required"]) - len(r["missing"]) for r in per_resource)
    findings = []
    if with_gaps:
        findings.append(
            "operation coverage incomplete for %s" % ", ".join(sorted(with_gaps))
        )
    if unreachable:
        findings.append(
            "management path cannot be relied on for %s" % ", ".join(sorted(unreachable))
        )
    return {
        "resources": names,
        "required": list(required),
        "per_resource": per_resource,
        "partial": partial,
        "with_gaps": with_gaps,
        "unreachable": unreachable,
        "coverage": (total_supported / float(total_required)) if total_required else None,
        "coverage_met": not with_gaps,
        "paths_independent": not unreachable,
        "service_provided": not with_gaps and not unreachable,
        "findings": findings,
    }
