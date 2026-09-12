import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from structural_data_exchange_logic import (
    ALLOWED_FORMATS,
    DISCIPLINE_MAP,
    REQUIRED_FIELDS,
    build_traceability_matrix,
    categorize_items,
    check_icd_authorization,
    validate_item,
    validate_package,
)


def _item(**overrides):
    base = {
        "item_id":    "ITEM-001",
        "data_type":  "fem_model",
        "sender":     "structural-team",
        "receiver":   "analysis-team",
        "format":     "nastran_bdf",
        "version":    "1.0",
        "source_doc": "DRD-STR-001 Rev A",
    }
    base.update(overrides)
    return base


class TestValidateItemPass(unittest.TestCase):

    def test_valid_fem_nastran_passes(self):
        r = validate_item(_item())
        self.assertTrue(r["valid"])
        self.assertEqual(r["errors"], [])

    def test_valid_fem_abaqus_passes(self):
        r = validate_item(_item(format="abaqus_inp"))
        self.assertTrue(r["valid"])

    def test_valid_cad_step_passes(self):
        r = validate_item(_item(data_type="cad_model", format="step"))
        self.assertTrue(r["valid"])

    def test_valid_loads_csv_passes(self):
        r = validate_item(_item(data_type="loads_file", format="csv"))
        self.assertTrue(r["valid"])

    def test_valid_material_card_json_passes(self):
        r = validate_item(_item(data_type="material_card", format="json"))
        self.assertTrue(r["valid"])

    def test_valid_test_results_pdf_passes(self):
        r = validate_item(_item(data_type="test_results", format="pdf"))
        self.assertTrue(r["valid"])

    def test_valid_icd_docx_passes(self):
        r = validate_item(_item(data_type="icd", format="docx"))
        self.assertTrue(r["valid"])


class TestValidateItemFail(unittest.TestCase):

    def test_missing_item_id_fails(self):
        item = _item()
        del item["item_id"]
        r = validate_item(item)
        self.assertFalse(r["valid"])
        self.assertIn("missing_field:item_id", r["errors"])

    def test_empty_source_doc_fails(self):
        r = validate_item(_item(source_doc=""))
        self.assertFalse(r["valid"])
        self.assertTrue(any("source_doc" in e for e in r["errors"]))

    def test_whitespace_version_fails(self):
        r = validate_item(_item(version="   "))
        self.assertFalse(r["valid"])
        self.assertTrue(any("version" in e for e in r["errors"]))

    def test_unknown_data_type_fails(self):
        r = validate_item(_item(data_type="mystery_data"))
        self.assertFalse(r["valid"])
        self.assertTrue(any("unknown_data_type" in e for e in r["errors"]))

    def test_invalid_format_for_type_fails(self):
        r = validate_item(_item(data_type="fem_model", format="pdf"))
        self.assertFalse(r["valid"])
        self.assertTrue(any("invalid_format" in e for e in r["errors"]))

    def test_multiple_missing_fields_all_reported(self):
        r = validate_item({"item_id": "X"})
        self.assertFalse(r["valid"])
        self.assertGreater(len(r["errors"]), 3)

    def test_missing_sender_reported(self):
        item = _item()
        del item["sender"]
        r = validate_item(item)
        self.assertFalse(r["valid"])
        self.assertIn("missing_field:sender", r["errors"])

    def test_cad_model_with_txt_format_fails(self):
        r = validate_item(_item(data_type="cad_model", format="txt"))
        self.assertFalse(r["valid"])
        self.assertTrue(any("invalid_format" in e for e in r["errors"]))


class TestIcdAuthorization(unittest.TestCase):

    def test_matching_pair_is_authorized(self):
        item = _item(sender="team-a", receiver="team-b")
        self.assertTrue(check_icd_authorization(item, [("team-a", "team-b")]))

    def test_non_matching_pair_is_unauthorized(self):
        item = _item(sender="team-a", receiver="team-c")
        self.assertFalse(check_icd_authorization(item, [("team-a", "team-b")]))

    def test_empty_icd_list_rejects_every_pair(self):
        self.assertFalse(check_icd_authorization(_item(), []))

    def test_pair_order_matters(self):
        item = _item(sender="team-a", receiver="team-b")
        self.assertFalse(check_icd_authorization(item, [("team-b", "team-a")]))


