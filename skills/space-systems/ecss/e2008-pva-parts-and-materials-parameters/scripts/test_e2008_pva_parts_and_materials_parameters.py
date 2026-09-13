#!/usr/bin/env python3
"""Contract test for the PVA parts, materials and processes parameters (offline)."""

import copy
import unittest

from e2008_pva_parts_and_materials_parameters_logic import (
    DEFAULT_PMP_POLICY,
    ENTRY_KINDS,
    LIST_NOT_TRACKED,
    LIST_TRACKED,
    NOT_ACCEPTABLE,
    PARAMETERS_INCOMPLETE,
    PARAMETERS_TRACKED,
    PROCUREMENT_LEVELS,
    REQUIRED_PARAMETERS,
    WAIVER_REQUIRED,
    assess_pmp_entry,
    audit_pmp_list,
    missing_parameters,
    outgassing_screen,
    parameter_completeness_fraction,
    procurement_disposition,
    required_parameters,
    shelf_life_status,
    validate_pmp_policy,
)

PART = {
    "kind": "part",
    "parameters": {
        "identification": "string bypass diode",
        "manufacturer": "supplier A",
        "lot-or-batch": "lot 7734",
        "specification-reference": "drawing sheet 3",
        "procurement-level": "space-qualified",
    },
}

MATERIAL = {
    "kind": "material",
    "parameters": {
        "identification": "cell-to-coverglass adhesive",
        "manufacturer": "supplier B",
        "lot-or-batch": "batch 22",
        "specification-reference": "drawing sheet 5",
        "shelf-life-days": 1000.0,
        "age-at-use-days": 400.0,
        "outgassing-data": {
            "total_mass_loss_percent": 0.40,
            "collected_volatile_percent": 0.02,
        },
    },
}

PROCESS = {
    "kind": "process",
    "parameters": {
        "identification": "interconnect welding",
        "process-specification-reference": "process specification 12",
        "qualification-reference": "qualification report 4",
        "operator-certification": "operator certificate 88",
    },
}


