#!/usr/bin/env python3
"""Gate 3 contract test for q6005-chip-procurement-specification-requirements.

Offline, stdlib unittest. Exercises the applicable-content set, the
conditional-item switching, placeholder detection, the completeness ratio and
the release-to-order decision of ECSS-Q-ST-60-05C clause 8.1.3 as paraphrased
in the logic module. The ratio is compared with assertAlmostEqual: a quotient
that should land exactly on a bound is asserted as an equality, never as a
strict inequality that libm could round either way.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_chip_procurement_specification_requirements_logic import (  # noqa: E402
    CONDITIONAL_ITEMS,
    MANDATORY_ITEMS,
    applicable_items,
    assess_procurement_specification,
    completeness_ratio,
    declared_items,
    is_defined,
    normalize_item_key,
    surplus_items,
    undefined_items,
    validate_context,
)


def complete_specification(**overrides):
    """A specification defining every always-mandatory item."""
    spec = {item: "defined in drawing sheet 2" for item in MANDATORY_ITEMS}
    spec.update(overrides)
    return spec


class KeyNormalizationTests(unittest.TestCase):
    def test_underscores_and_spaces_become_hyphens(self):
        self.assertEqual(normalize_item_key("Bond_Pad Metallization"), "bond-pad-metallization")

    def test_repeated_separators_collapse(self):
        self.assertEqual(normalize_item_key("  passivation   "), "passivation")
        self.assertEqual(normalize_item_key("die__revision"), "die-revision")

    def test_blank_key_is_refused(self):
        for bad in ("", "   ", "___"):
            with self.assertRaises(ValueError):
                normalize_item_key(bad)

    def test_non_string_key_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_item_key(17)

    def test_duplicate_keys_after_normalization_are_refused(self):
        with self.assertRaises(ValueError):
            declared_items({"passivation": "yes", "Passivation": "yes"})


class DefinednessTests(unittest.TestCase):
    def test_placeholder_strings_are_not_definitions(self):
        for placeholder in ("TBD", " tba ", "N/A", "-", "", "to be advised"):
            self.assertFalse(is_defined(placeholder), placeholder)

    def test_real_text_is_a_definition(self):
        self.assertTrue(is_defined("aluminium, 1.0 micron minimum"))

    def test_empty_collection_is_not_a_definition(self):
        self.assertFalse(is_defined([]))
        self.assertFalse(is_defined({}))
        self.assertTrue(is_defined(["screen A", "screen B"]))

    def test_false_flag_is_not_a_definition_but_true_is(self):
        self.assertFalse(is_defined(False))
        self.assertTrue(is_defined(True))

    def test_none_is_not_a_definition(self):
        self.assertFalse(is_defined(None))

    def test_unsupported_value_type_is_refused(self):
        with self.assertRaises(ValueError):
            is_defined(object())


class ContextTests(unittest.TestCase):
    def test_absent_context_switches_every_conditional_item_off(self):
        flags = validate_context(None)
        self.assertEqual(set(flags), set(CONDITIONAL_ITEMS.values()))
        self.assertFalse(any(flags.values()))

    def test_unknown_context_flag_is_refused(self):
        with self.assertRaises(ValueError):
            validate_context({"cryogenic_requirement": True})

    def test_non_boolean_context_flag_is_refused(self):
        with self.assertRaises(ValueError):
            validate_context({"radiation_requirement": "yes"})

    def test_declared_context_adds_its_conditional_item(self):
        items = applicable_items({"radiation_requirement": True})
        self.assertIn("radiation-hardness-level", items)
        self.assertEqual(len(items), len(MANDATORY_ITEMS) + 1)

    def test_every_conditional_flag_on_adds_every_conditional_item(self):
        context = {flag: True for flag in CONDITIONAL_ITEMS.values()}
        items = applicable_items(context)
        self.assertEqual(len(items), len(MANDATORY_ITEMS) + len(CONDITIONAL_ITEMS))
        for item in CONDITIONAL_ITEMS:
            self.assertIn(item, items)


class UndefinedItemTests(unittest.TestCase):
    def test_complete_specification_leaves_nothing_undefined(self):
        self.assertEqual(undefined_items(complete_specification()), [])

    def test_absent_item_is_undefined(self):
        spec = complete_specification()
        del spec["passivation"]
        self.assertEqual(undefined_items(spec), ["passivation"])

    def test_placeholder_item_is_undefined_even_though_the_key_exists(self):
        spec = complete_specification(**{"backside-finish": "TBD"})
        self.assertEqual(undefined_items(spec), ["backside-finish"])

    def test_conditional_item_is_only_owed_when_its_context_is_declared(self):
        spec = complete_specification()
        self.assertEqual(undefined_items(spec, None), [])
        self.assertEqual(
            undefined_items(spec, {"screening_required": True}),
            ["additional-screening-plan"],
        )

    def test_undefined_items_are_reported_in_the_applicable_order(self):
        spec = complete_specification()
        del spec["chip-type-identification"]
        del spec["delivery-documentation"]
        self.assertEqual(
            undefined_items(spec),
            ["chip-type-identification", "delivery-documentation"],
        )

    def test_inapplicable_declared_item_is_surplus_not_missing(self):
        spec = complete_specification(**{"radiation-hardness-level": "total dose 100 krad"})
        self.assertEqual(undefined_items(spec), [])
        self.assertEqual(surplus_items(spec), ["radiation-hardness-level"])


class CompletenessRatioTests(unittest.TestCase):
    def test_complete_specification_sits_exactly_at_the_top_of_the_range(self):
        # The ratio should equal one; assert the equality, not a rounding side.
        self.assertAlmostEqual(completeness_ratio(complete_specification()), 1.0, places=9)

    def test_ratio_counts_the_applicable_set_only(self):
        spec = complete_specification()
        del spec["passivation"]
        expected = (len(MANDATORY_ITEMS) - 1) / float(len(MANDATORY_ITEMS))
        self.assertAlmostEqual(completeness_ratio(spec), expected, places=9)

    def test_surplus_item_cannot_inflate_the_ratio(self):
        spec = complete_specification()
        del spec["passivation"]
        bare = completeness_ratio(spec)
        spec["radiation-hardness-level"] = "total dose 100 krad"
        self.assertAlmostEqual(completeness_ratio(spec), bare, places=9)

    def test_declaring_a_context_enlarges_the_denominator(self):
        spec = complete_specification()
        expected = len(MANDATORY_ITEMS) / float(len(MANDATORY_ITEMS) + 1)
        self.assertAlmostEqual(
            completeness_ratio(spec, {"serialization_required": True}), expected, places=9
        )

    def test_empty_specification_scores_the_bottom_of_the_range(self):
        self.assertAlmostEqual(completeness_ratio({}), 0.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_complete_specification_is_ready_to_order(self):
        result = assess_procurement_specification({"specification": complete_specification()})
        self.assertTrue(result["ready_to_order"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["completeness_ratio"], 1.0, places=9)

    def test_one_undefined_item_blocks_release_to_order(self):
        spec = complete_specification(**{"esd-sensitivity-category": "  "})
        result = assess_procurement_specification({"specification": spec})
        self.assertFalse(result["ready_to_order"])
        self.assertIn("esd-sensitivity-category", result["undefined_items"])
        self.assertTrue(any("undefined" in f for f in result["findings"]))

    def test_declared_context_is_reported_with_its_conditional_items(self):
        result = assess_procurement_specification(
            {
                "specification": complete_specification(),
                "context": {"radiation_requirement": True, "screening_required": True},
            }
        )
        self.assertEqual(
            result["conditional_items_applicable"],
            ["additional-screening-plan", "radiation-hardness-level"],
        )
        self.assertFalse(result["ready_to_order"])

    def test_partial_ratio_can_be_met_while_release_is_still_refused(self):
        spec = complete_specification()
        del spec["passivation"]
        result = assess_procurement_specification(
            {"specification": spec, "required_ratio": 0.5}
        )
        self.assertTrue(result["meets_required_ratio"])
        self.assertFalse(result["ready_to_order"])

    def test_required_ratio_met_exactly_is_reported_as_met(self):
        result = assess_procurement_specification(
            {"specification": complete_specification(), "required_ratio": 1.0}
        )
        self.assertAlmostEqual(
            result["completeness_ratio"], result["required_ratio"], places=9
        )
        self.assertTrue(result["meets_required_ratio"])

    def test_surplus_item_raises_a_finding_without_blocking_the_order(self):
        spec = complete_specification(**{"single-wafer-lot-quantity": "one lot"})
        result = assess_procurement_specification({"specification": spec})
        self.assertTrue(result["ready_to_order"])
        self.assertEqual(result["surplus_items"], ["single-wafer-lot-quantity"])
        self.assertTrue(any("outside the applicable set" in f for f in result["findings"]))

    def test_missing_specification_key_is_refused(self):
        with self.assertRaises(ValueError):
            assess_procurement_specification({})

    def test_required_ratio_outside_the_unit_interval_is_refused(self):
        for bad in (-0.1, 1.5):
            with self.assertRaises(ValueError):
                assess_procurement_specification(
                    {"specification": complete_specification(), "required_ratio": bad}
                )

    def test_non_mapping_specification_is_refused(self):
        with self.assertRaises(ValueError):
            assess_procurement_specification({"specification": ["passivation"]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
