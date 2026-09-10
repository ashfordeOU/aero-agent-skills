#!/usr/bin/env python3
"""ECSS-E-ST-10-02C clause 5.2.6.5 software tool qualification for
verification by analysis (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): a
software tool used to produce verification-by-analysis evidence must be
qualified for that use -- validated, held under configuration control,
run inside its validated domain, and independently cross-checked for a
safety-critical use -- consistent with the tool/model validation
principle of ECSS-E-ST-10C clause 5.3.4. This module implements that
per-use qualification check; it does not classify tools into
qualification categories (see the sibling e1002-tools-general leaf) or
validate analysis methods/tools/models in general (see the sibling
e10-analysis-tools-models leaf).
"""

STATUSES = (
    "not_qualified",
    "qualified_pending_configuration_control",
    "qualified_out_of_domain",
    "qualified_pending_independent_check",
    "qualified",
)


def check_domain(validated_domain, analysis_conditions):
    """Parameter names from analysis_conditions that fall outside the
    tool's validated_domain, sorted. A parameter used in the analysis
    but absent from validated_domain is treated as out-of-domain (an
    unbounded parameter was never validated)."""
    out_of_domain = []
    for parameter, value in analysis_conditions.items():
        bounds = validated_domain.get(parameter)
        if bounds is None:
            out_of_domain.append(parameter)
            continue
        low, high = bounds
        if value < low or value > high:
            out_of_domain.append(parameter)
    return sorted(out_of_domain)


def qualify_tool(tool, analysis_conditions):
    """Qualification status for one software-tool use, by fixed
    precedence: not validated -> not_qualified; validated but not
    configuration-controlled -> qualified_pending_configuration_control;
    validated and controlled but analysis_conditions fall outside the
    tool's validated domain -> qualified_out_of_domain; validated,
    controlled, in-domain, safety-critical without an independent check
    -> qualified_pending_independent_check; otherwise -> qualified."""
    if not tool["validated"]:
        return "not_qualified"
    if not tool["configuration_controlled"]:
        return "qualified_pending_configuration_control"
    if check_domain(tool["validated_domain"], analysis_conditions):
        return "qualified_out_of_domain"
    if tool.get("safety_critical", False) and not tool.get("independent_check", False):
        return "qualified_pending_independent_check"
    return "qualified"


def qualify_tool_usage(tool_usage):
    """Full qualification record for one tool-usage dict. Required
    keys: id, validated, configuration_controlled, validated_domain,
    analysis_conditions; optional keys: safety_critical,
    independent_check (default False). Returns a new dict; does not
    mutate the input. Raises ValueError if 'id' is missing."""
    if "id" not in tool_usage:
        raise ValueError("tool usage is missing an id")
    out_of_domain = check_domain(
        tool_usage["validated_domain"], tool_usage["analysis_conditions"]
    )
    status = qualify_tool(tool_usage, tool_usage["analysis_conditions"])
    return {
        "id": tool_usage["id"],
        "status": status,
        "out_of_domain_parameters": out_of_domain,
    }


def build_qualification_record(tool_usages):
    """Qualification record list for a set of tool usages, in input
    order. Raises ValueError on a duplicate tool-usage id."""
    records = []
    seen_ids = set()
    for usage in tool_usages:
        record = qualify_tool_usage(usage)
        if record["id"] in seen_ids:
            raise ValueError("duplicate tool usage id: %r" % (record["id"],))
        seen_ids.add(record["id"])
        records.append(record)
    return records


def acceptable_for_verification_evidence(record):
    """True only when status == 'qualified' -- the only status under
    which a tool's analysis output may be accepted as
    verification-by-analysis evidence without further disposition."""
    return record["status"] == "qualified"


def find_unacceptable(records):
    """Ids from records whose status blocks acceptance as verification
    evidence, in records order -- callers route these back to
    disposition (re-validation, configuration freeze, re-run inside the
    validated domain, or an independent check) before VCD close-out."""
    return [record["id"] for record in records if not acceptable_for_verification_evidence(record)]
