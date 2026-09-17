"""Contract tests for the clause 8.2.2 item-data-list and as-built logic."""

import unittest

from q6003_configuration_item_data_lists_logic import (
    BASE_FIELDS,
    COVERAGE_TOLERANCE,
    ITEM_KINDS,
    SERIALISED_KINDS,
    assess_data_list,
    build_as_built_index,
    build_data_list,
    identification_coverage,
    missing_serial_numbers,
    normalize_identifier,
    normalize_kind,
    reconcile_lists,
    required_fields,
    unbacked_deviations,
    validate_as_built_entry,
    validate_item,
)


def board_item(**overrides):
    base = {
        "kind": "hardware-assembly",
        "item_id": "ci-100",
        "part_number": "pn-4400-01",
        "revision": "c",
        "supplier": "unit-supplier",
    }
    base.update(overrides)
    return base


def device_item(**overrides):
    base = {
        "kind": "programmable-device",
        "item_id": "ci-200",
        "part_number": "pn-9000-07",
        "revision": "b",
        "supplier": "device-foundry",
        "device_technology": "flash-fpga",
    }
    base.update(overrides)
    return base


def document_item(**overrides):
    base = {
        "kind": "delivered-document",
        "item_id": "ci-300",
        "part_number": "doc-0021",
        "revision": "a",
        "supplier": "design-authority",
        "issue_reference": "issue-2",
    }
    base.update(overrides)
    return base


def full_spec(**overrides):
    base = {
        "items": [board_item(), device_item(), document_item()],
        "as_built": [
            {"item_id": "ci-100", "revision": "c", "serial_number": "sn-0001"},
            {"item_id": "ci-200", "revision": "b", "serial_number": "sn-0002"},
            {"item_id": "ci-300", "revision": "a"},
        ],
        "approved_waivers": [],
        "required_coverage": 1.0,
    }
    base.update(overrides)
    return base


class NormalisationTests(unittest.TestCase):
    def test_identifier_is_trimmed_and_upper_cased(self):
        self.assertEqual(normalize_identifier("  ci-100 ", "item_id"), "CI-100")

    def test_identifier_collapses_internal_whitespace(self):
        self.assertEqual(normalize_identifier("pn  4400", "part_number"), "PN 4400")

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_identifier("   ", "item_id")

    def test_non_string_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_identifier(17, "item_id")

    def test_kind_case_folded(self):
        self.assertEqual(normalize_kind(" Hardware-Assembly "), "hardware-assembly")

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_kind("unbuilt-widget")

    def test_kind_vocabulary_is_stable(self):
        self.assertIn("software-load", ITEM_KINDS)
        self.assertIn("programmable-device", SERIALISED_KINDS)


class RequiredFieldTests(unittest.TestCase):
    def test_every_kind_demands_the_base_fields(self):
        for kind in ITEM_KINDS:
            for field in BASE_FIELDS:
                self.assertIn(field, required_fields(kind))

    def test_software_load_demands_a_build_identifier(self):
        self.assertIn("build_identifier", required_fields("software-load"))

    def test_programmable_device_demands_its_technology(self):
        self.assertIn("device_technology", required_fields("programmable-device"))

    def test_missing_kind_specific_field_rejected(self):
        broken = device_item()
        del broken["device_technology"]
        with self.assertRaises(ValueError):
            validate_item(broken)

    def test_missing_base_field_rejected(self):
        broken = board_item()
        del broken["revision"]
        with self.assertRaises(ValueError):
            validate_item(broken)

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(["ci-100"])


class DataListTests(unittest.TestCase):
    def test_serialised_flag_follows_the_kind(self):
        self.assertTrue(validate_item(board_item())["serialised"])
        self.assertFalse(validate_item(document_item())["serialised"])

    def test_duplicate_item_identifier_rejected(self):
        with self.assertRaises(ValueError):
            build_data_list([board_item(), board_item(part_number="pn-other")])

    def test_case_difference_still_counts_as_a_duplicate(self):
        with self.assertRaises(ValueError):
            build_data_list([board_item(), board_item(item_id="CI-100")])

    def test_empty_data_list_rejected(self):
        with self.assertRaises(ValueError):
            build_data_list([])

    def test_deviation_reference_is_optional(self):
        self.assertIsNone(validate_item(board_item())["deviation_reference"])
        cited = validate_item(board_item(deviation_reference="dev-7"))
        self.assertEqual(cited["deviation_reference"], "DEV-7")


