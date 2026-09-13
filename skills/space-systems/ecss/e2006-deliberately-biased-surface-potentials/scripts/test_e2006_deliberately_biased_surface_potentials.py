#!/usr/bin/env python3
"""Gate 3 contract test for the clause 6.5 biased-surface disturbance."""

import math
import unittest

import e2006_deliberately_biased_surface_potentials_logic as logic


LEO = {
    "electron_temperature_ev": 0.2,
    "ion_temperature_ev": 0.1,
    "electron_density_m3": 1.0e11,
    "electron_current_density_a_m2": 1.0e-3,
    "ion_current_density_a_m2": 2.0e-5,
}


def array_end(**kw):
    row = {
        "id": "array-pos",
        "function": "solar-array-string-end",
        "bias_v": 120.0,
        "exposed_area_m2": 0.02,
    }
    row.update(kw)
    return row


def probe(**kw):
    row = {
        "id": "probe-1",
        "function": "biased-plasma-probe",
        "bias_v": -20.0,
        "exposed_area_m2": 0.001,
    }
    row.update(kw)
    return row


def manual_row(**kw):
    row = {
        "id": "row-1",
        "function": "solar-array-string-end",
        "bias_v": 10.0,
        "potential_v": 10.0,
        "exposed_area_m2": 0.01,
        "current_a": 0.0,
        "sheath_extent_m": 0.1,
        "clearance_m": None,
        "clearance_margin_m": None,
        "positive_limit_v": 100.0,
        "negative_limit_v": -150.0,
    }
    row.update(kw)
    return row


class ElementValidationTests(unittest.TestCase):
    def test_happy_element_keeps_its_bias(self):
        row = logic.normalize_biased_element(array_end())
        self.assertAlmostEqual(row["bias_v"], 120.0)
        self.assertAlmostEqual(row["exposed_area_m2"], 0.02)

    def test_function_thresholds_are_filled_in(self):
        row = logic.normalize_biased_element(array_end())
        self.assertAlmostEqual(row["positive_limit_v"], 100.0)
        self.assertAlmostEqual(row["negative_limit_v"], -150.0)

    def test_insulated_element_has_no_exposed_area(self):
        row = logic.normalize_biased_element(array_end(insulated=True))
        self.assertAlmostEqual(row["exposed_area_m2"], 0.0)
        self.assertAlmostEqual(row["declared_area_m2"], 0.02)

    def test_custom_thresholds_are_kept(self):
        row = logic.normalize_biased_element(
            array_end(positive_limit_v=55.0, negative_limit_v=-70.0)
        )
        self.assertAlmostEqual(row["positive_limit_v"], 55.0)
        self.assertAlmostEqual(row["negative_limit_v"], -70.0)

    def test_zero_exposed_area_is_allowed(self):
        row = logic.normalize_biased_element(array_end(exposed_area_m2=0.0))
        self.assertAlmostEqual(row["exposed_area_m2"], 0.0)

    def test_non_mapping_element_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_biased_element(("array-pos", 120.0))

    def test_blank_id_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_biased_element(array_end(id=""))

    def test_unknown_function_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_biased_element(array_end(function="payload-radiator"))

    def test_zero_bias_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_biased_element(array_end(bias_v=0.0))

    def test_non_finite_bias_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_biased_element(array_end(bias_v=float("nan")))

    def test_non_boolean_insulation_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_biased_element(array_end(insulated="no"))

    def test_negative_area_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_biased_element(array_end(exposed_area_m2=-0.01))

    def test_zero_clearance_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_biased_element(array_end(clearance_m=0.0))

    def test_positive_negative_limit_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_biased_element(array_end(negative_limit_v=10.0))

    def test_zero_positive_limit_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_biased_element(array_end(positive_limit_v=0.0))


class BiasSetTests(unittest.TestCase):
    def test_set_length(self):
        self.assertEqual(len(logic.build_bias_set([array_end(), probe()])), 2)

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            logic.build_bias_set([])

    def test_non_list_set_rejected(self):
        with self.assertRaises(ValueError):
            logic.build_bias_set(array_end())

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            logic.build_bias_set([array_end(), array_end()])


class EnvironmentTests(unittest.TestCase):
    def test_environment_round_trips(self):
        env = logic.normalize_environment(LEO)
        self.assertAlmostEqual(env["electron_temperature_ev"], 0.2)

    def test_non_mapping_environment_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_environment("leo")

    def test_missing_temperature_rejected(self):
        env = dict(LEO)
        del env["electron_temperature_ev"]
        with self.assertRaises(ValueError):
            logic.normalize_environment(env)

    def test_zero_density_rejected(self):
        env = dict(LEO, electron_density_m3=0.0)
        with self.assertRaises(ValueError):
            logic.normalize_environment(env)

    def test_zero_ion_temperature_rejected(self):
        env = dict(LEO, ion_temperature_ev=0.0)
        with self.assertRaises(ValueError):
            logic.normalize_environment(env)

    def test_negative_electron_current_rejected(self):
        env = dict(LEO, electron_current_density_a_m2=-1.0e-3)
        with self.assertRaises(ValueError):
            logic.normalize_environment(env)


