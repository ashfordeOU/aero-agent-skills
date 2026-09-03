"""Offline deterministic contract test for fastener_installation_quality.

Run with: python3 test_fastener_installation_quality.py
Covers the worked example anchors from the wave-28
fastener-installation-quality spec: stack 14.0 mm, grip 15.875 mm,
protrusion 1.875 mm, clamp load 18897.6 N at 24 N m with k 0.2 and
D 0.00635 m, clamp verdict clamp-ok inside [12000, 25000] N, the pass
verdict, every rework and scrap defect path, the torque scatter note,
and ValueError rejection of non-physical inputs.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastener_installation_quality_logic import (
    FASTENER_TYPES,
    FLUSHNESS_TOLERANCE_DEFAULT_MM,
    HEAD_STYLES,
    K_TYPICAL,
    PROTRUSION_MAX_MM,
    PROTRUSION_MIN_MM,
    SCATTER_BAND_PCT,
    THREADS_MIN,
    clamp_load_N,
    clamp_verdict,
    collar_engagement_ok,
    flushness_ok,
    installation_verdict,
    protrusion_ok,
    select_grip,
)

STACK = [4.0, 6.0, 4.0]
GRIPS = [12.7, 15.875, 19.05]
GRIPS_LONG = [12.7, 15.875, 19.05, 22.0]
D = 0.00635
TORQUE = 24
K = 0.2
MIN_CLAMP = 12000
MAX_CLAMP = 25000


class GripSelectionContractTest(unittest.TestCase):
    """Grip length selection for the clamped stack."""

    def test_select_grip_worked_example(self):
        result = select_grip(STACK, GRIPS)
        self.assertAlmostEqual(result["stack_total_mm"], 14.0, places=9)
        self.assertAlmostEqual(result["grip_mm"], 15.875, places=9)
        self.assertAlmostEqual(result["protrusion_mm"], 1.875,
                               places=9)

    def test_select_grip_exact_match_zero_protrusion(self):
        result = select_grip([12.7], [12.7, 15.875])
        self.assertAlmostEqual(result["grip_mm"], 12.7, places=9)
        self.assertAlmostEqual(result["protrusion_mm"], 0.0, places=9)

    def test_select_grip_none_when_no_grip_reaches_stack(self):
        result = select_grip([10.0, 8.0], [12.7, 15.875])
        self.assertEqual(result["stack_total_mm"], 18.0)
        self.assertIsNone(result["grip_mm"])
        self.assertIsNone(result["protrusion_mm"])

    def test_select_grip_next_increment_above_stack(self):
        result = select_grip([10.0, 8.0], GRIPS_LONG)
        self.assertAlmostEqual(result["grip_mm"], 19.05, places=9)
        self.assertAlmostEqual(result["protrusion_mm"], 1.05, places=9)

    def test_select_grip_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            select_grip([], GRIPS)
        with self.assertRaises(ValueError):
            select_grip([-1.0, 4.0], GRIPS)
        with self.assertRaises(ValueError):
            select_grip(STACK, [])
        with self.assertRaises(ValueError):
            select_grip(STACK, [19.05, 12.7, 15.875])


class ProtrusionContractTest(unittest.TestCase):
    """Thread protrusion band check."""

    def test_protrusion_ok_in_band_and_boundaries(self):
        self.assertTrue(protrusion_ok(1.875))
        self.assertTrue(protrusion_ok(PROTRUSION_MIN_MM))
        self.assertTrue(protrusion_ok(PROTRUSION_MAX_MM))

    def test_protrusion_ok_out_of_band(self):
        self.assertFalse(protrusion_ok(0.4))
        self.assertFalse(protrusion_ok(3.1))
        self.assertFalse(protrusion_ok(-0.025))


class ClampLoadContractTest(unittest.TestCase):
    """Clamp load from applied torque, k factor and diameter."""

    def test_clamp_load_worked_example(self):
        clamp = clamp_load_N(TORQUE, K, D)
        self.assertAlmostEqual(clamp, 18897.6, delta=0.5)

    def test_clamp_load_scales_with_torque(self):
        clamp = clamp_load_N(40, K, D)
        self.assertAlmostEqual(clamp, 31496.0, delta=0.5)

    def test_clamp_load_uses_k_factor(self):
        clamp = clamp_load_N(TORQUE, 0.15, D)
        self.assertAlmostEqual(clamp, 25196.85, delta=0.5)
        self.assertEqual(K_TYPICAL, 0.2)

    def test_clamp_load_non_positive_inputs_raise(self):
        with self.assertRaises(ValueError):
            clamp_load_N(0, K, D)
        with self.assertRaises(ValueError):
            clamp_load_N(-10, K, D)
        with self.assertRaises(ValueError):
            clamp_load_N(TORQUE, 0, D)
        with self.assertRaises(ValueError):
            clamp_load_N(TORQUE, K, 0)
        with self.assertRaises(ValueError):
            clamp_load_N(TORQUE, K, -D)


class ClampVerdictContractTest(unittest.TestCase):
    """Clamp load against the joint allowables."""

    def test_clamp_verdict_ok(self):
        self.assertEqual(clamp_verdict(18897.6, MIN_CLAMP, MAX_CLAMP),
                         "clamp-ok")

    def test_clamp_verdict_under_clamp(self):
        self.assertEqual(clamp_verdict(7874.0, MIN_CLAMP, MAX_CLAMP),
                         "under-clamp")

    def test_clamp_verdict_over_clamp(self):
        self.assertEqual(clamp_verdict(31496.0, MIN_CLAMP, MAX_CLAMP),
                         "over-clamp")

    def test_clamp_verdict_boundaries_inclusive(self):
        self.assertEqual(clamp_verdict(MIN_CLAMP, MIN_CLAMP, MAX_CLAMP),
                         "clamp-ok")
        self.assertEqual(clamp_verdict(MAX_CLAMP, MIN_CLAMP, MAX_CLAMP),
                         "clamp-ok")
        self.assertEqual(
            clamp_verdict(MIN_CLAMP - 0.1, MIN_CLAMP, MAX_CLAMP),
            "under-clamp")
        self.assertEqual(
            clamp_verdict(MAX_CLAMP + 0.1, MIN_CLAMP, MAX_CLAMP),
            "over-clamp")

    def test_clamp_verdict_invalid_limits_raise(self):
        with self.assertRaises(ValueError):
            clamp_verdict(10000, 0, MAX_CLAMP)
        with self.assertRaises(ValueError):
            clamp_verdict(10000, -12000, MAX_CLAMP)
        with self.assertRaises(ValueError):
            clamp_verdict(10000, MAX_CLAMP, MIN_CLAMP)


class FlushnessContractTest(unittest.TestCase):
    """Countersink flushness for flush head fasteners."""

    def test_flushness_ok_within_and_boundary(self):
        self.assertTrue(flushness_ok(0.0))
        self.assertTrue(flushness_ok(0.10))
        self.assertTrue(flushness_ok(0.13))
        self.assertTrue(flushness_ok(-0.13))
        self.assertEqual(FLUSHNESS_TOLERANCE_DEFAULT_MM, 0.13)

    def test_flushness_ok_out_of_tolerance(self):
        self.assertFalse(flushness_ok(0.22))
        self.assertFalse(flushness_ok(-0.22))
        self.assertFalse(flushness_ok(0.14))


class CollarEngagementContractTest(unittest.TestCase):
    """Swage collar engagement for lock-bolt fasteners."""

    def test_collar_engagement_ok_at_minimum_and_above(self):
        self.assertTrue(collar_engagement_ok(THREADS_MIN))
        self.assertTrue(collar_engagement_ok(3))
        self.assertEqual(THREADS_MIN, 2)

    def test_collar_engagement_below_minimum(self):
        self.assertFalse(collar_engagement_ok(1))
        self.assertFalse(collar_engagement_ok(0))

    def test_collar_engagement_none_input_returns_none(self):
        self.assertIsNone(collar_engagement_ok(None))

    def test_collar_engagement_negative_raises(self):
        with self.assertRaises(ValueError):
            collar_engagement_ok(-1)


class InstallationVerdictContractTest(unittest.TestCase):
    """Full installation verdict, defect and scatter note."""

    def base_inputs(self):
        return dict(stack_thicknesses_mm=STACK,
                    available_grips_mm=GRIPS,
                    fastener_diameter_m=D,
                    applied_torque_Nm=TORQUE,
                    min_clamp_N=MIN_CLAMP,
                    max_clamp_N=MAX_CLAMP)

    def test_verdict_pass_bolt_nut_worked_example(self):
        result = installation_verdict(**self.base_inputs())
        self.assertEqual(result["verdict"], "pass")
        self.assertIsNone(result["defect"])
        self.assertAlmostEqual(result["grip_mm"], 15.875, places=9)
        self.assertAlmostEqual(result["protrusion_mm"], 1.875,
                               places=9)
        self.assertTrue(result["protrusion_ok"])
        self.assertAlmostEqual(result["clamp_N"], 18897.6, delta=0.5)
        self.assertEqual(result["clamp_verdict"], "clamp-ok")

    def test_verdict_no_grip_fits(self):
        inputs = self.base_inputs()
        inputs["stack_thicknesses_mm"] = [10.0, 8.0]
        inputs["available_grips_mm"] = [12.7, 15.875]
        result = installation_verdict(**inputs)
        self.assertEqual(result["verdict"], "rework")
        self.assertEqual(result["defect"], "no-grip-fits")
        self.assertIsNone(result["grip_mm"])
        self.assertAlmostEqual(result["stack_total_mm"], 18.0,
                               places=9)

    def test_verdict_protrusion_out_of_band(self):
        inputs = self.base_inputs()
        inputs["stack_thicknesses_mm"] = [15.9]
        inputs["available_grips_mm"] = GRIPS_LONG
        result = installation_verdict(**inputs)
        self.assertEqual(result["verdict"], "rework")
        self.assertEqual(result["defect"], "protrusion-out-of-band")
        self.assertAlmostEqual(result["grip_mm"], 19.05, places=9)
        self.assertAlmostEqual(result["protrusion_mm"], 3.15, places=9)
        self.assertFalse(result["protrusion_ok"])

    def test_verdict_over_clamp_scrap(self):
        inputs = self.base_inputs()
        inputs["applied_torque_Nm"] = 40
        result = installation_verdict(**inputs)
        self.assertEqual(result["verdict"], "scrap")
        self.assertEqual(result["defect"], "over-clamp")
        self.assertAlmostEqual(result["clamp_N"], 31496.0, delta=0.5)
        self.assertEqual(result["clamp_verdict"], "over-clamp")

    def test_verdict_under_clamp_rework(self):
        inputs = self.base_inputs()
        inputs["applied_torque_Nm"] = 10
        result = installation_verdict(**inputs)
        self.assertEqual(result["verdict"], "rework")
        self.assertEqual(result["defect"], "under-clamp")
        self.assertAlmostEqual(result["clamp_N"], 7874.0, delta=0.5)
        self.assertEqual(result["clamp_verdict"], "under-clamp")

    def test_verdict_flushness_out_of_tolerance(self):
        inputs = self.base_inputs()
        inputs["head_style"] = "flush"
        inputs["measured_flushness_mm"] = 0.22
        result = installation_verdict(**inputs)
        self.assertEqual(result["verdict"], "rework")
        self.assertEqual(result["defect"], "flushness-out-of-tolerance")
        self.assertFalse(result["flushness_ok"])
        inputs["measured_flushness_mm"] = -0.22
        recessed = installation_verdict(**inputs)
        self.assertEqual(recessed["verdict"], "rework")
        self.assertEqual(recessed["defect"],
                         "flushness-out-of-tolerance")

    def test_verdict_flushness_pass_within_tolerance(self):
        inputs = self.base_inputs()
        inputs["head_style"] = "flush"
        inputs["measured_flushness_mm"] = 0.10
        result = installation_verdict(**inputs)
        self.assertEqual(result["verdict"], "pass")
        self.assertIsNone(result["defect"])
        self.assertTrue(result["flushness_ok"])

    def test_verdict_collar_engagement_rework(self):
        inputs = self.base_inputs()
        inputs["fastener_type"] = "lock-bolt"
        inputs["collar_engaged_threads"] = 1
        result = installation_verdict(**inputs)
        self.assertEqual(result["verdict"], "rework")
        self.assertEqual(result["defect"], "collar-engagement")
        self.assertFalse(result["collar_engagement_ok"])

    def test_verdict_lockbolt_and_rivet_type_paths(self):
        locked = self.base_inputs()
        locked["fastener_type"] = "lock-bolt"
        locked["collar_engaged_threads"] = 2
        passed = installation_verdict(**locked)
        self.assertEqual(passed["verdict"], "pass")
        self.assertIsNone(passed["defect"])
        self.assertTrue(passed["collar_engagement_ok"])
        unmeasured = self.base_inputs()
        unmeasured["fastener_type"] = "lock-bolt"
        blocked = installation_verdict(**unmeasured)
        self.assertEqual(blocked["verdict"], "rework")
        self.assertEqual(blocked["defect"], "collar-engagement")
        self.assertIsNone(blocked["collar_engagement_ok"])
        riveted = self.base_inputs()
        riveted["fastener_type"] = "rivet"
        rivet_pass = installation_verdict(**riveted)
        self.assertEqual(rivet_pass["verdict"], "pass")
        self.assertIsNone(rivet_pass["defect"])
        self.assertIsNone(rivet_pass["collar_engagement_ok"])

    def test_scatter_note_ok_within_band(self):
        inputs = self.base_inputs()
        inputs["installed_torque_actual_Nm"] = 26.4
        result = installation_verdict(**inputs)
        self.assertEqual(result["verdict"], "pass")
        self.assertAlmostEqual(result["scatter_pct"], 10.0, places=9)
        self.assertTrue(result["scatter_ok"])
        self.assertEqual(SCATTER_BAND_PCT, 15.0)

    def test_scatter_note_over_band_informational_only(self):
        inputs = self.base_inputs()
        inputs["installed_torque_actual_Nm"] = 30.0
        result = installation_verdict(**inputs)
        self.assertEqual(result["verdict"], "pass")
        self.assertAlmostEqual(result["scatter_pct"], 25.0, places=9)
        self.assertFalse(result["scatter_ok"])

    def test_scatter_note_absent_without_actual_torque(self):
        result = installation_verdict(**self.base_inputs())
        self.assertIsNone(result["scatter_pct"])
        self.assertIsNone(result["scatter_ok"])

    def test_verdict_invalid_inputs_raise(self):
        bad_type = self.base_inputs()
        bad_type["fastener_type"] = "screw"
        with self.assertRaises(ValueError):
            installation_verdict(**bad_type)
        bad_style = self.base_inputs()
        bad_style["head_style"] = "domed"
        with self.assertRaises(ValueError):
            installation_verdict(**bad_style)
        bad_diameter = self.base_inputs()
        bad_diameter["fastener_diameter_m"] = 0
        with self.assertRaises(ValueError):
            installation_verdict(**bad_diameter)
        bad_torque = self.base_inputs()
        bad_torque["applied_torque_Nm"] = 0
        with self.assertRaises(ValueError):
            installation_verdict(**bad_torque)
        bad_flush = self.base_inputs()
        bad_flush["head_style"] = "flush"
        bad_flush["measured_flushness_mm"] = None
        with self.assertRaises(ValueError):
            installation_verdict(**bad_flush)
        self.assertEqual(FASTENER_TYPES,
                         ("bolt-nut", "lock-bolt", "rivet"))
        self.assertEqual(HEAD_STYLES, ("protruding", "flush"))


if __name__ == "__main__":
    unittest.main()
