#!/usr/bin/env python3
"""Gate 3 contract test for e2007-indirect-discharge-test-equipment.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_indirect_discharge_test_equipment.py
"""

import math
import unittest

from e2007_indirect_discharge_test_equipment_logic import (
    ADEQUATE,
    CEILING,
    FLOOR,
    INADEQUATE,
    MARGINAL,
    NETWORK_TOLERANCE,
    RECHARGE_FRACTION,
    SUPPLY_REGULATION_LIMIT_PCT,
    VERDICT_FIT,
    VERDICT_FIT_WITH_LIMITATIONS,
    VERDICT_UNFIT,
    achievable_repetition_rate_hz,
    assess_indirect_discharge_equipment,
    categorize_capability,
    first_peak_current_a,
    governing_shortfall,
    network_time_constant_s,
    normalize_inventory,
    recharge_time_s,
    relative_error,
    required_charge_resistance_ohm,
    required_holdoff_v,
    required_supply_ceiling_v,
    shortfall_factor,
    stored_energy_j,
    validate_exposure,
)

NOMINAL_C_F = 150.0e-12
NOMINAL_R_OHM = 330.0


def exposure(**over):
    record = {
        "generator_mode": "contact-discharge",
        "severity_level_v": 4000.0,
        "discharge_interval_s": 1.0,
        "nominal_capacitance_f": NOMINAL_C_F,
        "nominal_discharge_resistance_ohm": NOMINAL_R_OHM,
    }
    record.update(over)
    return record


def inventory(**over):
    values = {
        "supply_ceiling_v": 8000.0,
        "supply_regulation_pct": 2.0,
        "electrode_holdoff_v": 10000.0,
        "storage_capacitance_f": NOMINAL_C_F,
        "discharge_resistance_ohm": NOMINAL_R_OHM,
        "charge_resistance_ohm": 50.0e6,
    }
    values.update(over)
    return [{"item": name, "value": values[name]} for name in sorted(values)]


def assess(exposure_over=None, **inventory_over):
    return assess_indirect_discharge_equipment(
        exposure(**(exposure_over or {})), inventory(**inventory_over)
    )


class TestExposureValidation(unittest.TestCase):
    def test_good_exposure_normalizes(self):
        spec = validate_exposure(exposure())
        self.assertEqual(spec["generator_mode"], "contact-discharge")
        self.assertAlmostEqual(spec["severity_level_v"], 4000.0, places=9)

    def test_generator_mode_token_is_case_normalized(self):
        spec = validate_exposure(exposure(generator_mode="Air-Discharge"))
        self.assertEqual(spec["generator_mode"], "air-discharge")

    def test_unknown_generator_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure(exposure(generator_mode="spark-by-eye"))

    def test_zero_severity_level_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure(exposure(severity_level_v=0.0))

    def test_boolean_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure(exposure(discharge_interval_s=True))

    def test_missing_nominal_capacitance_is_rejected(self):
        record = exposure()
        del record["nominal_capacitance_f"]
        with self.assertRaises(ValueError):
            validate_exposure(record)


class TestInventoryNormalization(unittest.TestCase):
    def test_full_inventory_normalizes(self):
        values, missing = normalize_inventory(inventory())
        self.assertEqual(missing, ())
        self.assertAlmostEqual(values["discharge_resistance_ohm"], 330.0, places=9)

    def test_absent_item_is_reported_as_missing(self):
        declared = [r for r in inventory() if r["item"] != "electrode_holdoff_v"]
        values, missing = normalize_inventory(declared)
        self.assertEqual(missing, ("electrode_holdoff_v",))
        self.assertNotIn("electrode_holdoff_v", values)

    def test_unrecognized_item_is_refused(self):
        declared = inventory() + [{"item": "coffee_machine_w", "value": 900.0}]
        with self.assertRaises(ValueError):
            normalize_inventory(declared)

    def test_duplicate_declaration_is_refused(self):
        declared = inventory() + [{"item": "supply_ceiling_v", "value": 9000.0}]
        with self.assertRaises(ValueError):
            normalize_inventory(declared)

    def test_non_positive_declared_value_is_refused(self):
        declared = inventory(supply_ceiling_v=0.0)
        with self.assertRaises(ValueError):
            normalize_inventory(declared)

    def test_bare_string_inventory_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_inventory("supply_ceiling_v")

    def test_declaration_without_a_value_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_inventory([{"item": "supply_ceiling_v"}])


