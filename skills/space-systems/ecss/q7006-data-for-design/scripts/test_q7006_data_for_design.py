"""Contract test for the radiation data-for-design leaf (stdlib unittest)."""

import unittest

from q7006_data_for_design_logic import (
    DESIGN_CASES,
    ENVELOPE_AT_LEAST,
    ENVELOPE_AT_MOST,
    MIN_EMITTANCE,
    STEFAN_BOLTZMANN_W_M2_K4,
    alpha_over_epsilon,
    build_design_data,
    clamp_absorptance,
    clamp_emittance,
    design_pair,
    envelope_ratio,
    envelope_shortfalls,
    equilibrium_temperature_k,
)

TEST_ENVELOPE = {
    "particle_fluence_cm2": 2.0e15,
    "uv_dose_esh": 2000.0,
    "max_temperature_c": 120.0,
    "min_temperature_c": -120.0,
}

MISSION_ENVELOPE = {
    "particle_fluence_cm2": 1.0e15,
    "uv_dose_esh": 1500.0,
    "max_temperature_c": 100.0,
    "min_temperature_c": -90.0,
}


def record(**kw):
    item = {
        "material": "white pigmented silicone coating",
        "bol_absorptance": 0.200,
        "eol_absorptance": 0.320,
        "bol_emittance": 0.880,
        "eol_emittance": 0.860,
        "absorptance_uncertainty": 0.010,
        "emittance_uncertainty": 0.005,
        "solar_flux_w_m2": 1361.0,
        "test_envelope": dict(TEST_ENVELOPE),
        "mission_envelope": dict(MISSION_ENVELOPE),
    }
    item.update(kw)
    return item


class TestOpticalRange(unittest.TestCase):
    def test_an_absorptance_above_one_is_clamped(self):
        self.assertAlmostEqual(clamp_absorptance(1.4), 1.0, places=9)

    def test_a_negative_absorptance_is_clamped_to_zero(self):
        self.assertAlmostEqual(clamp_absorptance(-0.2), 0.0, places=9)

    def test_an_emittance_is_never_clamped_below_the_floor(self):
        self.assertAlmostEqual(clamp_emittance(-0.5), MIN_EMITTANCE, places=12)

    def test_an_emittance_above_one_is_clamped(self):
        self.assertAlmostEqual(clamp_emittance(1.3), 1.0, places=9)

    def test_an_absorptance_outside_the_physical_range_raises(self):
        with self.assertRaises(ValueError):
            alpha_over_epsilon(1.4, 0.88)

    def test_a_vanishing_emittance_raises(self):
        with self.assertRaises(ValueError):
            alpha_over_epsilon(0.20, 0.0)

    def test_a_non_numeric_absorptance_raises(self):
        with self.assertRaises(ValueError):
            alpha_over_epsilon("0.20", 0.88)


class TestRatioAndTemperature(unittest.TestCase):
    def test_the_ratio_is_absorptance_over_emittance(self):
        self.assertAlmostEqual(alpha_over_epsilon(0.20, 0.80), 0.25, places=9)

    def test_a_grey_surface_sits_at_the_black_body_temperature(self):
        expected = (1361.0 / STEFAN_BOLTZMANN_W_M2_K4) ** 0.25
        self.assertAlmostEqual(
            equilibrium_temperature_k(0.90, 0.90, 1361.0), expected, delta=1.0e-6
        )

    def test_a_darker_surface_runs_hotter(self):
        cool = equilibrium_temperature_k(0.20, 0.88, 1361.0)
        warm = equilibrium_temperature_k(0.40, 0.88, 1361.0)
        self.assertGreater(warm - cool, 1.0)

    def test_doubling_the_ratio_raises_the_temperature_by_the_fourth_root_of_two(self):
        cool = equilibrium_temperature_k(0.20, 0.80, 1361.0)
        warm = equilibrium_temperature_k(0.40, 0.80, 1361.0)
        self.assertAlmostEqual(warm / cool, 2.0 ** 0.25, delta=1.0e-9)

    def test_a_zero_solar_flux_raises(self):
        with self.assertRaises(ValueError):
            equilibrium_temperature_k(0.20, 0.88, 0.0)


class TestEnvelope(unittest.TestCase):
    def test_a_covering_test_has_no_shortfall(self):
        self.assertEqual(envelope_shortfalls(TEST_ENVELOPE, MISSION_ENVELOPE), [])

    def test_a_short_fluence_is_a_shortfall(self):
        tested = dict(TEST_ENVELOPE, particle_fluence_cm2=5.0e14)
        self.assertIn("particle_fluence_cm2", envelope_shortfalls(tested, MISSION_ENVELOPE))

    def test_a_test_exactly_at_the_mission_exposure_covers_it(self):
        tested = dict(TEST_ENVELOPE, uv_dose_esh=MISSION_ENVELOPE["uv_dose_esh"])
        self.assertNotIn("uv_dose_esh", envelope_shortfalls(tested, MISSION_ENVELOPE))

    def test_a_test_that_never_went_cold_enough_is_a_shortfall(self):
        tested = dict(TEST_ENVELOPE, min_temperature_c=-40.0)
        self.assertIn("min_temperature_c", envelope_shortfalls(tested, MISSION_ENVELOPE))

    def test_a_missing_axis_is_a_shortfall(self):
        tested = dict(TEST_ENVELOPE)
        del tested["max_temperature_c"]
        self.assertIn("max_temperature_c", envelope_shortfalls(tested, MISSION_ENVELOPE))

    def test_every_declared_axis_is_checked(self):
        self.assertEqual(
            envelope_shortfalls({}, {}),
            sorted(ENVELOPE_AT_LEAST + ENVELOPE_AT_MOST),
        )

    def test_the_envelope_ratio_is_the_exposure_ratio(self):
        self.assertAlmostEqual(envelope_ratio(2.0e15, 1.0e15), 2.0, places=9)

    def test_a_zero_mission_exposure_has_no_envelope_ratio(self):
        with self.assertRaises(ValueError):
            envelope_ratio(2.0e15, 0.0)

    def test_a_non_mapping_envelope_raises(self):
        with self.assertRaises(ValueError):
            envelope_shortfalls("wide", MISSION_ENVELOPE)


