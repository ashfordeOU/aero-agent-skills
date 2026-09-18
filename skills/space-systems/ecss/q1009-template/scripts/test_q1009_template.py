#!/usr/bin/env python3
"""Contract tests for the Annex C nonconformance report template.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused grading
policy, no form supplied, a form with no reference, a content group left
without a heading, field coverage below what the pattern asks, a local
section addition, a re-sequenced form measured as an inversion share, and
a form that adopts the pattern exactly.
"""

import unittest

from q1009_template_logic import (
    CANONICAL_GROUP_ORDER,
    DEFAULT_TEMPLATE_POLICY,
    GROUP_AFFECTED_ITEM,
    GROUP_CAUSE,
    GROUP_CLOSURE,
    GROUP_DESCRIPTION,
    GROUP_DISPOSITION,
    GROUP_IDENTIFICATION,
    GROUP_REQUIREMENT,
    REQUIRED_FIELDS,
    TEMPLATE_ACCEPTED_AS_DEFAULT,
    TEMPLATE_ACCEPTED_WITH_DEVIATIONS,
    TEMPLATE_FIELD_COVERAGE_SHORT,
    TEMPLATE_HEADING_MISSING,
    TEMPLATE_NOT_SUPPLIED,
    assess_ncr_template,
    field_coverage,
    field_gap_report,
    group_field_coverage,
    group_field_gaps,
    heading_coverage,
    local_sections,
    mapped_groups,
    missing_groups,
    order_inversion_share,
    order_inversions,
    validate_section,
    validate_sections,
    validate_template_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_TEMPLATE_POLICY)
    policy.update(overrides)
    return policy


def _heading_for(group):
    return "Section - %s" % group


def _sections(order=None, drop=(), drop_fields=None, extra=()):
    order = order or CANONICAL_GROUP_ORDER
    drop_fields = drop_fields or {}
    sections = []
    for group in order:
        if group in drop:
            continue
        omitted = set(drop_fields.get(group, ()))
        sections.append(
            {
                "heading": _heading_for(group),
                "maps_to": group,
                "fields": [
                    field for field in REQUIRED_FIELDS[group] if field not in omitted
                ],
            }
        )
    for heading in extra:
        sections.append({"heading": heading, "maps_to": "", "fields": ["local-note"]})
    return sections


def _template(**overrides):
    template = {
        "template_reference": "NCR-FORM-A1",
        "sections": _sections(),
    }
    template.update(overrides)
    return template


def _case(**overrides):
    case = {"policy": _policy(), "template": _template()}
    case.update(overrides)
    return case


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_usable(self):
        self.assertIs(
            validate_template_policy(DEFAULT_TEMPLATE_POLICY), DEFAULT_TEMPLATE_POLICY
        )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_template_policy(0.9)

    def test_field_coverage_above_heading_coverage_refused(self):
        with self.assertRaises(ValueError):
            validate_template_policy(
                _policy(min_heading_coverage=0.5, min_field_coverage=0.9)
            )

    def test_inversion_share_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_template_policy(_policy(max_order_inversion_share=1.4))

    def test_non_boolean_local_section_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_template_policy(_policy(allow_local_sections="sometimes"))


class SectionValidationTests(unittest.TestCase):
    def test_section_is_read_back(self):
        record = validate_section(_sections()[0])
        self.assertEqual(record["maps_to"], GROUP_IDENTIFICATION)
        self.assertEqual(record["fields"], REQUIRED_FIELDS[GROUP_IDENTIFICATION])

    def test_a_section_with_no_heading_refused(self):
        with self.assertRaises(ValueError):
            validate_section({"heading": "  ", "maps_to": "", "fields": []})

    def test_an_unrecognised_content_group_refused(self):
        with self.assertRaises(ValueError):
            validate_section(
                {"heading": "Extras", "maps_to": "thoughts", "fields": []}
            )

    def test_a_field_named_twice_refused(self):
        with self.assertRaises(ValueError):
            validate_section(
                {
                    "heading": "Identification",
                    "maps_to": GROUP_IDENTIFICATION,
                    "fields": ["ncr-number", "ncr-number"],
                }
            )

    def test_a_heading_repeated_refused(self):
        sections = _sections()
        sections.append(dict(sections[0], maps_to=""))
        with self.assertRaises(ValueError):
            validate_sections(sections)

    def test_a_group_laid_out_twice_refused(self):
        sections = _sections()
        sections.append(
            {
                "heading": "Identification again",
                "maps_to": GROUP_IDENTIFICATION,
                "fields": list(REQUIRED_FIELDS[GROUP_IDENTIFICATION]),
            }
        )
        with self.assertRaises(ValueError):
            validate_sections(sections)

    def test_an_empty_form_refused(self):
        with self.assertRaises(ValueError):
            validate_sections([])


