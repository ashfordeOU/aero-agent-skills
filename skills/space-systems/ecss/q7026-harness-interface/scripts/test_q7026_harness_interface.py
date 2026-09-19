"""Contract test for the crimping and harness interface leaf (unittest)."""

import unittest

from q7026_harness_interface_logic import (
    AGREED,
    CONFLICT,
    ESCALATE,
    GAP,
    MAXIMUM,
    MINIMUM,
    RECONCILED,
    RECONCILED_WITH_GAPS,
    SENIOR,
    SINGLE,
    STRICTER,
    allocate_topic,
    band_is_empty,
    reconcile_interface,
    stricter_limit,
    validate_interface,
    validate_requirement,
)

CRIMP = "q-st-70-26"
HARNESS = "q-st-20-30"


def spec(**kw):
    s = {
        "crimping_document": CRIMP,
        "harness_document": HARNESS,
        "required_topics": [
            "crimp-pull-off-minimum-force",
            "harness-wire-bend-radius",
            "harness-contact-insertion-tooling",
            "harness-sleeving-and-labelling",
            "harness-conductor-service-loop",
        ],
        "subordination": {},
    }
    s.update(kw)
    return s


def limit(document, topic, value, direction=MINIMUM):
    return {
        "document": document,
        "topic": topic,
        "kind": "limit",
        "direction": direction,
        "value": value,
    }


def rule(document, topic, rule_id):
    return {
        "document": document,
        "topic": topic,
        "kind": "rule",
        "rule_id": rule_id,
    }


class TestInterfaceValidation(unittest.TestCase):
    def test_a_non_mapping_interface_raises(self):
        with self.assertRaises(ValueError):
            validate_interface("two standards")

    def test_naming_the_same_document_twice_raises(self):
        with self.assertRaises(ValueError):
            validate_interface(spec(harness_document=CRIMP))

    def test_an_empty_required_topic_list_raises(self):
        with self.assertRaises(ValueError):
            validate_interface(spec(required_topics=[]))

    def test_a_senior_document_outside_the_interface_raises(self):
        with self.assertRaises(ValueError):
            validate_interface(
                spec(subordination={"harness-wire-bend-radius": "e-st-20-01"})
            )

    def test_required_topics_are_returned_sorted_and_folded(self):
        checked = validate_interface(
            spec(required_topics=["Harness-Wire-Bend-Radius", "a-topic"])
        )
        self.assertEqual(
            checked["required_topics"], ["a-topic", "harness-wire-bend-radius"]
        )


class TestRequirementValidation(unittest.TestCase):
    def test_a_requirement_from_a_third_document_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(
                limit("e-st-20-01", "harness-wire-bend-radius", 5.0), spec()
            )

    def test_an_unknown_requirement_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(
                {
                    "document": CRIMP,
                    "topic": "harness-wire-bend-radius",
                    "kind": "suggestion",
                },
                spec(),
            )

    def test_a_limit_without_a_direction_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(
                {
                    "document": CRIMP,
                    "topic": "harness-wire-bend-radius",
                    "kind": "limit",
                    "direction": "roughly",
                    "value": 5.0,
                },
                spec(),
            )

    def test_a_non_numeric_limit_value_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(
                limit(CRIMP, "harness-wire-bend-radius", "five"), spec()
            )

    def test_a_rule_without_an_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(
                {"document": CRIMP, "topic": "x", "kind": "rule", "rule_id": ""},
                spec(),
            )


