#!/usr/bin/env python3
"""Gate 3 contract test for e2007-launch-pad-lightning-risk.

Stdlib unittest, offline, deterministic.
"""

import unittest

import e2007_launch_pad_lightning_risk_logic as logic


def stroke_record(**overrides):
    rec = {"peak_current_ka": 200.0, "rise_time_us": 2.0, "distance_m": 100.0}
    rec.update(overrides)
    return rec


def pad_config(**overrides):
    cfg = {
        "protection_level": "level-iii",
        "vehicle_height_m": 10.0,
        "masts": [
            {"height_m": 40.0, "horizontal_offset_m": 10.0},
            {"height_m": 40.0, "horizontal_offset_m": 12.0},
        ],
        "stroke": stroke_record(),
        "victim": {"loop_area_m2": 0.5, "transient_withstand_v": 500.0},
        "umbilical": {
            "share_fraction": 0.05,
            "transfer_impedance_ohm_per_m": 1.0e-3,
            "length_m": 10.0,
            "transient_withstand_v": 500.0,
        },
        "assessed_components": [
            "direct-attachment",
            "nearby-strike",
            "umbilical-conducted",
        ],
    }
    cfg.update(overrides)
    return cfg


class TestThreatCategorization(unittest.TestCase):
    def test_canonical_kind_is_returned(self):
        self.assertEqual(
            logic.threat_component_kind("direct-attachment"), logic.THREAT_DIRECT
        )

    def test_direct_strike_alias_resolves(self):
        self.assertEqual(
            logic.threat_component_kind("Direct-Strike"), logic.THREAT_DIRECT
        )

    def test_nearby_strike_alias_resolves(self):
        self.assertEqual(
            logic.threat_component_kind("nearby-strike"), logic.THREAT_INDIRECT
        )

    def test_umbilical_alias_resolves(self):
        self.assertEqual(
            logic.threat_component_kind("umbilical-conducted"), logic.THREAT_UMBILICAL
        )

    def test_blank_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.threat_component_kind("   ")

    def test_unknown_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.threat_component_kind("static-discharge")

    def test_no_component_is_uncovered_when_all_three_are_declared(self):
        covered = ["direct-attachment", "nearby-strike", "umbilical-conducted"]
        self.assertEqual(logic.uncovered_threat_components(covered), ())

    def test_missing_umbilical_component_is_reported(self):
        covered = ["direct-attachment", "nearby-strike"]
        self.assertEqual(
            logic.uncovered_threat_components(covered), (logic.THREAT_UMBILICAL,)
        )

    def test_declared_components_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            logic.uncovered_threat_components("direct-attachment")


class TestRollingSphere(unittest.TestCase):
    def test_level_two_radius(self):
        self.assertAlmostEqual(logic.rolling_sphere_radius_m("level-ii"), 30.0, places=12)

    def test_level_four_radius(self):
        self.assertAlmostEqual(logic.rolling_sphere_radius_m("LEVEL-IV"), 60.0, places=12)

    def test_unknown_protection_level_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.rolling_sphere_radius_m("level-v")

    def test_short_mast_ground_level_reach(self):
        self.assertAlmostEqual(
            logic.protective_radius_m(40.0, 0.0, 45.0), 44.7213595500, places=8
        )

    def test_short_mast_reach_at_vehicle_height(self):
        self.assertAlmostEqual(
            logic.protective_radius_m(40.0, 10.0, 45.0), 16.4370883000, places=8
        )

    def test_reach_at_the_mast_tip_is_zero(self):
        self.assertAlmostEqual(
            logic.protective_radius_m(40.0, 40.0, 45.0), 0.0, places=9
        )

    def test_point_above_the_mast_tip_is_unprotected(self):
        self.assertAlmostEqual(
            logic.protective_radius_m(40.0, 55.0, 45.0), 0.0, places=12
        )

    def test_tall_mast_uses_the_flank_branch(self):
        self.assertAlmostEqual(
            logic.protective_radius_m(120.0, 20.0, 45.0), 7.5834261300, places=8
        )

    def test_tall_mast_protects_nothing_above_the_sphere_radius(self):
        self.assertAlmostEqual(
            logic.protective_radius_m(120.0, 45.0, 45.0), 0.0, places=12
        )
        self.assertAlmostEqual(
            logic.protective_radius_m(120.0, 50.0, 45.0), 0.0, places=12
        )

    def test_tall_mast_ground_reach_equals_the_sphere_radius(self):
        self.assertAlmostEqual(
            logic.protective_radius_m(120.0, 0.0, 45.0), 45.0, places=12
        )

    def test_negative_point_height_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.protective_radius_m(40.0, -1.0, 45.0)

    def test_non_positive_mast_height_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.protective_radius_m(0.0, 10.0, 45.0)

    def test_non_positive_sphere_radius_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.protective_radius_m(40.0, 10.0, 0.0)

    def test_non_numeric_geometry_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.protective_radius_m("forty", 10.0, 45.0)


