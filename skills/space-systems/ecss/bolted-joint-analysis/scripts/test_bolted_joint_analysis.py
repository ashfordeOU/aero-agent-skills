#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C clause 4.6.2.13 bolted-joint analysis.

Exercises scripts/bolted_joint_analysis_logic.py (stdlib unittest,
offline). Contract: joint type is categorized as metallic_fastener,
composite_bolted, or lug_joint and an unrecognized type raises; applied
load is distributed among fasteners proportionally to axial stiffness;
bearing stress is load divided by diameter times thickness; margin of
safety is (allowable / stress) - 1 and is negative for an overstressed
fastener; bypass ratio is the fraction of load that passes the fastener
and is zero when the fastener transfers the full load; the linear
bearing-bypass interaction sums both ratios and must not exceed 1.0;
preload is derived from torque via T/(K*D); a missing allowable bearing
stress is a finding; the joint is compliant only when no violations exist.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bolted_joint_analysis_logic as bj  # noqa: E402


class CategorizeJointTest(unittest.TestCase):
    def test_metallic_fastener_accepted(self):
        self.assertEqual(bj.categorize_joint("metallic_fastener"), "metallic_fastener")

    def test_composite_bolted_accepted(self):
        self.assertEqual(bj.categorize_joint("composite_bolted"), "composite_bolted")

    def test_lug_joint_accepted(self):
        self.assertEqual(bj.categorize_joint("lug_joint"), "lug_joint")

    def test_unknown_joint_type_raises(self):
        with self.assertRaises(ValueError):
            bj.categorize_joint("riveted_splice")


class DistributeFastenerLoadsTest(unittest.TestCase):
    def test_equal_stiffnesses_equal_loads(self):
        loads = bj.distribute_fastener_loads(9000.0, [1.0e6, 1.0e6, 1.0e6])
        self.assertEqual(len(loads), 3)
        for load in loads:
            self.assertAlmostEqual(load, 3000.0)

    def test_proportional_distribution_two_fasteners(self):
        # stiffness ratio 1:3 -> load ratio 1:3
        loads = bj.distribute_fastener_loads(8000.0, [1.0e6, 3.0e6])
        self.assertAlmostEqual(loads[0], 2000.0)
        self.assertAlmostEqual(loads[1], 6000.0)

    def test_single_fastener_takes_all_load(self):
        loads = bj.distribute_fastener_loads(5000.0, [2.0e6])
        self.assertAlmostEqual(loads[0], 5000.0)

    def test_zero_total_load_gives_zero_fastener_loads(self):
        loads = bj.distribute_fastener_loads(0.0, [1.0e6, 1.0e6])
        for load in loads:
            self.assertAlmostEqual(load, 0.0)

    def test_empty_stiffnesses_raises(self):
        with self.assertRaises(ValueError):
            bj.distribute_fastener_loads(5000.0, [])

    def test_negative_total_load_raises(self):
        with self.assertRaises(ValueError):
            bj.distribute_fastener_loads(-100.0, [1.0e6])

    def test_zero_stiffness_raises(self):
        with self.assertRaises(ValueError):
            bj.distribute_fastener_loads(5000.0, [1.0e6, 0.0])

    def test_negative_stiffness_raises(self):
        with self.assertRaises(ValueError):
            bj.distribute_fastener_loads(5000.0, [1.0e6, -1.0e6])


class BearingStressMPaTest(unittest.TestCase):
    def test_basic_bearing_stress(self):
        # 1000 N on 10 mm diameter, 5 mm thick: 1000/(10*5) = 20 MPa
        result = bj.bearing_stress_MPa(1000.0, 10.0, 5.0)
        self.assertAlmostEqual(result, 20.0)

    def test_bearing_stress_zero_load(self):
        result = bj.bearing_stress_MPa(0.0, 6.0, 3.0)
        self.assertAlmostEqual(result, 0.0)

    def test_zero_diameter_raises(self):
        with self.assertRaises(ValueError):
            bj.bearing_stress_MPa(1000.0, 0.0, 5.0)

    def test_zero_thickness_raises(self):
        with self.assertRaises(ValueError):
            bj.bearing_stress_MPa(1000.0, 6.0, 0.0)

    def test_negative_load_raises(self):
        with self.assertRaises(ValueError):
            bj.bearing_stress_MPa(-500.0, 6.0, 3.0)