class TestStrictness(unittest.TestCase):
    def test_the_larger_floor_is_the_stricter_one(self):
        chosen = stricter_limit(
            limit(CRIMP, "t", 90.0, MINIMUM), limit(HARNESS, "t", 110.0, MINIMUM)
        )
        self.assertEqual(chosen["document"], HARNESS)

    def test_the_smaller_ceiling_is_the_stricter_one(self):
        chosen = stricter_limit(
            limit(CRIMP, "t", 8.0, MAXIMUM), limit(HARNESS, "t", 6.0, MAXIMUM)
        )
        self.assertEqual(chosen["document"], HARNESS)

    def test_two_equal_limits_have_no_stricter_one(self):
        self.assertIsNone(
            stricter_limit(
                limit(CRIMP, "t", 90.0, MINIMUM), limit(HARNESS, "t", 90.0, MINIMUM)
            )
        )

    def test_comparing_opposite_directions_raises(self):
        with self.assertRaises(ValueError):
            stricter_limit(
                limit(CRIMP, "t", 90.0, MINIMUM), limit(HARNESS, "t", 90.0, MAXIMUM)
            )

    def test_a_floor_above_a_ceiling_is_an_empty_band(self):
        self.assertTrue(
            band_is_empty(
                limit(CRIMP, "t", 9.0, MINIMUM), limit(HARNESS, "t", 6.0, MAXIMUM)
            )
        )

    def test_a_floor_below_a_ceiling_leaves_a_band(self):
        self.assertFalse(
            band_is_empty(
                limit(CRIMP, "t", 4.0, MINIMUM), limit(HARNESS, "t", 6.0, MAXIMUM)
            )
        )

    def test_a_floor_exactly_on_a_ceiling_still_leaves_a_band(self):
        self.assertFalse(
            band_is_empty(
                limit(CRIMP, "t", 6.0, MINIMUM), limit(HARNESS, "t", 6.0, MAXIMUM)
            )
        )

    def test_two_same_direction_limits_cannot_form_a_band(self):
        with self.assertRaises(ValueError):
            band_is_empty(
                limit(CRIMP, "t", 4.0, MINIMUM), limit(HARNESS, "t", 6.0, MINIMUM)
            )


class TestTopicAllocation(unittest.TestCase):
    def test_a_topic_only_one_document_reaches_is_governed_by_it(self):
        allocated = allocate_topic(
            "crimp-pull-off-minimum-force",
            [limit(CRIMP, "crimp-pull-off-minimum-force", 90.0)],
            spec(),
        )
        self.assertEqual(allocated["basis"], SINGLE)
        self.assertEqual(allocated["governing_document"], CRIMP)

    def test_a_topic_neither_document_reaches_is_a_gap(self):
        allocated = allocate_topic(
            "harness-conductor-service-loop",
            [limit(CRIMP, "crimp-pull-off-minimum-force", 90.0)],
            spec(),
        )
        self.assertEqual(allocated["basis"], GAP)
        self.assertIsNone(allocated["governing_document"])

    def test_the_stricter_limit_governs_a_shared_topic(self):
        allocated = allocate_topic(
            "crimp-pull-off-minimum-force",
            [
                limit(CRIMP, "crimp-pull-off-minimum-force", 90.0),
                limit(HARNESS, "crimp-pull-off-minimum-force", 110.0),
            ],
            spec(),
        )
        self.assertEqual(allocated["basis"], STRICTER)
        self.assertEqual(allocated["governing_document"], HARNESS)
        self.assertEqual(allocated["superseded"], [CRIMP])

    def test_two_equal_limits_are_recorded_as_agreement(self):
        allocated = allocate_topic(
            "crimp-pull-off-minimum-force",
            [
                limit(CRIMP, "crimp-pull-off-minimum-force", 90.0),
                limit(HARNESS, "crimp-pull-off-minimum-force", 90.0),
            ],
            spec(),
        )
        self.assertEqual(allocated["basis"], AGREED)

    def test_a_subordination_beats_the_arithmetic(self):
        allocated = allocate_topic(
            "crimp-pull-off-minimum-force",
            [
                limit(CRIMP, "crimp-pull-off-minimum-force", 90.0),
                limit(HARNESS, "crimp-pull-off-minimum-force", 110.0),
            ],
            spec(subordination={"crimp-pull-off-minimum-force": CRIMP}),
        )
        self.assertEqual(allocated["basis"], SENIOR)
        self.assertEqual(allocated["governing_document"], CRIMP)

    def test_two_identical_rules_are_agreement(self):
        allocated = allocate_topic(
            "harness-sleeving-and-labelling",
            [
                rule(CRIMP, "harness-sleeving-and-labelling", "sleeve-then-label"),
                rule(HARNESS, "harness-sleeving-and-labelling", "sleeve-then-label"),
            ],
            spec(),
        )
        self.assertEqual(allocated["basis"], AGREED)

    def test_two_differing_rules_with_no_subordination_conflict(self):
        allocated = allocate_topic(
            "harness-sleeving-and-labelling",
            [
                rule(CRIMP, "harness-sleeving-and-labelling", "sleeve-then-label"),
                rule(HARNESS, "harness-sleeving-and-labelling", "label-then-sleeve"),
            ],
            spec(),
        )
        self.assertEqual(allocated["basis"], CONFLICT)
        self.assertIsNone(allocated["governing_document"])

    def test_a_rule_against_a_limit_is_a_conflict(self):
        allocated = allocate_topic(
            "harness-wire-bend-radius",
            [
                limit(CRIMP, "harness-wire-bend-radius", 4.0),
                rule(HARNESS, "harness-wire-bend-radius", "follow-the-drawing"),
            ],
            spec(),
        )
        self.assertEqual(allocated["basis"], CONFLICT)

    def test_an_empty_band_across_the_documents_is_a_conflict(self):
        allocated = allocate_topic(
            "harness-wire-bend-radius",
            [
                limit(CRIMP, "harness-wire-bend-radius", 9.0, MINIMUM),
                limit(HARNESS, "harness-wire-bend-radius", 6.0, MAXIMUM),
            ],
            spec(),
        )
        self.assertEqual(allocated["basis"], CONFLICT)
        self.assertEqual(
            allocated["reason"], "the-two-limits-leave-an-empty-band"
        )

    def test_a_workable_band_across_the_documents_is_kept_as_a_band(self):
        allocated = allocate_topic(
            "harness-wire-bend-radius",
            [
                limit(CRIMP, "harness-wire-bend-radius", 4.0, MINIMUM),
                limit(HARNESS, "harness-wire-bend-radius", 6.0, MAXIMUM),
            ],
            spec(),
        )
        self.assertEqual(allocated["basis"], STRICTER)
        self.assertEqual(allocated["instruction"]["kind"], "band")