class TestValidatePackage(unittest.TestCase):

    def test_all_valid_items_and_authorized_pairs_passes(self):
        items = [
            _item(item_id="A1", sender="str", receiver="ana"),
            _item(item_id="A2", data_type="loads_file", format="csv",
                  sender="str", receiver="ana"),
        ]
        r = validate_package(items, [("str", "ana")])
        self.assertTrue(r["valid"])
        self.assertEqual(r["unauthorized_pairs"], [])

    def test_unauthorized_pair_invalidates_package(self):
        items = [_item(item_id="B1", sender="str", receiver="mfg")]
        r = validate_package(items, [("str", "ana")])
        self.assertFalse(r["valid"])
        self.assertEqual(len(r["unauthorized_pairs"]), 1)
        self.assertEqual(r["unauthorized_pairs"][0]["pair"], ("str", "mfg"))

    def test_invalid_item_invalidates_package(self):
        items = [_item(item_id="C1", source_doc="")]
        r = validate_package(items, [("structural-team", "analysis-team")])
        self.assertFalse(r["valid"])

    def test_item_results_length_matches_input(self):
        items = [_item(item_id="D1"), _item(item_id="D2")]
        r = validate_package(items, [("structural-team", "analysis-team")])
        self.assertEqual(len(r["item_results"]), 2)

    def test_empty_package_is_valid(self):
        r = validate_package([], [])
        self.assertTrue(r["valid"])


class TestTraceabilityMatrix(unittest.TestCase):

    def test_unique_items_produce_full_matrix(self):
        items = [
            _item(item_id="T1"),
            _item(item_id="T2", data_type="cad_model", format="step"),
        ]
        r = build_traceability_matrix(items)
        self.assertTrue(r["traceable"])
        self.assertEqual(len(r["matrix"]), 2)
        self.assertEqual(r["duplicates"], [])

    def test_duplicate_item_id_flagged(self):
        items = [_item(item_id="T1"), _item(item_id="T1")]
        r = build_traceability_matrix(items)
        self.assertFalse(r["traceable"])
        self.assertIn("T1", r["duplicates"])

    def test_matrix_entries_contain_traceability_fields(self):
        r = build_traceability_matrix([_item(item_id="T3")])
        entry = r["matrix"][0]
        for key in ("item_id", "source_doc", "version", "data_type"):
            self.assertIn(key, entry)

    def test_empty_input_yields_empty_matrix(self):
        r = build_traceability_matrix([])
        self.assertEqual(r["matrix"], [])
        self.assertTrue(r["traceable"])

    def test_source_doc_preserved_in_matrix(self):
        r = build_traceability_matrix([_item(item_id="T4", source_doc="DRD-X Rev B")])
        self.assertEqual(r["matrix"][0]["source_doc"], "DRD-X Rev B")


class TestCategorizeItems(unittest.TestCase):

    def test_fem_model_goes_to_analysis(self):
        r = categorize_items([_item(item_id="F1", data_type="fem_model")])
        self.assertIn("F1", r["analysis"])
        self.assertNotIn("F1", r["uncategorized"])

    def test_material_card_in_analysis_and_manufacturing(self):
        r = categorize_items([_item(item_id="M1", data_type="material_card", format="csv")])
        self.assertIn("M1", r["analysis"])
        self.assertIn("M1", r["manufacturing"])

    def test_cad_model_goes_to_design(self):
        r = categorize_items([_item(item_id="C1", data_type="cad_model", format="step")])
        self.assertIn("C1", r["design"])

    def test_test_results_go_to_test_group(self):
        r = categorize_items([_item(item_id="R1", data_type="test_results", format="csv")])
        self.assertIn("R1", r["test"])

    def test_icd_goes_to_design(self):
        r = categorize_items([_item(item_id="I1", data_type="icd", format="pdf")])
        self.assertIn("I1", r["design"])

    def test_unknown_type_goes_to_uncategorized(self):
        r = categorize_items([_item(item_id="U1", data_type="mystery_data")])
        self.assertIn("U1", r["uncategorized"])
        self.assertNotIn("U1", r.get("analysis", []))
        self.assertNotIn("U1", r.get("design", []))

    def test_empty_list_returns_empty_groups(self):
        r = categorize_items([])
        for key in r:
            self.assertEqual(r[key], [], f"group '{key}' should be empty")


class TestConstants(unittest.TestCase):

    def test_allowed_formats_covers_all_expected_types(self):
        expected = {"fem_model", "cad_model", "loads_file", "material_card", "test_results", "icd"}
        self.assertEqual(set(ALLOWED_FORMATS.keys()), expected)

    def test_nastran_bdf_allowed_for_fem(self):
        self.assertIn("nastran_bdf", ALLOWED_FORMATS["fem_model"])

    def test_pdf_not_allowed_for_fem(self):
        self.assertNotIn("pdf", ALLOWED_FORMATS["fem_model"])

    def test_pdf_allowed_for_icd(self):
        self.assertIn("pdf", ALLOWED_FORMATS["icd"])

    def test_required_fields_tuple_complete(self):
        for field in ("item_id", "data_type", "sender", "receiver", "format", "version", "source_doc"):
            self.assertIn(field, REQUIRED_FIELDS)

    def test_discipline_map_has_expected_groups(self):
        for group in ("design", "analysis", "manufacturing", "test"):
            self.assertIn(group, DISCIPLINE_MAP)


if __name__ == "__main__":
    unittest.main()
