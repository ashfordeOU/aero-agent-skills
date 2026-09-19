#!/usr/bin/env python3
"""Contract test for braze defect disposition (offline)."""

import copy
import unittest

from q7040_defect_disposition_logic import (
    ACCEPT_AS_IS,
    CEILING,
    DEFAULT_REBRAZE_LIMIT,
    DISPOSITION_ESCALATION,
    FLOOR,
    LOCAL_REPAIR,
    REJECT_AND_SCRAP,
    RE_BRAZE,
    USE_AS_IS_ON_DEVIATION,
    dispose_all,
    dispose_defect,
    reinspection_for,
    remaining_rebraze_attempts,
    rework_bound,
    severity_ratio,
    thermal_exposure_remaining,
    within_limit,
)

VOID_DEFECT = {
    "id": "D-001",
    "defect_type": "oversize-void",
    "location": "load-path",
    "braze_class": "class-a",
    "measured": 0.08,
    "limit": 0.05,
    "detected_by": "radiographic-testing",
    "hermetic": True,
    "rebraze_count": 0,
    "thermal_cycles_used": 1,
}


def _defect(**overrides):
    defect = copy.deepcopy(VOID_DEFECT)
    defect.update(overrides)
    return defect


class SeverityTests(unittest.TestCase):
    def test_a_ceiling_ratio_is_measured_over_limit(self):
        self.assertAlmostEqual(severity_ratio(0.10, 0.05, CEILING), 2.0, places=9)

    def test_a_floor_ratio_is_limit_over_measured(self):
        self.assertAlmostEqual(severity_ratio(0.45, 0.90, FLOOR), 2.0, places=9)

    def test_a_measurement_on_its_ceiling_is_within_limit(self):
        self.assertTrue(within_limit(0.05, 0.05, CEILING))

    def test_a_measurement_on_its_floor_is_within_limit(self):
        self.assertTrue(within_limit(0.90, 0.90, FLOOR))

    def test_a_measurement_past_its_ceiling_is_not_within_limit(self):
        self.assertFalse(within_limit(0.06, 0.05, CEILING))

    def test_a_zero_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            severity_ratio(0.05, 0.0, CEILING)

    def test_an_unknown_sense_is_rejected(self):
        with self.assertRaises(ValueError):
            severity_ratio(0.05, 0.10, "sideways")


class BudgetTests(unittest.TestCase):
    def test_an_unused_joint_has_its_whole_rebraze_budget(self):
        self.assertEqual(remaining_rebraze_attempts(0), DEFAULT_REBRAZE_LIMIT)

    def test_each_attempt_spends_one_from_the_budget(self):
        self.assertEqual(remaining_rebraze_attempts(1, 2), 1)
        self.assertEqual(remaining_rebraze_attempts(2, 2), 0)

    def test_a_count_over_the_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            remaining_rebraze_attempts(3, 2)

    def test_a_negative_count_is_rejected(self):
        with self.assertRaises(ValueError):
            remaining_rebraze_attempts(-1, 2)

    def test_exposure_allowance_never_goes_negative(self):
        self.assertEqual(thermal_exposure_remaining(9, 3), 0)

    def test_exposure_allowance_counts_down(self):
        self.assertEqual(thermal_exposure_remaining(1, 3), 2)

    def test_the_rework_bound_relaxes_with_the_class(self):
        self.assertGreater(rework_bound("class-c"), rework_bound("class-a"))

    def test_an_unknown_class_has_no_rework_bound(self):
        with self.assertRaises(ValueError):
            rework_bound("class-z")