class TestPrimaryCircuit(unittest.TestCase):
    def test_stored_energy_is_half_c_v_squared(self):
        self.assertAlmostEqual(
            stored_energy_j(NOMINAL_C_F, 4000.0), 1.2e-3, places=12
        )

    def test_stored_energy_scales_with_the_square_of_the_voltage(self):
        low = stored_energy_j(NOMINAL_C_F, 2000.0)
        high = stored_energy_j(NOMINAL_C_F, 4000.0)
        self.assertAlmostEqual(high / low, 4.0, places=9)

    def test_first_peak_current_is_voltage_over_resistance(self):
        self.assertAlmostEqual(
            first_peak_current_a(3300.0, NOMINAL_R_OHM), 10.0, places=9
        )

    def test_zero_discharge_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            first_peak_current_a(4000.0, 0.0)

    def test_network_time_constant_is_the_product(self):
        self.assertAlmostEqual(
            network_time_constant_s(NOMINAL_R_OHM, NOMINAL_C_F), 49.5e-9, places=15
        )

    def test_negative_capacitance_is_rejected(self):
        with self.assertRaises(ValueError):
            network_time_constant_s(NOMINAL_R_OHM, -1.0e-12)


class TestChargingCircuit(unittest.TestCase):
    def test_recharge_time_follows_the_exponential_law(self):
        expected = 1.0e6 * NOMINAL_C_F * -math.log(1.0 - RECHARGE_FRACTION)
        self.assertAlmostEqual(
            recharge_time_s(1.0e6, NOMINAL_C_F), expected, places=15
        )

    def test_recharge_fraction_outside_the_open_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            recharge_time_s(1.0e6, NOMINAL_C_F, 1.0)

    def test_repetition_rate_is_the_reciprocal_of_the_recharge_time(self):
        self.assertAlmostEqual(achievable_repetition_rate_hz(0.5), 2.0, places=9)

    def test_zero_recharge_time_is_rejected(self):
        with self.assertRaises(ValueError):
            achievable_repetition_rate_hz(0.0)

    def test_required_charge_resistance_recharges_exactly_in_the_interval(self):
        ceiling = required_charge_resistance_ohm(1.0, NOMINAL_C_F)
        self.assertAlmostEqual(recharge_time_s(ceiling, NOMINAL_C_F), 1.0, places=9)

    def test_required_charge_resistance_is_linear_in_the_interval(self):
        short = required_charge_resistance_ohm(0.5, NOMINAL_C_F)
        long_gap = required_charge_resistance_ohm(2.0, NOMINAL_C_F)
        self.assertAlmostEqual(long_gap / short, 4.0, places=9)


class TestRequirementsAndGrading(unittest.TestCase):
    def test_supply_ceiling_carries_the_declared_headroom(self):
        self.assertAlmostEqual(
            required_supply_ceiling_v(4000.0, 1.10), 4400.0, places=9
        )

    def test_headroom_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            required_supply_ceiling_v(4000.0, 0.9)

    def test_holdoff_exceeds_the_severity_level(self):
        self.assertAlmostEqual(required_holdoff_v(4000.0, 1.20), 4800.0, places=9)

    def test_relative_error_is_symmetric_about_the_nominal(self):
        self.assertAlmostEqual(relative_error(363.0, 330.0), 0.1, places=9)
        self.assertAlmostEqual(relative_error(297.0, 330.0), 0.1, places=9)

    def test_zero_nominal_is_rejected(self):
        with self.assertRaises(ValueError):
            relative_error(330.0, 0.0)

    def test_capability_well_past_a_floor_is_adequate(self):
        self.assertEqual(categorize_capability(8000.0, 4400.0, FLOOR), ADEQUATE)

    def test_capability_sitting_on_a_floor_is_marginal(self):
        self.assertEqual(categorize_capability(4400.0, 4400.0, FLOOR), MARGINAL)

    def test_capability_under_a_floor_is_inadequate(self):
        self.assertEqual(categorize_capability(4000.0, 4400.0, FLOOR), INADEQUATE)

    def test_capability_sitting_on_a_ceiling_is_marginal(self):
        self.assertEqual(categorize_capability(5.0, 5.0, CEILING), MARGINAL)

    def test_capability_over_a_ceiling_is_inadequate(self):
        self.assertEqual(categorize_capability(8.0, 5.0, CEILING), INADEQUATE)

    def test_unknown_sense_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_capability(1.0, 1.0, "sideways")

    def test_shortfall_factor_reads_above_unity_when_short(self):
        self.assertAlmostEqual(shortfall_factor(2200.0, 4400.0, FLOOR), 2.0, places=9)
        self.assertAlmostEqual(shortfall_factor(10.0, 5.0, CEILING), 2.0, places=9)

    def test_governing_shortfall_is_the_worst_one(self):
        checks = [
            {"item": "a", "category": INADEQUATE, "shortfall_factor": 1.2},
            {"item": "b", "category": INADEQUATE, "shortfall_factor": 3.4},
            {"item": "c", "category": ADEQUATE, "shortfall_factor": 0.2},
        ]
        self.assertEqual(governing_shortfall(checks), "b")

    def test_governing_shortfall_is_none_when_nothing_is_short(self):
        checks = [{"item": "a", "category": ADEQUATE, "shortfall_factor": 0.3}]
        self.assertIsNone(governing_shortfall(checks))


