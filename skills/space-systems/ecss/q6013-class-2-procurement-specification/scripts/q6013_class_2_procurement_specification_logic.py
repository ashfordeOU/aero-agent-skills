"""Purchase-specification content assessment for class 2 commercial EEE parts.

Anchor: ECSS-Q-ST-60-13C clause 5.3.2 (the content of the controlled purchase
specification a commercial electrical, electronic and electromechanical part
is bought against at the intermediate assurance class). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the specification header. The document is invoked by a purchase
   order, so without an identifier, an issue and an approving authority there
   is nothing for the order to cite.
2. Validate every parameter against its declared acceptance basis. At this
   class a parameter may either carry the specification's own test condition
   and ordered limit pair, or defer to the manufacturer's published data --
   but the deferral counts only where the citation names a document and an
   issue, and the ordered limits then have to be the published ones.
3. Confirm an own-limit parameter does not order a window wider than the
   published one. A purchase may tighten a published limit and never loosen
   it; an ordered limit equal to the published limit is admissible under a
   named tolerance.
4. Confirm the ordered temperature range sits inside the published one, with
   equality at either end admissible under the same tolerance. Ordering a part
   over a range the manufacturer never characterized is the same defect as
   ordering a wider parameter window, in the axis that carries every other
   parameter with it.
5. Validate the acceptance route declared per part: every device screened, a
   lot acceptance sample whose accept number that sample can carry, or -- the
   route this class adds -- the manufacturer's own standard production flow,
   which counts only where the flow is named.
6. Reconcile the covered part numbers against the ordered ones in both
   directions and report the share of parameters resting on published data.
7. Return the per-part records and a verdict carrying every finding.
"""

import math

__all__ = [
    "ACCEPTANCE_BASES",
    "ACCEPTANCE_ROUTES",
    "LIMIT_TOLERANCE",
    "validate_header",
    "validate_citation",
    "validate_limit_pair",
    "validate_temperature_range",
    "temperature_range_findings",
    "validate_parameter",
    "limit_tightening_findings",
    "published_basis_findings",
    "validate_acceptance_route",
    "assess_parameter",
    "assess_part_entry",
    "assess_purchase_specification",
]

# How a parameter's acceptance may be fixed at this class.
ACCEPTANCE_BASES = ("purchase-specification-limit", "published-data-limit")

# The routes a part's acceptance may be declared under.
ACCEPTANCE_ROUTES = (
    "100-percent-screening",
    "lot-acceptance-sampling",
    "manufacturer-standard-flow",
)

# Limits are floats read from two documents; an ordered limit set equal to the
# published one must not fail on representation alone.
LIMIT_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _normalize_token(value, label):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def _optional_real(value, label):
    """Return a finite float, or None when the bound is not ordered."""
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number or None, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _no_wider(ordered, published, tolerance=LIMIT_TOLERANCE):
    """Return True when the ordered bound is inside the published one."""
    return ordered <= published or math.isclose(
        ordered, published, rel_tol=0.0, abs_tol=tolerance
    )


def validate_header(document):
    """Return the validated identity of the controlled purchase specification."""
    if not isinstance(document, dict):
        raise ValueError("document must be a mapping")
    for key in ("identifier", "issue", "approved_by"):
        if key not in document:
            raise ValueError("document missing required key '%s'" % key)
    return {
        "identifier": _require_text(document["identifier"], "identifier"),
        "issue": _require_text(document["issue"], "issue"),
        "approved_by": _require_text(document["approved_by"], "approved_by"),
    }


