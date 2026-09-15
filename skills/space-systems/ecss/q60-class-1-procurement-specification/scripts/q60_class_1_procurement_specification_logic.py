"""Purchasing-specification baseline assessment for Class 1 EEE part types.

Anchor: ECSS-Q-ST-60C clause 4.3.2 — Class 1 parts are bought against a
controlled written purchasing specification raised for each component type.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each purchasing specification as a configuration-controlled
   document: identifier, issue, approving authority and an effective date.
   A document missing any of the four cannot be invoked on a purchase order,
   because nobody can later say which text the delivery was bought under.
2. Map the ordered component types onto the specifications. The clause buys
   per type, so the mapping has to be one-to-one: a type with no
   specification is unbought, and a type carried by two specifications leaves
   the acceptance basis undecided.
3. Judge each specification on its own content: the declared quality level,
   the named manufacturer and manufacturing line, the invoked procurement
   test programme, and the lot traceability level it imposes.
4. Confirm the issue cited was in force on the order date. A specification
   made effective after the order was placed was not the baseline the parts
   were actually bought against.
5. Hold every declared deviation to an approval reference; an unapproved
   deviation silently widens the baseline it sits in.
6. Report per-type records, the controlled fraction of the ordered types and
   a verdict carrying every finding.
"""

import datetime

__all__ = [
    "REQUIRED_QUALITY_LEVEL",
    "TRACEABILITY_RANK",
    "MINIMUM_TRACEABILITY",
    "FRACTION_TOLERANCE",
    "normalize_token",
    "parse_iso_date",
    "traceability_rank",
    "validate_specification",
    "specification_findings",
    "map_types_to_specifications",
    "controlled_fraction",
    "assess_procurement_baseline",
]

# The quality level a Class 1 purchasing specification has to declare.
REQUIRED_QUALITY_LEVEL = "class-1"

# Traceability levels, weakest first. A purchasing specification may impose a
# stronger level than the minimum, never a weaker one.
TRACEABILITY_RANK = {
    "none": 0,
    "delivery-batch": 1,
    "lot-date-code": 2,
    "wafer-lot": 3,
    "serial-number": 4,
}

# Class 1 buys to at least lot and date code traceability.
MINIMUM_TRACEABILITY = "lot-date-code"

# The controlled fraction is a ratio of two small counts; an exact 1.0 must
# not fail on representation alone.
FRACTION_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def normalize_token(value, label):
    """Return a lower-case hyphenated token from a free-text field."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def parse_iso_date(value, label):
    """Return a date parsed from an ISO calendar string, raising on anything else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _require_text(value, label)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO calendar date, got '%s'" % (label, text))


def traceability_rank(level):
    """Return the ordinal rank of a traceability level."""
    token = normalize_token(level, "traceability level")
    if token not in TRACEABILITY_RANK:
        raise ValueError(
            "traceability level '%s' is not recognized; expected one of %s"
            % (token, ", ".join(sorted(TRACEABILITY_RANK, key=TRACEABILITY_RANK.get)))
        )
    return TRACEABILITY_RANK[token]


