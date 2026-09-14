"""Contract tests for the clause 4.3.9 destructive physical analysis logic."""

import unittest

from q6013_class_1_destructive_physical_analysis_logic import (
    DEFAULT_MIN_SAMPLE,
    DEFAULT_SAMPLE_FRACTION,
    MAJOR_DEFECTS,
    MINOR_DEFECTS,
    assess_destructive_physical_analysis,
    bond_pull_assessment,
    categorize_defect,
    categorize_defects,
    dpa_sample_size,
    lot_disposition,
    sample_plan,
    validate_fraction,
    void_assessment,
)

VOID_LIMITS = {"total_limit": 0.10, "largest_limit": 0.05}


class FractionValidationTests(unittest.TestCase):
    def test_returns_float(self):
        self.assertAlmostEqual(validate_fraction(0.25, "f"), 0.25, places=9)

    def test_zero_allowed_by_default(self):
        self.assertAlmostEqual(validate_fraction(0.0, "f"), 0.0, places=9)

    def test_zero_rejected_when_disallowed(self):
        with self.assertRaises(ValueError):
            validate_fraction(0.0, "f", allow_zero=False)

    def test_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(1.4, "f")

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(-0.01, "f")

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction(True, "f")


class DefectRegisterTests(unittest.TestCase):
    def test_major_code_categorized(self):
        self.assertEqual(categorize_defect("wire-bond-lift"), "major")

    def test_minor_code_categorized(self):
        self.assertEqual(categorize_defect("lead-finish-blemish"), "minor")

    def test_case_and_padding_tolerated(self):
        self.assertEqual(categorize_defect("  Die-Crack "), "major")

    def test_unregistered_code_rejected(self):
        with self.assertRaises(ValueError):
            categorize_defect("odd-looking-thing")

    def test_empty_code_rejected(self):
        with self.assertRaises(ValueError):
            categorize_defect("  ")

    def test_registers_do_not_overlap(self):
        self.assertEqual(MAJOR_DEFECTS & MINOR_DEFECTS, frozenset())

    def test_grouping_splits_the_sequence(self):
        grouped = categorize_defects(["die-crack", "lead-finish-blemish"])
        self.assertEqual(grouped["major"], ["die-crack"])
        self.assertEqual(grouped["minor"], ["lead-finish-blemish"])

    def test_grouping_empty_sequence(self):
        self.assertEqual(categorize_defects([]), {"major": [], "minor": []})

    def test_grouping_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            categorize_defects("die-crack")


class SampleSizeTests(unittest.TestCase):
    def test_fraction_rounds_up(self):
        self.assertEqual(dpa_sample_size(250, 0.01, 2), 3)

    def test_exact_fraction_does_not_round_up_a_whole_unit(self):
        self.assertEqual(dpa_sample_size(200, 0.01, 2), 2)

    def test_floor_applies_to_a_small_group(self):
        self.assertEqual(dpa_sample_size(40, 0.01, 2), 2)

    def test_sample_never_exceeds_the_group(self):
        self.assertEqual(dpa_sample_size(1, 0.01, 2), 1)

    def test_larger_fraction_takes_more_units(self):
        self.assertEqual(dpa_sample_size(1000, 0.02, 2), 20)

    def test_defaults_are_exposed(self):
        self.assertEqual(
            dpa_sample_size(1000),
            dpa_sample_size(1000, DEFAULT_SAMPLE_FRACTION, DEFAULT_MIN_SAMPLE),
        )

    def test_zero_group_rejected(self):
        with self.assertRaises(ValueError):
            dpa_sample_size(0, 0.01, 2)

    def test_zero_fraction_rejected(self):
        with self.assertRaises(ValueError):
            dpa_sample_size(500, 0.0, 2)

    def test_float_group_rejected(self):
        with self.assertRaises(ValueError):
            dpa_sample_size(500.0, 0.01, 2)


