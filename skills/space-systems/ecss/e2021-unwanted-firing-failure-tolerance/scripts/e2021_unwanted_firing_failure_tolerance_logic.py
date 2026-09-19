"""Single-failure tolerance against unwanted firing of an actuator.

Anchor: ECSS-E-ST-20-21C clause 5.1.2 (reliability of the general functional
interface: no single failure may cause an actuator to fire when it was not
commanded). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Read the inhibit inventory of an actuation chain: which barrier each inhibit
   belongs to, and which shared resources it depends on.
2. Collapse inhibits that depend on a common resource into one effective
   independent inhibit, because a resource failure removes all of them at once.
3. Scan every candidate single failure -- each declared failure mode and each
   shared resource on its own -- and report any that leaves no inhibit standing.
4. Convert the worst stray current a single failure can drive into the initiator
   into a margin in decibels against the no-fire current, and grade it.
5. Return a verdict that is true only when every barrier is populated, two
   effective independent inhibits survive, no single failure clears the chain,
   and the stray-current margin is met.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE_DB",
    "BARRIERS",
    "MIN_INDEPENDENT_INHIBITS",
    "validate_positive",
    "normalize_barrier",
    "normalize_inhibits",
    "resource_map",
    "independent_groups",
    "independent_inhibit_count",
    "barrier_coverage",
    "single_failure_scan",
    "no_fire_margin_db",
    "stray_energy_verdict",
    "assess_unwanted_firing",
]

# The margin is a difference of logarithms; an exactly-met margin can land a few
# ULP low. Absorb the representation error here, not in the required margin.
MARGIN_TOLERANCE_DB = 1e-9

# The three events an actuation chain nests, each of which owes an inhibit.
BARRIERS = ("arm", "select", "fire")

# Single-failure tolerance means one failure must still leave a barrier up.
MIN_INDEPENDENT_INHIBITS = 2


def validate_positive(label, value):
    """Return value as a strictly positive finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def normalize_barrier(name):
    """Return the canonical barrier name of an inhibit."""
    if not isinstance(name, str):
        raise ValueError("barrier must be a string, got %r" % (name,))
    key = name.strip().lower()
    if key not in BARRIERS:
        raise ValueError(
            "unknown barrier %r; the chain nests %s" % (name, ", ".join(BARRIERS))
        )
    return key


def normalize_inhibits(inhibits):
    """Return the validated inhibit inventory of an actuation chain."""
    if not isinstance(inhibits, (list, tuple)) or not inhibits:
        raise ValueError("inhibits must be a non-empty sequence of mappings")
    seen = set()
    normalized = []
    for index, inhibit in enumerate(inhibits):
        if not isinstance(inhibit, dict):
            raise ValueError("inhibits[%d] must be a mapping" % index)
        for key in ("inhibit_id", "barrier", "resources"):
            if key not in inhibit:
                raise ValueError("inhibits[%d] missing '%s'" % (index, key))
        inhibit_id = inhibit["inhibit_id"]
        if not isinstance(inhibit_id, str) or not inhibit_id.strip():
            raise ValueError("inhibits[%d]['inhibit_id'] must be a non-empty string" % index)
        inhibit_id = inhibit_id.strip()
        if inhibit_id in seen:
            raise ValueError("duplicate inhibit_id %r" % inhibit_id)
        seen.add(inhibit_id)
        resources = inhibit["resources"]
        if not isinstance(resources, (list, tuple, set, frozenset)):
            raise ValueError("inhibits[%d]['resources'] must be a sequence" % index)
        names = set()
        for resource in resources:
            if not isinstance(resource, str) or not resource.strip():
                raise ValueError(
                    "inhibits[%d] resource names must be non-empty strings" % index
                )
            names.add(resource.strip())
        normalized.append(
            {
                "inhibit_id": inhibit_id,
                "barrier": normalize_barrier(inhibit["barrier"]),
                "resources": sorted(names),
            }
        )
    return normalized


def resource_map(inhibits):
    """Return each shared resource and the inhibits that depend on it."""
    normalized = normalize_inhibits(inhibits)
    mapping = {}
    for inhibit in normalized:
        for resource in inhibit["resources"]:
            mapping.setdefault(resource, set()).add(inhibit["inhibit_id"])
    return {resource: sorted(ids) for resource, ids in mapping.items()}


def independent_groups(inhibits):
    """Group inhibits that a single resource failure would remove together."""
    normalized = normalize_inhibits(inhibits)
    parent = {inhibit["inhibit_id"]: inhibit["inhibit_id"] for inhibit in normalized}

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a, b):
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for ids in resource_map(inhibits).values():
        for other in ids[1:]:
            union(ids[0], other)
    grouped = {}
    for inhibit in normalized:
        grouped.setdefault(find(inhibit["inhibit_id"]), []).append(inhibit["inhibit_id"])
    return sorted(sorted(members) for members in grouped.values())


def independent_inhibit_count(inhibits):
    """Return how many inhibits survive as genuinely independent."""
    return len(independent_groups(inhibits))


def barrier_coverage(inhibits):
    """Report which of the nested barriers carry no inhibit at all."""
    normalized = normalize_inhibits(inhibits)
    present = {inhibit["barrier"] for inhibit in normalized}
    missing = [barrier for barrier in BARRIERS if barrier not in present]
    return {
        "present": sorted(present),
        "missing": missing,
        "complete": not missing,
    }