def validate_specification(spec):
    """Return one validated purchasing-specification record."""
    if not isinstance(spec, dict):
        raise ValueError("each purchasing specification must be a mapping")
    for key in ("identifier", "issue", "approved_by", "effective_date", "component_types"):
        if key not in spec:
            raise ValueError("purchasing specification missing required key '%s'" % key)

    identifier = _require_text(spec["identifier"], "identifier")
    issue = _require_text(spec["issue"], "issue")
    approved_by = _require_text(spec["approved_by"], "approved_by")
    effective_date = parse_iso_date(spec["effective_date"], "effective_date")

    types_raw = spec["component_types"]
    if not isinstance(types_raw, (list, tuple)) or not types_raw:
        raise ValueError(
            "component_types for '%s' must be a non-empty sequence" % identifier
        )
    component_types = []
    for index, value in enumerate(types_raw):
        token = normalize_token(value, "component_types[%d]" % index)
        if token in component_types:
            raise ValueError(
                "component type '%s' is listed twice on '%s'" % (token, identifier)
            )
        component_types.append(token)

    quality_level = spec.get("quality_level")
    quality_token = (
        normalize_token(quality_level, "quality_level") if quality_level else ""
    )

    traceability = spec.get("traceability")
    traceability_token = (
        normalize_token(traceability, "traceability") if traceability else ""
    )
    if traceability_token:
        traceability_rank(traceability_token)

    deviations_raw = spec.get("deviations", ())
    if not isinstance(deviations_raw, (list, tuple)):
        raise ValueError("deviations for '%s' must be a sequence" % identifier)
    deviations = []
    for index, item in enumerate(deviations_raw):
        if not isinstance(item, dict):
            raise ValueError("deviations[%d] on '%s' must be a mapping" % (index, identifier))
        if "subject" not in item:
            raise ValueError(
                "deviations[%d] on '%s' missing required key 'subject'" % (index, identifier)
            )
        approval = item.get("approval_reference") or ""
        if approval and not isinstance(approval, str):
            raise ValueError(
                "approval_reference on '%s' must be a string" % identifier
            )
        deviations.append(
            {
                "subject": _require_text(item["subject"], "deviation subject"),
                "approval_reference": approval.strip(),
            }
        )

    return {
        "identifier": identifier,
        "issue": issue,
        "approved_by": approved_by,
        "effective_date": effective_date,
        "component_types": component_types,
        "quality_level": quality_token,
        "manufacturer": (spec.get("manufacturer") or "").strip(),
        "manufacturing_line": (spec.get("manufacturing_line") or "").strip(),
        "test_programme": (spec.get("test_programme") or "").strip(),
        "traceability": traceability_token,
        "deviations": deviations,
    }


def specification_findings(record, order_date):
    """Return the findings raised by one validated specification record."""
    if not isinstance(record, dict) or "identifier" not in record:
        raise ValueError("record must be a validated specification mapping")
    placed = parse_iso_date(order_date, "order_date")
    findings = []
    name = record["identifier"]

    if record["quality_level"] != REQUIRED_QUALITY_LEVEL:
        findings.append(
            "specification '%s' declares quality level '%s' rather than '%s'"
            % (name, record["quality_level"] or "none", REQUIRED_QUALITY_LEVEL)
        )
    if not record["manufacturer"]:
        findings.append("specification '%s' names no manufacturer" % name)
    if not record["manufacturing_line"]:
        findings.append(
            "specification '%s' names no manufacturing line to build the type on" % name
        )
    if not record["test_programme"]:
        findings.append(
            "specification '%s' invokes no procurement test programme" % name
        )
    if not record["traceability"]:
        findings.append("specification '%s' imposes no lot traceability level" % name)
    elif traceability_rank(record["traceability"]) < traceability_rank(MINIMUM_TRACEABILITY):
        findings.append(
            "specification '%s' imposes traceability '%s', weaker than '%s'"
            % (name, record["traceability"], MINIMUM_TRACEABILITY)
        )
    if record["effective_date"] > placed:
        findings.append(
            "specification '%s' issue '%s' became effective on %s, after the order date %s"
            % (name, record["issue"], record["effective_date"].isoformat(), placed.isoformat())
        )
    for deviation in record["deviations"]:
        if not deviation["approval_reference"]:
            findings.append(
                "deviation '%s' on specification '%s' carries no approval reference"
                % (deviation["subject"], name)
            )
    return findings


