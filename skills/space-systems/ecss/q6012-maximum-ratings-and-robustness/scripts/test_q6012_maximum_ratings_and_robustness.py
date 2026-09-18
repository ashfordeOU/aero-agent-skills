"""Contract tests for the clause 7.2.9 maximum-rating and robustness logic.

Each workflow step of the skill - rating validation, onset margin, robustness
evidence review, derated application stress and the grouped verdict - has its
own case here, so a regression in any one step is caught before the leaf gate
is reached. Offline, stdlib unittest only.
"""

import math
import unittest

from q6012_maximum_ratings_and_robustness_logic import (
    RATIO_TOLERANCE,
    assess_demonstrations,
    assess_maximum_ratings,
    assess_rating,
    derated_limit,
    group_outcomes,
    onset_headroom,
    rating_supported_by_onset,
    usage_ratio,
    validate_demonstration,
    validate_rating,
    validate_requirements,
    worst_case_stress,
)


def drain_rating(**overrides):
    """A drain-source boundary drawn from a step-stress onset, in volts."""
    rating = {
        "name": "vds-max",
        "unit": "V",
        "boundary": 20.0,
        "onset": 30.0,
        "safety_factor": 1.5,
        "derating_factor": 0.75,
        "applied_nominal": 12.0,
        "applied_tolerance_fraction": 0.05,
        "applied_transient_factor": 1.1,
    }
    rating.update(overrides)
    return rating


def soak(**overrides):
    """A robustness soak driven at the boundary itself."""
    demo = {
        "rating": "vds-max",
        "stress_level": 20.0,
        "sample_size": 10,
        "duration_h": 240.0,
        "devices_lost": 0,
        "drift_fraction": 0.02,
    }
    demo.update(overrides)
    return demo


class ValidateRatingTests(unittest.TestCase):
    def test_normalises_to_floats(self):
        record = validate_rating(drain_rating(boundary=20, onset=30))
        self.assertEqual(record["boundary"], 20.0)
        self.assertEqual(record["onset"], 30.0)

    def test_defaults_are_filled_when_absent(self):
        rating = drain_rating()
        del rating["applied_tolerance_fraction"]
        del rating["applied_transient_factor"]
        record = validate_rating(rating)
        self.assertEqual(record["applied_tolerance_fraction"], 0.0)
        self.assertEqual(record["applied_transient_factor"], 1.0)

    def test_zero_boundary_rejected(self):
        with self.assertRaises(ValueError):
            validate_rating(drain_rating(boundary=0.0))

    def test_negative_onset_rejected(self):
        with self.assertRaises(ValueError):
            validate_rating(drain_rating(onset=-30.0))

    def test_safety_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_rating(drain_rating(safety_factor=0.9))

    def test_derating_factor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_rating(drain_rating(derating_factor=1.2))

    def test_boolean_boundary_rejected(self):
        with self.assertRaises(ValueError):
            validate_rating(drain_rating(boundary=True))

    def test_non_finite_boundary_rejected(self):
        with self.assertRaises(ValueError):
            validate_rating(drain_rating(boundary=float("inf")))

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_rating(drain_rating(name="  "))

    def test_missing_key_rejected(self):
        rating = drain_rating()
        del rating["onset"]
        with self.assertRaises(ValueError):
            validate_rating(rating)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_rating(["vds-max", 20.0])


class DemonstrationValidationTests(unittest.TestCase):
    def test_accepts_a_well_formed_soak(self):
        record = validate_demonstration(soak())
        self.assertEqual(record["sample_size"], 10)

    def test_fractional_sample_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_demonstration(soak(sample_size=7.5))

    def test_losses_beyond_the_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_demonstration(soak(devices_lost=11))

    def test_negative_drift_rejected(self):
        with self.assertRaises(ValueError):
            validate_demonstration(soak(drift_fraction=-0.01))

    def test_requirements_defaults(self):
        checked = validate_requirements(None)
        self.assertEqual(checked["min_sample_size"], 5)
        self.assertAlmostEqual(checked["min_duration_h"], 168.0, places=9)

    def test_requirement_drift_at_or_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements({"max_drift_fraction": 1.0})


