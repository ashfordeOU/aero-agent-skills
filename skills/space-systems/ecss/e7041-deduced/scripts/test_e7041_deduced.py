"""Contract tests for the clause 7.3.12 deduced data-type logic."""

import unittest

from e7041_deduced_logic import (
    FIELD_KINDS,
    assess_deduced_layout,
    mapping_coverage,
    resolve_layout,
    resolve_selector_value,
    type_size_bits,
    validate_catalogue,
    validate_layout,
)

CATALOGUE = {
    "uint8": 8,
    "uint16": 16,
    "int32": 32,
    "real32": 32,
}

LAYOUT = [
    {"name": "header", "kind": "fixed", "size_bits": 48},
    {"name": "parameter-id", "kind": "selector", "size_bits": 2, "values": [0, 1, 2, 3]},
    {"name": "parameter-value", "kind": "deduced", "deduced_from": "parameter-id",
     "mapping": {0: "uint8", 1: "uint16", 2: "int32", 3: "real32"}},
]


class CatalogueTests(unittest.TestCase):
    def test_a_catalogue_normalises(self):
        self.assertEqual(validate_catalogue(CATALOGUE)["uint16"], 16)

    def test_a_named_type_is_sized(self):
        self.assertEqual(type_size_bits("int32", CATALOGUE), 32)

    def test_a_type_absent_from_the_catalogue_refused(self):
        with self.assertRaises(ValueError):
            type_size_bits("uint64", CATALOGUE)

    def test_an_empty_catalogue_refused(self):
        with self.assertRaises(ValueError):
            validate_catalogue({})

    def test_a_zero_width_type_refused(self):
        with self.assertRaises(ValueError):
            validate_catalogue({"void": 0})

    def test_a_non_integer_width_refused(self):
        with self.assertRaises(ValueError):
            validate_catalogue({"uint8": "8"})


class LayoutTests(unittest.TestCase):
    def test_the_three_field_kinds_are_the_declared_ones(self):
        self.assertEqual(set(FIELD_KINDS), {"fixed", "selector", "deduced"})

    def test_a_valid_layout_records_positions(self):
        out = validate_layout(LAYOUT)
        self.assertEqual([f["position"] for f in out], [0, 1, 2])

    def test_selector_values_are_sorted_and_deduplicated(self):
        out = validate_layout([
            {"name": "sel", "kind": "selector", "size_bits": 3, "values": [4, 1, 1, 0]},
            {"name": "val", "kind": "deduced", "deduced_from": "sel",
             "mapping": {0: "uint8", 1: "uint8", 4: "uint8"}},
        ])
        self.assertEqual(out[0]["values"], [0, 1, 4])

    def test_a_selector_after_its_deduced_field_refused(self):
        with self.assertRaises(ValueError):
            validate_layout([
                {"name": "val", "kind": "deduced", "deduced_from": "sel",
                 "mapping": {0: "uint8"}},
                {"name": "sel", "kind": "selector", "size_bits": 2, "values": [0]},
            ])

    def test_a_deduced_field_pointing_at_nothing_refused(self):
        with self.assertRaises(ValueError):
            validate_layout([
                {"name": "val", "kind": "deduced", "deduced_from": "absent",
                 "mapping": {0: "uint8"}},
            ])

    def test_a_duplicate_field_name_refused(self):
        with self.assertRaises(ValueError):
            validate_layout([
                {"name": "a", "kind": "fixed", "size_bits": 8},
                {"name": "a", "kind": "fixed", "size_bits": 8},
            ])

    def test_an_unknown_field_kind_refused(self):
        with self.assertRaises(ValueError):
            validate_layout([{"name": "a", "kind": "computed", "size_bits": 8}])

    def test_a_selector_value_wider_than_its_field_refused(self):
        with self.assertRaises(ValueError):
            validate_layout([
                {"name": "sel", "kind": "selector", "size_bits": 2, "values": [4]},
            ])

    def test_an_empty_selector_value_set_refused(self):
        with self.assertRaises(ValueError):
            validate_layout([
                {"name": "sel", "kind": "selector", "size_bits": 2, "values": []},
            ])

    def test_an_empty_mapping_refused(self):
        with self.assertRaises(ValueError):
            validate_layout([
                {"name": "sel", "kind": "selector", "size_bits": 2, "values": [0]},
                {"name": "val", "kind": "deduced", "deduced_from": "sel", "mapping": {}},
            ])

    def test_an_empty_layout_refused(self):
        with self.assertRaises(ValueError):
            validate_layout([])

    def test_a_chain_of_deductions_is_accepted_in_order(self):
        out = validate_layout([
            {"name": "sel", "kind": "selector", "size_bits": 1, "values": [0, 1]},
            {"name": "mid", "kind": "deduced", "deduced_from": "sel",
             "mapping": {0: "uint8", 1: "uint16"}},
            {"name": "tail", "kind": "deduced", "deduced_from": "sel",
             "mapping": {0: "uint16", 1: "int32"}},
        ])
        self.assertEqual(len(out), 3)


