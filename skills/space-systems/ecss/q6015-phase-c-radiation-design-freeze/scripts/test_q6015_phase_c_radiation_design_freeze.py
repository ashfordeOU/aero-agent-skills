"""Contract tests for the clause 4.4.3 design-freeze logic."""

import math
import unittest

from q6015_phase_c_radiation_design_freeze_logic import (
    MARGIN_TOLERANCE,
    MIN_CHARACTERIZATION_SAMPLE,
    TOLERANCE_FACTORS,
    assess_design_freeze,
    assess_part_freeze,
    characterized_capability,
    radiation_design_margin,
    sample_mean,
    sample_stdev,
    shielded_dose,
    spot_shield_mass_kg,
    tolerance_factor,
    total_shielding_mm,
)

CURVE = [
    (1.0, 100.0),
    (2.0, 50.0),
    (4.0, 25.0),
    (8.0, 12.5),
    (16.0, 6.25),
]

TIGHT_LOT = [100.0, 101.0, 99.0, 100.5, 99.5]


class ToleranceFactorTests(unittest.TestCase):
    def test_tabulated_size_returns_its_factor(self):
        self.assertAlmostEqual(tolerance_factor(10), TOLERANCE_FACTORS[10], places=9)

    def test_size_between_entries_reads_the_lower_one(self):
        self.assertAlmostEqual(tolerance_factor(11), TOLERANCE_FACTORS[10], places=9)

    def test_large_sample_reads_the_largest_entry(self):
        largest = max(TOLERANCE_FACTORS)
        self.assertAlmostEqual(tolerance_factor(500), TOLERANCE_FACTORS[largest], places=9)

    def test_factor_falls_as_the_sample_grows(self):
        self.assertGreater(tolerance_factor(3), tolerance_factor(30))

    def test_sample_below_the_minimum_rejected(self):
        with self.assertRaises(ValueError):
            tolerance_factor(MIN_CHARACTERIZATION_SAMPLE - 1)

    def test_non_integer_sample_rejected(self):
        with self.assertRaises(ValueError):
            tolerance_factor(7.5)


class SampleStatisticTests(unittest.TestCase):
    def test_mean_of_a_symmetric_lot(self):
        self.assertAlmostEqual(sample_mean(TIGHT_LOT), 100.0, places=9)

    def test_stdev_uses_the_sample_denominator(self):
        values = [10.0, 12.0, 14.0]
        expected = math.sqrt(((10 - 12) ** 2 + 0 + (14 - 12) ** 2) / 2.0)
        self.assertAlmostEqual(sample_stdev(values), expected, places=9)

    def test_identical_results_give_zero_spread(self):
        self.assertAlmostEqual(sample_stdev([50.0, 50.0, 50.0]), 0.0, places=12)

    def test_single_result_rejected(self):
        with self.assertRaises(ValueError):
            sample_mean([100.0])

    def test_non_positive_result_rejected(self):
        with self.assertRaises(ValueError):
            sample_stdev([100.0, 0.0, 90.0])

    def test_non_numeric_result_rejected(self):
        with self.assertRaises(ValueError):
            sample_mean([100.0, "ninety"])


class CapabilityTests(unittest.TestCase):
    def test_zero_spread_capability_equals_the_mean(self):
        self.assertAlmostEqual(
            characterized_capability([80.0, 80.0, 80.0, 80.0, 80.0]), 80.0, places=9
        )

    def test_capability_sits_below_the_mean_when_the_lot_scatters(self):
        self.assertLess(characterized_capability(TIGHT_LOT), sample_mean(TIGHT_LOT))

    def test_capability_matches_the_closed_form(self):
        expected = sample_mean(TIGHT_LOT) - tolerance_factor(len(TIGHT_LOT)) * sample_stdev(
            TIGHT_LOT
        )
        self.assertAlmostEqual(characterized_capability(TIGHT_LOT), expected, places=9)

    def test_a_wide_lot_can_collapse_the_capability(self):
        self.assertLess(characterized_capability([10.0, 200.0, 40.0]), 0.0)

    def test_sample_of_two_is_refused_by_the_factor_table(self):
        with self.assertRaises(ValueError):
            characterized_capability([100.0, 101.0])


class ShieldingTests(unittest.TestCase):
    def test_spot_shield_adds_to_the_inherent_thickness(self):
        self.assertAlmostEqual(total_shielding_mm(2.0, 3.0), 5.0, places=9)

    def test_no_spot_shield_leaves_the_inherent_thickness(self):
        self.assertAlmostEqual(total_shielding_mm(2.0), 2.0, places=9)

    def test_negative_spot_shield_rejected(self):
        with self.assertRaises(ValueError):
            total_shielding_mm(2.0, -1.0)

    def test_dose_at_a_tabulated_thickness(self):
        self.assertAlmostEqual(shielded_dose(CURVE, 4.0), 25.0, places=9)

    def test_spot_shield_lowers_the_dose(self):
        self.assertLess(shielded_dose(CURVE, 2.0, 2.0), shielded_dose(CURVE, 2.0))

    def test_thickness_beyond_the_curve_refused(self):
        with self.assertRaises(ValueError):
            shielded_dose(CURVE, 8.0, 20.0)

    def test_non_monotone_curve_rejected(self):
        with self.assertRaises(ValueError):
            shielded_dose([(2.0, 50.0), (2.0, 25.0)], 2.0)

    def test_mass_scales_with_thickness_and_area(self):
        self.assertAlmostEqual(spot_shield_mass_kg(100.0, 2.0, 2.70), 0.054, places=9)

    def test_zero_spot_shield_costs_no_mass(self):
        self.assertAlmostEqual(spot_shield_mass_kg(100.0, 0.0, 2.70), 0.0, places=12)

    def test_negative_density_rejected(self):
        with self.assertRaises(ValueError):
            spot_shield_mass_kg(100.0, 2.0, -2.70)


