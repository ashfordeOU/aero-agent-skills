#!/usr/bin/env python3
"""Offline, deterministic contract test for e10_engineering_data_logic.
Run: python3 test_e10_engineering_data.py"""

import unittest

from e10_engineering_data_logic import (
    DATA_ITEM_TYPES,
    TYPE_CODES,
    assign_storage,
    authorize_distribution,
    identify_item,
    items_by_type,
    items_missing_configuration_control,
    link_configuration,
    may_distribute,
    parse_identifier,
    register_status,
)


class ParseIdentifierTests(unittest.TestCase):
    def test_valid_identifier(self):
        parsed = parse_identifier("ESA-DRW-0012-A")
        self.assertEqual(
            parsed,
            {"originator": "ESA", "type_code": "DRW", "number": "0012", "revision": "A"},
        )

    def test_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            parse_identifier("")

    def test_wrong_field_count_rejected(self):
        with self.assertRaises(ValueError):
            parse_identifier("ESA-DRW-0012")

    def test_unrecognized_type_code_rejected(self):
        with self.assertRaises(ValueError):
            parse_identifier("ESA-XYZ-0012-A")

    def test_non_numeric_number_rejected(self):
        with self.assertRaises(ValueError):
            parse_identifier("ESA-DRW-00AB-A")


class IdentifyItemTests(unittest.TestCase):
    def test_identify_success(self):
        record = identify_item("ESA-DRW-0012-A", "drawing", "ESA", "A", "Structure panel drawing")
        self.assertEqual(record["status"], "identified")
        self.assertFalse(record["configuration_controlled"])
        self.assertEqual(record["distribution_list"], ())

    def test_unknown_item_type_rejected(self):
        with self.assertRaises(ValueError):
            identify_item("ESA-DRW-0012-A", "blueprint", "ESA", "A", "desc")

    def test_empty_description_rejected(self):
        with self.assertRaises(ValueError):
            identify_item("ESA-DRW-0012-A", "drawing", "ESA", "A", "")

    def test_type_code_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            identify_item("ESA-DRW-0012-A", "specification", "ESA", "A", "desc")

    def test_originator_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            identify_item("ESA-DRW-0012-A", "drawing", "NASA", "A", "desc")

    def test_revision_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            identify_item("ESA-DRW-0012-A", "drawing", "ESA", "B", "desc")

    def test_all_item_types_have_codes(self):
        for item_type in DATA_ITEM_TYPES:
            self.assertIn(item_type, TYPE_CODES)


class AssignStorageTests(unittest.TestCase):
    def setUp(self):
        self.identified = identify_item(
            "ESA-SPC-0007-B", "specification", "ESA", "B", "Thermal control spec"
        )

    def test_assign_storage_success(self):
        stored = assign_storage(self.identified, "PDM-vault-1", 10)
        self.assertEqual(stored["status"], "stored")
        self.assertEqual(stored["storage_repository"], "PDM-vault-1")
        self.assertEqual(stored["retention_years"], 10)
        self.assertEqual(self.identified["status"], "identified")

    def test_wrong_status_rejected(self):
        stored = assign_storage(self.identified, "PDM-vault-1", 10)
        with self.assertRaises(ValueError):
            assign_storage(stored, "PDM-vault-2", 5)

    def test_empty_repository_rejected(self):
        with self.assertRaises(ValueError):
            assign_storage(self.identified, "", 10)

    def test_non_positive_retention_rejected(self):
        with self.assertRaises(ValueError):
            assign_storage(self.identified, "PDM-vault-1", 0)

    def test_non_integer_retention_rejected(self):
        with self.assertRaises(ValueError):
            assign_storage(self.identified, "PDM-vault-1", 5.5)

    def test_boolean_retention_rejected(self):
        with self.assertRaises(ValueError):
            assign_storage(self.identified, "PDM-vault-1", True)


class LinkConfigurationTests(unittest.TestCase):
    def setUp(self):
        identified = identify_item("ESA-MOD-0003-C", "model", "ESA", "C", "Thermal model")
        self.stored = assign_storage(identified, "PDM-vault-1", 15)

    def test_link_success(self):
        controlled = link_configuration(self.stored, "BL-2026-01")
        self.assertEqual(controlled["status"], "controlled")
        self.assertTrue(controlled["configuration_controlled"])
        self.assertEqual(controlled["baseline_id"], "BL-2026-01")
        self.assertEqual(self.stored["configuration_controlled"], False)

    def test_link_before_storage_rejected(self):
        identified = identify_item("ESA-MOD-0004-A", "model", "ESA", "A", "Structural model")
        with self.assertRaises(ValueError):
            link_configuration(identified, "BL-2026-01")

    def test_empty_baseline_id_rejected(self):
        with self.assertRaises(ValueError):
            link_configuration(self.stored, "")


