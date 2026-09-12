#!/usr/bin/env python3
"""Gate 3 contract test for e20-battery-clause-applicability (offline, stdlib)."""

import unittest

from e20_battery_clause_applicability_logic import (
    CATEGORY_CONVERTER,
    CATEGORY_NON_ELECTROCHEMICAL,
    CATEGORY_PRIMARY,
    CATEGORY_SECONDARY,
    assess_energy_store_inventory,
    battery_topology,
    categorize_energy_source,
    evaluate_energy_store,
    nominal_cell_voltage,
    normalize_chemistry,
    provisions_in_reach,
)


def secondary_entry(**overrides):
    entry = {
        "id": "BAT-1",
        "chemistry": "lithium-ion",
        "series_cells": 8,
        "parallel_strings": 4,
        "cell_capacity_ah": 5.0,
        "declared_in_battery_scope": True,
        "charge_control_present": True,
    }
    entry.update(overrides)
    return entry


class NormalizeChemistryTests(unittest.TestCase):
    def test_normalizes_case_and_whitespace(self):
        self.assertEqual(normalize_chemistry("  Lithium-Ion \n"), "lithium-ion")

    def test_rejects_empty_string(self):
        with self.assertRaises(ValueError):
            normalize_chemistry("   ")

    def test_rejects_non_string(self):
        with self.assertRaises(ValueError):
            normalize_chemistry(7)


class CategorizationTests(unittest.TestCase):
    def test_rechargeable_chemistry_is_secondary(self):
        self.assertEqual(
            categorize_energy_source("nickel-hydrogen"), CATEGORY_SECONDARY
        )

    def test_single_discharge_chemistry_is_primary(self):
        self.assertEqual(
            categorize_energy_source("lithium-thionyl-chloride"), CATEGORY_PRIMARY
        )

    def test_externally_fed_store_is_a_converter(self):
        self.assertEqual(
            categorize_energy_source("fuel-cell-pem"), CATEGORY_CONVERTER
        )

    def test_capacitor_bank_is_non_electrochemical(self):
        self.assertEqual(
            categorize_energy_source("capacitor-bank"), CATEGORY_NON_ELECTROCHEMICAL
        )

    def test_unknown_chemistry_raises(self):
        with self.assertRaises(ValueError):
            categorize_energy_source("zero-point-cell")


class ProvisionReachTests(unittest.TestCase):
    def test_secondary_reaches_charge_management(self):
        self.assertIn("charge-management", provisions_in_reach(CATEGORY_SECONDARY))

    def test_primary_does_not_reach_charge_management(self):
        groups = provisions_in_reach(CATEGORY_PRIMARY)
        self.assertNotIn("charge-management", groups)
        self.assertIn("safety-management", groups)

    def test_out_of_scope_categories_reach_nothing(self):
        self.assertEqual(provisions_in_reach(CATEGORY_CONVERTER), ())
        self.assertEqual(provisions_in_reach(CATEGORY_NON_ELECTROCHEMICAL), ())

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            provisions_in_reach("battery-ish")


class CellVoltageTests(unittest.TestCase):
    def test_secondary_cell_voltage(self):
        self.assertAlmostEqual(nominal_cell_voltage("lithium-ion"), 3.60, places=6)

    def test_primary_cell_voltage(self):
        self.assertAlmostEqual(
            nominal_cell_voltage("silver-zinc-primary"), 1.55, places=6
        )

    def test_converter_has_no_cell_voltage(self):
        with self.assertRaises(ValueError):
            nominal_cell_voltage("regenerative-fuel-cell")


class TopologyTests(unittest.TestCase):
    def test_resolves_voltage_capacity_and_energy(self):
        topo = battery_topology("lithium-ion", 8, 4, 5.0)
        self.assertAlmostEqual(topo["nominal_voltage_v"], 28.8, places=6)
        self.assertAlmostEqual(topo["capacity_ah"], 20.0, places=6)
        self.assertAlmostEqual(topo["stored_energy_wh"], 576.0, places=6)
        self.assertEqual(topo["cell_count"], 32)

    def test_single_cell_assembly_is_valid(self):
        topo = battery_topology("nickel-cadmium", 1, 1, 2.5)
        self.assertAlmostEqual(topo["stored_energy_wh"], 3.0, places=6)

    def test_zero_series_count_raises(self):
        with self.assertRaises(ValueError):
            battery_topology("lithium-ion", 0, 4, 5.0)

    def test_non_integer_parallel_count_raises(self):
        with self.assertRaises(ValueError):
            battery_topology("lithium-ion", 8, 4.5, 5.0)

    def test_boolean_series_count_raises(self):
        with self.assertRaises(ValueError):
            battery_topology("lithium-ion", True, 4, 5.0)

    def test_non_positive_cell_capacity_raises(self):
        with self.assertRaises(ValueError):
            battery_topology("lithium-ion", 8, 4, 0.0)

    def test_non_numeric_cell_capacity_raises(self):
        with self.assertRaises(ValueError):
            battery_topology("lithium-ion", 8, 4, "5")


