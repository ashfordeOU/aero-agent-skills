"""Forward-control definition store of the real-time forwarding control service.

Anchor: ECSS-E-ST-70-41C clause 6.14.3.2 (the forward-control definitions a
service 14 subservice holds). Paraphrased into an implementable procedure; no
standard text is reproduced.

Store shape
-----------
{apid: {"whole": bool,
        "service_types": {service_type: {"whole": bool, "subtypes": set()}}}}

A "whole" flag at application process level forwards everything from that
application process; a "whole" flag at service type level forwards every
subtype of that service type.

Procedure implemented here
--------------------------
1. Validate the level triple of every operation.
2. Resolve an add against the widest entry already held: redundant when it is
   already covered, absorbing when it widens an existing narrower entry.
3. Refuse an add that would exceed a per-level capacity limit.
4. Delete at exactly the level named, refusing an entry that is not held and
   pruning parents left empty.
5. Answer coverage from the widest level down and report the store sorted.
"""

__all__ = [
    "new_store",
    "validate_level",
    "add_definition",
    "delete_definition",
    "is_forwarded",
    "definition_count",
    "report_store",
    "assess_definitions",
]

DEFAULT_LIMITS = {
    "max_application_processes": 16,
    "max_service_types_per_application_process": 16,
    "max_subtypes_per_service_type": 16,
}


def new_store():
    """Return an empty forward-control definition store."""
    return {}


def _require_limits(limits):
    """Return a complete limit mapping with validated positive whole values."""
    merged = dict(DEFAULT_LIMITS)
    if limits is not None:
        if not isinstance(limits, dict):
            raise ValueError("limits must be a mapping")
        for key, value in limits.items():
            if key not in DEFAULT_LIMITS:
                raise ValueError("unrecognised limit %r" % (key,))
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError("limit %r must be a positive integer, got %r" % (key, value))
            merged[key] = value
    return merged


def validate_level(application_process, service_type=None, message_subtype=None,
                   forwardable=None):
    """Return the validated (apid, service_type, subtype) definition level."""
    if not isinstance(application_process, int) or isinstance(application_process, bool):
        raise ValueError(
            "application_process must be an integer identifier, got %r"
            % (application_process,)
        )
    if application_process < 0:
        raise ValueError("application_process must not be negative")
    if message_subtype is not None and service_type is None:
        raise ValueError(
            "a message subtype cannot be given without the service type it belongs to"
        )
    for label, value in (("service_type", service_type), ("message_subtype", message_subtype)):
        if value is None:
            continue
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (label, value))
        if value <= 0:
            raise ValueError("%s must be positive, got %d" % (label, value))
    if forwardable is not None:
        if not isinstance(forwardable, (list, tuple, set, frozenset)):
            raise ValueError("forwardable must be a collection of application processes")
        if application_process not in set(forwardable):
            raise ValueError(
                "application process %d is not one the subservice can forward"
                % application_process
            )
    return (application_process, service_type, message_subtype)


def add_definition(store, application_process, service_type=None, message_subtype=None,
                   forwardable=None, limits=None):
    """Add one definition to the store; return the findings it raised."""
    if not isinstance(store, dict):
        raise ValueError("store must be a mapping")
    apid, stype, subtype = validate_level(
        application_process, service_type, message_subtype, forwardable
    )
    caps = _require_limits(limits)
    findings = []
    entry = store.get(apid)

    if entry is not None and entry["whole"]:
        findings.append(
            "definition for application process %d is already forwarded wholesale; "
            "the narrower entry adds nothing" % apid
        )
        return findings

    if entry is None:
        if len(store) >= caps["max_application_processes"]:
            raise ValueError(
                "definition store already holds %d application processes, its limit"
                % caps["max_application_processes"]
            )
        entry = {"whole": False, "service_types": {}}
        store[apid] = entry

    if stype is None:
        absorbed = len(entry["service_types"])
        if absorbed:
            findings.append(
                "wholesale entry for application process %d absorbs %d narrower "
                "definition(s)" % (apid, absorbed)
            )
        entry["whole"] = True
        entry["service_types"] = {}
        return findings

    service = entry["service_types"].get(stype)
    if service is not None and service["whole"]:
        findings.append(
            "service type %d of application process %d is already forwarded whole; "
            "the subtype entry adds nothing" % (stype, apid)
        )
        return findings

    if service is None:
        if len(entry["service_types"]) >= caps["max_service_types_per_application_process"]:
            raise ValueError(
                "application process %d already holds %d service types, its limit"
                % (apid, caps["max_service_types_per_application_process"])
            )
        service = {"whole": False, "subtypes": set()}
        entry["service_types"][stype] = service

    if subtype is None:
        absorbed = len(service["subtypes"])
        if absorbed:
            findings.append(
                "whole service type %d of application process %d absorbs %d subtype "
                "definition(s)" % (stype, apid, absorbed)
            )
        service["whole"] = True
        service["subtypes"] = set()
        return findings

    if subtype in service["subtypes"]:
        findings.append(
            "subtype %d of service type %d of application process %d is already held"
            % (subtype, stype, apid)
        )
        return findings
    if len(service["subtypes"]) >= caps["max_subtypes_per_service_type"]:
        raise ValueError(
            "service type %d of application process %d already holds %d subtypes, its limit"
            % (stype, apid, caps["max_subtypes_per_service_type"])
        )
    service["subtypes"].add(subtype)
    return findings


