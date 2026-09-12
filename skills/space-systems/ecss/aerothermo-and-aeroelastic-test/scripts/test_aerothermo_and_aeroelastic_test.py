"""
Stdlib unittest for aerothermo_and_aeroelastic_test_logic.py.
Run: python3 test_aerothermo_and_aeroelastic_test.py
Expected output: OK
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from aerothermo_and_aeroelastic_test_logic import (
    AeroTestError,
    categorize_test_item,
    check_damping_ratio,
    check_temperature_limit,
    compute_combined_thermal_structural_utilization,
    compute_dynamic_pressure_stability_factor,
    compute_flutter_speed_margin,
    compute_heat_flux_margin,
    validate_test_sequence,
)


class TestCategorizeTestItem(unittest.TestCase):
    def test_aerothermodynamic_type_returns_aerothermodynamic(self):
        self.assertEqual(categorize_test_item("aerothermodynamic"), "aerothermodynamic")

    def test_thermal_only_returns_aerothermodynamic(self):
        self.assertEqual(categorize_test_item("thermal-only"), "aerothermodynamic")

    def test_flutter_clearance_returns_aeroelastic(self):
        self.assertEqual(categorize_test_item("flutter-clearance"), "aeroelastic")

    def test_divergence_check_returns_aeroelastic(self):
        self.assertEqual(categorize_test_item("divergence-check"), "aeroelastic")

    def test_control_reversal_returns_aeroelastic(self):
        self.assertEqual(categorize_test_item("control-reversal"), "aeroelastic")

    def test_unknown_type_raises(self):
        with self.assertRaises(AeroTestError):
            categorize_test_item("undefined-test")

    def test_empty_string_raises(self):
        with self.assertRaises(AeroTestError):
            categorize_test_item("")


class TestHeatFluxMargin(unittest.TestCase):
    def test_positive_margin_when_allowable_exceeds_applied(self):
        margin = compute_heat_flux_margin(applied_flux=800.0, allowable_flux=1000.0)
        self.assertAlmostEqual(margin, 0.25)

    def test_zero_margin_at_exact_limit(self):
        margin = compute_heat_flux_margin(applied_flux=1000.0, allowable_flux=1000.0)
        self.assertAlmostEqual(margin, 0.0)

    def test_negative_margin_when_applied_exceeds_allowable(self):
        margin = compute_heat_flux_margin(applied_flux=1200.0, allowable_flux=1000.0)
        self.assertLess(margin, 0.0)

    def test_zero_applied_flux_raises(self):
        with self.assertRaises(AeroTestError):
            compute_heat_flux_margin(applied_flux=0.0, allowable_flux=1000.0)

    def test_negative_allowable_flux_raises(self):
        with self.assertRaises(AeroTestError):
            compute_heat_flux_margin(applied_flux=800.0, allowable_flux=-100.0)


class TestTemperatureLimit(unittest.TestCase):
    def test_peak_below_allowable_passes(self):
        result = check_temperature_limit(peak_temp_K=1400.0, allowable_temp_K=1600.0)
        self.assertTrue(result["pass"])
        self.assertLess(result["excess_K"], 0.0)

    def test_peak_equals_allowable_passes(self):
        result = check_temperature_limit(peak_temp_K=1600.0, allowable_temp_K=1600.0)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["excess_K"], 0.0)

    def test_peak_above_allowable_fails(self):
        result = check_temperature_limit(peak_temp_K=1700.0, allowable_temp_K=1600.0)
        self.assertFalse(result["pass"])
        self.assertGreater(result["excess_K"], 0.0)

    def test_zero_peak_temp_raises(self):
        with self.assertRaises(AeroTestError):
            check_temperature_limit(peak_temp_K=0.0, allowable_temp_K=1600.0)


class TestFlutterSpeedMargin(unittest.TestCase):
    def test_adequate_flutter_margin_passes(self):
        result = compute_flutter_speed_margin(
            flutter_onset_speed=230.0,
            design_limit_speed=200.0,
            required_margin_factor=1.15,
        )
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["actual_factor"], 1.15)

    def test_flutter_margin_below_required_fails(self):
        result = compute_flutter_speed_margin(
            flutter_onset_speed=210.0,
            design_limit_speed=200.0,
            required_margin_factor=1.15,
        )
        self.assertFalse(result["pass"])
        self.assertLess(result["actual_factor"], result["required_factor"])

    def test_margin_factor_at_exactly_required_passes(self):
        result = compute_flutter_speed_margin(
            flutter_onset_speed=345.0,
            design_limit_speed=300.0,
            required_margin_factor=1.15,
        )
        self.assertTrue(result["pass"])

    def test_required_margin_factor_lte_one_raises(self):
        with self.assertRaises(AeroTestError):
            compute_flutter_speed_margin(
                flutter_onset_speed=200.0,
                design_limit_speed=180.0,
                required_margin_factor=1.0,
            )


class TestDampingRatio(unittest.TestCase):
    def test_damping_above_floor_passes(self):
        result = check_damping_ratio(measured_damping=0.03, min_required_damping=0.01)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["margin"], 0.02)

    def test_zero_damping_fails(self):
        result = check_damping_ratio(measured_damping=0.0, min_required_damping=0.01)
        self.assertFalse(result["pass"])

    def test_negative_damping_fails(self):
        result = check_damping_ratio(measured_damping=-0.005, min_required_damping=0.01)
        self.assertFalse(result["pass"])

    def test_negative_required_raises(self):
        with self.assertRaises(AeroTestError):
            check_damping_ratio(measured_damping=0.02, min_required_damping=-0.01)


class TestDynamicPressureStability(unittest.TestCase):
    def test_stable_when_critical_exceeds_design(self):
        factor = compute_dynamic_pressure_stability_factor(
            critical_dynamic_pressure=8000.0, design_dynamic_pressure=5000.0
        )
        self.assertGreater(factor, 1.0)

    def test_unstable_when_critical_below_design(self):
        factor = compute_dynamic_pressure_stability_factor(
            critical_dynamic_pressure=4000.0, design_dynamic_pressure=5000.0
        )
        self.assertLess(factor, 1.0)

    def test_zero_design_dp_raises(self):
        with self.assertRaises(AeroTestError):
            compute_dynamic_pressure_stability_factor(
                critical_dynamic_pressure=8000.0, design_dynamic_pressure=0.0
            )


class TestCombinedThermalStructural(unittest.TestCase):
    def test_combined_utilization_within_limit_passes(self):
        result = compute_combined_thermal_structural_utilization(
            thermal_utilization=0.6, structural_utilization=0.6
        )
        # sqrt(0.6^2 + 0.6^2) = 0.849 < 1.0 → passes
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["interaction"], (0.6**2 + 0.6**2) ** 0.5, places=6)

    def test_low_utilizations_pass(self):
        result = compute_combined_thermal_structural_utilization(
            thermal_utilization=0.5, structural_utilization=0.5
        )
        self.assertTrue(result["pass"])
        self.assertLess(result["interaction"], 1.0)

    def test_high_utilizations_fail(self):
        result = compute_combined_thermal_structural_utilization(
            thermal_utilization=0.9, structural_utilization=0.9
        )
        self.assertFalse(result["pass"])
        self.assertGreater(result["interaction"], 1.0)

    def test_negative_utilization_raises(self):
        with self.assertRaises(AeroTestError):
            compute_combined_thermal_structural_utilization(
                thermal_utilization=-0.1, structural_utilization=0.5
            )


class TestValidateTestSequence(unittest.TestCase):
    def test_valid_aerothermodynamic_sequence(self):
        phases = ["pre-test-inspection", "aerothermodynamic-load", "peak-heat-flux", "post-test-inspection"]
        result = validate_test_sequence(phases)
        self.assertTrue(result["valid"])
        self.assertEqual(result["findings"], [])

    def test_valid_aeroelastic_sequence(self):
        phases = ["pre-test-inspection", "aeroelastic-sweep", "flutter-dip", "post-test-inspection"]
        result = validate_test_sequence(phases)
        self.assertTrue(result["valid"])

    def test_missing_pre_inspection_fails(self):
        phases = ["aerothermodynamic-load", "post-test-inspection"]
        result = validate_test_sequence(phases)
        self.assertFalse(result["valid"])

    def test_missing_post_inspection_fails(self):
        phases = ["pre-test-inspection", "aeroelastic-sweep"]
        result = validate_test_sequence(phases)
        self.assertFalse(result["valid"])

    def test_empty_sequence_fails(self):
        result = validate_test_sequence([])
        self.assertFalse(result["valid"])

    def test_unrecognized_phase_fails(self):
        phases = ["pre-test-inspection", "mystery-phase", "post-test-inspection"]
        result = validate_test_sequence(phases)
        self.assertFalse(result["valid"])
        self.assertTrue(any("mystery-phase" in f for f in result["findings"]))


if __name__ == "__main__":
    unittest.main()
