#!/usr/bin/env python3
"""Gate 3 contract test for e2001-multipactor-verification-process.

Stdlib unittest, offline, deterministic. Run:
    python3 test_e2001_multipactor_verification_process.py
"""

import math
import unittest

import e2001_multipactor_verification_process_logic as logic


def gap(**over):
    rec = {
        "id": "connector-interface",
        "frequency_hz": 12.0e9,
        "gap_m": 0.5e-3,
        "material": "silver",
        "impedance_ohm": 50.0,
        "peak_operating_power_w": 50.0,
    }
    rec.update(over)
    return rec


def good_setup(**over):
    rec = {
        "seeding_source": "strontium-90",
        "detection_methods": ["forward-reverse-power-nulling", "third-harmonic"],
    }
    rec.update(over)
    return rec


def unit(**over):
    rec = {
        "gaps": [gap(), gap(id="filter-iris", peak_operating_power_w=400.0)],
        "test_setup": good_setup(),
    }
    rec.update(over)
    return rec


class TestFrequencyGapProduct(unittest.TestCase):
    def test_product_is_gigahertz_millimetre(self):
        self.assertAlmostEqual(logic.frequency_gap_product(12.0e9, 0.5e-3), 6.0)

    def test_product_scales_linearly_with_the_gap(self):
        one = logic.frequency_gap_product(10.0e9, 1.0e-3)
        two = logic.frequency_gap_product(10.0e9, 2.0e-3)
        self.assertAlmostEqual(two, 2.0 * one)

    def test_similarity_holds_for_the_same_product(self):
        a = logic.frequency_gap_product(20.0e9, 0.25e-3)
        b = logic.frequency_gap_product(5.0e9, 1.0e-3)
        self.assertAlmostEqual(a, b)

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            logic.frequency_gap_product(0.0, 1.0e-3)

    def test_negative_gap_raises(self):
        with self.assertRaises(ValueError):
            logic.frequency_gap_product(12.0e9, -1.0e-3)

    def test_non_numeric_frequency_raises(self):
        with self.assertRaises(ValueError):
            logic.frequency_gap_product("12 GHz", 1.0e-3)


class TestChartBand(unittest.TestCase):
    def test_mid_band_product_is_inside(self):
        self.assertEqual(logic.categorize_gap_band(6.0), logic.BAND_INSIDE)

    def test_product_below_the_band_is_reported(self):
        self.assertEqual(logic.categorize_gap_band(0.02), logic.BAND_BELOW)

    def test_product_above_the_band_is_reported(self):
        self.assertEqual(logic.categorize_gap_band(150.0), logic.BAND_ABOVE)

    def test_lower_band_edge_is_inside(self):
        self.assertEqual(
            logic.categorize_gap_band(logic.FD_BAND_MIN_GHZ_MM), logic.BAND_INSIDE
        )

    def test_upper_band_edge_is_inside(self):
        self.assertEqual(
            logic.categorize_gap_band(logic.FD_BAND_MAX_GHZ_MM), logic.BAND_INSIDE
        )

    def test_zero_product_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_gap_band(0.0)


class TestMaterials(unittest.TestCase):
    def test_silver_resolves(self):
        self.assertAlmostEqual(logic.material_data("silver")["coefficient"], 63.0)

    def test_material_label_is_normalized(self):
        self.assertEqual(logic.material_data("Silver Plated Aluminium")["material"],
                         "silver-plated-aluminium")

    def test_low_yield_surface_breaks_down_later(self):
        fd = 6.0
        self.assertGreater(
            logic.breakdown_voltage(fd, "gold"), logic.breakdown_voltage(fd, "silver")
        )

    def test_alodine_surface_breaks_down_earlier_than_bare_alloy(self):
        fd = 6.0
        self.assertLess(
            logic.breakdown_voltage(fd, "aluminium-alodine"),
            logic.breakdown_voltage(fd, "aluminium-alloy"),
        )

    def test_first_crossover_energy_orders_the_materials(self):
        self.assertGreater(
            logic.material_data("titanium")["sey_first_crossover_ev"],
            logic.material_data("aluminium-alodine")["sey_first_crossover_ev"],
        )

    def test_uncategorized_material_raises(self):
        with self.assertRaises(ValueError):
            logic.material_data("ceramic-alumina")

    def test_blank_material_raises(self):
        with self.assertRaises(ValueError):
            logic.material_data("   ")


