#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-03C clause 5.5.1 general equipment
test requirements.

Exercises scripts/e1003_eq_general_tests_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the baseline and
final sequence positions always require a comprehensive functional/
performance test while an interim position may be abbreviated unless an
anomaly is suspected; a functional/performance result is judged against
the baseline within tolerance, not a fixed spec alone; physical
configuration verification fails on either a mass out of tolerance or a
reported visual anomaly; launch configuration verification only applies
to a test point representing the launch environment; and sequence
closure requires both mandatory positions present and every point a
pass.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_eq_general_tests_logic as gt  # noqa: E402


class RequiredFunctionalDepthTest(unittest.TestCase):
    def test_baseline_is_always_comprehensive(self):
        self.assertEqual(gt.required_functional_depth("baseline", False), "comprehensive")

    def test_final_is_always_comprehensive(self):
        self.assertEqual(gt.required_functional_depth("final", False), "comprehensive")

    def test_interim_without_anomaly_is_abbreviated(self):
        self.assertEqual(gt.required_functional_depth("interim", False), "abbreviated")

    def test_interim_with_anomaly_is_comprehensive(self):
        self.assertEqual(gt.required_functional_depth("interim", True), "comprehensive")

    def test_unknown_position_raises(self):
        with self.assertRaises(ValueError):
            gt.required_functional_depth("post_launch", False)


class EvaluateFunctionalPerformanceTest(unittest.TestCase):
    def test_no_drift_is_clean(self):
        baseline = {"gain_db": 20.0, "current_ma": 150.0}
        current = {"gain_db": 20.1, "current_ma": 150.5}
        self.assertEqual(gt.evaluate_functional_performance(baseline, current, 2.0), [])

    def test_drift_beyond_tolerance_is_flagged(self):
        baseline = {"gain_db": 20.0, "current_ma": 150.0}
        current = {"gain_db": 20.1, "current_ma": 200.0}
        self.assertEqual(
            gt.evaluate_functional_performance(baseline, current, 2.0), ["current_ma"]
        )

    def test_results_sorted_by_parameter_name(self):
        baseline = {"z_param": 1.0, "a_param": 1.0}
        current = {"z_param": 2.0, "a_param": 2.0}
        self.assertEqual(
            gt.evaluate_functional_performance(baseline, current, 1.0),
            ["a_param", "z_param"],
        )

    def test_zero_baseline_matching_zero_is_clean(self):
        self.assertEqual(
            gt.evaluate_functional_performance({"offset": 0.0}, {"offset": 0.0}, 1.0), []
        )

    def test_zero_baseline_with_nonzero_current_is_flagged(self):
        self.assertEqual(
            gt.evaluate_functional_performance({"offset": 0.0}, {"offset": 0.5}, 1.0),
            ["offset"],
        )

    def test_missing_current_parameter_raises(self):
        with self.assertRaises(ValueError):
            gt.evaluate_functional_performance({"gain_db": 20.0}, {}, 2.0)


class CheckPhysicalConfigurationTest(unittest.TestCase):
    def test_mass_in_tolerance_no_anomaly_is_as_configured(self):
        self.assertEqual(
            gt.check_physical_configuration(10.02, 10.0, 1.0, False), "as_configured"
        )

    def test_mass_out_of_tolerance_is_discrepancy(self):
        self.assertEqual(
            gt.check_physical_configuration(10.5, 10.0, 1.0, False),
            "configuration_discrepancy",
        )

    def test_visual_anomaly_is_discrepancy_even_with_mass_in_tolerance(self):
        self.assertEqual(
            gt.check_physical_configuration(10.0, 10.0, 1.0, True),
            "configuration_discrepancy",
        )

    def test_zero_reference_mass_raises(self):
        with self.assertRaises(ValueError):
            gt.check_physical_configuration(1.0, 0.0, 1.0, False)


class CheckLaunchConfigurationTest(unittest.TestCase):
    def test_not_applicable_when_not_launch_environment(self):
        self.assertTrue(gt.check_launch_configuration("bench", "stowed", False))

    def test_matching_configuration_ok(self):
        self.assertTrue(gt.check_launch_configuration("stowed", "stowed", True))

    def test_mismatched_configuration_flagged(self):
        self.assertFalse(gt.check_launch_configuration("deployed", "stowed", True))