def _entry(base, **parameter_overrides):
    entry = copy.deepcopy(base)
    entry["parameters"].update(parameter_overrides)
    return entry


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_pmp_policy(DEFAULT_PMP_POLICY), DEFAULT_PMP_POLICY)

    def test_policy_covers_every_procurement_level(self):
        for level in PROCUREMENT_LEVELS:
            self.assertIn(level, DEFAULT_PMP_POLICY["procurement_disposition"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_pmp_policy("default")

    def test_policy_with_zero_mass_loss_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_PMP_POLICY)
        broken["max_total_mass_loss_percent"] = 0.0
        with self.assertRaises(ValueError):
            validate_pmp_policy(broken)

    def test_policy_with_full_shelf_life_margin_rejected(self):
        broken = copy.deepcopy(DEFAULT_PMP_POLICY)
        broken["min_shelf_life_margin_fraction"] = 1.0
        with self.assertRaises(ValueError):
            validate_pmp_policy(broken)

    def test_policy_missing_a_procurement_level_rejected(self):
        broken = copy.deepcopy(DEFAULT_PMP_POLICY)
        del broken["procurement_disposition"]["commercial"]
        with self.assertRaises(ValueError):
            validate_pmp_policy(broken)

    def test_policy_with_an_unknown_disposition_rejected(self):
        broken = copy.deepcopy(DEFAULT_PMP_POLICY)
        broken["procurement_disposition"]["commercial"] = "probably-fine"
        with self.assertRaises(ValueError):
            validate_pmp_policy(broken)


class ParameterSetTests(unittest.TestCase):
    def test_each_kind_has_its_own_parameter_set(self):
        for kind in ENTRY_KINDS:
            self.assertEqual(required_parameters(kind), REQUIRED_PARAMETERS[kind])

    def test_material_set_carries_outgassing_and_shelf_life(self):
        expected = required_parameters("material")
        self.assertIn("outgassing-data", expected)
        self.assertIn("shelf-life-days", expected)

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            required_parameters("subassembly")

    def test_complete_entry_has_no_missing_parameter(self):
        self.assertEqual(missing_parameters(PART), [])
        self.assertEqual(missing_parameters(MATERIAL), [])
        self.assertEqual(missing_parameters(PROCESS), [])

    def test_blank_parameter_counts_as_missing(self):
        entry = _entry(PART, **{"lot-or-batch": "   "})
        self.assertEqual(missing_parameters(entry), ["lot-or-batch"])

    def test_absent_parameter_counts_as_missing(self):
        entry = copy.deepcopy(PROCESS)
        del entry["parameters"]["qualification-reference"]
        self.assertEqual(missing_parameters(entry), ["qualification-reference"])

    def test_completeness_fraction_counts_the_declared_share(self):
        self.assertAlmostEqual(parameter_completeness_fraction(PART), 1.0, places=9)
        entry = _entry(PART, **{"manufacturer": None})
        self.assertAlmostEqual(parameter_completeness_fraction(entry), 0.8, places=9)

    def test_entry_without_a_parameter_mapping_rejected(self):
        with self.assertRaises(ValueError):
            missing_parameters({"kind": "part", "parameters": "see drawing"})

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            missing_parameters("string bypass diode")


class OutgassingTests(unittest.TestCase):
    def test_clean_material_passes_both_criteria(self):
        screen = outgassing_screen(0.40, 0.02)
        self.assertTrue(screen["passes"])
        self.assertEqual(screen["findings"], [])

    def test_result_exactly_on_both_limits_passes(self):
        screen = outgassing_screen(1.0, 0.10)
        self.assertAlmostEqual(screen["total_mass_loss_percent"], 1.0, places=9)
        self.assertAlmostEqual(screen["collected_volatile_percent"], 0.10, places=9)
        self.assertTrue(screen["passes"])

    def test_excess_mass_loss_fails(self):
        screen = outgassing_screen(1.4, 0.02)
        self.assertFalse(screen["mass_loss_ok"])
        self.assertTrue(screen["condensable_ok"])
        self.assertFalse(screen["passes"])
        self.assertTrue(any("total mass loss" in f for f in screen["findings"]))

    def test_excess_condensable_fails(self):
        screen = outgassing_screen(0.40, 0.25)
        self.assertTrue(screen["mass_loss_ok"])
        self.assertFalse(screen["condensable_ok"])
        self.assertTrue(any("condensable" in f for f in screen["findings"]))

    def test_negative_mass_loss_rejected(self):
        with self.assertRaises(ValueError):
            outgassing_screen(-0.1, 0.02)

    def test_non_numeric_condensable_rejected(self):
        with self.assertRaises(ValueError):
            outgassing_screen(0.4, "0.02 percent")

    def test_a_stricter_policy_can_fail_a_clean_material(self):
        policy = copy.deepcopy(DEFAULT_PMP_POLICY)
        policy["max_total_mass_loss_percent"] = 0.20
        self.assertFalse(outgassing_screen(0.40, 0.02, policy)["passes"])


class ShelfLifeTests(unittest.TestCase):
    def test_fresh_material_keeps_most_of_its_span(self):
        status = shelf_life_status(1000.0, 400.0)
        self.assertAlmostEqual(status["remaining_days"], 600.0, places=9)
        self.assertAlmostEqual(status["remaining_fraction"], 0.6, places=9)
        self.assertTrue(status["sufficient"])
        self.assertFalse(status["expired"])

    def test_span_exactly_on_the_required_margin_is_sufficient(self):
        status = shelf_life_status(1000.0, 900.0)
        self.assertAlmostEqual(status["remaining_fraction"], 0.10, places=9)
        self.assertAlmostEqual(status["required_fraction"], 0.10, places=9)
        self.assertTrue(status["sufficient"])

    def test_thin_span_is_insufficient_but_not_expired(self):
        status = shelf_life_status(1000.0, 950.0)
        self.assertFalse(status["sufficient"])
        self.assertFalse(status["expired"])
        self.assertTrue(any("shelf life" in f for f in status["findings"]))

    def test_overrun_span_is_expired(self):
        status = shelf_life_status(1000.0, 1100.0)
        self.assertTrue(status["expired"])
        self.assertAlmostEqual(status["remaining_days"], -100.0, places=9)

    def test_zero_shelf_life_rejected(self):
        with self.assertRaises(ValueError):
            shelf_life_status(0.0, 10.0)

    def test_negative_age_rejected(self):
        with self.assertRaises(ValueError):
            shelf_life_status(1000.0, -10.0)


class ProcurementTests(unittest.TestCase):
    def test_space_qualified_part_is_tracked(self):
        self.assertEqual(procurement_disposition("space-qualified"), PARAMETERS_TRACKED)

    def test_upscreened_part_needs_a_waiver(self):
        self.assertEqual(
            procurement_disposition("upscreened-commercial"), WAIVER_REQUIRED
        )

    def test_commercial_part_is_not_acceptable(self):
        self.assertEqual(procurement_disposition("commercial"), NOT_ACCEPTABLE)

    def test_unknown_procurement_level_rejected(self):
        with self.assertRaises(ValueError):
            procurement_disposition("from-the-drawer")


class EntryAssessmentTests(unittest.TestCase):
    def test_complete_part_is_tracked(self):
        record = assess_pmp_entry(PART)
        self.assertEqual(record["verdict"], PARAMETERS_TRACKED)
        self.assertEqual(record["findings"], [])
        self.assertEqual(record["procurement_level"], "space-qualified")

    def test_complete_material_is_tracked(self):
        record = assess_pmp_entry(MATERIAL)
        self.assertEqual(record["verdict"], PARAMETERS_TRACKED)
        self.assertTrue(record["outgassing"]["passes"])
        self.assertTrue(record["shelf_life"]["sufficient"])

    def test_complete_process_is_tracked(self):
        self.assertEqual(assess_pmp_entry(PROCESS)["verdict"], PARAMETERS_TRACKED)

    def test_incomplete_entry_is_not_screened(self):
        entry = copy.deepcopy(MATERIAL)
        del entry["parameters"]["outgassing-data"]
        record = assess_pmp_entry(entry)
        self.assertEqual(record["verdict"], PARAMETERS_INCOMPLETE)
        self.assertIsNone(record["outgassing"])
        self.assertEqual(record["missing_parameters"], ["outgassing-data"])

    def test_material_failing_outgassing_is_not_acceptable(self):
        entry = _entry(
            MATERIAL,
            **{
                "outgassing-data": {
                    "total_mass_loss_percent": 1.6,
                    "collected_volatile_percent": 0.02,
                }
            }
        )
        self.assertEqual(assess_pmp_entry(entry)["verdict"], NOT_ACCEPTABLE)

    def test_material_short_on_shelf_life_needs_a_waiver(self):
        entry = _entry(MATERIAL, **{"age-at-use-days": 950.0})
        self.assertEqual(assess_pmp_entry(entry)["verdict"], WAIVER_REQUIRED)

    def test_expired_material_is_not_acceptable(self):
        entry = _entry(MATERIAL, **{"age-at-use-days": 1100.0})
        self.assertEqual(assess_pmp_entry(entry)["verdict"], NOT_ACCEPTABLE)

    def test_upscreened_part_needs_a_waiver(self):
        entry = _entry(PART, **{"procurement-level": "upscreened-commercial"})
        record = assess_pmp_entry(entry)
        self.assertEqual(record["verdict"], WAIVER_REQUIRED)
        self.assertTrue(any("dispositioned" in f for f in record["findings"]))

    def test_material_with_non_mapping_outgassing_data_rejected(self):
        entry = _entry(MATERIAL, **{"outgassing-data": "see report"})
        with self.assertRaises(ValueError):
            assess_pmp_entry(entry)

    def test_part_with_an_unknown_procurement_level_rejected(self):
        entry = _entry(PART, **{"procurement-level": "from-the-drawer"})
        with self.assertRaises(ValueError):
            assess_pmp_entry(entry)

    def test_entry_with_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_pmp_entry({"kind": "subassembly", "parameters": {}})


class ListAuditTests(unittest.TestCase):
    def test_clean_list_is_tracked(self):
        result = audit_pmp_list({"entries": [PART, MATERIAL, PROCESS]})
        self.assertEqual(result["verdict"], LIST_TRACKED)
        self.assertAlmostEqual(result["tracked_fraction"], 1.0, places=9)
        self.assertAlmostEqual(result["mean_completeness_fraction"], 1.0, places=9)
        self.assertEqual(result["open_entries"], [])

    def test_one_open_entry_holds_the_list(self):
        entry = _entry(PART, **{"procurement-level": "commercial"})
        result = audit_pmp_list({"entries": [entry, MATERIAL]})
        self.assertEqual(result["verdict"], LIST_NOT_TRACKED)
        self.assertEqual(result["open_entries"], ["string bypass diode"])
        self.assertAlmostEqual(result["tracked_fraction"], 0.5, places=9)

    def test_list_groups_entries_by_verdict(self):
        entry = _entry(PART, **{"procurement-level": "upscreened-commercial"})
        result = audit_pmp_list({"entries": [entry, MATERIAL, PROCESS]})
        self.assertEqual(result["grouped_by_verdict"][WAIVER_REQUIRED], ["string bypass diode"])
        self.assertEqual(len(result["grouped_by_verdict"][PARAMETERS_TRACKED]), 2)

    def test_list_reports_the_mean_completeness(self):
        entry = copy.deepcopy(PROCESS)
        del entry["parameters"]["operator-certification"]
        result = audit_pmp_list({"entries": [entry]})
        self.assertAlmostEqual(result["mean_completeness_fraction"], 0.75, places=9)
        self.assertEqual(result["verdict"], LIST_NOT_TRACKED)

    def test_list_collects_every_finding(self):
        entry = _entry(MATERIAL, **{"age-at-use-days": 950.0})
        findings = audit_pmp_list({"entries": [entry]})["findings"]
        self.assertTrue(any("shelf life" in f for f in findings))

    def test_unidentified_entry_is_still_reported(self):
        entry = copy.deepcopy(PROCESS)
        entry["parameters"]["identification"] = "  "
        result = audit_pmp_list({"entries": [entry]})
        self.assertEqual(result["open_entries"], ["<unidentified process>"])

    def test_empty_list_rejected(self):
        with self.assertRaises(ValueError):
            audit_pmp_list({"entries": []})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            audit_pmp_list([PART])


if __name__ == "__main__":
    unittest.main()
