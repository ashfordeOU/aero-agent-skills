"""Contract tests for the post-repair verification logic."""

import unittest

from q7028_post_repair_verification_logic import (
    MAGNIFICATION_STEPS,
    REFERENCE_APPARENT_SIZE_MM,
    assess_post_repair_verification,
    grade_dimensional,
    grade_electrical,
    grade_radiographic,
    grade_visual,
    missing_inspections,
    require_band,
    require_real,
    required_inspection_set,
    required_magnification,
)


class InputValidationTests(unittest.TestCase):
    def test_require_real_returns_float(self):
        self.assertAlmostEqual(require_real("x", 4), 4.0, places=9)

    def test_require_real_rejects_bool(self):
        with self.assertRaises(ValueError):
            require_real("x", True)

    def test_require_real_rejects_infinity(self):
        with self.assertRaises(ValueError):
            require_real("x", float("inf"))

    def test_require_band_rejects_inverted(self):
        with self.assertRaises(ValueError):
            require_band("b", (2.0, 1.0))


class MagnificationTests(unittest.TestCase):
    def test_one_millimetre_feature_takes_the_three_times_step(self):
        self.assertAlmostEqual(required_magnification(1.0), 3.0, places=9)

    def test_a_feature_needing_exactly_a_step_takes_that_step(self):
        feature = REFERENCE_APPARENT_SIZE_MM / 10.0
        self.assertAlmostEqual(required_magnification(feature), 10.0, places=9)

    def test_a_smaller_feature_moves_up_a_step(self):
        self.assertAlmostEqual(required_magnification(0.5), 7.5, places=9)

    def test_the_largest_feature_takes_the_lowest_step(self):
        self.assertAlmostEqual(required_magnification(5.0),
                               MAGNIFICATION_STEPS[0], places=9)

    def test_a_feature_beyond_the_bench_is_refused(self):
        with self.assertRaises(ValueError):
            required_magnification(0.01)

    def test_zero_feature_size_rejected(self):
        with self.assertRaises(ValueError):
            required_magnification(0.0)


class InspectionSetTests(unittest.TestCase):
    def test_every_repair_owes_a_visual(self):
        self.assertIn("visual", required_inspection_set(["conformal-coating-repair"]))

    def test_a_coating_repair_owes_no_electrical(self):
        self.assertNotIn("electrical",
                         required_inspection_set(["conformal-coating-repair"]))

    def test_a_track_cut_owes_an_electrical(self):
        self.assertIn("electrical", required_inspection_set(["track-cut"]))

    def test_a_plated_hole_repair_owes_a_radiograph(self):
        self.assertIn("radiographic",
                      required_inspection_set(["plated-hole-repair"]))

    def test_a_hidden_joint_owes_a_radiograph_on_its_own(self):
        required = required_inspection_set(["solder-joint-rework"], True)
        self.assertIn("radiographic", required)

    def test_a_visible_joint_rework_owes_no_radiograph(self):
        required = required_inspection_set(["solder-joint-rework"], False)
        self.assertNotIn("radiographic", required)

    def test_several_repairs_union_their_inspections(self):
        required = required_inspection_set(["track-cut", "laminate-repair"])
        self.assertEqual(required, ["dimensional", "electrical", "visual"])

    def test_unknown_repair_kind_rejected(self):
        with self.assertRaises(ValueError):
            required_inspection_set(["re-varnishing"])

    def test_empty_repair_list_rejected(self):
        with self.assertRaises(ValueError):
            required_inspection_set([])

    def test_non_boolean_hidden_flag_rejected(self):
        with self.assertRaises(ValueError):
            required_inspection_set(["track-cut"], "yes")

    def test_missing_inspections_are_listed(self):
        self.assertEqual(
            missing_inspections(["electrical", "visual"], ["visual"]), ["electrical"]
        )

    def test_nothing_missing_when_all_performed(self):
        self.assertEqual(
            missing_inspections(["visual"], ["visual", "electrical"]), []
        )

    def test_unknown_performed_inspection_rejected(self):
        with self.assertRaises(ValueError):
            missing_inspections(["visual"], ["sniff-test"])


