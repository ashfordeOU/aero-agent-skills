#!/usr/bin/env python3
"""The nonconformance report form used as the project's default pattern.

Anchor: ECSS-Q-ST-10-09 Annex C, the informative report template whose
headings and fields follow the normative Annex A data item. The annex
offers a form, not an obligation, so the layout may be adapted — but the
content the form lays out is owed either way. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Four things follow from an informative annex over a normative data item.

A heading is a container for content. A template adopting the pattern
has to carry a section for every content group the data item fixes, and
a project form that drops the requirement-not-met heading has dropped
the content, not simplified the layout.

Fields are weighed by what the group holds. A group asking for four
fields and a group asking for two are not equally covered by one field
each, so field coverage is the weighted mean over the groups rather than
a count of fields found.

Order is a deviation, not a defect. Re-sequencing the sections of an
informative form changes nothing the data item demands, so ordering
differences are measured as an inversion share against the annex
sequence and recorded, never refused.

Local sections are additions, not errors. A project form carrying its
own routing block is still following the pattern, and the additions are
reported so the deviation list is complete.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

GROUP_IDENTIFICATION = "identification-and-raising-date"
GROUP_AFFECTED_ITEM = "affected-item-and-configuration"
GROUP_DESCRIPTION = "description-and-detection-point"
GROUP_REQUIREMENT = "requirement-not-met"
GROUP_CATEGORY = "category-and-safety-effect"
GROUP_CAUSE = "cause-analysis"
GROUP_DISPOSITION = "proposed-disposition-and-justification"
GROUP_IMPLEMENTATION = "implementation-and-verification"
GROUP_CLOSURE = "closure-authority-and-date"

CANONICAL_GROUP_ORDER = (
    GROUP_IDENTIFICATION,
    GROUP_AFFECTED_ITEM,
    GROUP_DESCRIPTION,
    GROUP_REQUIREMENT,
    GROUP_CATEGORY,
    GROUP_CAUSE,
    GROUP_DISPOSITION,
    GROUP_IMPLEMENTATION,
    GROUP_CLOSURE,
)

REQUIRED_FIELDS = {
    GROUP_IDENTIFICATION: ("ncr-number", "raising-date", "originator"),
    GROUP_AFFECTED_ITEM: (
        "item-name",
        "part-number",
        "serial-or-lot-number",
        "configuration-status",
    ),
    GROUP_DESCRIPTION: (
        "nonconformance-description",
        "detection-point",
        "detecting-activity",
    ),
    GROUP_REQUIREMENT: ("requirement-reference", "requirement-summary"),
    GROUP_CATEGORY: ("nonconformance-category", "safety-effect"),
    GROUP_CAUSE: ("cause-statement", "cause-category"),
    GROUP_DISPOSITION: ("proposed-disposition", "disposition-justification", "board"),
    GROUP_IMPLEMENTATION: ("implementation-reference", "verification-record"),
    GROUP_CLOSURE: ("closure-authority", "closure-date"),
}

TEMPLATE_NOT_SUPPLIED = "ncr-template-not-supplied"
TEMPLATE_HEADING_MISSING = "ncr-template-required-heading-missing"
TEMPLATE_FIELD_COVERAGE_SHORT = "ncr-template-field-coverage-short"
TEMPLATE_ACCEPTED_WITH_DEVIATIONS = "ncr-template-accepted-with-deviations"
TEMPLATE_ACCEPTED_AS_DEFAULT = "ncr-template-accepted-as-default"

DEFAULT_TEMPLATE_POLICY = {
    "min_heading_coverage": 1.0,
    "min_field_coverage": 0.9,
    "max_order_inversion_share": 0.15,
    "allow_local_sections": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_template_policy(policy):
    """Check the policy the candidate form is graded against."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    headings = _require_fraction(
        "min_heading_coverage", policy.get("min_heading_coverage")
    )
    fields = _require_fraction("min_field_coverage", policy.get("min_field_coverage"))
    if fields > headings:
        raise ValueError(
            "min_field_coverage %g above min_heading_coverage %g demands fields "
            "inside sections the form need not carry" % (fields, headings)
        )
    _require_fraction(
        "max_order_inversion_share", policy.get("max_order_inversion_share")
    )
    _require_flag("allow_local_sections", policy.get("allow_local_sections"))
    return policy


