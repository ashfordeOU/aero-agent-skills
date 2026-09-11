"""Configuration management traceability audit logic.

Paraphrase of ECSS-E-ST-10C §8.2.3 practice (summarised, not copied):
each requirement must carry a unique identifier that persists through the
project lifecycle, a documented source trace linking it to an originating
parent requirement, standard clause, or customer specification, and an
assignment to a named configuration baseline. Requirements missing or
violating any of these attributes are reported as CM-trace findings.

Source trace types: parent-req, standard, customer-spec, interface-req.
All logic uses stdlib only; no external dependencies.
"""

SOURCE_TYPES = frozenset(("parent-req", "standard", "customer-spec", "interface-req"))

REQUIRED_FIELDS = ("id", "title", "source_type", "source_ref", "baseline")


def validate_identity(req_id):
    """Return True when req_id is a non-empty string.

    Raises ValueError for a non-string input or an empty/whitespace-only value.
    """
    if not isinstance(req_id, str):
        raise ValueError(
            "req_id must be a string, got %r" % type(req_id).__name__
        )
    if not req_id.strip():
        raise ValueError("req_id must be a non-empty string")
    return True


def check_source_trace(source_type, source_ref):
    """Return a list of findings for a requirement's source trace fields.

    Returns an empty list when both fields are valid.  Returns one or more
    finding strings when source_type is empty, unrecognised, or source_ref
    is empty.  Raises ValueError for non-string arguments.
    """
    if not isinstance(source_type, str):
        raise ValueError(
            "source_type must be a string, got %r" % type(source_type).__name__
        )
    if not isinstance(source_ref, str):
        raise ValueError(
            "source_ref must be a string, got %r" % type(source_ref).__name__
        )

    findings = []
    if not source_type.strip():
        findings.append(
            "source_type is empty; must be one of: %s"
            % ", ".join(sorted(SOURCE_TYPES))
        )
    elif source_type not in SOURCE_TYPES:
        findings.append(
            "source_type %r is not a recognised trace category; "
            "expected one of: %s" % (source_type, ", ".join(sorted(SOURCE_TYPES)))
        )
    if not source_ref.strip():
        findings.append(
            "source_ref is empty; must name the specific originating "
            "requirement, standard clause, or specification section"
        )
    return findings


def check_cm_baseline(baseline):
    """Return a list of findings for a requirement's CM baseline field.

    Returns an empty list when the baseline is a non-empty string.  Returns
    a finding string when the field is empty.  Raises ValueError for a
    non-string argument.
    """
    if not isinstance(baseline, str):
        raise ValueError(
            "baseline must be a string, got %r" % type(baseline).__name__
        )
    findings = []
    if not baseline.strip():
        findings.append(
            "baseline is empty; requirement must be assigned to a "
            "named configuration baseline to be under CM control"
        )
    return findings


def audit_single_requirement(req):
    """Audit one requirement record for CM traceability completeness.

    req must be a dict containing all REQUIRED_FIELDS keys.  Returns a dict:
      req_id   - the requirement's id value (or '<missing>' if absent)
      findings - list of finding strings (empty when compliant)
      compliant - True when findings is empty

    Raises ValueError for a non-dict input or a record missing required keys.
    """
    if not isinstance(req, dict):
        raise ValueError(
            "req must be a dict, got %r" % type(req).__name__
        )
    missing = [f for f in REQUIRED_FIELDS if f not in req]
    if missing:
        raise ValueError(
            "requirement record is missing required fields: %s"
            % ", ".join(missing)
        )

    findings = []

    try:
        validate_identity(req["id"])
    except ValueError as exc:
        findings.append("identity: %s" % exc)

    findings.extend(check_source_trace(req["source_type"], req["source_ref"]))
    findings.extend(check_cm_baseline(req["baseline"]))

    return {
        "req_id": req.get("id", "<missing>"),
        "findings": findings,
        "compliant": len(findings) == 0,
    }


def audit_requirement_set(requirements):
    """Audit a collection of requirement records for CM traceability.

    Audits each record individually, then checks the full set for duplicate
    identifiers and marks every record sharing a duplicate ID as non-compliant.

    Returns a dict:
      total          - total number of records
      compliant      - count of compliant records
      non_compliant  - count of non-compliant records
      duplicate_ids  - list of identifiers that appear more than once
      per_requirement - list of individual audit result dicts
      set_compliant  - True only when total > 0, non_compliant == 0, and
                       duplicate_ids is empty

    Raises ValueError for a non-list/tuple input.
    """
    if not isinstance(requirements, (list, tuple)):
        raise ValueError(
            "requirements must be a list or tuple, got %r"
            % type(requirements).__name__
        )

    results = []
    seen_ids = {}
    duplicate_ids = []

    for req in requirements:
        result = audit_single_requirement(req)
        results.append(result)
        req_id = req.get("id", "")
        if req_id:
            if req_id in seen_ids:
                if req_id not in duplicate_ids:
                    duplicate_ids.append(req_id)
            else:
                seen_ids[req_id] = True

    for result in results:
        if result["req_id"] in duplicate_ids:
            dup_msg = (
                "identity: identifier %r is not unique — "
                "requirement identifiers must be distinct across the set"
                % result["req_id"]
            )
            if dup_msg not in result["findings"]:
                result["findings"].append(dup_msg)
                result["compliant"] = False

    compliant_count = sum(1 for r in results if r["compliant"])

    return {
        "total": len(results),
        "compliant": compliant_count,
        "non_compliant": len(results) - compliant_count,
        "duplicate_ids": duplicate_ids,
        "per_requirement": results,
        "set_compliant": (
            len(results) > 0
            and compliant_count == len(results)
            and not duplicate_ids
        ),
    }
