"""Contract test for the black-anodizing parameters leaf (stdlib unittest)."""

import unittest

from q7003_anodizing_process_parameters_logic import (
    COATING_RATE_UM_PER_A_DM2_MIN,
    DISSOLUTION_PER_DEGREE,
    LIMITING_TEMPERATURE_C,
    MAX_BATH_TEMPERATURE_C,
    MAX_CHLORIDE_G_L,
    MAX_CURRENT_DENSITY_A_DM2,
    MAX_DISSOLVED_ALUMINIUM_G_L,
    MAX_FREE_ACID_G_L,
    MIN_BATH_TEMPERATURE_C,
    MIN_CURRENT_DENSITY_A_DM2,
    MIN_FREE_ACID_G_L,
    REFERENCE_TEMPERATURE_C,
    assess_anodizing_run,
    assess_anodizing_runs,
    check_electrical,
    check_electrolyte,
    coating_thickness_um,
    dissolution_factor,
    growth_rate_um_per_min,
    required_time_min,
    total_current_a,
    validate_run,
)


def run(rid="R-1", **kw):
    record = {
        "id": rid,
        "free_acid_g_l": 180.0,
        "dissolved_aluminium_g_l": 5.0,
        "chloride_g_l": 0.01,
        "current_density_a_dm2": 1.5,
        "temperature_c": 20.0,
        "minutes": 25.0,
        "racked_area_dm2": 10.0,
        "target_thickness_um": 10.0,
        "agitation": "air-sparge",
    }
    record.update(kw)
    return record


class TestDissolution(unittest.TestCase):
    def test_at_the_reference_temperature_nothing_is_lost(self):
        self.assertAlmostEqual(
            dissolution_factor(REFERENCE_TEMPERATURE_C), 1.0, places=9
        )

    def test_below_the_reference_temperature_nothing_is_lost(self):
        self.assertAlmostEqual(
            dissolution_factor(REFERENCE_TEMPERATURE_C - 5.0), 1.0, places=9
        )

    def test_above_the_reference_the_loss_is_linear(self):
        expected = 1.0 - DISSOLUTION_PER_DEGREE * 2.0
        self.assertAlmostEqual(
            dissolution_factor(REFERENCE_TEMPERATURE_C + 2.0), expected, places=9
        )

    def test_at_the_limiting_temperature_nothing_survives(self):
        self.assertAlmostEqual(
            dissolution_factor(LIMITING_TEMPERATURE_C), 0.0, places=9
        )

    def test_non_numeric_temperature_raises(self):
        with self.assertRaises(ValueError):
            dissolution_factor("twenty")


class TestGrowth(unittest.TestCase):
    def test_rate_at_the_reference_is_the_constant_times_the_density(self):
        self.assertAlmostEqual(
            growth_rate_um_per_min(1.5, REFERENCE_TEMPERATURE_C),
            COATING_RATE_UM_PER_A_DM2_MIN * 1.5,
            places=9,
        )

    def test_thickness_is_rate_times_time(self):
        rate = growth_rate_um_per_min(1.5, 20.0)
        self.assertAlmostEqual(
            coating_thickness_um(1.5, 20.0, 25.0), rate * 25.0, places=9
        )

    def test_a_hot_bath_grows_a_thinner_coating(self):
        cool = coating_thickness_um(1.5, 20.0, 25.0)
        warm = coating_thickness_um(1.5, 24.0, 25.0)
        self.assertLess(warm, cool)

    def test_growth_beyond_the_limiting_temperature_raises(self):
        with self.assertRaises(ValueError):
            growth_rate_um_per_min(1.5, LIMITING_TEMPERATURE_C + 5.0)

    def test_negative_current_density_raises(self):
        with self.assertRaises(ValueError):
            growth_rate_um_per_min(-1.0, 20.0)

    def test_negative_time_raises(self):
        with self.assertRaises(ValueError):
            coating_thickness_um(1.5, 20.0, -1.0)


class TestRequiredTime(unittest.TestCase):
    def test_required_time_inverts_the_growth(self):
        minutes = required_time_min(10.0, 1.5, 20.0)
        self.assertAlmostEqual(coating_thickness_um(1.5, 20.0, minutes), 10.0,
                               places=9)

    def test_a_hot_bath_needs_longer(self):
        self.assertGreater(
            required_time_min(10.0, 1.5, 24.0), required_time_min(10.0, 1.5, 20.0)
        )

    def test_negative_target_raises(self):
        with self.assertRaises(ValueError):
            required_time_min(-1.0, 1.5, 20.0)

    def test_zero_current_density_raises(self):
        with self.assertRaises(ValueError):
            required_time_min(10.0, 0.0, 20.0)


class TestRectifierSizing(unittest.TestCase):
    def test_current_is_density_times_area(self):
        self.assertAlmostEqual(total_current_a(1.5, 12.0), 18.0, places=9)

    def test_zero_area_raises(self):
        with self.assertRaises(ValueError):
            total_current_a(1.5, 0.0)

    def test_boolean_area_is_rejected(self):
        with self.assertRaises(ValueError):
            total_current_a(1.5, True)


