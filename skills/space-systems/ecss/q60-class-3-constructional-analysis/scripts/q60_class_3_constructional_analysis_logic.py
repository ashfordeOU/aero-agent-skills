#!/usr/bin/env python3
"""Cross-sectioning and internal inspection of Class 3 evaluation samples.

Anchor: ECSS-Q-ST-60C clause 6.2.3.3. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

A Class 3 part is built on a line the project does not control, so a
constructional analysis is asking two questions at once and the second is the
one usually skipped:

    against the baseline   does the construction found inside the package
                           match the construction the supplier declared
    across the groups      do samples drawn from different date codes agree
                           with each other, or did the build change between
                           them without anybody being told

The analysis is destructive, so the sample set is the whole argument. Samples
have to reach every date code in the procurement, and in enough numbers that a
single unlucky device is not the evidence.

Each construction attribute carries a criticality, because the attributes do
not fail alike. A different bond wire metal is a different part; a different
lead finish is a purchasing note. Numeric attributes match inside a stated
relative band rather than exactly, since a measured section is a measurement.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ATTRIBUTE_CRITICALITY = {
    "die-metallization": "critical",
    "die-attach": "critical",
    "wire-bond-material": "critical",
    "passivation": "critical",
    "wire-bond-diameter-um": "major",
    "package-seal": "major",
    "lead-finish": "minor",
    "die-dimensions-mm": "minor",
}

NUMERIC_ATTRIBUTES = ("wire-bond-diameter-um", "die-dimensions-mm")

CRITICALITY_WEIGHTS = {"critical": 1.0, "major": 0.5, "minor": 0.2}

NUMERIC_MATCH_TOLERANCE = 0.05

CONFORMANCE_FLOOR = 0.90

CONSTRUCTION_CONFORMS = "class-3-construction-conforms"
CONSTRUCTION_ANALYSIS_INCOMPLETE = "class-3-construction-analysis-incomplete"
CONSTRUCTION_DEVIATION = "class-3-construction-deviation"

REPRESENTATION_TOLERANCE = 1e-9


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_count(name, value, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_positive_number(name, value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _absorbs(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=REPRESENTATION_TOLERANCE, abs_tol=1e-12
    )


def _at_least(value, bound):
    """value >= bound, absorbing floating-point representation error."""
    return value >= bound or math.isclose(
        value, bound, rel_tol=REPRESENTATION_TOLERANCE, abs_tol=1e-12
    )


def _ceil_sqrt(population):
    """Smallest whole number whose square reaches the population.

    Computed on integers so the answer cannot move between platforms the way
    a floating square root followed by a ceiling can.
    """
    root = math.isqrt(population)
    return root if root * root == population else root + 1


def validate_attribute(attribute):
    """Reject anything that is not a declared construction attribute."""
    name = _require_text("attribute", attribute)
    if name not in ATTRIBUTE_CRITICALITY:
        raise ValueError(
            "unknown construction attribute %r; the declared set is %s"
            % (name, ", ".join(sorted(ATTRIBUTE_CRITICALITY)))
        )
    return name


def attribute_criticality(attribute):
    """How much a difference in this attribute matters."""
    return ATTRIBUTE_CRITICALITY[validate_attribute(attribute)]


def attribute_weight(attribute):
    """Weight this attribute carries in the conformance index."""
    return CRITICALITY_WEIGHTS[attribute_criticality(attribute)]


def _normalize_material(value):
    return " ".join(str(value).strip().lower().split())


def attribute_values_match(attribute, baseline_value, observed_value):
    """True when the section agrees with the declared construction.

    Numeric attributes agree inside a stated relative band, because a
    sectioned dimension is a measurement rather than a nameplate. Material
    attributes agree only on the name, normalized for case and spacing.
    """
    name = validate_attribute(attribute)
    if name in NUMERIC_ATTRIBUTES:
        declared = _require_positive_number("baseline %s" % name, baseline_value)
        found = _require_positive_number("observed %s" % name, observed_value)
        difference = abs(found - declared)
        limit = declared * NUMERIC_MATCH_TOLERANCE
        return _absorbs(difference, limit)
    if not isinstance(baseline_value, str) or not isinstance(observed_value, str):
        raise ValueError(
            "attribute %s is a material name, so both values must be strings" % name
        )
    return _normalize_material(baseline_value) == _normalize_material(observed_value)


def validate_baseline(baseline):
    """Read the declared construction baseline."""
    if not isinstance(baseline, dict) or not baseline:
        raise ValueError("baseline must be a non-empty mapping, got %r" % (baseline,))
    cleaned = {}
    for attribute, value in baseline.items():
        cleaned[validate_attribute(attribute)] = value
    return cleaned


def validate_date_code_groups(groups):
    """Read the date-code groups the procurement is drawn from."""
    if not isinstance(groups, (list, tuple)) or not groups:
        raise ValueError("date_code_groups must be a non-empty sequence")
    seen = set()
    cleaned = []
    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            raise ValueError("date_code_groups[%d] must be a mapping" % index)
        date_code = _require_text(
            "date_code_groups[%d] date_code" % index, group.get("date_code")
        )
        if date_code in seen:
            raise ValueError("date code %s appears twice" % date_code)
        seen.add(date_code)
        population = _require_count(
            "date_code_groups[%d] population" % index, group.get("population")
        )
        examined = _require_count(
            "date_code_groups[%d] samples_examined" % index,
            group.get("samples_examined", 0),
            minimum=0,
        )
        if examined > population:
            raise ValueError(
                "date code %s examines %d samples out of a population of %d"
                % (date_code, examined, population)
            )
        observed = group.get("observed", {})
        if not isinstance(observed, dict):
            raise ValueError("date code %s observed must be a mapping" % date_code)
        cleaned_observed = {}
        for attribute, value in observed.items():
            cleaned_observed[validate_attribute(attribute)] = value
        cleaned.append(
            {
                "date_code": date_code,
                "population": population,
                "samples_examined": examined,
                "observed": cleaned_observed,
            }
        )
    return cleaned


def sample_plan(groups, minimum_per_date_code=2):
    """Size the destructive sample set from the lots the parts came from."""
    cleaned = validate_date_code_groups(groups)
    per_group = _require_count("minimum_per_date_code", minimum_per_date_code)
    total_population = sum(group["population"] for group in cleaned)
    floor_from_population = _ceil_sqrt(total_population)
    required_total = max(per_group * len(cleaned), floor_from_population)
    required_total = min(required_total, total_population)
    return {
        "date_code_count": len(cleaned),
        "total_population": total_population,
        "minimum_per_date_code": per_group,
        "population_floor": floor_from_population,
        "required_total": required_total,
    }


def assess_sample_coverage(groups, minimum_per_date_code=2):
    """Check the sections actually reach every date code, in enough numbers."""
    cleaned = validate_date_code_groups(groups)
    plan = sample_plan(cleaned, minimum_per_date_code)
    records = []
    findings = []
    total_examined = 0
    for group in cleaned:
        required = min(plan["minimum_per_date_code"], group["population"])
        shortfall = max(0, required - group["samples_examined"])
        total_examined += group["samples_examined"]
        records.append(
            {
                "date_code": group["date_code"],
                "population": group["population"],
                "samples_examined": group["samples_examined"],
                "required": required,
                "shortfall": shortfall,
                "met": shortfall == 0,
            }
        )
        if shortfall:
            findings.append(
                "date code %s was sectioned %d time(s) against %d required, so "
                "that lot is not spoken for"
                % (group["date_code"], group["samples_examined"], required)
            )
    total_shortfall = max(0, plan["required_total"] - total_examined)
    if total_shortfall:
        findings.append(
            "the sample set totals %d sections against %d required across a "
            "population of %d"
            % (total_examined, plan["required_total"], plan["total_population"])
        )
    return {
        "plan": plan,
        "groups": records,
        "total_examined": total_examined,
        "total_required": plan["required_total"],
        "total_shortfall": total_shortfall,
        "complete": total_shortfall == 0 and all(item["met"] for item in records),
        "findings": findings,
    }


def compare_to_baseline(baseline, observed):
    """Grade one group's section against the declared construction."""
    declared = validate_baseline(baseline)
    if not isinstance(observed, dict):
        raise ValueError("observed must be a mapping, got %r" % (observed,))
    found = {validate_attribute(name): value for name, value in observed.items()}
    stray = sorted(set(found) - set(declared))
    if stray:
        raise ValueError(
            "the section reports attributes absent from the baseline: %s"
            % ", ".join(stray)
        )
    records = []
    for attribute in sorted(found):
        matches = attribute_values_match(attribute, declared[attribute], found[attribute])
        records.append(
            {
                "attribute": attribute,
                "baseline": declared[attribute],
                "observed": found[attribute],
                "criticality": attribute_criticality(attribute),
                "weight": attribute_weight(attribute),
                "matches": matches,
            }
        )
    not_examined = sorted(set(declared) - set(found))
    return {"attributes": records, "not_examined": not_examined}