class SamplePlanTests(unittest.TestCase):
    def test_single_date_code_plan(self):
        plan = sample_plan({"2341": 500})
        self.assertEqual(plan["total_units"], 500)
        self.assertEqual(plan["total_sample"], 5)
        self.assertEqual(plan["findings"], [])

    def test_each_date_code_sampled_separately(self):
        plan = sample_plan({"2341": 500, "2402": 500})
        self.assertEqual(plan["total_sample"], 10)
        self.assertEqual(len(plan["groups"]), 2)

    def test_multiple_date_codes_raise_a_finding(self):
        plan = sample_plan({"2341": 500, "2402": 500})
        self.assertTrue(any("date codes" in f for f in plan["findings"]))

    def test_group_consumed_by_its_own_sample_is_a_finding(self):
        plan = sample_plan({"2341": 2})
        self.assertTrue(any("consumes the group" in f for f in plan["findings"]))

    def test_groups_are_returned_in_date_code_order(self):
        plan = sample_plan({"2402": 300, "2341": 300})
        self.assertEqual([g["date_code"] for g in plan["groups"]], ["2341", "2402"])

    def test_empty_shipment_rejected(self):
        with self.assertRaises(ValueError):
            sample_plan({})

    def test_zero_count_rejected(self):
        with self.assertRaises(ValueError):
            sample_plan({"2341": 0})

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            sample_plan([("2341", 500)])


class VoidAssessmentTests(unittest.TestCase):
    def test_voiding_inside_limits(self):
        out = void_assessment(0.04, 0.02, VOID_LIMITS)
        self.assertTrue(out["within_limits"])
        self.assertEqual(out["defects"], [])

    def test_total_voiding_over_limit_is_major(self):
        out = void_assessment(0.18, 0.04, VOID_LIMITS)
        self.assertFalse(out["within_limits"])
        self.assertEqual(out["defects"], ["die-attach-void-excess"])

    def test_single_void_over_limit_is_major_even_when_total_passes(self):
        out = void_assessment(0.08, 0.07, VOID_LIMITS)
        self.assertFalse(out["within_limits"])

    def test_value_exactly_on_the_total_limit_passes(self):
        out = void_assessment(0.10, 0.02, VOID_LIMITS)
        self.assertAlmostEqual(out["total_void_fraction"], out["total_limit"], places=9)
        self.assertTrue(out["within_limits"])

    def test_value_exactly_on_the_largest_limit_passes(self):
        out = void_assessment(0.08, 0.05, VOID_LIMITS)
        self.assertAlmostEqual(out["largest_void_fraction"], out["largest_limit"], places=9)
        self.assertTrue(out["within_limits"])

    def test_zero_voiding_passes(self):
        self.assertTrue(void_assessment(0.0, 0.0, VOID_LIMITS)["within_limits"])

    def test_largest_void_above_total_rejected(self):
        with self.assertRaises(ValueError):
            void_assessment(0.04, 0.06, VOID_LIMITS)

    def test_inconsistent_limits_rejected(self):
        with self.assertRaises(ValueError):
            void_assessment(0.04, 0.02, {"total_limit": 0.05, "largest_limit": 0.10})

    def test_missing_limit_key_rejected(self):
        with self.assertRaises(ValueError):
            void_assessment(0.04, 0.02, {"total_limit": 0.10})


class BondPullTests(unittest.TestCase):
    def test_strong_bonds_pass(self):
        out = bond_pull_assessment([9.0, 10.0, 11.0], 4.0, 6.0)
        self.assertTrue(out["within_limits"])
        self.assertAlmostEqual(out["mean_observed_g"], 10.0, places=9)

    def test_one_weak_bond_disposes_of_the_lot(self):
        out = bond_pull_assessment([9.0, 10.0, 2.0], 4.0, 6.0)
        self.assertFalse(out["within_limits"])
        self.assertEqual(out["defects"], ["bond-pull-below-limit"])

    def test_mean_below_the_mean_floor_fails_even_with_no_single_failure(self):
        out = bond_pull_assessment([5.0, 5.0, 5.0], 4.0, 6.0)
        self.assertFalse(out["within_limits"])

    def test_minimum_exactly_on_the_floor_passes(self):
        out = bond_pull_assessment([4.0, 10.0, 10.0], 4.0, 6.0)
        self.assertAlmostEqual(out["minimum_observed_g"], out["minimum_limit_g"], places=9)
        self.assertTrue(out["within_limits"])

    def test_mean_exactly_on_the_mean_floor_passes(self):
        out = bond_pull_assessment([6.0, 6.0, 6.0], 4.0, 6.0)
        self.assertAlmostEqual(out["mean_observed_g"], out["mean_limit_g"], places=9)
        self.assertTrue(out["within_limits"])

    def test_observed_minimum_is_reported(self):
        out = bond_pull_assessment([9.0, 7.5, 11.0], 4.0, 6.0)
        self.assertAlmostEqual(out["minimum_observed_g"], 7.5, places=9)

    def test_empty_sample_rejected(self):
        with self.assertRaises(ValueError):
            bond_pull_assessment([], 4.0, 6.0)

    def test_negative_pull_value_rejected(self):
        with self.assertRaises(ValueError):
            bond_pull_assessment([9.0, -1.0], 4.0, 6.0)

    def test_floor_above_mean_floor_rejected(self):
        with self.assertRaises(ValueError):
            bond_pull_assessment([9.0, 10.0], 8.0, 6.0)

    def test_non_numeric_pull_value_rejected(self):
        with self.assertRaises(ValueError):
            bond_pull_assessment([9.0, "10"], 4.0, 6.0)


