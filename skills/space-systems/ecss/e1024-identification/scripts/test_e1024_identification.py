"""
Gate 3 contract tests for e1024-identification.
Stdlib unittest, offline, deterministic.  Run:  python3 test_e1024_identification.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1024_identification_logic import (
    build_interface_record,
    build_interface_tree,
    check_identifier_unique,
    generate_identifier,
    get_category_info,
    list_categories,
    normalize_category,
    validate_interface_list,
)


# ---------------------------------------------------------------------------
# normalize_category
# ---------------------------------------------------------------------------

class TestNormalizeCategory(unittest.TestCase):

    def test_canonical_mechanical_passes(self):
        self.assertEqual(normalize_category("mechanical"), "mechanical")

    def test_canonical_electrical_passes(self):
        self.assertEqual(normalize_category("electrical"), "electrical")

    def test_alias_elec_maps_to_electrical(self):
        self.assertEqual(normalize_category("elec"), "electrical")

    def test_alias_therm_maps_to_thermal(self):
        self.assertEqual(normalize_category("therm"), "thermal")

    def test_alias_sw_maps_to_data(self):
        self.assertEqual(normalize_category("sw"), "data")

    def test_alias_radio_maps_to_rf(self):
        self.assertEqual(normalize_category("radio"), "rf")

    def test_case_insensitive_upper(self):
        self.assertEqual(normalize_category("MECHANICAL"), "mechanical")

    def test_case_insensitive_mixed(self):
        self.assertEqual(normalize_category("Thermal"), "thermal")

    def test_unknown_category_raises_value_error(self):
        with self.assertRaises(ValueError):
            normalize_category("pneumatic")

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            normalize_category("")

    def test_optical_canonical(self):
        self.assertEqual(normalize_category("optical"), "optical")

    def test_fluid_canonical(self):
        self.assertEqual(normalize_category("fluid"), "fluid")


# ---------------------------------------------------------------------------
# get_category_info
# ---------------------------------------------------------------------------

class TestGetCategoryInfo(unittest.TestCase):

    def test_mechanical_has_code_mec(self):
        self.assertEqual(get_category_info("mechanical")["code"], "MEC")

    def test_electrical_has_code_elc(self):
        self.assertEqual(get_category_info("electrical")["code"], "ELC")

    def test_data_has_code_dat(self):
        self.assertEqual(get_category_info("data")["code"], "DAT")

    def test_thermal_has_code_thm(self):
        self.assertEqual(get_category_info("thermal")["code"], "THM")

    def test_fluid_has_code_fld(self):
        self.assertEqual(get_category_info("fluid")["code"], "FLD")

    def test_rf_has_code_rf_(self):
        self.assertEqual(get_category_info("rf")["code"], "RF_")

    def test_optical_has_code_opt(self):
        self.assertEqual(get_category_info("optical")["code"], "OPT")

    def test_returns_dict(self):
        self.assertIsInstance(get_category_info("data"), dict)

    def test_result_has_examples_key(self):
        self.assertIn("examples", get_category_info("mechanical"))

    def test_invalid_category_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_category_info("gravitational")

    def test_alias_accepted_by_get_info(self):
        info = get_category_info("elec")
        self.assertEqual(info["code"], "ELC")

    def test_result_is_independent_copy(self):
        info = get_category_info("thermal")
        info["code"] = "XXX"
        self.assertEqual(get_category_info("thermal")["code"], "THM")


# ---------------------------------------------------------------------------
# generate_identifier
# ---------------------------------------------------------------------------

class TestGenerateIdentifier(unittest.TestCase):

    def test_basic_format_sc_aocs_elc(self):
        ident = generate_identifier("SC", "AOCS", "electrical", 1)
        self.assertEqual(ident, "SC-AOCS-ELC-001")

    def test_seq_zero_padded_to_three_digits(self):
        ident = generate_identifier("SC", "AOCS", "mechanical", 5)
        self.assertEqual(ident, "SC-AOCS-MEC-005")

    def test_seq_three_digits_no_pad(self):
        ident = generate_identifier("SC", "STR", "thermal", 100)
        self.assertEqual(ident, "SC-STR-THM-100")

    def test_sides_normalized_to_uppercase(self):
        ident = generate_identifier("sc", "obdh", "data", 1)
        self.assertEqual(ident, "SC-OBDH-DAT-001")

    def test_rf_category_code(self):
        ident = generate_identifier("SC", "GS", "rf", 1)
        self.assertEqual(ident, "SC-GS-RF_-001")

    def test_optical_category_code(self):
        ident = generate_identifier("PLM", "CAM", "optical", 2)
        self.assertEqual(ident, "PLM-CAM-OPT-002")

    def test_empty_side_a_raises_value_error(self):
        with self.assertRaises(ValueError):
            generate_identifier("", "AOCS", "electrical", 1)

    def test_empty_side_b_raises_value_error(self):
        with self.assertRaises(ValueError):
            generate_identifier("SC", "", "electrical", 1)

    def test_seq_zero_raises_value_error(self):
        with self.assertRaises(ValueError):
            generate_identifier("SC", "AOCS", "electrical", 0)

    def test_seq_negative_raises_value_error(self):
        with self.assertRaises(ValueError):
            generate_identifier("SC", "AOCS", "electrical", -1)

    def test_alias_accepted_in_identifier(self):
        ident = generate_identifier("SC", "PROP", "fld", 1)
        self.assertEqual(ident, "SC-PROP-FLD-001")


# ---------------------------------------------------------------------------
# build_interface_record
# ---------------------------------------------------------------------------

class TestBuildInterfaceRecord(unittest.TestCase):

    def test_record_has_identifier(self):
        rec = build_interface_record("SC", "AOCS", "electrical", 1)
        self.assertIn("identifier", rec)

    def test_identifier_matches_generate(self):
        rec = build_interface_record("SC", "AOCS", "electrical", 1)
        self.assertEqual(rec["identifier"], "SC-AOCS-ELC-001")

    def test_record_has_all_required_keys(self):
        rec = build_interface_record("SC", "AOCS", "mechanical", 1)
        for key in ("identifier", "side_a", "side_b", "category",
                    "category_code", "seq", "description", "complete"):
            self.assertIn(key, rec)

    def test_record_complete_is_true(self):
        rec = build_interface_record("SC", "AOCS", "data", 1)
        self.assertTrue(rec["complete"])

    def test_side_a_normalized_to_upper(self):
        rec = build_interface_record("sc", "obdh", "data", 1)
        self.assertEqual(rec["side_a"], "SC")

    def test_side_b_normalized_to_upper(self):
        rec = build_interface_record("SC", "obdh", "data", 1)
        self.assertEqual(rec["side_b"], "OBDH")

    def test_category_stored_as_canonical(self):
        rec = build_interface_record("SC", "STR", "mec", 1)
        self.assertEqual(rec["category"], "mechanical")

    def test_description_stored(self):
        rec = build_interface_record("SC", "AOCS", "electrical", 1,
                                     description="28V unregulated power bus")
        self.assertEqual(rec["description"], "28V unregulated power bus")

    def test_self_interface_raises_value_error(self):
        with self.assertRaises(ValueError):
            build_interface_record("SC", "SC", "mechanical", 1)

    def test_self_interface_case_insensitive(self):
        with self.assertRaises(ValueError):
            build_interface_record("aocs", "AOCS", "electrical", 1)

    def test_invalid_category_raises_value_error(self):
        with self.assertRaises(ValueError):
            build_interface_record("SC", "AOCS", "nuclear", 1)

    def test_seq_stored_as_int(self):
        rec = build_interface_record("SC", "AOCS", "thermal", 3)
        self.assertEqual(rec["seq"], 3)


# ---------------------------------------------------------------------------
# check_identifier_unique
# ---------------------------------------------------------------------------

class TestCheckIdentifierUnique(unittest.TestCase):

    def test_empty_list_returns_empty(self):
        self.assertEqual(check_identifier_unique([]), [])

    def test_unique_identifiers_returns_empty(self):
        recs = [
            build_interface_record("SC", "AOCS", "electrical", 1),
            build_interface_record("SC", "AOCS", "mechanical", 1),
        ]
        self.assertEqual(check_identifier_unique(recs), [])

    def test_duplicate_detected(self):
        rec = build_interface_record("SC", "AOCS", "electrical", 1)
        duplicates = check_identifier_unique([rec, rec])
        self.assertIn("SC-AOCS-ELC-001", duplicates)

    def test_no_false_positives_across_categories(self):
        recs = [
            build_interface_record("SC", "STR", "mechanical", 1),
            build_interface_record("SC", "STR", "thermal", 1),
            build_interface_record("SC", "STR", "electrical", 1),
        ]
        self.assertEqual(check_identifier_unique(recs), [])

    def test_returns_list(self):
        self.assertIsInstance(check_identifier_unique([]), list)


# ---------------------------------------------------------------------------
# validate_interface_list
# ---------------------------------------------------------------------------

class TestValidateInterfaceList(unittest.TestCase):

    def test_empty_list_is_valid(self):
        result = validate_interface_list([])
        self.assertTrue(result["valid"])
        self.assertEqual(result["issues"], [])

    def test_valid_records_pass(self):
        recs = [
            build_interface_record("SC", "AOCS", "electrical", 1),
            build_interface_record("SC", "PROP", "fluid", 1),
            build_interface_record("SC", "GS", "rf", 1),
        ]
        result = validate_interface_list(recs)
        self.assertTrue(result["valid"])

    def test_duplicate_identifier_fails(self):
        rec = build_interface_record("SC", "AOCS", "electrical", 1)
        result = validate_interface_list([rec, rec])
        self.assertFalse(result["valid"])
        self.assertTrue(any("Duplicate" in issue for issue in result["issues"]))

    def test_missing_side_a_fails(self):
        rec = build_interface_record("SC", "OBDH", "data", 1)
        rec["side_a"] = ""
        result = validate_interface_list([rec])
        self.assertFalse(result["valid"])

    def test_missing_category_fails(self):
        rec = build_interface_record("SC", "OBDH", "data", 1)
        rec["category"] = ""
        result = validate_interface_list([rec])
        self.assertFalse(result["valid"])

    def test_seq_zero_fails(self):
        rec = {"identifier": "SC-STR-MEC-000", "side_a": "SC", "side_b": "STR",
               "category": "mechanical", "category_code": "MEC",
               "seq": 0, "description": "", "complete": False}
        result = validate_interface_list([rec])
        self.assertFalse(result["valid"])

    def test_unknown_category_fails(self):
        rec = {"identifier": "SC-STR-XYZ-001", "side_a": "SC", "side_b": "STR",
               "category": "pneumatic", "category_code": "XYZ",
               "seq": 1, "description": "", "complete": False}
        result = validate_interface_list([rec])
        self.assertFalse(result["valid"])

    def test_result_has_valid_and_issues_keys(self):
        result = validate_interface_list([])
        self.assertIn("valid", result)
        self.assertIn("issues", result)

    def test_issues_is_list(self):
        result = validate_interface_list([])
        self.assertIsInstance(result["issues"], list)

    def test_self_interface_in_raw_dict_fails(self):
        rec = {"identifier": "SC-SC-MEC-001", "side_a": "SC", "side_b": "SC",
               "category": "mechanical", "category_code": "MEC",
               "seq": 1, "description": "", "complete": False}
        result = validate_interface_list([rec])
        self.assertFalse(result["valid"])


# ---------------------------------------------------------------------------
# build_interface_tree
# ---------------------------------------------------------------------------

class TestBuildInterfaceTree(unittest.TestCase):

    def test_empty_list_returns_empty_tree(self):
        self.assertEqual(build_interface_tree([]), {})

    def test_single_record_creates_owner_key(self):
        rec = build_interface_record("SC", "AOCS", "electrical", 1)
        tree = build_interface_tree([rec])
        self.assertIn("SC", tree)

    def test_records_grouped_by_side_a(self):
        recs = [
            build_interface_record("SC", "AOCS", "electrical", 1),
            build_interface_record("SC", "PROP", "fluid", 1),
            build_interface_record("AOCS", "IMU", "data", 1),
        ]
        tree = build_interface_tree(recs)
        self.assertEqual(len(tree["SC"]), 2)
        self.assertEqual(len(tree["AOCS"]), 1)

    def test_all_identifiers_preserved_in_tree(self):
        recs = [
            build_interface_record("SC", "AOCS", "electrical", 1),
            build_interface_record("SC", "STR", "mechanical", 1),
            build_interface_record("PLM", "CAM", "optical", 1),
        ]
        tree = build_interface_tree(recs)
        all_ids = {rec["identifier"] for group in tree.values() for rec in group}
        expected = {r["identifier"] for r in recs}
        self.assertEqual(all_ids, expected)

    def test_tree_records_are_independent_copies(self):
        rec = build_interface_record("SC", "AOCS", "electrical", 1)
        tree = build_interface_tree([rec])
        tree["SC"][0]["identifier"] = "MUTATED"
        fresh_tree = build_interface_tree([rec])
        self.assertEqual(fresh_tree["SC"][0]["identifier"], "SC-AOCS-ELC-001")

    def test_returns_dict(self):
        self.assertIsInstance(build_interface_tree([]), dict)


# ---------------------------------------------------------------------------
# list_categories
# ---------------------------------------------------------------------------

class TestListCategories(unittest.TestCase):

    def test_returns_seven_categories(self):
        self.assertEqual(len(list_categories()), 7)

    def test_contains_all_canonical_keys(self):
        cats = list_categories()
        for expected in ("mechanical", "electrical", "data", "thermal",
                         "fluid", "rf", "optical"):
            self.assertIn(expected, cats)

    def test_returns_list(self):
        self.assertIsInstance(list_categories(), list)


if __name__ == "__main__":
    unittest.main()