def single_failure_scan(inhibits, failures=None):
    """Report every single failure that would leave no inhibit standing."""
    normalized = normalize_inhibits(inhibits)
    all_ids = {inhibit["inhibit_id"] for inhibit in normalized}
    resources = resource_map(inhibits)
    candidates = []
    for resource, ids in sorted(resources.items()):
        candidates.append(("resource", resource, set(ids)))
    if failures is not None:
        if not isinstance(failures, (list, tuple)):
            raise ValueError("failures must be a sequence of mappings")
        for index, failure in enumerate(failures):
            if not isinstance(failure, dict):
                raise ValueError("failures[%d] must be a mapping" % index)
            for key in ("failure_id", "defeats_inhibits"):
                if key not in failure:
                    raise ValueError("failures[%d] missing '%s'" % (index, key))
            failure_id = failure["failure_id"]
            if not isinstance(failure_id, str) or not failure_id.strip():
                raise ValueError("failures[%d]['failure_id'] must be a non-empty string" % index)
            defeated = failure["defeats_inhibits"]
            if not isinstance(defeated, (list, tuple, set, frozenset)):
                raise ValueError("failures[%d]['defeats_inhibits'] must be a sequence" % index)
            removed = set()
            for item in defeated:
                if not isinstance(item, str) or not item.strip():
                    raise ValueError("failures[%d] inhibit names must be non-empty strings" % index)
                name = item.strip()
                if name not in all_ids:
                    raise ValueError(
                        "failures[%d] names inhibit %r that the chain does not hold"
                        % (index, name)
                    )
                removed.add(name)
            for resource in failure.get("defeats_resources") or []:
                if not isinstance(resource, str) or not resource.strip():
                    raise ValueError("failures[%d] resource names must be non-empty strings" % index)
                key = resource.strip()
                if key not in resources:
                    raise ValueError(
                        "failures[%d] names resource %r that no inhibit depends on"
                        % (index, key)
                    )
                removed.update(resources[key])
            candidates.append(("failure", failure_id.strip(), removed))
    clearing = []
    findings = []
    for kind, name, removed in candidates:
        survivors = all_ids - removed
        if not survivors:
            clearing.append({"kind": kind, "name": name, "defeats": sorted(removed)})
            findings.append(
                "single %s '%s' defeats every inhibit, so an uncommanded firing is "
                "possible" % (kind, name)
            )
    return {
        "inhibit_count": len(all_ids),
        "candidates_examined": len(candidates),
        "clearing_failures": clearing,
        "tolerant": not clearing,
        "findings": findings,
    }


def no_fire_margin_db(no_fire_current_a, induced_current_a):
    """Return the margin in decibels between a no-fire current and a stray current."""
    no_fire = validate_positive("no_fire_current_a", no_fire_current_a)
    induced = validate_positive("induced_current_a", induced_current_a)
    return 20.0 * math.log10(no_fire / induced)


def stray_energy_verdict(no_fire_current_a, induced_current_a, required_margin_db):
    """Grade the stray current a single failure can drive into the initiator."""
    achieved = no_fire_margin_db(no_fire_current_a, induced_current_a)
    if not isinstance(required_margin_db, (int, float)) or isinstance(required_margin_db, bool):
        raise ValueError("required_margin_db must be a real number")
    required = float(required_margin_db)
    if not math.isfinite(required) or required < 0.0:
        raise ValueError("required_margin_db must be non-negative and finite")
    met = achieved > required or math.isclose(
        achieved, required, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE_DB
    )
    findings = []
    if not met:
        findings.append(
            "stray-current margin %.3f dB is below the required %.3f dB"
            % (achieved, required)
        )
    return {
        "achieved_margin_db": achieved,
        "required_margin_db": required,
        "met": met,
        "findings": findings,
    }


def assess_unwanted_firing(spec):
    """Run the full clause 5.1.2 unwanted-firing tolerance assessment.

    spec keys: inhibits, optional failures, no_fire_current_a,
    worst_case_induced_current_a, required_margin_db.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "inhibits" not in spec:
        raise ValueError("spec missing required key 'inhibits'")
    coverage = barrier_coverage(spec["inhibits"])
    groups = independent_groups(spec["inhibits"])
    independent = len(groups)
    scan = single_failure_scan(spec["inhibits"], spec.get("failures"))
    findings = list(scan["findings"])
    if not coverage["complete"]:
        findings.append(
            "no inhibit implements the %s barrier" % ", ".join(coverage["missing"])
        )
    if independent < MIN_INDEPENDENT_INHIBITS:
        findings.append(
            "only %d independent inhibit(s) survive shared-resource collapse; "
            "single-failure tolerance needs %d"
            % (independent, MIN_INDEPENDENT_INHIBITS)
        )
    stray = None
    stray_keys = ("no_fire_current_a", "worst_case_induced_current_a", "required_margin_db")
    provided = [key for key in stray_keys if key in spec]
    if provided:
        if len(provided) != len(stray_keys):
            raise ValueError(
                "stray-current assessment needs all of %s" % ", ".join(stray_keys)
            )
        stray = stray_energy_verdict(
            spec["no_fire_current_a"],
            spec["worst_case_induced_current_a"],
            spec["required_margin_db"],
        )
        findings.extend(stray["findings"])
    return {
        "barrier_coverage": coverage,
        "independent_groups": groups,
        "independent_inhibits": independent,
        "single_failure_scan": scan,
        "stray_energy": stray,
        "single_failure_tolerant": not findings,
        "findings": findings,
    }