class DebyeTests(unittest.TestCase):
    def test_textbook_value(self):
        env = dict(LEO, electron_temperature_ev=1.0, electron_density_m3=1.0e12)
        self.assertAlmostEqual(logic.debye_length_m(env), 7.434e-3, places=6)

    def test_hotter_plasma_has_a_longer_debye_length(self):
        cold = logic.debye_length_m(dict(LEO, electron_temperature_ev=0.1))
        hot = logic.debye_length_m(dict(LEO, electron_temperature_ev=1.0))
        self.assertGreater(hot, cold)

    def test_denser_plasma_has_a_shorter_debye_length(self):
        thin = logic.debye_length_m(dict(LEO, electron_density_m3=1.0e10))
        dense = logic.debye_length_m(dict(LEO, electron_density_m3=1.0e12))
        self.assertLess(dense, thin)


class CollectedCurrentTests(unittest.TestCase):
    def test_zero_area_collects_nothing(self):
        self.assertAlmostEqual(logic.collected_current_a(0.0, 50.0, LEO), 0.0)

    def test_branches_agree_at_zero_potential(self):
        value = logic.collected_current_a(2.0, 0.0, LEO)
        expected = 2.0 * (
            LEO["electron_current_density_a_m2"] - LEO["ion_current_density_a_m2"]
        )
        self.assertAlmostEqual(value, expected)

    def test_positive_surface_collects_more_electrons(self):
        self.assertGreater(
            logic.collected_current_a(1.0, 20.0, LEO),
            logic.collected_current_a(1.0, 0.0, LEO),
        )

    def test_negative_surface_collects_ions(self):
        self.assertLess(logic.collected_current_a(1.0, -20.0, LEO), 0.0)

    def test_deep_negative_current_follows_the_ion_branch(self):
        value = logic.collected_current_a(1.0, -100.0, LEO)
        expected = -LEO["ion_current_density_a_m2"] * (
            1.0 + 100.0 / LEO["ion_temperature_ev"]
        )
        self.assertAlmostEqual(value, expected, places=9)

    def test_electron_branch_grows_linearly(self):
        value = logic.collected_current_a(1.0, 2.0, LEO)
        expected = LEO["electron_current_density_a_m2"] * (
            1.0 + 2.0 / LEO["electron_temperature_ev"]
        ) - LEO["ion_current_density_a_m2"] * math.exp(
            -2.0 / LEO["ion_temperature_ev"]
        )
        self.assertAlmostEqual(value, expected)

    def test_negative_area_rejected(self):
        with self.assertRaises(ValueError):
            logic.collected_current_a(-1.0, 0.0, LEO)

    def test_non_finite_potential_rejected(self):
        with self.assertRaises(ValueError):
            logic.collected_current_a(1.0, float("inf"), LEO)


class FrameSolutionTests(unittest.TestCase):
    def test_balance_vanishes_at_the_solution(self):
        bias_set = logic.build_bias_set([array_end()])
        frame = logic.solve_frame_potential(bias_set, 8.0, LEO)
        residual = logic.net_vehicle_current_a(bias_set, 8.0, frame, LEO)
        self.assertAlmostEqual(residual, 0.0, places=7)

    def test_positive_bias_drives_the_frame_negative(self):
        bias_set = logic.build_bias_set([array_end()])
        self.assertLess(logic.solve_frame_potential(bias_set, 8.0, LEO), 0.0)

    def test_more_exposed_bias_area_drives_the_frame_further(self):
        small = logic.solve_frame_potential(
            logic.build_bias_set([array_end(exposed_area_m2=0.02)]), 8.0, LEO
        )
        large = logic.solve_frame_potential(
            logic.build_bias_set([array_end(exposed_area_m2=0.60)]), 8.0, LEO
        )
        self.assertLess(large, small)

    def test_insulating_the_element_removes_the_shift(self):
        exposed = logic.solve_frame_potential(
            logic.build_bias_set([array_end()]), 8.0, LEO
        )
        insulated = logic.solve_frame_potential(
            logic.build_bias_set([array_end(insulated=True)]), 8.0, LEO
        )
        self.assertLess(exposed, insulated)

    def test_no_exposed_area_anywhere_rejected(self):
        bias_set = logic.build_bias_set([array_end(insulated=True)])
        with self.assertRaises(ValueError):
            logic.solve_frame_potential(bias_set, 0.0, LEO)

    def test_balance_without_a_sign_change_rejected(self):
        env = dict(LEO, ion_current_density_a_m2=0.0)
        bias_set = logic.build_bias_set([array_end()])
        with self.assertRaises(ValueError):
            logic.solve_frame_potential(bias_set, 8.0, env)

    def test_vehicle_current_sums_structure_and_elements(self):
        bias_set = logic.build_bias_set([array_end()])
        total = logic.net_vehicle_current_a(bias_set, 4.0, -3.0, LEO)
        expected = logic.collected_current_a(4.0, -3.0, LEO) + logic.collected_current_a(
            0.02, 117.0, LEO
        )
        self.assertAlmostEqual(total, expected)

    def test_insulated_element_drops_out_of_the_sum(self):
        bias_set = logic.build_bias_set([array_end(insulated=True)])
        total = logic.net_vehicle_current_a(bias_set, 4.0, -3.0, LEO)
        self.assertAlmostEqual(total, logic.collected_current_a(4.0, -3.0, LEO))