class CoverageTests(unittest.TestCase):
    def test_a_total_mapping_covers_the_whole_space(self):
        report = mapping_coverage(2, {0: "a", 1: "a", 2: "a", 3: "a"})
        self.assertAlmostEqual(report["fraction"], 1.0, places=9)

    def test_a_partial_mapping_reports_its_fraction(self):
        report = mapping_coverage(3, {0: "a", 1: "a"})
        self.assertEqual(report["space"], 8)
        self.assertAlmostEqual(report["fraction"], 0.25, places=9)

    def test_values_outside_the_space_do_not_count_as_covered(self):
        report = mapping_coverage(2, {0: "a", 99: "a"})
        self.assertEqual(report["covered"], 1)

    def test_a_zero_width_selector_refused(self):
        with self.assertRaises(ValueError):
            mapping_coverage(0, {0: "a"})

    def test_a_non_mapping_refused(self):
        with self.assertRaises(ValueError):
            mapping_coverage(2, [0, 1])


class ResolutionTests(unittest.TestCase):
    def test_a_selector_value_settles_a_type(self):
        field = validate_layout(LAYOUT)[2]
        out = resolve_selector_value(field, 1, CATALOGUE)
        self.assertEqual(out["type"], "uint16")
        self.assertEqual(out["size_bits"], 16)

    def test_an_unmapped_selector_value_refused(self):
        field = validate_layout(LAYOUT)[2]
        with self.assertRaises(ValueError):
            resolve_selector_value(field, 7, CATALOGUE)

    def test_resolving_a_non_deduced_field_refused(self):
        field = validate_layout(LAYOUT)[0]
        with self.assertRaises(ValueError):
            resolve_selector_value(field, 0, CATALOGUE)

    def test_a_negative_selector_value_refused(self):
        field = validate_layout(LAYOUT)[2]
        with self.assertRaises(ValueError):
            resolve_selector_value(field, -1, CATALOGUE)

    def test_the_layout_resolves_to_a_total_width(self):
        out = resolve_layout(LAYOUT, {"parameter-id": 1}, CATALOGUE)
        self.assertEqual(out["total_bits"], 48 + 2 + 16)

    def test_a_different_selector_value_moves_every_later_field(self):
        narrow = resolve_layout(LAYOUT, {"parameter-id": 0}, CATALOGUE)
        wide = resolve_layout(LAYOUT, {"parameter-id": 2}, CATALOGUE)
        self.assertNotEqual(narrow["total_bits"], wide["total_bits"])

    def test_the_resolved_field_carries_its_settled_type(self):
        out = resolve_layout(LAYOUT, {"parameter-id": 3}, CATALOGUE)
        self.assertEqual(out["fields"][2]["type"], "real32")

    def test_octet_alignment_is_reported(self):
        out = resolve_layout(LAYOUT, {"parameter-id": 0}, CATALOGUE)
        self.assertFalse(out["octet_aligned"])

    def test_a_missing_selector_value_refused(self):
        with self.assertRaises(ValueError):
            resolve_layout(LAYOUT, {}, CATALOGUE)

    def test_a_selector_value_the_definition_excludes_refused(self):
        layout = [
            {"name": "sel", "kind": "selector", "size_bits": 3, "values": [0, 1]},
            {"name": "val", "kind": "deduced", "deduced_from": "sel",
             "mapping": {0: "uint8", 1: "uint16"}},
        ]
        with self.assertRaises(ValueError):
            resolve_layout(layout, {"sel": 5}, CATALOGUE)

    def test_non_mapping_selector_values_refused(self):
        with self.assertRaises(ValueError):
            resolve_layout(LAYOUT, [1], CATALOGUE)


