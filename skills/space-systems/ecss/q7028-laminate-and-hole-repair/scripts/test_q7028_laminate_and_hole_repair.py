"""Contract tests for the laminate, delamination and plated-hole repair logic."""

import unittest

from q7028_laminate_and_hole_repair_logic import (
    AREA_TOLERANCE,
    MIN_EYELET_HOLE_DIAMETER_MM,
    WALL_TOLERANCE_UM,
    area_fraction,
    assess_laminate_and_hole_repair,
    assess_surface_defect,
    barrel_wall_after_repair_um,
    rectangle_area_mm2,
    repair_allowance,
    require_count,
    require_real,
    select_hole_repair_method,
)

BOARD_L = 200.0
BOARD_W = 100.0
BOARD_AREA = BOARD_L * BOARD_W


class InputValidationTests(unittest.TestCase):
    def test_require_real_returns_float(self):
        self.assertAlmostEqual(require_real("x", 3), 3.0, places=9)

    def test_require_real_rejects_text(self):
        with self.assertRaises(ValueError):
            require_real("x", "3")

    def test_require_real_rejects_bool(self):
        with self.assertRaises(ValueError):
            require_real("x", True)

    def test_require_real_rejects_non_finite(self):
        with self.assertRaises(ValueError):
            require_real("x", float("nan"))

    def test_require_real_rejects_below_minimum(self):
        with self.assertRaises(ValueError):
            require_real("x", -0.5)

    def test_require_count_rejects_float(self):
        with self.assertRaises(ValueError):
            require_count("n", 2.0)

    def test_require_count_rejects_negative(self):
        with self.assertRaises(ValueError):
            require_count("n", -1)


class AreaTests(unittest.TestCase):
    def test_rectangle_area(self):
        self.assertAlmostEqual(rectangle_area_mm2(20.0, 5.0), 100.0, places=9)

    def test_zero_side_rejected(self):
        with self.assertRaises(ValueError):
            rectangle_area_mm2(0.0, 5.0)

    def test_fraction_of_board(self):
        self.assertAlmostEqual(area_fraction(200.0, BOARD_AREA), 0.01, places=9)

    def test_defect_larger_than_board_rejected(self):
        with self.assertRaises(ValueError):
            area_fraction(BOARD_AREA * 2.0, BOARD_AREA)

    def test_zero_board_area_rejected(self):
        with self.assertRaises(ValueError):
            area_fraction(10.0, 0.0)


class SurfaceDefectTests(unittest.TestCase):
    def _assess(self, area=100.0, gap=1.0, clearance=0.5, limit=0.01,
                kind="delamination"):
        return assess_surface_defect(kind, area, BOARD_AREA, gap, clearance, limit)

    def test_small_clear_defect_is_repairable(self):
        self.assertTrue(self._assess()["repairable"])

    def test_area_over_the_limit_is_refused(self):
        result = self._assess(area=400.0)
        self.assertTrue(result["over_area"])
        self.assertFalse(result["repairable"])

    def test_area_exactly_on_the_limit_is_accepted(self):
        result = self._assess(area=BOARD_AREA * 0.01)
        self.assertAlmostEqual(result["area_fraction"], 0.01, places=9)
        self.assertFalse(result["over_area"])

    def test_encroaching_the_clearance_envelope_is_refused(self):
        result = self._assess(gap=0.2, clearance=0.5)
        self.assertTrue(result["encroaches_clearance"])
        self.assertFalse(result["repairable"])

    def test_clearance_exactly_met_is_accepted(self):
        result = self._assess(gap=0.5, clearance=0.5)
        self.assertFalse(result["encroaches_clearance"])

    def test_a_tiny_defect_between_conductors_still_fails(self):
        result = self._assess(area=1.0, gap=0.05, clearance=0.5)
        self.assertFalse(result["over_area"])
        self.assertFalse(result["repairable"])

    def test_unknown_defect_kind_rejected(self):
        with self.assertRaises(ValueError):
            self._assess(kind="scratched-solder-resist")

    def test_area_fraction_limit_above_one_rejected(self):
        with self.assertRaises(ValueError):
            self._assess(limit=1.5)

    def test_measling_is_a_recognised_kind(self):
        self.assertEqual(self._assess(kind="measling")["kind"], "measling")