def validate_citation(citation, label="citation"):
    """Return the validated (document, issue) pointer of a published-data basis."""
    if not isinstance(citation, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("document", "issue"):
        if key not in citation:
            raise ValueError("%s missing required key '%s'" % (label, key))
    return {
        "document": _require_text(citation["document"], "%s document" % label),
        "issue": _require_text(citation["issue"], "%s issue" % label),
    }


def validate_limit_pair(minimum, maximum, label="limit"):
    """Return the validated (lower, upper) ordered limit pair; either may be None."""
    lower = _optional_real(minimum, "%s lower bound" % label)
    upper = _optional_real(maximum, "%s upper bound" % label)
    if lower is not None and upper is not None and lower > upper:
        raise ValueError(
            "%s lower bound %g exceeds its upper bound %g" % (label, lower, upper)
        )
    return (lower, upper)


def validate_temperature_range(span, label="temperature range"):
    """Return the validated (low, high) temperature range in degrees Celsius."""
    if span is None:
        return None
    if not isinstance(span, dict):
        raise ValueError("%s must be a mapping or None" % label)
    for key in ("low_c", "high_c"):
        if key not in span:
            raise ValueError("%s missing required key '%s'" % (label, key))
    low = _optional_real(span["low_c"], "%s low_c" % label)
    high = _optional_real(span["high_c"], "%s high_c" % label)
    if low is None or high is None:
        raise ValueError("%s must fix both ends" % label)
    if low > high:
        raise ValueError(
            "%s low end %g exceeds its high end %g" % (label, low, high)
        )
    return (low, high)


def temperature_range_findings(ordered, published):
    """Return the findings raised by an ordered range outside the published one."""
    if ordered is None:
        return ["the specification orders no temperature range for the part"]
    if published is None:
        return []
    findings = []
    if not _no_wider(published[0], ordered[0]):
        findings.append(
            "ordered temperature range reaches %g C, below the published %g C"
            % (ordered[0], published[0])
        )
    if not _no_wider(ordered[1], published[1]):
        findings.append(
            "ordered temperature range reaches %g C, above the published %g C"
            % (ordered[1], published[1])
        )
    return findings


def validate_parameter(parameter):
    """Return one validated parameter record with its declared acceptance basis."""
    if not isinstance(parameter, dict):
        raise ValueError("each parameter must be a mapping")
    for key in ("name", "basis"):
        if key not in parameter:
            raise ValueError("parameter missing required key '%s'" % key)
    name = _require_text(parameter["name"], "parameter name")
    basis = _normalize_token(parameter["basis"], "parameter '%s' basis" % name)
    if basis not in ACCEPTANCE_BASES:
        raise ValueError(
            "parameter '%s' declares basis '%s', which is not one this class "
            "recognizes; expected one of %s"
            % (name, basis, ", ".join(ACCEPTANCE_BASES))
        )
    condition_raw = parameter.get("test_condition", "")
    if condition_raw is None:
        condition_raw = ""
    if not isinstance(condition_raw, str):
        raise ValueError("test_condition for parameter '%s' must be a string" % name)
    lower, upper = validate_limit_pair(
        parameter.get("minimum"), parameter.get("maximum"), "parameter '%s'" % name
    )
    pub_lower, pub_upper = validate_limit_pair(
        parameter.get("published_minimum"),
        parameter.get("published_maximum"),
        "published limit for parameter '%s'" % name,
    )
    citation = parameter.get("citation")
    reference = (
        validate_citation(citation, "parameter '%s' citation" % name)
        if citation is not None
        else None
    )
    return {
        "name": name,
        "basis": basis,
        "test_condition": condition_raw.strip(),
        "minimum": lower,
        "maximum": upper,
        "published_minimum": pub_lower,
        "published_maximum": pub_upper,
        "citation": reference,
    }


def limit_tightening_findings(record):
    """Return the findings raised by an ordered limit wider than the published one."""
    if not isinstance(record, dict) or "name" not in record:
        raise ValueError("record must be a validated parameter mapping")
    findings = []
    name = record["name"]
    lower = record.get("minimum")
    upper = record.get("maximum")
    pub_lower = record.get("published_minimum")
    pub_upper = record.get("published_maximum")
    if pub_lower is not None:
        if lower is None:
            findings.append(
                "parameter '%s' orders no lower bound although the published data "
                "fixes one" % name
            )
        elif not _no_wider(pub_lower, lower):
            findings.append(
                "parameter '%s' orders a lower bound of %g, looser than the "
                "published %g" % (name, lower, pub_lower)
            )
    if pub_upper is not None:
        if upper is None:
            findings.append(
                "parameter '%s' orders no upper bound although the published data "
                "fixes one" % name
            )
        elif not _no_wider(upper, pub_upper):
            findings.append(
                "parameter '%s' orders an upper bound of %g, looser than the "
                "published %g" % (name, upper, pub_upper)
            )
    return findings


def published_basis_findings(record):
    """Return the findings raised by a parameter resting on published data."""
    if not isinstance(record, dict) or "basis" not in record:
        raise ValueError("record must be a validated parameter mapping")
    if record["basis"] != "published-data-limit":
        return []
    findings = []
    name = record["name"]
    if record.get("citation") is None:
        findings.append(
            "parameter '%s' rests on published data with no citation naming a "
            "document and an issue" % name
        )
    if record.get("published_minimum") is None and \
            record.get("published_maximum") is None:
        findings.append(
            "parameter '%s' rests on published data that fixes no limit" % name
        )
    return findings


def validate_acceptance_route(route):
    """Return the validated acceptance route declared for a part."""
    if not isinstance(route, dict):
        raise ValueError("acceptance route must be a mapping")
    if "mode" not in route:
        raise ValueError("acceptance route missing required key 'mode'")
    mode = _normalize_token(route["mode"], "acceptance mode")
    if mode not in ACCEPTANCE_ROUTES:
        raise ValueError(
            "acceptance mode '%s' is not a recognized route; expected one of %s"
            % (mode, ", ".join(ACCEPTANCE_ROUTES))
        )
    record = {"mode": mode, "sample_size": None, "accept_on": None, "flow": None}
    if mode == "lot-acceptance-sampling":
        for key in ("sample_size", "accept_on"):
            if key not in route:
                raise ValueError("lot acceptance route missing required key '%s'" % key)
            value = route[key]
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError("%s must be an integer, got %r" % (key, value))
        sample_size = route["sample_size"]
        accept_on = route["accept_on"]
        if sample_size < 1:
            raise ValueError("sample_size must be at least 1, got %d" % sample_size)
        if accept_on < 0:
            raise ValueError("accept_on must not be negative, got %d" % accept_on)
        if accept_on >= sample_size:
            raise ValueError(
                "accept_on %d cannot reach the sample size %d; the route would "
                "accept every lot" % (accept_on, sample_size)
            )
        record["sample_size"] = sample_size
        record["accept_on"] = accept_on
    if mode == "manufacturer-standard-flow":
        if "flow" not in route:
            raise ValueError(
                "manufacturer standard flow route missing required key 'flow'; "
                "an unnamed flow cannot be ordered against"
            )
        record["flow"] = _require_text(route["flow"], "flow")
    return record


def assess_parameter(parameter):
    """Return one parameter record carrying its own findings."""
    record = validate_parameter(parameter)
    findings = []
    if record["basis"] == "purchase-specification-limit":
        if not record["test_condition"]:
            findings.append(
                "parameter '%s' fixes no test condition to measure it at"
                % record["name"]
            )
        if record["minimum"] is None and record["maximum"] is None:
            findings.append(
                "parameter '%s' fixes no acceptance limit" % record["name"]
            )
    findings.extend(published_basis_findings(record))
    findings.extend(limit_tightening_findings(record))
    record["findings"] = findings
    record["acceptable"] = not findings
    return record


def assess_part_entry(entry):
    """Return one part record carrying its parameters, its route and its findings."""
    if not isinstance(entry, dict):
        raise ValueError("each specification entry must be a mapping")
    for key in ("part_number", "parameters"):
        if key not in entry:
            raise ValueError("specification entry missing required key '%s'" % key)
    part_number = _require_text(entry["part_number"], "part_number")
    parameters = entry["parameters"]
    if not isinstance(parameters, (list, tuple)):
        raise ValueError("parameters for '%s' must be a sequence" % part_number)

    findings = []
    records = []
    seen = []
    for parameter in parameters:
        record = assess_parameter(parameter)
        key = record["name"].lower()
        if key in seen:
            raise ValueError(
                "parameter '%s' is declared twice for part '%s'"
                % (record["name"], part_number)
            )
        seen.append(key)
        records.append(record)
        findings.extend(record["findings"])
    if not records:
        findings.append("part '%s' fixes no parameter to accept it on" % part_number)

    ordered_span = validate_temperature_range(
        entry.get("ordered_temperature_range"),
        "ordered temperature range for '%s'" % part_number,
    )
    published_span = validate_temperature_range(
        entry.get("published_temperature_range"),
        "published temperature range for '%s'" % part_number,
    )
    findings.extend(temperature_range_findings(ordered_span, published_span))

    route = entry.get("acceptance_route")
    if route is None:
        route_record = None
        findings.append(
            "part '%s' declares no acceptance route" % part_number
        )
    else:
        route_record = validate_acceptance_route(route)

    published_basis = [r["name"] for r in records
                       if r["basis"] == "published-data-limit"]
    return {
        "part_number": part_number,
        "parameters": records,
        "ordered_temperature_range": ordered_span,
        "published_temperature_range": published_span,
        "acceptance_route": route_record,
        "published_basis_parameters": published_basis,
        "findings": findings,
        "acceptable": not findings,
    }


def assess_purchase_specification(spec):
    """Run the full clause 5.3.2 purchase-specification content assessment.

    spec keys: document, ordered_part_numbers, entries.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("document", "ordered_part_numbers", "entries"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    header = validate_header(spec["document"])

    ordered = spec["ordered_part_numbers"]
    if not isinstance(ordered, (list, tuple)) or not ordered:
        raise ValueError("ordered_part_numbers must be a non-empty sequence")
    ordered_list = []
    for index, value in enumerate(ordered):
        ordered_list.append(_require_text(value, "ordered_part_numbers[%d]" % index))

    entries = spec["entries"]
    if not isinstance(entries, (list, tuple)):
        raise ValueError("entries must be a sequence of specification entries")

    records = []
    covered = []
    parameter_count = 0
    published_count = 0
    for entry in entries:
        record = assess_part_entry(entry)
        if record["part_number"] in covered:
            raise ValueError("part '%s' is specified twice" % record["part_number"])
        covered.append(record["part_number"])
        records.append(record)
        parameter_count += len(record["parameters"])
        published_count += len(record["published_basis_parameters"])

    findings = []
    uncovered = [p for p in ordered_list if p not in covered]
    for part_number in uncovered:
        findings.append(
            "ordered part '%s' has no entry in the purchase specification" % part_number
        )
    unordered = [p for p in covered if p not in ordered_list]
    for part_number in unordered:
        findings.append(
            "specification entry '%s' names a part the order does not carry"
            % part_number
        )
    for record in records:
        findings.extend(record["findings"])

    published_share = (
        published_count / parameter_count if parameter_count else 0.0
    )
    return {
        "document": header,
        "ordered_part_numbers": ordered_list,
        "covered_part_numbers": covered,
        "uncovered_part_numbers": uncovered,
        "unordered_entries": unordered,
        "parts": records,
        "parameter_count": parameter_count,
        "published_basis_count": published_count,
        "published_basis_share": published_share,
        "fit_to_order_against": not findings,
        "findings": findings,
    }
