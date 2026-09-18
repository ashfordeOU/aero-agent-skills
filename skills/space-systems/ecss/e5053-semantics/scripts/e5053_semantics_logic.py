"""Semantics-subclause validation for SpaceWire service primitives.

Anchor: ECSS-E-ST-50-53 clause 5.2.2.2 (the semantics subclause of a service
primitive specification: the parameter list the primitive carries and the
presence category of each parameter). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every parameter entry: name, type, presence category, and a
   stated condition whenever presence is conditional.
2. Index each primitive's list, refusing a duplicate name once case and
   surrounding space are normalised.
3. Split a primitive name into its service and kind (request, indication,
   response, confirm) and group the specification by service.
4. Align every partner primitive of a service against its request: a
   mandatory request parameter may not disappear, a partner may not carry a
   parameter the request never declared unless it is provider generated, and
   a partner may not strengthen a parameter's presence category.
5. Roll the per-primitive and per-service results into a compliant count.
"""

__all__ = [
    "PRESENCE_KINDS",
    "PRESENCE_STRENGTH",
    "PRIMITIVE_KINDS",
    "validate_parameter",
    "validate_parameter_list",
    "parameter_index",
    "presence_counts",
    "split_primitive_name",
    "group_by_service",
    "presence_is_stronger",
    "align_with_request",
    "assess_primitive_semantics",
    "assess_service_semantics",
]

# The closed set of presence categories a parameter entry may carry.
PRESENCE_KINDS = ("mandatory", "conditional", "optional")

# Ordering used to decide whether a partner primitive strengthens a parameter:
# a partner may relax (mandatory -> conditional -> optional), never tighten.
PRESENCE_STRENGTH = {"optional": 0, "conditional": 1, "mandatory": 2}

# The primitive kinds one service is built from.
PRIMITIVE_KINDS = ("request", "indication", "response", "confirm")