class SheathTests(unittest.TestCase):
    def test_zero_potential_has_no_sheath(self):
        self.assertAlmostEqual(logic.sheath_extent_m(0.0, LEO), 0.0)

    def test_sheath_grows_with_potential(self):
        self.assertGreater(
            logic.sheath_extent_m(200.0, LEO), logic.sheath_extent_m(20.0, LEO)
        )

    def test_sheath_is_symmetric_in_sign(self):
        self.assertAlmostEqual(
            logic.sheath_extent_m(-80.0, LEO), logic.sheath_extent_m(80.0, LEO)
        )

    def test_sheath_follows_the_three_quarter_power(self):
        single = logic.sheath_extent_m(50.0, LEO)
        double = logic.sheath_extent_m(100.0, LEO)
        self.assertAlmostEqual(double / single, 2.0 ** 0.75, places=9)

    def test_sheath_scales_with_the_debye_length(self):
        thin = dict(LEO, electron_density_m3=1.0e10)
        self.assertGreater(
            logic.sheath_extent_m(50.0, thin), logic.sheath_extent_m(50.0, LEO)
        )

    def test_non_finite_potential_rejected(self):
        with self.assertRaises(ValueError):
            logic.sheath_extent_m(float("nan"), LEO)


class ElementRowTests(unittest.TestCase):
    def test_potential_is_frame_plus_bias(self):
        rows = logic.element_rows(logic.build_bias_set([array_end()]), -30.0, LEO)
        self.assertAlmostEqual(rows[0]["potential_v"], 90.0)

    def test_clearance_margin_is_none_without_a_clearance(self):
        rows = logic.element_rows(logic.build_bias_set([array_end()]), -30.0, LEO)
        self.assertIsNone(rows[0]["clearance_margin_m"])

    def test_clearance_margin_is_clearance_minus_sheath(self):
        rows = logic.element_rows(
            logic.build_bias_set([array_end(clearance_m=2.0)]), -30.0, LEO
        )
        self.assertAlmostEqual(
            rows[0]["clearance_margin_m"], 2.0 - rows[0]["sheath_extent_m"]
        )

    def test_row_current_matches_the_element_area(self):
        rows = logic.element_rows(logic.build_bias_set([probe()]), -5.0, LEO)
        self.assertAlmostEqual(
            rows[0]["current_a"], logic.collected_current_a(0.001, -25.0, LEO)
        )