def delete_definition(store, application_process, service_type=None, message_subtype=None):
    """Delete the definition held at exactly this level."""
    if not isinstance(store, dict):
        raise ValueError("store must be a mapping")
    apid, stype, subtype = validate_level(application_process, service_type, message_subtype)
    entry = store.get(apid)
    if entry is None:
        raise ValueError("no definition is held for application process %d" % apid)

    if stype is None:
        if not entry["whole"]:
            raise ValueError(
                "application process %d is not forwarded wholesale; delete the narrower "
                "definition instead" % apid
            )
        del store[apid]
        return store

    service = entry["service_types"].get(stype)
    if service is None:
        raise ValueError(
            "no definition is held for service type %d of application process %d"
            % (stype, apid)
        )

    if subtype is None:
        if not service["whole"]:
            raise ValueError(
                "service type %d of application process %d is not forwarded whole; "
                "delete the subtype definition instead" % (stype, apid)
            )
        del entry["service_types"][stype]
    else:
        if subtype not in service["subtypes"]:
            raise ValueError(
                "no definition is held for subtype %d of service type %d of "
                "application process %d" % (subtype, stype, apid)
            )
        service["subtypes"].discard(subtype)
        if not service["subtypes"] and not service["whole"]:
            del entry["service_types"][stype]

    if not entry["service_types"] and not entry["whole"]:
        del store[apid]
    return store


def is_forwarded(store, application_process, service_type, message_subtype):
    """Return whether the store covers a report at this application level."""
    if not isinstance(store, dict):
        raise ValueError("store must be a mapping")
    apid, stype, subtype = validate_level(
        application_process, service_type, message_subtype
    )
    if stype is None or subtype is None:
        raise ValueError("a coverage question needs a service type and a message subtype")
    entry = store.get(apid)
    if entry is None:
        return False
    if entry["whole"]:
        return True
    service = entry["service_types"].get(stype)
    if service is None:
        return False
    if service["whole"]:
        return True
    return subtype in service["subtypes"]


def definition_count(store):
    """Return how many definitions the store holds across all levels."""
    if not isinstance(store, dict):
        raise ValueError("store must be a mapping")
    total = 0
    for entry in store.values():
        if entry["whole"]:
            total += 1
            continue
        for service in entry["service_types"].values():
            if service["whole"]:
                total += 1
            else:
                total += len(service["subtypes"])
    return total


def report_store(store):
    """Return the store as a deterministic sorted structure."""
    if not isinstance(store, dict):
        raise ValueError("store must be a mapping")
    report = []
    for apid in sorted(store):
        entry = store[apid]
        services = []
        for stype in sorted(entry["service_types"]):
            service = entry["service_types"][stype]
            services.append(
                {
                    "service_type": stype,
                    "whole": service["whole"],
                    "message_subtypes": sorted(service["subtypes"]),
                }
            )
        report.append(
            {
                "application_process": apid,
                "whole": entry["whole"],
                "service_types": services,
            }
        )
    return report


def assess_definitions(spec):
    """Apply a sequence of clause 6.14.3.2 definition operations.

    spec keys: forwardable (collection of application processes), operations
    (list of {action: add|delete, application_process, optional service_type,
    optional message_subtype}), optional limits, optional store.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("forwardable", "operations"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    operations = spec["operations"]
    if not isinstance(operations, (list, tuple)):
        raise ValueError("spec['operations'] must be a sequence")
    store = spec.get("store")
    if store is None:
        store = new_store()
    limits = spec.get("limits")
    findings = []
    refused = []

    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise ValueError("operations[%d] must be a mapping" % index)
        if "action" not in operation or "application_process" not in operation:
            raise ValueError("operations[%d] needs an action and an application process" % index)
        action = operation["action"]
        if action not in ("add", "delete"):
            raise ValueError("operations[%d] action %r is not add or delete" % (index, action))
        try:
            if action == "add":
                findings.extend(
                    add_definition(
                        store,
                        operation["application_process"],
                        operation.get("service_type"),
                        operation.get("message_subtype"),
                        spec["forwardable"],
                        limits,
                    )
                )
            else:
                delete_definition(
                    store,
                    operation["application_process"],
                    operation.get("service_type"),
                    operation.get("message_subtype"),
                )
        except ValueError as exc:
            refused.append({"index": index, "action": action, "reason": str(exc)})

    return {
        "store": store,
        "report": report_store(store),
        "definition_count": definition_count(store),
        "refused": refused,
        "findings": findings,
        "clean": not refused and not findings,
    }
