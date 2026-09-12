#!/usr/bin/env python3
"""Gate 3 contract test for e20-battery-specification-for-energy-balance."""

import unittest

from e20_battery_specification_for_energy_balance_logic import (
    DEFAULT_MAX_DOD,
    assess_battery_specification,
    bol_capacity_for_eol_wh,
    end_of_life_capacity_wh,
    phase_energy_wh,
    recharge_feasibility,
    required_capacity_wh,
    size_battery,
    validate_phase,
    verify_energy_balance,
)


def eclipse_phase(**overrides):
    phase = {
        "name": "eclipse",
        "category": "eclipse",
        "duration_h": 0.6,
        "load_power_w": 300.0,
        "generated_power_w": 0.0,
    }
    phase.update(overrides)
    return phase


def sunlight_phase(**overrides):
    phase = {
        "name": "sunlight",
        "category": "nominal-operations",
        "duration_h": 1.0,
        "load_power_w": 300.0,
        "generated_power_w": 700.0,
    }
    phase.update(overrides)
    return phase


def safe_mode_phase(**overrides):
    phase = {
        "name": "safe",
        "category": "safe-mode",
        "duration_h": 2.0,
        "load_power_w": 150.0,
        "generated_power_w": 0.0,
    }
    phase.update(overrides)
    return phase


class ValidatePhaseTests(unittest.TestCase):
    def test_default_dod_comes_from_the_category(self):
        normalized = validate_phase(eclipse_phase())
        self.assertAlmostEqual(
            normalized["max_dod"], DEFAULT_MAX_DOD["eclipse"], places=6
        )
        self.assertFalse(normalized["is_contingency"])
        self.assertTrue(normalized["in_recurring_cycle"])

    def test_contingency_phase_is_outside_the_recurring_cycle(self):
        normalized = validate_phase(safe_mode_phase())
        self.assertTrue(normalized["is_contingency"])
        self.assertFalse(normalized["in_recurring_cycle"])

    def test_explicit_dod_overrides_the_default(self):
        normalized = validate_phase(eclipse_phase(max_dod=0.2))
        self.assertAlmostEqual(normalized["max_dod"], 0.2, places=6)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            validate_phase(eclipse_phase(category="cruise"))

    def test_missing_name_raises(self):
        phase = eclipse_phase()
        del phase["name"]
        with self.assertRaises(ValueError):
            validate_phase(phase)

    def test_zero_duration_raises(self):
        with self.assertRaises(ValueError):
            validate_phase(eclipse_phase(duration_h=0.0))

    def test_negative_load_raises(self):
        with self.assertRaises(ValueError):
            validate_phase(eclipse_phase(load_power_w=-1.0))

    def test_dod_above_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_phase(eclipse_phase(max_dod=1.5))

    def test_zero_dod_raises(self):
        with self.assertRaises(ValueError):
            validate_phase(eclipse_phase(max_dod=0.0))

    def test_non_mapping_phase_raises(self):
        with self.assertRaises(ValueError):
            validate_phase("eclipse")


class PhaseEnergyTests(unittest.TestCase):
    def test_discharge_phase_energy(self):
        energy = phase_energy_wh(eclipse_phase())
        self.assertAlmostEqual(energy["consumed_wh"], 180.0, places=6)
        self.assertAlmostEqual(energy["available_wh"], 0.0, places=6)
        self.assertAlmostEqual(energy["discharge_wh"], 180.0, places=6)
        self.assertAlmostEqual(energy["surplus_wh"], 0.0, places=6)

    def test_surplus_phase_energy(self):
        energy = phase_energy_wh(sunlight_phase())
        self.assertAlmostEqual(energy["surplus_wh"], 400.0, places=6)
        self.assertAlmostEqual(energy["discharge_wh"], 0.0, places=6)

    def test_distribution_loss_increases_consumption(self):
        energy = phase_energy_wh(eclipse_phase(), distribution_efficiency=0.9)
        self.assertAlmostEqual(energy["consumed_wh"], 200.0, places=6)

    def test_distribution_efficiency_above_unity_raises(self):
        with self.assertRaises(ValueError):
            phase_energy_wh(eclipse_phase(), distribution_efficiency=1.1)