class BarrelWallTests(unittest.TestCase):
    def test_wall_after_removal_and_replating(self):
        self.assertAlmostEqual(barrel_wall_after_repair_um(35.0, 20.0, 18.0), 33.0,
                               places=9)

    def test_replating_can_restore_the_original_wall(self):
        self.assertAlmostEqual(barrel_wall_after_repair_um(25.0, 10.0, 10.0), 25.0,
                               places=9)

    def test_removing_more_than_the_wall_rejected(self):
        with self.assertRaises(ValueError):
            barrel_wall_after_repair_um(25.0, 30.0, 25.0)

    def test_negative_replating_rejected(self):
        with self.assertRaises(ValueError):
            barrel_wall_after_repair_um(25.0, 10.0, -1.0)


class HoleMethodTests(unittest.TestCase):
    def _pick(self, wall=30.0, min_wall=25.0, diameter=1.0, growth=0.05,
              max_growth=0.10, eyelet=True):
        return select_hole_repair_method(wall, min_wall, diameter, growth,
                                         max_growth, eyelet)

    def test_healthy_wall_gets_replating(self):
        self.assertEqual(self._pick()["method"], "barrel-replating")

    def test_wall_exactly_on_the_minimum_gets_replating(self):
        result = self._pick(wall=25.0, min_wall=25.0)
        self.assertEqual(result["method"], "barrel-replating")
        self.assertAlmostEqual(result["wall_after_um"], 25.0, places=9)

    def test_thin_wall_falls_back_to_an_eyelet(self):
        self.assertEqual(self._pick(wall=12.0)["method"], "eyelet-insertion")

    def test_thin_wall_in_a_small_hole_is_refused(self):
        self.assertEqual(self._pick(wall=12.0, diameter=0.4)["method"],
                         "not-repairable")

    def test_eyelet_at_the_minimum_diameter_is_allowed(self):
        result = self._pick(wall=12.0, diameter=MIN_EYELET_HOLE_DIAMETER_MM)
        self.assertEqual(result["method"], "eyelet-insertion")

    def test_eyelet_withheld_by_the_drawing_is_refused(self):
        self.assertEqual(self._pick(wall=12.0, eyelet=False)["method"],
                         "not-repairable")

    def test_diameter_growth_over_the_allowance_overrides_a_good_wall(self):
        self.assertEqual(self._pick(growth=0.5)["method"], "not-repairable")

    def test_growth_exactly_on_the_allowance_is_accepted(self):
        self.assertEqual(self._pick(growth=0.10, max_growth=0.10)["method"],
                         "barrel-replating")

    def test_non_boolean_eyelet_flag_rejected(self):
        with self.assertRaises(ValueError):
            self._pick(eyelet="yes")


