"""Contract tests for the particulate cleanliness level selection logic."""

import unittest

from q7001_particulate_level_selection_logic import (
    BANDS,
    DEFAULT_CATEGORY_CEILING_UM,
    DEFAULT_LEVEL_LADDER_UM,
    SELECTION_TOLERANCE,
    category_ceiling_um,
    evaluate_candidate,
    level_obscuration_percent,
    projected_fallout_percent,
    select_particulate_level,
    validate_band,
    validate_ladder,
    validate_non_negative,
    validate_positive,
)


def nominal_spec(**overrides):
    spec = {
        "band": "sensitive",
        "allowed_obscuration_percent": 0.1,
        "margin_factor": 1.5,
        "fallout_rate_percent_per_day": 0.0005,
        "exposure_days": 30.0,
    }
    spec.update(overrides)
    return spec


class ValidationTests(unittest.TestCase):
    def test_positive_value_returns_float(self):
        self.assertEqual(validate_positive(300, "level_um"), 300.0)

    def test_zero_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "level_um")

    def test_non_negative_accepts_zero_exposure(self):
        self.assertEqual(validate_non_negative(0, "exposure_days"), 0.0)

    def test_negative_fallout_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_non_negative(-0.1, "fallout_rate_percent_per_day")

    def test_band_names_are_normalised(self):
        self.assertEqual(validate_band("  Highly-Sensitive "), "highly-sensitive")

    def test_unknown_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band("pristine")

    def test_every_band_has_a_default_ceiling(self):
        for band in BANDS:
            self.assertIn(band, DEFAULT_CATEGORY_CEILING_UM)

    def test_default_ladder_is_accepted_and_ordered(self):
        ladder = validate_ladder()
        self.assertEqual(ladder, sorted(ladder))
        self.assertEqual(len(ladder), len(DEFAULT_LEVEL_LADDER_UM))

    def test_declared_ladder_is_sorted(self):
        self.assertEqual(validate_ladder([300.0, 100.0, 200.0]), [100.0, 200.0, 300.0])

    def test_repeated_ladder_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_ladder([100.0, 100.0, 300.0])

    def test_empty_ladder_rejected(self):
        with self.assertRaises(ValueError):
            validate_ladder([])


class CeilingTests(unittest.TestCase):
    def test_more_demanding_band_has_a_finer_ceiling(self):
        self.assertLess(
            category_ceiling_um("highly-sensitive"), category_ceiling_um("tolerant")
        )

    def test_declared_ceilings_override_the_default(self):
        self.assertAlmostEqual(
            category_ceiling_um("sensitive", {"sensitive": 150.0}), 150.0, places=9
        )

    def test_band_absent_from_the_declared_ceilings_rejected(self):
        with self.assertRaises(ValueError):
            category_ceiling_um("sensitive", {"tolerant": 1000.0})

    def test_non_mapping_ceilings_rejected(self):
        with self.assertRaises(ValueError):
            category_ceiling_um("sensitive", [1000.0])


class AccumulationTests(unittest.TestCase):
    def test_fallout_is_rate_times_exposure(self):
        self.assertAlmostEqual(projected_fallout_percent(0.0005, 30.0), 0.015, places=12)

    def test_zero_exposure_accumulates_nothing(self):
        self.assertAlmostEqual(projected_fallout_percent(0.0005, 0.0), 0.0)

    def test_negative_exposure_rejected(self):
        with self.assertRaises(ValueError):
            projected_fallout_percent(0.0005, -1.0)


class LevelObscurationTests(unittest.TestCase):
    def test_a_coarser_level_obscures_more(self):
        self.assertGreater(
            level_obscuration_percent(300.0), level_obscuration_percent(100.0)
        )

    def test_obscuration_is_a_small_percentage_for_a_fine_level(self):
        value = level_obscuration_percent(100.0)
        self.assertGreater(value, 0.0)
        self.assertLess(value, 0.01)

    def test_declared_channels_are_honoured(self):
        with_channels = level_obscuration_percent(300.0, [15.0, 45.0, 90.0, 180.0, 300.0])
        self.assertAlmostEqual(with_channels, level_obscuration_percent(300.0), places=9)

    def test_channels_above_the_label_are_dropped(self):
        value = level_obscuration_percent(100.0, [5.0, 25.0, 100.0, 300.0])
        self.assertGreater(value, 0.0)

    def test_too_few_usable_channels_rejected(self):
        with self.assertRaises(ValueError):
            level_obscuration_percent(10.0, [50.0, 100.0])

    def test_non_increasing_channels_rejected(self):
        with self.assertRaises(ValueError):
            level_obscuration_percent(300.0, [50.0, 50.0, 100.0])

    def test_zero_slope_rejected(self):
        with self.assertRaises(ValueError):
            level_obscuration_percent(300.0, None, 0.0)