class ReinspectionTests(unittest.TestCase):
    def test_an_accepted_joint_owes_no_reinspection(self):
        self.assertEqual(
            reinspection_for(ACCEPT_AS_IS, "radiographic-testing", True), []
        )

    def test_a_scrapped_joint_owes_no_reinspection(self):
        self.assertEqual(
            reinspection_for(REJECT_AND_SCRAP, "ultrasonic-testing", True), []
        )

    def test_rework_repeats_the_method_that_found_the_defect(self):
        methods = reinspection_for(RE_BRAZE, "ultrasonic-testing", False)
        self.assertIn("ultrasonic-testing", methods)
        self.assertIn("visual-inspection", methods)

    def test_a_hermetic_joint_owes_its_leak_test_again(self):
        self.assertIn(
            "leak-testing", reinspection_for(LOCAL_REPAIR, "radiographic-testing", True)
        )

    def test_a_non_hermetic_joint_owes_no_leak_test(self):
        self.assertNotIn(
            "leak-testing", reinspection_for(LOCAL_REPAIR, "radiographic-testing", False)
        )

    def test_a_visually_found_defect_is_not_listed_twice(self):
        methods = reinspection_for(RE_BRAZE, "visual-inspection", False)
        self.assertEqual(methods, ["visual-inspection"])

    def test_an_unknown_inspection_method_is_rejected(self):
        with self.assertRaises(ValueError):
            reinspection_for(RE_BRAZE, "thermography", False)