class DispositionTests(unittest.TestCase):
    def test_clean_record_accepts(self):
        self.assertEqual(lot_disposition({"major": [], "minor": []}), "lot-accepted")

    def test_minor_only_record_accepts_with_a_note(self):
        self.assertEqual(
            lot_disposition({"major": [], "minor": ["lead-finish-blemish"]}),
            "lot-accepted-with-record",
        )

    def test_any_major_rejects(self):
        self.assertEqual(
            lot_disposition({"major": ["die-crack"], "minor": ["lead-finish-blemish"]}),
            "lot-rejected",
        )

    def test_missing_bucket_rejected(self):
        with self.assertRaises(ValueError):
            lot_disposition({"major": []})


class AssessmentTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {
            "date_code_counts": {"2341": 600},
            "observed_defects": [],
            "void_limits": dict(VOID_LIMITS),
            "total_void_fraction": 0.04,
            "largest_void_fraction": 0.02,
            "pull_values_g": [9.0, 10.0, 11.0],
            "bond_minimum_g": 4.0,
            "bond_mean_minimum_g": 6.0,
        }
        spec.update(over)
        return spec

    def test_clean_teardown_accepts_the_lot(self):
        out = assess_destructive_physical_analysis(self._spec())
        self.assertEqual(out["disposition"], "lot-accepted")
        self.assertTrue(out["accepted"])
        self.assertEqual(out["findings"], [])

    def test_sample_plan_travels_with_the_result(self):
        out = assess_destructive_physical_analysis(self._spec())
        self.assertEqual(out["sample_plan"]["total_sample"], 6)

    def test_minor_observation_keeps_the_lot(self):
        out = assess_destructive_physical_analysis(
            self._spec(observed_defects=["external-marking-blemish"])
        )
        self.assertEqual(out["disposition"], "lot-accepted-with-record")
        self.assertTrue(out["accepted"])

    def test_major_observation_rejects_the_lot(self):
        out = assess_destructive_physical_analysis(
            self._spec(observed_defects=["package-seal-leak"])
        )
        self.assertEqual(out["disposition"], "lot-rejected")
        self.assertFalse(out["accepted"])

    def test_numeric_void_failure_becomes_a_major_defect(self):
        out = assess_destructive_physical_analysis(
            self._spec(total_void_fraction=0.30, largest_void_fraction=0.20)
        )
        self.assertIn("die-attach-void-excess", out["defects"]["major"])
        self.assertEqual(out["disposition"], "lot-rejected")

    def test_numeric_bond_failure_becomes_a_major_defect(self):
        out = assess_destructive_physical_analysis(
            self._spec(pull_values_g=[9.0, 1.0, 11.0])
        )
        self.assertIn("bond-pull-below-limit", out["defects"]["major"])

    def test_multi_date_code_shipment_raises_a_finding(self):
        out = assess_destructive_physical_analysis(
            self._spec(date_code_counts={"2341": 600, "2402": 400})
        )
        self.assertTrue(any("date codes" in f for f in out["findings"]))

    def test_unregistered_observed_defect_rejected(self):
        with self.assertRaises(ValueError):
            assess_destructive_physical_analysis(
                self._spec(observed_defects=["something-unusual"])
            )

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["void_limits"]
        with self.assertRaises(ValueError):
            assess_destructive_physical_analysis(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_destructive_physical_analysis(["date_code_counts"])

    def test_duplicate_defect_codes_are_reported_once(self):
        out = assess_destructive_physical_analysis(
            self._spec(observed_defects=["die-crack", "die-crack"])
        )
        self.assertEqual(out["defects"]["major"], ["die-crack"])


if __name__ == "__main__":
    unittest.main()
