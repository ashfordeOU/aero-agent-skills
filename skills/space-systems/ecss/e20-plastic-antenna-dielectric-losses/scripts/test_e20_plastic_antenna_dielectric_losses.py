#!/usr/bin/env python3
"""Contract test for the plastic part dielectric loss leaf.

Offline, deterministic, python3 standard library only.
Run: python3 test_e20_plastic_antenna_dielectric_losses.py
"""

import unittest

import e20_plastic_antenna_dielectric_losses_logic as logic


def _radome(**overrides):
    part = {
        "label": "feed-radome",
        "part_type": "radome",
        "thickness_m": 0.003,
        "relative_permittivity": 2.6,
        "loss_tangent": 0.0005,
        "thermal_resistance_k_per_w": 20.0,
        "maximum_use_temperature_k": 420.0,
    }
    part.update(overrides)
    return part


def _strut(**overrides):
    part = {"label": "mount-strut", "part_type": "structural-bracket-outside-field"}
    part.update(overrides)
    return part


def _run(parts=None, frequency_hz=12.0e9, input_power_w=100.0, allocation_db=1.0):
    return logic.assess_plastic_dielectric_losses(
        parts if parts is not None else [_radome(), _strut()],
        frequency_hz,
        input_power_w,
        allocation_db,
    )


class PartCategorization(unittest.TestCase):
    def test_a_radome_sits_in_the_field(self):
        self.assertTrue(logic.categorize_plastic_part("radome")["in_rf_path"])

    def test_a_lens_sits_in_the_field(self):
        self.assertTrue(logic.categorize_plastic_part("lens")["in_rf_path"])

    def test_a_waveguide_window_sits_in_the_field(self):
        self.assertTrue(logic.categorize_plastic_part("waveguide-window")["in_rf_path"])

    def test_a_matching_layer_sits_in_the_field(self):
        self.assertTrue(logic.categorize_plastic_part("matching-layer")["in_rf_path"])

    def test_a_structural_bracket_sits_outside_the_field(self):
        self.assertFalse(
            logic.categorize_plastic_part("structural-bracket-outside-field")["in_rf_path"]
        )

    def test_a_harness_standoff_sits_outside_the_field(self):
        self.assertFalse(
            logic.categorize_plastic_part("harness-standoff-outside-field")["in_rf_path"]
        )

    def test_case_and_whitespace_are_normalised(self):
        self.assertEqual(
            logic.categorize_plastic_part("  Radome ")["part_type"], "radome"
        )

    def test_an_uncategorized_part_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_plastic_part("moulded-widget")

    def test_an_empty_part_type_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_plastic_part("   ")

    def test_a_non_string_part_type_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_plastic_part(42)


class AttenuationConstant(unittest.TestCase):
    def test_a_known_material_matches_the_low_loss_form(self):
        self.assertAlmostEqual(
            logic.attenuation_np_per_m(12.0e9, 2.6, 0.0005), 0.10138346, places=7
        )

    def test_doubling_the_frequency_doubles_the_attenuation(self):
        low = logic.attenuation_np_per_m(12.0e9, 2.6, 0.0005)
        high = logic.attenuation_np_per_m(24.0e9, 2.6, 0.0005)
        self.assertAlmostEqual(high / low, 2.0, places=9)

    def test_doubling_the_loss_tangent_doubles_the_attenuation(self):
        low = logic.attenuation_np_per_m(12.0e9, 2.6, 0.0005)
        high = logic.attenuation_np_per_m(12.0e9, 2.6, 0.001)
        self.assertAlmostEqual(high / low, 2.0, places=9)

    def test_a_lossless_material_does_not_attenuate(self):
        self.assertAlmostEqual(
            logic.attenuation_np_per_m(12.0e9, 2.6, 0.0), 0.0, places=12
        )

    def test_zero_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.attenuation_np_per_m(0.0, 2.6, 0.0005)

    def test_permittivity_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.attenuation_np_per_m(12.0e9, 0.4, 0.0005)

    def test_a_negative_loss_tangent_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.attenuation_np_per_m(12.0e9, 2.6, -0.0005)

    def test_a_loss_tangent_at_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.attenuation_np_per_m(12.0e9, 2.6, 1.0)