class AssessmentTests(unittest.TestCase):
    def test_a_total_mapping_reports_no_findings(self):
        report = assess_deduced_layout(LAYOUT, CATALOGUE)
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["resolvable"])

    def test_an_unmapped_admitted_value_is_a_finding(self):
        layout = [
            {"name": "sel", "kind": "selector", "size_bits": 2, "values": [0, 1, 2]},
            {"name": "val", "kind": "deduced", "deduced_from": "sel",
             "mapping": {0: "uint8", 1: "uint16"}},
        ]
        report = assess_deduced_layout(layout, CATALOGUE)
        self.assertTrue(any("unreadable from that field onwards" in f
                            for f in report["findings"]))

    def test_a_mapping_onto_an_unknown_type_is_a_finding(self):
        layout = [
            {"name": "sel", "kind": "selector", "size_bits": 1, "values": [0, 1]},
            {"name": "val", "kind": "deduced", "deduced_from": "sel",
             "mapping": {0: "uint8", 1: "uint64"}},
        ]
        report = assess_deduced_layout(layout, CATALOGUE)
        self.assertTrue(any("absent from the catalogue" in f for f in report["findings"]))

    def test_a_mapping_entry_the_selector_never_takes_is_a_finding(self):
        layout = [
            {"name": "sel", "kind": "selector", "size_bits": 2, "values": [0, 1]},
            {"name": "val", "kind": "deduced", "deduced_from": "sel",
             "mapping": {0: "uint8", 1: "uint16", 3: "int32"}},
        ]
        report = assess_deduced_layout(layout, CATALOGUE)
        self.assertTrue(any("never takes" in f for f in report["findings"]))

    def test_a_layout_with_no_deduced_field_is_out_of_scope(self):
        report = assess_deduced_layout(
            [{"name": "a", "kind": "fixed", "size_bits": 8}], CATALOGUE
        )
        self.assertTrue(any("does not apply" in f for f in report["findings"]))

    def test_a_deduced_field_settled_by_a_fixed_field_is_a_finding(self):
        layout = [
            {"name": "plain", "kind": "fixed", "size_bits": 8},
            {"name": "val", "kind": "deduced", "deduced_from": "plain",
             "mapping": {0: "uint8"}},
        ]
        report = assess_deduced_layout(layout, CATALOGUE)
        self.assertTrue(any("not a selector field" in f for f in report["findings"]))

    def test_samples_of_different_widths_mark_the_packet_variable(self):
        report = assess_deduced_layout(
            LAYOUT, CATALOGUE,
            [{"parameter-id": 0}, {"parameter-id": 2}],
        )
        self.assertTrue(report["variable_length_packet"])
        self.assertEqual(len(report["distinct_widths_bits"]), 2)

    def test_one_sample_width_is_not_variable(self):
        report = assess_deduced_layout(LAYOUT, CATALOGUE, [{"parameter-id": 1}])
        self.assertFalse(report["variable_length_packet"])

    def test_coverage_is_reported_per_deduced_field(self):
        report = assess_deduced_layout(LAYOUT, CATALOGUE)
        self.assertAlmostEqual(report["coverage"]["parameter-value"]["fraction"], 1.0,
                               places=9)

    def test_an_unresolvable_sample_is_a_finding(self):
        report = assess_deduced_layout(LAYOUT, CATALOGUE, [{}])
        self.assertTrue(any("does not resolve" in f for f in report["findings"]))

    def test_the_deduced_field_names_are_listed(self):
        report = assess_deduced_layout(LAYOUT, CATALOGUE)
        self.assertEqual(report["deduced_fields"], ["parameter-value"])


if __name__ == "__main__":
    unittest.main()