class TestReconciliation(unittest.TestCase):
    def test_an_empty_requirement_set_raises(self):
        with self.assertRaises(ValueError):
            reconcile_interface(spec(), [])

    def test_a_requirement_on_an_unlisted_topic_raises(self):
        with self.assertRaises(ValueError):
            reconcile_interface(
                spec(), [limit(CRIMP, "harness-paint-colour", 1.0)]
            )

    def test_a_fully_covered_interface_reconciles(self):
        requirements = [
            limit(CRIMP, "crimp-pull-off-minimum-force", 90.0),
            limit(HARNESS, "crimp-pull-off-minimum-force", 110.0),
            limit(HARNESS, "harness-wire-bend-radius", 6.0, MINIMUM),
            rule(CRIMP, "harness-contact-insertion-tooling", "use-the-listed-tool"),
            rule(HARNESS, "harness-sleeving-and-labelling", "sleeve-then-label"),
            limit(HARNESS, "harness-conductor-service-loop", 30.0, MINIMUM),
        ]
        report = reconcile_interface(spec(), requirements)
        self.assertEqual(report["verdict"], RECONCILED)
        self.assertTrue(report["shop_has_one_instruction"])

    def test_an_uncovered_topic_leaves_the_interface_with_a_gap(self):
        report = reconcile_interface(
            spec(), [limit(CRIMP, "crimp-pull-off-minimum-force", 90.0)]
        )
        self.assertEqual(report["verdict"], RECONCILED_WITH_GAPS)
        self.assertIn("harness-wire-bend-radius", report["gaps"])
        self.assertFalse(report["shop_has_one_instruction"])

    def test_a_conflict_escalates_the_whole_interface(self):
        requirements = [
            limit(CRIMP, "crimp-pull-off-minimum-force", 90.0),
            limit(HARNESS, "harness-wire-bend-radius", 6.0, MINIMUM),
            rule(CRIMP, "harness-contact-insertion-tooling", "use-the-listed-tool"),
            rule(CRIMP, "harness-sleeving-and-labelling", "sleeve-then-label"),
            rule(HARNESS, "harness-sleeving-and-labelling", "label-then-sleeve"),
            limit(HARNESS, "harness-conductor-service-loop", 30.0, MINIMUM),
        ]
        report = reconcile_interface(spec(), requirements)
        self.assertEqual(report["verdict"], ESCALATE)
        self.assertEqual(report["conflicts"], ["harness-sleeving-and-labelling"])

    def test_the_report_groups_the_topics_by_governing_document(self):
        requirements = [
            limit(CRIMP, "crimp-pull-off-minimum-force", 90.0),
            limit(HARNESS, "harness-wire-bend-radius", 6.0, MINIMUM),
            rule(CRIMP, "harness-contact-insertion-tooling", "use-the-listed-tool"),
            rule(HARNESS, "harness-sleeving-and-labelling", "sleeve-then-label"),
            limit(HARNESS, "harness-conductor-service-loop", 30.0, MINIMUM),
        ]
        report = reconcile_interface(spec(), requirements)
        self.assertEqual(
            report["governed_by_crimping"],
            ["crimp-pull-off-minimum-force", "harness-contact-insertion-tooling"],
        )
        self.assertEqual(len(report["governed_by_harness"]), 3)


if __name__ == "__main__":
    unittest.main()