class RefractedPath(unittest.TestCase):
    def test_normal_incidence_travels_the_thickness(self):
        self.assertAlmostEqual(
            logic.refracted_path_length_m(0.003, 2.6, 0.0), 0.003, places=12
        )

    def test_oblique_incidence_travels_further(self):
        self.assertGreater(
            logic.refracted_path_length_m(0.003, 2.6, 60.0),
            logic.refracted_path_length_m(0.003, 2.6, 0.0),
        )

    def test_a_denser_slab_bends_the_ray_closer_to_the_normal(self):
        dense = logic.refracted_path_length_m(0.003, 9.0, 60.0)
        light = logic.refracted_path_length_m(0.003, 2.0, 60.0)
        self.assertLess(dense, light)

    def test_zero_thickness_travels_nothing(self):
        self.assertAlmostEqual(
            logic.refracted_path_length_m(0.0, 2.6, 45.0), 0.0, places=12
        )

    def test_grazing_incidence_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.refracted_path_length_m(0.003, 2.6, 90.0)

    def test_a_negative_incidence_angle_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.refracted_path_length_m(0.003, 2.6, -5.0)

    def test_a_negative_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.refracted_path_length_m(-0.003, 2.6, 0.0)


class AbsorptionAndMismatch(unittest.TestCase):
    def test_a_known_radome_absorbs_the_expected_decibels(self):
        self.assertAlmostEqual(
            logic.absorption_loss_db(0.003, 2.6, 0.0005, 12.0e9), 0.002642, places=6
        )

    def test_zero_thickness_absorbs_nothing(self):
        self.assertAlmostEqual(
            logic.absorption_loss_db(0.0, 2.6, 0.0005, 12.0e9), 0.0, places=12
        )

    def test_a_lossless_part_absorbs_nothing(self):
        self.assertAlmostEqual(
            logic.absorption_loss_db(0.003, 2.6, 0.0, 12.0e9), 0.0, places=12
        )

    def test_doubling_the_thickness_doubles_the_absorption(self):
        thin = logic.absorption_loss_db(0.003, 2.6, 0.0005, 12.0e9)
        thick = logic.absorption_loss_db(0.006, 2.6, 0.0005, 12.0e9)
        self.assertAlmostEqual(thick / thin, 2.0, places=9)

    def test_oblique_incidence_absorbs_more(self):
        self.assertGreater(
            logic.absorption_loss_db(0.003, 2.6, 0.0005, 12.0e9, 60.0),
            logic.absorption_loss_db(0.003, 2.6, 0.0005, 12.0e9, 0.0),
        )

    def test_air_reflects_nothing_at_its_interfaces(self):
        self.assertAlmostEqual(logic.interface_mismatch_loss_db(1.0), 0.0, places=12)

    def test_a_known_slab_reflects_the_expected_decibels(self):
        self.assertAlmostEqual(logic.interface_mismatch_loss_db(2.6), 0.491, places=3)

    def test_a_denser_slab_reflects_more(self):
        self.assertGreater(
            logic.interface_mismatch_loss_db(9.0), logic.interface_mismatch_loss_db(2.6)
        )

    def test_a_permittivity_below_unity_is_rejected_by_the_mismatch_term(self):
        with self.assertRaises(ValueError):
            logic.interface_mismatch_loss_db(0.5)


class HeatAndTemperature(unittest.TestCase):
    def test_a_lossless_part_dissipates_nothing(self):
        self.assertAlmostEqual(logic.dissipated_power_w(100.0, 0.0), 0.0, places=12)

    def test_three_decibels_dissipates_half(self):
        self.assertAlmostEqual(
            logic.dissipated_power_w(100.0, 3.0103), 50.0, places=3
        )

    def test_a_negative_absorption_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.dissipated_power_w(100.0, -1.0)

    def test_zero_input_power_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.dissipated_power_w(0.0, 1.0)

    def test_the_rise_is_the_product_of_heat_and_resistance(self):
        self.assertAlmostEqual(logic.temperature_rise_k(0.5, 20.0), 10.0, places=12)

    def test_a_perfectly_sunk_part_does_not_rise(self):
        self.assertAlmostEqual(logic.temperature_rise_k(0.5, 0.0), 0.0, places=12)

    def test_a_negative_thermal_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.temperature_rise_k(0.5, -1.0)

    def test_a_negative_dissipation_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.temperature_rise_k(-0.5, 20.0)