class ArithmeticTests(unittest.TestCase):
    def test_derated_limit_scales_the_boundary(self):
        self.assertAlmostEqual(derated_limit(20.0, 0.75), 15.0, places=9)

    def test_derating_of_one_leaves_the_boundary(self):
        self.assertAlmostEqual(derated_limit(20.0, 1.0), 20.0, places=9)

    def test_worst_case_stress_stacks_tolerance_and_transient(self):
        self.assertAlmostEqual(
            worst_case_stress(10.0, 0.05, 1.2), 10.0 * 1.05 * 1.2, places=9
        )

    def test_worst_case_stress_of_a_quiet_nominal_is_zero(self):
        self.assertAlmostEqual(worst_case_stress(0.0, 0.1, 1.5), 0.0, places=9)

    def test_transient_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_stress(10.0, 0.0, 0.9)

    def test_usage_ratio_is_stress_over_limit(self):
        self.assertAlmostEqual(usage_ratio(7.5, 15.0), 0.5, places=9)

    def test_usage_ratio_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            usage_ratio(7.5, 0.0)

    def test_onset_headroom_is_a_multiple(self):
        self.assertAlmostEqual(onset_headroom(30.0, 20.0), 1.5, places=9)


class OnsetSupportTests(unittest.TestCase):
    def test_exact_required_headroom_is_supported(self):
        self.assertTrue(rating_supported_by_onset(30.0, 20.0, 1.5))

    def test_headroom_above_requirement_is_supported(self):
        self.assertTrue(rating_supported_by_onset(40.0, 20.0, 1.5))

    def test_boundary_level_with_the_onset_is_not_supported(self):
        self.assertFalse(rating_supported_by_onset(20.0, 20.0, 1.5))

    def test_clearly_short_headroom_is_not_supported(self):
        self.assertFalse(rating_supported_by_onset(22.0, 20.0, 1.5))

    def test_tolerance_is_small_enough_to_keep_the_limit_meaningful(self):
        self.assertLess(RATIO_TOLERANCE, 1e-6)


class DemonstrationAssessmentTests(unittest.TestCase):
    def _rating(self, **kw):
        return validate_rating(drain_rating(**kw))

    def test_missing_evidence_is_reported(self):
        result = assess_demonstrations(self._rating(), [])
        self.assertEqual(result["outcome"], "no-robustness-demonstration")
        self.assertIsNone(result["used"])

    def test_soak_at_the_boundary_is_accepted(self):
        result = assess_demonstrations(self._rating(), [soak()])
        self.assertEqual(result["outcome"], "accepted")
        self.assertAlmostEqual(result["stress_ratio"], 1.0, places=9)

    def test_soak_below_the_boundary_is_rejected(self):
        result = assess_demonstrations(self._rating(), [soak(stress_level=18.0)])
        self.assertEqual(result["outcome"], "demonstration-below-boundary")

    def test_undersized_sample_is_rejected(self):
        result = assess_demonstrations(self._rating(), [soak(sample_size=3)])
        self.assertEqual(result["outcome"], "demonstration-undersized")

    def test_short_soak_is_rejected(self):
        result = assess_demonstrations(self._rating(), [soak(duration_h=24.0)])
        self.assertEqual(result["outcome"], "demonstration-too-short")

    def test_a_lost_device_stops_acceptance(self):
        result = assess_demonstrations(self._rating(), [soak(devices_lost=1)])
        self.assertEqual(result["outcome"], "demonstration-lost-device")

    def test_excess_drift_is_rejected(self):
        result = assess_demonstrations(self._rating(), [soak(drift_fraction=0.4)])
        self.assertEqual(result["outcome"], "demonstration-drift-excessive")

    def test_strongest_soak_is_the_one_reviewed(self):
        weak = soak(stress_level=18.0)
        strong = soak(stress_level=24.0)
        result = assess_demonstrations(self._rating(), [weak, strong])
        self.assertEqual(result["count"], 2)
        self.assertAlmostEqual(result["used"]["stress_level"], 24.0, places=9)

    def test_evidence_for_another_rating_is_ignored(self):
        result = assess_demonstrations(
            self._rating(), [soak(rating="ich-max")]
        )
        self.assertEqual(result["outcome"], "no-robustness-demonstration")

    def test_non_sequence_evidence_rejected(self):
        with self.assertRaises(ValueError):
            assess_demonstrations(self._rating(), {"rating": "vds-max"})


