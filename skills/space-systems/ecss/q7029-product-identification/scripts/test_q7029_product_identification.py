"""Contract tests for the ECSS-Q-ST-70-29 product-identification logic."""

import unittest

from q7029_product_identification_logic import (
    DEFAULT_CONFIRMED_SCORE,
    DEFAULT_RI_WINDOW,
    GRADE_CONFIRMED,
    GRADE_TENTATIVE,
    GRADE_UNIDENTIFIED,
    apply_confirmation_rule,
    assess_identification,
    best_candidate,
    coelution_pairs,
    grade_assignment,
    identify_peak,
    retention_index_deviation,
    unidentified_area_fraction,
    validate_library,
    validate_peak,
)

LIBRARY = {
    "toluene": {"reference_index": 770.0, "toxicity_driver": False},
    "benzene": {"reference_index": 660.0, "toxicity_driver": True},
    "hexanal": {"reference_index": 800.0, "toxicity_driver": False},
    "acetaldehyde": {"reference_index": 450.0, "toxicity_driver": True},
}


def peak(peak_id, ri, area, candidates, second=False):
    return {
        "peak_id": peak_id,
        "retention_index": ri,
        "area_counts": area,
        "candidates": candidates,
        "second_technique": second,
    }


class ValidatePeakTests(unittest.TestCase):
    def test_valid_peak_is_normalised(self):
        record = validate_peak(peak("p1", 770.0, 1000.0, [{"compound": "toluene", "match_score": 900.0}]))
        self.assertEqual(record["peak_id"], "p1")
        self.assertAlmostEqual(record["retention_index"], 770.0)
        self.assertAlmostEqual(record["area_counts"], 1000.0)

    def test_missing_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_peak({"peak_id": "p1", "retention_index": 770.0})

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_peak(peak("p1", 770.0, 0.0, []))

    def test_empty_peak_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_peak(peak("   ", 770.0, 10.0, []))

    def test_boolean_retention_index_rejected(self):
        with self.assertRaises(ValueError):
            validate_peak(peak("p1", True, 10.0, []))

    def test_score_above_scale_rejected(self):
        with self.assertRaises(ValueError):
            validate_peak(peak("p1", 770.0, 10.0, [{"compound": "toluene", "match_score": 1200.0}]))

    def test_non_mapping_peak_rejected(self):
        with self.assertRaises(ValueError):
            validate_peak(["p1"])


class ValidateLibraryTests(unittest.TestCase):
    def test_library_entries_are_normalised(self):
        lib = validate_library(LIBRARY)
        self.assertAlmostEqual(lib["benzene"]["reference_index"], 660.0)
        self.assertTrue(lib["benzene"]["toxicity_driver"])

    def test_empty_library_rejected(self):
        with self.assertRaises(ValueError):
            validate_library({})

    def test_entry_without_reference_index_rejected(self):
        with self.assertRaises(ValueError):
            validate_library({"toluene": {"toxicity_driver": False}})


class DeviationAndGradeTests(unittest.TestCase):
    def test_deviation_is_absolute(self):
        self.assertAlmostEqual(retention_index_deviation(765.0, 770.0), 5.0)
        self.assertAlmostEqual(retention_index_deviation(775.0, 770.0), 5.0)

    def test_negative_index_rejected(self):
        with self.assertRaises(ValueError):
            retention_index_deviation(-765.0, 770.0)

    def test_strong_match_in_window_is_confirmed(self):
        self.assertEqual(grade_assignment(920.0, 4.0), GRADE_CONFIRMED)

    def test_score_exactly_on_the_confirmation_threshold_is_confirmed(self):
        self.assertAlmostEqual(DEFAULT_CONFIRMED_SCORE, 850.0, places=9)
        self.assertEqual(grade_assignment(DEFAULT_CONFIRMED_SCORE, 1.0), GRADE_CONFIRMED)

    def test_deviation_exactly_on_the_window_is_still_in_window(self):
        self.assertEqual(grade_assignment(900.0, DEFAULT_RI_WINDOW), GRADE_CONFIRMED)

    def test_strong_score_outside_the_window_is_only_tentative(self):
        self.assertEqual(grade_assignment(950.0, 30.0), GRADE_TENTATIVE)

    def test_weak_score_in_window_is_tentative(self):
        self.assertEqual(grade_assignment(720.0, 3.0), GRADE_TENTATIVE)

    def test_weak_score_far_outside_is_unidentified(self):
        self.assertEqual(grade_assignment(500.0, 90.0), GRADE_UNIDENTIFIED)

    def test_tentative_threshold_above_confirmed_rejected(self):
        with self.assertRaises(ValueError):
            grade_assignment(900.0, 1.0, 20.0, 700.0, 850.0)


class CandidateSelectionTests(unittest.TestCase):
    def test_best_candidate_prefers_the_better_grade_over_the_better_score(self):
        record = validate_peak(peak("p1", 770.0, 100.0, [
            {"compound": "hexanal", "match_score": 980.0},
            {"compound": "toluene", "match_score": 880.0},
        ]))
        best = best_candidate(record, validate_library(LIBRARY))
        self.assertEqual(best["compound"], "toluene")
        self.assertEqual(best["grade"], GRADE_CONFIRMED)

    def test_candidate_absent_from_the_library_is_ignored(self):
        record = validate_peak(peak("p1", 770.0, 100.0, [
            {"compound": "unknown-ester", "match_score": 990.0},
        ]))
        self.assertIsNone(best_candidate(record, validate_library(LIBRARY)))

    def test_peak_with_no_gradeable_candidate_is_unidentified(self):
        record = identify_peak(peak("p9", 300.0, 50.0, [
            {"compound": "toluene", "match_score": 300.0},
        ]), LIBRARY)
        self.assertEqual(record["grade"], GRADE_UNIDENTIFIED)
        self.assertIsNone(record["compound"])
        self.assertEqual(len(record["notes"]), 1)