class TestElectrolyte(unittest.TestCase):
    def test_a_bath_inside_every_window_is_clean(self):
        self.assertEqual(check_electrolyte(180.0, 5.0, 0.01), [])

    def test_free_acid_on_either_bound_is_accepted(self):
        self.assertEqual(check_electrolyte(MIN_FREE_ACID_G_L, 5.0, 0.01), [])
        self.assertEqual(check_electrolyte(MAX_FREE_ACID_G_L, 5.0, 0.01), [])

    def test_weak_acid_is_found(self):
        self.assertIn(
            "free-acid-below-the-electrolyte-window",
            check_electrolyte(MIN_FREE_ACID_G_L - 10.0, 5.0, 0.01),
        )

    def test_strong_acid_is_found(self):
        self.assertIn(
            "free-acid-above-the-electrolyte-window",
            check_electrolyte(MAX_FREE_ACID_G_L + 10.0, 5.0, 0.01),
        )

    def test_dissolved_aluminium_above_the_limit_is_found(self):
        self.assertIn(
            "dissolved-aluminium-above-the-bath-limit",
            check_electrolyte(180.0, MAX_DISSOLVED_ALUMINIUM_G_L + 1.0, 0.01),
        )

    def test_chloride_above_the_limit_is_found(self):
        self.assertIn(
            "chloride-above-the-pitting-limit",
            check_electrolyte(180.0, 5.0, MAX_CHLORIDE_G_L * 2.0),
        )

    def test_negative_chloride_raises(self):
        with self.assertRaises(ValueError):
            check_electrolyte(180.0, 5.0, -0.01)


class TestElectrical(unittest.TestCase):
    def test_parameters_inside_the_windows_are_clean(self):
        self.assertEqual(check_electrical(1.5, 20.0, "air-sparge"), [])

    def test_bounds_themselves_are_accepted(self):
        self.assertEqual(
            check_electrical(MIN_CURRENT_DENSITY_A_DM2, MIN_BATH_TEMPERATURE_C,
                             "solution-pumping"),
            [],
        )
        self.assertEqual(
            check_electrical(MAX_CURRENT_DENSITY_A_DM2, MAX_BATH_TEMPERATURE_C,
                             "solution-pumping"),
            [],
        )

    def test_low_current_density_is_found(self):
        self.assertIn(
            "current-density-below-the-process-window",
            check_electrical(MIN_CURRENT_DENSITY_A_DM2 - 0.3, 20.0, "air-sparge"),
        )

    def test_hot_bath_is_found(self):
        self.assertIn(
            "bath-temperature-above-the-process-window",
            check_electrical(1.5, MAX_BATH_TEMPERATURE_C + 2.0, "air-sparge"),
        )

    def test_missing_agitation_is_found(self):
        self.assertIn(
            "no-agitation-declared-for-the-anodizing-tank",
            check_electrical(1.5, 20.0, "none"),
        )

    def test_unknown_agitation_raises(self):
        with self.assertRaises(ValueError):
            check_electrical(1.5, 20.0, "hand-stirring")


class TestValidateRun(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_run({"id": "R-9"})
        self.assertAlmostEqual(norm["current_density_a_dm2"], 1.5, places=9)
        self.assertEqual(norm["agitation"], "air-sparge")

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_run(["R-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_run(run(""))

    def test_unknown_agitation_raises(self):
        with self.assertRaises(ValueError):
            validate_run(run(agitation="wishful"))


class TestAssessRun(unittest.TestCase):
    def test_a_sound_run_is_compliant(self):
        result = assess_anodizing_run(run())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["total_current_a"], 15.0, places=9)

    def test_a_short_run_misses_the_target(self):
        result = assess_anodizing_run(run(minutes=5.0))
        self.assertIn("achieved-thickness-below-the-target", result["findings"])

    def test_a_run_landing_exactly_on_the_target_is_accepted(self):
        minutes = required_time_min(10.0, 1.5, 20.0)
        result = assess_anodizing_run(run(minutes=minutes, target_thickness_um=10.0))
        self.assertNotIn("achieved-thickness-below-the-target", result["findings"])
        self.assertAlmostEqual(result["achieved_thickness_um"], 10.0, places=9)

    def test_a_run_past_the_limiting_temperature_reports_no_thickness(self):
        result = assess_anodizing_run(run(temperature_c=LIMITING_TEMPERATURE_C + 2.0))
        self.assertIsNone(result["achieved_thickness_um"])
        self.assertIn("bath-temperature-at-or-above-the-limiting-temperature",
                      result["findings"])

    def test_batch_reports_the_failing_runs(self):
        report = assess_anodizing_runs([run("R-1"), run("R-2", minutes=2.0)])
        self.assertEqual(report["non_compliant_ids"], ["R-2"])
        self.assertFalse(report["compliant"])

    def test_duplicate_run_id_raises(self):
        with self.assertRaises(ValueError):
            assess_anodizing_runs([run("R-1"), run("R-1")])

    def test_empty_batch_raises(self):
        with self.assertRaises(ValueError):
            assess_anodizing_runs([])


if __name__ == "__main__":
    unittest.main()