class RatingAssessmentTests(unittest.TestCase):
    def test_a_sound_rating_is_accepted(self):
        record = assess_rating(drain_rating(), [soak()])
        self.assertTrue(record["accepted"])
        self.assertEqual(record["outcome"], "accepted")
        self.assertEqual(record["findings"], [])

    def test_derated_envelope_and_usage_are_reported(self):
        record = assess_rating(drain_rating(), [soak()])
        self.assertAlmostEqual(record["derated_limit"], 15.0, places=9)
        self.assertAlmostEqual(
            record["worst_case_stress"], 12.0 * 1.05 * 1.1, places=9
        )
        self.assertAlmostEqual(
            record["derated_usage_ratio"], (12.0 * 1.05 * 1.1) / 15.0, places=9
        )

    def test_stress_exactly_on_the_derated_limit_is_accepted(self):
        record = assess_rating(
            drain_rating(applied_nominal=15.0, applied_tolerance_fraction=0.0,
                         applied_transient_factor=1.0),
            [soak()],
        )
        self.assertAlmostEqual(record["derated_usage_ratio"], 1.0, places=9)
        self.assertTrue(record["accepted"])

    def test_stress_over_the_derated_limit_is_a_finding(self):
        record = assess_rating(drain_rating(applied_nominal=16.0), [soak()])
        self.assertEqual(record["outcome"], "application-over-derated-limit")
        self.assertFalse(record["accepted"])

    def test_short_onset_margin_dominates_the_outcome(self):
        record = assess_rating(drain_rating(onset=22.0), [soak()])
        self.assertEqual(record["outcome"], "onset-margin-short")
        self.assertAlmostEqual(record["onset_headroom"], 1.1, places=9)

    def test_missing_evidence_surfaces_as_the_outcome(self):
        record = assess_rating(drain_rating(), [])
        self.assertEqual(record["outcome"], "no-robustness-demonstration")

    def test_every_broken_rule_is_listed_not_just_the_first(self):
        record = assess_rating(
            drain_rating(onset=21.0, applied_nominal=18.0), []
        )
        self.assertEqual(len(record["findings"]), 3)


class GroupingTests(unittest.TestCase):
    def test_outcomes_are_counted(self):
        grouped = group_outcomes(
            [{"outcome": "accepted"}, {"outcome": "accepted"},
             {"outcome": "onset-margin-short"}]
        )
        self.assertEqual(grouped["accepted"], 2)
        self.assertEqual(grouped["onset-margin-short"], 1)

    def test_findings_are_ordered_before_acceptance(self):
        grouped = group_outcomes(
            [{"outcome": "accepted"}, {"outcome": "onset-margin-short"}]
        )
        self.assertEqual(list(grouped)[0], "onset-margin-short")

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            group_outcomes([{"name": "vds-max"}])


class AssessMaximumRatingsTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "ratings": [
                drain_rating(),
                drain_rating(name="tch-max", unit="C", boundary=150.0,
                             onset=200.0, safety_factor=1.3,
                             derating_factor=0.8, applied_nominal=95.0,
                             applied_tolerance_fraction=0.05,
                             applied_transient_factor=1.0),
            ],
            "demonstrations": [soak(), soak(rating="tch-max", stress_level=150.0)],
        }
        spec.update(overrides)
        return spec

    def test_a_complete_file_is_accepted(self):
        result = assess_maximum_ratings(self._spec())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["grouped"], {"accepted": 2})

    def test_records_come_back_in_name_order(self):
        result = assess_maximum_ratings(self._spec())
        self.assertEqual([r["name"] for r in result["records"]],
                         ["tch-max", "vds-max"])

    def test_one_bad_rating_stops_the_whole_file(self):
        spec = self._spec()
        spec["ratings"][0] = drain_rating(onset=21.0)
        result = assess_maximum_ratings(spec)
        self.assertFalse(result["accepted"])
        self.assertTrue(result["findings"])

    def test_duplicate_rating_name_rejected(self):
        spec = self._spec()
        spec["ratings"].append(drain_rating())
        with self.assertRaises(ValueError):
            assess_maximum_ratings(spec)

    def test_empty_rating_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_maximum_ratings({"ratings": []})

    def test_missing_ratings_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_maximum_ratings({"demonstrations": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_maximum_ratings(["ratings"])

    def test_tighter_requirements_reject_a_previously_good_soak(self):
        spec = self._spec(requirements={"min_sample_size": 22})
        result = assess_maximum_ratings(spec)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["grouped"].get("demonstration-undersized"), 2)

    def test_headroom_matches_the_ratio_of_onset_to_boundary(self):
        result = assess_maximum_ratings(self._spec())
        by_name = {r["name"]: r for r in result["records"]}
        self.assertAlmostEqual(
            by_name["tch-max"]["onset_headroom"], 200.0 / 150.0, places=9
        )
        self.assertTrue(math.isfinite(by_name["vds-max"]["onset_headroom"]))


if __name__ == "__main__":
    unittest.main()