class AssessmentTests(unittest.TestCase):
    def test_snapover_exceedance_is_a_finding(self):
        findings = logic.assess_bias_disturbance([manual_row(potential_v=140.0)], -5.0)
        self.assertEqual(findings[0]["kind"], "snapover-onset-exceedance")

    def test_arc_inception_exceedance_is_a_finding(self):
        findings = logic.assess_bias_disturbance([manual_row(potential_v=-400.0)], -5.0)
        self.assertEqual(findings[0]["kind"], "arc-inception-exceedance")

    def test_potential_exactly_at_the_positive_limit_passes(self):
        row = manual_row(potential_v=(0.1 + 0.2), positive_limit_v=0.3)
        self.assertEqual(logic.assess_bias_disturbance([row], -5.0), [])

    def test_potential_exactly_at_the_negative_limit_passes(self):
        row = manual_row(potential_v=-(0.1 + 0.2), negative_limit_v=-0.3)
        self.assertEqual(logic.assess_bias_disturbance([row], -5.0), [])

    def test_sheath_reaching_a_sensitive_item_is_a_finding(self):
        row = manual_row(sheath_extent_m=1.4, clearance_m=0.9)
        findings = logic.assess_bias_disturbance([row], -5.0)
        self.assertEqual(findings[0]["kind"], "sheath-reaches-sensitive-item")

    def test_sheath_exactly_at_the_clearance_passes(self):
        row = manual_row(sheath_extent_m=(0.1 + 0.2), clearance_m=0.3)
        self.assertEqual(logic.assess_bias_disturbance([row], -5.0), [])

    def test_frame_below_the_sputtering_limit_is_a_finding(self):
        findings = logic.assess_bias_disturbance([manual_row()], -260.0)
        self.assertEqual(findings[0]["kind"], "frame-potential-sputtering-exceedance")

    def test_frame_exactly_at_the_sputtering_limit_passes(self):
        findings = logic.assess_bias_disturbance(
            [manual_row()], -(0.1 + 0.2), {"frame_sputtering_limit_v": -0.3}
        )
        self.assertEqual(findings, [])

    def test_insulated_row_is_not_assessed(self):
        row = manual_row(potential_v=900.0, exposed_area_m2=0.0)
        self.assertEqual(logic.assess_bias_disturbance([row], -5.0), [])

    def test_non_negative_sputtering_limit_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_bias_disturbance(
                [manual_row()], -5.0, {"frame_sputtering_limit_v": 0.0}
            )

    def test_custom_sputtering_limit_is_used(self):
        findings = logic.assess_bias_disturbance(
            [manual_row()], -20.0, {"frame_sputtering_limit_v": -10.0}
        )
        self.assertEqual(len(findings), 1)


class ReportTests(unittest.TestCase):
    def test_small_exposed_bias_is_compliant(self):
        report = logic.analyze_biased_surface_potentials(
            [array_end(exposed_area_m2=0.002, bias_v=30.0)], 8.0, LEO
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(report["element_count"], 1)

    def test_large_exposed_bias_drives_a_finding(self):
        report = logic.analyze_biased_surface_potentials(
            [array_end(exposed_area_m2=0.60)], 2.0, LEO
        )
        self.assertFalse(report["compliant"])
        self.assertIn(
            "frame-potential-sputtering-exceedance", logic.summarize_findings(report)
        )

    def test_frame_shift_is_negative_for_a_positive_bias(self):
        report = logic.analyze_biased_surface_potentials([array_end()], 8.0, LEO)
        self.assertLess(report["frame_shift_v"], 0.0)

    def test_insulated_element_produces_no_shift(self):
        report = logic.analyze_biased_surface_potentials(
            [array_end(insulated=True)], 8.0, LEO
        )
        self.assertAlmostEqual(report["frame_shift_v"], 0.0, places=5)

    def test_report_without_structure_area_has_no_reference(self):
        report = logic.analyze_biased_surface_potentials([array_end()], 0.0, LEO)
        self.assertIsNone(report["unbiased_frame_potential_v"])
        self.assertIsNone(report["frame_shift_v"])

    def test_report_carries_the_debye_length(self):
        report = logic.analyze_biased_surface_potentials([array_end()], 8.0, LEO)
        self.assertAlmostEqual(report["debye_length_m"], logic.debye_length_m(LEO))

    def test_report_is_deterministic(self):
        first = logic.analyze_biased_surface_potentials([array_end()], 8.0, LEO)
        second = logic.analyze_biased_surface_potentials([array_end()], 8.0, LEO)
        self.assertAlmostEqual(
            first["frame_potential_v"], second["frame_potential_v"]
        )
        self.assertEqual(len(first["findings"]), len(second["findings"]))

    def test_every_biased_function_can_be_analysed(self):
        for name in sorted(logic.BIASED_FUNCTIONS):
            report = logic.analyze_biased_surface_potentials(
                [array_end(function=name, exposed_area_m2=0.005)], 8.0, LEO
            )
            self.assertTrue(math.isfinite(report["frame_potential_v"]))

    def test_summary_counts_every_finding(self):
        report = logic.analyze_biased_surface_potentials(
            [array_end(exposed_area_m2=0.60, clearance_m=0.05)], 2.0, LEO
        )
        counts = logic.summarize_findings(report)
        self.assertEqual(sum(counts.values()), len(report["findings"]))

    def test_summary_rejects_a_foreign_mapping(self):
        with self.assertRaises(ValueError):
            logic.summarize_findings({"elements": []})

    def test_two_elements_share_one_frame(self):
        report = logic.analyze_biased_surface_potentials(
            [array_end(), probe()], 8.0, LEO
        )
        self.assertEqual(report["element_count"], 2)
        for row in report["elements"]:
            self.assertAlmostEqual(
                row["potential_v"] - row["bias_v"], report["frame_potential_v"]
            )


if __name__ == "__main__":
    unittest.main()