class TestBreakdownVoltage(unittest.TestCase):
    def test_threshold_rises_with_the_product(self):
        low = logic.breakdown_voltage(1.0, "silver")
        high = logic.breakdown_voltage(10.0, "silver")
        self.assertGreater(high, low)

    def test_threshold_matches_the_documented_fit(self):
        data = logic.material_data("silver")
        expected = data["coefficient"] * (6.0 ** data["exponent"])
        self.assertAlmostEqual(logic.breakdown_voltage(6.0, "silver"), expected)

    def test_unit_product_returns_the_coefficient(self):
        self.assertAlmostEqual(logic.breakdown_voltage(1.0, "silver"), 63.0)

    def test_product_below_the_band_refuses_extrapolation(self):
        with self.assertRaises(ValueError):
            logic.breakdown_voltage(0.01, "silver")

    def test_product_above_the_band_refuses_extrapolation(self):
        with self.assertRaises(ValueError):
            logic.breakdown_voltage(500.0, "silver")


class TestPowerVoltageConversion(unittest.TestCase):
    def test_power_and_voltage_round_trip(self):
        volt = logic.peak_voltage_from_power(100.0, 50.0)
        self.assertAlmostEqual(logic.power_from_peak_voltage(volt, 50.0), 100.0)

    def test_peak_voltage_matches_the_closed_form(self):
        self.assertAlmostEqual(
            logic.peak_voltage_from_power(100.0, 50.0), math.sqrt(2.0 * 100.0 * 50.0)
        )

    def test_zero_impedance_raises(self):
        with self.assertRaises(ValueError):
            logic.peak_voltage_from_power(100.0, 0.0)

    def test_negative_power_raises(self):
        with self.assertRaises(ValueError):
            logic.peak_voltage_from_power(-5.0, 50.0)

    def test_zero_voltage_raises(self):
        with self.assertRaises(ValueError):
            logic.power_from_peak_voltage(0.0, 50.0)


class TestMargins(unittest.TestCase):
    def test_double_power_is_about_three_decibel(self):
        self.assertAlmostEqual(logic.multipactor_margin_db(50.0, 100.0), 3.0103, places=4)

    def test_equal_power_is_zero_margin(self):
        self.assertAlmostEqual(logic.multipactor_margin_db(80.0, 80.0), 0.0)

    def test_operating_above_threshold_is_a_negative_margin(self):
        self.assertLess(logic.multipactor_margin_db(200.0, 100.0), 0.0)

    def test_voltage_form_agrees_with_the_power_form(self):
        impedance = 50.0
        v_threshold = 400.0
        v_operating = 200.0
        p_threshold = logic.power_from_peak_voltage(v_threshold, impedance)
        p_operating = logic.power_from_peak_voltage(v_operating, impedance)
        self.assertAlmostEqual(
            logic.voltage_margin_db(v_operating, v_threshold),
            logic.multipactor_margin_db(p_operating, p_threshold),
        )

    def test_voltage_ratio_of_two_is_about_six_decibel(self):
        self.assertAlmostEqual(logic.voltage_margin_db(100.0, 200.0), 6.0206, places=4)

    def test_zero_operating_power_raises(self):
        with self.assertRaises(ValueError):
            logic.multipactor_margin_db(0.0, 100.0)

    def test_zero_threshold_voltage_raises(self):
        with self.assertRaises(ValueError):
            logic.voltage_margin_db(100.0, 0.0)