class AsBuiltTests(unittest.TestCase):
    def test_as_built_entry_needs_a_revision(self):
        with self.assertRaises(ValueError):
            validate_as_built_entry({"item_id": "ci-100"})

    def test_as_built_serial_is_optional(self):
        record = validate_as_built_entry({"item_id": "ci-100", "revision": "c"})
        self.assertIsNone(record["serial_number"])

    def test_repeated_item_lines_are_kept(self):
        index = build_as_built_index(
            [
                {"item_id": "ci-100", "revision": "c", "serial_number": "sn-1"},
                {"item_id": "ci-100", "revision": "c", "serial_number": "sn-2"},
            ]
        )
        self.assertEqual(len(index["CI-100"]), 2)

    def test_as_built_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            build_as_built_index({"item_id": "ci-100"})


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.data_list = build_data_list([board_item(), device_item(), document_item()])

    def test_clean_delivery_reconciles(self):
        index = build_as_built_index(full_spec()["as_built"])
        result = reconcile_lists(self.data_list, index)
        self.assertEqual(result["not_built"], [])
        self.assertEqual(result["not_listed"], [])
        self.assertEqual(result["revision_drift"], [])

    def test_listed_item_never_built_is_reported(self):
        index = build_as_built_index(
            [{"item_id": "ci-100", "revision": "c", "serial_number": "sn-1"}]
        )
        result = reconcile_lists(self.data_list, index)
        self.assertEqual(result["not_built"], ["CI-200", "CI-300"])

    def test_unlisted_delivered_element_is_reported(self):
        entries = full_spec()["as_built"] + [{"item_id": "ci-900", "revision": "a"}]
        result = reconcile_lists(self.data_list, build_as_built_index(entries))
        self.assertEqual(result["not_listed"], ["CI-900"])

    def test_revision_drift_names_both_revisions(self):
        entries = [
            {"item_id": "ci-100", "revision": "d", "serial_number": "sn-1"},
            {"item_id": "ci-200", "revision": "b", "serial_number": "sn-2"},
            {"item_id": "ci-300", "revision": "a"},
        ]
        result = reconcile_lists(self.data_list, build_as_built_index(entries))
        self.assertEqual(len(result["revision_drift"]), 1)
        drift = result["revision_drift"][0]
        self.assertEqual(drift["listed_revision"], "C")
        self.assertEqual(drift["as_built_revision"], "D")

    def test_repeated_serial_on_one_item_is_reported(self):
        entries = [
            {"item_id": "ci-100", "revision": "c", "serial_number": "sn-1"},
            {"item_id": "ci-100", "revision": "c", "serial_number": "sn-1"},
        ]
        result = reconcile_lists(self.data_list, build_as_built_index(entries))
        self.assertEqual(result["repeated_serials"][0]["serial_number"], "SN-1")

    def test_empty_data_list_mapping_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_lists({}, {})