def _text(value, label):
    """Return a stripped non-empty string, raising otherwise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    stripped = value.strip()
    if not stripped:
        raise ValueError("%s must not be empty" % label)
    return stripped


def validate_parameter(param, index=0):
    """Return one normalised parameter entry, raising on a malformed one."""
    if not isinstance(param, dict):
        raise ValueError("parameter %d must be a mapping" % index)
    name = _text(param.get("name"), "parameter %d name" % index)
    type_name = _text(param.get("type"), "parameter %r type" % name)
    presence = param.get("presence", "mandatory")
    if not isinstance(presence, str):
        raise ValueError("parameter %r presence must be a string" % name)
    presence = presence.strip().lower()
    if presence not in PRESENCE_KINDS:
        raise ValueError(
            "parameter %r presence must be one of %s, got %r"
            % (name, "|".join(PRESENCE_KINDS), presence)
        )
    condition = param.get("condition")
    if condition is not None and not isinstance(condition, str):
        raise ValueError("parameter %r condition must be text or null" % name)
    condition = condition.strip() if isinstance(condition, str) else ""
    if presence == "conditional" and not condition:
        raise ValueError(
            "parameter %r is conditional but states no condition" % name
        )
    if presence != "conditional" and condition:
        raise ValueError(
            "parameter %r states a condition but its presence is %r" % (name, presence)
        )
    return {
        "name": name,
        "type": type_name,
        "presence": presence,
        "condition": condition,
        "provider_generated": bool(param.get("provider_generated", False)),
    }


def validate_parameter_list(params):
    """Return the normalised parameter list of one primitive."""
    if params is None:
        return []
    if not isinstance(params, (list, tuple)):
        raise ValueError("parameter list must be a sequence")
    entries = []
    seen = set()
    for index, param in enumerate(params):
        entry = validate_parameter(param, index)
        key = entry["name"].lower()
        if key in seen:
            raise ValueError("parameter %r is declared twice in one primitive" % entry["name"])
        seen.add(key)
        entries.append(entry)
    return entries


def parameter_index(params):
    """Return a case-folded name to entry index for a validated list."""
    return {entry["name"].lower(): entry for entry in validate_parameter_list(params)}


def presence_counts(params):
    """Return how many entries sit in each presence category."""
    counts = {kind: 0 for kind in PRESENCE_KINDS}
    for entry in validate_parameter_list(params):
        counts[entry["presence"]] += 1
    return counts


def split_primitive_name(name):
    """Return (service, kind) for a primitive named service.kind."""
    text = _text(name, "primitive name")
    if "." not in text:
        raise ValueError(
            "primitive name %r carries no kind suffix (expected service.kind)" % text
        )
    service, _, kind = text.rpartition(".")
    service = service.strip()
    kind = kind.strip().lower()
    if not service:
        raise ValueError("primitive name %r has an empty service part" % text)
    if kind not in PRIMITIVE_KINDS:
        raise ValueError(
            "primitive %r has kind %r, expected one of %s"
            % (text, kind, "|".join(PRIMITIVE_KINDS))
        )
    return (service, kind)


def group_by_service(specs):
    """Group primitive specifications by service, keyed by kind."""
    if not isinstance(specs, (list, tuple)) or not specs:
        raise ValueError("specs must be a non-empty sequence of primitive specifications")
    grouped = {}
    for index, spec in enumerate(specs):
        if not isinstance(spec, dict):
            raise ValueError("primitive specification %d must be a mapping" % index)
        service, kind = split_primitive_name(spec.get("primitive"))
        bucket = grouped.setdefault(service, {})
        if kind in bucket:
            raise ValueError(
                "service %r declares its %s primitive twice" % (service, kind)
            )
        bucket[kind] = spec
    return grouped


def presence_is_stronger(candidate, reference):
    """True when candidate presence is a tighter obligation than reference."""
    for label, value in (("candidate", candidate), ("reference", reference)):
        if not isinstance(value, str) or value.strip().lower() not in PRESENCE_STRENGTH:
            raise ValueError("%s presence %r is not a known category" % (label, value))
    return (
        PRESENCE_STRENGTH[candidate.strip().lower()]
        > PRESENCE_STRENGTH[reference.strip().lower()]
    )


def align_with_request(request_params, partner_params, partner_kind):
    """Return the findings raised by one partner primitive against the request."""
    request_index = parameter_index(request_params)
    partner_index = parameter_index(partner_params)
    findings = []
    for key in sorted(request_index):
        entry = request_index[key]
        if entry["presence"] == "mandatory" and key not in partner_index:
            findings.append(
                "mandatory request parameter %r is absent from the %s"
                % (entry["name"], partner_kind)
            )
    for key in sorted(partner_index):
        entry = partner_index[key]
        if key not in request_index:
            if not entry["provider_generated"]:
                findings.append(
                    "%s parameter %r is not declared by the request and is not marked "
                    "provider generated" % (partner_kind, entry["name"])
                )
            continue
        reference = request_index[key]
        if presence_is_stronger(entry["presence"], reference["presence"]):
            findings.append(
                "%s parameter %r is %s but the request declares it %s; a partner may "
                "relax a presence category, never tighten it"
                % (partner_kind, entry["name"], entry["presence"], reference["presence"])
            )
    return findings


def assess_primitive_semantics(spec, index=0):
    """Validate the semantics subclause of one primitive specification."""
    if not isinstance(spec, dict):
        raise ValueError("primitive specification %d must be a mapping" % index)
    service, kind = split_primitive_name(spec.get("primitive"))
    params = validate_parameter_list(spec.get("parameters"))
    findings = []
    if not params:
        findings.append(
            "%s.%s declares an empty parameter list; state the empty list explicitly "
            "or add the parameters" % (service, kind)
        )
    return {
        "primitive": "%s.%s" % (service, kind),
        "service": service,
        "kind": kind,
        "parameters": params,
        "presence_counts": presence_counts(params),
        "findings": findings,
        "compliant": not findings,
    }


def assess_service_semantics(specs):
    """Validate the clause 5.2.2.2 semantics subclause across a service definition."""
    grouped = group_by_service(specs)
    primitives = []
    service_findings = []
    for index, spec in enumerate(specs):
        primitives.append(assess_primitive_semantics(spec, index))
    services = {}
    for service in sorted(grouped):
        bucket = grouped[service]
        findings = []
        request = bucket.get("request")
        if request is None:
            findings.append(
                "service %r declares no request primitive, so its partners cannot be "
                "aligned" % service
            )
        else:
            request_params = request.get("parameters")
            for kind in PRIMITIVE_KINDS:
                if kind == "request" or kind not in bucket:
                    continue
                findings.extend(
                    "service %s: %s" % (service, text)
                    for text in align_with_request(
                        request_params, bucket[kind].get("parameters"), kind
                    )
                )
        services[service] = {
            "kinds": tuple(k for k in PRIMITIVE_KINDS if k in bucket),
            "findings": findings,
            "compliant": not findings,
        }
        service_findings.extend(findings)
    compliant_primitives = sum(1 for p in primitives if p["compliant"])
    return {
        "primitives": primitives,
        "services": services,
        "findings": service_findings,
        "compliant_primitives": compliant_primitives,
        "total_primitives": len(primitives),
        "compliant": compliant_primitives == len(primitives) and not service_findings,
    }