class BearingMarginOfSafetyTest(unittest.TestCase):
    def test_positive_margin_when_allowable_exceeds_stress(self):
        ms = bj.bearing_margin_of_safety(200.0, 400.0)
        self.assertAlmostEqual(ms, 1.0)

    def test_zero_margin_at_allowable(self):
        ms = bj.bearing_margin_of_safety(300.0, 300.0)
        self.assertAlmostEqual(ms, 0.0)

    def test_negative_margin_when_overstressed(self):
        ms = bj.bearing_margin_of_safety(400.0, 300.0)
        self.assertAlmostEqual(ms, -0.25)

    def test_zero_bearing_stress_raises(self):
        with self.assertRaises(ValueError):
            bj.bearing_margin_of_safety(0.0, 300.0)

    def test_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            bj.bearing_margin_of_safety(200.0, 0.0)


class BypassRatioTest(unittest.TestCase):
    def test_full_load_transfer_gives_zero_bypass(self):
        self.assertAlmostEqual(bj.bypass_ratio(5000.0, 5000.0), 0.0)

    def test_zero_fastener_load_gives_full_bypass(self):
        self.assertAlmostEqual(bj.bypass_ratio(0.0, 5000.0), 1.0)

    def test_partial_transfer(self):
        # fastener carries 2000 N of 8000 N total -> bypass = 0.75
        self.assertAlmostEqual(bj.bypass_ratio(2000.0, 8000.0), 0.75)

    def test_zero_total_load_returns_zero(self):
        self.assertAlmostEqual(bj.bypass_ratio(0.0, 0.0), 0.0)

    def test_fastener_load_exceeds_total_raises(self):
        with self.assertRaises(ValueError):
            bj.bypass_ratio(6000.0, 5000.0)

    def test_negative_fastener_load_raises(self):
        with self.assertRaises(ValueError):
            bj.bypass_ratio(-100.0, 5000.0)


class BearingBypassInteractionTest(unittest.TestCase):
    def test_interaction_below_limit(self):
        result = bj.bearing_bypass_interaction(0.4, 0.5)
        self.assertAlmostEqual(result, 0.9)

    def test_interaction_at_limit(self):
        result = bj.bearing_bypass_interaction(0.5, 0.5)
        self.assertAlmostEqual(result, 1.0)

    def test_interaction_exceeds_limit(self):
        result = bj.bearing_bypass_interaction(0.6, 0.6)
        self.assertAlmostEqual(result, 1.2)

    def test_zero_both_ratios(self):
        result = bj.bearing_bypass_interaction(0.0, 0.0)
        self.assertAlmostEqual(result, 0.0)

    def test_negative_bearing_ratio_raises(self):
        with self.assertRaises(ValueError):
            bj.bearing_bypass_interaction(-0.1, 0.5)

    def test_negative_bypass_ratio_raises(self):
        with self.assertRaises(ValueError):
            bj.bearing_bypass_interaction(0.4, -0.1)


class PreloadFromTorqueTest(unittest.TestCase):
    def test_preload_basic(self):
        # T=10 N·m, K=0.2, D=10 mm=0.01 m -> F = 10/(0.2*0.01) = 5000 N
        result = bj.preload_from_torque_N(10.0, 0.2, 10.0)
        self.assertAlmostEqual(result, 5000.0)

    def test_smaller_diameter_gives_higher_preload(self):
        # T=5 N·m, K=0.2, D=5 mm -> F = 5/(0.2*0.005) = 5000 N
        result = bj.preload_from_torque_N(5.0, 0.2, 5.0)
        self.assertAlmostEqual(result, 5000.0)

    def test_zero_torque_raises(self):
        with self.assertRaises(ValueError):
            bj.preload_from_torque_N(0.0, 0.2, 6.0)

    def test_negative_torque_raises(self):
        with self.assertRaises(ValueError):
            bj.preload_from_torque_N(-5.0, 0.2, 6.0)

    def test_zero_nut_factor_raises(self):
        with self.assertRaises(ValueError):
            bj.preload_from_torque_N(10.0, 0.0, 6.0)

    def test_zero_diameter_raises(self):
        with self.assertRaises(ValueError):
            bj.preload_from_torque_N(10.0, 0.2, 0.0)


