"""Three-barrier safety architecture for an actuation chain.

Anchor: ECSS-E-ST-20-21C clause 5.2.1 (paraphrased into an
implementable procedure; no standard text is reproduced).

The clause requires three independent barriers -- arm, select and fire
-- every one of which has to be deliberately removed before a
deployment device can activate. The engineering content is not the
count but the independence: three inhibits that all fall to the same
relay, the same command domain or the same power feed are one barrier
wearing three names.

Procedure implemented here:

1. Categorize every declared barrier by the function it serves (arm,
   select or fire), by the element whose release removes it, and by the
   command domain that can order that release. Reject a barrier whose
   function is unknown and reject an architecture that leaves one of
   the three functions uncovered or covers one of them twice.
2. Detect shared release elements and shared command domains. Two
   barriers released by the same element are one barrier; two barriers
   ordered from the same command domain fall together to one erroneous
   command.
3. Count the activation depth: the number of distinct elements an
   inadvertent activation would have to defeat. A barrier that is
   already released by default contributes nothing to that count.
4. Work out what survives one credible failure -- the worst single
   element loss -- and report the remaining depth.
5. Close with a verdict: the architecture is compliant when all three
   functions are covered, every barrier is inhibited by default, the
   depth reaches the required three, and at least one barrier isolates
   the firing energy rather than only the command.

Stdlib only, offline, deterministic.
"""

BARRIER_FUNCTIONS = ("arm", "select", "fire")

STATE_INHIBITED = "inhibited"
STATE_RELEASED = "released"
DEFAULT_STATES = (STATE_INHIBITED, STATE_RELEASED)

ISOLATION_KINDS = (
    "series-power-switch",
    "relay-contact",
    "safe-and-arm-device",
    "logic-enable",
    "connector-shunt",
)

# Isolation kinds that break the firing energy path itself rather than
# only withholding a command word.
ENERGY_ISOLATING_KINDS = (
    "series-power-switch",
    "relay-contact",
    "safe-and-arm-device",
    "connector-shunt",
)

REQUIRED_BARRIER_DEPTH = 3

FINDING_SHARED_RELEASE_ELEMENT = "shared-release-element"
FINDING_SHARED_COMMAND_DOMAIN = "shared-command-domain"
FINDING_BARRIER_RELEASED_BY_DEFAULT = "barrier-released-by-default"
FINDING_DEPTH_BELOW_REQUIREMENT = "activation-depth-below-requirement"
FINDING_NO_ENERGY_ISOLATION = "no-energy-isolating-barrier"


def _non_empty_text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_barrier(barrier):
    """Validate one declared barrier and return a normalized copy."""
    if not isinstance(barrier, dict):
        raise ValueError("barrier must be a mapping, got %r" % (barrier,))
    barrier_id = _non_empty_text("barrier id", barrier.get("id"))
    function = barrier.get("function")
    if function not in BARRIER_FUNCTIONS:
        raise ValueError(
            "barrier %s has unknown function %r (expected one of %s)"
            % (barrier_id, function, ", ".join(BARRIER_FUNCTIONS))
        )
    isolation = barrier.get("isolation_kind")
    if isolation not in ISOLATION_KINDS:
        raise ValueError(
            "barrier %s has unknown isolation_kind %r (expected one of %s)"
            % (barrier_id, isolation, ", ".join(ISOLATION_KINDS))
        )
    state = barrier.get("default_state", STATE_INHIBITED)
    if state not in DEFAULT_STATES:
        raise ValueError(
            "barrier %s has unknown default_state %r (expected one of %s)"
            % (barrier_id, state, ", ".join(DEFAULT_STATES))
        )
    return {
        "id": barrier_id,
        "function": function,
        "release_element": _non_empty_text(
            "barrier %s release_element" % barrier_id, barrier.get("release_element")
        ),
        "command_domain": _non_empty_text(
            "barrier %s command_domain" % barrier_id, barrier.get("command_domain")
        ),
        "isolation_kind": isolation,
        "default_state": state,
        "energy_isolating": _boolean(
            "barrier %s energy_isolating" % barrier_id,
            barrier.get("energy_isolating", isolation in ENERGY_ISOLATING_KINDS),
        ),
    }


def validate_architecture(barriers):
    """Validate the declared barrier set and return normalized records."""
    if not isinstance(barriers, (list, tuple)):
        raise ValueError("barriers must be a sequence of mappings")
    if not barriers:
        raise ValueError("barriers must not be empty")
    normalized = [validate_barrier(b) for b in barriers]
    seen_ids = set()
    for record in normalized:
        if record["id"] in seen_ids:
            raise ValueError("duplicate barrier id %s" % record["id"])
        seen_ids.add(record["id"])
    counts = {}
    for record in normalized:
        counts[record["function"]] = counts.get(record["function"], 0) + 1
    for function, count in sorted(counts.items()):
        if count > 1:
            raise ValueError(
                "function %s is declared %d times; one barrier per function"
                % (function, count)
            )
    return normalized


