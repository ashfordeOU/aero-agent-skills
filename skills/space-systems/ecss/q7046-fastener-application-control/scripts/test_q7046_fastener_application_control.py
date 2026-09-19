#!/usr/bin/env python3
"""Contract test for fastener application control (offline)."""

import copy
import math
import unittest

from q7046_fastener_application_control_logic import (
    CONSEQUENCES,
    FAIL,
    LOCKING_FEATURES,
    PASS,
    PLASTIC_METHODS,
    TIGHTENING_METHODS,
    assess_preload_window,
    locking_requirement,
    plan_application,
    preload_band_n,
    proof_load_n,
    reuse_verdict,
    target_preload_n,
    tensile_stress_area,
    tightening_scatter,
    torque_for_preload_nm,
)

GOOD_CASE = {
    "diameter_mm": 10.0,
    "pitch_mm": 1.5,
    "proof_stress_mpa": 830.0,
    "utilisation": 0.65,
    "method": "torque-wrench",
    "separating_load_n": 15000.0,
    "consequence": "loss-of-function",
    "locking_feature": "positive-mechanical-locking",
    "nut_factor": 0.2,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class ThreadAreaTests(unittest.TestCase):
    def test_stress_area_matches_the_iso_metric_value(self):
        self.assertAlmostEqual(tensile_stress_area(10.0, 1.5), 57.99, places=1)

    def test_stress_area_grows_with_the_diameter(self):
        self.assertGreater(
            tensile_stress_area(12.0, 1.75), tensile_stress_area(10.0, 1.5)
        )

    def test_a_coarser_pitch_gives_a_smaller_area_at_one_diameter(self):
        self.assertLess(
            tensile_stress_area(10.0, 1.5), tensile_stress_area(10.0, 1.25)
        )

    def test_a_pitch_past_the_diameter_is_not_a_thread(self):
        with self.assertRaises(ValueError):
            tensile_stress_area(2.0, 2.0)

    def test_zero_diameter_rejected(self):
        with self.assertRaises(ValueError):
            tensile_stress_area(0.0, 1.5)


class ProofAndTargetTests(unittest.TestCase):
    def test_proof_load_is_area_times_stress(self):
        expected = tensile_stress_area(10.0, 1.5) * 830.0
        self.assertAlmostEqual(proof_load_n(10.0, 1.5, 830.0), expected, places=9)

    def test_target_preload_is_the_utilisation_of_the_proof_load(self):
        proof = proof_load_n(10.0, 1.5, 830.0)
        target = target_preload_n(10.0, 1.5, 830.0, 0.65)
        self.assertAlmostEqual(target, proof * 0.65, places=9)

    def test_a_full_utilisation_lands_exactly_on_the_proof_load(self):
        proof = proof_load_n(10.0, 1.5, 830.0)
        self.assertAlmostEqual(
            target_preload_n(10.0, 1.5, 830.0, 1.0), proof, places=9
        )

    def test_a_utilisation_past_the_proof_load_is_rejected(self):
        with self.assertRaises(ValueError):
            target_preload_n(10.0, 1.5, 830.0, 1.2)

    def test_zero_proof_stress_rejected(self):
        with self.assertRaises(ValueError):
            proof_load_n(10.0, 1.5, 0.0)


class ScatterAndTorqueTests(unittest.TestCase):
    def test_every_method_has_a_band_straddling_the_target(self):
        for method in TIGHTENING_METHODS:
            low, high = tightening_scatter(method)
            self.assertLess(low, 1.0)
            self.assertGreater(high, 1.0)

    def test_a_controlled_method_is_tighter_than_a_bare_wrench(self):
        hand_low, hand_high = tightening_scatter("hand-wrench-no-control")
        ultra_low, ultra_high = tightening_scatter("ultrasonic-preload")
        self.assertGreater(hand_high - hand_low, ultra_high - ultra_low)

    def test_the_band_scales_with_the_target(self):
        low, high = preload_band_n(10000.0, "torque-wrench")
        self.assertAlmostEqual(low, 7500.0, places=9)
        self.assertAlmostEqual(high, 12500.0, places=9)

    def test_torque_follows_the_nut_factor_diameter_and_preload(self):
        self.assertAlmostEqual(
            torque_for_preload_nm(20000.0, 10.0, 0.2), 40.0, places=9
        )

    def test_an_absurd_nut_factor_is_rejected(self):
        with self.assertRaises(ValueError):
            torque_for_preload_nm(20000.0, 10.0, 3.0)

    def test_unknown_tightening_method_rejected(self):
        with self.assertRaises(ValueError):
            tightening_scatter("felt-about-right")


class PreloadWindowTests(unittest.TestCase):
    def test_a_sound_window_passes_both_limits(self):
        result = assess_preload_window(GOOD_CASE)
        self.assertEqual(result["verdict"], PASS)
        self.assertTrue(result["holds_joint_closed"])
        self.assertTrue(result["stays_under_proof"])

    def test_a_high_utilisation_with_wide_scatter_passes_the_proof_load(self):
        result = assess_preload_window(
            _case(utilisation=0.95, method="hand-wrench-no-control")
        )
        self.assertFalse(result["stays_under_proof"])
        self.assertEqual(result["verdict"], FAIL)

    def test_a_low_band_below_the_separating_load_fails(self):
        result = assess_preload_window(_case(separating_load_n=40000.0))
        self.assertFalse(result["holds_joint_closed"])

    def test_a_band_low_end_exactly_on_the_separating_load_still_holds(self):
        target = target_preload_n(10.0, 1.5, 830.0, 0.65)
        low, _high = preload_band_n(target, "torque-wrench")
        result = assess_preload_window(_case(separating_load_n=low))
        self.assertTrue(result["holds_joint_closed"])

    def test_a_tighter_method_widens_the_usable_window(self):
        loose = assess_preload_window(
            _case(utilisation=0.85, method="hand-wrench-no-control")
        )
        tight = assess_preload_window(
            _case(utilisation=0.85, method="ultrasonic-preload")
        )
        self.assertLess(tight["preload_high_n"], loose["preload_high_n"])
        self.assertGreater(tight["preload_low_n"], loose["preload_low_n"])

    def test_a_negative_separating_load_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_preload_window(_case(separating_load_n=-1.0))

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_preload_window("tighten it firmly")

    def test_a_non_finite_input_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_preload_window(_case(proof_stress_mpa=float("inf")))


class LockingTests(unittest.TestCase):
    def test_a_mission_loss_needs_positive_locking(self):
        result = locking_requirement("loss-of-mission",
                                     "positive-mechanical-locking")
        self.assertTrue(result["positive_locking_required"])
        self.assertTrue(result["adequate"])

    def test_friction_locking_is_not_enough_for_a_mission_loss(self):
        result = locking_requirement("loss-of-mission",
                                     "friction-prevailing-torque")
        self.assertFalse(result["adequate"])
        self.assertIn("decays", result["reason"])

    def test_adhesive_locking_is_not_enough_for_a_function_loss(self):
        self.assertFalse(
            locking_requirement("loss-of-function",
                                "thread-locking-adhesive")["adequate"]
        )

    def test_no_locking_at_all_is_called_out_for_a_severe_consequence(self):
        result = locking_requirement("loss-of-function", "none")
        self.assertFalse(result["adequate"])
        self.assertIn("without a locking feature", result["reason"])

    def test_a_degraded_performance_joint_accepts_friction_locking(self):
        self.assertTrue(
            locking_requirement("degraded-performance",
                                "friction-prevailing-torque")["adequate"]
        )

    def test_every_consequence_and_feature_pair_is_decidable(self):
        for consequence in CONSEQUENCES:
            for feature in LOCKING_FEATURES:
                result = locking_requirement(consequence, feature)
                self.assertIn("adequate", result)

    def test_unknown_consequence_rejected(self):
        with self.assertRaises(ValueError):
            locking_requirement("mildly-annoying", "none")


class ReuseTests(unittest.TestCase):
    def test_a_yield_tightened_fastener_is_single_use(self):
        for method in PLASTIC_METHODS:
            result = reuse_verdict(
                {"method": method, "locking_feature": "none", "cycles_used": 1}
            )
            self.assertFalse(result["reusable"])
            self.assertTrue(any("single-use" in f for f in result["findings"]))

    def test_a_prevailing_torque_nut_above_its_minimum_may_be_reused(self):
        result = reuse_verdict(
            {
                "method": "torque-wrench",
                "locking_feature": "friction-prevailing-torque",
                "cycles_used": 2,
                "measured_prevailing_torque_nm": 1.4,
                "minimum_prevailing_torque_nm": 1.0,
            }
        )
        self.assertTrue(result["reusable"])

    def test_a_decayed_prevailing_torque_blocks_reuse(self):
        result = reuse_verdict(
            {
                "method": "torque-wrench",
                "locking_feature": "friction-prevailing-torque",
                "cycles_used": 5,
                "measured_prevailing_torque_nm": 0.4,
                "minimum_prevailing_torque_nm": 1.0,
            }
        )
        self.assertFalse(result["reusable"])

    def test_a_prevailing_torque_exactly_on_the_minimum_is_accepted(self):
        result = reuse_verdict(
            {
                "method": "torque-wrench",
                "locking_feature": "friction-prevailing-torque",
                "cycles_used": 3,
                "measured_prevailing_torque_nm": 1.0,
                "minimum_prevailing_torque_nm": 1.0,
            }
        )
        self.assertTrue(result["reusable"])

    def test_a_prevailing_torque_feature_without_measurements_is_refused(self):
        with self.assertRaises(ValueError):
            reuse_verdict(
                {
                    "method": "torque-wrench",
                    "locking_feature": "friction-prevailing-torque",
                    "cycles_used": 1,
                }
            )

    def test_adhesive_locking_does_not_carry_over(self):
        result = reuse_verdict(
            {
                "method": "torque-wrench",
                "locking_feature": "thread-locking-adhesive",
                "cycles_used": 1,
            }
        )
        self.assertFalse(result["reusable"])

    def test_negative_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            reuse_verdict(
                {"method": "torque-wrench", "locking_feature": "none",
                 "cycles_used": -2}
            )


class PlanApplicationTests(unittest.TestCase):
    def test_a_sound_installation_passes(self):
        result = plan_application(GOOD_CASE)
        self.assertEqual(result["verdict"], PASS)
        self.assertEqual(result["findings"], [])

    def test_the_target_torque_is_carried_into_the_plan(self):
        result = plan_application(GOOD_CASE)
        expected = torque_for_preload_nm(
            result["preload"]["target_preload_n"], 10.0, 0.2
        )
        self.assertAlmostEqual(result["target_torque_nm"], expected, places=9)

    def test_no_nut_factor_leaves_the_torque_unstated_rather_than_zero(self):
        case = _case()
        del case["nut_factor"]
        self.assertIsNone(plan_application(case)["target_torque_nm"])

    def test_inadequate_locking_fails_an_otherwise_sound_joint(self):
        result = plan_application(
            _case(locking_feature="friction-prevailing-torque")
        )
        self.assertEqual(result["verdict"], FAIL)

    def test_a_reinstallation_pulls_the_reuse_verdict_in(self):
        result = plan_application(
            _case(is_reinstallation=True, method="yield-controlled",
                  cycles_used=1)
        )
        self.assertIsNotNone(result["reuse"])
        self.assertEqual(result["verdict"], FAIL)

    def test_a_first_installation_has_no_reuse_verdict(self):
        self.assertIsNone(plan_application(GOOD_CASE)["reuse"])

    def test_every_torque_is_finite(self):
        for method in TIGHTENING_METHODS:
            result = plan_application(_case(method=method))
            self.assertTrue(math.isfinite(result["target_torque_nm"]))


if __name__ == "__main__":
    unittest.main()
