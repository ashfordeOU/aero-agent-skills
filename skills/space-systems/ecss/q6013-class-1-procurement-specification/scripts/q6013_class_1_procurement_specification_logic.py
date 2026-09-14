"""Purchase-specification assessment for class 1 commercial EEE parts.

Anchor: ECSS-Q-ST-60-13C clause 4.3.2 (the controlled purchase specification
that fixes, for each part, the tests to be performed and the acceptance the
delivery is measured against). Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the specification header. A purchase specification is a
   configuration-controlled document: without an identifier, an issue and an
   approving authority there is nothing for a purchase order to invoke.
2. Check the specification covers every part number on the order, and report
   any entry describing a part the order does not carry.
3. Validate each parameter entry: a name, the test condition it is measured
   at, and an ordered limit pair whose lower bound does not exceed its upper
   bound. A parameter with no limit at all, or with no test condition, is a
   finding, because it cannot be dispositioned on delivery.
4. Where the manufacturer's published limits are supplied, confirm the ordered
   limits are no wider than them: the purchase may tighten a limit, never
   loosen it. An ordered limit equal to the published limit is admissible, and
   the equality is taken under a named tolerance.
5. Validate the declared acceptance route for each part: full screening of
   every device, or a lot acceptance sample with a sample size and an accept
   number that sample can carry.
6. Return the per-part records and a verdict carrying every finding.
"""

import math

__all__ = [
    "SAMPLING_MODES",
    "LIMIT_TOLERANCE",
    "validate_header",
    "validate_limit_pair",
    "validate_parameter",
    "limit_tightening_findings",
    "validate_sampling_plan",
    "assess_parameter",
    "assess_part_entry",
    "assess_purchase_specification",
]

# The two acceptance routes a purchase specification may declare per part.
SAMPLING_MODES = ("100-percent-screening", "lot-acceptance-sampling")

# Limits are compared as floats read from two documents; an ordered limit set
# equal to the published one must not fail on representation alone.
LIMIT_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


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


def _normalize_token(value, label):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


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


def validate_limit_pair(minimum, maximum, label="limit"):
    """Return the validated (lower, upper) ordered limit pair; either may be None."""
    lower = _optional_real(minimum, "%s lower bound" % label)
    upper = _optional_real(maximum, "%s upper bound" % label)
    if lower is not None and upper is not None and lower > upper:
        raise ValueError(
            "%s lower bound %g exceeds its upper bound %g" % (label, lower, upper)
        )
    return (lower, upper)


def validate_parameter(parameter):
    """Return one validated parameter record from the specification."""
    if not isinstance(parameter, dict):
        raise ValueError("each parameter must be a mapping")
    if "name" not in parameter:
        raise ValueError("parameter missing required key 'name'")
    name = _require_text(parameter["name"], "parameter name")
    condition_raw = parameter.get("test_condition", "")
    if condition_raw is None:
        condition_raw = ""
    if not isinstance(condition_raw, str):
        raise ValueError("test_condition for parameter '%s' must be a string" % name)
    lower, upper = validate_limit_pair(
        parameter.get("minimum"), parameter.get("maximum"), "parameter '%s'" % name
    )
    ds_lower, ds_upper = validate_limit_pair(
        parameter.get("datasheet_minimum"),
        parameter.get("datasheet_maximum"),
        "datasheet limit for parameter '%s'" % name,
    )
    return {
        "name": name,
        "test_condition": condition_raw.strip(),
        "minimum": lower,
        "maximum": upper,
        "datasheet_minimum": ds_lower,
        "datasheet_maximum": ds_upper,
    }


def limit_tightening_findings(record):
    """Return the findings raised by an ordered limit wider than the published one."""
    if not isinstance(record, dict) or "name" not in record:
        raise ValueError("record must be a validated parameter mapping")
    findings = []
    name = record["name"]
    lower = record.get("minimum")
    upper = record.get("maximum")
    ds_lower = record.get("datasheet_minimum")
    ds_upper = record.get("datasheet_maximum")
    if ds_lower is not None:
        if lower is None:
            findings.append(
                "parameter '%s' orders no lower bound although the published data fixes one"
                % name
            )
        elif lower < ds_lower and not math.isclose(
            lower, ds_lower, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
        ):
            findings.append(
                "parameter '%s' orders a lower bound of %g, looser than the published %g"
                % (name, lower, ds_lower)
            )
    if ds_upper is not None:
        if upper is None:
            findings.append(
                "parameter '%s' orders no upper bound although the published data fixes one"
                % name
            )
        elif upper > ds_upper and not math.isclose(
            upper, ds_upper, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
        ):
            findings.append(
                "parameter '%s' orders an upper bound of %g, looser than the published %g"
                % (name, upper, ds_upper)
            )
    return findings