def validate_section(section):
    """Read one template section: its heading, what it holds, its fields."""
    if not isinstance(section, dict):
        raise ValueError("section must be a mapping, got %r" % (section,))
    heading = _require_label("heading", section.get("heading", ""))
    if not heading:
        raise ValueError("a template section with no heading cannot be followed")

    declared = section.get("maps_to", "")
    if declared is None:
        declared = ""
    maps_to = _require_label("maps_to", declared)
    if maps_to and maps_to not in REQUIRED_FIELDS:
        raise ValueError(
            "section %r maps to unrecognised content group %r; the data item "
            "fixes the groups" % (heading, maps_to)
        )

    fields = section.get("fields", ())
    if not isinstance(fields, (list, tuple)):
        raise ValueError("fields on %r must be a sequence of field names" % heading)
    checked_fields = []
    for field in fields:
        label = _require_label("field on %r" % heading, field)
        if not label:
            raise ValueError("section %r carries a blank field name" % heading)
        if label in checked_fields:
            raise ValueError("section %r carries field %r twice" % (heading, label))
        checked_fields.append(label)

    return {
        "heading": heading,
        "maps_to": maps_to or None,
        "fields": tuple(checked_fields),
    }


def validate_sections(sections):
    """Read the whole form, refusing a repeated heading or content group."""
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be a sequence of template sections")
    checked = []
    headings = set()
    groups = set()
    for section in sections:
        record = validate_section(section)
        if record["heading"] in headings:
            raise ValueError("heading %r appears twice" % record["heading"])
        headings.add(record["heading"])
        if record["maps_to"] is not None:
            if record["maps_to"] in groups:
                raise ValueError(
                    "content group %r is laid out in two sections" % record["maps_to"]
                )
            groups.add(record["maps_to"])
        checked.append(record)
    if not checked:
        raise ValueError("the candidate template carries no sections at all")
    return tuple(checked)


def mapped_groups(sections):
    """Content groups the form carries, in the order the form carries them."""
    return tuple(
        record["maps_to"]
        for record in validate_sections(sections)
        if record["maps_to"] is not None
    )


def missing_groups(sections):
    """Content groups the data item fixes and the form does not carry."""
    held = set(mapped_groups(sections))
    return tuple(name for name in CANONICAL_GROUP_ORDER if name not in held)


def local_sections(sections):
    """Headings the form adds beyond the pattern."""
    return tuple(
        record["heading"]
        for record in validate_sections(sections)
        if record["maps_to"] is None
    )


def heading_coverage(sections):
    """Share of the content groups the form gives a heading to."""
    return (len(CANONICAL_GROUP_ORDER) - len(missing_groups(sections))) / float(
        len(CANONICAL_GROUP_ORDER)
    )


def group_field_gaps(section):
    """Required fields the section's content group asks for and it omits."""
    record = validate_section(section)
    if record["maps_to"] is None:
        return ()
    held = set(record["fields"])
    return tuple(
        field for field in REQUIRED_FIELDS[record["maps_to"]] if field not in held
    )


def group_field_coverage(section):
    """Share of its group's required fields one section carries."""
    record = validate_section(section)
    if record["maps_to"] is None:
        return 0.0
    owed = REQUIRED_FIELDS[record["maps_to"]]
    return (len(owed) - len(group_field_gaps(record))) / float(len(owed))


def field_coverage(sections):
    """Weighted mean field coverage across every group the data item fixes."""
    records = {
        record["maps_to"]: record
        for record in validate_sections(sections)
        if record["maps_to"] is not None
    }
    total_weight = 0
    carried = 0
    for group, owed in REQUIRED_FIELDS.items():
        total_weight += len(owed)
        record = records.get(group)
        if record is None:
            continue
        carried += len(owed) - len(group_field_gaps(record))
    if total_weight == 0:
        return 1.0
    return carried / float(total_weight)


def field_gap_report(sections):
    """Every group with a field gap, and the fields it is short."""
    report = []
    for record in validate_sections(sections):
        if record["maps_to"] is None:
            continue
        gaps = group_field_gaps(record)
        if gaps:
            report.append((record["maps_to"], gaps))
    return tuple(report)


def order_inversions(sections):
    """Pairs of carried groups the form sequences against the annex order."""
    order = {name: index for index, name in enumerate(CANONICAL_GROUP_ORDER)}
    carried = [order[name] for name in mapped_groups(sections)]
    inversions = 0
    for left in range(len(carried)):
        for right in range(left + 1, len(carried)):
            if carried[left] > carried[right]:
                inversions += 1
    return inversions