class EvaluateEnergyStoreTests(unittest.TestCase):
    def test_in_scope_secondary_entry_is_clean(self):
        record = evaluate_energy_store(secondary_entry())
        self.assertTrue(record["in_battery_scope"])
        self.assertEqual(record["category"], CATEGORY_SECONDARY)
        self.assertEqual(record["findings"], ())
        self.assertAlmostEqual(record["topology"]["capacity_ah"], 20.0, places=6)

    def test_out_of_scope_entry_carries_no_provisions(self):
        record = evaluate_energy_store(
            {"id": "FW-1", "chemistry": "flywheel", "declared_in_battery_scope": False}
        )
        self.assertFalse(record["in_battery_scope"])
        self.assertEqual(record["provisions"], ())
        self.assertEqual(record["findings"], ())

    def test_missing_assembly_on_in_scope_entry_is_a_finding(self):
        record = evaluate_energy_store(
            {"id": "BAT-2", "chemistry": "nickel-cadmium"}
        )
        self.assertEqual(len(record["findings"]), 1)
        self.assertIn("cell assembly not declared", record["findings"][0])

    def test_declared_reach_contradicting_derived_reach_is_a_finding(self):
        record = evaluate_energy_store(
            secondary_entry(declared_in_battery_scope=False)
        )
        self.assertTrue(
            any("contradicts derived reach" in f for f in record["findings"])
        )

    def test_rechargeable_without_charge_control_is_a_finding(self):
        record = evaluate_energy_store(secondary_entry(charge_control_present=False))
        self.assertTrue(
            any("no charge control" in f for f in record["findings"])
        )

    def test_primary_without_charge_control_is_not_a_finding(self):
        record = evaluate_energy_store(
            {
                "id": "PBAT-1",
                "chemistry": "lithium-manganese-dioxide",
                "series_cells": 4,
                "parallel_strings": 1,
                "cell_capacity_ah": 1.5,
                "charge_control_present": False,
            }
        )
        self.assertEqual(record["category"], CATEGORY_PRIMARY)
        self.assertEqual(record["findings"], ())

    def test_partial_assembly_raises(self):
        entry = secondary_entry()
        del entry["parallel_strings"]
        with self.assertRaises(ValueError):
            evaluate_energy_store(entry)

    def test_assembly_on_out_of_scope_entry_raises(self):
        with self.assertRaises(ValueError):
            evaluate_energy_store(
                {
                    "id": "SC-1",
                    "chemistry": "supercapacitor",
                    "series_cells": 6,
                    "parallel_strings": 2,
                    "cell_capacity_ah": 0.5,
                }
            )

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            evaluate_energy_store({"chemistry": "lithium-ion"})

    def test_non_mapping_entry_raises(self):
        with self.assertRaises(ValueError):
            evaluate_energy_store(["lithium-ion"])

    def test_non_boolean_declared_flag_raises(self):
        with self.assertRaises(ValueError):
            evaluate_energy_store(secondary_entry(declared_in_battery_scope="yes"))

    def test_non_boolean_charge_control_flag_raises(self):
        with self.assertRaises(ValueError):
            evaluate_energy_store(secondary_entry(charge_control_present="yes"))


class InventoryTests(unittest.TestCase):
    def test_settled_inventory_sums_stored_energy(self):
        result = assess_energy_store_inventory(
            [
                secondary_entry(),
                {
                    "id": "PBAT-1",
                    "chemistry": "lithium-thionyl-chloride",
                    "series_cells": 2,
                    "parallel_strings": 1,
                    "cell_capacity_ah": 10.0,
                },
                {"id": "FW-1", "chemistry": "flywheel"},
            ]
        )
        self.assertTrue(result["settled"])
        self.assertEqual(result["in_scope_ids"], ("BAT-1", "PBAT-1"))
        self.assertEqual(result["out_of_scope_ids"], ("FW-1",))
        self.assertAlmostEqual(
            result["total_stored_energy_wh"], 576.0 + 72.0, places=6
        )

    def test_findings_block_settlement(self):
        result = assess_energy_store_inventory(
            [secondary_entry(charge_control_present=False)]
        )
        self.assertFalse(result["settled"])
        self.assertEqual(len(result["findings"]), 1)

    def test_duplicate_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_energy_store_inventory([secondary_entry(), secondary_entry()])

    def test_empty_inventory_raises(self):
        with self.assertRaises(ValueError):
            assess_energy_store_inventory([])

    def test_non_list_inventory_raises(self):
        with self.assertRaises(ValueError):
            assess_energy_store_inventory({"id": "BAT-1"})


if __name__ == "__main__":
    unittest.main()