def validate_sampling_plan(plan):
    """Return the validated acceptance route declared for a part."""
    if not isinstance(plan, dict):
        raise ValueError("sampling plan must be a mapping")
    if "mode" not in plan:
        raise ValueError("sampling plan missing required key 'mode'")
    mode = _normalize_token(plan["mode"], "sampling mode")
    if mode not in SAMPLING_MODES:
        raise ValueError(
            "sampling mode '%s' is not a recognized route; expected one of %s"
            % (mode, ", ".join(SAMPLING_MODES))
        )
    record = {"mode": mode, "sample_size": None, "accept_on": None}
    if mode == "lot-acceptance-sampling":
        for key in ("sample_size", "accept_on"):
            if key not in plan:
                raise ValueError("lot acceptance plan missing required key '%s'" % key)
            value = plan[key]
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError("%s must be an integer, got %r" % (key, value))
        sample_size = plan["sample_size"]
        accept_on = plan["accept_on"]
        if sample_size < 1:
            raise ValueError("sample_size must be at least 1, got %d" % sample_size)
        if accept_on < 0:
            raise ValueError("accept_on must not be negative, got %d" % accept_on)
        if accept_on >= sample_size:
            raise ValueError(
                "accept_on %d cannot reach the sample size %d; the plan would accept "
                "every lot" % (accept_on, sample_size)
            )
        record["sample_size"] = sample_size
        record["accept_on"] = accept_on
    return record


def assess_parameter(parameter):
    """Return one parameter record carrying its own findings."""
    record = validate_parameter(parameter)
    findings = []
    if not record["test_condition"]:
        findings.append(
            "parameter '%s' fixes no test condition to measure it at" % record["name"]
        )
    if record["minimum"] is None and record["maximum"] is None:
        findings.append("parameter '%s' fixes no acceptance limit" % record["name"])
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
    seen = set()
    for parameter in parameters:
        record = assess_parameter(parameter)
        key = record["name"].lower()
        if key in seen:
            raise ValueError(
                "parameter '%s' is declared twice for part '%s'" % (record["name"], part_number)
            )
        seen.add(key)
        records.append(record)
        findings.extend(record["findings"])
    if not records:
        findings.append("part '%s' fixes no parameter to test" % part_number)

    plan = entry.get("sampling_plan")
    if plan is None:
        plan_record = None
        findings.append(
            "part '%s' declares no screening or lot acceptance route" % part_number
        )
    else:
        plan_record = validate_sampling_plan(plan)

    return {
        "part_number": part_number,
        "parameters": records,
        "sampling_plan": plan_record,
        "findings": findings,
        "acceptable": not findings,
    }


def assess_purchase_specification(spec):
    """Run the full clause 4.3.2 purchase-specification assessment.

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
    for entry in entries:
        record = assess_part_entry(entry)
        if record["part_number"] in covered:
            raise ValueError("part '%s' is specified twice" % record["part_number"])
        covered.append(record["part_number"])
        records.append(record)

    findings = []
    uncovered = [p for p in ordered_list if p not in covered]
    for part_number in uncovered:
        findings.append(
            "ordered part '%s' has no entry in the purchase specification" % part_number
        )
    unordered = [p for p in covered if p not in ordered_list]
    for part_number in unordered:
        findings.append(
            "specification entry '%s' names a part the order does not carry" % part_number
        )
    for record in records:
        findings.extend(record["findings"])

    return {
        "document": header,
        "ordered_part_numbers": ordered_list,
        "covered_part_numbers": covered,
        "uncovered_part_numbers": uncovered,
        "unordered_entries": unordered,
        "parts": records,
        "fit_to_order_against": not findings,
        "findings": findings,
    }