class DispositionTests(unittest.TestCase):
    def test_a_defect_inside_its_limit_is_accepted_as_is(self):
        result = dispose_defect(_defect(measured=0.04))
        self.assertEqual(result["disposition"], ACCEPT_AS_IS)
        self.assertTrue(result["within_limit"])
        self.assertEqual(result["reinspection"], [])

    def test_a_defect_exactly_on_its_limit_is_accepted_as_is(self):
        result = dispose_defect(_defect(measured=0.05))
        self.assertEqual(result["disposition"], ACCEPT_AS_IS)

    def test_a_modest_overshoot_goes_to_re_braze(self):
        result = dispose_defect(VOID_DEFECT)
        self.assertEqual(result["disposition"], RE_BRAZE)
        self.assertEqual(result["remaining_rebraze_attempts"], 2)

    def test_a_defect_exactly_on_the_rework_bound_is_still_reworkable(self):
        result = dispose_defect(_defect(measured=0.10))
        self.assertAlmostEqual(result["severity_ratio"], 2.0, places=9)
        self.assertEqual(result["disposition"], RE_BRAZE)

    def test_a_defect_past_the_rework_bound_is_scrapped(self):
        result = dispose_defect(_defect(measured=0.20))
        self.assertEqual(result["disposition"], REJECT_AND_SCRAP)
        self.assertTrue(any("rework bound" in f for f in result["findings"]))

    def test_a_spent_rebraze_budget_closes_the_thermal_route(self):
        result = dispose_defect(_defect(rebraze_count=2, rebraze_limit=2))
        self.assertNotEqual(result["disposition"], RE_BRAZE)
        self.assertTrue(any("budget" in f for f in result["findings"]))

    def test_a_spent_exposure_allowance_closes_the_thermal_route(self):
        result = dispose_defect(
            _defect(thermal_cycles_used=3, thermal_cycle_allowance=3)
        )
        self.assertNotEqual(result["disposition"], RE_BRAZE)
        self.assertTrue(any("exposure allowance" in f for f in result["findings"]))

    def test_a_parent_metal_crack_leaves_the_rework_routes(self):
        result = dispose_defect(
            _defect(defect_type="base-metal-crack", measured=0.01, limit=0.05)
        )
        self.assertEqual(result["disposition"], REJECT_AND_SCRAP)
        self.assertTrue(any("parent metal" in f for f in result["findings"]))

    def test_a_filler_crack_inside_its_limit_is_still_not_accepted(self):
        result = dispose_defect(
            _defect(defect_type="filler-crack", measured=0.01, limit=0.05)
        )
        self.assertNotEqual(result["disposition"], ACCEPT_AS_IS)

    def test_eroded_parent_metal_out_of_the_load_path_is_repaired(self):
        result = dispose_defect(
            _defect(defect_type="base-metal-erosion", location="non-load-path")
        )
        self.assertEqual(result["disposition"], LOCAL_REPAIR)

    def test_eroded_parent_metal_in_the_load_path_is_scrapped(self):
        result = dispose_defect(_defect(defect_type="base-metal-erosion"))
        self.assertEqual(result["disposition"], REJECT_AND_SCRAP)

    def test_entrapped_flux_is_removed_mechanically(self):
        result = dispose_defect(_defect(defect_type="flux-entrapment"))
        self.assertEqual(result["disposition"], LOCAL_REPAIR)
        self.assertEqual(result["remaining_rebraze_attempts"], 2)

    def test_a_mechanical_defect_past_the_bound_is_scrapped(self):
        result = dispose_defect(
            _defect(defect_type="excess-filler", measured=0.30)
        )
        self.assertEqual(result["disposition"], REJECT_AND_SCRAP)

    def test_an_approved_deviation_carries_a_defect_out_of_the_load_path(self):
        result = dispose_defect(
            _defect(
                rebraze_count=2, rebraze_limit=2,
                location="non-load-path", deviation_approved=True,
            )
        )
        self.assertEqual(result["disposition"], USE_AS_IS_ON_DEVIATION)

    def test_a_deviation_cannot_carry_a_load_path_defect(self):
        result = dispose_defect(
            _defect(rebraze_count=2, rebraze_limit=2, deviation_approved=True)
        )
        self.assertEqual(result["disposition"], REJECT_AND_SCRAP)
        self.assertTrue(any("load-path" in f for f in result["findings"]))

    def test_no_deviation_on_file_is_reported(self):
        result = dispose_defect(
            _defect(rebraze_count=2, rebraze_limit=2, location="non-load-path")
        )
        self.assertEqual(result["disposition"], REJECT_AND_SCRAP)
        self.assertTrue(any("no approved deviation" in f for f in result["findings"]))

    def test_a_fill_shortfall_is_scored_as_a_floor(self):
        result = dispose_defect(
            _defect(defect_type="fill-shortfall", measured=0.60, limit=0.90)
        )
        self.assertAlmostEqual(result["severity_ratio"], 1.5, places=9)

    def test_a_non_mapping_defect_is_rejected(self):
        with self.assertRaises(ValueError):
            dispose_defect("oversize-void")

    def test_an_unknown_defect_type_is_rejected(self):
        with self.assertRaises(ValueError):
            dispose_defect(_defect(defect_type="cold-shut"))

    def test_a_non_boolean_deviation_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            dispose_defect(_defect(deviation_approved="signed"))


class DispositionSetTests(unittest.TestCase):
    def test_the_worst_route_governs_the_part(self):
        summary = dispose_all(
            [_defect(measured=0.04), _defect(id="D-002", measured=0.20)]
        )
        self.assertEqual(summary["governing_disposition"], REJECT_AND_SCRAP)
        self.assertTrue(summary["scrapped"])

    def test_a_scrapped_part_owes_no_combined_reinspection(self):
        summary = dispose_all([_defect(measured=0.20)])
        self.assertEqual(summary["combined_reinspection"], [])

    def test_a_reworked_part_combines_its_reinspection_once_each(self):
        summary = dispose_all([VOID_DEFECT, _defect(id="D-003")])
        self.assertEqual(
            summary["combined_reinspection"],
            ["visual-inspection", "radiographic-testing", "leak-testing"],
        )

    def test_every_disposition_appears_in_the_counts(self):
        summary = dispose_all([VOID_DEFECT])
        self.assertEqual(sorted(summary["counts"]), sorted(DISPOSITION_ESCALATION))

    def test_an_empty_defect_set_is_rejected(self):
        with self.assertRaises(ValueError):
            dispose_all([])


if __name__ == "__main__":
    unittest.main()
