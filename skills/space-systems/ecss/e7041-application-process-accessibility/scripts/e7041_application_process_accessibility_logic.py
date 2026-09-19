"""Connection-test application process accessibility.

Anchor: ECSS-E-ST-70-41C clause 6.17.4.1 (application process accessibility
for the on-board connection test). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the accessibility declaration of one test-service instance: every
   entry inside the identifier field, none the reserved idle value, and no
   duplicates.
2. Validate the set of application processes the mission defines, so the
   declaration has something to be compared against.
3. Compare the two and separate the reachable entries from the stale ones
   that name no defined process.
4. Partition requested identifiers into reachable and refused, carrying the
   reason of each refusal.
5. Census coverage: the fraction of defined processes the service can reach
   and the named list it cannot.
"""

__all__ = [
    "APID_MIN",
    "APID_MAX",
    "APID_IDLE",
    "REFUSAL_REASONS",
    "validate_application_process_id",
    "categorize_identifier",
    "validate_declaration",
    "validate_defined_processes",
    "is_accessible",
    "stale_declarations",
    "reachable_processes",
    "partition_requests",
    "accessibility_census",
    "assess_application_process_accessibility",
]

APID_MIN = 0
APID_MAX = 2046
APID_IDLE = 2047

REFUSAL_REASONS = (
    "identifier-out-of-range",
    "reserved-idle-identifier",
    "not-declared-accessible",
)


def validate_application_process_id(value, label="application_process_id"):
    """Return a validated application process identifier."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value == APID_IDLE:
        raise ValueError(
            "%s %d is the reserved idle identifier and names no application process"
            % (label, value)
        )
    if value < APID_MIN or value > APID_MAX:
        raise ValueError(
            "%s %d is outside the range [%d, %d]" % (label, value, APID_MIN, APID_MAX)
        )
    return int(value)


def categorize_identifier(value):
    """Return (usable, reason) for a requested identifier without raising."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("requested identifier must be an integer, got %r" % (value,))
    if value == APID_IDLE:
        return (False, "reserved-idle-identifier")
    if value < APID_MIN or value > APID_MAX:
        return (False, "identifier-out-of-range")
    return (True, None)


def validate_declaration(declaration):
    """Return the normalised accessibility declaration of one test service."""
    if not isinstance(declaration, dict):
        raise ValueError("declaration must be a mapping, got %r" % (declaration,))
    service_id = declaration.get("test_service_id")
    if not isinstance(service_id, str) or not service_id.strip():
        raise ValueError("test_service_id must be a non-empty string")
    entries = declaration.get("accessible_application_process_ids")
    if not isinstance(entries, (list, tuple)):
        raise ValueError(
            "accessible_application_process_ids must be a sequence, got %r" % (entries,)
        )
    seen = []
    for entry in entries:
        apid = validate_application_process_id(entry, "declared accessible identifier")
        if apid in seen:
            raise ValueError(
                "test service %s declares application process %d twice"
                % (service_id.strip(), apid)
            )
        seen.append(apid)
    return {
        "test_service_id": service_id.strip(),
        "accessible_application_process_ids": sorted(seen),
    }


def validate_defined_processes(processes):
    """Return the sorted set of application processes the mission defines."""
    if not isinstance(processes, (list, tuple)) or not processes:
        raise ValueError("at least one defined application process is required")
    seen = []
    for entry in processes:
        apid = validate_application_process_id(entry, "defined application process")
        if apid in seen:
            raise ValueError("application process %d is defined twice" % apid)
        seen.append(apid)
    return sorted(seen)


def is_accessible(declaration, application_process_id):
    """Return True when the test service declares it can address the process."""
    norm = validate_declaration(declaration)
    usable, _ = categorize_identifier(application_process_id)
    if not usable:
        return False
    return application_process_id in norm["accessible_application_process_ids"]


def stale_declarations(declaration, defined_processes):
    """Return the declared identifiers that name no defined application process."""
    norm = validate_declaration(declaration)
    defined = validate_defined_processes(defined_processes)
    return [a for a in norm["accessible_application_process_ids"] if a not in defined]


def reachable_processes(declaration, defined_processes):
    """Return the defined application processes the test service can address."""
    norm = validate_declaration(declaration)
    defined = validate_defined_processes(defined_processes)
    return [a for a in defined if a in norm["accessible_application_process_ids"]]


def partition_requests(declaration, requested):
    """Partition requested identifiers into accessible and refused-with-reason."""
    norm = validate_declaration(declaration)
    if not isinstance(requested, (list, tuple)):
        raise ValueError("requested must be a sequence of identifiers")
    accessible = []
    refused = []
    for value in requested:
        usable, reason = categorize_identifier(value)
        if not usable:
            refused.append({"application_process_id": value, "reason": reason})
            continue
        if value in norm["accessible_application_process_ids"]:
            accessible.append(value)
        else:
            refused.append(
                {
                    "application_process_id": value,
                    "reason": "not-declared-accessible",
                    "test_service_id": norm["test_service_id"],
                }
            )
    return {"accessible": accessible, "refused": refused}


def accessibility_census(declaration, defined_processes):
    """Return the coverage of the defined process set by one test service."""
    defined = validate_defined_processes(defined_processes)
    reachable = reachable_processes(declaration, defined)
    unreachable = [a for a in defined if a not in reachable]
    return {
        "defined_count": len(defined),
        "reachable_count": len(reachable),
        "coverage": len(reachable) / float(len(defined)),
        "reachable_application_process_ids": reachable,
        "unreachable_application_process_ids": unreachable,
    }


def assess_application_process_accessibility(spec):
    """Run the clause 6.17.4.1 accessibility assessment for one test service.

    spec keys: declaration, defined_application_process_ids, requested
    (optional sequence of identifiers a campaign intends to address).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("declaration", "defined_application_process_ids"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    declaration = validate_declaration(spec["declaration"])
    defined = validate_defined_processes(spec["defined_application_process_ids"])
    stale = stale_declarations(declaration, defined)
    census = accessibility_census(declaration, defined)
    partition = partition_requests(declaration, spec.get("requested", []) or [])
    findings = []
    for apid in stale:
        findings.append(
            "test service %s declares application process %d accessible but the "
            "mission defines no such process; the declaration is stale"
            % (declaration["test_service_id"], apid)
        )
    for item in partition["refused"]:
        findings.append(
            "request against application process %r refused: %s; nothing was "
            "learned about that process"
            % (item["application_process_id"], item["reason"])
        )
    if census["unreachable_application_process_ids"]:
        findings.append(
            "a clean connection-test sweep from test service %s would leave %d of "
            "%d defined application processes untouched (%s)"
            % (
                declaration["test_service_id"],
                len(census["unreachable_application_process_ids"]),
                census["defined_count"],
                ", ".join(
                    str(a) for a in census["unreachable_application_process_ids"]
                ),
            )
        )
    return {
        "declaration": declaration,
        "defined_application_process_ids": defined,
        "stale_declarations": stale,
        "census": census,
        "requests": partition,
        "findings": findings,
        "clean": not findings,
    }