class TestProtectedVolume(unittest.TestCase):
    def test_point_inside_the_cone_is_protected(self):
        self.assertTrue(logic.is_within_protected_volume(40.0, 10.0, 10.0, 45.0))

    def test_point_outside_the_cone_is_not_protected(self):
        self.assertFalse(logic.is_within_protected_volume(40.0, 10.0, 25.0, 45.0))

    def test_point_exactly_on_the_boundary_is_protected(self):
        reach = logic.protective_radius_m(40.0, 10.0, 45.0)
        self.assertTrue(logic.is_within_protected_volume(40.0, 10.0, reach, 45.0))

    def test_negative_offset_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.is_within_protected_volume(40.0, 10.0, -5.0, 45.0)

    def test_point_above_the_tip_is_never_protected(self):
        self.assertFalse(logic.is_within_protected_volume(40.0, 60.0, 0.5, 45.0))

    def test_one_covering_mast_is_enough(self):
        masts = [
            {"height_m": 40.0, "horizontal_offset_m": 40.0},
            {"height_m": 40.0, "horizontal_offset_m": 8.0},
        ]
        self.assertTrue(logic.vehicle_is_protected(masts, 10.0, 45.0))

    def test_no_covering_mast_leaves_the_vehicle_exposed(self):
        masts = [
            {"height_m": 40.0, "horizontal_offset_m": 40.0},
            {"height_m": 40.0, "horizontal_offset_m": 35.0},
        ]
        self.assertFalse(logic.vehicle_is_protected(masts, 10.0, 45.0))

    def test_pad_with_no_mast_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.vehicle_is_protected([], 10.0, 45.0)

    def test_mast_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.vehicle_is_protected([(40.0, 10.0)], 10.0, 45.0)


class TestStroke(unittest.TestCase):
    def test_stroke_happy_path(self):
        got = logic.normalize_stroke(stroke_record())
        self.assertAlmostEqual(got["peak_current_ka"], 200.0, places=12)

    def test_stroke_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.normalize_stroke([200.0, 2.0, 100.0])

    def test_non_positive_peak_current_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_stroke(stroke_record(peak_current_ka=0.0))

    def test_non_positive_rise_time_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_stroke(stroke_record(rise_time_us=-2.0))

    def test_non_positive_distance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_stroke(stroke_record(distance_m=0.0))

    def test_current_derivative_value(self):
        self.assertAlmostEqual(
            logic.current_derivative_a_per_s(200.0, 2.0) / 1.0e11, 1.0, places=12
        )

    def test_halving_the_rise_time_doubles_the_derivative(self):
        slow = logic.current_derivative_a_per_s(200.0, 2.0)
        fast = logic.current_derivative_a_per_s(200.0, 1.0)
        self.assertAlmostEqual(fast / slow, 2.0, places=12)

    def test_current_derivative_rejects_non_positive_peak(self):
        with self.assertRaises(ValueError):
            logic.current_derivative_a_per_s(-200.0, 2.0)

    def test_current_derivative_rejects_non_positive_rise_time(self):
        with self.assertRaises(ValueError):
            logic.current_derivative_a_per_s(200.0, 0.0)