def map_types_to_specifications(ordered_types, records):
    """Return the type-to-specification mapping and its coverage findings."""
    if not isinstance(ordered_types, (list, tuple)) or not ordered_types:
        raise ValueError("ordered_types must be a non-empty sequence")
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of validated specifications")

    wanted = []
    for index, value in enumerate(ordered_types):
        token = normalize_token(value, "ordered_types[%d]" % index)
        if token in wanted:
            raise ValueError("component type '%s' is ordered twice" % token)
        wanted.append(token)

    mapping = dict((token, []) for token in wanted)
    surplus = []
    for record in records:
        for token in record["component_types"]:
            if token in mapping:
                mapping[token].append(record["identifier"])
            elif token not in surplus:
                surplus.append(token)

    findings = []
    uncovered = [t for t in wanted if not mapping[t]]
    for token in uncovered:
        findings.append(
            "component type '%s' is ordered with no controlled purchasing specification"
            % token
        )
    ambiguous = [t for t in wanted if len(mapping[t]) > 1]
    for token in ambiguous:
        findings.append(
            "component type '%s' is carried by %d specifications (%s); the acceptance "
            "basis is undecided" % (token, len(mapping[token]), ", ".join(mapping[token]))
        )
    for token in surplus:
        findings.append(
            "specification coverage names component type '%s', which the order does not carry"
            % token
        )
    return {
        "ordered_types": wanted,
        "mapping": mapping,
        "uncovered_types": uncovered,
        "ambiguous_types": ambiguous,
        "surplus_types": surplus,
        "findings": findings,
    }


def controlled_fraction(ordered_types, controlled_types):
    """Return the fraction of ordered types bought against exactly one specification."""
    if not isinstance(ordered_types, (list, tuple)) or not ordered_types:
        raise ValueError("ordered_types must be a non-empty sequence")
    if not isinstance(controlled_types, (list, tuple, set, frozenset)):
        raise ValueError("controlled_types must be a collection")
    controlled = set(controlled_types)
    unknown = controlled - set(ordered_types)
    if unknown:
        raise ValueError(
            "controlled_types names %s, which is not ordered" % ", ".join(sorted(unknown))
        )
    return len(controlled) / float(len(ordered_types))


def assess_procurement_baseline(baseline):
    """Run the full clause 4.3.2 Class 1 purchasing-specification assessment.

    baseline keys: order_reference, order_date, ordered_types, specifications.
    """
    if not isinstance(baseline, dict):
        raise ValueError("baseline must be a mapping")
    for key in ("order_reference", "order_date", "ordered_types", "specifications"):
        if key not in baseline:
            raise ValueError("baseline missing required key '%s'" % key)

    order_reference = _require_text(baseline["order_reference"], "order_reference")
    order_date = parse_iso_date(baseline["order_date"], "order_date")

    specifications = baseline["specifications"]
    if not isinstance(specifications, (list, tuple)):
        raise ValueError("specifications must be a sequence")

    records = []
    seen = []
    for spec in specifications:
        record = validate_specification(spec)
        key = (record["identifier"], record["issue"])
        if key in seen:
            raise ValueError(
                "specification '%s' issue '%s' is supplied twice"
                % (record["identifier"], record["issue"])
            )
        seen.append(key)
        record["findings"] = specification_findings(record, order_date)
        record["acceptable"] = not record["findings"]
        records.append(record)

    coverage = map_types_to_specifications(baseline["ordered_types"], records)

    by_identifier = dict((r["identifier"], r) for r in records)
    controlled = []
    type_records = []
    for token in coverage["ordered_types"]:
        holders = coverage["mapping"][token]
        holder = by_identifier[holders[0]] if len(holders) == 1 else None
        governed = holder is not None and holder["acceptable"]
        if governed:
            controlled.append(token)
        type_records.append(
            {
                "component_type": token,
                "specifications": list(holders),
                "issue": holder["issue"] if holder else None,
                "governed": governed,
            }
        )

    findings = list(coverage["findings"])
    for record in records:
        findings.extend(record["findings"])

    return {
        "order_reference": order_reference,
        "order_date": order_date.isoformat(),
        "types": type_records,
        "specifications": records,
        "uncovered_types": coverage["uncovered_types"],
        "ambiguous_types": coverage["ambiguous_types"],
        "surplus_types": coverage["surplus_types"],
        "controlled_fraction": controlled_fraction(coverage["ordered_types"], controlled),
        "orderable": not findings,
        "findings": findings,
    }