class WholeAssessment(unittest.TestCase):
    def test_a_thin_low_loss_radome_is_compliant(self):
        result = _run()
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_a_part_outside_the_field_costs_nothing(self):
        with_strut = _run([_radome(), _strut()])
        without_strut = _run([_radome()])
        self.assertAlmostEqual(
            with_strut["total_loss_db"], without_strut["total_loss_db"], places=12
        )

    def test_the_chain_total_is_the_sum_of_the_in_path_parts(self):
        result = _run([_radome(), _radome(label="second-radome")])
        in_path = [p for p in result["parts"] if p["in_rf_path"]]
        self.assertAlmostEqual(
            result["total_loss_db"],
            sum(p["part_loss_db"] for p in in_path),
            places=12,
        )

    def test_power_falls_along_the_chain(self):
        result = _run([_radome(), _radome(label="second-radome")])
        in_path = [p for p in result["parts"] if p["in_rf_path"]]
        self.assertLess(in_path[1]["power_leaving_w"], in_path[0]["power_leaving_w"])

    def test_a_matched_part_carries_no_interface_mismatch(self):
        result = _run([_radome(part_type="matching-layer", impedance_matched=True)])
        self.assertAlmostEqual(result["parts"][0]["mismatch_loss_db"], 0.0, places=12)

    def test_a_matched_part_still_absorbs(self):
        result = _run([_radome(part_type="matching-layer", impedance_matched=True)])
        self.assertGreater(result["parts"][0]["absorption_loss_db"], 0.0)

    def test_a_lossy_thick_part_overheats(self):
        result = _run(
            [
                _radome(
                    thickness_m=0.010,
                    loss_tangent=0.02,
                    thermal_resistance_k_per_w=10.0,
                    maximum_use_temperature_k=420.0,
                )
            ],
            frequency_hz=30.0e9,
            input_power_w=200.0,
            allocation_db=5.0,
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("maximum-use-temperature" in f for f in result["findings"])
        )

    def test_an_exceeded_allocation_is_a_finding(self):
        result = _run(allocation_db=0.1)
        self.assertFalse(result["within_allocation"])
        self.assertTrue(any("against an allocation" in f for f in result["findings"]))

    def test_an_allocation_equal_to_the_chain_total_passes(self):
        baseline = _run()
        tight = _run(allocation_db=baseline["total_loss_db"])
        self.assertTrue(tight["within_allocation"])

    def test_an_allocation_a_hair_under_the_chain_total_still_passes(self):
        baseline = _run()
        tight = _run(allocation_db=baseline["total_loss_db"] - 1e-12)
        self.assertTrue(tight["within_allocation"])

    def test_an_allocation_five_hundredths_under_the_chain_total_fails(self):
        baseline = _run()
        tight = _run(allocation_db=baseline["total_loss_db"] - 0.05)
        self.assertFalse(tight["within_allocation"])

    def test_a_limit_equal_to_the_reached_temperature_passes(self):
        baseline = _run([_radome()])
        reached = baseline["parts"][0]["temperature_k"]
        tight = _run([_radome(maximum_use_temperature_k=reached)])
        self.assertTrue(tight["parts"][0]["thermally_compliant"])

    def test_a_limit_a_hair_under_the_reached_temperature_still_passes(self):
        baseline = _run([_radome()])
        reached = baseline["parts"][0]["temperature_k"]
        tight = _run([_radome(maximum_use_temperature_k=reached - 1e-12)])
        self.assertTrue(tight["parts"][0]["thermally_compliant"])

    def test_a_limit_half_a_kelvin_under_the_reached_temperature_fails(self):
        baseline = _run([_radome()])
        reached = baseline["parts"][0]["temperature_k"]
        tight = _run([_radome(maximum_use_temperature_k=reached - 0.5)])
        self.assertFalse(tight["parts"][0]["thermally_compliant"])

    def test_an_empty_chain_is_rejected(self):
        with self.assertRaises(ValueError):
            _run([])

    def test_a_part_without_a_label_is_rejected(self):
        part = _radome()
        del part["label"]
        with self.assertRaises(ValueError):
            _run([part])

    def test_a_part_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            _run(["radome"])

    def test_an_in_path_part_without_a_thickness_is_rejected(self):
        part = _radome()
        del part["thickness_m"]
        with self.assertRaises(ValueError):
            _run([part])

    def test_an_in_path_part_without_a_temperature_limit_is_rejected(self):
        part = _radome()
        del part["maximum_use_temperature_k"]
        with self.assertRaises(ValueError):
            _run([part])

    def test_a_non_boolean_matched_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            _run([_radome(impedance_matched="yes")])

    def test_a_zero_input_power_chain_is_rejected(self):
        with self.assertRaises(ValueError):
            _run(input_power_w=0.0)

    def test_a_non_positive_allocation_is_rejected(self):
        with self.assertRaises(ValueError):
            _run(allocation_db=0.0)

    def test_a_zero_frequency_chain_is_rejected(self):
        with self.assertRaises(ValueError):
            _run(frequency_hz=0.0)

    def test_a_non_positive_baseline_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_plastic_dielectric_losses(
                [_radome()], 12.0e9, 100.0, 1.0, baseline_temperature_k=0.0
            )


if __name__ == "__main__":
    unittest.main()