class DeliveryObligationTests(unittest.TestCase):
    def setUp(self):
        self.data_list = build_data_list([board_item(), device_item(), document_item()])

    def test_serialised_item_without_a_serial_is_reported(self):
        entries = [
            {"item_id": "ci-100", "revision": "c"},
            {"item_id": "ci-200", "revision": "b", "serial_number": "sn-2"},
            {"item_id": "ci-300", "revision": "a"},
        ]
        gaps = missing_serial_numbers(self.data_list, build_as_built_index(entries))
        self.assertEqual(gaps, ["CI-100"])

    def test_document_needs_no_serial(self):
        index = build_as_built_index(full_spec()["as_built"])
        self.assertEqual(missing_serial_numbers(self.data_list, index), [])

    def test_deviation_without_an_approved_waiver_is_reported(self):
        listed = build_data_list(
            [board_item(deviation_reference="dev-7"), device_item(), document_item()]
        )
        gaps = unbacked_deviations(listed, [])
        self.assertEqual(gaps[0]["deviation_reference"], "DEV-7")

    def test_approved_waiver_clears_the_deviation(self):
        listed = build_data_list(
            [board_item(deviation_reference="dev-7"), device_item(), document_item()]
        )
        self.assertEqual(unbacked_deviations(listed, ["DEV-7"]), [])

    def test_waiver_matching_ignores_case_and_padding(self):
        listed = build_data_list([board_item(deviation_reference="dev-7")])
        self.assertEqual(unbacked_deviations(listed, ["  dev-7 "]), [])

    def test_waiver_argument_must_be_a_sequence(self):
        listed = build_data_list([board_item()])
        with self.assertRaises(ValueError):
            unbacked_deviations(listed, 7)


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.data_list = build_data_list([board_item(), device_item(), document_item()])

    def test_full_coverage_on_a_clean_delivery(self):
        index = build_as_built_index(full_spec()["as_built"])
        self.assertAlmostEqual(
            identification_coverage(self.data_list, index), 1.0, places=9
        )

    def test_coverage_drops_for_an_unbuilt_item(self):
        entries = [
            {"item_id": "ci-100", "revision": "c", "serial_number": "sn-1"},
            {"item_id": "ci-200", "revision": "b", "serial_number": "sn-2"},
        ]
        value = identification_coverage(self.data_list, build_as_built_index(entries))
        self.assertAlmostEqual(value, 2.0 / 3.0, places=9)

    def test_revision_drift_does_not_count_as_identified(self):
        entries = [
            {"item_id": "ci-100", "revision": "d", "serial_number": "sn-1"},
            {"item_id": "ci-200", "revision": "b", "serial_number": "sn-2"},
            {"item_id": "ci-300", "revision": "a"},
        ]
        value = identification_coverage(self.data_list, build_as_built_index(entries))
        self.assertAlmostEqual(value, 2.0 / 3.0, places=9)

    def test_missing_serial_does_not_count_as_identified(self):
        entries = [
            {"item_id": "ci-100", "revision": "c"},
            {"item_id": "ci-200", "revision": "b", "serial_number": "sn-2"},
            {"item_id": "ci-300", "revision": "a"},
        ]
        value = identification_coverage(self.data_list, build_as_built_index(entries))
        self.assertAlmostEqual(value, 2.0 / 3.0, places=9)

    def test_tolerance_is_small_and_positive(self):
        self.assertGreater(COVERAGE_TOLERANCE, 0.0)
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


class AssessmentTests(unittest.TestCase):
    def test_clean_delivery_is_deliverable(self):
        result = assess_data_list(full_spec())
        self.assertTrue(result["deliverable"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["item_count"], 3)
        self.assertEqual(result["as_built_line_count"], 3)

    def test_exactly_met_coverage_floor_passes(self):
        entries = [
            {"item_id": "ci-100", "revision": "c", "serial_number": "sn-1"},
            {"item_id": "ci-200", "revision": "b", "serial_number": "sn-2"},
        ]
        result = assess_data_list(
            full_spec(as_built=entries, required_coverage=2.0 / 3.0)
        )
        self.assertTrue(result["coverage_ok"])
        self.assertAlmostEqual(
            result["identification_coverage"], result["required_coverage"], places=9
        )

    def test_shortfall_below_the_floor_is_a_finding(self):
        entries = [{"item_id": "ci-100", "revision": "c", "serial_number": "sn-1"}]
        result = assess_data_list(full_spec(as_built=entries))
        self.assertFalse(result["coverage_ok"])
        self.assertFalse(result["deliverable"])

    def test_unbacked_deviation_blocks_the_delivery(self):
        spec = full_spec(
            items=[
                board_item(deviation_reference="dev-7"),
                device_item(),
                document_item(),
            ]
        )
        result = assess_data_list(spec)
        self.assertFalse(result["deliverable"])
        self.assertTrue(
            any("no approved waiver" in line for line in result["findings"])
        )

    def test_out_of_range_required_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_data_list(full_spec(required_coverage=1.5))

    def test_boolean_required_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_data_list(full_spec(required_coverage=True))

    def test_spec_missing_as_built_rejected(self):
        spec = full_spec()
        del spec["as_built"]
        with self.assertRaises(ValueError):
            assess_data_list(spec)

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_data_list([("items", [])])

    def test_findings_name_every_defect_kind(self):
        spec = full_spec(
            items=[
                board_item(deviation_reference="dev-7"),
                device_item(),
                document_item(),
            ],
            as_built=[
                {"item_id": "ci-100", "revision": "d"},
                {"item_id": "ci-900", "revision": "a"},
            ],
        )
        result = assess_data_list(spec)
        joined = " | ".join(result["findings"])
        self.assertIn("no as-built record line", joined)
        self.assertIn("appears in no data-list item", joined)
        self.assertIn("was built at revision", joined)
        self.assertIn("without a serial number", joined)
        self.assertIn("no approved waiver", joined)


if __name__ == "__main__":
    unittest.main()