class TestRouteSelection(unittest.TestCase):
    def test_large_margin_takes_the_analysis_route(self):
        self.assertEqual(
            logic.select_verification_route(12.0), logic.ROUTE_ANALYSIS_ONLY
        )

    def test_margin_exactly_on_the_analysis_threshold_takes_the_analysis_route(self):
        self.assertEqual(logic.select_verification_route(8.0), logic.ROUTE_ANALYSIS_ONLY)

    def test_analysis_threshold_reached_by_a_difference_a_few_ulps_short(self):
        # 32.3 dBm threshold minus 24.3 dBm operating is exactly 8 dB
        # physically, but lands a few ULPs under it in binary floating point.
        margin = 32.3 - 24.3
        self.assertLess(margin, 8.0)
        self.assertEqual(
            logic.select_verification_route(margin), logic.ROUTE_ANALYSIS_ONLY
        )

    def test_middle_margin_takes_the_test_route(self):
        self.assertEqual(logic.select_verification_route(5.0), logic.ROUTE_TEST_REQUIRED)

    def test_margin_exactly_on_the_test_threshold_takes_the_test_route(self):
        self.assertEqual(logic.select_verification_route(3.0), logic.ROUTE_TEST_REQUIRED)

    def test_test_threshold_reached_by_a_difference_a_few_ulps_short(self):
        margin = 32.3 - 29.3
        self.assertLess(margin, 3.0)
        self.assertEqual(logic.select_verification_route(margin), logic.ROUTE_TEST_REQUIRED)

    def test_small_margin_forces_redesign(self):
        self.assertEqual(logic.select_verification_route(1.0), logic.ROUTE_REDESIGN)

    def test_negative_margin_forces_redesign(self):
        self.assertEqual(logic.select_verification_route(-4.0), logic.ROUTE_REDESIGN)

    def test_project_thresholds_override_the_defaults(self):
        self.assertEqual(
            logic.select_verification_route(7.0, analysis_margin_db=6.0, test_margin_db=3.0),
            logic.ROUTE_ANALYSIS_ONLY,
        )

    def test_collapsed_thresholds_raise(self):
        with self.assertRaises(ValueError):
            logic.select_verification_route(5.0, analysis_margin_db=3.0, test_margin_db=3.0)

    def test_non_positive_test_threshold_raises(self):
        with self.assertRaises(ValueError):
            logic.select_verification_route(5.0, analysis_margin_db=8.0, test_margin_db=0.0)


class TestElevatedTestLevel(unittest.TestCase):
    def test_three_decibel_roughly_doubles_the_level(self):
        self.assertAlmostEqual(logic.required_test_power(100.0, 3.0103), 200.0, places=2)

    def test_zero_margin_leaves_the_level_unchanged(self):
        self.assertAlmostEqual(logic.required_test_power(100.0, 0.0), 100.0)

    def test_six_decibel_roughly_quadruples_the_level(self):
        self.assertAlmostEqual(logic.required_test_power(100.0, 6.0206), 400.0, places=2)

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            logic.required_test_power(100.0, -1.0)

    def test_zero_operating_power_raises(self):
        with self.assertRaises(ValueError):
            logic.required_test_power(0.0, 3.0)


class TestSetupValidation(unittest.TestCase):
    def test_seeded_global_and_local_pair_is_valid(self):
        out = logic.validate_test_setup(good_setup())
        self.assertTrue(out["valid"])

    def test_single_detection_method_is_a_finding(self):
        out = logic.validate_test_setup(
            good_setup(detection_methods=["third-harmonic"])
        )
        self.assertFalse(out["valid"])
        self.assertIn("fewer than two independent detection methods", out["findings"])

    def test_duplicated_method_does_not_count_twice(self):
        out = logic.validate_test_setup(
            good_setup(detection_methods=["third-harmonic", "third-harmonic"])
        )
        self.assertEqual(out["detection_methods"], ["third-harmonic"])
        self.assertFalse(out["valid"])

    def test_two_local_methods_are_not_a_global_and_local_pair(self):
        out = logic.validate_test_setup(
            good_setup(detection_methods=["third-harmonic", "electron-current-probe"])
        )
        self.assertIn("detection methods are not a global and local pair", out["findings"])

    def test_uncategorized_seeding_source_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_test_setup(good_setup(seeding_source="ambient-cosmic-ray"))

    def test_uncategorized_detection_method_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_test_setup(good_setup(detection_methods=["thermocouple"]))

    def test_missing_seeding_source_raises(self):
        rec = good_setup()
        del rec["seeding_source"]
        with self.assertRaises(ValueError):
            logic.validate_test_setup(rec)

    def test_non_list_detection_methods_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_test_setup(good_setup(detection_methods="third-harmonic"))