def functions_covered(barriers):
    """Barrier functions present, in arm/select/fire order."""
    present = {b["function"] for b in validate_architecture(barriers)}
    return tuple(f for f in BARRIER_FUNCTIONS if f in present)


def missing_functions(barriers):
    """Barrier functions the architecture does not cover."""
    present = set(functions_covered(barriers))
    return tuple(f for f in BARRIER_FUNCTIONS if f not in present)


def _group_by(records, key):
    grouped = {}
    for record in records:
        grouped.setdefault(record[key], []).append(record["id"])
    return grouped


def shared_release_elements(barriers):
    """Release elements that remove more than one barrier."""
    grouped = _group_by(validate_architecture(barriers), "release_element")
    return {k: sorted(v) for k, v in grouped.items() if len(v) > 1}


def shared_command_domains(barriers):
    """Command domains that can order more than one barrier released."""
    grouped = _group_by(validate_architecture(barriers), "command_domain")
    return {k: sorted(v) for k, v in grouped.items() if len(v) > 1}


def activation_depth(barriers):
    """Distinct elements an inadvertent activation must defeat."""
    records = validate_architecture(barriers)
    holding = {
        r["release_element"] for r in records if r["default_state"] == STATE_INHIBITED
    }
    return len(holding)


def depth_after_single_failure(barriers):
    """Worst-case remaining depth after one element is lost.

    Returns (remaining_depth, worst_element). The worst element is the
    one whose loss removes the most holding barriers; with nothing
    holding, the element is None.
    """
    records = validate_architecture(barriers)
    holding = [r for r in records if r["default_state"] == STATE_INHIBITED]
    if not holding:
        return 0, None
    elements = sorted({r["release_element"] for r in holding})
    worst_element = elements[0]
    worst_remaining = len(elements)
    for element in elements:
        remaining = len({e for e in elements if e != element})
        if remaining < worst_remaining:
            worst_remaining = remaining
            worst_element = element
    return worst_remaining, worst_element


def energy_isolating_barriers(barriers):
    """Ids of the barriers that break the firing energy path."""
    return sorted(
        r["id"] for r in validate_architecture(barriers) if r["energy_isolating"]
    )


def independence_findings(barriers):
    """Findings against barrier independence, sorted by code then subject."""
    records = validate_architecture(barriers)
    findings = []
    for element, ids in sorted(shared_release_elements(records).items()):
        findings.append(
            {
                "code": FINDING_SHARED_RELEASE_ELEMENT,
                "subject": element,
                "barriers": ids,
                "detail": "one element releases %d barriers" % len(ids),
            }
        )
    for domain, ids in sorted(shared_command_domains(records).items()):
        findings.append(
            {
                "code": FINDING_SHARED_COMMAND_DOMAIN,
                "subject": domain,
                "barriers": ids,
                "detail": "one command domain orders %d barriers" % len(ids),
            }
        )
    for record in records:
        if record["default_state"] == STATE_RELEASED:
            findings.append(
                {
                    "code": FINDING_BARRIER_RELEASED_BY_DEFAULT,
                    "subject": record["id"],
                    "barriers": [record["id"]],
                    "detail": "the %s barrier holds nothing in its default state"
                    % record["function"],
                }
            )
    return sorted(findings, key=lambda f: (f["code"], f["subject"]))


def assess_barrier_architecture(barriers, required_depth=REQUIRED_BARRIER_DEPTH):
    """Grade a declared actuation barrier architecture."""
    if not isinstance(required_depth, int) or isinstance(required_depth, bool):
        raise ValueError("required_depth must be an integer, got %r" % (required_depth,))
    if required_depth < 1:
        raise ValueError("required_depth must be >= 1, got %r" % (required_depth,))
    records = validate_architecture(barriers)
    findings = independence_findings(records)
    depth = activation_depth(records)
    remaining, worst_element = depth_after_single_failure(records)
    isolating = energy_isolating_barriers(records)
    absent = missing_functions(records)
    if depth < required_depth:
        findings.append(
            {
                "code": FINDING_DEPTH_BELOW_REQUIREMENT,
                "subject": "architecture",
                "barriers": sorted(r["id"] for r in records),
                "detail": "activation depth %d below the required %d"
                % (depth, required_depth),
            }
        )
    if not isolating:
        findings.append(
            {
                "code": FINDING_NO_ENERGY_ISOLATION,
                "subject": "architecture",
                "barriers": sorted(r["id"] for r in records),
                "detail": "every barrier withholds a command; none breaks the "
                "firing energy path",
            }
        )
    findings = sorted(findings, key=lambda f: (f["code"], f["subject"]))
    return {
        "barrier_count": len(records),
        "functions_covered": functions_covered(records),
        "missing_functions": absent,
        "activation_depth": depth,
        "required_depth": required_depth,
        "depth_after_single_failure": remaining,
        "worst_single_element": worst_element,
        "energy_isolating_barriers": isolating,
        "findings": findings,
        "finding_codes": sorted({f["code"] for f in findings}),
        "compliant": not absent and not findings,
    }
