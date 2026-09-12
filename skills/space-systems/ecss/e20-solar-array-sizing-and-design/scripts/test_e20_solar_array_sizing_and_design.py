"""Gate 3 contract test for the ECSS-E-ST-20C 5.5.2 solar array sizing leaf.

stdlib unittest, offline, deterministic. Run:
    python3 test_e20_solar_array_sizing_and_design.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_solar_array_sizing_and_design_logic as logic  # noqa: E402


def full_sun_phase(**overrides):
    phase = {
        "name": "full-sun-cruise",
        "orbit_period_s": 5400.0,
        "eclipse_duration_s": 0.0,
        "sunlit_load_w": 1000.0,
        "eclipse_load_w": 0.0,
        "duration_days": 60.0,
        "sun_incidence_deg": 0.0,
    }
    phase.update(overrides)
    return phase


def eclipse_phase(**overrides):
    phase = {
        "name": "leo-nominal",
        "orbit_period_s": 6000.0,
        "eclipse_duration_s": 2000.0,
        "sunlit_load_w": 800.0,
        "eclipse_load_w": 600.0,
        "duration_days": 365.0,
        "sun_incidence_deg": 0.0,
    }
    phase.update(overrides)
    return phase


def dark_phase(**overrides):
    phase = {
        "name": "eclipse-coast",
        "orbit_period_s": 5400.0,
        "eclipse_duration_s": 5400.0,
        "sunlit_load_w": 0.0,
        "eclipse_load_w": 400.0,
        "duration_days": 1.0,
        "sun_incidence_deg": 0.0,
    }
    phase.update(overrides)
    return phase


class TestPhaseValidation(unittest.TestCase):
    def test_validate_phase_derives_sunlit_duration(self):
        record = logic.validate_phase(eclipse_phase())
        self.assertAlmostEqual(record["sunlit_duration_s"], 4000.0, places=9)
        self.assertEqual(record["name"], "leo-nominal")

    def test_validate_phase_rejects_non_mapping(self):
        with self.assertRaises(ValueError):
            logic.validate_phase(["leo-nominal", 6000.0])

    def test_validate_phase_rejects_empty_name(self):
        with self.assertRaises(ValueError):
            logic.validate_phase(eclipse_phase(name="  "))

    def test_validate_phase_rejects_non_positive_orbit_period(self):
        with self.assertRaises(ValueError):
            logic.validate_phase(eclipse_phase(orbit_period_s=0.0))

    def test_validate_phase_rejects_eclipse_longer_than_orbit(self):
        with self.assertRaises(ValueError):
            logic.validate_phase(eclipse_phase(eclipse_duration_s=6001.0))

    def test_validate_phase_rejects_negative_eclipse(self):
        with self.assertRaises(ValueError):
            logic.validate_phase(eclipse_phase(eclipse_duration_s=-1.0))

    def test_validate_phase_rejects_negative_load(self):
        with self.assertRaises(ValueError):
            logic.validate_phase(eclipse_phase(sunlit_load_w=-5.0))

    def test_validate_phase_rejects_both_loads_zero(self):
        with self.assertRaises(ValueError):
            logic.validate_phase(eclipse_phase(sunlit_load_w=0.0, eclipse_load_w=0.0))

    def test_validate_phase_rejects_non_positive_duration_days(self):
        with self.assertRaises(ValueError):
            logic.validate_phase(eclipse_phase(duration_days=0.0))

    def test_validate_phase_rejects_incidence_at_ninety(self):
        with self.assertRaises(ValueError):
            logic.validate_phase(eclipse_phase(sun_incidence_deg=90.0))

    def test_validate_phase_rejects_non_finite_number(self):
        with self.assertRaises(ValueError):
            logic.validate_phase(eclipse_phase(orbit_period_s=float("inf")))


class TestIlluminationRegime(unittest.TestCase):
    def test_zero_eclipse_is_continuous_sunlight(self):
        self.assertEqual(
            logic.categorize_illumination(full_sun_phase()), logic.CONTINUOUS_SUNLIGHT
        )

    def test_partial_eclipse_is_eclipse_cycling(self):
        self.assertEqual(
            logic.categorize_illumination(eclipse_phase()), logic.ECLIPSE_CYCLING
        )

    def test_full_eclipse_is_dark_coast(self):
        self.assertEqual(logic.categorize_illumination(dark_phase()), logic.DARK_COAST)

    def test_every_regime_is_a_declared_regime(self):
        for phase in (full_sun_phase(), eclipse_phase(), dark_phase()):
            self.assertIn(
                logic.categorize_illumination(phase), logic.ILLUMINATION_REGIMES
            )


class TestRequiredArrayPower(unittest.TestCase):
    def test_full_sun_phase_is_load_over_path_efficiency(self):
        power = logic.required_array_power(full_sun_phase())
        self.assertAlmostEqual(power, 1111.1111111, places=6)

    def test_eclipse_phase_adds_the_recharge_term(self):
        power = logic.required_array_power(eclipse_phase())
        self.assertAlmostEqual(power, 1267.6767677, places=6)

    def test_shorter_sunlit_window_costs_more_array_power(self):
        wide = logic.required_array_power(eclipse_phase(eclipse_duration_s=1000.0))
        narrow = logic.required_array_power(eclipse_phase(eclipse_duration_s=4000.0))
        self.assertGreater(narrow, wide)

    def test_dark_coast_phase_demands_no_array_power(self):
        self.assertAlmostEqual(logic.required_array_power(dark_phase()), 0.0, places=9)

    def test_rejects_efficiency_above_one(self):
        with self.assertRaises(ValueError):
            logic.required_array_power(eclipse_phase(), charge_efficiency=1.4)

    def test_rejects_zero_efficiency(self):
        with self.assertRaises(ValueError):
            logic.required_array_power(eclipse_phase(), sunlit_path_efficiency=0.0)


class TestEndOfLifeDensity(unittest.TestCase):
    def test_matches_hand_calculation(self):
        density = logic.end_of_life_power_density(
            340.0, 0.88, 0.025, 2.0, 65.0, -0.0045, 0.0
        )
        self.assertAlmostEqual(density, 237.0699045, places=6)

    def test_incidence_angle_applies_a_cosine_factor(self):
        normal = logic.end_of_life_power_density(
            340.0, 0.88, 0.025, 2.0, 65.0, -0.0045, 0.0
        )
        oblique = logic.end_of_life_power_density(
            340.0, 0.88, 0.025, 2.0, 65.0, -0.0045, 60.0
        )
        self.assertAlmostEqual(oblique, normal * 0.5, places=6)

    def test_later_epoch_gives_lower_density(self):
        early = logic.end_of_life_power_density(
            340.0, 0.88, 0.025, 1.0, 65.0, -0.0045, 0.0
        )
        late = logic.end_of_life_power_density(
            340.0, 0.88, 0.025, 12.0, 65.0, -0.0045, 0.0
        )
        self.assertLess(late, early)

    def test_rejects_positive_temperature_coefficient(self):
        with self.assertRaises(ValueError):
            logic.end_of_life_power_density(340.0, 0.88, 0.025, 2.0, 65.0, 0.002, 0.0)

    def test_rejects_negative_elapsed_years(self):
        with self.assertRaises(ValueError):
            logic.end_of_life_power_density(340.0, 0.88, 0.025, -1.0, 65.0, -0.0045, 0.0)

    def test_rejects_annual_degradation_at_one(self):
        with self.assertRaises(ValueError):
            logic.end_of_life_power_density(340.0, 0.88, 1.0, 2.0, 65.0, -0.0045, 0.0)

    def test_rejects_collapsed_temperature_factor(self):
        with self.assertRaises(ValueError):
            logic.end_of_life_power_density(
                340.0, 0.88, 0.025, 2.0, 400.0, -0.0045, 0.0
            )

    def test_rejects_non_positive_reference_density(self):
        with self.assertRaises(ValueError):
            logic.end_of_life_power_density(0.0, 0.88, 0.025, 2.0, 65.0, -0.0045, 0.0)


class TestAreaSizing(unittest.TestCase):
    def test_applies_the_design_margin(self):
        self.assertAlmostEqual(logic.size_array_area(1000.0, 200.0, 0.15), 5.75, places=9)

    def test_zero_margin_is_allowed_boundary(self):
        self.assertAlmostEqual(logic.size_array_area(1000.0, 200.0, 0.0), 5.0, places=9)

    def test_rejects_zero_density(self):
        with self.assertRaises(ValueError):
            logic.size_array_area(1000.0, 0.0, 0.15)

    def test_rejects_margin_at_one(self):
        with self.assertRaises(ValueError):
            logic.size_array_area(1000.0, 200.0, 1.0)

    def test_rejects_negative_required_power(self):
        with self.assertRaises(ValueError):
            logic.size_array_area(-1.0, 200.0, 0.15)


class TestEnergyBalance(unittest.TestCase):
    def test_generated_over_consumed_margin(self):
        result = logic.energy_balance(full_sun_phase(), 10.0, 200.0)
        self.assertAlmostEqual(result["margin"], 0.8, places=9)
        self.assertTrue(result["closes"])

    def test_undersized_array_closes_negative(self):
        result = logic.energy_balance(full_sun_phase(), 1.0, 200.0)
        self.assertFalse(result["closes"])
        self.assertLess(result["margin"], 0.0)

    def test_dark_coast_phase_never_closes(self):
        result = logic.energy_balance(dark_phase(), 10.0, 200.0)
        self.assertEqual(result["regime"], logic.DARK_COAST)
        self.assertFalse(result["closes"])

    def test_rejects_zero_area(self):
        with self.assertRaises(ValueError):
            logic.energy_balance(full_sun_phase(), 0.0, 200.0)

    def test_rejects_zero_density(self):
        with self.assertRaises(ValueError):
            logic.energy_balance(full_sun_phase(), 10.0, 0.0)


class TestSizeSolarArray(unittest.TestCase):
    def setUp(self):
        self.commissioning = eclipse_phase(
            name="commissioning",
            orbit_period_s=5400.0,
            eclipse_duration_s=2100.0,
            sunlit_load_w=900.0,
            eclipse_load_w=700.0,
            duration_days=30.0,
            sun_incidence_deg=10.0,
        )
        self.nominal = eclipse_phase(
            name="nominal-operations",
            orbit_period_s=5400.0,
            eclipse_duration_s=2100.0,
            sunlit_load_w=850.0,
            eclipse_load_w=650.0,
            duration_days=2500.0,
            sun_incidence_deg=25.0,
        )

    def test_late_degraded_phase_drives_the_area(self):
        result = logic.size_solar_array([self.commissioning, self.nominal])
        self.assertEqual(result["driving_phase"], "nominal-operations")
        self.assertGreater(result["selected_area_m2"], 0.0)
        self.assertTrue(result["compliant"])

    def test_smaller_load_can_still_drive_the_size(self):
        result = logic.size_solar_array([self.commissioning, self.nominal])
        by_name = {entry["name"]: entry for entry in result["phases"]}
        self.assertLess(
            by_name["nominal-operations"]["required_power_w"],
            by_name["commissioning"]["required_power_w"],
        )
        self.assertGreater(
            by_name["nominal-operations"]["required_area_m2"],
            by_name["commissioning"]["required_area_m2"],
        )

    def test_dark_coast_phase_is_reported_as_unsized(self):
        result = logic.size_solar_array([self.nominal, dark_phase()])
        self.assertFalse(result["compliant"])
        self.assertTrue(any("dark-coast" in f for f in result["findings"]))

    def test_all_dark_phases_cannot_be_sized(self):
        with self.assertRaises(ValueError):
            logic.size_solar_array([dark_phase()])

    def test_rejects_empty_phase_list(self):
        with self.assertRaises(ValueError):
            logic.size_solar_array([])

    def test_rejects_unknown_cell_spec_key(self):
        with self.assertRaises(ValueError):
            logic.size_solar_array([self.nominal], cell_spec={"efficiency": 0.3})

    def test_rejects_non_mapping_cell_spec(self):
        with self.assertRaises(ValueError):
            logic.size_solar_array([self.nominal], cell_spec=[0.3])

    def test_result_is_deterministic_across_runs(self):
        first = logic.size_solar_array([self.commissioning, self.nominal])
        second = logic.size_solar_array([self.commissioning, self.nominal])
        self.assertAlmostEqual(
            first["selected_area_m2"], second["selected_area_m2"], places=12
        )
        self.assertEqual(first["findings"], second["findings"])


if __name__ == "__main__":
    unittest.main()