class TestGapAssessment(unittest.TestCase):
    def test_comfortable_gap_takes_the_analysis_route(self):
        out = logic.assess_gap(gap())
        self.assertEqual(out["route"], logic.ROUTE_ANALYSIS_ONLY)
        self.assertAlmostEqual(out["fd_ghz_mm"], 6.0)
        self.assertGreater(out["margin_db"], 8.0)

    def test_higher_operating_power_moves_the_gap_to_test(self):
        out = logic.assess_gap(gap(peak_operating_power_w=400.0))
        self.assertEqual(out["route"], logic.ROUTE_TEST_REQUIRED)
        self.assertIn("required_test_power_w", out)
        self.assertAlmostEqual(
            out["required_test_power_w"], 400.0 * (10.0 ** 0.3), places=6
        )

    def test_very_high_operating_power_forces_redesign(self):
        out = logic.assess_gap(gap(peak_operating_power_w=1500.0))
        self.assertEqual(out["route"], logic.ROUTE_REDESIGN)
        self.assertNotIn("required_test_power_w", out)

    def test_out_of_band_gap_is_dropped_with_a_reason(self):
        out = logic.assess_gap(gap(frequency_hz=1.0e9, gap_m=0.02e-3))
        self.assertEqual(out["band"], logic.BAND_BELOW)
        self.assertIsNone(out["route"])
        self.assertIsNone(out["margin_db"])
        self.assertIn("no credible multipactor risk", out["reason"])

    def test_material_choice_changes_the_route(self):
        silver = logic.assess_gap(gap(peak_operating_power_w=380.0, material="silver"))
        gold = logic.assess_gap(gap(peak_operating_power_w=380.0, material="gold"))
        self.assertGreater(gold["margin_db"], silver["margin_db"])

    def test_blank_gap_identifier_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_gap(gap(id="  "))

    def test_missing_gap_key_raises(self):
        rec = gap()
        del rec["impedance_ohm"]
        with self.assertRaises(ValueError):
            logic.assess_gap(rec)

    def test_non_mapping_gap_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_gap(["connector-interface", 12.0e9])

    def test_zero_operating_power_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_gap(gap(peak_operating_power_w=0.0))


class TestUnitVerification(unittest.TestCase):
    def test_unit_with_a_valid_setup_is_verified(self):
        out = logic.run_verification_process(unit())
        self.assertTrue(out["verified"])
        self.assertEqual(out["to_test"], ["filter-iris"])
        self.assertEqual(out["redesign"], [])

    def test_gaps_routed_to_test_without_a_setup_block_the_verdict(self):
        rec = unit()
        del rec["test_setup"]
        out = logic.run_verification_process(rec)
        self.assertFalse(out["verified"])
        self.assertIn("gaps routed to test with no test setup on record", out["findings"])

    def test_a_gap_needing_redesign_blocks_the_verdict(self):
        rec = unit(
            gaps=[gap(), gap(id="coupling-slot", peak_operating_power_w=1500.0)]
        )
        out = logic.run_verification_process(rec)
        self.assertFalse(out["verified"])
        self.assertEqual(out["redesign"], ["coupling-slot"])

    def test_an_invalid_setup_blocks_the_verdict(self):
        rec = unit(test_setup=good_setup(detection_methods=["third-harmonic"]))
        out = logic.run_verification_process(rec)
        self.assertFalse(out["verified"])
        self.assertTrue(any(f.startswith("test-setup") for f in out["findings"]))

    def test_analysis_only_unit_needs_no_setup(self):
        rec = {"gaps": [gap(), gap(id="waveguide-step", peak_operating_power_w=40.0)]}
        out = logic.run_verification_process(rec)
        self.assertTrue(out["verified"])
        self.assertEqual(out["to_test"], [])

    def test_out_of_band_gaps_are_listed_separately(self):
        rec = unit(
            gaps=[gap(), gap(id="wide-cavity", frequency_hz=30.0e9, gap_m=6.0e-3)]
        )
        out = logic.run_verification_process(rec)
        self.assertEqual(out["out_of_band"], ["wide-cavity"])

    def test_worst_margin_ignores_out_of_band_gaps(self):
        rec = unit(
            gaps=[
                gap(),
                gap(id="filter-iris", peak_operating_power_w=400.0),
                gap(id="wide-cavity", frequency_hz=30.0e9, gap_m=6.0e-3),
            ]
        )
        out = logic.run_verification_process(rec)
        graded = [g["margin_db"] for g in out["gaps"] if g["margin_db"] is not None]
        self.assertAlmostEqual(out["worst_margin_db"], min(graded))

    def test_project_thresholds_reach_the_gap_assessment(self):
        rec = unit(
            gaps=[gap(id="filter-iris", peak_operating_power_w=400.0)],
            analysis_margin_db=6.0,
            test_margin_db=3.0,
        )
        out = logic.run_verification_process(rec)
        self.assertEqual(out["to_test"], [])
        self.assertTrue(out["verified"])

    def test_unit_with_no_gap_raises(self):
        with self.assertRaises(ValueError):
            logic.run_verification_process({"gaps": []})

    def test_unit_missing_the_gaps_key_raises(self):
        with self.assertRaises(ValueError):
            logic.run_verification_process({"test_setup": good_setup()})

    def test_non_mapping_unit_raises(self):
        with self.assertRaises(ValueError):
            logic.run_verification_process(["filter-iris"])


if __name__ == "__main__":
    unittest.main()