class CoelutionTests(unittest.TestCase):
    def _records(self):
        return [
            identify_peak(peak("p1", 770.0, 100.0, [{"compound": "toluene", "match_score": 900.0}]), LIBRARY),
            identify_peak(peak("p2", 772.0, 100.0, [{"compound": "hexanal", "match_score": 900.0}]), LIBRARY),
        ]

    def test_close_pair_is_detected(self):
        self.assertEqual(coelution_pairs(self._records()), [("p1", "p2")])

    def test_resolved_pair_is_not_detected(self):
        records = [
            identify_peak(peak("p1", 770.0, 100.0, [{"compound": "toluene", "match_score": 900.0}]), LIBRARY),
            identify_peak(peak("p3", 800.0, 100.0, [{"compound": "hexanal", "match_score": 900.0}]), LIBRARY),
        ]
        self.assertEqual(coelution_pairs(records), [])

    def test_zero_resolution_floor_rejected(self):
        with self.assertRaises(ValueError):
            coelution_pairs(self._records(), 0.0)


class ConfirmationRuleTests(unittest.TestCase):
    def test_unconfirmed_driver_is_downgraded(self):
        records = [identify_peak(
            peak("p4", 660.0, 100.0, [{"compound": "benzene", "match_score": 960.0}]), LIBRARY
        )]
        self.assertEqual(records[0]["grade"], GRADE_CONFIRMED)
        self.assertEqual(apply_confirmation_rule(records), ["p4"])
        self.assertEqual(records[0]["grade"], GRADE_TENTATIVE)

    def test_driver_with_second_technique_survives(self):
        records = [identify_peak(
            peak("p4", 660.0, 100.0, [{"compound": "benzene", "match_score": 960.0}], second=True),
            LIBRARY,
        )]
        self.assertEqual(apply_confirmation_rule(records), [])
        self.assertEqual(records[0]["grade"], GRADE_CONFIRMED)


class AreaAccountingTests(unittest.TestCase):
    def test_fraction_counts_only_unidentified_area(self):
        records = [
            identify_peak(peak("p1", 770.0, 900.0, [{"compound": "toluene", "match_score": 900.0}]), LIBRARY),
            identify_peak(peak("p9", 300.0, 100.0, []), LIBRARY),
        ]
        self.assertAlmostEqual(unidentified_area_fraction(records), 0.1, places=9)

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            unidentified_area_fraction([])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "peaks": [
                peak("p1", 770.0, 900.0, [{"compound": "toluene", "match_score": 930.0}]),
                peak("p2", 800.0, 60.0, [{"compound": "hexanal", "match_score": 900.0}]),
                peak("p3", 310.0, 40.0, []),
            ],
            "library": LIBRARY,
        }
        spec.update(overrides)
        return spec

    def test_clean_inventory_has_no_findings(self):
        result = assess_identification(self._spec())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["inventory_complete"])
        self.assertEqual(result["grade_counts"][GRADE_CONFIRMED], 2)

    def test_unidentified_fraction_is_reported(self):
        result = assess_identification(self._spec())
        self.assertAlmostEqual(result["unidentified_area_fraction"], 0.04, places=9)

    def test_budget_exceeded_is_flagged(self):
        result = assess_identification(self._spec(unidentified_budget=0.01))
        self.assertFalse(result["inventory_complete"])
        self.assertEqual(len(result["findings"]), 1)

    def test_fraction_exactly_on_the_budget_is_within_it(self):
        result = assess_identification(self._spec(unidentified_budget=0.04))
        self.assertAlmostEqual(result["unidentified_area_fraction"], result["unidentified_budget"], places=9)
        self.assertTrue(result["inventory_complete"])

    def test_unconfirmed_driver_raises_a_finding(self):
        spec = self._spec(peaks=[
            peak("p1", 770.0, 900.0, [{"compound": "toluene", "match_score": 930.0}]),
            peak("p4", 660.0, 100.0, [{"compound": "benzene", "match_score": 960.0}]),
        ])
        result = assess_identification(spec)
        self.assertEqual(result["unconfirmed_drivers"], ["p4"])
        self.assertEqual(len(result["findings"]), 1)

    def test_duplicate_peak_id_rejected(self):
        spec = self._spec(peaks=[
            peak("p1", 770.0, 900.0, [{"compound": "toluene", "match_score": 930.0}]),
            peak("p1", 800.0, 100.0, [{"compound": "hexanal", "match_score": 930.0}]),
        ])
        with self.assertRaises(ValueError):
            assess_identification(spec)

    def test_missing_library_key_rejected(self):
        spec = self._spec()
        del spec["library"]
        with self.assertRaises(ValueError):
            assess_identification(spec)

    def test_empty_peak_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_identification(self._spec(peaks=[]))

    def test_budget_above_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_identification(self._spec(unidentified_budget=1.5))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_identification(["peaks"])


if __name__ == "__main__":
    unittest.main()