class CoverageTests(unittest.TestCase):
    def test_a_full_form_carries_every_group(self):
        self.assertEqual(missing_groups(_sections()), ())
        self.assertAlmostEqual(heading_coverage(_sections()), 1.0, places=9)

    def test_a_dropped_group_is_named(self):
        sections = _sections(drop=(GROUP_REQUIREMENT,))
        self.assertEqual(missing_groups(sections), (GROUP_REQUIREMENT,))

    def test_heading_coverage_falls_with_a_dropped_group(self):
        sections = _sections(drop=(GROUP_REQUIREMENT,))
        self.assertAlmostEqual(heading_coverage(sections), 8.0 / 9.0, places=9)

    def test_mapped_groups_follow_the_form_order(self):
        order = list(CANONICAL_GROUP_ORDER)
        order[0], order[1] = order[1], order[0]
        self.assertEqual(mapped_groups(_sections(order=order))[0], GROUP_AFFECTED_ITEM)

    def test_a_full_form_covers_every_field(self):
        self.assertAlmostEqual(field_coverage(_sections()), 1.0, places=9)

    def test_group_field_gaps_are_named(self):
        sections = _sections(drop_fields={GROUP_CAUSE: ("cause-category",)})
        record = [s for s in sections if s["maps_to"] == GROUP_CAUSE][0]
        self.assertEqual(group_field_gaps(record), ("cause-category",))

    def test_group_field_coverage_is_the_share_of_its_own_fields(self):
        sections = _sections(drop_fields={GROUP_CAUSE: ("cause-category",)})
        record = [s for s in sections if s["maps_to"] == GROUP_CAUSE][0]
        self.assertAlmostEqual(group_field_coverage(record), 0.5, places=9)

    def test_field_coverage_weighs_the_groups_by_what_they_hold(self):
        wide = _sections(
            drop_fields={GROUP_AFFECTED_ITEM: REQUIRED_FIELDS[GROUP_AFFECTED_ITEM][:2]}
        )
        narrow = _sections(drop_fields={GROUP_CLOSURE: ("closure-date",)})
        self.assertLess(field_coverage(wide), field_coverage(narrow))

    def test_a_dropped_group_costs_its_fields_too(self):
        sections = _sections(drop=(GROUP_DESCRIPTION,))
        self.assertLess(field_coverage(sections), 1.0)

    def test_the_field_gap_report_names_every_short_group(self):
        sections = _sections(
            drop_fields={
                GROUP_CAUSE: ("cause-category",),
                GROUP_CLOSURE: ("closure-date",),
            }
        )
        self.assertEqual(len(field_gap_report(sections)), 2)


class OrderAndAdditionTests(unittest.TestCase):
    def test_the_annex_order_has_no_inversions(self):
        self.assertEqual(order_inversions(_sections()), 0)
        self.assertAlmostEqual(order_inversion_share(_sections()), 0.0, places=9)

    def test_one_swapped_pair_is_one_inversion(self):
        order = list(CANONICAL_GROUP_ORDER)
        order[0], order[1] = order[1], order[0]
        self.assertEqual(order_inversions(_sections(order=order)), 1)

    def test_a_reversed_form_inverts_every_pair(self):
        order = list(reversed(CANONICAL_GROUP_ORDER))
        self.assertAlmostEqual(
            order_inversion_share(_sections(order=order)), 1.0, places=9
        )

    def test_a_single_group_form_has_no_pairs_to_invert(self):
        sections = [
            {
                "heading": _heading_for(GROUP_IDENTIFICATION),
                "maps_to": GROUP_IDENTIFICATION,
                "fields": list(REQUIRED_FIELDS[GROUP_IDENTIFICATION]),
            }
        ]
        self.assertAlmostEqual(order_inversion_share(sections), 0.0, places=9)

    def test_local_sections_are_named(self):
        sections = _sections(extra=("Routing and distribution",))
        self.assertEqual(local_sections(sections), ("Routing and distribution",))


