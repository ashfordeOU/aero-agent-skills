"""Contract tests for the ECSS-E-ST-31 high-temperature and TPS logic."""

import unittest

from e31_high_temperature_range_tps_requirements_logic import (
    HIGH_TEMPERATURE_LOWER_K,
    assess_reuse,
    assess_tps_item,
    assess_tps_set,
    bondline_temperature,
    emissivity_after_cycles,
    inflated_peak_temperature,
    material_temperature_margin,
    residual_thickness,
    validate_item,
)


def item(name="leading-edge-tile", **over):
    base = {
        "name": name,
        "predicted_peak_k": 1400.0,
        "uncertainty_hot_k": 100.0,
        "max_use_temperature_k": 1600.0,
        "installed_thickness_m": 0.050,
        "required_residual_m": 0.030,
        "recession_rate_m_per_s": 1.0e-5,
        "exposure_s": 1000.0,
        "heat_flux_w_m2": 1375.0,
        "conductivity_w_mk": 0.05,
        "bondline_limit_k": 450.0,
        "emissivity_bol": 0.85,
        "emissivity_floor": 0.70,
        "emissivity_loss_per_cycle": 0.01,
        "required_cycles": 10,
        "qualified_cycles": 25,
    }
    base.update(over)
    return base


class AdmissionTests(unittest.TestCase):
    def test_hot_item_is_admitted(self):
        checked = validate_item(item())
        self.assertEqual(checked["name"], "leading-edge-tile")

    def test_item_below_the_boundary_is_refused(self):
        with self.assertRaises(ValueError):
            validate_item(item(predicted_peak_k=380.0, uncertainty_hot_k=10.0))

    def test_uncertainty_can_carry_an_item_over_the_boundary(self):
        checked = validate_item(
            item(predicted_peak_k=460.0, uncertainty_hot_k=40.0,
                 max_use_temperature_k=800.0, bondline_limit_k=430.0,
                 heat_flux_w_m2=10.0)
        )
        self.assertGreater(
            inflated_peak_temperature(checked), HIGH_TEMPERATURE_LOWER_K
        )

    def test_negative_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(item(uncertainty_hot_k=-5.0))

    def test_required_residual_above_installed_thickness_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(item(required_residual_m=0.060))

    def test_emissivity_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(item(emissivity_bol=1.3))

    def test_zero_cycles_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(item(required_cycles=0))

    def test_boolean_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(item(qualified_cycles=True))

    def test_unnamed_item_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(item(name="   "))


class MaterialMarginTests(unittest.TestCase):
    def test_margin_is_measured_on_the_inflated_peak(self):
        result = material_temperature_margin(validate_item(item()))
        self.assertAlmostEqual(result["inflated_peak_k"], 1500.0, places=9)
        self.assertAlmostEqual(result["margin_k"], 100.0, places=9)
        self.assertTrue(result["acceptable"])

    def test_raw_peak_would_have_overstated_the_margin(self):
        checked = validate_item(item())
        raw = checked["max_use_temperature_k"] - checked["predicted_peak_k"]
        inflated = material_temperature_margin(checked)["margin_k"]
        self.assertAlmostEqual(raw - inflated, checked["uncertainty_hot_k"], places=9)

    def test_inflated_peak_exactly_on_the_limit_is_acceptable(self):
        result = material_temperature_margin(
            validate_item(item(max_use_temperature_k=1500.0))
        )
        self.assertAlmostEqual(result["margin_k"], 0.0, places=9)
        self.assertTrue(result["acceptable"])

    def test_inflated_peak_over_the_limit_is_not_acceptable(self):
        result = material_temperature_margin(
            validate_item(item(max_use_temperature_k=1450.0))
        )
        self.assertFalse(result["acceptable"])


class RecessionTests(unittest.TestCase):
    def test_recession_is_spent_over_the_exposure(self):
        result = residual_thickness(validate_item(item()))
        self.assertAlmostEqual(result["recessed_m"], 0.010, places=9)
        self.assertAlmostEqual(result["residual_m"], 0.040, places=9)
        self.assertTrue(result["acceptable"])

    def test_residual_exactly_on_the_requirement_is_acceptable(self):
        result = residual_thickness(validate_item(item(recession_rate_m_per_s=2.0e-5)))
        self.assertAlmostEqual(
            result["residual_m"], 0.030, places=9
        )
        self.assertTrue(result["acceptable"])

    def test_residual_below_the_requirement_is_not_acceptable(self):
        result = residual_thickness(validate_item(item(recession_rate_m_per_s=3.0e-5)))
        self.assertFalse(result["acceptable"])
        self.assertFalse(result["burn_through"])

    def test_full_consumption_is_a_burn_through(self):
        result = residual_thickness(
            validate_item(item(recession_rate_m_per_s=6.0e-5, required_residual_m=0.0))
        )
        self.assertTrue(result["burn_through"])
        self.assertFalse(result["acceptable"])

    def test_non_ablating_item_keeps_its_thickness(self):
        result = residual_thickness(validate_item(item(recession_rate_m_per_s=0.0)))
        self.assertAlmostEqual(result["residual_m"], 0.050, places=9)