class TestIndirectCoupling(unittest.TestCase):
    def test_induced_loop_voltage_value(self):
        self.assertAlmostEqual(
            logic.induced_loop_voltage_v(stroke_record(), 0.5), 100.0, places=6
        )

    def test_voltage_scales_with_loop_area(self):
        small = logic.induced_loop_voltage_v(stroke_record(), 0.5)
        large = logic.induced_loop_voltage_v(stroke_record(), 1.5)
        self.assertAlmostEqual(large / small, 3.0, places=9)

    def test_voltage_falls_with_distance(self):
        near = logic.induced_loop_voltage_v(stroke_record(distance_m=50.0), 0.5)
        far = logic.induced_loop_voltage_v(stroke_record(distance_m=200.0), 0.5)
        self.assertAlmostEqual(near / far, 4.0, places=9)

    def test_zero_loop_area_induces_nothing(self):
        self.assertAlmostEqual(
            logic.induced_loop_voltage_v(stroke_record(), 0.0), 0.0, places=12
        )

    def test_negative_loop_area_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.induced_loop_voltage_v(stroke_record(), -0.5)

    def test_induced_voltage_needs_a_stroke_mapping(self):
        with self.assertRaises(ValueError):
            logic.induced_loop_voltage_v("200 kA", 0.5)


class TestUmbilicalPath(unittest.TestCase):
    def test_umbilical_voltage_value(self):
        self.assertAlmostEqual(
            logic.umbilical_transient_voltage_v(200.0, 0.05, 1.0e-3, 10.0),
            100.0,
            places=9,
        )

    def test_zero_share_carries_no_transient(self):
        self.assertAlmostEqual(
            logic.umbilical_transient_voltage_v(200.0, 0.0, 1.0e-3, 10.0),
            0.0,
            places=12,
        )

    def test_share_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.umbilical_transient_voltage_v(200.0, 1.5, 1.0e-3, 10.0)

    def test_negative_share_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.umbilical_transient_voltage_v(200.0, -0.1, 1.0e-3, 10.0)

    def test_negative_transfer_impedance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.umbilical_transient_voltage_v(200.0, 0.05, -1.0e-3, 10.0)

    def test_non_positive_length_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.umbilical_transient_voltage_v(200.0, 0.05, 1.0e-3, 0.0)

    def test_non_positive_peak_current_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.umbilical_transient_voltage_v(0.0, 0.05, 1.0e-3, 10.0)


class TestWithstandComparison(unittest.TestCase):
    def test_stress_below_the_level_passes(self):
        self.assertTrue(logic.withstands(80.0, 100.0))

    def test_stress_exactly_at_the_level_passes(self):
        self.assertTrue(logic.withstands(100.0, 100.0))

    def test_physically_compliant_case_is_not_failed_by_representation_error(self):
        applied = logic.induced_loop_voltage_v(stroke_record(), 0.5)
        self.assertTrue(logic.withstands(applied, 100.0))

    def test_real_exceedance_is_not_absorbed(self):
        self.assertFalse(logic.withstands(140.0, 100.0))

    def test_non_positive_withstand_level_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.withstands(80.0, 0.0)

    def test_negative_applied_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.withstands(-80.0, 100.0)

    def test_negative_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.withstands(80.0, 100.0, tolerance=-1.0)

    def test_stress_ratio_value(self):
        self.assertAlmostEqual(logic.stress_ratio(50.0, 200.0), 0.25, places=12)

    def test_stress_ratio_rejects_zero_withstand(self):
        with self.assertRaises(ValueError):
            logic.stress_ratio(50.0, 0.0)

    def test_stress_ratio_rejects_negative_stress(self):
        with self.assertRaises(ValueError):
            logic.stress_ratio(-50.0, 200.0)