class TestEquipmentAssessment(unittest.TestCase):
    def test_good_bench_is_fit(self):
        report = assess()
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["limitations"], [])
        self.assertEqual(report["verdict"], VERDICT_FIT)
        self.assertIsNone(report["governing_shortfall"])

    def test_report_carries_the_derived_primary_circuit_numbers(self):
        derived = assess()["derived"]
        self.assertAlmostEqual(derived["stored_energy_j"], 1.2e-3, places=12)
        self.assertAlmostEqual(
            derived["first_peak_current_a"], 4000.0 / 330.0, places=9
        )
        self.assertAlmostEqual(derived["network_time_constant_s"], 49.5e-9, places=15)

    def test_a_supply_that_cannot_reach_the_level_is_a_finding(self):
        report = assess(supply_ceiling_v=3000.0)
        self.assertEqual(report["verdict"], VERDICT_UNFIT)
        self.assertEqual(report["governing_shortfall"], "supply_ceiling_v")

    def test_loose_regulation_is_a_finding(self):
        report = assess(supply_regulation_pct=SUPPLY_REGULATION_LIMIT_PCT * 3.0)
        self.assertEqual(report["verdict"], VERDICT_UNFIT)
        self.assertEqual(report["governing_shortfall"], "supply_regulation_pct")

    def test_a_capacitor_outside_the_network_tolerance_is_a_finding(self):
        report = assess(storage_capacitance_f=NOMINAL_C_F * 1.5)
        self.assertEqual(report["verdict"], VERDICT_UNFIT)
        self.assertEqual(report["governing_shortfall"], "storage_capacitance_tolerance")

    def test_a_capacitor_inside_the_network_tolerance_is_accepted(self):
        report = assess(storage_capacitance_f=NOMINAL_C_F * (1.0 + NETWORK_TOLERANCE / 2.0))
        self.assertEqual(report["findings"], [])

    def test_too_large_a_charging_resistor_cannot_keep_the_interval(self):
        report = assess(charge_resistance_ohm=1.0e12)
        self.assertEqual(report["verdict"], VERDICT_UNFIT)
        self.assertEqual(report["governing_shortfall"], "charge_resistance_ohm")

    def test_an_undeclared_item_is_a_finding_of_its_own(self):
        declared = [r for r in inventory() if r["item"] != "supply_regulation_pct"]
        report = assess_indirect_discharge_equipment(exposure(), declared)
        self.assertEqual(report["missing_items"], ("supply_regulation_pct",))
        self.assertEqual(report["verdict"], VERDICT_UNFIT)

    def test_a_marginal_holdoff_is_a_limitation_not_a_finding(self):
        report = assess(electrode_holdoff_v=4800.0)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_FIT_WITH_LIMITATIONS)
        self.assertEqual(len(report["limitations"]), 1)

    def test_air_discharge_mode_is_carried_as_a_limitation(self):
        report = assess({"generator_mode": "air-discharge"})
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_FIT_WITH_LIMITATIONS)

    def test_the_worst_of_two_shortfalls_governs(self):
        report = assess(supply_ceiling_v=4300.0, supply_regulation_pct=50.0)
        self.assertEqual(report["governing_shortfall"], "supply_regulation_pct")
        self.assertEqual(len(report["findings"]), 2)

    def test_assessment_propagates_an_inventory_error(self):
        with self.assertRaises(ValueError):
            assess_indirect_discharge_equipment(exposure(), inventory(supply_ceiling_v=-1.0))


if __name__ == "__main__":
    unittest.main()