class AuthorizeDistributionTests(unittest.TestCase):
    def setUp(self):
        identified = identify_item("ESA-RPT-0021-A", "report", "ESA", "A", "Verification report")
        stored = assign_storage(identified, "PDM-vault-2", 20)
        self.controlled = link_configuration(stored, "BL-2026-02")

    def test_authorize_success(self):
        distributed = authorize_distribution(self.controlled, ["subsystem-lead", "quality"])
        self.assertEqual(distributed["status"], "distributed")
        self.assertEqual(distributed["distribution_list"], ("subsystem-lead", "quality"))

    def test_not_controlled_rejected(self):
        identified = identify_item("ESA-RPT-0022-A", "report", "ESA", "A", "desc")
        with self.assertRaises(ValueError):
            authorize_distribution(identified, ["quality"])

    def test_empty_recipients_rejected(self):
        with self.assertRaises(ValueError):
            authorize_distribution(self.controlled, [])

    def test_duplicate_recipients_rejected(self):
        with self.assertRaises(ValueError):
            authorize_distribution(self.controlled, ["quality", "quality"])


class MayDistributeTests(unittest.TestCase):
    def test_identified_may_not_distribute(self):
        record = identify_item("ESA-ANL-0009-A", "analysis", "ESA", "A", "Loads analysis")
        self.assertFalse(may_distribute(record))

    def test_stored_may_not_distribute(self):
        identified = identify_item("ESA-ANL-0010-A", "analysis", "ESA", "A", "Loads analysis")
        stored = assign_storage(identified, "PDM-vault-1", 10)
        self.assertFalse(may_distribute(stored))

    def test_controlled_may_distribute(self):
        identified = identify_item("ESA-ANL-0011-A", "analysis", "ESA", "A", "Loads analysis")
        stored = assign_storage(identified, "PDM-vault-1", 10)
        controlled = link_configuration(stored, "BL-2026-03")
        self.assertTrue(may_distribute(controlled))

    def test_distributed_may_distribute(self):
        identified = identify_item("ESA-ANL-0012-A", "analysis", "ESA", "A", "Loads analysis")
        stored = assign_storage(identified, "PDM-vault-1", 10)
        controlled = link_configuration(stored, "BL-2026-03")
        distributed = authorize_distribution(controlled, ["quality"])
        self.assertTrue(may_distribute(distributed))


class RegisterQueriesTests(unittest.TestCase):
    def setUp(self):
        identified_a = identify_item("ESA-DRW-0001-A", "drawing", "ESA", "A", "Panel drawing")
        stored_a = assign_storage(identified_a, "PDM-vault-1", 10)
        controlled_a = link_configuration(stored_a, "BL-2026-01")
        self.distributed_a = authorize_distribution(controlled_a, ["quality"])

        identified_b = identify_item("ESA-SPC-0002-A", "specification", "ESA", "A", "Interface spec")
        self.stored_b = assign_storage(identified_b, "PDM-vault-1", 10)

        self.identified_c = identify_item("ESA-RPT-0003-A", "report", "ESA", "A", "Test report")

    def test_register_status_not_ready(self):
        ready, pending = register_status([self.distributed_a, self.stored_b, self.identified_c])
        self.assertFalse(ready)
        self.assertEqual(pending, [self.stored_b, self.identified_c])

    def test_register_status_ready(self):
        ready, pending = register_status([self.distributed_a])
        self.assertTrue(ready)
        self.assertEqual(pending, [])

    def test_items_missing_configuration_control(self):
        gaps = items_missing_configuration_control(
            [self.distributed_a, self.stored_b, self.identified_c]
        )
        self.assertEqual(gaps, [self.stored_b])

    def test_items_by_type(self):
        drawings = items_by_type([self.distributed_a, self.stored_b, self.identified_c], "drawing")
        self.assertEqual(drawings, [self.distributed_a])


if __name__ == "__main__":
    unittest.main()