class RequiredCapacityTests(unittest.TestCase):
    def test_capacity_covers_discharge_and_dod(self):
        self.assertAlmostEqual(
            required_capacity_wh(eclipse_phase(), 1.0, 0.95),
            631.578947,
            places=4,
        )

    def test_contingency_phase_allows_a_deeper_discharge(self):
        self.assertAlmostEqual(
            required_capacity_wh(safe_mode_phase(), 1.0, 0.95),
            526.315789,
            places=4,
        )

    def test_surplus_phase_demands_no_capacity(self):
        self.assertAlmostEqual(
            required_capacity_wh(sunlight_phase(), 1.0, 0.95), 0.0, places=9
        )

    def test_zero_discharge_efficiency_raises(self):
        with self.assertRaises(ValueError):
            required_capacity_wh(eclipse_phase(), 1.0, 0.0)


class FadeTests(unittest.TestCase):
    def test_capacity_fades_over_the_mission(self):
        self.assertAlmostEqual(
            end_of_life_capacity_wh(800.0, 0.03, 5.0), 686.987221, places=4
        )

    def test_zero_fade_keeps_capacity(self):
        self.assertAlmostEqual(
            end_of_life_capacity_wh(800.0, 0.0, 5.0), 800.0, places=6
        )

    def test_bol_demand_inverts_the_fade(self):
        self.assertAlmostEqual(
            bol_capacity_for_eol_wh(686.987221, 0.03, 5.0), 800.0, places=4
        )

    def test_fade_of_one_raises(self):
        with self.assertRaises(ValueError):
            end_of_life_capacity_wh(800.0, 1.0, 5.0)

    def test_negative_mission_years_raises(self):
        with self.assertRaises(ValueError):
            end_of_life_capacity_wh(800.0, 0.03, -1.0)

    def test_non_positive_bol_raises(self):
        with self.assertRaises(ValueError):
            end_of_life_capacity_wh(0.0, 0.03, 5.0)


class RechargeTests(unittest.TestCase):
    def test_charge_window_restores_the_discharge(self):
        result = recharge_feasibility(eclipse_phase(), sunlight_phase(), 0.9)
        self.assertTrue(result["feasible"])
        self.assertAlmostEqual(result["restored_wh"], 360.0, places=6)
        self.assertAlmostEqual(result["deficit_wh"], 0.0, places=9)

    def test_weak_charge_window_leaves_a_deficit(self):
        result = recharge_feasibility(
            eclipse_phase(), sunlight_phase(generated_power_w=400.0), 0.9
        )
        self.assertFalse(result["feasible"])
        self.assertAlmostEqual(result["deficit_wh"], 90.0, places=6)

    def test_charge_efficiency_of_zero_raises(self):
        with self.assertRaises(ValueError):
            recharge_feasibility(eclipse_phase(), sunlight_phase(), 0.0)


class SizingTests(unittest.TestCase):
    def test_driving_phase_sets_the_capacity(self):
        sizing = size_battery(
            [eclipse_phase(), sunlight_phase(), safe_mode_phase()],
            1.0,
            0.95,
            0.03,
            5.0,
        )
        self.assertEqual(sizing["driving_phase"], "eclipse")
        self.assertAlmostEqual(
            sizing["required_eol_capacity_wh"], 631.578947, places=4
        )
        self.assertAlmostEqual(
            sizing["required_bol_capacity_wh"], 735.476793, places=4
        )

    def test_a_deeper_contingency_can_drive_the_sizing(self):
        sizing = size_battery(
            [eclipse_phase(), safe_mode_phase(duration_h=8.0)], 1.0, 0.95
        )
        self.assertEqual(sizing["driving_phase"], "safe")

    def test_empty_phase_set_raises(self):
        with self.assertRaises(ValueError):
            size_battery([])


