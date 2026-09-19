"""Independence of the nominal and redundant actuator firing paths.

Anchor: ECSS-E-ST-20-21C clause 5.3.2 (paraphrased into an
implementable procedure; no standard text is reproduced).

The nominal and the redundant firing path have to stay independent all
the way to the actuator, so that no single failure can take actuation
away. Independence fails in two different ways and only one of them is
visible on a block diagram. The obvious way is a shared element: one
box that both paths pass through. The quiet way is a shared resource:
two separate boxes that nonetheless sit in the same harness bundle,
behind the same connector shell, on the same secondary bus or inside
the same routing zone. A connector crushed on integration takes out
both paths just as completely as a failed switch would.

Procedure implemented here:

1. Validate each path as an ordered chain of elements from the energy
   source to the actuator interface, refusing an element declared
   twice inside one path and refusing a path that does not carry the
   element kinds a firing path needs to be a firing path.
2. Intersect the two element sets and report every element both paths
   pass through.
3. Intersect the resources the two paths reference and report every
   resource both depend on, naming the element on each side that
   brings it in. This is the finding a block diagram cannot show.
4. Collect the common cause failures: the union of those two
   intersections. Each one is a single failure that loses actuation
   altogether, which is exactly what the clause forbids.
5. Report what survives the loss of any named element, and close with
   an independence verdict.

Stdlib only, offline, deterministic.
"""

PATH_NOMINAL = "nominal-firing-path"
PATH_REDUNDANT = "redundant-firing-path"
PATH_NAMES = (PATH_NOMINAL, PATH_REDUNDANT)

ELEMENT_KINDS = (
    "energy-source",
    "arming-switch",
    "firing-switch",
    "current-limiter",
    "harness",
    "connector",
    "actuator-interface",
)

# A firing path that does not carry all of these is not a complete
# path: it has no energy, no way to break the circuit, no route to the
# device, or no termination at it.
REQUIRED_ELEMENT_KINDS = (
    "energy-source",
    "firing-switch",
    "harness",
    "actuator-interface",
)

CAUSE_SHARED_ELEMENT = "shared-element"
CAUSE_SHARED_RESOURCE = "shared-resource"

FINDING_PATH_INCOMPLETE = "firing-path-incomplete"
FINDING_SHARED_ELEMENT = "paths-share-an-element"
FINDING_SHARED_RESOURCE = "paths-share-a-resource"


def _non_empty_text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def validate_element(element):
    """Validate one firing path element and return a normalized copy."""
    if not isinstance(element, dict):
        raise ValueError("element must be a mapping, got %r" % (element,))
    element_id = _non_empty_text("element id", element.get("id"))
    kind = element.get("kind")
    if kind not in ELEMENT_KINDS:
        raise ValueError(
            "element %s has unknown kind %r (expected one of %s)"
            % (element_id, kind, ", ".join(ELEMENT_KINDS))
        )
    resources = element.get("resources", [])
    if not isinstance(resources, (list, tuple)):
        raise ValueError("element %s resources must be a sequence" % element_id)
    normalized_resources = []
    for resource in resources:
        name = _non_empty_text("element %s resource" % element_id, resource)
        if name in normalized_resources:
            raise ValueError(
                "element %s lists resource %s twice" % (element_id, name)
            )
        normalized_resources.append(name)
    return {
        "id": element_id,
        "kind": kind,
        "resources": tuple(sorted(normalized_resources)),
    }


def validate_path(path):
    """Validate one firing path and return a normalized copy."""
    if not isinstance(path, dict):
        raise ValueError("path must be a mapping, got %r" % (path,))
    name = path.get("name")
    if name not in PATH_NAMES:
        raise ValueError(
            "unknown path name %r (expected one of %s)" % (name, ", ".join(PATH_NAMES))
        )
    elements = path.get("elements")
    if not isinstance(elements, (list, tuple)):
        raise ValueError("path %s elements must be a sequence" % name)
    if not elements:
        raise ValueError("path %s carries no element" % name)
    normalized = [validate_element(e) for e in elements]
    seen = set()
    for record in normalized:
        if record["id"] in seen:
            raise ValueError(
                "path %s lists element %s twice" % (name, record["id"])
            )
        seen.add(record["id"])
    return {"name": name, "elements": tuple(normalized)}


def validate_path_pair(nominal, redundant):
    """Validate the two firing paths and return the normalized pair."""
    first = validate_path(nominal)
    second = validate_path(redundant)
    if first["name"] == second["name"]:
        raise ValueError(
            "both paths are declared as %s; one nominal and one redundant path "
            "are expected" % first["name"]
        )
    ordered = sorted((first, second), key=lambda p: PATH_NAMES.index(p["name"]))
    return tuple(ordered)


def path_element_ids(path):
    """Element identifiers of one path."""
    return tuple(e["id"] for e in validate_path(path)["elements"])


def path_kinds(path):
    """Element kinds present in one path."""
    return tuple(sorted({e["kind"] for e in validate_path(path)["elements"]}))