class TestRiskGrading(unittest.TestCase):
    def test_low_risk_corner(self):
        self.assertEqual(logic.risk_level("improbable", "negligible"), "low")

    def test_medium_risk_band(self):
        self.assertEqual(logic.risk_level("remote", "critical"), "medium")

    def test_high_risk_band(self):
        self.assertEqual(logic.risk_level("occasional", "catastrophic"), "high")

    def test_unacceptable_corner(self):
        self.assertEqual(logic.risk_level("frequent", "catastrophic"), "unacceptable")

    def test_unknown_likelihood_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.risk_level("likely", "critical")

    def test_unknown_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.risk_level("remote", "severe")

    def test_ratio_below_a_tenth_is_improbable(self):
        self.assertEqual(logic.likelihood_from_ratio(0.05), "improbable")

    def test_ratio_of_a_quarter_is_remote(self):
        self.assertEqual(logic.likelihood_from_ratio(0.25), "remote")

    def test_ratio_of_three_quarters_is_occasional(self):
        self.assertEqual(logic.likelihood_from_ratio(0.75), "occasional")

    def test_ratio_above_unity_is_probable(self):
        self.assertEqual(logic.likelihood_from_ratio(1.5), "probable")

    def test_double_the_withstand_is_frequent(self):
        self.assertEqual(logic.likelihood_from_ratio(2.0), "frequent")

    def test_negative_ratio_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.likelihood_from_ratio(-0.5)

    def test_worst_level_wins(self):
        self.assertEqual(logic.worst_risk_level(["low", "high", "medium"]), "high")

    def test_worst_level_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            logic.worst_risk_level([])

    def test_worst_level_rejects_an_unknown_level(self):
        with self.assertRaises(ValueError):
            logic.worst_risk_level(["low", "severe"])


class TestPadAssessment(unittest.TestCase):
    def test_protected_pad_with_margins_is_acceptable(self):
        report = logic.assess_pad_lightning_risk(pad_config())
        self.assertTrue(report["acceptable"])
        self.assertEqual(report["findings"], ())
        self.assertTrue(report["direct_attachment_protected"])
        self.assertAlmostEqual(report["induced_loop_voltage_v"], 100.0, places=6)
        self.assertAlmostEqual(report["umbilical_voltage_v"], 100.0, places=9)

    def test_exposed_vehicle_raises_a_finding_and_the_residual_risk(self):
        masts = [{"height_m": 40.0, "horizontal_offset_m": 40.0}]
        report = logic.assess_pad_lightning_risk(pad_config(masts=masts))
        self.assertFalse(report["acceptable"])
        self.assertIn("vehicle-outside-protected-volume", report["findings"])
        self.assertEqual(report["residual_risk"], "high")

    def test_loop_voltage_above_withstand_is_a_finding(self):
        victim = {"loop_area_m2": 0.5, "transient_withstand_v": 50.0}
        report = logic.assess_pad_lightning_risk(pad_config(victim=victim))
        self.assertIn("indirect-coupling-exceeds-withstand", report["findings"])
        self.assertEqual(
            report["component_risk"][logic.THREAT_INDIRECT], "unacceptable"
        )

    def test_umbilical_transient_above_withstand_is_a_finding(self):
        umbilical = {
            "share_fraction": 0.5,
            "transfer_impedance_ohm_per_m": 1.0e-3,
            "length_m": 10.0,
            "transient_withstand_v": 500.0,
        }
        report = logic.assess_pad_lightning_risk(pad_config(umbilical=umbilical))
        self.assertIn("umbilical-transient-exceeds-withstand", report["findings"])

    def test_uncovered_threat_component_is_a_finding(self):
        report = logic.assess_pad_lightning_risk(
            pad_config(assessed_components=["direct-attachment"])
        )
        self.assertFalse(report["acceptable"])
        self.assertIn(
            "threat-component-not-assessed:%s" % logic.THREAT_UMBILICAL,
            report["findings"],
        )

    def test_tall_mast_does_not_protect_a_tall_vehicle(self):
        masts = [{"height_m": 120.0, "horizontal_offset_m": 5.0}]
        report = logic.assess_pad_lightning_risk(
            pad_config(masts=masts, vehicle_height_m=50.0)
        )
        self.assertFalse(report["direct_attachment_protected"])

    def test_configuration_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.assess_pad_lightning_risk("pad-39a")

    def test_victim_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.assess_pad_lightning_risk(pad_config(victim=None))

    def test_umbilical_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.assess_pad_lightning_risk(pad_config(umbilical=[0.05, 1.0e-3, 10.0]))

    def test_non_positive_vehicle_height_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_pad_lightning_risk(pad_config(vehicle_height_m=0.0))

    def test_sphere_radius_follows_the_declared_protection_level(self):
        report = logic.assess_pad_lightning_risk(pad_config(protection_level="level-i"))
        self.assertAlmostEqual(report["sphere_radius_m"], 20.0, places=12)


if __name__ == "__main__":
    unittest.main()