class AllowanceTests(unittest.TestCase):
    def test_fresh_board_has_room(self):
        state = repair_allowance(0, 3)
        self.assertFalse(state["exhausted"])
        self.assertEqual(state["remaining_after_this_repair"], 2)

    def test_last_permitted_repair_is_flagged(self):
        self.assertTrue(repair_allowance(2, 3)["last_allowed"])

    def test_exhausted_board(self):
        self.assertTrue(repair_allowance(3, 3)["exhausted"])

    def test_zero_maximum_rejected(self):
        with self.assertRaises(ValueError):
            repair_allowance(0, 0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "board_length_mm": BOARD_L,
            "board_width_mm": BOARD_W,
            "existing_repairs": 0,
            "max_repairs": 3,
            "surface_defect": {
                "kind": "delamination",
                "length_mm": 4.0,
                "width_mm": 3.0,
                "distance_to_conductor_mm": 1.2,
                "min_clearance_mm": 0.5,
            },
        }
        spec.update(overrides)
        return spec

    def test_clean_case_is_repairable_with_no_findings(self):
        result = assess_laminate_and_hole_repair(self._spec())
        self.assertEqual(result["verdict"], "repairable")
        self.assertEqual(result["findings"], [])

    def test_board_area_is_reported(self):
        result = assess_laminate_and_hole_repair(self._spec())
        self.assertAlmostEqual(result["board_area_mm2"], BOARD_AREA, places=9)

    def test_encroaching_defect_blocks_the_repair(self):
        spec = self._spec()
        spec["surface_defect"]["distance_to_conductor_mm"] = 0.1
        result = assess_laminate_and_hole_repair(spec)
        self.assertEqual(result["verdict"], "not-repairable")

    def test_oversized_defect_blocks_the_repair(self):
        spec = self._spec()
        spec["surface_defect"]["length_mm"] = 60.0
        spec["surface_defect"]["width_mm"] = 40.0
        result = assess_laminate_and_hole_repair(spec)
        self.assertEqual(result["verdict"], "not-repairable")

    def test_exhausted_allowance_blocks_an_otherwise_sound_repair(self):
        result = assess_laminate_and_hole_repair(
            self._spec(existing_repairs=3, max_repairs=3)
        )
        self.assertEqual(result["verdict"], "not-repairable")

    def test_last_allowed_repair_needs_approval(self):
        result = assess_laminate_and_hole_repair(
            self._spec(existing_repairs=2, max_repairs=3)
        )
        self.assertEqual(result["verdict"], "repair-with-approval")

    def test_eyelet_route_needs_approval(self):
        spec = self._spec(plated_hole={
            "original_wall_um": 30.0,
            "removed_um": 28.0,
            "replated_um": 8.0,
            "min_wall_um": 25.0,
            "hole_diameter_mm": 1.0,
            "diameter_growth_mm": 0.04,
            "max_diameter_growth_mm": 0.10,
        })
        result = assess_laminate_and_hole_repair(spec)
        self.assertEqual(result["plated_hole"]["method"], "eyelet-insertion")
        self.assertEqual(result["verdict"], "repair-with-approval")

    def test_refused_hole_blocks_the_whole_repair(self):
        spec = self._spec(plated_hole={
            "original_wall_um": 30.0,
            "removed_um": 28.0,
            "replated_um": 8.0,
            "min_wall_um": 25.0,
            "hole_diameter_mm": 0.5,
            "diameter_growth_mm": 0.04,
            "max_diameter_growth_mm": 0.10,
        })
        result = assess_laminate_and_hole_repair(spec)
        self.assertEqual(result["verdict"], "not-repairable")
        self.assertTrue(any("plated hole" in f for f in result["findings"]))

    def test_hole_only_spec_is_accepted(self):
        spec = {
            "board_length_mm": BOARD_L,
            "board_width_mm": BOARD_W,
            "existing_repairs": 0,
            "max_repairs": 3,
            "plated_hole": {
                "original_wall_um": 35.0,
                "removed_um": 10.0,
                "replated_um": 10.0,
                "min_wall_um": 25.0,
                "hole_diameter_mm": 1.0,
                "diameter_growth_mm": 0.02,
                "max_diameter_growth_mm": 0.10,
            },
        }
        result = assess_laminate_and_hole_repair(spec)
        self.assertEqual(result["verdict"], "repairable")
        self.assertIsNone(result["surface_defect"])

    def test_spec_with_neither_defect_nor_hole_rejected(self):
        spec = self._spec()
        del spec["surface_defect"]
        with self.assertRaises(ValueError):
            assess_laminate_and_hole_repair(spec)

    def test_missing_board_key_rejected(self):
        spec = self._spec()
        del spec["board_width_mm"]
        with self.assertRaises(ValueError):
            assess_laminate_and_hole_repair(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_laminate_and_hole_repair(["board"])

    def test_malformed_surface_defect_rejected(self):
        spec = self._spec()
        del spec["surface_defect"]["min_clearance_mm"]
        with self.assertRaises(ValueError):
            assess_laminate_and_hole_repair(spec)

    def test_area_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(AREA_TOLERANCE, 1e-6)
        self.assertLess(WALL_TOLERANCE_UM, 1e-6)


if __name__ == "__main__":
    unittest.main()