class VerificationTests(unittest.TestCase):
    def test_adequate_capacity_balances_every_phase(self):
        result = verify_energy_balance(
            [eclipse_phase(), sunlight_phase(), safe_mode_phase()], 700.0, 1.0, 0.95
        )
        self.assertTrue(result["balanced"])
        self.assertAlmostEqual(result["cycle_net_wh"], 220.0, places=6)
        self.assertAlmostEqual(
            result["per_phase"][0]["depth_of_discharge"], 0.270677, places=4
        )

    def test_undersized_store_exceeds_the_allowable_dod(self):
        result = verify_energy_balance([eclipse_phase()], 300.0, 1.0, 0.95)
        self.assertFalse(result["balanced"])
        self.assertTrue(
            any("depth of discharge" in f for f in result["findings"])
        )

    def test_negative_cycle_energy_is_a_finding(self):
        result = verify_energy_balance(
            [eclipse_phase(), sunlight_phase(generated_power_w=400.0)],
            700.0,
            1.0,
            0.95,
        )
        self.assertAlmostEqual(result["cycle_net_wh"], -80.0, places=6)
        self.assertTrue(
            any("recurring cycle" in f for f in result["findings"])
        )

    def test_contingency_energy_stays_out_of_the_cycle_sum(self):
        result = verify_energy_balance(
            [sunlight_phase(), safe_mode_phase()], 700.0, 1.0, 0.95
        )
        self.assertAlmostEqual(result["cycle_net_wh"], 400.0, places=6)

    def test_non_positive_capacity_raises(self):
        with self.assertRaises(ValueError):
            verify_energy_balance([eclipse_phase()], 0.0)


class SpecificationAssessmentTests(unittest.TestCase):
    def base_spec(self, **overrides):
        spec = {
            "phases": [eclipse_phase(), sunlight_phase(), safe_mode_phase()],
            "distribution_efficiency": 1.0,
            "discharge_efficiency": 0.95,
            "annual_fade_fraction": 0.03,
            "mission_years": 5.0,
            "declared_bol_capacity_wh": 900.0,
        }
        spec.update(overrides)
        return spec

    def test_sufficient_declaration_is_compliant(self):
        result = assess_battery_specification(self.base_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], ())
        self.assertEqual(result["sizing"]["driving_phase"], "eclipse")
        self.assertTrue(result["verification"]["balanced"])

    def test_undersized_declaration_is_flagged(self):
        result = assess_battery_specification(
            self.base_spec(declared_bol_capacity_wh=500.0)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("end of life" in f for f in result["findings"])
        )

    def test_phase_set_without_a_contingency_is_flagged(self):
        result = assess_battery_specification(
            self.base_spec(phases=[eclipse_phase(), sunlight_phase()])
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("no contingency" in f for f in result["findings"])
        )

    def test_undeclared_capacity_still_returns_the_sizing(self):
        spec = self.base_spec()
        del spec["declared_bol_capacity_wh"]
        result = assess_battery_specification(spec)
        self.assertIsNone(result["verification"])
        self.assertAlmostEqual(
            result["sizing"]["required_bol_capacity_wh"], 735.476793, places=4
        )

    def test_missing_phases_raises(self):
        with self.assertRaises(ValueError):
            assess_battery_specification({"declared_bol_capacity_wh": 900.0})

    def test_non_mapping_specification_raises(self):
        with self.assertRaises(ValueError):
            assess_battery_specification([eclipse_phase()])

    def test_out_of_range_discharge_efficiency_raises(self):
        with self.assertRaises(ValueError):
            assess_battery_specification(self.base_spec(discharge_efficiency=1.4))


if __name__ == "__main__":
    unittest.main()