class EvaluateTestPointTest(unittest.TestCase):
    BASE = {
        "position": "interim",
        "anomaly_suspected": False,
        "baseline_measurements": {"gain_db": 20.0},
        "current_measurements": {"gain_db": 20.1},
        "tolerance_pct": 2.0,
        "measured_mass": 10.0,
        "reference_mass": 10.0,
        "mass_tolerance_pct": 1.0,
        "visual_anomaly_detected": False,
        "represents_launch_environment": True,
        "current_configuration": "stowed",
        "required_launch_configuration": "stowed",
    }

    def test_clean_interim_point_passes(self):
        self.assertEqual(
            gt.evaluate_test_point(self.BASE),
            {
                "position": "interim",
                "functional_depth": "abbreviated",
                "degraded_parameters": [],
                "configuration_status": "as_configured",
                "launch_configuration_ok": True,
                "verdict": "pass",
            },
        )

    def test_functional_degradation_takes_priority(self):
        point = dict(
            self.BASE,
            current_measurements={"gain_db": 25.0},
            measured_mass=12.0,
            current_configuration="deployed",
        )
        self.assertEqual(gt.evaluate_test_point(point)["verdict"], "functional_degradation")

    def test_configuration_discrepancy_when_functional_clean(self):
        point = dict(self.BASE, measured_mass=12.0)
        self.assertEqual(gt.evaluate_test_point(point)["verdict"], "configuration_discrepancy")

    def test_launch_configuration_mismatch_when_otherwise_clean(self):
        point = dict(self.BASE, current_configuration="deployed")
        self.assertEqual(
            gt.evaluate_test_point(point)["verdict"], "launch_configuration_mismatch"
        )

    def test_launch_mismatch_exempt_when_not_launch_environment(self):
        point = dict(
            self.BASE, current_configuration="deployed", represents_launch_environment=False
        )
        self.assertEqual(gt.evaluate_test_point(point)["verdict"], "pass")

    def test_baseline_position_requires_comprehensive_depth(self):
        point = dict(self.BASE, position="baseline")
        self.assertEqual(gt.evaluate_test_point(point)["functional_depth"], "comprehensive")

    def test_does_not_mutate_input(self):
        before = dict(self.BASE)
        gt.evaluate_test_point(self.BASE)
        self.assertEqual(self.BASE, before)


class BuildSequenceDispositionsTest(unittest.TestCase):
    def test_dispositions_in_input_order(self):
        base = dict(EvaluateTestPointTest.BASE, position="baseline")
        final = dict(EvaluateTestPointTest.BASE, position="final", measured_mass=15.0)
        result = gt.build_sequence_dispositions([base, final])
        self.assertEqual([entry["position"] for entry in result], ["baseline", "final"])
        self.assertEqual(result[1]["verdict"], "configuration_discrepancy")


class MissingMandatoryPositionsTest(unittest.TestCase):
    def test_detects_missing_final(self):
        points = [dict(EvaluateTestPointTest.BASE, position="baseline")]
        self.assertEqual(gt.missing_mandatory_positions(points), ["final"])

    def test_detects_missing_both(self):
        points = [dict(EvaluateTestPointTest.BASE, position="interim")]
        self.assertEqual(gt.missing_mandatory_positions(points), ["baseline", "final"])

    def test_no_gap_when_both_present(self):
        points = [
            dict(EvaluateTestPointTest.BASE, position="baseline"),
            dict(EvaluateTestPointTest.BASE, position="final"),
        ]
        self.assertEqual(gt.missing_mandatory_positions(points), [])


class CloseOutGeneralTestSequenceTest(unittest.TestCase):
    def test_all_clear_sequence_closes_clean(self):
        points = [
            dict(EvaluateTestPointTest.BASE, position="baseline"),
            dict(EvaluateTestPointTest.BASE, position="interim"),
            dict(EvaluateTestPointTest.BASE, position="final"),
        ]
        dispositions = gt.build_sequence_dispositions(points)
        self.assertEqual(
            gt.close_out_general_test_sequence(points, dispositions), (True, [], [])
        )

    def test_missing_final_blocks_closure(self):
        points = [dict(EvaluateTestPointTest.BASE, position="baseline")]
        dispositions = gt.build_sequence_dispositions(points)
        all_clear, missing_positions, open_items = gt.close_out_general_test_sequence(
            points, dispositions
        )
        self.assertFalse(all_clear)
        self.assertEqual(missing_positions, ["final"])
        self.assertEqual(open_items, [])

    def test_open_item_blocks_closure(self):
        points = [
            dict(EvaluateTestPointTest.BASE, position="baseline"),
            dict(EvaluateTestPointTest.BASE, position="final", measured_mass=20.0),
        ]
        dispositions = gt.build_sequence_dispositions(points)
        all_clear, missing_positions, open_items = gt.close_out_general_test_sequence(
            points, dispositions
        )
        self.assertFalse(all_clear)
        self.assertEqual(missing_positions, [])
        self.assertEqual(
            open_items, [{"position": "final", "verdict": "configuration_discrepancy"}]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