class BondlineTests(unittest.TestCase):
    def test_bondline_sits_below_the_surface_by_the_conduction_drop(self):
        result = bondline_temperature(1500.0, 0.040, 1375.0, 0.05)
        self.assertAlmostEqual(result["drop_k"], 1100.0, places=9)
        self.assertAlmostEqual(result["bondline_k"], 400.0, places=9)

    def test_thinner_residual_gives_a_hotter_bondline(self):
        thick = bondline_temperature(1500.0, 0.040, 1000.0, 0.05)
        thin = bondline_temperature(1500.0, 0.030, 1000.0, 0.05)
        self.assertGreater(thin["bondline_k"], thick["bondline_k"])

    def test_drop_exceeding_the_surface_temperature_is_refused(self):
        with self.assertRaises(ValueError):
            bondline_temperature(1500.0, 0.050, 2000.0, 0.05)

    def test_zero_flux_leaves_the_bondline_at_the_surface(self):
        result = bondline_temperature(1500.0, 0.040, 0.0, 0.05)
        self.assertAlmostEqual(result["bondline_k"], 1500.0, places=9)

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            bondline_temperature(1500.0, 0.0, 100.0, 0.05)


class ReuseTests(unittest.TestCase):
    def test_first_cycle_keeps_the_beginning_of_life_value(self):
        self.assertAlmostEqual(emissivity_after_cycles(0.85, 0.01, 1), 0.85, places=9)

    def test_emissivity_walks_down_with_cycles(self):
        self.assertAlmostEqual(emissivity_after_cycles(0.85, 0.01, 10), 0.76, places=9)

    def test_emissivity_is_floored_at_zero(self):
        self.assertAlmostEqual(emissivity_after_cycles(0.2, 0.1, 20), 0.0, places=9)

    def test_zero_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            emissivity_after_cycles(0.85, 0.01, 0)

    def test_reuse_within_qualification_is_acceptable(self):
        result = assess_reuse(validate_item(item()))
        self.assertTrue(result["acceptable"])
        self.assertAlmostEqual(result["end_of_life_emissivity"], 0.76, places=9)

    def test_end_of_life_emissivity_exactly_on_the_floor_is_acceptable(self):
        result = assess_reuse(validate_item(item(emissivity_floor=0.76)))
        self.assertAlmostEqual(
            result["end_of_life_emissivity"], 0.76, places=9
        )
        self.assertTrue(result["emissivity_acceptable"])

    def test_more_cycles_than_qualified_is_a_finding(self):
        result = assess_reuse(validate_item(item(required_cycles=30)))
        self.assertFalse(result["cycles_qualified"])

    def test_degraded_surface_below_the_floor_is_a_finding(self):
        result = assess_reuse(validate_item(item(emissivity_loss_per_cycle=0.03)))
        self.assertFalse(result["emissivity_acceptable"])


class AssessItemTests(unittest.TestCase):
    def test_sound_item_passes_every_constraint(self):
        result = assess_tps_item(item())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["failed_constraints"], [])
        self.assertEqual(result["findings"], [])

    def test_bondline_is_computed_on_the_residual_not_installed_thickness(self):
        result = assess_tps_item(item())
        installed = bondline_temperature(1500.0, 0.050, 1375.0, 0.05)["bondline_k"]
        self.assertGreater(result["bondline"]["bondline_k"], installed)

    def test_bondline_breach_fails_only_the_bondline(self):
        result = assess_tps_item(item(bondline_limit_k=350.0))
        self.assertEqual(result["failed_constraints"], ["bondline"])

    def test_burn_through_leaves_no_bondline_estimate(self):
        result = assess_tps_item(
            item(recession_rate_m_per_s=6.0e-5, required_residual_m=0.0)
        )
        self.assertIsNone(result["bondline"])
        self.assertIn("recession", result["failed_constraints"])
        self.assertTrue(any("burn-through" in f for f in result["findings"]))

    def test_material_breach_fails_only_the_material(self):
        result = assess_tps_item(
            item(max_use_temperature_k=1450.0)
        )
        self.assertEqual(result["failed_constraints"], ["material"])

    def test_reuse_shortfall_fails_only_the_reuse_constraint(self):
        result = assess_tps_item(item(required_cycles=30))
        self.assertEqual(result["failed_constraints"], ["reuse"])

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            assess_tps_item(["name"])


class AssessSetTests(unittest.TestCase):
    def test_set_names_the_material_driver(self):
        result = assess_tps_set(
            [
                item("tile-a"),
                item("tile-b", max_use_temperature_k=1550.0),
            ]
        )
        self.assertEqual(result["material_driver"], "tile-b")
        self.assertAlmostEqual(result["material_driver_margin_k"], 50.0, places=9)
        self.assertTrue(result["acceptable"])

    def test_one_failing_item_fails_the_set(self):
        result = assess_tps_set(
            [
                item("tile-a"),
                item("tile-b", bondline_limit_k=350.0),
            ]
        )
        self.assertFalse(result["acceptable"])
        self.assertEqual(result["failing"], ["tile-b"])

    def test_duplicate_item_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_tps_set([item(), item()])

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_tps_set([])


if __name__ == "__main__":
    unittest.main()
