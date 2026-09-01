#!/usr/bin/env python3
"""Gate 3 contract test: LPBF parameter development.

Exercises scripts/lpbf_parameter_development_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 -

volumetric_energy_density() computes VED = laser power / (scan speed x
hatch spacing x layer thickness) from hand-computed reference values
(200 W, 800 mm/s, 0.1 mm hatch, 0.05 mm layer give 50.0 J/mm^3;
300 W, 1000 mm/s, 0.1 mm, 0.03 mm give 100.0 J/mm^3; 500 W, 2500 mm/s,
0.08 mm, 0.04 mm give 62.5 J/mm^3). hatch_overlap_fraction() and
melt_pool_penetration() check track overlap and melt pool depth.
classify_process_window() maps VED to the conduction, transition, or
keyhole regime with porosity expectations. build_parameter_matrix()
builds the power x speed x hatch grid with a regime per combination.
process_window_verdict() flags keyhole risk. build_qualification_test_matrix()
derives the coupon build and test plan per candidate parameter set.
Invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lpbf_parameter_development_logic as lpbf  # noqa: E402


class VolumetricEnergyDensityTest(unittest.TestCase):
    def test_reference_case_200w(self):
        # 200 / (800 x 0.1 x 0.05) = 200 / 4.0 = 50.0 J/mm^3
        self.assertAlmostEqual(
            lpbf.volumetric_energy_density(200, 800, 0.1, 0.05), 50.0, places=9
        )

    def test_reference_case_300w(self):
        # 300 / (1000 x 0.1 x 0.03) = 300 / 3.0 = 100.0 J/mm^3
        self.assertAlmostEqual(
            lpbf.volumetric_energy_density(300, 1000, 0.1, 0.03), 100.0, places=9
        )

    def test_reference_case_500w(self):
        # 500 / (2500 x 0.08 x 0.04) = 500 / 8.0 = 62.5 J/mm^3
        self.assertAlmostEqual(
            lpbf.volumetric_energy_density(500, 2500, 0.08, 0.04), 62.5, places=9
        )

    def test_halved_hatch_doubles_ved(self):
        # Same power, speed, layer; half the hatch spacing doubles VED.
        base = lpbf.volumetric_energy_density(200, 800, 0.1, 0.05)
        tight = lpbf.volumetric_energy_density(200, 800, 0.05, 0.05)
        self.assertAlmostEqual(tight, 2.0 * base, places=9)

    def test_doubled_speed_halves_ved(self):
        # Same power, hatch, layer; double the scan speed halves VED.
        base = lpbf.volumetric_energy_density(200, 800, 0.1, 0.05)
        fast = lpbf.volumetric_energy_density(200, 1600, 0.1, 0.05)
        self.assertAlmostEqual(fast, 0.5 * base, places=9)

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            lpbf.volumetric_energy_density("hot", 800, 0.1, 0.05)
        with self.assertRaises(ValueError):
            lpbf.volumetric_energy_density(200, None, 0.1, 0.05)

    def test_non_positive_raises(self):
        with self.assertRaises(ValueError):
            lpbf.volumetric_energy_density(0, 800, 0.1, 0.05)
        with self.assertRaises(ValueError):
            lpbf.volumetric_energy_density(200, -800, 0.1, 0.05)
        with self.assertRaises(ValueError):
            lpbf.volumetric_energy_density(200, 800, 0.0, 0.05)


class HatchOverlapTest(unittest.TestCase):
    def test_positive_overlap_reference(self):
        # width 0.12, hatch 0.08 -> (0.12 - 0.08) / 0.12 = 1/3
        self.assertAlmostEqual(
            lpbf.hatch_overlap_fraction(0.12, 0.08), 1.0 / 3.0, places=9
        )

    def test_equal_width_and_hatch_zero_overlap(self):
        self.assertEqual(lpbf.hatch_overlap_fraction(0.10, 0.10), 0.0)

    def test_hatch_wider_than_pool_negative_overlap(self):
        # 0.08 pool, 0.12 hatch -> (0.08 - 0.12) / 0.08 = -0.5 (gaps)
        self.assertAlmostEqual(
            lpbf.hatch_overlap_fraction(0.08, 0.12), -0.5, places=9
        )

    def test_overlap_decreases_as_hatch_grows(self):
        tight = lpbf.hatch_overlap_fraction(0.12, 0.06)
        wide = lpbf.hatch_overlap_fraction(0.12, 0.10)
        self.assertGreater(tight, wide)

    def test_non_positive_raises(self):
        with self.assertRaises(ValueError):
            lpbf.hatch_overlap_fraction(0.0, 0.1)
        with self.assertRaises(ValueError):
            lpbf.hatch_overlap_fraction(0.1, -0.1)

    def test_penetration_reference(self):
        # 0.12 mm deep pool over 0.03 mm layer -> 4 layers deep.
        self.assertAlmostEqual(lpbf.melt_pool_penetration(0.12, 0.03), 4.0, places=9)


class ProcessWindowTest(unittest.TestCase):
    def test_low_ved_conduction(self):
        result = lpbf.classify_process_window(40.0)
        self.assertEqual(result["regime"], "conduction")
        self.assertAlmostEqual(result["ved"], 40.0, places=9)
        self.assertIn("porosity_expectation", result)
        self.assertIn("note", result)

    def test_boundary_conduction_inclusive(self):
        self.assertEqual(lpbf.classify_process_window(60.0)["regime"], "conduction")

    def test_high_ved_keyhole_flag(self):
        # 150 J/mm^3 sits above the default 100 J/mm^3 keyhole bound.
        self.assertEqual(lpbf.classify_process_window(150.0)["regime"], "keyhole")
        self.assertIn("vapor", lpbf.classify_process_window(150.0)["porosity_expectation"])

    def test_boundary_keyhole_inclusive(self):
        self.assertEqual(lpbf.classify_process_window(100.0)["regime"], "keyhole")

    def test_mid_ved_transition(self):
        self.assertEqual(lpbf.classify_process_window(75.0)["regime"], "transition")

    def test_custom_window_bounds(self):
        # Tight window: everything above 40 is keyhole.
        self.assertEqual(
            lpbf.classify_process_window(50.0, conduction_ved=20.0, keyhole_ved=40.0)["regime"],
            "keyhole",
        )
        self.assertEqual(
            lpbf.classify_process_window(30.0, conduction_ved=20.0, keyhole_ved=40.0)["regime"],
            "transition",
        )

    def test_inverted_bounds_raise(self):
        with self.assertRaises(ValueError):
            lpbf.classify_process_window(50.0, conduction_ved=100.0, keyhole_ved=60.0)

    def test_non_positive_ved_raises(self):
        with self.assertRaises(ValueError):
            lpbf.classify_process_window(0.0)


class ParameterMatrixTest(unittest.TestCase):
    def test_matrix_dimensions(self):
        # 2 powers x 3 speeds x 2 hatches = 12 rows.
        rows = lpbf.build_parameter_matrix(
            [200, 300], [800, 1000, 1200], [0.08, 0.10], 0.03
        )
        self.assertEqual(len(rows), 12)
        for row in rows:
            self.assertEqual(
                set(row.keys()),
                {
                    "power",
                    "scan_speed",
                    "hatch_spacing",
                    "layer_thickness",
                    "volumetric_energy_density",
                    "regime",
                },
            )

    def test_matrix_deterministic_order(self):
        rows = lpbf.build_parameter_matrix(
            [300, 200], [1000, 800], [0.10, 0.08], 0.03
        )
        powers = [r["power"] for r in rows]
        self.assertEqual(powers, sorted(powers))
        # First row is the lowest power, lowest speed, lowest hatch.
        self.assertEqual(rows[0]["power"], 200.0)
        self.assertEqual(rows[0]["scan_speed"], 800.0)
        self.assertEqual(rows[0]["hatch_spacing"], 0.08)

    def test_matrix_regime_matches_classifier(self):
        rows = lpbf.build_parameter_matrix([200, 500], [800, 2500], [0.1], 0.03)
        for row in rows:
            expected = lpbf.classify_process_window(row["volumetric_energy_density"])[
                "regime"
            ]
            self.assertEqual(row["regime"], expected)

    def test_high_power_low_speed_combo_is_keyhole(self):
        rows = lpbf.build_parameter_matrix([500], [800], [0.08], 0.03)
        self.assertEqual(rows[0]["regime"], "keyhole")
        self.assertAlmostEqual(rows[0]["volumetric_energy_density"], 260.4166667, places=6)

    def test_empty_grid_raises(self):
        with self.assertRaises(ValueError):
            lpbf.build_parameter_matrix([], [800], [0.1], 0.03)
        with self.assertRaises(ValueError):
            lpbf.build_parameter_matrix([200], [800], [], 0.03)
        with self.assertRaises(ValueError):
            lpbf.build_parameter_matrix([200], [800], [0.1], "thin")

    def test_verdict_flags_keyhole(self):
        rows = lpbf.build_parameter_matrix([200, 500], [800, 2500], [0.1], 0.03)
        verdict = lpbf.process_window_verdict(rows, material="Ti-6Al-4V")
        self.assertEqual(verdict["total"], 4)
        self.assertTrue(verdict["any_keyhole"])
        self.assertGreaterEqual(verdict["keyhole_count"], 1)
        self.assertEqual(verdict["conduction_count"] + verdict["transition_count"] + verdict["keyhole_count"], 4)
        self.assertIn("keyhole", verdict["verdict"])
        self.assertEqual(verdict["material"], "Ti-6Al-4V")

    def test_verdict_all_conduction(self):
        rows = lpbf.build_parameter_matrix([150], [1200], [0.12], 0.03)
        verdict = lpbf.process_window_verdict(rows)
        self.assertFalse(verdict["any_keyhole"])
        self.assertEqual(verdict["conduction_count"], 1)
        self.assertIn("conduction", verdict["verdict"])

    def test_verdict_rejects_empty_matrix(self):
        with self.assertRaises(ValueError):
            lpbf.process_window_verdict([])
        with self.assertRaises(ValueError):
            lpbf.process_window_verdict([{"regime": "bogus"}])


class QualificationTestMatrixTest(unittest.TestCase):
    def _candidates(self):
        return [
            {
                "parameter_set_id": "LPBF-A",
                "laser_power": 300,
                "scan_speed": 1000,
                "hatch_spacing": 0.1,
                "layer_thickness": 0.03,
            },
            {
                "parameter_set_id": "LPBF-B",
                "laser_power": 350,
                "scan_speed": 1000,
                "hatch_spacing": 0.09,
                "layer_thickness": 0.03,
            },
        ]

    def test_default_matrix_rows(self):
        rows = lpbf.build_qualification_test_matrix(self._candidates())
        # 2 parameter sets x 4 tests = 8 rows.
        self.assertEqual(len(rows), 8)
        tests = [r["test"] for r in rows]
        self.assertEqual(tests, ["density", "fatigue", "hardness", "tensile"] * 2)
        density_rows = [r for r in rows if r["test"] == "density"]
        self.assertEqual(len(density_rows), 2)
        for row in density_rows:
            self.assertEqual(row["coupon_count"], 3)

    def test_default_tensile_coupon_count(self):
        rows = lpbf.build_qualification_test_matrix(self._candidates())
        tensile = [r for r in rows if r["test"] == "tensile"]
        for row in tensile:
            self.assertEqual(row["coupon_count"], 5)

    def test_custom_coupon_counts(self):
        rows = lpbf.build_qualification_test_matrix(
            self._candidates(), coupon_counts={"density": 6, "tensile": 2}
        )
        for row in rows:
            if row["test"] == "density":
                self.assertEqual(row["coupon_count"], 6)
            elif row["test"] == "tensile":
                self.assertEqual(row["coupon_count"], 2)
            elif row["test"] == "fatigue":
                self.assertEqual(row["coupon_count"], 5)

    def test_deterministic_sort_by_set_id(self):
        rows = lpbf.build_qualification_test_matrix(self._candidates())
        ids = [r["parameter_set_id"] for r in rows]
        self.assertEqual(ids, sorted(ids))

    def test_empty_parameter_sets_raise(self):
        with self.assertRaises(ValueError):
            lpbf.build_qualification_test_matrix([])

    def test_malformed_parameter_set_raises(self):
        with self.assertRaises(ValueError):
            lpbf.build_qualification_test_matrix([{"parameter_set_id": "LPBF-A"}])
        with self.assertRaises(ValueError):
            lpbf.build_qualification_test_matrix([{"parameter_set_id": "  "}])
        bad = self._candidates()
        bad[0]["laser_power"] = -300
        with self.assertRaises(ValueError):
            lpbf.build_qualification_test_matrix(bad)

    def test_bad_coupon_count_raises(self):
        with self.assertRaises(ValueError):
            lpbf.build_qualification_test_matrix(
                self._candidates(), coupon_counts={"density": 0}
            )
        with self.assertRaises(ValueError):
            lpbf.build_qualification_test_matrix(
                self._candidates(), coupon_counts={"density": True}
            )


if __name__ == "__main__":
    unittest.main()