def missing_element_kinds(path):
    """Element kinds a complete firing path needs and this one lacks."""
    present = set(path_kinds(path))
    return tuple(k for k in REQUIRED_ELEMENT_KINDS if k not in present)


def path_resources(path):
    """Resources one path depends on, in sorted order."""
    resources = set()
    for element in validate_path(path)["elements"]:
        resources.update(element["resources"])
    return tuple(sorted(resources))


def shared_elements(nominal, redundant):
    """Element identifiers both paths pass through."""
    first, second = validate_path_pair(nominal, redundant)
    return tuple(
        sorted(set(path_element_ids(first)) & set(path_element_ids(second)))
    )


def shared_resources(nominal, redundant):
    """Resources both paths depend on, with the elements that bring them in."""
    first, second = validate_path_pair(nominal, redundant)
    common = set(path_resources(first)) & set(path_resources(second))
    report = {}
    for resource in sorted(common):
        report[resource] = {
            first["name"]: tuple(
                sorted(e["id"] for e in first["elements"] if resource in e["resources"])
            ),
            second["name"]: tuple(
                sorted(e["id"] for e in second["elements"] if resource in e["resources"])
            ),
        }
    return report


def common_cause_failures(nominal, redundant):
    """Single failures that take both firing paths away."""
    first, second = validate_path_pair(nominal, redundant)
    causes = []
    for element_id in shared_elements(first, second):
        causes.append({"cause": CAUSE_SHARED_ELEMENT, "subject": element_id})
    for resource, holders in sorted(shared_resources(first, second).items()):
        causes.append(
            {
                "cause": CAUSE_SHARED_RESOURCE,
                "subject": resource,
                "holders": holders,
            }
        )
    return sorted(causes, key=lambda c: (c["cause"], c["subject"]))


def paths_are_independent(nominal, redundant):
    """True when no single failure takes both firing paths away."""
    return not common_cause_failures(nominal, redundant)


def paths_surviving_element_loss(nominal, redundant, element_id):
    """Path names that still reach the actuator once one element is lost."""
    first, second = validate_path_pair(nominal, redundant)
    lost = _non_empty_text("element_id", element_id)
    known = set(path_element_ids(first)) | set(path_element_ids(second))
    if lost not in known:
        raise ValueError("element %s is in neither firing path" % lost)
    return tuple(
        path["name"]
        for path in (first, second)
        if lost not in path_element_ids(path)
    )


def paths_surviving_resource_loss(nominal, redundant, resource):
    """Path names that still reach the actuator once one resource is lost."""
    first, second = validate_path_pair(nominal, redundant)
    lost = _non_empty_text("resource", resource)
    known = set(path_resources(first)) | set(path_resources(second))
    if lost not in known:
        raise ValueError("resource %s is used by neither firing path" % lost)
    return tuple(
        path["name"]
        for path in (first, second)
        if lost not in path_resources(path)
    )


def independence_findings(nominal, redundant):
    """Findings against the firing path independence requirement."""
    first, second = validate_path_pair(nominal, redundant)
    findings = []
    for path in (first, second):
        for kind in missing_element_kinds(path):
            findings.append(
                {
                    "code": FINDING_PATH_INCOMPLETE,
                    "subject": "%s/%s" % (path["name"], kind),
                    "detail": "%s carries no %s element" % (path["name"], kind),
                }
            )
    for element_id in shared_elements(first, second):
        findings.append(
            {
                "code": FINDING_SHARED_ELEMENT,
                "subject": element_id,
                "detail": "both firing paths pass through %s" % element_id,
            }
        )
    for resource, holders in sorted(shared_resources(first, second).items()):
        findings.append(
            {
                "code": FINDING_SHARED_RESOURCE,
                "subject": resource,
                "detail": "both firing paths depend on %s (%s via %s, %s via %s)"
                % (
                    resource,
                    first["name"],
                    ", ".join(holders[first["name"]]),
                    second["name"],
                    ", ".join(holders[second["name"]]),
                ),
            }
        )
    return sorted(findings, key=lambda f: (f["code"], f["subject"]))


def assess_actuator_path_independence(nominal, redundant):
    """Grade the independence of a declared pair of firing paths."""
    first, second = validate_path_pair(nominal, redundant)
    findings = independence_findings(first, second)
    causes = common_cause_failures(first, second)
    return {
        "path_names": (first["name"], second["name"]),
        "element_counts": {
            first["name"]: len(first["elements"]),
            second["name"]: len(second["elements"]),
        },
        "missing_element_kinds": {
            first["name"]: missing_element_kinds(first),
            second["name"]: missing_element_kinds(second),
        },
        "shared_elements": shared_elements(first, second),
        "shared_resources": shared_resources(first, second),
        "common_cause_failures": causes,
        "common_cause_count": len(causes),
        "independent": paths_are_independent(first, second),
        "findings": findings,
        "finding_codes": sorted({f["code"] for f in findings}),
        "compliant": not findings,
    }