def cross_group_consistency(groups):
    """Name the attributes that differ between date-code groups."""
    cleaned = validate_date_code_groups(groups)
    examined = [group for group in cleaned if group["observed"]]
    if len(examined) < 2:
        return {"comparable": False, "differences": [], "findings": []}
    differences = []
    findings = []
    attributes = set()
    for group in examined:
        attributes.update(group["observed"])
    for attribute in sorted(attributes):
        carriers = [group for group in examined if attribute in group["observed"]]
        if len(carriers) < 2:
            continue
        reference = carriers[0]
        for other in carriers[1:]:
            same = attribute_values_match(
                attribute,
                reference["observed"][attribute],
                other["observed"][attribute],
            )
            if not same:
                differences.append(
                    {
                        "attribute": attribute,
                        "criticality": attribute_criticality(attribute),
                        "weight": attribute_weight(attribute),
                        "date_codes": [reference["date_code"], other["date_code"]],
                        "values": [
                            reference["observed"][attribute],
                            other["observed"][attribute],
                        ],
                    }
                )
                findings.append(
                    "%s differs between date codes %s and %s, so the build "
                    "moved without a declared change"
                    % (attribute, reference["date_code"], other["date_code"])
                )
    return {"comparable": True, "differences": differences, "findings": findings}