def order_inversion_share(sections):
    """Inversions over the pairs that could be inverted at all."""
    count = len(mapped_groups(sections))
    if count < 2:
        return 0.0
    pairs = count * (count - 1) / 2.0
    return order_inversions(sections) / pairs


def assess_ncr_template(case):
    """Grade a candidate nonconformance report form against the annex pattern."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    policy = validate_template_policy(case.get("policy") or DEFAULT_TEMPLATE_POLICY)

    findings = []
    advisories = []
    deviations = []
    result = {
        "template_reference": None,
        "heading_coverage": 0.0,
        "field_coverage": 0.0,
        "missing_groups": (),
        "field_gaps": (),
        "local_sections": (),
        "order_inversions": 0,
        "order_inversion_share": 0.0,
        "deviations": deviations,
        "verdict": None,
        "findings": findings,
        "advisories": advisories,
    }

    template = case.get("template")
    if template is None:
        findings.append(
            "no candidate report form has been supplied, so there is no "
            "default pattern to adopt"
        )
        result["verdict"] = TEMPLATE_NOT_SUPPLIED
        return result
    if not isinstance(template, dict):
        raise ValueError("template must be a mapping, got %r" % (template,))

    result["template_reference"] = _require_label(
        "template_reference", template.get("template_reference", "")
    )
    if not result["template_reference"]:
        findings.append(
            "the candidate form carries no reference, so no project could cite "
            "the form it adopted"
        )
        result["verdict"] = TEMPLATE_NOT_SUPPLIED
        return result

    sections = template.get("sections")
    if sections is None:
        raise ValueError("the template declares no sections to assess")
    checked = validate_sections(sections)

    absent = missing_groups(checked)
    headings = heading_coverage(checked)
    fields = field_coverage(checked)
    gaps = field_gap_report(checked)
    additions = local_sections(checked)
    inversions = order_inversions(checked)
    inversion_share = order_inversion_share(checked)

    result["heading_coverage"] = headings
    result["field_coverage"] = fields
    result["missing_groups"] = absent
    result["field_gaps"] = gaps
    result["local_sections"] = additions
    result["order_inversions"] = inversions
    result["order_inversion_share"] = inversion_share

    if not _at_least(headings, float(policy["min_heading_coverage"])):
        for name in absent:
            findings.append(
                "the form carries no section for the %s content the data item "
                "fixes" % name
            )
        result["verdict"] = TEMPLATE_HEADING_MISSING
        return result

    if not _at_least(fields, float(policy["min_field_coverage"])):
        for group, missing in gaps:
            findings.append(
                "the %s section omits the %s field(s) its group asks for"
                % (group, ", ".join(missing))
            )
        findings.append(
            "field coverage is %.3g per cent against the %.3g per cent the "
            "pattern asks for"
            % (fields * 100.0, float(policy["min_field_coverage"]) * 100.0)
        )
        result["verdict"] = TEMPLATE_FIELD_COVERAGE_SHORT
        return result

    for group, missing in gaps:
        deviations.append(
            "the %s section omits %s, inside the field coverage the policy "
            "tolerates" % (group, ", ".join(missing))
        )

    if additions:
        if not policy["allow_local_sections"]:
            findings.append(
                "the form adds the %s section(s), which this project does not "
                "permit on the default pattern" % ", ".join(additions)
            )
            result["verdict"] = TEMPLATE_FIELD_COVERAGE_SHORT
            return result
        deviations.append(
            "the form adds the %s section(s) beyond the annex pattern"
            % ", ".join(additions)
        )

    if inversions > 0:
        deviations.append(
            "the form sequences %d group pair(s) against the annex order, an "
            "inversion share of %.3g" % (inversions, inversion_share)
        )
        if not _at_most(
            inversion_share, float(policy["max_order_inversion_share"])
        ):
            advisories.append(
                "the sequence differs from the annex on %.3g of the group "
                "pairs, past the %.3g the policy expects to see recorded"
                % (inversion_share, float(policy["max_order_inversion_share"]))
            )

    if deviations:
        result["verdict"] = TEMPLATE_ACCEPTED_WITH_DEVIATIONS
        return result

    result["verdict"] = TEMPLATE_ACCEPTED_AS_DEFAULT
    return result