class CandidateTests(unittest.TestCase):
    def test_candidate_sums_delivery_and_accumulation(self):
        record = evaluate_candidate(300.0, nominal_spec())
        self.assertAlmostEqual(
            record["end_of_exposure_percent"],
            record["delivered_obscuration_percent"]
            + record["accumulated_obscuration_percent"],
            places=12,
        )

    def test_margin_multiplies_the_end_of_exposure_figure(self):
        record = evaluate_candidate(300.0, nominal_spec())
        self.assertAlmostEqual(
            record["with_margin_percent"],
            1.5 * record["end_of_exposure_percent"],
            places=12,
        )

    def test_unit_margin_leaves_the_figure_unchanged(self):
        record = evaluate_candidate(300.0, nominal_spec(margin_factor=1.0))
        self.assertAlmostEqual(
            record["with_margin_percent"], record["end_of_exposure_percent"], places=12
        )

    def test_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_candidate(300.0, nominal_spec(margin_factor=0.8))

    def test_a_coarse_candidate_leaves_the_budget(self):
        record = evaluate_candidate(1000.0, nominal_spec())
        self.assertFalse(record["inside_budget"])


class SelectionTests(unittest.TestCase):
    def test_nominal_selection_is_the_band_ceiling(self):
        result = select_particulate_level(nominal_spec())
        self.assertTrue(result["selected"])
        self.assertAlmostEqual(result["selected_level_um"], 300.0, places=9)
        self.assertEqual(result["binding_constraint"], "category-ceiling")
        self.assertEqual(result["findings"], [])

    def test_admissible_levels_are_the_ones_at_or_below_the_selection(self):
        result = select_particulate_level(nominal_spec())
        self.assertEqual(result["admissible_levels_um"], [50.0, 100.0, 200.0, 300.0])

    def test_budget_binds_when_the_ceiling_is_loose(self):
        result = select_particulate_level(nominal_spec(band="tolerant"))
        self.assertEqual(result["binding_constraint"], "obscuration-budget")
        self.assertAlmostEqual(result["selected_level_um"], 300.0, places=9)

    def test_ladder_end_binds_when_nothing_else_does(self):
        result = select_particulate_level(
            nominal_spec(band="tolerant", allowed_obscuration_percent=50.0)
        )
        self.assertEqual(result["binding_constraint"], "ladder-exhausted")
        self.assertAlmostEqual(result["selected_level_um"], 1000.0, places=9)

    def test_no_level_meets_a_very_tight_budget(self):
        result = select_particulate_level(
            nominal_spec(
                allowed_obscuration_percent=1e-9, fallout_rate_percent_per_day=0.0
            )
        )
        self.assertFalse(result["selected"])
        self.assertIsNone(result["selected_level_um"])
        self.assertTrue(any("no candidate level" in f for f in result["findings"]))

    def test_fallout_alone_eating_the_budget_is_its_own_finding(self):
        result = select_particulate_level(
            nominal_spec(fallout_rate_percent_per_day=0.01, exposure_days=100.0)
        )
        self.assertTrue(
            any("already exceeds" in finding for finding in result["findings"])
        )

    def test_verification_floor_can_exclude_every_candidate(self):
        result = select_particulate_level(
            nominal_spec(band="tolerant", verification_floor_um=400.0)
        )
        self.assertFalse(result["selected"])
        self.assertTrue(any("verification floor" in f for f in result["findings"]))

    def test_verification_floor_below_the_selection_changes_nothing(self):
        result = select_particulate_level(nominal_spec(verification_floor_um=100.0))
        self.assertAlmostEqual(result["selected_level_um"], 300.0, places=9)
        self.assertEqual(result["admissible_levels_um"], [100.0, 200.0, 300.0])

    def test_floor_coarser_than_the_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            select_particulate_level(nominal_spec(verification_floor_um=400.0))

    def test_declared_ladder_is_used_for_the_candidates(self):
        result = select_particulate_level(
            nominal_spec(band="tolerant", ladder=[100.0, 250.0])
        )
        self.assertEqual([r["level_um"] for r in result["candidates"]], [100.0, 250.0])

    def test_missing_band_rejected(self):
        spec = nominal_spec()
        del spec["band"]
        with self.assertRaises(ValueError):
            select_particulate_level(spec)

    def test_missing_budget_rejected(self):
        spec = nominal_spec()
        del spec["allowed_obscuration_percent"]
        with self.assertRaises(ValueError):
            select_particulate_level(spec)

    def test_non_mapping_specification_rejected(self):
        with self.assertRaises(ValueError):
            select_particulate_level(["band"])

    def test_tolerance_is_small_enough_to_be_a_representation_allowance(self):
        self.assertLess(SELECTION_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