class TestDesignPairs(unittest.TestCase):
    def test_the_hot_case_takes_the_worst_corner(self):
        alpha, epsilon = design_pair(record(), "hot")
        self.assertAlmostEqual(alpha, 0.330, places=9)
        self.assertAlmostEqual(epsilon, 0.855, places=9)

    def test_the_cold_case_takes_the_opposite_corner(self):
        alpha, epsilon = design_pair(record(), "cold")
        self.assertAlmostEqual(alpha, 0.190, places=9)
        self.assertAlmostEqual(epsilon, 0.885, places=9)

    def test_the_hot_case_ratio_is_above_the_cold_case_one(self):
        hot_alpha, hot_eps = design_pair(record(), "hot")
        cold_alpha, cold_eps = design_pair(record(), "cold")
        self.assertGreater(
            alpha_over_epsilon(hot_alpha, hot_eps),
            alpha_over_epsilon(cold_alpha, cold_eps),
        )

    def test_a_pair_is_available_for_every_declared_case(self):
        for case in DESIGN_CASES:
            alpha, epsilon = design_pair(record(), case)
            self.assertGreaterEqual(alpha, 0.0)
            self.assertGreaterEqual(epsilon, MIN_EMITTANCE)

    def test_an_unknown_design_case_raises(self):
        with self.assertRaises(ValueError):
            design_pair(record(), "warm")

    def test_an_uncertainty_wider_than_the_property_is_clamped_not_negative(self):
        alpha, _ = design_pair(record(absorptance_uncertainty=0.9), "cold")
        self.assertAlmostEqual(alpha, 0.0, places=9)


class TestDesignData(unittest.TestCase):
    def test_a_covered_campaign_issues_design_data(self):
        data = build_design_data(record())
        self.assertEqual(data["findings"], [])
        self.assertTrue(data["issuable"])

    def test_the_ratio_grows_from_beginning_to_end_of_life(self):
        data = build_design_data(record())
        self.assertGreater(data["ratio_growth"], 1.0)
        self.assertAlmostEqual(
            data["bol_alpha_over_epsilon"], 0.200 / 0.880, places=9
        )

    def test_the_hot_case_runs_hotter_than_the_cold_case(self):
        data = build_design_data(record())
        self.assertGreater(
            data["cases"]["hot"]["equilibrium_temperature_k"],
            data["cases"]["cold"]["equilibrium_temperature_k"],
        )

    def test_an_uncovered_mission_blocks_the_issue(self):
        data = build_design_data(
            record(test_envelope=dict(TEST_ENVELOPE, uv_dose_esh=100.0))
        )
        self.assertIn("test-envelope-does-not-cover-the-mission", data["findings"])
        self.assertFalse(data["issuable"])
        self.assertIn("uv_dose_esh", data["envelope_shortfalls"])

    def test_data_issued_with_no_uncertainty_allowance_is_a_finding(self):
        data = build_design_data(record(absorptance_uncertainty=0.0))
        self.assertIn(
            "design-data-issued-without-an-uncertainty-allowance", data["findings"]
        )

    def test_an_absorptance_above_its_allocation_is_a_finding(self):
        data = build_design_data(record(allocated_eol_absorptance=0.300))
        self.assertIn("hot-case-absorptance-above-its-allocation", data["findings"])

    def test_an_allocation_exactly_on_the_hot_case_value_is_met(self):
        data = build_design_data(record(allocated_eol_absorptance=0.330))
        self.assertNotIn("hot-case-absorptance-above-its-allocation", data["findings"])

    def test_an_emittance_under_its_allocated_floor_is_a_finding(self):
        data = build_design_data(record(allocated_eol_emittance_floor=0.900))
        self.assertIn("hot-case-emittance-below-its-allocation", data["findings"])

    def test_a_ratio_above_the_thermal_allocation_is_a_finding(self):
        data = build_design_data(record(allocated_eol_alpha_over_epsilon=0.300))
        self.assertIn("hot-case-ratio-above-the-thermal-allocation", data["findings"])

    def test_a_generous_ratio_allocation_is_met(self):
        data = build_design_data(record(allocated_eol_alpha_over_epsilon=0.600))
        self.assertNotIn(
            "hot-case-ratio-above-the-thermal-allocation", data["findings"]
        )

    def test_a_blank_material_name_raises(self):
        with self.assertRaises(ValueError):
            build_design_data(record(material="   "))

    def test_a_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            build_design_data(["white pigmented silicone coating"])


if __name__ == "__main__":
    unittest.main()