class GradingTests(unittest.TestCase):
    def test_adequate_magnification_is_acceptable(self):
        self.assertTrue(grade_visual(10.0, 1.0)["acceptable"])

    def test_magnification_exactly_on_the_requirement_is_acceptable(self):
        result = grade_visual(3.0, 1.0)
        self.assertFalse(result["under_magnified"])

    def test_under_magnified_visual_is_flagged(self):
        self.assertTrue(grade_visual(1.75, 0.5)["under_magnified"])

    def test_sound_electrical_result(self):
        self.assertTrue(grade_electrical(500.0, 100.0, 2.0, 10.0)["acceptable"])

    def test_low_insulation_is_flagged(self):
        result = grade_electrical(10.0, 100.0, 2.0, 10.0)
        self.assertTrue(result["insulation_low"])
        self.assertFalse(result["acceptable"])

    def test_high_path_resistance_is_flagged(self):
        self.assertTrue(
            grade_electrical(500.0, 100.0, 40.0, 10.0)["path_resistance_high"]
        )

    def test_readings_exactly_on_their_limits_are_acceptable(self):
        self.assertTrue(grade_electrical(100.0, 100.0, 10.0, 10.0)["acceptable"])

    def test_dimension_in_band(self):
        self.assertTrue(grade_dimensional(1.5, (1.0, 2.0))["acceptable"])

    def test_dimension_under_band(self):
        self.assertTrue(grade_dimensional(0.5, (1.0, 2.0))["under_band"])

    def test_dimension_over_band(self):
        self.assertTrue(grade_dimensional(2.5, (1.0, 2.0))["over_band"])

    def test_dimension_on_the_band_edge_is_acceptable(self):
        self.assertTrue(grade_dimensional(2.0, (1.0, 2.0))["acceptable"])

    def test_acceptable_voiding(self):
        self.assertTrue(grade_radiographic(0.10, 0.25)["acceptable"])

    def test_voiding_exactly_on_the_limit_is_acceptable(self):
        self.assertTrue(grade_radiographic(0.25, 0.25)["acceptable"])

    def test_excessive_voiding_is_flagged(self):
        self.assertTrue(grade_radiographic(0.40, 0.25)["excessive_voiding"])

    def test_void_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            grade_radiographic(1.4, 0.25)


class AssessmentTests(unittest.TestCase):
    def _results(self, **overrides):
        results = {
            "visual": {"magnification_used": 10.0, "smallest_feature_mm": 1.0},
            "electrical": {
                "insulation_mohm": 500.0, "min_insulation_mohm": 100.0,
                "path_resistance_mohm": 2.0, "max_path_resistance_mohm": 10.0,
            },
        }
        results.update(overrides)
        return results

    def test_complete_and_passing_verification_is_accepted(self):
        result = assess_post_repair_verification({
            "repair_kinds": ["track-cut"],
            "results": self._results(),
        })
        self.assertEqual(result["verdict"], "accept")
        self.assertEqual(result["findings"], [])

    def test_a_missing_required_inspection_is_incomplete_not_a_pass(self):
        result = assess_post_repair_verification({
            "repair_kinds": ["track-cut"],
            "results": {"visual": {"magnification_used": 10.0,
                                   "smallest_feature_mm": 1.0}},
        })
        self.assertEqual(result["verdict"], "incomplete")
        self.assertEqual(result["missing_inspections"], ["electrical"])

    def test_a_failed_inspection_outranks_a_missing_one(self):
        result = assess_post_repair_verification({
            "repair_kinds": ["plated-hole-repair"],
            "results": self._results(
                visual={"magnification_used": 1.75, "smallest_feature_mm": 0.5}
            ),
        })
        self.assertEqual(result["verdict"], "reject")
        self.assertIn("visual", result["failed_inspections"])

    def test_a_hidden_joint_pulls_in_the_radiograph(self):
        result = assess_post_repair_verification({
            "repair_kinds": ["solder-joint-rework"],
            "hidden_connection": True,
            "results": self._results(),
        })
        self.assertIn("radiographic", result["required_inspections"])
        self.assertEqual(result["verdict"], "incomplete")

    def test_a_radiograph_that_was_run_is_graded(self):
        result = assess_post_repair_verification({
            "repair_kinds": ["plated-hole-repair"],
            "results": self._results(
                dimensional={"measured_mm": 1.1, "band_mm": (1.0, 1.2)},
                radiographic={"void_fraction": 0.4, "max_void_fraction": 0.25},
            ),
        })
        self.assertEqual(result["verdict"], "reject")
        self.assertIn("radiographic", result["failed_inspections"])

    def test_an_extra_inspection_is_graded_but_not_required(self):
        result = assess_post_repair_verification({
            "repair_kinds": ["track-cut"],
            "results": self._results(
                dimensional={"measured_mm": 1.1, "band_mm": (1.0, 1.2)}
            ),
        })
        self.assertNotIn("dimensional", result["required_inspections"])
        self.assertIn("dimensional", result["performed_inspections"])
        self.assertEqual(result["verdict"], "accept")

    def test_every_missing_inspection_is_named_in_the_findings(self):
        result = assess_post_repair_verification({
            "repair_kinds": ["plated-hole-repair"],
            "results": {"visual": {"magnification_used": 10.0,
                                   "smallest_feature_mm": 1.0}},
        })
        self.assertEqual(len(result["findings"]), 3)

    def test_unknown_inspection_in_the_results_rejected(self):
        with self.assertRaises(ValueError):
            assess_post_repair_verification({
                "repair_kinds": ["track-cut"],
                "results": {"smell": {}},
            })

    def test_results_missing_a_reading_rejected(self):
        with self.assertRaises(ValueError):
            assess_post_repair_verification({
                "repair_kinds": ["track-cut"],
                "results": {"visual": {"magnification_used": 10.0}},
            })

    def test_spec_without_results_rejected(self):
        with self.assertRaises(ValueError):
            assess_post_repair_verification({"repair_kinds": ["track-cut"]})

    def test_spec_without_repair_kinds_rejected(self):
        with self.assertRaises(ValueError):
            assess_post_repair_verification({"results": {}})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_post_repair_verification("verify")


if __name__ == "__main__":
    unittest.main()
