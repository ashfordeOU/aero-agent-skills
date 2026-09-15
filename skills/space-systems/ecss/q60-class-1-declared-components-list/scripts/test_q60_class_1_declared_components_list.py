"""Contract tests for the clause 4.1.4 editable declared components list logic."""

import unittest

from q60_class_1_declared_components_list_logic import (
    COVERAGE_TOLERANCE,
    EXCHANGE_FORMATS,
    MANDATORY_DELIVERY_ATTRIBUTES,
    OBLIGED_CATEGORY,
    assess_declared_components_list,
    delivery_completeness,
    evaluate_delivery,
    format_editability,
    item_coverage,
    obliged_items,
    revision_state,
    validate_item_id,
)

ITEM = "PCDU-A"


def item(**overrides):
    """Return one Class 1 equipment item with optional overrides."""
    base = {
        "item_id": ITEM,
        "product_category": "class-1",
        "build_revision": 3,
        "declared_part_count": 120,
    }
    base.update(overrides)
    return base


def delivery(**overrides):
    """Return one acceptable delivered list with optional overrides."""
    base = {
        "delivery_id": "D001",
        "item_id": ITEM,
        "exchange_format": "xlsx",
        "issued_revision": 3,
        "line_count": 120,
    }
    base.update(overrides)
    return base


def index(*items):
    return {entry["item_id"]: entry for entry in items}


class ValidateItemTests(unittest.TestCase):
    def test_strips_surrounding_space(self):
        self.assertEqual(validate_item_id("  PCDU-A "), ITEM)

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            validate_item_id("  ")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_item_id(42)


class FormatEditabilityTests(unittest.TestCase):
    def test_spreadsheet_is_editable(self):
        self.assertTrue(format_editability("xlsx"))

    def test_flattened_print_is_not_editable(self):
        self.assertFalse(format_editability("pdf-flat"))

    def test_scan_is_not_editable(self):
        self.assertFalse(format_editability("pdf-scan"))

    def test_lookup_is_case_insensitive(self):
        self.assertTrue(format_editability("CSV"))

    def test_unknown_format_rejected(self):
        with self.assertRaises(ValueError):
            format_editability("whatever-the-supplier-sent")

    def test_every_known_format_answers_a_boolean(self):
        for fmt in EXCHANGE_FORMATS:
            self.assertIsInstance(format_editability(fmt), bool)


class DeliveryCompletenessTests(unittest.TestCase):
    def test_complete_delivery_scores_one(self):
        missing, fraction = delivery_completeness(delivery())
        self.assertEqual(missing, ())
        self.assertAlmostEqual(fraction, 1.0, places=9)

    def test_missing_attribute_is_named(self):
        incomplete = delivery()
        del incomplete["exchange_format"]
        missing, fraction = delivery_completeness(incomplete)
        self.assertEqual(missing, ("exchange_format",))
        expected = (len(MANDATORY_DELIVERY_ATTRIBUTES) - 1) / len(
            MANDATORY_DELIVERY_ATTRIBUTES
        )
        self.assertAlmostEqual(fraction, expected, places=9)

    def test_blank_string_counts_as_missing(self):
        missing, _ = delivery_completeness(delivery(item_id="   "))
        self.assertEqual(missing, ("item_id",))

    def test_none_counts_as_missing(self):
        missing, _ = delivery_completeness(delivery(line_count=None))
        self.assertEqual(missing, ("line_count",))

    def test_non_mapping_delivery_rejected(self):
        with self.assertRaises(ValueError):
            delivery_completeness(["D001"])


class RevisionStateTests(unittest.TestCase):
    def test_same_revision_is_current(self):
        self.assertEqual(revision_state(3, 3), "current")

    def test_older_issue_is_stale(self):
        self.assertEqual(revision_state(2, 3), "stale")

    def test_newer_issue_is_ahead_of_build(self):
        self.assertEqual(revision_state(4, 3), "ahead-of-build")

    def test_negative_revision_rejected(self):
        with self.assertRaises(ValueError):
            revision_state(-1, 3)

    def test_boolean_revision_rejected(self):
        with self.assertRaises(ValueError):
            revision_state(True, 3)


class ObligedItemsTests(unittest.TestCase):
    def test_only_the_obliged_category_is_selected(self):
        build = [item(), item(item_id="HARNESS-B", product_category="class-3")]
        self.assertEqual(obliged_items(build), (ITEM,))

    def test_obliged_category_constant_is_the_one_used(self):
        build = [item(product_category=OBLIGED_CATEGORY.upper())]
        self.assertEqual(obliged_items(build), (ITEM,))

    def test_build_with_no_obliged_item_rejected(self):
        with self.assertRaises(ValueError):
            obliged_items([item(product_category="class-2")])

    def test_repeated_item_identifier_rejected(self):
        with self.assertRaises(ValueError):
            obliged_items([item(), item()])

    def test_zero_declared_part_count_rejected(self):
        with self.assertRaises(ValueError):
            obliged_items([item(declared_part_count=0)])

    def test_empty_build_rejected(self):
        with self.assertRaises(ValueError):
            obliged_items([])