class AssessJointTest(unittest.TestCase):
    def _make_joint(self, joint_type, total_load_N, fasteners):
        return {
            "joint_type": joint_type,
            "total_load_N": total_load_N,
            "fasteners": fasteners,
        }

    def test_single_fastener_within_allowable_is_compliant(self):
        # 5000 N on 10 mm dia, 5 mm thick -> bearing = 100 MPa, allowable = 400 MPa
        joint = self._make_joint(
            "metallic_fastener", 5000.0,
            [{"id": "B1", "stiffness_N_per_m": 1.0e6,
              "diameter_mm": 10.0, "plate_thickness_mm": 5.0,
              "allowable_bearing_MPa": 400.0}],
        )
        result = bj.assess_joint(joint)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["violations"], [])
        self.assertTrue(bj.is_joint_compliant(result))

    def test_bearing_overstress_flagged(self):
        # 5000 N on 5 mm dia, 5 mm thick -> bearing = 200 MPa, allowable = 150 MPa
        joint = self._make_joint(
            "metallic_fastener", 5000.0,
            [{"id": "B1", "stiffness_N_per_m": 1.0e6,
              "diameter_mm": 5.0, "plate_thickness_mm": 5.0,
              "allowable_bearing_MPa": 150.0}],
        )
        result = bj.assess_joint(joint)
        self.assertFalse(result["compliant"])
        issues = [v["issue"] for v in result["violations"]]
        self.assertIn("bearing_overstress", issues)

    def test_missing_allowable_flagged(self):
        joint = self._make_joint(
            "composite_bolted", 3000.0,
            [{"id": "B1", "stiffness_N_per_m": 1.0e6,
              "diameter_mm": 8.0, "plate_thickness_mm": 4.0,
              "allowable_bearing_MPa": None}],
        )
        result = bj.assess_joint(joint)
        self.assertFalse(result["compliant"])
        issues = [v["issue"] for v in result["violations"]]
        self.assertIn("missing_allowable_bearing_stress", issues)

    def test_interaction_exceeded_flagged(self):
        # craft a case where bearing ratio near 0.5 and bypass ratio near 0.9
        # two fasteners: B1 stiffness 1e5 (weak), B2 stiffness 9e5 (strong)
        # total = 10000 N -> B1 gets 1000 N, B2 gets 9000 N
        # B1: bearing = 1000/(6*4) = 41.7 MPa, bypass = 0.9
        # bearing ratio with allowable 50 MPa: 41.7/50 = 0.83
        # interaction = 0.83 + 0.9 = 1.73 -> exceeded
        joint = self._make_joint(
            "metallic_fastener", 10000.0,
            [
                {"id": "B1", "stiffness_N_per_m": 1.0e5,
                 "diameter_mm": 6.0, "plate_thickness_mm": 4.0,
                 "allowable_bearing_MPa": 50.0},
                {"id": "B2", "stiffness_N_per_m": 9.0e5,
                 "diameter_mm": 12.0, "plate_thickness_mm": 5.0,
                 "allowable_bearing_MPa": 400.0},
            ],
        )
        result = bj.assess_joint(joint)
        self.assertFalse(result["compliant"])
        issues = [v["issue"] for v in result["violations"]]
        self.assertIn("bearing_bypass_interaction_exceeded", issues)

    def test_unknown_joint_type_raises(self):
        joint = self._make_joint(
            "adhesive_lap", 5000.0,
            [{"id": "B1", "stiffness_N_per_m": 1.0e6,
              "diameter_mm": 6.0, "plate_thickness_mm": 3.0,
              "allowable_bearing_MPa": 400.0}],
        )
        with self.assertRaises(ValueError):
            bj.assess_joint(joint)

    def test_multi_fastener_load_sum_equals_total(self):
        joint = self._make_joint(
            "lug_joint", 12000.0,
            [
                {"id": "B1", "stiffness_N_per_m": 2.0e6,
                 "diameter_mm": 8.0, "plate_thickness_mm": 4.0,
                 "allowable_bearing_MPa": 500.0},
                {"id": "B2", "stiffness_N_per_m": 2.0e6,
                 "diameter_mm": 8.0, "plate_thickness_mm": 4.0,
                 "allowable_bearing_MPa": 500.0},
                {"id": "B3", "stiffness_N_per_m": 2.0e6,
                 "diameter_mm": 8.0, "plate_thickness_mm": 4.0,
                 "allowable_bearing_MPa": 500.0},
            ],
        )
        result = bj.assess_joint(joint)
        total = sum(fr["load_N"] for fr in result["fastener_results"])
        self.assertAlmostEqual(total, 12000.0)

    def test_lug_joint_type_accepted(self):
        joint = self._make_joint(
            "lug_joint", 4000.0,
            [{"id": "L1", "stiffness_N_per_m": 1.0e6,
              "diameter_mm": 10.0, "plate_thickness_mm": 8.0,
              "allowable_bearing_MPa": 300.0}],
        )
        result = bj.assess_joint(joint)
        self.assertEqual(result["joint_type"], "lug_joint")

    def test_zero_load_joint_is_compliant(self):
        joint = self._make_joint(
            "metallic_fastener", 0.0,
            [{"id": "B1", "stiffness_N_per_m": 1.0e6,
              "diameter_mm": 6.0, "plate_thickness_mm": 3.0,
              "allowable_bearing_MPa": 400.0}],
        )
        result = bj.assess_joint(joint)
        self.assertTrue(result["compliant"])


if __name__ == "__main__":
    unittest.main()