class PartFreezeTests(unittest.TestCase):
    def test_margin_is_a_ratio(self):
        self.assertAlmostEqual(radiation_design_margin(240.0, 80.0), 3.0, places=9)

    def test_part_with_margin_is_ready(self):
        record = assess_part_freeze(
            {"reference": "U1", "characterization_results": [300.0] * 5}, 100.0, 2.0
        )
        self.assertTrue(record["ready"])
        self.assertIsNone(record["blocker"])

    def test_part_exactly_on_the_required_margin_is_ready(self):
        record = assess_part_freeze(
            {"reference": "U1", "characterization_results": [200.0] * 5}, 100.0, 2.0
        )
        self.assertTrue(record["ready"])
        self.assertAlmostEqual(record["margin"], 2.0, places=9)
        self.assertLessEqual(abs(record["margin"] - 2.0), MARGIN_TOLERANCE)

    def test_part_short_of_the_margin_is_blocked(self):
        record = assess_part_freeze(
            {"reference": "U1", "characterization_results": [150.0] * 5}, 100.0, 2.0
        )
        self.assertFalse(record["ready"])
        self.assertIn("below the required", record["blocker"])

    def test_part_without_characterization_is_blocked(self):
        record = assess_part_freeze({"reference": "U1"}, 100.0, 2.0)
        self.assertFalse(record["ready"])
        self.assertIsNone(record["capability"])

    def test_collapsed_capability_is_blocked(self):
        record = assess_part_freeze(
            {"reference": "U1", "characterization_results": [10.0, 200.0, 40.0]}, 100.0, 2.0
        )
        self.assertFalse(record["ready"])
        self.assertIn("no usable design capability", record["blocker"])

    def test_part_without_reference_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_freeze({"characterization_results": [300.0] * 5}, 100.0, 2.0)

    def test_non_positive_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_freeze(
                {"reference": "U1", "characterization_results": [300.0] * 5}, 100.0, 0.0
            )


class DesignFreezeTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "parts": [{"reference": "U1", "characterization_results": [300.0] * 5}],
            "dose_depth_curve": CURVE,
            "inherent_shielding_mm": 4.0,
            "design_factor": 2.0,
            "required_margin": 2.0,
            "spot_shield_mm": 0.0,
            "open_waivers": [],
        }
        spec.update(overrides)
        return spec

    def test_clean_equipment_may_freeze(self):
        result = assess_design_freeze(self._spec())
        self.assertTrue(result["freeze_allowed"])
        self.assertEqual(result["blockers"], [])

    def test_specified_level_is_the_dose_times_the_factor(self):
        result = assess_design_freeze(self._spec())
        self.assertAlmostEqual(
            result["specified_level_krad"], result["location_dose_krad"] * 2.0, places=9
        )

    def test_spot_shield_lowers_the_specified_level(self):
        bare = assess_design_freeze(self._spec())
        shielded = assess_design_freeze(self._spec(spot_shield_mm=4.0))
        self.assertLess(shielded["specified_level_krad"], bare["specified_level_krad"])

    def test_uncharacterized_part_blocks_the_freeze(self):
        result = assess_design_freeze(self._spec(parts=[{"reference": "U2"}]))
        self.assertFalse(result["freeze_allowed"])
        self.assertEqual(len(result["blockers"]), 1)

    def test_open_waiver_blocks_the_freeze(self):
        result = assess_design_freeze(self._spec(open_waivers=["single-event latch-up on U7"]))
        self.assertFalse(result["freeze_allowed"])

    def test_shield_mass_over_allocation_blocks_the_freeze(self):
        result = assess_design_freeze(
            self._spec(
                spot_shield_mm=4.0,
                spot_shield_area_cm2=400.0,
                spot_shield_density_g_cm3=2.70,
                shielding_mass_allocation_kg=0.1,
            )
        )
        self.assertFalse(result["freeze_allowed"])
        self.assertTrue(any("allocation" in b for b in result["blockers"]))

    def test_shield_mass_is_reported_when_a_footprint_is_given(self):
        result = assess_design_freeze(
            self._spec(spot_shield_mm=2.0, spot_shield_area_cm2=100.0)
        )
        self.assertAlmostEqual(result["spot_shield_mass_kg"], 0.054, places=9)

    def test_parts_are_reported_in_reference_order(self):
        result = assess_design_freeze(
            self._spec(
                parts=[
                    {"reference": "U9", "characterization_results": [300.0] * 5},
                    {"reference": "U2", "characterization_results": [300.0] * 5},
                ]
            )
        )
        self.assertEqual([item["reference"] for item in result["parts"]], ["U2", "U9"])

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["design_factor"]
        with self.assertRaises(ValueError):
            assess_design_freeze(spec)

    def test_empty_part_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_freeze(self._spec(parts=[]))

    def test_non_sequence_waivers_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_freeze(self._spec(open_waivers="latch-up"))


if __name__ == "__main__":
    unittest.main()