class AssessmentTests(unittest.TestCase):
    def test_a_form_following_the_pattern_is_the_default(self):
        result = assess_ncr_template(_case())
        self.assertEqual(result["verdict"], TEMPLATE_ACCEPTED_AS_DEFAULT)
        self.assertAlmostEqual(result["field_coverage"], 1.0, places=9)

    def test_no_form_at_all_stops_the_assessment(self):
        result = assess_ncr_template(_case(template=None))
        self.assertEqual(result["verdict"], TEMPLATE_NOT_SUPPLIED)

    def test_a_form_with_no_reference_cannot_be_adopted(self):
        result = assess_ncr_template(
            _case(template=_template(template_reference="  "))
        )
        self.assertEqual(result["verdict"], TEMPLATE_NOT_SUPPLIED)

    def test_a_dropped_content_group_outranks_the_later_checks(self):
        template = _template(sections=_sections(drop=(GROUP_REQUIREMENT,)))
        result = assess_ncr_template(_case(template=template))
        self.assertEqual(result["verdict"], TEMPLATE_HEADING_MISSING)
        self.assertEqual(result["missing_groups"], (GROUP_REQUIREMENT,))

    def test_field_coverage_below_the_bar_is_refused(self):
        template = _template(
            sections=_sections(
                drop_fields={
                    GROUP_AFFECTED_ITEM: REQUIRED_FIELDS[GROUP_AFFECTED_ITEM][:3],
                    GROUP_DISPOSITION: REQUIRED_FIELDS[GROUP_DISPOSITION][:2],
                }
            )
        )
        result = assess_ncr_template(_case(template=template))
        self.assertEqual(result["verdict"], TEMPLATE_FIELD_COVERAGE_SHORT)

    def test_a_tolerated_field_gap_is_a_recorded_deviation(self):
        template = _template(
            sections=_sections(drop_fields={GROUP_CLOSURE: ("closure-date",)})
        )
        result = assess_ncr_template(_case(template=template))
        self.assertEqual(result["verdict"], TEMPLATE_ACCEPTED_WITH_DEVIATIONS)
        self.assertEqual(len(result["deviations"]), 1)

    def test_a_local_section_is_a_recorded_deviation(self):
        template = _template(sections=_sections(extra=("Routing and distribution",)))
        result = assess_ncr_template(_case(template=template))
        self.assertEqual(result["verdict"], TEMPLATE_ACCEPTED_WITH_DEVIATIONS)
        self.assertEqual(result["local_sections"], ("Routing and distribution",))

    def test_a_local_section_may_be_barred_by_policy(self):
        template = _template(sections=_sections(extra=("Routing and distribution",)))
        result = assess_ncr_template(
            _case(policy=_policy(allow_local_sections=False), template=template)
        )
        self.assertEqual(result["verdict"], TEMPLATE_FIELD_COVERAGE_SHORT)

    def test_a_resequenced_form_is_accepted_with_a_deviation(self):
        order = list(CANONICAL_GROUP_ORDER)
        order[0], order[1] = order[1], order[0]
        template = _template(sections=_sections(order=order))
        result = assess_ncr_template(_case(template=template))
        self.assertEqual(result["verdict"], TEMPLATE_ACCEPTED_WITH_DEVIATIONS)
        self.assertEqual(result["order_inversions"], 1)
        self.assertEqual(result["advisories"], [])

    def test_a_heavily_resequenced_form_is_still_accepted_but_advised(self):
        order = list(reversed(CANONICAL_GROUP_ORDER))
        template = _template(sections=_sections(order=order))
        result = assess_ncr_template(_case(template=template))
        self.assertEqual(result["verdict"], TEMPLATE_ACCEPTED_WITH_DEVIATIONS)
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_template_with_no_sections_key_is_refused(self):
        template = _template()
        del template["sections"]
        with self.assertRaises(ValueError):
            assess_ncr_template(_case(template=template))

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_ncr_template(("template",))


if __name__ == "__main__":
    unittest.main()