class EvaluateDeliveryTests(unittest.TestCase):
    def test_editable_current_full_list_is_accepted(self):
        record = evaluate_delivery(delivery(), index(item()))
        self.assertEqual(record["disposition"], "accepted")
        self.assertTrue(record["accepted"])

    def test_incomplete_delivery_is_not_a_format_failure(self):
        incomplete = delivery()
        del incomplete["issued_revision"]
        record = evaluate_delivery(incomplete, index(item()))
        self.assertEqual(record["disposition"], "record-incomplete")
        self.assertFalse(record["accepted"])

    def test_flattened_print_is_rejected_though_the_words_are_there(self):
        record = evaluate_delivery(
            delivery(exchange_format="pdf-flat"), index(item())
        )
        self.assertEqual(record["disposition"], "format-not-editable")
        self.assertFalse(record["editable"])

    def test_stale_issue_is_kept_apart_from_one_ahead_of_build(self):
        stale = evaluate_delivery(delivery(issued_revision=2), index(item()))
        ahead = evaluate_delivery(delivery(issued_revision=9), index(item()))
        self.assertEqual(stale["disposition"], "revision-stale")
        self.assertEqual(ahead["disposition"], "revision-ahead-of-build")

    def test_short_list_is_a_coverage_failure_not_an_acceptance(self):
        record = evaluate_delivery(delivery(line_count=118), index(item()))
        self.assertEqual(record["disposition"], "line-count-short")

    def test_list_longer_than_the_part_count_is_still_accepted(self):
        record = evaluate_delivery(delivery(line_count=131), index(item()))
        self.assertEqual(record["disposition"], "accepted")

    def test_item_outside_the_build_is_named_unknown(self):
        record = evaluate_delivery(delivery(item_id="GHOST-9"), index(item()))
        self.assertEqual(record["disposition"], "unknown-item")

    def test_other_category_item_is_outside_the_obligation(self):
        other = item(item_id="HARNESS-B", product_category="class-3")
        record = evaluate_delivery(
            delivery(item_id="HARNESS-B"), index(item(), other)
        )
        self.assertEqual(record["disposition"], "outside-obligation")

    def test_second_list_for_a_closed_item_is_a_duplicate(self):
        record = evaluate_delivery(
            delivery(delivery_id="D002"), index(item()), already_seen={ITEM}
        )
        self.assertEqual(record["disposition"], "duplicate-item-delivery")

    def test_empty_item_index_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_delivery(delivery(), {})


class ItemCoverageTests(unittest.TestCase):
    def test_full_coverage_is_one(self):
        records = [evaluate_delivery(delivery(), index(item()))]
        value = item_coverage(records, index(item()), (ITEM,))
        self.assertAlmostEqual(value, 1.0, places=9)

    def test_coverage_is_weighted_by_declared_part_count(self):
        big = item()
        small = item(item_id="RIU-C", declared_part_count=40)
        idx = index(big, small)
        records = [evaluate_delivery(delivery(), idx)]
        value = item_coverage(records, idx, (ITEM, "RIU-C"))
        self.assertAlmostEqual(value, 120 / 160, places=9)

    def test_rejected_delivery_contributes_nothing(self):
        idx = index(item())
        records = [evaluate_delivery(delivery(exchange_format="paper"), idx)]
        self.assertAlmostEqual(item_coverage(records, idx, (ITEM,)), 0.0, places=9)

    def test_empty_obliged_set_rejected(self):
        with self.assertRaises(ValueError):
            item_coverage([], index(item()), ())


class AssessDeclaredComponentsListTests(unittest.TestCase):
    def _spec(self, **overrides):
        base = {
            "items": [item()],
            "deliveries": [delivery()],
            "required_coverage": 1.0,
        }
        base.update(overrides)
        return base

    def test_clean_build_is_issued(self):
        result = assess_declared_components_list(self._spec())
        self.assertEqual(result["verdict"], "issue")
        self.assertTrue(result["issuable"])
        self.assertEqual(result["findings"], [])

    def test_missing_list_for_an_obliged_item_is_a_finding(self):
        spec = self._spec(
            items=[item(), item(item_id="RIU-C", declared_part_count=40)]
        )
        result = assess_declared_components_list(spec)
        self.assertEqual(result["items_without_a_list"], ("RIU-C",))
        self.assertEqual(result["verdict"], "hold")

    def test_other_category_item_raises_no_shortfall(self):
        spec = self._spec(
            items=[item(), item(item_id="BRACKET-D", product_category="class-3")]
        )
        result = assess_declared_components_list(spec)
        self.assertEqual(result["obliged_items"], (ITEM,))
        self.assertEqual(result["verdict"], "issue")

    def test_findings_are_ranked_with_the_worst_first(self):
        incomplete = delivery(delivery_id="D000")
        del incomplete["line_count"]
        spec = self._spec(
            items=[item(), item(item_id="RIU-C", declared_part_count=40)],
            deliveries=[
                delivery(),
                incomplete,
                delivery(delivery_id="D003", item_id="RIU-C", exchange_format="tiff",
                         line_count=40),
            ],
        )
        result = assess_declared_components_list(spec)
        self.assertEqual(result["findings"][0]["disposition"], "record-incomplete")

    def test_corrected_resubmission_after_a_rejection_still_counts(self):
        spec = self._spec(
            deliveries=[
                delivery(delivery_id="D001", exchange_format="pdf-scan"),
                delivery(delivery_id="D002"),
            ]
        )
        result = assess_declared_components_list(spec)
        self.assertAlmostEqual(result["item_coverage"], 1.0, places=9)

    def test_requirement_met_exactly_is_not_a_shortfall(self):
        spec = self._spec(required_coverage=1.0)
        result = assess_declared_components_list(spec)
        self.assertAlmostEqual(
            result["item_coverage"], result["required_coverage"], places=9
        )
        self.assertEqual(result["verdict"], "issue")

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)

    def test_missing_deliveries_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_components_list({"items": [item()]})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_components_list(["items"])

    def test_out_of_range_required_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_components_list(self._spec(required_coverage=1.7))

    def test_boolean_required_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_components_list(self._spec(required_coverage=True))


if __name__ == "__main__":
    unittest.main()