def conformance_index(attribute_records):
    """Weighted share of the graded attributes that matched the baseline."""
    if not isinstance(attribute_records, (list, tuple)):
        raise ValueError("attribute_records must be a sequence")
    if not attribute_records:
        raise ValueError("attribute_records must not be empty")
    total = 0.0
    matched = 0.0
    for record in attribute_records:
        if not isinstance(record, dict) or "weight" not in record:
            raise ValueError("every attribute record needs a weight")
        weight = float(record["weight"])
        total += weight
        if record.get("matches"):
            matched += weight
    if total <= 0.0:
        raise ValueError("the graded attributes carry no weight at all")
    return matched / total


def assess_constructional_analysis(case):
    """Full clause 6.2.3.3 check over one Class 3 constructional analysis."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    manufacturer = _require_text("manufacturer", case.get("manufacturer"))
    part_number = _require_text("part_number", case.get("part_number"))
    baseline = validate_baseline(case.get("baseline"))
    groups = validate_date_code_groups(case.get("date_code_groups"))
    coverage = assess_sample_coverage(groups, case.get("minimum_per_date_code", 2))
    consistency = cross_group_consistency(groups)
    findings = list(coverage["findings"]) + list(consistency["findings"])
    graded = []
    unexamined = set(baseline)
    for group in groups:
        if not group["observed"]:
            findings.append(
                "date code %s reports no internal observations at all"
                % group["date_code"]
            )
            continue
        comparison = compare_to_baseline(baseline, group["observed"])
        unexamined &= set(comparison["not_examined"])
        for record in comparison["attributes"]:
            entry = dict(record)
            entry["date_code"] = group["date_code"]
            graded.append(entry)
            if not record["matches"]:
                findings.append(
                    "%s on date code %s differs from the declared construction "
                    "(%s criticality)"
                    % (record["attribute"], group["date_code"], record["criticality"])
                )
    if not graded:
        return {
            "manufacturer": manufacturer,
            "part_number": part_number,
            "coverage": coverage,
            "consistency": consistency,
            "attributes": [],
            "deviations": [],
            "attributes_never_examined": sorted(baseline),
            "conformance_index": 0.0,
            "verdict": CONSTRUCTION_ANALYSIS_INCOMPLETE,
            "conforms": False,
            "findings": findings
            + [
                "no section reported an internal observation, so the analysis "
                "grades nothing"
            ],
        }
    never_examined = sorted(unexamined)
    for attribute in never_examined:
        findings.append(
            "%s was declared in the baseline but no section reported it"
            % attribute
        )
    index = conformance_index(graded)
    deviations = [record for record in graded if not record["matches"]]
    blocking = [
        record
        for record in deviations + consistency["differences"]
        if record["criticality"] in ("critical", "major")
    ]
    if blocking:
        verdict = CONSTRUCTION_DEVIATION
    elif not _at_least(index, CONFORMANCE_FLOOR):
        verdict = CONSTRUCTION_DEVIATION
    elif not coverage["complete"] or never_examined:
        verdict = CONSTRUCTION_ANALYSIS_INCOMPLETE
    else:
        verdict = CONSTRUCTION_CONFORMS
    return {
        "manufacturer": manufacturer,
        "part_number": part_number,
        "coverage": coverage,
        "consistency": consistency,
        "attributes": graded,
        "deviations": deviations,
        "blocking_deviations": blocking,
        "attributes_never_examined": never_examined,
        "conformance_index": index,
        "verdict": verdict,
        "conforms": verdict == CONSTRUCTION_CONFORMS,
        "findings": findings,
    }
